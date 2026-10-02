import pytest

from app.core.streaming_transcription_session import (
    StreamingTranscriptionSession,
)
from app.registry.provider_registry import (
    ProviderRegistry,
)
from app.services.realtime_enhanced_service import (
    RealtimeEnhancedService,
)

from app.core.streaming_translation_chunk import (
    StreamingTranslationChunk,
)

from app.core.streaming_speech_chunk import (
    StreamingSpeechChunk,
)



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
            audio=b"audio-1",
            content_type="audio/pcm",
            sample_rate=24000,
        )

        yield StreamingSpeechChunk(
            audio=b"",
            is_final=True,
            content_type="audio/pcm",
            sample_rate=24000,
        )

class FakeStreamingTranslationProvider:

    def __init__(self) -> None:
        self.received_text: str | None = None
        self.received_target_language: str | None = None
        self.received_context: str | None = None
        self.received_terminology: list[str] | None = None

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
        self.received_text = text

        self.received_target_language = (
            target_language
        )

        self.received_context = context

        self.received_terminology = (
            terminology
        )

        yield StreamingTranslationChunk(
            text="Bon",
        )

        yield StreamingTranslationChunk(
            text="jour",
        )

        yield StreamingTranslationChunk(
            text="",
            is_final=True,
        )


class FakeStreamingTranscriptionProvider:

    def __init__(self) -> None:
        self.received_languages: list[str] | None = None
        self.received_prompt: str | None = None
        self.received_keywords: list[str] | None = None
        self.received_delay: str | None = None

    @property
    def name(self) -> str:
        return "fake"

    @property
    def model(self) -> str:
        return "fake-streaming-transcription-model"

    async def create_session(
        self,
        *,
        languages: list[str] | None = None,
        prompt: str | None = None,
        keywords: list[str] | None = None,
        delay: str = "low",
    ) -> StreamingTranscriptionSession:

        self.received_languages = languages
        self.received_prompt = prompt
        self.received_keywords = keywords
        self.received_delay = delay

        return StreamingTranscriptionSession(
            provider=self.name,
            model=self.model,
            client_secret="fake-client-secret",
            expires_at=1234567890,
            metadata={
                "transport": "webrtc",
                "session_type": "transcription",
            },
        )


def build_service(
    transcription_provider: FakeStreamingTranscriptionProvider,
    translation_provider: FakeStreamingTranslationProvider | None = None,
    speech_provider: FakeStreamingSpeechProvider | None = None,
) -> RealtimeEnhancedService:

    registry = ProviderRegistry()

    if translation_provider is None:
        translation_provider = (
            FakeStreamingTranslationProvider()
        )

    if speech_provider is None:
        speech_provider = (
            FakeStreamingSpeechProvider()
        )

    registry.register(
        capability="streaming_transcription",
        name=transcription_provider.name,
        provider=transcription_provider,
    )

    registry.register(
        capability="streaming_translation",
        name=translation_provider.name,
        provider=translation_provider,
    )

    registry.register(
        capability="streaming_speech",
        name=speech_provider.name,
        provider=speech_provider,
    )

    return RealtimeEnhancedService(
        provider_registry=registry,
        transcription_provider_name=(
            transcription_provider.name
        ),
        translation_provider_name=(
            translation_provider.name
        ),
        speech_provider_name=(
            speech_provider.name
        ),
    )


@pytest.mark.asyncio
async def test_create_enhanced_session() -> None:
    provider = FakeStreamingTranscriptionProvider()

    service = build_service(provider)

    session = await service.create_session(
        target_language="FR",
        source_languages=[
            "wo",
            "fr",
        ],
        prompt=(
            "Conversation about Waaxalma "
            "and AI Gateway."
        ),
        keywords=[
            "Waaxalma",
            "Elimane",
            "Dakar",
        ],
    )

    assert session.mode == "enhanced"

    assert (
        session.transcription_provider
        == "fake"
    )

    assert (
        session.transcription_model
        == "fake-streaming-transcription-model"
    )

    assert (
        session.target_language
        == "fr"
    )

    assert (
        session.client_secret
        == "fake-client-secret"
    )

    assert (
        session.expires_at
        == 1234567890
    )

    assert session.metadata == {
        "transport": "webrtc",
        "session_type": "transcription",
        "mode": "enhanced",
        "stage": "streaming_transcription",
    }


@pytest.mark.asyncio
async def test_create_enhanced_session_forwards_context() -> None:
    provider = FakeStreamingTranscriptionProvider()

    service = build_service(provider)

    await service.create_session(
        target_language="en",
        source_languages=[
            "wo",
            "fr",
        ],
        prompt="Waaxalma technical discussion",
        keywords=[
            "Waaxalma",
            "Elimane",
        ],
    )

    assert provider.received_languages == [
        "wo",
        "fr",
    ]

    assert (
        provider.received_prompt
        == "Waaxalma technical discussion"
    )

    assert provider.received_keywords == [
        "Waaxalma",
        "Elimane",
    ]

    assert (
        provider.received_delay
        == "low"
    )


