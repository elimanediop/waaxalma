import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette import status

from app.exceptions.error_codes import ErrorCode
from app.exceptions.pipeline_exception import PipelineException

from fastapi.encoders import jsonable_encoder

from app.core.realtime_exceptions import (
    RealtimeTranslationException,
)

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(PipelineException)
    async def pipeline_exception_handler(
        request: Request,
        exc: PipelineException,
    ) -> JSONResponse:
        logger.warning(
            "Pipeline failure method=%s path=%s code=%s message=%s",
            request.method,
            request.url.path,
            exc.code,
            exc.message,
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.to_detail(),
            },
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        errors = jsonable_encoder(
            exc.errors(),
            custom_encoder={
                Exception: str,
            },
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                "detail": {
                    "code": "REQUEST_VALIDATION_ERROR",
                    "message": "Request validation failed.",
                    "details": {
                        "errors": errors,
                    },
                }
            },
    )

    @app.exception_handler(Exception)
    async def unexpected_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.exception(
            "Unexpected error method=%s path=%s",
            request.method,
            request.url.path,
            exc_info=exc,
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": {
                    "code": ErrorCode.PIPELINE_ERROR.value,
                    "message": "An unexpected internal error occurred.",
                },
            },
        )
async def realtime_translation_exception_handler(
        request: Request,
        exc: RealtimeTranslationException,
    ) -> JSONResponse:
        logger.warning(
            "Realtime translation failed "
            "method=%s path=%s code=%s provider=%s retryable=%s",
            request.method,
            request.url.path,
            exc.code,
            exc.provider,
            exc.retryable,
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": {
                        "provider":
                            exc.provider,
                        "retryable":
                            exc.retryable,
                    },
                }
            },
        )