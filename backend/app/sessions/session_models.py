from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


SESSION_STATUS_ACTIVE = "active"
SESSION_STATUS_CLOSED = "closed"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ConversationSession:
    session_id: str
    agent_name: str
    owner_id: str | None = None
    execution_mode: str = "standard"
    source_language: str = "auto"
    target_language: str = "English"
    status: str = SESSION_STATUS_ACTIVE
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    closed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    history: list[dict[str, Any]] = field(default_factory=list)

    @staticmethod
    def create(
        agent_name: str,
        target_language: str = "English",
        *,
        owner_id: str | None = None,
        source_language: str = "auto",
        execution_mode: str = "standard",
        metadata: dict[str, Any] | None = None,
    ) -> "ConversationSession":
        now = utc_now()

        return ConversationSession(
            session_id=str(uuid4()),
            agent_name=agent_name,
            owner_id=owner_id,
            execution_mode=execution_mode,
            source_language=source_language,
            target_language=target_language,
            status=SESSION_STATUS_ACTIVE,
            created_at=now,
            updated_at=now,
            metadata=dict(metadata or {}),
        )

    @property
    def is_active(self) -> bool:
        return self.status == SESSION_STATUS_ACTIVE

    def add_message(
        self,
        role: str,
        content: str,
    ) -> dict[str, Any]:
        now = utc_now()

        message = {
            "role": role,
            "content": content,
            "timestamp": now.isoformat(),
        }

        self.history.append(message)
        self.updated_at = now

        return message

    def update(
        self,
        *,
        source_language: str | None = None,
        target_language: str | None = None,
        execution_mode: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if source_language is not None:
            self.source_language = source_language

        if target_language is not None:
            self.target_language = target_language

        if execution_mode is not None:
            self.execution_mode = execution_mode

        if metadata:
            self.metadata.update(metadata)

        self.updated_at = utc_now()

    def close(self) -> None:
        if self.status == SESSION_STATUS_CLOSED:
            return

        now = utc_now()

        self.status = SESSION_STATUS_CLOSED
        self.closed_at = now
        self.updated_at = now
