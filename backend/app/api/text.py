import uuid

from app.core.agent_execution_factory import AgentExecutionFactory
from fastapi import APIRouter, HTTPException

from app.agents.agent_manager import agent_manager
from app.orchestration.agent_orchestrator import AgentOrchestrator
from app.agents.translation_agent import TranslationAgent
from app.core.agent_input import AgentInput
from app.core.logging import logger
from app.core.session_context import SessionContext
from app.models.request_models import TranslateTextRequest, SpeakTextRequest
from app.models.response_models import (
    TranslateTextResponse,
    SpeakTextResponse,
    TranslateAndSpeakResponse,
)

router = APIRouter(prefix="/api/text", tags=["text"])

# Existing instance kept temporarily for the routes not yet migrated.
translation_agent = TranslationAgent()

# New orchestration entry point.
agent_orchestrator = AgentOrchestrator(
    agents=agent_manager.get_all(),
)


@router.post("/translate", response_model=TranslateTextResponse)
async def translate_text(
    request: TranslateTextRequest,
) -> TranslateTextResponse:
    logger.info("translate_text started")

    session_id = str(uuid.uuid4())

    execution = AgentExecutionFactory.create(
            operation="translate",
            payload={
                "text": request.text,
                "target_language": request.target_language,
            },
            session_id=request.session_id,
            target_language=request.target_language,
    )

    result = await agent_orchestrator.execute(
        agent_name="translation",
        agent_input=execution.agent_input,
        context=execution.context,
    )

    if not result.success:
        logger.error(
            "translate_text failed: code=%s message=%s",
            result.error_code,
            result.error_message,
        )

        status_code = (
            404
            if result.error_code == "AGENT_NOT_FOUND"
            else 400
            if result.error_code
            in {
                "INVALID_INPUT",
                "UNSUPPORTED_OPERATION",
            }
            else 500
        )

        raise HTTPException(
            status_code=status_code,
            detail={
                "code": result.error_code,
                "message": result.error_message,
            },
        )

    logger.info(
        "translate_text completed: session_id=%s duration_ms=%.2f",
        session_id,
        result.duration_ms or 0,
    )

    return TranslateTextResponse(**result.output)


@router.post("/speak", response_model=SpeakTextResponse)
async def speak_text(request: SpeakTextRequest):
    try:
        logger.info("speak_text started")

        result = await agent_orchestrator.execute(
            agent_name="translation",
            agent_input=AgentInput(
                operation="speak",
                payload={
                    "text": request.text,
                },
            ),
            context=SessionContext(
                session_id=str(uuid.uuid4()),
                target_language="English",  # Default target language
            ),
        )

        return SpeakTextResponse(**result)

    except Exception as e:
        logger.exception("speak_text failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/translate-and-speak",
    response_model=TranslateAndSpeakResponse,
)
async def translate_and_speak(request: TranslateTextRequest):
    try:
        logger.info("translate_and_speak started")

        result = await agent_orchestrator.execute(
            agent_name="translation",
            agent_input=AgentInput(
                operation="translate_and_speak",
                payload={
                    "text": request.text,
                    "target_language": request.target_language,
                },
            ),
            context=SessionContext(
                session_id=str(uuid.uuid4()),
                target_language=request.target_language,
            ),
        )

        return TranslateAndSpeakResponse(**result)

    except Exception as e:
        logger.exception("translate_and_speak failed")
        raise HTTPException(status_code=500, detail=str(e))