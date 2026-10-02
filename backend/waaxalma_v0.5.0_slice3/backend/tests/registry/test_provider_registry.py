import pytest

from app.registry.provider_registry import ProviderRegistry


class FakeTranslationProvider:

    @property
    def name(self) -> str:
        return "fake"

    async def translate(
        self,
        text: str,
        target_language: str,
    ) -> str:
        return f"[{target_language}] {text}"


def test_register_and_resolve_provider() -> None:
    registry = ProviderRegistry()

    provider = FakeTranslationProvider()

    registry.register(
        capability="translation",
        name=provider.name,
        provider=provider,
    )

    resolved = registry.get(
        capability="translation",
        name="fake",
    )

    assert resolved is provider


def test_contains_registered_provider() -> None:
    registry = ProviderRegistry()

    provider = FakeTranslationProvider()

    registry.register(
        capability="translation",
        name=provider.name,
        provider=provider,
    )

    assert registry.contains(
        capability="translation",
        name="fake",
    )

    assert not registry.contains(
        capability="translation",
        name="unknown",
    )


def test_duplicate_provider_registration_is_rejected() -> None:
    registry = ProviderRegistry()

    provider = FakeTranslationProvider()

    registry.register(
        capability="translation",
        name="fake",
        provider=provider,
    )

    with pytest.raises(
        ValueError,
        match="already registered",
    ):
        registry.register(
            capability="translation",
            name="fake",
            provider=provider,
        )


def test_unknown_provider_is_rejected() -> None:
    registry = ProviderRegistry()

    with pytest.raises(
        KeyError,
        match="not registered",
    ):
        registry.get(
            capability="translation",
            name="unknown",
        )


def test_names_are_filtered_by_capability() -> None:
    registry = ProviderRegistry()

    translation_provider = object()
    another_translation_provider = object()
    speech_provider = object()

    registry.register(
        capability="translation",
        name="openai",
        provider=translation_provider,
    )

    registry.register(
        capability="translation",
        name="fake",
        provider=another_translation_provider,
    )

    registry.register(
        capability="speech",
        name="openai",
        provider=speech_provider,
    )

    assert registry.names_for(
        "translation"
    ) == [
        "fake",
        "openai",
    ]

    assert registry.names_for(
        "speech"
    ) == [
        "openai",
    ]


def test_provider_is_selected_by_name() -> None:
    registry = ProviderRegistry()

    openai_provider = object()
    alternative_provider = object()

    registry.register(
        capability="translation",
        name="openai",
        provider=openai_provider,
    )

    registry.register(
        capability="translation",
        name="alternative",
        provider=alternative_provider,
    )

    selected = registry.get(
        capability="translation",
        name="alternative",
    )

    assert selected is alternative_provider
    assert selected is not openai_provider

def test_same_provider_name_can_support_multiple_capabilities() -> None:
    registry = ProviderRegistry()

    translation_provider = object()
    speech_provider = object()

    registry.register(
        capability="translation",
        name="openai",
        provider=translation_provider,
    )

    registry.register(
        capability="speech",
        name="openai",
        provider=speech_provider,
    )

    assert registry.get(
        capability="translation",
        name="openai",
    ) is translation_provider

    assert registry.get(
        capability="speech",
        name="openai",
    ) is speech_provider

def test_realtime_translation_provider_can_be_registered() -> None:
    registry = ProviderRegistry()

    provider = object()

    registry.register(
        capability="realtime_translation",
        name="fake",
        provider=provider,
    )

    resolved = registry.get(
        capability="realtime_translation",
        name="fake",
    )

    assert resolved is provider

    assert registry.contains(
        capability="realtime_translation",
        name="fake",
    )

def test_realtime_translation_is_isolated_from_translation() -> None:
    registry = ProviderRegistry()

    translation_provider = object()
    realtime_provider = object()

    registry.register(
        capability="translation",
        name="openai",
        provider=translation_provider,
    )

    registry.register(
        capability="realtime_translation",
        name="openai",
        provider=realtime_provider,
    )

    assert (
        registry.get(
            capability="translation",
            name="openai",
        )
        is translation_provider
    )

    assert (
        registry.get(
            capability="realtime_translation",
            name="openai",
        )
        is realtime_provider
    )