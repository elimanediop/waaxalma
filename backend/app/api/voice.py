import os
import shutil
import uuid

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.agents.agent_manager import agent_manager
from app.core.config import UPLOAD_DIR
from app.models.response_models import InterpretTextResponse
from app.sessions.session_manager import session_manager

router = APIRouter(prefix="/api/voice", tags=["voice"])

os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/interpret", response_model=InterpretTextResponse)
async def interpret_voice(
    file: UploadFile = File(...),
    target_language: str = Form("English"),
    session_id: str | None = Form(None),
):
    input_path = None

    try:
        request_id = str(uuid.uuid4())
        extension = file.filename.split(".")[-1] if file.filename else "wav"
        input_path = os.path.join(UPLOAD_DIR, f"{request_id}.{extension}")

        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        if session_id:
            session = session_manager.get_session(session_id)

            if not session:
                raise HTTPException(status_code=404, detail="Session not found")

            target_language = session.target_language

        agent = agent_manager.get("interpreter")

        result = agent.interpret_audio(
            audio_path=input_path,
            target_language=target_language,
            session_id=session_id,
        )

        if session_id:
            session_manager.add_message(session_id, "user", result["source_text"])
            session_manager.add_message(session_id, "assistant", result["interpreted_text"])

        return InterpretTextResponse(**result)

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if input_path and os.path.exists(input_path):
            os.remove(input_path)