from app.core.voice_config import VoiceConfig


def build_voice_config(
    *,
    provider: str,
    voice_id: str,
) -> VoiceConfig:
    normalized_provider = provider.strip().lower()
    normalized_voice_id = voice_id.strip()

    if not normalized_provider:
        raise ValueError(
            "Voice provider cannot be empty."
        )

    if not normalized_voice_id:
        raise ValueError(
            "Voice ID cannot be empty."
        )

    return VoiceConfig(
        provider=normalized_provider,
        voice_id=normalized_voice_id,
    )