# Database Schema Reference

All tables live in a single Supabase Postgres database. Multi-tenancy is enforced via Row-Level Security (RLS) with `org_id` on every tenant-scoped table.

## Entity Relationship Overview

```
organizations ─┬── org_members ──── auth.users
               ├── org_invitations
               ├── org_api_keys
               ├── seller_profiles
               ├── customers ──── contacts
               │                  addresses (customer)
               ├── addresses (org warehouses)
               ├── products
               ├── documents ──── document_relationships
               ├── document_templates
               ├── form_schemas
               ├── generation_configs
               └── pipeline_definitions ──── pipeline_runs ──── pipeline_step_runs
                                                              pipeline_feedback
```

## Tables

### organizations

Top-level tenant entity. Every org represents a company using FreightFlow.

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | |
| name | TEXT | NOT NULL | Company display name |
| slug | TEXT | NOT NULL, UNIQUE | URL-safe identifier |
| settings | JSONB | DEFAULT '{}' | Org-wide settings (timezone, defaults, etc.) |
| onboarding_completed_at | TIMESTAMPTZ | | Set when org finishes setup |
| created_at | TIMESTAMPTZ | DEFAULT now() | |
| updated_at | TIMESTAMPTZ | DEFAULT now() | |

### org_members

Maps authenticated users to organizations with role-based access.

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | |
| org_id | UUID | NOT NULL, FK → organizations(id) ON DELETE CASCADE | |
| user_id | UUID | NOT NULL, FK → auth.users(id) ON DELETE CASCADE | |
| role | TEXT | NOT NULL, CHECK (role IN ('owner', 'admin', 'member')) | |
| created_at | TIMESTAMPTZ | DEFAULT now() | |
| | | UNIQUE(org_id, user_id) | One membership per org per user |

### org_invitations

Pending email invitations to join an organization.

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | |
| org_id | UUID | NOT NULL, FK → organizations(id) ON DELETE CASCADE | |
| email | TEXT | NOT NULL | Invitee email |
| role | TEXT | NOT NULL, DEFAULT 'member' | Role to assign on acceptance |
| invited_by | UUID | NOT NULL, FK → auth.users(id) | |
| expires_at | TIMESTAMPTZ | NOT NULL | Invitation expiry |
| accepted_at | TIMESTAMPTZ | | Set when accepted |
| created_at | TIMESTAMPTZ | DEFAULT now() | |

### org_api_keys

Encrypted storage for org-provided API keys (BYOK model).

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | |
| org_id | UUID | NOT NULL, FK → organizations(id) ON DELETE CASCADE | |
| provider | TEXT | NOT NULL, CHECK (provider IN ('openai', 'reducto')) | |
| encrypted_key | TEXT | NOT NULL | Encrypted via pgcrypto |
| key_hint | TEXT | | Last 4 chars for display |
| added_by | UUID | FK → auth.users(id) | Who added this key |
| last_used_at | TIMESTAMPTZ | | Updated on each API call |
| created_at | TIMESTAMPTZ | DEFAULT now() | |
| | | UNIQUE(org_id, provider) | One key per provider per org |

### customers

Client companies that the org does business with. Replaces legacy `accounts` table.

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | |
| org_id | UUID | NOT NULL, FK → organizations(id) ON DELETE CASCADE | |
| company_name | TEXT | NOT NULL | |
| customer_code | TEXT | | Short identifier (e.g., "SOL" for Solenis) |
| default_payment_terms | TEXT | DEFAULT 'NET 90 DAYS' | |
| default_delivery_terms | TEXT | DEFAULT 'Free Carrier DESTINATION' | |
| notes | TEXT | | |
| created_at | TIMESTAMPTZ | DEFAULT now() | |
| updated_at | TIMESTAMPTZ | DEFAULT now() | |
| | | UNIQUE(org_id, customer_code) | Codes unique within org |

### contacts

People at customer companies. Normalized out of the customer record.

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | |
| org_id | UUID | NOT NULL, FK → organizations(id) ON DELETE CASCADE | |
| customer_id | UUID | NOT NULL, FK → customers(id) ON DELETE CASCADE | |
| name | TEXT | NOT NULL | |
| email | TEXT | | |
| phone | TEXT | | |
| role | TEXT | | Job title or role description |
| is_primary | BOOLEAN | DEFAULT false | Primary contact for this customer |
| created_at | TIMESTAMPTZ | DEFAULT now() | |

