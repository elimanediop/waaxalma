from app.agents.base_agent import BaseAgent


class AgentRegistry:
    """
    Registry responsible for agent registration and discovery.

    The orchestrator must not know which concrete agents exist.
    """

    def __init__(self) -> None:
        self._agents: dict[str, BaseAgent] = {}

    def register(
        self,
        agent: BaseAgent,
    ) -> None:
        if not agent.name:
            raise ValueError(
                "Agent name cannot be empty."
            )

        if agent.name in self._agents:
            raise ValueError(
                f"Agent '{agent.name}' is already registered."
            )

        self._agents[agent.name] = agent

    def find(
        self,
        name: str,
    ) -> BaseAgent | None:
        return self._agents.get(name)

    def contains(
        self,
        name: str,
    ) -> bool:
        return name in self._agents

    def names(self) -> list[str]:
        return sorted(self._agents.keys())

    def __len__(self) -> int:
        return len(self._agents)