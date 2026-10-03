# Waaxalma Architecture and Vision Book v1.0.0

Waaxalma v1.0.0 establishes a stable extension surface for multilingual voice
agents while retaining the product readiness architecture delivered in v0.5.0.
This book is for framework authors, maintainers and operators. Public contracts,
reviewed transport schemas and an explicit runtime/upgrade profile define the
release boundary. Publication follows the verified-commit acceptance checklist.

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
| Packaging/CI | Clean installs, platform regressions, wheel/container verification and verified release artifacts |

Cross-cutting security and telemetry modules do not change provider contract results or ingest audio/text content for logging. SQLite transactions and the API ownership policy serve different purposes: transactions maintain local consistency; ownership constrains protected API access.

## Execution modes

Standard text interpretation applies context/translation/quality/speech stages as configured. Audio interpretation adds validated upload and speech-to-text before the text stages. A persisted session can supply language/context metadata and retain supported message history. Transient execution context remains distinct from a durable conversation record.

Realtime Direct creates ephemeral provider credentials through the backend, then the browser exchanges audio with OpenAI over WebRTC. The backend cannot measure every remote audio operation or persist an in-flight WebRTC conversation simply because an application session exists. Provider credentials are sensitive response data and are excluded from events.

Realtime Enhanced creates a transcription session and uses backend streaming translation/TTS with rolling context and terminology. The browser owns microphone selection, utterance commit and playback. Child tasks inherit correlation context; stream instrumentation scopes context around iterator advancement so the consumer does not inherit an active provider span across yield. Disconnect/cancellation is propagated. Pending buffers/tasks are volatile and require a new realtime session after restart.

The conferencing bridge remains application-agnostic: selected browser output can feed a virtual audio cable for Teams/Meet/Zoom while local monitoring uses headphones independently. Inbound conferencing capture and full-duplex remain experimental. Device routing and browser constraints do not become backend service-level guarantees in v1.0.0.

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

v0.5.0 establishes a portable readiness baseline. Subsequent work can add authenticated ingress integration, protected audio delivery, active/file retention, more providers, durable jobs/distributed state, multi-worker observability and richer tracing/exporter choices. Experimental duplex features can mature with dedicated browser/audio acceptance criteria. v1.0.0 establishes stable contracts and verified operational behavior within the documented deployment profile.

Operational details: [operations](operations.md), [observability](observability.md), [release checklist](release-v1.0.0.md), [security](../SECURITY.md), [environment](../ENVIRONMENT.md).


## Stable public framework

Extension authors import the 24 public contracts from `app.framework`. The
facade re-exports original objects, preserving class identity and existing
module imports. Importing the facade does not construct provider clients,
initialize SQLite or require an API key. Application composition belongs to
startup, outside the contract namespace.

`app.framework.testing` supplies optional, pytest-independent conformance checks
for agents, pipeline stages and standard/live providers. Checks execute the
provided sample and validate returned types, async conventions and cleanup.
They do not prove provider correctness or impose new success/error invariants.
Streaming samples are bounded and close their iterator on failure or cancellation.
The external extension example is exercised from an installed wheel outside
the source checkout.

Compatibility applies to documented imports and calling conventions. Internal
implementation modules do not become public merely because they are importable.
Additive optional fields remain possible; incompatible public contract changes
require a major version and documented migration. See `framework-contracts.md`
for the precise compatibility and deprecation policy.

## Transport stability and cancellation

Reviewed HTTP and Enhanced WebSocket schemas live in `docs/contracts` and are
checked against generated schemas on Linux and Windows. OpenAPI release version
is normalized in the snapshot; business models and events remain reviewable.
HTTP failures use structured code/message envelopes; unexpected failures expose
a safe message. Identity, ownership and session lifecycle retain 401/403/404/409
semantics. Generic agent output remains operation-specific.

Enhanced streaming separates receive monitoring from serial event processing.
Recoverable invalid events produce documented errors. Incoming and speech/output
queues are bounded. Disconnect cancels processing and closes provider streams;
processing failure clears the processor before another start. Contract tests
cover malformed events, cancellation and cleanup. These guarantees do not
promise a provider latency threshold or restore an interrupted live session.

## Supported runtime and upgrade

The supported profile is CPython 3.12 on Linux/Windows x64 with independent
backend and UI locks. Containers are Linux amd64 and run as UID/GID 10001 with
one backend worker. Node 22 validates JavaScript in CI. Native macOS, ARM64,
other Python minors and multiple workers require their own acceptance work.

SQLite remains schema 2. Upgrade from v0.5.0 preserves session identifiers,
owners, language/mode, timestamps, status, JSON metadata and ordered messages.
Startup rejects future schemas before database changes. Legacy ownerless
sessions stay inaccessible until deliberate offline assignment.

The installed `waaxalma-session-database` command inspects an existing database
read-only and creates an exclusive SQLite backup containing committed WAL rows.
It validates integrity and foreign keys and prints counts, not conversation
content. Retain configuration, the full volume and prior artifacts for rollback.
Stored active conversations survive restart; live connections, pending audio
and transcript buffers do not.

## Release acceptance and governance

All five framework slices are integrated: public contracts, extension
conformance, API/streaming stability, supported runtime/upgrade, and stable
release acceptance. Runtime, package, health/OpenAPI and image versions are
1.0.0. The workflow verifies installs, static checks, regression/contracts,
optional telemetry, the isolated wheel, containers, restart and artifact hashes.

Checksums are streamed and independently verified before artifact upload.
They detect changed bytes, not publisher identity. CI assets have a 14-day
retention; permanent release publication is a separate maintainer action.
The workflow remains portable and does not deploy to a specific cloud.

The final annotated `v1.0.0` tag must reference the accepted commit after all CI
jobs and real browser audio modes pass. Tag-triggered CI also checks tag/version
agreement. Follow `release-v1.0.0.md` and record acceptance for the exact commit.
No tag or release publication is implied by preparing these documents.

## Vision after the stable release

Future work can expand providers, authentication integration, audio interaction
and deployment profiles through reviewed contracts. Each addition needs its own
compatibility, security and runtime evidence. The stable release supplies the
extension and operations foundation; it does not advertise unimplemented
providers, full-duplex conferencing or multi-replica persistence as supported.
