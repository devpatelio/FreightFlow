# CLAUDE.md — AI Assistant Context for FreightFlow

## What This Project Is

FreightFlow is a logistics document automation platform. Users upload Purchase Order (PO) PDFs, and the system generates Bill of Lading (BOL) and Packing Slip PDFs using AI extraction (OpenAI) and PDF filling (Reducto).

The app is being rebuilt from a Flask/Jinja2 monolith into a Next.js + Flask API architecture with Supabase Auth and multi-tenant RLS.

## Architecture

- **Frontend**: Next.js 15 (App Router) with TypeScript, Tailwind CSS, shadcn/ui — lives in `frontend/`
- **Backend API**: Flask 3.x returning JSON — lives in `src/api/`
- **Legacy code**: `src/app.py`, `src/backend.py`, `src/supabase_service.py`, `src/modules.py` — being migrated to `src/api/`
- **Database**: Supabase Postgres with Row-Level Security. Migrations in `supabase/migrations/`
- **Storage**: Supabase Storage buckets (`document-uploads`, `generated-documents`, `templates`)
- **AI Pipeline**: OpenAI for PO→JSON extraction, Reducto for PDF parse and PDF fill

## Key Conventions

### Python (Backend)
- Use Pydantic v2 models for all request/response validation in `src/api/models/`
- Flask Blueprints for route modules in `src/api/routes/`
- Service layer pattern: routes call services, services call Supabase/AI
- All API routes are prefixed with `/api/` and return JSON
- Auth middleware validates Supabase JWTs and injects `org_id` into request context
- Never hardcode company-specific data — read from database (`seller_profiles`, `document_templates`)
- API keys are per-org (BYOK) — never use global env vars for OpenAI/Reducto in production code paths

### TypeScript (Frontend)
- Use App Router conventions (page.tsx, layout.tsx, loading.tsx, error.tsx)
- Supabase client for auth and direct DB reads; Flask API for document pipeline operations
- All components in `frontend/src/components/`, organized by feature
- Use shadcn/ui components as the base; extend with Tailwind utilities
- Type all API responses with interfaces in `frontend/src/lib/types.ts`

### Database
- Every tenant-scoped table has an `org_id UUID NOT NULL REFERENCES organizations(id)` column
- UUIDs for all primary keys (never app-managed integer counters)
- Timestamps: `created_at TIMESTAMPTZ DEFAULT now()`, `updated_at TIMESTAMPTZ DEFAULT now()`
- Use `snake_case` for all table and column names
- RLS policies on every tenant-scoped table
- Migrations are numbered sequentially in `supabase/migrations/`

### File Organization
- AI prompt templates: stored in `document_templates` table per org (legacy: `templates/*.txt`)
- PDF templates: stored in Supabase Storage `templates` bucket per org (legacy: `templates/*.pdf`)
- Form schemas: stored in `form_schemas` table per org

## Important Patterns

### Multi-Tenancy
All data is scoped to an organization. The RLS policy pattern:
```sql
CREATE POLICY "org_isolation" ON <table>
  USING (org_id = (SELECT org_id FROM org_members WHERE user_id = auth.uid() LIMIT 1));
```

### Document Pipeline Flow
1. Upload PO PDF → Reducto parse → chunks/blocks stored as `parsed_data` JSONB
2. OpenAI extracts structured JSON (BOL or PackingSlip format) using org's seller profile + prompt template
3. User reviews and can edit extracted JSON
4. Reducto Edit fills PDF template using natural-language instructions + form schema
5. Filled PDF saved to Supabase Storage, document records created with relationships

### BYOK (Bring Your Own Keys)
Each org provides their own OpenAI and Reducto API keys, stored encrypted in `org_api_keys`. The AI service decrypts keys per-request using the org context from the JWT.

## Things to Avoid

- Never import from `src/app.py` in new code — it's the legacy monolith being phased out
- Never hardcode "Hanson Chemicals" or any company-specific data
- Never store API keys in plaintext or log them
- Never use `session` for state — the API is stateless (JWT auth)
- Never use `render_template` in new routes — return JSON only
- Never create app-managed integer IDs for documents — use Postgres UUIDs
- Never write raw SQL in Python code — use the Supabase client or migrations
- Don't add dependencies without checking `requirements.txt` / `package.json` first

## Common Tasks

### Add a new API endpoint
1. Create or update the route in `src/api/routes/<module>.py`
2. Add Pydantic models in `src/api/models/types.py`
3. Add business logic in `src/api/services/<service>.py`
4. Register the Blueprint in `src/api/__init__.py` if new

### Add a new database table
1. Create a new migration file in `supabase/migrations/`
2. Add RLS policies in the same migration
3. Update `docs/database-schema.md`
4. Add service methods in the appropriate service file

### Modify the document pipeline
1. Read `docs/pipeline.md` first to understand the full flow
2. Pipeline steps are defined in `pipeline_definitions` table
3. Changes to extraction prompts should be documented in `docs/prompts.md`
4. Test with existing PO documents before deploying

## File Reference

| Path | Purpose |
|------|---------|
| `src/api/__init__.py` | Flask app factory with Blueprint registration |
| `src/api/routes/` | API route modules (one per resource) |
| `src/api/services/` | Business logic layer |
| `src/api/models/types.py` | Pydantic models |
| `src/api/auth.py` | JWT validation middleware |
| `frontend/src/app/` | Next.js pages and layouts |
| `frontend/src/components/` | React components |
| `frontend/src/lib/` | Supabase client, types, utilities |
| `supabase/migrations/` | SQL migration files |
| `templates/` | Legacy prompt templates (migrating to DB) |
| `docs/` | Architecture and design documentation |
