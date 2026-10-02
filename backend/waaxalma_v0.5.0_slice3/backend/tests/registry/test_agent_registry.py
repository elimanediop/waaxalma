import pytest

from app.registry.agent_registry import AgentRegistry
from app.core.agent_result import AgentResult
from app.core.agent_input import AgentInput
from app.core.session_context import SessionContext
from app.agents.base_agent import BaseAgent
from app.orchestration.agent_orchestrator import AgentOrchestrator


class FakeAgent(BaseAgent):

    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    async def execute(
        self,
        agent_input: AgentInput,
        context: SessionContext,
    ) -> AgentResult:
        return AgentResult(
            success=True,
            output={
                "message": "echo",
            },
        )


def test_register_and_find_agent() -> None:
    registry = AgentRegistry()

    agent = FakeAgent(
        name="echo",
    )

    registry.register(agent)

    assert registry.find("echo") is agent
    assert registry.contains("echo") is True
    assert len(registry) == 1


def test_unknown_agent_returns_none() -> None:
    registry = AgentRegistry()

    assert registry.find("unknown") is None
    assert registry.contains("unknown") is False


def test_duplicate_agent_registration_is_rejected() -> None:
    registry = AgentRegistry()

    registry.register(
        FakeAgent(name="echo")
    )

    with pytest.raises(
        ValueError,
        match="already registered",
    ):
        registry.register(
            FakeAgent(name="echo")
        )


def test_registry_returns_sorted_agent_names() -> None:
    registry = AgentRegistry()

    registry.register(
        FakeAgent(name="translation")
    )

    registry.register(
        FakeAgent(name="interpreter")
    )

    registry.register(
        FakeAgent(name="quality")
    )

    assert registry.names() == [
        "interpreter",
        "quality",
        "translation",
    ]


@pytest.mark.asyncio
async def test_unknown_agent_is_normalized_by_orchestrator() -> None:
    registry = AgentRegistry()

    orchestrator = AgentOrchestrator(
        registry=registry,
    )

    context = SessionContext(
        session_id="unknown-agent-test",
    )

    result = await orchestrator.execute(
        agent_name="does-not-exist",
        agent_input=AgentInput(
            operation="execute",
            payload={},
        ),
        context=context,
    )

    assert result.success is False
    assert result.output is None
    assert result.error_code == "AGENT_NOT_FOUND"

    assert result.metadata["agent"] == "does-not-exist"
    assert (
        result.metadata["session_id"]
        == "unknown-agent-test"
    )