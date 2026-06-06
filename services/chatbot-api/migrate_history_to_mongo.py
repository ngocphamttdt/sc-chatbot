"""One-shot migration: TinyDB conversations.json -> MongoDB.

Walks every tenant under DATA_DIR and copies records from
`data/{tenant}/conversations.json` into the `messages` collection (+ upserts
`conversations` rows). Idempotent: skips records already present (by
tenant_id + session_id + ts).

Usage (from services/chatbot-api):
    python migrate_history_to_mongo.py
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from app.core import mongo
from app.tenancy import list_tenants


def _migrate_tenant(tenant_id: str) -> dict:
    tenant_root: Path = settings.data_dir / tenant_id
    conv_file = tenant_root / "conversations.json"
    if not conv_file.exists():
        return {"tenant_id": tenant_id, "found": 0, "inserted": 0, "skipped": 0}

    raw = json.loads(conv_file.read_text(encoding="utf-8"))
    table = raw.get("_default", {}) if isinstance(raw, dict) else {}
    rows = list(table.values()) if isinstance(table, dict) else []

    found = len(rows)
    inserted = 0
    skipped = 0
    seen_sessions: dict[str, tuple[float, float]] = {}

    for r in rows:
        session_id = r.get("session_id")
        ts = r.get("ts")
        if not session_id or ts is None:
            skipped += 1
            continue

        already = mongo.messages().find_one(
            {"tenant_id": tenant_id, "session_id": session_id, "ts": ts}
        )
        if already:
            skipped += 1
        else:
            created_at = datetime.fromtimestamp(ts, tz=timezone.utc)
            mongo.messages().insert_one(
                {
                    "session_id": session_id,
                    "tenant_id": tenant_id,
                    "role": r.get("role", "user"),
                    "content": r.get("content", ""),
                    "ts": ts,
                    "created_at": created_at,
                }
            )
            inserted += 1

        # track session boundaries for conversations collection
        first, last = seen_sessions.get(session_id, (ts, ts))
        seen_sessions[session_id] = (min(first, ts), max(last, ts))

    # Upsert conversations summary for each touched session
    for session_id, (first_ts, last_ts) in seen_sessions.items():
        mongo.conversations().update_one(
            {"tenant_id": tenant_id, "session_id": session_id},
            {
                "$set": {"last_active": datetime.fromtimestamp(last_ts, tz=timezone.utc)},
                "$setOnInsert": {
                    "created_at": datetime.fromtimestamp(first_ts, tz=timezone.utc),
                },
            },
            upsert=True,
        )

    return {
        "tenant_id": tenant_id,
        "found": found,
        "inserted": inserted,
        "skipped": skipped,
        "sessions": len(seen_sessions),
    }


def main() -> None:
    # Probe MongoDB up front so failures are obvious
    try:
        mongo.get_db().command("ping")
    except Exception as e:  # noqa: BLE001
        raise SystemExit(f"Cannot reach MongoDB at {settings.mongo_uri}: {e}")

    results = [_migrate_tenant(t["tenant_id"]) for t in list_tenants()]
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
