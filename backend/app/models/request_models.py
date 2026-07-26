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