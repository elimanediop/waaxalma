import uuid

from app.agents.base_agent import BaseAgent
from app.core.config import STATIC_AUDIO_URL_PREFIX
from app.providers.openai_provider import (
    OpenAITranslationProvider,
    OpenAISpeechProvider,
)
from app.skills.translation_skill import TranslationSkill
from app.skills.speech_skill import SpeechSkill
from app.providers.openai_provider import OpenAISpeechToTextProvider
from app.skills.speech_to_text_skill import SpeechToTextSkill


class InterpreterAgent(BaseAgent):
    name = "interpreter-agent"
    description = "Agent that interprets user messages into another language and speaks them."

    def __init__(self):
        translation_provider = OpenAITranslationProvider()
        speech_provider = OpenAISpeechProvider()
        stt_provider = OpenAISpeechToTextProvider()
        self.speech_to_text_skill = SpeechToTextSkill(stt_provider)

        self.translation_skill = TranslationSkill(translation_provider)
        self.speech_skill = SpeechSkill(speech_provider)

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
            "audio_url": f"{STATIC_AUDIO_URL_PREFIX}/{output_filename}",
        }
    def interpret_audio(
    self,
    audio_path: str,
    target_language: str = "English",
    session_id: str | None = None,
    ) -> dict:  
     source_text = self.speech_to_text_skill.execute(audio_path)

     return self.interpret(
        text=source_text,
        target_language=target_language,
        session_id=session_id,
    )