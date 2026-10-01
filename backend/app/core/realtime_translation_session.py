from typing import Any

from pydantic import BaseModel, Field


class RealtimeTranslationSession(BaseModel):
    provider: str
    model: str
    target_language: str

    client_secret: str

    expires_at: int | None = None
    voice_id: str | None = None

    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )