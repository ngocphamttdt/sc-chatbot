"""JWT auth for /admin/* endpoints.

Single admin from env (ADMIN_USER + ADMIN_PASSWORD). Password compared via
bcrypt — we hash the env password at module import so plaintext is never
compared directly.
"""
from __future__ import annotations

import time

import bcrypt
import jwt
from fastapi import Header, HTTPException, status

from app.config import settings

_ALGO = "HS256"

# Hash the env password once at startup so login uses bcrypt.checkpw (constant
# time) rather than == on the plaintext.
_ADMIN_HASH = bcrypt.hashpw(
    settings.admin_password.encode("utf-8"), bcrypt.gensalt()
)


def verify_credentials(username: str, password: str) -> bool:
    if username != settings.admin_user:
        return False
    return bcrypt.checkpw(password.encode("utf-8"), _ADMIN_HASH)


def issue_token(username: str) -> str:
    now = int(time.time())
    payload = {
        "sub": username,
        "iat": now,
        "exp": now + settings.jwt_expires_min * 60,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGO)


def _decode(token: str) -> dict:
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


def require_admin(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "missing bearer token"},
        )
    token = authorization.split(" ", 1)[1].strip()
    claims = _decode(token)
    sub = claims.get("sub")
    if sub != settings.admin_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid subject"},
        )
    return sub
