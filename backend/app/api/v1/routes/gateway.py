"""
Xpert Fintech eKYC Platform
API Gateway Routes - M12
GET  /gateway/health           - Service health check
GET  /gateway/version          - API version info
POST /gateway/webhook/register - Register webhook endpoint
GET  /gateway/webhook/list     - List webhooks for institution
POST /gateway/webhook/dispatch - Dispatch webhook event (internal)
GET  /gateway/webhook/log      - Webhook delivery log
POST /gateway/residency/check  - Check data residency compliance
POST /gateway/residency/whitelist - Add domain to whitelist
GET  /gateway/rate-limits      - Rate limit configuration
POST /gateway/rate-limits/check - Check rate limit for endpoint
GET  /gateway/openapi-summary  - API endpoint summary
"""
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import JWTError

from app.core.security import decode_token
from app.core.config import settings
from app.services.gateway_service import (
    check_rate_limit, check_data_residency, add_whitelisted_domain,
    register_webhook, dispatch_webhook, get_webhooks,
    get_webhook_delivery_log, verify_webhook_signature,
    WEBHOOK_EVENTS, RATE_LIMITS, WHITELISTED_DOMAINS,
    API_VERSION, API_VERSION_INT, DEPRECATION_POLICY_MONTHS,
)

router   = APIRouter(prefix="/gateway", tags=["API Gateway"])
security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    try:
        return decode_token(credentials.credentials)
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

class WebhookRegisterRequest(BaseModel):
    institution_id: str
    url:            str
    events:         list
    secret:         Optional[str] = None

class WebhookDispatchRequest(BaseModel):
    institution_id: str
    event:          str
    payload:        dict

class ResidencyCheckRequest(BaseModel):
    destination_domain: str
    payload:            dict

class WhitelistRequest(BaseModel):
    domain: str

class RateLimitCheckRequest(BaseModel):
    endpoint:   str
    client_key: str

# ---------------------------------------------------------------------------
# GET /gateway/health
# ---------------------------------------------------------------------------
@router.get("/health")
def health_check():
    """Service health check. No auth required. Used by load balancers."""
    return {
        "status":    "ok",
        "service":   settings.APP_NAME,
        "version":   settings.APP_VERSION,
        "api":       API_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

# ---------------------------------------------------------------------------
# GET /gateway/version
# ---------------------------------------------------------------------------
@router.get("/version")
def version_info():
    """API version information and deprecation policy."""
    return {
        "current_version":          API_VERSION,
        "version_int":              API_VERSION_INT,
        "deprecation_policy_months": DEPRECATION_POLICY_MONTHS,
        "versioning_scheme":         "URL-based (/api/v{n}/)",
        "breaking_change_policy":    "New version issued. Previous version supported 12 months.",
        "changelog_url":            "/api/v1/gateway/changelog",
        "bfiu_compliance":          "BFIU Circular No. 29 - December 31, 2026 deadline",
    }

# ---------------------------------------------------------------------------
# POST /gateway/webhook/register
# ---------------------------------------------------------------------------
@router.post("/webhook/register", status_code=201)
def webhook_register(
    req: WebhookRegisterRequest,
    current_user: dict = Depends(get_current_user),
):
    """Register a webhook endpoint for onboarding status events."""
    result = register_webhook(req.institution_id, req.url, req.events, req.secret)
    if not result["success"]:
        raise HTTPException(status_code=422, detail=result["error"])
    return result

# ---------------------------------------------------------------------------
# GET /gateway/webhook/list
# ---------------------------------------------------------------------------
@router.get("/webhook/list")
def webhook_list(
    institution_id: str,
    current_user:   dict = Depends(get_current_user),
):
    """List registered webhooks for an institution."""
    return {"webhooks": get_webhooks(institution_id), "institution_id": institution_id}

# ---------------------------------------------------------------------------
# POST /gateway/webhook/dispatch
# ---------------------------------------------------------------------------
@router.post("/webhook/dispatch")
def webhook_dispatch(
    req: WebhookDispatchRequest,
    current_user: dict = Depends(get_current_user),
):
    """Dispatch a webhook event (internal use / testing)."""
    if req.event not in WEBHOOK_EVENTS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid event. Must be one of: {WEBHOOK_EVENTS}",
        )
    results = dispatch_webhook(req.institution_id, req.event, req.payload)
    return {"dispatched": len(results), "results": results}

# ---------------------------------------------------------------------------
# GET /gateway/webhook/log
# ---------------------------------------------------------------------------
@router.get("/webhook/log")
def webhook_log(
    institution_id: Optional[str] = None,
    current_user:   dict = Depends(get_current_user),
):
    """Webhook delivery log."""
    return {"deliveries": get_webhook_delivery_log(institution_id)}

