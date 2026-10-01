from typing import Literal, TypeAlias

from pydantic import BaseModel

from app.core.streaming_speech_chunk import (
    StreamingSpeechChunk,
)
from app.core.streaming_translation_chunk import (
    StreamingTranslationChunk,
)


class RealtimeEnhancedTranslationOutput(BaseModel):
    type: Literal["translation"] = "translation"
    chunk: StreamingTranslationChunk


class RealtimeEnhancedSpeechOutput(BaseModel):
    type: Literal["speech"] = "speech"
    chunk: StreamingSpeechChunk


RealtimeEnhancedOutput: TypeAlias = (
    RealtimeEnhancedTranslationOutput
    | RealtimeEnhancedSpeechOutput
)