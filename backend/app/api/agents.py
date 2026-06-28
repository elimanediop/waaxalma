from fastapi import APIRouter

from app.agents.agent_manager import agent_manager

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("")
async def list_agents():
    return agent_manager.list_agents()