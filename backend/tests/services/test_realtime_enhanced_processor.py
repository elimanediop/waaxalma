import pytest

from app.core.realtime_enhanced_runtime import (
    RealtimeEnhancedRuntime,
)
from app.core.streaming_speech_chunk import (
    StreamingSpeechChunk,
)
from app.core.streaming_translation_chunk import (
    StreamingTranslationChunk,
)
from app.services.realtime_enhanced_processor import (
    RealtimeEnhancedProcessor,
)



class FakeRealtimeEnhancedService:

    def __init__(self) -> None:
        self.received_text: str | None = None

        self.received_target_language: str | None = None

        self.received_context: str | None = None

        self.received_terminology: list[str] | None = None

        self.received_speech_text: str | None = None

        self.received_voice_id: str | None = None

        self.received_speech_instructions: str | None = None

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
            metadata={
                "provider": "fake",
            },
        )

        yield StreamingTranslationChunk(
            text="jour",
            metadata={
                "provider": "fake",
            },
        )

        yield StreamingTranslationChunk(
            text="",
            is_final=True,
            metadata={
                "provider": "fake",
            },
        )

    async def speak_stream(
        self,
        *,
        text: str,
        voice_id: str,
        instructions: str | None = None,
    ):
        self.received_speech_text = text

        self.received_voice_id = voice_id

        self.received_speech_instructions = (
            instructions
        )

        yield StreamingSpeechChunk(
            audio=b"audio-1",
            content_type="audio/pcm",
            sample_rate=24000,
            metadata={
                "provider": "fake",
            },
        )

        yield StreamingSpeechChunk(
            audio=b"audio-2",
            content_type="audio/pcm",
            sample_rate=24000,
            metadata={
                "provider": "fake",
            },
        )

        yield StreamingSpeechChunk(
            audio=b"",
            is_final=True,
            content_type="audio/pcm",
            sample_rate=24000,
            metadata={
                "provider": "fake",
            },
        )


def build_processor(
    *,
    target_language: str = "fr",
    context: str | None = None,
    terminology: list[str] | None = None,
    session_id: str = "session-123",
    speakable_soft_max_chars: int = 80,
):
    runtime = RealtimeEnhancedRuntime(
        target_language=target_language,
        context=context,
        terminology=terminology,
        session_id=session_id,
    )

    service = FakeRealtimeEnhancedService()

    processor = RealtimeEnhancedProcessor(
        runtime=runtime,
        service=service,
        speakable_soft_max_chars=(
            speakable_soft_max_chars
        ),
    )

    return processor, service


def test_processor_accumulates_transcript_deltas() -> None:
    processor, _ = build_processor()

    processor.append_transcript_delta(
        "Hello"
    )

    processor.append_transcript_delta(
        " "
    )

    processor.append_transcript_delta(
        "world"
    )

    assert (
        processor.pending_transcript
        == "Hello world"
    )


@pytest.mark.asyncio
async def test_commit_translates_stable_segment() -> None:
    processor, service = build_processor()

    processor.append_transcript_delta(
        "Hello"
    )

    processor.append_transcript_delta(
        " "
    )

    processor.append_transcript_delta(
        "world"
    )

    chunks = [
        chunk
        async for chunk
        in processor.commit_and_translate()
    ]

    assert (
        service.received_text
        == "Hello world"
    )

    assert (
        service.received_target_language
        == "fr"
    )

    assert len(chunks) == 3

    assert (
        "".join(
            chunk.text
            for chunk in chunks
        )
        == "Bonjour"
    )

    assert (
        processor.pending_transcript
        == ""
    )


@pytest.mark.asyncio
async def test_processor_forwards_context_and_terminology() -> None:
    processor, service = build_processor(
        context=(
            "Waaxalma is a product name."
        ),
        terminology=[
            "Waaxalma",
            "Elimane",
        ],
    )

    processor.append_transcript_delta(
        "Hello Waaxalma"
    )

    chunks = [
        chunk
        async for chunk
        in processor.commit_and_translate()
    ]

    assert chunks

    assert (
        service.received_context
        == "Waaxalma is a product name."
    )

    assert (
        service.received_terminology
        == [
            "Waaxalma",
            "Elimane",
        ]
    )


