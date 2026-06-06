"""Pydantic models for the client-server API surface."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class OrderItemIn(BaseModel):
    product_id: str
    qty: int = Field(gt=0)


class OrderCustomer(BaseModel):
    name: str
    phone: str
    address: str


class OrderRequest(BaseModel):
    items: list[OrderItemIn] = Field(min_length=1)
    customer: OrderCustomer


class BookingCustomer(BaseModel):
    name: str
    phone: str


class BookingRequest(BaseModel):
    type: Literal["spa", "tour"]
    service_id: str
    datetime: str
    people: int = Field(gt=0, default=1)
    customer: BookingCustomer
