"""Provider instrumentation without observing input/output content."""
import asyncio
from contextlib import contextmanager
from functools import wraps
import inspect
import time
from app.observability.context import bound, fields, enrich
from app.observability.events import emit
from app.observability.production_metrics import PROVIDER_CALLS, PROVIDER_ERRORS, PROVIDER_LATENCY, TOKENS, COST
from app.observability.tracing import span, detached_span, activate

ERRORS = {"PROVIDER_TIMEOUT", "PROVIDER_UNAVAILABLE", "PROVIDER_RATE_LIMITED", "PROVIDER_AUTHENTICATION_FAILED", "PROVIDER_REQUEST_FAILED"}


@contextmanager
def operation(name, provider="openai", model=None):
    started = time.perf_counter()
    status, error_type = "success", None
    with bound(operation=name, provider=provider, model=model):
        with span("waaxalma.provider." + name):
            try:
                yield
            except (asyncio.CancelledError, GeneratorExit):
                status, error_type = "cancelled", "cancelled"
                raise
            except Exception as error:
                status = "error"
                code = getattr(error, "code", None)
                error_type = code if isinstance(code, str) and code in ERRORS else "provider_error"
                raise
            finally:
                elapsed = time.perf_counter() - started
                PROVIDER_CALLS.labels(provider, name, status).inc()
                PROVIDER_LATENCY.labels(provider, name).observe(elapsed)
                if status == "error":
                    PROVIDER_ERRORS.labels(provider, name, error_type).inc()
                enrich(status=status, error_type=error_type, latency_ms=round(elapsed*1000,3))
                emit("provider.completed", latency_ms=round(elapsed*1000,3), status=status, error_type=error_type)


def observe(name, model=None):
    def decorate(function):
        def selected(args):
            return getattr(args[0], "model", model) if args else model
        if inspect.isasyncgenfunction(function):
            @wraps(function)
            async def wrapped(*args, **kwargs):
                snapshot = {**fields(), "operation": name, "provider": "openai", "model": selected(args)}
                started = time.perf_counter()
                status, error_type = "success", None
                iterator = function(*args, **kwargs)
                current = detached_span("waaxalma.provider." + name)
                try:
                    while True:
                        try:
                            # Never retain a ContextVar token or active span across yield.
                            with bound(**snapshot), activate(current):
                                chunk = await iterator.__anext__()
                        except StopAsyncIteration:
                            break
                        yield chunk
                except (asyncio.CancelledError, GeneratorExit):
                    status, error_type = "cancelled", "cancelled"
                    raise
                except Exception:
                    status, error_type = "error", "provider_error"
                    raise
                finally:
                    try:
                        await iterator.aclose()
                    finally:
                        elapsed = time.perf_counter() - started
                        with bound(**snapshot):
                            PROVIDER_CALLS.labels("openai", name, status).inc()
                            PROVIDER_LATENCY.labels("openai", name).observe(elapsed)
                            if status == "error":
                                PROVIDER_ERRORS.labels("openai", name, error_type).inc()
                            with activate(current):
                                emit("provider.completed", latency_ms=round(elapsed*1000,3), status=status, error_type=error_type)
                            if current is not None:
                                from opentelemetry.trace import Status, StatusCode
                                for key,value in {**snapshot, "status": status, "error_type": error_type, "latency_ms": elapsed*1000}.items():
                                    if value is not None and type(value) in (str,int,float,bool):
                                        current.set_attribute("waaxalma." + key, value)
                                if status != "success":
                                    current.set_status(Status(StatusCode.ERROR))
                                current.end()
        elif inspect.iscoroutinefunction(function):
            @wraps(function)
            async def wrapped(*args, **kwargs):
                with operation(name, model=selected(args)):
                    return await function(*args, **kwargs)
        else:
            @wraps(function)
            def wrapped(*args, **kwargs):
                with operation(name, model=selected(args)):
                    return function(*args, **kwargs)
        return wrapped
    return decorate


def record_usage(usage, *, operation="translation", model=None):
    # Unknown or unavailable usage remains absent, never a fabricated zero.
    values = {}
    for field, direction in (("input_tokens", "input"), ("output_tokens", "output")):
        value = usage.get(field) if isinstance(usage, dict) else getattr(usage, field, None)
        if type(value) is int and value >= 0:
            TOKENS.labels("openai", operation, direction).inc(value)
            values[field] = value
    if not values:
        return
    from app.core.settings import get_settings
    rates = get_settings().provider_token_prices_usd_per_million.get(model or "")
    if rates and len(values) == 2:
        cost = (values["input_tokens"] * rates["input"] + values["output_tokens"] * rates["output"]) / 1_000_000
        import math
        if math.isfinite(cost):
            COST.labels("openai", operation).inc(cost)
            values["estimated_cost_usd"] = cost
    emit("provider.usage", provider="openai", operation=operation, model=model, **values)
