"""
Rate Limit Routes - M28
GET  /rate-limits         - View all configured limits
POST /rate-limits/check   - Check limit for endpoint + client
GET  /rate-limits/stats   - Active counter stats
POST /rate-limits/reset   - Reset counters (admin/test only)
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.rate_limiter import (
    check_rate_limit, get_all_limits, get_limit_config,
    reset_counters, get_stats, RATE_LIMITS,
)

router = APIRouter(prefix="/rate-limits", tags=["Rate Limiting"])

class RateLimitCheckRequest(BaseModel):
    endpoint:   str
    client_key: str = "test_client"

class RateLimitResetRequest(BaseModel):
    endpoint:   Optional[str] = None
    client_key: Optional[str] = None

@router.get("", operation_id="rate_limits_list")
async def list_rate_limits():
    return {"rate_limits": get_all_limits(), "bfiu_ref": "BFIU Circular No. 29 - Section 7.1"}

@router.post("/check", operation_id="rate_limit_check")
async def check_limit(req: RateLimitCheckRequest):
    if req.endpoint not in RATE_LIMITS and req.endpoint != "default":
        raise HTTPException(400, f"Unknown endpoint: {req.endpoint!r}")
    result = check_rate_limit(req.endpoint, req.client_key)
    if not result["allowed"]:
        raise HTTPException(429, detail={
            "error": "RATE_LIMIT_EXCEEDED", "remaining": 0,
            "limit": result["limit"], "reset_at": result["reset_at"],
        })
    return result

@router.get("/stats", operation_id="rate_limit_stats")
async def rate_limit_stats():
    return get_stats()

@router.post("/reset", operation_id="rate_limit_reset")
async def reset_rate_limits(req: RateLimitResetRequest):
    reset_counters(req.endpoint, req.client_key)
    return {"success": True, "reset": {"endpoint": req.endpoint, "client_key": req.client_key}}
