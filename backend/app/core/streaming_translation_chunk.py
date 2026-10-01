from typing import Any

from pydantic import BaseModel, Field


class StreamingTranslationChunk(BaseModel):
    text: str
    is_final: bool = False

    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )