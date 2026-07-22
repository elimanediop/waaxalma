import uuid

from app.agents.base_agent import BaseAgent
from app.core.agent_input import AgentInput
from app.core.agent_result import AgentResult
from app.core.config import STATIC_AUDIO_URL_PREFIX
from app.core.session_context import SessionContext
from app.providers.openai_provider import (
    OpenAISpeechProvider,
    OpenAISpeechToTextProvider,
    OpenAITranslationProvider,
)
from app.skills.speech_skill import SpeechSkill
from app.skills.speech_to_text_skill import SpeechToTextSkill
from app.skills.translation_skill import TranslationSkill


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
            return self._execute_text_interpretation(
                payload=payload,
                context=context,
            )

        if operation == "interpret_audio":
            return self._execute_audio_interpretation(
                payload=payload,
                context=context,
            )

        return AgentResult(
            success=False,
            error_code="UNSUPPORTED_OPERATION",
            error_message=(
                f"Operation '{operation}' is not supported "
                f"by agent '{self.name}'"
            ),
            metadata={
                "agent": self.name,
                "operation": operation,
                "session_id": context.session_id,
            },
        )

    def _execute_text_interpretation(
        self,
        payload: dict,
        context: SessionContext,
    ) -> AgentResult:
        text = payload.get("text")

        if not text:
            return AgentResult(
                success=False,
                error_code="INVALID_INPUT",
                error_message="'text' is required",
                metadata={
                    "agent": self.name,
                    "operation": "interpret",
                    "session_id": context.session_id,
                },
            )

        target_language = payload.get(
            "target_language",
            context.target_language,
        )

        output = self.interpret(
            text=text,
            target_language=target_language,
            session_id=context.session_id,
        )

        return AgentResult(
            success=True,
            output=output,
            metadata={
                "agent": self.name,
                "operation": "interpret",
                "session_id": context.session_id,
            },
        )

    def _execute_audio_interpretation(
        self,
        payload: dict,
        context: SessionContext,
    ) -> AgentResult:
        audio_path = payload.get("audio_path")

        if not audio_path:
            return AgentResult(
                success=False,
                error_code="INVALID_INPUT",
                error_message="'audio_path' is required",
                metadata={
                    "agent": self.name,
                    "operation": "interpret_audio",
                    "session_id": context.session_id,
                },
            )

        target_language = payload.get(
            "target_language",
            context.target_language,
        )

        output = self.interpret_audio(
            audio_path=audio_path,
            target_language=target_language,
            session_id=context.session_id,
        )

        return AgentResult(
            success=True,
            output=output,
            metadata={
                "agent": self.name,
                "operation": "interpret_audio",
                "session_id": context.session_id,
            },
        )

    def interpret(
        self,
        text: str,
        target_language: str = "English",
        session_id: str | None = None,
    ) -> dict:
        request_id = str(uuid.uuid4())

        interpreted_text = self.translation_skill.execute(
            text=text,
            target_language=target_language,
        )

        output_filename = f"{request_id}.mp3"

        self.speech_skill.execute(
            text=interpreted_text,
            output_filename=output_filename,
        )

        return {
            "request_id": request_id,
            "session_id": session_id,
            "agent": self.name,
            "source_text": text,
            "interpreted_text": interpreted_text,
            "audio_url": (
                f"{STATIC_AUDIO_URL_PREFIX}/{output_filename}"
            ),
        }

    def interpret_audio(
        self,
        audio_path: str,
        target_language: str = "English",
        session_id: str | None = None,
    ) -> dict:
        source_text = self.speech_to_text_skill.execute(
            audio_path,
        )

        return self.interpret(
            text=source_text,
            target_language=target_language,
            session_id=session_id,
        )