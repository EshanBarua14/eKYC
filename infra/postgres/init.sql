-- Xpert Fintech eKYC Platform
-- PostgreSQL initialization script
-- Multi-tenant schema setup (BFIU Circular No. 29)

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

-- Public schema is the default tenant (shared/system tables)
-- Each institution gets its own schema at onboarding time

-- Institutions registry (lives in public schema)
CREATE TABLE IF NOT EXISTS public.institutions (
    id              SERIAL PRIMARY KEY,
    code            VARCHAR(20) UNIQUE NOT NULL,
    name            VARCHAR(255) NOT NULL,
    type            VARCHAR(20) NOT NULL CHECK (type IN ('insurance', 'cmi')),
    schema_name     VARCHAR(63) UNIQUE NOT NULL,
    is_active       BOOLEAN DEFAULT TRUE,
    ip_whitelist    TEXT[],
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Audit log (lives in public schema, partitioned by tenant)
CREATE TABLE IF NOT EXISTS public.audit_log (
    id              BIGSERIAL PRIMARY KEY,
    institution_id  INTEGER REFERENCES public.institutions(id),
    actor_id        INTEGER,
    action          VARCHAR(100) NOT NULL,
    resource        VARCHAR(100),
    resource_id     VARCHAR(100),
    ip_address      INET,
    payload         JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_institution ON public.audit_log(institution_id);
CREATE INDEX IF NOT EXISTS idx_audit_created ON public.audit_log(created_at);

-- Insert default demo institution
INSERT INTO public.institutions (code, name, type, schema_name)
VALUES ('DEMO', 'Demo Insurance Co.', 'insurance', 'tenant_demo')
ON CONFLICT (code) DO NOTHING;

-- Create demo tenant schema
CREATE SCHEMA IF NOT EXISTS tenant_demo;

RAISE NOTICE 'eKYC database initialized successfully';
