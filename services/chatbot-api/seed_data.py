"""Bootstrap two demo tenants and load their products + FAQ into the system.

Run once after `pip install -r requirements.txt`:
    python seed_data.py
"""
from __future__ import annotations

import json
from pathlib import Path

from tinydb import TinyDB

from app.knowledge import ingest
from app.tenancy import register_tenant

ROOT = Path(__file__).parent / "seed"


def _load_products(tenant, products_file: Path) -> int:
    data = json.loads(products_file.read_text(encoding="utf-8"))
    with TinyDB(tenant.products_db) as db:
        db.truncate()
        db.insert_multiple(data)
    return len(data)


def _seed_one(tenant_id: str, name: str, industry: str, folder: str) -> dict:
    ctx = register_tenant(tenant_id, name, industry)
    base = ROOT / folder
    n_prod = _load_products(ctx, base / "products.json")

    # Index products into the KB too, so the bot can answer "công dụng / chống
    # chỉ định" questions purely from RAG without calling get_product.
    n_chunks = 0
    products = json.loads((base / "products.json").read_text(encoding="utf-8"))
    for p in products:
        text = (
            f"Sản phẩm {p['sku']} - {p['name']}\n"
            f"Danh mục: {p.get('category','')}\n"
            f"Giá: {p.get('price')}đ\n"
            f"Mô tả: {p.get('description','')}\n"
            + (f"Công dụng / hướng dẫn: {p['usage']}\n" if p.get("usage") else "")
            + (f"Chống chỉ định: {p['contraindication']}\n" if p.get("contraindication") else "")
        )
        n_chunks += ingest.ingest_text(ctx, text, source=f"product:{p['sku']}")

    # Index FAQ
    faq = base / "faq.md"
    if faq.exists():
        n_chunks += ingest.ingest_file(ctx, faq)

    return {"tenant_id": tenant_id, "products": n_prod, "kb_chunks": n_chunks}


def main():
    results = [
        _seed_one("demo-beauty", "Mỹ phẩm Glow", "beauty", "beauty"),
        _seed_one("demo-travel", "Du lịch SaoMai", "travel", "travel"),
    ]
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
