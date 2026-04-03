-- 009: Row-Level Security policies for all tenant-scoped tables

-- Organizations: members can read their own orgs
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "org_member_select" ON organizations
  FOR SELECT USING (
    id IN (SELECT public.user_org_ids())
  );

CREATE POLICY "org_owner_update" ON organizations
  FOR UPDATE USING (
    id IN (
      SELECT org_id FROM org_members
      WHERE user_id = auth.uid() AND role IN ('owner', 'admin')
    )
  );

-- Org members: can see members of their own orgs
ALTER TABLE org_members ENABLE ROW LEVEL SECURITY;

CREATE POLICY "org_members_select" ON org_members
  FOR SELECT USING (org_id IN (SELECT public.user_org_ids()));

CREATE POLICY "org_members_admin_insert" ON org_members
  FOR INSERT WITH CHECK (
    org_id IN (
      SELECT org_id FROM org_members
      WHERE user_id = auth.uid() AND role IN ('owner', 'admin')
    )
  );

CREATE POLICY "org_members_owner_delete" ON org_members
  FOR DELETE USING (
    org_id IN (
      SELECT org_id FROM org_members
      WHERE user_id = auth.uid() AND role = 'owner'
    )
  );

-- Org invitations
ALTER TABLE org_invitations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "org_invitations_select" ON org_invitations
  FOR SELECT USING (org_id IN (SELECT public.user_org_ids()));

CREATE POLICY "org_invitations_admin_manage" ON org_invitations
  FOR ALL USING (
    org_id IN (
      SELECT org_id FROM org_members
      WHERE user_id = auth.uid() AND role IN ('owner', 'admin')
    )
  );

-- Org API keys: only admins/owners can manage, members can't see
ALTER TABLE org_api_keys ENABLE ROW LEVEL SECURITY;

CREATE POLICY "org_api_keys_admin" ON org_api_keys
  FOR ALL USING (
    org_id IN (
      SELECT org_id FROM org_members
      WHERE user_id = auth.uid() AND role IN ('owner', 'admin')
    )
  )
  WITH CHECK (
    org_id IN (
      SELECT org_id FROM org_members
      WHERE user_id = auth.uid() AND role IN ('owner', 'admin')
    )
  );

-- Customers
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;

CREATE POLICY "customers_org_isolation" ON customers
  FOR ALL
  USING (org_id IN (SELECT public.user_org_ids()))
  WITH CHECK (org_id IN (SELECT public.user_org_ids()));

-- Contacts
ALTER TABLE contacts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "contacts_org_isolation" ON contacts
  FOR ALL
  USING (org_id IN (SELECT public.user_org_ids()))
  WITH CHECK (org_id IN (SELECT public.user_org_ids()));

-- Addresses
ALTER TABLE addresses ENABLE ROW LEVEL SECURITY;

CREATE POLICY "addresses_org_isolation" ON addresses
  FOR ALL
  USING (org_id IN (SELECT public.user_org_ids()))
  WITH CHECK (org_id IN (SELECT public.user_org_ids()));

-- Seller profiles
ALTER TABLE seller_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "seller_profiles_org_isolation" ON seller_profiles
  FOR ALL
  USING (org_id IN (SELECT public.user_org_ids()))
  WITH CHECK (org_id IN (SELECT public.user_org_ids()));

-- Products
ALTER TABLE products ENABLE ROW LEVEL SECURITY;

CREATE POLICY "products_org_isolation" ON products
  FOR ALL
  USING (org_id IN (SELECT public.user_org_ids()))
  WITH CHECK (org_id IN (SELECT public.user_org_ids()));

-- Documents
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

CREATE POLICY "documents_org_isolation" ON documents
  FOR ALL
  USING (org_id IN (SELECT public.user_org_ids()))
  WITH CHECK (org_id IN (SELECT public.user_org_ids()));

-- Document relationships: accessible if PO document is accessible
ALTER TABLE document_relationships ENABLE ROW LEVEL SECURITY;

CREATE POLICY "document_relationships_via_po" ON document_relationships
  FOR ALL
  USING (
    po_document_id IN (SELECT id FROM documents WHERE org_id IN (SELECT public.user_org_ids()))
  )
  WITH CHECK (
    po_document_id IN (SELECT id FROM documents WHERE org_id IN (SELECT public.user_org_ids()))
  );

-- Document templates
ALTER TABLE document_templates ENABLE ROW LEVEL SECURITY;

CREATE POLICY "document_templates_org_isolation" ON document_templates
  FOR ALL
  USING (org_id IN (SELECT public.user_org_ids()))
  WITH CHECK (org_id IN (SELECT public.user_org_ids()));

-- Form schemas
ALTER TABLE form_schemas ENABLE ROW LEVEL SECURITY;

CREATE POLICY "form_schemas_org_isolation" ON form_schemas
  FOR ALL
  USING (org_id IN (SELECT public.user_org_ids()))
  WITH CHECK (org_id IN (SELECT public.user_org_ids()));

-- Generation configs
ALTER TABLE generation_configs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "generation_configs_org_isolation" ON generation_configs
  FOR ALL
  USING (org_id IN (SELECT public.user_org_ids()))
  WITH CHECK (org_id IN (SELECT public.user_org_ids()));

-- Pipeline definitions: org-scoped OR system-wide (org_id IS NULL)
ALTER TABLE pipeline_definitions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "pipeline_definitions_read" ON pipeline_definitions
  FOR SELECT USING (
    org_id IS NULL
    OR org_id IN (SELECT public.user_org_ids())
  );

CREATE POLICY "pipeline_definitions_write" ON pipeline_definitions
  FOR INSERT WITH CHECK (org_id IN (SELECT public.user_org_ids()));

CREATE POLICY "pipeline_definitions_update" ON pipeline_definitions
  FOR UPDATE USING (org_id IN (SELECT public.user_org_ids()));

CREATE POLICY "pipeline_definitions_delete" ON pipeline_definitions
  FOR DELETE USING (org_id IN (SELECT public.user_org_ids()));

-- Pipeline runs
ALTER TABLE pipeline_runs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "pipeline_runs_org_isolation" ON pipeline_runs
  FOR ALL
  USING (org_id IN (SELECT public.user_org_ids()))
  WITH CHECK (org_id IN (SELECT public.user_org_ids()));

-- Pipeline step runs: accessible via pipeline run
ALTER TABLE pipeline_step_runs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "pipeline_step_runs_via_run" ON pipeline_step_runs
  FOR ALL
  USING (
    pipeline_run_id IN (SELECT id FROM pipeline_runs WHERE org_id IN (SELECT public.user_org_ids()))
  );

-- Pipeline feedback
ALTER TABLE pipeline_feedback ENABLE ROW LEVEL SECURITY;

CREATE POLICY "pipeline_feedback_org_isolation" ON pipeline_feedback
  FOR ALL
  USING (org_id IN (SELECT public.user_org_ids()))
  WITH CHECK (org_id IN (SELECT public.user_org_ids()));
