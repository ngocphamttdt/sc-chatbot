"""Order management tools: stock check (REST -> client-server), create, lookup."""
from __future__ import annotations

import json
import time
import uuid

from langchain_core.tools import tool
from tinydb import Query, TinyDB

from app.core import analytics
from app.integrations import client_server
from app.tenancy import TenantContext


def _orders(tenant: TenantContext) -> TinyDB:
    return TinyDB(tenant.orders_db)


def _products(tenant: TenantContext) -> TinyDB:
    return TinyDB(tenant.products_db)


# Local mock stock used by create_order — kept until create_order is also wired
# to client-server. New stock queries go through `check_stock` -> REST.
_REGIONS = {"HN": "Hà Nội", "HCM": "TP. Hồ Chí Minh", "DN": "Đà Nẵng"}


def _stock(sku: str, region: str) -> int:
    h = abs(hash(sku.upper() + region.upper())) % 30
    return h  # 0..29


def _resolve_product(query: str) -> dict | None:
    """Map an LLM-supplied SKU or product name to a real client-server product.

    The model often invents plausible SKUs, so we fall back to matching the
    query against the live catalogue by id or name substring.
    """
    q = query.strip().lower()

    # 1. Direct SKU hit
    data = client_server.get_stock(query.upper())
    if data is not None:
        return data

    # 2. Match against the live catalogue
    catalog = client_server.list_products()
    for p in catalog:
        if p["id"].lower() == q:
            return client_server.get_stock(p["id"])
    for p in catalog:
        name = p["name"].lower()
        if q in name or name in q:
            return client_server.get_stock(p["id"])
    return None


def make_order_tools(tenant: TenantContext):
    @tool
    def check_stock(product: str) -> str:
        """Kiểm tra tồn kho sản phẩm (gọi sang client-server).

        `product`: SKU (vd BTY-SR01) HOẶC tên sản phẩm (vd "serum vitamin C").
        Nếu không tìm thấy, tool trả về danh sách SKU hợp lệ để chọn lại.
        """
        data = _resolve_product(product)
        if data is None:
            catalog = client_server.list_products()
            if not catalog:
                return "Dịch vụ tồn kho đang lỗi, vui lòng thử lại sau."
            options = "; ".join(f"{p['id']} = {p['name']}" for p in catalog)
            return (
                f"Không tìm thấy '{product}'. "
                f"Hãy chọn đúng SKU trong danh sách: {options}"
            )
        return json.dumps(
            {
                "sku": data["product_id"],
                "name": data["name"],
                "stock": data["stock"],
                "in_stock": data["stock"] > 0,
                "unit_price": data["price"],
            },
            ensure_ascii=False,
        )

    @tool
    def create_order(
        sku: str,
        qty: int,
        customer_name: str,
        phone: str,
        address: str,
        region: str,
    ) -> str:
        """Tạo đơn hàng mới. AI phải hỏi đủ thông tin trước khi gọi tool.

        Bắt buộc: sku, qty, customer_name, phone, address, region.
        Trả về order_id và tổng tiền nếu thành công.
        """
        region = region.upper()
        if region not in _REGIONS:
            return f"Khu vực không hỗ trợ. Chỉ nhận: {list(_REGIONS)}."
        P = Query()
        with _products(tenant) as db:
            prod = db.get(P.sku == sku.upper())
        if not prod:
            return f"Không tìm thấy sản phẩm {sku}."
        if _stock(sku, region) < qty:
            return "Tồn kho không đủ cho khu vực này, đề nghị giảm số lượng hoặc đổi khu vực."

        order_id = "ORD-" + uuid.uuid4().hex[:8].upper()
        total = int(prod.get("price", 0)) * int(qty)
        record = {
            "order_id": order_id,
            "sku": sku.upper(),
            "product_name": prod.get("name"),
            "qty": qty,
            "unit_price": prod.get("price"),
            "total": total,
            "customer": {"name": customer_name, "phone": phone},
            "shipping": {"address": address, "region": _REGIONS[region]},
            "status": "confirmed",
            "created_at": time.time(),
        }
        with _orders(tenant) as db:
            db.insert(record)
        analytics.track(tenant, "order_created", {"order_id": order_id, "total": total})
        return json.dumps(
            {"order_id": order_id, "total": total, "status": "confirmed"}, ensure_ascii=False
        )

    @tool
    def lookup_order(order_id: str) -> str:
        """Tra cứu trạng thái đơn hàng theo order_id."""
        O = Query()
        with _orders(tenant) as db:
            row = db.get(O.order_id == order_id.upper())
        if not row:
            return f"Không tìm thấy đơn {order_id}."
        return json.dumps(row, ensure_ascii=False)

    return [check_stock, create_order, lookup_order]
