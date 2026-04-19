"""v1 API router"""
from fastapi import APIRouter
from app.api.v1.routes.settings import router as settings_router
from app.api.v1.routes.face_verify  import router as face_router
from app.api.v1.routes.ai_analyze   import router as ai_router
from app.api.v1.routes.kyc_profile  import router as kyc_router
from app.api.v1.routes.fingerprint  import router as fingerprint_router
from app.api.v1.routes.auth         import router as auth_router
from app.api.v1.routes.nid          import router as nid_router
from app.api.v1.routes.risk         import router as risk_router
from app.api.v1.routes.onboarding   import router as onboarding_router
from app.api.v1.routes.screening    import router as screening_router
from app.api.v1.routes.lifecycle    import router as lifecycle_router
from app.api.v1.routes.audit        import router as audit_router
from app.api.v1.routes.gateway      import router as gateway_router
from app.api.v1.routes.admin        import router as admin_router
from app.api.v1.routes.compliance    import router as compliance_router
from app.api.v1.routes.kyc_pdf        import router as kyc_pdf_router
from app.api.v1.routes.consent         import router as consent_router
from app.api.v1.routes.notification     import router as notification_router
from app.api.v1.routes.outcome           import router as outcome_router
from app.api.v1.routes.fallback           import router as fallback_router
from app.api.v1.routes.cmi               import router as cmi_router
from app.api.v1.routes.bfiu_report        import router as bfiu_report_router
from app.api.v1.routes.notification     import router as notification_router
from app.api.v1.routes.outcome           import router as outcome_router
from app.api.v1.routes.fallback           import router as fallback_router
from app.api.v1.routes.cmi               import router as cmi_router
from app.api.v1.routes.bfiu_report        import router as bfiu_report_router

v1_router = APIRouter()
v1_router.include_router(auth_router)
v1_router.include_router(nid_router)
v1_router.include_router(risk_router)
v1_router.include_router(onboarding_router)
v1_router.include_router(screening_router)
v1_router.include_router(lifecycle_router)
v1_router.include_router(audit_router)
v1_router.include_router(gateway_router)
v1_router.include_router(face_router)
v1_router.include_router(ai_router)
v1_router.include_router(kyc_router)
v1_router.include_router(fingerprint_router)
v1_router.include_router(admin_router)
v1_router.include_router(compliance_router)
v1_router.include_router(kyc_pdf_router)
v1_router.include_router(consent_router)
v1_router.include_router(notification_router)
v1_router.include_router(outcome_router)
v1_router.include_router(fallback_router)
v1_router.include_router(cmi_router)
v1_router.include_router(bfiu_report_router)
v1_router.include_router(notification_router)
v1_router.include_router(outcome_router)
v1_router.include_router(fallback_router)
v1_router.include_router(cmi_router)
v1_router.include_router(bfiu_report_router)

v1_router.include_router(settings_router)
