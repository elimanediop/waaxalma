import pytest

from app.providers.openai_streaming_speech_provider import (
    OpenAIStreamingSpeechProvider,
)


class FakeSpeechResponse:

    def __init__(
        self,
        chunks: list[bytes],
    ) -> None:
        self._chunks = chunks

    async def __aenter__(
        self,
    ):
        return self

    async def __aexit__(
        self,
        exc_type,
        exc,
        traceback,
    ) -> bool:
        return False

    async def iter_bytes(
        self,
    ):
        for chunk in self._chunks:
            yield chunk


class FakeStreamingSpeechAPI:

    def __init__(
        self,
        chunks: list[bytes],
    ) -> None:
        self._chunks = chunks
        self.received_request: (
            dict | None
        ) = None

    def create(
        self,
        **kwargs,
    ) -> FakeSpeechResponse:

        self.received_request = kwargs

        return FakeSpeechResponse(
            self._chunks
        )


class FakeSpeechAPI:

    def __init__(
        self,
        chunks: list[bytes],
    ) -> None:
        self.with_streaming_response = (
            FakeStreamingSpeechAPI(
                chunks
            )
        )


class FakeAudioAPI:

    def __init__(
        self,
        chunks: list[bytes],
    ) -> None:
        self.speech = FakeSpeechAPI(
            chunks
        )


class FakeOpenAIClient:

    def __init__(
        self,
        chunks: list[bytes],
    ) -> None:
        self.audio = FakeAudioAPI(
            chunks
        )


@pytest.mark.asyncio
async def test_streaming_speech_emits_audio_chunks() -> None:

    client = FakeOpenAIClient(
        chunks=[
            b"audio-1",
            b"audio-2",
        ]
    )

    provider = OpenAIStreamingSpeechProvider(
        api_key="test-api-key",
        model="gpt-4o-mini-tts",
        client=client,
    )

    chunks = [
        chunk
        async for chunk
        in provider.speak_stream(
            text="Bonjour",
            voice_id="coral",
        )
    ]

    assert len(chunks) == 3

    assert (
        chunks[0].audio
        == b"audio-1"
    )

    assert (
        chunks[0].is_final
        is False
    )

    assert (
        chunks[1].audio
        == b"audio-2"
    )

    assert (
        chunks[1].is_final
        is False
    )

    assert chunks[2].audio == b""

    assert (
        chunks[2].is_final
        is True
    )

    assert (
        b"".join(
            chunk.audio
            for chunk in chunks
        )
        == b"audio-1audio-2"
    )


@pytest.mark.asyncio
async def test_streaming_speech_sends_expected_request() -> None:

    client = FakeOpenAIClient(
        chunks=[
            b"audio",
        ]
    )

    provider = OpenAIStreamingSpeechProvider(
        api_key="test-api-key",
        model="gpt-4o-mini-tts",
        client=client,
    )

    chunks = [
        chunk
        async for chunk
        in provider.speak_stream(
            text=" Bonjour Waaxalma ",
            voice_id=" coral ",
            instructions=(
                " Speak clearly "
                "and naturally. "
            ),
        )
    ]

    assert chunks

    request = (
        client
        .audio
        .speech
        .with_streaming_response
        .received_request
    )

    assert request is not None

    assert request == {
        "model":
            "gpt-4o-mini-tts",

        "voice":
            "coral",

        "input":
            "Bonjour Waaxalma",

        "response_format":
            "pcm",

        "instructions":
            (
                "Speak clearly "
                "and naturally."
            ),
    }


@pytest.mark.asyncio
async def test_streaming_speech_metadata() -> None:

    client = FakeOpenAIClient(
        chunks=[
            b"audio",
        ]
    )

    provider = OpenAIStreamingSpeechProvider(
        api_key="test-api-key",
        model="gpt-4o-mini-tts",
        client=client,
    )

    chunks = [
        chunk
        async for chunk
        in provider.speak_stream(
            text="Bonjour",
            voice_id="coral",
        )
    ]

    first = chunks[0]

    assert (
        first.content_type
        == "audio/pcm"
    )

    assert (
        first.sample_rate
        == 24000
    )

    assert first.metadata == {
        "provider":
            "openai",

        "model":
            "gpt-4o-mini-tts",

        "voice_id":
            "coral",
    }


@pytest.mark.asyncio
async def test_empty_speech_text_is_rejected() -> None:

    client = FakeOpenAIClient(
        chunks=[]
    )

    provider = OpenAIStreamingSpeechProvider(
        api_key="test-api-key",
        model="gpt-4o-mini-tts",
        client=client,
    )

    with pytest.raises(
        ValueError,
        match=(
            "Speech text cannot be empty."
        ),
    ):
        chunks = [
            chunk
            async for chunk
            in provider.speak_stream(
                text="   ",
                voice_id="coral",
            )
        ]


@pytest.mark.asyncio
async def test_empty_voice_id_is_rejected() -> None:

    client = FakeOpenAIClient(
        chunks=[]
    )

    provider = OpenAIStreamingSpeechProvider(
        api_key="test-api-key",
        model="gpt-4o-mini-tts",
        client=client,
    )

    with pytest.raises(
        ValueError,
        match=(
            "Voice ID cannot be empty."
        ),
    ):
        chunks = [
            chunk
            async for chunk
            in provider.speak_stream(
                text="Bonjour",
                voice_id="   ",
            )
        ]


def test_provider_rejects_empty_api_key() -> None:

    with pytest.raises(
        ValueError,
        match=(
            "OpenAI API key cannot be empty."
        ),
    ):
        OpenAIStreamingSpeechProvider(
            api_key="   ",
            model="gpt-4o-mini-tts",
        )


def test_provider_rejects_empty_model() -> None:

    with pytest.raises(
        ValueError,
        match=(
            "Streaming speech model "
            "cannot be empty."
        ),
    ):
        OpenAIStreamingSpeechProvider(
            api_key="test-api-key",
            model="   ",
        )