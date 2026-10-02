from fastapi import Depends
from app.security.backend import resolve_security_context, require_session_access
from app.security.security_context import SecurityContext
from typing import NoReturn

from fastapi import APIRouter, HTTPException, status

from app.bootstrap.container import (
    agent_manager,
    session_manager,
)
from app.exceptions.error_codes import ErrorCode
from app.models.request_models import (
    CreateSessionRequest,
    UpdateSessionRequest,
)
from app.models.response_models import (
    CreateSessionResponse,
    SessionResponse,
)
from app.sessions.session_models import ConversationSession
from app.sessions.session_service import (
    SessionClosedError,
    SessionNotFoundError,
)

router = APIRouter(
    prefix="/api/sessions",
    tags=["sessions"],
)


def _to_session_response(
    session: ConversationSession,
) -> SessionResponse:
    return SessionResponse(
        owner_id=session.owner_id,
        session_id=session.session_id,
        agent_name=session.agent_name,
        execution_mode=session.execution_mode,
        source_language=session.source_language,
        target_language=session.target_language,
        status=session.status,
        created_at=session.created_at,
        updated_at=session.updated_at,
        closed_at=session.closed_at,
        metadata=session.metadata,
        history=session.history,
    )


def _raise_not_found(
    session_id: str,
) -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "code": ErrorCode.SESSION_NOT_FOUND.value,
            "message": "Session not found.",
            "details": {
                "session_id": session_id,
            },
        },
    )


def _raise_closed(
    session_id: str,
) -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": ErrorCode.SESSION_CLOSED.value,
            "message": "Session is closed.",
            "details": {
                "session_id": session_id,
            },
        },
    )


@router.post(
    "",
    response_model=CreateSessionResponse,
)
async def create_session(
    request: CreateSessionRequest,
    security: SecurityContext = Depends(resolve_security_context),
) -> CreateSessionResponse:
    agent = agent_manager.get_agent(
        request.agent_type
    )

    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": ErrorCode.AGENT_NOT_FOUND.value,
                "message": (
                    f"Agent '{request.agent_type}' was not found."
                ),
            },
        )

    session = session_manager.create_session(
        owner_id=security.identity.client_id,
        agent_name=agent.name,
        source_language=request.source_language,
        target_language=request.target_language,
        execution_mode=request.execution_mode,
        metadata=request.metadata,
    )

    return CreateSessionResponse(
        session_id=session.session_id,
        agent_name=session.agent_name,
        target_language=session.target_language,
    )


@router.get(
    "/{session_id}",
    response_model=SessionResponse,
)
async def get_session(
    session_id: str,
    security: SecurityContext = Depends(resolve_security_context),
) -> SessionResponse:
    session = require_session_access(session_manager, session_id, security)

    if session is None:
        _raise_not_found(session_id)

    return _to_session_response(session)


@router.patch(
    "/{session_id}",
    response_model=SessionResponse,
)
async def update_session(
    session_id: str,
    request: UpdateSessionRequest,
    security: SecurityContext = Depends(resolve_security_context),
) -> SessionResponse:
    require_session_access(session_manager, session_id, security, active=True)
    try:
        session = session_manager.update_session(
            session_id=session_id,
            source_language=request.source_language,
            target_language=request.target_language,
            execution_mode=request.execution_mode,
            metadata=request.metadata,
        )
    except SessionNotFoundError:
        _raise_not_found(session_id)
    except SessionClosedError:
        _raise_closed(session_id)

    return _to_session_response(session)


@router.post(
    "/{session_id}/close",
    response_model=SessionResponse,
)
async def close_session(
    session_id: str,
    security: SecurityContext = Depends(resolve_security_context),
) -> SessionResponse:
    require_session_access(session_manager, session_id, security)
    try:
        session = session_manager.close_session(
            session_id
        )
    except SessionNotFoundError:
        _raise_not_found(session_id)

    return _to_session_response(session)
