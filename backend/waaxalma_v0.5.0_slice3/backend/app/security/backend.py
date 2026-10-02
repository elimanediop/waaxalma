"""HTTP adapter; the identity/policy modules are independent of FastAPI."""
from fastapi import Header, HTTPException
from app.sessions.session_models import ConversationSession
from app.sessions.session_service import SessionService
from app.security.client_identity import ClientIdentity, ClientIdentityError
from app.security.security_context import SecurityContext
from app.security.session_access_policy import SessionAccessPolicy, SessionAccessDeniedError


def resolve_security_context(x_client_id: str | None = Header(default=None)) -> SecurityContext:
    try:
        return SecurityContext(ClientIdentity(x_client_id))
    except ClientIdentityError as exc:
        raise HTTPException(401, detail={
            "code": "CLIENT_ID_REQUIRED" if x_client_id is None else "INVALID_CLIENT_ID",
            "message": "A valid X-Client-Id header is required.",
        }) from exc


def require_session_access(service: SessionService, session_id: str, context: SecurityContext, *, active: bool = False) -> ConversationSession:
    session = service.get_session(session_id)
    if session is None:
        raise HTTPException(404, detail={"code": "SESSION_NOT_FOUND", "message": "Session not found."})
    try:
        SessionAccessPolicy.require_access(context=context, session=session)
    except SessionAccessDeniedError as exc:
        raise HTTPException(403, detail={"code": "SESSION_ACCESS_DENIED", "message": str(exc)}) from exc
    if active and not session.is_active:
        raise HTTPException(409, detail={"code": "SESSION_CLOSED", "message": "Session is closed."})
    return session


def check_existing_session(service: SessionService, session_id: str, context: SecurityContext) -> None:
    # Generic/realtime IDs can also be ephemeral correlation IDs. If the ID
    # names a persisted conversation, apply its ownership and lifecycle policy.
    if service.get_session(session_id) is not None:
        require_session_access(service, session_id, context, active=True)
