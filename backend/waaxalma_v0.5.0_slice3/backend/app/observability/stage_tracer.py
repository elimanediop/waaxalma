import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import TypeVar

from app.core.execution_trace import (
    ExecutionTrace,
    StageTrace,
)
from app.exceptions.pipeline_exception import PipelineException
from app.observability.metrics import (
    record_stage_execution,
)


T = TypeVar("T")

logger = logging.getLogger(__name__)


async def trace_async_stage(
    *,
    trace: ExecutionTrace,
    agent: str,
    stage: str,
    operation: str,
    provider: str | None,
    call: Callable[[], Awaitable[T]],
) -> T:
    started_at = datetime.now(timezone.utc)
    started_counter = time.perf_counter()

    try:
        result = await call()

    except asyncio.CancelledError:
        duration_ms = _elapsed_ms(started_counter)

        _record_stage(
            trace=trace,
            agent=agent,
            stage=stage,
            operation=operation,
            provider=provider,
            started_at=started_at,
            duration_ms=duration_ms,
            success=False,
            outcome="cancelled",
            error_code="CANCELLED",
        )

        raise

    except PipelineException as exc:
        duration_ms = _elapsed_ms(started_counter)

        _record_stage(
            trace=trace,
            agent=agent,
            stage=stage,
            operation=operation,
            provider=provider,
            started_at=started_at,
            duration_ms=duration_ms,
            success=False,
            outcome="error",
            error_code=exc.code,
        )

        raise

    except Exception:
        duration_ms = _elapsed_ms(started_counter)

        _record_stage(
            trace=trace,
            agent=agent,
            stage=stage,
            operation=operation,
            provider=provider,
            started_at=started_at,
            duration_ms=duration_ms,
            success=False,
            outcome="error",
            error_code="UNEXPECTED_ERROR",
        )

        raise

    duration_ms = _elapsed_ms(started_counter)

    _record_stage(
        trace=trace,
        agent=agent,
        stage=stage,
        operation=operation,
        provider=provider,
        started_at=started_at,
        duration_ms=duration_ms,
        success=True,
        outcome="success",
    )

    return result


def _record_stage(
    *,
    trace: ExecutionTrace,
    agent: str,
    stage: str,
    operation: str,
    provider: str | None,
    started_at: datetime,
    duration_ms: float,
    success: bool,
    outcome: str,
    error_code: str | None = None,
) -> None:
    finished_at = datetime.now(timezone.utc)

    trace.add_stage(
        StageTrace(
            stage=stage,
            operation=operation,
            provider=provider,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
            success=success,
            error_code=error_code,
        )
    )

    record_stage_execution(
        agent=agent,
        stage=stage,
        operation=operation,
        provider=provider,
        outcome=outcome,
        duration_ms=duration_ms,
    )

    logger.info(
        "Pipeline stage completed "
        "trace_id=%s agent=%s stage=%s operation=%s "
        "provider=%s outcome=%s duration_ms=%.3f "
        "error_code=%s",
        trace.trace_id,
        agent,
        stage,
        operation,
        provider or "internal",
        outcome,
        duration_ms,
        error_code,
    )


def _elapsed_ms(
    started_counter: float,
) -> float:
    return round(
        (time.perf_counter() - started_counter) * 1000,
        3,
    )