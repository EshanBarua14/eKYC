"""
Shared test helpers - TOTP-aware admin login
Used by test files that need ADMIN/CHECKER JWT tokens.
"""
import pyotp

_TEST_TOTP_SECRET = "JBSWY3DPEHPK3PXP"

def setup_totp_and_login(client, email, role, password="Admin@12345",
                          auth_base="/api/v1/auth"):
    """Register user, set up TOTP if needed, return access token."""
    client.post(f"{auth_base}/register", json={
        "email": email, "phone": "01700000000",
        "full_name": f"Test {role}", "role": role,
        "password": password, "institution_id": "inst-demo-001",
    })
    if role.upper() in ("ADMIN", "CHECKER"):
        # Set TOTP on in-memory user; fall back to DB if 409 (already registered)
        from app.api.v1.routes.auth import _demo_users
        user = next((u for u in _demo_users if u.email == email), None)
        if user is None:
            try:
                from app.db.database import SessionLocal
                from app.db.models import User as UserModel
                _db = SessionLocal()
                db_user = _db.query(UserModel).filter_by(email=email).first()
                _db.close()
                if db_user:
                    db_user.totp_secret = _TEST_TOTP_SECRET
                    _db2 = SessionLocal()
                    _db2.query(UserModel).filter_by(email=email).update(
                        {"totp_secret": _TEST_TOTP_SECRET, "totp_enabled": True})
                    _db2.commit(); _db2.close()
                    _demo_users.append(db_user)
                    user = db_user
            except Exception as e:
                print(f"[test_helpers] DB fallback error: {e}")
        if user and not user.totp_enabled:
            user.totp_secret = _TEST_TOTP_SECRET
            user.totp_enabled = True
        totp_code = pyotp.TOTP(_TEST_TOTP_SECRET).now()
        r = client.post(f"{auth_base}/token", json={
            "email": email, "password": password, "totp_code": totp_code})
    else:
        r = client.post(f"{auth_base}/token", json={
            "email": email, "password": password})
    return r.json().get("access_token", "") if r.status_code == 200 else ""
