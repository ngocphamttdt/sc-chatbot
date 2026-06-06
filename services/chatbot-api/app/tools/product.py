"""Product catalog tools: lookup, keyword search, suggestion."""
from __future__ import annotations

import json

from langchain_core.tools import tool
from tinydb import Query, TinyDB

from app.core import analytics
from app.tenancy import TenantContext


def _db(tenant: TenantContext) -> TinyDB:
    return TinyDB(tenant.products_db)


def make_product_tools(tenant: TenantContext):
    @tool
    def get_product(sku: str) -> str:
        """Lấy thông tin chi tiết một sản phẩm theo mã SKU.

        Trả về: tên, mô tả, công dụng, giá, tồn kho, các thuộc tính khác.
        """
        P = Query()
        with _db(tenant) as db:
            row = db.get(P.sku == sku.upper())
        if not row:
            return f"Không tìm thấy sản phẩm với SKU {sku}."
        analytics.track(tenant, "product_view", {"sku": sku.upper()})
        return json.dumps(row, ensure_ascii=False)

    @tool
    def search_products(keyword: str, limit: int = 5) -> str:
        """Tìm sản phẩm theo từ khóa (tên / mô tả / danh mục).

        `keyword`: từ khóa tiếng Việt. `limit`: số kết quả tối đa.
        """
        kw = keyword.lower()
        with _db(tenant) as db:
            rows = db.all()
        scored = []
        for r in rows:
            haystack = " ".join(
                str(r.get(f, "")) for f in ("name", "description", "category", "tags")
            ).lower()
            if kw in haystack:
                scored.append(r)
            if len(scored) >= limit:
                break
        if not scored:
            return "Không tìm thấy sản phẩm phù hợp."
        return json.dumps(
            [
                {
                    "sku": r["sku"],
                    "name": r["name"],
                    "price": r.get("price"),
                    "category": r.get("category"),
                }
                for r in scored
            ],
            ensure_ascii=False,
        )

    @tool
    def suggest_products(needs: str, limit: int = 3) -> str:
        """Gợi ý sản phẩm phù hợp dựa trên nhu cầu / mô tả khách hàng.

        Heuristic: tách từ khóa từ `needs`, ưu tiên match tags/category trước
        rồi đến tên/mô tả. Trả về tối đa `limit` sản phẩm xếp theo điểm phù hợp.
        """
        tokens = [t.strip().lower() for t in needs.split() if t.strip()]
        with _db(tenant) as db:
            rows = db.all()

        def score(r: dict) -> int:
            tags = " ".join(r.get("tags", [])).lower()
            cat = str(r.get("category", "")).lower()
            text = (str(r.get("name", "")) + " " + str(r.get("description", ""))).lower()
            s = 0
            for t in tokens:
                if t in tags:
                    s += 3
                if t in cat:
                    s += 2
                if t in text:
                    s += 1
            return s

        ranked = sorted(rows, key=score, reverse=True)
        ranked = [r for r in ranked if score(r) > 0][:limit]
        if not ranked:
            return "Chưa có sản phẩm phù hợp. Hãy hỏi thêm khách về nhu cầu cụ thể."
        return json.dumps(
            [
                {
                    "sku": r["sku"],
                    "name": r["name"],
                    "price": r.get("price"),
                    "why": f"Phù hợp với: {', '.join([t for t in tokens if t in (' '.join(r.get('tags', [])) + ' ' + str(r.get('category',''))).lower()]) or 'mô tả sản phẩm'}",
                }
                for r in ranked
            ],
            ensure_ascii=False,
        )

    return [get_product, search_products, suggest_products]
