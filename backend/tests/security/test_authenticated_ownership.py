from uuid import uuid4
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.security.user_ownership import user_owner_id
from app.security.client_identity import ClientIdentity, ClientIdentityError
from app.sessions.in_memory_session_repository import InMemorySessionRepository
from app.sessions.session_service import SessionService


def test_user_owner_namespace_cannot_be_used_as_legacy_client_id():
    owner = user_owner_id(str(uuid4()))
    assert owner.startswith("user:")
    try:
        ClientIdentity(owner)
        assert False, "legacy header accepted a user owner"
    except ClientIdentityError:
        pass


def test_authenticated_http_isolation(monkeypatch):
    from app.api import user_sessions
    monkeypatch.setenv("WAAXALMA_AUTH_ENABLED", "true")
    monkeypatch.setenv("WAAXALMA_AUTH_ALLOWED_ORIGINS", "http://localhost:3000")
    manager = SessionService(InMemorySessionRepository())
    monkeypatch.setattr(user_sessions, "session_manager", manager)
    first, second = str(uuid4()), str(uuid4())
    owner_a, owner_b = user_owner_id(first), user_owner_id(second)
    session_a = manager.create_session("interpreter", owner_id=owner_a)
    session_b = manager.create_session("interpreter", owner_id=owner_b)
    active = {"user_id": first}
    monkeypatch.setattr(user_sessions, "require_session", lambda request: ("token", dict(active)))
    monkeypatch.setattr(user_sessions.auth, "csrf_valid", lambda token, candidate: candidate == "csrf")
    with TestClient(app) as client:
        assert client.get("/api/user/sessions/" + session_a.session_id).status_code == 200
        for method, path in (("get", session_b.session_id), ("patch", session_b.session_id), ("post", session_b.session_id + "/close")):
            kwargs = {"json": {"target_language": "French"}} if method == "patch" else {}
            response = getattr(client, method)("/api/user/sessions/" + path, headers={"origin": "http://localhost:3000", "x-csrf-token": "csrf"}, **kwargs)
            assert response.status_code == 404
        active["user_id"] = second
        assert client.get("/api/user/sessions/" + session_b.session_id).status_code == 200
        assert client.get("/api/user/sessions/" + session_a.session_id).status_code == 404
    assert manager.get_session(session_b.session_id).is_active
