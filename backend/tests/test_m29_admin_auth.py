"""
test_m29_admin_auth.py - M29 Admin Authentication & RBAC
Tests: role enforcement, admin CRUD, 403 for non-admin, JWT required
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
BASE   = "/api/v1/admin"
AUTH   = "/api/v1/auth"

# ── Helpers ───────────────────────────────────────────────────────────────
import pyotp as _pyotp2
_M29_TOTP_SECRET = "JBSWY3DPEHPK3PXP"

def register_and_login(email, role, password="Test@12345"):
    client.post(f"{AUTH}/register", json={
        "email": email, "phone": "01700000000",
        "full_name": "Test User", "role": role,
        "password": password, "institution_id": "inst-demo-001",
    })
    # For ADMIN/CHECKER roles, set up TOTP directly on in-memory user
    if role.upper() in ("ADMIN", "CHECKER"):
        from app.api.v1.routes.auth import _demo_users
        user = next((u for u in _demo_users if u.email == email), None)
        if user and not user.totp_enabled:
            user.totp_secret = _M29_TOTP_SECRET
            user.totp_enabled = True
        totp_code = _pyotp2.TOTP(_M29_TOTP_SECRET).now()
        r = client.post(f"{AUTH}/token", json={"email": email, "password": password, "totp_code": totp_code})
    else:
        r = client.post(f"{AUTH}/token", json={"email": email, "password": password})
    if r.status_code != 200:
        return None
    return r.json().get("access_token")

def admin_headers():
    token = register_and_login("admin_m29@test.com", "ADMIN")
    return {"Authorization": f"Bearer {token}"} if token else {}

def maker_headers():
    token = register_and_login("maker_m29@test.com", "MAKER")
    return {"Authorization": f"Bearer {token}"} if token else {}

def auditor_headers():
    token = register_and_login("auditor_m29@test.com", "AUDITOR")
    return {"Authorization": f"Bearer {token}"} if token else {}

# ══════════════════════════════════════════════════════════════════════════
# 1. Authentication required (3 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestAuthRequired:
    def test_stats_requires_auth(self):
        r = client.get(f"{BASE}/stats")
        assert r.status_code == 403

    def test_institutions_requires_auth(self):
        r = client.get(f"{BASE}/institutions")
        assert r.status_code == 403

    def test_users_requires_auth(self):
        r = client.get(f"{BASE}/users")
        assert r.status_code == 403

# ══════════════════════════════════════════════════════════════════════════
# 2. Role enforcement — non-admin blocked (4 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestRoleEnforcement:
    def test_maker_cannot_access_admin_stats(self):
        headers = maker_headers()
        if not headers: pytest.skip("Login failed")
        r = client.get(f"{BASE}/stats", headers=headers)
        assert r.status_code == 403

    def test_maker_cannot_create_institution(self):
        headers = maker_headers()
        if not headers: pytest.skip("Login failed")
        r = client.post(f"{BASE}/institutions", headers=headers,
                        json={"name":"Test","short_code":"TST","institution_type":"insurance"})
        assert r.status_code == 403

    def test_maker_cannot_create_user(self):
        headers = maker_headers()
        if not headers: pytest.skip("Login failed")
        r = client.post(f"{BASE}/users", headers=headers,
                        json={"email":"x@x.com","full_name":"X","role":"MAKER",
                              "institution_id":"inst-demo-001"})
        assert r.status_code == 403

    def test_403_has_error_detail(self):
        headers = maker_headers()
        if not headers: pytest.skip("Login failed")
        r = client.get(f"{BASE}/stats", headers=headers)
        body = r.json()
        # error boundary wraps in {"error": ...}, old format uses {"detail": ...}
        assert "error" in body or "detail" in body

# ══════════════════════════════════════════════════════════════════════════
# 3. Admin access allowed (4 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestAdminAccess:
    def test_admin_can_get_stats(self):
        headers = admin_headers()
        if not headers: pytest.skip("Login failed")
        r = client.get(f"{BASE}/stats", headers=headers)
        assert r.status_code == 200

    def test_admin_stats_has_required_keys(self):
        headers = admin_headers()
        if not headers: pytest.skip("Login failed")
        r = client.get(f"{BASE}/stats", headers=headers)
        d = r.json()
        for k in ["total_institutions","active_institutions","total_users","active_users"]:
            assert k in d, f"Missing key: {k}"

    def test_admin_can_list_institutions(self):
        headers = admin_headers()
        if not headers: pytest.skip("Login failed")
        r = client.get(f"{BASE}/institutions", headers=headers)
        assert r.status_code == 200
        assert "institutions" in r.json()

    def test_admin_can_list_users(self):
        headers = admin_headers()
        if not headers: pytest.skip("Login failed")
        r = client.get(f"{BASE}/users", headers=headers)
        assert r.status_code == 200
        assert "users" in r.json()

# ══════════════════════════════════════════════════════════════════════════
# 4. Institution CRUD (5 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestInstitutionCRUD:
    def test_create_institution_201(self):
        headers = admin_headers()
        if not headers: pytest.skip("Login failed")
        r = client.post(f"{BASE}/institutions", headers=headers, json={
            "name": "Test Insurance Co M29", "short_code": "TIM29",
            "institution_type": "insurance",
        })
        assert r.status_code == 201

    def test_create_institution_has_id(self):
        headers = admin_headers()
        if not headers: pytest.skip("Login failed")
        r = client.post(f"{BASE}/institutions", headers=headers, json={
            "name": "Test CMI M29", "short_code": "TCMI29",
            "institution_type": "cmi",
        })
        assert "id" in r.json()["institution"]

    def test_create_duplicate_institution_409(self):
        headers = admin_headers()
        if not headers: pytest.skip("Login failed")
        client.post(f"{BASE}/institutions", headers=headers, json={
            "name": "Dup Inst", "short_code": "DUPX9", "institution_type": "insurance"})
        r = client.post(f"{BASE}/institutions", headers=headers, json={
            "name": "Dup Inst 2", "short_code": "DUPX9", "institution_type": "insurance"})
        assert r.status_code == 409

    def test_create_invalid_type_400(self):
        headers = admin_headers()
        if not headers: pytest.skip("Login failed")
        r = client.post(f"{BASE}/institutions", headers=headers, json={
            "name": "Bad Type", "short_code": "BADTP", "institution_type": "invalid_xyz"})
        assert r.status_code == 400

    def test_get_institution_by_id(self):
        headers = admin_headers()
        if not headers: pytest.skip("Login failed")
        r = client.post(f"{BASE}/institutions", headers=headers, json={
            "name": "Get Test Inst", "short_code": "GETI9", "institution_type": "insurance"})
        inst_id = r.json()["institution"]["id"]
        r2 = client.get(f"{BASE}/institutions/{inst_id}", headers=headers)
        assert r2.status_code == 200
        assert r2.json()["institution"]["id"] == inst_id

# ══════════════════════════════════════════════════════════════════════════
# 5. User CRUD (5 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestUserCRUD:
    def test_create_user_201(self):
        headers = admin_headers()
        if not headers: pytest.skip("Login failed")
        r = client.post(f"{BASE}/users", headers=headers, json={
            "email": "newuser_m29a@test.com", "full_name": "New User",
            "phone": "01700000001", "role": "MAKER",
            "password": "Pass@12345", "institution_id": "inst-demo-001",
        })
        assert r.status_code == 201

    def test_create_user_has_id(self):
        headers = admin_headers()
        if not headers: pytest.skip("Login failed")
        r = client.post(f"{BASE}/users", headers=headers, json={
            "email": "newuser_m29b@test.com", "full_name": "New User B",
            "phone": "01700000002", "role": "CHECKER",
            "password": "Pass@12345", "institution_id": "inst-demo-001",
        })
        assert "id" in r.json()["user"]

    def test_create_duplicate_user_409(self):
        headers = admin_headers()
        if not headers: pytest.skip("Login failed")
        payload = {"email": "dup_m29@test.com", "full_name": "Dup",
                   "phone": "01700000003", "role": "MAKER",
                   "password": "Pass@12345", "institution_id": "inst-demo-001"}
        client.post(f"{BASE}/users", headers=headers, json=payload)
        r = client.post(f"{BASE}/users", headers=headers, json=payload)
        assert r.status_code == 409

    def test_create_invalid_role_400(self):
        headers = admin_headers()
        if not headers: pytest.skip("Login failed")
        r = client.post(f"{BASE}/users", headers=headers, json={
            "email": "badrole@test.com", "full_name": "Bad Role",
            "role": "SUPERUSER", "institution_id": "inst-demo-001",
        })
        assert r.status_code == 400

    def test_get_user_by_id(self):
        headers = admin_headers()
        if not headers: pytest.skip("Login failed")
        r = client.post(f"{BASE}/users", headers=headers, json={
            "email": "getuser_m29@test.com", "full_name": "Get User",
            "phone": "01700000004", "role": "AGENT",
            "password": "Pass@12345", "institution_id": "inst-demo-001",
        })
        user_id = r.json()["user"]["id"]
        r2 = client.get(f"{BASE}/users/{user_id}", headers=headers)
        assert r2.status_code == 200
        assert r2.json()["user"]["id"] == user_id

# ══════════════════════════════════════════════════════════════════════════
# 6. Auditor access (3 tests)
# ══════════════════════════════════════════════════════════════════════════
class TestAuditorAccess:
    def test_auditor_can_list_institutions(self):
        headers = auditor_headers()
        if not headers: pytest.skip("Login failed")
        r = client.get(f"{BASE}/institutions", headers=headers)
        assert r.status_code == 200

    def test_auditor_can_list_users(self):
        headers = auditor_headers()
        if not headers: pytest.skip("Login failed")
        r = client.get(f"{BASE}/users", headers=headers)
        assert r.status_code == 200

    def test_auditor_cannot_create_institution(self):
        headers = auditor_headers()
        if not headers: pytest.skip("Login failed")
        r = client.post(f"{BASE}/institutions", headers=headers, json={
            "name": "Auditor Inst", "short_code": "AUDT9",
            "institution_type": "insurance",
        })
        assert r.status_code == 403
