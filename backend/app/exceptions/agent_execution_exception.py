from typing import Any

from app.core.agent_result import AgentResult
from app.exceptions.error_codes import ErrorCode
from app.exceptions.pipeline_exception import PipelineException


AGENT_ERROR_STATUS_CODES: dict[str, int] = {
    ErrorCode.AGENT_NOT_FOUND.value: 404,
    ErrorCode.INVALID_INPUT.value: 400,
    ErrorCode.UNSUPPORTED_OPERATION.value: 400,
    ErrorCode.AGENT_TIMEOUT.value: 504,

    ErrorCode.PROVIDER_TIMEOUT.value: 504,
    ErrorCode.PROVIDER_UNAVAILABLE.value: 503,
    ErrorCode.PROVIDER_RATE_LIMITED.value: 503,
    ErrorCode.PROVIDER_AUTHENTICATION_FAILED.value: 502,
    ErrorCode.PROVIDER_REQUEST_FAILED.value: 502,

    ErrorCode.INVALID_AGENT_RESULT.value: 500,
    ErrorCode.AGENT_EXECUTION_FAILED.value: 500,
}


class AgentExecutionException(PipelineException):
    """
    Represents a normalized agent execution failure.

    API routes can raise this exception directly from an unsuccessful
    AgentResult without performing their own HTTP status mapping.
    """

    def __init__(
        self,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=AGENT_ERROR_STATUS_CODES.get(code, 500),
            details=details,
        )

    @classmethod
    def from_result(
        cls,
        result: AgentResult,
    ) -> "AgentExecutionException":
        code = (
            result.error_code
            or ErrorCode.AGENT_EXECUTION_FAILED.value
        )

        message = (
            result.error_message
            or "Agent execution failed."
        )

        details: dict[str, Any] = {}

        if result.metadata:
            details["metadata"] = result.metadata

        return cls(
            code=code,
            message=message,
            details=details or None,
        )