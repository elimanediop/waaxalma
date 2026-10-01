import pytest

from app.core.streaming_translation_chunk import (
    StreamingTranslationChunk,
)


def test_streaming_translation_chunk_defaults() -> None:
    chunk = StreamingTranslationChunk(
        text="Hello",
    )

    assert chunk.text == "Hello"
    assert chunk.is_final is False
    assert chunk.metadata == {}


def test_streaming_translation_chunk_final() -> None:
    chunk = StreamingTranslationChunk(
        text="Bonjour",
        is_final=True,
        metadata={
            "provider": "fake",
        },
    )

    assert chunk.text == "Bonjour"
    assert chunk.is_final is True

    assert chunk.metadata == {
        "provider": "fake",
    }


def test_streaming_translation_chunk_metadata_is_not_shared() -> None:
    first = StreamingTranslationChunk(
        text="one",
    )

    second = StreamingTranslationChunk(
        text="two",
    )

    first.metadata["test"] = True

    assert first.metadata == {
        "test": True,
    }

    assert second.metadata == {}


class FakeStreamingTranslationProvider:

    @property
    def name(self) -> str:
        return "fake"

    @property
    def model(self) -> str:
        return "fake-streaming-translation-model"

    async def translate_stream(
        self,
        *,
        text: str,
        target_language: str,
        context: str | None = None,
        terminology: list[str] | None = None,
    ):
        yield StreamingTranslationChunk(
            text="Bon",
            metadata={
                "source": text,
                "target_language": target_language,
            },
        )

        yield StreamingTranslationChunk(
            text="jour",
            is_final=True,
        )


@pytest.mark.asyncio
async def test_streaming_translation_provider_can_emit_chunks() -> None:
    provider = FakeStreamingTranslationProvider()

    chunks = [
        chunk
        async for chunk
        in provider.translate_stream(
            text="Hello",
            target_language="fr",
        )
    ]

    assert len(chunks) == 2

    assert chunks[0].text == "Bon"
    assert chunks[0].is_final is False

    assert chunks[1].text == "jour"
    assert chunks[1].is_final is True

    assert (
        "".join(
            chunk.text
            for chunk in chunks
        )
        == "Bonjour"
    )


@pytest.mark.asyncio
async def test_streaming_translation_provider_receives_context() -> None:
    provider = FakeStreamingTranslationProvider()

    chunks = [
        chunk
        async for chunk
        in provider.translate_stream(
            text="Hello Waaxalma",
            target_language="fr",
            context=(
                "Waaxalma is the product name."
            ),
            terminology=[
                "Waaxalma",
                "Elimane",
            ],
        )
    ]

    assert chunks

    assert (
        chunks[0].metadata[
            "source"
        ]
        == "Hello Waaxalma"
    )

    assert (
        chunks[0].metadata[
            "target_language"
        ]
        == "fr"
    )