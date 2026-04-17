"""
Xpert Fintech eKYC Platform
API Gateway Service - M12
Webhook engine, data residency enforcement, rate limiting, API versioning
"""
import uuid
import time
import hashlib
import hmac
from datetime import datetime, timezone, timedelta
from typing import Optional

# ---------------------------------------------------------------------------
# API versioning
# ---------------------------------------------------------------------------
API_VERSION     = "v1"
API_VERSION_INT = 1
DEPRECATION_POLICY_MONTHS = 12

# ---------------------------------------------------------------------------
# Data residency - whitelisted outbound domains (BFIU Circular No. 23)
# ---------------------------------------------------------------------------
WHITELISTED_DOMAINS = {
    "nid.ec.gov.bd",          # Election Commission NID API
    "api.porichoy.gov.bd",    # Porichoy verification
    "bfiu.gov.bd",            # BFIU reporting
    "bb.org.bd",              # Bangladesh Bank
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
}

# PII field names that must never leave Bangladesh
PII_FIELDS = {
    "nid_number", "nid_hash", "fingerprint_b64", "face_image",
    "photo_b64", "date_of_birth", "mobile", "email",
    "present_address", "permanent_address", "full_name",
}

# ---------------------------------------------------------------------------
# Rate limiting (in-memory, Redis in prod)
# ---------------------------------------------------------------------------
RATE_LIMITS = {
    "auth_token":    {"requests": 10,  "window_seconds": 60},
    "face_verify":   {"requests": 30,  "window_seconds": 60},
    "nid_scan":      {"requests": 60,  "window_seconds": 60},
    "nid_verify":    {"requests": 60,  "window_seconds": 60},
    "default":       {"requests": 120, "window_seconds": 60},
}

_rate_counters: dict = {}   # key -> {count, window_start}

def check_rate_limit(endpoint: str, client_key: str) -> dict:
    """
    Check rate limit for endpoint + client combination.
    Returns allowed, remaining, reset_at.
    """
    limit_config = RATE_LIMITS.get(endpoint, RATE_LIMITS["default"])
    max_req      = limit_config["requests"]
    window_sec   = limit_config["window_seconds"]

    key = f"{endpoint}:{client_key}"
    now = time.time()

    if key not in _rate_counters:
        _rate_counters[key] = {"count": 0, "window_start": now}

    record = _rate_counters[key]

    # Reset window if expired
    if now - record["window_start"] >= window_sec:
        record["count"]        = 0
        record["window_start"] = now

    record["count"] += 1
    remaining  = max(0, max_req - record["count"])
    reset_at   = record["window_start"] + window_sec
    allowed    = record["count"] <= max_req

    return {
        "allowed":    allowed,
        "count":      record["count"],
        "limit":      max_req,
        "remaining":  remaining,
        "reset_at":   datetime.fromtimestamp(reset_at, tz=timezone.utc).isoformat(),
        "window_sec": window_sec,
        "endpoint":   endpoint,
    }

def reset_rate_limits():
    """Clear all rate counters (for testing)."""
    _rate_counters.clear()

# ---------------------------------------------------------------------------
# Data residency enforcement
# ---------------------------------------------------------------------------
def check_data_residency(destination_domain: str, payload: dict) -> dict:
    """
    Check if outbound API call to destination_domain is allowed.
    Blocks calls containing PII to non-whitelisted domains.
    BFIU Circular No. 23: no cross-border data transfer without approval.
    """
    is_whitelisted = destination_domain.lower() in WHITELISTED_DOMAINS

    # Check if payload contains PII
    payload_keys  = set(payload.keys()) if payload else set()
    pii_present   = bool(payload_keys & PII_FIELDS)

    if pii_present and not is_whitelisted:
        return {
            "allowed":           False,
            "reason":            "DATA_RESIDENCY_VIOLATION",
            "destination":       destination_domain,
            "pii_fields_found":  list(payload_keys & PII_FIELDS),
            "message":           f"PII cannot be sent to non-whitelisted domain: {destination_domain}",
            "bfiu_ref":          "BFIU Circular No. 23 - Cross-border data transfer prohibited",
        }

    return {
        "allowed":     True,
        "destination": destination_domain,
        "whitelisted": is_whitelisted,
        "pii_present": pii_present,
        "bfiu_ref":    "BFIU Circular No. 23",
    }