@pytest.mark.asyncio
async def test_processor_enriches_translation_chunk_metadata() -> None:
    processor, _ = build_processor(
        session_id="session-abc",
        target_language="fr",
    )

    processor.append_transcript_delta(
        "Hello"
    )

    chunks = [
        chunk
        async for chunk
        in processor.commit_and_translate()
    ]

    assert chunks

    for chunk in chunks:
        assert (
            chunk.metadata["provider"]
            == "fake"
        )

        assert (
            chunk.metadata["session_id"]
            == "session-abc"
        )

        assert (
            chunk.metadata["segment_sequence"]
            == 1
        )

        assert (
            chunk.metadata["target_language"]
            == "fr"
        )


@pytest.mark.asyncio
async def test_empty_commit_does_not_translate() -> None:
    processor, service = build_processor()

    chunks = [
        chunk
        async for chunk
        in processor.commit_and_translate()
    ]

    assert chunks == []

    assert (
        service.received_text
        is None
    )


@pytest.mark.asyncio
async def test_segment_sequence_increments() -> None:
    processor, _ = build_processor()

    processor.append_transcript_delta(
        "First"
    )

    first_chunks = [
        chunk
        async for chunk
        in processor.commit_and_translate()
    ]

    processor.append_transcript_delta(
        "Second"
    )

    second_chunks = [
        chunk
        async for chunk
        in processor.commit_and_translate()
    ]

    assert (
        first_chunks[0]
        .metadata["segment_sequence"]
        == 1
    )

    assert (
        second_chunks[0]
        .metadata["segment_sequence"]
        == 2
    )


@pytest.mark.asyncio
async def test_processor_reset_resets_segment_sequence() -> None:
    processor, _ = build_processor()

    processor.append_transcript_delta(
        "Before reset"
    )

    first = [
        chunk
        async for chunk
        in processor.commit_and_translate()
    ]

    assert (
        first[0]
        .metadata["segment_sequence"]
        == 1
    )

    processor.reset()

    processor.append_transcript_delta(
        "After reset"
    )

    second = [
        chunk
        async for chunk
        in processor.commit_and_translate()
    ]

    assert (
        second[0]
        .metadata["segment_sequence"]
        == 1
    )


@pytest.mark.asyncio
async def test_commit_translate_and_speak_emits_text_and_audio() -> None:
    processor, service = build_processor()

    processor.append_transcript_delta(
        "Hello"
    )

    events = [
        event
        async for event
        in processor.commit_translate_and_speak(
            voice_id="coral",
            speech_instructions=(
                "Speak naturally."
            ),
        )
    ]

    translation_events = [
        event
        for event in events
        if event.type == "translation"
    ]

    speech_events = [
        event
        for event in events
        if event.type == "speech"
    ]

    assert translation_events
    assert speech_events

    assert (
        "".join(
            event.chunk.text
            for event in translation_events
        )
        == "Bonjour"
    )

    assert (
        service.received_speech_text
        == "Bonjour"
    )

    assert (
        service.received_voice_id
        == "coral"
    )

    assert (
        service.received_speech_instructions
        == "Speak naturally."
    )

    assert (
        speech_events[0].chunk.audio
        == b"audio-1"
    )

    assert (
        speech_events[1].chunk.audio
        == b"audio-2"
    )

    assert (
        speech_events[-1]
        .chunk
        .is_final
        is True
    )


@pytest.mark.asyncio
async def test_speech_chunks_keep_session_and_segment_metadata() -> None:
    processor, _ = build_processor(
        session_id="session-audio",
    )

    processor.append_transcript_delta(
        "Hello"
    )

    events = [
        event
        async for event
        in processor.commit_translate_and_speak(
            voice_id="coral",
        )
    ]

    speech_events = [
        event
        for event in events
        if event.type == "speech"
    ]

    assert speech_events

    for event in speech_events:
        metadata = event.chunk.metadata

        assert (
            metadata["provider"]
            == "fake"
        )

        assert (
            metadata["session_id"]
            == "session-audio"
        )

        assert (
            metadata[
                "source_segment_sequence"
            ]
            == 1
        )

        assert (
            metadata[
                "speech_segment_sequence"
            ]
            == 1
        )

        assert (
            metadata["target_language"]
            == "fr"
        )


