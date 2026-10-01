# Waaxalma

> **Speak for me.**

Waaxalma is an open-source **AI Voice Agent Framework** for natural multilingual communication through intelligent, composable, observable, and provider-independent voice agents.

Its mission is to help people communicate across languages by combining speech recognition, translation, contextual processing, quality evaluation, and speech synthesis within a modular framework.

---

## ✨ Highlights — v0.4.2

Waaxalma v0.4.2 adds **Realtime Enhanced Streaming** while preserving the existing standard interpreter pipelines and the v0.4.1 **Realtime Direct** mode.

The framework now exposes three execution models:

```text
Standard
  Request / response
  Configurable pipelines
  Context + Quality stages

Realtime Direct
  Provider-native realtime translation
  Optimized for low latency

Realtime Enhanced
  Streaming STT
    → authoritative final transcript
    → terminology + rolling context
    → streaming translation
    → incremental TTS
    → jitter-buffered audio playback
```

The architectural principle remains unchanged:

> **Add an agent, provider, pipeline, or realtime capability without changing the API or orchestration core.**

---

## ✨ Features

- 🎙️ Speech-to-Text
- 🌍 Multilingual translation
- 🔊 Text-to-Speech
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
- ⚡ Realtime Direct translation over WebRTC
- 🎛️ Realtime Enhanced streaming mode
- 📝 Live source transcript
- 🧭 Explicit source-language selection
- 📚 Terminology / keyword hints
- 🧠 Rolling realtime source context
- 🔄 Streaming translation
- 🗣️ Streaming TTS
- 🎚️ Configurable realtime voice
- 🔉 PCM16 continuity handling
- 📦 20 ms client playback jitter buffer
- 🎤 Local VAD-based utterance commit
- 🛡️ Audio input validation
- ⏱️ Provider timeouts
- 🔁 Selective retries with exponential backoff
- 🔍 Execution tracing
- 📊 Prometheus metrics
- 📈 Realtime latency measurements
- 🚀 FastAPI backend
- 🖥️ Streamlit client
- ✅ Automated resilience, composition, realtime, and regression tests

---

## 🏗️ Framework Architecture

The standard framework path remains registry- and contract-driven:

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

Realtime sessions are intentionally kept outside `AgentOrchestrator` and `SequentialPipeline` because they are long-lived, streaming, and transport-aware.

---

## 🤖 Agent Extensibility

Agents are registered through `AgentRegistry` and executed through `AgentOrchestrator`.

The generic endpoint:

```text
POST /api/agents/{agent_name}/execute
```

contains no agent-specific routing logic.

Adding a registered agent does not require a new FastAPI route or a change to the orchestration core.

---

## 🔌 Provider Extensibility

Providers are resolved through `ProviderRegistry` by:

```text
capability + provider name
```

Default v0.4.2 provider mapping:

```text
translation               / openai
speech                    / openai
speech_to_text            / openai
context                   / passthrough
quality                   / deterministic

realtime_translation      / openai

streaming_transcription   / openai
streaming_translation     / openai
streaming_speech          / openai
```

This allows provider implementations to be replaced without modifying the API, agent, pipeline orchestration, or provider-independent service contracts.

---

## 🔀 Standard Interpreter Pipelines

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

Pipeline order is explicit and testable.

New stages can be introduced without embedding orchestration logic inside `InterpreterAgent`.

---

## 🧠 Context and Quality

Context and Quality remain first-class capabilities for standard interpreter pipelines.

The default configuration adds **no additional LLM call**:

```dotenv
CONTEXT_PROVIDER=passthrough
QUALITY_PROVIDER=deterministic
```

`PassthroughContextProvider` preserves the source text while keeping contextual enrichment as a replaceable capability.

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

Realtime modes use different context strategies:

```text
Standard
  ContextStage + QualityStage

Realtime Direct
  bypasses standard Context / Quality
  to minimize provider-native latency

Realtime Enhanced
  terminology + rolling source context
  applied inside the streaming runtime
```

