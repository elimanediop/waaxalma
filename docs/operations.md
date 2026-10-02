# Waaxalma v0.5.0 operations

## Start and health

Python 3.12 is the supported runtime. Keep backend and UI virtual environments separate. Install their hashed locks; development uses requirements-dev.lock. Compose builds a wheel inside the backend image, installs that wheel with runtime dependencies, and starts one Uvicorn worker. Configure OPENAI_API_KEY in the root Compose `.env`, then:

```powershell
docker compose up --build -d
docker compose ps
python ci/smoke.py --ui http://127.0.0.1:8501
```

Liveness `/health/live` reports `ok` when the process responds. Readiness `/health/ready` reports `ready` only after startup and local storage checks. Readiness does not make paid provider calls or certify upstream availability. `/metrics` exposes process metrics and a repository-backed active-session count. Preserve separate internal `BACKEND_API_URL` and browser `PUBLIC_BACKEND_URL` settings.

## Data and restart

SQLite lives in the named `waaxalma-data` volume in the supplied Compose configuration. Do not use `docker compose down -v` on data you want to retain. `docker compose down` preserves the volume. Owners, session status, metadata and persisted messages survive a backend restart. Session IDs do not resume an interrupted provider call. HTTP uploads in flight, pending streaming tasks, WebRTC credentials, rolling enhanced context and browser audio state are not a durable job queue. Reconnect and start a new realtime session after restart; do not blindly replay non-idempotent requests.

The SQLite schema upgrade from Slice 1 adds nullable owner_id and user_version 2. Legacy rows remain unowned and inaccessible through protected APIs. Assign known ownership only with the existing offline `scripts.assign_session_owner` tool and a verified migration plan. There is no auto-claim step.

## Retention

Default policy: closed sessions older than 30 days are eligible; active sessions are retained. Automatic cleanup is disabled until `SESSION_CLEANUP_ENABLED=true` is deliberately configured. `SESSION_RETENTION_DAYS` must be positive; `SESSION_CLEANUP_INTERVAL_SECONDS` defaults to 3600. When enabled, the worker performs its first pass after application startup and then periodically. Failed cleanup is logged without exception content and increments `waaxalma_session_cleanup_failures_total`; successful deletion increments `waaxalma_sessions_deleted_total`.

The cutoff uses closed_at in UTC, strictly earlier than the cutoff. Exactly-at-cutoff rows survive. SQLite count/delete occurs in one transaction with foreign-key cascade of session_messages. Dry-run does not delete or migrate. A missing database is never created by maintenance. In-memory storage follows the same policy for tests. Unknown timestamps are not treated as eligible.

For controlled maintenance, stop the backend, back up the database, activate the backend environment and use its actual database path:

```powershell
python -m scripts.cleanup_sessions --database data/waaxalma_sessions.sqlite3 --retention-days 30
# Review eligible_sessions before applying:
python -m scripts.cleanup_sessions --database data/waaxalma_sessions.sqlite3 --retention-days 30 --apply
```

For the Compose volume, after stopping the backend and backing up the volume, run the installed tool in a one-off container (dry-run):

```powershell
docker compose stop backend
docker compose run --rm --no-deps backend python -m scripts.cleanup_sessions --database /var/lib/waaxalma/waaxalma_sessions.sqlite3 --retention-days 30
```

Add `--apply` only after reviewing the result, then `docker compose start backend`. The UI remains unable to call the backend during this maintenance window.

The command defaults to dry-run and returns a JSON count/cutoff without contents or IDs. The --apply flag explicitly requests deletion. Do not point it at an arbitrary schema or an unverified production file.

This policy does not expire abandoned active conversations, remove files/audio, vacuum SQLite, erase backups/logs or certify compliance with a legal retention requirement. Configure those independently for your deployment. A committed deletion frees SQLite pages for reuse; it does not guarantee forensic erasure from the filesystem or backups.

## Shutdown

The installed `waaxalma-backend` command passes `SHUTDOWN_TIMEOUT_SECONDS` to Uvicorn (default 15). The Compose stop grace is 30 seconds. Uvicorn stops accepting connections, drains work until its budget and cancels remaining tasks before lifespan cleanup. Cancellation remains cancellation in resilience/provider code. Lifespan marks readiness false, signals the retention worker and waits for an in-flight transaction, then shuts down optional telemetry on a thread.

`TELEMETRY_SHUTDOWN_TIMEOUT_SECONDS` defaults to 5 for the asynchronous telemetry wait. A timeout is logged. A synchronous SDK exporter/thread cannot be forcibly killed by asyncio; the OS/container stop deadline remains the final bound. Defaults leave room for SQLite's five-second busy timeout and telemetry flush, but they are not a mathematical hard deadline for arbitrary third-party repositories or exporters. If you increase application budgets, increase Compose stop_grace_period accordingly and rerun stop/restart tests.

No automatic change closes all active conversations on process exit: persistence reflects explicit conversation lifecycle. A forced kill can lose an in-flight call, but a completed SQLite transaction is preserved. A process exit is not proof of upstream cancellation; do not promise that remote billing stops immediately.

## Backup and restore

Stop the backend and perform an SQLite-aware backup, or use SQLite's backup API under a controlled access path. Do not copy only sessions.db while a writer may have a WAL: committed changes can be in the WAL. Store backups with restricted access/encryption and an independent retention policy. Restore while the backend is stopped, keep schema/ownership consistent and preserve UID/GID 10001 permissions on the data volume. Verify readiness and a known session/owner after restore. Never overwrite a live database as a rollback technique.

Application rollback requires a prior compatible image and a backup/migration plan. Slice 2's schema extension is not automatically reversed. Restore data only from a reviewed snapshot; do not use `down -v` as cleanup during rollback.

## Troubleshooting and metrics

401: check X-Client-Id propagation. 403: verify ownership/offline legacy migration. 404: verify the session exists. 503 readiness: inspect storage permissions/path/database availability. Provider failures: inspect safe error_type, provider counters and request_id correlation without pasting secrets or audio/transcripts into tickets.

Active-session counts are recomputed after restart; process counters/histograms reset. `waaxalma_sessions_scrape_error=1` means the active gauge is unavailable, not zero. Detailed metrics, optional SDK installation/sampling and estimation limitations are in observability.md. Direct browser/OpenAI audio is not fully observable from the backend.

## Container release smoke

On a disposable environment only, `python ci/restart_smoke.py` creates a session, stops the backend, checks a completed lifespan shutdown and expected exit code (0 or SIGTERM 143), starts it and verifies the owner/metadata survive. It interrupts backend traffic. Run it in CI or a maintenance window, not against an occupied deployment. CI removes its own disposable volume after tests. These checks do not verify a live microphone, full-duplex audio or an actual paid translation.
