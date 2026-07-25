from pathlib import Path
import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from starlette import status

from app.agents.agent_manager import agent_manager
from app.core.agent_execution_factory import AgentExecutionFactory
from app.core.config import UPLOAD_DIR
from app.exceptions.error_codes import ErrorCode
from app.exceptions.pipeline_exception import PipelineException
from app.models.response_models import InterpretTextResponse
from app.orchestration.agent_orchestrator import AgentOrchestrator
from app.sessions.session_manager import session_manager
from app.validation.audio_validator import (
    AudioValidator,
    ValidatedAudio,
)

router = APIRouter(prefix="/api/voice", tags=["voice"])

agent_orchestrator = AgentOrchestrator(
    agents=agent_manager.get_all(),
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
) -> InterpretTextResponse:
    validated_audio: ValidatedAudio | None = None
    request_id = str(uuid.uuid4())

    try:
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