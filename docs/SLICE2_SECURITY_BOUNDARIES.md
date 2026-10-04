# Waaxalma v0.5.0 — Slice 2: Security Boundaries

This archive builds on Slice 1 persistent sessions. No OAuth, OIDC, JWT,
accounts, login/password, or IAM system is introduced or planned by this slice.

## Client contract

Send a stable `X-Client-Id: waaxalma-desktop` on session creation and subsequent
requests. IDs are case-sensitive, 1–128 ASCII characters; the first character
must be alphanumeric and the remainder alphanumeric, underscore, dot, or hyphen.
Whitespace is rejected rather than normalized. Each distinct installation/client
must use a distinct stable ID to isolate its conversations.

HTTP session create/read/update/close, interpretation, text operations, generic
agent execution, and realtime session creation require this header. Public
health, metrics, agent listing and static audio routes retain their existing
behavior. ClientIdentity and SecurityContext are immutable and framework
independent; SessionAccessPolicy owns authorization; security.backend adapts
HTTP identity and errors.

For native WebSocket clients, send the same header on the handshake. Browser
WebSocket clients use `/api/realtime/enhanced/stream?client_id=waaxalma-desktop`
because the browser constructor cannot set headers. Identical validation applies;
conflicting header/query IDs are rejected. Missing or invalid identity closes
with code 1008 before accept. A foreign persisted ID in `session.start` returns
an error and closes with 1008 before processor creation.

## Ownership

API creation assigns owner_id from the resolved identity, never the request body.
GET, PATCH and close authorize before reading/altering session contents.
Interpretation with a session_id requires an existing, owned, active conversation
before audio validation or provider calls, and preserves persistent history.
Text/generic/realtime operations historically also accept transient correlation
IDs: unknown IDs remain transient and do not read/write a persistent conversation;
IDs that match persisted conversations require ownership and active status.
Generic execution checks both its context ID and the payload session_id.
Normal repository updates preserve owner_id; API PATCH exposes no ownership field.
Direct SessionService/repository calls are trusted internal operations, not an
HTTP authentication boundary. Internal creation without owner remains supported
for older tests/callers, but such sessions are denied through the API.

| Condition | HTTP status / code |
|---|---|
| Missing identity | 401 / CLIENT_ID_REQUIRED |
| Invalid identity | 401 / INVALID_CLIENT_ID |
| Foreign or unowned session | 403 / SESSION_ACCESS_DENIED |
| Unknown persistent conversation | 404 / SESSION_NOT_FOUND |
| Owned closed conversation used for processing/update | 409 / SESSION_CLOSED |

Ownership is checked before lifecycle status. Closing an owned session twice is
idempotent. Reading an owned closed session remains allowed.

## Slice 1 SQLite migration

On repository startup, a serialized, idempotent migration adds nullable owner_id
and sets schema user_version to 2. Existing sessions, metadata and messages are
preserved. Old rows have NULL owner_id and are inaccessible through the API;
there is no first-request ownership claim and no default shared owner. Back up
the existing database before rollout. For a known legacy session, explicitly
assign its owner offline using the included command (from backend):

```bash
python -m scripts.assign_session_owner --database data/waaxalma_sessions.sqlite3 --session-id YOUR_SESSION_ID --client-id waaxalma-desktop
```

This command only assigns previously unowned rows, not existing owners. Stop the
backend while administering legacy ownership. Use the configured SESSION_DB_PATH
if different from the default. New API sessions need no administrative step.

## Identification trust boundary

X-Client-Id is client-declared identification, not proof of identity. Anyone able
to send requests can copy another client ID. The same applies to the WebSocket
query value. This slice enforces isolation by declared client ID in a trusted
local/private deployment; it does not claim protection against malicious clients
on an untrusted network. Existing static audio URLs remain publicly readable to
clients that can reach the backend; session ownership does not protect them.
No authentication platform is required or introduced.

## Run and verify

```bash
pip install -r requirements.txt -r requirements-dev.txt
# Configure OPENAI_API_KEY as in Slice 1 (tests use a dummy value, no real calls).
OPENAI_API_KEY=test-key SESSION_STORAGE_BACKEND=memory python -m pytest -q
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The regression suite includes explicit client headers in existing API fixtures.
New security tests cover validation, lifecycle, foreign/legacy access, all
session-bearing HTTP entry points, WebSocket boundaries, SQLite ownership
persistence, and Slice 1 migration. Provider integrations are mocked in tests;
no live translation/audio-device validation is claimed.

## Validation result

270 tests passed (223 baseline + 47 security tests), using Python 3.12.
