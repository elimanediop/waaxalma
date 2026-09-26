# Waaxalma

> **Speak for me.**

Waaxalma is an open-source AI Voice Agent Framework designed to enable natural multilingual communication through intelligent, composable, observable, and realtime voice agents.

Its mission is to help people communicate seamlessly across languages by combining speech recognition, translation, contextual processing, quality evaluation, speech synthesis, and low-latency realtime translation within a modular and extensible framework.

> **Current release: `v0.4.1` — Realtime Translation & Voice Configuration**

---

## ✨ Features

- 🎙️ Speech-to-Text
- 🌍 Multilingual translation
- 🔊 Text-to-Speech
- ⚡ Realtime speech translation over WebRTC
- 📝 Live translated transcript
- 🔈 Live translated audio
- 🎚️ Voice configuration foundation
- 🤖 Multi-agent architecture
- 🧩 Skills-based design
- 🔌 Provider abstraction and interchangeability
- 🗂️ Agent, provider, and pipeline registries
- 🔀 Configurable text and audio pipelines
- 🧠 Context capability
- ✅ Quality evaluation capability
- 💬 Session-aware execution
- 🔄 Unified agent orchestration
- 🌐 Generic agent execution API
- 🛡️ Audio input validation
- ⏱️ Provider timeouts
- 🔁 Selective retries with exponential backoff
- ♻️ Controlled realtime reconnect
- 🔍 Execution tracing
- 📊 Prometheus metrics
- 📈 Browser/WebRTC latency telemetry
- 🚀 FastAPI backend
- 🖥️ Streamlit client
- ✅ Automated resilience, composition, realtime, metrics, and regression tests

---

## 🏗️ Framework Architecture

### Standard execution path

```text
Clients
(Streamlit / REST API)
        │
        ▼
Generic API
(FastAPI routes, validation, error handlers)
        │
        ▼
AgentOrchestrator
        │
        ▼
AgentRegistry
        │
        ▼
Agents
        │
        ▼
PipelineRegistry
        │
        ▼
Configurable Pipelines
        │
        ▼
Pipeline Stages
(Context / STT / Translation / Quality / Speech)
        │
        ▼
Skills
        │
        ▼
Provider Contracts
        │
        ▼
ProviderRegistry
        │
        ▼
Concrete Providers
(OpenAI / passthrough / deterministic / future providers)
```

`SessionContext`, execution tracing, error normalization, resilience controls, and metrics are cross-cutting concerns shared across the standard execution path.

### Realtime Direct execution path

`v0.4.1` introduces a separate low-latency execution path for live interpretation:

```text
Microphone
    │
    ▼
Waaxalma Realtime Session API
    │
    ▼
RealtimeTranslationService
    │
    ▼
ProviderRegistry
    │
    ▼
RealtimeTranslationProvider
    │
    ▼
OpenAI gpt-realtime-translate
    │
    ▼
WebRTC
    ├── translated audio stream
    └── live translated transcript
```

Realtime Direct intentionally bypasses the standard Context and Quality stages in order to minimize latency.

This keeps the two execution models independent:

```text
Standard
Agent → Pipeline → Stage → Skill → Provider

Realtime Direct
RealtimeTranslationService → RealtimeTranslationProvider → WebRTC
```

---

## 🧩 Agent Extensibility

Agents are registered through `AgentRegistry` and executed through `AgentOrchestrator`.

The generic endpoint:

```text
POST /api/agents/{agent_name}/execute
```

contains no agent-specific routing logic. Adding a new registered agent does not require a new FastAPI route or a change to the orchestration core.

---

## 🔌 Provider Extensibility

Skills depend on provider contracts instead of concrete implementations. Providers are resolved through `ProviderRegistry` by:

```text
capability + provider name
```

Current provider mapping:

```text
translation             / openai
speech                  / openai
speech_to_text          / openai
context                 / passthrough
quality                 / deterministic
realtime_translation    / openai
```

This allows provider implementations to be swapped through configuration without modifying Skills, Agents, the API, or `AgentOrchestrator`.

---

## 🔀 Configurable Pipelines

Interpreter workflows are composed with `SequentialPipeline` and registered through `PipelineRegistry`.

### Text interpretation

```text
Context
  → Translation
  → Quality
  → Speech
```

### Audio interpretation

```text
Transcription
  → Context
  → Translation
  → Quality
  → Speech
```

Pipeline order is explicit and testable. New stages can be added without embedding orchestration logic inside `InterpreterAgent`.

---

## 🧠 Context and Quality

Context and Quality are first-class framework capabilities.

The default configuration adds **no additional LLM call**:

