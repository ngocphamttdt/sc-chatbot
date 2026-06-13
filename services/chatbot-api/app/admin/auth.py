"""JWT auth for /admin/* endpoints.

Two auth paths:
1. Env super admin (ADMIN_USER + ADMIN_PASSWORD) — always available, backward compat
2. DB-based admin users (admin_users MongoDB collection)

JWT payload:
  sub          : email or env username
  user_type    : "admin" | "tenant"
  role         : "super_admin" | "support" | "manager" | "editor" | "viewer"
  tenant_id    : null for admin users, tenant_id string for tenant users
  display_name : human-readable name shown in UI
"""
from __future__ import annotations

import hashlib
import time
from typing import Optional

import bcrypt
import jwt
from fastapi import Header, HTTPException, status

from app.config import settings

_ALGO = "HS256"


def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


_ADMIN_HASH = bcrypt.hashpw(
    _sha256_hex(settings.admin_password).encode("utf-8"), bcrypt.gensalt()
)


def verify_env_admin(username: str, password: str) -> bool:
    if username != settings.admin_user:
        return False
    return bcrypt.checkpw(password.encode("utf-8"), _ADMIN_HASH)


def issue_token(
    sub: str,
    user_type: str,
    role: str,
    tenant_id: Optional[str] = None,
    display_name: Optional[str] = None,
    permissions: Optional[list] = None,
) -> str:
    now = int(time.time())
    payload = {
        "sub": sub,
        "user_type": user_type,
        "role": role,
        "tenant_id": tenant_id,
        "display_name": display_name or sub,
        "permissions": permissions or [],
        "iat": now,
        "exp": now + settings.jwt_expires_min * 60,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGO)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[_ALGO])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "token expired"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid token"},
        )


def _extract_bearer(authorization: Optional[str]) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "missing bearer token"},
        )
    return authorization.split(" ", 1)[1].strip()


def require_admin(authorization: Optional[str] = Header(default=None)) -> dict:
    """Accept any valid admin token (super_admin or support).

    Backward compat: old tokens without user_type are treated as super_admin.
    """
    token = _extract_bearer(authorization)
    claims = decode_token(token)
    user_type = claims.get("user_type", "admin")
    if user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "admin access required"},
        )
    return claims


def require_super_admin(authorization: Optional[str] = Header(default=None)) -> dict:
    """Only super_admin role. Old env-based tokens (no role field) pass through."""
    claims = require_admin(authorization)
    role = claims.get("role")
    if role is not None and role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "super admin access required"},
        )
    return claims


def require_permission(permission: str):
    """Factory: returns a FastAPI dependency that accepts admin users OR tenant users with the given permission."""
    def _dep(authorization: Optional[str] = Header(default=None)) -> dict:
        token = _extract_bearer(authorization)
        claims = decode_token(token)
        user_type = claims.get("user_type", "admin")
        if user_type == "admin":
            return claims
        if permission not in claims.get("permissions", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": f"permission required: {permission}"},
            )
        return claims
    return _dep


def enforce_tenant_scope(claims: dict, tenant_id: str) -> None:
    """Raise 403 if a tenant user tries to access another tenant's data."""
    if claims.get("user_type") == "tenant" and claims.get("tenant_id") != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "access to other tenant data is not allowed"},
        )
