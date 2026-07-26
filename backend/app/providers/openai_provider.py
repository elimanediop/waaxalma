from pathlib import Path
from typing import Any, NoReturn

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    NotFoundError,
    OpenAIError,
    PermissionDeniedError,
    RateLimitError,
    UnprocessableEntityError,
)

from app.core.config import (
    AUDIO_OUTPUT_DIR,
    OPENAI_TRANSCRIPTION_MODEL,
    OPENAI_TRANSLATION_MODEL,
    OPENAI_TTS_MODEL,
    OPENAI_TTS_VOICE,
)
from app.exceptions.provider_exception import (
    ProviderAuthenticationException,
    ProviderRateLimitException,
    ProviderRequestException,
    ProviderTimeoutException,
    ProviderUnavailableException,
)
from app.resilience.container import resilience_executor
from app.resilience.policies import (
    STT_RESILIENCE_POLICY,
    TRANSLATION_RESILIENCE_POLICY,
    TTS_RESILIENCE_POLICY,
)


PROVIDER_NAME = "openai"

# Waaxalma owns retry behavior through ResilienceExecutor.
client = AsyncOpenAI(
    max_retries=0,
)


class OpenAITranslationProvider:

    @property
    def name(self) -> str:
        return PROVIDER_NAME

    async def translate(
        self,
        text: str,
        target_language: str = "English",
    ) -> str:
        return await resilience_executor.execute_async(
            provider=self.name,
            operation="translate",
            policy=TRANSLATION_RESILIENCE_POLICY,
            call=lambda: self._translate_once(
                text=text,
                target_language=target_language,
            ),
        )

    async def _translate_once(
        self,
        text: str,
        target_language: str,
    ) -> str:
        try:
            response = await client.responses.create(
                model=OPENAI_TRANSLATION_MODEL,
                input=f"""
You are Waaxalma, a voice translation assistant.

Translate the following text into {target_language}.
Keep the meaning faithful.
Use natural spoken language.
Return only the translation.

Text:
{text}
""",
                timeout=(
                    TRANSLATION_RESILIENCE_POLICY.timeout_seconds
                ),
            )

            translated_text = response.output_text.strip()

            if not translated_text:
                raise ProviderRequestException(
                    provider=self.name,
                    operation="translate",
                    message=(
                        "The translation provider returned "
                        "an empty result."
                    ),
                )

            return translated_text

        except OpenAIError as exc:
            _raise_openai_provider_error(
                exc=exc,
                operation="translate",
                timeout_seconds=(
                    TRANSLATION_RESILIENCE_POLICY.timeout_seconds
                ),
            )


class OpenAISpeechProvider:

    @property
    def name(self) -> str:
        return PROVIDER_NAME

    async def speak(
        self,
        text: str,
        output_filename: str,
    ) -> str:
        output_directory = Path(AUDIO_OUTPUT_DIR)
        output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path = output_directory / output_filename

        return await resilience_executor.execute_async(
            provider=self.name,
            operation="speak",
            policy=TTS_RESILIENCE_POLICY,
            call=lambda: self._speak_once(
                text=text,
                output_path=output_path,
            ),
        )

    async def _speak_once(
        self,
        text: str,
        output_path: Path,
    ) -> str:
        # Remove a possible partial file from a previous attempt.
        output_path.unlink(missing_ok=True)

        try:
            async with (
                client.audio.speech
                .with_streaming_response
                .create(
                    model=OPENAI_TTS_MODEL,
                    voice=OPENAI_TTS_VOICE,
                    input=text,
                    instructions=(
                        "Speak clearly in natural spoken language."
                    ),
                    timeout=(
                        TTS_RESILIENCE_POLICY.timeout_seconds
                    ),
                )
            ) as response:
                await response.stream_to_file(output_path)

            if (
                not output_path.is_file()
                or output_path.stat().st_size == 0
            ):
                output_path.unlink(missing_ok=True)

                raise ProviderRequestException(
                    provider=self.name,
                    operation="speak",
                    message=(
                        "The speech provider returned "
                        "an empty audio file."
                    ),
                )

            return str(output_path)

        except OpenAIError as exc:
            output_path.unlink(missing_ok=True)

            _raise_openai_provider_error(
                exc=exc,
                operation="speak",
                timeout_seconds=(
                    TTS_RESILIENCE_POLICY.timeout_seconds
                ),
            )

        except Exception:
            # Do not leave an incomplete MP3 on disk.
            output_path.unlink(missing_ok=True)
            raise


class OpenAISpeechToTextProvider:

    @property
    def name(self) -> str:
        return PROVIDER_NAME

    async def transcribe(
        self,
        audio_path: str,
    ) -> str:
        path = Path(audio_path)

        if not path.is_file():
            raise ProviderRequestException(
                provider=self.name,
                operation="transcribe",
                message="The audio file does not exist.",
                details={
                    "file_name": path.name,
                },
            )

        return await resilience_executor.execute_async(
            provider=self.name,
            operation="transcribe",
            policy=STT_RESILIENCE_POLICY,
            call=lambda: self._transcribe_once(path),
        )

    async def _transcribe_once(
        self,
        audio_path: Path,
    ) -> str:
        try:
            # The file is reopened on every attempt.
            with audio_path.open("rb") as audio_file:
                transcription = (
                    await client.audio.transcriptions.create(
                        model=OPENAI_TRANSCRIPTION_MODEL,
                        file=audio_file,
                        response_format="text",
                        timeout=(
                            STT_RESILIENCE_POLICY.timeout_seconds
                        ),
                    )
                )

            text = transcription.strip()

            if not text:
                raise ProviderRequestException(
                    provider=self.name,
                    operation="transcribe",
                    message=(
                        "The transcription provider returned "
                        "an empty result."
                    ),
                )

            return text

        except OpenAIError as exc:
            _raise_openai_provider_error(
                exc=exc,
                operation="transcribe",
                timeout_seconds=(
                    STT_RESILIENCE_POLICY.timeout_seconds
                ),
            )


def _raise_openai_provider_error(
    *,
    exc: OpenAIError,
    operation: str,
    timeout_seconds: float,
) -> NoReturn:
    """
    Convert OpenAI SDK exceptions into Waaxalma exceptions.

    Only transient exceptions are retryable.
    """

    details = _build_openai_error_details(exc)

    if isinstance(exc, APITimeoutError):
        raise ProviderTimeoutException(
            provider=PROVIDER_NAME,
            operation=operation,
            timeout_seconds=timeout_seconds,
            details=details,
        ) from exc

    if isinstance(exc, RateLimitError):
        raise ProviderRateLimitException(
            provider=PROVIDER_NAME,
            operation=operation,
            details=details,
        ) from exc

    if isinstance(
        exc,
        (
            AuthenticationError,
            PermissionDeniedError,
        ),
    ):
        raise ProviderAuthenticationException(
            provider=PROVIDER_NAME,
            operation=operation,
            details=details,
        ) from exc

    if isinstance(exc, APIConnectionError):
        raise ProviderUnavailableException(
            provider=PROVIDER_NAME,
            operation=operation,
            message=(
                f"OpenAI could not be reached during "
                f"'{operation}'."
            ),
            details=details,
        ) from exc

    if isinstance(exc, InternalServerError):
        raise ProviderUnavailableException(
            provider=PROVIDER_NAME,
            operation=operation,
            message=(
                f"OpenAI is temporarily unavailable "
                f"during '{operation}'."
            ),
            details=details,
        ) from exc

    if isinstance(
        exc,
        (
            BadRequestError,
            NotFoundError,
            UnprocessableEntityError,
        ),
    ):
        raise ProviderRequestException(
            provider=PROVIDER_NAME,
            operation=operation,
            message=(
                f"OpenAI rejected the '{operation}' request."
            ),
            details=details,
        ) from exc

    if isinstance(exc, APIStatusError):
        if exc.status_code in {408, 409}:
            raise ProviderUnavailableException(
                provider=PROVIDER_NAME,
                operation=operation,
                message=(
                    f"OpenAI temporarily could not process "
                    f"'{operation}'."
                ),
                details=details,
            ) from exc

        if exc.status_code >= 500:
            raise ProviderUnavailableException(
                provider=PROVIDER_NAME,
                operation=operation,
                details=details,
            ) from exc

    raise ProviderRequestException(
        provider=PROVIDER_NAME,
        operation=operation,
        message=(
            f"The OpenAI '{operation}' request failed."
        ),
        details=details,
    ) from exc


def _build_openai_error_details(
    exc: OpenAIError,
) -> dict[str, Any]:
    details: dict[str, Any] = {}

    status_code = getattr(exc, "status_code", None)

    if status_code is not None:
        details["provider_status_code"] = status_code

    request_id = getattr(exc, "request_id", None)

    if request_id:
        details["provider_request_id"] = request_id

    return details