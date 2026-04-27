"""
M64 - Docker Compose + Nginx + SSL
Tests: infrastructure config validation (BFIU section 4.5 compliance)
"""
import yaml
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


@pytest.fixture(scope="module")
def docker_compose():
    with open(PROJECT_ROOT / "docker-compose.yml") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def nginx_conf():
    return (PROJECT_ROOT / "nginx/conf.d/ekyc.conf").read_text()


@pytest.fixture(scope="module")
def nginx_main():
    return (PROJECT_ROOT / "nginx/nginx.conf").read_text()


@pytest.fixture(scope="module")
def env_production():
    return (PROJECT_ROOT / ".env.production").read_text()


class TestDockerComposeStructure:
    def test_file_exists(self):
        assert (PROJECT_ROOT / "docker-compose.yml").exists()

    def test_required_services_present(self, docker_compose):
        services = docker_compose["services"]
        required = {"db", "redis", "backend", "celery_worker", "celery_beat", "nginx", "certbot"}
        assert required.issubset(set(services.keys()))

    def test_db_has_healthcheck(self, docker_compose):
        assert "healthcheck" in docker_compose["services"]["db"]

    def test_redis_has_healthcheck(self, docker_compose):
        assert "healthcheck" in docker_compose["services"]["redis"]

    def test_backend_has_healthcheck(self, docker_compose):
        assert "healthcheck" in docker_compose["services"]["backend"]

    def test_nginx_exposes_80_and_443(self, docker_compose):
        ports = docker_compose["services"]["nginx"]["ports"]
        port_strs = [str(p) for p in ports]
        assert any("80:80" in p for p in port_strs)
        assert any("443:443" in p for p in port_strs)

    def test_backend_depends_on_db_healthy(self, docker_compose):
        deps = docker_compose["services"]["backend"]["depends_on"]
        assert "db" in deps
        assert deps["db"]["condition"] == "service_healthy"

    def test_backend_depends_on_redis_healthy(self, docker_compose):
        deps = docker_compose["services"]["backend"]["depends_on"]
        assert "redis" in deps
        assert deps["redis"]["condition"] == "service_healthy"

    def test_secret_key_required_no_default(self, docker_compose):
        env = docker_compose["services"]["backend"]["environment"]
        sk = str(env.get("SECRET_KEY", ""))
        assert ":?" in sk

    def test_postgres_password_required(self, docker_compose):
        env = docker_compose["services"]["db"]["environment"]
        pw = str(env.get("POSTGRES_PASSWORD", ""))
        assert ":?" in pw

    def test_redis_aof_persistence_enabled(self, docker_compose):
        cmd = str(docker_compose["services"]["redis"]["command"])
        assert "appendonly yes" in cmd

    def test_volumes_declared(self, docker_compose):
        vols = docker_compose.get("volumes", {})
        assert "postgres_data" in vols
        assert "redis_data" in vols

    def test_networks_internal_and_external(self, docker_compose):
        nets = docker_compose.get("networks", {})
        assert "internal" in nets
        assert "external" in nets

    def test_internal_network_is_internal(self, docker_compose):
        internal = docker_compose["networks"]["internal"]
        assert internal.get("internal") is True

    def test_certbot_service_present(self, docker_compose):
        assert "certbot" in docker_compose["services"]


