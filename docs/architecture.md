# Architecture

## System Overview

FreightFlow is a multi-tenant logistics document automation platform. It processes Purchase Order PDFs into Bill of Lading and Packing Slip documents using AI-powered extraction and PDF filling.

```
┌─────────────────────────────────────────────────────────────────┐
│                        Clients (Browser)                        │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                ┌───────────▼───────────┐
                │   Next.js Frontend    │
                │   (Vercel)            │
                │                       │
                │   - Auth UI           │
                │   - Dashboard         │
                │   - CRUD pages        │
                │   - Document pipeline │
                │   - PDF viewer        │
                └───┬───────────┬───────┘
                    │           │
        Direct DB   │           │  Pipeline
        reads/auth  │           │  operations
                    ▼           ▼
        ┌───────────────┐  ┌──────────────────┐
        │   Supabase    │  │   Flask API      │
        │               │  │   (Railway)      │
        │   - Auth      │  │                  │
        │   - Postgres  │  │   - /api/docs    │
        │   - Storage   │  │   - /api/schemas │
        │   - RLS       │  │   - AI pipeline  │
        └───────────────┘  └───────┬──────────┘
                                   │
                        ┌──────────┼──────────┐
                        ▼          ▼          ▼
                   ┌─────────┐ ┌───────┐ ┌──────────┐
                   │ OpenAI  │ │Reducto│ │ Supabase │
                   │ (BYOK)  │ │(BYOK) │ │ (DB+S3)  │
                   └─────────┘ └───────┘ └──────────┘
```

## Design Decisions

### Why Next.js + Flask (not full Next.js)?

The document generation pipeline involves long-running operations (Reducto parse: 5-15s, OpenAI extraction: 3-10s, Reducto fill: 5-15s). These exceed typical serverless function timeouts and require persistent connections to AI services. Flask on Railway provides:

- Long-running request support (no 10s timeout)
- Persistent AI client connections
- Simpler secret management for per-org API keys
- Python ecosystem for AI/ML libraries

The Next.js frontend handles auth, routing, and direct Supabase reads (fast, no backend needed). Only pipeline operations go through Flask.

### Why Single Database with RLS (not DB-per-tenant)?

- Simpler operations: one connection string, one migration path, one backup
- Supabase RLS is battle-tested and enforced at the database level
- Scales to thousands of orgs without connection pool exhaustion
- Cross-org analytics possible when needed (admin queries)
- Migration to DB-per-tenant is possible later if a customer requires full isolation

### Why BYOK (Bring Your Own Keys)?

- FreightFlow's value is the pipeline and UX, not API key management
- Eliminates AI cost subsidization — each org pays their own OpenAI/Reducto bills
- Customers retain full control over their API usage and billing
- Simplifies FreightFlow's pricing to a pure SaaS subscription

## Multi-Tenancy Model

```
organizations
    │
    ├── org_members (user ↔ org mapping with roles)
    │
    ├── org_api_keys (encrypted OpenAI/Reducto keys)
    │
    ├── customers (org's clients)
    │   └── contacts
    │   └── addresses (customer ship-to addresses)
    │
    ├── addresses (org's own warehouses/offices)
    │
    ├── seller_profiles (org's business identity for documents)
    │
    ├── products (org's product catalog)
    │
    ├── documents (POs, BOLs, Packing Slips)
    │   └── document_relationships (PO → BOL/PS links)
    │
    ├── document_templates (prompt templates + PDF template refs)
    │
    ├── form_schemas (Reducto field schemas per template)
    │
    ├── generation_configs (AI settings, model preferences)
    │
    └── pipeline_definitions (pipeline step configurations)
        └── pipeline_runs → pipeline_step_runs
        └── pipeline_feedback (user corrections)
```

Every table except `organizations` itself has an `org_id` column. RLS policies enforce that authenticated users can only see data for orgs they belong to.

## API Design

### Routing Convention

```
/api/organizations          — Org management
/api/organizations/keys     — API key management
/api/customers              — Customer CRUD
/api/customers/:id/contacts — Customer contacts
/api/addresses              — Address CRUD
/api/sellers                — Seller profile CRUD
/api/products               — Product catalog CRUD
/api/documents              — Document CRUD + pipeline operations
/api/documents/upload       — PO upload + parse
/api/documents/:id/extract  — AI extraction (BOL/PS JSON)
/api/documents/:id/generate — PDF generation (Reducto fill)
/api/templates              — Prompt + PDF template management
/api/schemas                — Form schema management
/api/pipelines              — Pipeline definition management
/api/pipelines/runs         — Pipeline run history
```

### Authentication Flow

1. User signs in via Supabase Auth (Next.js frontend)
2. Frontend receives JWT containing `user_id`
3. For Flask API calls, JWT is sent in `Authorization: Bearer <token>` header
4. Flask middleware validates JWT signature against Supabase JWT secret
5. Middleware extracts `user_id`, queries `org_members` to get `org_id`
6. `org_id` is injected into the request context for use by route handlers
7. All service calls are scoped to `org_id`

### Error Handling

All API errors return consistent JSON:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Customer name is required",
    "details": { "field": "company_name" }
  }
}
```

Standard HTTP status codes: 200 (success), 201 (created), 400 (validation), 401 (unauthorized), 403 (forbidden), 404 (not found), 500 (server error).

## Frontend Architecture

### Page Structure

```
frontend/src/app/
├── (auth)/
│   ├── login/page.tsx
│   ├── signup/page.tsx
│   └── onboarding/page.tsx       # Org setup + API keys
├── (dashboard)/
│   ├── layout.tsx                # Sidebar nav + breadcrumbs
│   ├── page.tsx                  # Dashboard home
│   ├── customers/
│   │   ├── page.tsx              # Customer list
│   │   ├── [id]/page.tsx         # Customer detail
│   │   └── new/page.tsx          # Create customer
│   ├── addresses/page.tsx
│   ├── seller/page.tsx           # Org seller profile (single page)
│   ├── products/page.tsx
│   ├── documents/
│   │   ├── page.tsx              # Document list
│   │   ├── upload/page.tsx       # PO upload
│   │   ├── [id]/review/page.tsx  # Review + edit extracted data
│   │   └── [id]/page.tsx         # Document detail + PDF viewer
│   ├── templates/page.tsx
│   ├── schemas/page.tsx
│   ├── pipelines/page.tsx
│   └── settings/
│       ├── page.tsx              # Org settings
│       ├── members/page.tsx
│       └── keys/page.tsx         # API key management
└── layout.tsx                    # Root layout
```

### Data Fetching Strategy

- **Supabase direct** (via `@supabase/ssr`): Auth state, org data, customers, addresses, products — anything that's a simple CRUD read
- **Flask API** (via `fetch`): Document pipeline operations (upload, extract, generate), schema operations, anything involving AI services or file processing

This split keeps reads fast (no backend round-trip) while routing compute-heavy operations through the Flask API.

## Deployment

### Production

- **Frontend**: Vercel (automatic from `frontend/` directory)
- **Backend**: Railway (Gunicorn, from `Procfile`)
- **Database**: Supabase cloud project

### Environment Separation

- Development: Local Flask + local Next.js + Supabase project (dev branch)
- Staging: Railway preview + Vercel preview + Supabase project (staging branch)
- Production: Railway + Vercel + Supabase project (main branch)
