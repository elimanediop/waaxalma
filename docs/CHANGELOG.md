# Changelog

All notable changes to Waaxalma are documented in this file.

The project follows repository milestones that map architecture changes to Git tags.

## [0.4.0] - 2026-09-22

### Added

- `AgentRegistry` as the source of truth for registered agents.
- Generic agent execution endpoint: `POST /api/agents/{agent_name}/execute`.
- Provider contracts for translation, speech, speech-to-text, context, and quality capabilities.
- `ProviderRegistry` with capability + provider-name resolution.
- Configuration-driven provider selection.
- Provider interchangeability tests using fake implementations.
- `PipelineState` and `PipelineStage` contracts.
- `SequentialPipeline` execution engine.
- `PipelineRegistry` for named workflow composition.
- `TranscriptionStage`, `ContextStage`, `TranslationStage`, `QualityStage`, and `SpeechStage`.
- Configurable text interpreter pipeline: Context → Translation → Quality → Speech.
- Configurable audio interpreter pipeline: Transcription → Context → Translation → Quality → Speech.
- `ContextAgent` and `QualityAgent` as first-class agents.
- `PassthroughContextProvider` for zero-cost context integration.
- `DeterministicQualityProvider` for structural checks without a semantic LLM evaluation call.
- Quality metadata in interpreter responses.
- Fail-fast validation for unknown configured providers and unregistered pipelines.
- Composition and architecture tests for registries, providers, pipelines, and generic API behavior.

### Changed

- `InterpreterAgent` now receives configured pipelines instead of directly orchestrating STT, translation, and speech Skills.
- Concrete provider construction is centralized in the application composition root.
- Skills depend on provider contracts rather than OpenAI-specific classes.
- Pipeline composition is centralized and reusable instead of being encoded inside agent methods.
- Translation stages can consume `enriched_text` while preserving the original `source_text`.
- Context and Quality are part of the execution trace and stage metrics.

### Preserved

- v0.3 timeout, retry, backoff, cancellation, normalized provider errors, tracing, and Prometheus behavior.
- Existing FastAPI contracts and `AgentOrchestrator` execution semantics.
- Default Context and Quality configuration introduces no additional LLM call.

### Framework principle

> Add an agent, provider, or pipeline capability without changing the API or orchestration core.

## [0.3.0]

### Added

- Audio input validation for format, MIME type, size, duration, empty content, and corrupted recordings.
- Asynchronous provider and Skill execution.
- Operation-specific provider timeouts.
- Selective retry with exponential backoff and configurable jitter.
- Normalized provider and pipeline exceptions.
- Cancellation propagation.
- Execution tracing by session and stage.
- Per-agent and per-stage Prometheus metrics.
- Provider retry metrics.
- Automated resilience and partial-failure tests.

### Changed

- OpenAI SDK retries disabled so resilience policy is owned by Waaxalma.
- Agent execution normalized through `AgentOrchestrator`.
- Failure results return `output=None` and stable error metadata.

## [0.2.0]

### Added

- `AgentOrchestrator` as the unified agent execution path.
- `SessionContext` for session-aware execution.
- Typed `AgentInput` and `AgentResult` contracts.
- Interpreter and translation agent orchestration.
- Shared execution model for text and voice flows.
- Integration tests for orchestration behavior.

## [0.1.0]

### Added

- Initial voice → translation → speech proof of concept.
- FastAPI backend.
- Streamlit interface.
- Text and voice endpoints.
- OpenAI-backed translation and speech capabilities.
