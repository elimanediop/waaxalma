from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class RealtimeEnhancedStartEvent(BaseModel):
    type: Literal["session.start"]

    target_language: str = Field(min_length=1)

    @field_validator("target_language")
    @classmethod
    def normalize_target(cls, value: str) -> str:
        value = value.strip().lower()
        if not value:
            raise ValueError("Target language cannot be empty.")
        return value

    context: str | None = None

    terminology: list[str] | None = None

    session_id: str | None = None

    voice_id: str | None = None

    speech_instructions: str | None = None


class RealtimeEnhancedTranscriptDeltaEvent(BaseModel):
    type: Literal["transcript.delta"]

    delta: str


class RealtimeEnhancedTranscriptCommitEvent(BaseModel):
    type: Literal["transcript.commit"]

    text: str | None = None


class RealtimeEnhancedResetEvent(BaseModel):
    type: Literal["session.reset"]


class RealtimeEnhancedTranslationDeltaEvent(BaseModel):
    type: Literal["translation.delta"] = (
        "translation.delta"
    )

    text: str

    is_final: bool = False

    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class RealtimeEnhancedSessionReadyEvent(BaseModel):
    type: Literal["session.ready"] = (
        "session.ready"
    )

    session_id: str

    target_language: str

    voice_id: str | None = None


class RealtimeEnhancedErrorEvent(BaseModel):
    type: Literal["error"] = "error"

    code: str

    message: str

class RealtimeEnhancedAudioDeltaEvent(BaseModel):
    type: Literal["audio.delta"] = "audio.delta"

    audio: str

    is_final: bool = False

    content_type: str = "audio/pcm"

    sample_rate: int | None = None

    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )
