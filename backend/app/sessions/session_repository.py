from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.sessions.session_models import ConversationSession


class SessionRepository(ABC):
    """Persistence contract for application-level conversation sessions."""

    @abstractmethod
    def create(
        self,
        session: ConversationSession,
    ) -> ConversationSession:
        raise NotImplementedError

    @abstractmethod
    def list_by_owner(self, owner_id: str, *, limit: int = 50, offset: int = 0) -> list[ConversationSession]:
        """List only sessions owned by the authenticated user."""
        raise NotImplementedError

    @abstractmethod
    def get(
        self,
        session_id: str,
    ) -> ConversationSession | None:
        raise NotImplementedError

    @abstractmethod
    def update(
        self,
        session: ConversationSession,
    ) -> ConversationSession:
        raise NotImplementedError

    @abstractmethod
    def append_message(
        self,
        session_id: str,
        message: dict[str, Any],
        *,
        updated_at: str,
    ) -> None:
        raise NotImplementedError
