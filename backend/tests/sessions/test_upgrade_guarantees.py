from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from app.sessions.database_tools import backup_database, inspect_database, UnsupportedSessionSchemaError
from app.sessions.sqlite_session_repository import SQLiteSessionRepository
from app.sessions.session_models import ConversationSession
from app.security.client_identity import ClientIdentity
from app.security.security_context import SecurityContext
from app.security.session_access_policy import SessionAccessPolicy, SessionAccessDeniedError


V05_SCHEMA = """
CREATE TABLE sessions (
 session_id TEXT PRIMARY KEY, agent_name TEXT NOT NULL, owner_id TEXT,
 execution_mode TEXT NOT NULL, source_language TEXT NOT NULL,
 target_language TEXT NOT NULL, status TEXT NOT NULL,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL, closed_at TEXT,
 metadata_json TEXT NOT NULL
);
CREATE TABLE session_messages (
 id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
 role TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL,
 FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);
CREATE INDEX idx_session_messages_session_id_id ON session_messages(session_id, id);
PRAGMA user_version = 2;
"""


def v05_database(path):
    # Freeze the prior schema independently of the new repository initializer.
    with closing(sqlite3.connect(path)) as db, db:
        db.executescript(V05_SCHEMA)
        for session_id, status, owner in (("active", "active", "client-a"), ("closed", "closed", "client-b"), ("legacy", "active", None)):
            db.execute("INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (
                session_id, "interpreter", owner, "standard", "auto", "English", status,
                "2026-10-01T09:00:00+00:00", "2026-10-02T09:00:00+00:00",
                "2026-10-02T09:00:00+00:00" if status == "closed" else None,
                json.dumps({"nested": {"name": "Waaxalma", "text": "é →"}}),
            ))
            for role, text in (("user", "bonjour"), ("assistant", "hello")):
                db.execute("INSERT INTO session_messages(session_id,role,content,created_at) VALUES (?,?,?,?)",
                           (session_id, role, text, "2026-10-02T09:00:00+00:00"))


def rows(path):
    with closing(sqlite3.connect(path)) as db:
        return (db.execute("SELECT * FROM sessions ORDER BY session_id").fetchall(),
                db.execute("SELECT * FROM session_messages ORDER BY id").fetchall())


def test_v05_upgrade_is_idempotent_and_preserves_all_stored_values(tmp_path):
    path = tmp_path / "sessions.db"
    v05_database(path)
    before = rows(path)
    for _ in range(3):
        repo = SQLiteSessionRepository(path)
        assert rows(path) == before
        assert repo.get("active").owner_id == "client-a"
        assert repo.get("closed").status == "closed"
        assert repo.get("closed").closed_at is not None
        assert repo.get("legacy").owner_id is None
        assert [m["content"] for m in repo.get("active").history] == ["bonjour", "hello"]
    with closing(sqlite3.connect(path)) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 2


def test_owned_and_unowned_security_boundaries_survive_upgrade(tmp_path):
    path = tmp_path / "sessions.db"
    v05_database(path)
    repo = SQLiteSessionRepository(path)
    owner = SecurityContext(ClientIdentity("client-a"))
    foreign = SecurityContext(ClientIdentity("client-b"))
    SessionAccessPolicy.require_access(context=owner, session=repo.get("active"))
    for context, session_id in ((foreign, "active"), (owner, "legacy")):
        with pytest.raises(SessionAccessDeniedError):
            SessionAccessPolicy.require_access(context=context, session=repo.get(session_id))


def test_newer_schema_is_rejected_without_downgrading_or_mutating(tmp_path):
    path = tmp_path / "future.db"
    v05_database(path)
    with closing(sqlite3.connect(path)) as db:
        db.execute("PRAGMA user_version = 99")
    before = hashlib.sha256(path.read_bytes()).digest()
    with pytest.raises(UnsupportedSessionSchemaError):
        SQLiteSessionRepository(path)
    assert hashlib.sha256(path.read_bytes()).digest() == before
    with pytest.raises(UnsupportedSessionSchemaError):
        inspect_database(path)


