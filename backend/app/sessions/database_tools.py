"""Read-only upgrade inspection and SQLite-consistent backup utilities."""
from contextlib import closing
import os
from pathlib import Path
import sqlite3

SESSION_SCHEMA_VERSION = 2
SUPPORTED_SESSION_SCHEMA_VERSIONS = (0, 1, 2)


class UnsupportedSessionSchemaError(ValueError):
    pass


def require_supported_schema(version: int) -> None:
    if version not in SUPPORTED_SESSION_SCHEMA_VERSIONS:
        raise UnsupportedSessionSchemaError(
            f"Unsupported session schema version {version}; supported versions are 0, 1 and 2. "
            "Use a compatible release or restore a compatible backup."
        )


def inspect_database(database: str | Path) -> dict:
    path = Path(database).resolve()
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=5)) as connection:
        return _inspect(connection)


def _inspect(connection: sqlite3.Connection) -> dict:
    version = connection.execute("PRAGMA user_version").fetchone()[0]
    require_supported_schema(version)
    columns = {row[1] for row in connection.execute("PRAGMA table_info(sessions)")}
    required = {"session_id", "agent_name", "execution_mode", "source_language",
                "target_language", "status", "created_at", "updated_at", "closed_at", "metadata_json"}
    if not required.issubset(columns) or (version == 2 and "owner_id" not in columns):
        raise ValueError("Database does not contain a supported sessions schema.")
    message_columns = {row[1] for row in connection.execute("PRAGMA table_info(session_messages)")}
    if not {"id", "session_id", "role", "content", "created_at"}.issubset(message_columns):
        raise ValueError("Database does not contain a supported message schema.")
    if connection.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
        raise ValueError("SQLite integrity check failed.")
    if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
        raise ValueError("SQLite foreign-key check failed.")
    count = connection.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    messages = connection.execute("SELECT COUNT(*) FROM session_messages").fetchone()[0]
    unowned = (connection.execute("SELECT COUNT(*) FROM sessions WHERE owner_id IS NULL").fetchone()[0]
               if "owner_id" in columns else count)
    return {"schema_version": version, "target_schema_version": SESSION_SCHEMA_VERSION,
            "sessions": count, "messages": messages, "unowned_sessions": unowned,
            "migration_required": version != SESSION_SCHEMA_VERSION, "integrity": "ok"}


def backup_database(database: str | Path, destination: str | Path) -> dict:
    source = Path(database).resolve()
    target = Path(destination).resolve()
    if source == target:
        raise ValueError("Backup destination must differ from the source.")
    with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True, timeout=5)) as connection:
        _inspect(connection)
        # Reserve a new private destination exclusively; never overwrite a backup.
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(descriptor)
        try:
            with closing(sqlite3.connect(str(target), timeout=5)) as backup:
                connection.backup(backup)
                backup.execute("PRAGMA journal_mode = DELETE")
                report = _inspect(backup)
        except BaseException:
            target.unlink(missing_ok=True)
            raise
    return report
