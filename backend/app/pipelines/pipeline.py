from typing import Protocol

from app.core.session_context import SessionContext
from app.pipelines.pipeline_state import PipelineState


class Pipeline(Protocol):

    @property
    def name(self) -> str:
        ...

    @property
    def stage_names(self) -> list[str]:
        ...

    async def execute(
        self,
        state: PipelineState,
        context: SessionContext,
    ) -> PipelineState:
        ...