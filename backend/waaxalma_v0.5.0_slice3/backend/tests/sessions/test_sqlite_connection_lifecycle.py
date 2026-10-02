import sqlite3
import pytest
from fastapi.testclient import TestClient
from app.bootstrap import container
from app.main import app
from app.sessions.session_manager import SessionManager
from app.sessions.session_models import ConversationSession
from app.sessions.sqlite_session_repository import SQLiteSessionRepository


@pytest.fixture
def connections(monkeypatch):
    # Retain strong references: the checks must not rely on garbage collection.
    opened = []
    original = sqlite3.connect

    class TrackedConnection(sqlite3.Connection):
        closed = False

        def close(self):
            super().close()
            self.closed = True

    def connect(*args, **kwargs):
        kwargs['factory'] = TrackedConnection
        connection = original(*args, **kwargs)
        opened.append(connection)
        return connection

    monkeypatch.setattr(sqlite3, 'connect', connect)
    return opened


def assert_closed(connections):
    assert connections
    for connection in connections:
        assert connection.closed, "SQLite connection was not explicitly closed"


def test_repository_releases_handles_after_all_operations(tmp_path, connections):
    repo = SQLiteSessionRepository(tmp_path/'sessions.db')
    assert_closed(connections)
    manager = SessionManager(repo)
    session = manager.create_session('interpreter', owner_id='client-a')
    manager.get_session(session.session_id)
    manager.update_session(session.session_id, target_language='French')
    manager.add_message(session.session_id, 'user', 'hello')
    manager.close_session(session.session_id)
    assert_closed(connections)
    # The file can now be removed under Windows as well as POSIX.
    repo.database_path.unlink()


def test_failed_write_rolls_back_and_closes(tmp_path, connections):
    repo = SQLiteSessionRepository(tmp_path/'sessions.db')
    session = repo.create(ConversationSession.create('interpreter', owner_id='client-a'))
    with pytest.raises(ValueError, match='already exists'):
        repo.create(session)
    assert repo.get(session.session_id).owner_id == 'client-a'
    assert_closed(connections)


def test_readiness_releases_database_handles(tmp_path, connections, monkeypatch):
    repo = SQLiteSessionRepository(tmp_path/'sessions.db')
    monkeypatch.setattr(container, 'session_manager', SessionManager(repo))
    with TestClient(app) as client:
        assert client.get('/health/ready').status_code == 200
        assert_closed(connections)
        repo.database_path.unlink()
        assert client.get('/health/ready').status_code == 503
        assert client.get('/health/live').status_code == 200
