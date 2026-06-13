"""MongoDB client singleton.

Lazy connection — pymongo doesn't actually connect until the first command,
so importing this module is cheap. Indexes are created on first access of
the helper getters.
"""
from __future__ import annotations

from urllib.parse import urlparse

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from app.config import settings

_client: MongoClient | None = None
_db: Database | None = None
_indexes_created = False


def _default_db_name(uri: str) -> str:
    parsed = urlparse(uri)
    # uri may end with /dbname; otherwise default to scchatbot
    name = parsed.path.lstrip("/")
    return name or "scchatbot"


def get_db() -> Database:
    global _client, _db
    if _db is None:
        _client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=3000)
        _db = _client[_default_db_name(settings.mongo_uri)]
    return _db


def _ensure_indexes() -> None:
    global _indexes_created
    if _indexes_created:
        return
    db = get_db()
    db.messages.create_index(
        [("tenant_id", ASCENDING), ("session_id", ASCENDING), ("ts", ASCENDING)]
    )
    db.messages.create_index([("tenant_id", ASCENDING), ("ts", DESCENDING)])
    db.conversations.create_index(
        [("tenant_id", ASCENDING), ("session_id", ASCENDING)], unique=True
    )
    db.conversations.create_index([("tenant_id", ASCENDING), ("last_active", DESCENDING)])
    db.tenants.create_index("tenant_id", unique=True)
    db.system_prompts.create_index([("tenant_id", ASCENDING)])
    db.system_prompts.create_index([("tenant_id", ASCENDING), ("is_active", ASCENDING)])
    db.roles.create_index("id", unique=True)
    db.analytics_events.create_index([("tenant_id", ASCENDING), ("ts", DESCENDING)])
    db.analytics_events.create_index([("tenant_id", ASCENDING), ("event", ASCENDING)])
    db.documents.create_index([("tenant_id", ASCENDING), ("uploaded_at", DESCENDING)])
    db.documents.create_index([("tenant_id", ASCENDING), ("id", ASCENDING)], unique=True)
    db.bookings.create_index([("tenant_id", ASCENDING), ("booking_id", ASCENDING)], unique=True)
    db.bookings.create_index([("tenant_id", ASCENDING), ("tour_code", ASCENDING), ("date", ASCENDING)])
    db.orders.create_index([("tenant_id", ASCENDING), ("order_id", ASCENDING)], unique=True)
    db.products.create_index([("tenant_id", ASCENDING), ("sku", ASCENDING)], unique=True)
    _indexes_created = True


def messages() -> Collection:
    _ensure_indexes()
    return get_db().messages


def conversations() -> Collection:
    _ensure_indexes()
    return get_db().conversations


def settings_col() -> Collection:
    _ensure_indexes()
    col = get_db().settings
    col.create_index([("key", ASCENDING), ("scope", ASCENDING)], unique=True)
    return col
def analytics_events() -> Collection:
    _ensure_indexes()
    return get_db().analytics_events


def documents() -> Collection:
    _ensure_indexes()
    return get_db().documents


def bookings() -> Collection:
    _ensure_indexes()
    return get_db().bookings


def orders() -> Collection:
    _ensure_indexes()
    return get_db().orders


def products() -> Collection:
    _ensure_indexes()
    return get_db().products
