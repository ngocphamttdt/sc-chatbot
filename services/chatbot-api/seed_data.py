"""Bootstrap two demo tenants and seed global settings.

Run once after `pip install -r requirements.txt`:
    python seed_data.py

All content (products, FAQ, prompt) is managed via the admin Documents panel.
"""
from __future__ import annotations

import json

from app.config import SETTING_METADATA, settings
from app.settings_repository import create_repository
from app.tenancy import register_tenant


def _seed_one(tenant_id: str, name: str, industry: str) -> dict:
    register_tenant(tenant_id, name, industry)
    return {"tenant_id": tenant_id}


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
        _seed_one("demo-beauty", "Mỹ phẩm Glow", "beauty"),
        _seed_one("demo-travel", "Du lịch SaoMai", "travel"),
    ]
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