@pytest.mark.asyncio
async def test_translation_chunks_keep_source_segment_metadata() -> None:
    processor, _ = build_processor(
        session_id="session-translation",
        target_language="fr",
    )

    processor.append_transcript_delta(
        "Hello"
    )

    events = [
        event
        async for event
        in processor.commit_translate_and_speak(
            voice_id="coral",
        )
    ]

    translation_events = [
        event
        for event in events
        if event.type == "translation"
    ]

    assert translation_events

    for event in translation_events:
        metadata = event.chunk.metadata

        assert (
            metadata["provider"]
            == "fake"
        )

        assert (
            metadata["session_id"]
            == "session-translation"
        )

        assert (
            metadata[
                "source_segment_sequence"
            ]
            == 1
        )

        assert (
            metadata["target_language"]
            == "fr"
        )


@pytest.mark.asyncio
async def test_commit_translate_and_speak_without_text_returns_no_events() -> None:
    processor, service = build_processor()

    events = [
        event
        async for event
        in processor.commit_translate_and_speak(
            voice_id="coral",
        )
    ]

    assert events == []

    assert (
        service.received_text
        is None
    )

    assert (
        service.received_speech_text
        is None
    )


@pytest.mark.asyncio
async def test_speakable_buffer_flushes_translation_at_end() -> None:
    processor, service = build_processor(
        speakable_soft_max_chars=80,
    )

    processor.append_transcript_delta(
        "Hello"
    )

    events = [
        event
        async for event
        in processor.commit_translate_and_speak(
            voice_id="coral",
        )
    ]

    speech_events = [
        event
        for event in events
        if event.type == "speech"
    ]

    assert speech_events

    assert (
        service.received_speech_text
        == "Bonjour"
    )


@pytest.mark.asyncio
async def test_processor_reset_resets_speech_segment_sequence() -> None:
    processor, _ = build_processor(
        session_id="session-reset",
    )

    processor.append_transcript_delta(
        "First"
    )

    first_events = [
        event
        async for event
        in processor.commit_translate_and_speak(
            voice_id="coral",
        )
    ]

    first_speech_events = [
        event
        for event in first_events
        if event.type == "speech"
    ]

    assert first_speech_events

    assert (
        first_speech_events[0]
        .chunk
        .metadata[
            "speech_segment_sequence"
        ]
        == 1
    )

    processor.reset()

    processor.append_transcript_delta(
        "Second"
    )

    second_events = [
        event
        async for event
        in processor.commit_translate_and_speak(
            voice_id="coral",
        )
    ]

    second_speech_events = [
        event
        for event in second_events
        if event.type == "speech"
    ]

    assert second_speech_events

    assert (
        second_speech_events[0]
        .chunk
        .metadata[
            "speech_segment_sequence"
        ]
        == 1
    )


@pytest.mark.asyncio
async def test_source_segment_sequence_increments_with_audio_pipeline() -> None:
    processor, _ = build_processor(
        session_id="session-sequence",
    )

    processor.append_transcript_delta(
        "First"
    )

    first_events = [
        event
        async for event
        in processor.commit_translate_and_speak(
            voice_id="coral",
        )
    ]

    processor.append_transcript_delta(
        "Second"
    )

    second_events = [
        event
        async for event
        in processor.commit_translate_and_speak(
            voice_id="coral",
        )
    ]

    first_translation = next(
        event
        for event in first_events
        if event.type == "translation"
    )

    second_translation = next(
        event
        for event in second_events
        if event.type == "translation"
    )

    assert (
        first_translation
        .chunk
        .metadata[
            "source_segment_sequence"
        ]
        == 1
    )

    assert (
        second_translation
        .chunk
        .metadata[
            "source_segment_sequence"
        ]
        == 2
    )