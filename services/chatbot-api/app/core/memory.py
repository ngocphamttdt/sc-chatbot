"""Conversation history — pluggable backend.

Switch backend via `STORAGE_BACKEND` env var:
  - "tinydb" (default): local JSON file per tenant
  - "mongo": MongoDB (collections `messages` + `conversations`)

Public API (`append_turn`, `load_history`, `session_summary`) is identical
across backends; agent.chat() and admin endpoints don't care which one runs.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from tinydb import Query, TinyDB

from app.config import settings
from app.tenancy import TenantContext


# --- Public API (dispatcher) ----------------------------------------

def append_turn(tenant: TenantContext, session_id: str, role: str, content: str) -> None:
    if settings.storage_backend == "mongo":
        _mongo_append_turn(tenant, session_id, role, content)
    else:
        _tinydb_append_turn(tenant, session_id, role, content)


def load_history(tenant: TenantContext, session_id: str, limit: int = 20) -> list[BaseMessage]:
    if settings.storage_backend == "mongo":
        rows = _mongo_load_rows(tenant, session_id, limit)
    else:
        rows = _tinydb_load_rows(tenant, session_id, limit)
    return [_to_message(r) for r in rows]


def session_summary(tenant: TenantContext) -> list[dict]:
    if settings.storage_backend == "mongo":
        return _mongo_session_summary(tenant)
    return _tinydb_session_summary(tenant)


# --- Shared helpers -------------------------------------------------

def _to_message(row: dict) -> BaseMessage:
    role, content = row["role"], row["content"]
    if role == "user":
        return HumanMessage(content=content)
    if role == "assistant":
        return AIMessage(content=content)
    return SystemMessage(content=content)


# --- TinyDB backend -------------------------------------------------

def _tinydb_append_turn(tenant: TenantContext, session_id: str, role: str, content: str) -> None:
    with TinyDB(tenant.conversations_db) as db:
        db.insert(
            {
                "session_id": session_id,
                "tenant_id": tenant.tenant_id,
                "role": role,
                "content": content,
                "ts": time.time(),
            }
        )


def _tinydb_load_rows(tenant: TenantContext, session_id: str, limit: int) -> list[dict]:
    Q = Query()
    with TinyDB(tenant.conversations_db) as db:
        rows = db.search(Q.session_id == session_id)
    rows.sort(key=lambda r: r["ts"])
    return rows[-limit:] if limit else rows


def _tinydb_session_summary(tenant: TenantContext) -> list[dict]:
    with TinyDB(tenant.conversations_db) as db:
        rows = db.all()
    by_session: dict[str, dict] = {}
    for r in rows:
        s = by_session.setdefault(
            r["session_id"],
            {"session_id": r["session_id"], "turns": 0, "started_at": r["ts"]},
        )
        s["turns"] += 1
        s["last_ts"] = r["ts"]
    return list(by_session.values())


# --- MongoDB backend ------------------------------------------------
# Imports done lazily so missing pymongo (or missing server) only fails if
# the user actually selects this backend.

def _mongo_append_turn(tenant: TenantContext, session_id: str, role: str, content: str) -> None:
    from app.core import mongo

    now = datetime.now(timezone.utc)
    ts = time.time()
    mongo.messages().insert_one(
        {
            "session_id": session_id,
            "tenant_id": tenant.tenant_id,
            "role": role,
            "content": content,
            "ts": ts,
            "created_at": now,
        }
    )
    mongo.conversations().update_one(
        {"session_id": session_id, "tenant_id": tenant.tenant_id},
        {
            "$set": {"last_active": now},
            "$setOnInsert": {"created_at": now, "domain": tenant.industry},
        },
        upsert=True,
    )


def _mongo_load_rows(tenant: TenantContext, session_id: str, limit: int) -> list[dict]:
    from app.core import mongo

    cursor = (
        mongo.messages()
        .find({"tenant_id": tenant.tenant_id, "session_id": session_id})
        .sort("ts", 1)
    )
    rows = list(cursor)
    return rows[-limit:] if limit else rows


def _mongo_session_summary(tenant: TenantContext) -> list[dict]:
    from app.core import mongo

    pipeline = [
        {"$match": {"tenant_id": tenant.tenant_id}},
        {
            "$group": {
                "_id": "$session_id",
                "turns": {"$sum": 1},
                "started_at": {"$min": "$ts"},
                "last_ts": {"$max": "$ts"},
            }
        },
    ]
    return [
        {
            "session_id": r["_id"],
            "turns": r["turns"],
            "started_at": r["started_at"],
            "last_ts": r["last_ts"],
        }
        for r in mongo.messages().aggregate(pipeline)
    ]
