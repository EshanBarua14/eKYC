#!/bin/bash
set -e
DOMAIN="${1:?Usage: $0 <domain>}"
apt-get install -y certbot
certbot certonly --standalone --agree-tos --no-eff-email \
  -m "admin@xpertfintech.com.bd" -d "$DOMAIN"
mkdir -p /etc/nginx/ssl
cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem /etc/nginx/ssl/
cp /etc/letsencrypt/live/$DOMAIN/privkey.pem   /etc/nginx/ssl/
chmod 600 /etc/nginx/ssl/privkey.pem
echo "0 3 * * * certbot renew --quiet && docker-compose exec nginx nginx -s reload" | crontab -u root -
echo "Done."
