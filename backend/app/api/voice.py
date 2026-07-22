import os
import shutil
import uuid

from app.core.agent_execution_factory import AgentExecutionFactory
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.agents.agent_manager import agent_manager
from app.orchestration.agent_orchestrator import AgentOrchestrator
from app.core.agent_input import AgentInput
from app.core.config import UPLOAD_DIR
from app.core.session_context import SessionContext
from app.models.response_models import InterpretTextResponse
from app.sessions.session_manager import session_manager

router = APIRouter(prefix="/api/voice", tags=["voice"])

agent_orchestrator = AgentOrchestrator(
    agents=agent_manager.get_all(),
)

os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/interpret", response_model=InterpretTextResponse)
async def interpret_voice(
    file: UploadFile = File(...),
    target_language: str = Form("English"),
    session_id: str | None = Form(None),
) -> InterpretTextResponse:
    input_path: str | None = None

    try:
        request_id = str(uuid.uuid4())

        extension = (
            file.filename.rsplit(".", 1)[-1]
            if file.filename and "." in file.filename
            else "wav"
        )

        input_path = os.path.join(
            UPLOAD_DIR,
            f"{request_id}.{extension}",
        )

        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        if session_id:
            session = session_manager.get_session(session_id)

            if not session:
                raise HTTPException(
                    status_code=404,
                    detail="Session not found",
                )

            target_language = session.target_language

        execution = AgentExecutionFactory.create(
            operation="interpret_audio",
            payload={
                "audio_path": input_path,
                "target_language": target_language,
                "session_id": session_id,
            },
            session_id=session_id or request_id,
            target_language=target_language,
        )

        result = await agent_orchestrator.execute(
            agent_name="interpreter",
            agent_input=execution.agent_input,
            context=execution.context,
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
                role="user",
                content=output["source_text"],
            )

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

    finally:
        await file.close()

        if input_path and os.path.exists(input_path):
            os.remove(input_path)