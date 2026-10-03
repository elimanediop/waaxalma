import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api import health
from app.bootstrap import container
from app.sessions.session_manager import SessionManager
from app.sessions.sqlite_session_repository import SQLiteSessionRepository


def test_health_without_client_identity():
    with TestClient(app) as client:
        assert client.get('/health').status_code==200
        assert client.get('/health/live').json()['version']=='1.0.0'
        assert client.get('/health/ready').status_code==200
    assert app.state.startup_complete is False


def test_readiness_before_startup_is_503():
    app.state.startup_complete=False
    with TestClient(app) as client:
        app.state.startup_complete=False
        assert client.get('/health/ready').status_code==503
        assert client.get('/health/live').status_code==200


def test_local_failure_does_not_kill_liveness(monkeypatch):
    with TestClient(app) as client:
        def failure(): raise OSError('private filesystem path')
        monkeypatch.setattr(health,'check_local_resources',failure)
        response=client.get('/health/ready')
        assert response.status_code==503
        assert response.json()=={'status':'not_ready'}
        assert client.get('/health/live').status_code==200


def test_readiness_checks_sqlite_without_mutation(tmp_path,monkeypatch):
    repo=SQLiteSessionRepository(tmp_path/'sessions.db')
    manager=SessionManager(repo)
    session=manager.create_session('interpreter',owner_id='client-a')
    manager.add_message(session.session_id,'user','preserve this')
    before=repo.get(session.session_id)
    monkeypatch.setattr(container,'session_manager',manager)
    with TestClient(app) as client:
        assert client.get('/health/ready').status_code==200
    assert repo.get(session.session_id)==before


def test_removed_database_is_not_recreated_by_readiness(tmp_path,monkeypatch):
    repo=SQLiteSessionRepository(tmp_path/'sessions.db')
    monkeypatch.setattr(container,'session_manager',SessionManager(repo))
    with TestClient(app) as client:
        repo.database_path.unlink()
        assert client.get('/health/ready').status_code==503
        assert not repo.database_path.exists()
        assert client.get('/health/live').status_code==200
