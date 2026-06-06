"""In-memory store seeded from JSON files.

Single-process only — fine for the mock business API. Use a Lock to keep
counters monotonic under FastAPI's threadpool.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

SEED_DIR = Path(__file__).resolve().parents[1] / "seed"

_lock = Lock()
_bootstrapped = False

_products: dict[str, dict] = {}
_spa_services: dict[str, dict] = {}
_tours: dict[str, dict] = {}
_orders: dict[str, dict] = {}
_bookings: dict[str, dict] = {}
_counters = {"order": 0, "booking": 0}


def bootstrap() -> None:
    global _bootstrapped
    with _lock:
        if _bootstrapped:
            return
        _products.update(
            {p["id"]: p for p in _load(SEED_DIR / "products.json")}
        )
        _spa_services.update(
            {s["id"]: s for s in _load(SEED_DIR / "spa.json")}
        )
        _tours.update(
            {t["id"]: t for t in _load(SEED_DIR / "travel.json")}
        )
        _bootstrapped = True


def _load(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


# --- Products ----------------------------------------------------------

def all_products() -> list[dict]:
    return list(_products.values())


def get_product(product_id: str) -> dict | None:
    return _products.get(product_id)


# --- Spa & tours -------------------------------------------------------

def all_spa_services() -> list[dict]:
    return list(_spa_services.values())


def all_tours() -> list[dict]:
    return list(_tours.values())


def get_service(kind: str, service_id: str) -> dict | None:
    if kind == "spa":
        return _spa_services.get(service_id)
    if kind == "tour":
        return _tours.get(service_id)
    return None


# --- Orders ------------------------------------------------------------

def create_order(items: list[dict], customer: dict) -> dict:
    """Validate stock, decrement, return persisted order.

    Raises ValueError("not_found:<id>") if a product_id is unknown,
    or ValueError("out_of_stock:<id>") if requested qty exceeds stock.
    """
    with _lock:
        total = 0
        resolved: list[dict] = []
        for it in items:
            pid = it["product_id"]
            qty = it["qty"]
            prod = _products.get(pid)
            if not prod:
                raise ValueError(f"not_found:{pid}")
            if qty > prod["stock"]:
                raise ValueError(f"out_of_stock:{pid}")
            resolved.append({**it, "price": prod["price"], "name": prod["name"]})
            total += prod["price"] * qty

        for r in resolved:
            _products[r["product_id"]]["stock"] -= r["qty"]

        _counters["order"] += 1
        order_id = f"ORD-{_counters['order']:04d}"
        order = {
            "order_id": order_id,
            "status": "confirmed",
            "items": resolved,
            "customer": customer,
            "total": total,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        _orders[order_id] = order
        return order


def get_order(order_id: str) -> dict | None:
    return _orders.get(order_id)


# --- Bookings ----------------------------------------------------------

def create_booking(
    kind: str,
    service_id: str,
    when: str,
    people: int,
    customer: dict,
) -> dict:
    """Returns persisted booking. Raises ValueError('not_found') if missing."""
    if not get_service(kind, service_id):
        raise ValueError("not_found")
    with _lock:
        _counters["booking"] += 1
        booking_id = f"BK-{_counters['booking']:04d}"
        booking = {
            "booking_id": booking_id,
            "status": "confirmed",
            "type": kind,
            "service_id": service_id,
            "datetime": when,
            "people": people,
            "customer": customer,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        _bookings[booking_id] = booking
        return booking


def get_booking(booking_id: str) -> dict | None:
    return _bookings.get(booking_id)
