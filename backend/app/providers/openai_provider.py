from openai import OpenAI

from app.core.config import (
    OPENAI_TRANSCRIPTION_MODEL,
    OPENAI_TRANSLATION_MODEL,
    OPENAI_TTS_MODEL,
    OPENAI_TTS_VOICE,
    AUDIO_OUTPUT_DIR,
)

import os

client = OpenAI()


class OpenAITranslationProvider:
    def translate(self, text: str, target_language: str = "English") -> str:
        response = client.responses.create(
            model=OPENAI_TRANSLATION_MODEL,
            input=f"""
You are Waaxalma, a voice translation assistant.

Translate the following text into {target_language}.
Keep the meaning faithful.
Use natural spoken language.
Return only the translation.

Text:
{text}
"""
        )

        return response.output_text.strip()


class OpenAISpeechProvider:
    def speak(self, text: str, output_filename: str) -> str:
        os.makedirs(AUDIO_OUTPUT_DIR, exist_ok=True)

        output_path = os.path.join(AUDIO_OUTPUT_DIR, output_filename)

        with client.audio.speech.with_streaming_response.create(
            model=OPENAI_TTS_MODEL,
            voice=OPENAI_TTS_VOICE,
            input=text,
            instructions="Speak clearly in natural English.",
        ) as response:
            response.stream_to_file(output_path)

        return output_path

class OpenAISpeechToTextProvider:
    def transcribe(self, audio_path: str) -> str:
        with open(audio_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model=OPENAI_TRANSCRIPTION_MODEL,
                file=audio_file,
                response_format="text",
            )

        return transcription.strip()