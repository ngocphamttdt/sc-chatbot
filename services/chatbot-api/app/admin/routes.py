"""Admin router — JWT-gated endpoints for the web-admin SPA."""
from __future__ import annotations

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from pydantic import BaseModel

from app.admin import aggregations, auth, configs, documents, settings as settings_router
from app.tenancy import get_tenant

router = APIRouter(prefix="/api")
router.include_router(settings_router.router)


# --- Login ------------------------------------------------------------

class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(req: LoginRequest):
    if not auth.verify_credentials(req.username, req.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid credentials"},
        )
    return {"token": auth.issue_token(req.username)}


# --- Documents --------------------------------------------------------

@router.post("/documents", status_code=status.HTTP_201_CREATED)
async def upload_document(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    tenant_id: str = Form(...),
    _: str = Depends(auth.require_admin),
):
    try:
        tenant = get_tenant(tenant_id)
    except KeyError:
        raise HTTPException(404, {"error": "tenant not found"})

    allowed = {".pdf", ".docx", ".txt", ".md"}
    suffix = "." + (file.filename or "").rsplit(".", 1)[-1].lower()
    if suffix not in allowed:
        raise HTTPException(
            400, {"error": f"unsupported file type {suffix}; allowed: {sorted(allowed)}"}
        )

    content = await file.read()
    MAX_BYTES = 20 * 1024 * 1024
    if len(content) > MAX_BYTES:
        raise HTTPException(400, {"error": "file > 20MB"})

    rec = documents.save_upload(tenant, file.filename or "upload", content)
    background.add_task(documents.run_ingest, tenant, rec["id"])
    return rec


@router.get("/documents")
def list_documents(
    tenant_id: str = Query(...),
    _: str = Depends(auth.require_admin),
):
    try:
        tenant = get_tenant(tenant_id)
    except KeyError:
        raise HTTPException(404, {"error": "tenant not found"})
    return documents.list_documents(tenant)


@router.delete("/documents/{doc_id}")
def delete_document(
    doc_id: str,
    tenant_id: str = Query(...),
    _: str = Depends(auth.require_admin),
):
    try:
        tenant = get_tenant(tenant_id)
    except KeyError:
        raise HTTPException(404, {"error": "tenant not found"})
    if not documents.delete_document(tenant, doc_id):
        raise HTTPException(404, {"error": "document not found"})
    return {"ok": True}


# --- Config / prompt --------------------------------------------------

class PromptUpdate(BaseModel):
    tenant_id: str
    system_prompt: str


@router.get("/config/prompt")
def get_prompt(
    tenant_id: str = Query(...),
    _: str = Depends(auth.require_admin),
):
    try:
        tenant = get_tenant(tenant_id)
    except KeyError:
        raise HTTPException(404, {"error": "tenant not found"})
    return {
        "tenant_id": tenant.tenant_id,
        "tenant_name": tenant.name,
        "industry": tenant.industry,
        "system_prompt": configs.get_prompt(tenant) or "",
        "updated_at": configs.updated_at(tenant),
    }


@router.put("/config/prompt")
def put_prompt(
    req: PromptUpdate,
    _: str = Depends(auth.require_admin),
):
    try:
        tenant = get_tenant(req.tenant_id)
    except KeyError:
        raise HTTPException(404, {"error": "tenant not found"})
    configs.set_prompt(tenant, req.system_prompt)
    return {"ok": True, "tenant_id": tenant.tenant_id}


# --- Conversations ----------------------------------------------------

@router.get("/conversations")
def list_conversations(
    tenant_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    _: str = Depends(auth.require_admin),
):
    return aggregations.list_sessions(tenant_id, page, size)


@router.get("/conversations/{session_id}")
def get_conversation(
    session_id: str,
    tenant_id: str = Query(...),
    _: str = Depends(auth.require_admin),
):
    try:
        get_tenant(tenant_id)
    except KeyError:
        raise HTTPException(404, {"error": "tenant not found"})
    return {
        "session_id": session_id,
        "tenant_id": tenant_id,
        "messages": aggregations.get_session_messages(tenant_id, session_id),
    }


# --- Stats ------------------------------------------------------------

@router.get("/stats")
def get_stats(_: str = Depends(auth.require_admin)):
    return aggregations.stats()


# --- Tenants (read-only convenience) ----------------------------------

@router.get("/tenants")
def list_tenants_admin(_: str = Depends(auth.require_admin)):
    from app.tenancy import list_tenants as _list
    return _list()
