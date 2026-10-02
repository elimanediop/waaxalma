from typing import Any

from app.agents.base_agent import BaseAgent
from app.core.agent_input import AgentInput
from app.core.agent_result import AgentResult
from app.core.session_context import SessionContext
from app.exceptions.error_codes import ErrorCode
from app.skills.context_skill import ContextSkill


class ContextAgent(BaseAgent):
    description = (
        "Agent that enriches input text with contextual information."
    )

    def __init__(
        self,
        context_skill: ContextSkill,
    ) -> None:
        self.context_skill = context_skill

    @property
    def name(self) -> str:
        return "context"

    async def execute(
        self,
        agent_input: AgentInput,
        context: SessionContext,
    ) -> AgentResult:
        if agent_input.operation != "enrich":
            return AgentResult(
                success=False,
                output=None,
                error_code=ErrorCode.UNSUPPORTED_OPERATION.value,
                error_message=(
                    f"Operation '{agent_input.operation}' "
                    f"is not supported by agent '{self.name}'."
                ),
                metadata=self._build_metadata(
                    operation=agent_input.operation,
                    context=context,
                ),
            )

        text = agent_input.payload.get("text")

        if not isinstance(text, str) or not text.strip():
            return AgentResult(
                success=False,
                output=None,
                error_code=ErrorCode.INVALID_INPUT.value,
                error_message="'text' is required.",
                metadata=self._build_metadata(
                    operation=agent_input.operation,
                    context=context,
                ),
            )

        metadata = agent_input.payload.get(
            "metadata",
            {},
        )

        if not isinstance(metadata, dict):
            return AgentResult(
                success=False,
                output=None,
                error_code=ErrorCode.INVALID_INPUT.value,
                error_message="'metadata' must be an object.",
                metadata=self._build_metadata(
                    operation=agent_input.operation,
                    context=context,
                ),
            )

        result = await self.context_skill.execute(
            text=text.strip(),
            metadata=metadata,
        )

        return AgentResult(
            success=True,
            output={
                "agent": self.name,
                "original_text": result.original_text,
                "enriched_text": result.enriched_text,
                "metadata": result.metadata,
            },
            metadata=self._build_metadata(
                operation=agent_input.operation,
                context=context,
            ),
        )

    def _build_metadata(
        self,
        *,
        operation: str,
        context: SessionContext,
    ) -> dict[str, Any]:
        return {
            "agent": self.name,
            "operation": operation,
            "session_id": context.session_id,
        }