```dotenv
CONTEXT_PROVIDER=passthrough
QUALITY_PROVIDER=deterministic
```

`PassthroughContextProvider` preserves the original text while keeping contextual processing as a replaceable pipeline capability.

`DeterministicQualityProvider` performs structural checks without claiming semantic translation evaluation.

Example quality result:

```json
{
  "quality": {
    "accepted": true,
    "score": null,
    "issues": [],
    "metadata": {
      "evaluation": "deterministic",
      "semantic_evaluation": false,
      "target_language": "English"
    }
  }
}
```

A future semantic evaluator can replace the deterministic provider without changing the pipeline contract.

---

## 🔄 Execution Flow

### Standard audio interpretation

```text
Audio input
    │
    ▼
Audio validation
    │
    ▼
TranscriptionStage
    │
    ▼
ContextStage
    │
    ▼
TranslationStage
    │
    ▼
QualityStage
    │
    ▼
SpeechStage
    │
    ▼
Generated audio + quality metadata
```

### Standard text interpretation

```text
Text input
    │
    ▼
ContextStage
    │
    ▼
TranslationStage
    │
    ▼
QualityStage
    │
    ▼
SpeechStage
    │
    ▼
Generated audio + quality metadata
```

Each stage is independently traceable and associated with the same session and trace identifier.

### Realtime Direct translation

```text
Microphone stream
    │
    ▼
POST /api/realtime/translation/session
    │
    ▼
Ephemeral provider session
    │
    ▼
WebRTC negotiation
    │
    ▼
gpt-realtime-translate
    │
    ├── live translated transcript
    └── live translated audio
```

---

## ⚡ Realtime Translation — v0.4.1

### Session API

Create a realtime translation session:

```text
POST /api/realtime/translation/session
```

Request:

```json
{
  "target_language": "fr"
}
```

Example response:

```json
{
  "provider": "openai",
  "model": "gpt-realtime-translate",
  "target_language": "fr",
  "client_secret": "<ephemeral-secret>",
  "expires_at": null,
  "voice_id": null,
  "metadata": {
    "transport": "webrtc",
    "endpoint": "/v1/realtime/translations"
  }
}
```

The browser uses the ephemeral client secret only to establish the WebRTC connection.

### Realtime hardening

The Direct mode includes:

- normalized provider errors;
- authentication failure handling;
- provider rate-limit handling;
- provider 5xx handling;
- timeout and network failure handling;
- controlled WebRTC reconnect;
- one reconnect attempt by default;
- fresh ephemeral session on reconnect;
- no reuse of an old client secret;
- microphone reuse during reconnect when possible;
- deterministic cleanup on final stop;
- no reconnect after a manual stop.

### Realtime source transcript

The current Direct WebRTC path exposes the translated output transcript. The UI treats the source transcript as optional and displays a fallback when it is not available.

---

## 🎚️ Voice Configuration

`v0.4.1` introduces a framework-level voice configuration foundation:

```text
VoiceConfig
├── provider
└── voice_id
```

Standard TTS voice selection remains provider-configurable.

Realtime `voice_id` is optional in the session contract so future realtime providers can expose voice selection without changing the contract.

---

## 🛡️ Reliability

Waaxalma `v0.3.0` introduced the reliability layer that remains part of the `v0.4.x` framework foundation.

### Audio validation

Uploaded audio is validated before entering the standard pipeline:

- File extension and MIME type
- Empty file detection
- Maximum file size
- Maximum audio duration
- Corrupted or undecodable audio
- Temporary file cleanup

### Provider resilience

Provider calls support:

- Asynchronous execution
- Explicit operation-specific timeouts
- Selective retries for transient failures
- Exponential backoff
- Configurable jitter
- Immediate failure for non-retryable errors
- Normalized provider exceptions
- Cancellation propagation

OpenAI SDK retries are disabled so retry behavior remains centralized and predictable within Waaxalma.

### Standard error normalization

Example:

```json
{
  "detail": {
    "code": "PROVIDER_UNAVAILABLE",
    "message": "The provider is currently unavailable.",
    "details": {
      "provider": "openai",
      "operation": "speak",
      "retryable": true
    }
  }
}
```

Typical standard error codes include:

- `EMPTY_AUDIO`
- `CORRUPTED_AUDIO`
- `PROVIDER_TIMEOUT`
- `PROVIDER_UNAVAILABLE`
- `PROVIDER_RATE_LIMITED`
- `PROVIDER_REQUEST_FAILED`
- `PROVIDER_AUTHENTICATION_FAILED`
- `AGENT_TIMEOUT`
- `AGENT_EXECUTION_FAILED`

