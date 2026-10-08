import os
import pytest
from app.sessions.sqlite_session_repository import SQLiteSessionRepository
from app.sessions.session_models import ConversationSession
from scripts.migrate_sqlite_to_postgres import migrate


def test_import_preflight_does_not_write(tmp_path):
    pytest.importorskip('psycopg')
    url = os.getenv('WAAXALMA_TEST_POSTGRES_URL')
    if not url:
        pytest.skip('Requires disposable PostgreSQL with Alembic upgrade head')
    path = tmp_path / 'sessions.db'
    sqlite_repo = SQLiteSessionRepository(path)
    session = ConversationSession.create('interpreter', owner_id=None)
    sqlite_repo.create(session)
    result = migrate(str(path), url)
    assert result['mode'] == 'preflight'
    assert result['source_sessions'] == 1
    assert result['unowned_sessions'] == 1
