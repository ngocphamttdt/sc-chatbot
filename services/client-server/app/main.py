"""client-server: mock business API used by chatbot-api Function Calling tools.

All non-health routes require header `X-API-Key` matching `INTERNAL_API_KEY`.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from app import storage
from app.routes import bookings, orders, products

load_dotenv()


@asynccontextmanager
async def _lifespan(_: FastAPI):
    storage.bootstrap()
    yield


app = FastAPI(title="SC Chatbot - client-server", version="0.1.0", lifespan=_lifespan)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


app.include_router(products.router)
app.include_router(orders.router)
app.include_router(bookings.router)
