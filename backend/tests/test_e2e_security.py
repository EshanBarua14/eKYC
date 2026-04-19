import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

class TestE2EFullFlow:
    def test_e2e_step1_consent_recorded(self):
        r = client.post("/api/v1/consent/record", json={
            "session_id":"e2e_sess_001","nid_hash":"e2e_hash_001",
            "institution_id":"inst_e2e","agent_id":"agent_e2e","channel":"AGENCY"})
        assert r.status_code == 201
        assert r.json()["consent"]["status"] == "GRANTED"

    def test_e2e_step2_consent_verified(self):
        client.post("/api/v1/consent/record", json={
            "session_id":"e2e_sess_002","nid_hash":"h2",
            "institution_id":"i","agent_id":"a","channel":"AGENCY"})
        r = client.post("/api/v1/consent/verify", json={"session_id":"e2e_sess_002"})
        assert r.status_code == 200
        assert r.json()["consent_verified"] is True

    def test_e2e_step3_ec_blocked_without_consent(self):
        r = client.post("/api/v1/consent/verify", json={"session_id":"e2e_no_consent_xyz"})
        assert r.status_code == 403
        assert r.json()["detail"]["error_code"] == "CONSENT_NOT_RECORDED"

    def test_e2e_step4_outcome_created(self):
        r = client.post("/api/v1/outcome/create", json={
            "session_id":"e2e_sess_003","verdict":"MATCHED","confidence":87.5,
            "risk_grade":"LOW","risk_score":4,"screening_result":"CLEAR",
            "full_name":"E2E Test Customer","agent_id":"agent_e2e"})
        assert r.status_code == 201
        assert r.json()["outcome"]["state"] == "PENDING"

    def test_e2e_step5_auto_routing_low_risk(self):
        client.post("/api/v1/outcome/create", json={
            "session_id":"e2e_sess_004","verdict":"MATCHED","confidence":87.5,
            "risk_grade":"LOW","screening_result":"CLEAR"})
        r = client.post("/api/v1/outcome/e2e_sess_004/auto-route")
        assert r.status_code == 200
        assert r.json()["outcome"]["state"] == "APPROVED"
        assert r.json()["auto_approved"] is True

    def test_e2e_step6_notification_sent(self):
        r = client.post("/api/v1/notify/kyc-success", json={
            "session_id":"e2e_sess_005","full_name":"E2E Test Customer",
            "mobile":"01712345678","email":"e2e@test.com",
            "account_number":"ACC-E2E-001","kyc_type":"SIMPLIFIED",
            "risk_grade":"LOW","confidence":87.5})
        assert r.status_code in (201, 200)

    def test_e2e_step7_pdf_generated(self):
        r = client.post("/api/v1/kyc/pdf/generate", json={
            "session_id":"e2e_sess_006","verdict":"MATCHED","confidence":87.5,
            "full_name":"E2E Test Customer","mobile":"01712345678",
            "risk_grade":"LOW","kyc_type":"SIMPLIFIED","status":"APPROVED"})
        assert r.status_code == 201
        assert r.json()["size_bytes"] > 1000

    def test_e2e_step8_bfiu_report(self):
        r = client.post("/api/v1/bfiu-report/generate",
                        json={"year":2026,"month":4})
        assert r.status_code == 201
        assert "section_7_summary" in r.json()["report"]


class TestE2EFallbackFlow:
    def test_fallback_triggered_on_ec_unavailable(self):
        r = client.post("/api/v1/fallback/create", json={
            "session_id":"e2e_fb_001","trigger_code":"NID_API_UNAVAILABLE",
            "kyc_type":"SIMPLIFIED","customer_name":"E2E Fallback Customer",
            "customer_mobile":"01712345678"})
        assert r.status_code == 201
        assert r.json()["case"]["status"] == "INITIATED"

    def test_fallback_outcome_state_set(self):
        client.post("/api/v1/outcome/create", json={
            "session_id":"e2e_fb_002","verdict":"MATCHED","confidence":87.5})
        r = client.post("/api/v1/outcome/e2e_fb_002/fallback",
                        json={"reason":"EC API unavailable"})
        assert r.status_code == 200
        assert r.json()["outcome"]["state"] == "FALLBACK_KYC"

    def test_failure_notification_sent(self):
        r = client.post("/api/v1/notify/kyc-failure", json={
            "session_id":"e2e_fb_003","mobile":"01712345678",
            "failed_step":"NID_VERIFICATION","reason":"EC server unavailable"})
        assert r.status_code in (201, 200)

    def test_cmi_bo_account_full_flow(self):
        r = client.post("/api/v1/cmi/bo/open", json={
            "session_id":"e2e_cmi_001","kyc_verdict":"MATCHED","confidence":87.5,
            "full_name":"E2E CMI Investor","nid_hash":"e2e_cmi_hash",
            "mobile":"01712345678","date_of_birth":"1990-01-15",
            "product_type":"BO_INDIVIDUAL","deposit_amount":500000,"risk_grade":"LOW"})
        assert r.status_code == 201
        assert r.json()["bo_account"]["status"] == "ACTIVE"
        assert r.json()["bo_account"]["bo_number"].startswith("1201")


class TestSecurityAccessControl:
    def test_nid_verify_requires_auth(self):
        r = client.post("/api/v1/nid/verify",
                        json={"nid_number":"1234567890123","session_id":"s1"})
        assert r.status_code == 403

    def test_risk_grade_requires_auth(self):
        r = client.post("/api/v1/risk/grade", json={"kyc_profile_id":"p1"})
        assert r.status_code == 403

    def test_audit_log_requires_auth(self):
        r = client.get("/api/v1/audit/log")
        assert r.status_code == 403

    def test_screening_requires_auth(self):
        r = client.post("/api/v1/screening/unscr",
                        json={"name":"Test","institution_id":"inst_01"})
        assert r.status_code == 403

    def test_lifecycle_requires_auth(self):
        r = client.get("/api/v1/lifecycle/due-reviews")
        assert r.status_code == 403


