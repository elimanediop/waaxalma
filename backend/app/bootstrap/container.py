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


def build_orchestrator() -> AgentOrchestrator:
    registry = build_agent_registry()

    return AgentOrchestrator(
        registry=registry,
    )