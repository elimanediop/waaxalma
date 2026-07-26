import time

from app.agents.base_agent import BaseAgent
from app.core.agent_input import AgentInput
from app.core.agent_result import AgentResult
from app.core.session_context import SessionContext
from app.exceptions.pipeline_exception import PipelineException


class AgentOrchestrator:

    def __init__(self, agents: dict[str, BaseAgent]) -> None:
        self._agents = agents

    async def execute(
        self,
        agent_name: str,
        agent_input: AgentInput,
        context: SessionContext,
    ) -> AgentResult:
        agent = self._agents.get(agent_name)

        if agent is None:
            return AgentResult(
                success=False,
                error_code="AGENT_NOT_FOUND",
                error_message=f"Unknown agent: {agent_name}",
            )

        started_at = time.perf_counter()

        try:
            result = await agent.execute(agent_input, context)
            result.duration_ms = (
                time.perf_counter() - started_at
            ) * 1000
            return result
        except TimeoutError:
            return AgentResult(
                success=False,
                error_code="AGENT_TIMEOUT",
                error_message=f"Agent {agent_name} timed out",
                duration_ms=(
                    time.perf_counter() - started_at
                ) * 1000,
            )
        except Exception as exc:
            return AgentResult(
                success=False,
                error_code="AGENT_EXECUTION_ERROR",
                error_message=str(exc),
                duration_ms=(
                    time.perf_counter() - started_at
                ) * 1000,
            )