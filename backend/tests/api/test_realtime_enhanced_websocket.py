import base64

from fastapi.testclient import TestClient

import app.api.realtime as realtime_api

from app.core.config import (
    STREAMING_SPEECH_VOICE,
)
from app.core.streaming_speech_chunk import (
    StreamingSpeechChunk,
)
from app.core.streaming_translation_chunk import (
    StreamingTranslationChunk,
)
from app.main import app


client = TestClient(app)


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

        self.received_voice_id = (
            voice_id
        )

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


def receive_commit_events(
    websocket,
) -> list[dict]:
    events: list[dict] = []

    translation_final = False
    audio_final = False

    while not (
        translation_final
        and audio_final
    ):
        event = (
            websocket.receive_json()
        )

        events.append(
            event
        )

        if (
            event["type"]
            == "translation.delta"
            and event["is_final"]
        ):
            translation_final = True

        if (
            event["type"]
            == "audio.delta"
            and event["is_final"]
        ):
            audio_final = True

    return events


def test_websocket_session_start(
    monkeypatch,
) -> None:
    fake_service = (
        FakeRealtimeEnhancedService()
    )

    monkeypatch.setattr(
        realtime_api,
        "realtime_enhanced_service",
        fake_service,
    )

    with client.websocket_connect(
        "/api/realtime/enhanced/stream"
    ) as websocket:

        websocket.send_json(
            {
                "type":
                    "session.start",

                "target_language":
                    "fr",

                "session_id":
                    "session-test-1",
            }
        )

        response = (
            websocket.receive_json()
        )

        assert response == {
            "type":
                "session.ready",

            "session_id":
                "session-test-1",

            "target_language":
                "fr",

            "voice_id":
                STREAMING_SPEECH_VOICE,
        }


def test_websocket_session_start_accepts_voice_configuration(
    monkeypatch,
) -> None:
    fake_service = (
        FakeRealtimeEnhancedService()
    )

    monkeypatch.setattr(
        realtime_api,
        "realtime_enhanced_service",
        fake_service,
    )

    with client.websocket_connect(
        "/api/realtime/enhanced/stream"
    ) as websocket:

        websocket.send_json(
            {
                "type":
                    "session.start",

                "target_language":
                    "fr",

                "session_id":
                    "session-voice",

                "voice_id":
                    " coral ",

                "speech_instructions":
                    " Speak naturally. ",
            }
        )

        response = (
            websocket.receive_json()
        )

        assert (
            response["type"]
            == "session.ready"
        )

        assert (
            response["voice_id"]
            == "coral"
        )

        websocket.send_json(
            {
                "type":
                    "transcript.delta",

                "delta":
                    "Hello",
            }
        )

        websocket.send_json(
            {
                "type":
                    "transcript.commit",
            }
        )

        receive_commit_events(
            websocket
        )

        assert (
            fake_service.received_voice_id
            == "coral"
        )

        assert (
            fake_service
            .received_speech_instructions
            == "Speak naturally."
        )


def test_websocket_requires_session_start(
    monkeypatch,
) -> None:
    fake_service = (
        FakeRealtimeEnhancedService()
    )

    monkeypatch.setattr(
        realtime_api,
        "realtime_enhanced_service",
        fake_service,
    )

    with client.websocket_connect(
        "/api/realtime/enhanced/stream"
    ) as websocket:

        websocket.send_json(
            {
                "type":
                    "transcript.delta",

                "delta":
                    "Hello",
            }
        )

        response = (
            websocket.receive_json()
        )

        assert response == {
            "type":
                "error",

            "code":
                "SESSION_NOT_STARTED",

            "message":
                (
                    "session.start must "
                    "be sent first."
                ),
        }


