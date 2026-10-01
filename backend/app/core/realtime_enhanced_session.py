from typing import Any

from pydantic import BaseModel, Field


class RealtimeEnhancedSession(BaseModel):
    mode: str = "enhanced"

    transcription_provider: str
    transcription_model: str

    target_language: str

    client_secret: str
    expires_at: int | None = None

    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )