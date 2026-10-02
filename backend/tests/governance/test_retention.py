from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import asyncio
import pytest
from app.sessions.sqlite_session_repository import SQLiteSessionRepository
from app.sessions.in_memory_session_repository import InMemorySessionRepository
from app.sessions.session_manager import SessionManager
from app.sessions.retention import cleanup, RetentionWorker


@pytest.fixture(params=['memory','sqlite'])
def repository(request,tmp_path):
    return InMemorySessionRepository() if request.param == 'memory' else SQLiteSessionRepository(tmp_path/'sessions.db')


def test_retention_only_deletes_old_closed_rows_and_their_messages(repository):
    service = SessionManager(repository)
    now = datetime.now(timezone.utc)
    old = service.create_session('interpreter',owner_id='owner')
    service.add_message(old.session_id,'user','private transcript')
    old = service.close_session(old.session_id)
    old.closed_at = now-timedelta(days=31)
    repository.update(old)
    active = service.create_session('interpreter',owner_id='owner')
    active.created_at = now-timedelta(days=365)
    repository.update(active)
    recent = service.close_session(service.create_session('interpreter',owner_id='owner').session_id)
    boundary = service.close_session(service.create_session('interpreter',owner_id='owner').session_id)
    boundary.closed_at = now-timedelta(days=30)
    repository.update(boundary)
    assert cleanup(repository,30,dry_run=True,now=now) == 1
    assert repository.get(old.session_id) is not None
    assert cleanup(repository,30,dry_run=False,now=now) == 1
    assert repository.get(old.session_id) is None
    assert repository.get(active.session_id).is_active
    assert repository.get(recent.session_id) is not None
    assert repository.get(boundary.session_id) is not None
    assert cleanup(repository,30,dry_run=False,now=now) == 0
    if hasattr(repository,'_connect'):
        with repository._connect() as db:
            assert db.execute('SELECT COUNT(*) FROM session_messages WHERE session_id=?',(old.session_id,)).fetchone()[0] == 0


def test_purge_missing_database_does_not_recreate_it(tmp_path):
    repo = SQLiteSessionRepository(tmp_path/'sessions.db')
    repo.database_path.unlink()
    with pytest.raises(Exception):
        repo.purge_closed_before(datetime.now(timezone.utc))
    assert not repo.database_path.exists()


@pytest.mark.parametrize('days',[0,-1])
def test_bad_retention_days_fail_without_deleting(repository,days):
    with pytest.raises(ValueError):
        cleanup(repository,days,dry_run=False)


def test_naive_clock_is_rejected(repository):
    with pytest.raises(ValueError):
        cleanup(repository,30,now=datetime.now())


@pytest.mark.asyncio
async def test_worker_disabled_does_not_mutate_repository(repository):
    worker = RetentionWorker(repository,SimpleNamespace(session_cleanup_enabled=False))
    worker.start()
    assert worker.task is None
    await worker.stop()


@pytest.mark.asyncio
async def test_worker_runs_and_stops_without_leaving_task(repository):
    settings = SimpleNamespace(session_cleanup_enabled=True,session_retention_days=30,session_cleanup_interval_seconds=.01)
    worker = RetentionWorker(repository,settings)
    worker.start()
    await asyncio.sleep(.02)
    await worker.stop()
    assert worker.task.done()


def test_offline_cli_dry_run_and_missing_database(tmp_path,capsys):
    from scripts.cleanup_sessions import main
    repo = SQLiteSessionRepository(tmp_path/'sessions.db')
    main(['--database',str(repo.database_path)])
    assert '"dry_run": true' in capsys.readouterr().out
    repo.database_path.unlink()
    with pytest.raises(SystemExit) as exc:
        main(['--database',str(repo.database_path),'--apply'])
    assert exc.value.code == 1
    assert not repo.database_path.exists()


def test_cli_passes_graceful_shutdown_budget(monkeypatch):
    from app import cli
    from app.core import settings
    import uvicorn
    calls = []
    monkeypatch.setattr(settings,'get_settings',lambda:SimpleNamespace(host='127.0.0.1',port=8000,log_level='info',shutdown_timeout_seconds=12))
    monkeypatch.setattr(uvicorn,'run',lambda *a,**kw:calls.append(kw))
    cli.main()
    assert calls[0]['timeout_graceful_shutdown'] == 12
    assert calls[0]['workers'] == 1
