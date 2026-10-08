# Changelog

All notable changes to **Waaxalma** are documented here.

The project follows semantic versioning where practical.

------------------------------------------------------------------------

## [v1.1.1] — Conference audio isolation and monitoring — 2026-10-08

### Added
- Independent Conference Monitor to play selected Conference Input through a local headset.
- Dedicated monitor enable/output-device preferences in Streamlit.
- Reference-aware audio isolation for Direct and Enhanced using a separately selected Conference Input.
- Documented Windows/Teams dual-cable (CABLE-A inbound / CABLE-B outbound) setup and validation checklist.

### Behavior and limitations
- Conference Monitor does not depend on Full Duplex or inbound translation Start/Stop.
- Conference Monitor and translated-audio Local Monitor are separate features.
- The current reference-VAD gate is **not** a full acoustic echo canceller; simultaneous speakers and missing/invalid references require further testing.
- Manual acceptance reported for Teams playback and no remote retranslation in Direct and Enhanced with the A/B setup. Automated CI and Docker smoke tests must still run on the full repository before tagging.

## \[v1.1.0\] --- Text Translation Workspace --- 2026-10-07

### Added

-   Dedicated **Text** workspace in Streamlit alongside the existing **Voice**
    workspace.
-   `TextTranslationService` for speech-free translation using the existing
    **Context → Translation → Quality** pipeline capabilities.
-   `TextTranslationResult` value model for translated text and quality
    metadata.
-   `POST /api/text/translate` backed by the new text translation service while
    preserving the existing REST response contract.
-   Source-language selection in the Text workspace, with an unspecified
    source language represented internally as `None`.
-   Text translation service tests and Voice/Text Streamlit render checks.

### Changed

-   Streamlit settings now separate **Workspace type** (`Voice` / `Text`) from
    Voice execution mode (`Standard` / `Direct` / `Enhanced`).
-   The composition root now constructs the dedicated text translation service
    from the existing provider registry and Context, Translation and Quality
    capabilities.
-   Text translation inherits existing request correlation, provider telemetry,
    Prometheus metrics, token accounting and estimated-cost instrumentation.

### Compatibility and scope

-   Existing Voice Standard, Direct and Enhanced execution paths remain
    available and are not replaced by the Text workspace.
-   `X-Client-Id` remains the client-isolation boundary for the text API.
-   Text translation does not invoke TTS.
-   Document/PDF/DOCX translation, batch translation, persistent translation
    history and custom glossaries are outside the v1.1.0 scope.
-   OpenTelemetry remains optional and independent.

### Verification

-   Static checks passed.
-   Streamlit Voice/Text render checks passed.
-   Full automated test suite passed.
-   Docker Compose build/runtime and backend health checks passed.
-   `POST /api/text/translate` smoke test passed in the packaged environment.
-   End-to-end translation from the Streamlit Text workspace was manually
    validated.

This release adds a new user-facing text translation capability while reusing
the framework's existing provider, pipeline, quality, security and
observability foundations.

------------------------------------------------------------------------

## \[v1.0.2\] --- Metrics Observability --- 2026-10-06

### Added

-   Prometheus service integrated into Docker Compose and configured to
    scrape the backend `/metrics` endpoint.
-   Grafana service integrated into Docker Compose with automatic
    Prometheus datasource provisioning.
-   Provisioned **Waaxalma --- Overview** dashboard with Provider,
    Operation and Route filters.
-   Dashboard views for HTTP traffic and latency, active sessions, AI
    provider calls/errors/retries/latency, pipeline stages and agents,
    realtime sessions/client latency, token usage and estimated provider
    cost.
-   Static observability-stack tests that validate configuration and
    dashboard wiring without requiring Docker.
-   Updated English and French Architecture & Vision Books for v1.0.2.

### Observability behavior

-   Existing low-cardinality Prometheus metric contracts are preserved.
-   `/metrics` remains visible as HTTP traffic by design.
-   Token usage can be recorded without pricing; estimated cost requires
    configured provider token prices.
