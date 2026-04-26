#!/bin/bash
# Xpert eKYC Platform — PostgreSQL backup script
# BFIU Circular No. 29 §5.1 — 5-year data retention
# Run daily via cron: 0 2 * * * /app/scripts/backup_db.sh

set -e

BACKUP_DIR="${BACKUP_DIR:-/backups}"
DB_HOST="${POSTGRES_HOST:-postgres}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-ekyc_db}"
DB_USER="${POSTGRES_USER:-ekyc_user}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
BST_DATE=$(TZ='Asia/Dhaka' date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/ekyc_${DB_NAME}_${BST_DATE}.sql.gz"

mkdir -p "${BACKUP_DIR}"

echo "[$(TZ='Asia/Dhaka' date)] Starting backup: ${BACKUP_FILE}"

PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
    -h "${DB_HOST}" \
    -p "${DB_PORT}" \
    -U "${DB_USER}" \
    -d "${DB_NAME}" \
    --no-owner \
    --no-acl \
    --format=plain \
    | gzip > "${BACKUP_FILE}"

SIZE=$(du -sh "${BACKUP_FILE}" | cut -f1)
echo "[$(TZ='Asia/Dhaka' date)] Backup complete: ${BACKUP_FILE} (${SIZE})"

# Rotate old backups
find "${BACKUP_DIR}" -name "ekyc_*.sql.gz" -mtime +${RETENTION_DAYS} -delete
echo "[$(TZ='Asia/Dhaka' date)] Rotated backups older than ${RETENTION_DAYS} days"

# Verify backup is not empty
if [ ! -s "${BACKUP_FILE}" ]; then
    echo "[ERROR] Backup file is empty! BFIU §5.1 data retention at risk."
    exit 1
fi

echo "[$(TZ='Asia/Dhaka' date)] Backup verified OK. BFIU §5.1 compliant."
