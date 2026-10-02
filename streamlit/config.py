import os
import re
from urllib.parse import urlsplit
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class UISettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", hide_input_in_errors=True, allow_inf_nan=False)
    backend_api_url: str = "http://127.0.0.1:8000"
    public_backend_url: str = "http://127.0.0.1:8000"
    client_id: str = "waaxalma-for-elimane"
    request_timeout_seconds: float = 120

    @field_validator("backend_api_url", "public_backend_url")
    @classmethod
    def valid_url(cls, value):
        parsed = urlsplit(value)
        if any(c in value for c in "\r\n<>\"'"):
            raise ValueError("Backend URL contains invalid characters")
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.query or parsed.fragment or parsed.username or parsed.password:
            raise ValueError("Expected an HTTP(S) backend URL without credentials/query/fragment")
        return value.rstrip("/")

    @field_validator("client_id")
    @classmethod
    def valid_client(cls, value):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", value):
            raise ValueError("Invalid CLIENT_ID")
        return value

    @field_validator("request_timeout_seconds")
    @classmethod
    def valid_timeout(cls, value):
        if value <= 0:
            raise ValueError("REQUEST_TIMEOUT_SECONDS must be positive")
        return value


settings = UISettings(_env_file=".env" if os.getenv("APP_ENV", "development") == "development" else None)
API_URL = settings.backend_api_url
PUBLIC_API_URL = settings.public_backend_url
CLIENT_ID = settings.client_id
REQUEST_TIMEOUT_SECONDS = settings.request_timeout_seconds
