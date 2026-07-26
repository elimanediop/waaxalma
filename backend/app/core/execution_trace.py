from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class StageTrace(BaseModel):
    stage: str
    operation: str
    provider: str | None = None

    started_at: datetime
    finished_at: datetime

    duration_ms: float
    success: bool

    error_code: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExecutionTrace(BaseModel):
    trace_id: str = Field(
        default_factory=lambda: str(uuid4())
    )

    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    total_duration_ms: float | None = None

    stages: list[StageTrace] = Field(
        default_factory=list
    )

    def add_stage(
        self,
        stage: StageTrace,
    ) -> None:
        self.stages.append(stage)

    def stage_durations(self) -> dict[str, float]:
        return {
            stage.stage: stage.duration_ms
            for stage in self.stages
        }