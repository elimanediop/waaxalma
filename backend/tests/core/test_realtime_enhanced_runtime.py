import pytest

from app.core.realtime_enhanced_runtime import (
    RealtimeEnhancedRuntime,
)


def test_runtime_normalizes_target_language() -> None:
    runtime = RealtimeEnhancedRuntime(
        target_language=" FR ",
    )

    assert runtime.target_language == "fr"


def test_runtime_generates_session_id() -> None:
    runtime = RealtimeEnhancedRuntime(
        target_language="fr",
    )

    assert runtime.session_id
    assert isinstance(
        runtime.session_id,
        str,
    )


def test_runtime_accepts_explicit_session_id() -> None:
    runtime = RealtimeEnhancedRuntime(
        target_language="fr",
        session_id="session-123",
    )

    assert (
        runtime.session_id
        == "session-123"
    )


def test_runtime_accumulates_and_commits_transcript() -> None:
    runtime = RealtimeEnhancedRuntime(
        target_language="fr",
        session_id="session-123",
    )

    runtime.append_transcript_delta(
        "Hello"
    )

    runtime.append_transcript_delta(
        " "
    )

    runtime.append_transcript_delta(
        "Waaxalma"
    )

    assert (
        runtime.pending_transcript
        == "Hello Waaxalma"
    )

    segment = (
        runtime.commit_transcript()
    )

    assert segment is not None

    assert segment.sequence == 1

    assert (
        segment.text
        == "Hello Waaxalma"
    )

    assert segment.metadata == {
        "session_id":
            "session-123",

        "target_language":
            "fr",
    }

    assert (
        runtime.pending_transcript
        == ""
    )


def test_runtime_commit_sequence_increments() -> None:
    runtime = RealtimeEnhancedRuntime(
        target_language="fr",
    )

    runtime.append_transcript_delta(
        "First"
    )

    first = (
        runtime.commit_transcript()
    )

    runtime.append_transcript_delta(
        "Second"
    )

    second = (
        runtime.commit_transcript()
    )

    assert first is not None
    assert second is not None

    assert first.sequence == 1
    assert second.sequence == 2


def test_runtime_commit_without_text_returns_none() -> None:
    runtime = RealtimeEnhancedRuntime(
        target_language="fr",
    )

    segment = (
        runtime.commit_transcript()
    )

    assert segment is None


def test_runtime_reset_clears_transcript_and_sequence() -> None:
    runtime = RealtimeEnhancedRuntime(
        target_language="fr",
    )

    runtime.append_transcript_delta(
        "First"
    )

    first = (
        runtime.commit_transcript()
    )

    assert first is not None
    assert first.sequence == 1

    runtime.append_transcript_delta(
        "Pending"
    )

    runtime.reset()

    assert (
        runtime.pending_transcript
        == ""
    )

    runtime.append_transcript_delta(
        "After reset"
    )

    after_reset = (
        runtime.commit_transcript()
    )

    assert after_reset is not None

    assert (
        after_reset.sequence
        == 1
    )


def test_runtime_instances_are_isolated() -> None:
    first_runtime = (
        RealtimeEnhancedRuntime(
            target_language="fr",
            session_id="session-a",
        )
    )

    second_runtime = (
        RealtimeEnhancedRuntime(
            target_language="en",
            session_id="session-b",
        )
    )

    first_runtime.append_transcript_delta(
        "Bonjour"
    )

    second_runtime.append_transcript_delta(
        "Hello"
    )

    assert (
        first_runtime.pending_transcript
        == "Bonjour"
    )

    assert (
        second_runtime.pending_transcript
        == "Hello"
    )

    first_segment = (
        first_runtime.commit_transcript()
    )

    second_segment = (
        second_runtime.commit_transcript()
    )

    assert first_segment is not None
    assert second_segment is not None

    assert (
        first_segment.metadata[
            "session_id"
        ]
        == "session-a"
    )

    assert (
        second_segment.metadata[
            "session_id"
        ]
        == "session-b"
    )


def test_runtime_preserves_context_and_terminology() -> None:
    runtime = RealtimeEnhancedRuntime(
        target_language="fr",
        context=(
            "Technical discussion "
            "about Waaxalma."
        ),
        terminology=[
            "Waaxalma",
            "Elimane",
        ],
    )

    assert runtime.context == (
        "Technical discussion "
        "about Waaxalma."
    )

    assert runtime.terminology == [
        "Waaxalma",
        "Elimane",
    ]


def test_empty_target_language_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "Target language "
            "cannot be empty."
        ),
    ):
        RealtimeEnhancedRuntime(
            target_language="   ",
        )