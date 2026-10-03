"""Disposable Compose CI restart checks; never run against production data."""
import json
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = "http://127.0.0.1:8000"
OWNER = "ci-restart-owner"


def api(path, body=None, *, method=None, client_id=OWNER):
    headers = {"X-Client-Id": client_id, "Content-Type": "application/json"}
    request = Request(BASE + path, data=json.dumps(body).encode() if body is not None else None,
                      headers=headers, method=method)
    with urlopen(request, timeout=5) as response:
        return json.load(response)


def require_error(path, code, *, body=None, method=None, client_id=OWNER):
    try:
        api(path, body, method=method, client_id=client_id)
    except HTTPError as exc:
        result = json.load(exc)
        assert exc.code == code, result
        return result["detail"]["code"]
    raise AssertionError("Expected HTTP error")


def main():
    active = api("/api/sessions", {"metadata": {"restart_smoke": True, "nested": {"version": "v0.5-compatible"}}})["session_id"]
    closed = api("/api/sessions", {"metadata": {"closed_restart_smoke": True}})["session_id"]
    api("/api/sessions/" + active, {"target_language": "French"}, method="PATCH")
    api("/api/sessions/" + closed + "/close", {})
    # Synthetic history only, no paid provider invocation.
    code = """
import sys
from datetime import datetime, timezone
from app.core.settings import get_settings
from app.sessions.sqlite_session_repository import SQLiteSessionRepository
repo=SQLiteSessionRepository(get_settings().session_db_path)
now=datetime.now(timezone.utc).isoformat()
repo.append_message(sys.argv[1], {"role":"user","content":"restart-history","timestamp":now}, updated_at=now)
"""
    subprocess.run(["docker", "compose", "exec", "-T", "backend", "python", "-c", code, active], check=True, timeout=15)
    subprocess.run(["docker", "compose", "exec", "-T", "backend", "waaxalma-session-database",
                    "--database", "/var/lib/waaxalma/waaxalma_sessions.sqlite3",
                    "--backup", "/var/lib/waaxalma/ci_restart_backup.sqlite3"], check=True, timeout=20)
    before = {session: api("/api/sessions/" + session) for session in (active, closed)}
    container = subprocess.check_output(["docker", "compose", "ps", "-q", "backend"], text=True).strip()
    assert container
    subprocess.run(["docker", "compose", "stop", "--timeout", "25", "backend"], check=True, timeout=35)
    exit_code = subprocess.check_output(["docker", "inspect", "--format", "{{.State.ExitCode}}", container], text=True).strip()
    assert exit_code in {"0", "143"}, "Unexpected backend exit code: " + exit_code
    logs = subprocess.check_output(["docker", "logs", container], stderr=subprocess.STDOUT, text=True)
    assert "Application shutdown complete." in logs, "Lifespan did not finish before stop"
    subprocess.run(["docker", "compose", "start", "backend"], check=True, timeout=30)
    for _ in range(100):
        try:
            if api("/health/ready")["status"] == "ready":
                break
        except (URLError, TimeoutError, ConnectionError):
            pass
        time.sleep(.5)
    else:
        raise AssertionError("Backend readiness did not recover")
    for session, expected in before.items():
        assert api("/api/sessions/" + session) == expected, "Persisted session changed across restart"
        assert require_error("/api/sessions/" + session, 403, client_id="ci-foreign-owner") == "SESSION_ACCESS_DENIED"
    assert before[active]["history"][0]["content"] == "restart-history"
    assert before[closed]["closed_at"] is not None
    assert require_error("/api/sessions/" + closed, 409, body={"target_language": "English"}, method="PATCH") == "SESSION_CLOSED"
    assert require_error("/api/sessions/missing-restart-session", 404) == "SESSION_NOT_FOUND"
    subprocess.run(["docker", "compose", "exec", "-T", "backend", "waaxalma-session-database",
                    "--database", "/var/lib/waaxalma/ci_restart_backup.sqlite3"], check=True, timeout=15)
    api("/api/sessions/" + active + "/close", {})
    print("Container clean exit, restart, full session/history/owner continuity, isolation and backup integrity: OK")


if __name__ == "__main__":
    main()
