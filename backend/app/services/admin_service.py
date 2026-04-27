"""
Admin Service - M29
Platform admin operations: institution CRUD, user management, thresholds.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional
from app.db.database import db_session
from app.db.models.auth import Institution, User
from app.services.auth_service import hash_password

def _now(): return datetime.now(timezone.utc)

# ── Institution management ───────────────────────────────────────────────
def create_institution(name: str, short_code: str, institution_type: str,
    ip_whitelist: list = None, status: str = "ACTIVE") -> dict:
    with db_session() as db:
        existing = db.query(Institution).filter_by(short_code=short_code).first()
        if existing:
            return {"error": f"Institution {short_code!r} already exists"}
        schema_name = f"tenant_{short_code.lower()}"
        client_id   = f"client_{short_code.lower()}_{str(uuid.uuid4())[:6]}"
        inst = Institution(
            id=str(uuid.uuid4()), name=name, short_code=short_code,
            institution_type=institution_type, schema_name=schema_name,
            client_id=client_id, client_secret_hash="pending",
            ip_whitelist=ip_whitelist or [], status=status,
            created_at=_now(), updated_at=_now(),
        )
        db.add(inst); db.flush()
        return _inst_dict(inst)

def list_institutions(status: str = None, limit: int = 50) -> list:
    with db_session() as db:
        q = db.query(Institution)
        if status: q = q.filter_by(status=status)
        return [_inst_dict(r) for r in q.limit(limit).all()]

def get_institution(institution_id: str) -> Optional[dict]:
    with db_session() as db:
        r = db.query(Institution).filter_by(id=institution_id).first()
        return _inst_dict(r) if r else None

def update_institution_status(institution_id: str, status: str) -> dict:
    with db_session() as db:
        r = db.query(Institution).filter_by(id=institution_id).first()
        if not r: return {"error": "Institution not found"}
        r.status = status; r.updated_at = _now()
        return _inst_dict(r)

def _inst_dict(r) -> dict:
    return {"id": r.id, "name": r.name, "short_code": r.short_code,
            "institution_type": r.institution_type, "schema_name": r.schema_name,
            "client_id": r.client_id, "status": r.status,
            "ip_whitelist": r.ip_whitelist or [],
            "created_at": str(r.created_at)}

# ── User management ──────────────────────────────────────────────────────
def create_admin_user(email: str, full_name: str, phone: str,
    role: str, password: str, institution_id: str) -> dict:
    with db_session() as db:
        existing = db.query(User).filter_by(email=email).first()
        if existing: return {"error": f"Email {email!r} already registered"}
        # Ensure institution exists (create stub if needed for dev/test)
        inst = db.query(Institution).filter_by(id=institution_id).first()
        if not inst:
            inst = Institution(
                id=institution_id, name="Demo Institution",
                short_code=f"DEMO_{institution_id[-4:].upper()}",
                institution_type="insurance",
                schema_name=f"tenant_demo_{institution_id[-4:]}",
                client_id=f"client_{institution_id[-8:]}",
                client_secret_hash="demo", status="ACTIVE",
                created_at=_now(), updated_at=_now(),
            )
            db.add(inst); db.flush()
        user = User(
            id=str(uuid.uuid4()), institution_id=institution_id,
            email=email, phone=phone, full_name=full_name,
            role=role.upper(), password_hash=hash_password(password),
            totp_enabled=False, is_active=True, failed_login_count=0,
            created_at=_now(), updated_at=_now(),
        )
        db.add(user); db.flush()
        return _user_dict(user)

def list_users(institution_id: str = None, role: str = None, limit: int = 50) -> list:
    with db_session() as db:
        q = db.query(User)
        if institution_id: q = q.filter_by(institution_id=institution_id)
        if role: q = q.filter_by(role=role.upper())
        return [_user_dict(r) for r in q.limit(limit).all()]

def get_user(user_id: str) -> Optional[dict]:
    with db_session() as db:
        r = db.query(User).filter_by(id=user_id).first()
        return _user_dict(r) if r else None

def deactivate_user(user_id: str) -> dict:
    with db_session() as db:
        r = db.query(User).filter_by(id=user_id).first()
        if not r: return {"error": "User not found"}
        r.is_active = False; r.updated_at = _now()
        return _user_dict(r)

def update_user_role(user_id: str, new_role: str) -> dict:
    with db_session() as db:
        r = db.query(User).filter_by(id=user_id).first()
        if not r: return {"error": "User not found"}
        r.role = new_role.upper(); r.updated_at = _now()
        return _user_dict(r)

def _user_dict(r) -> dict:
    return {"id": r.id, "email": r.email, "full_name": r.full_name,
            "role": r.role, "phone": r.phone,
            "institution_id": r.institution_id,
            "is_active": r.is_active,
            "totp_enabled": r.totp_enabled,
            "created_at": str(r.created_at)}

# ── Platform stats ───────────────────────────────────────────────────────
def get_platform_stats() -> dict:
    with db_session() as db:
        total_institutions = db.query(Institution).count()
        active_institutions = db.query(Institution).filter_by(status="ACTIVE").count()
        total_users = db.query(User).count()
        active_users = db.query(User).filter_by(is_active=True).count()
        try:
            from app.db.models import PEPEntry
            total_pep = db.query(PEPEntry).count()
        except Exception:
            total_pep = 0
        try:
            from app.db.models import KYCSession
            total_sessions = db.query(KYCSession).count()
        except Exception:
            total_sessions = 0
    return {
        "total_institutions":  total_institutions,
        "active_institutions": active_institutions,
        "total_users":         total_users,
        "active_users":        active_users,
        "total_pep":           total_pep,
        "total_sessions":      total_sessions,
        "bfiu_ref":            "BFIU Circular No. 29",
    }
