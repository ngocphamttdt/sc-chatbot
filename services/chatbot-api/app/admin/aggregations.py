"""Cross-tenant rollups for the conversations log + stats dashboard."""
from __future__ import annotations

import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from math import ceil

from app.tenancy import list_tenants

# Dashboard serves a Vietnamese business; bucket days/hours in ICT (UTC+7) so
# "today", daily activity and peak hours match local expectations.
ICT = timezone(timedelta(hours=7))


# --- Conversations --------------------------------------------------

def list_sessions(tenant_id: str | None, page: int, size: int) -> dict:
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
    return {"page": page, "size": size, "total": total, "items": items_all[start: start + size]}


def get_session_messages(tenant_id: str, session_id: str) -> list[dict]:
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


def _count_distinct_sessions(tenant_id: str | None = None, since_ts: float | None = None) -> int:
    from app.core import mongo

    match: dict = {}
    if tenant_id:
        match["tenant_id"] = tenant_id
    if since_ts is not None:
        match["ts"] = {"$gte": since_ts}
    pipeline = [{"$match": match}, {"$group": {"_id": {"t": "$tenant_id", "s": "$session_id"}}}]
    return len(list(mongo.messages().aggregate(pipeline)))


# --- Stats ----------------------------------------------------------

def _percentile(values: list[float], pct: float) -> float:
    """Nearest-rank percentile (pct in 0..100). Returns 0.0 for empty input."""
    if not values:
        return 0.0
    ordered = sorted(values)
    k = max(0, min(len(ordered) - 1, ceil(pct / 100 * len(ordered)) - 1))
    return ordered[k]


def stats(tenant_id: str | None = None, days: int = 30) -> dict:
    from app.core.mongo import analytics_events

    days = max(1, min(365, days))
    today = datetime.now(ICT).date()
    start_date = today - timedelta(days=days - 1)
    cutoff_ts = datetime(start_date.year, start_date.month, start_date.day, tzinfo=ICT).timestamp()

    query: dict = {"ts": {"$gte": cutoff_ts}}
    if tenant_id:
        query["tenant_id"] = tenant_id
    events = list(analytics_events().find(query, {"_id": 0}))

    total_orders = 0
    total_bookings = 0
    gmv = 0.0
    revenue_txns = 0  # transactions that actually carry an amount (for AOV)
    qa_by_day: Counter[str] = Counter()
    orders_by_day: Counter[str] = Counter()
    hour_buckets: Counter[int] = Counter()
    latencies: list[float] = []
    csat_scores: list[int] = []
    sku_counts: Counter[str] = Counter()
    question_counts: Counter[str] = Counter()
    missing_bookings: set[tuple[str, str]] = set()  # (tenant_id, booking_id)
    total_messages_in = 0

    for e in events:
        ev = e["event"]
        payload = e.get("payload", {}) or {}
        ts = e.get("ts", 0)
        local = datetime.fromtimestamp(ts, tz=ICT)
        day = local.date().isoformat()

        if ev == "message_in":
            total_messages_in += 1
            qa_by_day[day] += 1
            hour_buckets[local.hour] += 1
        elif ev == "order_created":
            total_orders += 1
            orders_by_day[day] += 1
            amount = payload.get("total")
            if isinstance(amount, (int, float)):
                gmv += amount
                revenue_txns += 1
        elif ev == "booking_created":
            total_bookings += 1
            orders_by_day[day] += 1
            amount = payload.get("total_price")
            if isinstance(amount, (int, float)):
                gmv += amount
                revenue_txns += 1
            elif payload.get("booking_id") and e.get("tenant_id"):
                # Older events didn't store total_price; backfill from bookings.
                # Key by (tenant_id, booking_id) — booking_id isn't unique globally.
                missing_bookings.add((e["tenant_id"], payload["booking_id"]))
        elif ev == "product_view":
            sku = payload.get("sku")
            if sku:
                sku_counts[str(sku)] += 1
        elif ev == "faq_hit":
            q = payload.get("query")
            if q:
                question_counts[str(q).strip()] += 1
        elif ev == "response_latency_ms":
            ms = payload.get("ms")
            if isinstance(ms, (int, float)):
                latencies.append(ms)
        elif ev == "csat_rated":
            sc = payload.get("score")
            if isinstance(sc, (int, float)):
                csat_scores.append(int(sc))

    # Backfill GMV for legacy booking events that lack total_price in the payload
    # by reading the price straight from the bookings collection. Match on the
    # (tenant_id, booking_id) pair since booking_id isn't unique across tenants.
    if missing_bookings:
        from app.core.mongo import bookings

        ids = [bid for _, bid in missing_bookings]
        match: dict = {"booking_id": {"$in": ids}}
        if tenant_id:
            match["tenant_id"] = tenant_id
        proj = {"_id": 0, "tenant_id": 1, "booking_id": 1, "total_price": 1}
        for b in bookings().find(match, proj):
            if (b.get("tenant_id"), b.get("booking_id")) not in missing_bookings:
                continue
            price = b.get("total_price")
            if isinstance(price, (int, float)):
                gmv += price
                revenue_txns += 1

    day_keys = [(today - timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]
    qa_per_day = [{"date": d, "count": qa_by_day.get(d, 0)} for d in day_keys]
    orders_per_day = [{"date": d, "count": orders_by_day.get(d, 0)} for d in day_keys]

    conversions = total_orders + total_bookings
    conversion_rate = (conversions / total_messages_in) if total_messages_in else 0.0

    return {
        "total_conversations": _count_distinct_sessions(tenant_id, cutoff_ts),
        "total_messages_in": total_messages_in,
        "total_orders": total_orders,
        "total_bookings": total_bookings,
        "gmv": round(gmv, 2),
        "aov": round(gmv / revenue_txns, 2) if revenue_txns else 0.0,
        "conversion_rate": round(conversion_rate, 3),
        "avg_response_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else 0.0,
        "p50_response_latency_ms": round(_percentile(latencies, 50), 1),
        "p95_response_latency_ms": round(_percentile(latencies, 95), 1),
        "avg_csat": round(sum(csat_scores) / len(csat_scores), 2) if csat_scores else None,
        "top_skus": [{"sku": k, "count": v} for k, v in sku_counts.most_common(5)],
        "top_questions": [{"query": k, "count": v} for k, v in question_counts.most_common(5)],
        "peak_hours": [{"hour": h, "count": hour_buckets.get(h, 0)} for h in range(24)],
        "qa_per_day": qa_per_day,
        "orders_per_day": orders_per_day,
        "generated_at": time.time(),
    }
