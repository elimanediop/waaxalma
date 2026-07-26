import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette import status

from app.exceptions.error_codes import ErrorCode
from app.exceptions.pipeline_exception import PipelineException

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
        logger.warning(
            "Request validation failed method=%s path=%s errors=%s",
            request.method,
            request.url.path,
            exc.errors(),
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": {
                    "code": ErrorCode.INVALID_INPUT.value,
                    "message": "The request payload is invalid.",
                    "details": {
                        "errors": exc.errors(),
                    },
                },
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