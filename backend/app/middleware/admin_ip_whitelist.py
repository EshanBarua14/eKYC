"""
M66: Admin endpoint IP whitelist middleware
BFIU Circular No. 29 §4.5 — access control

Blocks requests to /api/v1/admin/* and /api/v1/pep/* from IPs
not in ADMIN_IP_WHITELIST env var.
Empty whitelist = allow all (dev mode).
"""
import logging
import os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger("ekyc.security")

PROTECTED_PREFIXES = [
    "/api/v1/admin",
    "/api/v1/pep/entries",
    "/api/v1/users",
    "/api/v1/institutions",
]


def _get_whitelist() -> list[str]:
    raw = os.getenv("ADMIN_IP_WHITELIST", "")
    if not raw:
        return []
    return [ip.strip() for ip in raw.split(",") if ip.strip()]


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class AdminIPWhitelistMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        is_admin_path = any(path.startswith(p) for p in PROTECTED_PREFIXES)

        if not is_admin_path:
            return await call_next(request)

        whitelist = _get_whitelist()
        if not whitelist:
            return await call_next(request)

        client_ip = _get_client_ip(request)
        if client_ip not in whitelist:
            logger.warning(
                "Admin access blocked",
                extra={
                    "client_ip": client_ip,
                    "path": path,
                    "bfiu_ref": "BFIU Circular No. 29 §4.5",
                }
            )
            return JSONResponse(
                status_code=403,
                content={
                    "error": "IP_NOT_WHITELISTED",
                    "message": "Access to admin endpoints is restricted by IP.",
                    "bfiu_ref": "BFIU Circular No. 29 §4.5",
                }
            )

        return await call_next(request)
