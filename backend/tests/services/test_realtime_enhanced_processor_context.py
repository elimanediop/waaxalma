import pytest

from app.core.realtime_enhanced_runtime import (
    RealtimeEnhancedRuntime,
)
from app.core.streaming_translation_chunk import (
    StreamingTranslationChunk,
)
from app.services.realtime_enhanced_processor import (
    RealtimeEnhancedProcessor,
)


class FakeRealtimeEnhancedService:

    def __init__(
        self,
    ) -> None:
        self.calls: list[dict] = []

    async def translate_stream(
        self,
        *,
        text: str,
        target_language: str,
        context: str | None = None,
        terminology: list[str] | None = None,
    ):
        self.calls.append(
            {
                "text":
                    text,
                "target_language":
                    target_language,
                "context":
                    context,
                "terminology":
                    terminology,
            }
        )

        yield StreamingTranslationChunk(
            text="translated",
            metadata={
                "provider":
                    "fake",
            },
        )

        yield StreamingTranslationChunk(
            text="",
            is_final=True,
            metadata={
                "provider":
                    "fake",
            },
        )


def make_processor(
    service: FakeRealtimeEnhancedService,
) -> RealtimeEnhancedProcessor:
    runtime = RealtimeEnhancedRuntime(
        target_language="en",
        context="Waaxalma realtime interpretation.",
        terminology=[
            "Waaxalma",
            "Enhanced",
            "Direct",
        ],
        session_id="hardening-test",
    )

    return RealtimeEnhancedProcessor(
        runtime=runtime,
        service=service,
    )


@pytest.mark.asyncio
async def test_final_transcript_overrides_partial_deltas() -> None:
    service = FakeRealtimeEnhancedService()
    processor = make_processor(
        service
    )

    processor.append_transcript_delta(
        "Le mode extanded"
    )

    chunks = [
        chunk
        async for chunk
        in processor.commit_and_translate(
            final_text=(
                "Le mode Enhanced expose "
                "le transcript source."
            ),
        )
    ]

    assert chunks
    assert len(service.calls) == 1

    assert (
        service.calls[0]["text"]
        == (
            "Le mode Enhanced expose "
            "le transcript source."
        )
    )


@pytest.mark.asyncio
async def test_previous_final_transcript_is_rolling_context() -> None:
    service = FakeRealtimeEnhancedService()
    processor = make_processor(
        service
    )

    processor.append_transcript_delta(
        "first partial"
    )

    _ = [
        chunk
        async for chunk
        in processor.commit_and_translate(
            final_text=(
                "Le transcript final est autoritaire."
            ),
        )
    ]

    processor.append_transcript_delta(
        "second partial"
    )

    _ = [
        chunk
        async for chunk
        in processor.commit_and_translate(
            final_text=(
                "Le rolling context aide "
                "les fragments courts."
            ),
        )
    ]

    assert len(service.calls) == 2

    second_context = (
        service.calls[1]["context"]
    )

    assert second_context is not None

    assert (
        "Le transcript final est autoritaire."
        in second_context
    )

    assert (
        "Previous source transcript segments"
        in second_context
    )


@pytest.mark.asyncio
async def test_reset_clears_rolling_context() -> None:
    service = FakeRealtimeEnhancedService()
    processor = make_processor(
        service
    )

    processor.append_transcript_delta(
        "first partial"
    )

    _ = [
        chunk
        async for chunk
        in processor.commit_and_translate(
            final_text="Previous source segment.",
        )
    ]

    processor.reset()

    processor.append_transcript_delta(
        "second partial"
    )

    _ = [
        chunk
        async for chunk
        in processor.commit_and_translate(
            final_text="New source segment.",
        )
    ]

    assert len(service.calls) == 2

    second_context = (
        service.calls[1]["context"]
    )

    assert second_context is not None

    assert (
        "Previous source segment."
        not in second_context
    )

    assert (
        "Waaxalma realtime interpretation."
        in second_context
    )
