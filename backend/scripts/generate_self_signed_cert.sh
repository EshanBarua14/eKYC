#!/bin/bash
# Generate self-signed SSL cert for development/staging
# For production: use Certbot with Let's Encrypt
# BFIU §4.5 — HTTPS mandatory

CERT_DIR="${1:-../nginx/ssl}"
DOMAIN="${2:-ekyc.local}"

mkdir -p "${CERT_DIR}"

openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "${CERT_DIR}/privkey.pem" \
    -out "${CERT_DIR}/fullchain.pem" \
    -subj "/C=BD/ST=Dhaka/L=Dhaka/O=Xpert Fintech/OU=eKYC/CN=${DOMAIN}"

echo "Self-signed cert generated at ${CERT_DIR}"
echo "For production: run certbot certonly --webroot -w /var/www/certbot -d ${DOMAIN}"
echo "BFIU §4.5 — ensure valid SSL cert before go-live"
