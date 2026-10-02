from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TranslateTextResponse(BaseModel):
    request_id: str
    agent: str
    original_text: str
    translated_text: str


class SpeakTextResponse(BaseModel):
    request_id: str
    agent: str
    text: str
    audio_url: str


class TranslateAndSpeakResponse(BaseModel):
    request_id: str
    agent: str
    original_text: str
    translated_text: str
    audio_url: str


class AgentInfoResponse(BaseModel):
    type: str
    name: str
    description: str


class CreateSessionResponse(BaseModel):
    session_id: str
    agent_name: str
    target_language: str


class SessionResponse(BaseModel):
    owner_id: str | None = None
    session_id: str
    agent_name: str
    execution_mode: str
    source_language: str
    target_language: str
    status: str
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    history: list[dict[str, Any]] = Field(default_factory=list)


class InterpretTextResponse(BaseModel):
    request_id: str
    session_id: str | None = None
    agent: str
    source_text: str
    interpreted_text: str
    audio_url: str
