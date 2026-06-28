from pydantic import BaseModel


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


class InterpretTextResponse(BaseModel):
    request_id: str
    session_id: str | None = None
    agent: str
    source_text: str
    interpreted_text: str
    audio_url: str