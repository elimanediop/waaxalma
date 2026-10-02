# v0.5.0 Slice 4 — CI/CD & Quality Gates

Copy `.github/`, `ci/` and this document into the project root containing `backend/`, `streamlit/` and `compose.yaml`. Keep the existing root README, environment files and session data. The delivered ZIP is an overlay, not another backend distribution.

GitHub Actions runs on pull requests, pushes to main/master and manual dispatch. No cloud deployment, registry push, release publication or final version tag is configured. The final v0.5.0 tag remains Slice 6.

## Gates

1. Python AST parsing and Node syntax checks for JavaScript files and inline HTML scripts.
2. Clean backend dependency installation with hashes, `pip check`, and the full pytest suite on Windows and Linux (Slice 3 baseline: 300 tests; Slice 5 adds observability coverage). Any test failure blocks the next stage; no artificial fixed test count.
3. Independent UI dependency installation and `pip check` on Windows and Linux. Validate actual HTML rendering, browser URL separation and identity injection.
4. Build the wheel, inspect metadata and install it in a separate virtual environment outside the source checkout. Import the installed application in test mode.
5. Build both containers; wait for their health checks; assert runtime UID 10001. HTTP smoke checks cover liveness/readiness, session creation/closure, owner isolation and 401/403/404 responses, plus Streamlit health.
6. Export the tested images with `docker save`, and publish wheel, images and SHA256SUMS as a downloadable CI release candidate. Artifacts expire after 14 days. This is not a GitHub Release.

No Ruff/mypy configuration exists in the current baseline. Syntax checks are not linting or static type analysis; these tools require a separate agreed baseline. Actions currently use major version references; immutable action SHA pinning can be addressed with the governance work in Slice 6.

## Local commands

From the root, with Node installed:

```powershell
python ci/static_checks.py
# Use the separate backend development virtual environment:
python -m pip check
cd backend
python -m pytest -q
cd ..
# Use the separate UI virtual environment:
python ci/ui_render_checks.py
# Running Compose must already be healthy:
python ci/smoke.py --ui http://127.0.0.1:8501
```

CI uses a dummy API key and does not invoke remote AI providers. Its disposable volume is removed during cleanup. Smoke tests create and close one owned session; when run locally this session remains in your database.

Configure branch protection to require `static`, both `backend-tests` jobs, both `ui-install` jobs, `package` and `container`. Repository settings are not changed by copying this overlay. A workflow failure prevents artifacts from reaching the release-candidate step. Container logs are printed even on failure.

## Validation limits

The supplied workflow must be run in your GitHub repository to confirm runner behavior. Docker is unavailable in the authoring environment; container builds and the Docker smoke gate have not been executed here. The Slice 3 Docker run was confirmed separately on the user's machine. No realtime audio/browser interaction is claimed by the HTTP smoke test.

Slice 5 adds a required optional-SDK test job (`otel-tests`) and changes image tags to `0.5.0-slice5`. See observability.md.
