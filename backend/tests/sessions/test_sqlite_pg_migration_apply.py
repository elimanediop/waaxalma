"""End-to-end SQLite v2 -> PostgreSQL import on a disposable test database.

WARNING: The fixture clears translation data in the dedicated migration test DB.
Never point WAAXALMA_MIGRATION_TEST_POSTGRES_URL at an application database.
"""
import os

import pytest

psycopg = pytest.importorskip('psycopg')
from psycopg.conninfo import conninfo_to_dict

from app.sessions.session_models import ConversationSession
from app.sessions.sqlite_session_repository import SQLiteSessionRepository
from app.sessions.postgresql_session_repository import PostgreSQLSessionRepository
from scripts.migrate_sqlite_to_postgres import migrate


@pytest.fixture
def empty_migration_database():
    url = os.getenv('WAAXALMA_MIGRATION_TEST_POSTGRES_URL')
    if not url:
        pytest.skip('Requires WAAXALMA_MIGRATION_TEST_POSTGRES_URL')

    normalized = url.replace('postgresql+psycopg://', 'postgresql://', 1)
    params = conninfo_to_dict(normalized)
    # Explicit guard: never truncate a general-purpose or production database.
    if params.get('dbname') != 'waaxalma_migration_test' or params.get('host') not in ('localhost', '127.0.0.1', '::1', 'postgres'):
        pytest.fail('Refusing destructive test cleanup: expected dedicated waaxalma_migration_test on local/CI PostgreSQL')

    def clear():
        with psycopg.connect(normalized, connect_timeout=5) as db:
            with db.cursor() as cur:
                cur.execute('TRUNCATE TABLE translation_messages, translation_sessions RESTART IDENTITY')

    clear()
    try:
        yield normalized
    finally:
        clear()


def test_migration_apply_preserves_sessions_and_order(tmp_path, empty_migration_database):
    url = empty_migration_database
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
