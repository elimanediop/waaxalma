# v1.0.0 Validation Record

## Evidence and remaining acceptance

The integrated Slice 4 baseline was accepted by the maintainer after local
checks, regression tests and container validation. Slice 5 changes version
metadata, release gates and documentation; final Windows/container/browser
acceptance must run against this exact release commit before tagging.

Local Linux CPython 3.12.14 validation: 472 tests passed, 4 optional SDK tests
skipped, and one existing Starlette deprecation warning. Python/JavaScript
syntax, runtime/release hygiene and HTTP/WebSocket snapshot checks passed.
The 1.0.0 wheel built successfully, installed into a fresh hashed runtime
environment outside the checkout, and passed version/OpenAPI/public import
and maintenance CLI checks. Artifact checksums passed; tampered bytes and
unsafe manifests were rejected. The five-page Word book was rendered and
reviewed. UI render dependencies were unavailable in the local offline cache;
that gate, Windows and container/browser checks remain CI/operator acceptance. The backend development environment intentionally omits the optional
OpenTelemetry SDK, so four SDK tests skip; the separate CI otel-tests job is
required for release. The existing Starlette TestClient deprecation warning
is non-fatal and is not an application failure.

The release checklist is `release-v1.0.0.md`. A clean run on a previous commit
is baseline evidence, not evidence for newly built 1.0.0 images. No published
tag, GitHub Release or registry upload is claimed by this record.
