from prometheus_client import Counter, Histogram


STAGE_EXECUTIONS_TOTAL = Counter(
    "waaxalma_stage_executions_total",
    "Number of Waaxalma pipeline stage executions.",
    [
        "agent",
        "stage",
        "operation",
        "provider",
        "outcome",
    ],
)

STAGE_DURATION_SECONDS = Histogram(
    "waaxalma_stage_duration_seconds",
    "Duration of Waaxalma pipeline stages.",
    [
        "agent",
        "stage",
        "operation",
        "provider",
        "outcome",
    ],
    buckets=(
        0.05,
        0.1,
        0.25,
        0.5,
        1,
        2,
        5,
        10,
        20,
        30,
        60,
    ),
)

AGENT_EXECUTIONS_TOTAL = Counter(
    "waaxalma_agent_executions_total",
    "Number of Waaxalma agent executions.",
    [
        "agent",
        "operation",
        "outcome",
    ],
)

AGENT_DURATION_SECONDS = Histogram(
    "waaxalma_agent_duration_seconds",
    "Total duration of Waaxalma agent executions.",
    [
        "agent",
        "operation",
        "outcome",
    ],
    buckets=(
        0.05,
        0.1,
        0.25,
        0.5,
        1,
        2,
        5,
        10,
        20,
        30,
        60,
        120,
    ),
)

PROVIDER_RETRIES_TOTAL = Counter(
    "waaxalma_provider_retries_total",
    "Number of provider retries.",
    [
        "provider",
        "operation",
        "error_code",
    ],
)


def record_stage_execution(
    *,
    agent: str,
    stage: str,
    operation: str,
    provider: str | None,
    outcome: str,
    duration_ms: float,
) -> None:
    normalized_provider = provider or "internal"

    labels = {
        "agent": agent,
        "stage": stage,
        "operation": operation,
        "provider": normalized_provider,
        "outcome": outcome,
    }

    STAGE_EXECUTIONS_TOTAL.labels(**labels).inc()

    STAGE_DURATION_SECONDS.labels(
        **labels
    ).observe(duration_ms / 1000)


def record_agent_execution(
    *,
    agent: str,
    operation: str,
    outcome: str,
    duration_ms: float,
) -> None:
    labels = {
        "agent": agent,
        "operation": operation,
        "outcome": outcome,
    }

    AGENT_EXECUTIONS_TOTAL.labels(**labels).inc()

    AGENT_DURATION_SECONDS.labels(
        **labels
    ).observe(duration_ms / 1000)


def record_provider_retry(
    *,
    provider: str,
    operation: str,
    error_code: str,
) -> None:
    PROVIDER_RETRIES_TOTAL.labels(
        provider=provider,
        operation=operation,
        error_code=error_code,
    ).inc()