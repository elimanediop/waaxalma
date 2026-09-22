from fastapi.testclient import TestClient

import app.api.agents as agents_api

from app.agents.context_agent import ContextAgent
from app.agents.quality_agent import QualityAgent
from app.core.context_result import ContextResult
from app.core.quality_result import QualityResult
from app.main import app
from app.orchestration.agent_orchestrator import AgentOrchestrator
from app.registry.agent_registry import AgentRegistry
from app.skills.context_skill import ContextSkill
from app.skills.quality_skill import QualitySkill


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
            enriched_text=text,
            metadata=metadata,
        )


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
            score=None,
            issues=[],
            metadata={
                "evaluation": "fake",
            },
        )


def configure_test_agents(
    monkeypatch,
) -> None:
    registry = AgentRegistry()

    registry.register(
        ContextAgent(
            context_skill=ContextSkill(
                provider=FakeContextProvider(),
            )
        )
    )

    registry.register(
        QualityAgent(
            quality_skill=QualitySkill(
                provider=FakeQualityProvider(),
            )
        )
    )

    orchestrator = AgentOrchestrator(
        registry=registry,
    )

    monkeypatch.setattr(
        agents_api,
        "agent_registry",
        registry,
    )

    monkeypatch.setattr(
        agents_api,
        "agent_orchestrator",
        orchestrator,
    )


def test_generic_api_lists_context_and_quality_agents(
    monkeypatch,
) -> None:
    configure_test_agents(
        monkeypatch
    )

    client = TestClient(app)

    response = client.get(
        "/api/agents"
    )

    assert response.status_code == 200

    assert response.json() == {
        "agents": [
            "context",
            "quality",
        ]
    }


def test_context_agent_is_available_through_generic_api(
    monkeypatch,
) -> None:
    configure_test_agents(
        monkeypatch
    )

    client = TestClient(app)

    response = client.post(
        "/api/agents/context/execute",
        json={
            "operation": "enrich",
            "session_id": "api-context-test",
            "payload": {
                "text": "Naka nga def?",
                "metadata": {
                    "topic": "greeting",
                },
            },
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert (
        payload["original_text"]
        == "Naka nga def?"
    )

    assert (
        payload["enriched_text"]
        == "Naka nga def?"
    )

    assert payload["metadata"] == {
        "topic": "greeting",
    }


def test_quality_agent_is_available_through_generic_api(
    monkeypatch,
) -> None:
    configure_test_agents(
        monkeypatch
    )

    client = TestClient(app)

    response = client.post(
        "/api/agents/quality/execute",
        json={
            "operation": "evaluate",
            "session_id": "api-quality-test",
            "payload": {
                "source_text": "Naka nga def?",
                "interpreted_text": "How are you?",
                "target_language": "English",
            },
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["accepted"] is True
    assert payload["score"] is None
    assert payload["issues"] == []

    assert payload["metadata"] == {
        "evaluation": "fake",
    }