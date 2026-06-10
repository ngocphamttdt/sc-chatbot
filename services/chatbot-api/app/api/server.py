"""FastAPI app - HTTP surface for the chatbot (Zalo OA layer omitted per scope)."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.admin.routes import router as admin_router
from app.api.schemas import (
    AnalyticsResponse,
    ChatRequest,
    ChatResponse,
    CSATRequest,
    IngestRequest,
    IngestResponse,
    TenantCreateRequest,
)
from app.config import init_settings
from app.core import agent, analytics, memory
from app.knowledge import ingest
from app.tenancy import get_tenant, list_tenants, register_tenant


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_settings()
    yield


app = FastAPI(title="SC Chatbot", version="0.1.0", lifespan=lifespan)
app.include_router(admin_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


# --- Tenant admin --------------------------------------------------------

@app.get("/tenants")
def tenants():
    return {"tenants": list_tenants()}


@app.post("/tenants")
def create_tenant(req: TenantCreateRequest):
    ctx = register_tenant(req.tenant_id, req.name, req.industry)
    return {"tenant_id": ctx.tenant_id, "name": ctx.name, "industry": ctx.industry}


# --- Chat ----------------------------------------------------------------

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        tenant = get_tenant(req.tenant_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    result = agent.chat(tenant, req.session_id, req.message)
    return ChatResponse(**result)


@app.get("/sessions/{session_id}")
def session(session_id: str, tenant_id: str | None = None):
    try:
        tenant = get_tenant(tenant_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    history = memory.load_history(tenant, session_id, limit=200)
    return {
        "session_id": session_id,
        "messages": [{"role": _role(m), "content": m.content} for m in history],
    }


def _role(m) -> str:
    cls = type(m).__name__
    if cls == "HumanMessage":
        return "user"
    if cls == "AIMessage":
        return "assistant"
    return "system"


# --- Knowledge ingestion -------------------------------------------------

@app.post("/ingest", response_model=IngestResponse)
def ingest_endpoint(req: IngestRequest):
    try:
        tenant = get_tenant(req.tenant_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if req.text:
        n = ingest.ingest_text(tenant, req.text, source=req.source)
    elif req.url:
        n = ingest.ingest_url(tenant, req.url)
    elif req.folder:
        n = ingest.ingest_folder(tenant, req.folder)
    else:
        raise HTTPException(status_code=400, detail="Provide one of: text | url | folder.")
    return IngestResponse(chunks_indexed=n)


# --- Analytics -----------------------------------------------------------

@app.get("/analytics/{tenant_id}", response_model=AnalyticsResponse)
def analytics_report(tenant_id: str):
    try:
        tenant = get_tenant(tenant_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return AnalyticsResponse(report=analytics.report(tenant))


@app.post("/csat")
def csat(req: CSATRequest):
    try:
        tenant = get_tenant(req.tenant_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    analytics.rate_csat(tenant, req.session_id, req.score)
    return {"ok": True}


# --- Simple chat UI ------------------------------------------------------

_UI_PATH = Path(__file__).resolve().parents[2] / "ui" / "index.html"


@app.get("/")
def ui_root():
    if _UI_PATH.exists():
        return FileResponse(_UI_PATH)
    return {"hint": "POST /chat to talk to the bot."}
