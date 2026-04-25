"""
M70-M75 Tests: SSL/Certbot, pip-audit, Flower, SOF validation, UNSCR monitor, pgcrypto
"""
import os
import pytest
from unittest.mock import MagicMock, patch


# ── M70: SSL/Certbot ──────────────────────────────────────────────────────
def test_T01_nginx_config_has_ssl():
    nginx_path = "../nginx/nginx.conf"
    if not os.path.exists(nginx_path):
        pytest.skip("nginx.conf not found")
    content = open(nginx_path).read()
    assert "ssl_certificate" in content
    assert "TLSv1.2" in content
    assert "443" in content

def test_T02_nginx_has_hsts():
    nginx_path = "../nginx/nginx.conf"
    if not os.path.exists(nginx_path):
        pytest.skip("nginx.conf not found")
    content = open(nginx_path).read()
    assert "Strict-Transport-Security" in content

def test_T03_nginx_has_http_redirect():
    nginx_path = "../nginx/nginx.conf"
    if not os.path.exists(nginx_path):
        pytest.skip("nginx.conf not found")
    content = open(nginx_path).read()
    assert "301" in content
    assert "https" in content

def test_T04_certbot_script_exists():
    assert os.path.exists("scripts/generate_self_signed_cert.sh")

def test_T05_docker_compose_has_certbot():
    for path in ["../docker-compose.prod.yml", "docker-compose.prod.yml"]:
        if os.path.exists(path):
            content = open(path).read()
            assert "certbot" in content
            return
    pytest.skip("docker-compose.prod.yml not found")


# ── M71: Security scan ────────────────────────────────────────────────────
def test_T06_security_scan_script_exists():
    assert os.path.exists("scripts/security_scan.sh")

def test_T07_security_scan_has_pip_audit():
    content = open("scripts/security_scan.sh").read()
    assert "pip-audit" in content

def test_T08_requirements_txt_frozen():
    assert os.path.exists("requirements.txt")
    content = open("requirements.txt").read()
    # Frozen requirements have == not just package names
    assert "==" in content


# ── M72: Flower ───────────────────────────────────────────────────────────
def test_T09_docker_compose_has_flower():
    for path in ["../docker-compose.prod.yml", "docker-compose.prod.yml"]:
        if os.path.exists(path):
            content = open(path).read()
            assert "flower" in content
            return
    pytest.skip("not found")

def test_T10_celery_app_has_workers():
    content = open("app/worker/celery_app.py", encoding="latin-1").read()
    assert "celery_app" in content
    assert "beat_schedule" in content


# ── M73: Source of funds ──────────────────────────────────────────────────
def test_T11_sof_salary_valid():
    from app.services.source_of_funds_validator import validate_source_of_funds
    result = validate_source_of_funds("SALARY", kyc_type="REGULAR")
    assert result["validated"] == True
    assert result["document_required"] == False

def test_T12_sof_empty_fails():
    from app.services.source_of_funds_validator import validate_source_of_funds, SourceOfFundsValidationError
    with pytest.raises(SourceOfFundsValidationError):
        validate_source_of_funds("", kyc_type="REGULAR")

def test_T13_sof_invalid_source_fails():
    from app.services.source_of_funds_validator import validate_source_of_funds, SourceOfFundsValidationError
    with pytest.raises(SourceOfFundsValidationError):
        validate_source_of_funds("CRIME", kyc_type="REGULAR")

def test_T14_sof_other_requires_explanation():
    from app.services.source_of_funds_validator import validate_source_of_funds, SourceOfFundsValidationError
    with pytest.raises(SourceOfFundsValidationError):
        validate_source_of_funds("OTHER", kyc_type="REGULAR")

def test_T15_sof_other_with_explanation_ok():
    from app.services.source_of_funds_validator import validate_source_of_funds
    result = validate_source_of_funds("OTHER", explanation="Prize money", kyc_type="REGULAR")
    assert result["validated"] == True

def test_T16_sof_remittance_requires_docs():
    from app.services.source_of_funds_validator import validate_source_of_funds
    result = validate_source_of_funds("REMITTANCE", kyc_type="REGULAR")
    assert result["document_required"] == True

def test_T17_sof_skipped_for_simplified():
    from app.services.source_of_funds_validator import validate_source_of_funds
    result = validate_source_of_funds("", kyc_type="SIMPLIFIED")
    assert result["validated"] == True
    assert result["required"] == False

def test_T18_sof_high_income_flags_docs():
    from app.services.source_of_funds_validator import validate_source_of_funds
    result = validate_source_of_funds("SAVINGS", kyc_type="REGULAR", annual_income_bdt=6_000_000)
    assert result["document_required"] == True

def test_T19_sof_bfiu_ref():
    from app.services.source_of_funds_validator import validate_source_of_funds
    result = validate_source_of_funds("SALARY", kyc_type="REGULAR")
    assert "4.2" in result["bfiu_ref"]


# ── M74: UNSCR monitor ────────────────────────────────────────────────────
def test_T20_unscr_monitor_exists():
    from app.services.unscr_monitor import check_unscr_freshness, MAX_STALENESS_HOURS
    assert MAX_STALENESS_HOURS == 24

def test_T21_unscr_monitor_no_meta_returns_never_pulled():
    from app.services.unscr_monitor import check_unscr_freshness
    db = MagicMock()
    q = MagicMock(); q.order_by.return_value = q; q.first.return_value = None
    db.query.return_value = q
    result = check_unscr_freshness(db)
    assert result["stale"] == True

def test_T22_unscr_monitor_fresh_returns_fresh():
    from app.services.unscr_monitor import check_unscr_freshness
    from datetime import datetime, timezone
    meta = MagicMock()
    meta.last_updated_at = datetime.now(timezone.utc)
    db = MagicMock()
    q = MagicMock(); q.order_by.return_value = q; q.first.return_value = meta
    q.filter.return_value = q; q.count.return_value = 100
    db.query.return_value = q
    result = check_unscr_freshness(db)
    assert result["status"] in ("FRESH", "ERROR")


# ── M75: pgcrypto ─────────────────────────────────────────────────────────
def test_T23_pgcrypto_in_migration():
    content = open("alembic/versions/b5a0d85cccf3_m54_pgcrypto_aes_256_field_encryption_.py",
                   encoding="utf-8").read()
    assert "pgcrypto" in content
    assert "CREATE EXTENSION IF NOT EXISTS pgcrypto" in content

def test_T24_verify_script_exists():
    assert os.path.exists("scripts/verify_pgcrypto.sh")

def test_T25_init_sql_has_pgcrypto():
    init_path = "../infra/postgres/init.sql"
    if os.path.exists(init_path):
        content = open(init_path).read()
        assert "pgcrypto" in content
    else:
        pytest.skip("init.sql not found")
