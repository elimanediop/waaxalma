import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]

ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)

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

SPEECH_VOICE = os.getenv(
    "SPEECH_VOICE",
    "marin",
).strip()

REALTIME_TRANSLATION_PROVIDER = os.getenv(
    "REALTIME_TRANSLATION_PROVIDER",
    "openai",
).strip().lower()

REALTIME_TRANSLATION_MODEL = os.getenv(
    "REALTIME_TRANSLATION_MODEL",
    "gpt-realtime-translate",
).strip()

REALTIME_TRANSLATION_VOICE = os.getenv(
    "REALTIME_TRANSLATION_VOICE",
    "marin",
).strip()



OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

OPENAI_TRANSLATION_MODEL = os.getenv("OPENAI_TRANSLATION_MODEL", "gpt-4.1-mini")
OPENAI_TTS_MODEL = os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
OPENAI_TTS_VOICE = os.getenv("OPENAI_TTS_VOICE", "coral")

STATIC_DIR = BASE_DIR / "static"

STATIC_AUDIO_DIR = STATIC_DIR / "audio"

AUDIO_OUTPUT_DIR = STATIC_AUDIO_DIR
STATIC_AUDIO_URL_PREFIX = "/static/audio"

OPENAI_TRANSCRIPTION_MODEL = os.getenv("OPENAI_TRANSCRIPTION_MODEL", "gpt-4o-transcribe")
UPLOAD_DIR = "tmp/uploads"

if not OPENAI_API_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY is not configured."
    )