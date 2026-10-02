from app.observability.operations import observe, record_usage
import httpx

from app.core.streaming_transcription_session import (
    StreamingTranscriptionSession,
)


class OpenAIStreamingTranscriptionProvider:

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
                "Streaming transcription model "
                "cannot be empty."
            )

        self._api_key = (
            api_key.strip()
        )

        self._model = (
            model.strip()
        )

        self._base_url = (
            base_url.rstrip("/")
        )

        self._timeout_seconds = (
            timeout_seconds
        )

        self._http_client = (
            http_client
        )


    @property
    def name(self) -> str:
        return "openai"


    @property
    def model(self) -> str:
        return self._model


    @observe("stt_session", model=None)
    async def create_session(
        self,
        *,
        languages: list[str] | None = None,
        prompt: str | None = None,
        keywords: list[str] | None = None,
        delay: str = "low",
    ) -> StreamingTranscriptionSession:

        transcription_config = (
            self._build_transcription_config(
                languages=languages,
                prompt=prompt,
                keywords=keywords,
                delay=delay,
            )
        )


        payload = {
            "session": {
                "type": "transcription",
                "audio": {
                    "input": {
                        "format": {
                            "type": "audio/pcm",
                            "rate": 24000,
                        },
                        "transcription":
                            transcription_config,
                        "turn_detection":
                            None,
                    }
                },
            }
        }


        if (
            self._http_client
            is not None
        ):

            return await self._create_session(
                client=self._http_client,
                payload=payload,
            )


        async with httpx.AsyncClient(
            timeout=self._timeout_seconds,
        ) as client:

            return await self._create_session(
                client=client,
                payload=payload,
            )


    def _build_transcription_config(
        self,
        *,
        languages: list[str] | None,
        prompt: str | None,
        keywords: list[str] | None,
        delay: str,
    ) -> dict:

        config: dict = {
            "model":
                self._model,

            "delay":
                delay,
        }


        if languages:

            normalized_languages = [
                language.strip().lower()
                for language in languages
                if language.strip()
            ]


            if normalized_languages:

                config["languages"] = (
                    normalized_languages
                )


        if (
            prompt
            and prompt.strip()
        ):

            config["prompt"] = (
                prompt.strip()
            )


        if keywords:

            normalized_keywords = [
                keyword.strip()
                for keyword in keywords
                if keyword.strip()
            ]


            if normalized_keywords:

                config["keywords"] = (
                    normalized_keywords
                )


        return config


    async def _create_session(
        self,
        *,
        client: httpx.AsyncClient,
        payload: dict,
    ) -> StreamingTranscriptionSession:

        response = await client.post(
            (
                f"{self._base_url}"
                "/realtime/client_secrets"
            ),
            headers={
                "Authorization":
                    f"Bearer {self._api_key}",

                "Content-Type":
                    "application/json",
            },
            json=payload,
        )


        response.raise_for_status()


        response_payload = (
            response.json()
        )


        return StreamingTranscriptionSession(
            provider=self.name,
            model=self._model,
            client_secret=(
                response_payload["value"]
            ),
            expires_at=(
                response_payload.get(
                    "expires_at"
                )
            ),
            metadata={
                "transport":
                    "webrtc",

                "endpoint":
                    "/v1/realtime/calls",

                "session_type":
                    "transcription",

                "audio_format":
                    "audio/pcm",

                "sample_rate":
                    24000,
            },
        )