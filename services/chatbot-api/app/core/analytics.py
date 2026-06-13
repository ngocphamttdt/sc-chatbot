"""Lightweight analytics: counts events and exposes a report for KPI dashboards.

Tracked event types: message_in, message_out, faq_hit, product_view,
booking_created, order_created, csat_rated, response_latency_ms.
"""
from __future__ import annotations

import time
from collections import Counter
from typing import Any

from app.tenancy import TenantContext


def _col():
    from app.core.mongo import analytics_events
    return analytics_events()


def track(tenant: TenantContext, event: str, payload: dict[str, Any] | None = None) -> None:
    _col().insert_one({
        "tenant_id": tenant.tenant_id,
        "event": event,
        "payload": payload or {},
        "ts": time.time(),
    })


def report(tenant: TenantContext) -> dict[str, Any]:
    rows = list(_col().find({"tenant_id": tenant.tenant_id}, {"_id": 0}))
    counts = Counter(r["event"] for r in rows)

    latencies = [
        r["payload"].get("ms", 0)
        for r in rows
        if r["event"] == "response_latency_ms" and isinstance(r["payload"].get("ms"), (int, float))
    ]
    avg_latency_ms = sum(latencies) / len(latencies) if latencies else 0.0

    csat = [
        r["payload"].get("score")
        for r in rows
        if r["event"] == "csat_rated" and isinstance(r["payload"].get("score"), (int, float))
    ]
    avg_csat = sum(csat) / len(csat) if csat else None

    messages_in = counts.get("message_in", 0)
    bookings = counts.get("booking_created", 0)
    orders = counts.get("order_created", 0)
    conversion = (bookings + orders) / messages_in if messages_in else 0.0

    return {
        "tenant_id": tenant.tenant_id,
        "events": dict(counts),
        "avg_response_latency_ms": round(avg_latency_ms, 1),
        "avg_csat": round(avg_csat, 2) if avg_csat is not None else None,
        "messages_in": messages_in,
        "bookings_created": bookings,
        "orders_created": orders,
        "conversion_rate": round(conversion, 3),
    }


def rate_csat(tenant: TenantContext, session_id: str, score: int) -> None:
    score = max(1, min(5, int(score)))
    track(tenant, "csat_rated", {"session_id": session_id, "score": score})
    # Keep only the latest csat per session
    all_csat = list(
        _col()
        .find({"tenant_id": tenant.tenant_id, "event": "csat_rated", "payload.session_id": session_id})
        .sort("ts", 1)
    )
    if len(all_csat) > 1:
        ids_to_delete = [r["_id"] for r in all_csat[:-1]]
        _col().delete_many({"_id": {"$in": ids_to_delete}})
