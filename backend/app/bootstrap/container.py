from app.agents.interpreter_agent import InterpreterAgent
from app.agents.translation_agent import TranslationAgent
from app.orchestration.agent_orchestrator import AgentOrchestrator
from app.registry.agent_registry import AgentRegistry


def build_agent_registry() -> AgentRegistry:
    registry = AgentRegistry()

    registry.register(
        TranslationAgent()
    )

    registry.register(
        InterpreterAgent()
    )

    return registry


def build_orchestrator(
    registry: AgentRegistry,
) -> AgentOrchestrator:
    return AgentOrchestrator(
        registry=registry,
    )


# Application-level instances.
# There must be only one registry used by the application.
agent_registry = build_agent_registry()

agent_orchestrator = build_orchestrator(
    registry=agent_registry,
)