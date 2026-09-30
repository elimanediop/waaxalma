from collections.abc import AsyncIterator
from typing import Protocol

from app.core.streaming_translation_chunk import (
    StreamingTranslationChunk,
)


class StreamingTranslationProvider(Protocol):

    @property
    def name(self) -> str:
        ...

    @property
    def model(self) -> str:
        ...

    def translate_stream(
        self,
        *,
        text: str,
        target_language: str,
        context: str | None = None,
        terminology: list[str] | None = None,
    ) -> AsyncIterator[
        StreamingTranslationChunk
    ]:
        ...