class TestSecurityJWT:
    def _h(self, token):
        return {"Authorization": f"Bearer {token}"}

    def test_invalid_jwt_rejected(self):
        r = client.get("/api/v1/audit/log", headers=self._h("invalid.jwt.token"))
        assert r.status_code in (401, 403)

    def test_tampered_jwt_rejected(self):
        fake = "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJoYWNrZXIifQ.invalidsig"
        r = client.get("/api/v1/audit/log", headers=self._h(fake))
        assert r.status_code in (401, 403)

    def test_empty_bearer_rejected(self):
        r = client.get("/api/v1/audit/log", headers=self._h(""))
        assert r.status_code in (403, 422)

    def test_no_bearer_scheme_rejected(self):
        r = client.get("/api/v1/audit/log",
                       headers={"Authorization": "Basic dXNlcjpwYXNz"})
        assert r.status_code == 403


class TestSecurityInjection:
    def test_sql_injection_in_session_id(self):
        r = client.post("/api/v1/consent/record", json={
            "session_id":"\'; DROP TABLE consents; --","nid_hash":"h",
            "institution_id":"i","agent_id":"a","channel":"AGENCY"})
        assert r.status_code != 500

    def test_xss_in_full_name(self):
        r = client.post("/api/v1/consent/record", json={
            "session_id":"xss_test_01",
            "nid_hash":"<script>alert(1)</script>",
            "institution_id":"i","agent_id":"a","channel":"AGENCY"})
        assert r.status_code != 500

    def test_oversized_payload_handled(self):
        r = client.post("/api/v1/consent/record", json={
            "session_id":"A"*5000,"nid_hash":"h",
            "institution_id":"i","agent_id":"a","channel":"AGENCY"})
        assert r.status_code != 500

    def test_path_traversal_in_report_id(self):
        r = client.get("/api/v1/bfiu-report/../../../etc/passwd")
        assert r.status_code in (404, 422)
        assert r.status_code != 500


class TestSecurityBusinessLogic:
    def test_cannot_open_bo_with_failed_verdict(self):
        r = client.post("/api/v1/cmi/bo/open", json={
            "session_id":"sec_bl_01","kyc_verdict":"FAILED","confidence":15.0,
            "full_name":"Hacker","nid_hash":"h",
            "mobile":"01700000000","date_of_birth":"1990-01-01"})
        assert r.status_code == 422

    def test_cannot_generate_pdf_with_invalid_verdict(self):
        r = client.post("/api/v1/kyc/pdf/generate", json={
            "session_id":"sec_bl_02","verdict":"HACKED","confidence":100.0})
        assert r.status_code == 400

    def test_consent_revoke_blocks_verify(self):
        client.post("/api/v1/consent/record", json={
            "session_id":"sec_bl_03","nid_hash":"h",
            "institution_id":"i","agent_id":"a","channel":"AGENCY"})
        client.post("/api/v1/consent/sec_bl_03/revoke")
        r = client.post("/api/v1/consent/verify", json={"session_id":"sec_bl_03"})
        assert r.status_code == 403

    def test_duplicate_outcome_rejected(self):
        client.post("/api/v1/outcome/create", json={
            "session_id":"sec_bl_04","verdict":"MATCHED","confidence":87.5})
        r = client.post("/api/v1/outcome/create", json={
            "session_id":"sec_bl_04","verdict":"MATCHED","confidence":87.5})
        assert r.status_code == 409


class TestSecurityMisconfiguration:
    def test_404_no_stack_trace(self):
        r = client.get("/api/v1/nonexistent-endpoint-xyz")
        assert r.status_code == 404
        assert "Traceback" not in r.text

    def test_health_endpoint_accessible(self):
        # Public health check — gateway health is unauthenticated
        r = client.get("/api/v1/gateway/health")
        assert r.status_code == 200

    def test_openapi_docs_accessible(self):
        r = client.get("/openapi.json")
        assert r.status_code == 200
        assert "paths" in r.json()


class TestSecurityAuthFailures:
    def test_login_wrong_password_returns_401(self):
        r = client.post("/api/v1/auth/token",
                        data={"username":"admin","password":"wrongpassword123"})
        assert r.status_code in (401, 422)

    def test_register_missing_fields_422(self):
        r = client.post("/api/v1/auth/register", json={})
        assert r.status_code == 422

    def test_auth_token_endpoint_exists(self):
        r = client.post("/api/v1/auth/token",
                        data={"username":"x","password":"y"})
        assert r.status_code != 404


class TestAuditTrail:
    def test_notification_log_persists(self):
        r = client.get("/api/v1/notify/log")
        assert r.status_code == 200
        assert "total" in r.json()

    def test_consent_records_ip_for_audit(self):
        r = client.post("/api/v1/consent/record", json={
            "session_id":"audit_consent_01","nid_hash":"h",
            "institution_id":"i","agent_id":"a","channel":"AGENCY"})
        assert r.status_code == 201
        c = r.json()["consent"]
        assert "ip_address" in c and "timestamp" in c

    def test_outcome_history_trail(self):
        client.post("/api/v1/outcome/create", json={
            "session_id":"audit_out_01","verdict":"MATCHED","confidence":87.5,
            "risk_grade":"LOW"})
        client.post("/api/v1/outcome/audit_out_01/auto-route")
        r = client.get("/api/v1/outcome/audit_out_01")
        history = r.json()["outcome"]["history"]
        assert len(history) >= 2
        states = [h["state"] for h in history]
        assert "PENDING" in states