-   OpenTelemetry remains optional and independent from the
    Prometheus/Grafana stack.

### Verification

-   **478 passed, 4 optional OpenTelemetry SDK tests skipped**.
-   One known non-blocking Starlette/AnyIO deprecation warning remains.
-   Prometheus target and Grafana dashboard provisioning were manually
    validated with Docker Compose.

This release extends operational visibility without changing the stable
public framework contracts or adding a new execution mode.

------------------------------------------------------------------------

## \[v1.0.0\] --- Stable Framework Release --- 2026-10-03

### Added

-   **Slice 1 --- Public Contracts & Compatibility:** explicit
    `app.framework` extension facade, existing class identities and
    imports preserved, public contract inventory and planned
    stable-release compatibility/deprecation policy.

-   Contract regression tests and installed-wheel facade checks in
    packaging CI.

-   **Slice 2 --- Extension Conformance:** opt-in
    `app.framework.testing` helpers for agents, stages and standard/live
    providers; deterministic external extension example,
    negative/cleanup/cancellation tests and installed-wheel example
    gate.

-   **Slice 3 --- API & Streaming Stability:** reviewed HTTP/WebSocket
    schema snapshots and CI gate, normalized HTTP error envelopes,
    recoverable invalid WebSocket events, sanitized processing errors,
    independent disconnect monitor, deterministic stream/task cleanup
    and bounded processing queues.

-   **Slice 4 --- Supported Runtime & Upgrade Guarantees:** declared
    CPython 3.12 Linux/Windows profile, runtime/CI/package consistency
    check, future SQLite schema refusal, read-only inspection and
    WAL-consistent backup command, frozen v0.5.0 storage fixtures and
    stronger restart/ownership/history checks.

-   **Slice 5 --- Stable Release Acceptance:** aligned runtime, wheel,
    images and tag workflow to 1.0.0; health/OpenAPI version smoke
    gates, tag/version agreement, streamed artifact checksums, checksum
    verification, final acceptance and tag procedure, and Architecture &
    Vision Book v1.0.0 in Markdown and Word.

This entry documents the prepared release. Publication requires the
verified commit, green CI and the `v1.0.0` tag; it does not claim that
tagging occurred.

------------------------------------------------------------------------

## \[v0.5.0\] --- Product Readiness --- Release candidate --- 2026-10-03

The six readiness slices are implemented. Final tagging follows the
release checklist and container/browser acceptance; this entry does not
announce an already published release.

### Added

-   **Slice 1 --- Persistent sessions:** SQLite repositories,
    conversation metadata, saved messages and explicit session
    lifecycle.
-   **Slice 2 --- Security Boundaries:** strict `X-Client-Id`, immutable
    persisted `owner_id`, isolation for GET/PATCH/close and
    interpretation referencing a persisted session; idempotent migration
    from Slice 1 and offline legacy owner assignment. Missing/invalid
    identity returns 401, foreign ownership 403 and missing persisted
    sessions 404; active operations on closed sessions return 409.
-   **Slice 3 --- Production Configuration & Packaging:** typed
    development/test/ production settings, liveness/readiness, Python
    wheel and installed backend command, separate hashed backend/UI
    locks, pinned Docker base, non-root service and documented
    environment variables.
-   **Slice 4 --- CI/CD & Quality Gates:** clean Windows/Linux installs,
    syntax and regression checks, optional telemetry tests, wheel
    installation outside the checkout, container build and smoke tests,
    checksums and release artefacts. Deployment remains independent of a
    cloud provider.
-   **Slice 5 --- Production Observability:** structured business events
    with request, session, execution mode, provider/model, language,
    latency, status and safe error metadata; request correlation;
    provider/session/stage metrics; available token usage and explicitly
    configured partial cost estimates; optional OpenTelemetry SDK and
    OTLP/HTTP export.
