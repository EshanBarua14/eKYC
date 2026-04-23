"""
M38 - Beneficial Ownership Tests - BFIU Circular No. 29 s4.2
"""
import pytest, uuid
from fastapi.testclient import TestClient
from app.main import app
from app.db.database import db_session
from app.db.models import KYCProfile, BeneficialOwner, BODeclaration

client = TestClient(app)

@pytest.fixture(scope="module")
def auth_token():
    import pyotp
    from app.api.v1.routes.auth import _demo_users
    from app.db.database import SessionLocal
    from app.db.models import User as UserModel
    _S = "JBSWY3DPEHPK3PXP"
    # ensure user in _demo_users with TOTP
    u = next((x for x in _demo_users if x.email == "admin@demo.ekyc"), None)
    if u is None:
        _db = SessionLocal()
        u = _db.query(UserModel).filter_by(email="admin@demo.ekyc").first()
        _db.close()
        if u:
            _db2 = SessionLocal()
            _db2.query(UserModel).filter_by(email="admin@demo.ekyc").update(
                {"totp_secret": _S, "totp_enabled": True})
            _db2.commit(); _db2.close()
            u.totp_secret = _S; u.totp_enabled = True
            _demo_users.append(u)
    if u and not u.totp_enabled:
        u.totp_secret = _S; u.totp_enabled = True
    r = client.post("/api/v1/auth/token", json={
        "email": "admin@demo.ekyc", "password": "AdminDemo@2026",
        "totp_code": pyotp.TOTP(_S).now()})
    assert r.status_code == 200, f"Auth failed: {r.text}"
    return r.json()["access_token"]

@pytest.fixture(scope="module")
def headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}

@pytest.fixture(scope="module")
def session_id():
    sid = f"test_m38_{uuid.uuid4().hex[:8]}"
    with db_session() as db:
        db.add(KYCProfile(session_id=sid, institution_id="inst-demo-001",
            kyc_type="Regular", status="PENDING", verdict="PASS", confidence=0.99,
            full_name="Test BO Corp", date_of_birth="1990-01-01", mobile="01700000000"))
    yield sid
    with db_session() as db:
        db.query(BODeclaration).filter_by(session_id=sid).delete()
        db.query(BeneficialOwner).filter_by(session_id=sid).delete()
        db.query(KYCProfile).filter_by(session_id=sid).delete()

@pytest.fixture(scope="module")
def bo_id(session_id, headers):
    r = client.post("/api/v1/kyc/beneficial-owner", json={
        "session_id": session_id, "full_name": "Rahim Uddin",
        "nid_number": "9876543210", "date_of_birth": "1980-01-01",
        "ownership_type": "direct", "ownership_pct": 55.0,
        "source_of_funds": "Business income"}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["beneficial_owner"]["id"]

def test_create_bo(session_id, headers):
    r = client.post("/api/v1/kyc/beneficial-owner", json={
        "session_id": session_id, "full_name": "Karim Sheikh",
        "ownership_type": "indirect", "ownership_pct": 30.0}, headers=headers)
    assert r.status_code == 201
    assert r.json()["beneficial_owner"]["session_id"] == session_id
    assert "bfiu_ref" in r.json()

def test_create_bo_invalid_type(session_id, headers):
    r = client.post("/api/v1/kyc/beneficial-owner", json={
        "session_id": session_id, "full_name": "Bad",
        "ownership_type": "invalid"}, headers=headers)
    assert r.status_code == 422

def test_create_bo_missing_session(headers):
    r = client.post("/api/v1/kyc/beneficial-owner", json={
        "session_id": "nonexistent_xyz", "full_name": "Ghost",
        "ownership_type": "direct"}, headers=headers)
    assert r.status_code == 404

def test_list_bos(session_id, bo_id, headers):
    r = client.get(f"/api/v1/kyc/beneficial-owner/{session_id}", headers=headers)
    assert r.status_code == 200
    d = r.json()
    assert d["count"] >= 1
    assert any(b["id"] == bo_id for b in d["beneficial_owners"])

def test_declaration_false_no_bos(headers):
    fresh = f"test_m38_fresh_{uuid.uuid4().hex[:8]}"
    with db_session() as db:
        db.add(KYCProfile(session_id=fresh, institution_id="inst-demo-001",
            kyc_type="Regular", status="PENDING", verdict="PASS", confidence=0.99,
            full_name="Fresh Corp", date_of_birth="1990-01-01", mobile="01700000000"))
    r = client.post("/api/v1/kyc/beneficial-owner/declaration",
        json={"session_id": fresh, "has_beneficial_owner": False}, headers=headers)
    assert r.status_code == 201
    assert r.json()["has_beneficial_owner"] == False
    with db_session() as db:
        db.query(BODeclaration).filter_by(session_id=fresh).delete()
        db.query(KYCProfile).filter_by(session_id=fresh).delete()

def test_declaration_true_without_bos(headers):
    fresh = f"test_m38_nodecl_{uuid.uuid4().hex[:8]}"
    with db_session() as db:
        db.add(KYCProfile(session_id=fresh, institution_id="inst-demo-001",
            kyc_type="Regular", status="PENDING", verdict="PASS", confidence=0.99,
            full_name="No BO Corp", date_of_birth="1990-01-01", mobile="01700000000"))
    r = client.post("/api/v1/kyc/beneficial-owner/declaration",
        json={"session_id": fresh, "has_beneficial_owner": True}, headers=headers)
    assert r.status_code == 400
    with db_session() as db:
        db.query(KYCProfile).filter_by(session_id=fresh).delete()

def test_declaration_submit(session_id, bo_id, headers):
    r = client.post("/api/v1/kyc/beneficial-owner/declaration", json={
        "session_id": session_id, "has_beneficial_owner": True,
        "declaration_text": "All BOs disclosed per BFIU s4.2"}, headers=headers)
    assert r.status_code == 201
    assert r.json()["has_beneficial_owner"] == True
    assert "declaration_id" in r.json()

def test_compliance_status(session_id, bo_id, headers):
    r = client.get(f"/api/v1/kyc/beneficial-owner/compliance-status/{session_id}", headers=headers)
    assert r.status_code == 200
    d = r.json()
    assert "bo_check_complete" in d
    assert d["beneficial_owners"] >= 1

def test_delete_bo(session_id, headers):
    r = client.post("/api/v1/kyc/beneficial-owner", json={
        "session_id": session_id, "full_name": "Delete Me",
        "ownership_type": "other"}, headers=headers)
    assert r.status_code == 201
    bid = r.json()["beneficial_owner"]["id"]
    r2 = client.delete(f"/api/v1/kyc/beneficial-owner/record/{bid}", headers=headers)
    assert r2.status_code == 200
    assert r2.json()["deleted"] == True

def test_delete_nonexistent(headers):
    r = client.delete("/api/v1/kyc/beneficial-owner/record/nonexistent-xyz", headers=headers)
    assert r.status_code == 404

def test_unauthenticated():
    r = client.get("/api/v1/kyc/beneficial-owner/some_session")
    assert r.status_code == 403
