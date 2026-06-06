"""Per-tenant system prompt overrides, stored in TinyDB."""
from __future__ import annotations

import time

from tinydb import TinyDB

from app.tenancy import TenantContext


def get_prompt(tenant: TenantContext) -> str | None:
    with TinyDB(tenant.config_db) as db:
        rows = db.all()
    for r in rows:
        if r.get("key") == "system_prompt":
            return r.get("value")
    return None


def set_prompt(tenant: TenantContext, prompt: str) -> None:
    with TinyDB(tenant.config_db) as db:
        db.truncate()
        db.insert(
            {
                "key": "system_prompt",
                "value": prompt,
                "updated_at": time.time(),
            }
        )


def updated_at(tenant: TenantContext) -> float | None:
    with TinyDB(tenant.config_db) as db:
        rows = db.all()
    for r in rows:
        if r.get("key") == "system_prompt":
            return r.get("updated_at")
    return None
