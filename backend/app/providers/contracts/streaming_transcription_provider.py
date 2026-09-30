from typing import Protocol

from app.core.streaming_transcription_session import (
    StreamingTranscriptionSession,
)


class StreamingTranscriptionProvider(
    Protocol
):

    @property
    def name(self) -> str:
        ...


    @property
    def model(self) -> str:
        ...


    async def create_session(
        self,
        *,
        languages: list[str] | None = None,
        prompt: str | None = None,
        keywords: list[str] | None = None,
        delay: str = "low",
    ) -> StreamingTranscriptionSession:
        ...