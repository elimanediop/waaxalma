from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Iterator
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any

from app.sessions.session_models import ConversationSession
from app.sessions.session_repository import SessionRepository
from app.sessions.database_tools import SESSION_SCHEMA_VERSION, require_supported_schema


class SQLiteSessionRepository(SessionRepository):
    """SQLite-backed persistent session repository.

    A connection is opened per repository operation. This keeps the repository
    safe to use from FastAPI worker threads without sharing sqlite connection
    objects across threads.
    """

    def __init__(
        self,
        database_path: str | Path,
    ) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        self._initialize_schema()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(
            str(self.database_path),
            timeout=5.0,
        )
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            with connection:
                yield connection
        finally:
            # SQLite's own context manager commits/rolls back, but does not
            # close the handle. Always release it, including on exceptions.
            connection.close()

    def _initialize_schema(self) -> None:
        with self._connect() as connection:
            require_supported_schema(connection.execute("PRAGMA user_version").fetchone()[0])
            connection.execute("PRAGMA journal_mode = WAL")
            # Keep all schema changes in one serialized transaction.
            connection.execute("BEGIN IMMEDIATE")
            require_supported_schema(connection.execute("PRAGMA user_version").fetchone()[0])
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    agent_name TEXT NOT NULL,
                    owner_id TEXT,
                    execution_mode TEXT NOT NULL,
                    source_language TEXT NOT NULL,
                    target_language TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    closed_at TEXT,
                    metadata_json TEXT NOT NULL
                )
                """
            )
            # Never auto-claim legacy data.
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(sessions)")}
            if "owner_id" not in columns:
                connection.execute("ALTER TABLE sessions ADD COLUMN owner_id TEXT")
            connection.execute(f"PRAGMA user_version = {SESSION_SCHEMA_VERSION}")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS session_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(session_id)
                        REFERENCES sessions(session_id)
                        ON DELETE CASCADE
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                    idx_session_messages_session_id_id
                ON session_messages(session_id, id)
                """
            )

    def purge_closed_before(self, cutoff: datetime, *, dry_run: bool = True) -> int:
        from contextlib import closing
        if cutoff.tzinfo is None:
            raise ValueError("Retention cutoff must have a timezone")
        # Existing database only; transactions serialize count/delete and cascades.
        with closing(sqlite3.connect(self.database_path.as_uri()+"?mode=rw", uri=True, timeout=5)) as connection, connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("BEGIN IMMEDIATE")
            condition = "status = 'closed' AND closed_at IS NOT NULL AND julianday(closed_at) < julianday(?)"
            params = (cutoff.isoformat(),)
            count = connection.execute("SELECT COUNT(*) FROM sessions WHERE " + condition, params).fetchone()[0]
            if not dry_run:
                connection.execute("DELETE FROM sessions WHERE " + condition, params)
            return count

    def count_active(self) -> int:
        from contextlib import closing
        # Read-only existing DB: a scrape never recreates deleted data.
        with closing(sqlite3.connect(self.database_path.as_uri() + "?mode=ro", uri=True, timeout=.25)) as connection:
            return connection.execute("SELECT COUNT(*) FROM sessions WHERE status = 'active'").fetchone()[0]

    def create(
        self,
        session: ConversationSession,
    ) -> ConversationSession:
        with self._connect() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO sessions (
                        session_id,
                        agent_name,
                        execution_mode,
                        source_language,
                        target_language,
                        status,
                        created_at,
                        updated_at,
                        closed_at,
                        metadata_json,
                        owner_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    self._session_values(session),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError(
                    f"Session '{session.session_id}' already exists."
                ) from exc

            for message in session.history:
                self._insert_message(
                    connection,
                    session.session_id,
                    message,
                )

        persisted = self.get(session.session_id)
        assert persisted is not None
        return persisted

    def list_by_owner(self, owner_id: str, *, limit: int = 50, offset: int = 0) -> list[ConversationSession]:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT session_id FROM sessions WHERE owner_id = ?
                   ORDER BY created_at DESC, session_id DESC LIMIT ? OFFSET ?""",
                (owner_id, limit, offset),
            ).fetchall()
            ids = [row["session_id"] for row in rows]
        return [session for sid in ids if (session := self.get(sid)) is not None]

    def get(
        self,
        session_id: str,
    ) -> ConversationSession | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    session_id,
                    agent_name,
                    execution_mode,
                    source_language,
                    target_language,
                    status,
                    created_at,
                    updated_at,
                    closed_at,
                    metadata_json,
                    owner_id
                FROM sessions
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()

            if row is None:
                return None

            message_rows = connection.execute(
                """
                SELECT role, content, created_at
                FROM session_messages
                WHERE session_id = ?
                ORDER BY id ASC
                """,
                (session_id,),
            ).fetchall()

        history = [
            {
                "role": message["role"],
                "content": message["content"],
                "timestamp": message["created_at"],
            }
            for message in message_rows
        ]

        return ConversationSession(
            session_id=row["session_id"],
            agent_name=row["agent_name"],
            owner_id=row["owner_id"],
            execution_mode=row["execution_mode"],
            source_language=row["source_language"],
            target_language=row["target_language"],
            status=row["status"],
            created_at=self._parse_datetime(row["created_at"]),
            updated_at=self._parse_datetime(row["updated_at"]),
            closed_at=(
                self._parse_datetime(row["closed_at"])
                if row["closed_at"]
                else None
            ),
            metadata=json.loads(row["metadata_json"]),
            history=history,
        )

    def update(
        self,
        session: ConversationSession,
    ) -> ConversationSession:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE sessions
                SET
                    agent_name = ?,
                    execution_mode = ?,
                    source_language = ?,
                    target_language = ?,
                    status = ?,
                    created_at = ?,
                    updated_at = ?,
                    closed_at = ?,
                    metadata_json = ?
                WHERE session_id = ?
                """,
                (
                    session.agent_name,
                    session.execution_mode,
                    session.source_language,
                    session.target_language,
                    session.status,
                    session.created_at.isoformat(),
                    session.updated_at.isoformat(),
                    (
                        session.closed_at.isoformat()
                        if session.closed_at is not None
                        else None
                    ),
                    self._serialize_metadata(session.metadata),
                    session.session_id,
                ),
            )

            if cursor.rowcount == 0:
                raise KeyError(session.session_id)

        persisted = self.get(session.session_id)
        assert persisted is not None
        return persisted

    def append_message(
        self,
        session_id: str,
        message: dict[str, Any],
        *,
        updated_at: str,
    ) -> None:
        with self._connect() as connection:
            exists = connection.execute(
                """
                SELECT 1
                FROM sessions
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()

            if exists is None:
                raise KeyError(session_id)

            self._insert_message(
                connection,
                session_id,
                message,
            )

            connection.execute(
                """
                UPDATE sessions
                SET updated_at = ?
                WHERE session_id = ?
                """,
                (updated_at, session_id),
            )

    def _insert_message(
        self,
        connection: sqlite3.Connection,
        session_id: str,
        message: dict[str, Any],
    ) -> None:
        connection.execute(
            """
            INSERT INTO session_messages (
                session_id,
                role,
                content,
                created_at
            ) VALUES (?, ?, ?, ?)
            """,
            (
                session_id,
                str(message.get("role", "")),
                str(message.get("content", "")),
                str(message.get("timestamp", "")),
            ),
        )

    @staticmethod
    def _session_values(
        session: ConversationSession,
    ) -> tuple[Any, ...]:
        return (
            session.session_id,
            session.agent_name,
            session.execution_mode,
            session.source_language,
            session.target_language,
            session.status,
            session.created_at.isoformat(),
            session.updated_at.isoformat(),
            (
                session.closed_at.isoformat()
                if session.closed_at is not None
                else None
            ),
            SQLiteSessionRepository._serialize_metadata(
                session.metadata
            ),
            session.owner_id,
        )

    @staticmethod
    def _serialize_metadata(
        metadata: dict[str, Any],
    ) -> str:
        return json.dumps(
            metadata,
            separators=(",", ":"),
            sort_keys=True,
        )

    @staticmethod
    def _parse_datetime(value: str) -> datetime:
        parsed = datetime.fromisoformat(value)

        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)

        return parsed
