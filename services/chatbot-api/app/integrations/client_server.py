"""Thin HTTP client for the client-server business API.

All calls carry the shared X-API-Key header. Timeouts are tight (5s) so the
agent loop doesn't hang when client-server is down.
"""
from __future__ import annotations

import logging

import httpx

from app.config import settings

log = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(5.0)


def _headers() -> dict[str, str]:
    return {"X-API-Key": settings.internal_api_key}


def get_stock(product_id: str) -> dict | None:
    """Returns {product_id, name, stock, price} or None if not found."""
    url = f"{settings.client_server_url.rstrip('/')}/products/{product_id}/stock"
    try:
        r = httpx.get(url, headers=_headers(), timeout=_TIMEOUT)
    except httpx.HTTPError as e:
        log.warning("client-server unreachable: %s", e)
        return None
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


def list_products() -> list[dict]:
    """Returns [{id, name, price, stock}] or [] if unreachable."""
    url = f"{settings.client_server_url.rstrip('/')}/products"
    try:
        r = httpx.get(url, headers=_headers(), timeout=_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPError as e:
        log.warning("client-server unreachable: %s", e)
        return []
