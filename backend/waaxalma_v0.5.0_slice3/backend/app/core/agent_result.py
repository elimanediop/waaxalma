from typing import Any
from pydantic import BaseModel, Field


class AgentResult(BaseModel):
    success: bool

    output: dict[str, Any] | None = None

    error_code: str | None = None
    error_message: str | None = None

    duration_ms: float | None = None

    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )