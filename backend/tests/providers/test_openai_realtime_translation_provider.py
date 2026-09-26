import json

import httpx
import pytest

from app.providers.openai_realtime_translation_provider import (
    OpenAIRealtimeTranslationProvider,
)
from app.core.realtime_exceptions import RealtimeTranslationException


@pytest.mark.asyncio
async def test_openai_realtime_provider_creates_session() -> None:
    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert request.method == "POST"

        assert request.url.path == (
            "/v1/realtime/translations/client_secrets"
        )

        assert request.headers[
            "Authorization"
        ] == "Bearer test-api-key"

        body = json.loads(
            request.content.decode()
        )

        assert body == {
            "session": {
                "model": "gpt-realtime-translate",
                "audio": {
                    "output": {
                        "language": "fr",
                    },
                },
            },
        }

        return httpx.Response(
            status_code=200,
            json={
                "value": "ek_test_secret",
                "expires_at": 1234567890,
            },
        )

    transport = httpx.MockTransport(
        handler
    )

    async with httpx.AsyncClient(
        transport=transport,
        base_url="https://api.openai.com",
    ) as client:
        provider = OpenAIRealtimeTranslationProvider(
            api_key="test-api-key",
            model="gpt-realtime-translate",
            http_client=client,
        )

        session = await provider.create_session(
            target_language="fr",
        )

    assert session.provider == "openai"

    assert (
        session.model
        == "gpt-realtime-translate"
    )

    assert session.target_language == "fr"

    assert (
        session.client_secret
        == "ek_test_secret"
    )

    assert session.expires_at == 1234567890

    assert session.voice_id is None

    assert session.metadata == {
        "transport": "webrtc",
        "endpoint": (
            "/v1/realtime/translations"
        ),
    }

def test_openai_realtime_provider_requires_api_key() -> None:
    with pytest.raises(
        ValueError,
        match="API key cannot be empty",
    ):
        OpenAIRealtimeTranslationProvider(
            api_key=" ",
            model="gpt-realtime-translate",
        )

@pytest.mark.asyncio
async def test_openai_realtime_provider_rejects_empty_language() -> None:
    provider = OpenAIRealtimeTranslationProvider(
        api_key="test-api-key",
        model="gpt-realtime-translate",
    )

    with pytest.raises(
        ValueError,
        match="Target language cannot be empty",
    ):
        await provider.create_session(
            target_language=" ",
        )

@pytest.mark.asyncio
async def test_realtime_provider_normalizes_rate_limit() -> None:
    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            status_code=429,
        )

    transport = httpx.MockTransport(
        handler
    )

    async with httpx.AsyncClient(
        transport=transport,
    ) as client:
        provider = (
            OpenAIRealtimeTranslationProvider(
                api_key="test-key",
                model="gpt-realtime-translate",
                http_client=client,
            )
        )

        with pytest.raises(
            RealtimeTranslationException
        ) as exc_info:
            await provider.create_session(
                target_language="fr"
            )

    assert (
        exc_info.value.code
        == "REALTIME_RATE_LIMITED"
    )

    assert (
        exc_info.value.retryable
        is True
    )

