# FreightFlow

Automated logistics document management platform. FreightFlow takes Purchase Order PDFs and generates Bill of Lading and Packing Slip documents using AI-powered extraction and PDF filling.

## Architecture

```
┌─────────────────────────┐     ┌──────────────────────────┐
│   Next.js Frontend      │     │   Flask API Backend      │
│   (App Router + TS)     │────▶│   (JSON REST API)        │
│   Tailwind + shadcn/ui  │     │   Pydantic validation    │
└───────────┬─────────────┘     └──────┬───────────────────┘
            │                          │
            ▼                          ▼
┌─────────────────────────────────────────────────────────┐
│                    Supabase                              │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │   Auth   │  │   Postgres   │  │     Storage        │  │
│  │  (JWT)   │  │   (RLS)      │  │  (PDFs, templates) │  │
│  └──────────┘  └──────────────┘  └───────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

**Document generation pipeline:**

1. **Parse** — Reducto OCR extracts structured data from PO PDFs
2. **Extract** — OpenAI transforms parsed data into BOL/Packing Slip JSON
3. **Fill** — Reducto Edit maps JSON onto PDF templates with form schemas

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15 (App Router), TypeScript, Tailwind CSS, shadcn/ui |
| Backend API | Flask 3.x, Pydantic, Gunicorn |
| Database | Supabase (Postgres with Row-Level Security) |
| Auth | Supabase Auth (email/password + OAuth) |
| File Storage | Supabase Storage (document-uploads, generated-documents, templates) |
| AI / OCR | OpenAI GPT (JSON extraction), Reducto (PDF parse + edit) |
| Deployment | Railway (backend), Vercel (frontend) |

## Project Structure

```
freightflow/
├── frontend/                  # Next.js application
│   ├── src/
│   │   ├── app/               # App Router pages and layouts
│   │   ├── components/        # Reusable UI components
│   │   ├── lib/               # Supabase client, utils, types
│   │   └── styles/            # Global styles
│   └── package.json
├── src/                       # Flask API backend
│   ├── api/
│   │   ├── __init__.py        # Flask app factory
│   │   ├── config.py          # Environment and app config
│   │   ├── auth.py            # Supabase JWT validation middleware
│   │   ├── routes/            # REST API route modules
│   │   ├── services/          # Business logic (AI pipeline, DB, storage)
│   │   └── models/            # Pydantic request/response models
│   ├── app.py                 # Legacy Flask app (being migrated)
│   ├── backend.py             # Legacy document pipeline (being migrated)
│   └── supabase_service.py    # Legacy DB access (being migrated)
├── supabase/
│   └── migrations/            # Versioned SQL migration files
├── templates/                 # AI prompt templates and PDF templates
├── docs/                      # Architecture and design documentation
├── requirements.txt           # Python dependencies
└── Procfile                   # Production process definition
```

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 20+
- A Supabase project (free tier works)
- OpenAI API key
- Reducto API key

### Backend Setup

```bash
# Clone and enter the project
cd freightflow

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment template and fill in your keys
cp .env.example .env
# Edit .env with your SUPABASE_URL, SUPABASE_KEY, OPENAI_API_KEY, REDUCTO_API_KEY

# Run database migrations
# (apply SQL files from supabase/migrations/ in order via Supabase dashboard or CLI)

# Start the development server
flask --app src.app run --debug --port 5000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Copy environment template
cp .env.example .env.local
# Edit .env.local with NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY, NEXT_PUBLIC_API_URL

# Start development server
npm run dev
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_KEY` | Yes | Supabase service role key (backend) |
| `NEXT_PUBLIC_SUPABASE_URL` | Yes | Supabase project URL (frontend) |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Yes | Supabase anon key (frontend) |
| `OPENAI_API_KEY` | Yes* | OpenAI API key (*per-org in production via BYOK) |
| `REDUCTO_API_KEY` | Yes* | Reducto API key (*per-org in production via BYOK) |
| `FLASK_SECRET_KEY` | Yes | Flask session signing key |
| `NEXT_PUBLIC_API_URL` | Yes | Flask API base URL for frontend |

## Multi-Tenancy

FreightFlow uses Row-Level Security (RLS) in a single Supabase database. Every data table has an `org_id` column, and RLS policies ensure users can only access data belonging to their organization.

Organizations bring their own API keys (BYOK) for OpenAI and Reducto — FreightFlow does not subsidize AI costs.

## Documentation

- [`docs/architecture.md`](docs/architecture.md) — System architecture and design decisions
- [`docs/database-schema.md`](docs/database-schema.md) — Complete database schema reference
- [`docs/pipeline.md`](docs/pipeline.md) — Document generation pipeline (models, prompts, data flow)
- [`docs/pipeline-extending.md`](docs/pipeline-extending.md) — Adding new document types and pipeline steps
- [`docs/prompts.md`](docs/prompts.md) — AI prompt template catalog
- [`docs/migration-plan.md`](docs/migration-plan.md) — Migration strategy from legacy schema

## License

Proprietary. All rights reserved.
