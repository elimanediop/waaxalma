from app.agents.translation_agent import TranslationAgent
from app.agents.interpreter_agent import InterpreterAgent


class AgentManager:
    def __init__(self):
        self.agents = {
            "translation": TranslationAgent(),
            "interpreter": InterpreterAgent(),
        }

    def get(self, agent_type: str):
        agent = self.agents.get(agent_type)

        if not agent:
            raise ValueError(f"Unknown agent type: {agent_type}")

        return agent

    def list_agents(self) -> list[dict]:
        return [
            {
                "type": agent_type,
                **agent.info(),
            }
            for agent_type, agent in self.agents.items()
        ]


agent_manager = AgentManager()