#!/bin/bash
set -e
DOMAIN="${1:-localhost}"
OUT="$(dirname "$0")"
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout "$OUT/privkey.pem" -out "$OUT/fullchain.pem" \
  -subj "/CN=$DOMAIN/O=Xpert Fintech/C=BD" \
  -addext "subjectAltName=DNS:$DOMAIN,IP:127.0.0.1"
chmod 600 "$OUT/privkey.pem"
echo "Done. For production: sudo certbot certonly --standalone -d $DOMAIN"
