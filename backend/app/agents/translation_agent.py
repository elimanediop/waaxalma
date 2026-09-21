import uuid

from app.agents.base_agent import BaseAgent
from app.core.agent_input import AgentInput
from app.core.agent_result import AgentResult
from app.core.session_context import SessionContext
from app.core.config import STATIC_AUDIO_URL_PREFIX
from app.skills.translation_skill import TranslationSkill
from app.skills.speech_skill import SpeechSkill


class TranslationAgent(BaseAgent):
    description = "Agent that translates text and generates spoken audio."

    def __init__(
        self,
        translation_skill: TranslationSkill,
        speech_skill: SpeechSkill,
    ) -> None:
        self.translation_skill = translation_skill
        self.speech_skill = speech_skill


    @property
    def name(self) -> str:
        return "translation"

    async def execute(
        self,
        agent_input: AgentInput,
        context: SessionContext,
    ) -> AgentResult:
        operation = agent_input.operation
        payload = agent_input.payload

        text = payload.get("text")

        if not text:
            return AgentResult(
                success=False,
                output=None,
                error_code="INVALID_INPUT",
                error_message="'text' is required",
                metadata={
                    "agent": self.name,
                    "operation": operation,
                    "session_id": context.session_id,
                },
            )

        if operation == "translate":
            target_language = payload.get(
                "target_language",
                context.target_language,
            )

            output = await self.translate_text(
                text=text,
                target_language=target_language,
            )

        elif operation == "speak":
            output = await self.speak_text(
                text=text,
            )

        elif operation == "translate_and_speak":
            target_language = payload.get(
                "target_language",
                context.target_language,
            )

            output = await self.translate_and_speak(
                text=text,
                target_language=target_language,
            )

        else:
            return AgentResult(
                success=False,
                output=None,
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

        return AgentResult(
            success=True,
            output=output,
            metadata={
                "agent": self.name,
                "operation": operation,
                "session_id": context.session_id,
            },
        )

    async def translate_text(
        self,
        text: str,
        target_language: str = "English",
    ) -> dict:
        request_id = str(uuid.uuid4())

        translated_text = await self.translation_skill.execute(
            text=text,
            target_language=target_language,
        )

        return {
            "request_id": request_id,
            "agent": self.name,
            "original_text": text,
            "translated_text": translated_text,
        }

    async def speak_text(
        self,
        text: str,
    ) -> dict:
        request_id = str(uuid.uuid4())
        output_filename = f"{request_id}.mp3"

        await self.speech_skill.execute(
            text=text,
            output_filename=output_filename,
        )

        return {
            "request_id": request_id,
            "agent": self.name,
            "text": text,
            "audio_url": (
                f"{STATIC_AUDIO_URL_PREFIX}/{output_filename}"
            ),
        }

    async def translate_and_speak(
        self,
        text: str,
        target_language: str = "English",
    ) -> dict:
        request_id = str(uuid.uuid4())

        translated_text = await self.translation_skill.execute(
            text=text,
            target_language=target_language,
        )

        output_filename = f"{request_id}.mp3"

        await self.speech_skill.execute(
            text=translated_text,
            output_filename=output_filename,
        )

        return {
            "request_id": request_id,
            "agent": self.name,
            "original_text": text,
            "translated_text": translated_text,
            "audio_url": (
                f"{STATIC_AUDIO_URL_PREFIX}/{output_filename}"
            ),
        }