Enhanced does not add a semantic quality-evaluation LLM call in v0.4.2.

---

# ⚡ Realtime Translation

Waaxalma exposes two explicit realtime modes.

---

## Realtime Direct — v0.4.1+

Realtime Direct is the provider-native low-latency path.

```text
Microphone
    ↓
Realtime Session API
    ↓
RealtimeTranslationService
    ↓
ProviderRegistry
    ↓
RealtimeTranslationProvider
    ↓
Provider WebRTC session
    ↓
Translated transcript
    +
Translated audio
```

Primary backend endpoint:

```text
POST /api/realtime/translation/session
```

The backend creates a short-lived provider session and returns an ephemeral client secret.

The browser then negotiates WebRTC directly with the realtime provider.

Realtime Direct deliberately bypasses the standard Context and Quality stages.

---

## Realtime Enhanced — v0.4.2

Realtime Enhanced decomposes realtime interpretation into explicit streaming capabilities.

```text
Microphone
    ↓
WebRTC Streaming STT
    ↓
Partial transcript ─────────────► Live source UI
    ↓
Authoritative final STT transcript
    ↓
RealtimeEnhancedProcessor
    ↓
Terminology + rolling source context
    ↓
StreamingTranslationProvider
    ↓
Translated text deltas ─────────► Live translation UI
    ↓
SpeakableTextBuffer
    ↓
StreamingSpeechProvider
    ↓
PCM16 streaming audio
    ↓
20 ms jitter buffer
    ↓
Translated audio
```

Backend interfaces:

```text
POST /api/realtime/enhanced/session
WS   /api/realtime/enhanced/stream
```

### Enhanced session responsibilities

The session runtime keeps:

- target language;
- optional source language;
- terminology;
- session identifier;
- pending transcript state;
- three previous committed source segments as rolling context.

### Final transcript authority

Partial transcription events are useful for live UI feedback, but they are not treated as the translation source of truth.

```text
partial STT deltas
        ↓
live source UI

final STT transcript
        ↓
authoritative committed source text
        ↓
translation
```

This avoids translating an imperfect reconstruction of incremental deltas.

### Rolling context

The previous three final source segments are retained as **reference-only context**.

They help disambiguate short utterances but are not translated again.

### Terminology

Enhanced supports explicit terminology / keyword hints for names, product terms, and domain vocabulary.

Example:

```text
Waaxalma, Enhanced, Direct, transcript, terminology
```

Terminology is used to improve both recognition and translation consistency.

### Streaming speech

Translated text is passed incrementally to `SpeakableTextBuffer`.

Speakable segments are sent to TTS as soon as they are ready, allowing translation and speech generation to overlap.

### Audio playback hardening

Enhanced playback includes:

- PCM16 byte continuity across provider chunks;
- carry-byte handling for odd-sized network chunks;
- 24 kHz PCM playback;
- ordered Web Audio scheduling;
- minimum 20 ms playback jitter buffering.

---

## 🎤 Turn Detection

Enhanced currently uses a lightweight browser-side RMS voice activity detector.

The configured silence window is approximately:

```text
16 frames × 20 ms ≈ 320 ms
```

This is a latency / segmentation compromise, not a semantic endpoint detector.

The VAD triggers the transcription audio commit for each utterance.

---

## 🎚️ Realtime Voice Configuration

Enhanced uses configurable streaming speech settings.

Example:

```dotenv
STREAMING_SPEECH_PROVIDER=openai
STREAMING_SPEECH_MODEL=gpt-4o-mini-tts
STREAMING_SPEECH_VOICE=coral
```

Realtime Direct keeps provider-specific realtime voice behavior.

---

## 🛡️ Reliability

Waaxalma v0.3.0 introduced the reliability layer that remains part of the v0.4.x framework foundation.

### Audio validation

Uploaded audio is validated before entering the standard agent pipeline:

- file extension and MIME type;
- empty file detection;
- maximum file size;
- maximum audio duration;
- corrupted or undecodable audio;
- temporary file cleanup.

### Provider resilience

Provider calls support, where appropriate:

- asynchronous execution;
- explicit operation-specific timeouts;
- selective retries for transient failures;
- exponential backoff;
- configurable jitter;
- immediate failure for non-retryable errors;
- normalized provider exceptions;
- cancellation propagation.

OpenAI SDK retries are disabled for standard provider calls so retry behavior remains centralized and predictable within Waaxalma.

### Realtime hardening

Realtime behavior additionally includes:

- ephemeral provider credentials;
- normalized session-creation failures;
- controlled Direct reconnect behavior;
- WebSocket disconnect handling;
- clean Stop / resource teardown;
- browser logging quiet by default;
- detailed internal timing available at debug level.

---

## ⚠️ Error Normalization

Pipeline and provider errors use a consistent API contract.

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

Typical error codes include:

- `EMPTY_AUDIO`
- `CORRUPTED_AUDIO`
- `PROVIDER_TIMEOUT`
- `PROVIDER_UNAVAILABLE`
- `PROVIDER_RATE_LIMITED`
- `PROVIDER_REQUEST_FAILED`
- `PROVIDER_AUTHENTICATION_FAILED`
- `AGENT_TIMEOUT`
- `AGENT_EXECUTION_FAILED`

---

## 🔍 Observability

Prometheus metrics are exposed through:

```text
GET /metrics
```

Standard execution metrics include:

```text
waaxalma_agent_executions_total
waaxalma_agent_duration_seconds
waaxalma_stage_executions_total
waaxalma_stage_duration_seconds
waaxalma_provider_retries_total
```

Realtime metrics include:

```text
waaxalma_realtime_sessions_total
waaxalma_realtime_session_creation_duration_seconds
waaxalma_realtime_session_errors_total
waaxalma_realtime_client_latency_seconds
```

Enhanced additionally records processor-level latency checkpoints such as:

```text
commit → first translation
commit → first speakable text
commit → TTS start
commit → first audio
TTS start → first audio
translation → first audio
```

Browser Enhanced metrics are tracked per utterance.

---

## 📈 Realtime Performance Baselines

These are observed local benchmark results, not service-level guarantees.

### Realtime Direct baseline

```text
Realtime session request            ~1.61 s
Microphone acquisition              ~0.47 s
WebRTC establishment                ~1.84 s

Speech → first translated text      ~0.39 s
Speech → first translated audio     ~1.35 s
Translation → translated audio      ~0.96 s
```

### Realtime Enhanced warm-path benchmark

Measured over a 10-segment local sample:

| Metric | p50 | p95 |
|---|---:|---:|
| Commit → first translation | ~0.55 s | ~0.75 s |
| Translation → first audio | ~0.60 s | ~0.81 s |
| Commit → first audio | ~1.17 s | ~1.46 s |
| TTS start → first audio | ~0.51 s | ~0.69 s |

Provider response latency can vary between requests.

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

Or from the `backend` directory:

```powershell
python -m uvicorn app.main:app --reload
```

The API is available at:

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

The realtime interface lets the user choose:

```text
Direct
Enhanced
```

Enhanced additionally exposes:

```text
Source language
Target language
Terminology
Source transcript
Translation
Realtime latency measurements
```

---

## ⚙️ Configuration

Provider credentials should be stored in a local `.env` file and must not be committed to Git.

### Standard provider selection

```dotenv
TRANSLATION_PROVIDER=openai
SPEECH_PROVIDER=openai
SPEECH_TO_TEXT_PROVIDER=openai
CONTEXT_PROVIDER=passthrough
QUALITY_PROVIDER=deterministic
```

### Realtime Direct

```dotenv
REALTIME_TRANSLATION_PROVIDER=openai
REALTIME_TRANSLATION_MODEL=gpt-realtime-translate
```

### Realtime Enhanced

```dotenv
STREAMING_TRANSCRIPTION_PROVIDER=openai
STREAMING_TRANSCRIPTION_MODEL=gpt-live-transcribe

STREAMING_TRANSLATION_PROVIDER=openai
STREAMING_TRANSLATION_MODEL=gpt-4.1-mini

STREAMING_SPEECH_PROVIDER=openai
STREAMING_SPEECH_MODEL=gpt-4o-mini-tts
STREAMING_SPEECH_VOICE=coral
```

