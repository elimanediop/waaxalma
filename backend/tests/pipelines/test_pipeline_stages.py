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
from app.core.context_result import ContextResult
from app.core.quality_result import QualityResult
from app.pipelines.stages.context_stage import ContextStage
from app.pipelines.stages.quality_stage import QualityStage


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

@pytest.mark.asyncio
async def test_context_stage_enriches_pipeline_state() -> None:
    skill = create_skill(
        provider_name="fake-context",
    )

    skill.execute.return_value = ContextResult(
        original_text="Naka nga def?",
        enriched_text="[context] Naka nga def?",
        metadata={
            "topic": "greeting",
        },
    )

    stage = ContextStage(
        context_skill=skill,
    )

    state = PipelineState(
        data={
            "agent_name": "interpreter",
            "source_text": "Naka nga def?",
            "context_metadata": {
                "topic": "greeting",
            },
        }
    )

    context = SessionContext(
        session_id="context-stage-test",
    )

    result = await stage.execute(
        state=state,
        context=context,
    )

    assert (
        result.require("source_text")
        == "Naka nga def?"
    )

    assert (
        result.require("enriched_text")
        == "[context] Naka nga def?"
    )

    assert result.require(
        "context_metadata"
    ) == {
        "topic": "greeting",
    }

    skill.execute.assert_awaited_once_with(
        text="Naka nga def?",
        metadata={
            "topic": "greeting",
        },
    )

    assert (
        context.trace.stages[-1].stage
        == "context"
    )


@pytest.mark.asyncio
async def test_quality_stage_adds_evaluation_to_pipeline_state() -> None:
    skill = create_skill(
        provider_name="fake-quality",
    )

    skill.execute.return_value = QualityResult(
        accepted=True,
        score=None,
        issues=[],
        metadata={
            "evaluation": "deterministic",
            "semantic_evaluation": False,
        },
    )

    stage = QualityStage(
        quality_skill=skill,
    )

    state = PipelineState(
        data={
            "agent_name": "interpreter",
            "source_text": "Naka nga def?",
            "interpreted_text": "How are you?",
            "target_language": "English",
        }
    )

    context = SessionContext(
        session_id="quality-stage-test",
        target_language="English",
    )

    result = await stage.execute(
        state=state,
        context=context,
    )

    assert (
        result.require("quality_accepted")
        is True
    )

    assert (
        result.get("quality_score")
        is None
    )

    assert result.require(
        "quality_issues"
    ) == []

    assert result.require(
        "quality_metadata"
    ) == {
        "evaluation": "deterministic",
        "semantic_evaluation": False,
    }

    skill.execute.assert_awaited_once_with(
        source_text="Naka nga def?",
        interpreted_text="How are you?",
        target_language="English",
    )

    assert (
        context.trace.stages[-1].stage
        == "quality"
    )

@pytest.mark.asyncio
async def test_translation_stage_prefers_enriched_text() -> None:
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
            "source_text": "Original text",
            "enriched_text": "Context enriched text",
            "target_language": "English",
        }
    )

    context = SessionContext(
        session_id="enriched-translation-test",
        target_language="English",
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
        text="Context enriched text",
        target_language="English",
    )