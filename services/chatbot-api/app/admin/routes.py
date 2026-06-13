"""Admin router — JWT-gated endpoints for the web-admin SPA."""
from __future__ import annotations

from typing import List, Optional

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
router = APIRouter(prefix="/admin", tags=["Admin"])


# ── Response models ────────────────────────────────────────────────────────────

class TokenOut(BaseModel):
    token: str
    user_type: str
    role: str
    tenant_id: Optional[str]
    tenant_name: Optional[str] = None
    display_name: str
    permissions: List[str] = []


class TenantOut(BaseModel):
    tenant_id: str
    name: str
    industry: str


class AdminUserOut(BaseModel):
    id: str
    email: str
    role: str
    created_at: float
    created_by: str


class TenantUserOut(BaseModel):
    id: str
    email: str
    tenant_id: str
    role: str
    created_at: float
    created_by: str


class RoleOut(BaseModel):
    id: str
    name: str
    description: str
    color: str
    permissions: List[str]
    is_system: bool
    created_at: float


class SystemPromptOut(BaseModel):
    id: str
    tenant_id: str
    name: str
    content: str
    is_active: bool
    created_at: float
    updated_at: float


# ── Request models ─────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class AdminUserCreate(BaseModel):
    email: str
    password: str
    role: str = "support"


class TenantUserCreate(BaseModel):
    email: str
    password: str
    role: str = "viewer"


class TenantUserPatch(BaseModel):
    role: str


class TenantCreate(BaseModel):
    tenant_id: str
    name: str
    industry: str = "general"


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None


class RoleCreate(BaseModel):
    name: str
    description: str = ""
    color: str = "blue"
    permissions: List[str] = []


class RolePatch(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    permissions: Optional[List[str]] = None


class PromptCreate(BaseModel):
    name: str
    content: str


class PromptUpdate(BaseModel):
    name: str
    content: str


class PromptConfigUpdate(BaseModel):
    tenant_id: str
    system_prompt: str


# ── Auth ───────────────────────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=TokenOut,
    tags=["Auth"],
    summary="Đăng nhập",
    description="Đăng nhập bằng tài khoản admin hoặc nhân viên tenant. Trả về JWT token.",
)
def login(req: LoginRequest):
    if auth.verify_env_admin(req.username, req.password):
        token = auth.issue_token(
            sub=req.username, user_type="admin", role="super_admin", display_name="Super Admin",
        )
        return TokenOut(token=token, user_type="admin", role="super_admin",
                        tenant_id=None, display_name="Super Admin")

    from app.users.store import verify_admin_user, verify_tenant_user
    admin_user = verify_admin_user(req.username, req.password)
    if admin_user:
        token = auth.issue_token(
            sub=admin_user["email"], user_type="admin",
            role=admin_user["role"], display_name=admin_user["email"],
        )
        return TokenOut(token=token, user_type="admin", role=admin_user["role"],
                        tenant_id=None, display_name=admin_user["email"])

    tenant_user = verify_tenant_user(req.username, req.password)
    if tenant_user:
        from app.admin.role_store import get_role_permissions
        perms = get_role_permissions(tenant_user["role"])
        token = auth.issue_token(
            sub=tenant_user["email"], user_type="tenant",
            role=tenant_user["role"], tenant_id=tenant_user["tenant_id"],
            display_name=tenant_user["email"], permissions=perms,
        )
        try:
            tenant_name = get_tenant(tenant_user["tenant_id"]).name
        except Exception:
            tenant_name = tenant_user["tenant_id"]
        return TokenOut(token=token, user_type="tenant", role=tenant_user["role"],
                        tenant_id=tenant_user["tenant_id"], tenant_name=tenant_name,
                        display_name=tenant_user["email"], permissions=perms)

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                        detail={"error": "invalid credentials"})


# ── Tenants ────────────────────────────────────────────────────────────────────

@router.get(
    "/tenants",
    response_model=List[TenantOut],
    tags=["Tenants"],
    summary="Danh sách doanh nghiệp",
)
def list_tenants_admin(_: dict = Depends(auth.require_admin)):
    from app.tenancy import list_tenants as _list
    return _list()


@router.patch(
    "/tenants/{tenant_id}",
    response_model=TenantOut,
    tags=["Tenants"],
    summary="Cập nhật thông tin doanh nghiệp",
)
def update_tenant_admin(tenant_id: str, req: TenantUpdate, _: dict = Depends(auth.require_admin)):
    from app.tenancy import register_tenant
    try:
        tenant = get_tenant(tenant_id)
    except KeyError:
        raise HTTPException(404, {"error": "tenant not found"})
    name = req.name if req.name is not None else tenant.name
    industry = req.industry if req.industry is not None else tenant.industry
    register_tenant(tenant_id, name, industry)
    return TenantOut(tenant_id=tenant_id, name=name, industry=industry)


