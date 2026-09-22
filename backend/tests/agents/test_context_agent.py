import pytest

from app.agents.context_agent import ContextAgent
from app.core.agent_input import AgentInput
from app.core.context_result import ContextResult
from app.core.session_context import SessionContext
from app.skills.context_skill import ContextSkill


class FakeContextProvider:

    @property
    def name(self) -> str:
        return "fake-context"

    async def enrich(
        self,
        *,
        text: str,
        metadata: dict,
    ) -> ContextResult:
        return ContextResult(
            original_text=text,
            enriched_text=f"[context] {text}",
            metadata=metadata,
        )


def create_agent() -> ContextAgent:
    return ContextAgent(
        context_skill=ContextSkill(
            provider=FakeContextProvider(),
        )
    )


@pytest.mark.asyncio
async def test_context_agent_enriches_text() -> None:
    agent = create_agent()

    result = await agent.execute(
        agent_input=AgentInput(
            operation="enrich",
            payload={
                "text": "Naka nga def?",
                "metadata": {
                    "topic": "greeting",
                },
            },
        ),
        context=SessionContext(
            session_id="context-agent-test",
        ),
    )

    assert result.success is True
    assert result.output is not None

    assert result.output["original_text"] == (
        "Naka nga def?"
    )

    assert result.output["enriched_text"] == (
        "[context] Naka nga def?"
    )

    assert result.output["metadata"] == {
        "topic": "greeting",
    }


@pytest.mark.asyncio
async def test_context_agent_rejects_missing_text() -> None:
    agent = create_agent()

    result = await agent.execute(
        agent_input=AgentInput(
            operation="enrich",
            payload={},
        ),
        context=SessionContext(
            session_id="context-invalid-test",
        ),
    )

    assert result.success is False
    assert result.output is None
    assert result.error_code == "INVALID_INPUT"


@pytest.mark.asyncio
async def test_context_agent_rejects_unknown_operation() -> None:
    agent = create_agent()

    result = await agent.execute(
        agent_input=AgentInput(
            operation="unknown",
            payload={
                "text": "hello",
            },
        ),
        context=SessionContext(
            session_id="context-operation-test",
        ),
    )

    assert result.success is False
    assert result.error_code == (
        "UNSUPPORTED_OPERATION"
    )