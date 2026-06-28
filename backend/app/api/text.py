from fastapi import APIRouter, HTTPException

from app.core.logging import logger
from app.models.request_models import TranslateTextRequest, SpeakTextRequest
from app.models.response_models import (
    TranslateTextResponse,
    SpeakTextResponse,
    TranslateAndSpeakResponse,
)
from app.agents.translation_agent import TranslationAgent

router = APIRouter(prefix="/api/text", tags=["text"])

translation_agent = TranslationAgent()


@router.post("/translate", response_model=TranslateTextResponse)
async def translate_text(request: TranslateTextRequest):
    try:
        logger.info("translate_text started")

        result = translation_agent.translate_text(
            text=request.text,
            target_language=request.target_language,
        )

        return TranslateTextResponse(**result)

    except Exception as e:
        logger.exception("translate_text failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/speak", response_model=SpeakTextResponse)
async def speak_text(request: SpeakTextRequest):
    try:
        logger.info("speak_text started")

        result = translation_agent.speak_text(
            text=request.text,
        )

        return SpeakTextResponse(**result)

    except Exception as e:
        logger.exception("speak_text failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/translate-and-speak", response_model=TranslateAndSpeakResponse)
async def translate_and_speak(request: TranslateTextRequest):
    try:
        logger.info("translate_and_speak started")

        result = translation_agent.translate_and_speak(
            text=request.text,
            target_language=request.target_language,
        )

        return TranslateAndSpeakResponse(**result)

    except Exception as e:
        logger.exception("translate_and_speak failed")
        raise HTTPException(status_code=500, detail=str(e))