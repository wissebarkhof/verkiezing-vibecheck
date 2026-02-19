FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first (better layer caching)
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev

# Download spaCy Dutch model
RUN uv run python -m spacy download nl_core_news_sm

# Copy application code and data
COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini .
COPY data/ data/

# Run as non-root user
RUN useradd -r -u 1001 appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
