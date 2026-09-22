from app.core.session_context import SessionContext
from app.observability.stage_tracer import trace_async_stage
from app.pipelines.pipeline_state import PipelineState
from app.skills.quality_skill import QualitySkill


class QualityStage:

    def __init__(
        self,
        quality_skill: QualitySkill,
    ) -> None:
        self._quality_skill = quality_skill

    @property
    def name(self) -> str:
        return "quality"

    async def execute(
        self,
        state: PipelineState,
        context: SessionContext,
    ) -> PipelineState:
        source_text = state.require(
            "source_text"
        )

        interpreted_text = state.require(
            "interpreted_text"
        )

        target_language = state.get(
            "target_language",
            context.target_language,
        )

        agent_name = state.require(
            "agent_name"
        )

        result = await trace_async_stage(
            trace=context.trace,
            agent=agent_name,
            stage=self.name,
            operation="evaluate",
            provider=self._quality_skill.provider_name,
            call=lambda: self._quality_skill.execute(
                source_text=source_text,
                interpreted_text=interpreted_text,
                target_language=target_language,
            ),
        )

        state.set(
            "quality_accepted",
            result.accepted,
        )

        state.set(
            "quality_score",
            result.score,
        )

        state.set(
            "quality_issues",
            result.issues,
        )

        state.set(
            "quality_metadata",
            result.metadata,
        )

        return state