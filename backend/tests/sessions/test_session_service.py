import pytest

from app.sessions.in_memory_session_repository import (
    InMemorySessionRepository,
)
from app.sessions.session_service import (
    SessionClosedError,
    SessionNotFoundError,
    SessionService,
)


def test_require_session_raises_for_unknown_session() -> None:
    service = SessionService(
        repository=InMemorySessionRepository()
    )

    with pytest.raises(SessionNotFoundError):
        service.require_session("missing")


def test_closed_session_cannot_be_updated_or_receive_messages() -> None:
    service = SessionService(
        repository=InMemorySessionRepository()
    )

    session = service.create_session(
        agent_name="interpreter"
    )
    service.close_session(
        session.session_id
    )

    with pytest.raises(SessionClosedError):
        service.update_session(
            session.session_id,
            target_language="French",
        )

    with pytest.raises(SessionClosedError):
        service.add_message(
            session.session_id,
            role="user",
            content="hello",
        )


def test_close_is_idempotent() -> None:
    service = SessionService(
        repository=InMemorySessionRepository()
    )

    session = service.create_session(
        agent_name="interpreter"
    )

    first = service.close_session(
        session.session_id
    )
    second = service.close_session(
        session.session_id
    )

    assert first.closed_at == second.closed_at
