"""HTTP contract regression tests for the authenticated Sessions Workspace."""
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api import user_sessions
from app.main import app
from app.sessions.in_memory_session_repository import InMemorySessionRepository
from app.sessions.session_service import SessionService


@pytest.fixture
def context(monkeypatch):
    monkeypatch.setenv("WAAXALMA_AUTH_ENABLED", "true")
    monkeypatch.setenv("WAAXALMA_AUTH_ALLOWED_ORIGINS", "http://localhost:3001")
    manager = SessionService(InMemorySessionRepository())
    monkeypatch.setattr(user_sessions, "session_manager", manager)
    identity = {"user_id": str(uuid4())}
    monkeypatch.setattr(user_sessions, "require_session", lambda request: ("test-token", identity.copy()))
    monkeypatch.setattr(user_sessions.auth, "csrf_valid", lambda token, candidate: candidate == "valid-csrf")

    class Agent:
        name = "interpreter"

    monkeypatch.setattr(user_sessions.agent_manager, "get_agent", lambda name: Agent() if name == "interpreter" else None)
    with TestClient(app) as client:
        yield client, identity, manager


def headers(csrf="valid-csrf", origin="http://localhost:3001"):
    return {"origin": origin, "x-csrf-token": csrf}


def create(client):
    response = client.post(
        "/api/user/sessions",
        json={"agent_type": "interpreter", "source_language": "French",
              "target_language": "English", "execution_mode": "standard"},
        headers=headers(),
    )
    assert response.status_code == 201, response.text
    return response.json()["session_id"]


def test_full_lifecycle_and_closed_session_is_read_only(context):
    client, _, _ = context
    sid = create(client)
    listing = client.get("/api/user/sessions")
    assert listing.status_code == 200
    assert [s["session_id"] for s in listing.json()["items"]] == [sid]

    detail = client.get(f"/api/user/sessions/{sid}")
    assert detail.status_code == 200

    updated = client.patch(f"/api/user/sessions/{sid}", headers=headers(),
                           json={"target_language": "Spanish"})
    assert updated.status_code == 200
    assert client.get("/api/user/sessions").json()["items"][0]["target_language"] == "Spanish"

    closed = client.post(f"/api/user/sessions/{sid}/close", headers=headers())
    assert closed.status_code == 200
    assert client.patch(f"/api/user/sessions/{sid}", headers=headers(),
                        json={"target_language": "German"}).status_code == 409
    assert client.get(f"/api/user/sessions/{sid}").status_code == 200


def test_list_is_scoped_and_pagination_is_validated(context):
    client, identity, _ = context
    sid_a = create(client)
    sid_b = create(client)
    response = client.get("/api/user/sessions?limit=1&offset=0")
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1
    response2 = client.get("/api/user/sessions?limit=1&offset=1")
    assert response2.status_code == 200
    assert {response.json()["items"][0]["session_id"], response2.json()["items"][0]["session_id"]} == {sid_a, sid_b}
    for params in ("limit=0", "limit=101", "offset=-1"):
        assert client.get("/api/user/sessions?" + params).status_code == 422

    identity["user_id"] = str(uuid4())
    assert client.get("/api/user/sessions").json()["items"] == []
    assert client.get(f"/api/user/sessions/{sid_a}").status_code == 404
    assert client.patch(f"/api/user/sessions/{sid_a}", headers=headers(),
                        json={"target_language": "German"}).status_code == 404
    assert client.post(f"/api/user/sessions/{sid_a}/close", headers=headers()).status_code == 404


@pytest.mark.parametrize("method,path,payload", [
    ("post", "/api/user/sessions", {"agent_type": "interpreter"}),
    ("patch", "/api/user/sessions/{sid}", {"target_language": "German"}),
    ("post", "/api/user/sessions/{sid}/close", None),
])
def test_mutations_require_csrf_and_allowed_origin(context, method, path, payload):
    client, _, _ = context
    sid = create(client) if "{sid}" in path else ""
    url = path.format(sid=sid)
    request = getattr(client, method)
    kwargs = {"json": payload} if payload is not None else {}
    assert request(url, headers=headers(csrf="invalid"), **kwargs).status_code == 403
    assert request(url, headers=headers(origin="https://untrusted.example"), **kwargs).status_code == 403


def test_anonymous_and_disabled_auth_are_rejected(context, monkeypatch):
    client, _, _ = context
    from fastapi import HTTPException
    monkeypatch.setattr(user_sessions, "require_session",
                        lambda request: (_ for _ in ()).throw(HTTPException(401, "Not authenticated")))
    assert client.get("/api/user/sessions").status_code == 401
    assert client.post("/api/user/sessions", json={}, headers=headers()).status_code == 401
    monkeypatch.setenv("WAAXALMA_AUTH_ENABLED", "false")
    assert client.get("/api/user/sessions").status_code == 404


def test_request_validation_and_unknown_agent(context):
    client, _, _ = context
    assert client.post("/api/user/sessions", headers=headers(),
                       json={"agent_type": "unknown"}).status_code == 404
    assert client.post("/api/user/sessions", headers=headers(),
                       json={"target_language": "x"}).status_code == 422
