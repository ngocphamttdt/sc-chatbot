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
    log.info("→ client-server GET %s", url)
    try:
        r = httpx.get(url, headers=_headers(), timeout=_TIMEOUT)
    except httpx.HTTPError as e:
        log.warning("client-server unreachable: %s", e)
        return None
    if r.status_code == 404:
        log.info("← client-server 404 product_id=%s", product_id)
        return None
    r.raise_for_status()
    log.info("← client-server %s stock=%s", product_id, r.json().get("stock"))
    return r.json()


def list_products() -> list[dict]:
    """Returns [{id, name, price, stock}] or [] if unreachable."""
    url = f"{settings.client_server_url.rstrip('/')}/products"
    log.info("→ client-server GET %s", url)
    try:
        r = httpx.get(url, headers=_headers(), timeout=_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        log.info("← client-server list_products count=%s", len(data))
        return data
    except httpx.HTTPError as e:
        log.warning("client-server unreachable: %s", e)
        return []


def create_order(product_id: str, qty: int, customer: dict) -> dict:
    """POST /orders — decrements stock, returns {order_id, status, total}.

    Raises ValueError on not_found / out_of_stock.
    """
    url = f"{settings.client_server_url.rstrip('/')}/orders"
    payload = {
        "items": [{"product_id": product_id, "qty": qty}],
        "customer": customer,
    }
    log.info("→ client-server POST %s sku=%s qty=%s", url, product_id, qty)
    try:
        r = httpx.post(url, json=payload, headers=_headers(), timeout=_TIMEOUT)
    except httpx.HTTPError as e:
        log.warning("client-server unreachable: %s", e)
        raise ValueError("client-server unreachable")
    if r.status_code in (404, 409):
        detail = r.json().get("detail", {}).get("error", r.text)
        raise ValueError(detail)
    r.raise_for_status()
    data = r.json()
    log.info("← client-server order_id=%s total=%s", data.get("order_id"), data.get("total"))
    return data