### Realtime error normalization

Typical realtime error codes include:

- `REALTIME_AUTHENTICATION_FAILED`
- `REALTIME_RATE_LIMITED`
- `REALTIME_PROVIDER_TIMEOUT`
- `REALTIME_PROVIDER_UNAVAILABLE`
- `REALTIME_SESSION_FAILED`

Example:

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

---

## 🔍 Observability

Every standard agent execution is correlated using:

- `session_id`
- `trace_id`
- Agent name
- Operation name

The standard execution path records:

- Total agent execution duration
- Per-stage duration
- Stage success or failure
- Provider retry count
- Error code and failure stage
- Context and quality stage execution

Prometheus metrics are exposed through:

```text
GET /metrics
```

### Existing framework metrics

```text
waaxalma_agent_executions_total
waaxalma_agent_duration_seconds
waaxalma_stage_executions_total
waaxalma_stage_duration_seconds
waaxalma_provider_retries_total
```

### Realtime backend metrics

```text
waaxalma_realtime_sessions_total
waaxalma_realtime_session_creation_duration_seconds
waaxalma_realtime_session_errors_total
```

### Realtime browser / QoE metrics

The browser reports selected WebRTC latency measurements back to the backend through:

```text
POST /api/realtime/metrics
```

Prometheus metric:

```text
waaxalma_realtime_client_latency_seconds
```

Supported metric labels:

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

The browser also records additional diagnostic timings in the developer console, including:

```text
microphone_acquisition_ms
remote_audio_track_available_ms
data_channel_open_ms
speech_start_after_connection_ms
start_to_first_translation_ms
connection_to_first_translation_ms
provider_first_translation_elapsed_ms
translation_to_first_audio_ms
```

A lightweight local audio-energy detector is used to estimate source speech start and first audible translated audio.

---

## 📈 Realtime Latency Baseline

A local `v0.4.1` benchmark produced:

| Metric | Observed latency |
|---|---:|
| Realtime session request | ~1.61 s |
| Microphone acquisition | ~0.47 s |
| WebRTC establishment | ~1.84 s |
| Speech → first translated text | **~0.39 s** |
| Speech → first translated audio | **~1.35 s** |
| Translation text → translated audio | ~0.96 s |

The distinction between startup latency and interpretation latency is important.

### Startup latency

```text
session creation
+ microphone acquisition
+ WebRTC establishment
```

### Interpretation latency

```text
speech start
    ↓
first translated text
    ↓
first translated audio
```

Detailed methodology and benchmark notes are kept in:

```text
docs/realtime-latency-report-v0.4.1.md
```

---

## 🚀 Current Status

### v0.4.1 — Realtime Translation & Voice Configuration

Implemented and validated:

- `RealtimeTranslationProvider`
- OpenAI realtime translation provider
- `gpt-realtime-translate`
- Ephemeral realtime sessions
- Browser WebRTC connection
- Live translated text
- Live translated audio
- Voice configuration foundation
- Controlled reconnect
- Normalized realtime errors
- Realtime Prometheus metrics
- Browser QoE metrics
- Streamlit Live Translation UI
- Standard mode regression validation
- Static audio path hardening
- `109` automated backend tests passing

The central framework principle remains:

> **Add an agent, provider, pipeline, or realtime capability without changing the API or orchestration core.**

---

## 🚀 Running the Project

### Backend

From the repository root:

```powershell
.\backend\.venv\Scripts\Activate.ps1

python -m uvicorn app.main:app `
  --reload `
  --app-dir backend
```

Or from `backend/`:

```powershell
python -m uvicorn app.main:app --reload
```

API:

```text
http://127.0.0.1:8000
```

API documentation:

```text
http://127.0.0.1:8000/docs
```

Prometheus metrics:

```text
http://127.0.0.1:8000/metrics
```

### Streamlit client

From the repository root:

```powershell
.\backend\.venv\Scripts\Activate.ps1

python -m streamlit run streamlit/streamlit_app.py
```

The UI exposes:

```text
🎙️ Interpretation
⚡ Live Translation
```

---

## ✅ Running the Tests

From the `backend` directory:

```powershell
python -m pytest -q
```

Current `v0.4.1` result:

```text
109 passed
```

Known non-blocking warning:

```text
StarletteDeprecationWarning:
Using httpx with starlette.testclient is deprecated;
install httpx2 instead.
```

The warning is intentionally outside the `v0.4.1` scope.

Run resilience tests:

```powershell
python -m pytest tests/resilience -v
```

Run interpreter pipeline tests:

