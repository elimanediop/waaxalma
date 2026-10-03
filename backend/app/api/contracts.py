"""HTTP error schema shared by runtime handlers and OpenAPI."""
from typing import Any
from pydantic import BaseModel, Field


class APIErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class APIErrorResponse(BaseModel):
    detail: APIErrorDetail


class AgentListResponse(BaseModel):
    agents: list[str] = Field(default_factory=list)


ERROR_RESPONSES = {
    code: {"model": APIErrorResponse}
    for code in (400, 401, 403, 404, 405, 409, 422, 500, 502, 503, 504)
}
