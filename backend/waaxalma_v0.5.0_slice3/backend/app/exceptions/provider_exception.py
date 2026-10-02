from typing import Any

from starlette import status

from app.exceptions.error_codes import ErrorCode
from app.exceptions.pipeline_exception import PipelineException


class ProviderException(PipelineException):
    """
    Base exception for failures originating from an external provider.
    """

    def __init__(
        self,
        *,
        code: ErrorCode,
        message: str,
        provider: str,
        operation: str,
        status_code: int,
        retryable: bool,
        details: dict[str, Any] | None = None,
    ) -> None:
        provider_details: dict[str, Any] = {
            "provider": provider,
            "operation": operation,
            "retryable": retryable,
        }

        if details:
            provider_details.update(details)

        self.provider = provider
        self.operation = operation
        self.retryable = retryable

        super().__init__(
            code=code,
            message=message,
            status_code=status_code,
            details=provider_details,
        )


class RetryableProviderException(ProviderException):
    """
    Marker class for transient provider failures that may be retried.
    """


class ProviderTimeoutException(RetryableProviderException):
    def __init__(
        self,
        *,
        provider: str,
        operation: str,
        timeout_seconds: float,
        details: dict[str, Any] | None = None,
    ) -> None:
        timeout_details = {
            "timeout_seconds": timeout_seconds,
        }

        if details:
            timeout_details.update(details)

        super().__init__(
            code=ErrorCode.PROVIDER_TIMEOUT,
            message=(
                f"Provider '{provider}' timed out while executing "
                f"'{operation}'."
            ),
            provider=provider,
            operation=operation,
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            retryable=True,
            details=timeout_details,
        )


class ProviderUnavailableException(
    RetryableProviderException
):
    def __init__(
        self,
        *,
        provider: str,
        operation: str,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code=ErrorCode.PROVIDER_UNAVAILABLE,
            message=message or (
                f"Provider '{provider}' is temporarily unavailable."
            ),
            provider=provider,
            operation=operation,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            retryable=True,
            details=details,
        )


class ProviderRateLimitException(
    RetryableProviderException
):
    def __init__(
        self,
        *,
        provider: str,
        operation: str,
        retry_after_seconds: float | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        rate_limit_details = dict(details or {})

        if retry_after_seconds is not None:
            rate_limit_details["retry_after_seconds"] = (
                retry_after_seconds
            )

        super().__init__(
            code=ErrorCode.PROVIDER_RATE_LIMITED,
            message=(
                f"Provider '{provider}' temporarily rejected "
                "the request because of rate limiting."
            ),
            provider=provider,
            operation=operation,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            retryable=True,
            details=rate_limit_details,
        )


class ProviderAuthenticationException(ProviderException):
    def __init__(
        self,
        *,
        provider: str,
        operation: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code=ErrorCode.PROVIDER_AUTHENTICATION_FAILED,
            message=(
                f"Authentication with provider '{provider}' failed."
            ),
            provider=provider,
            operation=operation,
            status_code=status.HTTP_502_BAD_GATEWAY,
            retryable=False,
            details=details,
        )


class ProviderRequestException(ProviderException):
    def __init__(
        self,
        *,
        provider: str,
        operation: str,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code=ErrorCode.PROVIDER_REQUEST_FAILED,
            message=message or (
                f"Provider '{provider}' rejected the request."
            ),
            provider=provider,
            operation=operation,
            status_code=status.HTTP_502_BAD_GATEWAY,
            retryable=False,
            details=details,
        )