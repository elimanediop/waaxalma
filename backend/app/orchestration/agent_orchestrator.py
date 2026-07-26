import asyncio
import logging
import time

from app.agents.base_agent import BaseAgent
from app.core.agent_input import AgentInput
from app.core.agent_result import AgentResult
from app.core.session_context import SessionContext
from app.exceptions.error_codes import ErrorCode
from app.exceptions.pipeline_exception import PipelineException


logger = logging.getLogger(__name__)


class AgentOrchestrator:

    def __init__(
        self,
        agents: dict[str, BaseAgent],
    ) -> None:
        self._agents = agents

    async def execute(
        self,
        agent_name: str,
        agent_input: AgentInput,
        context: SessionContext,
    ) -> AgentResult:
        started_at = time.perf_counter()

        agent = self._agents.get(agent_name)

        if agent is None:
            return AgentResult(
                success=False,
                error_code=ErrorCode.AGENT_NOT_FOUND.value,
                error_message=f"Unknown agent: {agent_name}",
                metadata=self._build_metadata(
                    agent_name=agent_name,
                    operation=agent_input.operation,
                    context=context,
                ),
                duration_ms=self._elapsed_ms(started_at),
            )

        try:
            result = await agent.execute(
                agent_input,
                context,
            )

            result.duration_ms = self._elapsed_ms(started_at)

            result.metadata = {
                **(result.metadata or {}),
                **self._build_metadata(
                    agent_name=agent_name,
                    operation=agent_input.operation,
                    context=context,
                ),
            }

            return result

        except asyncio.CancelledError:
            # Une requête annulée ne doit jamais être transformée
            # en erreur métier ou être retentée.
            logger.info(
                "Agent execution cancelled "
                "agent=%s operation=%s session_id=%s",
                agent_name,
                agent_input.operation,
                context.session_id,
            )
            raise

        except PipelineException as exc:
            logger.warning(
                "Agent pipeline failure "
                "agent=%s operation=%s session_id=%s "
                "code=%s message=%s",
                agent_name,
                agent_input.operation,
                context.session_id,
                exc.code,
                exc.message,
            )

            metadata = self._build_metadata(
                agent_name=agent_name,
                operation=agent_input.operation,
                context=context,
            )

            metadata["http_status"] = exc.status_code

            if exc.details:
                metadata["error_details"] = exc.details

            return AgentResult(
                success=False,
                error_code=exc.code,
                error_message=exc.message,
                metadata=metadata,
                duration_ms=self._elapsed_ms(started_at),
            )

        except TimeoutError:
            logger.warning(
                "Agent execution timeout "
                "agent=%s operation=%s session_id=%s",
                agent_name,
                agent_input.operation,
                context.session_id,
            )

            return AgentResult(
                success=False,
                error_code=ErrorCode.AGENT_TIMEOUT.value,
                error_message=(
                    f"Agent '{agent_name}' timed out."
                ),
                metadata=self._build_metadata(
                    agent_name=agent_name,
                    operation=agent_input.operation,
                    context=context,
                ),
                duration_ms=self._elapsed_ms(started_at),
            )

        except Exception:
            logger.exception(
                "Unexpected agent execution failure "
                "agent=%s operation=%s session_id=%s",
                agent_name,
                agent_input.operation,
                context.session_id,
            )

            return AgentResult(
                success=False,
                error_code=(
                    ErrorCode.AGENT_EXECUTION_FAILED.value
                ),
                error_message=(
                    f"Agent '{agent_name}' execution failed."
                ),
                metadata=self._build_metadata(
                    agent_name=agent_name,
                    operation=agent_input.operation,
                    context=context,
                ),
                duration_ms=self._elapsed_ms(started_at),
            )

    @staticmethod
    def _build_metadata(
        *,
        agent_name: str,
        operation: str,
        context: SessionContext,
    ) -> dict:
        return {
            "agent": agent_name,
            "operation": operation,
            "session_id": context.session_id,
        }

    @staticmethod
    def _elapsed_ms(
        started_at: float,
    ) -> float:
        return round(
            (time.perf_counter() - started_at) * 1000,
            3,
        )