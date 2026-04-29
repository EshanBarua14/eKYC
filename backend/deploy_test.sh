#!/usr/bin/env bash
# deploy_test.sh — AlmaLinux test server bootstrap
# Run on SERVER via SSH as root or sudo user

set -euo pipefail

echo "=== STEP 1: Install Docker + Docker Compose ==="
dnf install -y dnf-plugins-core
dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
systemctl enable --now docker

echo "=== STEP 2: Install Git ==="
dnf install -y git openssl

echo "=== STEP 3: Clone repo ==="
cd /opt
git clone https://github.com/EshanBarua14/eKYC.git ekyc
cd ekyc/backend

echo "=== STEP 4: Generate secrets ==="
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
DB_PASSWORD=$(python3 -c "import secrets; print(secrets.token_hex(16))")
REDIS_PASSWORD=$(python3 -c "import secrets; print(secrets.token_hex(16))")

echo "SECRET_KEY=$SECRET_KEY"
echo "DB_PASSWORD=$DB_PASSWORD"
echo "REDIS_PASSWORD=$REDIS_PASSWORD"

echo "=== STEP 5: Build .env.production ==="
cp .env.production .env.production.bak
sed -i "s|SECRET_KEY=CHANGE_ME_REQUIRED_min_64_chars_hex|SECRET_KEY=$SECRET_KEY|" .env.production
sed -i "s|CHANGE_ME_DB_PASSWORD|$DB_PASSWORD|g" .env.production
sed -i "s|CHANGE_ME_REDIS_PASSWORD|$REDIS_PASSWORD|g" .env.production

echo "=== STEP 6: Create nginx dir + self-signed cert ==="
mkdir -p nginx/certs
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/certs/selfsigned.key \
  -out nginx/certs/selfsigned.crt \
  -subj "/C=BD/ST=Dhaka/L=Dhaka/O=Xpert Fintech/CN=ekyc-test"

echo "=== STEP 7: Copy nginx.conf ==="
cp nginx.conf nginx/nginx.conf  # assumes nginx.conf already in repo root

echo "=== STEP 8: Build + start ==="
docker compose up -d --build

echo "=== STEP 9: Wait for app health ==="
sleep 15
docker compose ps
curl -k https://localhost/health

echo "=== STEP 10: Run Alembic migrations ==="
docker compose exec app alembic upgrade head

echo "=== DONE. Test at: https://SERVER_IP/docs ==="
EOF