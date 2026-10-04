# Waaxalma v0.5.0 — Slice 1

## Persistent Sessions

Slice 1 replaces the previous process-local session dictionary with an explicit
repository + service boundary.

```text
API / execution endpoints
        │
        ▼
   SessionManager
   (SessionService)
        │
        ▼
 SessionRepository
        │
        ├── InMemorySessionRepository
        │       tests / deterministic local use
        │
        └── SQLiteSessionRepository
                persistent default
```

`SessionContext` remains the per-execution context passed through agents and
pipelines. `ConversationSession` is the durable application-level session
record. Interpreter and voice endpoints hydrate their execution context from
the durable session when a `session_id` is supplied.

## Persistent model

Each session stores:

```text
session_id
agent_name
execution_mode
source_language
target_language
status
created_at
updated_at
closed_at
metadata
history
```

Session states in this slice:

```text
active
closed
```

A closed session can still be retrieved, but cannot be updated or receive new
conversation messages.

## SQLite schema

SQLite uses two tables:

```text
sessions
session_messages
```

Messages are normalized rather than serializing the full conversation history
into the session row. The repository opens a connection per operation and
enables foreign keys and WAL mode.

## Configuration

Default:

```text
SESSION_STORAGE_BACKEND=sqlite
SESSION_DB_PATH=data/waaxalma_sessions.sqlite3
```

`SESSION_DB_PATH` is resolved relative to the backend root when a relative path
is provided.

For deterministic unit tests or an explicitly ephemeral runtime:

```text
SESSION_STORAGE_BACKEND=memory
```

SQLite is implemented with Python's standard `sqlite3` module, so Slice 1 adds
no external runtime dependency.

Generated SQLite files are ignored by Git.

## API lifecycle

Existing session creation remains backward-compatible:

```http
POST /api/sessions
```

Example request:

```json
{
  "agent_type": "interpreter",
  "source_language": "fr",
  "target_language": "en",
  "execution_mode": "standard",
  "metadata": {
    "client": "streamlit"
  }
}
```

The existing create response shape is preserved:

```json
{
  "session_id": "...",
  "agent_name": "interpreter",
  "target_language": "en"
}
```

New lifecycle operations:

```http
GET   /api/sessions/{session_id}
PATCH /api/sessions/{session_id}
POST  /api/sessions/{session_id}/close
```

`PATCH` merges supplied metadata keys into the current session metadata.

## Execution behavior

When Standard text or voice interpretation receives a persistent `session_id`:

- the session must exist;
- the session must still be active;
- the persisted target language overrides the request target language;
- persisted source language and metadata are copied into `SessionContext`;
- user and assistant messages are persisted through the repository.

Existing request execution without a `session_id` remains ephemeral and
unchanged.

## Tests added

```text
tests/sessions/test_session_repositories.py
tests/sessions/test_session_service.py
```

They cover:

- detached in-memory repository semantics;
- create / retrieve / update / close lifecycle;
- persistent message history;
- process-restart simulation with a fresh SQLite repository instance;
- closed-session protections;
- idempotent close.

Local validation in the artifact environment:

```text
7 new session tests passed
76 selected non-provider regression tests passed
Python compileall passed
SQLite restart smoke passed
```

The complete project test suite cannot be executed in the artifact environment
because the OpenAI Python dependency used by existing provider/bootstrap tests
is not installed there. Run the complete suite in the project `.venv` before
accepting the slice:

```powershell
cd backend
python -m pytest -q
```

Starting from the v0.4.4 baseline of 216 tests, the expected count after adding
these 7 tests is 223 if no other tests have changed.

## Slice 1 Definition of Done

```text
✅ repository abstraction
✅ deterministic in-memory repository
✅ SQLite repository
✅ create persistent session
✅ retrieve by session_id
✅ update session metadata/language/mode
✅ close session
✅ persist conversation history
✅ survive repository/process recreation
✅ Standard text/voice use persistent session state
✅ closed session rejected for further interpretation
✅ backward-compatible create response
✅ no new runtime dependency
```

Security ownership/authentication is intentionally not part of Slice 1. It is
the next Product Readiness slice.