@pytest.mark.asyncio
async def test_create_enhanced_session_accepts_optional_context() -> None:
    provider = FakeStreamingTranscriptionProvider()

    service = build_service(provider)

    session = await service.create_session(
        target_language="es",
    )

    assert (
        session.target_language
        == "es"
    )

    assert (
        provider.received_languages
        is None
    )

    assert (
        provider.received_prompt
        is None
    )

    assert (
        provider.received_keywords
        is None
    )

    assert (
        provider.received_delay
        == "low"
    )


@pytest.mark.asyncio
async def test_target_language_is_normalized() -> None:
    provider = FakeStreamingTranscriptionProvider()

    service = build_service(provider)

    session = await service.create_session(
        target_language=" FR ",
    )

    assert (
        session.target_language
        == "fr"
    )


@pytest.mark.asyncio
async def test_empty_target_language_is_rejected() -> None:
    provider = FakeStreamingTranscriptionProvider()

    service = build_service(provider)

    with pytest.raises(
        ValueError,
        match="Target language cannot be empty.",
    ):
        await service.create_session(
            target_language="   ",
        )

@pytest.mark.asyncio
async def test_translate_stream_emits_translation_chunks() -> None:
    transcription_provider = (
        FakeStreamingTranscriptionProvider()
    )

    translation_provider = (
        FakeStreamingTranslationProvider()
    )

    service = build_service(
        transcription_provider,
        translation_provider,
    )

    chunks = [
        chunk
        async for chunk
        in service.translate_stream(
            text="Hello",
            target_language="fr",
        )
    ]

    assert len(chunks) == 3

    assert chunks[0].text == "Bon"
    assert chunks[0].is_final is False

    assert chunks[1].text == "jour"
    assert chunks[1].is_final is False

    assert chunks[2].text == ""
    assert chunks[2].is_final is True

    translated_text = "".join(
        chunk.text
        for chunk in chunks
    )

    assert translated_text == "Bonjour"

@pytest.mark.asyncio
async def test_translate_stream_forwards_context_and_terminology() -> None:
    transcription_provider = (
        FakeStreamingTranscriptionProvider()
    )

    translation_provider = (
        FakeStreamingTranslationProvider()
    )

    service = build_service(
        transcription_provider,
        translation_provider,
    )

    chunks = [
        chunk
        async for chunk
        in service.translate_stream(
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
        translation_provider.received_text
        == "Hello Waaxalma"
    )

    assert (
        translation_provider.received_target_language
        == "fr"
    )

    assert (
        translation_provider.received_context
        == "Waaxalma is the product name."
    )

    assert (
        translation_provider.received_terminology
        == [
            "Waaxalma",
            "Elimane",
        ]
    )

@pytest.mark.asyncio
async def test_enhanced_service_uses_independent_streaming_capabilities() -> None:
    transcription_provider = (
        FakeStreamingTranscriptionProvider()
    )

    translation_provider = (
        FakeStreamingTranslationProvider()
    )

    service = build_service(
        transcription_provider,
        translation_provider,
    )

    session = await service.create_session(
        target_language="fr",
    )

    chunks = [
        chunk
        async for chunk
        in service.translate_stream(
            text="Hello",
            target_language="fr",
        )
    ]

    assert (
        session.transcription_model
        == "fake-streaming-transcription-model"
    )

    assert (
        translation_provider.model
        == "fake-streaming-translation-model"
    )

    assert chunks

@pytest.mark.asyncio
async def test_speak_stream_emits_audio_chunks() -> None:
    transcription_provider = (
        FakeStreamingTranscriptionProvider()
    )

    translation_provider = (
        FakeStreamingTranslationProvider()
    )

    speech_provider = (
        FakeStreamingSpeechProvider()
    )

    service = build_service(
        transcription_provider,
        translation_provider,
        speech_provider,
    )

    chunks = [
        chunk
        async for chunk
        in service.speak_stream(
            text="Bonjour",
            voice_id="coral",
            instructions=(
                "Speak clearly."
            ),
        )
    ]

    assert len(chunks) == 2

    assert (
        chunks[0].audio
        == b"audio-1"
    )

    assert (
        chunks[1].is_final
        is True
    )

    assert (
        speech_provider.received_text
        == "Bonjour"
    )

    assert (
        speech_provider.received_voice_id
        == "coral"
    )

    assert (
        speech_provider.received_instructions
        == "Speak clearly."
    )