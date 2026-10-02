from app.core.session_context import SessionContext
from app.pipelines.pipeline_stage import PipelineStage
from app.pipelines.pipeline_state import PipelineState


class SequentialPipeline:

    def __init__(
        self,
        *,
        name: str,
        stages: list[PipelineStage],
    ) -> None:
        if not name.strip():
            raise ValueError(
                "Pipeline name cannot be empty."
            )

        if not stages:
            raise ValueError(
                f"Pipeline '{name}' must contain at least one stage."
            )

        self._name = name
        self._stages = list(stages)

    @property
    def name(self) -> str:
        return self._name

    @property
    def stage_names(self) -> list[str]:
        return [
            stage.name
            for stage in self._stages
        ]

    async def execute(
        self,
        state: PipelineState,
        context: SessionContext,
    ) -> PipelineState:
        current_state = state

        for stage in self._stages:
            current_state = await stage.execute(
                state=current_state,
                context=context,
            )

        return current_state