"""Serial event processing with an independent disconnect monitor."""
import asyncio
import base64
from contextlib import aclosing
import json
import logging
import anyio

from fastapi import HTTPException, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.core.realtime_enhanced_events import (
    RealtimeEnhancedStartEvent, RealtimeEnhancedTranscriptDeltaEvent,
    RealtimeEnhancedTranscriptCommitEvent, RealtimeEnhancedResetEvent,
)
from app.core.realtime_enhanced_runtime import RealtimeEnhancedRuntime
from app.security.backend import check_existing_session
from app.services.realtime_enhanced_processor import RealtimeEnhancedProcessor

logger = logging.getLogger(__name__)
INVALID = object()
MAX_PENDING_EVENTS = 64


async def run_enhanced_stream(websocket: WebSocket, *, service, security, default_voice: str) -> None:
    pending: asyncio.Queue = asyncio.Queue(maxsize=MAX_PENDING_EVENTS)
    send_lock = asyncio.Lock()
    disconnected = False

    async def send(payload) -> bool:
        try:
            async with send_lock:
                await websocket.send_json(payload)
            return True
        except (WebSocketDisconnect, RuntimeError, OSError):
            return False

    async def error(code, message) -> bool:
        return await send({"type": "error", "code": code, "message": message})

    async def receive() -> None:
        nonlocal disconnected
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                disconnected = True
                return
            try:
                payload = json.loads(message.get("text", ""))
                if not isinstance(payload, dict):
                    payload = INVALID
            except (ValueError, TypeError):
                payload = INVALID
            try:
                pending.put_nowait(payload)
            except asyncio.QueueFull:
                await error("EVENT_QUEUE_FULL", "Too many pending events.")
                await websocket.close(code=1008)
                return

    async def process() -> None:
        processor = None
        voice = default_voice
        instructions = None
        while True:
            payload = await pending.get()
            if payload is INVALID:
                if not await error("INVALID_EVENT", "Expected a JSON event object."):
                    return
                continue
            event_type = payload.get("type")
            if event_type != "session.start" and processor is None:
                if not await error("SESSION_NOT_STARTED", "session.start must be sent first."):
                    return
                continue
            try:
                if event_type == "session.start":
                    event = RealtimeEnhancedStartEvent.model_validate(payload)
                    from app.bootstrap.container import session_manager
                    if event.session_id:
                        try:
                            check_existing_session(session_manager, event.session_id, security)
                        except HTTPException as exc:
                            await send({"type": "error", **exc.detail})
                            await websocket.close(code=1008)
                            return
                    processor = RealtimeEnhancedProcessor(
                        runtime=RealtimeEnhancedRuntime(
                            target_language=event.target_language, context=event.context,
                            terminology=event.terminology, session_id=event.session_id,
                        ), service=service,
                    )
                    voice = (event.voice_id or "").strip() or default_voice
                    instructions = (event.speech_instructions or "").strip() or None
                    from app.observability.context import enrich
                    enrich(session_id=processor.session_id, target_language=processor.target_language)
                    if not await send({"type": "session.ready", "session_id": processor.session_id,
                                       "target_language": processor.target_language, "voice_id": voice}):
                        return
                elif event_type == "transcript.delta":
                    event = RealtimeEnhancedTranscriptDeltaEvent.model_validate(payload)
                    processor.append_transcript_delta(event.delta)
                elif event_type == "transcript.commit":
                    event = RealtimeEnhancedTranscriptCommitEvent.model_validate(payload)
                    try:
                        async with aclosing(processor.commit_translate_and_speak(
                            voice_id=voice, speech_instructions=instructions, final_text=event.text,
                        )) as stream:
                            async for output in stream:
                                chunk = output.chunk
                                if output.type == "translation":
                                    body = {"type": "translation.delta", "text": chunk.text,
                                            "is_final": chunk.is_final, "metadata": chunk.metadata}
                                else:
                                    body = {"type": "audio.delta",
                                            "audio": base64.b64encode(chunk.audio).decode("ascii"),
                                            "is_final": chunk.is_final, "content_type": chunk.content_type,
                                            "sample_rate": chunk.sample_rate, "metadata": chunk.metadata}
                                if not await send(body):
                                    return
                    except Exception:
                        # Details may contain provider credentials or transcript content.
                        logger.error("Enhanced realtime processing failed")
                        processor.reset()
                        if not await error("ENHANCED_PROCESSING_ERROR", "Enhanced realtime processing failed."):
                            return
                elif event_type == "session.reset":
                    RealtimeEnhancedResetEvent.model_validate(payload)
                    processor.reset()
                else:
                    if not await error("UNKNOWN_EVENT", f"Unsupported event: {event_type}"):
                        return
            except ValidationError:
                if not await error("INVALID_EVENT", "Event validation failed."):
                    return

    reader = asyncio.create_task(receive(), name="waaxalma-ws-receive")
    worker = asyncio.create_task(process(), name="waaxalma-ws-process")
    try:
        done, _ = await asyncio.wait((reader, worker), return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            task.result()
    except WebSocketDisconnect:
        pass
    except asyncio.CancelledError:
        if not disconnected:
            raise
    finally:
        for task in (reader, worker):
            if not task.done():
                task.cancel()
        # ASGI servers may cancel the connection scope during teardown.
        # Complete child cleanup even when that scope is already cancelled.
        with anyio.CancelScope(shield=True):
            await asyncio.gather(reader, worker, return_exceptions=True)