# ── Admin users (super_admin only) ────────────────────────────────────────────

@router.get(
    "/users",
    response_model=List[AdminUserOut],
    tags=["Admin Users"],
    summary="Danh sách tài khoản admin",
)
def list_admin_users(claims: dict = Depends(auth.require_super_admin)):
    from app.users.store import list_admin_users as _list
    try:
        return _list()
    except Exception as e:
        raise HTTPException(503, {"error": f"DB unavailable: {e}"})


@router.post(
    "/users",
    response_model=AdminUserOut,
    status_code=status.HTTP_201_CREATED,
    tags=["Admin Users"],
    summary="Tạo tài khoản admin",
)
def create_admin_user(req: AdminUserCreate, claims: dict = Depends(auth.require_super_admin)):
    from app.users.store import create_admin_user as _create
    try:
        return _create(req.email, req.password, req.role, created_by=claims.get("sub", ""))
    except ValueError as e:
        raise HTTPException(400, {"error": str(e)})
    except Exception as e:
        raise HTTPException(503, {"error": f"DB unavailable: {e}"})


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Admin Users"],
    summary="Xóa tài khoản admin",
)
def delete_admin_user(user_id: str, _: dict = Depends(auth.require_super_admin)):
    from app.users.store import delete_admin_user as _delete
    try:
        if not _delete(user_id):
            raise HTTPException(404, {"error": "user not found"})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(503, {"error": f"DB unavailable: {e}"})


# ── Tenant users ───────────────────────────────────────────────────────────────

@router.get(
    "/tenants/{tenant_id}/users",
    response_model=List[TenantUserOut],
    tags=["Tenant Users"],
    summary="Danh sách nhân viên của tenant",
)
def list_tenant_users(tenant_id: str, _: dict = Depends(auth.require_admin)):
    from app.users.store import list_tenant_users as _list
    try:
        return _list(tenant_id)
    except Exception as e:
        raise HTTPException(503, {"error": f"DB unavailable: {e}"})


@router.post(
    "/tenants/{tenant_id}/users",
    response_model=TenantUserOut,
    status_code=status.HTTP_201_CREATED,
    tags=["Tenant Users"],
    summary="Thêm nhân viên vào tenant",
)
def create_tenant_user(tenant_id: str, req: TenantUserCreate, claims: dict = Depends(auth.require_admin)):
    try:
        get_tenant(tenant_id)
    except KeyError:
        raise HTTPException(404, {"error": "tenant not found"})
    from app.users.store import create_tenant_user as _create
    try:
        return _create(tenant_id, req.email, req.password, req.role, created_by=claims.get("sub", ""))
    except ValueError as e:
        raise HTTPException(400, {"error": str(e)})
    except Exception as e:
        raise HTTPException(503, {"error": f"DB unavailable: {e}"})


@router.patch(
    "/tenants/{tenant_id}/users/{user_id}",
    response_model=TenantUserOut,
    tags=["Tenant Users"],
    summary="Cập nhật role nhân viên",
)
def update_tenant_user(tenant_id: str, user_id: str, req: TenantUserPatch,
                       _: dict = Depends(auth.require_admin)):
    from app.users.store import update_tenant_user_role as _update
    try:
        updated = _update(user_id, req.role)
        if not updated:
            raise HTTPException(404, {"error": "user not found"})
        return updated
    except ValueError as e:
        raise HTTPException(400, {"error": str(e)})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(503, {"error": f"DB unavailable: {e}"})


@router.delete(
    "/tenants/{tenant_id}/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Tenant Users"],
    summary="Xóa nhân viên khỏi tenant",
)
def delete_tenant_user(tenant_id: str, user_id: str, _: dict = Depends(auth.require_admin)):
    from app.users.store import delete_tenant_user as _delete
    try:
        if not _delete(user_id):
            raise HTTPException(404, {"error": "user not found"})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(503, {"error": f"DB unavailable: {e}"})


# ── Roles ──────────────────────────────────────────────────────────────────────

@router.get(
    "/roles",
    response_model=List[RoleOut],
    tags=["Roles"],
    summary="Danh sách roles",
)
def list_roles(_: dict = Depends(auth.require_admin)):
    from app.admin.role_store import list_roles as _list
    try:
        return _list()
    except Exception as e:
        raise HTTPException(503, {"error": f"DB unavailable: {e}"})


