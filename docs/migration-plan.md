# Migration Plan

Strategy for migrating from the legacy single-tenant Supabase schema to the new multi-tenant schema with RLS.

## Current State (Legacy)

The legacy database has no `org_id`, no RLS, and uses app-managed integer `document_id` values. All data implicitly belongs to a single organization (Hanson Chemicals).

**Legacy tables:**
- `accounts` — customers
- `addresses` — linked to accounts or seller companies
- `seller_companies` — seller identity
- `products` — product catalog
- `documents` — POs, BOLs, Packing Slips (integer `document_id`, `bol_data`/`packing_slip_data` columns)
- `document_relationships` — links by integer `document_id`
- `form_schemas` — Reducto schemas

**Legacy filesystem artifacts:**
- `templates/HansonChemicals.txt` — company context prompt
- `templates/BOL_Template.txt` — BOL extraction prompt
- `templates/PackingSlip_Template.txt` — Packing Slip extraction prompt
- `templates/BOL_Template.pdf` — PDF template for Reducto fill
- `templates/PackingSlip_Template.pdf` — PDF template for Reducto fill

## Migration Strategy

### Approach: Fresh Schema + Data Seed

Rather than in-place ALTER TABLE migrations (which are risky with production data), we:

1. Create the new schema as entirely new tables
2. Write a seed migration that copies data from legacy tables into new tables
3. Run both schemas in parallel during transition
4. Drop legacy tables once the new system is fully validated

This avoids downtime and allows rollback.

### Step 1: Deploy New Schema (migrations 001-010)

Apply all migration files in order. This creates the new tables alongside the existing legacy tables. No data conflict — different table names.

### Step 2: Seed Hanson Chemicals Data (migration 011)

The seed migration:

1. **Create organization** — "Hanson Chemicals" with slug "hanson-chemicals"
2. **Map existing user** — The current admin user becomes `owner` in `org_members`
3. **Copy accounts → customers** — Map `customer_id` field to `customer_code`, assign `org_id`
4. **Copy addresses** — Relink from legacy `account_id`/`seller_company_id` to new `customer_id`, add `org_id`
5. **Copy seller_companies → seller_profiles** — Include `context_text` from `HansonChemicals.txt`
6. **Copy products** — Add `org_id`
7. **Copy documents** — Generate UUID PKs, convert integer `document_id` references, move `bol_data`/`packing_slip_data` to `generated_data`
8. **Copy document_relationships** — Remap to new UUID document IDs
9. **Copy form_schemas** — Add `org_id`
10. **Seed document_templates** — Import `BOL_Template.txt` and `PackingSlip_Template.txt` content into database

### Step 3: Validate

Run validation queries to confirm:
- All legacy data appears in new tables
- Document relationships are intact
- Form schemas are accessible
- RLS policies work (test as the org member user)

### Step 4: Cut Over

1. Update Flask API to use new schema (new `supabase_service.py`)
2. Deploy Next.js frontend pointing to new API
3. Monitor for errors

### Step 5: Clean Up

Once stable (1-2 weeks):
1. Drop legacy tables (`accounts`, `seller_companies`, legacy `documents`, etc.)
2. Remove `HansonChemicals.txt` from codebase
3. Remove legacy Flask routes and templates

## Data Mapping

### accounts → customers

| Legacy Column | New Column | Transform |
|--------------|-----------|-----------|
| id (UUID) | — | Generate new UUID |
| company_name | company_name | Direct copy |
| customer_id | customer_code | Rename |
| default_payment_terms | default_payment_terms | Direct copy |
| default_delivery_terms | default_delivery_terms | Direct copy |
| notes | notes | Direct copy |
| — | org_id | Set to Hanson org UUID |

### documents → documents

| Legacy Column | New Column | Transform |
|--------------|-----------|-----------|
| id (UUID) | — | — |
| document_id (INT) | — | Dropped (UUID PK instead) |
| document_type | document_type | Direct copy |
| document_name | document_name | Direct copy |
| account_id | customer_id | Remap via customers lookup |
| file_path | file_path | Direct copy |
| file_url | file_url | Direct copy |
| parsed_data | parsed_data | Direct copy |
| bol_data | — | Move to generated document's `generated_data` |
| packing_slip_data | — | Move to generated document's `generated_data` |
| status | status | Map to new enum values |
| — | org_id | Set to Hanson org UUID |

### HansonChemicals.txt → seller_profiles.context_text

The full text content of `HansonChemicals.txt` is stored in the `context_text` column of the org's seller profile. This allows the AI pipeline to read company context from the database instead of the filesystem.

## Rollback Plan

If migration fails:
1. The legacy tables are untouched — the old Flask app continues to work
2. Drop the new tables: `DROP TABLE IF EXISTS ... CASCADE`
3. Revert Flask API code to use legacy routes
4. Investigate and fix the issue, then retry

## Timeline

1. **Day 1**: Deploy new schema migrations (no data impact)
2. **Day 2**: Run seed migration in staging, validate
3. **Day 3**: Deploy new Flask API + Next.js frontend to staging
4. **Day 4-5**: End-to-end testing in staging
5. **Day 6**: Production seed migration + cutover
6. **Week 2-3**: Monitor, then clean up legacy tables
