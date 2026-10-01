import httpx
import pytest

from app.providers.openai_streaming_transcription_provider import (
    OpenAIStreamingTranscriptionProvider,
)


@pytest.mark.asyncio
async def test_create_streaming_transcription_session() -> None:
    captured_request: dict = {}

    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        captured_request["method"] = (
            request.method
        )

        captured_request["path"] = (
            request.url.path
        )

        captured_request["authorization"] = (
            request.headers.get(
                "Authorization"
            )
        )

        captured_request["content_type"] = (
            request.headers.get(
                "Content-Type"
            )
        )

        captured_request["json"] = (
            __import__("json")
            .loads(
                request.content
            )
        )

        return httpx.Response(
            status_code=200,
            json={
                "value":
                    "fake-ephemeral-secret",

                "expires_at":
                    1234567890,
            },
        )

    transport = httpx.MockTransport(
        handler
    )

    async with httpx.AsyncClient(
        transport=transport,
    ) as client:
        provider = (
            OpenAIStreamingTranscriptionProvider(
                api_key="test-api-key",
                model="gpt-live-transcribe",
                http_client=client,
            )
        )

        session = (
            await provider.create_session()
        )

    assert (
        captured_request["method"]
        == "POST"
    )

    assert (
        captured_request["path"]
        == "/v1/realtime/client_secrets"
    )

    assert (
        captured_request["authorization"]
        == "Bearer test-api-key"
    )

    assert (
        captured_request["content_type"]
        == "application/json"
    )

    assert captured_request["json"] == {
        "session": {
            "type":
                "transcription",

            "audio": {
                "input": {
                    "format": {
                        "type":
                            "audio/pcm",

                        "rate":
                            24000,
                    },

                    "transcription": {
                        "model":
                            "gpt-live-transcribe",

                        "delay":
                            "low",
                    },

                    "turn_detection":
                        None,
                }
            },
        }
    }

    assert session.provider == "openai"

    assert (
        session.model
        == "gpt-live-transcribe"
    )

    assert (
        session.client_secret
        == "fake-ephemeral-secret"
    )

    assert (
        session.expires_at
        == 1234567890
    )

    assert session.metadata == {
        "transport":
            "webrtc",

        "endpoint":
            "/v1/realtime/calls",

        "session_type":
            "transcription",

        "audio_format":
            "audio/pcm",

        "sample_rate":
            24000,
    }


@pytest.mark.asyncio
async def test_create_streaming_transcription_session_with_context() -> None:
    captured_payload: dict = {}

    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        import json

        captured_payload.update(
            json.loads(
                request.content
            )
        )

        return httpx.Response(
            status_code=200,
            json={
                "value":
                    "context-secret",

                "expires_at":
                    1234567890,
            },
        )

    transport = httpx.MockTransport(
        handler
    )

    async with httpx.AsyncClient(
        transport=transport,
    ) as client:
        provider = (
            OpenAIStreamingTranscriptionProvider(
                api_key="test-api-key",
                model="gpt-live-transcribe",
                http_client=client,
            )
        )

        await provider.create_session(
            languages=[
                "FR",
                " en ",
            ],
            prompt=(
                " Technical discussion about "
                "Waaxalma and AI Gateway. "
            ),
            keywords=[
                " Waaxalma ",
                "Elimane",
                "AI Gateway",
                "",
            ],
            delay="low",
        )

    transcription = (
        captured_payload[
            "session"
        ][
            "audio"
        ][
            "input"
        ][
            "transcription"
        ]
    )

    assert transcription == {
        "model":
            "gpt-live-transcribe",

        "delay":
            "low",

        "languages": [
            "fr",
            "en",
        ],

        "prompt": (
            "Technical discussion about "
            "Waaxalma and AI Gateway."
        ),

        "keywords": [
            "Waaxalma",
            "Elimane",
            "AI Gateway",
        ],
    }


@pytest.mark.asyncio
async def test_empty_optional_context_is_not_sent() -> None:
    captured_payload: dict = {}

    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        import json

        captured_payload.update(
            json.loads(
                request.content
            )
        )

        return httpx.Response(
            status_code=200,
            json={
                "value":
                    "fake-secret",
            },
        )

    transport = httpx.MockTransport(
        handler
    )

    async with httpx.AsyncClient(
        transport=transport,
    ) as client:
        provider = (
            OpenAIStreamingTranscriptionProvider(
                api_key="test-api-key",
                model="gpt-live-transcribe",
                http_client=client,
            )
        )

        await provider.create_session(
            languages=[
                "",
                "   ",
            ],
            prompt="   ",
            keywords=[
                "",
                "   ",
            ],
        )

    transcription = (
        captured_payload[
            "session"
        ][
            "audio"
        ][
            "input"
        ][
            "transcription"
        ]
    )

    assert transcription == {
        "model":
            "gpt-live-transcribe",

        "delay":
            "low",
    }


def test_provider_rejects_empty_api_key() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "OpenAI API key "
            "cannot be empty"
        ),
    ):
        OpenAIStreamingTranscriptionProvider(
            api_key="   ",
            model="gpt-live-transcribe",
        )


def test_provider_rejects_empty_model() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "Streaming transcription model "
            "cannot be empty"
        ),
    ):
        OpenAIStreamingTranscriptionProvider(
            api_key="test-api-key",
            model="   ",
        )