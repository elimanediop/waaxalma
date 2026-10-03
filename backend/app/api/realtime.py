from app.api.contracts import ERROR_RESPONSES
from fastapi import HTTPException
from fastapi import Depends
from app.security.backend import resolve_security_context, check_existing_session
from app.security.security_context import SecurityContext
import base64
from typing import Any

from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
)
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


# ------------------------------------------------------------------
# Router
#
# Important:
# Provider/service composition is resolved lazily to avoid circular imports.
# ------------------------------------------------------------------

router = APIRouter(responses=ERROR_RESPONSES, 
    prefix="/api/realtime",
    tags=["realtime"],
)


# ------------------------------------------------------------------
# Lazy service references
#
# Existing tests can still monkeypatch:
#   realtime_api.realtime_translation_service
#   realtime_api.realtime_enhanced_service
# ------------------------------------------------------------------

realtime_translation_service = None
realtime_enhanced_service = None


def _get_realtime_translation_service():
    global realtime_translation_service

    if realtime_translation_service is None:
        from app.bootstrap.container import (
            realtime_translation_service as service,
        )

        realtime_translation_service = service

    return realtime_translation_service


def _get_realtime_enhanced_service():
    global realtime_enhanced_service

    if realtime_enhanced_service is None:
        from app.bootstrap.container import (
            realtime_enhanced_service as service,
        )

        realtime_enhanced_service = service

    return realtime_enhanced_service


# ------------------------------------------------------------------
# Enhanced session API contracts
# ------------------------------------------------------------------


class RealtimeEnhancedSessionRequest(BaseModel):
    target_language: str = Field(
        min_length=2,
        max_length=64,
    )

    source_languages: list[str] | None = None

    prompt: str | None = Field(
        default=None,
        max_length=4000,
    )

    keywords: list[str] | None = None

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

        normalized = (
            value
            .strip()
            .lower()
        )

        if not normalized:
            raise ValueError(
                "Target language cannot be empty."
            )

        return normalized

    @field_validator(
        "source_languages",
        mode="before",
    )
    @classmethod
    def normalize_source_languages(
        cls,
        value: list[str] | None,
    ) -> list[str] | None:
        if value is None:
            return None

        normalized = [
            language.strip().lower()
            for language in value
            if isinstance(language, str)
            and language.strip()
        ]

        return normalized or None

    @field_validator(
        "keywords",
        mode="before",
    )
    @classmethod
    def normalize_keywords(
        cls,
        value: list[str] | None,
    ) -> list[str] | None:
        if value is None:
            return None

        normalized = [
            keyword.strip()
            for keyword in value
            if isinstance(keyword, str)
            and keyword.strip()
        ]

        return normalized or None


class RealtimeEnhancedSession(BaseModel):
    mode: str = "enhanced"

    transcription_provider: str
    transcription_model: str
    target_language: str

    client_secret: str
    expires_at: int | None = None

    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


# ------------------------------------------------------------------
# Realtime Direct session API contracts
# ------------------------------------------------------------------


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

        normalized_value = (
            value
            .strip()
            .lower()
        )

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


# ------------------------------------------------------------------
# Realtime client metrics contracts
# ------------------------------------------------------------------


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


# ------------------------------------------------------------------
# Realtime Direct — v0.4.1
# ------------------------------------------------------------------


@router.post(
    "/translation/session",
    response_model=RealtimeTranslationSessionResponse,
)
async def create_translation_session(
    request: RealtimeTranslationSessionRequest,
    security: SecurityContext = Depends(resolve_security_context),
) -> RealtimeTranslationSessionResponse:
    from app.observability.context import enrich
    enrich(target_language=request.target_language)
    service = (
        _get_realtime_translation_service()
    )

    session = (
        await service.create_session(
            target_language=(
                request.target_language
            ),
        )
    )

    return RealtimeTranslationSessionResponse(
        provider=session.provider,
        model=session.model,
        target_language=(
            session.target_language
        ),
        client_secret=(
            session.client_secret
        ),
        expires_at=session.expires_at,
        voice_id=session.voice_id,
        metadata=session.metadata,
    )


# ------------------------------------------------------------------
# Realtime Enhanced session — v0.4.2
# ------------------------------------------------------------------


@router.post(
    "/enhanced/session",
    response_model=RealtimeEnhancedSession,
)
async def create_realtime_enhanced_session(
    request: RealtimeEnhancedSessionRequest,
    security: SecurityContext = Depends(resolve_security_context),
) -> RealtimeEnhancedSession:
    from app.observability.context import enrich
    enrich(target_language=request.target_language)
    service = (
        _get_realtime_enhanced_service()
    )

    session = (
        await service.create_session(
            target_language=(
                request.target_language
            ),
            source_languages=(
                request.source_languages
            ),
            prompt=request.prompt,
            keywords=request.keywords,
        )
    )

    return RealtimeEnhancedSession(
        mode=session.mode,
        transcription_provider=(
            session.transcription_provider
        ),
        transcription_model=(
            session.transcription_model
        ),
        target_language=(
            session.target_language
        ),
        client_secret=(
            session.client_secret
        ),
        expires_at=session.expires_at,
        metadata=session.metadata,
    )


# ------------------------------------------------------------------
# Realtime browser metrics
# ------------------------------------------------------------------


@router.post(
    "/metrics",
    response_model=RealtimeClientMetricsResponse,
)
async def record_realtime_client_metrics(
    request: RealtimeClientMetricsRequest,
) -> RealtimeClientMetricsResponse:
    from app.core.config import (
        REALTIME_TRANSLATION_MODEL,
        REALTIME_TRANSLATION_PROVIDER,
    )
    from app.observability.realtime_client_metrics import (
        REALTIME_CLIENT_LATENCY_SECONDS,
    )

    recorded = 0

    values = request.model_dump(
        exclude_none=True,
    )

    for field_name, value_ms in (
        values.items()
    ):
        metric_name = (
            CLIENT_METRIC_NAMES[
                field_name
            ]
        )

        (
            REALTIME_CLIENT_LATENCY_SECONDS
            .labels(
                metric=metric_name,
                provider=(
                    REALTIME_TRANSLATION_PROVIDER
                ),
                model=(
                    REALTIME_TRANSLATION_MODEL
                ),
                mode="direct",
            )
            .observe(
                value_ms / 1000.0
            )
        )

        recorded += 1

    return (
        RealtimeClientMetricsResponse(
            recorded=recorded,
        )
    )


# ------------------------------------------------------------------
# Realtime Enhanced WebSocket — v0.4.2
# ------------------------------------------------------------------


@router.websocket(
    "/enhanced/stream"
)
async def realtime_enhanced_stream(
    websocket: WebSocket,
) -> None:
    from app.core.config import STREAMING_SPEECH_VOICE
    from app.api.enhanced_stream import run_enhanced_stream
    try:
        header_id = websocket.headers.get("x-client-id")
        query_id = websocket.query_params.get("client_id")
        if header_id is not None and query_id is not None and header_id != query_id:
            raise HTTPException(401, detail={"code": "INVALID_CLIENT_ID"})
        security = resolve_security_context(header_id if header_id is not None else query_id)
    except HTTPException:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    await run_enhanced_stream(
        websocket, service=_get_realtime_enhanced_service(),
        security=security, default_voice=STREAMING_SPEECH_VOICE,
    )
