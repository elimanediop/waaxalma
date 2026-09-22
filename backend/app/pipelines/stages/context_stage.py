from app.core.session_context import SessionContext
from app.observability.stage_tracer import trace_async_stage
from app.pipelines.pipeline_state import PipelineState
from app.skills.context_skill import ContextSkill


class ContextStage:

    def __init__(
        self,
        context_skill: ContextSkill,
    ) -> None:
        self._context_skill = context_skill

    @property
    def name(self) -> str:
        return "context"

    async def execute(
        self,
        state: PipelineState,
        context: SessionContext,
    ) -> PipelineState:
        source_text = state.require(
            "source_text"
        )

        agent_name = state.require(
            "agent_name"
        )

        metadata = state.get(
            "context_metadata",
            {},
        )

        result = await trace_async_stage(
            trace=context.trace,
            agent=agent_name,
            stage=self.name,
            operation="enrich",
            provider=self._context_skill.provider_name,
            call=lambda: self._context_skill.execute(
                text=source_text,
                metadata=metadata,
            ),
        )

        state.set(
            "enriched_text",
            result.enriched_text,
        )

        state.set(
            "context_metadata",
            result.metadata,
        )

        return state