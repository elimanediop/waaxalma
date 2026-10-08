"""Run with WAAXALMA_TEST_POSTGRES_URL pointing to an Alembic-upgraded disposable database."""
import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import pytest

psycopg = pytest.importorskip('psycopg')
from app.sessions.session_models import ConversationSession
from app.sessions.postgresql_session_repository import PostgreSQLSessionRepository


@pytest.fixture
def pg_repo():
    url = os.getenv('WAAXALMA_TEST_POSTGRES_URL')
    if not url:
        pytest.skip('Set WAAXALMA_TEST_POSTGRES_URL for live PostgreSQL integration tests')
    repo = PostgreSQLSessionRepository(url)
    repo.check_readiness()
    yield repo


@pytest.fixture
def fresh_session(pg_repo):
    session = ConversationSession.create('interpreter', owner_id='integration-owner', metadata={'nested': {'a': 1}})
    pg_repo.create(session)
    yield session
    with pg_repo._connect() as db, db.cursor() as cur:
        cur.execute('DELETE FROM translation_sessions WHERE session_id=%s', (session.session_id,))


def test_lifecycle_messages_order_and_restart(pg_repo, fresh_session):
    sid = fresh_session.session_id
    for idx in range(12):
        pg_repo.append_message(sid, {'role': 'user', 'content': f'message-{idx}', 'timestamp': fresh_session.created_at.isoformat()}, updated_at=fresh_session.updated_at.isoformat())
    again = PostgreSQLSessionRepository(pg_repo.database_url).get(sid)
    assert again.owner_id == 'integration-owner'
    assert again.metadata == {'nested': {'a': 1}}
    assert [m['content'] for m in again.history] == [f'message-{i}' for i in range(12)]
    again.update(target_language='French')
    again.close()
    pg_repo.update(again)
    persisted = PostgreSQLSessionRepository(pg_repo.database_url).get(sid)
    assert persisted.status == 'closed' and persisted.target_language == 'French'
    assert len(persisted.history) == 12


def test_missing_session_and_duplicate(pg_repo, fresh_session):
    with pytest.raises(ValueError):
        pg_repo.create(fresh_session)
    with pytest.raises(KeyError):
        pg_repo.append_message(str(uuid4()), {'role': 'user', 'content': 'x'}, updated_at=fresh_session.updated_at.isoformat())
    assert pg_repo.get(str(uuid4())) is None


def test_concurrent_appends_preserve_all_messages(pg_repo, fresh_session):
    sid = fresh_session.session_id
    def append(i):
        pg_repo.append_message(sid, {'role': 'user', 'content': str(i)}, updated_at=fresh_session.updated_at.isoformat())
    with ThreadPoolExecutor(max_workers=6) as executor:
        list(executor.map(append, range(30)))
    messages = pg_repo.get(sid).history
    assert len(messages) == 30
    assert {m['content'] for m in messages} == {str(i) for i in range(30)}


def test_readiness(pg_repo):
    pg_repo.check_readiness()
