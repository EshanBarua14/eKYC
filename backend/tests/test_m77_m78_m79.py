"""
M77/M78/M79 tests — BFIU Circular No. 29
M77: Account opening notification dispatch (§3.2 Step 5)
M78: KYC profile DB persistence + notification wire
M79: Tenant schema auto-provisioning (§5.2)
"""
import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime


# ═══════════════════════════════════════════════════════════════════════
# M77 — Notification Celery tasks
# ═══════════════════════════════════════════════════════════════════════

class TestM77NotificationTask:

    def test_success_task_calls_notify_kyc_success(self):
        with patch("app.worker.tasks.notify_account_opening.notify_kyc_success") as mock_notify:
            mock_notify.return_value = {"status": "sent", "channels": {"sms": {"status": "DEV_LOGGED"}}}
            from app.worker.tasks.notify_account_opening import send_account_opening_success
            result = send_account_opening_success(
                session_id="sess-001",
                full_name="Karim Uddin",
                mobile="01700000001",
                email="karim@example.com",
                account_number="ACC-001",
                kyc_type="SIMPLIFIED",
                risk_grade="LOW",
                confidence=0.92,
            )
            mock_notify.assert_called_once()
            call_kwargs = mock_notify.call_args[1]
            assert call_kwargs["session_id"] == "sess-001"
            assert call_kwargs["mobile"] == "01700000001"
            assert call_kwargs["full_name"] == "Karim Uddin"

    def test_failure_task_calls_notify_kyc_failure(self):
        with patch("app.worker.tasks.notify_account_opening.notify_kyc_failure") as mock_notify:
            mock_notify.return_value = {"status": "sent"}
            from app.worker.tasks.notify_account_opening import send_account_opening_failure
            result = send_account_opening_failure(
                session_id="sess-002",
                mobile="01700000002",
                reason="NID mismatch",
                failed_step="face_verify",
            )
            mock_notify.assert_called_once()
            kw = mock_notify.call_args[1]
            assert kw["session_id"] == "sess-002"
            assert kw["reason"] == "NID mismatch"

    def test_success_task_returns_result(self):
        with patch("app.worker.tasks.notify_account_opening.notify_kyc_success") as mock_notify:
            mock_notify.return_value = {"status": "sent", "session_id": "sess-003"}
            from app.worker.tasks.notify_account_opening import send_account_opening_success
            result = send_account_opening_success(
                session_id="sess-003",
                full_name="Rahim",
                mobile="01800000001",
            )
            assert result["status"] == "sent"

    def test_success_task_retries_on_exception(self):
        """Task must propagate exception after max retries exhausted."""
        from app.worker.tasks.notify_account_opening import send_account_opening_success
        with patch("app.worker.tasks.notify_account_opening.notify_kyc_success",
                   side_effect=ConnectionError("SMTP down")):
            result = send_account_opening_success.apply(
                kwargs=dict(session_id="sess-retry", full_name="Test",
                            mobile="01700000099"),
            )
            assert result.failed(), "Task should fail when notify raises"
            assert isinstance(result.result, (ConnectionError, Exception))

    def test_failure_task_retries_on_exception(self):
        """Task must propagate exception after max retries exhausted."""
        from app.worker.tasks.notify_account_opening import send_account_opening_failure
        with patch("app.worker.tasks.notify_account_opening.notify_kyc_failure",
                   side_effect=ConnectionError("SMS gateway down")):
            result = send_account_opening_failure.apply(
                kwargs=dict(session_id="sess-retry2", mobile="01700000098"),
            )
            assert result.failed(), "Task should fail when notify raises"
            assert isinstance(result.result, (ConnectionError, Exception))

    def test_success_task_name(self):
        from app.worker.tasks.notify_account_opening import send_account_opening_success
        assert send_account_opening_success.name == "notify.account_opening_success"

    def test_failure_task_name(self):
        from app.worker.tasks.notify_account_opening import send_account_opening_failure
        assert send_account_opening_failure.name == "notify.account_opening_failure"

    def test_success_task_max_retries(self):
        from app.worker.tasks.notify_account_opening import send_account_opening_success
        assert send_account_opening_success.max_retries == 3

    def test_failure_task_max_retries(self):
        from app.worker.tasks.notify_account_opening import send_account_opening_failure
        assert send_account_opening_failure.max_retries == 3

    def test_success_passes_institution_name(self):
        with patch("app.worker.tasks.notify_account_opening.notify_kyc_success") as mock_notify:
            mock_notify.return_value = {"status": "sent"}
            from app.worker.tasks.notify_account_opening import send_account_opening_success
            send_account_opening_success(
                session_id="s1",
                full_name="Test",
                mobile="017",
                institution_name="Dutch Bangla Bank",
            )
            kw = mock_notify.call_args[1]
            assert kw["institution_name"] == "Dutch Bangla Bank"

    def test_success_default_account_number_pending(self):
        with patch("app.worker.tasks.notify_account_opening.notify_kyc_success") as mock_notify:
            mock_notify.return_value = {"status": "sent"}
            from app.worker.tasks.notify_account_opening import send_account_opening_success
            send_account_opening_success(
                session_id="s2", full_name="X", mobile="018"
            )
            kw = mock_notify.call_args[1]
            assert kw["account_number"] == "PENDING"


