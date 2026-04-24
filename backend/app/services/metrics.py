"""
M57 — Prometheus custom metrics
BFIU Circular No. 29 observability
"""
from prometheus_client import Counter, Histogram, Gauge

# p99 face-verify latency
FACE_VERIFY_LATENCY = Histogram(
    "ekyc_face_verify_duration_seconds",
    "Face verification end-to-end latency",
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0],
)

# EC API error rate
EC_API_ERRORS = Counter(
    "ekyc_ec_api_errors_total",
    "EC NID API errors",
    ["error_type"],  # timeout | http_error | parse_error
)

EC_API_REQUESTS = Counter(
    "ekyc_ec_api_requests_total",
    "EC NID API requests total",
    ["status"],  # success | error
)

# Celery queue depth
CELERY_QUEUE_DEPTH = Gauge(
    "ekyc_celery_queue_depth",
    "Celery task queue depth",
    ["queue_name"],  # default | nid_verify | reports
)

# Adverse media flag rate
ADVERSE_MEDIA_FLAGS = Counter(
    "ekyc_adverse_media_flags_total",
    "Adverse media screening flags",
    ["verdict"],  # CLEAR | REVIEW | MATCH
)

# Screening results
SCREENING_RESULTS = Counter(
    "ekyc_screening_results_total",
    "UNSCR/PEP screening results",
    ["screen_type", "verdict"],  # unscr/pep/adverse × CLEAR/REVIEW/MATCH
)

# Active KYC sessions
ACTIVE_KYC_SESSIONS = Gauge(
    "ekyc_active_kyc_sessions",
    "Currently active KYC onboarding sessions",
)
