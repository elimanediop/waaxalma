# Production Observability

The v1.0.0 release retains business observability and opt-in retention metrics. Compose images use `1.0.0`; Git release tagging follows final acceptance.

This slice adds Waaxalma business events, provider measurements, session metrics and optional OpenTelemetry. It keeps the existing pipeline and realtime metrics. No cloud backend, collector or deployment is required by default.

## Integration

Apply the ZIP as an overlay at the root containing `backend/`, `streamlit/` and `compose.yaml`. Merge `backend/`, `.github/`, `ci/` and `docs/`; replace `compose.yaml` with the supplied version. Preserve your `.env`, session database, virtual environments and root README. The updated `.env.example` files are reference templates only.

Backend dependencies are unchanged by default. OpenTelemetry has a separate universal, hashed lock. CI runs the optional SDK through the `otel-tests` quality gate. Runtime installations without that optional lock skip its four SDK tests.

```powershell
# Backend development environment, from backend/:
$env:APP_ENV = "test"
python -m pytest -q
# From project root with your usual production Compose environment:
docker compose up --build -d
python ci/smoke.py --ui http://127.0.0.1:8501
```

Do not leave a test-mode process environment set when testing native production. Compose explicitly selects production. The HTTP smoke test creates and closes one conversation without invoking an AI provider.

## Structured events and correlation

`waaxalma.events` writes one JSON object per event to stderr. Existing runtime/server access and diagnostic logs can remain textual. `LOG_LEVEL` controls business event visibility at application startup; the default `info` includes the events.

Events include `request.completed`, `websocket.completed`, `agent.completed`, `stage.completed`, `provider.completed`, `provider.retry`, `provider.usage`, `session.created` and `session.closed`.

Each event contains the standard fields below, with `null` where the operation has no corresponding concept. Stage events identify stages; provider events identify the actual configured model. A request spanning several models does not pretend to have one overall model.

| Field | Meaning |
| --- | --- |
| request_id | Valid incoming `X-Request-Id`, otherwise a generated UUID |
| session_id | Persistent conversation or existing transient execution identifier |
| execution_mode | Actual route mode: standard, realtime_direct or realtime_enhanced; session lifecycle uses normalized persisted mode |
| provider / model | Provider and configured model for the measured provider call |
| source_language / target_language | Known language metadata; missing/auto-detected values remain null where not available |
| latency_ms | Elapsed operation/response/stream time measured with a monotonic clock |
| status / error_type | Outcome and safe error category/code, never exception messages |
| trace_id | Existing Waaxalma execution trace ID for stage events |
| otel_trace_id / otel_span_id | OpenTelemetry identifiers when tracing is enabled and a span is active |
| session_duration_seconds | Creation-to-close wall time on session.closed |

HTTP responses expose `X-Request-Id`, including handled errors and internal error responses. CORS exposes that response header to browser code. Accepted IDs are 1–128 ASCII characters matching `[A-Za-z0-9][A-Za-z0-9_.-]{0,127}`. Invalid values are replaced, without changing identity authorization. Duplicate correlation IDs are allowed and are not an idempotency mechanism. Generated audio filenames are independently unique: clients must use the returned audio URL rather than infer it from request_id.

The middleware is pure ASGI and does not consume request bodies. Task-local context isolates concurrent requests and propagates to child tasks and `asyncio.to_thread`. Stream context is scoped around advancement of the iterator and does not leak to the consumer across `yield`. Early close/cancellation is recorded and propagated.

WebSocket connections have a generated/header correlation ID; the selected session_id and target language are set at session.start before processor tasks are created. Direct WebRTC audio travels between browser and OpenAI, so the backend measures session credential creation and existing browser-reported latency, not the full remote audio processing lifetime.

## Privacy

Business events use a field allowlist. Request/response bodies, client IDs, audio bytes, transcripts, translations, prompts, keywords, credentials and exception messages are not collected. Legacy enhanced debug logs containing speech text have been removed. Application exception logs omit tracebacks that could include provider content; OpenAI/httpx/httpcore diagnostic logging is kept at WARNING to avoid SDK request-body debug output. Uvicorn logs remain separate: do not place credentials in URLs.

Identifiers and language metadata can still be identifying data. Restrict log and `/metrics` access at your deployment boundary. This slice does not introduce authentication for those endpoints or a retention policy; retention/security governance is Slice 6. An allowlist is not protection against deliberately placing sensitive content in a metadata field such as a language or correlation identifier.

## Prometheus metrics

`GET /metrics` remains available without `X-Client-Id`. New labels exclude client/request/session IDs, raw URLs, languages and model names. HTTP labels use resolved route templates (for example `/api/sessions/{session_id}`); unmatched URLs share `unmatched`. Unknown agent and operation names in existing agent/stage helpers are grouped as `other`.

| Metric | Meaning |
| --- | --- |
| waaxalma_http_requests_total | HTTP requests by method, route template and status code |
| waaxalma_http_duration_seconds | Full HTTP response duration, including streamed response time |
| waaxalma_provider_calls_total | Logical provider operations by provider, operation and outcome |
| waaxalma_provider_errors_total | Final failed provider operations by safe error category |
| waaxalma_provider_duration_seconds | STT, translation, TTS and credential-session operation durations |
| waaxalma_provider_retries_total | Each Waaxalma-managed retry (existing metric, now emitted by executor) |
| waaxalma_sessions_active | Active persisted conversations, read from the repository at each scrape |
| waaxalma_sessions_scrape_error | 1 if the repository cannot be counted; active gauge is omitted in that scrape |
| waaxalma_session_events_total | Created/closed conversations by bounded execution mode |
| waaxalma_session_duration_seconds | Wall duration of explicitly closed persisted conversations |
| waaxalma_provider_tokens_total | Provider-reported input/output tokens when available |
| waaxalma_provider_estimated_cost_usd_total | Partial configured token-based USD estimate |

