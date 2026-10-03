import asyncio
from pathlib import Path
from types import SimpleNamespace
import os
import subprocess
import sys

import pytest

from app.framework import (
    AgentInput, AgentResult, BaseAgent, PipelineState, SessionContext,
    RealtimeTranslationSession, StreamingTranscriptionSession,
    StreamingTranslationChunk, StreamingSpeechChunk,
)
from app.framework import testing as checks


class Provider:
    name = "fake"
    model = "offline"

    def __init__(self, response):
        self.response = response
        self.closed = False

    async def translate(self, text, target_language):
        return self.response

    async def speak(self, text, output_filename):
        return self.response

    async def transcribe(self, audio_path):
        return self.response

    async def create_session(self, **kwargs):
        return self.response

    def translate_stream(self, **kwargs):
        return self.stream()

    def speak_stream(self, **kwargs):
        return self.stream()

    async def stream(self):
        try:
            for chunk in self.response:
                yield chunk
        finally:
            self.closed = True


CASES = [
    (checks.assert_translation_provider_conformance, {"text": "bonjour", "target_language": "en"}, "hello", "translate must return str"),
    (checks.assert_speech_provider_conformance, {"text": "hello", "output_filename": "unused.wav"}, None, "speak must return None"),
    (checks.assert_transcription_provider_conformance, {"audio_path": "unused.wav"}, "hello", "transcribe must return str"),
    (checks.assert_realtime_provider_conformance, {"target_language": "en"},
     RealtimeTranslationSession(provider="fake", model="offline", target_language="en", client_secret="fake-secret"),
     "create_session must return RealtimeTranslationSession"),
    (checks.assert_streaming_transcription_provider_conformance, {},
     StreamingTranscriptionSession(provider="fake", model="offline", client_secret="fake-secret"),
     "create_session must return StreamingTranscriptionSession"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("checker,arguments,response,error", CASES)
async def test_standard_provider_sample(checker, arguments, response, error):
    assert await checker(Provider(response), **arguments) is response


@pytest.mark.asyncio
@pytest.mark.parametrize("checker,arguments,response,error", CASES)
async def test_wrong_provider_result_is_diagnostic(checker, arguments, response, error):
    with pytest.raises(checks.ConformanceError, match=error):
        await checker(Provider(123), **arguments)


@pytest.mark.asyncio
@pytest.mark.parametrize("name", [None, "", " ", 42])
async def test_invalid_names_rejected_before_execution(name):
    provider = Provider("hello")
    provider.name = name
    with pytest.raises(checks.ConformanceError, match="name must"):
        await checks.assert_translation_provider_conformance(provider, text="hello", target_language="en")


@pytest.mark.asyncio
async def test_live_model_is_required():
    provider = Provider([])
    provider.model = ""
    with pytest.raises(checks.ConformanceError, match="model must"):
        await checks.assert_streaming_translation_provider_conformance(provider, text="hello", target_language="en")


@pytest.mark.asyncio
@pytest.mark.parametrize("method,error", [
    (None, "translate must be callable"),
    (lambda wrong: "hello", "translate does not accept"),
    (lambda text, target_language: "hello", "translate must return an awaitable"),
])
async def test_provider_method_diagnostics(method, error):
    with pytest.raises(checks.ConformanceError, match=error):
        await checks.assert_translation_provider_conformance(
            SimpleNamespace(name="fake", translate=method), text="hello", target_language="en",
        )


STREAM_CASES = [
    (checks.assert_streaming_translation_provider_conformance,
     {"text": "hello", "target_language": "en"}, StreamingTranslationChunk(text="hello")),
    (checks.assert_streaming_speech_provider_conformance,
     {"text": "hello", "voice_id": "demo"}, StreamingSpeechChunk(audio=b"\x00\x00")),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("checker,arguments,chunk", STREAM_CASES)
async def test_streams_are_consumed_and_closed(checker, arguments, chunk):
    provider = Provider([chunk, chunk.model_copy(update={"is_final": True})])
    assert await checker(provider, **arguments) == provider.response
    assert provider.closed


@pytest.mark.asyncio
@pytest.mark.parametrize("checker,arguments,chunk", STREAM_CASES)
async def test_bad_chunk_closes_iterator(checker, arguments, chunk):
    provider = Provider(["invalid"])
    with pytest.raises(checks.ConformanceError, match="stream must yield"):
        await checker(provider, **arguments)
    assert provider.closed


@pytest.mark.asyncio
@pytest.mark.parametrize("checker,arguments,chunk", STREAM_CASES)
async def test_chunk_limit_closes_iterator(checker, arguments, chunk):
    provider = Provider([chunk, chunk])
    with pytest.raises(checks.ConformanceError, match="exceeded max_chunks"):
        await checker(provider, max_chunks=1, **arguments)
    assert provider.closed


@pytest.mark.asyncio
@pytest.mark.parametrize("limit", [0, -1, True, 1.5])
async def test_invalid_limit_rejected(limit):
    with pytest.raises(checks.ConformanceError, match="positive integer"):
        await checks.assert_streaming_translation_provider_conformance(
            Provider([]), text="hello", target_language="en", max_chunks=limit,
        )


@pytest.mark.asyncio
async def test_empty_stream_is_allowed():
    provider = Provider([])
    assert await checks.assert_streaming_translation_provider_conformance(
        provider, text="", target_language="en",
    ) == []
    assert provider.closed


@pytest.mark.asyncio
async def test_coroutine_instead_of_iterator_rejected_without_leak():
    class WrongProvider(Provider):
        async def translate_stream(self, **kwargs):
            return self.stream()
    with pytest.raises(checks.ConformanceError, match="async iterator directly"):
        await checks.assert_streaming_translation_provider_conformance(
            WrongProvider([]), text="hello", target_language="en",
        )


@pytest.mark.asyncio
async def test_sync_iterator_rejected():
    provider = SimpleNamespace(name="fake", model="offline", translate_stream=lambda **kw: iter([]))
    with pytest.raises(checks.ConformanceError, match="async iterator"):
        await checks.assert_streaming_translation_provider_conformance(provider, text="hello", target_language="en")


@pytest.mark.asyncio
@pytest.mark.parametrize("error_type", [RuntimeError, asyncio.CancelledError])
async def test_stream_failures_propagate_and_close(error_type):
    failure = error_type("provider failure")
    class FailedProvider(Provider):
        async def stream(self):
            try:
                yield StreamingTranslationChunk(text="hello")
                raise failure
            finally:
                self.closed = True
    provider = FailedProvider([])
    with pytest.raises(error_type) as caught:
        await checks.assert_streaming_translation_provider_conformance(provider, text="hello", target_language="en")
    assert caught.value is failure
    assert provider.closed


@pytest.mark.asyncio
async def test_actual_task_cancellation_releases_stream():
    entered = asyncio.Event()
    class WaitingProvider(Provider):
        async def stream(self):
            try:
                entered.set()
                await asyncio.Event().wait()
                yield StreamingTranslationChunk(text="unreachable")
            finally:
                self.closed = True
    provider = WaitingProvider([])
    task = asyncio.create_task(checks.assert_streaming_translation_provider_conformance(
        provider, text="hello", target_language="en",
    ))
    await asyncio.wait_for(entered.wait(), 1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert provider.closed


class Agent(BaseAgent):
    name = "fake_agent"
    def __init__(self, response):
        self.response = response
    async def execute(self, agent_input, context):
        return self.response


@pytest.mark.asyncio
@pytest.mark.parametrize("success", [True, False])
async def test_agent_allows_success_and_business_failure(success):
    result = AgentResult(success=success, output={"text": "hello"} if success else None)
    assert await checks.assert_agent_conformance(
        Agent(result), AgentInput(operation="echo"), SessionContext(),
    ) is result


@pytest.mark.asyncio
async def test_agent_rejects_raw_dict():
    with pytest.raises(checks.ConformanceError, match="return AgentResult"):
        await checks.assert_agent_conformance(Agent({"success": True}), AgentInput(operation="echo"), SessionContext())


@pytest.mark.asyncio
async def test_agent_requires_base_contract():
    with pytest.raises(checks.ConformanceError, match="implement BaseAgent"):
        await checks.assert_agent_conformance(object(), AgentInput(operation="echo"), SessionContext())


@pytest.mark.asyncio
@pytest.mark.parametrize("error_type", [RuntimeError, asyncio.CancelledError])
async def test_agent_exceptions_propagate(error_type):
    failure = error_type("agent failure")
    class FailedAgent(Agent):
        async def execute(self, agent_input, context):
            raise failure
    with pytest.raises(error_type) as caught:
        await checks.assert_agent_conformance(FailedAgent(None), AgentInput(operation="echo"), SessionContext())
    assert caught.value is failure


@pytest.mark.asyncio
async def test_stage_structural_contract_and_output():
    async def execute(*, state, context):
        return PipelineState({"language": context.target_language})
    result = await checks.assert_stage_conformance(
        SimpleNamespace(name="stage", execute=execute), PipelineState(), SessionContext(),
    )
    assert result.require("language") == "en"


@pytest.mark.asyncio
async def test_stage_rejects_wrong_state():
    async def execute(*, state, context):
        return {}
    with pytest.raises(checks.ConformanceError, match="return PipelineState"):
        await checks.assert_stage_conformance(SimpleNamespace(name="stage", execute=execute), PipelineState(), SessionContext())


def test_external_example_runs_as_separate_program():
    backend = Path(__file__).resolve().parents[2]
    example = backend.parent / "examples/framework_extension/check_extension.py"
    environment = os.environ.copy()
    environment.update(APP_ENV="invalid-for-runtime", OPENAI_API_KEY="", PYTHONPATH=str(backend))
    subprocess.run([sys.executable, str(example)], env=environment, cwd=example.parent, check=True, timeout=15)


def test_testing_helpers_import_without_application_startup():
    environment = os.environ.copy()
    environment.update(APP_ENV="invalid-for-runtime", OPENAI_API_KEY="")
    subprocess.run([sys.executable, "-c", "import sys; import app.framework.testing; assert 'app.core.settings' not in sys.modules; assert 'openai' not in sys.modules"],
                   env=environment, check=True, timeout=10)
