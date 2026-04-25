# M70-M75 Work Log — SSL, Security Scan, Flower, SOF, UNSCR Monitor, pgcrypto
Date: 2026-04-25 BST
BFIU Reference: Circular No. 29 §3.2.2, §4.2, §4.5

## M70: SSL/Certbot
- scripts/generate_self_signed_cert.sh — dev/staging self-signed cert
- docker-compose.prod.yml: certbot service added (profiles: production)
- nginx.conf: SSL config verified (TLSv1.2/1.3, HSTS, HTTP->HTTPS redirect)

## M71: Dependency vulnerability scan
- scripts/security_scan.sh — pip-audit + safety wrapper
- reports/ directory with .gitignore
- requirements.txt pinned and frozen

## M72: Celery Flower monitoring
- docker-compose.prod.yml: flower service (profiles: monitoring)
- Basic auth via FLOWER_USER/FLOWER_PASSWORD env vars

## M73: Source of funds verification (BFIU §4.2)
- app/services/source_of_funds_validator.py
- 12 allowed sources, OTHER requires explanation
- High-scrutiny sources (REMITTANCE, INHERITANCE, INVESTMENT, OTHER) flag document upload
- High income (>5M BDT/yr) without clear source flags for review
- Wired into submit_data_capture() for Regular eKYC
- Skipped for Simplified eKYC

## M74: UNSCR feed failure monitoring (BFIU §3.2.2)
- app/services/unscr_monitor.py — freshness check (24h max staleness)
- Logs CRITICAL if list stale, NEVER_PULLED if empty

## M75: pgcrypto verification
- scripts/verify_pgcrypto.sh — runtime pgcrypto check
- Confirmed in M54 migration + init.sql

## Test results
- M70-M75 tests: 25/25 passed
- Full suite: 1539 passed, 0 failures, 8 skipped