-   **Slice 6 --- Release Hardening & Governance:** opt-in cleanup of
    closed sessions older than the configurable 30-day default, offline
    dry-run/apply maintenance, shutdown budgets, restart ownership
    continuity checks, targeted secret hygiene checks, security and
    operations documentation, release checklist and updated English
    Architecture and Vision Book in `docs/books/`.

### Fixed

-   Cross-platform lock completeness, including Windows transitive
    dependencies.
-   SQLite handles are closed reliably so Windows readiness tests can
    remove the database; readiness and metrics do not recreate a missing
    database.
-   Provider telemetry retains correlation across streaming work without
    leaking context to consumers; request identifiers are independent of
    audio filenames.
-   Sensitive text, prompts, audio, credentials and raw exception
    content are excluded from business events; noisy HTTP/provider debug
    logs are suppressed.

### Compatibility and operational limits

-   Protected clients must supply a valid `X-Client-Id`. Identity is
    self-declared, not authentication: exposed deployments need a
    trusted authenticated ingress. Legacy ownerless sessions are denied
    until explicitly assigned offline.
-   Standard, Direct, Enhanced and browser device control remain
    independent. Inbound conferencing and Full Duplex remain
    experimental.
-   Persistent session state survives restart; provider calls, browser
    connections, pending realtime buffers and tasks do not. Restart does
    not close active rows.
-   Cleanup is disabled by default and preserves active sessions. Audio
    files, backups, logs and active-session expiry require separate
    retention policies.
-   Health, metrics, documentation and static audio remain separate
    unauthenticated surfaces. Multi-worker metrics, durable jobs and
    cloud deployment are outside this release scope. Cost estimates are
    not complete provider invoices.

### Verification

-   Local Slice 6 backend: **344 passed, 4 optional SDK tests skipped**,
    or **348 passed with the SDK**, with one existing deprecation
    warning.
-   Clean wheel installation, local health/ownership and native
    shutdown/restart persistence verified. Updated Windows/Linux CI and
    container smoke acceptance, manual browser checks and the final tag
    remain release checklist gates.
-   Historical audio benchmarks below are preserved; no new v0.5.0
    performance baseline is claimed.

------------------------------------------------------------------------

## \[v0.4.4\] --- Conferencing Audio & Device Control --- 2026-10-01

### Added

#### Explicit Realtime Input Selection

-   Added shared browser-side `WaaxalmaAudioInputManager`.
-   Added explicit microphone discovery and selection for Realtime
    Direct and Realtime Enhanced.
-   Added browser persistence through:

``` text
waaxalma.audioInputDeviceId
```

-   Direct and Enhanced no longer require the Windows global default
    microphone.
-   Added safe fallback to the browser default if the selected physical
    microphone disappears.

#### Independent Local Monitoring

-   Added a separate Local Monitor destination for translated audio.
-   Added browser persistence through:

``` text
waaxalma.monitorOutputDeviceId
waaxalma.monitorEnabled
```

-   Direct can play the same translated WebRTC stream to the
    conferencing output and local headphones independently.
-   Enhanced fans the existing `MediaStreamAudioDestinationNode` stream
    to independent conference and monitor sinks without changing PCM
    scheduling.
-   Standard generated audio can be mirrored to an independent monitor
    device.
-   Added same-device protection to avoid duplicate playback when
    conference and monitor sinks resolve to the same device.

#### Streamlit Audio Workspace

-   Switched the main application layout to `wide`.
-   Grouped device controls under **Audio Devices & Conferencing**.
-   Added dedicated tabs for Microphone, Conference Output, Local
    Monitor, and Conference Input.
-   Kept `st.iframe` as the embedded-client mechanism.

#### Experimental Conference Input / Inbound Translation

-   Added `WaaxalmaConferenceInputManager`.
-   Added explicit conference-input selection and persistence through:

``` text
waaxalma.conferenceInputDeviceId
```

-   Added conference-input signal diagnostics using RMS / dBFS.
-   Added an experimental inbound path that reuses the existing Enhanced
    endpoints:

``` text
POST /api/realtime/enhanced/session
WS   /api/realtime/enhanced/stream
```

-   Inbound TTS is bound to Local Monitor only and is not routed to
    Primary / Conference Output.
-   Added experimental Full Duplex Start / Stop coordination and
    fail-safe direction shutdown using same-origin browser storage.

### Improved

-   Preserved Direct reconnect and WebRTC behavior while making
    microphone selection deterministic.
-   Preserved Enhanced final-transcript authority, rolling context,
    terminology, PCM16 carry-byte continuity, ordered playback and the
    20 ms jitter buffer.
-   Removed reliance on Windows **Listen to this device** for local
    monitoring.
-   Clarified the conferencing integration boundary: Waaxalma integrates
    through standard browser audio devices rather than
    Teams/Meet/Zoom-specific SDKs.
-   Added `tools/README.md` guidance for external virtual-audio
    prerequisites without committing third-party installers.

### Release Scope

The blocking v0.4.4 product path is outbound conferencing:

``` text
Physical microphone
    → Waaxalma
    → translated audio
    → Primary / Conference Output
    → virtual audio cable
    → Teams / Meet / Zoom microphone
```

Inbound conference capture, inbound translation, and Full Duplex
coordination are included as experimental capabilities and are not
required to declare v0.4.4 released.

### Manual Validation

Validated during v0.4.4 development:

``` text
✅ explicit physical microphone selection
✅ Realtime Direct uses the selected microphone
✅ Realtime Enhanced uses the selected microphone
✅ independent Local Monitor output
✅ translated audio can reach conference output and headphones concurrently
✅ no Windows "Listen to this device" required
```

The previously validated real Microsoft Teams bridge remains the
reference outbound conferencing POC:

``` text
Waaxalma → VB-CABLE → Teams → remote participant
```

with Microsoft Edge as the validated reference browser.

### Tests

Final backend freeze regression:

``` text
216 passed
0 failed
1 known non-blocking warning
14.90 s
```

Known warning:

``` text
StarletteDeprecationWarning:
Using httpx with starlette.testclient is deprecated;
install httpx2 instead.
```

The warning is intentionally deferred beyond v0.4.4 because it does not
affect the conferencing/device-control release behavior.

### Architecture

v0.4.4 keeps execution and audio routing responsibilities separate:

``` text
Physical microphone
    ↓
AudioInputManager
    ↓
Direct / Enhanced
    ↓
translated audio
    ├── Primary / Conference Output → virtual cable → conferencing app
    └── Local Monitor               → headphones
```

Experimental inbound direction:

``` text
conferencing app
    → independent virtual path
    → ConferenceInputManager
    → Enhanced STT / Translation / TTS
    → Local Monitor
```

------------------------------------------------------------------------

## \[v0.4.3\] --- Universal Audio Output & Conferencing Bridge --- 2026-10-01

### Added

#### Universal Audio Output

-   Added shared browser-side `WaaxalmaAudioOutputManager`.
-   Added output-device discovery through
    `navigator.mediaDevices.enumerateDevices()`.
-   Added output-device routing through `HTMLMediaElement.setSinkId()`.
-   Added global Streamlit **Audio Output** selector.
-   Added output-device refresh and browser permission-aware device
    discovery.
-   Added browser-side persistence of the selected device using:

``` text
waaxalma.audioOutputDeviceId
```

#### Standard Output Routing

-   Added `standard_audio_player.html`.
-   Routed Standard interpreted-result playback through a managed
    `HTMLAudioElement`.
-   Standard generated audio can now target the same selected output
    device as realtime modes.
-   Preserved the Standard microphone/upload input path.

#### Realtime Direct Output Routing

-   Routed the translated WebRTC remote stream through a managed
    `HTMLAudioElement`.
-   Applied the selected sink to Direct translated audio.
-   Preserved Direct WebRTC session flow, transcript events, telemetry,
    reconnect behavior, microphone reuse, and cleanup semantics.

#### Realtime Enhanced Output Routing

-   Added `MediaStreamAudioDestinationNode` as the final Enhanced
    playback bridge.
-   Routed scheduled Enhanced PCM audio to a managed `HTMLAudioElement`.
-   Applied the selected sink to Enhanced translated audio.
-   Preserved PCM16 carry-byte continuity, odd-chunk handling, the 20 ms
    jitter buffer, ordered `nextPlaybackTime` scheduling,
    final-transcript authority, rolling source context, terminology, and
    per-utterance latency metrics.

#### Conferencing Bridge

-   Validated VB-Audio Virtual Cable as an application-agnostic
    conferencing bridge.

Reference mapping:

``` text
Waaxalma output
    → CABLE Input (VB-Audio Virtual Cable)
    → VB-CABLE
    → CABLE Output (VB-Audio Virtual Cable)
    → conferencing application microphone
```

-   Validated Microsoft Teams microphone input using `CABLE Output`.
-   Validated a real Teams call end-to-end with Microsoft Edge: the
    remote participant received Waaxalma translated audio.
-   Kept Teams speaker output on a physical headset / speaker device so
    incoming meeting audio remains audible locally.

### Improved

#### Streamlit Embedding

-   Replaced deprecated `st.components.v1.html` usage with `st.iframe`.
-   Kept the shared output-manager script injected into embedded Direct
    and Enhanced clients.
-   Removed temporary visible audio-routing diagnostics after
    validation.
-   Removed the temporary **Test output** diagnostic control from the
    production selector.

#### Resource Management

-   Added managed audio-element registration/unregistration.
-   Added output-device fallback when the selected device disappears.
-   Added cleanup of managed output elements during Stop / unload.
-   Kept Enhanced Web Audio context cleanup and Direct WebRTC cleanup
    independent from the shared output layer.

### Browser / Environment Notes

-   Browser audio-device permission may be required before non-default
    outputs appear in `enumerateDevices()`.
-   Microsoft Edge is the validated reference browser for the v0.4.3
    Teams bridge.
-   In the tested environment, Chrome exposed and selected `CABLE Input`
    after permission was granted, but a remote Teams participant did not
    receive the audio through the same setup.
-   Windows default recording/input should remain the physical
    microphone used by Waaxalma.
-   `CABLE Output` should be selected specifically as the conferencing
    application's microphone rather than made the Windows global default
    input.
-   Windows **Listen to this device** on `CABLE Output` should remain
    disabled during normal conferencing to avoid acoustic feedback
    loops.

### Out of Scope

-   Native Microsoft Graph / Teams calling bot integration.
-   Automatic meeting joining.
-   Inbound conference-participant audio capture.
-   Bidirectional conferencing translation.
-   Explicit Waaxalma input-device selection.
-   Separate local monitor output (`monitor_device_id`).
-   Realtime provider latency re-baselining.

### Validation

Manually validated:

``` text
Standard  → AudioOutputManager → CABLE Input → CABLE Output
Direct    → AudioOutputManager → CABLE Input → CABLE Output
Enhanced  → AudioOutputManager → CABLE Input → CABLE Output
```

Conferencing validation:

``` text
Physical microphone
    → Waaxalma
    → translated audio
    → CABLE Input
    → CABLE Output
    → Microsoft Teams microphone
    → remote participant
```

The real Teams call succeeded with Microsoft Edge.

The last full backend regression baseline remains the v0.4.2 result:

``` text
216 passed
0 failed
```

The full backend suite should be rerun immediately before creating the
Git tag.

### Architecture

v0.4.3 does not merge the three audio-generation pipelines.

``` text
Standard generated audio ─┐
Direct WebRTC audio      ─┼─→ AudioOutputManager → selected sink
Enhanced streamed PCM    ─┘
```

`AudioOutputManager` owns only the browser playback destination.

------------------------------------------------------------------------

## \[v0.4.2\] --- Realtime Enhanced Streaming --- 2026-09-30

### Added

-   Added Realtime Enhanced as a second explicit realtime execution
    mode.
