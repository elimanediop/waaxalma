import pytest

from app.services.text_translation_service import (
    TextTranslationService,
)


class FakeTextTranslationPipeline:

    def __init__(self) -> None:
        self.received_state = None
        self.received_context = None

    async def execute(
        self,
        state,
        context,
    ):
        self.received_state = state
        self.received_context = context

        state.set(
            "interpreted_text",
            "Hello world",
        )
        state.set(
            "quality_accepted",
            True,
        )
        state.set(
            "quality_score",
            1.0,
        )
        state.set(
            "quality_issues",
            [],
        )
        state.set(
            "context_metadata",
            {
                "context_applied": True,
            },
        )
        state.set(
            "quality_metadata",
            {
                "evaluator": "deterministic",
            },
        )

        return state


@pytest.mark.asyncio
async def test_translate_executes_text_pipeline():
    pipeline = FakeTextTranslationPipeline()

    service = TextTranslationService(
        pipeline=pipeline,
    )

    result = await service.translate(
        text="Bonjour le monde",
        source_language="fr",
        target_language="en",
        metadata={
            "domain": "general",
        },
    )

    assert result.source_text == "Bonjour le monde"
    assert result.translated_text == "Hello world"
    assert result.source_language == "fr"
    assert result.target_language == "en"

    assert result.quality_accepted is True
    assert result.quality_score == 1.0
    assert result.quality_issues == []

    assert result.metadata == {
        "context": {
            "context_applied": True,
        },
        "quality": {
            "evaluator": "deterministic",
        },
    }

    assert pipeline.received_state.get(
        "agent_name"
    ) == "text_translation"

    assert pipeline.received_state.get(
        "source_text"
    ) == "Bonjour le monde"

    assert pipeline.received_state.get(
        "target_language"
    ) == "en"

    assert pipeline.received_context.source_language == "fr"
    assert pipeline.received_context.target_language == "en"


@pytest.mark.asyncio
async def test_translate_supports_unspecified_source_language():
    pipeline = FakeTextTranslationPipeline()

    service = TextTranslationService(
        pipeline=pipeline,
    )

    result = await service.translate(
        text="Bonjour",
        target_language="en",
    )

    assert result.source_language is None
    assert pipeline.received_context.source_language is None


@pytest.mark.asyncio
async def test_translate_rejects_empty_text():
    service = TextTranslationService(
        pipeline=FakeTextTranslationPipeline(),
    )

    with pytest.raises(
        ValueError,
        match="Text cannot be empty",
    ):
        await service.translate(
            text="   ",
            target_language="en",
        )


@pytest.mark.asyncio
async def test_translate_rejects_empty_target_language():
    service = TextTranslationService(
        pipeline=FakeTextTranslationPipeline(),
    )

    with pytest.raises(
        ValueError,
        match="Target language cannot be empty",
    ):
        await service.translate(
            text="Bonjour",
            target_language="   ",
        )


@pytest.mark.asyncio
async def test_translate_normalizes_input():
    pipeline = FakeTextTranslationPipeline()

    service = TextTranslationService(
        pipeline=pipeline,
    )

    result = await service.translate(
        text="  Bonjour  ",
        source_language="  fr  ",
        target_language="  en  ",
    )

    assert result.source_text == "Bonjour"
    assert result.source_language == "fr"
    assert result.target_language == "en"

    assert pipeline.received_state.get(
        "source_text"
    ) == "Bonjour"

    assert pipeline.received_state.get(
        "source_language"
    ) == "fr"

    assert pipeline.received_state.get(
        "target_language"
    ) == "en"