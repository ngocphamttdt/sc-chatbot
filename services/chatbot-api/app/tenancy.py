"""Multi-tenant context.

Every API call carries a tenant_id. Each tenant gets its own folder under
DATA_DIR with isolated databases (conversations, bookings, orders, analytics)
and a private FAISS vector index for its knowledge base.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.config import settings


@dataclass(frozen=True)
class TenantContext:
    tenant_id: str
    name: str
    industry: str
    root: Path

    @property
    def conversations_db(self) -> str:
        return str(self.root / "conversations.json")

    @property
    def bookings_db(self) -> str:
        return str(self.root / "bookings.json")

    @property
    def orders_db(self) -> str:
        return str(self.root / "orders.json")

    @property
    def analytics_db(self) -> str:
        return str(self.root / "analytics.json")

    @property
    def documents_db(self) -> str:
        return str(self.root / "documents.json")

    @property
    def config_db(self) -> str:
        return str(self.root / "config.json")

    @property
    def vector_dir(self) -> Path:
        d = self.root / "vector"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def uploads_dir(self) -> Path:
        d = self.root / "uploads"
        d.mkdir(parents=True, exist_ok=True)
        return d


def _tenants_registry() -> Path:
    return settings.data_dir / "tenants.json"


def global_settings_db() -> Path:
    return settings.data_dir / "global_settings.json"


def register_tenant(tenant_id: str, name: str, industry: str) -> TenantContext:
    """Create / update a tenant entry and ensure its folder exists."""
    from app.core.mongo import get_db
    now = time.time()
    get_db().tenants.update_one(
        {"tenant_id": tenant_id},
        {
            "$set": {"name": name, "industry": industry, "updated_at": now},
            "$setOnInsert": {"tenant_id": tenant_id, "created_at": now},
        },
        upsert=True,
    )
    _load_tenant.cache_clear()
    return _load_tenant(tenant_id)


def list_tenants() -> list[dict]:
    from app.core.mongo import get_db
    return [
        {"tenant_id": r["tenant_id"], "name": r["name"], "industry": r.get("industry", "general")}
        for r in get_db().tenants.find({}, {"_id": 0})
    ]


@lru_cache(maxsize=64)
def _load_tenant(tenant_id: str) -> TenantContext:
    from app.core.mongo import get_db
    r = get_db().tenants.find_one({"tenant_id": tenant_id})
    if not r:
        raise KeyError(f"Tenant '{tenant_id}' is not registered.")
    root = settings.data_dir / tenant_id
    root.mkdir(parents=True, exist_ok=True)
    return TenantContext(
        tenant_id=tenant_id,
        name=r["name"],
        industry=r.get("industry", "general"),
        root=root,
    )


def get_tenant(tenant_id: str | None) -> TenantContext:
    ctx = _load_tenant(tenant_id or settings.default_tenant)
    # Defensive: directory may have been wiped after the TenantContext was
    # cached. mkdir is idempotent and cheap, so do it every call.
    ctx.root.mkdir(parents=True, exist_ok=True)
    return ctx
