from fastapi import APIRouter, HTTPException

from app.agents.agent_manager import agent_manager
from app.models.request_models import InterpretTextRequest
from app.models.response_models import InterpretTextResponse
from app.sessions.session_manager import session_manager

router = APIRouter(prefix="/api/interpreter", tags=["interpreter"])


@router.post("/interpret", response_model=InterpretTextResponse)
async def interpret_text(request: InterpretTextRequest):
    try:
        session_id = request.session_id
        target_language = request.target_language

        if session_id:
            session = session_manager.get_session(session_id)

            if not session:
                raise HTTPException(status_code=404, detail="Session not found")

            target_language = session.target_language
            session.add_message("user", request.text)

        agent = agent_manager.get("interpreter")

        result = agent.interpret(
            text=request.text,
            target_language=target_language,
            session_id=session_id,
        )

        if session_id:
            session_manager.add_message(
                session_id=session_id,
                role="assistant",
                content=result["interpreted_text"],
            )

        return InterpretTextResponse(**result)

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))