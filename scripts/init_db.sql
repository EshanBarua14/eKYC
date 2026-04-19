-- Xpert eKYC Platform — PostgreSQL initialization
-- Run once before first deployment

-- Extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;      -- field-level encryption
CREATE EXTENSION IF NOT EXISTS pg_trgm;       -- fuzzy text search for screening
CREATE EXTENSION IF NOT EXISTS unaccent;      -- Bangla name normalization

-- Row-level security on KYC profiles (multi-tenant isolation)
-- Enable after tables are created by Alembic
-- ALTER TABLE kyc_profiles ENABLE ROW LEVEL SECURITY;
