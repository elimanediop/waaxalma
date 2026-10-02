from typing import Any

from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    agent_type: str = Field(
        default="interpreter",
        min_length=1,
        max_length=64,
    )
    source_language: str = Field(
        default="auto",
        min_length=2,
        max_length=64,
    )
    target_language: str = Field(
        default="English",
        min_length=2,
        max_length=64,
    )
    execution_mode: str = Field(
        default="standard",
        min_length=2,
        max_length=64,
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class UpdateSessionRequest(BaseModel):
    source_language: str | None = Field(
        default=None,
        min_length=2,
        max_length=64,
    )
    target_language: str | None = Field(
        default=None,
        min_length=2,
        max_length=64,
    )
    execution_mode: str | None = Field(
        default=None,
        min_length=2,
        max_length=64,
    )
    metadata: dict[str, Any] | None = None


class InterpretTextRequest(BaseModel):
    text: str = Field(..., min_length=1)
    target_language: str = "English"
    session_id: str | None = None


class TranslateTextRequest(BaseModel):
    session_id: str | None = None
    source_language: str | None = None
    text: str = Field(..., min_length=1)
    target_language: str = "English"


class SpeakTextRequest(BaseModel):
    session_id: str | None = None
    language: str = "English"
    text: str = Field(..., min_length=1)


class TranslateAndSpeakRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        description="Text to translate and synthesize as speech.",
    )
    source_language: str | None = Field(
        default=None,
        description="Source language. If omitted, language detection may be used.",
    )
    target_language: str = Field(
        default="English",
        min_length=2,
        description="Target language for translation and speech synthesis.",
    )
    session_id: str | None = Field(
        default=None,
        description="Optional conversation session identifier.",
    )
