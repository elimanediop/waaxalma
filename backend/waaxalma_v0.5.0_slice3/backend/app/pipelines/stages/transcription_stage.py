from app.core.session_context import SessionContext
from app.observability.stage_tracer import trace_async_stage
from app.pipelines.pipeline_state import PipelineState
from app.skills.speech_to_text_skill import SpeechToTextSkill


class TranscriptionStage:

    def __init__(
        self,
        speech_to_text_skill: SpeechToTextSkill,
    ) -> None:
        self._speech_to_text_skill = speech_to_text_skill

    @property
    def name(self) -> str:
        return "transcription"

    async def execute(
        self,
        state: PipelineState,
        context: SessionContext,
    ) -> PipelineState:
        audio_path = state.require("audio_path")
        agent_name = state.require("agent_name")

        source_text = await trace_async_stage(
            trace=context.trace,
            agent=agent_name,
            stage=self.name,
            operation="transcribe",
            provider=self._speech_to_text_skill.provider_name,
            call=lambda: self._speech_to_text_skill.execute(
                audio_path=audio_path,
            ),
        )

        state.set(
            "source_text",
            source_text,
        )

        return state