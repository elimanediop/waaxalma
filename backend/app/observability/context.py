"""Task-local observability context. No bodies, headers or secrets are retained."""
from contextlib import contextmanager
from contextvars import ContextVar
import re
from uuid import uuid4

CONTEXT = ContextVar("waaxalma_observability", default=None)
FIELDS = {"request_id", "session_id", "execution_mode", "provider", "model", "source_language", "target_language", "latency_ms", "status", "error_type", "operation", "agent", "stage", "route", "method", "status_code", "trace_id", "span_id", "otel_trace_id", "otel_span_id", "input_tokens", "output_tokens", "estimated_cost_usd", "session_duration_seconds"}


def request_id(value=None):
    if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", value, flags=re.ASCII):
        return value
    return str(uuid4())


def fields():
    return dict(CONTEXT.get() or {})


def enrich(**values):
    context = CONTEXT.get()
    if context is not None:
        context.update({k: v for k, v in values.items() if k in FIELDS})


@contextmanager
def bound(**values):
    token = CONTEXT.set({**fields(), **{k: v for k, v in values.items() if k in FIELDS}})
    try:
        yield
    finally:
        CONTEXT.reset(token)
