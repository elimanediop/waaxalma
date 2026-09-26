from prometheus_client import Histogram


REALTIME_CLIENT_LATENCY_SECONDS = Histogram(
    "waaxalma_realtime_client_latency_seconds",
    (
        "Client-observed realtime translation latency "
        "measured in the browser."
    ),
    [
        "metric",
        "provider",
        "model",
        "mode",
    ],
    buckets=(
        0.05,
        0.1,
        0.25,
        0.5,
        0.75,
        1.0,
        1.5,
        2.0,
        3.0,
        5.0,
        10.0,
        30.0,
    ),
)