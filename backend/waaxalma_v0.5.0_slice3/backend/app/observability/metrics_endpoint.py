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
        