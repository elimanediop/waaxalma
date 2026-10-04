# v1.0.0 Slice 1 — Public Contracts & Compatibility

Status: implemented on the v0.5.0 baseline, awaiting the remaining v1.0.0
slices and final acceptance. Package/image versions remain 0.5.0 until the
release preparation slice changes them together. This is not a v1.0.0 release.

## Public imports

Extension authors should import contracts from `app.framework`. These are
re-exports of existing classes, not wrappers or duplicate models. Original
module imports remain available; instances, subclasses and Pydantic models
have the same identity through either import path.

| Surface | Public exports |
| --- | --- |
| Agents | `BaseAgent`, `AgentInput`, `AgentResult`, `SessionContext` |
| Tracing | `ExecutionTrace`, `StageTrace` |
| Pipelines | `Pipeline`, `PipelineStage`, `PipelineState`, `SequentialPipeline` |
| Discovery | `AgentRegistry`, `PipelineRegistry`, `ProviderRegistry` |
| Standard providers | `TranslationProvider`, `SpeechProvider`, `SpeechToTextProvider` |
| Live providers | `RealtimeTranslationProvider`, `StreamingTranscriptionProvider`, `StreamingTranslationProvider`, `StreamingSpeechProvider` |
| Live values | `RealtimeTranslationSession`, `StreamingTranscriptionSession`, `StreamingTranslationChunk`, `StreamingSpeechChunk` |

Importing `app.framework` needs no API key, valid `APP_ENV`, application startup,
SQLite initialization or provider client. Only the package's model dependencies
are needed. Application composition remains explicit and outside this facade.

## Calling conventions

`BaseAgent` is an abstract base class: implement `name` and
`async execute(agent_input, context) -> AgentResult`. `info()` is optional to
override. Names identify implementations in their registry. Keep names stable
and non-empty. Agent input carries `operation`, `payload` and `metadata`;
extension-specific payload validation belongs to the agent.

`AgentResult` carries `success`, optional `output`, `error_code`, `error_message`,
`duration_ms`, and `metadata`. A successful agent should return its output;
a failed agent should supply an error code/message. These are authoring
conventions, not newly enforced Pydantic invariants. The generic HTTP execution
route currently returns the agent output, not this internal result envelope.

`SessionContext` is an execution context with a generated ID, UTC creation time,
language preferences, mutable data/metadata and a trace. It is not a persisted
conversation or proof of ownership. HTTP identity and persisted session access
continue to use the existing `X-Client-Id` boundary.

Provider and pipeline interfaces are structural `typing.Protocol` contracts:
inheritance is optional, and they are not runtime `isinstance` validators.

| Contract | Operation |
| --- | --- |
| Translation | `await translate(text, target_language) -> str` |
| Speech | `await speak(text, output_filename) -> None` |
| Transcription | `await transcribe(audio_path) -> str` |
| Realtime translation | `await create_session(*, target_language)` |
| Streaming transcription | `await create_session(*, languages=None, prompt=None, keywords=None, delay="low")` |
| Streaming translation | `translate_stream(*, text, target_language, context=None, terminology=None)` returns an async iterator |
| Streaming speech | `speak_stream(*, text, voice_id, instructions=None)` returns an async iterator |
| Pipeline/stage | `await execute(state, context) -> PipelineState` |

Every provider exposes `name`; live providers also expose `model`. Streaming
methods return async iterators directly: consume with `async for`, without
awaiting the iterator itself. Chunk boundaries are provider-specific; a final
chunk may have an empty payload. Session client secrets are sensitive values
and must not be logged.

`SequentialPipeline(name=..., stages=...)` awaits stages in order, passing each
returned state to the next stage. It rejects blank names and empty stage lists.
Errors and cancellation propagate; it introduces no retries or error mapping.
`PipelineState.require(key)` raises `ValueError` for a missing key;
`to_dict()` returns a shallow copy. State keys are agreed between composed
stages, not a global schema.

Registry registration rejects duplicates. `AgentRegistry.find()` returns
`None` on a miss; pipeline/provider `get()` raises `KeyError`. Discovery lists
are sorted. Provider keys are `(capability, name)`; the registry does not
validate a provider against a protocol. There is no automatic plugin loading
or new global registry in this slice.

## Compatibility policy for the stable release

Once v1.0.0 is accepted, the documented facade exports, required method
parameters, return contracts and documented behavior form the extension API.
Patch releases fix bugs compatibly. Minor releases can add optional features
and new exports, while preserving existing calls. Removing an export, changing
a required parameter or breaking a return contract requires a major release.
Consumers should tolerate new metadata keys and optional features.

A future deprecation must name its replacement and removal version in the
changelog and migration guide. When executable deprecated behavior is used,
emit an appropriate `DeprecationWarning` with a caller-facing stack level.
Removal occurs in a later major release, following at least one documented
minor-release transition. This slice adds no import-time warnings and removes
no existing import.

The old synchronous ABCs in `app.providers.base_provider` are legacy interfaces,
not the async extension API. They remain available for compatibility, but are
not exported by `app.framework`; migrate implementations to the async protocols
explicitly. No implicit sync-to-async adapter is provided.

Internal bootstrap/container wiring, concrete providers, API routers, skills,
settings internals, implementation-specific pipeline keys and the duplicate
legacy `app/models.py` file are outside this guarantee. Persistence repositories
are also outside this slice's stable surface: retention/count operations must
be formalized before promising a third-party repository contract. HTTP and
WebSocket schema/lifecycle guarantees are addressed in Slice 3.

## Validation and remaining slices

The compatibility suite runs with backend regression tests on Linux and
Windows. It checks all export identities, async/iterator calling conventions,
model defaults and importing without application configuration. Packaging CI
also imports the facade from the installed wheel outside the source tree and
checks that the facade is present in the artifact.

Slice 2 implements extension conformance tests and external examples; see
`extension-conformance.md` for the opt-in `app.framework.testing` namespace. Slice 3 fixes
API/streaming guarantees, Slice 4 defines runtime/upgrade support, and Slice 5
completes stable-release acceptance. No deployment platform is introduced.
