"""Opt-in public authentication API; does not change legacy X-Client-Id routes."""
from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field

from app.identity import auth_service as auth

router = APIRouter(prefix="/api/auth", tags=["authentication"])


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=1024)


def require_enabled() -> None:
    if os.getenv("WAAXALMA_AUTH_ENABLED", "false").lower() != "true":
        raise HTTPException(status_code=404, detail="Not found")


def secure_cookie() -> bool:
    return os.getenv("APP_ENV", "development").lower() == "production"


def require_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    allowed = os.getenv("WAAXALMA_AUTH_ALLOWED_ORIGINS", "http://localhost:3000")
    if not auth.allowed_origin(origin, allowed):
        raise HTTPException(status_code=403, detail="Invalid origin")


def require_session(request: Request) -> tuple[str, dict]:
    token = request.cookies.get(auth.COOKIE_NAME)
    user = auth.resolve_user(token)
    if not token or not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return token, user


def set_cookie(response: Response, token: str) -> None:
    response.set_cookie(auth.COOKIE_NAME, token, max_age=auth.SESSION_DAYS * 86400,
                        httponly=True, secure=secure_cookie(), samesite="lax", path="/api")


@router.post("/register", status_code=201)
def register(payload: Credentials, request: Request):
    require_enabled()
    require_origin(request)
    try:
        return auth.register(str(payload.email), payload.password)
    except ValueError as exc:
        # Never return the password or hash.
        raise HTTPException(status_code=400, detail=str(exc)) from None


@router.post("/login")
def login(payload: Credentials, request: Request, response: Response):
    require_enabled()
    require_origin(request)
    try:
        user, token = auth.authenticate(str(payload.email), payload.password)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid credentials") from None
    set_cookie(response, token)
    return {"user": user, "csrf_token": auth.csrf_token(token)}


@router.get("/me")
def me(request: Request):
    require_enabled()
    token, user = require_session(request)
    return {"user": user, "csrf_token": auth.csrf_token(token)}


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response):
    require_enabled()
    require_origin(request)
    token, _ = require_session(request)
    if not auth.csrf_valid(token, request.headers.get("x-csrf-token")):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")
    auth.revoke(token)
    response.delete_cookie(auth.COOKIE_NAME, path="/api", secure=secure_cookie(), httponly=True, samesite="lax")
