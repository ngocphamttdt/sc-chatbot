"""Pydantic request/response schemas."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str = Field(..., min_length=1, max_length=128)
    tenant_id: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    latency_ms: int
    error: Optional[str] = None


class TenantCreateRequest(BaseModel):
    tenant_id: str
    name: str
    industry: str = "general"


class IngestRequest(BaseModel):
    tenant_id: Optional[str] = None
    text: Optional[str] = None
    url: Optional[str] = None
    folder: Optional[str] = None
    source: str = "manual"


class IngestResponse(BaseModel):
    chunks_indexed: int


class CSATRequest(BaseModel):
    tenant_id: Optional[str] = None
    session_id: str
    score: int = Field(..., ge=1, le=5)


class AnalyticsResponse(BaseModel):
    report: dict[str, Any]
