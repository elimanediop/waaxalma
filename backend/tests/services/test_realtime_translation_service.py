import pytest
from prometheus_client import REGISTRY

from app.core.realtime_translation_session import (
    RealtimeTranslationSession,
)
from app.registry.provider_registry import (
    ProviderRegistry,
)
from app.services.realtime_translation_service import (
    RealtimeTranslationService,
)

from app.core.realtime_exceptions import (
    RealtimeTranslationException,
)

class FailingRealtimeTranslationProvider:

    @property
    def name(self) -> str:
        return "fake-failing"

    @property
    def model(self) -> str:
        return "fake-realtime-model"

    async def create_session(
        self,
        *,
        target_language: str,
    ) -> RealtimeTranslationSession:

        raise RealtimeTranslationException(
            code="REALTIME_RATE_LIMITED",
            message=(
                "Realtime translation provider "
                "rate limit exceeded."
            ),
            provider=self.name,
            retryable=True,
            status_code=503,
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
            model=self.model,
            target_language=target_language,
            client_secret="fake-client-secret",
            expires_at=None,
            voice_id=None,
            metadata={},
        )

@pytest.fixture
def provider_registry() -> ProviderRegistry:
    registry = ProviderRegistry()

    provider = (
        FakeRealtimeTranslationProvider()
    )

    registry.register(
        capability="realtime_translation",
        name=provider.name,
        provider=provider,
    )

    return registry

@pytest.mark.asyncio
async def test_service_creates_realtime_translation_session() -> None:
    registry = ProviderRegistry()

    registry.register(
        capability="realtime_translation",
        name="fake",
        provider=FakeRealtimeTranslationProvider(),
    )

    service = RealtimeTranslationService(
        provider_registry=registry,
        provider_name="fake",
    )

    session = await service.create_session(
        target_language="fr",
    )

    assert session.provider == "fake"

    assert session.model == "fake-realtime-model"

    assert session.target_language == "fr"

    assert (
        session.client_secret
        == "fake-client-secret"
    )

@pytest.mark.asyncio
async def test_service_fails_for_unknown_provider() -> None:
    registry = ProviderRegistry()

    service = RealtimeTranslationService(
        provider_registry=registry,
        provider_name="unknown",
    )

    with pytest.raises(
        KeyError,
        match="not registered",
    ):
        await service.create_session(
            target_language="fr",
        )

@pytest.mark.asyncio
async def test_realtime_session_success_is_observed(
    provider_registry: ProviderRegistry,
) -> None:

    service = RealtimeTranslationService(
        provider_registry=provider_registry,
        provider_name="fake",
    )

    labels = {
        "provider": "fake",
        "model": "fake-realtime-model",
        "outcome": "success",
    }

    before = (
        REGISTRY.get_sample_value(
            "waaxalma_realtime_sessions_total",
            labels=labels,
        )
        or 0
    )

    await service.create_session(
        target_language="fr",
    )

    after = (
        REGISTRY.get_sample_value(
            "waaxalma_realtime_sessions_total",
            labels=labels,
        )
        or 0
    )

    assert after == before + 1

@pytest.mark.asyncio
async def test_realtime_session_duration_is_observed(
    provider_registry: ProviderRegistry,
) -> None:

    service = RealtimeTranslationService(
        provider_registry=provider_registry,
        provider_name="fake",
    )

    labels = {
        "provider": "fake",
        "model": "fake-realtime-model",
    }

    before = (
        REGISTRY.get_sample_value(
            (
                "waaxalma_realtime_session_"
                "creation_duration_seconds_count"
            ),
            labels=labels,
        )
        or 0
    )

    await service.create_session(
        target_language="fr",
    )

    after = (
        REGISTRY.get_sample_value(
            (
                "waaxalma_realtime_session_"
                "creation_duration_seconds_count"
            ),
            labels=labels,
        )
        or 0
    )

    assert after == before + 1

@pytest.mark.asyncio
async def test_realtime_session_error_is_observed() -> None:

    registry = ProviderRegistry()

    provider = (
        FailingRealtimeTranslationProvider()
    )

    registry.register(
        capability="realtime_translation",
        name=provider.name,
        provider=provider,
    )

    service = RealtimeTranslationService(
        provider_registry=registry,
        provider_name=provider.name,
    )

    labels = {
        "provider": "fake-failing",
        "model": "fake-realtime-model",
        "code": "REALTIME_RATE_LIMITED",
        "retryable": "true",
    }

    before = (
        REGISTRY.get_sample_value(
            "waaxalma_realtime_session_errors_total",
            labels=labels,
        )
        or 0
    )

    error_labels = {
    "provider": "fake-failing",
    "model": "fake-realtime-model",
    "outcome": "error",
    }

    before_errors = (
        REGISTRY.get_sample_value(
            "waaxalma_realtime_sessions_total",
            labels=error_labels,
        )
        or 0
    )

    with pytest.raises(
        RealtimeTranslationException
    ):
        await service.create_session(
            target_language="fr",
        )

    after_errors = (
        REGISTRY.get_sample_value(
            "waaxalma_realtime_sessions_total",
            labels=error_labels,
        )
        or 0
    )

    assert after_errors == before_errors + 1


