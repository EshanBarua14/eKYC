-- Run this after initial create_all to fix schema gaps
-- 1. Expand role column
ALTER TABLE users ALTER COLUMN role TYPE VARCHAR(32);

-- 2. Add missing PEP columns
ALTER TABLE pep_entries ADD COLUMN IF NOT EXISTS passport_number VARCHAR(50);
ALTER TABLE pep_entries ADD COLUMN IF NOT EXISTS source_reference VARCHAR(255);

-- 3. Fix notification_logs
ALTER TABLE notification_logs ALTER COLUMN id TYPE VARCHAR(36);
ALTER TABLE notification_logs ALTER COLUMN session_id DROP NOT NULL;

-- 4. Add missing audit_logs id default
-- (already VARCHAR, just ensure it has gen_random_uuid default)
