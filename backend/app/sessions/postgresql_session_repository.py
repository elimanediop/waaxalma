"""PostgreSQL persistence adapter. Schema is managed by Alembic, not at startup."""
from __future__ import annotations
from datetime import datetime
from typing import Any
import json
import psycopg
from psycopg.rows import dict_row
from psycopg.errors import UniqueViolation
from app.sessions.session_repository import SessionRepository
from app.sessions.session_models import ConversationSession

class PostgreSQLSessionRepository(SessionRepository):
    def __init__(self, database_url: str):
        self.database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)

    def _connect(self):
        return psycopg.connect(self.database_url, row_factory=dict_row, connect_timeout=5)

    def check_readiness(self) -> None:
        with self._connect() as db, db.cursor() as cur:
            cur.execute("SELECT session_id FROM translation_sessions LIMIT 0")
            cur.execute("SELECT 1")

    @staticmethod
    def _values(session: ConversationSession) -> tuple:
        return (session.session_id, session.agent_name, session.owner_id,
                session.execution_mode, session.source_language, session.target_language,
                session.status, session.created_at, session.updated_at, session.closed_at,
                json.dumps(session.metadata))

    @staticmethod
    def _insert_message(cur, session_id: str, message: dict[str, Any]) -> None:
        cur.execute("""INSERT INTO translation_messages(session_id, role, content, created_at)
                       VALUES (%s,%s,%s,%s)""", (session_id, str(message.get('role','')),
                        str(message.get('content','')), str(message.get('timestamp',''))))

    def create(self, session: ConversationSession) -> ConversationSession:
        try:
            with self._connect() as db, db.cursor() as cur:
                cur.execute("""INSERT INTO translation_sessions
                    (session_id,agent_name,owner_id,execution_mode,source_language,
                     target_language,status,created_at,updated_at,closed_at,metadata_json)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)""", self._values(session))
                for msg in session.history:
                    self._insert_message(cur, session.session_id, msg)
        except UniqueViolation as exc:
            raise ValueError(f"Session '{session.session_id}' already exists.") from exc
        return self.get(session.session_id)

    def get(self, session_id: str) -> ConversationSession | None:
        with self._connect() as db, db.cursor() as cur:
            cur.execute("SELECT * FROM translation_sessions WHERE session_id=%s", (session_id,))
            row = cur.fetchone()
            if row is None:
                return None
            cur.execute("""SELECT role,content,created_at FROM translation_messages
                           WHERE session_id=%s ORDER BY id ASC""", (session_id,))
            messages = cur.fetchall()
        def dt(value):
            return datetime.fromisoformat(value) if isinstance(value,str) else value
        metadata = row['metadata_json']
        if isinstance(metadata,str): metadata = json.loads(metadata)
        return ConversationSession(session_id=row['session_id'], agent_name=row['agent_name'],
            owner_id=row['owner_id'], execution_mode=row['execution_mode'],
            source_language=row['source_language'], target_language=row['target_language'],
            status=row['status'], created_at=dt(row['created_at']), updated_at=dt(row['updated_at']),
            closed_at=dt(row['closed_at']) if row['closed_at'] else None,
            metadata=metadata, history=[dict(role=m['role'],content=m['content'],timestamp=m['created_at']) for m in messages])

    def update(self, session: ConversationSession) -> ConversationSession:
        with self._connect() as db, db.cursor() as cur:
            cur.execute("""UPDATE translation_sessions SET agent_name=%s, execution_mode=%s,
                source_language=%s, target_language=%s, status=%s, created_at=%s,
                updated_at=%s, closed_at=%s, metadata_json=%s::jsonb
                WHERE session_id=%s""", (session.agent_name, session.execution_mode,
                session.source_language, session.target_language, session.status,
                session.created_at, session.updated_at, session.closed_at,
                json.dumps(session.metadata), session.session_id))
            if cur.rowcount == 0: raise KeyError(session.session_id)
        return self.get(session.session_id)

    def append_message(self, session_id: str, message: dict[str, Any], *, updated_at: str) -> None:
        with self._connect() as db, db.cursor() as cur:
            cur.execute("UPDATE translation_sessions SET updated_at=%s WHERE session_id=%s",
                        (updated_at,session_id))
            if cur.rowcount == 0: raise KeyError(session_id)
            self._insert_message(cur,session_id,message)

    def purge_closed_before(self, cutoff: datetime, *, dry_run: bool=True) -> int:
        if cutoff.tzinfo is None: raise ValueError('Retention cutoff must have a timezone')
        with self._connect() as db, db.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS n FROM translation_sessions WHERE status='closed' AND closed_at < %s",(cutoff,))
            count=cur.fetchone()['n']
            if not dry_run:
                cur.execute("DELETE FROM translation_sessions WHERE status='closed' AND closed_at < %s",(cutoff,))
            return count
