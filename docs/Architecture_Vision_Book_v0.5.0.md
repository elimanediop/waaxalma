# Waaxalma — Architecture & Vision Book v0.5.0

Status: release candidate; the final tag follows the release checklist. This document consolidates the delivered backend/product-readiness slices with the existing v0.4.4 voice and conferencing architecture. It does not claim a new microphone or realtime performance benchmark.

## Vision and design constraints

Waaxalma helps people communicate across languages through composable voice agents. The product boundary is natural multilingual interaction; the framework boundary is a set of explicit agent, skill, provider, pipeline and transport contracts. Standard translation, low-latency Direct translation and Enhanced streaming share browser audio-device capabilities while retaining their different processing responsibilities.

The guiding principle remains: add an agent, provider, pipeline or audio-device integration without rewriting the API/orchestration core. Portability matters: source becomes a Python package and a non-root container image, independent of a specific cloud. A typed configuration boundary replaces scattered environment access. The runtime currently composes OpenAI providers with passthrough context and deterministic quality; provider contracts describe extensibility, not an already-delivered multi-provider production matrix.

## Components and responsibilities

| Layer | Responsibility |
| --- | --- |
| FastAPI transport | Request validation, identity boundary, response/error contracts, correlation and HTTP/WebSocket lifecycle |
| AgentOrchestrator | Agent dispatch, execution metadata, cancellation propagation and execution outcome measurements |
| Agents and skills | Domain operations, capability composition and provider abstraction |
| Pipelines and stages | Ordered transformation of text/audio state, stage traces and duration metrics |
| Provider adapters/resilience | Remote calls, configured models, timeouts, selective retries and normalized failures |
| SessionService/repositories | Persistent conversation state, immutable owner and explicit session lifecycle |
| Observability | Business events, low-cardinality metrics and optional SDK traces |
| Streamlit/browser | Backend interaction, WebRTC, enhanced stream consumption and audio-device routing |
| Packaging/CI | Clean installs, platform regressions, wheel/container verification and release candidate assets |

Cross-cutting security and telemetry modules do not change provider contract results or ingest audio/text content for logging. SQLite transactions and the API ownership policy serve different purposes: transactions maintain local consistency; ownership constrains protected API access.

## Execution modes

Standard text interpretation applies context/translation/quality/speech stages as configured. Audio interpretation adds validated upload and speech-to-text before the text stages. A persisted session can supply language/context metadata and retain supported message history. Transient execution context remains distinct from a durable conversation record.

Realtime Direct creates ephemeral provider credentials through the backend, then the browser exchanges audio with OpenAI over WebRTC. The backend cannot measure every remote audio operation or persist an in-flight WebRTC conversation simply because an application session exists. Provider credentials are sensitive response data and are excluded from events.

Realtime Enhanced creates a transcription session and uses backend streaming translation/TTS with rolling context and terminology. The browser owns microphone selection, utterance commit and playback. Child tasks inherit correlation context; stream instrumentation scopes context around iterator advancement so the consumer does not inherit an active provider span across yield. Disconnect/cancellation is propagated. Pending buffers/tasks are volatile and require a new realtime session after restart.

The conferencing bridge remains application-agnostic: selected browser output can feed a virtual audio cable for Teams/Meet/Zoom while local monitoring uses headphones independently. Inbound conferencing capture and full-duplex remain experimental. Device routing and browser constraints do not become backend service-level guarantees in v0.5.0.

## Identity and session boundaries

Clients present X-Client-Id; the chosen development UI value is configurable. Its syntax is strict ASCII and equality is case-sensitive. Creation binds owner_id; ordinary updates cannot transfer ownership. GET/PATCH/close and interpretation paths referencing a persisted session enforce ownership/lifecycle checks. Legacy ownerless rows are denied until explicitly migrated offline.

This identity is self-declared. Network-reachable callers can impersonate an identifier, so an authenticated deployment boundary must overwrite/assert trusted identity. The framework intentionally does not introduce OAuth/OIDC/JWT/IAM. Health/metrics/docs/static audio are separate unauthenticated surfaces. Opaque audio URLs are not authorization. SECURITY.md records these limitations rather than implying that client isolation alone authenticates users.

## Durable and volatile state

