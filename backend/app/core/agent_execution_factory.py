from dataclasses import dataclass
from typing import Any

from app.core.agent_input import AgentInput
from app.core.session_context import SessionContext


@dataclass(frozen=True)
class AgentExecution:
    agent_input: AgentInput
    context: SessionContext


class AgentExecutionFactory:

    @staticmethod
    def create(
        operation: str,
        payload: dict[str, Any] | None = None,
        session_id: str | None = None,
        source_language: str | None = None,
        target_language: str = "English",
        input_metadata: dict[str, Any] | None = None,
        context_metadata: dict[str, Any] | None = None,
    ) -> AgentExecution:
        context_values: dict[str, Any] = {
            "source_language": source_language,
            "target_language": target_language,
            "metadata": context_metadata or {},
        }

        if session_id is not None:
            context_values["session_id"] = session_id

        return AgentExecution(
            agent_input=AgentInput(
                operation=operation,
                payload=payload or {},
                metadata=input_metadata or {},
            ),
            context=SessionContext(**context_values),
        )