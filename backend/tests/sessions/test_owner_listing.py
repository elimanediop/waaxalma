from app.sessions.in_memory_session_repository import InMemorySessionRepository
from app.sessions.session_service import SessionService
import pytest


def test_list_sessions_is_scoped_to_authenticated_owner():
    service = SessionService(InMemorySessionRepository())
    alice = service.create_session("translator", owner_id="user:alice")
    service.create_session("translator", owner_id="user:bob")
    rows = service.list_sessions_by_owner("user:alice")
    assert [s.session_id for s in rows] == [alice.session_id]
    assert service.list_sessions_by_owner("user:bob")[0].owner_id == "user:bob"


def test_list_sessions_pagination_and_owner_validation():
    service = SessionService(InMemorySessionRepository())
    for _ in range(3):
        service.create_session("translator", owner_id="user:alice")
    first = service.list_sessions_by_owner("user:alice", limit=2)
    second = service.list_sessions_by_owner("user:alice", limit=2, offset=2)
    assert len(first) == 2 and len(second) == 1
    assert set(s.session_id for s in first).isdisjoint(s.session_id for s in second)
    with pytest.raises(ValueError):
        service.list_sessions_by_owner("legacy-client")
    with pytest.raises(ValueError):
        service.list_sessions_by_owner("user:alice", limit=101)
