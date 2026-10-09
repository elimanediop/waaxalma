"""Authenticated WebSocket endpoint, separate from legacy client-id WebSocket."""
from __future__ import annotations
import os
import asyncio
from contextlib import suppress

from fastapi import APIRouter, WebSocket

from app.identity import auth_service as auth
from app.security.client_identity import ClientIdentity
from app.security.security_context import SecurityContext
from app.security.user_ownership import user_owner_id

router = APIRouter(tags=["authenticated-realtime"])

# Bounded detection of logout/revocation for already-established sockets.
REVOCATION_CHECK_SECONDS = 2.0


def session_still_valid(token: str, user_id: str) -> bool:
    """Fail closed when a token is revoked, expired, or reassigned."""
    try:
        current = auth.resolve_user(token)
    except Exception:
        return False
    return current is not None and current["user_id"] == user_id


async def close_when_revoked(websocket: WebSocket, token: str, user_id: str) -> None:
    """Poll session validity independently of incoming client events."""
    while True:
        await asyncio.sleep(REVOCATION_CHECK_SECONDS)
        if not await asyncio.to_thread(session_still_valid, token, user_id):
            with suppress(RuntimeError, OSError):
                await websocket.close(code=1008, reason="Authentication expired")
            return


@router.websocket("/api/user/realtime/enhanced/stream")
async def user_realtime(websocket: WebSocket):
    if os.getenv("WAAXALMA_AUTH_ENABLED", "false").lower() != "true":
        await websocket.close(code=1008)
        return
    origin = websocket.headers.get("origin")
    allowed = os.getenv("WAAXALMA_AUTH_ALLOWED_ORIGINS", "http://localhost:3000")
    if not auth.allowed_origin(origin, allowed):
        await websocket.close(code=1008)
        return
    token = websocket.cookies.get(auth.COOKIE_NAME)
    user = auth.resolve_user(token)
    if user is None:
        await websocket.close(code=1008)
        return
    # A legacy client cannot express 'user:<uuid>' in X-Client-Id.
    # Construct a context solely from the authenticated cookie.
    from app.api.enhanced_stream import run_enhanced_stream
    from app.api.realtime import _get_realtime_enhanced_service
    from app.core.config import STREAMING_SPEECH_VOICE
    from app.security.security_context import SecurityContext
    from app.security.client_identity import ClientIdentity
    # This authenticated-only context uses a distinct owner representation.
    from dataclasses import dataclass
    @dataclass(frozen=True)
    class _AuthenticatedIdentity:
        client_id: str
    security = SecurityContext(identity=_AuthenticatedIdentity(user_owner_id(user["user_id"])))
    await websocket.accept()
    stream = asyncio.create_task(
        run_enhanced_stream(
            websocket, service=_get_realtime_enhanced_service(),
            security=security, default_voice=STREAMING_SPEECH_VOICE,
        ), name="waaxalma-authenticated-stream",
    )
    monitor = asyncio.create_task(
        close_when_revoked(websocket, token, user["user_id"]),
        name="waaxalma-auth-session-monitor",
    )
    try:
        done, _ = await asyncio.wait((stream, monitor), return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            await task
    finally:
        for task in (stream, monitor):
            if not task.done():
                task.cancel()
        await asyncio.gather(stream, monitor, return_exceptions=True)
