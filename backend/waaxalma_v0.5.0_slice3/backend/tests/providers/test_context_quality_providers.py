import pytest

from app.providers.deterministic_quality_provider import (
    DeterministicQualityProvider,
)
from app.providers.passthrough_context_provider import (
    PassthroughContextProvider,
)


@pytest.mark.asyncio
async def test_passthrough_context_preserves_text() -> None:
    provider = PassthroughContextProvider()

    result = await provider.enrich(
        text="Naka nga def?",
        metadata={
            "topic": "greeting",
        },
    )

    assert result.original_text == "Naka nga def?"
    assert result.enriched_text == "Naka nga def?"

    assert result.metadata == {
        "topic": "greeting",
    }

    assert provider.name == "passthrough"


@pytest.mark.asyncio
async def test_deterministic_quality_accepts_valid_content() -> None:
    provider = DeterministicQualityProvider()

    result = await provider.evaluate(
        source_text="Naka nga def?",
        interpreted_text="How are you?",
        target_language="English",
    )

    assert result.accepted is True
    assert result.score is None
    assert result.issues == []

    assert (
        result.metadata["evaluation"]
        == "deterministic"
    )

    assert (
        result.metadata["semantic_evaluation"]
        is False
    )


@pytest.mark.asyncio
async def test_deterministic_quality_rejects_empty_interpretation() -> None:
    provider = DeterministicQualityProvider()

    result = await provider.evaluate(
        source_text="Naka nga def?",
        interpreted_text="   ",
        target_language="English",
    )

    assert result.accepted is False

    assert result.issues == [
        "empty_interpreted_text",
    ]


@pytest.mark.asyncio
async def test_deterministic_quality_reports_multiple_issues() -> None:
    provider = DeterministicQualityProvider()

    result = await provider.evaluate(
        source_text="",
        interpreted_text="",
        target_language="",
    )

    assert result.accepted is False

    assert result.issues == [
        "empty_source_text",
        "empty_interpreted_text",
        "missing_target_language",
    ]