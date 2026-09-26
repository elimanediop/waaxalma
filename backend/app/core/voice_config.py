from pydantic import BaseModel, Field


class VoiceConfig(BaseModel):
    provider: str = Field(
        min_length=1,
    )

    voice_id: str = Field(
        min_length=1,
    )