"""Create spa / tour bookings."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app import storage
from app.auth import require_api_key
from app.schemas import BookingRequest

router = APIRouter(prefix="/bookings", dependencies=[Depends(require_api_key)])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_booking(req: BookingRequest) -> dict:
    try:
        booking = storage.create_booking(
            kind=req.type,
            service_id=req.service_id,
            when=req.datetime,
            people=req.people,
            customer=req.customer.model_dump(),
        )
    except ValueError:
        raise HTTPException(
            status_code=404,
            detail={"error": f"{req.type} service '{req.service_id}' not found"},
        )

    return {
        "booking_id": booking["booking_id"],
        "status": booking["status"],
        "datetime": booking["datetime"],
    }
