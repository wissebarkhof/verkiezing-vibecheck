FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first (better layer caching)
COPY pyproject.toml uv.lock* README.md ./
RUN uv sync --frozen --no-dev

# Download spaCy Dutch model (install directly to avoid pip dependency)
RUN uv pip install https://github.com/explosion/spacy-models/releases/download/nl_core_news_sm-3.8.0/nl_core_news_sm-3.8.0-py3-none-any.whl

# Copy application code and data
COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini .
COPY data/ data/
COPY docker-entrypoint.sh .

# Run as non-root user
RUN useradd -r -u 1001 -m appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

ENTRYPOINT ["sh", "docker-entrypoint.sh"]
