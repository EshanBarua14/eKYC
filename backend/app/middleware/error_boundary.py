"""
Error Boundary - M30
Global exception handling, request ID tracking, structured error responses.
No stack traces leak to clients in production.
BFIU Circular No. 29 - Section 6.1 Error Format Standard.
"""
import uuid
import time
import traceback
import logging
from datetime import datetime, timezone

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("ekyc.errors")

HTTP_ERROR_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    408: "REQUEST_TIMEOUT",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMIT_EXCEEDED",
    500: "INTERNAL_SERVER_ERROR",
    502: "BAD_GATEWAY",
    503: "SERVICE_UNAVAILABLE",
}

def _now_iso():
    return datetime.now(timezone.utc).isoformat()

def _new_request_id():
    return str(uuid.uuid4())

def _error_response(status_code, code, message, request_id, details=None):
    body = {
        "error": {
            "code":       code,
            "message":    message,
            "status":     status_code,
            "request_id": request_id,
            "timestamp":  _now_iso(),
            "bfiu_ref":   "BFIU Circular No. 29 - Section 6.1",
        }
    }
    if details:
        body["error"]["details"] = details
    return JSONResponse(
        status_code=status_code,
        content=body,
        headers={"X-Request-ID": request_id},
    )

async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or _new_request_id()
    request.state.request_id = request_id
    start_time = time.time()
    response = await call_next(request)
    duration_ms = round((time.time() - start_time) * 1000, 2)
    response.headers["X-Request-ID"]    = request_id
    response.headers["X-Response-Time"] = f"{duration_ms}ms"
    return response

async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = getattr(request.state, "request_id", _new_request_id())
    code = HTTP_ERROR_CODES.get(exc.status_code, "HTTP_ERROR")
    if isinstance(exc.detail, dict):
        message = exc.detail.get("message") or exc.detail.get("error") or str(exc.detail)
        details = exc.detail
    else:
        message = str(exc.detail) if exc.detail else "An error occurred"
        details = None
    logger.warning(f"[{request_id}] HTTP {exc.status_code} {code}: {message}")
    return _error_response(exc.status_code, code, message, request_id, details)

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = getattr(request.state, "request_id", _new_request_id())
    errors = []
    for err in exc.errors():
        errors.append({
            "field":   " -> ".join(str(loc) for loc in err["loc"]),
            "message": err["msg"],
            "type":    err["type"],
        })
    logger.warning(f"[{request_id}] VALIDATION_ERROR: {errors}")
    return _error_response(
        422, "VALIDATION_ERROR",
        "Request validation failed. Check the details field for field-level errors.",
        request_id,
        {"validation_errors": errors},
    )

async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", _new_request_id())
    logger.error(
        f"[{request_id}] UNHANDLED EXCEPTION on {request.method} {request.url}\n"
        + traceback.format_exc()
    )
    return _error_response(
        500, "INTERNAL_SERVER_ERROR",
        "An unexpected error occurred. Our team has been notified. Please retry or contact support.",
        request_id,
    )

def register_error_handlers(app):
    from starlette.middleware.base import BaseHTTPMiddleware
    app.add_middleware(BaseHTTPMiddleware, dispatch=request_id_middleware)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    print("[M30] Error boundary registered")
