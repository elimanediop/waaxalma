# Upgrade v0.5.0 → v1.0.0

This guide applies to the v1.0.0 code and artifacts upgrading v0.5.0. Create
the final tag only after the release acceptance checklist passes.

## Storage contract

The current upgrade keeps SQLite `PRAGMA user_version=2`. It does not rename
tables, rewrite stored sessions or assign owners. Repository startup is
idempotent. It preserves session IDs, owners (including NULL), languages,
execution mode, active/closed state and timestamps, JSON metadata and ordered
message rows. Schema-0/1 legacy storage remains supported through the existing
owner-column migration; those unowned sessions remain inaccessible until
explicit ownership assignment.

Startup now refuses unknown/future schema versions before schema or journal
changes, rather than resetting their version to 2. No automatic downgrade is
provided. An unrelated database is not an upgrade source. The read-only
inspection utility checks table shape, quick integrity and foreign keys.

## Inspect and back up

Use an actual configured `SESSION_DB_PATH`, not an assumed working directory.
Stop application writers for the maintenance window. Keep the existing release
artifact, configuration and full storage backup for rollback.

From `backend`, with the new backend development environment activated:

```powershell
python -m scripts.session_database --database .\data\waaxalma_sessions.sqlite3
New-Item -ItemType Directory -Force backups
python -m scripts.session_database --database .\data\waaxalma_sessions.sqlite3 --backup .\backups\before-v1.sqlite3
```

The installed wheel also exposes `waaxalma-session-database` with the same
arguments. Inspection opens an existing file read-only and does not migrate,
create a missing database or print session content/owner IDs. Its JSON report
contains schema version, integrity and counts, including unowned sessions.

Backup uses SQLite's backup API so committed WAL rows are included; simply
copying the main SQLite file while writers run can omit them. A new destination
is required. Existing destinations and source-equals-destination are rejected.
The resulting standalone snapshot is checked for integrity/foreign keys and
uses DELETE journaling. It can be opened by a new repository/process.

For the default Compose volume, after integrating this slice and building its
image, run a stopped-writer maintenance backup:

```powershell
docker compose stop ui backend
docker compose run --rm --no-deps --entrypoint waaxalma-session-database backend --database /var/lib/waaxalma/waaxalma_sessions.sqlite3 --backup /var/lib/waaxalma/before-v1.sqlite3
docker compose cp backend:/var/lib/waaxalma/before-v1.sqlite3 ./before-v1.sqlite3
```

Choose a new backup filename for each run. Store an independent copy outside
the Docker volume. This utility does not back up generated audio or secrets;
include other required volume contents/configuration in your maintenance plan.
Never run `ci/restart_smoke.py` against a real deployment: it creates/modifies
test sessions and is intended only for the disposable CI Compose project.

## Install and verify

Use a fresh Python 3.12 backend environment and hashed locks; install the new
wheel, or rebuild the container. Keep the UI in its own environment. Retain the
same volume/project/database path and client IDs. Start with the existing
retention configuration; enabling cleanup changes which old closed sessions
remain stored.

```powershell
docker compose up --build -d --wait
```

Verify readiness and internal UI/backend reachability. Check an existing owned
active session and a closed session through the API. Verify history/metadata,
foreign-client 403 and closed-session active-operation 409. An unowned legacy
session must not suddenly become accessible. Test Standard/Direct/Enhanced
with real audio during manual acceptance.

The upgrade compatibility suite starts from an independently frozen v0.5.0
schema and data, reopens it repeatedly, and compares raw persisted values.
It also opens/closes/verifies storage in separate Python processes. Compose CI
checks full active/closed session payloads, synthetic history, owner isolation,
clean shutdown and backup integrity across backend stop/start.

## Client compatibility and rollback

Original extension imports remain available; new extensions should use
`app.framework`. There is no automatic plugin discovery. HTTP success payloads
remain stable; older string-valued HTTP errors now use `detail.code` and
`detail.message`. Invalid enhanced events return recoverable errors. Review
`api-streaming-stability.md` for lifecycle/queue limits and reconnect behavior.

Rollback requires stopping every writer before replacing storage. Restore the
pre-upgrade database snapshot to the configured path and remove stale WAL/SHM
sidecars belonging to the replaced database, while all writers remain stopped.
Restore the matching release/configuration/full storage backup as appropriate,
then start and verify. Restoring an older snapshot discards writes committed
after that snapshot; rollback is not a merge mechanism.

Because this candidate retains schema 2, v0.5.0 can read the same table layout,
but that is not a promise of backward compatibility for future schemas or
changed application semantics. Use the validated backup/release pair rather
than letting older code migrate unknown future storage. In-flight provider
operations/live streams are never resumed by database restoration.
