import asyncio
import json

import pytest

from app.api.enhanced_stream import MAX_PENDING_EVENTS, run_enhanced_stream
from app.core.streaming_translation_chunk import StreamingTranslationChunk
from app.core.streaming_speech_chunk import StreamingSpeechChunk
from app.security.backend import resolve_security_context
from app.core.realtime_enhanced_runtime import RealtimeEnhancedRuntime
from app.services.realtime_enhanced_processor import RealtimeEnhancedProcessor


class Socket:
    def __init__(self):
        self.incoming = asyncio.Queue()
        self.sent = []
        self.changed = asyncio.Event()
        self.closed = None
        self.fail_send = False

    async def receive(self):
        return await self.incoming.get()

    async def send_json(self, payload):
        if self.fail_send:
            raise RuntimeError("Socket closed")
        self.sent.append(payload)
        self.changed.set()

    async def close(self, code):
        self.closed = code

    async def event(self, payload):
        await self.incoming.put({"type": "websocket.receive", "text": json.dumps(payload)})

    async def until(self, predicate):
        async def wait():
            while not predicate(self.sent):
                self.changed.clear()
                await self.changed.wait()
        await asyncio.wait_for(wait(), 2)


class Service:
    def __init__(self, blocked):
        self.blocked = blocked
        self.entered = asyncio.Event()
        self.translation_closed = False
        self.speech_closed = False

    async def translate_stream(self, **kwargs):
        try:
            if self.blocked == "translation":
                self.entered.set()
                await asyncio.Event().wait()
            yield StreamingTranslationChunk(text="Hello.", is_final=True)
        finally:
            self.translation_closed = True

    async def speak_stream(self, **kwargs):
        try:
            if self.blocked == "speech":
                self.entered.set()
                await asyncio.Event().wait()
            yield StreamingSpeechChunk(audio=b"\x00\x00", is_final=True)
        finally:
            self.speech_closed = True


async def start(socket, service):
    task = asyncio.create_task(run_enhanced_stream(
        socket, service=service, security=resolve_security_context("test-client"), default_voice="demo",
    ))
    await socket.event({"type": "session.start", "target_language": "en"})
    await socket.until(lambda events: any(e["type"] == "session.ready" for e in events))
    await socket.event({"type": "transcript.delta", "delta": "bonjour"})
    await socket.event({"type": "transcript.commit"})
    return task


@pytest.mark.asyncio
@pytest.mark.parametrize("blocked", ["translation", "speech"])
@pytest.mark.parametrize("termination", ["disconnect", "cancel"])
async def test_disconnect_and_cancellation_stop_blocked_providers(blocked, termination):
    socket = Socket()
    service = Service(blocked)
    task = await start(socket, service)
    try:
        await asyncio.wait_for(service.entered.wait(), 2)
        if termination == "disconnect":
            await socket.incoming.put({"type": "websocket.disconnect", "code": 1000})
            await asyncio.wait_for(task, 2)
        else:
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(task, 2)
        assert service.translation_closed
        if blocked == "speech":
            assert service.speech_closed
        assert not any(t.get_name().startswith("waaxalma-ws-") for t in asyncio.all_tasks() if t is not asyncio.current_task())
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


@pytest.mark.asyncio
async def test_send_failure_closes_stream():
    release = asyncio.Event()
    class ReleasedService(Service):
        async def translate_stream(self, **kwargs):
            try:
                self.entered.set()
                await release.wait()
                yield StreamingTranslationChunk(text="Hello.", is_final=True)
            finally:
                self.translation_closed = True
    socket = Socket()
    service = ReleasedService(None)
    task = await start(socket, service)
    await asyncio.wait_for(service.entered.wait(), 2)
    socket.fail_send = True
    release.set()
    await asyncio.wait_for(task, 2)
    assert service.translation_closed


@pytest.mark.asyncio
async def test_provider_error_is_sanitized_and_connection_recovers():
    class FailedService(Service):
        async def translate_stream(self, **kwargs):
            raise RuntimeError("secret-key transcript private")
            yield
    socket = Socket()
    task = await start(socket, FailedService(None))
    try:
        await socket.until(lambda events: any(e.get("code") == "ENHANCED_PROCESSING_ERROR" for e in events))
        assert "secret-key" not in json.dumps(socket.sent)
        await socket.event({"type": "session.start", "target_language": "fr"})
        await socket.until(lambda events: sum(e["type"] == "session.ready" for e in events) == 2)
        await socket.incoming.put({"type": "websocket.disconnect", "code": 1000})
        await asyncio.wait_for(task, 2)
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


@pytest.mark.asyncio
async def test_excess_pending_events_close_with_policy_code():
    socket = Socket()
    service = Service("translation")
    task = await start(socket, service)
    await asyncio.wait_for(service.entered.wait(), 2)
    for _ in range(MAX_PENDING_EVENTS + 1):
        await socket.event({"type": "transcript.delta", "delta": "x"})
    await asyncio.wait_for(task, 2)
    assert socket.closed == 1008
    assert any(e.get("code") == "EVENT_QUEUE_FULL" for e in socket.sent)
    assert service.translation_closed


@pytest.mark.asyncio
async def test_early_consumer_close_stops_backpressured_producers():
    class FastService(Service):
        produced = 0
        async def translate_stream(self, **kwargs):
            try:
                for _ in range(10_000):
                    self.produced += 1
                    yield StreamingTranslationChunk(text="Hello.")
            finally:
                self.translation_closed = True
    service = FastService(None)
    processor = RealtimeEnhancedProcessor(runtime=RealtimeEnhancedRuntime(target_language="en"), service=service)
    processor.append_transcript_delta("bonjour")
    stream = processor.commit_translate_and_speak(voice_id="demo")
    await asyncio.wait_for(anext(stream), 2)
    assert service.produced < 10_000
    await asyncio.wait_for(stream.aclose(), 2)
    assert service.translation_closed
