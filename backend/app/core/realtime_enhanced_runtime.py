from uuid import uuid4

from app.core.streaming_transcript_segment import (
    StreamingTranscriptSegment,
)
from app.services.streaming_transcript_buffer import (
    StreamingTranscriptBuffer,
)


class RealtimeEnhancedRuntime:

    def __init__(
        self,
        *,
        target_language: str,
        context: str | None = None,
        terminology: list[str] | None = None,
        session_id: str | None = None,
    ) -> None:
        normalized_target_language = (
            target_language
            .strip()
            .lower()
        )

        if not normalized_target_language:
            raise ValueError(
                "Target language cannot be empty."
            )

        self.session_id = (
            session_id
            or str(uuid4())
        )

        self.target_language = (
            normalized_target_language
        )

        self.context = context

        self.terminology = (
            list(terminology)
            if terminology
            else None
        )

        self._transcript_buffer = (
            StreamingTranscriptBuffer()
        )

    @property
    def pending_transcript(self) -> str:
        return (
            self._transcript_buffer
            .pending_text
        )

    def append_transcript_delta(
        self,
        delta: str,
    ) -> None:
        self._transcript_buffer.append(
            delta
        )

    def commit_transcript(
        self,
    ) -> StreamingTranscriptSegment | None:

        return self._transcript_buffer.commit(
            metadata={
                "session_id":
                    self.session_id,

                "target_language":
                    self.target_language,
            }
        )

    def reset(
        self,
    ) -> None:
        self._transcript_buffer.reset()