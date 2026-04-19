# Xpert eKYC Platform — Production Deployment Guide
BFIU Circular No. 29 Compliant | Deadline: December 31, 2026

## Prerequisites
- Ubuntu 22.04 LTS server (on-premise or private cloud — BFIU data residency)
- Docker + Docker Compose v2
- Domain with SSL certificate (Let's Encrypt or institution cert)
- Porichoy/EC API credentials from Election Commission

## Step 1 — Server Setup
```bash
apt update && apt install -y docker.io docker-compose-v2 nginx certbot
```

## Step 2 — Clone and configure
```bash
git clone https://github.com/EshanBarua14/eKYC.git /opt/ekyc
cd /opt/ekyc
cp backend/.env.example backend/.env
nano backend/.env  # Fill in all values
```

## Step 3 — Generate RSA keys for JWT
```bash
mkdir -p backend/keys
openssl genrsa -out backend/keys/private.pem 2048
openssl rsa -in backend/keys/private.pem -pubout -out backend/keys/public.pem
chmod 600 backend/keys/private.pem
```

## Step 4 — SSL Certificate
```bash
certbot certonly --standalone -d ekyc.yourcompany.com
mkdir -p nginx/ssl
cp /etc/letsencrypt/live/ekyc.yourcompany.com/fullchain.pem nginx/ssl/
cp /etc/letsencrypt/live/ekyc.yourcompany.com/privkey.pem nginx/ssl/
```

## Step 5 — Deploy
```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml logs -f
```

## Step 6 — Run migrations
```bash
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

## Step 7 — Verify
```bash
curl https://ekyc.yourcompany.com/health
# Expected: {"status":"healthy","db":"ok",...}
```

## Step 8 — PostgreSQL extensions (run once)
```bash
docker compose -f docker-compose.prod.yml exec postgres \
  psql -U ekyc_user -d ekyc_db -f /docker-entrypoint-initdb.d/init.sql
```

## Monitoring
- Logs: `docker compose logs -f backend`
- DB backup: `docker compose exec postgres pg_dump -U ekyc_user ekyc_db > backup.sql`
- Health: `curl /health`

## BFIU Compliance Checklist
- [ ] HTTPS enforced (HTTP redirects to HTTPS)
- [ ] Data stored on locally-hosted server
- [ ] No PII transmitted to non-whitelisted domains
- [ ] Audit logs enabled and immutable
- [ ] 5-year retention policy configured
- [ ] EC API credentials from Election Commission
- [ ] UNSCR list updated daily (cron job)
- [ ] Monthly BFIU report generated and submitted

## Emergency Contacts
- EC NID API support: nid@ec.gov.bd
- BFIU compliance: bfiu@bb.org.bd
- Implementation deadline: December 31, 2026
