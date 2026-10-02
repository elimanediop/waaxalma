from app.sessions.in_memory_session_repository import (
    InMemorySessionRepository,
)
from app.sessions.session_repository import SessionRepository
from app.sessions.session_service import SessionService


class SessionManager(SessionService):
    """Backward-compatible name for the persistent SessionService.

    Direct construction without a repository keeps the historical in-memory
    behavior. The application composition root injects SQLite by default.
    """

    def __init__(
        self,
        repository: SessionRepository | None = None,
    ) -> None:
        super().__init__(
            repository=(
                repository
                if repository is not None
                else InMemorySessionRepository()
            )
        )
