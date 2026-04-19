"""
Rate Limit FastAPI Dependency - M28
Use as: Depends(rate_limit("face_verify"))
Returns 429 if limit exceeded.
"""
import time
from fastapi import HTTPException, Request
from app.services.rate_limiter import check_rate_limit

def rate_limit(endpoint: str):
    """
    Factory that returns a FastAPI dependency for the given endpoint.
    Usage: @router.post("/foo", dependencies=[Depends(rate_limit("face_verify"))])
    """
    def _check(request: Request):
        client_ip = request.client.host if request.client else "unknown"
        result = check_rate_limit(endpoint, client_ip)
        if not result["allowed"]:
            raise HTTPException(
                status_code=429,
                detail={
                    "error":     "RATE_LIMIT_EXCEEDED",
                    "message":   f"Too many requests. Limit: {result['limit']} per {result['window_seconds']}s.",
                    "limit":     result["limit"],
                    "remaining": 0,
                    "reset_at":  result["reset_at"],
                    "bfiu_ref":  "BFIU Circular No. 29 - Section 7.1",
                },
                headers={"Retry-After": str(int(result["reset_at"] - time.time()))},
            )
        return result
    return _check
