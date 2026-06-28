from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
import uuid


@dataclass
class ConversationSession:
    session_id: str
    agent_name: str
    source_language: str = "auto"
    target_language: str = "English"
    created_at: datetime = field(default_factory=datetime.utcnow)
    history: list[dict[str, Any]] = field(default_factory=list)

    @staticmethod
    def create(agent_name: str, target_language: str = "English") -> "ConversationSession":
        return ConversationSession(
            session_id=str(uuid.uuid4()),
            agent_name=agent_name,
            target_language=target_language,
        )

    def add_message(self, role: str, content: str) -> None:
        self.history.append(
            {
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )