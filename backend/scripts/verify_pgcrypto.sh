#!/bin/bash
# M75: Verify pgcrypto is installed and working
# BFIU §4.5 — AES-256 field encryption mandatory
echo "Verifying pgcrypto..."
PGPASSWORD="${POSTGRES_PASSWORD:-ekyc_pass}" psql \
    -h "${POSTGRES_HOST:-localhost}" \
    -U "${POSTGRES_USER:-ekyc_user}" \
    -d "${POSTGRES_DB:-ekyc_db}" \
    -c "SELECT pgp_sym_encrypt('test', 'key') IS NOT NULL AS pgcrypto_ok;" 2>/dev/null \
    && echo "pgcrypto: OK" \
    || echo "pgcrypto: FAILED — run: CREATE EXTENSION IF NOT EXISTS pgcrypto;"
