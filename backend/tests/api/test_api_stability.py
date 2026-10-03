from pathlib import Path
import subprocess
import sys

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import pytest

from app.api.error_handlers import register_exception_handlers
from app.main import app


def test_reviewed_http_and_websocket_schemas():
    root = Path(__file__).resolve().parents[3]
    subprocess.run([sys.executable, str(root / "ci/api_contract_checks.py")], check=True, timeout=30)


@pytest.mark.parametrize("status", [400, 401, 403, 404, 405, 409, 422, 500, 503, 504])
def test_http_string_errors_use_common_shape_and_preserve_headers(status):
    isolated = FastAPI()
    register_exception_handlers(isolated)
    @isolated.get("/error")
    def fail():
        raise HTTPException(status, detail="test message", headers={"X-Test": "preserved"})
    response = TestClient(isolated).get("/error")
    assert response.status_code == status
    assert response.headers["X-Test"] == "preserved"
    assert response.json() == {"detail": {
        "code": f"HTTP_{status}",
        "message": "test message" if status < 500 else "An internal error occurred.",
    }}


def test_http_structured_errors_preserve_existing_codes_and_details():
    isolated = FastAPI()
    register_exception_handlers(isolated)
    detail = {"code": "CUSTOM_ERROR", "message": "A custom failure.", "details": {"retryable": False}}
    @isolated.get("/error")
    def fail():
        raise HTTPException(409, detail=detail)
    assert TestClient(isolated).get("/error").json() == {"detail": detail}


def test_http_unknown_route_and_invalid_body_are_structured():
    client = TestClient(app, headers={"X-Client-Id": "test-client"})
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "HTTP_404"
    response = client.post("/api/agents/translation/execute", json={})
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "REQUEST_VALIDATION_ERROR"
    assert response.json()["detail"]["details"]["errors"]


@pytest.mark.parametrize("payload", [[], None, {"type": "session.start"}, {"type": "session.start", "target_language": "   "}])
def test_invalid_ws_event_does_not_kill_connection(payload):
    client = TestClient(app, headers={"X-Client-Id": "test-client"})
    with client.websocket_connect("/api/realtime/enhanced/stream") as socket:
        socket.send_json(payload)
        assert socket.receive_json()["code"] == "INVALID_EVENT"
        socket.send_json({"type": "session.start", "target_language": " EN "})
        ready = socket.receive_json()
        assert ready["type"] == "session.ready"
        assert ready["target_language"] == "en"


def test_invalid_json_and_invalid_delta_recover():
    client = TestClient(app, headers={"X-Client-Id": "test-client"})
    with client.websocket_connect("/api/realtime/enhanced/stream") as socket:
        socket.send_text("{bad json")
        assert socket.receive_json()["code"] == "INVALID_EVENT"
        socket.send_json({"type": "session.start", "target_language": "en"})
        socket.receive_json()
        socket.send_json({"type": "transcript.delta", "delta": {"wrong": True}})
        assert socket.receive_json()["code"] == "INVALID_EVENT"
        socket.send_json({"type": "transcript.commit", "text": 12})
        assert socket.receive_json()["code"] == "INVALID_EVENT"
        socket.send_json({"type": "session.start", "target_language": "fr"})
        assert socket.receive_json()["target_language"] == "fr"
