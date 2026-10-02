from app.security.security_context import SecurityContext
from app.sessions.session_models import ConversationSession


class SessionAccessDeniedError(PermissionError):
    pass


class SessionAccessPolicy:
    @staticmethod
    def require_access(*, context: SecurityContext, session: ConversationSession) -> None:
        # Unowned legacy sessions cannot be claimed by a request.
        if not session.owner_id or session.owner_id != context.identity.client_id:
            raise SessionAccessDeniedError("Session access denied.")
