from fastapi import APIRouter, HTTPException

from app.models.request_models import CreateSessionRequest
from app.models.response_models import CreateSessionResponse
from app.sessions.session_manager import session_manager
from app.agents.agent_manager import agent_manager

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest):
    try:
        agent = agent_manager.get(request.agent_type)

        session = session_manager.create_session(
            agent_name=agent.name,
            target_language=request.target_language,
        )

        return CreateSessionResponse(
            session_id=session.session_id,
            agent_name=session.agent_name,
            target_language=session.target_language,
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))