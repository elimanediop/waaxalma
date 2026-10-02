# Slice 6 validation and acceptance

Local Linux/Python 3.12 results:

- Full optional-SDK environment: 348 tests passed.
- Clean default environment: 344 tests passed, 4 optional-SDK tests skipped.
- Python/JavaScript syntax, dependency compatibility and targeted release/credential hygiene checks passed.
- Retention tests exercise SQLite and memory, dry-run, message cascade, active/recent/boundary preservation, missing databases, task shutdown and CLI graceful-drain configuration.

A known Starlette/AnyIO deprecation warning remains. The supplied Compose container stop/restart test and Windows tests must run in your CI/environment before the final tag. Docker is unavailable in the authoring environment, so those checks are not claimed as completed locally.

The authoring smoke uses an installed wheel outside the source checkout, health/metrics/session ownership and native SIGTERM/restart persistence. It does not simulate a live microphone or a paid provider request. Runtime dependencies and provider model settings remain the prior locked baseline; this slice is not a dependency vulnerability audit.
