"""Bootstrap two demo tenants and load their products + FAQ into the system.

Also seeds default settings from env / defaults into the DB.

Run once after `pip install -r requirements.txt`:
    python seed_data.py
"""
from __future__ import annotations

import json
from pathlib import Path

from tinydb import TinyDB

from app.config import SETTING_METADATA, settings
from app.knowledge import ingest
from app.settings_repository import create_repository
from app.tenancy import register_tenant

ROOT = Path(__file__).parent / "seed"


def _load_products(tenant, products_file: Path) -> int:
    data = json.loads(products_file.read_text(encoding="utf-8"))
    db_path = Path(tenant.products_db)
    db_path.unlink(missing_ok=True)
    with TinyDB(tenant.products_db) as db:
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


def _seed_settings():
    """Write default settings from env / defaults into the DB."""
    repo = create_repository(
        settings.storage_backend,
        data_dir=settings.data_dir,
        mongo_uri=settings.mongo_uri,
    )
    existing = repo.list(scope="global")
    if existing:
        print(f"[settings] already seeded ({len(existing)} keys), skipping")
        return
    for key, meta in SETTING_METADATA.items():
        val = getattr(settings, key)
        repo.set(key, str(val), scope="global", description=meta["description"], is_secret=meta["is_secret"])
    print(f"[settings] seeded {len(SETTING_METADATA)} keys into DB")


def main():
    _seed_settings()
    results = [
        _seed_one("demo-beauty", "Mỹ phẩm Glow", "beauty", "beauty"),
        _seed_one("demo-travel", "Du lịch SaoMai", "travel", "travel"),
    ]
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
