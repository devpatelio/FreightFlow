-- 010: Additional performance indexes
-- Primary indexes are created in their respective table migrations.
-- This file adds composite and covering indexes for common query patterns.

-- Fast org lookup when validating JWTs
CREATE INDEX IF NOT EXISTS idx_org_members_user_org ON org_members(user_id, org_id);

-- Customer listing sorted by name within org
CREATE INDEX IF NOT EXISTS idx_customers_org_name ON customers(org_id, company_name);

-- Address lookup by type within org
CREATE INDEX IF NOT EXISTS idx_addresses_org_type ON addresses(org_id, address_type);

-- Document listing by type and status within org
CREATE INDEX IF NOT EXISTS idx_documents_org_type_status ON documents(org_id, document_type, status);

-- Document listing by creation date within org (for dashboard)
CREATE INDEX IF NOT EXISTS idx_documents_org_created ON documents(org_id, created_at DESC);

-- Pipeline runs by status within org (for monitoring)
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_org_status ON pipeline_runs(org_id, status);

-- Pipeline feedback for few-shot retrieval (by org + step)
CREATE INDEX IF NOT EXISTS idx_pipeline_feedback_org_step ON pipeline_feedback(org_id, step_name);

-- Document templates: active templates by org
CREATE INDEX IF NOT EXISTS idx_document_templates_org_active ON document_templates(org_id, is_active) WHERE is_active = true;

-- Invitation lookup by email (for signup flow)
CREATE INDEX IF NOT EXISTS idx_org_invitations_email_pending ON org_invitations(email) WHERE accepted_at IS NULL;