SQLite is the default for development/production; isolated tests can use memory. Slice 1 databases migrate idempotently to schema version 2 by adding nullable owner_id. Existing records are never automatically claimed. Message foreign keys cascade on session deletion. Connections are opened per operation and always closed, including exceptions, to retain Windows portability.

Owner, status, languages, timestamps, metadata and saved messages survive restart in the Compose volume. Audio/provider calls, browser connections, enhanced rolling state and tasks do not. There is no durable work queue or exactly-once request execution. Transaction success and response delivery are different events: a client may lose a response after a mutation commits.

Closed sessions become eligible for cleanup after a configurable 30-day default. Automation is opt-in. Maintenance deletes only explicitly closed rows older than cutoff and their messages in one transaction; active or missing-timestamp rows remain. Dry-run reports a count. File, backup/log retention and active-session expiry require independent policies. Restart never automatically closes every active conversation.

## Configuration and packaging

Settings distinguish development, test and production. Development can read its local .env; test/production rely on explicitly injected environment. Production requires a nonblank provider key and persistent storage. Models, retry budgets, paths, CORS, telemetry and retention settings are typed and validated.

The backend is a versioned Python 3.12 wheel with an installed `waaxalma-backend` command. Backend and UI dependencies are locked separately; combining environments can introduce dependency conflicts. Hash locks are universal across Windows/Linux. Docker pins the Python base by digest, installs the wheel, uses UID/GID 10001, a read-only root filesystem and explicit writable mounts. SDK tracing is a separate optional lock/build argument; default containers do not require OpenTelemetry.

Liveness certifies process response; readiness certifies startup and local writable/session storage. Neither certifies provider availability. One backend worker is the supported packaging profile. Multi-process metrics, distributed storage and cloud deployment are future deployment decisions, not implied by a container image.

## Observability model

Events are structured around request_id, session_id, execution_mode, provider/model, languages, latency, status and safe error type. HTTP propagates a validated or generated X-Request-Id. It does not use that identifier as a filename or an idempotency key. Exceptions, texts, prompts, audio and keys are excluded from business events; identifiers still require controlled access and retention.

Prometheus covers HTTP operations, agents/stages, retries, logical provider outcomes/durations, persisted active sessions, explicit session lifetime, cleanup and available token usage. Raw identifiers/languages do not label new metrics. Active counts read the repository on scrape and survive process restart; counters reset and are not a ledger. Missing database reads mark scrape_error without fabricating zero or recreating a file.

Token measurements use provider-reported data. Cost estimation requires explicit configured rates and both token directions, and omits unobserved audio/cache/billing dimensions. Optional private OpenTelemetry SDK spans propagate incoming trace context and export to an operator-supplied OTLP/HTTP collector. Explicit root sample ratio defaults to 1.0 and parent decisions are respected. Outbound SDK auto-instrumentation and a bundled monitoring stack are not included.

## Lifecycle, quality and governance

Uvicorn drains until the configured 15-second default and cancels remaining work; Docker's default 30-second grace is the final process bound. Lifespan then stops the maintenance worker and flushes optional telemetry with a logical asynchronous wait budget. Synchronous SDK threads cannot be forcibly cancelled by asyncio. Operators must size shutdown budgets for their exporters/repositories and rerun clean-exit tests.

PR quality gates include syntax, separate hashed installs, Windows/Linux backend regressions, UI render checks, optional tracing tests, a clean wheel install outside source, container/non-root health and owner smoke, plus clean-exit/restart owner continuity. Artifacts contain wheel, tested images and SHA-256 checksums. No cloud deployment is baked in. The final Git tag/public release is a reviewed operator action after the gates and manual browser acceptance checks.

The targeted secret hygiene gate flags tracked environment/generated data and common credential signatures. It does not replace human review or vulnerability assessment. The implementation ships a documented candidate, not a claim of completed independent security audit.

## Evolution

v0.5.0 establishes a portable readiness baseline. Subsequent work can add authenticated ingress integration, protected audio delivery, active/file retention, more providers, durable jobs/distributed state, multi-worker observability and richer tracing/exporter choices. Experimental duplex features can mature with dedicated browser/audio acceptance criteria. v1.0 should be defined by stable contracts and verified operational behavior, not by removing documented deployment constraints through a version label.

Operational details: [operations](operations.md), [observability](observability.md), [release checklist](release-v0.5.0.md), [security](../SECURITY.md), [environment](../ENVIRONMENT.md).
