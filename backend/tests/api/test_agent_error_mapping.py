import pytest

from app.core.agent_result import AgentResult
from app.exceptions.agent_execution_exception import (
    AgentExecutionException,
)
from app.orchestration.result_handler import (
    require_agent_output,
)


@pytest.mark.parametrize(
    ("error_code", "expected_status"),
    [
        ("PROVIDER_TIMEOUT", 504),
        ("PROVIDER_UNAVAILABLE", 503),
        ("PROVIDER_RATE_LIMITED", 503),
        ("PROVIDER_REQUEST_FAILED", 502),
        ("PROVIDER_AUTHENTICATION_FAILED", 502),
        ("INVALID_INPUT", 400),
    ],
)
def test_agent_error_is_mapped_to_http_status(
    error_code: str,
    expected_status: int,
) -> None:
    result = AgentResult(
        success=False,
        error_code=error_code,
        error_message="Test failure.",
    )

    with pytest.raises(
        AgentExecutionException
    ) as captured:
        require_agent_output(result)

    assert captured.value.code == error_code
    assert captured.value.status_code == expected_status
    assert captured.value.message == "Test failure."