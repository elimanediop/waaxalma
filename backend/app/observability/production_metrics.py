"""Low cardinality production metrics; identifiers and languages are excluded."""
from prometheus_client import Counter, Histogram

HTTP_REQUESTS = Counter("waaxalma_http_requests_total", "Completed HTTP requests.", ["method", "route", "status_code"])
HTTP_LATENCY = Histogram("waaxalma_http_duration_seconds", "Complete HTTP response latency.", ["method", "route"], buckets=(.01,.05,.1,.25,.5,1,2,5,10,30,60,120))
PROVIDER_CALLS = Counter("waaxalma_provider_calls_total", "Logical provider calls, including retries.", ["provider", "operation", "status"])
PROVIDER_ERRORS = Counter("waaxalma_provider_errors_total", "Failed logical provider calls.", ["provider", "operation", "error_type"])
PROVIDER_LATENCY = Histogram("waaxalma_provider_duration_seconds", "Logical provider latency including retries or entire stream.", ["provider", "operation"], buckets=(.05,.1,.25,.5,1,2,5,10,30,60,120))
SESSION_EVENTS = Counter("waaxalma_session_events_total", "Persisted session lifecycle events.", ["event", "execution_mode"])
SESSION_DURATION = Histogram("waaxalma_session_duration_seconds", "Wall time from session creation to explicit close.", ["execution_mode"], buckets=(1,10,30,60,300,900,1800,3600,86400))
TOKENS = Counter("waaxalma_provider_tokens_total", "Provider-reported input/output tokens when available.", ["provider", "operation", "direction"])
COST = Counter("waaxalma_provider_estimated_cost_usd_total", "Partial token-based USD estimate using configured rates.", ["provider", "operation"])


def mode(value):
    value = {"enhanced": "realtime_enhanced", "direct": "realtime_direct"}.get(value, value)
    return value if value in {"standard", "realtime_direct", "realtime_enhanced"} else "other"
