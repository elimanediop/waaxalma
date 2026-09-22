from fastapi import APIRouter

from app.bootstrap.container import agent_manager
from app.core.agent_execution_factory import AgentExecutionFactory
from app.exceptions.error_codes import ErrorCode
from app.exceptions.pipeline_exception import PipelineException
from app.models.request_models import InterpretTextRequest
from app.models.response_models import InterpretTextResponse
from app.orchestration.agent_orchestrator import AgentOrchestrator
from app.orchestration.result_handler import require_agent_output
from app.sessions.session_manager import session_manager
from app.registry.agent_registry import AgentRegistry

router = APIRouter(
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
) -> InterpretTextResponse:
    target_language = request.target_language
    session_id = request.session_id

    if session_id:
        session = session_manager.get_session(session_id)

        if not session:
            raise PipelineException(
                code=ErrorCode.SESSION_NOT_FOUND,
                message="Session not found.",
                status_code=404,
                details={
                    "session_id": session_id,
                },
            )

        target_language = session.target_language

    execution = AgentExecutionFactory.create(
        operation="interpret",
        payload={
            "text": request.text,
            "target_language": target_language,
        },
        session_id=session_id,
        target_language=target_language,
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