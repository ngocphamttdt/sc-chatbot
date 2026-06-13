"""Settings admin API — CRUD for global / tenant-scoped settings.

All endpoints require JWT admin auth.
"""
from __future__ import annotations

import time

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.admin.auth import require_admin
from app.config import SETTING_METADATA, settings

router = APIRouter(prefix="/settings")


class SettingUpdate(BaseModel):
    value: str
    scope: str = "global"


def _repo():
    if not settings._repo:
        raise HTTPException(500, {"error": "settings repository not initialised"})
    return settings._repo


def _enrich(row: dict) -> dict:
    key = row.get("key", "")
    meta = SETTING_METADATA.get(key, {})
    if "depends_on" in meta:
        row["depends_on"] = meta["depends_on"]
    return row


def _mask(row: dict) -> dict:
    if row.get("is_secret") and row.get("value") != "*****":
        row["value"] = "*****"
    return _enrich(row)


@router.get("")
def list_settings(
    scope: Optional[str] = Query(default=None),
    _: str = Depends(require_admin),
):
    repo = _repo()
    rows = repo.list(scope=scope)
    return [_mask(r) for r in rows]


@router.get("/{key}")
def get_setting(
    key: str,
    scope: str = Query(default="global"),
    _: str = Depends(require_admin),
):
    repo = _repo()
    row = repo.get(key, scope=scope)
    if not row:
        raise HTTPException(404, {"error": f"setting '{key}' not found in scope '{scope}'"})
    return _mask(row)


@router.put("/{key}")
def update_setting(
    key: str,
    body: SettingUpdate,
    _: str = Depends(require_admin),
):
    repo = _repo()
    meta = SETTING_METADATA.get(key, {})
    row = repo.set(
        key,
        body.value,
        scope=body.scope,
        description=meta.get("description", ""),
        is_secret=meta.get("is_secret", False),
    )
    return _mask(row)


@router.get("/{key}/reveal")
def reveal_setting(
    key: str,
    scope: str = Query(default="global"),
    _: str = Depends(require_admin),
):
    repo = _repo()
    row = repo.get(key, scope=scope)
    if not row:
        raise HTTPException(404, {"error": f"setting '{key}' not found in scope '{scope}'"})
    if not row.get("is_secret"):
        raise HTTPException(400, {"error": f"'{key}' is not a secret setting"})
    return {"key": row["key"], "value": row["value"]}


@router.delete("/{key}")
def delete_setting(
    key: str,
    scope: str = Query(default="global"),
    _: str = Depends(require_admin),
):
    repo = _repo()
    ok = repo.delete(key, scope=scope)
    if not ok:
        raise HTTPException(404, {"error": f"setting '{key}' not found in scope '{scope}' or cannot be deleted"})
    return {"ok": True}


@router.post("/reload")
def reload_settings(
    _: str = Depends(require_admin),
):
    settings.reload()
    return {"ok": True, "reloaded_at": time.time()}