@router.post(
    "/roles",
    response_model=RoleOut,
    status_code=status.HTTP_201_CREATED,
    tags=["Roles"],
    summary="Tạo role mới",
)
def create_role(req: RoleCreate, _: dict = Depends(auth.require_admin)):
    from app.admin.role_store import create_role as _create
    try:
        return _create(req.name, req.description, req.color, req.permissions)
    except ValueError as e:
        raise HTTPException(400, {"error": str(e)})
    except Exception as e:
        raise HTTPException(503, {"error": f"DB unavailable: {e}"})


@router.patch(
    "/roles/{role_id}",
    response_model=RoleOut,
    tags=["Roles"],
    summary="Cập nhật role",
)
def update_role(role_id: str, req: RolePatch, _: dict = Depends(auth.require_admin)):
    from app.admin.role_store import update_role as _update
    try:
        result = _update(role_id, req.name, req.description, req.color, req.permissions)
        if not result:
            raise HTTPException(404, {"error": "role not found"})
        return result
    except ValueError as e:
        raise HTTPException(400, {"error": str(e)})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(503, {"error": f"DB unavailable: {e}"})


@router.delete(
    "/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Roles"],
    summary="Xóa role",
)
def delete_role(role_id: str, _: dict = Depends(auth.require_admin)):
    from app.admin.role_store import delete_role as _delete
    try:
        if not _delete(role_id):
            raise HTTPException(404, {"error": "role not found"})
    except ValueError as e:
        raise HTTPException(400, {"error": str(e)})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(503, {"error": f"DB unavailable: {e}"})


# ── System Prompts ─────────────────────────────────────────────────────────────

@router.get(
    "/tenants/{tenant_id}/prompts",
    response_model=List[SystemPromptOut],
    tags=["System Prompts"],
    summary="Danh sách system prompt của tenant",
)
def list_prompts_admin(tenant_id: str, claims: dict = Depends(auth.require_permission("prompt.read"))):
    auth.enforce_tenant_scope(claims, tenant_id)
    try:
        tenant = get_tenant(tenant_id)
    except KeyError:
        raise HTTPException(404, {"error": "tenant not found"})
    return configs.list_prompts(tenant)


@router.post(
    "/tenants/{tenant_id}/prompts",
    response_model=SystemPromptOut,
    status_code=status.HTTP_201_CREATED,
    tags=["System Prompts"],
    summary="Tạo system prompt mới",
)
def create_prompt_admin(tenant_id: str, req: PromptCreate, claims: dict = Depends(auth.require_permission("prompt.write"))):
    auth.enforce_tenant_scope(claims, tenant_id)
    try:
        tenant = get_tenant(tenant_id)
    except KeyError:
        raise HTTPException(404, {"error": "tenant not found"})
    return configs.create_prompt(tenant, req.name, req.content)


@router.patch(
    "/tenants/{tenant_id}/prompts/{prompt_id}",
    response_model=SystemPromptOut,
    tags=["System Prompts"],
    summary="Cập nhật nội dung prompt",
)
def update_prompt_admin(tenant_id: str, prompt_id: str, req: PromptUpdate,
                        claims: dict = Depends(auth.require_permission("prompt.write"))):
    auth.enforce_tenant_scope(claims, tenant_id)
    try:
        tenant = get_tenant(tenant_id)
    except KeyError:
        raise HTTPException(404, {"error": "tenant not found"})
    result = configs.update_prompt(tenant, prompt_id, req.name, req.content)
    if not result:
        raise HTTPException(404, {"error": "prompt not found"})
    return result


@router.put(
    "/tenants/{tenant_id}/prompts/{prompt_id}/activate",
    response_model=SystemPromptOut,
    tags=["System Prompts"],
    summary="Kích hoạt prompt — đặt làm prompt đang dùng",
)
def activate_prompt_admin(tenant_id: str, prompt_id: str, claims: dict = Depends(auth.require_permission("prompt.write"))):
    auth.enforce_tenant_scope(claims, tenant_id)
    try:
        tenant = get_tenant(tenant_id)
    except KeyError:
        raise HTTPException(404, {"error": "tenant not found"})
    result = configs.activate_prompt(tenant, prompt_id)
    if not result:
        raise HTTPException(404, {"error": "prompt not found"})
    return result


@router.delete(
    "/tenants/{tenant_id}/prompts/{prompt_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["System Prompts"],
    summary="Xóa prompt",
)
def delete_prompt_admin(tenant_id: str, prompt_id: str, claims: dict = Depends(auth.require_permission("prompt.write"))):
    auth.enforce_tenant_scope(claims, tenant_id)
    try:
        tenant = get_tenant(tenant_id)
    except KeyError:
        raise HTTPException(404, {"error": "tenant not found"})
    if not configs.delete_prompt(tenant, prompt_id):
        raise HTTPException(404, {"error": "prompt not found"})


