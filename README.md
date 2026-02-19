# Verkiezing Vibecheck

AI-powered election information platform for Dutch municipal elections. Built for the Amsterdam gemeenteraadsverkiezingen 2026.

**Live:** https://verkiezing-app.politedune-d337c8d0.northeurope.azurecontainerapps.io

## What you can do

- **Explore parties** — read AI-generated summaries of party programs, so you don't have to wade through the full PDFs yourself
- **Compare parties by topic** — see side-by-side AI comparisons of how parties stand on themes like housing, climate, and mobility
- **Search party programs** — ask questions in natural language and get relevant excerpts from the actual program text (RAG)
- **Browse candidates** — view candidate profiles including their LinkedIn, Bluesky posts summarised by AI, and council motions they submitted
- **Council motions** — explore motions and amendments from the current council term, linked to parties and individual council members

## Tech stack

| Layer | Tools |
|---|---|
| Backend | Python, FastAPI, SQLAlchemy, Alembic |
| Frontend | Jinja2 templates, HTMX, Tailwind CSS |
| Database | PostgreSQL + pgvector |
| AI / LLM | LiteLLM (Anthropic Claude + OpenAI), OpenAI embeddings |
| NLP | spaCy (`nl_core_news_sm`) |
| Data sources | Party program PDFs, Bluesky AT Protocol API, Notubiz council data |
| Deployment | Docker, Azure Container Registry, Azure Container Apps, Azure Database for PostgreSQL |

## Setup

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Copy `.env.example` to `.env` and fill in the required variables (`DATABASE_URL`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, etc.)

3. Start the database:
   ```bash
   docker-compose up -d db
   ```

4. Run migrations:
   ```bash
   uv run alembic upgrade head
   ```

5. Ingest data (run in order):
   ```bash
   uv run python scripts/ingest.py
   uv run python scripts/generate_embeddings.py
   uv run python scripts/generate_summaries.py
   uv run python scripts/generate_comparisons.py
   uv run python scripts/fetch_social.py
   uv run python scripts/fetch_motions.py
   uv run python scripts/generate_motion_summaries.py
   ```

6. Run the app:
   ```bash
   uvicorn app.main:app --reload
   ```

Or run everything with Docker Compose:
```bash
docker-compose up
```

## Contact

verkiezingenvibecheck@gmail.com
