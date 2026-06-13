"""FastAPI app - HTTP surface for the chatbot (Zalo OA layer omitted per scope)."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from contextlib import asynccontextmanager
import threading

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

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
async def lifespan(_: FastAPI):
    # Re-run ingest for any docs stuck in 'processing' from a previous crashed/restarted run
    def _recover():
        try:
            from app.core.mongo import documents as get_col
            from app.admin.documents import run_ingest
            stuck = list(get_col().find({"status": "processing"}, {"_id": 0}))
            for doc in stuck:
                try:
                    tenant = get_tenant(doc["tenant_id"])
                    run_ingest(tenant, doc["id"])
                except Exception:
                    pass
        except Exception:
            pass
    threading.Thread(target=_recover, daemon=True).start()
    yield


app = FastAPI(
    lifespan=lifespan,
    title="SC Chatbot Admin API",
    version="1.0.0",
    description="""
API quản lý nền tảng chatbot đa tenant SC Chatbot.

## Xác thực

Tất cả endpoint `/admin/*` yêu cầu Bearer token từ `POST /admin/login`:

```
Authorization: Bearer <token>
```

## Phân quyền

- **super_admin** — toàn quyền
- **support** — xem và hỗ trợ
- **manager / editor / viewer** — tenant users, quyền theo role
""",
    openapi_tags=[
        {"name": "Auth", "description": "Đăng nhập, xác thực token"},
        {"name": "Tenants", "description": "Quản lý doanh nghiệp (tenant)"},
        {"name": "Admin Users", "description": "Nhân viên nội bộ platform"},
        {"name": "Tenant Users", "description": "Nhân viên của từng doanh nghiệp"},
        {"name": "Roles", "description": "Quản lý roles và phân quyền web-admin"},
        {"name": "System Prompts", "description": "System prompt chatbot theo tenant"},
        {"name": "Documents", "description": "Knowledge base — upload & quản lý tài liệu"},
        {"name": "Conversations", "description": "Lịch sử hội thoại"},
        {"name": "Stats", "description": "Thống kê dashboard"},
    ],
    docs_url="/docs",
    redoc_url="/redoc",
)
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
def session(session_id: str, tenant_id: Optional[str] = None):
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


# --- Static SPA (web-admin) at /admin ----------------------------------

STATIC_UI_DIR = Path(__file__).resolve().parents[2] / "static" / "web-admin"
if STATIC_UI_DIR.exists():
    app.mount(
        "/admin/assets",
        StaticFiles(directory=str(STATIC_UI_DIR / "assets")),
        name="admin-ui-assets",
    )

    _API_PATHS = {"health", "tenants", "chat", "ingest", "analytics", "csat", "sessions", "docs", "openapi.json"}

    @app.get("/admin/{full_path:path}")
    async def admin_ui_spa(full_path: str):
        path = full_path.rstrip("/")
        if path in _API_PATHS or path.startswith("api/"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        file_path = STATIC_UI_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        index_file = STATIC_UI_DIR / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return JSONResponse({"detail": "Not Found"}, status_code=404)

    @app.get("/admin")
    async def admin_ui_root():
        index_file = STATIC_UI_DIR / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return JSONResponse({"detail": "Not Found"}, status_code=404)

_UI_PATH = Path(__file__).resolve().parents[2] / "ui" / "index.html"


@app.get("/")
def ui_root():
    if _UI_PATH.exists():
        return FileResponse(_UI_PATH)
    return {"hint": "Trang quản trị tại /admin. POST /chat để trò chuyện với bot."}
