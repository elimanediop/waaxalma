from app.sessions.session_models import ConversationSession


class SessionManager:
    def __init__(self):
        self.sessions: dict[str, ConversationSession] = {}

    def create_session(
        self,
        agent_name: str,
        target_language: str = "English",
    ) -> ConversationSession:
        session = ConversationSession.create(
            agent_name=agent_name,
            target_language=target_language,
        )

        self.sessions[session.session_id] = session
        return session

    def get_session(self, session_id: str) -> ConversationSession | None:
        return self.sessions.get(session_id)

    def add_message(self, session_id: str, role: str, content: str) -> None:
        session = self.get_session(session_id)

        if session:
            session.add_message(role, content)


session_manager = SessionManager()