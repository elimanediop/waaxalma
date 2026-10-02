from typing import Any

from pydantic import BaseModel, Field


class ContextResult(BaseModel):
    original_text: str
    enriched_text: str

    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )