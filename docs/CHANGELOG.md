# Changelog

All notable changes to **Waaxalma** are documented here.

The project follows semantic versioning where practical.

---

## [v0.4.1] — Realtime Translation & Voice Configuration

### Added

#### Realtime Translation

- Added `RealtimeTranslationProvider` as a provider capability contract.
- Added realtime provider registration through `ProviderRegistry`.
- Added `OpenAIRealtimeTranslationProvider`.
- Added support for `gpt-realtime-translate`.
- Added ephemeral realtime translation session creation.
- Added:

```text
POST /api/realtime/translation/session
```

- Added browser-to-provider WebRTC connectivity.
- Added live translated transcript streaming.
- Added translated realtime audio playback.
- Added Streamlit Live Translation mode alongside the existing Standard Interpretation mode.

#### Voice Configuration

- Added `VoiceConfig`.
- Added `build_voice_config()`.
- Added configurable speech voice support for the standard speech pipeline.
- Prepared realtime session contracts for provider-specific voice support through optional `voice_id`.

#### Realtime UI

- Added `streamlit/realtime_client.html`.
- Added compact realtime controls:
  - target language;
  - start;
  - stop;
  - connection state.
- Added live translation display.
- Added source transcript fallback when the Direct WebRTC session does not expose source transcript events.
- Removed internal iframe scrolling from the Streamlit realtime view.

#### Realtime Observability

Added backend Prometheus metrics:

```text
waaxalma_realtime_sessions_total
waaxalma_realtime_session_creation_duration_seconds
waaxalma_realtime_session_errors_total
```

Added browser-observed realtime latency metric:

```text
waaxalma_realtime_client_latency_seconds
```

Supported client latency dimensions:

```text
metric="session_request"
metric="webrtc_connection"
metric="speech_to_first_translation"
metric="speech_to_first_audio"
```

Common labels:

```text
provider="openai"
model="gpt-realtime-translate"
mode="direct"
```

Added:

```text
POST /api/realtime/metrics
```

for reporting selected browser/WebRTC metrics back to the backend.

#### Browser Latency Instrumentation

Added local browser measurements for:

```text
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

- actual source speech start;
- first audible translated audio.

### Improved

#### Realtime Hardening

- Added normalized realtime provider exceptions.
- Added authentication error handling.
- Added rate-limit handling.
- Added provider 5xx handling.
- Added provider timeout handling.
- Added network request failure handling.
- Added controlled WebRTC reconnect behavior.
- Reconnect attempts are limited to one by default.
- Reconnect creates a new ephemeral realtime session and never reuses an old client secret.
- Active microphone stream is reused during reconnect where possible.
- Final stop closes:
  - realtime data channel;
  - WebRTC peer connection;
  - translated audio playback;
  - microphone tracks;
  - local audio monitoring resources.
- Manual stop does not trigger reconnect.

#### Error Handling

Realtime provider failures are normalized into stable Waaxalma errors such as:

```text
REALTIME_AUTHENTICATION_FAILED
REALTIME_RATE_LIMITED
REALTIME_PROVIDER_TIMEOUT
REALTIME_PROVIDER_UNAVAILABLE
REALTIME_SESSION_FAILED
```

Example response:

```json
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

- Hardened static audio path resolution.
- `STATIC_DIR` is now derived from `BASE_DIR` instead of depending on the process working directory.
- Standard generated audio continues to be exposed through:

```text
/static/audio/<filename>.mp3
```

#### Streamlit

- Added separate tabs for:
  - Standard Interpretation;
  - Live Translation.
- Preserved the existing standard voice interpretation workflow.
- Standard mode was manually regression-tested after realtime integration with no observed regression.

### Fixed

- Fixed JSON serialization of Pydantic validation errors containing `ValueError` objects by using `jsonable_encoder`.
- Replaced deprecated FastAPI 422 constant usage with:

```text
HTTP_422_UNPROCESSABLE_CONTENT
```

- Fixed realtime client DOM references after source and translation transcript areas were split.
- Fixed static audio 404 behavior caused by relative static directory resolution.
- Fixed realtime test fixture inconsistencies introduced during observability work.
- Fixed API test placement/import issues for normalized realtime exceptions.

### Performance / Observed Baseline

A local Realtime Direct benchmark produced:

| Metric | Observed latency |
| --- | ---: |
| Realtime session request | ~1.61 s |
| Microphone acquisition | ~0.47 s |
| WebRTC establishment | ~1.84 s |
| Speech → first translated text | **~0.39 s** |
| Speech → first translated audio | **~1.35 s** |
| Translation text → translated audio | ~0.96 s |

This separates startup latency from actual interpretation latency.

Detailed report:

```text
docs/realtime-latency-report-v0.4.1.md
```

### Tests

- Added realtime provider tests.
- Added authentication failure tests.
- Added rate-limit tests.
- Added provider 5xx tests.
- Added timeout tests.
- Added realtime service tests.
- Added realtime API validation tests.
- Added normalized realtime error tests.
- Added Prometheus session metric tests.
- Added browser metric API tests.
- Added partial metric payload tests.
- Added unknown metric rejection tests.
- Added invalid latency rejection tests.
- Added Prometheus client latency histogram tests.

Current backend test result:

```text
109 passed
```

Known non-blocking warning:

```text
StarletteDeprecationWarning:
Using httpx with starlette.testclient is deprecated;
install httpx2 instead.
```

This warning is intentionally left outside the scope of `v0.4.1`.

### Architecture

`v0.4.1` keeps Standard and Realtime Direct as separate execution paths.

Standard:

```text
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

```text
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

This preserves the existing `v0.4.0` framework architecture while adding realtime as a separate provider-backed capability.

### Roadmap

#### Planned `v0.4.2` — Realtime Enhanced Streaming

```text
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

- expose source transcript;
- improve proper-name and terminology handling;
- preserve contextual enrichment in realtime;
- support configurable realtime speech output;
- compare Direct and Enhanced modes using identical latency metrics.

Primary comparison metrics:

```text
speech_to_first_translation
speech_to_first_audio
```

#### Planned `v0.5.0` — Product Readiness

- persistent sessions;
- retention policy;
- authentication and authorization;
- privacy and security boundaries;
- packaging;
- CI/CD;
- release automation;
- production dashboards and alerts;
- deployment governance.

---

## [v0.4.0] — Framework Next

### Added

- `AgentRegistry`.
- `ProviderRegistry`.
- `PipelineRegistry`.
- Provider capability contracts.
- Configurable pipelines.
- Context capability.
- Quality capability.
- Generic API agent execution.
- `PassthroughContextProvider`.
- `DeterministicQualityProvider`.

### Architecture

Framework execution model:

```text
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

---

## [v0.3.0] — Reliability

### Added

- Input validation.
- Async provider execution.
- Retry policy.
- Provider timeouts.
- Exponential backoff.
- Jitter.
- Normalized errors.
- Session tracing.
- Agent metrics.
- Stage metrics.
- Provider retry metrics.
- Reliability tests.

---

## [v0.2.0] — Agent Orchestration

### Added

- Typed agent contracts.
- `AgentOrchestrator`.
- `SessionContext`.
- Provider adapters.
- Integration tests.
- Unified text and voice execution model.

---

## [v0.1.0] — Prototype

### Added

- FastAPI backend.
- Streamlit interface.
- Speech-to-text.
- Translation.
- Text-to-speech.
- Initial voice interpretation workflow.
