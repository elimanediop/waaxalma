import pytest

from app.core.realtime_translation_session import (
    RealtimeTranslationSession,
)


class FakeRealtimeTranslationProvider:

    @property
    def name(self) -> str:
        return "fake"
    
    @property
    def model(self) -> str:
        return "fake-realtime-model"

    async def create_session(
        self,
        *,
        target_language: str,
    ) -> RealtimeTranslationSession:
        return RealtimeTranslationSession(
            provider=self.name,
            model="fake-realtime-model",
            target_language=target_language,
            client_secret="fake-client-secret",
            expires_at=1234567890,
            voice_id=None,
            metadata={
                "transport": "webrtc",
            },
        )


@pytest.mark.asyncio
async def test_realtime_provider_creates_session() -> None:
    provider = FakeRealtimeTranslationProvider()

    session = await provider.create_session(
        target_language="English",
    )

    assert session.provider == "fake"

    assert (
        session.model
        == "fake-realtime-model"
    )

    assert (
        session.target_language
        == "English"
    )

    assert (
        session.client_secret
        == "fake-client-secret"
    )

    assert session.expires_at == 1234567890

    assert session.voice_id is None

    assert session.metadata == {
        "transport": "webrtc",
    }