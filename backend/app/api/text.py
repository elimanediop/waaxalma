import uuid

from app.core.agent_execution_factory import AgentExecutionFactory
from fastapi import APIRouter, HTTPException

from app.bootstrap.container import agent_manager
from app.registry.agent_registry import AgentRegistry
from app.orchestration.agent_orchestrator import AgentOrchestrator
from app.agents.translation_agent import TranslationAgent
from app.core.agent_input import AgentInput
from app.core.logging import logger
from app.core.session_context import SessionContext
from app.models.request_models import TranslateTextRequest, SpeakTextRequest, TranslateAndSpeakRequest
from app.models.response_models import (
    TranslateTextResponse,
    SpeakTextResponse,
    TranslateAndSpeakResponse,
)
from app.skills import speech_skill, translation_skill
from app.orchestration.result_handler import require_agent_output

router = APIRouter(prefix="/api/text", tags=["text"])

# Existing instance kept temporarily for the routes not yet migrated.
TranslationAgent(
    translation_skill=translation_skill,
    speech_skill=speech_skill,
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
    "/translate",
    response_model=TranslateTextResponse,
)
async def translate_text(
    request: TranslateTextRequest,
) -> TranslateTextResponse:
    execution = AgentExecutionFactory.create(
        operation="translate",
        payload={
            "text": request.text,
            "source_language": request.source_language,
            "target_language": request.target_language,
        },
        session_id=request.session_id,
        source_language=request.source_language,
        target_language=request.target_language,
    )

    result = await agent_orchestrator.execute(
        agent_name="translation",
        agent_input=execution.agent_input,
        context=execution.context,
    )

    output = require_agent_output(result)

    return TranslateTextResponse(**output)


@router.post(
    "/speak",
    response_model=SpeakTextResponse,
)
async def speak_text(
    request: SpeakTextRequest,
) -> SpeakTextResponse:
    execution = AgentExecutionFactory.create(
        operation="speak",
        payload={
            "text": request.text,
            "language": request.language,
        },
        session_id=request.session_id,
        target_language=request.language,
    )

    result = await agent_orchestrator.execute(
        agent_name="translation",
        agent_input=execution.agent_input,
        context=execution.context,
    )

    output = require_agent_output(result)

    return SpeakTextResponse(**output)


@router.post(
    "/translate-and-speak",
    response_model=TranslateAndSpeakResponse,
)
async def translate_and_speak(
    request: TranslateAndSpeakRequest,
) -> TranslateAndSpeakResponse:
    execution = AgentExecutionFactory.create(
        operation="translate_and_speak",
        payload={
            "text": request.text,
            "source_language": request.source_language,
            "target_language": request.target_language,
        },
        session_id=request.session_id,
        source_language=request.source_language,
        target_language=request.target_language,
    )

    result = await agent_orchestrator.execute(
        agent_name="translation",
        agent_input=execution.agent_input,
        context=execution.context,
    )

    output = require_agent_output(result)

    return TranslateAndSpeakResponse(**output)