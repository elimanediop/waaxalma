from app.services.streaming_transcript_buffer import (
    StreamingTranscriptBuffer,
)


def test_buffer_accumulates_transcript_deltas() -> None:
    buffer = StreamingTranscriptBuffer()

    buffer.append(
        "Hello"
    )

    buffer.append(
        " "
    )

    buffer.append(
        "world"
    )

    assert (
        buffer.pending_text
        == "Hello world"
    )

    assert (
        buffer.has_pending_text
        is True
    )


def test_commit_creates_stable_segment() -> None:
    buffer = StreamingTranscriptBuffer()

    buffer.append(
        "Hello "
    )

    buffer.append(
        "Waaxalma"
    )

    segment = buffer.commit()

    assert segment is not None

    assert segment.sequence == 1

    assert (
        segment.text
        == "Hello Waaxalma"
    )

    assert segment.metadata == {}

    assert (
        buffer.pending_text
        == ""
    )

    assert (
        buffer.has_pending_text
        is False
    )


def test_commit_preserves_metadata() -> None:
    buffer = StreamingTranscriptBuffer()

    buffer.append(
        "Hello"
    )

    segment = buffer.commit(
        metadata={
            "language": "en",
            "source": "streaming_stt",
        },
    )

    assert segment is not None

    assert segment.metadata == {
        "language": "en",
        "source": "streaming_stt",
    }


def test_repeated_commit_without_new_text_returns_none() -> None:
    buffer = StreamingTranscriptBuffer()

    buffer.append(
        "Hello"
    )

    first = buffer.commit()

    second = buffer.commit()

    assert first is not None

    assert (
        second
        is None
    )


def test_commit_sequence_increments() -> None:
    buffer = StreamingTranscriptBuffer()

    buffer.append(
        "First segment"
    )

    first = buffer.commit()

    buffer.append(
        "Second segment"
    )

    second = buffer.commit()

    assert first is not None
    assert second is not None

    assert first.sequence == 1
    assert second.sequence == 2


def test_whitespace_only_segment_is_not_committed() -> None:
    buffer = StreamingTranscriptBuffer()

    buffer.append(
        "   "
    )

    segment = buffer.commit()

    assert segment is None

    assert (
        buffer.pending_text
        == ""
    )


def test_reset_clears_buffer_and_sequence() -> None:
    buffer = StreamingTranscriptBuffer()

    buffer.append(
        "First"
    )

    first = buffer.commit()

    assert first is not None
    assert first.sequence == 1

    buffer.append(
        "Pending text"
    )

    buffer.reset()

    assert (
        buffer.pending_text
        == ""
    )

    buffer.append(
        "After reset"
    )

    after_reset = buffer.commit()

    assert after_reset is not None

    assert (
        after_reset.sequence
        == 1
    )