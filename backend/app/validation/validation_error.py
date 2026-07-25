from typing import Any

from app.exceptions.error_codes import ErrorCode
from app.exceptions.pipeline_exception import PipelineException


class AudioValidationError(PipelineException):
    """
    Exception raised when an uploaded audio file fails validation.
    """

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=status_code,
            details=details,
        )