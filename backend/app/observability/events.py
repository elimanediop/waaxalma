"""Dedicated JSON business events, with an explicit field allowlist."""
from datetime import datetime, timezone
import json
import logging
from app.observability.context import FIELDS, fields

DEFAULTS = dict.fromkeys(("request_id", "session_id", "execution_mode", "provider", "model", "source_language", "target_language", "latency_ms", "status", "error_type"))


class EventFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps(record.event_data, ensure_ascii=True, allow_nan=False, separators=(",", ":"))


logger = logging.getLogger("waaxalma.events")
logger.setLevel(logging.INFO)
logger.propagate = False
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(EventFormatter())
    logger.addHandler(handler)


def emit(event, **values):
    from app.observability.tracing import correlation
    data = {**DEFAULTS, **fields(), **correlation(), **{k: v for k, v in values.items() if k in FIELDS}}
    # Bound strings for operational fields; never serialize arbitrary objects.
    data = {k: (v[:256] if isinstance(v, str) else v if v is None or type(v) in (int, float, bool) else None) for k, v in data.items()}
    data.update(timestamp=datetime.now(timezone.utc).isoformat(), event=event)
    logger.info(event, extra={"event_data": data})
