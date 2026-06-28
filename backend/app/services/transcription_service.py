from openai import OpenAI
from app.core.config import OPENAI_TRANSCRIPTION_MODEL

client = OpenAI()

def transcribe_audio(file_path: str) -> str:
    with open(file_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model=OPENAI_TRANSCRIPTION_MODEL,
            file=audio_file,
            response_format="text"
        )

    return transcription.strip()