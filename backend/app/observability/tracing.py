"""Optional OpenTelemetry; no imports or exports while disabled."""
from contextlib import contextmanager
from app.observability.context import fields

_provider = None


def start(settings):
    global _provider
    if not settings.otel_enabled:
        return
    try:
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    except ImportError as error:
        raise RuntimeError("OTEL_ENABLED requires requirements-otel.lock") from error
    _provider = TracerProvider(sampler=ParentBased(TraceIdRatioBased(settings.otel_traces_sample_ratio)), resource=Resource.create({"service.name": settings.otel_service_name, "service.version": "0.5.0"}))
    _provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_traces_endpoint, timeout=5)))


def stop():
    global _provider
    provider, _provider = _provider, None
    if provider is not None:
        provider.shutdown()


@contextmanager
def span(name, headers=None):
    if _provider is None:
        yield None
        return
    from opentelemetry.trace import Status, StatusCode
    from opentelemetry.propagate import extract
    context = extract(headers) if headers is not None else None
    with _provider.get_tracer("waaxalma").start_as_current_span(name, context=context, record_exception=False, set_status_on_exception=False) as current:
        try:
            yield current
        except BaseException:
            current.set_status(Status(StatusCode.ERROR))
            raise
        finally:
            for key, value in fields().items():
                if value is not None and type(value) in (str, int, float, bool):
                    current.set_attribute("waaxalma." + key, value)


def detached_span(name):
    if _provider is None:
        return None
    return _provider.get_tracer("waaxalma").start_span(name)


@contextmanager
def activate(current):
    if current is None:
        yield
    else:
        from opentelemetry.trace import use_span
        with use_span(current, end_on_exit=False, record_exception=False, set_status_on_exception=False):
            yield


def correlation():
    if _provider is None:
        return {}
    from opentelemetry.trace import get_current_span
    context = get_current_span().get_span_context()
    if not context.is_valid:
        return {}
    return {"otel_trace_id": format(context.trace_id, "032x"), "otel_span_id": format(context.span_id, "016x")}