class TestNginxHTTPSCompliance:
    def test_nginx_conf_exists(self):
        assert (PROJECT_ROOT / "nginx/conf.d/ekyc.conf").exists()

    def test_http_redirects_to_https(self, nginx_conf):
        assert "return 301 https://" in nginx_conf

    def test_hsts_header_present(self, nginx_conf):
        assert "Strict-Transport-Security" in nginx_conf
        assert "max-age=31536000" in nginx_conf

    def test_hsts_includes_subdomains(self, nginx_conf):
        assert "includeSubDomains" in nginx_conf

    def test_tls_1_2_minimum(self, nginx_conf):
        assert "TLSv1.2" in nginx_conf
        assert "TLSv1.3" in nginx_conf
        assert "TLSv1.0" not in nginx_conf
        assert "TLSv1.1" not in nginx_conf

    def test_ssl_certificate_configured(self, nginx_conf):
        assert "ssl_certificate" in nginx_conf
        assert "ssl_certificate_key" in nginx_conf

    def test_http2_enabled(self, nginx_conf):
        assert "http2" in nginx_conf

    def test_api_proxy_to_backend(self, nginx_conf):
        assert "proxy_pass http://backend:8000" in nginx_conf

    def test_health_check_endpoint_exposed(self, nginx_conf):
        assert "/health" in nginx_conf

    def test_x_frame_options_deny(self, nginx_conf):
        assert "X-Frame-Options" in nginx_conf
        assert "DENY" in nginx_conf

    def test_x_content_type_nosniff(self, nginx_conf):
        assert "X-Content-Type-Options" in nginx_conf
        assert "nosniff" in nginx_conf

    def test_server_tokens_off(self, nginx_main):
        assert "server_tokens off" in nginx_main

    def test_rate_limiting_configured(self, nginx_main):
        assert "limit_req_zone" in nginx_main

    def test_auth_rate_limit_stricter(self, nginx_conf):
        assert "zone=auth" in nginx_conf

    def test_dot_files_blocked(self, nginx_conf):
        assert "deny all" in nginx_conf

    def test_csp_header_present(self, nginx_conf):
        assert "Content-Security-Policy" in nginx_conf

    def test_acme_challenge_location(self, nginx_conf):
        assert ".well-known/acme-challenge" in nginx_conf


class TestNginxMainConfig:
    def test_json_logging_format(self, nginx_main):
        assert "main_json" in nginx_main
        assert "escape=json" in nginx_main

    def test_gzip_enabled(self, nginx_main):
        assert "gzip on" in nginx_main


class TestSSLCertificate:
    def test_ssl_cert_file_exists(self):
        assert (PROJECT_ROOT / "nginx/ssl/server.crt").exists()

    def test_ssl_key_file_exists(self):
        assert (PROJECT_ROOT / "nginx/ssl/server.key").exists()

    def test_ssl_key_not_in_git(self):
        gitignore_path = PROJECT_ROOT / ".gitignore"
        gitignore = gitignore_path.read_text() if gitignore_path.exists() else ""
        assert any(p in gitignore for p in ["*.key", "server.key", "nginx/ssl"])


class TestEnvProduction:
    def test_env_production_exists(self):
        assert (PROJECT_ROOT / ".env.production").exists()

    def test_secret_key_placeholder_empty(self, env_production):
        lines = {}
        for line in env_production.splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                lines[k.strip()] = v.strip()
        assert lines.get("SECRET_KEY", "MISSING") == ""

    def test_env_production_in_gitignore(self):
        gitignore_path = PROJECT_ROOT / ".gitignore"
        gitignore = gitignore_path.read_text() if gitignore_path.exists() else ""
        assert any(p in gitignore for p in [".env.production", ".env*", ".env"])

    def test_env_has_required_keys(self, env_production):
        required = ["SECRET_KEY", "POSTGRES_PASSWORD", "REDIS_PASSWORD",
                    "ENVIRONMENT", "CORS_ORIGINS"]
        for key in required:
            assert key in env_production


class TestDockerfiles:
    def test_backend_dockerfile_exists(self):
        assert (PROJECT_ROOT / "backend/Dockerfile").exists()

    def test_frontend_dockerfile_exists(self):
        assert (PROJECT_ROOT / "frontend/Dockerfile").exists()

    def test_backend_dockerfile_non_root(self):
        content = (PROJECT_ROOT / "backend/Dockerfile").read_text()
        assert "USER ekyc" in content

    def test_backend_dockerfile_healthcheck(self):
        content = (PROJECT_ROOT / "backend/Dockerfile").read_text()
        assert "HEALTHCHECK" in content

    def test_frontend_dockerfile_multistage(self):
        content = (PROJECT_ROOT / "frontend/Dockerfile").read_text()
        assert content.count("FROM") >= 2


class TestGitignore:
    def test_ssl_private_key_ignored(self):
        gitignore_path = PROJECT_ROOT / ".gitignore"
        gitignore = gitignore_path.read_text() if gitignore_path.exists() else ""
        assert any(p in gitignore for p in ["*.key", "server.key", "nginx/ssl/", "nginx/ssl"])

    def test_env_production_ignored(self):
        gitignore_path = PROJECT_ROOT / ".gitignore"
        gitignore = gitignore_path.read_text() if gitignore_path.exists() else ""
        assert any(p in gitignore for p in [".env.production", ".env*", ".env"])
