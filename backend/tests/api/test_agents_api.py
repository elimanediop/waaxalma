import pytest
from fastapi.testclient import TestClient

import app.api.agents as agents_api

from app.agents.base_agent import BaseAgent
from app.core.agent_input import AgentInput
from app.core.agent_result import AgentResult
from app.core.session_context import SessionContext
from app.main import app
from app.orchestration.agent_orchestrator import AgentOrchestrator
from app.registry.agent_registry import AgentRegistry


class EchoAgent(BaseAgent):

    @property
    def name(self) -> str:
        return "echo"

    async def execute(
        self,
        agent_input: AgentInput,
        context: SessionContext,
    ) -> AgentResult:
        return AgentResult(
            success=True,
            output={
                "agent": self.name,
                "operation": agent_input.operation,
                "message": agent_input.payload.get("text"),
                "session_id": context.session_id,
            },
        )


@pytest.fixture
def client(
    monkeypatch: pytest.MonkeyPatch,
):
    """
    Replace the application-level registry/orchestrator
    used by the generic API with isolated test instances.

    No real provider is called.
    """
    registry = AgentRegistry()
    registry.register(EchoAgent())

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

    with TestClient(app) as test_client:
        yield test_client


def test_list_agents_returns_registered_agents(
    client: TestClient,
) -> None:
    response = client.get(
        "/api/agents"
    )

    assert response.status_code == 200

    assert response.json() == {
        "agents": [
            "echo",
        ]
    }


def test_execute_registered_agent(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/agents/echo/execute",
        json={
            "operation": "echo",
            "session_id": "generic-api-test",
            "payload": {
                "text": "Hello Waaxalma",
            },
        },
    )

    assert response.status_code == 200

    assert response.json() == {
        "agent": "echo",
        "operation": "echo",
        "message": "Hello Waaxalma",
        "session_id": "generic-api-test",
    }


def test_execute_unknown_agent_returns_agent_not_found(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/agents/not-existing/execute",
        json={
            "operation": "execute",
            "session_id": "unknown-agent-test",
            "payload": {},
        },
    )

    assert response.status_code == 404

    body = response.json()

    assert body["detail"]["code"] == "AGENT_NOT_FOUND"
    assert (
        body["detail"]["message"]
        == "Unknown agent: not-existing"
    )

    metadata = (
        body["detail"]
        ["details"]
        ["metadata"]
    )

    assert metadata["agent"] == "not-existing"
    assert metadata["operation"] == "execute"
    assert metadata["session_id"] == "unknown-agent-test"

    # trace_id is generated dynamically,
    # so only verify its presence.
    assert metadata["trace_id"]