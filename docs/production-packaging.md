# Waaxalma v0.5.0 — Slice 3: Production Configuration & Packaging

Complete backend and Streamlit sources following Slice 2, plus an installable
backend wheel, locked dependencies, non-root Docker images and local Compose.
Security identification remains X-Client-Id; no account or IAM platform is added.

## Quick start: Docker Compose (Windows Docker Desktop / Linux)

From this directory in PowerShell:

```powershell
Copy-Item .env.example .env
# Edit .env and set OPENAI_API_KEY to your provider key.
docker compose config --quiet
docker compose up --build -d
docker compose ps
```

Open http://localhost:8501. The default client ID is `waaxalma-for-elimane`.
Backend documentation: http://localhost:8000/docs.

```powershell
Invoke-RestMethod http://localhost:8000/health/live
Invoke-RestMethod http://localhost:8000/health/ready
docker compose logs --tail=100 backend ui
docker compose down
```

`down` retains the named volume. `down --volumes` deletes persisted data; use it
only if you intend to discard sessions and audio. Initial image builds require
internet access to Docker Hub and PyPI. Keep OPENAI_API_KEY in the local .env,
never in an image, Docker build argument, source archive, or Git.

Compose binds published ports to 127.0.0.1 for the established single-workstation
use case. It sets APP_ENV=production, uses the Dockerfile healthchecks, starts UI
only after backend readiness, uses non-root UID/GID 10001, read-only roots and
writable runtime volume/tmpfs. Runtime state lives in `waaxalma-data`:
SQLite at `/var/lib/waaxalma/waaxalma_sessions.sqlite3`, audio under
`/var/lib/waaxalma/static/audio`, uploads under `/var/lib/waaxalma/uploads`.
A pre-existing bind mount must be writable by UID/GID 10001. Fresh named volumes
inherit the image directory ownership. Restart the backend to apply config changes.

## Backend source → Python package → container image

`backend/pyproject.toml` defines waaxalma-backend 0.5.0, Python 3.12, the package
contents and `waaxalma-backend` console command. The wheel under `dist/` is an
installable artifact. The Docker builder creates a wheel and the runtime installs
that wheel, rather than importing a source checkout. It includes the explicit
legacy owner-assignment command from Slice 2.

Base images use a verified Python 3.12.12 slim-bookworm registry digest.
Application, transitive and build dependencies are version/hash locked. Install
with `--require-hashes`; wheel installation is `--no-deps` after the lock.
SOURCE_DATE_EPOCH fixes wheel timestamps. Updating dependencies/base images is
an explicit maintenance action; these locks are not a claim of a security audit.

## Native backend: development

From backend/, using Python 3.12 in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install --require-hashes -r requirements-dev.lock
.\.venv\Scripts\python -m pip install --no-build-isolation --no-deps .
Copy-Item .env.example .env
# Set OPENAI_API_KEY in backend/.env.
.\.venv\Scripts\waaxalma-backend
```

Development reads .env from the process working directory. Environment variables
have precedence. Set APP_ENV in the process environment to select the mode
before dotenv parsing. Explicit production/test modes never auto-read .env.

## Install the wheel independently

From the archive root:

```powershell
python -m venv .venv-runtime
.\.venv-runtime\Scripts\python -m pip install --require-hashes -r backend/requirements.lock
.\.venv-runtime\Scripts\python -m pip install --no-deps dist/waaxalma_backend-0.5.0-py3-none-any.whl
$env:APP_ENV = "production"
$env:OPENAI_API_KEY = "your-provider-key"
$env:HOST = "127.0.0.1"
$env:DATA_DIR = "$PWD/runtime/data"
$env:STATIC_DIR = "$PWD/runtime/static"
$env:UPLOAD_DIR = "$PWD/runtime/uploads"
.\.venv-runtime\Scripts\waaxalma-backend
```

This works from outside the source directory. No project static directory is
required: runtime directories are created at startup, never in site-packages.
For a native production deployment, run under a dedicated unprivileged OS user
and choose writable persistent paths. The console command uses one worker and
no reload. SQLite is the only production repository implemented in this slice.

## Native UI

From streamlit/ in a separate terminal:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install --require-hashes -r requirements.lock
Copy-Item .env.example .env
.\.venv\Scripts\python -m streamlit run streamlit_app.py --browser.gatherUsageStats=false
```

