from uuid import uuid4

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette import status
from starlette.exceptions import HTTPException as StarletteHTTPException


class ErrorResponse(JSONResponse):
    media_type = "application/problem+json"


def problem_response(
    *,
    status_code: int,
    title: str,
    detail: str,
    request: Request,
    code: str,
) -> ErrorResponse:
    trace_id = request.headers.get("x-request-id", str(uuid4()))
    return ErrorResponse(
        status_code=status_code,
        content={
            "type": f"https://enterprise-ai-soc.local/problems/{code}",
            "title": title,
            "status": status_code,
            "detail": detail,
            "trace_id": trace_id,
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request,
        exc: StarletteHTTPException,
    ) -> ErrorResponse:
        return problem_response(
            status_code=exc.status_code,
            title="HTTP error",
            detail=str(exc.detail),
            request=request,
            code="http-error",
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> ErrorResponse:
        return problem_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            title="Validation error",
            detail=str(exc.errors()),
            request=request,
            code="validation-error",
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> ErrorResponse:
        structlog.get_logger("api.error").exception("request.failed", error=str(exc))
        return problem_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            title="Internal server error",
            detail="An unexpected error occurred.",
            request=request,
            code="internal-server-error",
        )
