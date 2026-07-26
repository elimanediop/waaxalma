import uuid
from typing import Any

from app.agents.base_agent import BaseAgent
from app.core.agent_input import AgentInput
from app.core.agent_result import AgentResult
from app.core.config import STATIC_AUDIO_URL_PREFIX
from app.core.session_context import SessionContext
from app.exceptions.error_codes import ErrorCode
from app.providers.openai_provider import (
    OpenAISpeechProvider,
    OpenAISpeechToTextProvider,
    OpenAITranslationProvider,
)
from app.skills.speech_skill import SpeechSkill
from app.skills.speech_to_text_skill import SpeechToTextSkill
from app.skills.translation_skill import TranslationSkill

from app.observability.stage_tracer import trace_async_stage


class InterpreterAgent(BaseAgent):
    description = (
        "Agent that interprets user messages into another language "
        "and generates spoken audio."
    )

    def __init__(self) -> None:
        translation_provider = OpenAITranslationProvider()
        speech_provider = OpenAISpeechProvider()
        speech_to_text_provider = OpenAISpeechToTextProvider()

        self.translation_skill = TranslationSkill(
            translation_provider,
        )
        self.speech_skill = SpeechSkill(
            speech_provider,
        )
        self.speech_to_text_skill = SpeechToTextSkill(
            speech_to_text_provider,
        )

    @property
    def name(self) -> str:
        return "interpreter"

    async def execute(
        self,
        agent_input: AgentInput,
        context: SessionContext,
    ) -> AgentResult:
        operation = agent_input.operation
        payload = agent_input.payload

        if operation == "interpret":
            return await self._execute_text_interpretation(
                payload=payload,
                context=context,
            )

        if operation == "interpret_audio":
            return await self._execute_audio_interpretation(
                payload=payload,
                context=context,
            )

        return AgentResult(
            success=False,
            error_code=ErrorCode.UNSUPPORTED_OPERATION.value,
            error_message=(
                f"Operation '{operation}' is not supported "
                f"by agent '{self.name}'."
            ),
            metadata=self._build_metadata(
                operation=operation,
                context=context,
            ),
        )

    async def _execute_text_interpretation(
        self,
        payload: dict[str, Any],
        context: SessionContext,
    ) -> AgentResult:
        text = payload.get("text")

        if not isinstance(text, str) or not text.strip():
            return AgentResult(
                success=False,
                error_code=ErrorCode.INVALID_INPUT.value,
                error_message="'text' is required.",
                metadata=self._build_metadata(
                    operation="interpret",
                    context=context,
                ),
            )

        target_language = payload.get(
            "target_language",
            context.target_language,
        )

        output = await self.interpret(
            text=text.strip(),
            target_language=target_language,
            context=context,
        )
        return AgentResult(
            success=True,
            output=output,
            metadata=self._build_metadata(
                operation="interpret",
                context=context,
            ),
        )

    async def _execute_audio_interpretation(
        self,
        payload: dict[str, Any],
        context: SessionContext,
    ) -> AgentResult:
        audio_path = payload.get("audio_path")

        if not isinstance(audio_path, str) or not audio_path.strip():
            return AgentResult(
                success=False,
                error_code=ErrorCode.INVALID_INPUT.value,
                error_message="'audio_path' is required.",
                metadata=self._build_metadata(
                    operation="interpret_audio",
                    context=context,
                ),
            )

        target_language = payload.get(
            "target_language",
            context.target_language,
        )

        output = await self.interpret_audio(
            audio_path=audio_path,
            target_language=target_language,
            context=context,
        )

        return AgentResult(
            success=True,
            output=output,
            metadata=self._build_metadata(
                operation="interpret_audio",
                context=context,
            ),
        )

    async def interpret(
    self,
    text: str,
    target_language: str,
    context: SessionContext,
    ) -> dict:
        request_id = str(uuid.uuid4())

        interpreted_text = await trace_async_stage(
            trace=context.trace,
            agent=self.name,
            stage="translation",
            operation="translate",
            provider=self.translation_skill.provider_name,
            call=lambda: self.translation_skill.execute(
                text=text,
                target_language=target_language,
            ),
        )

        output_filename = f"{request_id}.mp3"

        await trace_async_stage(
            trace=context.trace,
            agent=self.name,
            stage="speech",
            operation="speak",
            provider=self.speech_skill.provider_name,
            call=lambda: self.speech_skill.execute(
                text=interpreted_text,
                output_filename=output_filename,
            ),
        )

        return {
            "request_id": request_id,
            "session_id": context.session_id,
            "agent": self.name,
            "source_text": text,
            "interpreted_text": interpreted_text,
            "audio_url": (
                f"{STATIC_AUDIO_URL_PREFIX}/{output_filename}"
            ),
    }


    async def interpret_audio(
        self,
        audio_path: str,
        target_language: str,
        context: SessionContext,
    ) -> dict:
        source_text = await trace_async_stage(
            trace=context.trace,
            agent=self.name,
            stage="transcription",
            operation="transcribe",
            provider=self.speech_to_text_skill.provider_name,
            call=lambda: self.speech_to_text_skill.execute(
                audio_path=audio_path,
            ),
        )

        return await self.interpret(
            text=source_text,
            target_language=target_language,
            context=context,
        )


    def _build_metadata(
        self,
        operation: str,
        context: SessionContext,
    ) -> dict[str, Any]:
        return {
            "agent": self.name,
            "operation": operation,
            "session_id": context.session_id,
        }