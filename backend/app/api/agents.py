from app.api.contracts import AgentListResponse
from app.api.contracts import ERROR_RESPONSES
from fastapi import Depends
from app.security.backend import resolve_security_context, check_existing_session
from app.security.security_context import SecurityContext
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


router = APIRouter(responses=ERROR_RESPONSES, 
    prefix="/api/agents",
    tags=["agents"],
)


class AgentExecutionRequest(BaseModel):
    operation: str
    payload: dict[str, Any] = Field(
        default_factory=dict,
    )
    session_id: str


@router.get("", response_model=AgentListResponse)
async def list_agents():
    return {
        "agents": agent_registry.names(),
    }


@router.post("/{agent_name}/execute", response_model=dict[str, Any])
async def execute_agent(
    agent_name: str,
    request: AgentExecutionRequest,
    security: SecurityContext = Depends(resolve_security_context),
):
    from app.bootstrap.container import session_manager
    check_existing_session(session_manager, request.session_id, security)
    payload_session_id = request.payload.get("session_id")
    if payload_session_id:
        check_existing_session(session_manager, payload_session_id, security)
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