```powershell
python -m pytest tests/agents/test_interpreter_pipeline.py -v
```

Run pipeline tests:

```powershell
python -m pytest tests/pipelines -v
```

Run framework composition tests:

```powershell
python -m pytest tests/bootstrap/test_provider_composition.py -v
```

Run realtime API tests:

```powershell
python -m pytest tests/api/test_realtime_api.py -v
```

---

## ⚙️ Configuration

### Provider selection

```dotenv
TRANSLATION_PROVIDER=openai
SPEECH_PROVIDER=openai
SPEECH_TO_TEXT_PROVIDER=openai
CONTEXT_PROVIDER=passthrough
QUALITY_PROVIDER=deterministic

REALTIME_TRANSLATION_PROVIDER=openai
REALTIME_TRANSLATION_MODEL=gpt-realtime-translate
```

### OpenAI models

```dotenv
OPENAI_API_KEY=<your-openai-api-key>

OPENAI_TRANSLATION_MODEL=gpt-4.1-mini
OPENAI_TRANSCRIPTION_MODEL=gpt-4o-transcribe
OPENAI_TTS_MODEL=gpt-4o-mini-tts
OPENAI_TTS_VOICE=coral
```

### Reliability configuration

```dotenv
STT_TIMEOUT_SECONDS=30
TRANSLATION_TIMEOUT_SECONDS=20
TTS_TIMEOUT_SECONDS=30

PROVIDER_MAX_ATTEMPTS=3
PROVIDER_INITIAL_BACKOFF_SECONDS=0.5
PROVIDER_BACKOFF_MULTIPLIER=2.0
PROVIDER_MAX_BACKOFF_SECONDS=4.0
PROVIDER_JITTER_RATIO=0.2
```

Secrets such as provider API keys must be stored in a local `.env` file and must not be committed to Git.

Static generated audio is stored under:

```text
backend/static/audio/
```

and exposed through:

```text
/static/audio/<filename>.mp3
```

---

## 📚 Documentation

Project documentation is available in the `docs/` directory.

It includes:

- Architecture & Vision Book
- Technical roadmap
- Version-aligned milestones
- Architecture Decision Records
- Agent, pipeline, and provider design documentation
- Realtime latency report

Realtime performance report:

```text
docs/realtime-latency-report-v0.4.1.md
```

---

## 🗺️ Roadmap

| Repository Version | Milestone | Focus | Status |
|---|---|---|---|
| **v0.1.0** | Prototype | Voice → Translation → Speech proof of concept | Released |
| **v0.2.0** | Agent Orchestration | Unified execution, `AgentOrchestrator`, `SessionContext`, agent contracts | Released |
| **v0.3.0** | Reliability | Validation, async execution, retries, timeouts, tracing, metrics | Released |
| **v0.4.0** | Framework Next | Registries, interchangeable providers, configurable pipelines, Context & Quality | Released |
| **v0.4.1** | Realtime Translation & Voice Configuration | WebRTC Direct translation, voice configuration, realtime hardening and observability | Current |
| **v0.4.2** | Realtime Enhanced Streaming | Streaming STT → Context → Translation → streaming TTS | Next |
| **v0.5.0** | Product Readiness | Persistent sessions, security, packaging, CI/CD, production observability | Planned |
| **v1.0.0** | Stable Framework | Production-ready open-source voice agent framework | Target |

### v0.4.2 — Realtime Enhanced Streaming

Planned:

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
- improve proper-name and domain terminology handling;
- preserve contextual enrichment in realtime;
- support configurable realtime speech output;
- benchmark Direct vs Enhanced with the same latency metrics.

Primary comparison metrics:

```text
speech_to_first_translation
speech_to_first_audio
```

### v0.5.0 — Product Readiness

Planned:

- Persistent sessions
- Explicit retention policies
- Authentication and authorization
- Security and privacy boundaries
- Packaging
- CI/CD
- Release automation
- Production dashboards and alerts
- Deployment governance

---

## 🖥️ Interface

The Streamlit interface provides both Standard Interpretation and Live Translation.

Existing project screenshot:

```markdown
![Waaxalma Streamlit interface](streamlit/image.png)
```

A dedicated realtime screenshot can be added later without changing the README structure.

---

## 🤝 Contributing

Waaxalma is under active development.

Contributions related to agents, providers, pipelines, multilingual support, realtime translation, testing, observability, documentation, and developer experience are welcome.

Before submitting a change:

```powershell
python -m pytest -q
```

Please ensure that new agent, provider, stage, pipeline, realtime, or observability behavior includes appropriate automated tests.

---

## 📄 License

Licensed under the Apache License 2.0.
