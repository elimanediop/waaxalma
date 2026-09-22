import os
from dotenv import load_dotenv

load_dotenv()

TRANSLATION_PROVIDER = os.getenv(
    "TRANSLATION_PROVIDER",
    "openai",
).strip().lower()

SPEECH_PROVIDER = os.getenv(
    "SPEECH_PROVIDER",
    "openai",
).strip().lower()

SPEECH_TO_TEXT_PROVIDER = os.getenv(
    "SPEECH_TO_TEXT_PROVIDER",
    "openai",
).strip().lower()

CONTEXT_PROVIDER = os.getenv(
    "CONTEXT_PROVIDER",
    "passthrough",
).strip().lower()

QUALITY_PROVIDER = os.getenv(
    "QUALITY_PROVIDER",
    "deterministic",
).strip().lower()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

OPENAI_TRANSLATION_MODEL = os.getenv("OPENAI_TRANSLATION_MODEL", "gpt-4.1-mini")
OPENAI_TTS_MODEL = os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
OPENAI_TTS_VOICE = os.getenv("OPENAI_TTS_VOICE", "coral")

AUDIO_OUTPUT_DIR = "app/static/audio"
STATIC_AUDIO_URL_PREFIX = "/static/audio"

OPENAI_TRANSCRIPTION_MODEL = os.getenv("OPENAI_TRANSCRIPTION_MODEL", "gpt-4o-transcribe")
UPLOAD_DIR = "tmp/uploads"