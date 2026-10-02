"""Typed settings; no configuration side effects or provider calls."""
from functools import lru_cache
import os
from pathlib import Path
from typing import Literal
from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=False, extra="ignore", hide_input_in_errors=True,
        env_file_encoding="utf-8", validate_default=True, allow_inf_nan=False,
    )
    app_env: Literal["development", "test", "production"] = "development"
    openai_api_key: SecretStr | None = None
    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1, le=65535)
    log_level: Literal["debug", "info", "warning", "error", "critical"] = "info"
    cors_origins: list[str] = Field(default_factory=lambda: [
        "http://localhost:8501", "http://127.0.0.1:8501",
        "http://localhost:5500", "http://127.0.0.1:5500",
    ])
    data_dir: Path = Path("data")
    static_dir: Path = Path("static")
    upload_dir: Path = Path("tmp/uploads")
    session_storage_backend: Literal["sqlite", "memory"] | None = None
    session_db_path: Path | None = None
    translation_provider: Literal["openai"] = "openai"
    speech_provider: Literal["openai"] = "openai"
    speech_to_text_provider: Literal["openai"] = "openai"
    context_provider: Literal["passthrough"] = "passthrough"
    quality_provider: Literal["deterministic"] = "deterministic"
    realtime_translation_provider: Literal["openai"] = "openai"
    streaming_transcription_provider: Literal["openai"] = "openai"
    streaming_translation_provider: Literal["openai"] = "openai"
    streaming_speech_provider: Literal["openai"] = "openai"
    openai_translation_model: str = "gpt-4.1-mini"
    openai_tts_model: str = "gpt-4o-mini-tts"
    openai_tts_voice: str = "coral"
    speech_voice: str = "marin"
    openai_transcription_model: str = "gpt-4o-transcribe"
    realtime_translation_model: str = "gpt-realtime-translate"
    realtime_translation_voice: str = "marin"
    streaming_transcription_model: str = "gpt-live-transcribe"
    streaming_translation_model: str | None = None
    streaming_speech_model: str | None = None
    streaming_speech_voice: str | None = None
    provider_max_attempts: int = Field(default=3, ge=1, le=10)
    provider_initial_backoff_seconds: float = Field(default=0.5, ge=0)
    provider_backoff_multiplier: float = Field(default=2.0, ge=1)
    provider_max_backoff_seconds: float = Field(default=4.0, ge=0)
    provider_jitter_ratio: float = Field(default=0.2, ge=0, le=1)
    stt_timeout_seconds: float = Field(default=30.0, gt=0)
    translation_timeout_seconds: float = Field(default=20.0, gt=0)
    tts_timeout_seconds: float = Field(default=30.0, gt=0)

    @field_validator("openai_api_key")
    @classmethod
    def nonempty_key(cls, value):
        if value is not None and not value.get_secret_value().strip():
            raise ValueError("OPENAI_API_KEY must not be blank")
        return value

    @field_validator("cors_origins")
    @classmethod
    def valid_origins(cls, value):
        from urllib.parse import urlsplit
        for origin in value:
            url = urlsplit(origin)
            if url.scheme not in {"http", "https"} or not url.netloc or url.path or url.query or url.fragment or url.username:
                raise ValueError("CORS_ORIGINS must contain explicit HTTP(S) origins")
        return value

    @model_validator(mode="after")
    def environment_defaults(self):
        if self.provider_max_backoff_seconds < self.provider_initial_backoff_seconds:
            raise ValueError("PROVIDER_MAX_BACKOFF_SECONDS must be >= PROVIDER_INITIAL_BACKOFF_SECONDS")
        if self.openai_api_key is None:
            if self.app_env != "test":
                raise ValueError("OPENAI_API_KEY is required outside the test environment")
            self.openai_api_key = SecretStr("test-key-not-for-provider-calls")
        if self.session_storage_backend is None:
            self.session_storage_backend = "memory" if self.app_env == "test" else "sqlite"
        if self.app_env == "production" and self.session_storage_backend != "sqlite":
            raise ValueError("Production requires persistent SESSION_STORAGE_BACKEND=sqlite")
        for name in ("data_dir", "static_dir", "upload_dir"):
            setattr(self, name, getattr(self, name).expanduser().resolve())
        self.session_db_path = (
            self.session_db_path.expanduser().resolve() if self.session_db_path is not None
            else self.data_dir / "waaxalma_sessions.sqlite3"
        )
        self.streaming_translation_model = self.streaming_translation_model or self.openai_translation_model
        self.streaming_speech_model = self.streaming_speech_model or self.openai_tts_model
        self.streaming_speech_voice = self.streaming_speech_voice or self.openai_tts_voice
        for name in self.__class__.model_fields:
            value = getattr(self, name)
            if name.endswith(("_model", "_voice")) and (not value or not value.strip()):
                raise ValueError(f"{name.upper()} must not be blank")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    # Production and tests never auto-load a local .env. The process environment
    # explicitly chooses the mode before dotenv parsing; development uses cwd.
    mode = os.getenv("APP_ENV", "development")
    return Settings(_env_file=Path.cwd()/".env" if mode == "development" else None)
