"""Settings repository protocol with TinyDB and MongoDB backends.

Each setting has: key, value, scope ("global" or "tenant:{id}"),
description, is_secret flag, and updated_at timestamp.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from pathlib import Path

from tinydb import TinyDB, Query


# ── Protocol ──────────────────────────────────────────────────────────────

class SettingsRepository(ABC):
    @abstractmethod
    def get(self, key: str, scope: str = "global") -> dict | None:
        ...

    @abstractmethod
    def list(self, scope: str | None = None) -> list[dict]:
        ...

    @abstractmethod
    def set(
        self,
        key: str,
        value: str,
        scope: str = "global",
        *,
        description: str = "",
        is_secret: bool = False,
    ) -> dict:
        ...

    @abstractmethod
    def delete(self, key: str, scope: str = "global") -> bool:
        ...


# ── TinyDB ────────────────────────────────────────────────────────────────

def _row_to_dict(row: dict) -> dict:
    return {
        "key": row["key"],
        "value": row["value"],
        "scope": row.get("scope", "global"),
        "description": row.get("description", ""),
        "is_secret": row.get("is_secret", False),
        "updated_at": row.get("updated_at", 0.0),
    }


class TinyDBSettingsRepository(SettingsRepository):
    def __init__(self, global_path: str, per_tenant_path_factory):
        self._global_path = global_path
        self._per_tenant_path = per_tenant_path_factory

    def _db(self, scope: str) -> TinyDB:
        if scope == "global":
            Path(self._global_path).parent.mkdir(parents=True, exist_ok=True)
            return TinyDB(self._global_path)
        tenant_id = scope.removeprefix("tenant:")
        path = self._per_tenant_path(tenant_id)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        return TinyDB(path)

    def get(self, key: str, scope: str = "global") -> dict | None:
        db = self._db(scope)
        try:
            rows = db.all()
        finally:
            db.close()
        Q = Query()
        for r in rows:
            if r.get("key") == key:
                row = _row_to_dict(r)
                row["scope"] = scope
                return row
        return None

    def list(self, scope: str | None = None) -> list[dict]:
        if scope:
            db = self._db(scope)
            try:
                rows = db.all()
            finally:
                db.close()
            return [_row_to_dict(r) | {"scope": scope} for r in rows]
        result = []
        # Global
        db = self._db("global")
        try:
            for r in db.all():
                result.append(_row_to_dict(r) | {"scope": "global"})
        finally:
            db.close()
        return result

    def set(
        self,
        key: str,
        value: str,
        scope: str = "global",
        *,
        description: str = "",
        is_secret: bool = False,
    ) -> dict:
        db = self._db(scope)
        try:
            rows = db.all()
            Q = Query()
            existing = None
            for r in rows:
                if r.get("key") == key:
                    existing = r
                    break
            now = time.time()
            if existing:
                db.update(
                    {"value": value, "description": description, "is_secret": is_secret, "updated_at": now},
                    Q.key == key,
                )
            else:
                db.insert(
                    {
                        "key": key,
                        "value": value,
                        "description": description,
                        "is_secret": is_secret,
                        "updated_at": now,
                    }
                )
        finally:
            db.close()
        return {"key": key, "value": value, "scope": scope, "description": description, "is_secret": is_secret, "updated_at": now}

    def delete(self, key: str, scope: str = "global") -> bool:
        if scope == "global":
            return False
        db = self._db(scope)
        try:
            Q = Query()
            removed = db.remove(Q.key == key)
            return len(removed) > 0
        finally:
            db.close()


# ── MongoDB ───────────────────────────────────────────────────────────────

class MongoSettingsRepository(SettingsRepository):
    def __init__(self, mongo_uri: str):
        from pymongo import MongoClient
        from urllib.parse import urlparse

        parsed = urlparse(mongo_uri)
        db_name = parsed.path.lstrip("/") or "scchatbot"
        self._client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
        self._col = self._client[db_name].settings
        self._col.create_index([("key", 1), ("scope", 1)], unique=True)

    def get(self, key: str, scope: str = "global") -> dict | None:
        doc = self._col.find_one({"key": key, "scope": scope})
        if not doc:
            return None
        return {
            "key": doc["key"],
            "value": doc["value"],
            "scope": doc["scope"],
            "description": doc.get("description", ""),
            "is_secret": doc.get("is_secret", False),
            "updated_at": doc.get("updated_at", 0.0),
        }

    def list(self, scope: str | None = None) -> list[dict]:
        q = {} if scope is None else {"scope": scope}
        result = []
        for doc in self._col.find(q):
            result.append({
                "key": doc["key"],
                "value": doc["value"],
                "scope": doc["scope"],
                "description": doc.get("description", ""),
                "is_secret": doc.get("is_secret", False),
                "updated_at": doc.get("updated_at", 0.0),
            })
        return result

    def set(
        self,
        key: str,
        value: str,
        scope: str = "global",
        *,
        description: str = "",
        is_secret: bool = False,
    ) -> dict:
        now = time.time()
        self._col.update_one(
            {"key": key, "scope": scope},
            {"$set": {"value": value, "description": description, "is_secret": is_secret, "updated_at": now}},
            upsert=True,
        )
        return {"key": key, "value": value, "scope": scope, "description": description, "is_secret": is_secret, "updated_at": now}

    def delete(self, key: str, scope: str = "global") -> bool:
        if scope == "global":
            return False
        result = self._col.delete_one({"key": key, "scope": scope})
        return result.deleted_count > 0


# ── Factory ───────────────────────────────────────────────────────────────

def create_repository(
    storage_backend: str,
    *,
    data_dir: str | Path | None = None,
    mongo_uri: str | None = None,
    per_tenant_path_factory=None,
) -> SettingsRepository:
    if storage_backend == "mongo":
        uri = mongo_uri or "mongodb://localhost:27017/scchatbot"
        return MongoSettingsRepository(uri)

    d = Path(data_dir or "./data").resolve()
    d.mkdir(parents=True, exist_ok=True)

    if per_tenant_path_factory is None:

        def _factory(tenant_id: str) -> str:
            p = d / tenant_id / "config.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            return str(p)

        per_tenant_path_factory = _factory

    return TinyDBSettingsRepository(str(d / "global_settings.json"), per_tenant_path_factory)
