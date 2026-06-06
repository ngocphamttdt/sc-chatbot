"""Product catalogue + stock lookup."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app import storage
from app.auth import require_api_key

router = APIRouter(prefix="/products", dependencies=[Depends(require_api_key)])


@router.get("")
def list_products() -> list[dict]:
    return [
        {"id": p["id"], "name": p["name"], "price": p["price"], "stock": p["stock"]}
        for p in storage.all_products()
    ]


@router.get("/{product_id}/stock")
def get_stock(product_id: str) -> dict:
    p = storage.get_product(product_id)
    if not p:
        raise HTTPException(status_code=404, detail={"error": "product not found"})
    return {
        "product_id": p["id"],
        "name": p["name"],
        "stock": p["stock"],
        "price": p["price"],
    }
