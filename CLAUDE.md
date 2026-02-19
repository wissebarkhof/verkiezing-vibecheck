# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered web app for Dutch municipal elections (Amsterdam gemeenteraadsverkiezingen 2026, election date 2026-03-18). Helps voters explore parties and candidates via AI-generated program summaries, topic-based party comparisons, and RAG-powered search over party programs. Also a portfolio/learning project targeting Azure deployment.

**UI language:** Dutch. **Code/comments:** English.

## Commands

```bash
# Install dependencies
uv sync

# Run development server
uvicorn app.main:app --reload

# Run with Docker Compose (includes PostgreSQL with pgvector)
docker-compose up

# Database migrations (Alembic)
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "description"

# Data ingestion scripts (run in order for a new election)
uv run python scripts/ingest.py              # YAML + PDFs → DB
uv run python scripts/generate_embeddings.py # chunks → pgvector
uv run python scripts/generate_summaries.py  # AI party summaries (Dutch)
uv run python scripts/generate_comparisons.py # AI topic comparisons (Dutch)
uv run python scripts/fetch_social.py        # Bluesky posts → AI summaries
uv run python scripts/fetch_motions.py       # Notubiz → council motions/amendments
uv run python scripts/generate_motion_summaries.py  # AI motion summaries per party

# Tests
uv run pytest
uv run pytest tests/path/to/test_file.py::test_name
```

## Environment

Copy `.env.example` to `.env`. Required variables:
- `DATABASE_URL` — PostgreSQL connection string
- `ANTHROPIC_API_KEY` — for Anthropic models via LiteLLM
- `OPENAI_API_KEY` — for OpenAI models + embeddings
- `ELECTION_CONFIG` — path to YAML config, e.g. `data/elections/amsterdam-2026.yml`
- `ENVIRONMENT` — `development` or `production`

## Election Config (YAML)

Election-specific data lives entirely in `data/elections/<slug>.yml`. The app is election-agnostic; swap the YAML + PDFs to support another city.

```yaml
election:
  name: "Gemeenteraadsverkiezingen Amsterdam 2026"
  city: amsterdam
  date: "2026-03-18"
parties:
  - name: "GroenLinks-PvdA"
    abbreviation: "GL-PvdA"
    website: "https://..."
    logo: "logos/gl-pvda.png"
    program_pdf: "programs/gl-pvda-2026.pdf"
    candidates:
      - name: "Rutger Groot Wassink"
        position: 1
        bluesky: "@rutgergw.bsky.social"
topics:  # used for party comparison feature
  - "Woningbouw en huisvesting"
  - "Klimaat en milieu"
```

## Architecture

**Entry point:** `app/main.py` — FastAPI app, mounts routers, static files, Jinja2 templates.

**Layered structure:**
- `app/routers/` — HTTP route handlers
- `app/services/` — Business logic (routers call services, not models directly)
- `app/models/` — SQLAlchemy ORM models
- `app/templates/` — Jinja2 + HTMX (server-rendered, Dutch UI text)
- `app/static/` — CSS (Tailwind via CDN), JS
- `scripts/` — One-off data ingestion and AI generation scripts
- `data/elections/` — YAML configs; `data/programs/` — PDFs (gitignored)

**Key architectural decisions:**
- **LiteLLM** abstracts over Anthropic/OpenAI — use `litellm.completion()`, never call provider SDKs directly. All LLM prompts instruct Dutch output.
- **pgvector** stores/queries document chunk embeddings. Embeddings use OpenAI `text-embedding-3-small`.
- **HTMX** handles interactive elements (search results, comparison loading) without JS complexity.
- **Alembic** manages all schema migrations — never alter tables manually.
- **spacy** (`nl_core_news_sm`) for Dutch NLP preprocessing.
- **Chunking:** PDFs split by section headers, ~500-token chunks with overlap.

## Data Models

```
Election       — id, slug, name, city, date
Party          — election_id (FK), name, abbreviation, logo_url, website_url,
                 description (AI summary, Dutch), program_text (from PDF)
Candidate      — party_id (FK), name, position_on_list, photo_url, bio,
                 bluesky_handle, linkedin_url, social_summary (AI, Dutch)
Document       — party_id (FK), source_type, content (text chunk),
                 embedding (pgvector), metadata (JSONB)
TopicComparison — election_id (FK), topic_name,
                  comparison_json (JSONB, per-party positions, Dutch)
Motion         — election_id (FK), notubiz_item_id (unique, upsert key),
                 title, motion_type, result, submission/resolution dates,
                 toelichting (raw HTML), document_url
MotionParty    — motion_id (FK), party_id (FK, nullable),
                 notubiz_party_name (raw name for audit)
MotionCandidate — motion_id (FK), candidate_id (FK, nullable),
                  notubiz_person_name, notubiz_person_id
```

## Implementation Phases

- **Phase 1 — Foundation:** config, DB, models, main.py, Alembic, base template, basic routes, YAML config
- **Phase 2 — Data Ingestion:** ingest service + script, PDF extraction, party/candidate pages with real data
- **Phase 3 — AI Features:** LLM service (summaries, comparisons, RAG), embeddings, search router, compare router
- **Phase 4 — Social Media:** Bluesky AT Protocol API, fetch + summarize posts per candidate, candidate detail pages
- **Phase 5 — Azure Deployment:** Azure Database for PostgreSQL (pgvector), Azure Container Registry, Azure Container Apps, env config, polish (mobile, error handling, SEO, rate limiting), tests