def test_websocket_transcript_commit_streams_translation_and_audio(
    monkeypatch,
) -> None:
    fake_service = (
        FakeRealtimeEnhancedService()
    )

    monkeypatch.setattr(
        realtime_api,
        "realtime_enhanced_service",
        fake_service,
    )

    with client.websocket_connect(
        "/api/realtime/enhanced/stream"
    ) as websocket:

        websocket.send_json(
            {
                "type":
                    "session.start",

                "target_language":
                    "fr",

                "context":
                    "Waaxalma is a product name.",

                "terminology": [
                    "Waaxalma",
                    "Elimane",
                ],

                "session_id":
                    "session-test-2",

                "voice_id":
                    "coral",
            }
        )

        ready = (
            websocket.receive_json()
        )

        assert (
            ready["type"]
            == "session.ready"
        )

        websocket.send_json(
            {
                "type":
                    "transcript.delta",

                "delta":
                    "Hello ",
            }
        )

        websocket.send_json(
            {
                "type":
                    "transcript.delta",

                "delta":
                    "Waaxalma",
            }
        )

        websocket.send_json(
            {
                "type":
                    "transcript.commit",
            }
        )

        events = (
            receive_commit_events(
                websocket
            )
        )

        translation_events = [
            event
            for event in events
            if (
                event["type"]
                == "translation.delta"
            )
        ]

        audio_events = [
            event
            for event in events
            if (
                event["type"]
                == "audio.delta"
            )
        ]

        assert (
            len(translation_events)
            == 3
        )

        assert (
            len(audio_events)
            == 3
        )

        assert (
            translation_events[0]["text"]
            == "Bon"
        )

        assert (
            translation_events[0]["is_final"]
            is False
        )

        assert (
            translation_events[1]["text"]
            == "jour"
        )

        assert (
            translation_events[1]["is_final"]
            is False
        )

        assert (
            translation_events[2]["text"]
            == ""
        )

        assert (
            translation_events[2]["is_final"]
            is True
        )

        assert (
            fake_service.received_text
            == "Hello Waaxalma"
        )

        assert (
            fake_service
            .received_target_language
            == "fr"
        )

        assert (
            fake_service.received_context
            == "Waaxalma is a product name."
        )

        assert (
            fake_service.received_terminology
            == [
                "Waaxalma",
                "Elimane",
            ]
        )

        assert (
            fake_service.received_speech_text
            == "Bonjour"
        )


def test_websocket_audio_is_base64_encoded(
    monkeypatch,
) -> None:
    fake_service = (
        FakeRealtimeEnhancedService()
    )

    monkeypatch.setattr(
        realtime_api,
        "realtime_enhanced_service",
        fake_service,
    )

    with client.websocket_connect(
        "/api/realtime/enhanced/stream"
    ) as websocket:

        websocket.send_json(
            {
                "type":
                    "session.start",

                "target_language":
                    "fr",

                "session_id":
                    "session-audio",

                "voice_id":
                    "coral",
            }
        )

        websocket.receive_json()

        websocket.send_json(
            {
                "type":
                    "transcript.delta",

                "delta":
                    "Hello",
            }
        )

        websocket.send_json(
            {
                "type":
                    "transcript.commit",
            }
        )

        events = (
            receive_commit_events(
                websocket
            )
        )

        audio_events = [
            event
            for event in events
            if (
                event["type"]
                == "audio.delta"
            )
        ]

        assert audio_events

        first_audio = (
            audio_events[0]
        )

        assert (
            base64.b64decode(
                first_audio["audio"]
            )
            == b"audio-1"
        )

        assert (
            first_audio["content_type"]
            == "audio/pcm"
        )

        assert (
            first_audio["sample_rate"]
            == 24000
        )

        assert (
            first_audio["is_final"]
            is False
        )

        final_audio = (
            audio_events[-1]
        )

        assert (
            base64.b64decode(
                final_audio["audio"]
            )
            == b""
        )

        assert (
            final_audio["is_final"]
            is True
        )