### addresses

Polymorphic address table — can belong to a customer (ship-to) or an org (ship-from/warehouse).

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | |
| org_id | UUID | NOT NULL, FK → organizations(id) ON DELETE CASCADE | |
| customer_id | UUID | FK → customers(id) ON DELETE CASCADE | Set for customer addresses |
| name | TEXT | NOT NULL | Location name |
| label | TEXT | | Friendly label (e.g., "US Distribution Center") |
| address_line | TEXT | NOT NULL | Street address |
| city | TEXT | NOT NULL | |
| state | TEXT | NOT NULL | |
| zip_code | TEXT | NOT NULL | |
| country | TEXT | NOT NULL, DEFAULT 'USA' | |
| phone | TEXT | | |
| email | TEXT | | |
| address_type | TEXT | NOT NULL, CHECK (address_type IN ('shipping', 'billing', 'warehouse', 'office')) | |
| is_default | BOOLEAN | DEFAULT false | Default address for its type |
| created_at | TIMESTAMPTZ | DEFAULT now() | |
| updated_at | TIMESTAMPTZ | DEFAULT now() | |

When `customer_id` is NULL, the address belongs to the org (e.g., their warehouses). When `customer_id` is set, it's a customer ship-to address.

### seller_profiles

The org's own business identity used in document generation. Replaces the legacy `seller_companies` table and `HansonChemicals.txt` file.

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | |
| org_id | UUID | NOT NULL, FK → organizations(id) ON DELETE CASCADE | |
| company_name | TEXT | NOT NULL | Legal company name |
| display_name | TEXT | | Name shown on documents |
| default_salesperson | TEXT | | |
| phone | TEXT | | |
| email | TEXT | | |
| context_text | TEXT | | Free-form context for AI prompts (replaces HansonChemicals.txt) |
| is_default | BOOLEAN | DEFAULT false | |
| created_at | TIMESTAMPTZ | DEFAULT now() | |
| updated_at | TIMESTAMPTZ | DEFAULT now() | |

### products

Product catalog per organization.

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | |
| org_id | UUID | NOT NULL, FK → organizations(id) ON DELETE CASCADE | |
| name | TEXT | NOT NULL | |
| description | TEXT | | |
| item_number | TEXT | | SKU or item code |
| un_code | TEXT | | UN hazmat code |
| default_unit_type | TEXT | DEFAULT 'kg' | kg, lb |
| default_handling_unit_type | TEXT | DEFAULT 'IBC' | IBC, Drum, Pallet, Box |
| notes | TEXT | | |
| created_at | TIMESTAMPTZ | DEFAULT now() | |
| updated_at | TIMESTAMPTZ | DEFAULT now() | |

### documents

Unified document store for POs, BOLs, and Packing Slips.

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | |
| org_id | UUID | NOT NULL, FK → organizations(id) ON DELETE CASCADE | |
| customer_id | UUID | FK → customers(id) ON DELETE SET NULL | Associated customer |
| document_type | TEXT | NOT NULL, CHECK (document_type IN ('PO', 'BOL', 'PACKING_SLIP')) | |
| document_name | TEXT | NOT NULL | Original filename |
| status | TEXT | NOT NULL, DEFAULT 'uploaded', CHECK (status IN ('uploaded', 'parsing', 'parsed', 'extracting', 'extracted', 'generating', 'generated', 'error')) | |
| file_path | TEXT | | Path in Supabase Storage |
| file_url | TEXT | | Public or signed URL |
| parsed_data | JSONB | | Reducto parse output (chunks, blocks) |
| generated_data | JSONB | | AI-extracted structured data (BOL/PS JSON) |
| created_at | TIMESTAMPTZ | DEFAULT now() | |
| updated_at | TIMESTAMPTZ | DEFAULT now() | |

### document_relationships

