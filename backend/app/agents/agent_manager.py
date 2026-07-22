from app.agents.base_agent import BaseAgent
from app.agents.translation_agent import TranslationAgent
from app.agents.interpreter_agent import InterpreterAgent


class AgentManager:
    def __init__(self):
        self._agents: dict[str, BaseAgent] = {}

        self.register(TranslationAgent())
        self.register(InterpreterAgent())

    def register(self, agent: BaseAgent) -> None:
        self._agents[agent.name] = agent

    def get(self, agent_name: str) -> BaseAgent:
        agent = self._agents.get(agent_name)

        if agent is None:
            raise ValueError(f"Unknown agent: {agent_name}")

        return agent

    def list_agents(self) -> list[dict]:
        return [
            {
                "type": agent_name,
                **agent.info(),
            }
            for agent_name, agent in self._agents.items()
        ]
    
    def get_all(self) -> dict[str, BaseAgent]:
        return self._agents.copy()


agent_manager = AgentManager()