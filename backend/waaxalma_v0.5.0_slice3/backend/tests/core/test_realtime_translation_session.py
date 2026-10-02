from app.core.realtime_translation_session import (
    RealtimeTranslationSession,
)


def test_realtime_translation_session() -> None:
    session = RealtimeTranslationSession(
        provider="openai",
        model="realtime-model",
        target_language="French",
        voice_id="marin",
        client_secret="secret",
    )

    assert session.provider == "openai"
    assert session.model == "realtime-model"
    assert session.target_language == "French"
    assert session.voice_id == "marin"
    assert session.client_secret == "secret"
    assert session.expires_at is None
    assert session.metadata == {}