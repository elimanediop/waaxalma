from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.core.execution_trace import ExecutionTrace


class SessionContext(BaseModel):
    session_id: str = Field(
        default_factory=lambda: str(uuid4())
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    source_language: str | None = None
    target_language: str = "en"

    data: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    trace: ExecutionTrace = Field(
        default_factory=ExecutionTrace
    )