Links PO documents to their generated BOL and Packing Slip documents.

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | |
| po_document_id | UUID | NOT NULL, FK → documents(id) ON DELETE CASCADE | Source PO |
| generated_document_id | UUID | NOT NULL, FK → documents(id) ON DELETE CASCADE | Generated BOL/PS |
| relationship_type | TEXT | NOT NULL, CHECK (relationship_type IN ('BOL', 'PACKING_SLIP')) | |
| created_at | TIMESTAMPTZ | DEFAULT now() | |

### document_templates

Stores prompt templates and PDF template references per org. Replaces the local `templates/*.txt` and `templates/*.pdf` files.

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | |
| org_id | UUID | NOT NULL, FK → organizations(id) ON DELETE CASCADE | |
| name | TEXT | NOT NULL | Template identifier (e.g., "bol_extraction", "ps_extraction") |
| template_type | TEXT | NOT NULL, CHECK (template_type IN ('prompt', 'pdf')) | |
| content | TEXT | | Prompt text content (for prompt type) |
| storage_path | TEXT | | Supabase Storage path (for pdf type) |
| description | TEXT | | |
| version | INTEGER | DEFAULT 1 | Template version for tracking changes |
| is_active | BOOLEAN | DEFAULT true | |
| created_at | TIMESTAMPTZ | DEFAULT now() | |
| updated_at | TIMESTAMPTZ | DEFAULT now() | |
| | | UNIQUE(org_id, name, version) | |

### form_schemas

Reducto form schemas that describe field locations on PDF templates.

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | |
| org_id | UUID | NOT NULL, FK → organizations(id) ON DELETE CASCADE | |
| template_name | TEXT | NOT NULL | PDF template this schema applies to |
| schema | JSONB | NOT NULL | Array of field definitions with bbox, description, type |
| num_fields | INTEGER | | Count of fields in schema |
| template_file_id | TEXT | | Reducto file ID for the template |
| description | TEXT | | |
| created_at | TIMESTAMPTZ | DEFAULT now() | |
| updated_at | TIMESTAMPTZ | DEFAULT now() | |
| | | UNIQUE(org_id, template_name) | |

### generation_configs

Per-org AI generation settings.

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | |
| org_id | UUID | NOT NULL, FK → organizations(id) ON DELETE CASCADE, UNIQUE | |
| default_model | TEXT | DEFAULT 'gpt-5.4' | OpenAI model for extraction |
| temperature | NUMERIC(3,2) | DEFAULT 0.0 | |
| enable_few_shot | BOOLEAN | DEFAULT true | Include past examples in prompts |
| max_few_shot_examples | INTEGER | DEFAULT 3 | |
| default_edit_options | JSONB | DEFAULT '{}' | Reducto edit options |
| created_at | TIMESTAMPTZ | DEFAULT now() | |
| updated_at | TIMESTAMPTZ | DEFAULT now() | |

### pipeline_definitions

Named pipeline variants with ordered step configurations.

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | |
| org_id | UUID | FK → organizations(id) ON DELETE CASCADE | NULL for system-wide defaults |
| name | TEXT | NOT NULL | Pipeline name (e.g., "default_bol") |
| document_type | TEXT | NOT NULL | Target document type |
| steps | JSONB | NOT NULL | Array of step configurations |
| is_default | BOOLEAN | DEFAULT false | |
| description | TEXT | | |
| created_at | TIMESTAMPTZ | DEFAULT now() | |
| updated_at | TIMESTAMPTZ | DEFAULT now() | |

### pipeline_runs

Execution log for pipeline runs.

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | |
| org_id | UUID | NOT NULL, FK → organizations(id) ON DELETE CASCADE | |
| pipeline_definition_id | UUID | FK → pipeline_definitions(id) ON DELETE SET NULL | |
| document_id | UUID | FK → documents(id) ON DELETE SET NULL | Source document |
| status | TEXT | NOT NULL, DEFAULT 'pending', CHECK (status IN ('pending', 'running', 'completed', 'failed')) | |
| started_at | TIMESTAMPTZ | | |
| completed_at | TIMESTAMPTZ | | |
| duration_ms | INTEGER | | |
| total_cost | JSONB | | Cost breakdown by provider |
| error_message | TEXT | | |
| created_at | TIMESTAMPTZ | DEFAULT now() | |