def test_backup_restores_data_without_overwriting_destination(tmp_path):
    path = tmp_path / "sessions.db"
    target = tmp_path / "backup.db"
    v05_database(path)
    before = rows(path)
    report = backup_database(path, target)
    assert report["sessions"] == 3 and report["messages"] == 6
    assert report["unowned_sessions"] == 1
    assert rows(target) == before
    repo = SQLiteSessionRepository(path)
    session = repo.get("active")
    session.close()
    repo.update(session)
    assert rows(target) == before
    with pytest.raises(FileExistsError):
        backup_database(path, target)
    assert rows(target) == before


def test_backup_captures_committed_wal_rows(tmp_path):
    path = tmp_path / "wal.db"
    v05_database(path)
    with closing(sqlite3.connect(path)) as writer:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("PRAGMA wal_autocheckpoint=0")
        writer.execute("UPDATE sessions SET target_language='French' WHERE session_id='active'")
        writer.commit()
        assert Path(str(path) + "-wal").exists()
        backup_database(path, tmp_path / "backup.db")
    assert SQLiteSessionRepository(tmp_path / "backup.db").get("active").target_language == "French"


def test_inspection_is_read_only_and_missing_path_is_not_created(tmp_path):
    path = tmp_path / "sessions.db"
    v05_database(path)
    before = path.read_bytes()
    report = inspect_database(path)
    assert report["schema_version"] == 2 and not report["migration_required"]
    assert path.read_bytes() == before
    missing = tmp_path / "missing.db"
    with pytest.raises(sqlite3.OperationalError):
        inspect_database(missing)
    assert not missing.exists()


def test_backup_rejects_same_path_and_foreign_database(tmp_path):
    path = tmp_path / "sessions.db"
    v05_database(path)
    with pytest.raises(ValueError, match="differ"):
        backup_database(path, path)
    foreign = tmp_path / "other.db"
    with closing(sqlite3.connect(foreign)) as db:
        db.execute("CREATE TABLE unrelated (id INTEGER)")
    with pytest.raises(ValueError, match="sessions schema"):
        backup_database(foreign, tmp_path / "backup.db")
    assert not (tmp_path / "backup.db").exists()


@pytest.mark.parametrize("version", [0, 1])
def test_legacy_inspection_does_not_claim_or_migrate(version, tmp_path):
    path = tmp_path / "legacy.db"
    v05_database(path)
    with closing(sqlite3.connect(path)) as db:
        db.execute("ALTER TABLE sessions DROP COLUMN owner_id")
        db.execute(f"PRAGMA user_version = {version}")
    report = inspect_database(path)
    assert report["unowned_sessions"] == 3 and report["migration_required"]
    repo = SQLiteSessionRepository(path)
    assert repo.get("active").owner_id is None
    assert inspect_database(path)["schema_version"] == 2


def test_separate_processes_reopen_committed_sessions(tmp_path):
    path = tmp_path / "restart.db"
    repo = SQLiteSessionRepository(path)
    session = ConversationSession.create("interpreter", owner_id="client-a", metadata={"restart": True})
    repo.create(session)
    repo.append_message(session.session_id, {"role": "user", "content": "é →", "timestamp": session.created_at.isoformat()}, updated_at=session.updated_at.isoformat())
    code = """
import sys
from app.sessions.sqlite_session_repository import SQLiteSessionRepository
repo=SQLiteSessionRepository(sys.argv[1])
session=repo.get(sys.argv[2])
assert session.owner_id == 'client-a'
assert session.metadata == {'restart': True}
assert len(session.history) == 1
if sys.argv[3] == 'close':
    session.close()
    repo.update(session)
else:
    assert session.status == 'closed' and session.closed_at is not None
"""
    for mode in ("close", "verify"):
        subprocess.run([sys.executable, "-c", code, str(path), session.session_id, mode], check=True, timeout=10)
    assert repo.get(session.session_id).status == "closed"