Both BACKEND_API_URL and PUBLIC_BACKEND_URL default to http://127.0.0.1:8000.
Compose instead uses http://backend:8000 internally and http://localhost:8000
publicly. PUBLIC_BACKEND_URL is also used for standard audio URLs. CLIENT_ID
is validated and injected into all three embedded realtime clients. Browser
WebSockets use client_id as the Slice 2 backend supports.

If changing BACKEND_PORT/UI_PORT, also update PUBLIC_BACKEND_URL/CORS_ORIGINS.
Microphones, headsets and virtual cables stay on the Windows/browser host; no
host audio devices are mounted in the containers. Browser permissions and the
existing device-selection UI still apply. A remote deployment requires appropriate
HTTPS/WSS and origin configuration, beyond the local Compose launch supplied.

## Health semantics

| Endpoint | Purpose | Response |
|---|---|---|
| /health | Compatibility liveness endpoint | 200 |
| /health/live | Process can answer HTTP | 200 |
| /health/ready | Startup complete, writable audio/uploads, usable session storage | 200 or 503 |

Checks require no client ID and make no OpenAI request. Readiness validates local
resources, not provider availability, key validity or model access. SQLite probes
open an existing database read/write, verify the ownership schema and roll back
a no-op write. They do not create sessions or append history. Failures return a
generic response and are logged. Startup fails if configuration or local resources
are unusable; a runtime storage failure makes readiness 503 while liveness stays 200.

## Environments and variables

See [ENVIRONMENT.md](ENVIRONMENT.md) and the three .env.example files.
Test mode supplies a dummy provider key only when none is configured and selects
memory storage by default. Tests still mock provider operations. Production
requires a nonblank provider key and SQLite. Unsupported modes/providers, invalid
ports/retry values and wildcard origins are rejected. Keys are SecretStr values
and validation error strings hide input values. Backend imports retain their
legacy config constants via a facade over one cached Settings instance.

## Existing sessions

Native default database location remains data/waaxalma_sessions.sqlite3 relative
to the working directory. Slice 2 ownership migration is preserved. Copying a
SQLite database into Docker requires stopping the original backend and including
its committed WAL state (use a proper SQLite backup or clean shutdown), then
placing it at the volume path above with UID/GID 10001 permissions. Ownership IDs
must match CLIENT_ID; unowned Slice 1 sessions stay denied until explicit offline
assignment. See backend/SLICE2_SECURITY_BOUNDARIES.md. No database is shipped here.

## Tests, package build and lock maintenance

From backend/:

```powershell
.\.venv\Scripts\python -m pytest -q
$env:SOURCE_DATE_EPOCH = "1760000000"
.\.venv\Scripts\python -m build --wheel --no-isolation --outdir ../dist
```

Tests select APP_ENV=test and temporary state directories via conftest.py. If
APP_ENV is explicitly set to production in your shell, switch it to test first.
Run tests in the backend directory. A dummy test key is not a provider credential.

Regenerate locks explicitly using uv after changing requirements/pyproject:

```text
uv pip compile backend/pyproject.toml --generate-hashes -o backend/requirements.lock
uv pip compile backend/requirements-dev.in --generate-hashes -o backend/requirements-dev.lock
uv pip compile streamlit/requirements.in --generate-hashes -o streamlit/requirements.lock
```

Build-tool versions are recorded separately in backend/requirements-build.lock.
CI gates, production telemetry and release governance remain Slices 4, 5 and 6.
See VALIDATION.md for checks performed and the Docker execution limitation.

## References

- [Pydantic settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [Docker build practices](https://docs.docker.com/build/building/best-practices/)