# ═══════════════════════════════════════════════════════════════════════
# M78 — KYC profile route notification wire
# ═══════════════════════════════════════════════════════════════════════

class TestM78KYCProfileNotificationWire:

    def test_notify_import_present_in_route(self):
        """notify_account_opening must be imported in kyc_profile route."""
        with open("app/api/v1/routes/kyc_profile.py", encoding="utf-8") as f:
            src = f.read()
        assert "notify_account_opening" in src, \
            "M77 import missing from kyc_profile.py"

    def test_notify_delay_called_in_route(self):
        """send_account_opening_success.delay must be wired in create_profile."""
        with open("app/api/v1/routes/kyc_profile.py", encoding="utf-8") as f:
            src = f.read()
        assert "send_account_opening_success.delay" in src, \
            "Notification dispatch not wired into create_profile endpoint"

    def test_notify_is_non_blocking(self):
        """Notification failure must not raise — wrapped in try/except."""
        with open("app/api/v1/routes/kyc_profile.py", encoding="utf-8") as f:
            src = f.read()
        # try block must wrap the .delay call
        notify_pos = src.find("send_account_opening_success.delay")
        try_pos = src.rfind("try:", 0, notify_pos)
        except_pos = src.find("except", notify_pos)
        assert try_pos != -1, "Notification dispatch must be in try block"
        assert except_pos != -1, "Notification dispatch must have except handler"

    def test_kyc_profile_route_syntax_valid(self):
        import ast
        with open("app/api/v1/routes/kyc_profile.py", encoding="utf-8") as f:
            src = f.read()
        ast.parse(src)  # raises SyntaxError if broken

    def test_profile_create_passes_mobile_to_notify(self):
        """mobile field must be forwarded to notification."""
        with open("app/api/v1/routes/kyc_profile.py", encoding="utf-8") as f:
            src = f.read()
        # mobile= must appear in the .delay() call block
        delay_start = src.find("send_account_opening_success.delay")
        delay_end = src.find(")", delay_start) + 1
        delay_block = src[delay_start:delay_end + 200]
        assert "mobile" in delay_block, \
            "mobile not passed to notification dispatch"

    def test_profile_create_passes_session_id_to_notify(self):
        with open("app/api/v1/routes/kyc_profile.py", encoding="utf-8") as f:
            src = f.read()
        delay_start = src.find("send_account_opening_success.delay")
        delay_block = src[delay_start:delay_start + 400]
        assert "session_id" in delay_block


# ═══════════════════════════════════════════════════════════════════════
# M79 — Tenant schema provisioning
# ═══════════════════════════════════════════════════════════════════════

