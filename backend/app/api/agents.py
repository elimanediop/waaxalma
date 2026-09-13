from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.bootstrap.container import (
    agent_orchestrator,
    agent_registry,
)
from app.core.agent_input import AgentInput
from app.core.session_context import SessionContext
from app.orchestration.result_handler import require_agent_output


router = APIRouter(
    prefix="/api/agents",
    tags=["agents"],
)


class AgentExecutionRequest(BaseModel):
    operation: str
    payload: dict[str, Any] = Field(
        default_factory=dict,
    )
    session_id: str


@router.get("")
async def list_agents():
    return {
        "agents": agent_registry.names(),
    }


@router.post("/{agent_name}/execute")
async def execute_agent(
    agent_name: str,
    request: AgentExecutionRequest,
):
    context = SessionContext(
        session_id=request.session_id,
    )

    result = await agent_orchestrator.execute(
        agent_name=agent_name,
        agent_input=AgentInput(
            operation=request.operation,
            payload=request.payload,
        ),
        context=context,
    )
    return require_agent_output(result)