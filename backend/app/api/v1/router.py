"""
v1 API router — all modules registered here
"""
from fastapi import APIRouter
from app.api.v1.routes.face_verify import router as face_router
from app.api.v1.routes.ai_analyze  import router as ai_router

# Future modules:
# from app.api.v1.routes.fingerprint import router as fingerprint_router
# from app.api.v1.routes.risk_grading import router as risk_router
# from app.api.v1.routes.sanctions   import router as sanctions_router
# from app.api.v1.routes.kyc_profile  import router as kyc_router

v1_router = APIRouter()
v1_router.include_router(face_router)
v1_router.include_router(ai_router)