# ── Documents ──────────────────────────────────────────────────────────────────

@router.post(
    "/documents",
    status_code=status.HTTP_201_CREATED,
    tags=["Documents"],
    summary="Upload tài liệu vào knowledge base",
)
async def upload_document(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    tenant_id: str = Form(...),
    claims: dict = Depends(auth.require_permission("documents.write")),
):
    auth.enforce_tenant_scope(claims, tenant_id)
    try:
        tenant = get_tenant(tenant_id)
    except KeyError:
        raise HTTPException(404, {"error": "tenant not found"})

    allowed = {".pdf", ".docx", ".txt", ".md"}
    suffix = "." + (file.filename or "").rsplit(".", 1)[-1].lower()
    if suffix not in allowed:
        raise HTTPException(400, {"error": f"unsupported file type {suffix}; allowed: {sorted(allowed)}"})

    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(400, {"error": "file > 20MB"})

    rec = documents.save_upload(tenant, file.filename or "upload", content)
    background.add_task(documents.run_ingest, tenant, rec["id"])
    return rec


@router.get(
    "/documents",
    tags=["Documents"],
    summary="Danh sách tài liệu của tenant",
)
def list_documents(tenant_id: str = Query(...), claims: dict = Depends(auth.require_permission("documents.read"))):
    auth.enforce_tenant_scope(claims, tenant_id)
    try:
        tenant = get_tenant(tenant_id)
    except KeyError:
        raise HTTPException(404, {"error": "tenant not found"})
    return documents.list_documents(tenant)


@router.delete(
    "/documents/{doc_id}",
    tags=["Documents"],
    summary="Xóa tài liệu",
)
def delete_document(doc_id: str, tenant_id: str = Query(...), claims: dict = Depends(auth.require_permission("documents.write"))):
    auth.enforce_tenant_scope(claims, tenant_id)
    try:
        tenant = get_tenant(tenant_id)
    except KeyError:
        raise HTTPException(404, {"error": "tenant not found"})
    if not documents.delete_document(tenant, doc_id):
        raise HTTPException(404, {"error": "document not found"})
    return {"ok": True}


# ── Conversations ──────────────────────────────────────────────────────────────

@router.get(
    "/conversations",
    tags=["Conversations"],
    summary="Danh sách hội thoại (phân trang)",
)
def list_conversations(
    tenant_id: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    claims: dict = Depends(auth.require_permission("conversations.read")),
):
    # Tenant users can only see their own tenant's conversations
    if claims.get("user_type") == "tenant":
        tenant_id = claims.get("tenant_id")
    return aggregations.list_sessions(tenant_id, page, size)


@router.get(
    "/conversations/{session_id}",
    tags=["Conversations"],
    summary="Chi tiết một hội thoại",
)
def get_conversation(session_id: str, tenant_id: str = Query(...),
                     claims: dict = Depends(auth.require_permission("conversations.read"))):
    auth.enforce_tenant_scope(claims, tenant_id)
    try:
        get_tenant(tenant_id)
    except KeyError:
        raise HTTPException(404, {"error": "tenant not found"})
    return {
        "session_id": session_id,
        "tenant_id": tenant_id,
        "messages": aggregations.get_session_messages(tenant_id, session_id),
    }


# ── Legacy prompt config (kept for backward compat) ───────────────────────────

@router.get("/config/prompt", tags=["System Prompts"], summary="[Legacy] Lấy prompt hiện tại")
def get_prompt_legacy(tenant_id: str = Query(...), claims: dict = Depends(auth.require_permission("prompt.read"))):
    auth.enforce_tenant_scope(claims, tenant_id)
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


@router.put("/config/prompt", tags=["System Prompts"], summary="[Legacy] Cập nhật prompt")
def put_prompt_legacy(req: PromptConfigUpdate, claims: dict = Depends(auth.require_permission("prompt.write"))):
    auth.enforce_tenant_scope(claims, req.tenant_id)
    try:
        tenant = get_tenant(req.tenant_id)
    except KeyError:
        raise HTTPException(404, {"error": "tenant not found"})
    configs.set_prompt(tenant, req.system_prompt)
    return {"ok": True, "tenant_id": tenant.tenant_id}


# ── Stats ──────────────────────────────────────────────────────────────────────

@router.get(
    "/stats",
    tags=["Stats"],
    summary="Thống kê tổng quan dashboard",
)
def get_stats(claims: dict = Depends(auth.require_permission("stats.read"))):
    # Tenant users only see stats for their own tenant
    tenant_id = claims.get("tenant_id") if claims.get("user_type") == "tenant" else None
    return aggregations.stats(tenant_id)
