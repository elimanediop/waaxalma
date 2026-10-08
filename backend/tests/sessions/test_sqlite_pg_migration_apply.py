"""End-to-end SQLite v2 -> PostgreSQL import using a dedicated, disposable database."""
import os

import pytest

pytest.importorskip('psycopg')
from app.sessions.session_models import ConversationSession
from app.sessions.sqlite_session_repository import SQLiteSessionRepository
from app.sessions.postgresql_session_repository import PostgreSQLSessionRepository
from scripts.migrate_sqlite_to_postgres import migrate


def test_migration_apply_preserves_sessions_and_order(tmp_path):
    url = os.getenv('WAAXALMA_MIGRATION_TEST_POSTGRES_URL')
    if not url:
        pytest.skip('Requires WAAXALMA_MIGRATION_TEST_POSTGRES_URL (disposable, empty, Alembic-upgraded database)')
    source = tmp_path / 'source.sqlite3'
    sqlite = SQLiteSessionRepository(source)
    session = ConversationSession.create('interpreter', owner_id='legacy-client', metadata={'nested': {'value': 7}})
    sqlite.create(session)
    for i in range(5):
        sqlite.append_message(session.session_id, {'role': 'user', 'content': f'line-{i}', 'timestamp': session.created_at.isoformat()}, updated_at=session.updated_at.isoformat())

    preflight = migrate(str(source), url)
    assert preflight['mode'] == 'preflight'
    assert (preflight['source_sessions'], preflight['source_messages']) == (1, 5)
    applied = migrate(str(source), url, apply=True)
    assert (applied['verified_sessions'], applied['verified_messages']) == (1, 5)
    migrated = PostgreSQLSessionRepository(url).get(session.session_id)
    assert migrated is not None
    assert migrated.owner_id == 'legacy-client'
    assert migrated.metadata == {'nested': {'value': 7}}
    assert [m['content'] for m in migrated.history] == [f'line-{i}' for i in range(5)]
    with pytest.raises(ValueError, match='Destination must be empty'):
        migrate(str(source), url, apply=True)
