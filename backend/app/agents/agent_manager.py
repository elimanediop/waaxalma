from app.agents.base_agent import BaseAgent
from app.registry.agent_registry import AgentRegistry


class AgentManager:
    """
    Read-only facade over the AgentRegistry.

    Agent construction and registration belong to the
    application composition root.
    """

    def __init__(
        self,
        registry: AgentRegistry,
    ) -> None:
        self._registry = registry

    def get_agent(
        self,
        name: str,
    ) -> BaseAgent | None:
        return self._registry.find(name)

    def get_all(
        self,
    ) -> dict[str, BaseAgent]:
        return {
            name: agent
            for name in self._registry.names()
            if (agent := self._registry.find(name)) is not None
        }

    def list_agents(self) -> list[dict]:
        agents = []

        for name in self._registry.names():
            agent = self._registry.find(name)

            if agent is None:
                continue

            agents.append(
                {
                    "name": agent.name,
                    "description": getattr(
                        agent,
                        "description",
                        "",
                    ),
                }
            )

        return agents