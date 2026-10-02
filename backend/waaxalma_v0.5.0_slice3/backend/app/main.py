from contextlib import asynccontextmanager
from app.core.settings import get_settings
from app.version import __version__
from app.api.health import router as health_router

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

@asynccontextmanager
async def lifespan(application):
    settings = get_settings()
    application.state.startup_complete = False
    for path in (settings.data_dir, settings.static_dir / "audio", settings.upload_dir):
        path.mkdir(parents=True, exist_ok=True)
    from app.api.health import check_local_resources
    check_local_resources()
    application.state.startup_complete = True
    try:
        yield
    finally:
        application.state.startup_complete = False


app = FastAPI(
    title="Waaxalma API",
    description="Voice Agent Framework.",
    version=__version__,
    lifespan=lifespan,
)

register_exception_handlers(app)
register_metrics_endpoint(app)

app.include_router(health_router)
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
    allow_origins=get_settings().cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR), check_dir=False),
    name="static",
)


