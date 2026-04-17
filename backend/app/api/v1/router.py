"""v1 API router"""
from fastapi import APIRouter
from app.api.v1.routes.face_verify   import router as face_router
from app.api.v1.routes.ai_analyze    import router as ai_router
from app.api.v1.routes.kyc_profile   import router as kyc_router
from app.api.v1.routes.fingerprint   import router as fingerprint_router

v1_router = APIRouter()
v1_router.include_router(face_router)
v1_router.include_router(ai_router)
v1_router.include_router(kyc_router)
v1_router.include_router(fingerprint_router)
