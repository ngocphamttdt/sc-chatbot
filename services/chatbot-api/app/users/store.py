"""CRUD for admin_users and tenant_users MongoDB collections."""
from __future__ import annotations

import time
from typing import Optional

import bcrypt
from bson import ObjectId
from bson.errors import InvalidId

from app.core.mongo import get_db

ADMIN_ROLES = ("super_admin", "support")


def _hash_pw(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _check_pw(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def _fmt(doc: dict) -> dict:
    d = {k: v for k, v in doc.items() if k not in ("_id", "password_hash")}
    d["id"] = str(doc["_id"])
    return d


def _oid(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except (InvalidId, TypeError):
        raise ValueError(f"Invalid id: {id_str}")


# ── Admin users ───────────────────────────────────────────────────────────────

def create_admin_user(email: str, password: str, role: str, created_by: str) -> dict:
    if role not in ADMIN_ROLES:
        raise ValueError(f"role phải là một trong: {ADMIN_ROLES}")
    db = get_db()
    if db.admin_users.find_one({"email": email}):
        raise ValueError("Email đã tồn tại")
    doc = {
        "email": email,
        "password_hash": _hash_pw(password),
        "role": role,
        "created_at": time.time(),
        "created_by": created_by,
    }
    result = db.admin_users.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _fmt(doc)


def list_admin_users() -> list:
    return [_fmt(r) for r in get_db().admin_users.find()]


def delete_admin_user(user_id: str) -> bool:
    result = get_db().admin_users.delete_one({"_id": _oid(user_id)})
    return result.deleted_count > 0


def verify_admin_user(email: str, password: str) -> Optional[dict]:
    r = get_db().admin_users.find_one({"email": email})
    if not r or not _check_pw(password, r["password_hash"]):
        return None
    return _fmt(r)


# ── Tenant users ──────────────────────────────────────────────────────────────

def _valid_tenant_role(role: str) -> bool:
    from app.admin.role_store import list_roles
    return any(r["id"] == role for r in list_roles())


def create_tenant_user(
    tenant_id: str, email: str, password: str, role: str, created_by: str
) -> dict:
    if not _valid_tenant_role(role):
        raise ValueError(f"Role không hợp lệ: {role!r}")
    db = get_db()
    if db.tenant_users.find_one({"email": email, "tenant_id": tenant_id}):
        raise ValueError("Email đã tồn tại trong tenant này")
    doc = {
        "email": email,
        "password_hash": _hash_pw(password),
        "tenant_id": tenant_id,
        "role": role,
        "created_at": time.time(),
        "created_by": created_by,
    }
    result = db.tenant_users.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _fmt(doc)


def list_tenant_users(tenant_id: str) -> list:
    return [_fmt(r) for r in get_db().tenant_users.find({"tenant_id": tenant_id})]


def delete_tenant_user(user_id: str) -> bool:
    result = get_db().tenant_users.delete_one({"_id": _oid(user_id)})
    return result.deleted_count > 0


def update_tenant_user_role(user_id: str, role: str) -> Optional[dict]:
    if not _valid_tenant_role(role):
        raise ValueError(f"Role không hợp lệ: {role!r}")
    r = get_db().tenant_users.find_one_and_update(
        {"_id": _oid(user_id)},
        {"$set": {"role": role}},
        return_document=True,
    )
    return _fmt(r) if r else None


def verify_tenant_user(email: str, password: str) -> Optional[dict]:
    r = get_db().tenant_users.find_one({"email": email})
    if not r or not _check_pw(password, r["password_hash"]):
        return None
    return _fmt(r)
