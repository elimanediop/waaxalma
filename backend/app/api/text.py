from fastapi import APIRouter, Depends

from app.observability.context import fields as observability_fields

from app.api.contracts import ERROR_RESPONSES
from app.bootstrap.container import (
    agent_manager,
    session_manager,
    text_translation_service,
)
from app.core.agent_execution_factory import AgentExecutionFactory
from app.models.request_models import (
    SpeakTextRequest,
    TranslateAndSpeakRequest,
    TranslateTextRequest,
)
from app.models.response_models import (
    SpeakTextResponse,
    TranslateAndSpeakResponse,
    TranslateTextResponse,
)
from app.orchestration.agent_orchestrator import AgentOrchestrator
from app.orchestration.result_handler import require_agent_output
from app.registry.agent_registry import AgentRegistry
from app.security.backend import (
    check_existing_session,
    resolve_security_context,
)
from app.security.security_context import SecurityContext


router = APIRouter(
    responses=ERROR_RESPONSES,
    prefix="/api/text",
    tags=["text"],
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
    security: SecurityContext = Depends(
        resolve_security_context
    ),
) -> TranslateTextResponse:
    if request.session_id:
        check_existing_session(
            session_manager,
            request.session_id,
            security,
        )

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

    result = await text_translation_service.translate(
        text=request.text,
        source_language=request.source_language,
        target_language=request.target_language,
        session_id=request.session_id,
        context=execution.context,
    )

    current_observability = observability_fields()
    current_request_id = current_observability.get(
        "request_id"
    )

    if not current_request_id:
        raise RuntimeError(
            "Request ID is missing from observability context."
        )

    return TranslateTextResponse(
        request_id=current_request_id,
        agent="translation",
        original_text=result.source_text,
        translated_text=result.translated_text,
    )


@router.post(
    "/speak",
    response_model=SpeakTextResponse,
)
async def speak_text(
    request: SpeakTextRequest,
    security: SecurityContext = Depends(
        resolve_security_context
    ),
) -> SpeakTextResponse:
    if request.session_id:
        check_existing_session(
            session_manager,
            request.session_id,
            security,
        )

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
    security: SecurityContext = Depends(
        resolve_security_context
    ),
) -> TranslateAndSpeakResponse:
    if request.session_id:
        check_existing_session(
            session_manager,
            request.session_id,
            security,
        )

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