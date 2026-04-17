"""
M11 - Audit Trail and Reporting Tests
Tests: immutable log, event types, query, export, dashboard, maker-checker, API
"""
import pytest
from fastapi.testclient import TestClient


class TestAuditLog:
    def setup_method(self):
        from app.services.audit_service import (
            log_event, get_entry, query_log,
            reset_audit_log, AUDIT_EVENTS, RETENTION_YEARS,
        )
        self.log    = log_event
        self.get    = get_entry
        self.query  = query_log
        self.reset  = reset_audit_log
        self.EVENTS = AUDIT_EVENTS
        self.RETAIN = RETENTION_YEARS
        self.reset()

    def test_retention_years_is_5(self):
        assert self.RETAIN == 5

    def test_log_returns_entry(self):
        e = self.log("USER_CREATED", "User", actor_id="user-001")
        assert "id" in e
        assert e["event_type"] == "USER_CREATED"

    def test_entry_has_uuid(self):
        e = self.log("AUTH_LOGIN_SUCCESS", "User")
        assert len(e["id"]) == 36

    def test_entry_has_retention_date(self):
        e = self.log("USER_CREATED", "User")
        assert "retention_until" in e

    def test_entry_has_bfiu_ref(self):
        e = self.log("USER_CREATED", "User")
        assert "5.1" in e["bfiu_ref"]

    def test_invalid_event_type_raises(self):
        with pytest.raises(ValueError):
            self.log("INVALID_EVENT", "User")

    def test_get_entry_by_id(self):
        e  = self.log("USER_CREATED", "User")
        e2 = self.get(e["id"])
        assert e2["id"] == e["id"]

    def test_get_unknown_entry_returns_none(self):
        assert self.get("nonexistent-id") is None

    def test_query_by_event_type(self):
        self.log("USER_CREATED", "User")
        self.log("AUTH_LOGIN_SUCCESS", "User")
        r = self.query(event_type="USER_CREATED")
        assert all(e["event_type"] == "USER_CREATED" for e in r["entries"])

    def test_query_returns_total(self):
        self.log("USER_CREATED", "User")
        self.log("USER_CREATED", "User")
        r = self.query(event_type="USER_CREATED")
        assert r["total"] >= 2

    def test_log_is_append_only(self):
        e1 = self.log("USER_CREATED", "User")
        e2 = self.log("AUTH_LOGIN_SUCCESS", "User")
        r  = self.query()
        assert r["total"] == 2

    def test_before_after_state_stored(self):
        e = self.log(
            "USER_ROLE_CHANGED", "User",
            before_state={"role": "MAKER"},
            after_state={"role": "CHECKER"},
        )
        assert e["before_state"]["role"] == "MAKER"
        assert e["after_state"]["role"]  == "CHECKER"

    def test_query_by_actor_id(self):
        self.log("USER_CREATED", "User", actor_id="admin-001")
        self.log("USER_CREATED", "User", actor_id="admin-002")
        r = self.query(actor_id="admin-001")
        assert all(e["actor_id"] == "admin-001" for e in r["entries"])

    def test_event_types_count(self):
        assert len(self.EVENTS) >= 30


class TestExport:
    def setup_method(self):
        from app.services.audit_service import (
            log_event, export_json, export_csv, reset_audit_log
        )
        self.log        = log_event
        self.export_json = export_json
        self.export_csv  = export_csv
        self.reset      = reset_audit_log
        self.reset()
        self.log("USER_CREATED", "User", institution_id="inst-001")
        self.log("AUTH_LOGIN_SUCCESS", "User", institution_id="inst-001")

    def test_json_export_is_string(self):
        r = self.export_json()
        assert isinstance(r, str)

    def test_json_export_has_bfiu_ref(self):
        import json
        r = json.loads(self.export_json())
        assert "bfiu_ref" in r

    def test_json_export_has_entries(self):
        import json
        r = json.loads(self.export_json())
        assert "entries" in r
        assert len(r["entries"]) >= 2

    def test_csv_export_is_string(self):
        r = self.export_csv()
        assert isinstance(r, str)

    def test_csv_has_header_row(self):
        r = self.export_csv()
        first_line = r.splitlines()[0]
        assert "event_type" in first_line

    def test_institution_filter_json(self):
        import json
        self.log("USER_CREATED", "User", institution_id="inst-002")
        r = json.loads(self.export_json(institution_id="inst-001"))
        assert all(
            e.get("institution_id") == "inst-001"
            for e in r["entries"]
        )


class TestDashboard:
    def setup_method(self):
        from app.services.audit_service import (
            log_event, get_dashboard_stats, reset_audit_log
        )
        self.log       = log_event
        self.dashboard = get_dashboard_stats
        self.reset     = reset_audit_log
        self.reset()

    def test_dashboard_has_required_keys(self):
        r = self.dashboard()
        assert "total_events" in r
        assert "face_verify_matched" in r
        assert "screening_blocked" in r
        assert "edd_triggered" in r

    def test_dashboard_counts_events(self):
        self.log("FACE_VERIFY_MATCHED", "VerificationResult")
        self.log("FACE_VERIFY_MATCHED", "VerificationResult")
        self.log("EDD_TRIGGERED",        "KYCProfile")
        r = self.dashboard()
        assert r["face_verify_matched"] == 2
        assert r["edd_triggered"] == 1

    def test_dashboard_institution_filter(self):
        self.log("SCREENING_BLOCKED", "KYCProfile", institution_id="inst-A")
        self.log("SCREENING_BLOCKED", "KYCProfile", institution_id="inst-B")
        r = self.dashboard(institution_id="inst-A")
        assert r["screening_blocked"] == 1


class TestMakerChecker:
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
        self.OPS      = MAKER_CHECKER_OPERATIONS
        self.reset()

    def _submit(self, operation="ACCOUNT_CLOSURE"):
        return self.submit(
            operation, "maker-001", "MAKER",
            "entity-001", "KYCProfile",
            {"reason": "test"}, "inst-001",
        )

    def test_submit_returns_action_id(self):
        r = self._submit()
        assert r["success"] is True
        assert "action_id" in r

    def test_submit_status_pending(self):
        r = self._submit()
        assert r["status"] == "PENDING"

    def test_invalid_operation_fails(self):
        r = self.submit("INVALID_OP", "maker-001", "MAKER",
                        "e-001", "KYCProfile", {}, "inst-001")
        assert r["success"] is False

    def test_checker_approves(self):
        action = self._submit()
        r = self.decide(action["action_id"], "checker-001", "CHECKER", "APPROVED")
        assert r["success"] is True
        assert r["status"] == "APPROVED"

    def test_checker_rejects(self):
        action = self._submit()
        r = self.decide(action["action_id"], "checker-001", "CHECKER", "REJECTED", "Not valid")
        assert r["success"] is True
        assert r["status"] == "REJECTED"

    def test_maker_cannot_be_checker(self):
        action = self._submit()
        r = self.decide(action["action_id"], "maker-001", "MAKER", "APPROVED")
        assert r["success"] is False

    def test_decide_twice_fails(self):
        action = self._submit()
        self.decide(action["action_id"], "checker-001", "CHECKER", "APPROVED")
        r = self.decide(action["action_id"], "checker-002", "CHECKER", "APPROVED")
        assert r["success"] is False

    def test_pending_list(self):
        self._submit()
        p = self.pending()
        assert len(p) >= 1

    def test_operations_include_closure(self):
        assert "ACCOUNT_CLOSURE" in self.OPS

    def test_operations_include_upgrade(self):
        assert "KYC_UPGRADE" in self.OPS


class TestAuditAPI:
    def setup_method(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from app.main import app
        self.client = TestClient(app)
        import app.api.v1.routes.auth as auth_module
        auth_module._demo_users.clear()
        self.client.post("/api/v1/auth/register", json={
            "email": "auditor@demo.com", "phone": "+8801712345678",
            "full_name": "Auditor User", "role": "AUDITOR", "password": "audit1234",
        })
        r = self.client.post("/api/v1/auth/token", json={
            "email": "auditor@demo.com", "password": "audit1234",
        })
        self.token   = r.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        from app.services.audit_service import reset_audit_log
        from app.services.maker_checker_service import reset_maker_checker
        reset_audit_log()
        reset_maker_checker()

    def test_write_log_entry(self):
        r = self.client.post("/api/v1/audit/log", json={
            "event_type":  "USER_CREATED",
            "entity_type": "User",
            "actor_id":    "admin-001",
        }, headers=self.headers)
        assert r.status_code == 201
        assert r.json()["event_type"] == "USER_CREATED"

    def test_invalid_event_type_rejected(self):
        r = self.client.post("/api/v1/audit/log", json={
            "event_type":  "FAKE_EVENT",
            "entity_type": "User",
        }, headers=self.headers)
        assert r.status_code == 422

    def test_query_log(self):
        self.client.post("/api/v1/audit/log", json={
            "event_type": "USER_CREATED", "entity_type": "User",
        }, headers=self.headers)
        r = self.client.get("/api/v1/audit/log", headers=self.headers)
        assert r.status_code == 200
        assert "entries" in r.json()

    def test_get_entry_by_id(self):
        post = self.client.post("/api/v1/audit/log", json={
            "event_type": "AUTH_LOGIN_SUCCESS", "entity_type": "User",
        }, headers=self.headers)
        entry_id = post.json()["id"]
        r = self.client.get(f"/api/v1/audit/log/{entry_id}", headers=self.headers)
        assert r.status_code == 200
        assert r.json()["id"] == entry_id

    def test_dashboard_endpoint(self):
        r = self.client.get("/api/v1/audit/dashboard", headers=self.headers)
        assert r.status_code == 200
        assert "total_events" in r.json()

    def test_export_json_endpoint(self):
        r = self.client.get("/api/v1/audit/export/json", headers=self.headers)
        assert r.status_code == 200

    def test_export_csv_endpoint(self):
        r = self.client.get("/api/v1/audit/export/csv", headers=self.headers)
        assert r.status_code == 200

    def test_events_list_endpoint(self):
        r = self.client.get("/api/v1/audit/events", headers=self.headers)
        assert r.status_code == 200
        assert r.json()["total"] >= 30

    def test_policy_endpoint(self):
        r = self.client.get("/api/v1/audit/policy", headers=self.headers)
        assert r.status_code == 200
        assert r.json()["retention_years"] == 5
        assert r.json()["log_is_immutable"] is True

    def test_maker_checker_flow(self):
        r = self.client.post("/api/v1/audit/maker", json={
            "operation":      "ACCOUNT_CLOSURE",
            "maker_id":       "maker-001",
            "maker_role":     "MAKER",
            "entity_id":      "profile-001",
            "entity_type":    "KYCProfile",
            "payload":        {"reason": "test"},
            "institution_id": "inst-001",
        }, headers=self.headers)
        assert r.status_code == 201
        action_id = r.json()["action_id"]
        r2 = self.client.post(f"/api/v1/audit/checker/{action_id}", json={
            "checker_id":   "checker-001",
            "checker_role": "CHECKER",
            "decision":     "APPROVED",
        }, headers=self.headers)
        assert r2.status_code == 200
        assert r2.json()["status"] == "APPROVED"

    def test_unauthenticated_fails(self):
        r = self.client.get("/api/v1/audit/log")
        assert r.status_code == 403