-   Added `StreamingTranscriptionProvider`.
-   Added `StreamingTranslationProvider`.
-   Added `StreamingSpeechProvider`.
-   Added OpenAI streaming transcription using `gpt-live-transcribe`.
-   Added OpenAI streaming translation using `gpt-4.1-mini`.
-   Added OpenAI streaming speech using `gpt-4o-mini-tts`.
-   Added:

``` text
POST /api/realtime/enhanced/session
WS   /api/realtime/enhanced/stream
```

-   Added explicit source-language selection.
-   Added terminology / keyword hints.
-   Added live source transcript.
-   Added three-segment rolling source context.
-   Added `SpeakableTextBuffer`.
-   Added overlapping streaming translation and speech synthesis.
-   Added per-utterance latency metrics.

### Improved

-   Made the final STT transcript authoritative for translation.
-   Kept partial STT deltas for live UI feedback only.
-   Added ASR-aware translation behavior.
-   Added PCM16 carry-byte continuity for odd-sized network chunks.
-   Added ordered Web Audio scheduling.
-   Added minimum 20 ms playback jitter buffering.
-   Added approximately 320 ms local VAD silence window for utterance
    commit.
-   Hardened WebSocket disconnect handling.
-   Reduced production browser/backend logging noise.

### Performance / Observed Baseline

10-segment local warm-path sample:

  Metric                              p50        p95
  ---------------------------- ---------- ----------
  Commit → first translation     \~0.55 s   \~0.75 s
  Translation → first audio      \~0.60 s   \~0.81 s
  Commit → first audio           \~1.17 s   \~1.46 s
  TTS start → first audio        \~0.51 s   \~0.69 s

Observed values are not service-level guarantees.

### Tests

Full backend regression result:

``` text
216 passed
0 failed
```

Known non-blocking warning:

``` text
StarletteDeprecationWarning:
Using httpx with starlette.testclient is deprecated;
install httpx2 instead.
```

### Architecture

Enhanced remains separate from the standard `AgentOrchestrator` /
`SequentialPipeline` execution path.

``` text
Microphone
    ↓
Streaming STT
    ↓
Authoritative final transcript
    ↓
Rolling context + terminology
    ↓
Streaming translation
    ↓
SpeakableTextBuffer
    ↓
Streaming TTS
    ↓
PCM16 / jitter-buffered browser playback
```

------------------------------------------------------------------------

## \[v0.4.1\] --- Realtime Translation & Voice Configuration

### Added

#### Realtime Translation

-   Added `RealtimeTranslationProvider` as a provider capability
    contract.
-   Added realtime provider registration through `ProviderRegistry`.
-   Added `OpenAIRealtimeTranslationProvider`.
-   Added support for `gpt-realtime-translate`.
-   Added ephemeral realtime translation session creation.
-   Added:

``` text
POST /api/realtime/translation/session
```

-   Added browser-to-provider WebRTC connectivity.
-   Added live translated transcript streaming.
-   Added translated realtime audio playback.
-   Added Streamlit Live Translation mode alongside the existing
    Standard Interpretation mode.

#### Voice Configuration

-   Added `VoiceConfig`.
-   Added `build_voice_config()`.
-   Added configurable speech voice support for the standard speech
    pipeline.
-   Prepared realtime session contracts for provider-specific voice
    support through optional `voice_id`.

#### Realtime UI

-   Added `streamlit/realtime_client.html`.
-   Added compact realtime controls:
    -   target language;
    -   start;
    -   stop;
    -   connection state.
-   Added live translation display.
-   Added source transcript fallback when the Direct WebRTC session does
    not expose source transcript events.
-   Removed internal iframe scrolling from the Streamlit realtime view.

#### Realtime Observability

Added backend Prometheus metrics:

``` text
waaxalma_realtime_sessions_total
waaxalma_realtime_session_creation_duration_seconds
waaxalma_realtime_session_errors_total
```

Added browser-observed realtime latency metric:

