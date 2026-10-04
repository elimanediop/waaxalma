"""Opt-in extension checks; never invoked by runtime registration.

These helpers execute caller-supplied examples. Use fakes for offline tests,
and supply an asyncio timeout when checking implementations that perform I/O.
Provider exceptions and cancellation propagate unchanged.
"""
from collections.abc import AsyncIterator
import inspect
from typing import Any

from app.framework import (
    AgentInput, AgentResult, BaseAgent, PipelineState, SessionContext,
    RealtimeTranslationSession, StreamingTranscriptionSession,
    StreamingTranslationChunk, StreamingSpeechChunk,
)

__all__ = [
    "ConformanceError", "assert_agent_conformance", "assert_stage_conformance",
    "assert_translation_provider_conformance", "assert_speech_provider_conformance",
    "assert_transcription_provider_conformance", "assert_realtime_provider_conformance",
    "assert_streaming_transcription_provider_conformance",
    "assert_streaming_translation_provider_conformance",
    "assert_streaming_speech_provider_conformance",
]


class ConformanceError(AssertionError):
    """An extension returned a value outside the documented contract."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ConformanceError(message)


def _identity(extension: Any, *, live: bool = False) -> None:
    for attribute in (("name", "model") if live else ("name",)):
        value = getattr(extension, attribute, None)
        _require(isinstance(value, str) and bool(value.strip()),
                 f"{attribute} must be a non-empty string")


def _call(extension: Any, method: str, *args: Any, **kwargs: Any) -> Any:
    function = getattr(extension, method, None)
    _require(callable(function), f"{method} must be callable")
    try:
        inspect.signature(function).bind(*args, **kwargs)
    except (TypeError, ValueError) as exc:
        raise ConformanceError(f"{method} does not accept the contract arguments") from exc
    return function(*args, **kwargs)


async def _await(value: Any, method: str) -> Any:
    _require(inspect.isawaitable(value), f"{method} must return an awaitable")
    return await value


async def assert_agent_conformance(
    agent: BaseAgent, agent_input: AgentInput, context: SessionContext,
) -> AgentResult:
    _require(isinstance(agent, BaseAgent), "agent must implement BaseAgent")
    _identity(agent)
    result = await _await(_call(agent, "execute", agent_input, context), "execute")
    _require(isinstance(result, AgentResult), "execute must return AgentResult")
    return result


async def assert_stage_conformance(
    stage: Any, state: PipelineState, context: SessionContext,
) -> PipelineState:
    _identity(stage)
    # SequentialPipeline invokes stages with named arguments.
    result = await _await(_call(stage, "execute", state=state, context=context), "execute")
    _require(isinstance(result, PipelineState), "execute must return PipelineState")
    return result


async def assert_translation_provider_conformance(
    provider: Any, *, text: str, target_language: str,
) -> str:
    _identity(provider)
    result = await _await(_call(provider, "translate", text=text,
                               target_language=target_language), "translate")
    _require(isinstance(result, str), "translate must return str")
    return result


async def assert_speech_provider_conformance(
    provider: Any, *, text: str, output_filename: str,
) -> None:
    _identity(provider)
    result = await _await(_call(provider, "speak", text=text,
                               output_filename=output_filename), "speak")
    _require(result is None, "speak must return None")


async def assert_transcription_provider_conformance(
    provider: Any, *, audio_path: str,
) -> str:
    _identity(provider)
    result = await _await(_call(provider, "transcribe", audio_path=audio_path), "transcribe")
    _require(isinstance(result, str), "transcribe must return str")
    return result


async def assert_realtime_provider_conformance(
    provider: Any, *, target_language: str,
) -> RealtimeTranslationSession:
    _identity(provider, live=True)
    result = await _await(_call(provider, "create_session",
                               target_language=target_language), "create_session")
    _require(isinstance(result, RealtimeTranslationSession),
             "create_session must return RealtimeTranslationSession")
    return result


async def assert_streaming_transcription_provider_conformance(
    provider: Any, *, languages: list[str] | None = None,
    prompt: str | None = None, keywords: list[str] | None = None, delay: str = "low",
) -> StreamingTranscriptionSession:
    _identity(provider, live=True)
    result = await _await(_call(provider, "create_session", languages=languages,
                               prompt=prompt, keywords=keywords, delay=delay), "create_session")
    _require(isinstance(result, StreamingTranscriptionSession),
             "create_session must return StreamingTranscriptionSession")
    return result


async def _chunks(stream: Any, chunk_type: type, max_chunks: int) -> list[Any]:
    if inspect.iscoroutine(stream):
        stream.close()
        raise ConformanceError("stream method must return an async iterator directly")
    _require(isinstance(stream, AsyncIterator), "stream must be an async iterator")
    result = []
    try:
        async for chunk in stream:
            _require(isinstance(chunk, chunk_type),
                     f"stream must yield {chunk_type.__name__}")
            _require(len(result) < max_chunks, "stream exceeded max_chunks")
            result.append(chunk)
    finally:
        close = getattr(stream, "aclose", None)
        if close is not None:
            await close()
    # Empty streams and absence of final markers are provider-specific, allowed.
    return result


def _limit(max_chunks: int) -> None:
    _require(type(max_chunks) is int and max_chunks > 0, "max_chunks must be a positive integer")


async def assert_streaming_translation_provider_conformance(
    provider: Any, *, text: str, target_language: str, context: str | None = None,
    terminology: list[str] | None = None, max_chunks: int = 1000,
) -> list[StreamingTranslationChunk]:
    _limit(max_chunks)
    _identity(provider, live=True)
    return await _chunks(_call(provider, "translate_stream", text=text,
                              target_language=target_language, context=context,
                              terminology=terminology), StreamingTranslationChunk, max_chunks)


async def assert_streaming_speech_provider_conformance(
    provider: Any, *, text: str, voice_id: str, instructions: str | None = None,
    max_chunks: int = 1000,
) -> list[StreamingSpeechChunk]:
    _limit(max_chunks)
    _identity(provider, live=True)
    return await _chunks(_call(provider, "speak_stream", text=text, voice_id=voice_id,
                              instructions=instructions), StreamingSpeechChunk, max_chunks)
