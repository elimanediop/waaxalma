from typing import Any
from pydantic import BaseModel, Field


class AgentInput(BaseModel):
    operation: str
    session_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)