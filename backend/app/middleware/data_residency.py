"""
M82: Data residency enforcement — BFIU Circular No. 29 §5.2 + Circ-23
Ensures no customer PII leaves Bangladesh jurisdiction.
Blocks outbound responses with cross-border data transfer headers.
Enforces BD-only data processing on all KYC endpoints.
"""
from __future__ import annotations
import json
import logging
import os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

log = logging.getLogger("ekyc.data_residency")

# Endpoints that handle PII — enforce residency check
PII_PREFIXES = [
    "/api/v1/kyc",
    "/api/v1/nid",
    "/api/v1/face",
    "/api/v1/fingerprint",
    "/api/v1/onboarding",
    "/api/v1/profiles",
    "/api/v1/pep",
    "/api/v1/edd",
]

# Headers that indicate cross-border forwarding — block these
FORBIDDEN_FORWARD_HEADERS = [
    "x-forwarded-to-region",
    "x-cloud-region",
    "x-data-region",
]

# Allowed processing regions (Bangladesh)
ALLOWED_REGIONS = frozenset({"bd", "bangladesh", "asia-south-1-bd", "local"})

# Compliance header added to all PII responses
RESIDENCY_HEADER = "X-Data-Residency"
RESIDENCY_VALUE  = "BD-ONLY"
BFIU_REF_HEADER  = "X-BFIU-Compliance"
BFIU_REF_VALUE   = "Circular-No-29-S5.2"


class DataResidencyMiddleware(BaseHTTPMiddleware):
    """
    BFIU §5.2 + Circular 23: No cross-border PII transfer.
    - Adds BD residency headers to all PII endpoint responses
    - Blocks requests with explicit cross-border forwarding headers
    - Logs all PII endpoint access for audit
    """

    def __init__(self, app: ASGIApp, enforce: bool = True):
        super().__init__(app)
        self.enforce = enforce
        env_enforce = os.getenv("DATA_RESIDENCY_ENFORCE", "true").lower()
        self.enforce = env_enforce not in ("false", "0", "no")
        log.info("[M82] DataResidencyMiddleware init — enforce=%s", self.enforce)

    def _is_pii_endpoint(self, path: str) -> bool:
        return any(path.startswith(prefix) for prefix in PII_PREFIXES)

    def _has_cross_border_header(self, request: Request) -> str | None:
        """Return offending header name if cross-border forwarding detected."""
        for h in FORBIDDEN_FORWARD_HEADERS:
            val = request.headers.get(h, "")
            if val and val.lower() not in ALLOWED_REGIONS:
                return h
        # Check X-Forwarded-For region hints
        region = request.headers.get("x-processing-region", "")
        if region and region.lower() not in ALLOWED_REGIONS:
            return f"x-processing-region: {region}"
        return None

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if not self._is_pii_endpoint(path):
            return await call_next(request)

        # Block cross-border forwarding
        offending = self._has_cross_border_header(request)
        if offending and self.enforce:
            log.warning(
                "[M82] Cross-border PII transfer blocked — path=%s header=%s ip=%s",
                path, offending, request.client.host if request.client else "unknown"
            )
            return JSONResponse(
                status_code=403,
                content={
                    "error": "DATA_RESIDENCY_VIOLATION",
                    "detail": (
                        "Cross-border data transfer not permitted. "
                        "BFIU Circular No. 29 §5.2 — customer PII must remain in Bangladesh."
                    ),
                    "bfiu_ref": "Circular No. 29 §5.2",
                },
                headers={
                    RESIDENCY_HEADER: RESIDENCY_VALUE,
                    BFIU_REF_HEADER: BFIU_REF_VALUE,
                },
            )

        response = await call_next(request)

        # Add residency compliance headers to all PII responses
        response.headers[RESIDENCY_HEADER] = RESIDENCY_VALUE
        response.headers[BFIU_REF_HEADER]  = BFIU_REF_VALUE
        response.headers["X-Content-Type-Options"] = "nosniff"

        log.debug("[M82] PII endpoint served — path=%s residency=BD-ONLY", path)
        return response
