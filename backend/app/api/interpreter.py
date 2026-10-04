from app.api.contracts import ERROR_RESPONSES
from fastapi import Depends
from app.security.backend import resolve_security_context, require_session_access
from app.security.security_context import SecurityContext
from fastapi import APIRouter

from app.bootstrap.container import (
    agent_manager,
    session_manager,
)
from app.core.agent_execution_factory import AgentExecutionFactory
from app.exceptions.error_codes import ErrorCode
from app.exceptions.pipeline_exception import PipelineException
from app.models.request_models import InterpretTextRequest
from app.models.response_models import InterpretTextResponse
from app.orchestration.agent_orchestrator import AgentOrchestrator
from app.orchestration.result_handler import require_agent_output
from app.registry.agent_registry import AgentRegistry

router = APIRouter(responses=ERROR_RESPONSES, 
    prefix="/api/interpreter",
    tags=["interpreter"],
)

def build_agent_registry() -> AgentRegistry:
    registry = AgentRegistry()

    for agent in agent_manager.get_all().values():
        registry.register(agent)

    return registry


agent_registry = build_agent_registry()

agent_orchestrator = AgentOrchestrator(
    registry=agent_registry,
)



@router.post(
    "/interpret",
    response_model=InterpretTextResponse,
)
async def interpret_text(
    request: InterpretTextRequest,
    security: SecurityContext = Depends(resolve_security_context),
) -> InterpretTextResponse:
    target_language = request.target_language
    source_language: str | None = None
    context_metadata: dict = {}
    session_id = request.session_id

    if session_id:
        session = require_session_access(session_manager, session_id, security, active=True)

        target_language = session.target_language
        source_language = (
            None
            if session.source_language == "auto"
            else session.source_language
        )
        context_metadata = dict(session.metadata)

    execution = AgentExecutionFactory.create(
        operation="interpret",
        payload={
            "text": request.text,
            "target_language": target_language,
        },
        session_id=session_id,
        source_language=source_language,
        target_language=target_language,
        context_metadata=context_metadata,
    )

    result = await agent_orchestrator.execute(
        agent_name="interpreter",
        agent_input=execution.agent_input,
        context=execution.context,
    )

    output = require_agent_output(result)

    if session_id:
        session_manager.add_message(
            session_id=session_id,
            role="user",
            content=request.text,
        )

        session_manager.add_message(
            session_id=session_id,
            role="assistant",
            content=output["interpreted_text"],
        )

    return InterpretTextResponse(**output)