``` text
waaxalma_realtime_client_latency_seconds
```

Supported client latency dimensions:

``` text
metric="session_request"
metric="webrtc_connection"
metric="speech_to_first_translation"
metric="speech_to_first_audio"
```

Common labels:

``` text
provider="openai"
model="gpt-realtime-translate"
mode="direct"
```

Added:

``` text
POST /api/realtime/metrics
```

for reporting selected browser/WebRTC metrics back to the backend.

#### Browser Latency Instrumentation

Added local browser measurements for:

``` text
session_request_ms
microphone_acquisition_ms
remote_audio_track_available_ms
webrtc_connection_ms
data_channel_open_ms
speech_start_after_connection_ms
start_to_first_translation_ms
connection_to_first_translation_ms
speech_to_first_translation_ms
provider_first_translation_elapsed_ms
speech_to_first_audio_ms
translation_to_first_audio_ms
```

Added lightweight local audio-energy detection to estimate:

-   actual source speech start;
-   first audible translated audio.

### Improved

#### Realtime Hardening

-   Added normalized realtime provider exceptions.
-   Added authentication error handling.
-   Added rate-limit handling.
-   Added provider 5xx handling.
-   Added provider timeout handling.
-   Added network request failure handling.
-   Added controlled WebRTC reconnect behavior.
-   Reconnect attempts are limited to one by default.
-   Reconnect creates a new ephemeral realtime session and never reuses
    an old client secret.
-   Active microphone stream is reused during reconnect where possible.
-   Final stop closes:
    -   realtime data channel;
    -   WebRTC peer connection;
    -   translated audio playback;
    -   microphone tracks;
    -   local audio monitoring resources.
-   Manual stop does not trigger reconnect.

#### Error Handling

Realtime provider failures are normalized into stable Waaxalma errors
such as:

``` text
REALTIME_AUTHENTICATION_FAILED
REALTIME_RATE_LIMITED
REALTIME_PROVIDER_TIMEOUT
REALTIME_PROVIDER_UNAVAILABLE
REALTIME_SESSION_FAILED
```

Example response:

``` json
{
  "detail": {
    "code": "REALTIME_RATE_LIMITED",
    "message": "Realtime translation provider rate limit exceeded.",
    "details": {
      "provider": "openai",
      "retryable": true
    }
  }
}
```

#### Static Audio Serving

-   Hardened static audio path resolution.
-   `STATIC_DIR` is now derived from `BASE_DIR` instead of depending on
    the process working directory.
-   Standard generated audio continues to be exposed through:

``` text
/static/audio/<filename>.mp3
```

#### Streamlit

-   Added separate tabs for:
    -   Standard Interpretation;
    -   Live Translation.
-   Preserved the existing standard voice interpretation workflow.
-   Standard mode was manually regression-tested after realtime
    integration with no observed regression.

### Fixed

-   Fixed JSON serialization of Pydantic validation errors containing
    `ValueError` objects by using `jsonable_encoder`.
-   Replaced deprecated FastAPI 422 constant usage with:

``` text
HTTP_422_UNPROCESSABLE_CONTENT
```

-   Fixed realtime client DOM references after source and translation
    transcript areas were split.
-   Fixed static audio 404 behavior caused by relative static directory
    resolution.
-   Fixed realtime test fixture inconsistencies introduced during
    observability work.
-   Fixed API test placement/import issues for normalized realtime
    exceptions.

### Performance / Observed Baseline

A local Realtime Direct benchmark produced:

  Metric                                  Observed latency
  ------------------------------------- ------------------
  Realtime session request                        \~1.61 s
  Microphone acquisition                          \~0.47 s
  WebRTC establishment                            \~1.84 s
  Speech → first translated text              **\~0.39 s**
  Speech → first translated audio             **\~1.35 s**
  Translation text → translated audio             \~0.96 s

This separates startup latency from actual interpretation latency.

Detailed report:

``` text
docs/realtime-latency-report-v0.4.1.md
```

### Tests

