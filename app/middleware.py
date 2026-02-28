import uuid

import structlog
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger()


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


def add_middleware(app: FastAPI) -> None:
    app.add_middleware(RequestIDMiddleware)
    _configure_structlog()


def _configure_structlog() -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )
