"""
M80/M81/M82 tests
M80: JWT RSA key rotation
M81: Alertmanager config wired
M82: Data residency middleware
"""
import os
import uuid
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path


# ═══════════════════════════════════════════════════════════════════════
# M80 — JWT RSA key rotation
# ═══════════════════════════════════════════════════════════════════════

class TestM80KeyRotation:

    def test_generate_rsa_keypair_returns_pem(self):
        from app.core.security import generate_rsa_keypair
        priv, pub = generate_rsa_keypair()
        assert "BEGIN PRIVATE KEY" in priv
        assert "BEGIN PUBLIC KEY" in pub

    def test_generate_rsa_keypair_unique(self):
        from app.core.security import generate_rsa_keypair
        priv1, pub1 = generate_rsa_keypair()
        priv2, pub2 = generate_rsa_keypair()
        assert priv1 != priv2
        assert pub1 != pub2

    def test_backup_current_keys_dry_run(self, tmp_path):
        from app.scripts.rotate_jwt_keys import backup_current_keys
        # Create dummy keys
        (tmp_path / "private.pem").write_text("FAKE_PRIV")
        (tmp_path / "public.pem").write_text("FAKE_PUB")
        with patch("app.scripts.rotate_jwt_keys.KEYS_DIR", tmp_path):
            result = backup_current_keys(dry_run=True)
        # dry_run — no actual copy
        backups = list(tmp_path.glob("*.bak.*"))
        assert len(backups) == 0
        assert len(result["backed_up"]) == 2

    def test_backup_current_keys_real(self, tmp_path):
        from app.scripts.rotate_jwt_keys import backup_current_keys
        (tmp_path / "private.pem").write_text("FAKE_PRIV")
        (tmp_path / "public.pem").write_text("FAKE_PUB")
        with patch("app.scripts.rotate_jwt_keys.KEYS_DIR", tmp_path):
            result = backup_current_keys(dry_run=False)
        backups = list(tmp_path.glob("*.bak.*"))
        assert len(backups) == 2

    def test_generate_and_write_keys_dry_run(self, tmp_path):
        from app.scripts.rotate_jwt_keys import generate_and_write_keys
        with patch("app.scripts.rotate_jwt_keys.KEYS_DIR", tmp_path):
            priv, pub = generate_and_write_keys(dry_run=True)
        # dry_run — no files written
        assert not (tmp_path / "private.pem").exists()
        assert "BEGIN PRIVATE KEY" in priv

    def test_generate_and_write_keys_real(self, tmp_path):
        from app.scripts.rotate_jwt_keys import generate_and_write_keys
        with patch("app.scripts.rotate_jwt_keys.KEYS_DIR", tmp_path):
            priv, pub = generate_and_write_keys(dry_run=False)
        assert (tmp_path / "private.pem").exists()
        assert (tmp_path / "public.pem").exists()
        assert "BEGIN PRIVATE KEY" in (tmp_path / "private.pem").read_text()

    def test_rotate_dry_run_no_file_changes(self, tmp_path):
        from app.scripts.rotate_jwt_keys import rotate
        (tmp_path / "private.pem").write_text("OLD_PRIV")
        (tmp_path / "public.pem").write_text("OLD_PUB")
        with patch("app.scripts.rotate_jwt_keys.KEYS_DIR", tmp_path):
            result = rotate(force=True, dry_run=True)
        assert result["status"] == "DRY_RUN"
        # Original files unchanged
        assert (tmp_path / "private.pem").read_text() == "OLD_PRIV"

    def test_rotate_force_creates_new_keys(self, tmp_path):
        from app.scripts.rotate_jwt_keys import rotate
        (tmp_path / "private.pem").write_text("OLD_PRIV")
        (tmp_path / "public.pem").write_text("OLD_PUB")
        with patch("app.scripts.rotate_jwt_keys.KEYS_DIR", tmp_path):
            with patch("app.scripts.rotate_jwt_keys.reload_security_module", return_value=True):
                result = rotate(force=True, dry_run=False)
        assert result["status"] == "ROTATED"
        new_priv = (tmp_path / "private.pem").read_text()
        assert new_priv != "OLD_PRIV"
        assert "BEGIN PRIVATE KEY" in new_priv

    def test_rotate_backs_up_old_keys(self, tmp_path):
        from app.scripts.rotate_jwt_keys import rotate
        (tmp_path / "private.pem").write_text("OLD_PRIV")
        (tmp_path / "public.pem").write_text("OLD_PUB")
        with patch("app.scripts.rotate_jwt_keys.KEYS_DIR", tmp_path):
            with patch("app.scripts.rotate_jwt_keys.reload_security_module", return_value=True):
                result = rotate(force=True, dry_run=False)
        assert len(result["backed_up"]) == 2
        backups = list(tmp_path.glob("private.pem.bak.*"))
        assert len(backups) == 1

    def test_rotate_writes_rotation_log(self, tmp_path):
        from app.scripts.rotate_jwt_keys import rotate
        (tmp_path / "private.pem").write_text("OLD")
        (tmp_path / "public.pem").write_text("OLD")
        with patch("app.scripts.rotate_jwt_keys.KEYS_DIR", tmp_path):
            with patch("app.scripts.rotate_jwt_keys.reload_security_module", return_value=True):
                rotate(force=True, dry_run=False)
        log_file = tmp_path / "rotation_log.txt"
        assert log_file.exists()
        content = log_file.read_text()
        assert "KEY_ROTATION" in content

    def test_cleanup_old_backups_keeps_5(self, tmp_path):
        from app.scripts.rotate_jwt_keys import cleanup_old_backups
        # Create 8 fake backups
        for i in range(8):
            (tmp_path / f"private.pem.bak.2026010{i}_000000").write_text("old")
            (tmp_path / f"public.pem.bak.2026010{i}_000000").write_text("old")
        with patch("app.scripts.rotate_jwt_keys.KEYS_DIR", tmp_path):
            removed = cleanup_old_backups(keep=5)
        remaining = list(tmp_path.glob("private.pem.bak.*"))
        assert len(remaining) == 5
        assert len(removed) == 6  # 3 priv + 3 pub removed

    def test_new_keys_can_sign_and_verify_jwt(self, tmp_path):
        """New keypair must produce valid JWTs."""
        from app.core.security import generate_rsa_keypair
        from jose import jwt
        priv, pub = generate_rsa_keypair()
        token = jwt.encode({"sub": "test", "exp": 9999999999}, priv, algorithm="RS256")
        decoded = jwt.decode(token, pub, algorithms=["RS256"])
        assert decoded["sub"] == "test"

    def test_rotate_cancelled_without_force(self, tmp_path):
        from app.scripts.rotate_jwt_keys import rotate
        with patch("builtins.input", return_value="no"):
            with patch("app.scripts.rotate_jwt_keys.KEYS_DIR", tmp_path):
                result = rotate(force=False, dry_run=False)
        assert result["status"] == "CANCELLED"


