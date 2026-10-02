from pathlib import Path

from app.sessions.in_memory_session_repository import (
    InMemorySessionRepository,
)
from app.sessions.session_models import (
    SESSION_STATUS_ACTIVE,
    SESSION_STATUS_CLOSED,
    ConversationSession,
)
from app.sessions.session_service import SessionService
from app.sessions.sqlite_session_repository import (
    SQLiteSessionRepository,
)


def test_in_memory_repository_returns_detached_copies() -> None:
    repository = InMemorySessionRepository()
    service = SessionService(repository=repository)

    created = service.create_session(
        agent_name="interpreter",
        target_language="French",
    )

    loaded = service.require_session(
        created.session_id
    )
    loaded.target_language = "Spanish"

    loaded_again = service.require_session(
        created.session_id
    )

    assert loaded_again.target_language == "French"


def test_session_service_updates_lifecycle_and_history() -> None:
    service = SessionService(
        repository=InMemorySessionRepository()
    )

    session = service.create_session(
        agent_name="interpreter",
        source_language="fr",
        target_language="en",
        execution_mode="standard",
        metadata={"client": "test"},
    )

    assert session.status == SESSION_STATUS_ACTIVE

    updated = service.update_session(
        session.session_id,
        target_language="es",
        metadata={"topic": "demo"},
    )

    assert updated.target_language == "es"
    assert updated.metadata == {
        "client": "test",
        "topic": "demo",
    }

    service.add_message(
        session.session_id,
        role="user",
        content="bonjour",
    )
    service.add_message(
        session.session_id,
        role="assistant",
        content="hello",
    )

    with_history = service.require_session(
        session.session_id
    )

    assert [
        item["role"]
        for item in with_history.history
    ] == [
        "user",
        "assistant",
    ]

    closed = service.close_session(
        session.session_id
    )

    assert closed.status == SESSION_STATUS_CLOSED
    assert closed.closed_at is not None


def test_sqlite_session_survives_repository_restart(
    tmp_path: Path,
) -> None:
    database_path = (
        tmp_path
        / "sessions.sqlite3"
    )

    first_service = SessionService(
        repository=SQLiteSessionRepository(
            database_path
        )
    )

    created = first_service.create_session(
        agent_name="interpreter",
        source_language="fr",
        target_language="en",
        execution_mode="standard",
        metadata={"origin": "restart-test"},
    )

    first_service.add_message(
        created.session_id,
        role="user",
        content="Salut",
    )

    # Simulate a process restart by constructing a fresh repository/service.
    second_service = SessionService(
        repository=SQLiteSessionRepository(
            database_path
        )
    )

    restored = second_service.require_session(
        created.session_id
    )

    assert restored.session_id == created.session_id
    assert restored.agent_name == "interpreter"
    assert restored.source_language == "fr"
    assert restored.target_language == "en"
    assert restored.execution_mode == "standard"
    assert restored.metadata == {
        "origin": "restart-test",
    }
    assert restored.history[0]["content"] == "Salut"


def test_sqlite_update_and_close_survive_restart(
    tmp_path: Path,
) -> None:
    database_path = (
        tmp_path
        / "sessions.sqlite3"
    )

    service = SessionService(
        repository=SQLiteSessionRepository(
            database_path
        )
    )

    created = service.create_session(
        agent_name="interpreter",
        target_language="English",
    )

    service.update_session(
        created.session_id,
        source_language="wo",
        target_language="fr",
        execution_mode="enhanced",
    )
    service.close_session(
        created.session_id
    )

    restarted = SessionService(
        repository=SQLiteSessionRepository(
            database_path
        )
    )

    restored = restarted.require_session(
        created.session_id
    )

    assert restored.source_language == "wo"
    assert restored.target_language == "fr"
    assert restored.execution_mode == "enhanced"
    assert restored.status == SESSION_STATUS_CLOSED
    assert restored.closed_at is not None