-   Added realtime provider tests.
-   Added authentication failure tests.
-   Added rate-limit tests.
-   Added provider 5xx tests.
-   Added timeout tests.
-   Added realtime service tests.
-   Added realtime API validation tests.
-   Added normalized realtime error tests.
-   Added Prometheus session metric tests.
-   Added browser metric API tests.
-   Added partial metric payload tests.
-   Added unknown metric rejection tests.
-   Added invalid latency rejection tests.
-   Added Prometheus client latency histogram tests.

Current backend test result:

``` text
109 passed
```

Known non-blocking warning:

``` text
StarletteDeprecationWarning:
Using httpx with starlette.testclient is deprecated;
install httpx2 instead.
```

This warning is intentionally left outside the scope of `v0.4.1`.

### Architecture

`v0.4.1` keeps Standard and Realtime Direct as separate execution paths.

Standard:

``` text
Agent
  ↓
Pipeline
  ↓
Stages
  ↓
Skills
  ↓
Provider Contracts
  ↓
ProviderRegistry
```

Realtime Direct:

``` text
RealtimeTranslationService
  ↓
ProviderRegistry
  ↓
RealtimeTranslationProvider
  ↓
OpenAI Realtime
  ↓
WebRTC
```

This preserves the existing `v0.4.0` framework architecture while adding
realtime as a separate provider-backed capability.

### Roadmap

#### Planned `v0.4.2` --- Realtime Enhanced Streaming

``` text
Microphone
    ↓
Streaming STT
    ↓
partial source transcript
    ↓
Context / terminology
    ↓
Streaming Translation
    ↓
partial translated text
    ↓
Streaming TTS
    ↓
translated audio
```

Objectives:

-   expose source transcript;
-   improve proper-name and terminology handling;
-   preserve contextual enrichment in realtime;
-   support configurable realtime speech output;
-   compare Direct and Enhanced modes using identical latency metrics.

Primary comparison metrics:

``` text
speech_to_first_translation
speech_to_first_audio
```

#### Planned `v0.5.0` --- Product Readiness

-   persistent sessions;
-   retention policy;
-   authentication and authorization;
-   privacy and security boundaries;
-   packaging;
-   CI/CD;
-   release automation;
-   production dashboards and alerts;
-   deployment governance.

------------------------------------------------------------------------

## \[v0.4.0\] --- Framework Next

### Added

-   `AgentRegistry`.
-   `ProviderRegistry`.
-   `PipelineRegistry`.
-   Provider capability contracts.
-   Configurable pipelines.
-   Context capability.
-   Quality capability.
-   Generic API agent execution.
-   `PassthroughContextProvider`.
-   `DeterministicQualityProvider`.

### Architecture

Framework execution model:

``` text
Generic API
    ↓
AgentOrchestrator
    ↓
AgentRegistry
    ↓
Agents
    ↓
PipelineRegistry
    ↓
Pipelines
    ↓
Stages
    ↓
Skills
    ↓
Provider Contracts
    ↓
ProviderRegistry
    ↓
Concrete Providers
```

------------------------------------------------------------------------

## \[v0.3.0\] --- Reliability

### Added

-   Input validation.
-   Async provider execution.
-   Retry policy.
-   Provider timeouts.
-   Exponential backoff.
-   Jitter.
-   Normalized errors.
-   Session tracing.
-   Agent metrics.
-   Stage metrics.
-   Provider retry metrics.
-   Reliability tests.

------------------------------------------------------------------------

## \[v0.2.0\] --- Agent Orchestration

### Added

-   Typed agent contracts.
-   `AgentOrchestrator`.
-   `SessionContext`.
-   Provider adapters.
-   Integration tests.
-   Unified text and voice execution model.

------------------------------------------------------------------------

## \[v0.1.0\] --- Prototype

### Added

-   FastAPI backend.
-   Streamlit interface.
-   Speech-to-text.
-   Translation.
-   Text-to-speech.
-   Initial voice interpretation workflow.