# ═══════════════════════════════════════════════════════════════════════
# M81 — Alertmanager config
# ═══════════════════════════════════════════════════════════════════════

class TestM81AlertmanagerConfig:

    def test_alertmanager_yml_exists(self):
        assert Path("monitoring/alertmanager/alertmanager.yml").exists(), \
            "monitoring/alertmanager/alertmanager.yml missing"

    def test_alertmanager_yml_has_routes(self):
        content = Path("monitoring/alertmanager/alertmanager.yml").read_text()
        assert "route:" in content
        assert "receiver:" in content

    def test_alertmanager_yml_has_compliance_receiver(self):
        content = Path("monitoring/alertmanager/alertmanager.yml").read_text()
        assert "ekyc-compliance" in content

    def test_alertmanager_yml_has_critical_receiver(self):
        content = Path("monitoring/alertmanager/alertmanager.yml").read_text()
        assert "ekyc-critical" in content

    def test_alertmanager_yml_has_unscr_route(self):
        """BFIU §3.2.2 — UNSCR feed failure must alert compliance."""
        content = Path("monitoring/alertmanager/alertmanager.yml").read_text()
        assert "UNSCRFeedStale" in content

    def test_alertmanager_yml_has_edd_route(self):
        """BFIU §4.3 — EDD SLA breach must alert."""
        content = Path("monitoring/alertmanager/alertmanager.yml").read_text()
        assert "EDDSLABreached" in content

    def test_alertmanager_rules_yml_exists(self):
        assert Path("monitoring/alertmanager_rules.yml").exists(), \
            "monitoring/alertmanager_rules.yml missing"

    def test_prometheus_yml_has_rule_files(self):
        content = Path("monitoring/prometheus.yml").read_text()
        assert "rule_files" in content or "alertmanager_rules" in content

    def test_prometheus_yml_has_alerting_block(self):
        content = Path("monitoring/prometheus.yml").read_text()
        assert "alerting:" in content
        assert "alertmanager" in content

    def test_docker_compose_monitoring_has_alertmanager(self):
        content = Path("docker-compose.monitoring.yml").read_text()
        assert "alertmanager" in content
        assert "9093" in content

    def test_alertmanager_repeat_intervals_set(self):
        content = Path("monitoring/alertmanager/alertmanager.yml").read_text()
        assert "repeat_interval" in content

    def test_alertmanager_inhibit_rules_set(self):
        content = Path("monitoring/alertmanager/alertmanager.yml").read_text()
        assert "inhibit_rules" in content


# ═══════════════════════════════════════════════════════════════════════
# M82 — Data residency middleware
# ═══════════════════════════════════════════════════════════════════════

