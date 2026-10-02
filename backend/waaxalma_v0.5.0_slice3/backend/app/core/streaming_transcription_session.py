from typing import Any

from pydantic import BaseModel, Field


class StreamingTranscriptionSession(
    BaseModel
):
    provider: str

    model: str

    client_secret: str

    expires_at: int | None = None

    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )