from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    agent_type: str = "interpreter"
    target_language: str = "English"


class InterpretTextRequest(BaseModel):
    text: str = Field(..., min_length=1)
    target_language: str = "English"
    session_id: str | None = None

    
class TranslateTextRequest(BaseModel):
    text: str = Field(..., min_length=1)
    target_language: str = "English"


class SpeakTextRequest(BaseModel):
    text: str = Field(..., min_length=1)