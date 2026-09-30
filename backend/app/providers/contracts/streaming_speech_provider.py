from collections.abc import AsyncIterator
from typing import Protocol

from app.core.streaming_speech_chunk import (
    StreamingSpeechChunk,
)


class StreamingSpeechProvider(Protocol):

    @property
    def name(self) -> str:
        ...

    @property
    def model(self) -> str:
        ...

    def speak_stream(
        self,
        *,
        text: str,
        voice_id: str,
        instructions: str | None = None,
    ) -> AsyncIterator[
        StreamingSpeechChunk
    ]:
        ...