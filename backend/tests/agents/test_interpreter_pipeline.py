from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.agents.interpreter_agent import InterpreterAgent
from app.core.agent_input import AgentInput
from app.core.session_context import SessionContext
from app.exceptions.provider_exception import (
    ProviderUnavailableException,
)
from app.orchestration.agent_orchestrator import (
    AgentOrchestrator,
)
from app.pipelines.sequential_pipeline import SequentialPipeline
from app.pipelines.stages.speech_stage import SpeechStage
from app.pipelines.stages.transcription_stage import (
    TranscriptionStage,
)
from app.pipelines.stages.translation_stage import (
    TranslationStage,
)
from app.registry.agent_registry import AgentRegistry


def create_skill(
    *,
    provider_name: str,
    result: str | None = None,
    error: Exception | None = None,
) -> SimpleNamespace:
    if error is not None:
        execute = AsyncMock(
            side_effect=error,
        )
    else:
        execute = AsyncMock(
            return_value=result,
        )

    return SimpleNamespace(
        provider_name=provider_name,
        execute=execute,
    )


def create_interpreter_agent(
    *,
    translation_skill,
    speech_skill,
    speech_to_text_skill,
) -> InterpreterAgent:
    text_pipeline = SequentialPipeline(
        name="text-interpreter",
        stages=[
            TranslationStage(
                translation_skill=translation_skill,
            ),
            SpeechStage(
                speech_skill=speech_skill,
            ),
        ],
    )

    audio_pipeline = SequentialPipeline(
        name="audio-interpreter",
        stages=[
            TranscriptionStage(
                speech_to_text_skill=speech_to_text_skill,
            ),
            TranslationStage(
                translation_skill=translation_skill,
            ),
            SpeechStage(
                speech_skill=speech_skill,
            ),
        ],
    )

    return InterpreterAgent(
        text_pipeline=text_pipeline,
        audio_pipeline=audio_pipeline,
    )


def create_orchestrator(
    agent: InterpreterAgent,
) -> AgentOrchestrator:
    registry = AgentRegistry()
    registry.register(agent)

    return AgentOrchestrator(
        registry=registry,
    )


@pytest.mark.asyncio
async def test_audio_pipeline_success() -> None:
    speech_to_text_skill = create_skill(
        provider_name="fake-stt",
        result="Naka nga def?",
    )

    translation_skill = create_skill(
        provider_name="fake-translation",
        result="How are you?",
    )

    speech_skill = create_skill(
        provider_name="fake-tts",
        result=None,
    )

    agent = create_interpreter_agent(
        translation_skill=translation_skill,
        speech_skill=speech_skill,
        speech_to_text_skill=speech_to_text_skill,
    )

    orchestrator = create_orchestrator(
        agent=agent,
    )

    context = SessionContext(
        session_id="session-success",
        target_language="English",
    )

    result = await orchestrator.execute(
        agent_name="interpreter",
        agent_input=AgentInput(
            operation="interpret_audio",
            payload={
                "audio_path": "fake-recording.wav",
                "target_language": "English",
            },
        ),
        context=context,
    )

    assert result.success is True
    assert result.error_code is None
    assert result.output is not None

    assert (
        result.output["source_text"]
        == "Naka nga def?"
    )

    assert (
        result.output["interpreted_text"]
        == "How are you?"
    )

    assert (
        result.output["session_id"]
        == "session-success"
    )

    assert result.output["audio_url"].endswith(
        ".mp3"
    )

    speech_to_text_skill.execute.assert_awaited_once_with(
        audio_path="fake-recording.wav",
    )

    translation_skill.execute.assert_awaited_once_with(
        text="Naka nga def?",
        target_language="English",
    )

    speech_skill.execute.assert_awaited_once()

    assert [
        stage.stage
        for stage in context.trace.stages
    ] == [
        "transcription",
        "translation",
        "speech",
    ]

    assert all(
        stage.success
        for stage in context.trace.stages
    )


@pytest.mark.asyncio
async def test_partial_pipeline_failure_during_speech() -> None:
    speech_to_text_skill = create_skill(
        provider_name="fake-stt",
        result="Naka nga def?",
    )

    translation_skill = create_skill(
        provider_name="fake-translation",
        result="How are you?",
    )

    speech_skill = create_skill(
        provider_name="fake-tts",
        error=ProviderUnavailableException(
            provider="fake-tts",
            operation="speak",
            message="TTS provider unavailable.",
        ),
    )

    agent = create_interpreter_agent(
        translation_skill=translation_skill,
        speech_skill=speech_skill,
        speech_to_text_skill=speech_to_text_skill,
    )

    orchestrator = create_orchestrator(
        agent=agent,
    )

    context = SessionContext(
        session_id="session-partial-failure",
        target_language="English",
    )

    result = await orchestrator.execute(
        agent_name="interpreter",
        agent_input=AgentInput(
            operation="interpret_audio",
            payload={
                "audio_path": "fake-recording.wav",
                "target_language": "English",
            },
        ),
        context=context,
    )

    assert result.success is False
    assert result.output is None

    assert (
        result.error_code
        == "PROVIDER_UNAVAILABLE"
    )

    assert (
        result.error_message
        == "TTS provider unavailable."
    )

    assert (
        result.metadata["agent"]
        == "interpreter"
    )

    assert (
        result.metadata["operation"]
        == "interpret_audio"
    )

    assert (
        result.metadata["session_id"]
        == "session-partial-failure"
    )

    assert (
        result.metadata["http_status"]
        == 503
    )

    speech_to_text_skill.execute.assert_awaited_once()
    translation_skill.execute.assert_awaited_once()
    speech_skill.execute.assert_awaited_once()

    stages = context.trace.stages

    assert [
        stage.stage
        for stage in stages
    ] == [
        "transcription",
        "translation",
        "speech",
    ]

    assert stages[0].success is True
    assert stages[1].success is True
    assert stages[2].success is False

    assert (
        stages[2].error_code
        == "PROVIDER_UNAVAILABLE"
    )


@pytest.mark.asyncio
async def test_text_interpreter_pipeline_success() -> None:
    translation_skill = create_skill(
        provider_name="fake-translation",
        result="How are you?",
    )

    speech_skill = create_skill(
        provider_name="fake-tts",
        result=None,
    )

    speech_to_text_skill = create_skill(
        provider_name="fake-stt",
    )

    agent = create_interpreter_agent(
        translation_skill=translation_skill,
        speech_skill=speech_skill,
        speech_to_text_skill=speech_to_text_skill,
    )

    orchestrator = create_orchestrator(
        agent=agent,
    )

    context = SessionContext(
        session_id="text-interpreter-test",
        target_language="English",
    )

    result = await orchestrator.execute(
        agent_name="interpreter",
        agent_input=AgentInput(
            operation="interpret",
            payload={
                "text": "Naka nga def?",
                "target_language": "English",
            },
        ),
        context=context,
    )

    assert result.success is True
    assert result.error_code is None
    assert result.output is not None

    assert (
        result.output["source_text"]
        == "Naka nga def?"
    )

    assert (
        result.output["interpreted_text"]
        == "How are you?"
    )

    assert (
        result.output["session_id"]
        == "text-interpreter-test"
    )

    assert result.output["audio_url"].endswith(
        ".mp3"
    )

    translation_skill.execute.assert_awaited_once_with(
        text="Naka nga def?",
        target_language="English",
    )

    speech_skill.execute.assert_awaited_once()

    speech_to_text_skill.execute.assert_not_awaited()

    assert [
        stage.stage
        for stage in context.trace.stages
    ] == [
        "translation",
        "speech",
    ]

    assert all(
        stage.success
        for stage in context.trace.stages
    )


def test_interpreter_pipelines_are_configurable() -> None:
    translation_skill = create_skill(
        provider_name="fake-translation",
    )

    speech_skill = create_skill(
        provider_name="fake-tts",
    )

    speech_to_text_skill = create_skill(
        provider_name="fake-stt",
    )

    text_pipeline = SequentialPipeline(
        name="custom-text",
        stages=[
            TranslationStage(
                translation_skill=translation_skill,
            ),
            SpeechStage(
                speech_skill=speech_skill,
            ),
        ],
    )

    audio_pipeline = SequentialPipeline(
        name="custom-audio",
        stages=[
            TranscriptionStage(
                speech_to_text_skill=speech_to_text_skill,
            ),
            TranslationStage(
                translation_skill=translation_skill,
            ),
            SpeechStage(
                speech_skill=speech_skill,
            ),
        ],
    )

    agent = InterpreterAgent(
        text_pipeline=text_pipeline,
        audio_pipeline=audio_pipeline,
    )

    assert (
        agent._text_pipeline.stage_names
        == [
            "translation",
            "speech",
        ]
    )

    assert (
        agent._audio_pipeline.stage_names
        == [
            "transcription",
            "translation",
            "speech",
        ]
    )