class TestM82DataResidency:

    def _make_middleware(self, enforce=True):
        from app.middleware.data_residency import DataResidencyMiddleware
        app = MagicMock()
        with patch.dict(os.environ, {"DATA_RESIDENCY_ENFORCE": "true" if enforce else "false"}):
            mw = DataResidencyMiddleware(app)
        return mw

    def test_middleware_instantiates(self):
        mw = self._make_middleware()
        assert mw is not None

    def test_pii_endpoint_detected(self):
        mw = self._make_middleware()
        assert mw._is_pii_endpoint("/api/v1/kyc/profile") is True
        assert mw._is_pii_endpoint("/api/v1/nid/verify") is True
        assert mw._is_pii_endpoint("/api/v1/face/verify") is True
        assert mw._is_pii_endpoint("/api/v1/pep/entries") is True

    def test_non_pii_endpoint_not_detected(self):
        mw = self._make_middleware()
        assert mw._is_pii_endpoint("/api/v1/health") is False
        assert mw._is_pii_endpoint("/docs") is False
        assert mw._is_pii_endpoint("/metrics") is False

    def test_cross_border_header_detected(self):
        mw = self._make_middleware()
        request = MagicMock()
        request.headers = {
            "x-forwarded-to-region": "us-east-1",
        }
        result = mw._has_cross_border_header(request)
        assert result is not None
        assert "x-forwarded-to-region" in result

    def test_bd_region_header_allowed(self):
        mw = self._make_middleware()
        request = MagicMock()
        request.headers = {"x-processing-region": "bd"}
        result = mw._has_cross_border_header(request)
        assert result is None

    def test_no_cross_border_header_returns_none(self):
        mw = self._make_middleware()
        request = MagicMock()
        request.headers = {}
        result = mw._has_cross_border_header(request)
        assert result is None

    @pytest.mark.asyncio
    async def test_dispatch_non_pii_passes_through(self):
        from app.middleware.data_residency import DataResidencyMiddleware
        mock_response = MagicMock()
        mock_response.headers = {}
        async def mock_call_next(req):
            return mock_response
        app = MagicMock()
        with patch.dict(os.environ, {"DATA_RESIDENCY_ENFORCE": "true"}):
            mw = DataResidencyMiddleware(app)
        request = MagicMock()
        request.url.path = "/api/v1/health"
        request.headers = {}
        response = await mw.dispatch(request, mock_call_next)
        assert response == mock_response

    @pytest.mark.asyncio
    async def test_dispatch_pii_adds_residency_header(self):
        from app.middleware.data_residency import DataResidencyMiddleware, RESIDENCY_VALUE
        mock_response = MagicMock()
        mock_response.headers = {}
        async def mock_call_next(req):
            return mock_response
        app = MagicMock()
        with patch.dict(os.environ, {"DATA_RESIDENCY_ENFORCE": "true"}):
            mw = DataResidencyMiddleware(app)
        request = MagicMock()
        request.url.path = "/api/v1/kyc/profile"
        request.headers = {}
        request.client.host = "127.0.0.1"
        await mw.dispatch(request, mock_call_next)
        assert mock_response.headers.get("X-Data-Residency") == RESIDENCY_VALUE

    @pytest.mark.asyncio
    async def test_dispatch_blocks_cross_border_request(self):
        from app.middleware.data_residency import DataResidencyMiddleware
        from starlette.responses import JSONResponse
        app = MagicMock()
        with patch.dict(os.environ, {"DATA_RESIDENCY_ENFORCE": "true"}):
            mw = DataResidencyMiddleware(app)
        request = MagicMock()
        request.url.path = "/api/v1/kyc/profile"
        request.headers = {"x-forwarded-to-region": "us-east-1"}
        request.client.host = "1.2.3.4"
        async def mock_call_next(req):
            return MagicMock()
        response = await mw.dispatch(request, mock_call_next)
        assert isinstance(response, JSONResponse)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_dispatch_non_enforce_allows_cross_border(self):
        from app.middleware.data_residency import DataResidencyMiddleware
        from starlette.responses import JSONResponse
        mock_response = MagicMock()
        mock_response.headers = {}
        async def mock_call_next(req):
            return mock_response
        app = MagicMock()
        with patch.dict(os.environ, {"DATA_RESIDENCY_ENFORCE": "false"}):
            mw = DataResidencyMiddleware(app)
        request = MagicMock()
        request.url.path = "/api/v1/kyc/profile"
        request.headers = {"x-forwarded-to-region": "us-east-1"}
        request.client.host = "1.2.3.4"
        response = await mw.dispatch(request, mock_call_next)
        # Should NOT be 403 when enforce=false
        assert not isinstance(response, JSONResponse)

    def test_middleware_wired_in_main(self):
        with open("app/main.py", encoding="utf-8") as f:
            src = f.read()
        assert "DataResidencyMiddleware" in src, \
            "DataResidencyMiddleware not wired into main.py"

    def test_bfiu_ref_header_added(self):
        from app.middleware.data_residency import BFIU_REF_VALUE
        assert "Circular" in BFIU_REF_VALUE
        assert "29" in BFIU_REF_VALUE

    def test_all_pii_prefixes_covered(self):
        from app.middleware.data_residency import PII_PREFIXES
        required = ["/api/v1/kyc", "/api/v1/nid", "/api/v1/face",
                    "/api/v1/pep", "/api/v1/edd"]
        for r in required:
            assert any(r in p for p in PII_PREFIXES), \
                f"PII prefix {r} not in DATA_RESIDENCY middleware"
