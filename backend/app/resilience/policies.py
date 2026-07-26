import os

from app.resilience.resilience_policy import ResiliencePolicy


def _env_float(
    name: str,
    default: float,
) -> float:
    return float(os.getenv(name, str(default)))


def _env_int(
    name: str,
    default: int,
) -> int:
    return int(os.getenv(name, str(default)))


PROVIDER_MAX_ATTEMPTS = _env_int(
    "PROVIDER_MAX_ATTEMPTS",
    3,
)

PROVIDER_INITIAL_BACKOFF_SECONDS = _env_float(
    "PROVIDER_INITIAL_BACKOFF_SECONDS",
    0.5,
)

PROVIDER_BACKOFF_MULTIPLIER = _env_float(
    "PROVIDER_BACKOFF_MULTIPLIER",
    2.0,
)

PROVIDER_MAX_BACKOFF_SECONDS = _env_float(
    "PROVIDER_MAX_BACKOFF_SECONDS",
    4.0,
)

PROVIDER_JITTER_RATIO = _env_float(
    "PROVIDER_JITTER_RATIO",
    0.2,
)


def build_policy(
    timeout_environment_variable: str,
    default_timeout_seconds: float,
) -> ResiliencePolicy:
    return ResiliencePolicy(
        timeout_seconds=_env_float(
            timeout_environment_variable,
            default_timeout_seconds,
        ),
        max_attempts=PROVIDER_MAX_ATTEMPTS,
        initial_backoff_seconds=(
            PROVIDER_INITIAL_BACKOFF_SECONDS
        ),
        backoff_multiplier=(
            PROVIDER_BACKOFF_MULTIPLIER
        ),
        max_backoff_seconds=(
            PROVIDER_MAX_BACKOFF_SECONDS
        ),
        jitter_ratio=PROVIDER_JITTER_RATIO,
    )


STT_RESILIENCE_POLICY = build_policy(
    timeout_environment_variable="STT_TIMEOUT_SECONDS",
    default_timeout_seconds=30.0,
)

TRANSLATION_RESILIENCE_POLICY = build_policy(
    timeout_environment_variable=(
        "TRANSLATION_TIMEOUT_SECONDS"
    ),
    default_timeout_seconds=20.0,
)

TTS_RESILIENCE_POLICY = build_policy(
    timeout_environment_variable="TTS_TIMEOUT_SECONDS",
    default_timeout_seconds=30.0,
)