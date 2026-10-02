import uuid

from app.core.config import STATIC_AUDIO_URL_PREFIX
from app.core.session_context import SessionContext
from app.observability.stage_tracer import trace_async_stage
from app.pipelines.pipeline_state import PipelineState
from app.skills.speech_skill import SpeechSkill


class SpeechStage:

    def __init__(
        self,
        speech_skill: SpeechSkill,
    ) -> None:
        self._speech_skill = speech_skill

    @property
    def name(self) -> str:
        return "speech"

    async def execute(
        self,
        state: PipelineState,
        context: SessionContext,
    ) -> PipelineState:
        interpreted_text = state.require(
            "interpreted_text"
        )

        agent_name = state.require(
            "agent_name"
        )

        request_id = state.get("request_id")

        if not request_id:
            request_id = str(uuid.uuid4())

            state.set(
                "request_id",
                request_id,
            )

        output_filename = (
            f"{request_id}.mp3"
        )

        await trace_async_stage(
            trace=context.trace,
            agent=agent_name,
            stage=self.name,
            operation="speak",
            provider=self._speech_skill.provider_name,
            call=lambda: self._speech_skill.execute(
                text=interpreted_text,
                output_filename=output_filename,
            ),
        )

        state.set(
            "audio_url",
            (
                f"{STATIC_AUDIO_URL_PREFIX}/"
                f"{output_filename}"
            ),
        )

        return state