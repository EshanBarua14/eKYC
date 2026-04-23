"""
M7 - Maker-Checker Workflow Tests
BFIU Circular No. 29 - dual-control requirement
"""
import pytest
from fastapi.testclient import TestClient
from tests.test_helpers import setup_totp_and_login


class TestMakerCheckerService:
    def setup_method(self):
        from app.services.maker_checker_service import (
            submit_maker_action, checker_decide,
            get_pending_actions, get_action,
            reset_maker_checker, MAKER_CHECKER_OPERATIONS,
        )
        self.submit   = submit_maker_action
        self.decide   = checker_decide
        self.pending  = get_pending_actions
        self.get      = get_action
        self.reset    = reset_maker_checker
        self.ops      = MAKER_CHECKER_OPERATIONS
        self.reset()

    def _submit(self, operation="KYC_UPGRADE", maker_id="maker-001"):
        return self.submit(
            operation      = operation,
            maker_id       = maker_id,
            maker_role     = "MAKER",
            entity_id      = "cust-123",
            entity_type    = "KYC_PROFILE",
            payload        = {"reason": "test"},
            institution_id = "inst-001",
        )

    def test_submit_valid_operation(self):
        r = self._submit()
        assert r["success"] is True
        assert r["status"] == "PENDING"
        assert "action_id" in r

    def test_submit_invalid_operation_fails(self):
        r = self.submit(
            operation="INVALID_OP", maker_id="m1", maker_role="MAKER",
            entity_id="e1", entity_type="X", payload={}, institution_id="i1",
        )
        assert r["success"] is False

    def test_pending_list_grows(self):
        self._submit("KYC_UPGRADE")
        self._submit("RISK_OVERRIDE")
        assert len(self.pending()) == 2

    def test_filter_by_institution(self):
        self._submit()
        assert len(self.pending("inst-001")) == 1
        assert len(self.pending("inst-999")) == 0

    def test_checker_approves(self):
        r = self._submit()
        d = self.decide(r["action_id"], "checker-001", "CHECKER", "APPROVED", "looks good")
        assert d["success"] is True
        assert d["status"] == "APPROVED"

    def test_checker_rejects(self):
        r = self._submit()
        d = self.decide(r["action_id"], "checker-001", "CHECKER", "REJECTED", "insufficient docs")
        assert d["success"] is True
        assert d["status"] == "REJECTED"

    def test_checker_cannot_be_maker(self):
        r = self._submit(maker_id="same-user")
        d = self.decide(r["action_id"], "same-user", "CHECKER", "APPROVED")
        assert d["success"] is False

    def test_invalid_decision_fails(self):
        r = self._submit()
        d = self.decide(r["action_id"], "checker-001", "CHECKER", "MAYBE")
        assert d["success"] is False

    def test_double_decide_fails(self):
        r = self._submit()
        self.decide(r["action_id"], "checker-001", "CHECKER", "APPROVED")
        d = self.decide(r["action_id"], "checker-002", "CHECKER", "APPROVED")
        assert d["success"] is False

    def test_approved_moves_to_completed(self):
        r = self._submit()
        aid = r["action_id"]
        self.decide(aid, "checker-001", "CHECKER", "APPROVED")
        assert len(self.pending()) == 0
        action = self.get(aid)
        assert action["status"] == "APPROVED"

    def test_get_nonexistent_returns_none(self):
        assert self.get("nonexistent-id") is None

    def test_all_operations_defined(self):
        expected = {
            "ACCOUNT_CLOSURE", "KYC_UPGRADE", "RISK_OVERRIDE",
            "USER_ROLE_CHANGE", "THRESHOLD_UPDATE", "EDD_WAIVER",
            "INSTITUTION_SUSPEND",
        }
        assert expected == self.ops


class TestMakerCheckerAPI:
    def setup_method(self):
        from app.main import app
        from app.services.maker_checker_service import reset_maker_checker
        reset_maker_checker()
        self.client = TestClient(app)
        token = setup_totp_and_login(self.client, email="admin_mc@example.com", role="ADMIN")
        self.headers = {"Authorization": f"Bearer {token}"}

    def test_list_operations(self):
        r = self.client.get("/api/v1/maker-checker/operations", headers=self.headers)
        assert r.status_code == 200
        data = r.json()
        assert "operations" in data
        assert "KYC_UPGRADE" in data["operations"]
        assert data["sla_hours"] == 24

    def test_submit_action(self):
        r = self.client.post("/api/v1/maker-checker/submit", json={
            "operation":      "KYC_UPGRADE",
            "entity_id":      "cust-123",
            "entity_type":    "KYC_PROFILE",
            "payload":        {"reason": "annual review"},
            "institution_id": "inst-001",
        }, headers=self.headers)
        assert r.status_code == 201
        data = r.json()
        assert data["success"] is True
        assert data["status"] == "PENDING"
        assert "action_id" in data

    def test_submit_invalid_operation_422(self):
        r = self.client.post("/api/v1/maker-checker/submit", json={
            "operation":   "INVALID_OP",
            "entity_id":   "cust-123",
            "entity_type": "KYC_PROFILE",
            "payload":     {},
        }, headers=self.headers)
        assert r.status_code == 422

    def test_pending_list(self):
        self.client.post("/api/v1/maker-checker/submit", json={
            "operation": "RISK_OVERRIDE", "entity_id": "e1",
            "entity_type": "KYC_PROFILE", "payload": {},
        }, headers=self.headers)
        r = self.client.get("/api/v1/maker-checker/pending", headers=self.headers)
        assert r.status_code == 200
        data = r.json()
        assert data["pending_count"] == 1
        assert data["sla_hours"] == 24

    def test_get_action_detail(self):
        sub = self.client.post("/api/v1/maker-checker/submit", json={
            "operation": "KYC_UPGRADE", "entity_id": "e1",
            "entity_type": "KYC_PROFILE", "payload": {},
        }, headers=self.headers)
        aid = sub.json()["action_id"]
        r = self.client.get(f"/api/v1/maker-checker/action/{aid}", headers=self.headers)
        assert r.status_code == 200
        assert r.json()["action_id"] == aid

    def test_get_nonexistent_action_404(self):
        r = self.client.get("/api/v1/maker-checker/action/nonexistent", headers=self.headers)
        assert r.status_code == 404

    def test_decide_action(self):
        sub = self.client.post("/api/v1/maker-checker/submit", json={
            "operation": "KYC_UPGRADE", "entity_id": "e1",
            "entity_type": "KYC_PROFILE", "payload": {},
        }, headers=self.headers)
        aid = sub.json()["action_id"]
        # Different user decides — use second token via different sub claim
        # In test env same user, expect same-user checker block
        r = self.client.post("/api/v1/maker-checker/decide", json={
            "action_id": aid,
            "decision":  "APPROVED",
            "note":      "verified",
        }, headers=self.headers)
        # Same user = maker == checker -> 422
        assert r.status_code == 422

    def test_unauthenticated_submit_fails(self):
        r = self.client.post("/api/v1/maker-checker/submit", json={
            "operation": "KYC_UPGRADE", "entity_id": "e1",
            "entity_type": "KYC_PROFILE", "payload": {},
        })
        assert r.status_code == 403
