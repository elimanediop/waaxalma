from fastapi import Depends
from app.security.backend import resolve_security_context, require_session_access
from app.security.security_context import SecurityContext
from pathlib import Path
import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from starlette import status

from app.bootstrap.container import (
    agent_manager,
    session_manager,
)
from app.core.agent_execution_factory import AgentExecutionFactory
from app.core.config import UPLOAD_DIR
from app.exceptions.error_codes import ErrorCode
from app.exceptions.pipeline_exception import PipelineException
from app.models.response_models import InterpretTextResponse
from app.orchestration.agent_orchestrator import AgentOrchestrator
from app.validation.audio_validator import (
    AudioValidator,
    ValidatedAudio,
)
from app.orchestration.result_handler import require_agent_output
from app.registry.agent_registry import AgentRegistry

router = APIRouter(prefix="/api/voice", tags=["voice"])

def build_agent_registry() -> AgentRegistry:
    registry = AgentRegistry()

    for agent in agent_manager.get_all().values():
        registry.register(agent)

    return registry


agent_registry = build_agent_registry()

agent_orchestrator = AgentOrchestrator(
    registry=agent_registry,
)


audio_validator = AudioValidator(
    upload_dir=UPLOAD_DIR,
    max_size_bytes=20 * 1024 * 1024,
    max_duration_seconds=120.0,
)


AGENT_ERROR_STATUS_CODES: dict[str, int] = {
    ErrorCode.AGENT_NOT_FOUND.value: status.HTTP_404_NOT_FOUND,
    ErrorCode.INVALID_INPUT.value: status.HTTP_400_BAD_REQUEST,
    ErrorCode.UNSUPPORTED_OPERATION.value: (
        status.HTTP_400_BAD_REQUEST
    ),
    ErrorCode.AGENT_TIMEOUT.value: status.HTTP_504_GATEWAY_TIMEOUT,
    ErrorCode.PROVIDER_TIMEOUT.value: (
        status.HTTP_504_GATEWAY_TIMEOUT
    ),
    ErrorCode.PROVIDER_UNAVAILABLE.value: (
        status.HTTP_503_SERVICE_UNAVAILABLE
    ),
}


def build_agent_exception(
    error_code: str | None,
    error_message: str | None,
) -> PipelineException:
    normalized_code = (
        error_code or ErrorCode.AGENT_EXECUTION_FAILED.value
    )

    return PipelineException(
        code=normalized_code,
        message=error_message or "Agent execution failed.",
        status_code=AGENT_ERROR_STATUS_CODES.get(
            normalized_code,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ),
    )


@router.post(
    "/interpret",
    response_model=InterpretTextResponse,
)
async def interpret_voice(
    file: UploadFile = File(...),
    target_language: str = Form("English"),
    session_id: str | None = Form(None),
    security: SecurityContext = Depends(resolve_security_context),
) -> InterpretTextResponse:
    validated_audio: ValidatedAudio | None = None
    request_id = str(uuid.uuid4())
    source_language: str | None = None
    context_metadata: dict = {}

    try:
        if session_id:
            session = require_session_access(session_manager, session_id, security, active=True)

            target_language = session.target_language
            source_language = (
                None
                if session.source_language == "auto"
                else session.source_language
            )
            context_metadata = dict(session.metadata)

        validated_audio = await audio_validator.validate_and_save(
            file=file,
            request_id=request_id,
        )

        execution = AgentExecutionFactory.create(
            operation="interpret_audio",
            payload={
                "audio_path": str(validated_audio.path),
                "target_language": target_language,
                "session_id": session_id,
                "audio_metadata": {
                    "extension": validated_audio.extension,
                    "mime_type": validated_audio.mime_type,
                    "size_bytes": validated_audio.size_bytes,
                    "duration_seconds": round(
                        validated_audio.duration_seconds,
                        3,
                    ),
                },
            },
            session_id=session_id or request_id,
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
                content=output["source_text"],
            )

            session_manager.add_message(
                session_id=session_id,
                role="assistant",
                content=output["interpreted_text"],
            )

        return InterpretTextResponse(**output)

    finally:
        await file.close()

        if validated_audio:
            validated_audio.path.unlink(missing_ok=True)