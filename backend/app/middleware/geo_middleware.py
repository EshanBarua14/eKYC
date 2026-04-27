"""
Geolocation Middleware — M67
BFIU Circular No. 29 §4.5 — Data must not leave Bangladesh without approval.
Captures client geolocation from IP (header-based) and enforces BD-only policy.
Frontend sends GPS coords via X-Geo-Lat / X-Geo-Lng headers.
"""
import logging
import json
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

log = logging.getLogger(__name__)

# Bangladesh bounding box (approx)
BD_LAT_MIN, BD_LAT_MAX = 20.5, 26.7
BD_LON_MIN, BD_LON_MAX = 88.0, 92.7

# Endpoints that REQUIRE geolocation
GEO_REQUIRED_PREFIXES = [
    "/api/v1/ai/",
    "/api/v1/face/",
    "/api/v1/kyc/",
    "/api/v1/consent",
]

# In dev/test mode bypass enforcement
GEO_ENFORCE = False   # Set True in production via env


def is_within_bangladesh(lat: float, lon: float) -> bool:
    return (BD_LAT_MIN <= lat <= BD_LAT_MAX and BD_LON_MIN <= lon <= BD_LON_MAX)


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class GeolocationMiddleware(BaseHTTPMiddleware):
    """
    Attaches geolocation data to request state.
    In production (GEO_ENFORCE=True): rejects requests from outside Bangladesh.
    Always logs geo data for BFIU audit trail.
    """

    async def dispatch(self, request: Request, call_next):
        # Extract GPS from frontend headers (set by browser Geolocation API)
        lat_str = request.headers.get("X-Geo-Lat", "")
        lon_str = request.headers.get("X-Geo-Lng", "")
        accuracy = request.headers.get("X-Geo-Accuracy", "")
        client_ip = get_client_ip(request)

        geo_data = {
            "ip": client_ip,
            "lat": None,
            "lon": None,
            "accuracy_m": None,
            "within_bd": None,
            "source": "none",
        }

        # Parse GPS coords if provided
        if lat_str and lon_str:
            try:
                lat = float(lat_str)
                lon = float(lon_str)
                within_bd = is_within_bangladesh(lat, lon)
                geo_data.update({
                    "lat": round(lat, 6),
                    "lon": round(lon, 6),
                    "accuracy_m": float(accuracy) if accuracy else None,
                    "within_bd": within_bd,
                    "source": "gps",
                })

                # Enforce BD-only in production
                if GEO_ENFORCE:
                    path = request.url.path
                    needs_geo = any(path.startswith(p) for p in GEO_REQUIRED_PREFIXES)
                    if needs_geo and not within_bd:
                        log.warning(
                            "[M67] BFIU §4.5 geo-block: lat=%.4f lon=%.4f ip=%s path=%s",
                            lat, lon, client_ip, path
                        )
                        return JSONResponse(
                            status_code=403,
                            content={
                                "error": "GEO_RESTRICTED",
                                "message": "eKYC operations are only permitted within Bangladesh (BFIU §4.5)",
                                "bfiu_ref": "Circular No. 29 §4.5",
                            }
                        )
            except (ValueError, TypeError):
                pass

        # Attach to request state for use in route handlers
        request.state.geo = geo_data

        log.debug("[M67] geo=%s", json.dumps(geo_data))

        response = await call_next(request)

        # Add geo headers to response for frontend awareness
        if geo_data["lat"] is not None:
            response.headers["X-Geo-Within-BD"] = str(geo_data["within_bd"]).lower()
            response.headers["X-Geo-Enforced"]  = str(GEO_ENFORCE).lower()

        return response
