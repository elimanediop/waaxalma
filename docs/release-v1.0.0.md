# v1.0.0 Stable Framework Release Acceptance

This checklist closes the five stable framework slices. Runtime, wheel and
Compose image versions are 1.0.0. Publication requires a verified commit and
an annotated tag; generating the implementation does not publish a release.

## Acceptance scope

The stable surface is documented in `framework-contracts.md`, with opt-in
extension checks in `extension-conformance.md`. HTTP and Enhanced WebSocket
schemas are reviewed snapshots, not provider behavior or latency guarantees.
The supported profile is CPython 3.12 on Linux/Windows x64 and Linux amd64
containers with one backend worker. SQLite stays at schema 2.

X-Client-Id provides client isolation using self-declared identity. An internet
exposure still requires the deployment's authentication and access controls.
No cloud deployment, multi-worker support, new provider matrix or performance
SLA is introduced by this release. OpenTelemetry remains optional.

## Local checks

Use separate backend and UI environments and the supported Python minor.
From the repository root with the backend development environment activated:

```powershell
python ci/static_checks.py
python ci/release_checks.py
python ci/runtime_checks.py
python ci/api_contract_checks.py
$env:APP_ENV = "test"
Push-Location backend
python -m pip check
python -m pytest -q
python -m build --wheel --no-isolation --outdir ../dist
Pop-Location
python ci/artifact_checks.py
python ci/verify_artifacts.py
```

Use a clean generated `dist` directory before building: the artifact check
requires exactly one backend wheel. Do not copy a previous version's wheel into
this directory. With the UI environment activated, run `python ci/ui_render_checks.py`
and `python -m pip check`. The optional SDK tests require the separate hashed
`backend/requirements-otel.lock`; CI installs it in its own job. Without it,
four SDK tests skip intentionally.

## CI and container acceptance

Require all quality jobs on the exact release commit: static, backend-tests on
Ubuntu and Windows, ui-install on Ubuntu and Windows, otel-tests, package and
container. Packaging installs the wheel outside the checkout and exercises
public imports, the external extension example and the database CLI.

The container job validates Compose, builds both images, waits for readiness,
checks non-root UID 10001, checks health/OpenAPI version 1.0.0, ownership and
metrics, then tests persistent metadata/history and lifecycle after restart.
Exported images and the wheel share a SHA256SUMS manifest, verified before
upload. These checks make no paid provider calls. Checksums detect corruption;
they do not authenticate an artifact publisher.

Before tagging, also exercise real browser audio in Standard, Direct and
Enhanced modes with the intended provider configuration. Verify microphone,
primary output and local monitoring, and repeat a stop/start with the persistent
volume. `docker compose up --build -d` uses the new 1.0.0 images. Do not use
`docker compose down --volumes` against deployment data; that cleanup belongs
to disposable CI. Keep provider credentials out of logs and commits.

## Upgrade and rollback

Follow `upgrade-v0.5-to-v1.md`: inspect and back up the configured SQLite file
through the backup utility, retain the full volume/configuration and previous
artifact, and test ownership and ordered history after upgrade. No live
WebRTC/WebSocket connection resumes after restart. Active stored conversations
remain active; in-flight audio and buffers are volatile. Retention and shutdown
budgets are documented in `operations.md`.

## Tag the verified commit

Merge the accepted commit into the release branch and check its CI before tagging.
From a clean checkout, with the intended release commit at HEAD:

```powershell
git status --short
git log -1 --oneline
git tag -a v1.0.0 -m "Waaxalma v1.0.0 Stable Framework Release"
git push origin v1.0.0
```

Inspect the workflow triggered by `v1.0.0` and its verified artifacts. The
release gate checks that the Git tag matches package metadata. Do not move or
force an already published tag. Release assets remain GitHub Actions artifacts
with 14-day retention unless separately published; this workflow does not
create a GitHub Release or upload packages to a public registry automatically.
