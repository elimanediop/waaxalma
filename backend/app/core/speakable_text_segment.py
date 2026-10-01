from typing import Any

from pydantic import BaseModel, Field


class SpeakableTextSegment(BaseModel):
    sequence: int = Field(
        ge=1,
    )

    text: str = Field(
        min_length=1,
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )