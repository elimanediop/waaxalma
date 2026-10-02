"""Pure ASGI middleware preserves streaming, cancellation and task isolation."""
import asyncio
import time
from app.observability.context import bound, request_id, fields, enrich
from app.observability.events import emit
from app.observability.production_metrics import HTTP_REQUESTS, HTTP_LATENCY
from app.observability.tracing import span


class ObservabilityMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] not in {"http", "websocket"}:
            return await self.app(scope, receive, send)
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k,v in scope.get("headers", [])}
        correlation = request_id(headers.get("x-request-id"))
        scope.setdefault("state", {})["request_id"] = correlation
        path = scope.get("path", "")
        execution_mode = "realtime_enhanced" if "/enhanced/" in path else "realtime_direct" if "/realtime/translation/" in path else "standard"
        started = time.perf_counter()
        status_code, error_type = 500, None
        async def wrapped_send(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                message = {**message, "headers": [(k,v) for k,v in message.get("headers", []) if k.lower() != b"x-request-id"] + [(b"x-request-id", correlation.encode("ascii"))]}
            await send(message)
        with bound(request_id=correlation, execution_mode=execution_mode):
            with span("waaxalma.request", headers=headers) as current:
                try:
                    await self.app(scope, receive, wrapped_send)
                except asyncio.CancelledError:
                    error_type = "cancelled"
                    raise
                except Exception:
                    error_type = "unexpected_error"
                    raise
                finally:
                    # Resolve the route template after routing. Never label raw paths.
                    route = getattr(scope.get("route"), "path", "unmatched")
                    method = scope.get("method", "WEBSOCKET")
                    method = method if method in {"GET","POST","PATCH","PUT","DELETE","OPTIONS","HEAD","WEBSOCKET"} else "OTHER"
                    elapsed = time.perf_counter() - started
                    if scope["type"] == "http":
                        HTTP_REQUESTS.labels(method, route, str(status_code)).inc()
                        HTTP_LATENCY.labels(method, route).observe(elapsed)
                        if current is not None and status_code >= 500:
                            from opentelemetry.trace import Status, StatusCode
                            current.set_status(Status(StatusCode.ERROR))
                    enrich(status="error" if error_type or scope["type"] == "http" and status_code >= 400 else "success", status_code=status_code if scope["type"] == "http" else None, route=route, method=method)
                    emit("request.completed" if scope["type"] == "http" else "websocket.completed", method=method, route=route, status_code=status_code if scope["type"] == "http" else None, latency_ms=round(elapsed*1000,3), status="cancelled" if error_type == "cancelled" else "error" if error_type or status_code >= 400 and scope["type"] == "http" else "success", error_type=error_type or fields().get("error_type") or ("http_error" if status_code >=400 and scope["type"] == "http" else None))
