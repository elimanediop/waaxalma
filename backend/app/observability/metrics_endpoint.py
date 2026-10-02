from fastapi import FastAPI, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    generate_latest,
)


def register_metrics_endpoint(
    app: FastAPI,
) -> None:
    @app.get(
        "/metrics",
        include_in_schema=False,
    )
    async def metrics() -> Response:
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST,
        )
        

from prometheus_client import REGISTRY
from prometheus_client.core import GaugeMetricFamily


class ActiveSessionsCollector:
    def describe(self):
        yield GaugeMetricFamily("waaxalma_sessions_active", "Active persisted conversation sessions.")
        yield GaugeMetricFamily("waaxalma_sessions_scrape_error", "Unable to read active session count.")

    def collect(self):
        from app.bootstrap import container
        error = 0
        try:
            count = container.session_manager.repository.count_active()
        except Exception:
            error = 1
        else:
            yield GaugeMetricFamily("waaxalma_sessions_active", "Active persisted conversation sessions.", value=count)
        yield GaugeMetricFamily("waaxalma_sessions_scrape_error", "Unable to read active session count.", value=error)


REGISTRY.register(ActiveSessionsCollector())
