# v1.0.0 Slice 3 — API & Streaming Stability

This document defines the v1.0.0 wire contract. It preserves success payloads
and existing named business error codes. Publication follows final acceptance.

## Reviewed schemas

`docs/contracts/openapi.json` records the HTTP paths, input/output schemas and
documented error responses. `enhanced-websocket.json` records the discriminated
incoming/outgoing event schemas. JSON snapshots are UTF-8, deterministic and
checked in backend CI on Linux/Windows. Only the release version in OpenAPI is
normalized; schema changes require explicit review and regeneration:

```powershell
python ci/api_contract_checks.py
# Only after reviewing an intentional contract change:
python ci/api_contract_checks.py --write
```

The script uses temporary test data and performs no provider requests. It does
not initialize the deployment database. Consumers should ignore additional
optional fields and metadata keys. A snapshot change is a review gate, not an
automatic declaration that a change is incompatible.

Standard interpretation/text/session success models remain unchanged. Agent
listing now explicitly documents `{"agents": [...]}`. Generic execution still
returns a dynamic output object, not an `AgentResult` envelope; its keys depend
on the registered agent and operation. Health responses now have explicit
success and not-ready schemas without changing their JSON payloads.

## HTTP identity and errors

Business execution and conversation-session endpoints require a valid
`X-Client-Id`. Missing/invalid headers return 401. The dependency accepts a
missing header syntactically to produce this 401 instead of FastAPI's default
422; consumers must still supply the header. This is client isolation using a
self-declared ID, not user authentication. Public health, metrics, documentation
and agent discovery retain their existing access behavior.

Persisted session ownership and lifecycle checks remain unchanged. Strict
conversation lookup returns 404 for missing sessions. Generic/realtime IDs can
remain ephemeral correlation IDs; when they match a persisted session, its
ownership and active-state policy applies.

Application HTTP errors use:

```json
{"detail": {"code": "ERROR_CODE", "message": "Human-readable message", "details": {}}}
```

`details` is optional. Existing structured errors preserve their codes and
details. Previously string-valued HTTP errors, including unknown routes and
method errors, now use `HTTP_<status>` with a message. This intentionally
normalizes an inconsistent pre-stable shape; consumers that parsed a string
`detail` should read `detail.message` instead. HTTP exception headers remain
intact. String-valued 5xx errors do not reveal their original exception text.

| Case | Status / code |
| --- | --- |
| Missing/invalid client ID | 401 / `CLIENT_ID_REQUIRED` or `INVALID_CLIENT_ID` |
| Foreign persisted session | 403 / `SESSION_ACCESS_DENIED` |
| Missing persisted session | 404 / `SESSION_NOT_FOUND` |
| Closed session used for an active operation | 409 / `SESSION_CLOSED` |
| Invalid HTTP request body | 422 / `REQUEST_VALIDATION_ERROR` |
| Unknown HTTP route | 404 / `HTTP_404` |
| Unexpected application exception | 500 / `PIPELINE_ERROR` |

Provider/agent errors retain their existing named codes and status mappings.
Clients should branch on code/status, not English message text. Readiness 503
is an intentional exception: it returns `{"status":"not_ready"}`. Metrics
and static media retain their content types; they are not JSON error envelopes.

## Enhanced WebSocket lifecycle

Path: `/api/realtime/enhanced/stream`. Supply `X-Client-Id` or, for browsers,
`?client_id=...`. Conflicting IDs or invalid identity reject the handshake with
policy code 1008 (an HTTP denial before upgrade may be displayed by the client).

| Input | Behavior |
| --- | --- |
| `session.start` | Validates target/settings and persisted ownership when applicable, creates or replaces the runtime, sends `session.ready` including selected `voice_id` |
| `transcript.delta` | Appends source text to the pending transcript |
| `transcript.commit` | Processes the accumulated transcript; optional string `text` supplies final text for that committed segment |
| `session.reset` | Clears pending transcript, context history and segment numbering |

Commit with no accumulated transcript remains a no-op. A final-text-only
commit does not create a source segment. Start target language is trimmed and
lowercased; blank values fail validation. Additional input fields retain the
existing Pydantic ignore behavior.

Malformed JSON, non-object frames, invalid known event fields and binary frames
return `INVALID_EVENT` while keeping the connection usable. Events before start
return `SESSION_NOT_STARTED`; an unsupported event after start returns
`UNKNOWN_EVENT`. These recoverable errors do not call providers. Persisted
ownership/lifecycle failures send their existing named error and close 1008.

Events process serially in receive order. Translation and audio can interleave;
ordering is preserved within each provider stream. There is no new global
commit-completed acknowledgement; existing final flags and metadata remain.
Audio chunks are base64 strings with their content type and optional sample
rate. A final chunk may have an empty payload. There is no replay/exactly-once
guarantee after reconnect.

A provider-processing failure sends `ENHANCED_PROCESSING_ERROR` with a fixed
message, resets the runtime buffers and keeps the connection open. This avoids
returning raw exception strings. Partial output already sent is not rolled
back; clients should discard or visibly mark the failed segment before sending
a new one. Resetting also restarts segment numbering.

The receive task remains active while providers work. A disconnect cancels the
processing task, which cancels/awaits translation and TTS tasks. Streams are
closed with `aclose()` when supported, including early consumer exit and send
failure. Parent-task cancellation propagates unless transport disconnect has
already been handled. ASGI teardown shields child cleanup from a cancelled
connection scope. Providers must cooperate with cancellation; this slice does
not impose a universal provider deadline.

Pending inbound events are limited to 64; exceeding that backlog returns
`EVENT_QUEUE_FULL` and closes 1008. Internal output/speech queues use backpressure
at 64/32 items rather than collecting unlimited chunks. These are item counts,
not a byte or transcript-size limit. Cancelled workers skip completion sentinels
so cleanup cannot wait on a full queue. Reset/start arriving during a commit
run after that commit; disconnect interrupts it immediately.

Direct browser/provider WebRTC sessions remain provider-managed. This slice
does not change their external protocol or promise server-side cancellation
of a browser's direct provider connection.

## Verification

Regression tests cover existing success payloads and security boundaries.
New tests cover schema snapshots, HTTP error/header compatibility, malformed
event recovery, blocked translation/TTS disconnect and cancellation, send
failure, sanitized provider failure, queue overload and early iterator close
under backpressure. No real audio/provider/network acceptance is claimed by
these offline tests; container/browser acceptance remains part of release CI.
