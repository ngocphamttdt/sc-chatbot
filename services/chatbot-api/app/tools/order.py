"""Order management tools: stock check (REST -> client-server), create, lookup."""
from __future__ import annotations

import json
import time

from langchain_core.tools import tool

from app.core import analytics
from app.integrations import client_server
from app.tenancy import TenantContext


def _orders_col():
    from app.core.mongo import orders
    return orders()



def _resolve_product(query: str) -> dict | None:
    """Map an LLM-supplied SKU or product name to a real client-server product."""
    q = query.strip().lower()

    data = client_server.get_stock(query.upper())
    if data is not None:
        return data

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
            return f"Không tìm thấy '{product}'. Hãy chọn đúng SKU trong danh sách: {options}"
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
    ) -> str:
        """Tạo đơn hàng mới. AI phải hỏi đủ thông tin trước khi gọi tool.

        Bắt buộc: sku, qty, customer_name, phone, address.
        Trả về order_id và tổng tiền nếu thành công.
        """
        prod = _resolve_product(sku)
        if not prod:
            return f"Không tìm thấy sản phẩm {sku} trong hệ thống."

        try:
            result = client_server.create_order(
                product_id=prod["product_id"],
                qty=qty,
                customer={"name": customer_name, "phone": phone, "address": address},
            )
        except ValueError:
            return "Sản phẩm hiện không còn hàng."

        record = {
            "tenant_id": tenant.tenant_id,
            "order_id": result["order_id"],
            "sku": prod["product_id"],
            "product_name": prod.get("name"),
            "qty": qty,
            "unit_price": prod.get("price"),
            "total": result["total"],
            "customer": {"name": customer_name, "phone": phone},
            "shipping": {"address": address},
            "status": result["status"],
            "created_at": time.time(),
        }
        _orders_col().insert_one(record)
        analytics.track(tenant, "order_created", {"order_id": result["order_id"], "total": result["total"]})
        return json.dumps(
            {"order_id": result["order_id"], "total": result["total"], "status": result["status"]},
            ensure_ascii=False,
        )

    @tool
    def lookup_order(order_id: str) -> str:
        """Tra cứu trạng thái đơn hàng theo order_id."""
        row = _orders_col().find_one(
            {"tenant_id": tenant.tenant_id, "order_id": order_id.upper()}, {"_id": 0}
        )
        if not row:
            return f"Không tìm thấy đơn {order_id}."
        return json.dumps(row, ensure_ascii=False)

    return [check_stock, create_order, lookup_order]
