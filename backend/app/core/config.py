"""Compatibility names backed by the single typed Settings instance."""
from pathlib import Path
from app.core.settings import get_settings

settings = get_settings()
BASE_DIR = Path.cwd()
ENV_FILE = BASE_DIR / ".env"
OPENAI_API_KEY = settings.openai_api_key.get_secret_value()
OPENAI_TRANSLATION_MODEL = settings.openai_translation_model
OPENAI_TTS_MODEL = settings.openai_tts_model
OPENAI_TTS_VOICE = settings.openai_tts_voice
TRANSLATION_PROVIDER = settings.translation_provider
SPEECH_PROVIDER = settings.speech_provider
SPEECH_TO_TEXT_PROVIDER = settings.speech_to_text_provider
CONTEXT_PROVIDER = settings.context_provider
QUALITY_PROVIDER = settings.quality_provider
SPEECH_VOICE = settings.speech_voice
REALTIME_TRANSLATION_PROVIDER = settings.realtime_translation_provider
STREAMING_TRANSCRIPTION_PROVIDER = settings.streaming_transcription_provider
STREAMING_TRANSCRIPTION_MODEL = settings.streaming_transcription_model
REALTIME_TRANSLATION_MODEL = settings.realtime_translation_model
REALTIME_TRANSLATION_VOICE = settings.realtime_translation_voice
STREAMING_TRANSLATION_PROVIDER = settings.streaming_translation_provider
STREAMING_TRANSLATION_MODEL = settings.streaming_translation_model
STREAMING_SPEECH_PROVIDER = settings.streaming_speech_provider
STREAMING_SPEECH_MODEL = settings.streaming_speech_model
STREAMING_SPEECH_VOICE = settings.streaming_speech_voice
OPENAI_TRANSCRIPTION_MODEL = settings.openai_transcription_model
SESSION_STORAGE_BACKEND = settings.session_storage_backend
SESSION_DB_PATH = settings.session_db_path
DATABASE_URL = settings.database_url
STATIC_DIR = settings.static_dir
UPLOAD_DIR = settings.upload_dir

STATIC_AUDIO_DIR = STATIC_DIR / "audio"
AUDIO_OUTPUT_DIR = STATIC_AUDIO_DIR
STATIC_AUDIO_URL_PREFIX = "/static/audio"
