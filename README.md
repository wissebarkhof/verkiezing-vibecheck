# Verkiezing Vibecheck

AI-powered election information platform for Dutch municipal elections.

## Setup

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Copy `.env.example` to `.env` and configure your environment variables

3. Run the application:
   ```bash
   uvicorn app.main:app --reload
   ```

## Docker

Run with Docker Compose:
```bash
docker-compose up
```

## Development

This project uses:
- FastAPI for the web framework
- PostgreSQL with pgvector for the database
- SQLAlchemy for ORM
- LiteLLM for LLM provider abstraction
