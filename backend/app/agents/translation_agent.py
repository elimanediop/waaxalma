import uuid

from app.agents.base_agent import BaseAgent
from app.core.config import STATIC_AUDIO_URL_PREFIX
from app.providers.openai_provider import (
    OpenAITranslationProvider,
    OpenAISpeechProvider,
)
from app.skills.translation_skill import TranslationSkill
from app.skills.speech_skill import SpeechSkill


class TranslationAgent(BaseAgent):
    name = "translation-agent"
    description = "Agent that translates text and generates spoken audio."

    def __init__(self):
        translation_provider = OpenAITranslationProvider()
        speech_provider = OpenAISpeechProvider()

        self.translation_skill = TranslationSkill(translation_provider)
        self.speech_skill = SpeechSkill(speech_provider)

    def translate_text(self, text: str, target_language: str = "English") -> dict:
        request_id = str(uuid.uuid4())

        translated_text = self.translation_skill.execute(
            text=text,
            target_language=target_language,
        )

        return {
            "request_id": request_id,
            "agent": self.name,
            "original_text": text,
            "translated_text": translated_text,
        }

    def speak_text(self, text: str) -> dict:
        request_id = str(uuid.uuid4())

        output_filename = f"{request_id}.mp3"

        self.speech_skill.execute(
            text=text,
            output_filename=output_filename,
        )

        return {
            "request_id": request_id,
            "agent": self.name,
            "text": text,
            "audio_url": f"{STATIC_AUDIO_URL_PREFIX}/{output_filename}",
        }

    def translate_and_speak(self, text: str, target_language: str = "English") -> dict:
        request_id = str(uuid.uuid4())

        translated_text = self.translation_skill.execute(
            text=text,
            target_language=target_language,
        )

        output_filename = f"{request_id}.mp3"

        self.speech_skill.execute(
            text=translated_text,
            output_filename=output_filename,
        )

        return {
            "request_id": request_id,
            "agent": self.name,
            "original_text": text,
            "translated_text": translated_text,
            "audio_url": f"{STATIC_AUDIO_URL_PREFIX}/{output_filename}",
        }