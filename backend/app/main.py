from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.api.text import router as text_router
from app.api.agents import router as agents_router
from app.api.sessions import router as sessions_router
from app.api.interpreter import router as interpreter_router
from app.api.voice import router as voice_router
from app.api.realtime import router as realtime_router
from app.api.error_handlers import register_exception_handlers, realtime_translation_exception_handler
from app.observability.metrics_endpoint import (
    register_metrics_endpoint,
)
from app.core.realtime_exceptions import (
    RealtimeTranslationException,
)
from app.core.config import STATIC_DIR

app = FastAPI(
    title="Waaxalma API",
    description="Voice Agent Framework.",
    version="0.2.0",
)

register_exception_handlers(app)
register_metrics_endpoint(app)

app.include_router(text_router)
app.include_router(agents_router)
app.include_router(sessions_router)
app.include_router(interpreter_router)
app.include_router(voice_router)
app.include_router(realtime_router)

app.add_exception_handler(
    RealtimeTranslationException,
    realtime_translation_exception_handler,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR)),
    name="static",
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "waaxalma",
        "version": "0.2.0",
    }