from app.core.session_context import SessionContext
from app.observability.stage_tracer import trace_async_stage
from app.pipelines.pipeline_state import PipelineState
from app.skills.translation_skill import TranslationSkill


class TranslationStage:

    def __init__(
        self,
        translation_skill: TranslationSkill,
    ) -> None:
        self._translation_skill = translation_skill

    @property
    def name(self) -> str:
        return "translation"

    async def execute(
        self,
        state: PipelineState,
        context: SessionContext,
    ) -> PipelineState:
        source_text = state.require(
            "source_text"
        )
        translation_input = state.get(
            "enriched_text",
            source_text,
        )
        agent_name = state.require("agent_name")

        target_language = state.get(
            "target_language",
            context.target_language,
        )

        interpreted_text = await trace_async_stage(
            trace=context.trace,
            agent=agent_name,
            stage=self.name,
            operation="translate",
            provider=self._translation_skill.provider_name,
            call=lambda: self._translation_skill.execute(
                text=translation_input,
                target_language=target_language,
            ),
        )

        state.set(
            "interpreted_text",
            interpreted_text,
        )

        return state