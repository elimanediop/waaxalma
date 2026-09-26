from fastapi.testclient import TestClient

import app.api.realtime as realtime_api

from app.core.realtime_translation_session import (
    RealtimeTranslationSession,
)

from app.core.realtime_exceptions import (
    RealtimeTranslationException,
)

from prometheus_client import REGISTRY

from app.core.config import (
    REALTIME_TRANSLATION_MODEL,
    REALTIME_TRANSLATION_PROVIDER,
)

from app.main import app


client = TestClient(app)


class FakeRealtimeTranslationService:

    async def create_session(
        self,
        *,
        target_language: str,
    ) -> RealtimeTranslationSession:
        return RealtimeTranslationSession(
            provider="fake",
            model="fake-realtime-model",
            target_language=target_language,
            client_secret="fake-client-secret",
            expires_at=1234567890,
            voice_id=None,
            metadata={
                "transport": "webrtc",
            },
        )


def test_create_realtime_translation_session(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        realtime_api,
        "realtime_translation_service",
        FakeRealtimeTranslationService(),
    )

    response = client.post(
        "/api/realtime/translation/session",
        json={
            "target_language": "fr",
        },
    )

    assert response.status_code == 200

    assert response.json() == {
        "provider": "fake",
        "model": "fake-realtime-model",
        "target_language": "fr",
        "client_secret": "fake-client-secret",
        "expires_at": 1234567890,
        "voice_id": None,
        "metadata": {
            "transport": "webrtc",
        },
    }

def test_realtime_translation_requires_target_language() -> None:
    response = client.post(
        "/api/realtime/translation/session",
        json={},
    )

    assert response.status_code == 422

def test_realtime_translation_rejects_empty_target_language() -> None:
    response = client.post(
        "/api/realtime/translation/session",
        json={
            "target_language": "",
        },
    )

    assert response.status_code == 422


def test_realtime_translation_rejects_blank_target_language() -> None:
    response = client.post(
        "/api/realtime/translation/session",
        json={
            "target_language": "   ",
        },
    )

    assert response.status_code == 422

def test_realtime_provider_error_is_normalized(
    monkeypatch,
) -> None:

    class FailingService:

        async def create_session(
            self,
            *,
            target_language: str,
        ):
            raise RealtimeTranslationException(
                code="REALTIME_RATE_LIMITED",
                message=(
                    "Realtime translation provider "
                    "rate limit exceeded."
                ),
                provider="openai",
                retryable=True,
                status_code=503,
            )

    monkeypatch.setattr(
        realtime_api,
        "realtime_translation_service",
        FailingService(),
    )

    response = client.post(
        "/api/realtime/translation/session",
        json={
            "target_language": "fr",
        },
    )

    assert response.status_code == 503

    assert response.json() == {
        "detail": {
            "code": "REALTIME_RATE_LIMITED",
            "message": (
                "Realtime translation provider "
                "rate limit exceeded."
            ),
            "details": {
                "provider": "openai",
                "retryable": True,
            },
        }
    }

def test_realtime_client_metrics_are_accepted() -> None:

    response = client.post(
        "/api/realtime/metrics",
        json={
            "session_request_ms": 1613.3,
            "webrtc_connection_ms": 1841.0,
            "speech_to_first_translation_ms": 390.3,
            "speech_to_first_audio_ms": 1350.5,
        },
    )

    assert response.status_code == 200

    assert response.json() == {
        "recorded": 4,
    }

def test_realtime_client_metrics_reject_unknown_metric() -> None:

    response = client.post(
        "/api/realtime/metrics",
        json={
            "totally_random_metric": 123,
        },
    )

    assert response.status_code == 422

def test_realtime_client_metrics_are_accepted() -> None:
    response = client.post(
        "/api/realtime/metrics",
        json={
            "session_request_ms": 1613.3,
            "webrtc_connection_ms": 1841.0,
            "speech_to_first_translation_ms": 390.3,
            "speech_to_first_audio_ms": 1350.5,
        },
    )

    assert response.status_code == 200

    assert response.json() == {
        "recorded": 4,
    }

def test_realtime_client_metrics_accept_partial_payload() -> None:
    response = client.post(
        "/api/realtime/metrics",
        json={
            "session_request_ms": 1500.0,
            "webrtc_connection_ms": 1900.0,
        },
    )

    assert response.status_code == 200

    assert response.json() == {
        "recorded": 2,
    }

def test_realtime_client_metrics_reject_unknown_metric() -> None:
    response = client.post(
        "/api/realtime/metrics",
        json={
            "speech_to_first_audio_ms": 1200.0,
            "unknown_metric": 42.0,
        },
    )

    assert response.status_code == 422

def test_realtime_client_metrics_reject_negative_latency() -> None:
    response = client.post(
        "/api/realtime/metrics",
        json={
            "speech_to_first_translation_ms": -1.0,
        },
    )

    assert response.status_code == 422

def test_realtime_client_metrics_reject_excessive_latency() -> None:
    response = client.post(
        "/api/realtime/metrics",
        json={
            "speech_to_first_audio_ms": 120_001.0,
        },
    )

    assert response.status_code == 422

def test_realtime_client_metrics_are_observed_in_prometheus() -> None:
    labels = {
        "metric": "speech_to_first_audio",
        "provider": REALTIME_TRANSLATION_PROVIDER,
        "model": REALTIME_TRANSLATION_MODEL,
        "mode": "direct",
    }

    before = (
        REGISTRY.get_sample_value(
            "waaxalma_realtime_client_latency_seconds_count",
            labels=labels,
        )
        or 0
    )

    response = client.post(
        "/api/realtime/metrics",
        json={
            "speech_to_first_audio_ms": 1350.5,
        },
    )

    assert response.status_code == 200

    after = (
        REGISTRY.get_sample_value(
            "waaxalma_realtime_client_latency_seconds_count",
            labels=labels,
        )
        or 0
    )

    assert after == before + 1