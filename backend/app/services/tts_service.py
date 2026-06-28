import os
from openai import OpenAI

from app.core.config import (
    AUDIO_OUTPUT_DIR,
    OPENAI_TTS_MODEL,
    OPENAI_TTS_VOICE,
)

client = OpenAI()


def generate_speech(text: str, output_filename: str) -> str:
    os.makedirs(AUDIO_OUTPUT_DIR, exist_ok=True)

    output_path = os.path.join(AUDIO_OUTPUT_DIR, output_filename)

    with client.audio.speech.with_streaming_response.create(
        model=OPENAI_TTS_MODEL,
        voice=OPENAI_TTS_VOICE,
        input=text,
        instructions="Speak clearly in natural English."
    ) as response:
        response.stream_to_file(output_path)

    return output_path