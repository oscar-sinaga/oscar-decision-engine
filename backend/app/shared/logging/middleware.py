"""ASGI middleware for request/correlation IDs, timing, and safe error mapping.

Responsibilities (docs/18):
- generate a request ID per request,
- accept a safe inbound ``X-Correlation-Id`` or generate one,
- expose both in response headers and the logging context,
- emit one structured technical log per request with duration and status,
- convert unhandled exceptions into the structured error envelope without
  leaking stack traces or internals.
"""

import json
import time
from typing import Any

from app.shared.logging.context import set_correlation_context
from app.shared.logging.logger import get_logger
from app.shared.utils.ids import new_correlation_id, new_request_id, sanitize_correlation_id

logger = get_logger("oscar.http")

REQUEST_ID_HEADER = b"x-request-id"
CORRELATION_ID_HEADER = b"x-correlation-id"


def _header(scope: dict[str, Any], name: bytes) -> str | None:
    headers: list[tuple[bytes, bytes]] = scope.get("headers", [])
    for key, value in headers:
        if key.lower() == name:
            return value.decode("latin-1")
    return None


class CorrelationMiddleware:
    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = new_request_id()
        correlation_id = (
            sanitize_correlation_id(_header(scope, CORRELATION_ID_HEADER)) or new_correlation_id()
        )
        started_at = time.perf_counter()
        response_started = False
        status_code: int | None = None

        async def send_with_headers(message: dict[str, Any]) -> None:
            nonlocal response_started, status_code
            if message["type"] == "http.response.start":
                response_started = True
                status_code = message["status"]
                headers = list(message.get("headers", []))
                headers.append((REQUEST_ID_HEADER, request_id.encode("latin-1")))
                headers.append((CORRELATION_ID_HEADER, correlation_id.encode("latin-1")))
                message = {**message, "headers": headers}
            await send(message)

        with set_correlation_context(request_id, correlation_id):
            try:
                await self.app(scope, receive, send_with_headers)
            except Exception:
                logger.exception(
                    "http.request.unhandled_error",
                    extra={"method": scope.get("method"), "path": scope.get("path")},
                )
                if response_started:
                    raise
                status_code = 500
                await _send_error_response(send, correlation_id, request_id)
            finally:
                duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
                logger.info(
                    "http.request",
                    extra={
                        "method": scope.get("method"),
                        "path": scope.get("path"),
                        "status_code": status_code,
                        "duration_ms": duration_ms,
                    },
                )


async def _send_error_response(send: Any, correlation_id: str, request_id: str) -> None:
    body = json.dumps(
        {
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An internal error occurred. Contact support with the correlation ID.",
                "details": [],
            },
            "correlation_id": correlation_id,
        }
    ).encode()
    await send(
        {
            "type": "http.response.start",
            "status": 500,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
                (REQUEST_ID_HEADER, request_id.encode("latin-1")),
                (CORRELATION_ID_HEADER, correlation_id.encode("latin-1")),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})
