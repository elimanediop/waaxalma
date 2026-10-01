from typing import Any

from pydantic import BaseModel, Field


class StreamingSpeechChunk(BaseModel):
    audio: bytes

    is_final: bool = False

    content_type: str = "audio/pcm"

    sample_rate: int | None = Field(
        default=None,
        gt=0,
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )