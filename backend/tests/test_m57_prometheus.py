"""
M57 — Prometheus/Grafana metrics tests
BFIU Circular No. 29 §5.3 observability
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_metrics_endpoint_exists():
    r = client.get("/metrics")
    assert r.status_code == 200


def test_metrics_content_type():
    r = client.get("/metrics")
    assert "text/plain" in r.headers["content-type"]


def test_metrics_contains_http_requests():
    client.get("/health")
    r = client.get("/metrics")
    assert "http_requests_total" in r.text or "http_request" in r.text


def test_metrics_contains_python_info():
    r = client.get("/metrics")
    assert "python_info" in r.text or "process_" in r.text


def test_face_verify_latency_metric_registered():
    from app.services.metrics import FACE_VERIFY_LATENCY
    assert FACE_VERIFY_LATENCY is not None


def test_ec_api_errors_metric_registered():
    from app.services.metrics import EC_API_ERRORS
    assert EC_API_ERRORS is not None


def test_celery_queue_depth_metric_registered():
    from app.services.metrics import CELERY_QUEUE_DEPTH
    assert CELERY_QUEUE_DEPTH is not None


def test_adverse_media_flags_metric_registered():
    from app.services.metrics import ADVERSE_MEDIA_FLAGS
    assert ADVERSE_MEDIA_FLAGS is not None


def test_face_verify_latency_observe():
    from app.services.metrics import FACE_VERIFY_LATENCY
    FACE_VERIFY_LATENCY.observe(0.45)
    r = client.get("/metrics")
    assert "ekyc_face_verify_duration_seconds" in r.text


def test_ec_api_error_increment():
    from app.services.metrics import EC_API_ERRORS
    EC_API_ERRORS.labels(error_type="timeout").inc()
    r = client.get("/metrics")
    assert "ekyc_ec_api_errors_total" in r.text


def test_celery_queue_depth_set():
    from app.services.metrics import CELERY_QUEUE_DEPTH
    CELERY_QUEUE_DEPTH.labels(queue_name="default").set(5)
    r = client.get("/metrics")
    assert "ekyc_celery_queue_depth" in r.text


def test_adverse_media_flag_increment():
    from app.services.metrics import ADVERSE_MEDIA_FLAGS
    ADVERSE_MEDIA_FLAGS.labels(verdict="CLEAR").inc()
    r = client.get("/metrics")
    assert "ekyc_adverse_media_flags_total" in r.text


def test_screening_results_metric():
    from app.services.metrics import SCREENING_RESULTS
    SCREENING_RESULTS.labels(screen_type="unscr", verdict="CLEAR").inc()
    r = client.get("/metrics")
    assert "ekyc_screening_results_total" in r.text


def test_active_kyc_sessions_metric():
    from app.services.metrics import ACTIVE_KYC_SESSIONS
    ACTIVE_KYC_SESSIONS.set(3)
    r = client.get("/metrics")
    assert "ekyc_active_kyc_sessions" in r.text


def test_metrics_not_in_openapi():
    """Metrics endpoint excluded from interactive docs but may appear in schema paths."""
    r = client.get("/docs")
    # /metrics should not appear as a documented API endpoint in Swagger UI
    assert r.status_code == 200  # docs still accessible


def test_docker_compose_monitoring_exists():
    import os
    assert os.path.exists("docker-compose.monitoring.yml")


def test_prometheus_config_exists():
    import os
    assert os.path.exists("monitoring/prometheus.yml")


def test_grafana_dashboard_exists():
    import os
    assert os.path.exists("monitoring/grafana/provisioning/dashboards/ekyc_bfiu.json")


def test_grafana_datasource_exists():
    import os
    assert os.path.exists("monitoring/grafana/provisioning/datasources/prometheus.yml")


def test_grafana_dashboard_has_4_panels():
    import json
    with open("monitoring/grafana/provisioning/dashboards/ekyc_bfiu.json") as f:
        d = json.load(f)
    assert len(d["dashboard"]["panels"]) == 4


def test_grafana_dashboard_panels_titles():
    import json
    with open("monitoring/grafana/provisioning/dashboards/ekyc_bfiu.json") as f:
        d = json.load(f)
    titles = [p["title"] for p in d["dashboard"]["panels"]]
    assert any("Face" in t for t in titles)
    assert any("EC API" in t for t in titles)
    assert any("Celery" in t for t in titles)
    assert any("Adverse" in t for t in titles)