Logical call durations include retries and backoff. Streaming durations include the whole consumed stream and consumer pacing; they are not time-to-first-token/audio. Cancelled calls have a distinct outcome and do not increment provider_errors. OpenAI SDK retries inside enhanced providers, if any, are not separately visible to the Waaxalma retry counter.

Active conversations include rows restored after restart, including legacy unowned rows. Closed sessions are excluded. Counting reads SQLite in existing read-only mode and cannot recreate a removed DB. It does not load conversation histories. Failed scrapes do not fabricate zero active sessions. SQLite uses a short 250 ms lock timeout; a blocked or missing DB signals scrape_error. Custom repositories need `count_active()` to support this gauge.

Counters/histograms are process-local and reset on restart; they are not billing records. This packaging runs one backend worker. Multiple workers require a dedicated Prometheus multiprocess setup and coordinated lifecycle counting, which this slice does not implement. Session duration is wall time until explicit closure, not speech duration or inactivity timeout. Closed-session retention is documented in `operations.md`; active sessions are excluded. Repeated close calls in sequence record one duration; lifecycle metrics are best-effort observations, not an exactly-once audit ledger across concurrent writers or crashes.

Example PromQL:

```promql
sum(rate(waaxalma_http_requests_total[5m])) by (route, status_code)
sum(rate(waaxalma_provider_errors_total[5m])) by (provider, operation)
histogram_quantile(0.95, sum(rate(waaxalma_provider_duration_seconds_bucket[5m])) by (le, operation))
waaxalma_sessions_active
waaxalma_sessions_scrape_error
```

## Usage and estimated cost

Standard OpenAI Responses translations and enhanced translation `response.completed` events provide usage when available. STT in plain-text mode, streamed TTS and browser-direct audio do not currently expose backend token usage. Unknown usage produces no usage event or token increment; it is not reported as zero.

No current provider pricing is hardcoded. Optionally configure rates in USD per million tokens using exact configured model keys:

```dotenv
PROVIDER_TOKEN_PRICES_USD_PER_MILLION='{"my-model":{"input":1.0,"output":2.0}}'
```

These numbers are illustrative, not actual provider prices. A cost is emitted only when both input and output counts and both rates are available. It ignores cache discounts, audio-specific units and other billing dimensions. It is explicitly an estimate for the observed subset, not total application spending. Missing model rates produce token observations without cost estimates.

## Optional OpenTelemetry

Default: `OTEL_ENABLED=false`. No OpenTelemetry SDK import, collector connection or dependency is needed in normal operation. Enabling it requires the optional lock and a full OTLP/HTTP traces URL.

Native backend:

```powershell
python -m pip install --require-hashes -r requirements-otel.lock
$env:OTEL_ENABLED = "true"
$env:OTEL_SERVICE_NAME = "waaxalma"
$env:OTEL_EXPORTER_OTLP_TRACES_ENDPOINT = "http://localhost:4318/v1/traces"
```

Compose `.env`:

```dotenv
INSTALL_OTEL=true
OTEL_ENABLED=true
OTEL_SERVICE_NAME=waaxalma
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://host.docker.internal:4318/v1/traces
```

Rebuild the backend image after changing INSTALL_OTEL. `host.docker.internal` suits Docker Desktop; on Linux use a collector address reachable from the container network. This slice does not provision a collector or a visualization stack. Use a trusted collector/network boundary; exporter authentication headers are not configured here.

Spans cover requests, agent executions and logical provider calls/streams. Incoming standard trace context is extracted for HTTP/WebSocket connections; child spans retain the parent relationship. Trace attributes use the same bounded metadata field set as events. Exception recording is disabled to avoid exporting content, while error status remains available. Outbound SDK auto-instrumentation is deliberately absent. The private SDK provider avoids changing process-global tracing ownership. `OTEL_TRACES_SAMPLE_RATIO` controls root sampling (default 1.0; range 0–1); incoming sampled/unsampled parent decisions are respected. This explicit sampler does not depend on ambient SDK sampler variables. The batch exporter shuts down in the application lifespan on a worker thread; a failed collector export does not fail a business request. Collector backlog/export time can still affect shutdown timing; shutdown budgets and restart behavior are documented in `operations.md`.

The optional CI job executes SDK tests with an in-memory exporter, covering parent propagation and absence of exception text. Default dependency jobs execute without the SDK. Optional packages do not enter the default runtime lock.

## Validation

See README_SLICE5.md for the delivered test results. The authoring environment cannot execute Docker; the updated Compose build and GitHub workflow need validation on your machine/repository. Local tests cover concurrent context isolation, error correlation, streams/cancellation, restart-aware active counts, deleted databases, optional tracing and reported usage. The HTTP smoke test verifies `/metrics` and health/session boundaries without paid provider calls.

References: [Prometheus label naming](https://prometheus.io/docs/practices/naming/), [OpenTelemetry Python instrumentation](https://opentelemetry.io/docs/languages/python/instrumentation/).
