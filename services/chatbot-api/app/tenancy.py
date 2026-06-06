"""Multi-tenant context.

Every API call carries a tenant_id. Each tenant gets its own folder under
DATA_DIR with isolated databases (conversations, bookings, orders, analytics)
and a private FAISS vector index for its knowledge base.
"""
from __future__ import annotations

import json
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
    def products_db(self) -> str:
        return str(self.root / "products.json")

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


def register_tenant(tenant_id: str, name: str, industry: str) -> TenantContext:
    """Create / update a tenant entry and ensure its folder exists."""
    reg_path = _tenants_registry()
    reg = {}
    if reg_path.exists():
        reg = json.loads(reg_path.read_text(encoding="utf-8"))
    reg[tenant_id] = {"name": name, "industry": industry}
    reg_path.write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")
    _load_tenant.cache_clear()
    return _load_tenant(tenant_id)


def list_tenants() -> list[dict]:
    reg_path = _tenants_registry()
    if not reg_path.exists():
        return []
    reg = json.loads(reg_path.read_text(encoding="utf-8"))
    return [{"tenant_id": k, **v} for k, v in reg.items()]


@lru_cache(maxsize=64)
def _load_tenant(tenant_id: str) -> TenantContext:
    reg_path = _tenants_registry()
    reg = {}
    if reg_path.exists():
        reg = json.loads(reg_path.read_text(encoding="utf-8"))
    meta = reg.get(tenant_id)
    if not meta:
        raise KeyError(f"Tenant '{tenant_id}' is not registered.")
    root = settings.data_dir / tenant_id
    root.mkdir(parents=True, exist_ok=True)
    return TenantContext(
        tenant_id=tenant_id,
        name=meta["name"],
        industry=meta.get("industry", "general"),
        root=root,
    )


def get_tenant(tenant_id: str | None) -> TenantContext:
    ctx = _load_tenant(tenant_id or settings.default_tenant)
    # Defensive: directory may have been wiped after the TenantContext was
    # cached. mkdir is idempotent and cheap, so do it every call.
    ctx.root.mkdir(parents=True, exist_ok=True)
    return ctx
