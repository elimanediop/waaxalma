# v1.0.0 Slice 4 — Supported Runtime

This profile defines the v1.0.0 supported runtime and its acceptance gates.
Runtime, package and image versions are aligned to 1.0.0.

| Component | Supported profile | Validation |
| --- | --- | --- |
| Backend and Python wheel | CPython 3.12, Linux/Windows x64 | Clean hashed install, regression/contract tests on GitHub Ubuntu/Windows runners |
| Streamlit UI | CPython 3.12, Linux/Windows x64, separate environment | Clean UI lock installation and UI render checks on both runners |
| Container artifact | Linux amd64, non-root UID/GID 10001 | Package build, Compose health/smoke/restart checks on Linux runner |
| Windows container hosting | Docker Desktop with Linux containers | Runs the Linux artifact; does not imply support for native Windows images |
| JavaScript validation | Node 22 | Syntax/render checks; Node is a CI tool, not an application runtime requirement |
| Persistence | Local SQLite schema 2, WAL, persistent writable volume | v0.5.0 fixture, backup/integrity, fresh-process reopen, container restart |
| Server workers | One backend worker | Installed console command explicitly uses `workers=1` |

Other Python minors, macOS native execution, ARM64 images and multi-worker/
multi-replica operation are outside the validated profile. They require their
own dependency/build/acceptance work before being advertised as supported.
Python 3.12 patch releases remain within the minor boundary; this is not a claim
that every patch release has been exercised. The pinned Docker base and CI
selected patch are the concrete tested builds.

`ci/runtime_matrix.json` is the profile declaration. `ci/runtime_checks.py`
checks it against `requires-python`, the CLI guard, schema version, Docker base
and configured CI matrices. The installed backend command rejects unsupported
Python minors before loading the server. Wheel metadata also constrains Python
to `>=3.12,<3.13`. The UI's standalone environment must use the same minor.

## Environment separation

Use different virtual environments for backend and UI. Their lock files are
independent; installing both in one environment can create incompatible
transitive dependencies. Never copy `.venv` between Windows and Linux or into
container build context. Build/install a wheel and the appropriate hashed lock.

| Mode | Configuration behavior |
| --- | --- |
| Development | Explicit `APP_ENV=development`; local `.env` may be loaded |
| Test | `APP_ENV=test`; no automatic `.env`, test key fallback, memory sessions unless SQLite is explicitly selected |
| Production | `APP_ENV=production`; environment-only configuration, provider key required, SQLite required |

OpenTelemetry remains optional through its own lock and configuration. Its four
tests may skip in the baseline backend environment; the dedicated CI job runs
with those dependencies installed. Provider models/access are external
configuration, not frozen framework semantics.

## Persistent versus transient state

Committed conversation rows, owners, languages, status/timestamps, metadata and
ordered message history persist when the SQLite file/volume is retained. Active
conversation status remains active after restart; it does not imply resuming a
WebSocket, audio device or provider connection. Closed status/closed timestamp
also persist. A missing owner stays missing until explicit offline assignment.

Execution contexts, pending transcript buffers, segment numbers, in-flight
translation/TTS, browser recordings and Streamlit session state are transient.
Clients must reconnect/restart live sessions. Partial work is not replayed and
there is no exactly-once recovery guarantee.

Keep the data volume and generated audio together when full application storage
recovery is required. The SQLite backup utility backs up conversation storage,
not static audio, uploads, configuration or secrets. Readiness tests local
resources only, not provider connectivity.

## Restart and network troubleshooting

`docker compose down` preserves named volumes; `down --volumes` deletes them.
The latter is only used by disposable CI cleanup. Changing Compose project name
can select a different volume and make existing sessions appear absent.

The Standard UI uses its internal `BACKEND_API_URL`; browser live clients use
`PUBLIC_BACKEND_URL`. Test both paths. For internal connectivity:

```powershell
docker compose exec -T ui python -c "import requests; from config import API_URL; r=requests.get(API_URL+'/health/ready', timeout=5); print(API_URL,r.status_code,r.text)"
```

A connect timeout occurs before Standard provider processing. Recreating the
Compose network can resolve stale connectivity while preserving volumes:

```powershell
docker compose down
docker compose up --build -d --wait
```

Do not treat success of a browser/provider connection as proof that the internal
UI/backend path works. If the timeout persists, inspect both container networks
and host VPN/firewall routing before changing application code.
