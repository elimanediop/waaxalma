"""Real PostgreSQL auth + user ownership acceptance tests.

Opt in with WAAXALMA_AUTH_TEST_POSTGRES_URL. No schema creation or TRUNCATE.
Only rows created by this test are removed, even when assertions fail.
"""
from __future__ import annotations

import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

psycopg = pytest.importorskip("psycopg")
from psycopg.conninfo import conninfo_to_dict

from app.main import app
from app.api import user_sessions
from app.sessions.postgresql_session_repository import PostgreSQLSessionRepository
from app.sessions.session_service import SessionService
from app.security.user_ownership import user_owner_id

ORIGIN = "http://localhost:3000"
PASSWORD = "integration-test-password-2026"


@pytest.fixture
def auth_database(monkeypatch):
    url = os.getenv("WAAXALMA_AUTH_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Set WAAXALMA_AUTH_TEST_POSTGRES_URL for real PostgreSQL auth tests")
    url = url.replace("postgresql+psycopg://", "postgresql://", 1)
    params = conninfo_to_dict(url)
    if params.get("dbname") != "waaxalma_test" or params.get("host") not in (
        "localhost", "127.0.0.1", "::1", "postgres"
    ):
        pytest.fail("Refusing auth integration tests outside dedicated local/CI waaxalma_test")

    # Verify migrations are applied. Never create or migrate a database implicitly.
    with psycopg.connect(url, connect_timeout=5) as db, db.cursor() as cur:
        cur.execute("SELECT version_num FROM alembic_version")
        if cur.fetchone()[0] != "0002_identity_foundation":
            pytest.fail("Apply Alembic migration 0002_identity_foundation first")
        cur.execute("SELECT 1 FROM users LIMIT 0")
        cur.execute("SELECT 1 FROM auth_sessions LIMIT 0")
        cur.execute("SELECT 1 FROM translation_sessions LIMIT 0")

    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("WAAXALMA_AUTH_ENABLED", "true")
    monkeypatch.setenv("WAAXALMA_AUTH_ALLOWED_ORIGINS", ORIGIN)
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setattr(user_sessions, "session_manager", SessionService(PostgreSQLSessionRepository(url)))

    created_emails = []
    created_sessions = []
    yield url, created_emails, created_sessions
    with psycopg.connect(url, connect_timeout=5) as db, db.cursor() as cur:
        if created_sessions:
            cur.execute("DELETE FROM translation_sessions WHERE session_id = ANY(%s)", (created_sessions,))
        if created_emails:
            # FK ON DELETE CASCADE clears auth_sessions; no global cleanup.
            cur.execute("DELETE FROM users WHERE email_normalized = ANY(%s)", (created_emails,))


def register_and_login(client, created_emails):
    email = f"auth-integration-{uuid4().hex}@example.com"
    created_emails.append(email)
    credentials = {"email": email, "password": PASSWORD}
    registered = client.post("/api/auth/register", json=credentials, headers={"Origin": ORIGIN})
    assert registered.status_code == 201, registered.text
    login = client.post("/api/auth/login", json=credentials, headers={"Origin": ORIGIN})
    assert login.status_code == 200, login.text
    assert "waaxalma_session" in client.cookies
    assert "httponly" in login.headers["set-cookie"].lower()
    assert "samesite=lax" in login.headers["set-cookie"].lower()
    return email, credentials, registered.json()["user_id"], login.json()["csrf_token"]


def test_postgres_registration_login_logout_and_csrf(auth_database):
    url, emails, _ = auth_database
    with TestClient(app) as client:
        email, credentials, user_id, csrf = register_and_login(client, emails)
        assert client.get("/api/auth/me").json()["user"]["user_id"] == user_id
        assert client.post("/api/auth/register", json=credentials, headers={"Origin": ORIGIN}).status_code == 400
        assert client.post("/api/auth/login", json={**credentials, "password": "wrong-password"}, headers={"Origin": ORIGIN}).status_code == 401
        assert client.post("/api/auth/logout", headers={"Origin": ORIGIN}).status_code == 403
        assert client.post("/api/auth/logout", headers={"Origin": "https://evil.example", "X-CSRF-Token": csrf}).status_code == 403
        assert client.get("/api/auth/me").status_code == 200
        assert client.post("/api/auth/logout", headers={"Origin": ORIGIN, "X-CSRF-Token": csrf}).status_code == 204
        assert client.get("/api/auth/me").status_code == 401
        # Authentication session is persisted and actually revoked in PostgreSQL.
        with psycopg.connect(url) as db, db.cursor() as cur:
            cur.execute("SELECT count(*) FROM auth_sessions WHERE user_id=%s AND revoked_at IS NOT NULL", (user_id,))
            assert cur.fetchone()[0] == 1


def test_postgres_expiry_and_disabled_user(auth_database):
    url, emails, _ = auth_database
    with TestClient(app) as client:
        _, _, user_id, _ = register_and_login(client, emails)
        with psycopg.connect(url) as db, db.cursor() as cur:
            cur.execute("UPDATE auth_sessions SET created_at = now() - interval '2 days', expires_at = now() - interval '1 day' WHERE user_id=%s", (user_id,))
        assert client.get("/api/auth/me").status_code == 401
        # A new login is possible until the user is deactivated.
        email = emails[-1]
        assert client.post("/api/auth/login", json={"email": email, "password": PASSWORD}, headers={"Origin": ORIGIN}).status_code == 200
        with psycopg.connect(url) as db, db.cursor() as cur:
            cur.execute("UPDATE users SET is_active=FALSE WHERE user_id=%s", (user_id,))
        assert client.get("/api/auth/me").status_code == 401


def test_postgres_cross_user_session_isolation(auth_database):
    _, emails, sessions = auth_database
    with TestClient(app) as alice, TestClient(app) as bob:
        _, _, alice_id, alice_csrf = register_and_login(alice, emails)
        _, _, bob_id, bob_csrf = register_and_login(bob, emails)
        manager = user_sessions.session_manager
        a = manager.create_session("interpreter", owner_id=user_owner_id(alice_id))
        b = manager.create_session("interpreter", owner_id=user_owner_id(bob_id))
        sessions.extend([a.session_id, b.session_id])
        assert alice.get(f"/api/user/sessions/{a.session_id}").status_code == 200
        assert bob.get(f"/api/user/sessions/{b.session_id}").status_code == 200
        for client, other, csrf in ((alice, b, alice_csrf), (bob, a, bob_csrf)):
            url = f"/api/user/sessions/{other.session_id}"
            assert client.get(url).status_code == 404
            headers = {"Origin": ORIGIN, "X-CSRF-Token": csrf}
            assert client.patch(url, json={"target_language": "French"}, headers=headers).status_code == 404
            assert client.post(url + "/close", headers=headers).status_code == 404
        assert manager.get_session(a.session_id).is_active
        assert manager.get_session(b.session_id).is_active
        assert alice.patch(f"/api/user/sessions/{a.session_id}", json={"target_language": "French"}, headers={"Origin": ORIGIN}).status_code == 403
        assert alice.patch(f"/api/user/sessions/{a.session_id}", json={"target_language": "French"}, headers={"Origin": ORIGIN, "X-CSRF-Token": alice_csrf}).status_code == 200
        assert alice.post(f"/api/user/sessions/{a.session_id}/close", headers={"Origin": ORIGIN, "X-CSRF-Token": alice_csrf}).status_code == 200
        assert not manager.get_session(a.session_id).is_active
        assert manager.get_session(b.session_id).is_active
