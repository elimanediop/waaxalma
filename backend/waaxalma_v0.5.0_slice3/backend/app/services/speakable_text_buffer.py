from typing import Any

from app.core.speakable_text_segment import (
    SpeakableTextSegment,
)


class SpeakableTextBuffer:

    TERMINAL_PUNCTUATION = (
        ".",
        "!",
        "?",
        ";",
        ":",
    )

    def __init__(
        self,
        *,
        soft_max_chars: int = 80,
    ) -> None:
        if soft_max_chars < 1:
            raise ValueError(
                "soft_max_chars must be greater than zero."
            )

        self._buffer = ""
        self._next_sequence = 1
        self._soft_max_chars = soft_max_chars

    @property
    def pending_text(self) -> str:
        return self._buffer

    @property
    def has_pending_text(self) -> bool:
        return bool(
            self._buffer.strip()
        )

    def append(
        self,
        delta: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> list[SpeakableTextSegment]:

        if not delta:
            return []

        self._buffer += delta

        segments: list[
            SpeakableTextSegment
        ] = []

        while True:
            split_index = (
                self._find_split_index()
            )

            if split_index is None:
                break

            text = (
                self._buffer[
                    :split_index
                ]
                .strip()
            )

            self._buffer = (
                self._buffer[
                    split_index:
                ]
            )

            if not text:
                continue

            segments.append(
                self._build_segment(
                    text=text,
                    metadata=metadata,
                )
            )

        return segments

    def flush(
        self,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> SpeakableTextSegment | None:

        text = self._buffer.strip()

        self._buffer = ""

        if not text:
            return None

        return self._build_segment(
            text=text,
            metadata=metadata,
        )

    def reset(self) -> None:
        self._buffer = ""
        self._next_sequence = 1

    def _find_split_index(
        self,
    ) -> int | None:

        # Prefer a natural sentence boundary.
        for index, char in enumerate(
            self._buffer
        ):
            if (
                char
                in self.TERMINAL_PUNCTUATION
            ):
                return index + 1

        # Otherwise avoid keeping an indefinitely
        # growing buffer.
        if (
            len(self._buffer)
            < self._soft_max_chars
        ):
            return None

        candidate = self._buffer[
            :self._soft_max_chars
        ]

        last_space = candidate.rfind(
            " "
        )

        if last_space > 0:
            return last_space + 1

        return self._soft_max_chars

    def _build_segment(
        self,
        *,
        text: str,
        metadata: dict[str, Any] | None,
    ) -> SpeakableTextSegment:

        segment = SpeakableTextSegment(
            sequence=self._next_sequence,
            text=text,
            metadata=metadata or {},
        )

        self._next_sequence += 1

        return segment