from fastapi import APIRouter, HTTPException

from app.agents.agent_manager import agent_manager
from app.orchestration.agent_orchestrator import AgentOrchestrator
from app.core.agent_input import AgentInput
from app.core.session_context import SessionContext
from app.models.request_models import InterpretTextRequest
from app.models.response_models import InterpretTextResponse
from app.sessions.session_manager import session_manager

router = APIRouter(prefix="/api/interpreter", tags=["interpreter"])

agent_orchestrator = AgentOrchestrator(
    agents=agent_manager.get_all(),
)


@router.post("/interpret", response_model=InterpretTextResponse)
async def interpret_text(
    request: InterpretTextRequest,
) -> InterpretTextResponse:
    try:
        session_id = request.session_id
        target_language = request.target_language

        if session_id:
            session = session_manager.get_session(session_id)

            if not session:
                raise HTTPException(
                    status_code=404,
                    detail="Session not found",
                )

            target_language = session.target_language

            session_manager.add_message(
                session_id=session_id,
                role="user",
                content=request.text,
            )

        context = SessionContext(
            session_id=session_id,
            target_language=target_language,
        )

        agent_input = AgentInput(
            operation="interpret",
            payload={
                "text": request.text,
                "target_language": target_language,
            },
        )

        result = await agent_orchestrator.execute(
            agent_name="interpreter",
            agent_input=agent_input,
            context=context,
        )

        if not result.success:
            status_code = 500

            if result.error_code == "AGENT_NOT_FOUND":
                status_code = 404
            elif result.error_code in {
                "INVALID_INPUT",
                "UNSUPPORTED_OPERATION",
            }:
                status_code = 400
            elif result.error_code == "AGENT_TIMEOUT":
                status_code = 504

            raise HTTPException(
                status_code=status_code,
                detail={
                    "code": result.error_code,
                    "message": result.error_message,
                },
            )

        output = result.output

        if session_id:
            session_manager.add_message(
                session_id=session_id,
                role="assistant",
                content=output["interpreted_text"],
            )

        return InterpretTextResponse(**output)

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc