"""Opt-in authenticated translation sessions, isolated from legacy client sessions."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.auth import require_enabled, require_session, require_origin
from app.identity import auth_service as auth
from app.security.user_ownership import user_owner_id
from app.bootstrap.container import agent_manager, session_manager
from app.models.request_models import CreateSessionRequest, UpdateSessionRequest
from app.api.sessions import _to_session_response
from app.sessions.session_service import SessionClosedError, SessionNotFoundError

router = APIRouter(prefix="/api/user/sessions", tags=["authenticated-sessions"])


def current_owner(request: Request) -> str:
    require_enabled()
    _, user = require_session(request)
    return user_owner_id(user["user_id"])


def csrf_owner(request: Request, owner: str = Depends(current_owner)) -> str:
    require_origin(request)
    token, _ = require_session(request)
    if not auth.csrf_valid(token, request.headers.get("x-csrf-token")):
        raise HTTPException(403, detail="Invalid CSRF token")
    return owner


def owned(session_id: str, owner: str, *, active: bool = False):
    session = session_manager.get_session(session_id)
    # Do not reveal whether another user's session exists.
    if session is None or session.owner_id != owner:
        raise HTTPException(404, detail="Session not found")
    if active and not session.is_active:
        raise HTTPException(409, detail="Session is closed")
    return session


@router.post("", status_code=201)
async def create(payload: CreateSessionRequest, owner: str = Depends(csrf_owner)):
    agent = agent_manager.get_agent(payload.agent_type)
    if agent is None:
        raise HTTPException(404, detail="Agent not found")
    session = session_manager.create_session(
        agent_name=agent.name, owner_id=owner,
        source_language=payload.source_language,
        target_language=payload.target_language,
        execution_mode=payload.execution_mode,
        metadata=payload.metadata,
    )
    return {"session_id": session.session_id, "agent_name": session.agent_name, "target_language": session.target_language}


@router.get("/{session_id}")
async def get(session_id: str, owner: str = Depends(current_owner)):
    return _to_session_response(owned(session_id, owner))


@router.patch("/{session_id}")
async def update(session_id: str, payload: UpdateSessionRequest, owner: str = Depends(csrf_owner)):
    owned(session_id, owner, active=True)
    try:
        session = session_manager.update_session(
            session_id=session_id, source_language=payload.source_language,
            target_language=payload.target_language,
            execution_mode=payload.execution_mode, metadata=payload.metadata,
        )
    except SessionNotFoundError:
        raise HTTPException(404, detail="Session not found") from None
    except SessionClosedError:
        raise HTTPException(409, detail="Session is closed") from None
    return _to_session_response(session)


@router.post("/{session_id}/close")
async def close(session_id: str, owner: str = Depends(csrf_owner)):
    owned(session_id, owner)
    try:
        session = session_manager.close_session(session_id)
    except SessionNotFoundError:
        raise HTTPException(404, detail="Session not found") from None
    return _to_session_response(session)
