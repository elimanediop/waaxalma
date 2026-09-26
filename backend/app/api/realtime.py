from typing import Any

from fastapi import APIRouter
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from app.bootstrap.container import (
    realtime_translation_service,
)
from app.core.config import (
    REALTIME_TRANSLATION_MODEL,
    REALTIME_TRANSLATION_PROVIDER,
)
from app.observability.realtime_client_metrics import (
    REALTIME_CLIENT_LATENCY_SECONDS,
)


class RealtimeClientMetricsRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    session_request_ms: float | None = Field(
        default=None,
        ge=0,
        le=120_000,
    )

    webrtc_connection_ms: float | None = Field(
        default=None,
        ge=0,
        le=120_000,
    )

    speech_to_first_translation_ms: float | None = Field(
        default=None,
        ge=0,
        le=120_000,
    )

    speech_to_first_audio_ms: float | None = Field(
        default=None,
        ge=0,
        le=120_000,
    )


class RealtimeClientMetricsResponse(BaseModel):
    recorded: int


CLIENT_METRIC_NAMES = {
    "session_request_ms":
        "session_request",

    "webrtc_connection_ms":
        "webrtc_connection",

    "speech_to_first_translation_ms":
        "speech_to_first_translation",

    "speech_to_first_audio_ms":
        "speech_to_first_audio",
}


class RealtimeTranslationSessionRequest(BaseModel):
    target_language: str = Field(
        min_length=2,
        max_length=64,
    )

    @field_validator(
        "target_language",
        mode="before",
    )
    @classmethod
    def normalize_target_language(
        cls,
        value: str,
    ) -> str:
        if not isinstance(value, str):
            return value

        normalized_value = value.strip()

        if not normalized_value:
            raise ValueError(
                "Target language cannot be empty."
            )

        return normalized_value


class RealtimeTranslationSessionResponse(BaseModel):
    provider: str
    model: str
    target_language: str

    client_secret: str
    expires_at: int | None = None

    voice_id: str | None = None

    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )

router = APIRouter(
    prefix="/api/realtime",
    tags=["realtime"],
)

@router.post(
    "/translation/session",
    response_model=RealtimeTranslationSessionResponse,
)
async def create_translation_session(
    request: RealtimeTranslationSessionRequest,
) -> RealtimeTranslationSessionResponse:
    session = await realtime_translation_service.create_session(
        target_language=request.target_language,
    )

    return RealtimeTranslationSessionResponse(
        provider=session.provider,
        model=session.model,
        target_language=session.target_language,
        client_secret=session.client_secret,
        expires_at=session.expires_at,
        voice_id=session.voice_id,
        metadata=session.metadata,
    )

@router.post(
    "/metrics",
    response_model=RealtimeClientMetricsResponse,
)
async def record_realtime_client_metrics(
    request: RealtimeClientMetricsRequest,
) -> RealtimeClientMetricsResponse:

    recorded = 0

    values = request.model_dump(
        exclude_none=True,
    )

    for field_name, value_ms in values.items():

        metric_name = CLIENT_METRIC_NAMES[
            field_name
        ]

        REALTIME_CLIENT_LATENCY_SECONDS.labels(
            metric=metric_name,
            provider=REALTIME_TRANSLATION_PROVIDER,
            model=REALTIME_TRANSLATION_MODEL,
            mode="direct",
        ).observe(
            value_ms / 1000.0
        )

        recorded += 1

    return RealtimeClientMetricsResponse(
        recorded=recorded,
    )