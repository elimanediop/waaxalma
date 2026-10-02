from typing import Any

from app.agents.base_agent import BaseAgent
from app.core.agent_input import AgentInput
from app.core.agent_result import AgentResult
from app.core.session_context import SessionContext
from app.exceptions.error_codes import ErrorCode
from app.skills.quality_skill import QualitySkill


class QualityAgent(BaseAgent):
    description = (
        "Agent that evaluates the quality of interpreted text."
    )

    def __init__(
        self,
        quality_skill: QualitySkill,
    ) -> None:
        self.quality_skill = quality_skill

    @property
    def name(self) -> str:
        return "quality"

    async def execute(
        self,
        agent_input: AgentInput,
        context: SessionContext,
    ) -> AgentResult:
        if agent_input.operation != "evaluate":
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

        source_text = agent_input.payload.get(
            "source_text"
        )

        interpreted_text = agent_input.payload.get(
            "interpreted_text"
        )

        target_language = agent_input.payload.get(
            "target_language",
            context.target_language,
        )

        if (
            not isinstance(source_text, str)
            or not source_text.strip()
        ):
            return AgentResult(
                success=False,
                output=None,
                error_code=ErrorCode.INVALID_INPUT.value,
                error_message="'source_text' is required.",
                metadata=self._build_metadata(
                    operation=agent_input.operation,
                    context=context,
                ),
            )

        if (
            not isinstance(interpreted_text, str)
            or not interpreted_text.strip()
        ):
            return AgentResult(
                success=False,
                output=None,
                error_code=ErrorCode.INVALID_INPUT.value,
                error_message="'interpreted_text' is required.",
                metadata=self._build_metadata(
                    operation=agent_input.operation,
                    context=context,
                ),
            )

        if (
            not isinstance(target_language, str)
            or not target_language.strip()
        ):
            return AgentResult(
                success=False,
                output=None,
                error_code=ErrorCode.INVALID_INPUT.value,
                error_message="'target_language' is required.",
                metadata=self._build_metadata(
                    operation=agent_input.operation,
                    context=context,
                ),
            )

        result = await self.quality_skill.execute(
            source_text=source_text.strip(),
            interpreted_text=interpreted_text.strip(),
            target_language=target_language.strip(),
        )

        return AgentResult(
            success=True,
            output={
                "agent": self.name,
                "accepted": result.accepted,
                "score": result.score,
                "issues": result.issues,
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