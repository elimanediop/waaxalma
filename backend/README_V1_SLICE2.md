# Waaxalma — v1.0.0 Slice 2

Apply this overlay at the project root after Slice 1, preserving paths. No files
need deletion. It includes reusable conformance helpers, their tests, an external
agent/provider/stage example, packaging CI checks, documentation and changelog.

From `backend` with the clean `.venv-v1` activated:

```powershell
python -m pip install --require-hashes -r requirements-dev.lock
python -m pip check
$env:APP_ENV = "test"
python -m pytest -q
python -m build --wheel --no-isolation --outdir ../dist
```

From the project root:

```powershell
python ci/static_checks.py
python ci/release_checks.py
python ci/artifact_checks.py
```

The four OpenTelemetry tests remain optional without `requirements-otel.lock`.
See `docs/extension-conformance.md` and the example README for usage and limits.
The example needs an installed wheel; the CI package job tests it in a clean
environment outside the checkout. Container validation remains in the full CI.
Do not tag v1.0.0 yet.

Validation locale Linux/Python 3.12 : 426 tests passent, 4 tests OpenTelemetry
sont ignorés, et le warning Starlette/AnyIO connu reste non bloquant. Les 44
nouveaux tests, les contrôles statiques/release/artefact, le build wheel et
l'exemple externe depuis une installation isolée passent. Windows et Docker
restent à valider dans la CI du projet.