### pipeline_step_runs

Per-step execution log within a pipeline run.

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | |
| pipeline_run_id | UUID | NOT NULL, FK → pipeline_runs(id) ON DELETE CASCADE | |
| step_name | TEXT | NOT NULL | Step identifier |
| step_type | TEXT | NOT NULL | parse, extract, fill |
| provider | TEXT | | openai, reducto |
| model | TEXT | | Model used (e.g., gpt-5.4) |
| input_tokens | INTEGER | | |
| output_tokens | INTEGER | | |
| credits_used | NUMERIC | | Reducto credits |
| duration_ms | INTEGER | | |
| status | TEXT | NOT NULL, DEFAULT 'pending' | |
| error_message | TEXT | | |
| created_at | TIMESTAMPTZ | DEFAULT now() | |

### pipeline_feedback

User corrections on generated fields. Used for few-shot learning.

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | |
| org_id | UUID | NOT NULL, FK → organizations(id) ON DELETE CASCADE | |
| pipeline_run_id | UUID | FK → pipeline_runs(id) ON DELETE SET NULL | |
| step_name | TEXT | NOT NULL | Which step produced the incorrect output |
| field_path | TEXT | NOT NULL | Dot-notation path (e.g., "ship_to.name") |
| original_value | TEXT | | What the AI produced |
| corrected_value | TEXT | | What the user changed it to |
| created_by | UUID | FK → auth.users(id) | |
| created_at | TIMESTAMPTZ | DEFAULT now() | |

## RLS Policy Pattern

Every tenant-scoped table uses this policy:

```sql
ALTER TABLE <table_name> ENABLE ROW LEVEL SECURITY;

CREATE POLICY "org_isolation" ON <table_name>
  FOR ALL
  USING (
    org_id IN (
      SELECT om.org_id FROM org_members om WHERE om.user_id = auth.uid()
    )
  )
  WITH CHECK (
    org_id IN (
      SELECT om.org_id FROM org_members om WHERE om.user_id = auth.uid()
    )
  );
```

For `pipeline_definitions` (which allows NULL `org_id` for system defaults):

```sql
CREATE POLICY "org_or_system" ON pipeline_definitions
  FOR SELECT
  USING (
    org_id IS NULL
    OR org_id IN (SELECT om.org_id FROM org_members om WHERE om.user_id = auth.uid())
  );

CREATE POLICY "org_write" ON pipeline_definitions
  FOR INSERT
  WITH CHECK (
    org_id IN (SELECT om.org_id FROM org_members om WHERE om.user_id = auth.uid())
  );
```

## Indexes

Key indexes beyond primary keys:

```sql
CREATE INDEX idx_org_members_user ON org_members(user_id);
CREATE INDEX idx_org_members_org ON org_members(org_id);
CREATE INDEX idx_customers_org ON customers(org_id);
CREATE INDEX idx_addresses_org ON addresses(org_id);
CREATE INDEX idx_addresses_customer ON addresses(customer_id);
CREATE INDEX idx_documents_org ON documents(org_id);
CREATE INDEX idx_documents_customer ON documents(customer_id);
CREATE INDEX idx_documents_type ON documents(org_id, document_type);
CREATE INDEX idx_document_relationships_po ON document_relationships(po_document_id);
CREATE INDEX idx_pipeline_runs_org ON pipeline_runs(org_id);
CREATE INDEX idx_pipeline_runs_document ON pipeline_runs(document_id);
CREATE INDEX idx_pipeline_feedback_org ON pipeline_feedback(org_id);
```

## Migration from Legacy Schema

The legacy schema has these tables (no `org_id`, no RLS):
- `accounts` → `customers`
- `addresses` → `addresses` (add `org_id`, rename `account_id` → `customer_id`, rename `address` → `address_line`)
- `seller_companies` → `seller_profiles`
- `products` → `products` (add `org_id`)
- `documents` → `documents` (UUID PK, drop integer `document_id`, move `bol_data`/`packing_slip_data` to `generated_data`)
- `document_relationships` → `document_relationships` (use UUID references)
- `form_schemas` → `form_schemas` (add `org_id`)

See [`migration-plan.md`](migration-plan.md) for the full migration strategy.
