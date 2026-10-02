from typing import Any

from pydantic import BaseModel, Field


class QualityResult(BaseModel):
    accepted: bool

    score: float | None = None

    issues: list[str] = Field(
        default_factory=list,
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )