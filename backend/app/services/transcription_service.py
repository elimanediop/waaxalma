import logging
from pathlib import Path
from typing import Any

from openai import (
    APIConnectionError,
    APIError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    UnprocessableEntityError,
)
from starlette import status

from app.core.config import OPENAI_TRANSCRIPTION_MODEL
from app.exceptions.error_codes import ErrorCode
from app.exceptions.pipeline_exception import PipelineException
from app.exceptions.provider_exception import (
    ProviderAuthenticationException,
    ProviderRateLimitException,
    ProviderRequestException,
    ProviderTimeoutException,
    ProviderUnavailableException,
)
from app.resilience.container import resilience_executor
from app.resilience.policies import STT_RESILIENCE_POLICY


logger = logging.getLogger(__name__)

PROVIDER_NAME = "openai"

# Waaxalma controls retries through ResilienceExecutor.
# Disable the OpenAI SDK retries to avoid nested retry policies.
client = AsyncOpenAI(
    max_retries=0,
    timeout=STT_RESILIENCE_POLICY.timeout_seconds,
)


async def transcribe_audio(
    file_path: str,
) -> str:
    """
    Transcribe an audio file through OpenAI with timeout and retries.

    Each retry reopens the file so the provider always receives the
    complete audio content from the beginning.
    """
    audio_path = Path(file_path)

    if not audio_path.is_file():
        raise PipelineException(
            code=ErrorCode.INVALID_INPUT,
            message="The audio file does not exist.",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={
                "file_name": audio_path.name,
            },
        )

    return await resilience_executor.execute_async(
        provider=PROVIDER_NAME,
        operation="transcribe",
        policy=STT_RESILIENCE_POLICY,
        call=lambda: _transcribe_once(audio_path),
    )


async def _transcribe_once(
    audio_path: Path,
) -> str:
    """
    Execute one OpenAI transcription attempt.

    OpenAI SDK errors are translated into Waaxalma provider exceptions
    before reaching ResilienceExecutor.
    """
    try:
        # Open the file inside each attempt. Reusing an already-read
        # file handle would break subsequent retries.
        with audio_path.open("rb") as audio_file:
            transcription = await client.audio.transcriptions.create(
                model=OPENAI_TRANSCRIPTION_MODEL,
                file=audio_file,
                response_format="text",
            )

        return _extract_transcription_text(transcription)

    except APITimeoutError as exc:
        raise ProviderTimeoutException(
            provider=PROVIDER_NAME,
            operation="transcribe",
            timeout_seconds=STT_RESILIENCE_POLICY.timeout_seconds,
        ) from exc

    except RateLimitError as exc:
        raise ProviderRateLimitException(
            provider=PROVIDER_NAME,
            operation="transcribe",
            details=_build_error_details(exc),
        ) from exc

    except (AuthenticationError, PermissionDeniedError) as exc:
        raise ProviderAuthenticationException(
            provider=PROVIDER_NAME,
            operation="transcribe",
            details=_build_error_details(exc),
        ) from exc

    except APIConnectionError as exc:
        raise ProviderUnavailableException(
            provider=PROVIDER_NAME,
            operation="transcribe",
            message="The OpenAI transcription service could not be reached.",
        ) from exc

    except InternalServerError as exc:
        raise ProviderUnavailableException(
            provider=PROVIDER_NAME,
            operation="transcribe",
            message=(
                "The OpenAI transcription service is temporarily "
                "unavailable."
            ),
            details=_build_error_details(exc),
        ) from exc

    except (
        BadRequestError,
        UnprocessableEntityError,
        NotFoundError,
    ) as exc:
        raise ProviderRequestException(
            provider=PROVIDER_NAME,
            operation="transcribe",
            message="The transcription request was rejected by OpenAI.",
            details=_build_error_details(exc),
        ) from exc

    except APIStatusError as exc:
        details = _build_error_details(exc)

        if exc.status_code >= 500:
            raise ProviderUnavailableException(
                provider=PROVIDER_NAME,
                operation="transcribe",
                details=details,
            ) from exc

        raise ProviderRequestException(
            provider=PROVIDER_NAME,
            operation="transcribe",
            message="The transcription request failed.",
            details=details,
        ) from exc

    except APIError as exc:
        raise ProviderRequestException(
            provider=PROVIDER_NAME,
            operation="transcribe",
            message="The OpenAI transcription request failed.",
        ) from exc

def _extract_transcription_text(
    transcription: Any,
) -> str:
    """
    Support both plain-text and object responses from the SDK.
    """
    if isinstance(transcription, str):
        text = transcription
    else:
        text = getattr(transcription, "text", "")

    normalized_text = str(text or "").strip()

    if not normalized_text:
        raise ProviderRequestException(
            provider=PROVIDER_NAME,
            operation="transcribe",
            message=(
                "The transcription provider returned an empty result."
            ),
        )

    return normalized_text


def _build_error_details(
    exc: APIStatusError,
) -> dict[str, Any]:
    details: dict[str, Any] = {
        "provider_status_code": exc.status_code,
    }

    request_id = getattr(exc, "request_id", None)

    if request_id:
        details["provider_request_id"] = request_id

    return details