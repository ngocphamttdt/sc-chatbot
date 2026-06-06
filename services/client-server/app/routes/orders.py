"""Create / lookup product orders."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app import storage
from app.auth import require_api_key
from app.schemas import OrderRequest

router = APIRouter(prefix="/orders", dependencies=[Depends(require_api_key)])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_order(req: OrderRequest) -> dict:
    try:
        order = storage.create_order(
            items=[i.model_dump() for i in req.items],
            customer=req.customer.model_dump(),
        )
    except ValueError as e:
        msg = str(e)
        if msg.startswith("not_found:"):
            raise HTTPException(status_code=404, detail={"error": msg})
        if msg.startswith("out_of_stock:"):
            raise HTTPException(status_code=409, detail={"error": msg})
        raise HTTPException(status_code=400, detail={"error": msg})

    return {
        "order_id": order["order_id"],
        "status": order["status"],
        "total": order["total"],
    }


@router.get("/{order_id}")
def get_order(order_id: str) -> dict:
    order = storage.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail={"error": "order not found"})
    return order
