import pytest

from app.agents.quality_agent import QualityAgent
from app.core.agent_input import AgentInput
from app.core.quality_result import QualityResult
from app.core.session_context import SessionContext
from app.skills.quality_skill import QualitySkill


class FakeQualityProvider:

    @property
    def name(self) -> str:
        return "fake-quality"

    async def evaluate(
        self,
        *,
        source_text: str,
        interpreted_text: str,
        target_language: str,
    ) -> QualityResult:
        return QualityResult(
            accepted=True,
            score=0.95,
            issues=[],
            metadata={
                "target_language": target_language,
            },
        )


def create_agent() -> QualityAgent:
    return QualityAgent(
        quality_skill=QualitySkill(
            provider=FakeQualityProvider(),
        )
    )


@pytest.mark.asyncio
async def test_quality_agent_evaluates_translation() -> None:
    agent = create_agent()

    result = await agent.execute(
        agent_input=AgentInput(
            operation="evaluate",
            payload={
                "source_text": "Naka nga def?",
                "interpreted_text": "How are you?",
                "target_language": "English",
            },
        ),
        context=SessionContext(
            session_id="quality-agent-test",
        ),
    )

    assert result.success is True
    assert result.output is not None

    assert result.output["accepted"] is True
    assert result.output["score"] == 0.95
    assert result.output["issues"] == []

    assert result.output["metadata"] == {
        "target_language": "English",
    }


@pytest.mark.asyncio
async def test_quality_agent_rejects_missing_interpreted_text() -> None:
    agent = create_agent()

    result = await agent.execute(
        agent_input=AgentInput(
            operation="evaluate",
            payload={
                "source_text": "Naka nga def?",
                "target_language": "English",
            },
        ),
        context=SessionContext(
            session_id="quality-invalid-test",
        ),
    )

    assert result.success is False
    assert result.output is None
    assert result.error_code == "INVALID_INPUT"


@pytest.mark.asyncio
async def test_quality_agent_rejects_unknown_operation() -> None:
    agent = create_agent()

    result = await agent.execute(
        agent_input=AgentInput(
            operation="unknown",
            payload={},
        ),
        context=SessionContext(
            session_id="quality-operation-test",
        ),
    )

    assert result.success is False
    assert result.error_code == (
        "UNSUPPORTED_OPERATION"
    )