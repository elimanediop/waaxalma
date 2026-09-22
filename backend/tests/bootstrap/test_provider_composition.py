import pytest

from app.bootstrap.container import (
    build_agent_registry,
    build_pipeline_registry,
)
from app.core.agent_input import AgentInput
from app.core.context_result import ContextResult
from app.core.quality_result import QualityResult
from app.core.session_context import SessionContext
from app.registry.provider_registry import ProviderRegistry
from app.skills.speech_skill import SpeechSkill
from app.skills.speech_to_text_skill import SpeechToTextSkill
from app.skills.translation_skill import TranslationSkill
from app.skills.context_skill import ContextSkill
from app.skills.quality_skill import QualitySkill


class FakeTranslationProvider:

    @property
    def name(self) -> str:
        return "fake"

    async def translate(
        self,
        text: str,
        target_language: str,
    ) -> str:
        return f"[fake:{target_language}] {text}"


class FakeSpeechProvider:

    def __init__(self) -> None:
        self.calls: list[dict] = []

    @property
    def name(self) -> str:
        return "fake"

    async def speak(
        self,
        text: str,
        output_filename: str,
    ) -> None:
        self.calls.append(
            {
                "text": text,
                "output_filename": output_filename,
            }
        )


class FakeSpeechToTextProvider:

    @property
    def name(self) -> str:
        return "fake"

    async def transcribe(
        self,
        audio_path: str,
    ) -> str:
        return "Fake transcription"


class FakeContextProvider:

    @property
    def name(self) -> str:
        return "fake"

    async def enrich(
        self,
        *,
        text: str,
        metadata: dict,
    ) -> ContextResult:
        return ContextResult(
            original_text=text,
            enriched_text=text,
            metadata=metadata,
        )


class FakeQualityProvider:

    @property
    def name(self) -> str:
        return "fake"

    async def evaluate(
        self,
        *,
        source_text: str,
        interpreted_text: str,
        target_language: str,
    ) -> QualityResult:
        return QualityResult(
            accepted=True,
            score=None,
            issues=[],
            metadata={
                "evaluation": "fake",
            },
        )

class RejectingQualityProvider:

    @property
    def name(self) -> str:
        return "rejecting"

    async def evaluate(
        self,
        *,
        source_text: str,
        interpreted_text: str,
        target_language: str,
    ) -> QualityResult:
        return QualityResult(
            accepted=False,
            score=None,
            issues=[
                "quality_check_failed",
            ],
            metadata={
                "evaluation": "deterministic",
            },
        )


def build_fake_provider_registry() -> ProviderRegistry:
    registry = ProviderRegistry()

    registry.register(
        capability="translation",
        name="fake",
        provider=FakeTranslationProvider(),
    )

    registry.register(
        capability="speech",
        name="fake",
        provider=FakeSpeechProvider(),
    )

    registry.register(
        capability="speech_to_text",
        name="fake",
        provider=FakeSpeechToTextProvider(),
    )

    registry.register(
        capability="context",
        name="fake",
        provider=FakeContextProvider(),
    )

    registry.register(
        capability="quality",
        name="fake",
        provider=FakeQualityProvider(),
    )

    return registry


def build_fake_agent_registry():
    """
    Build the application agent registry using only fake providers.

    This helper keeps composition tests independent from real
    external providers.
    """
    provider_registry = build_fake_provider_registry()

    return build_agent_registry(
        provider_registry=provider_registry,
        translation_provider_name="fake",
        speech_provider_name="fake",
        speech_to_text_provider_name="fake",
        context_provider_name="fake",
        quality_provider_name="fake",
    )


@pytest.mark.asyncio
async def test_agent_composition_uses_selected_translation_provider() -> None:
    provider_registry = build_fake_provider_registry()

    agent_registry = build_agent_registry(
        provider_registry=provider_registry,
        translation_provider_name="fake",
        speech_provider_name="fake",
        speech_to_text_provider_name="fake",
        context_provider_name="fake",
        quality_provider_name="fake",
    )

    translation_agent = agent_registry.find(
        "translation"
    )

    assert translation_agent is not None

    assert (
        translation_agent.translation_skill.provider_name
        == "fake"
    )

    assert (
        translation_agent.speech_skill.provider_name
        == "fake"
    )

    result = await translation_agent.execute(
        agent_input=AgentInput(
            operation="translate",
            payload={
                "text": "Bonjour",
                "target_language": "English",
            },
        ),
        context=SessionContext(
            session_id="fake-provider-test",
        ),
    )

    assert result.success is True
    assert result.output is not None

    assert (
        result.output["translated_text"]
        == "[fake:English] Bonjour"
    )


