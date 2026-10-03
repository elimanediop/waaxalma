# v1.0.0 Slice 2 — Extension Conformance

## Scope

`app.framework.testing` provides opt-in, pytest-independent checks for extension
authors. Importing the module does not start the service or construct clients.
Registration and application execution are unchanged. Helpers raise
`ConformanceError` (an `AssertionError` subclass) for invalid contract results.
They execute the supplied sample; provider exceptions and cancellation propagate.

| Helper | Sample result checked |
| --- | --- |
| `assert_agent_conformance(agent, agent_input, context)` | `BaseAgent` instance, non-empty name, awaitable execute, `AgentResult` |
| `assert_stage_conformance(stage, state, context)` | Name, keyword state/context invocation, `PipelineState` |
| `assert_translation_provider_conformance(provider, *, text, target_language)` | Name, awaitable translate, string |
| `assert_speech_provider_conformance(provider, *, text, output_filename)` | Name, awaitable speak, `None` |
| `assert_transcription_provider_conformance(provider, *, audio_path)` | Name, awaitable transcribe, string |
| `assert_realtime_provider_conformance(provider, *, target_language)` | Name/model, awaitable create_session, `RealtimeTranslationSession` |
| `assert_streaming_transcription_provider_conformance(provider, *, languages=None, prompt=None, keywords=None, delay="low")` | Name/model, awaitable create_session, `StreamingTranscriptionSession` |
| `assert_streaming_translation_provider_conformance(provider, *, text, target_language, context=None, terminology=None, max_chunks=1000)` | Direct async iterator yielding `StreamingTranslationChunk` |
| `assert_streaming_speech_provider_conformance(provider, *, text, voice_id, instructions=None, max_chunks=1000)` | Direct async iterator yielding `StreamingSpeechChunk` |

Helpers return the checked result for further domain assertions; speech returns
`None`, and stream helpers collect chunks in a list. Both successful and failed
`AgentResult` values are valid. Protocol implementations need not inherit a
provider/stage interface. Helper checks do not alter models or impose new
success/error invariants.

Streaming checks close an iterator through `aclose()` when available, including
on a wrong chunk, chunk-count failure, provider error or cancellation. Empty
streams and missing final markers remain allowed because those behaviors are
provider-specific. `max_chunks` must be a positive integer; exceeding the limit
consumes one extra chunk before failing, and bounds retained memory. This limit
does not bound the time spent awaiting a chunk.

## Using the checks

Install `requirements-dev.lock` for pytest tests. The helpers themselves are
included in the runtime wheel and require no pytest dependency.

```python
import asyncio
import pytest
from app.framework.testing import assert_translation_provider_conformance

@pytest.mark.asyncio
async def test_my_translation_provider():
    result = await asyncio.wait_for(
        assert_translation_provider_conformance(
            my_provider, text="bonjour", target_language="en",
        ),
        timeout=10,
    )
    assert result == "hello"
```

Replace `my_provider` with your fixture. Use offline fakes in ordinary CI and
explicit opt-in integration tests for real providers: helpers call their methods
and do not mock network activity. Choose your own timeout, output assertions,
language cases and sample files. For speech, separately verify the generated
file and its audio format; a `None` return alone does not prove audio validity.

These are sample-based contract checks, not a certification of translation
quality, every accepted signature, all payloads, model support or production
latency. Error and cancellation tests for your implementation should verify its
own resource cleanup. Stable HTTP/WebSocket lifecycle guarantees belong to the
next slice.

## External composition and packaging gate

`examples/framework_extension/extension.py` contains a deterministic provider,
a structural stage and a `BaseAgent` subclass. `build_extension()` explicitly
registers them and composes a sequential pipeline. `check_extension.py` checks
provider/stage/agent results, registry discovery and two business failure cases.
It runs as an ordinary external program using only public imports.

Backend regression tests exercise the helpers with valid/invalid extensions,
including iterator closing and actual task cancellation. Packaging CI copies
the example to the runner temporary directory and runs it with the clean
installed-wheel environment. No backend source is added to that environment's
import path. The artifact check verifies that the helper module is in the wheel.

This slice adds `app.framework.testing` as the opt-in testing namespace; the
Slice 1 root facade exports and original imports remain unchanged. The runtime
version is 1.0.0; publication follows the final release acceptance checklist.
