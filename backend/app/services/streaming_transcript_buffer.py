from typing import Any

from app.core.streaming_transcript_segment import (
    StreamingTranscriptSegment,
)


class StreamingTranscriptBuffer:

    def __init__(self) -> None:
        self._parts: list[str] = []
        self._next_sequence = 1

    @property
    def has_pending_text(self) -> bool:
        return bool(
            self.pending_text.strip()
        )

    @property
    def pending_text(self) -> str:
        return "".join(
            self._parts
        )

    def append(
        self,
        delta: str,
    ) -> None:
        if not delta:
            return

        self._parts.append(
            delta
        )

    def commit(
        self,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> StreamingTranscriptSegment | None:

        text = (
            self.pending_text
            .strip()
        )

        if not text:
            self._parts.clear()
            return None

        segment = StreamingTranscriptSegment(
            sequence=self._next_sequence,
            text=text,
            metadata=metadata or {},
        )

        self._next_sequence += 1

        self._parts.clear()

        return segment

    def reset(self) -> None:
        self._parts.clear()
        self._next_sequence = 1