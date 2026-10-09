"""Cookie-authenticated translation API, separate from legacy X-Client-Id routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.user_sessions import csrf_owner, owned
from app.bootstrap.container import session_manager, text_translation_service
from app.core.agent_execution_factory import AgentExecutionFactory
from app.models.response_models import TranslateTextResponse
from app.observability.context import fields as observability_fields
from app.sessions.session_service import SessionClosedError, SessionNotFoundError

router = APIRouter(prefix="/api/user/translate", tags=["authenticated-translation"])


class AuthenticatedTranslateTextRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    text: str = Field(min_length=1, max_length=5000)
    source_language: str | None = Field(default=None, max_length=64)
    target_language: str = Field(min_length=2, max_length=64)


@router.post("/text", response_model=TranslateTextResponse)
async def translate_text(payload: AuthenticatedTranslateTextRequest, owner: str = Depends(csrf_owner)) -> TranslateTextResponse:
    session = owned(payload.session_id, owner, active=True)
    if session.agent_name != "translation":
        raise HTTPException(409, detail="Session is not a translation session")
    if not payload.text.strip() or not payload.target_language.strip():
        raise HTTPException(422, detail="Text and target language must not be blank")

    source = payload.source_language if payload.source_language not in ("auto", "") else None
    execution = AgentExecutionFactory.create(
        operation="translate",
        payload={"text": payload.text, "source_language": source, "target_language": payload.target_language},
        session_id=payload.session_id,
        source_language=source,
        target_language=payload.target_language,
    )
    result = await text_translation_service.translate(
        text=payload.text,
        source_language=source,
        target_language=payload.target_language,
        session_id=payload.session_id,
        context=execution.context,
    )
    # Check again after the awaited provider call. Never persist to a closed or re-owned session.
    owned(payload.session_id, owner, active=True)
    try:
        session_manager.add_message(payload.session_id, "user", result.source_text)
        session_manager.add_message(payload.session_id, "assistant", result.translated_text)
    except SessionNotFoundError:
        raise HTTPException(404, detail="Session not found") from None
    except SessionClosedError:
        raise HTTPException(409, detail="Session is closed") from None

    request_id = observability_fields().get("request_id")
    if not request_id:
        raise RuntimeError("Request ID is missing from observability context.")
    return TranslateTextResponse(
        request_id=request_id,
        agent="translation",
        original_text=result.source_text,
        translated_text=result.translated_text,
    )
