# Waaxalma

> **Speak for me.**

Waaxalma is an open-source AI Voice Agent Framework designed to enable natural multilingual communication through intelligent, composable, and observable voice agents.

Its mission is to help people communicate seamlessly across languages by combining speech recognition, translation, contextual processing, quality evaluation, and speech synthesis within a modular and extensible framework.

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
- 🛡️ Audio input validation
- ⏱️ Provider timeouts
- 🔁 Selective retries with exponential backoff
- 🔍 Execution tracing
- 📊 Prometheus metrics
- 🚀 FastAPI backend
- 🖥️ Streamlit client
- ✅ Automated resilience, composition, and framework tests

---

## 🏗️ Framework Architecture

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

`SessionContext`, execution tracing, error normalization, resilience controls, and metrics are cross-cutting concerns shared across the execution path.

### Agent extensibility

Agents are registered through `AgentRegistry` and executed through `AgentOrchestrator`.

The generic endpoint:

```text
POST /api/agents/{agent_name}/execute
```

contains no agent-specific routing logic. Adding a new registered agent does not require a new FastAPI route or a change to the orchestration core.

### Provider extensibility

Skills depend on provider contracts instead of concrete implementations. Providers are resolved through `ProviderRegistry` by:

```text
capability + provider name
```

Default v0.4 provider mapping:

```text
translation      / openai
speech           / openai
speech_to_text   / openai
context          / passthrough
quality          / deterministic
```

This allows a provider implementation to be swapped through configuration without modifying the Skill, Agent, API, or `AgentOrchestrator`.

### Configurable pipelines

Interpreter workflows are composed with `SequentialPipeline` and registered through `PipelineRegistry`.

Text interpretation:

```text
Context
  → Translation
  → Quality
  → Speech
```

Audio interpretation:

```text
Transcription
  → Context
  → Translation
  → Quality
  → Speech
```

Pipeline order is explicit and testable. New stages can be added without embedding orchestration logic inside `InterpreterAgent`.

### Context and Quality

v0.4 introduces Context and Quality as first-class framework capabilities.

The default configuration adds **no additional LLM call**:

```dotenv
CONTEXT_PROVIDER=passthrough
QUALITY_PROVIDER=deterministic
```

`PassthroughContextProvider` preserves the original text while keeping contextual processing as a replaceable pipeline capability.

`DeterministicQualityProvider` performs structural checks without claiming semantic translation evaluation. The quality result is exposed in interpreter responses:

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

### Audio interpretation

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

### Text interpretation

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

---

## 🛡️ Reliability

Waaxalma v0.3.0 introduced the reliability layer that remains part of the v0.4 framework foundation.

### Audio validation

Uploaded audio is validated before entering the agent pipeline:

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

### Error normalization

Pipeline and provider errors are returned through a consistent API contract:

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

Every agent execution is correlated using:

- `session_id`
- `trace_id`
- Agent name
- Operation name

The execution path records:

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

Available metrics include:

```text
waaxalma_agent_executions_total
waaxalma_agent_duration_seconds
waaxalma_stage_executions_total
waaxalma_stage_duration_seconds
waaxalma_provider_retries_total
```

---

## 🚀 Current Status

### v0.4.0 — Framework Next

The framework extensibility milestone is complete.

Implemented and validated:

- `AgentRegistry` as the source of truth for agents
- Generic agent execution API
- Provider contracts based on structural typing
- `ProviderRegistry` with capability + provider-name resolution
- Configuration-driven provider selection
- Interchangeable provider implementations
- `PipelineState` and `PipelineStage` contracts
- `SequentialPipeline`
- `PipelineRegistry`
- Configurable text and audio interpreter pipelines
- `ContextAgent` and `QualityAgent`
- `ContextStage` and `QualityStage`
- `PassthroughContextProvider`
- `DeterministicQualityProvider`
- Quality information exposed in interpreter responses
- Fail-fast behavior for unknown providers and pipelines
- Framework composition tests preserving v0.3 reliability behavior

The central v0.4 principle is:

> **Add an agent, provider, or pipeline capability without changing the API or orchestration core.**

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

---

## ✅ Running the Tests

From the `backend` directory:

```powershell
python -m pytest -q
```

Run resilience tests only:

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

---

## ⚙️ Configuration

### Provider selection

```dotenv
TRANSLATION_PROVIDER=openai
SPEECH_PROVIDER=openai
SPEECH_TO_TEXT_PROVIDER=openai
CONTEXT_PROVIDER=passthrough
QUALITY_PROVIDER=deterministic
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

---

## 📚 Documentation

Project documentation is available in the `docs/` directory.

It includes:

- Architecture & Vision Book
- Technical roadmap
- Version-aligned milestones
- Architecture Decision Records
- Agent, pipeline, and provider design documentation

---

## 🗺️ Roadmap

| Repository Version | Milestone | Focus | Status |
|---|---|---|---|
| **v0.1.0** | Prototype | Voice → Translation → Speech proof of concept | Released |
| **v0.2.0** | Agent Orchestration | Unified execution, `AgentOrchestrator`, `SessionContext`, agent contracts | Released |
| **v0.3.0** | Reliability | Validation, async execution, retries, timeouts, tracing, metrics | Released |
| **v0.4.0** | Framework Next | Registries, interchangeable providers, configurable pipelines, Context & Quality | Current |
| **v0.5.0** | Product Readiness | Persistent sessions, security, packaging, CI/CD, production observability | Next |
| **v1.0.0** | Stable Framework | Production-ready open-source voice agent framework | Target |

---

## 🖥️ Interface

### v0.1.0 — Streamlit prototype

![Waaxalma Streamlit interface](streamlit/image.png)

---

## 🤝 Contributing

Waaxalma is under active development.

Contributions related to agents, providers, pipelines, multilingual support, testing, observability, documentation, and developer experience are welcome.

Before submitting a change:

```powershell
python -m pytest -q
```

Please ensure that new agent, provider, stage, or pipeline behavior includes appropriate automated tests.

---

## 📄 License

Licensed under the Apache License 2.0.
