"""
M65: Request logging middleware
Injects request_id, user context into every log record.
Logs all requests with BST timestamp, method, path, status, duration.
"""
import logging
import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from app.core.logging_config import RequestContextFilter

logger = logging.getLogger("ekyc.requests")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Per-request structured logging.
    - Injects request_id into all log records for this request
    - Logs request start + completion with timing
    - Extracts user_id + role from JWT if present
    """

    async def dispatch(self, request: Request, call_next):
        request_id = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID") or str(uuid.uuid4())
        start = time.time()

        # Inject into log context for this thread
        RequestContextFilter.set_context(request_id=request_id)

        # Try extract user context from token (best-effort)
        try:
            auth = request.headers.get("Authorization", "")
            if auth.startswith("Bearer "):
                from jose import jwt as _jwt
                from app.core.security import PUBLIC_KEY, ALGORITHM
                payload = _jwt.decode(auth[7:], PUBLIC_KEY, algorithms=[ALGORITHM])
                RequestContextFilter.set_context(
                    user_id=payload.get("user_id", ""),
                    role=payload.get("role", ""),
                    institution_id=payload.get("sub", ""),
                )
        except Exception:
            pass

        logger.info(
            "Request started",
            extra={
                "method": request.method,
                "path": request.url.path,
                "client_ip": request.client.host if request.client else "unknown",
            }
        )

        try:
            response = await call_next(request)
            duration_ms = int((time.time() - start) * 1000)

            logger.info(
                "Request completed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                    "bfiu_ref": "BFIU Circular No. 29 §5.1" if request.url.path.startswith("/api") else None,
                }
            )
            response.headers["X-Request-ID"] = request_id
            return response

        except Exception as exc:
            duration_ms = int((time.time() - start) * 1000)
            logger.error(
                "Request failed",
                exc_info=exc,
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                }
            )
            raise
        finally:
            RequestContextFilter.clear_context()
