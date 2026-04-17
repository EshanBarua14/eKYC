"""
M1 - Project Setup Tests
Tests: config loading, env vars, file structure, docker files present
"""
import pytest
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent


class TestEnvConfig:
    def test_env_file_exists(self):
        assert (ROOT / ".env").exists(), ".env file missing"

    def test_env_example_exists(self):
        assert (ROOT / ".env.example").exists(), ".env.example missing"

    def test_env_has_required_keys(self):
        content = (ROOT / ".env").read_text(encoding="utf-8")
        required = [
            "APP_NAME", "SECRET_KEY",
            "POSTGRES_HOST", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD",
            "REDIS_URL", "BFIU_MAX_ATTEMPTS_PER_SESSION", "BFIU_MAX_SESSIONS_PER_DAY"
        ]
        for key in required:
            assert key in content, f"Missing key in .env: {key}"


class TestDockerFiles:
    def test_dockerfile_exists(self):
        assert (ROOT / "Dockerfile").exists(), "Dockerfile missing"

    def test_dockerfile_has_python312(self):
        content = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        assert "python:3.12" in content

    def test_dockerfile_has_tesseract(self):
        content = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        assert "tesseract-ocr" in content

    def test_compose_exists(self):
        assert (ROOT / "docker-compose.yml").exists(), "docker-compose.yml missing"

    def test_compose_has_three_services(self):
        content = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        assert "api:" in content
        assert "db:" in content
        assert "redis:" in content

    def test_compose_has_healthchecks(self):
        content = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        assert content.count("healthcheck") >= 2

    def test_dockerignore_exists(self):
        assert (ROOT / ".dockerignore").exists(), ".dockerignore missing"

    def test_dockerignore_excludes_venv(self):
        content = (ROOT / ".dockerignore").read_text(encoding="utf-8")
        assert "venv/" in content


class TestInfraFiles:
    def test_postgres_init_sql_exists(self):
        assert (ROOT / "infra" / "postgres" / "init.sql").exists()

    def test_init_sql_has_extensions(self):
        content = (ROOT / "infra" / "postgres" / "init.sql").read_text(encoding="utf-8")
        assert "pgcrypto" in content
        assert "pg_trgm" in content

    def test_init_sql_has_institutions_table(self):
        content = (ROOT / "infra" / "postgres" / "init.sql").read_text(encoding="utf-8")
        assert "institutions" in content

    def test_init_sql_has_audit_log(self):
        content = (ROOT / "infra" / "postgres" / "init.sql").read_text(encoding="utf-8")
        assert "audit_log" in content

    def test_init_sql_has_tenant_schema(self):
        content = (ROOT / "infra" / "postgres" / "init.sql").read_text(encoding="utf-8")
        assert "tenant_demo" in content


class TestCICD:
    def test_github_workflow_exists(self):
        assert (ROOT / ".github" / "workflows" / "ci.yml").exists()

    def test_workflow_has_test_job(self):
        content = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        assert "pytest" in content

    def test_workflow_has_postgres_service(self):
        content = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        assert "postgres:16" in content

    def test_workflow_has_redis_service(self):
        content = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        assert "redis:7" in content


class TestConfig:
    def test_config_imports(self):
        import sys
        sys.path.insert(0, str(ROOT / "backend"))
        from app.core.config import settings
        assert settings.APP_NAME != ""

    def test_config_has_database_url_property(self):
        import sys
        sys.path.insert(0, str(ROOT / "backend"))
        from app.core.config import settings
        url = settings.DATABASE_URL
        assert "postgresql://" in url

    def test_config_bfiu_limits(self):
        import sys
        sys.path.insert(0, str(ROOT / "backend"))
        from app.core.config import settings
        assert settings.BFIU_MAX_ATTEMPTS_PER_SESSION == 10
        assert settings.BFIU_MAX_SESSIONS_PER_DAY == 2

    def test_config_has_redis_url(self):
        import sys
        sys.path.insert(0, str(ROOT / "backend"))
        from app.core.config import settings
        assert "redis://" in settings.REDIS_URL
