import httpx

from app.core.realtime_translation_session import (
    RealtimeTranslationSession
)

from app.core.realtime_exceptions import (
    RealtimeTranslationException,
)


class OpenAIRealtimeTranslationProvider:

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 10.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError(
                "OpenAI API key cannot be empty."
            )

        if not model.strip():
            raise ValueError(
                "Realtime translation model cannot be empty."
            )

        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._http_client = http_client

    @property
    def model(self) -> str:
        return self._model

    @property
    def name(self) -> str:
        return "openai"

    async def create_session(
        self,
        *,
        target_language: str,
    ) -> RealtimeTranslationSession:
        normalized_language = target_language.strip()

        if not normalized_language:
            raise ValueError(
                "Target language cannot be empty."
            )

        if self._http_client is not None:
            return await self._create_session(
                client=self._http_client,
                target_language=normalized_language,
            )

        async with httpx.AsyncClient(
            timeout=self._timeout_seconds,
        ) as client:
            return await self._create_session(
                client=client,
                target_language=normalized_language,
            )

    async def _create_session(
        self,
        *,
        client: httpx.AsyncClient,
        target_language: str,
    ) -> RealtimeTranslationSession:
        try:
            response = await client.post(
                (
                    f"{self._base_url}"
                    "/realtime/translations/client_secrets"
                ),
                headers={
                    "Authorization":
                        f"Bearer {self._api_key}",
                    "Content-Type":
                        "application/json",
                },
                json={
                    "session": {
                        "model":
                            self._model,
                        "audio": {
                            "output": {
                                "language":
                                    target_language,
                            },
                        },
                    },
                },
            )

        except httpx.TimeoutException as exc:
            raise RealtimeTranslationException(
                code="REALTIME_PROVIDER_TIMEOUT",
                message=(
                    "Realtime translation provider "
                    "timed out."
                ),
                provider=self.name,
                retryable=True,
                status_code=504,
            ) from exc

        except httpx.RequestError as exc:
            raise RealtimeTranslationException(
                code="REALTIME_PROVIDER_UNAVAILABLE",
                message=(
                    "Unable to reach realtime "
                    "translation provider."
                ),
                provider=self.name,
                retryable=True,
                status_code=503,
            ) from exc

        if response.status_code == 401:
            raise RealtimeTranslationException(
                code="REALTIME_AUTHENTICATION_FAILED",
                message=(
                    "Realtime translation provider "
                    "authentication failed."
                ),
                provider=self.name,
                retryable=False,
                status_code=502,
            )

        if response.status_code == 429:
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

        if response.status_code >= 500:
            raise RealtimeTranslationException(
                code="REALTIME_PROVIDER_UNAVAILABLE",
                message=(
                    "Realtime translation provider "
                    "is currently unavailable."
                ),
                provider=self.name,
                retryable=True,
                status_code=503,
            )

        if not response.is_success:
            raise RealtimeTranslationException(
                code="REALTIME_SESSION_FAILED",
                message=(
                    "Unable to create realtime "
                    "translation session."
                ),
                provider=self.name,
                retryable=False,
                status_code=502,
            )

        payload = response.json()

        return RealtimeTranslationSession(
            provider=self.name,
            model=self._model,
            target_language=target_language,
            client_secret=payload["value"],
            expires_at=payload.get(
                "expires_at"
            ),
            voice_id=None,
            metadata={
                "transport": "webrtc",
                "endpoint": (
                    "/v1/realtime/translations"
                ),
            },
        )