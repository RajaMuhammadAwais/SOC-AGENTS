from collections.abc import Awaitable, Callable
from time import perf_counter
from uuid import uuid4

import redis.asyncio as redis
import structlog
from fastapi import Request, Response
from starlette import status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("x-request-id", str(uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        started_at = perf_counter()
        response = await call_next(request)
        duration_ms = round((perf_counter() - started_at) * 1000, 2)

        response.headers["x-request-id"] = request_id
        structlog.get_logger("api.request").info(
            "request.completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        *,
        redis_url: str,
        limit: int,
        window_seconds: int,
    ) -> None:
        super().__init__(app)
        self.limit = limit
        self.window_seconds = window_seconds
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.logger = structlog.get_logger("api.rate_limit")

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.url.path.startswith("/api/v1/health/"):
            return await call_next(request)

        client_id = request.headers.get(
            "x-forwarded-for",
            request.client.host if request.client else "unknown",
        )
        key = f"rate-limit:{client_id}:{request.url.path}"

        try:
            current = await self.redis.incr(key)
            if current == 1:
                await self.redis.expire(key, self.window_seconds)
            if current > self.limit:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "type": "https://enterprise-ai-soc.local/problems/rate-limited",
                        "title": "Rate limit exceeded",
                        "status": status.HTTP_429_TOO_MANY_REQUESTS,
                        "detail": "Too many requests.",
                    },
                )
        except Exception as exc:
            self.logger.warning("rate_limit.unavailable", error=str(exc))

        return await call_next(request)
