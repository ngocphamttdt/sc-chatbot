"""Cross-tenant rollups for the conversations log + stats dashboard.

Conversation queries dispatch by `STORAGE_BACKEND`. Analytics + tenant
metadata stay in TinyDB regardless.
"""
from __future__ import annotations

import time
from collections import Counter
from datetime import datetime, timedelta, timezone

from tinydb import Query, TinyDB

from app.config import settings
from app.tenancy import get_tenant, list_tenants


# --- Conversations: dispatcher --------------------------------------

def list_sessions(tenant_id: str | None, page: int, size: int) -> dict:
    if settings.storage_backend == "mongo":
        return _mongo_list_sessions(tenant_id, page, size)
    return _tinydb_list_sessions(tenant_id, page, size)


def get_session_messages(tenant_id: str, session_id: str) -> list[dict]:
    if settings.storage_backend == "mongo":
        return _mongo_session_messages(tenant_id, session_id)
    return _tinydb_session_messages(tenant_id, session_id)


def _count_distinct_sessions() -> int:
    if settings.storage_backend == "mongo":
        from app.core import mongo

        return len(
            list(
                mongo.messages().aggregate(
                    [{"$group": {"_id": {"t": "$tenant_id", "s": "$session_id"}}}]
                )
            )
        )
    # TinyDB
    seen: set[tuple[str, str]] = set()
    for t in list_tenants():
        tenant = get_tenant(t["tenant_id"])
        with TinyDB(tenant.conversations_db) as db:
            for r in db.all():
                seen.add((tenant.tenant_id, r["session_id"]))
    return len(seen)


# --- TinyDB queries -------------------------------------------------

def _iter_tenants(tenant_id: str | None):
    if tenant_id:
        yield get_tenant(tenant_id)
        return
    for t in list_tenants():
        yield get_tenant(t["tenant_id"])


def _tinydb_list_sessions(tenant_id: str | None, page: int, size: int) -> dict:
    page = max(1, page)
    size = max(1, min(100, size))

    sessions: dict[tuple[str, str], dict] = {}
    for tenant in _iter_tenants(tenant_id):
        with TinyDB(tenant.conversations_db) as db:
            rows = db.all()
        for r in rows:
            key = (tenant.tenant_id, r["session_id"])
            s = sessions.setdefault(
                key,
                {
                    "session_id": r["session_id"],
                    "tenant_id": tenant.tenant_id,
                    "tenant_name": tenant.name,
                    "turns": 0,
                    "started_at": r["ts"],
                    "last_ts": r["ts"],
                    "last_message": "",
                    "last_role": "",
                },
            )
            s["turns"] += 1
            s["started_at"] = min(s["started_at"], r["ts"])
            if r["ts"] >= s["last_ts"]:
                s["last_ts"] = r["ts"]
                s["last_message"] = (r.get("content") or "")[:160]
                s["last_role"] = r.get("role", "")

    ordered = sorted(sessions.values(), key=lambda s: s["last_ts"], reverse=True)
    total = len(ordered)
    start = (page - 1) * size
    return {
        "page": page,
        "size": size,
        "total": total,
        "items": ordered[start : start + size],
    }


def _tinydb_session_messages(tenant_id: str, session_id: str) -> list[dict]:
    tenant = get_tenant(tenant_id)
    Q = Query()
    with TinyDB(tenant.conversations_db) as db:
        rows = db.search(Q.session_id == session_id)
    rows.sort(key=lambda r: r["ts"])
    return rows


# --- MongoDB queries ------------------------------------------------

def _mongo_list_sessions(tenant_id: str | None, page: int, size: int) -> dict:
    from app.core import mongo

    page = max(1, page)
    size = max(1, min(100, size))

    match: dict = {"tenant_id": tenant_id} if tenant_id else {}

    pipeline = [
        {"$match": match},
        {"$sort": {"ts": 1}},
        {
            "$group": {
                "_id": {"tenant_id": "$tenant_id", "session_id": "$session_id"},
                "turns": {"$sum": 1},
                "started_at": {"$min": "$ts"},
                "last_ts": {"$max": "$ts"},
                "last_doc": {"$last": "$$ROOT"},
            }
        },
        {"$sort": {"last_ts": -1}},
    ]
    all_sessions = list(mongo.messages().aggregate(pipeline))
    name_by_id = {t["tenant_id"]: t["name"] for t in list_tenants()}

    items_all = [
        {
            "session_id": r["_id"]["session_id"],
            "tenant_id": r["_id"]["tenant_id"],
            "tenant_name": name_by_id.get(r["_id"]["tenant_id"], r["_id"]["tenant_id"]),
            "turns": r["turns"],
            "started_at": r["started_at"],
            "last_ts": r["last_ts"],
            "last_message": (r["last_doc"].get("content") or "")[:160],
            "last_role": r["last_doc"].get("role", ""),
        }
        for r in all_sessions
    ]
    total = len(items_all)
    start = (page - 1) * size
    return {
        "page": page,
        "size": size,
        "total": total,
        "items": items_all[start : start + size],
    }


def _mongo_session_messages(tenant_id: str, session_id: str) -> list[dict]:
    from app.core import mongo

    cursor = (
        mongo.messages()
        .find({"tenant_id": tenant_id, "session_id": session_id})
        .sort("ts", 1)
    )
    return [
        {
            "session_id": r["session_id"],
            "tenant_id": r["tenant_id"],
            "role": r["role"],
            "content": r["content"],
            "ts": r["ts"],
        }
        for r in cursor
    ]


# --- Stats (mixed: events from TinyDB, sessions from active backend) ----

def stats() -> dict:
    total_orders = 0
    total_bookings = 0
    qa_by_day: Counter[str] = Counter()
    latencies: list[float] = []
    csat_scores: list[int] = []
    total_messages_in = 0

    for t in list_tenants():
        tenant = get_tenant(t["tenant_id"])
        with TinyDB(tenant.analytics_db) as adb:
            events = adb.all()
        for e in events:
            ev = e["event"]
            payload = e.get("payload", {}) or {}
            ts = e.get("ts", 0)

            if ev == "message_in":
                total_messages_in += 1
                day = datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
                qa_by_day[day] += 1
            elif ev == "order_created":
                total_orders += 1
            elif ev == "booking_created":
                total_bookings += 1
            elif ev == "response_latency_ms":
                ms = payload.get("ms")
                if isinstance(ms, (int, float)):
                    latencies.append(ms)
            elif ev == "csat_rated":
                sc = payload.get("score")
                if isinstance(sc, (int, float)):
                    csat_scores.append(int(sc))

    today = datetime.now(timezone.utc).date()
    qa_per_day = [
        {
            "date": (today - timedelta(days=i)).isoformat(),
            "count": qa_by_day.get((today - timedelta(days=i)).isoformat(), 0),
        }
        for i in range(6, -1, -1)
    ]

    conversions = total_orders + total_bookings
    conversion_rate = (conversions / total_messages_in) if total_messages_in else 0.0

    return {
        "total_conversations": _count_distinct_sessions(),
        "total_messages_in": total_messages_in,
        "total_orders": total_orders,
        "total_bookings": total_bookings,
        "conversion_rate": round(conversion_rate, 3),
        "avg_response_latency_ms": round(sum(latencies) / len(latencies), 1)
        if latencies
        else 0.0,
        "avg_csat": round(sum(csat_scores) / len(csat_scores), 2)
        if csat_scores
        else None,
        "qa_per_day": qa_per_day,
        "generated_at": time.time(),
    }
