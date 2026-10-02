from typing import Any

from app.core.agent_result import AgentResult
from app.exceptions.agent_execution_exception import (
    AgentExecutionException,
)
from app.exceptions.error_codes import ErrorCode
from app.exceptions.pipeline_exception import PipelineException


def require_agent_output(
    result: AgentResult,
) -> dict[str, Any]:
    """
    Return the output of a successful AgentResult.

    Raise a normalized exception when execution failed or when the
    result does not contain an output payload.
    """

    if not result.success:
        raise AgentExecutionException.from_result(result)

    if result.output is None:
        raise PipelineException(
            code=ErrorCode.INVALID_AGENT_RESULT,
            message="The agent returned no output.",
            status_code=500,
            details={
                "agent": result.agent_name,
            }
            if getattr(result, "agent_name", None)
            else None,
        )

    return result.output