@pytest.mark.asyncio
async def test_interpreter_uses_selected_providers() -> None:
    provider_registry = build_fake_provider_registry()

    speech_provider = provider_registry.get(
        capability="speech",
        name="fake",
    )

    agent_registry = build_agent_registry(
        provider_registry=provider_registry,
        translation_provider_name="fake",
        speech_provider_name="fake",
        speech_to_text_provider_name="fake",
        context_provider_name="fake",
        quality_provider_name="fake",
    )

    interpreter = agent_registry.find(
        "interpreter"
    )

    assert interpreter is not None

    context = SessionContext(
        session_id="fake-interpreter-test",
        target_language="English",
    )

    result = await interpreter.execute(
        agent_input=AgentInput(
            operation="interpret_audio",
            payload={
                "audio_path": "fake.wav",
                "target_language": "English",
            },
        ),
        context=context,
    )

    assert result.success is True
    assert result.output is not None

    assert (
        result.output["source_text"]
        == "Fake transcription"
    )

    assert (
        result.output["interpreted_text"]
        == "[fake:English] Fake transcription"
    )

    assert (
        result.output["audio_url"]
        .endswith(".mp3")
    )

    assert [
        stage.stage
        for stage in context.trace.stages
    ] == [
        "transcription",
        "context",
        "translation",
        "quality",
        "speech",
    ]

    assert len(speech_provider.calls) == 1

    assert (
        speech_provider.calls[0]["text"]
        == "[fake:English] Fake transcription"
    )

    assert (
        speech_provider.calls[0]["output_filename"]
        .endswith(".mp3")
    )

    assert result.output["quality"] == {
        "accepted": True,
        "score": None,
        "issues": [],
        "metadata": {
            "evaluation": "fake",
        },
    }


@pytest.mark.asyncio
async def test_context_agent_uses_selected_provider() -> None:
    agent_registry = build_fake_agent_registry()

    context_agent = agent_registry.find(
        "context"
    )

    assert context_agent is not None

    assert (
        context_agent.context_skill.provider_name
        == "fake"
    )

    result = await context_agent.execute(
        agent_input=AgentInput(
            operation="enrich",
            payload={
                "text": "Naka nga def?",
                "metadata": {
                    "topic": "greeting",
                },
            },
        ),
        context=SessionContext(
            session_id="fake-context-test",
        ),
    )

    assert result.success is True
    assert result.output is not None

    assert (
        result.output["original_text"]
        == "Naka nga def?"
    )

    assert (
        result.output["enriched_text"]
        == "Naka nga def?"
    )

    assert result.output["metadata"] == {
        "topic": "greeting",
    }


@pytest.mark.asyncio
async def test_quality_agent_uses_selected_provider() -> None:
    agent_registry = build_fake_agent_registry()

    quality_agent = agent_registry.find(
        "quality"
    )

    assert quality_agent is not None

    assert (
        quality_agent.quality_skill.provider_name
        == "fake"
    )

    result = await quality_agent.execute(
        agent_input=AgentInput(
            operation="evaluate",
            payload={
                "source_text": "Naka nga def?",
                "interpreted_text": "How are you?",
                "target_language": "English",
            },
        ),
        context=SessionContext(
            session_id="fake-quality-test",
        ),
    )

    assert result.success is True
    assert result.output is not None

    assert result.output["accepted"] is True
    assert result.output["score"] is None
    assert result.output["issues"] == []

    assert result.output["metadata"] == {
        "evaluation": "fake",
    }


def test_context_and_quality_agents_are_registered() -> None:
    agent_registry = build_fake_agent_registry()

    assert agent_registry.contains(
        "context"
    )

    assert agent_registry.contains(
        "quality"
    )

    assert (
        agent_registry.find("context")
        is not None
    )

    assert (
        agent_registry.find("quality")
        is not None
    )


def test_framework_registers_all_expected_agents() -> None:
    agent_registry = build_fake_agent_registry()

    assert agent_registry.names() == [
        "context",
        "interpreter",
        "quality",
        "translation",
    ]


def test_unknown_configured_provider_fails_fast() -> None:
    provider_registry = build_fake_provider_registry()

    with pytest.raises(
        KeyError,
        match="not registered",
    ):
        build_agent_registry(
            provider_registry=provider_registry,
            translation_provider_name="unknown",
            speech_provider_name="fake",
            speech_to_text_provider_name="fake",
            context_provider_name="fake",
            quality_provider_name="fake",
        )


def test_pipeline_registry_builds_interpreter_pipelines() -> None:
    provider_registry = build_fake_provider_registry()

    translation_skill = TranslationSkill(
        provider=provider_registry.get(
            capability="translation",
            name="fake",
        )
    )

    speech_skill = SpeechSkill(
        provider=provider_registry.get(
            capability="speech",
            name="fake",
        )
    )

    speech_to_text_skill = SpeechToTextSkill(
        provider=provider_registry.get(
            capability="speech_to_text",
            name="fake",
        )
    )

    context_skill = ContextSkill(
        provider=provider_registry.get(
            capability="context",
            name="fake",
        )
    )

    quality_skill = QualitySkill(
        provider=provider_registry.get(
            capability="quality",
            name="fake",
        )
    )

    pipeline_registry = build_pipeline_registry(
        translation_skill=translation_skill,
        speech_skill=speech_skill,
        speech_to_text_skill=speech_to_text_skill,
        context_skill=context_skill,
        quality_skill=quality_skill,
    )

    assert pipeline_registry.names() == [
        "interpreter.audio",
        "interpreter.text",
    ]

    assert (
        pipeline_registry
        .get("interpreter.text")
        .stage_names
    ) == [
        "context",
        "translation",
        "quality",
        "speech",
    ]

    assert (
        pipeline_registry
        .get("interpreter.audio")
        .stage_names
    ) == [
        "transcription",
        "context",
        "translation",
        "quality",
        "speech",
    ]

@pytest.mark.asyncio
async def test_interpreter_exposes_rejected_quality() -> None:
    provider_registry = build_fake_provider_registry()

    provider_registry.register(
        capability="quality",
        name="rejecting",
        provider=RejectingQualityProvider(),
    )

    agent_registry = build_agent_registry(
        provider_registry=provider_registry,
        translation_provider_name="fake",
        speech_provider_name="fake",
        speech_to_text_provider_name="fake",
        context_provider_name="fake",
        quality_provider_name="rejecting",
    )

    interpreter = agent_registry.find(
        "interpreter"
    )

    assert interpreter is not None

    result = await interpreter.execute(
        agent_input=AgentInput(
            operation="interpret",
            payload={
                "text": "Naka nga def?",
                "target_language": "English",
            },
        ),
        context=SessionContext(
            session_id="quality-rejected-test",
            target_language="English",
        ),
    )

    assert result.success is True
    assert result.output is not None

    assert result.output["quality"] == {
        "accepted": False,
        "score": None,
        "issues": [
            "quality_check_failed",
        ],
        "metadata": {
            "evaluation": "deterministic",
        },
    }

def test_unknown_context_provider_fails_fast() -> None:
    provider_registry = build_fake_provider_registry()

    with pytest.raises(
        KeyError,
        match="not registered",
    ):
        build_agent_registry(
            provider_registry=provider_registry,
            translation_provider_name="fake",
            speech_provider_name="fake",
            speech_to_text_provider_name="fake",
            context_provider_name="unknown",
            quality_provider_name="fake",
        )

def test_unknown_quality_provider_fails_fast() -> None:
    provider_registry = build_fake_provider_registry()

    with pytest.raises(
        KeyError,
        match="not registered",
    ):
        build_agent_registry(
            provider_registry=provider_registry,
            translation_provider_name="fake",
            speech_provider_name="fake",
            speech_to_text_provider_name="fake",
            context_provider_name="fake",
            quality_provider_name="unknown",
        )