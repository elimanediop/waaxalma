import pytest

from app.services.speakable_text_buffer import (
    SpeakableTextBuffer,
)


def test_append_without_boundary_keeps_text_pending() -> None:
    buffer = SpeakableTextBuffer(
        soft_max_chars=80,
    )

    segments = buffer.append(
        "Bonjour"
    )

    assert segments == []

    assert (
        buffer.pending_text
        == "Bonjour"
    )

    assert (
        buffer.has_pending_text
        is True
    )


def test_terminal_punctuation_emits_segment() -> None:
    buffer = SpeakableTextBuffer(
        soft_max_chars=80,
    )

    segments = []

    segments.extend(
        buffer.append(
            "Bonjour"
        )
    )

    segments.extend(
        buffer.append(
            " tout le"
        )
    )

    segments.extend(
        buffer.append(
            " monde."
        )
    )

    assert len(segments) == 1

    segment = segments[0]

    assert segment.sequence == 1

    assert (
        segment.text
        == "Bonjour tout le monde."
    )

    assert (
        buffer.pending_text
        == ""
    )


def test_multiple_sentences_can_be_emitted_from_single_append() -> None:
    buffer = SpeakableTextBuffer(
        soft_max_chars=80,
    )

    segments = buffer.append(
        "Bonjour. Comment allez-vous?"
    )

    assert len(segments) == 2

    assert (
        segments[0].text
        == "Bonjour."
    )

    assert (
        segments[1].text
        == "Comment allez-vous?"
    )

    assert (
        segments[0].sequence
        == 1
    )

    assert (
        segments[1].sequence
        == 2
    )

    assert (
        buffer.pending_text
        == ""
    )


def test_soft_max_chars_splits_on_last_space() -> None:
    buffer = SpeakableTextBuffer(
        soft_max_chars=20,
    )

    segments = buffer.append(
        "Bonjour tout le monde depuis Waaxalma"
    )

    assert len(segments) >= 1

    first = segments[0]

    assert (
        first.text
        == "Bonjour tout le"
    )

    assert (
        first.sequence
        == 1
    )

    assert (
        "monde"
        in buffer.pending_text
        or any(
            "monde" in segment.text
            for segment in segments[1:]
        )
    )


def test_soft_max_chars_splits_without_space() -> None:
    buffer = SpeakableTextBuffer(
        soft_max_chars=5,
    )

    segments = buffer.append(
        "abcdefghij"
    )

    assert len(segments) == 2

    assert (
        segments[0].text
        == "abcde"
    )

    assert (
        segments[1].text
        == "fghij"
    )

    assert (
        buffer.pending_text
        == ""
    )


def test_flush_emits_pending_text() -> None:
    buffer = SpeakableTextBuffer(
        soft_max_chars=80,
    )

    buffer.append(
        "Bonjour Waaxalma"
    )

    segment = buffer.flush()

    assert segment is not None

    assert segment.sequence == 1

    assert (
        segment.text
        == "Bonjour Waaxalma"
    )

    assert (
        buffer.pending_text
        == ""
    )

    assert (
        buffer.has_pending_text
        is False
    )


def test_flush_without_pending_text_returns_none() -> None:
    buffer = SpeakableTextBuffer()

    segment = buffer.flush()

    assert segment is None


def test_metadata_is_preserved() -> None:
    buffer = SpeakableTextBuffer()

    segments = buffer.append(
        "Bonjour.",
        metadata={
            "session_id":
                "session-123",

            "source_segment_sequence":
                4,
        },
    )

    assert len(segments) == 1

    assert segments[0].metadata == {
        "session_id":
            "session-123",

        "source_segment_sequence":
            4,
    }


def test_sequence_increments_across_segments() -> None:
    buffer = SpeakableTextBuffer()

    first = buffer.append(
        "Bonjour."
    )

    second = buffer.append(
        "Comment allez-vous?"
    )

    assert (
        first[0].sequence
        == 1
    )

    assert (
        second[0].sequence
        == 2
    )


def test_reset_clears_pending_text_and_sequence() -> None:
    buffer = SpeakableTextBuffer()

    first = buffer.append(
        "Bonjour."
    )

    assert (
        first[0].sequence
        == 1
    )

    buffer.append(
        "Pending"
    )

    buffer.reset()

    assert (
        buffer.pending_text
        == ""
    )

    assert (
        buffer.has_pending_text
        is False
    )

    after_reset = buffer.append(
        "Après reset."
    )

    assert (
        after_reset[0].sequence
        == 1
    )


def test_instances_are_isolated() -> None:
    first_buffer = (
        SpeakableTextBuffer()
    )

    second_buffer = (
        SpeakableTextBuffer()
    )

    first_buffer.append(
        "Bonjour"
    )

    second_buffer.append(
        "Hello"
    )

    assert (
        first_buffer.pending_text
        == "Bonjour"
    )

    assert (
        second_buffer.pending_text
        == "Hello"
    )


def test_empty_delta_does_nothing() -> None:
    buffer = SpeakableTextBuffer()

    segments = buffer.append(
        ""
    )

    assert segments == []

    assert (
        buffer.pending_text
        == ""
    )


@pytest.mark.parametrize(
    "punctuation",
    [
        ".",
        "!",
        "?",
        ";",
        ":",
    ],
)
def test_supported_terminal_punctuation(
    punctuation: str,
) -> None:
    buffer = SpeakableTextBuffer()

    segments = buffer.append(
        f"Bonjour{punctuation}"
    )

    assert len(segments) == 1

    assert (
        segments[0].text
        == f"Bonjour{punctuation}"
    )


def test_invalid_soft_max_chars_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "soft_max_chars must be "
            "greater than zero."
        ),
    ):
        SpeakableTextBuffer(
            soft_max_chars=0,
        )