from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.text import router as text_router
from app.api.agents import router as agents_router
from app.api.sessions import router as sessions_router
from app.api.interpreter import router as interpreter_router
from app.api.voice import router as voice_router

app = FastAPI(
    title="Waaxalma API",
    description="Voice Agent Framework.",
    version="0.2.0",
)

app.include_router(text_router)
app.include_router(agents_router)
app.include_router(sessions_router)
app.include_router(interpreter_router)
app.include_router(voice_router)

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "waaxalma",
        "version": "0.2.0",
    }