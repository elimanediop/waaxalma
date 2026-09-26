from time import perf_counter

from app.core.realtime_exceptions import (
    RealtimeTranslationException,
)

from app.core.realtime_translation_session import (
    RealtimeTranslationSession,
)

from app.observability.realtime_metrics import (
    REALTIME_SESSION_CREATION_DURATION_SECONDS,
    REALTIME_SESSION_ERRORS_TOTAL,
    REALTIME_SESSIONS_TOTAL,
)

from app.registry.provider_registry import (
    ProviderRegistry,
)


class RealtimeTranslationService:

    def __init__(
        self,
        *,
        provider_registry: ProviderRegistry,
        provider_name: str,
    ) -> None:
        self._provider_registry = (
            provider_registry
        )

        self._provider_name = (
            provider_name
        )


    @property
    def provider_name(self) -> str:
        return self._provider_name


    async def create_session(
        self,
        *,
        target_language: str,
    ) -> RealtimeTranslationSession:

        provider = (
            self._provider_registry.get(
                capability=(
                    "realtime_translation"
                ),
                name=self._provider_name,
            )
        )


        provider_name = (
            provider.name
        )

        model_name = (
            provider.model
        )


        started_at = (
            perf_counter()
        )


        try:

            session = (
                await provider.create_session(
                    target_language=(
                        target_language
                    ),
                )
            )


        except RealtimeTranslationException as exc:

            REALTIME_SESSIONS_TOTAL.labels(
                provider=provider_name,
                model=model_name,
                outcome="error",
            ).inc()


            REALTIME_SESSION_ERRORS_TOTAL.labels(
                provider=provider_name,
                model=model_name,
                code=exc.code,
                retryable=str(
                    exc.retryable
                ).lower(),
            ).inc()


            raise


        except Exception:

            REALTIME_SESSIONS_TOTAL.labels(
                provider=provider_name,
                model=model_name,
                outcome="error",
            ).inc()


            REALTIME_SESSION_ERRORS_TOTAL.labels(
                provider=provider_name,
                model=model_name,
                code="UNEXPECTED_ERROR",
                retryable="false",
            ).inc()


            raise


        else:

            REALTIME_SESSIONS_TOTAL.labels(
                provider=provider_name,
                model=model_name,
                outcome="success",
            ).inc()


            return session


        finally:

            duration_seconds = (
                perf_counter()
                - started_at
            )


            REALTIME_SESSION_CREATION_DURATION_SECONDS.labels(
                provider=provider_name,
                model=model_name,
            ).observe(
                duration_seconds
            )