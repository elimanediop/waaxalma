import builtins
from types import SimpleNamespace
import pytest
from app.observability import tracing
from app.observability.context import bound


@pytest.fixture(autouse=True)
def deterministic_sdk_sampling(monkeypatch):
    monkeypatch.setenv("OTEL_TRACES_SAMPLER", "always_on")


def test_disabled_tracing_does_not_import_sdk(monkeypatch):
    original = builtins.__import__
    def guarded(name, *args, **kwargs):
        if name.startswith('opentelemetry'):
            raise AssertionError('OpenTelemetry imported while disabled')
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', guarded)
    tracing.start(SimpleNamespace(otel_enabled=False))
    with tracing.span('disabled') as span:
        assert span is None
    tracing.stop()


def test_optional_spans_propagate_parent_without_exception_content(monkeypatch):
    pytest.importorskip('opentelemetry.sdk')
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
    provider = TracerProvider()
    exporter = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setattr(tracing, '_provider', provider)
    with bound(request_id='req-otel', session_id='session-otel'):
        with tracing.span('request', headers={'traceparent': '00-'+'1'*32+'-'+'2'*16+'-01'}):
            with pytest.raises(ValueError):
                with tracing.span('provider'):
                    raise ValueError('PRIVATE_EXCEPTION_TEXT')
    spans = exporter.get_finished_spans()
    assert len(spans) == 2
    assert spans[0].context.trace_id == int('1'*32,16)
    assert spans[0].parent.span_id == spans[1].context.span_id
    assert spans[0].attributes['waaxalma.request_id'] == 'req-otel'
    assert spans[0].events == ()
    provider.shutdown()


def test_otel_configuration_requires_endpoint():
    from app.core.settings import Settings
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Settings(app_env='test', otel_enabled=True)


def test_optional_exporter_initializes_and_shuts_down_without_export(monkeypatch):
    pytest.importorskip('opentelemetry.sdk')
    from app.core.settings import Settings
    tracing.start(Settings(app_env='test', otel_enabled=True, otel_exporter_otlp_traces_endpoint='http://127.0.0.1:4318/v1/traces'))
    assert tracing._provider is not None
    tracing.stop()
    assert tracing._provider is None


def test_optional_otlp_export_sends_metadata_without_exception_content():
    pytest.importorskip('opentelemetry.sdk')
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from threading import Thread
    from app.core.settings import Settings
    received = []
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            received.append((self.path, self.rfile.read(int(self.headers['Content-Length']))))
            self.send_response(200)
            self.end_headers()
        def log_message(self, *args):
            pass
    server = HTTPServer(('127.0.0.1',0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        tracing.start(Settings(app_env='test', otel_enabled=True, otel_exporter_otlp_traces_endpoint=f'http://127.0.0.1:{server.server_port}/v1/traces'))
        with bound(request_id='otel-export-test'):
            with pytest.raises(ValueError):
                with tracing.span('test.export'):
                    raise ValueError('PRIVATE_EXCEPTION_TEXT')
        assert tracing._provider.force_flush(timeout_millis=3000)
        assert received and received[0][0] == '/v1/traces'
        assert b'otel-export-test' in received[0][1]
        assert b'PRIVATE_EXCEPTION_TEXT' not in received[0][1]
    finally:
        tracing.stop()
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


@pytest.mark.asyncio
async def test_stream_span_does_not_leak_to_consumer(monkeypatch):
    pytest.importorskip('opentelemetry.sdk')
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
    from opentelemetry.trace import get_current_span
    from app.observability.operations import observe
    provider = TracerProvider()
    exporter = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setattr(tracing, '_provider', provider)
    @observe('translation', model='stream-test')
    async def stream():
        assert get_current_span().get_span_context().is_valid
        yield 'private content'
    with tracing.span('request') as parent:
        iterator = stream()
        assert await anext(iterator) == 'private content'
        assert get_current_span() is parent
        await iterator.aclose()
        assert get_current_span() is parent
    spans = exporter.get_finished_spans()
    assert len(spans) == 2
    assert spans[0].parent.span_id == spans[1].context.span_id
    assert spans[0].attributes['waaxalma.status'] == 'cancelled'
    provider.shutdown()
