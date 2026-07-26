from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ResiliencePolicy:
    timeout_seconds: float
    max_attempts: int = 3
    initial_backoff_seconds: float = 0.5
    backoff_multiplier: float = 2.0
    max_backoff_seconds: float = 4.0
    jitter_ratio: float = 0.2

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError(
                "timeout_seconds must be greater than zero"
            )

        if self.max_attempts < 1:
            raise ValueError(
                "max_attempts must be at least one"
            )

        if self.initial_backoff_seconds < 0:
            raise ValueError(
                "initial_backoff_seconds cannot be negative"
            )

        if self.backoff_multiplier < 1:
            raise ValueError(
                "backoff_multiplier must be at least one"
            )

        if (
            self.max_backoff_seconds
            < self.initial_backoff_seconds
        ):
            raise ValueError(
                "max_backoff_seconds cannot be smaller than "
                "initial_backoff_seconds"
            )

        if not 0 <= self.jitter_ratio <= 1:
            raise ValueError(
                "jitter_ratio must be between zero and one"
            )