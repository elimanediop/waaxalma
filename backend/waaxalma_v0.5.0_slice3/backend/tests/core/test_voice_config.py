import pytest

from app.core.voice_factory import build_voice_config


def test_build_voice_config() -> None:
    config = build_voice_config(
        provider="openai",
        voice_id="marin",
    )

    assert config.provider == "openai"
    assert config.voice_id == "marin"


def test_voice_config_normalizes_values() -> None:
    config = build_voice_config(
        provider=" OpenAI ",
        voice_id=" marin ",
    )

    assert config.provider == "openai"
    assert config.voice_id == "marin"


def test_voice_config_rejects_empty_provider() -> None:
    with pytest.raises(
        ValueError,
        match="provider cannot be empty",
    ):
        build_voice_config(
            provider="   ",
            voice_id="marin",
        )


def test_voice_config_rejects_empty_voice() -> None:
    with pytest.raises(
        ValueError,
        match="Voice ID cannot be empty",
    ):
        build_voice_config(
            provider="openai",
            voice_id="   ",
        )