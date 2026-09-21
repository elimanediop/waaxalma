from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.session_context import SessionContext
from app.pipelines.pipeline_state import PipelineState
from app.pipelines.sequential_pipeline import SequentialPipeline
from app.pipelines.stages.speech_stage import SpeechStage
from app.pipelines.stages.transcription_stage import (
    TranscriptionStage,
)
from app.pipelines.stages.translation_stage import (
    TranslationStage,
)


def create_skill(
    *,
    provider_name: str,
    result=None,
) -> SimpleNamespace:
    return SimpleNamespace(
        provider_name=provider_name,
        execute=AsyncMock(
            return_value=result,
        ),
    )


@pytest.mark.asyncio
async def test_transcription_stage() -> None:
    skill = create_skill(
        provider_name="fake-stt",
        result="Naka nga def?",
    )

    stage = TranscriptionStage(
        speech_to_text_skill=skill,
    )

    state = PipelineState(
        data={
            "agent_name": "interpreter",
            "audio_path": "fake.wav",
        }
    )

    context = SessionContext(
        session_id="transcription-test",
    )

    result = await stage.execute(
        state=state,
        context=context,
    )

    assert (
        result.require("source_text")
        == "Naka nga def?"
    )

    skill.execute.assert_awaited_once_with(
        audio_path="fake.wav",
    )

    assert context.trace.stages[-1].stage == (
        "transcription"
    )


@pytest.mark.asyncio
async def test_translation_stage() -> None:
    skill = create_skill(
        provider_name="fake-translation",
        result="How are you?",
    )

    stage = TranslationStage(
        translation_skill=skill,
    )

    state = PipelineState(
        data={
            "agent_name": "interpreter",
            "source_text": "Naka nga def?",
            "target_language": "English",
        }
    )

    context = SessionContext(
        session_id="translation-stage-test",
    )

    result = await stage.execute(
        state=state,
        context=context,
    )

    assert (
        result.require("interpreted_text")
        == "How are you?"
    )

    skill.execute.assert_awaited_once_with(
        text="Naka nga def?",
        target_language="English",
    )

    assert context.trace.stages[-1].stage == (
        "translation"
    )


@pytest.mark.asyncio
async def test_speech_stage() -> None:
    skill = create_skill(
        provider_name="fake-tts",
        result=None,
    )

    stage = SpeechStage(
        speech_skill=skill,
    )

    state = PipelineState(
        data={
            "agent_name": "interpreter",
            "request_id": "request-123",
            "interpreted_text": "How are you?",
        }
    )

    context = SessionContext(
        session_id="speech-stage-test",
    )

    result = await stage.execute(
        state=state,
        context=context,
    )

    assert (
        result.require("audio_url")
        .endswith("/request-123.mp3")
    )

    skill.execute.assert_awaited_once_with(
        text="How are you?",
        output_filename="request-123.mp3",
    )

    assert context.trace.stages[-1].stage == (
        "speech"
    )

@pytest.mark.asyncio
async def test_audio_interpreter_pipeline() -> None:
    stt_skill = create_skill(
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

    pipeline = SequentialPipeline(
        name="audio-interpreter",
        stages=[
            TranscriptionStage(
                speech_to_text_skill=stt_skill,
            ),
            TranslationStage(
                translation_skill=translation_skill,
            ),
            SpeechStage(
                speech_skill=speech_skill,
            ),
        ],
    )

    state = PipelineState(
        data={
            "agent_name": "interpreter",
            "request_id": "pipeline-123",
            "audio_path": "fake.wav",
            "target_language": "English",
        }
    )

    context = SessionContext(
        session_id="pipeline-test",
        target_language="English",
    )

    result = await pipeline.execute(
        state=state,
        context=context,
    )

    assert (
        result.require("source_text")
        == "Naka nga def?"
    )

    assert (
        result.require("interpreted_text")
        == "How are you?"
    )

    assert (
        result.require("audio_url")
        .endswith("/pipeline-123.mp3")
    )

    assert pipeline.stage_names == [
        "transcription",
        "translation",
        "speech",
    ]

    assert [
        stage.stage
        for stage in context.trace.stages
    ] == [
        "transcription",
        "translation",
        "speech",
    ]