import asyncio
import logging
import random
from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.exceptions.provider_exception import (
    ProviderException,
    ProviderTimeoutException,
    RetryableProviderException,
)
from app.resilience.resilience_policy import ResiliencePolicy

T = TypeVar("T")

logger = logging.getLogger(__name__)


class ResilienceExecutor:
    """
    Executes provider calls with:

    - a timeout for each attempt;
    - selective retries;
    - exponential backoff;
    - jitter;
    - cancellation propagation.
    """

    async def execute_async(
        self,
        *,
        provider: str,
        operation: str,
        policy: ResiliencePolicy,
        call: Callable[[], Awaitable[T]],
    ) -> T:
        return await self._execute(
            provider=provider,
            operation=operation,
            policy=policy,
            call=call,
        )

    async def execute_sync(
        self,
        *,
        provider: str,
        operation: str,
        policy: ResiliencePolicy,
        call: Callable[[], T],
    ) -> T:
        async def threaded_call() -> T:
            return await asyncio.to_thread(call)

        return await self._execute(
            provider=provider,
            operation=operation,
            policy=policy,
            call=threaded_call,
        )

    async def _execute(
        self,
        *,
        provider: str,
        operation: str,
        policy: ResiliencePolicy,
        call: Callable[[], Awaitable[T]],
    ) -> T:
        for attempt in range(1, policy.max_attempts + 1):
            try:
                logger.debug(
                    "Provider call started "
                    "provider=%s operation=%s attempt=%s",
                    provider,
                    operation,
                    attempt,
                )

                result = await asyncio.wait_for(
                    call(),
                    timeout=policy.timeout_seconds,
                )

                logger.debug(
                    "Provider call succeeded "
                    "provider=%s operation=%s attempt=%s",
                    provider,
                    operation,
                    attempt,
                )

                return result

            except asyncio.CancelledError:
                # Never convert or retry request cancellation.
                raise

            except TimeoutError as exc:
                provider_error = ProviderTimeoutException(
                    provider=provider,
                    operation=operation,
                    timeout_seconds=policy.timeout_seconds,
                )

                if attempt >= policy.max_attempts:
                    self._add_attempt_metadata(
                        provider_error,
                        attempt=attempt,
                        max_attempts=policy.max_attempts,
                    )

                    logger.error(
                        "Provider call timed out "
                        "provider=%s operation=%s attempts=%s",
                        provider,
                        operation,
                        attempt,
                    )

                    raise provider_error from exc

                await self._wait_before_retry(
                    provider=provider,
                    operation=operation,
                    attempt=attempt,
                    policy=policy,
                    error=provider_error,
                )

            except RetryableProviderException as exc:
                if attempt >= policy.max_attempts:
                    self._add_attempt_metadata(
                        exc,
                        attempt=attempt,
                        max_attempts=policy.max_attempts,
                    )

                    logger.error(
                        "Provider retries exhausted "
                        "provider=%s operation=%s "
                        "attempts=%s code=%s",
                        provider,
                        operation,
                        attempt,
                        exc.code,
                    )

                    raise

                await self._wait_before_retry(
                    provider=provider,
                    operation=operation,
                    attempt=attempt,
                    policy=policy,
                    error=exc,
                )

            except ProviderException:
                # Known but non-retryable provider error.
                raise

        raise RuntimeError(
            "ResilienceExecutor reached an unreachable state."
        )

    async def _wait_before_retry(
        self,
        *,
        provider: str,
        operation: str,
        attempt: int,
        policy: ResiliencePolicy,
        error: ProviderException,
    ) -> None:
        delay_seconds = self._calculate_backoff(
            attempt=attempt,
            policy=policy,
        )

        logger.warning(
            "Retrying provider call "
            "provider=%s operation=%s "
            "attempt=%s next_attempt=%s "
            "delay_seconds=%.3f code=%s",
            provider,
            operation,
            attempt,
            attempt + 1,
            delay_seconds,
            error.code,
        )

        await asyncio.sleep(delay_seconds)

    @staticmethod
    def _calculate_backoff(
        *,
        attempt: int,
        policy: ResiliencePolicy,
    ) -> float:
        exponential_delay = (
            policy.initial_backoff_seconds
            * (
                policy.backoff_multiplier
                ** max(attempt - 1, 0)
            )
        )

        bounded_delay = min(
            exponential_delay,
            policy.max_backoff_seconds,
        )

        jitter_range = (
            bounded_delay * policy.jitter_ratio
        )

        jitter = random.uniform(
            -jitter_range,
            jitter_range,
        )

        return max(0.0, bounded_delay + jitter)

    @staticmethod
    def _add_attempt_metadata(
        error: ProviderException,
        *,
        attempt: int,
        max_attempts: int,
    ) -> None:
        error.details = {
            **(error.details or {}),
            "attempts": attempt,
            "max_attempts": max_attempts,
            "retries_exhausted": True,
        }