# ---------------------------------------------------------------------------
# GET /gateway/webhook/events
# ---------------------------------------------------------------------------
@router.get("/webhook/events")
def webhook_events(current_user: dict = Depends(get_current_user)):
    """List all supported webhook event types."""
    return {"events": WEBHOOK_EVENTS, "total": len(WEBHOOK_EVENTS)}

# ---------------------------------------------------------------------------
# POST /gateway/residency/check
# ---------------------------------------------------------------------------
@router.post("/residency/check")
def residency_check(
    req: ResidencyCheckRequest,
    current_user: dict = Depends(get_current_user),
):
    """Check if outbound API call to domain is data-residency compliant."""
    return check_data_residency(req.destination_domain, req.payload)

# ---------------------------------------------------------------------------
# POST /gateway/residency/whitelist
# ---------------------------------------------------------------------------
@router.post("/residency/whitelist", status_code=201)
def residency_whitelist(
    req: WhitelistRequest,
    current_user: dict = Depends(get_current_user),
):
    """Add a domain to the data residency whitelist. Admin action."""
    return add_whitelisted_domain(req.domain)

# ---------------------------------------------------------------------------
# GET /gateway/residency/domains
# ---------------------------------------------------------------------------
@router.get("/residency/domains")
def residency_domains(current_user: dict = Depends(get_current_user)):
    """List whitelisted outbound domains."""
    return {
        "whitelisted_domains": sorted(WHITELISTED_DOMAINS),
        "total":              len(WHITELISTED_DOMAINS),
        "bfiu_ref":           "BFIU Circular No. 23",
    }

# ---------------------------------------------------------------------------
# GET /gateway/rate-limits
# ---------------------------------------------------------------------------
@router.get("/rate-limits")
def rate_limits_config(current_user: dict = Depends(get_current_user)):
    """Rate limit configuration per endpoint."""
    return {"rate_limits": RATE_LIMITS, "bfiu_ref": "BFIU Circular No. 29 - Section 7.1"}

# ---------------------------------------------------------------------------
# POST /gateway/rate-limits/check
# ---------------------------------------------------------------------------
@router.post("/rate-limits/check")
def rate_limit_check(
    req: RateLimitCheckRequest,
    current_user: dict = Depends(get_current_user),
):
    """Check rate limit status for an endpoint and client key."""
    return check_rate_limit(req.endpoint, req.client_key)

# ---------------------------------------------------------------------------
# GET /gateway/openapi-summary
# ---------------------------------------------------------------------------
@router.get("/openapi-summary")
def openapi_summary(current_user: dict = Depends(get_current_user)):
    """Summary of all API endpoints across all modules."""
    return {
        "api_version": API_VERSION,
        "base_url":    "/api/v1",
        "modules": {
            "auth":       ["/auth/register", "/auth/token", "/auth/refresh", "/auth/logout", "/auth/me", "/auth/totp/setup", "/auth/totp/verify", "/auth/roles"],
            "nid":        ["/nid/scan", "/nid/verify", "/nid/session-status"],
            "onboarding": ["/onboarding/start", "/onboarding/step", "/onboarding/fail", "/onboarding/session/{id}", "/onboarding/steps"],
            "risk":       ["/risk/grade", "/risk/edd", "/risk/rescore", "/risk/factors", "/risk/thresholds"],
            "screening":  ["/screening/unscr", "/screening/pep", "/screening/adverse-media", "/screening/exit-list/add", "/screening/exit-list/check", "/screening/full"],
            "lifecycle":  ["/lifecycle/register", "/lifecycle/due-reviews", "/lifecycle/complete-review", "/lifecycle/declare/generate", "/lifecycle/upgrade/initiate", "/lifecycle/close"],
            "audit":      ["/audit/log", "/audit/dashboard", "/audit/export/json", "/audit/export/csv", "/audit/maker", "/audit/checker/{id}"],
            "gateway":    ["/gateway/health", "/gateway/version", "/gateway/webhook/register", "/gateway/residency/check", "/gateway/rate-limits"],
            "face":       ["/face/verify", "/face/analyze"],
            "fingerprint": ["/fingerprint/verify", "/fingerprint/status"],
            "kyc":        ["/kyc/profile", "/kyc/profile/{id}", "/kyc/profiles"],
        },
        "total_endpoints": 50,
        "auth_scheme":     "JWT RS256 Bearer",
        "bfiu_compliant":  True,
    }
