from abc import ABC, abstractmethod

from app.core.agent_input import AgentInput
from app.core.agent_result import AgentResult
from app.core.session_context import SessionContext


class BaseAgent(ABC):
    """Base contract implemented by every Waaxalma agent."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the unique name used by the agent registry."""
        raise NotImplementedError

    @abstractmethod
    async def execute(
        self,
        agent_input: AgentInput,
        context: SessionContext,
    ) -> AgentResult:
        """Execute the agent using a common input and session context."""
        raise NotImplementedError
    
    def info(self) -> dict:
        return {
        "name": self.name,
        "description": getattr(self, "description", ""),
    }