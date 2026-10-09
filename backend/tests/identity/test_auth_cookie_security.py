"""Focused cookie and origin checks; no PostgreSQL required."""
from fastapi import Response
from app.api.auth import secure_cookie, set_cookie, require_origin
from app.identity.auth_service import allowed_origin
from fastapi import HTTPException
from starlette.requests import Request
import pytest


def test_cookie_attributes_in_development(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    response = Response()
    set_cookie(response, "test-opaque-token")
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert "path=/api" in cookie
    assert "max-age=604800" in cookie
    assert "secure" not in cookie


def test_cookie_secure_in_production(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    assert secure_cookie()
    response = Response()
    set_cookie(response, "test-opaque-token")
    assert "secure" in response.headers["set-cookie"].lower()


def test_origin_exact_match_and_missing_origin(monkeypatch):
    monkeypatch.setenv("WAAXALMA_AUTH_ALLOWED_ORIGINS", "http://localhost:3001")
    assert allowed_origin("http://localhost:3001", "http://localhost:3001")
    for origin in ("http://localhost:30011", "https://evil.example", None):
        scope = {"type": "http", "method": "POST", "path": "/api/auth/logout",
                 "headers": [(b"origin", origin.encode())] if origin else []}
        with pytest.raises(HTTPException) as exc:
            require_origin(Request(scope))
        assert exc.value.status_code == 403
