"""Per-tenant system prompt management, stored in MongoDB."""
from __future__ import annotations

import time
import uuid

from app.core.mongo import get_db
from app.tenancy import TenantContext


def _fmt(doc: dict) -> dict:
    return {k: v for k, v in doc.items() if k != "_id"}


# ── Multi-prompt CRUD ─────────────────────────────────────────────────────────

def list_prompts(tenant: TenantContext) -> list[dict]:
    return [_fmt(r) for r in get_db().system_prompts.find(
        {"tenant_id": tenant.tenant_id}, {"_id": 0}
    )]


def create_prompt(tenant: TenantContext, name: str, content: str) -> dict:
    doc = {
        "id": str(uuid.uuid4()),
        "tenant_id": tenant.tenant_id,
        "name": name,
        "content": content,
        "is_active": False,
        "created_at": time.time(),
        "updated_at": time.time(),
    }
    get_db().system_prompts.insert_one(doc)
    return _fmt(doc)


def update_prompt(tenant: TenantContext, prompt_id: str, name: str, content: str) -> dict | None:
    result = get_db().system_prompts.find_one_and_update(
        {"tenant_id": tenant.tenant_id, "id": prompt_id},
        {"$set": {"name": name, "content": content, "updated_at": time.time()}},
        return_document=True,
    )
    return _fmt(result) if result else None


def activate_prompt(tenant: TenantContext, prompt_id: str) -> dict | None:
    db = get_db()
    if not db.system_prompts.find_one({"tenant_id": tenant.tenant_id, "id": prompt_id}):
        return None
    db.system_prompts.update_many({"tenant_id": tenant.tenant_id}, {"$set": {"is_active": False}})
    result = db.system_prompts.find_one_and_update(
        {"tenant_id": tenant.tenant_id, "id": prompt_id},
        {"$set": {"is_active": True, "updated_at": time.time()}},
        return_document=True,
    )
    return _fmt(result) if result else None


def delete_prompt(tenant: TenantContext, prompt_id: str) -> bool:
    r = get_db().system_prompts.delete_one({"tenant_id": tenant.tenant_id, "id": prompt_id})
    return r.deleted_count > 0


# ── Legacy single-prompt API (used by chatbot runtime) ────────────────────────

def get_prompt(tenant: TenantContext) -> str | None:
    """Used by chatbot runtime — returns content of active prompt."""
    r = get_db().system_prompts.find_one({"tenant_id": tenant.tenant_id, "is_active": True})
    return r["content"] if r else None


def set_prompt(tenant: TenantContext, prompt: str) -> None:
    """Legacy compat — no-op since UI now uses create_prompt + activate_prompt."""
    pass


def seed_prompt_if_missing(
    tenant: TenantContext,
    name: str,
    content: str,
) -> None:
    """Create and activate a seed prompt only when the tenant has no prompts."""
    now = time.time()
    get_db().system_prompts.update_one(
        {"tenant_id": tenant.tenant_id},
        {
            "$setOnInsert": {
                "id": str(uuid.uuid4()),
                "tenant_id": tenant.tenant_id,
                "name": name,
                "content": content.strip(),
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            }
        },
        upsert=True,
    )


def updated_at(tenant: TenantContext) -> float | None:
    r = get_db().system_prompts.find_one({"tenant_id": tenant.tenant_id, "is_active": True})
    return r.get("updated_at") if r else None