---

## ✅ Running the Tests

From the `backend` directory:

```powershell
python -m pytest -q
```

Current v0.4.2 regression status:

```text
216 passed
0 failed
```

A known non-blocking Starlette `TestClient` / `httpx` deprecation warning remains outside the v0.4.2 scope.

Focused test examples:

```powershell
python -m pytest tests/resilience -v
python -m pytest tests/pipelines -v
python -m pytest tests/bootstrap/test_provider_composition.py -v
python -m pytest tests/providers/test_openai_streaming_translation_provider.py -q
python -m pytest tests/services/test_realtime_enhanced_processor_context.py -q
```

---

## 🚀 Current Status

### v0.4.2 — Realtime Enhanced Streaming

Implemented and validated:

- Realtime Direct retained as the provider-native latency path;
- Realtime Enhanced added as a controllable streaming path;
- streaming STT provider contract;
- explicit source-language selection;
- terminology and keyword hints;
- final STT transcript as authoritative translation input;
- three-segment rolling source context;
- ASR-aware streaming translation;
- streaming speech provider contract;
- concurrent translation and TTS;
- speakable-text buffering;
- PCM16 carry-byte continuity;
- 20 ms browser playback jitter buffer;
- ~320 ms local VAD silence window;
- per-utterance browser latency measurements;
- WebSocket disconnect hardening;
- production logging cleanup;
- dedicated final-transcript / rolling-context regression tests;
- full backend regression suite passing with **216 tests**.

---

## 📚 Documentation

Project documentation is available in the `docs/` directory.

It includes:

- Architecture & Vision Book;
- technical roadmap;
- version-aligned milestones;
- Architecture Decision Records;
- agent, pipeline, provider, and realtime design documentation.

The v0.4.2 Architecture & Vision Book documents the standard framework, Realtime Direct, and Realtime Enhanced execution models.

---

## 🗺️ Roadmap

| Repository Version | Milestone | Focus | Status |
|---|---|---|---|
| **v0.1.0** | Prototype | Voice → Translation → Speech proof of concept | Released |
| **v0.2.0** | Agent Orchestration | Unified execution, `AgentOrchestrator`, `SessionContext`, agent contracts | Released |
| **v0.3.0** | Reliability | Validation, async execution, retries, timeouts, tracing, metrics | Released |
| **v0.4.0** | Framework Next | Registries, interchangeable providers, configurable pipelines, Context & Quality | Released |
| **v0.4.1** | Realtime Translation & Voice Configuration | Realtime Direct, WebRTC, voice configuration, realtime observability | Released |
| **v0.4.2** | Realtime Enhanced Streaming | Streaming STT → context / terminology → translation → streaming TTS | Current |
| **v0.4.3** | Virtual Audio Output & Conferencing Bridge | Route translated audio to selectable / virtual audio outputs for conferencing tools | Next |
| **v0.5.0** | Product Readiness | Persistent sessions, security, packaging, CI/CD, production observability | Planned |
| **v1.0.0** | Stable Framework | Production-ready open-source voice agent framework | Target |

---

## 🖥️ Interface

The Streamlit interface provides:

```text
Standard Interpretation
Live Translation
    ├── Direct
    └── Enhanced
```

Existing project screenshot:

```markdown
![Waaxalma Streamlit interface](streamlit/image.png)
```

A dedicated realtime screenshot can be added without changing the README structure.

---

## 🤝 Contributing

Waaxalma is under active development.

Contributions related to agents, providers, pipelines, multilingual support, realtime translation, speech processing, testing, observability, documentation, and developer experience are welcome.

Before submitting a change:

```powershell
python -m pytest -q
```

New agent, provider, stage, pipeline, realtime, or observability behavior should include appropriate automated tests.

---

## 📄 License

Licensed under the Apache License 2.0.
