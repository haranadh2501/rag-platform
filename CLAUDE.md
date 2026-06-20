# CLAUDE.md — IISc Grounded Agentic RAG Platform

> **Read this file first.** Every AI assistant and team member working on this repo must read this before touching any code.

## Project in One Sentence
A multi-tenant, RAG-grounded customer onboarding platform: upload any document set, query via Web UI or WhatsApp/Slack. FastAPI gateway → n8n RAG engine → PostgreSQL/pgvector → OpenAI.

## Tech Stack
| Layer | Technology |
|---|---|
| API Gateway | Python 3.11 · FastAPI · Uvicorn |
| RAG Engine | n8n (self-hosted) · workflows as JSON |
| Database | PostgreSQL 15 + pgvector extension |
| Cache / Sessions | n/a — stateless JWT + in-process slowapi (Redis removed) |
| Frontend | Next.js 14 · TypeScript · TailwindCSS |
| AI | OpenAI API (text-embedding-3-small + gpt-4o-mini) |
| WhatsApp Bot | Twilio Programmable Messaging |
| Slack Bot | Slack Events API + Bolt SDK |
| Auth | JWT (python-jose) · bcrypt passwords |
| ORM | SQLAlchemy 2.0 · Alembic migrations |
| Containerisation | Docker · docker-compose |

## Key Design Principle
**FastAPI is a thin gateway.** It handles auth, file upload, routing, and webhook receipt ONLY.
ALL RAG logic (parse → chunk → embed → store → retrieve → generate) runs inside n8n workflows.
Do NOT put embedding or LLM calls in FastAPI.

## Repository Layout
```
rag-platform/
├── CLAUDE.md            ← you are here
├── PROJECT_SPEC.md      ← scope & goals
├── ARCHITECTURE.md      ← system design
├── SKILLS.md            ← platform capabilities reference
├── TEAM_WORKFLOW.md     ← PR rules, standups, branching
├── .env.example         ← copy to .env and fill in secrets
├── docker-compose.yml   ← spins up everything
├── specs/
│   ├── openapi.yaml     ← THE contract (996 lines) — read before coding any endpoint
│   └── MODULE_SPEC_M*.md ← your personal spec — read yours before coding
├── backend/             ← FastAPI app (M2, M3, M4, M13)
├── n8n-workflows/       ← JSON workflow exports (M5, M6)
├── frontend/            ← Next.js (M8, M9, M13)
├── database/            ← SQL init scripts (M7)
├── evaluation/          ← RAGAS eval + test Q&A (M10)
├── docs/                ← guides, ADRs (M11)
└── tests/               ← pytest integration tests (M10)
```

## Module Ownership — No Cross-Module Edits Without PR
| File / Folder | Owner |
|---|---|
| `specs/openapi.yaml`, `docker-compose.yml` | M1 |
| `backend/app/main.py`, `backend/alembic/`, `backend/scripts/` | M2 |
| `backend/app/api/admin.py`, `backend/app/api/chat.py` | M3 |
| `backend/app/api/webhooks.py`, `backend/app/bots/slack.py` | M4 |
| `n8n-workflows/ingestion-pipeline.json`, `n8n-workflows/ingest-ephemeral.json` | M5 |
| `n8n-workflows/retrieval-pipeline.json`, `n8n-workflows/retrieval-ephemeral.json`, `n8n-workflows/purge-ephemeral.json` | M6 |
| `database/`, `backend/Dockerfile`, `frontend/Dockerfile` | M7 |
| `frontend/src/app/admin/`, `frontend/src/components/admin/` | M8 |
| `frontend/src/app/chat/`, `frontend/src/components/chat/` | M9 |
| `evaluation/`, `tests/` | M10 |
| `docs/`, `evaluation/sample-data/` | M11 |
| `backend/app/bots/whatsapp.py`, `backend/app/bots/tenant_map.py` | M12 |
| `backend/app/api/onboarding.py`, `frontend/src/app/onboarding/` | M13 |

## Running Locally
```bash
# 1. Clone and set up env
git clone <repo-url>
cd rag-platform
cp .env.example .env          # fill in your secrets

# 2. Start all services
docker compose up -d          # postgres + pgvector + n8n (no redis)

# 3. Run backend
cd backend
pip install -r requirements.txt
alembic upgrade head          # apply DB migrations
python -m app.scripts.seed_admin  # create first admin user
uvicorn app.main:app --reload --port 8000

# 4. Run frontend (separate terminal)
cd frontend
npm install
npm run dev                   # http://localhost:3000

# 5. Import n8n workflows
# Open http://localhost:5678 → Workflows → Import from file
# Import: n8n-workflows/ingestion-pipeline.json
# Import: n8n-workflows/retrieval-pipeline.json
# Import: n8n-workflows/ingest-ephemeral.json      (M5 — WhatsApp/chat upload, 1-hour TTL)
# Import: n8n-workflows/retrieval-ephemeral.json   (M6 — session-scoped Q&A over ephemeral_chunks)
# Import: n8n-workflows/purge-ephemeral.json       (M6 — session-end purge by conversation_id)
```

## Environment Variables (see .env.example)
Never commit `.env`. All secrets go in `.env` which is gitignored.

## API Contract
ALL endpoints must match `specs/openapi.yaml` exactly.
- Request/response shape must match the spec
- If you need to change the spec, discuss with M1 and update the YAML first
- M1 reviews any openapi.yaml changes before merge

## MOCK_N8N Mode (critical for parallel dev)
Set `MOCK_N8N=true` in `.env` to get fake RAG responses from `POST /chat/query`.
This lets frontend (M8, M9) and bots (M12) develop without waiting for n8n workflows.

## Git Rules
- Branch from `dev`: `git checkout dev && git pull && git checkout -b feat/your-feature`
- PR title format: `feat(module): what it does` or `fix(module): what it fixes`
- All PRs → `dev`. M1 reviews within 2 hours on sprint days.
- `dev` → `main` only after E2E smoke test passes.
- Minimum 1 test (unit or integration) per PR.

## AI Usage Policy
- Document all significant AI-generated code in `agent_usage/` folder
- Note: what you prompted, what it generated, what you corrected
- Export Claude Code session with `/export` after each work session
- Track token usage with `/cost`

## Code Style
- Python: Black formatter, isort imports, type hints everywhere
- TypeScript: ESLint + Prettier, strict mode
- Commit messages: `type(scope): message` (feat, fix, test, docs, chore)
- No `print()` in production code — use Python `logging` module

## Do NOT
- Put LLM/embedding calls in FastAPI — that's n8n's job
- Commit secrets or `.env` files
- Push directly to `main` or `dev`
- Start coding before reading your MODULE_SPEC file
- Return ungrounded answers — every answer must cite a source chunk
