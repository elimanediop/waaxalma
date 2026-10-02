from prometheus_client import (
    Counter,
    Histogram,
)


REALTIME_SESSIONS_TOTAL = Counter(
    "waaxalma_realtime_sessions_total",
    "Realtime translation session creation attempts.",
    [
        "provider",
        "model",
        "outcome",
    ],
)


REALTIME_SESSION_CREATION_DURATION_SECONDS = Histogram(
    "waaxalma_realtime_session_creation_duration_seconds",
    "Time spent creating a realtime translation session.",
    [
        "provider",
        "model",
    ],
    buckets=(
        0.05,
        0.1,
        0.25,
        0.5,
        1.0,
        2.0,
        5.0,
        10.0,
        30.0,
    ),
)


REALTIME_SESSION_ERRORS_TOTAL = Counter(
    "waaxalma_realtime_session_errors_total",
    "Realtime translation session creation errors.",
    [
        "provider",
        "model",
        "code",
        "retryable",
    ],
)