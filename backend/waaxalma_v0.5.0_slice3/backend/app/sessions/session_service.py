from __future__ import annotations

from typing import Any

from app.sessions.session_models import ConversationSession
from app.sessions.session_repository import SessionRepository


class SessionNotFoundError(LookupError):
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__(f"Session '{session_id}' was not found.")


class SessionClosedError(RuntimeError):
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__(f"Session '{session_id}' is closed.")


class SessionService:
    def __init__(
        self,
        repository: SessionRepository,
    ) -> None:
        self.repository = repository

    def create_session(
        self,
        agent_name: str,
        target_language: str = "English",
        *,
        owner_id: str | None = None,
        source_language: str = "auto",
        execution_mode: str = "standard",
        metadata: dict[str, Any] | None = None,
    ) -> ConversationSession:
        session = ConversationSession.create(
            agent_name=agent_name,
            owner_id=owner_id,
            target_language=target_language,
            source_language=source_language,
            execution_mode=execution_mode,
            metadata=metadata,
        )

        return self.repository.create(session)

    def get_session(
        self,
        session_id: str,
    ) -> ConversationSession | None:
        return self.repository.get(session_id)

    def require_session(
        self,
        session_id: str,
    ) -> ConversationSession:
        session = self.get_session(session_id)

        if session is None:
            raise SessionNotFoundError(session_id)

        return session

    def require_active_session(
        self,
        session_id: str,
    ) -> ConversationSession:
        session = self.require_session(session_id)

        if not session.is_active:
            raise SessionClosedError(session_id)

        return session

    def update_session(
        self,
        session_id: str,
        *,
        source_language: str | None = None,
        target_language: str | None = None,
        execution_mode: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ConversationSession:
        session = self.require_active_session(session_id)

        session.update(
            source_language=source_language,
            target_language=target_language,
            execution_mode=execution_mode,
            metadata=metadata,
        )

        return self.repository.update(session)

    def close_session(
        self,
        session_id: str,
    ) -> ConversationSession:
        session = self.require_session(session_id)

        if not session.is_active:
            return session

        session.close()
        return self.repository.update(session)

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
    ) -> None:
        session = self.require_active_session(session_id)
        message = session.add_message(
            role=role,
            content=content,
        )

        self.repository.append_message(
            session_id=session_id,
            message=message,
            updated_at=session.updated_at.isoformat(),
        )
