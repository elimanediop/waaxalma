import pytest

from app.core.streaming_speech_chunk import (
    StreamingSpeechChunk,
)


def test_streaming_speech_chunk_defaults() -> None:
    chunk = StreamingSpeechChunk(
        audio=b"audio-data",
    )

    assert chunk.audio == b"audio-data"
    assert chunk.is_final is False
    assert chunk.content_type == "audio/pcm"
    assert chunk.sample_rate is None
    assert chunk.metadata == {}


def test_streaming_speech_chunk_final() -> None:
    chunk = StreamingSpeechChunk(
        audio=b"",
        is_final=True,
        content_type="audio/pcm",
        sample_rate=24000,
        metadata={
            "provider": "fake",
        },
    )

    assert chunk.audio == b""
    assert chunk.is_final is True
    assert chunk.content_type == "audio/pcm"
    assert chunk.sample_rate == 24000

    assert chunk.metadata == {
        "provider": "fake",
    }


def test_streaming_speech_chunk_metadata_is_not_shared() -> None:
    first = StreamingSpeechChunk(
        audio=b"first",
    )

    second = StreamingSpeechChunk(
        audio=b"second",
    )

    first.metadata["test"] = True

    assert first.metadata == {
        "test": True,
    }

    assert second.metadata == {}


class FakeStreamingSpeechProvider:

    def __init__(self) -> None:
        self.received_text: str | None = None
        self.received_voice_id: str | None = None
        self.received_instructions: str | None = None

    @property
    def name(self) -> str:
        return "fake"

    @property
    def model(self) -> str:
        return "fake-streaming-speech-model"

    async def speak_stream(
        self,
        *,
        text: str,
        voice_id: str,
        instructions: str | None = None,
    ):
        self.received_text = text
        self.received_voice_id = voice_id
        self.received_instructions = instructions

        yield StreamingSpeechChunk(
            audio=b"chunk-1",
            content_type="audio/pcm",
            sample_rate=24000,
            metadata={
                "provider": self.name,
            },
        )

        yield StreamingSpeechChunk(
            audio=b"chunk-2",
            content_type="audio/pcm",
            sample_rate=24000,
            metadata={
                "provider": self.name,
            },
        )

        yield StreamingSpeechChunk(
            audio=b"",
            is_final=True,
            content_type="audio/pcm",
            sample_rate=24000,
            metadata={
                "provider": self.name,
            },
        )


@pytest.mark.asyncio
async def test_streaming_speech_provider_emits_audio_chunks() -> None:
    provider = FakeStreamingSpeechProvider()

    chunks = [
        chunk
        async for chunk
        in provider.speak_stream(
            text="Bonjour",
            voice_id="coral",
        )
    ]

    assert len(chunks) == 3

    assert chunks[0].audio == b"chunk-1"
    assert chunks[0].is_final is False

    assert chunks[1].audio == b"chunk-2"
    assert chunks[1].is_final is False

    assert chunks[2].audio == b""
    assert chunks[2].is_final is True

    assert (
        b"".join(
            chunk.audio
            for chunk in chunks
        )
        == b"chunk-1chunk-2"
    )


@pytest.mark.asyncio
async def test_streaming_speech_provider_receives_configuration() -> None:
    provider = FakeStreamingSpeechProvider()

    chunks = [
        chunk
        async for chunk
        in provider.speak_stream(
            text="Bonjour Waaxalma",
            voice_id="coral",
            instructions=(
                "Speak clearly and naturally."
            ),
        )
    ]

    assert chunks

    assert (
        provider.received_text
        == "Bonjour Waaxalma"
    )

    assert (
        provider.received_voice_id
        == "coral"
    )

    assert (
        provider.received_instructions
        == "Speak clearly and naturally."
    )