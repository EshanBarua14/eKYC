#!/bin/bash
# M71: Dependency vulnerability scan
# Run: bash scripts/security_scan.sh
# Requires: pip install pip-audit safety

set -e
echo "=== Xpert eKYC Security Scan ==="
echo "Date: $(TZ='Asia/Dhaka' date)"

# pip-audit
if command -v pip-audit &> /dev/null; then
    echo "--- pip-audit ---"
    pip-audit -r requirements.txt --format=json > reports/pip_audit_$(date +%Y%m%d).json
    pip-audit -r requirements.txt
else
    echo "pip-audit not installed. Run: pip install pip-audit"
    echo "pip-audit -r requirements.txt"
fi

# safety check
if command -v safety &> /dev/null; then
    echo "--- safety check ---"
    safety check -r requirements.txt
else
    echo "safety not installed. Run: pip install safety"
fi

echo "=== Scan complete ==="
echo "BFIU §4.5 — run before each production deployment"
