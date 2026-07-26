import asyncio

import pytest

from app.exceptions.provider_exception import (
    ProviderRequestException,
    ProviderTimeoutException,
    ProviderUnavailableException,
)
from app.resilience.resilience_executor import ResilienceExecutor
from app.resilience.resilience_policy import ResiliencePolicy


def create_policy(
    *,
    timeout_seconds: float = 0.1,
    max_attempts: int = 3,
) -> ResiliencePolicy:
    """
    Policy optimized for unit tests.

    Backoff and jitter are disabled so the test suite remains fast
    and deterministic.
    """
    return ResiliencePolicy(
        timeout_seconds=timeout_seconds,
        max_attempts=max_attempts,
        initial_backoff_seconds=0,
        backoff_multiplier=1,
        max_backoff_seconds=0,
        jitter_ratio=0,
    )


@pytest.mark.asyncio
async def test_success_does_not_retry() -> None:
    executor = ResilienceExecutor()
    attempts = 0

    async def provider_call() -> str:
        nonlocal attempts
        attempts += 1
        return "success"

    result = await executor.execute_async(
        provider="fake-provider",
        operation="translate",
        policy=create_policy(),
        call=provider_call,
    )

    assert result == "success"
    assert attempts == 1


@pytest.mark.asyncio
async def test_timeout_retries_then_fails() -> None:
    executor = ResilienceExecutor()
    attempts = 0

    async def slow_provider_call() -> str:
        nonlocal attempts
        attempts += 1

        await asyncio.sleep(0.05)

        return "too late"

    with pytest.raises(ProviderTimeoutException) as captured:
        await executor.execute_async(
            provider="fake-provider",
            operation="transcribe",
            policy=create_policy(
                timeout_seconds=0.01,
                max_attempts=2,
            ),
            call=slow_provider_call,
        )

    assert attempts == 2
    assert captured.value.code == "PROVIDER_TIMEOUT"
    assert captured.value.details["attempts"] == 2
    assert captured.value.details["max_attempts"] == 2
    assert (
        captured.value.details["retries_exhausted"]
        is True
    )


@pytest.mark.asyncio
async def test_transient_failure_retries_then_succeeds() -> None:
    executor = ResilienceExecutor()
    attempts = 0

    async def provider_call() -> str:
        nonlocal attempts
        attempts += 1

        if attempts < 3:
            raise ProviderUnavailableException(
                provider="fake-provider",
                operation="translate",
            )

        return "success-after-retry"

    result = await executor.execute_async(
        provider="fake-provider",
        operation="translate",
        policy=create_policy(max_attempts=3),
        call=provider_call,
    )

    assert result == "success-after-retry"
    assert attempts == 3


@pytest.mark.asyncio
async def test_provider_unavailable_exhausts_retries() -> None:
    executor = ResilienceExecutor()
    attempts = 0

    async def unavailable_provider_call() -> str:
        nonlocal attempts
        attempts += 1

        raise ProviderUnavailableException(
            provider="fake-provider",
            operation="speak",
        )

    with pytest.raises(
        ProviderUnavailableException
    ) as captured:
        await executor.execute_async(
            provider="fake-provider",
            operation="speak",
            policy=create_policy(max_attempts=3),
            call=unavailable_provider_call,
        )

    assert attempts == 3
    assert captured.value.code == "PROVIDER_UNAVAILABLE"
    assert captured.value.details["attempts"] == 3
    assert (
        captured.value.details["retries_exhausted"]
        is True
    )


@pytest.mark.asyncio
async def test_non_retryable_error_stops_immediately() -> None:
    executor = ResilienceExecutor()
    attempts = 0

    async def rejected_provider_call() -> str:
        nonlocal attempts
        attempts += 1

        raise ProviderRequestException(
            provider="fake-provider",
            operation="translate",
            message="The request is invalid.",
        )

    with pytest.raises(ProviderRequestException) as captured:
        await executor.execute_async(
            provider="fake-provider",
            operation="translate",
            policy=create_policy(max_attempts=3),
            call=rejected_provider_call,
        )

    assert attempts == 1
    assert captured.value.code == "PROVIDER_REQUEST_FAILED"
    assert captured.value.retryable is False