def test_websocket_translation_metadata_contains_session_and_segment(
    monkeypatch,
) -> None:
    fake_service = (
        FakeRealtimeEnhancedService()
    )

    monkeypatch.setattr(
        realtime_api,
        "realtime_enhanced_service",
        fake_service,
    )

    with client.websocket_connect(
        "/api/realtime/enhanced/stream"
    ) as websocket:

        websocket.send_json(
            {
                "type":
                    "session.start",

                "target_language":
                    "fr",

                "session_id":
                    "session-metadata",
            }
        )

        websocket.receive_json()

        websocket.send_json(
            {
                "type":
                    "transcript.delta",

                "delta":
                    "Hello",
            }
        )

        websocket.send_json(
            {
                "type":
                    "transcript.commit",
            }
        )

        events = (
            receive_commit_events(
                websocket
            )
        )

        translation_events = [
            event
            for event in events
            if (
                event["type"]
                == "translation.delta"
            )
        ]

        assert translation_events

        metadata = (
            translation_events[0][
                "metadata"
            ]
        )

        assert (
            metadata["provider"]
            == "fake"
        )

        assert (
            metadata["session_id"]
            == "session-metadata"
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


def test_websocket_audio_metadata_contains_session_and_segments(
    monkeypatch,
) -> None:
    fake_service = (
        FakeRealtimeEnhancedService()
    )

    monkeypatch.setattr(
        realtime_api,
        "realtime_enhanced_service",
        fake_service,
    )

    with client.websocket_connect(
        "/api/realtime/enhanced/stream"
    ) as websocket:

        websocket.send_json(
            {
                "type":
                    "session.start",

                "target_language":
                    "fr",

                "session_id":
                    "session-audio-metadata",
            }
        )

        websocket.receive_json()

        websocket.send_json(
            {
                "type":
                    "transcript.delta",

                "delta":
                    "Hello",
            }
        )

        websocket.send_json(
            {
                "type":
                    "transcript.commit",
            }
        )

        events = (
            receive_commit_events(
                websocket
            )
        )

        audio_events = [
            event
            for event in events
            if (
                event["type"]
                == "audio.delta"
            )
        ]

        assert audio_events

        metadata = (
            audio_events[0][
                "metadata"
            ]
        )

        assert (
            metadata["provider"]
            == "fake"
        )

        assert (
            metadata["session_id"]
            == "session-audio-metadata"
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


def test_websocket_reset_resets_segment_sequences(
    monkeypatch,
) -> None:
    fake_service = (
        FakeRealtimeEnhancedService()
    )

    monkeypatch.setattr(
        realtime_api,
        "realtime_enhanced_service",
        fake_service,
    )

    with client.websocket_connect(
        "/api/realtime/enhanced/stream"
    ) as websocket:

        websocket.send_json(
            {
                "type":
                    "session.start",

                "target_language":
                    "fr",

                "session_id":
                    "session-reset",
            }
        )

        websocket.receive_json()

        websocket.send_json(
            {
                "type":
                    "transcript.delta",

                "delta":
                    "First",
            }
        )

        websocket.send_json(
            {
                "type":
                    "transcript.commit",
            }
        )

        first_events = (
            receive_commit_events(
                websocket
            )
        )

        first_translation = next(
            event
            for event in first_events
            if (
                event["type"]
                == "translation.delta"
            )
        )

        first_audio = next(
            event
            for event in first_events
            if (
                event["type"]
                == "audio.delta"
            )
        )

        assert (
            first_translation[
                "metadata"
            ][
                "source_segment_sequence"
            ]
            == 1
        )

        assert (
            first_audio[
                "metadata"
            ][
                "speech_segment_sequence"
            ]
            == 1
        )

        websocket.send_json(
            {
                "type":
                    "session.reset",
            }
        )

        websocket.send_json(
            {
                "type":
                    "transcript.delta",

                "delta":
                    "After reset",
            }
        )

        websocket.send_json(
            {
                "type":
                    "transcript.commit",
            }
        )

        second_events = (
            receive_commit_events(
                websocket
            )
        )

        second_translation = next(
            event
            for event in second_events
            if (
                event["type"]
                == "translation.delta"
            )
        )

        second_audio = next(
            event
            for event in second_events
            if (
                event["type"]
                == "audio.delta"
            )
        )

        assert (
            second_translation[
                "metadata"
            ][
                "source_segment_sequence"
            ]
            == 1
        )

        assert (
            second_audio[
                "metadata"
            ][
                "speech_segment_sequence"
            ]
            == 1
        )


def test_websocket_source_segment_sequence_increments(
    monkeypatch,
) -> None:
    fake_service = (
        FakeRealtimeEnhancedService()
    )

    monkeypatch.setattr(
        realtime_api,
        "realtime_enhanced_service",
        fake_service,
    )

    with client.websocket_connect(
        "/api/realtime/enhanced/stream"
    ) as websocket:

        websocket.send_json(
            {
                "type":
                    "session.start",

                "target_language":
                    "fr",

                "session_id":
                    "session-sequence",
            }
        )

        websocket.receive_json()

        websocket.send_json(
            {
                "type":
                    "transcript.delta",

                "delta":
                    "First",
            }
        )

        websocket.send_json(
            {
                "type":
                    "transcript.commit",
            }
        )

        first_events = (
            receive_commit_events(
                websocket
            )
        )

        websocket.send_json(
            {
                "type":
                    "transcript.delta",

                "delta":
                    "Second",
            }
        )

        websocket.send_json(
            {
                "type":
                    "transcript.commit",
            }
        )

        second_events = (
            receive_commit_events(
                websocket
            )
        )

        first_translation = next(
            event
            for event in first_events
            if (
                event["type"]
                == "translation.delta"
            )
        )

        second_translation = next(
            event
            for event in second_events
            if (
                event["type"]
                == "translation.delta"
            )
        )

        assert (
            first_translation[
                "metadata"
            ][
                "source_segment_sequence"
            ]
            == 1
        )

        assert (
            second_translation[
                "metadata"
            ][
                "source_segment_sequence"
            ]
            == 2
        )


def test_websocket_unknown_event_returns_error(
    monkeypatch,
) -> None:
    fake_service = (
        FakeRealtimeEnhancedService()
    )

    monkeypatch.setattr(
        realtime_api,
        "realtime_enhanced_service",
        fake_service,
    )

    with client.websocket_connect(
        "/api/realtime/enhanced/stream"
    ) as websocket:

        websocket.send_json(
            {
                "type":
                    "session.start",

                "target_language":
                    "fr",
            }
        )

        websocket.receive_json()

        websocket.send_json(
            {
                "type":
                    "something.unknown",
            }
        )

        response = (
            websocket.receive_json()
        )

        assert (
            response["type"]
            == "error"
        )

        assert (
            response["code"]
            == "UNKNOWN_EVENT"
        )

        assert (
            "something.unknown"
            in response["message"]
        )