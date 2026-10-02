"""HTTP smoke checks. Never invokes a paid provider."""
import argparse
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

parser = argparse.ArgumentParser()
parser.add_argument("--backend", default="http://127.0.0.1:8000")
parser.add_argument("--ui")
args = parser.parse_args()

def request(path, expected=200, method="GET", body=None, client=None):
    headers = {"Content-Type": "application/json", "X-Request-Id": "ci-smoke"}
    if client:
        headers["X-Client-Id"] = client
    data = None if body is None else json.dumps(body).encode()
    req = Request(args.backend + path, data=data, headers=headers, method=method)
    try:
        response = urlopen(req, timeout=10)
    except HTTPError as error:
        response = error
    with response:
        assert response.headers["X-Request-Id"] == "ci-smoke"
        assert response.code == expected, (path, response.code, expected)
        return json.loads(response.read())

assert request("/health/live")["status"] == "ok"
assert request("/health/ready")["status"] == "ready"
request("/api/sessions", expected=401, method="POST", body={})
session = request("/api/sessions", method="POST", body={}, client="ci-owner")["session_id"]
path = "/api/sessions/" + session
assert request(path, client="ci-owner")["owner_id"] == "ci-owner"
request(path, expected=403, client="ci-other")
request("/api/sessions/ci-missing-session", expected=404, client="ci-owner")
request(path + "/close", method="POST", client="ci-owner")
if args.ui:
    with urlopen(args.ui + "/_stcore/health", timeout=10) as response:
        assert response.status == 200
print("Health, session lifecycle and ownership smoke checks: OK")
if args.ui:
    print("UI health smoke check: OK")

with urlopen(args.backend + "/metrics", timeout=10) as response:
    metrics = response.read().decode()
    for name in ("waaxalma_sessions_active", "waaxalma_http_requests_total", "waaxalma_provider_duration_seconds", "waaxalma_sessions_scrape_error"):
        assert name in metrics, name
print("Production metrics exposure: OK")