class TestM79TenantProvisioning:

    def _make_db(self, schema_exists=False):
        db = MagicMock()
        result = MagicMock()
        result.fetchone.return_value = ("tenant_abc",) if schema_exists else None
        db.execute.return_value = result
        return db

    def test_provision_creates_schema_postgres(self):
        from app.services.tenant_provisioning import provision_tenant_schema
        with patch("app.services.tenant_provisioning._is_postgres", True):
            db = self._make_db(schema_exists=False)
            result = provision_tenant_schema(db, "inst-1", "tenant_testbank", "Test Bank")
            assert result["status"] == "CREATED"
            assert result["schema_name"] == "tenant_testbank"
            db.commit.assert_called()

    def test_provision_idempotent_already_exists(self):
        from app.services.tenant_provisioning import provision_tenant_schema
        with patch("app.services.tenant_provisioning._is_postgres", True):
            db = self._make_db(schema_exists=True)
            result = provision_tenant_schema(db, "inst-2", "tenant_testbank", "Test Bank")
            assert result["status"] == "ALREADY_EXISTS"

    def test_provision_skipped_non_postgres(self):
        from app.services.tenant_provisioning import provision_tenant_schema
        with patch("app.services.tenant_provisioning._is_postgres", False):
            db = self._make_db()
            result = provision_tenant_schema(db, "inst-3", "tenant_x", "X Bank")
            assert result["status"] == "SKIPPED"
            assert result["reason"] == "non-postgres"

    def test_provision_returns_bfiu_ref(self):
        from app.services.tenant_provisioning import provision_tenant_schema
        with patch("app.services.tenant_provisioning._is_postgres", True):
            db = self._make_db(schema_exists=False)
            result = provision_tenant_schema(db, "inst-4", "tenant_mfi01", "MFI One")
            assert result["bfiu_ref"] == "BFIU Circular No. 29 §5.2"

    def test_provision_invalid_schema_name_raises(self):
        from app.services.tenant_provisioning import provision_tenant_schema
        with patch("app.services.tenant_provisioning._is_postgres", True):
            db = self._make_db()
            with pytest.raises(ValueError):
                provision_tenant_schema(db, "inst-5", "DROP TABLE--", "Evil")

    def test_provision_reserved_name_raises(self):
        from app.services.tenant_provisioning import provision_tenant_schema
        with patch("app.services.tenant_provisioning._is_postgres", True):
            db = self._make_db()
            with pytest.raises(ValueError):
                provision_tenant_schema(db, "inst-6", "public", "Bad")

    def test_provision_schema_name_uppercase_normalized(self):
        from app.services.tenant_provisioning import provision_tenant_schema
        with patch("app.services.tenant_provisioning._is_postgres", True):
            db = self._make_db(schema_exists=False)
            result = provision_tenant_schema(db, "inst-7", "Tenant_Bank01", "Bank")
            assert result["schema_name"] == "tenant_bank01"

    def test_provision_schema_too_short_raises(self):
        from app.services.tenant_provisioning import provision_tenant_schema
        with patch("app.services.tenant_provisioning._is_postgres", True):
            db = self._make_db()
            with pytest.raises(ValueError):
                provision_tenant_schema(db, "inst-8", "ab", "Short")

    def test_provision_schema_starts_with_digit_raises(self):
        from app.services.tenant_provisioning import provision_tenant_schema
        with patch("app.services.tenant_provisioning._is_postgres", True):
            db = self._make_db()
            with pytest.raises(ValueError):
                provision_tenant_schema(db, "inst-9", "1tenant", "Bad")

    def test_deprovision_renames_not_drops(self):
        from app.services.tenant_provisioning import deprovision_tenant_schema
        with patch("app.services.tenant_provisioning._is_postgres", True):
            db = MagicMock()
            result = deprovision_tenant_schema(db, "tenant_old", "inst-10")
            assert result["status"] == "ARCHIVED"
            assert "archived_tenant_old" in result["archived_as"]
            # Must use RENAME not DROP — extract text from TextClause objects
            executed_sqls = " ".join(
                str(c[0][0].text) if hasattr(c[0][0], "text") else str(c[0][0])
                for c in db.execute.call_args_list
            )
            assert "RENAME" in executed_sqls.upper()
            assert "DROP" not in executed_sqls.upper()

    def test_deprovision_skipped_non_postgres(self):
        from app.services.tenant_provisioning import deprovision_tenant_schema
        with patch("app.services.tenant_provisioning._is_postgres", False):
            db = MagicMock()
            result = deprovision_tenant_schema(db, "tenant_old", "inst-11")
            assert result["status"] == "SKIPPED"

    def test_add_schema_to_allowlist(self):
        from app.services.tenant_provisioning import add_schema_to_allowlist
        import app.middleware.tenant_db as tenant_mod
        original = tenant_mod._ALLOWED_SCHEMAS
        add_schema_to_allowlist("tenant_newbank")
        assert "tenant_newbank" in tenant_mod._ALLOWED_SCHEMAS
        # Restore
        tenant_mod._ALLOWED_SCHEMAS = original

    def test_provision_includes_institution_name_in_result(self):
        from app.services.tenant_provisioning import provision_tenant_schema
        with patch("app.services.tenant_provisioning._is_postgres", True):
            db = self._make_db(schema_exists=False)
            result = provision_tenant_schema(db, "inst-12", "tenant_islami", "Islami Bank")
            assert result["institution_name"] == "Islami Bank"

    def test_admin_route_imports_provisioning(self):
        with open("app/api/v1/routes/admin.py", encoding="utf-8") as f:
            src = f.read()
        assert "tenant_provisioning" in src or "provision_tenant_schema" in src, \
            "M79 not wired into admin.py institution creation"

    def test_validate_schema_blocks_sql_injection(self):
        from app.services.tenant_provisioning import _validate_schema_name
        bad = ["'; DROP TABLE users;--", "public", "../etc", "ab",
               "1start", "has space", "has-dash"]
        for name in bad:
            with pytest.raises(ValueError, match=""):
                _validate_schema_name(name)

    def test_validate_schema_allows_valid_names(self):
        from app.services.tenant_provisioning import _validate_schema_name
        good = ["tenant_abc", "tenant_bank01", "mfi_dhaka", "nbfi_001"]
        for name in good:
            assert _validate_schema_name(name) == name
