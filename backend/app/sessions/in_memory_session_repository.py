from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from threading import RLock
from typing import Any

from app.sessions.session_models import ConversationSession
from app.sessions.session_repository import SessionRepository


class InMemorySessionRepository(SessionRepository):
    """Deterministic repository implementation for tests and local use."""

    def __init__(self) -> None:
        self._sessions: dict[str, ConversationSession] = {}
        self._lock = RLock()

    def purge_closed_before(self, cutoff: datetime, *, dry_run: bool = True) -> int:
        if cutoff.tzinfo is None:
            raise ValueError("Retention cutoff must have a timezone")
        with self._lock:
            keys = [key for key, session in self._sessions.items()
                    if not session.is_active and session.closed_at is not None and session.closed_at < cutoff]
            if not dry_run:
                for key in keys:
                    del self._sessions[key]
            return len(keys)

    def count_active(self) -> int:
        with self._lock:
            return sum(session.is_active for session in self._sessions.values())

    def create(
        self,
        session: ConversationSession,
    ) -> ConversationSession:
        with self._lock:
            if session.session_id in self._sessions:
                raise ValueError(
                    f"Session '{session.session_id}' already exists."
                )

            self._sessions[session.session_id] = deepcopy(session)
            return deepcopy(session)

    def get(
        self,
        session_id: str,
    ) -> ConversationSession | None:
        with self._lock:
            session = self._sessions.get(session_id)
            return deepcopy(session) if session is not None else None

    def update(
        self,
        session: ConversationSession,
    ) -> ConversationSession:
        with self._lock:
            if session.session_id not in self._sessions:
                raise KeyError(session.session_id)

            persisted = deepcopy(session)
            persisted.owner_id = self._sessions[session.session_id].owner_id
            self._sessions[session.session_id] = persisted
            return deepcopy(persisted)

    def append_message(
        self,
        session_id: str,
        message: dict[str, Any],
        *,
        updated_at: str,
    ) -> None:
        with self._lock:
            session = self._sessions.get(session_id)

            if session is None:
                raise KeyError(session_id)

            session.history.append(deepcopy(message))
            session.updated_at = datetime.fromisoformat(
                updated_at
            )