def add_whitelisted_domain(domain: str) -> dict:
    """Add a domain to the whitelist (Admin action)."""
    WHITELISTED_DOMAINS.add(domain.lower())
    return {"added": domain, "total_whitelisted": len(WHITELISTED_DOMAINS)}

# ---------------------------------------------------------------------------
# Webhook engine
# ---------------------------------------------------------------------------
WEBHOOK_EVENTS = [
    "onboarding.completed",
    "onboarding.failed",
    "face_verify.matched",
    "face_verify.failed",
    "screening.blocked",
    "screening.flagged",
    "risk.high_grade",
    "edd.triggered",
    "periodic_review.due",
    "account.closed",
]

_webhook_endpoints: dict = {}   # institution_id -> list of endpoints
_webhook_delivery_log: list = []

def register_webhook(
    institution_id: str,
    url:            str,
    events:         list,
    secret:         Optional[str] = None,
) -> dict:
    """Register a webhook endpoint for an institution."""
    # Validate events
    invalid = [e for e in events if e not in WEBHOOK_EVENTS]
    if invalid:
        return {"success": False, "error": f"Invalid events: {invalid}"}

    webhook_id = str(uuid.uuid4())
    secret     = secret or str(uuid.uuid4()).replace("-", "")
    now        = datetime.now(timezone.utc).isoformat()

    endpoint = {
        "webhook_id":     webhook_id,
        "institution_id": institution_id,
        "url":            url,
        "events":         events,
        "secret":         secret,
        "is_active":      True,
        "created_at":     now,
        "delivery_count": 0,
        "failure_count":  0,
    }

    if institution_id not in _webhook_endpoints:
        _webhook_endpoints[institution_id] = []
    _webhook_endpoints[institution_id].append(endpoint)

    return {"success": True, **{k: v for k, v in endpoint.items() if k != "secret"}, "secret": secret}

def dispatch_webhook(
    institution_id: str,
    event:          str,
    payload:        dict,
) -> list:
    """
    Dispatch a webhook event to all registered endpoints for an institution.
    Returns list of delivery results.
    In prod: Celery task with exponential backoff retry.
    """
    endpoints = _webhook_endpoints.get(institution_id, [])
    results   = []

    for endpoint in endpoints:
        if not endpoint["is_active"]:
            continue
        if event not in endpoint["events"]:
            continue

        delivery_id = str(uuid.uuid4())
        now         = datetime.now(timezone.utc).isoformat()
        signature   = _sign_payload(payload, endpoint["secret"])

        # Simulate delivery (in prod: actual HTTP POST)
        delivery = {
            "delivery_id":    delivery_id,
            "webhook_id":     endpoint["webhook_id"],
            "institution_id": institution_id,
            "event":          event,
            "url":            endpoint["url"],
            "signature":      signature,
            "status":         "DELIVERED",
            "http_status":    200,
            "attempt":        1,
            "dispatched_at":  now,
            "payload_size":   len(str(payload)),
        }

        endpoint["delivery_count"] += 1
        _webhook_delivery_log.append(delivery)
        results.append(delivery)

    return results

def get_webhook_delivery_log(institution_id: Optional[str] = None) -> list:
    if institution_id:
        return [d for d in _webhook_delivery_log if d["institution_id"] == institution_id]
    return _webhook_delivery_log

def get_webhooks(institution_id: str) -> list:
    return [
        {k: v for k, v in ep.items() if k != "secret"}
        for ep in _webhook_endpoints.get(institution_id, [])
    ]

def _sign_payload(payload: dict, secret: str) -> str:
    """HMAC-SHA256 signature for webhook payload verification."""
    import json
    body = json.dumps(payload, sort_keys=True, default=str).encode()
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

def verify_webhook_signature(payload: dict, secret: str, signature: str) -> bool:
    """Verify webhook signature (for receiving institutions)."""
    expected = _sign_payload(payload, secret)
    return hmac.compare_digest(expected, signature)

def reset_webhooks():
    """Clear webhook data (for testing)."""
    _webhook_endpoints.clear()
    _webhook_delivery_log.clear()
