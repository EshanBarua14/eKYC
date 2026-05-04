import os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

def test_db_session_imported():
    src = open("app/api/v1/routes/admin.py", encoding="utf-8").read()
    assert "from app.db.database import db_session" in src

def test_compliance_officer_in_valid_roles():
    src = open("app/api/v1/routes/admin.py", encoding="utf-8").read()
    import re
    m = re.search(r'VALID_ROLES\s*=\s*\{([^}]+)\}', src)
    assert m
    roles = {r.strip().strip('"').strip("'") for r in m.group(1).split(",")}
    assert "COMPLIANCE_OFFICER" in roles, f"Missing from: {roles}"

def test_disk_usage_linux_path():
    src = open("app/api/v1/routes/admin.py", encoding="utf-8").read()
    assert 'disk_usage("/")' in src
    assert "C:/" not in src

def test_disk_usage_works():
    import sys, pytest
    if sys.platform == "win32":
        pytest.skip("psutil disk_usage('/') is a Linux server test")
    import psutil
    d = psutil.disk_usage("/")
    assert d.total > 0

def test_no_dead_tenant_imports():
    src = open("app/api/v1/routes/admin.py", encoding="utf-8").read()
    assert "provision_tenant_schema" not in src

def test_env_has_encryption_key():
    src = open(".env.production", encoding="utf-8").read()
    assert "EKYC_FIELD_ENCRYPTION_KEY" in src

def test_env_has_sentry_dsn():
    src = open(".env.production", encoding="utf-8").read()
    assert "SENTRY_DSN" in src

def test_ssl_scripts_exist():
    assert os.path.exists("../infra/ssl/generate_self_signed.sh")
    assert os.path.exists("../infra/ssl/certbot_production.sh")

def test_kyc_wizard_11_steps():
    path = "../frontend/src/pages/KYCWizard.jsx"
    if not os.path.exists(path):
        pytest.skip("frontend not found")
    src = open(path, encoding="utf-8").read()
    assert "ScreeningStep" in src, "ScreeningStep missing"
    assert "BeneficialOwner" in src, "BeneficialOwnerStep missing"
    assert "RiskStep" in src, "RiskStep missing"
    assert "ConsentStep" in src, "ConsentStep missing"
    count = src.count("{ label:")
    assert count >= 11, f"Only {count} steps, need 11"
