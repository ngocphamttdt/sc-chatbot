"""MongoDB CRUD for roles collection."""
from __future__ import annotations

import time
import uuid
from typing import Optional

from app.core.mongo import get_db

VALID_COLORS = ("emerald", "blue", "purple", "amber", "slate", "rose")
VALID_PERMISSIONS = (
    "stats.read", "conversations.read",
    "documents.read", "documents.write",
    "prompt.read", "prompt.write",
)

_DEFAULT_ROLES = [
    {"id": "manager", "name": "Quản trị viên", "description": "Toàn quyền truy cập",
     "color": "emerald", "permissions": list(VALID_PERMISSIONS), "is_system": True, "created_at": 0.0},
    {"id": "editor", "name": "Biên tập viên", "description": "Quản lý nội dung",
     "color": "blue", "permissions": ["documents.read", "documents.write", "prompt.read", "prompt.write"],
     "is_system": True, "created_at": 0.0},
    {"id": "viewer", "name": "Chỉ xem", "description": "Xem nhưng không chỉnh sửa",
     "color": "slate", "permissions": ["stats.read", "conversations.read", "documents.read", "prompt.read"],
     "is_system": True, "created_at": 0.0},
]

_OLD_IDS = ["role_admin", "role_editor", "role_viewer"]


def _seed() -> None:
    db = get_db()
    # Migrate old-style IDs (role_admin → manager, etc.)
    if db.roles.count_documents({"id": {"$in": _OLD_IDS}}) > 0:
        db.roles.delete_many({"id": {"$in": _OLD_IDS}})
    # Insert default roles that are missing
    for role in _DEFAULT_ROLES:
        if not db.roles.find_one({"id": role["id"]}):
            db.roles.insert_one(dict(role))


def _fmt(doc: dict) -> dict:
    return {k: v for k, v in doc.items() if k != "_id"}


def list_roles() -> list[dict]:
    _seed()
    return [_fmt(r) for r in get_db().roles.find({}, {"_id": 0})]


def get_role_permissions(role_id: str) -> list[str]:
    _seed()
    doc = get_db().roles.find_one({"id": role_id}, {"_id": 0})
    return doc.get("permissions", []) if doc else []


def create_role(name: str, description: str, color: str, permissions: list[str]) -> dict:
    if color not in VALID_COLORS:
        raise ValueError(f"color phải là một trong: {VALID_COLORS}")
    invalid = [p for p in permissions if p not in VALID_PERMISSIONS]
    if invalid:
        raise ValueError(f"Permission không hợp lệ: {invalid}")
    doc = {
        "id": "role_" + str(uuid.uuid4())[:8],
        "name": name, "description": description,
        "color": color, "permissions": permissions,
        "is_system": False, "created_at": time.time(),
    }
    get_db().roles.insert_one(doc)
    return _fmt(doc)


def update_role(role_id: str, name: Optional[str], description: Optional[str],
                color: Optional[str], permissions: Optional[list[str]]) -> dict | None:
    db = get_db()
    existing = db.roles.find_one({"id": role_id})
    if not existing:
        return None
    if existing.get("is_system"):
        raise ValueError("Không thể sửa system role")
    patch: dict = {}
    if name is not None:
        patch["name"] = name
    if description is not None:
        patch["description"] = description
    if color is not None:
        if color not in VALID_COLORS:
            raise ValueError(f"color phải là một trong: {VALID_COLORS}")
        patch["color"] = color
    if permissions is not None:
        invalid = [p for p in permissions if p not in VALID_PERMISSIONS]
        if invalid:
            raise ValueError(f"Permission không hợp lệ: {invalid}")
        patch["permissions"] = permissions
    result = db.roles.find_one_and_update({"id": role_id}, {"$set": patch}, return_document=True)
    return _fmt(result) if result else None


def delete_role(role_id: str) -> bool:
    existing = get_db().roles.find_one({"id": role_id})
    if not existing:
        return False
    if existing.get("is_system"):
        raise ValueError("Không thể xóa system role")
    r = get_db().roles.delete_one({"id": role_id})
    return r.deleted_count > 0
