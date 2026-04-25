# M66 Work Log — CORS Lock + Admin IP Whitelist + Alertmanager Rules
Date: 2026-04-25 BST
BFIU Reference: Circular No. 29 §4.5

## What was built
- app/middleware/admin_ip_whitelist.py — AdminIPWhitelistMiddleware
- backend/monitoring/alertmanager_rules.yml — 8 Prometheus alert rules
- app/core/config.py — CORS localhost warning in production mode
- app/main.py — AdminIPWhitelistMiddleware wired

## Features
### Admin IP Whitelist
- Protects /api/v1/admin/*, /api/v1/pep/entries, /api/v1/users, /api/v1/institutions
- ADMIN_IP_WHITELIST env var (comma-separated IPs)
- Empty = allow all (dev mode)
- X-Forwarded-For header respected for reverse proxy deployments
- HTTP 403 with BFIU §4.5 reference on block

### Alertmanager Rules (8 alerts)
- UNSCRFeedStale: sanctions list not updated in 24h (BFIU §3.2.2)
- EDDCasesOverdue: EDD past 1-month SLA (BFIU §4.3)
- HighRejectionRate: >30% KYC rejections in 1h
- APIHighErrorRate: >5% 5xx responses
- APIDown: backend health check failing
- CeleryWorkerDown: adverse media + EDD tasks not running (BFIU §5.3)
- DatabaseConnectionsHigh: >80/100 connections
- RedisMemoryHigh: >85% memory

### CORS
- Warns in production if localhost in ALLOWED_ORIGINS
- Set ALLOWED_ORIGINS to production domain in .env.production

## Test results
- M66 tests: 16/16 passed
- Full suite: 1460 passed, 0 failures, 7 skipped
