"""Authenticated translation API contract tests; provider calls are stubbed."""
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api import user_sessions, user_translation
from app.main import app
from app.sessions.in_memory_session_repository import InMemorySessionRepository
from app.sessions.session_service import SessionService
from app.security.user_ownership import user_owner_id


@pytest.fixture
def translation_context(monkeypatch):
    monkeypatch.setenv("WAAXALMA_AUTH_ENABLED", "true")
    monkeypatch.setenv("WAAXALMA_AUTH_ALLOWED_ORIGINS", "http://localhost:3001")
    manager = SessionService(InMemorySessionRepository())
    monkeypatch.setattr(user_sessions, "session_manager", manager)
    monkeypatch.setattr(user_translation, "session_manager", manager)
    identity = {"user_id": str(uuid4())}
    monkeypatch.setattr(user_sessions, "require_session", lambda request: ("test-token", identity.copy()))
    monkeypatch.setattr(user_sessions.auth, "csrf_valid", lambda token, candidate: candidate == "valid-csrf")
    monkeypatch.setattr(user_translation, "observability_fields", lambda: {"request_id": "req-443"})
    calls = []

    async def translate(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(source_text=kwargs["text"], translated_text="Bonjour !")

    monkeypatch.setattr(user_translation.text_translation_service, "translate", translate)
    with TestClient(app) as client:
        yield client, identity, manager, calls


def headers(csrf="valid-csrf", origin="http://localhost:3001"):
    return {"origin": origin, "x-csrf-token": csrf}


def session(manager, identity, agent="translation"):
    return manager.create_session(agent_name=agent, owner_id=user_owner_id(identity["user_id"]))


def send(client, sid, **overrides):
    payload = {"session_id": sid, "text": "Hello!", "source_language": "auto", "target_language": "French"}
    payload.update(overrides)
    return client.post("/api/user/translate/text", json=payload, headers=headers())


def test_translation_success_persists_history_and_normalizes_auto(translation_context):
    client, identity, manager, calls = translation_context
    sid = session(manager, identity).session_id
    response = send(client, sid)
    assert response.status_code == 200, response.text
    assert response.json() == {"request_id": "req-443", "agent": "translation", "original_text": "Hello!", "translated_text": "Bonjour !"}
    assert calls[0]["source_language"] is None
    assert calls[0]["session_id"] == sid
    history = manager.get_session(sid).history
    assert [(m["role"], m["content"]) for m in history] == [("user", "Hello!"), ("assistant", "Bonjour !")]


def test_other_user_and_unknown_sessions_are_indistinguishable(translation_context):
    client, identity, manager, calls = translation_context
    sid = session(manager, identity).session_id
    identity["user_id"] = str(uuid4())
    assert send(client, sid).status_code == 404
    assert send(client, str(uuid4())).status_code == 404
    assert not calls
    assert manager.get_session(sid).history == []


def test_closed_and_wrong_agent_sessions_are_rejected(translation_context):
    client, identity, manager, calls = translation_context
    closed = session(manager, identity)
    manager.close_session(closed.session_id)
    assert send(client, closed.session_id).status_code == 409
    interpreter = session(manager, identity, agent="interpreter")
    assert send(client, interpreter.session_id).status_code == 409
    assert not calls


def test_csrf_and_origin_rejections(translation_context):
    client, identity, manager, calls = translation_context
    sid = session(manager, identity).session_id
    payload = {"session_id": sid, "text": "Hello", "target_language": "French"}
    for bad_headers in (headers(csrf="wrong"), headers(origin="https://evil.example"), {}):
        assert client.post("/api/user/translate/text", json=payload, headers=bad_headers).status_code == 403
    assert not calls


def test_anonymous_is_rejected(translation_context, monkeypatch):
    client, identity, manager, calls = translation_context
    sid = session(manager, identity).session_id
    def reject(request):
        raise HTTPException(401, detail="Not authenticated")
    monkeypatch.setattr(user_sessions, "require_session", reject)
    assert send(client, sid).status_code == 401
    assert not calls


@pytest.mark.parametrize("overrides", [
    {"text": ""}, {"text": "   "}, {"text": "x" * 5001},
    {"target_language": ""}, {"target_language": "  "},
    {"source_language": "x" * 65},
])
def test_invalid_payload_does_not_call_provider(translation_context, overrides):
    client, identity, manager, calls = translation_context
    sid = session(manager, identity).session_id
    assert send(client, sid, **overrides).status_code == 422
    assert not calls


def test_provider_failure_does_not_persist_history(translation_context, monkeypatch):
    client, identity, manager, calls = translation_context
    sid = session(manager, identity).session_id
    async def fail(**kwargs):
        raise RuntimeError("provider unavailable")
    monkeypatch.setattr(user_translation.text_translation_service, "translate", fail)
    with pytest.raises(RuntimeError, match="provider unavailable"):
        send(client, sid)
    assert manager.get_session(sid).history == []


def test_session_closed_during_provider_call_is_not_written(translation_context, monkeypatch):
    client, identity, manager, calls = translation_context
    sid = session(manager, identity).session_id
    async def close_while_translating(**kwargs):
        manager.close_session(sid)
        return SimpleNamespace(source_text="Hello!", translated_text="Bonjour !")
    monkeypatch.setattr(user_translation.text_translation_service, "translate", close_while_translating)
    assert send(client, sid).status_code == 409
    assert manager.get_session(sid).history == []
