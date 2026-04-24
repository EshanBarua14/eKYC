# M57 — Prometheus + Grafana Observability
**Date:** 2026-04-24
**Sprint:** BFIU Circular No. 29 Compliance — P2 Observability
**Status:** COMPLETE ✅

## Objective
Expose /metrics endpoint, custom business metrics, Docker monitoring
stack with Grafana dashboards for BFIU compliance observability.

## Files Created
| File | Purpose |
|------|---------|
| `app/services/metrics.py` | Custom Prometheus metrics |
| `docker-compose.monitoring.yml` | Prometheus + Grafana stack |
| `monitoring/prometheus.yml` | Prometheus scrape config |
| `monitoring/grafana/provisioning/datasources/prometheus.yml` | Grafana datasource |
| `monitoring/grafana/provisioning/dashboards/dashboards.yml` | Dashboard provisioning |
| `monitoring/grafana/provisioning/dashboards/ekyc_bfiu.json` | 4-panel dashboard |
| `tests/test_m57_prometheus.py` | 21 tests |

## Files Modified
| File | Change |
|------|--------|
| `app/main.py` | Instrumentator wired, /metrics exposed |

## Custom Metrics
| Metric | Type | Purpose |
|--------|------|---------|
| `ekyc_face_verify_duration_seconds` | Histogram | p99 face-verify latency |
| `ekyc_ec_api_errors_total` | Counter | EC API error rate by type |
| `ekyc_ec_api_requests_total` | Counter | EC API request volume |
| `ekyc_celery_queue_depth` | Gauge | Redis/Celery queue depth |
| `ekyc_adverse_media_flags_total` | Counter | Adverse media flag rate |
| `ekyc_screening_results_total` | Counter | UNSCR/PEP screening verdicts |
| `ekyc_active_kyc_sessions` | Gauge | Active onboarding sessions |

## Grafana Dashboards (4 panels)
- Face Verify p99 Latency
- EC API Error Rate by error_type
- Celery Queue Depth by queue_name
- Adverse Media Flag Rate by verdict

## To Start Monitoring Stack
```bash
docker-compose -f docker-compose.monitoring.yml up -d
# Prometheus: http://localhost:9090
# Grafana:    http://localhost:3001  (admin / ekyc_admin)
```

## Test Results
- M57 suite: 21 passed
- Full suite: 1242 passed, 0 failed
