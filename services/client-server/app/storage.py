"""In-memory store seeded from JSON files. Orders are persisted to disk.

Single-process only — fine for the mock business API. Use a Lock to keep
counters monotonic under FastAPI's threadpool.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

SEED_DIR = Path(__file__).resolve().parents[1] / "seed"
ORDERS_FILE = SEED_DIR / "orders.json"

_lock = Lock()
_bootstrapped = False

_products: dict[str, dict] = {}
_orders: dict[str, dict] = {}
_counters = {"order": 0}


def bootstrap() -> None:
    global _bootstrapped
    with _lock:
        if _bootstrapped:
            return
        _products.update(
            {p["id"]: p for p in _load(SEED_DIR / "products.json")}
        )
        if ORDERS_FILE.exists():
            for o in _load(ORDERS_FILE):
                _orders[o["order_id"]] = o
            if _orders:
                _counters["order"] = max(
                    int(k.split("-")[1]) for k in _orders if "-" in k
                )
        _bootstrapped = True


def _load(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def _save_orders() -> None:
    ORDERS_FILE.write_text(
        json.dumps(list(_orders.values()), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# --- Products ----------------------------------------------------------

def all_products() -> list[dict]:
    return list(_products.values())


def get_product(product_id: str) -> dict | None:
    return _products.get(product_id)


# --- Orders ------------------------------------------------------------

def create_order(items: list[dict], customer: dict) -> dict:
    """Validate stock, decrement, persist and return order.

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
        _save_orders()
        return order


def get_order(order_id: str) -> dict | None:
    return _orders.get(order_id)
