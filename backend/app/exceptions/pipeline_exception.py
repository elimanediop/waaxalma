from typing import Any

from app.exceptions.error_codes import ErrorCode


class PipelineException(Exception):
    """
    Base exception for predictable pipeline failures.

    The API layer can convert this exception into a stable HTTP response
    without exposing internal implementation details.
    """

    def __init__(
        self,
        code: ErrorCode | str,
        message: str,
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code.value if isinstance(code, ErrorCode) else code
        self.message = message
        self.status_code = status_code
        self.details = details

        super().__init__(message)

    def to_detail(self) -> dict[str, Any]:
        detail: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
        }

        if self.details:
            detail["details"] = self.details

        return detail