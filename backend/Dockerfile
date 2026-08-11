# Production image for the SOC-AGENTS FastAPI service.
# Two-stage build: dependencies and application sources are cached separately
# so that source changes do not invalidate the expensive wheel install.
# The image runs as a non-root user and exposes a readiness probe path.
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System toolchain: PostgreSQL client libraries (libpq) needed by asyncpg,
# plus curl for the container healthcheck.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 postgresql-client-16 curl \
    && rm -rf /var/lib/apt/lists/*

# Application user: never run the API as root.
RUN groupadd --system soc && useradd --system --gid soc --home-dir /app soc

# Dependencies: copied first so this layer survives application-only edits.
COPY backend/pyproject.toml /app/pyproject.toml
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e ".[dev,embeddings]"

# Application sources: copied after dependencies for layer-cache stability.
COPY backend/app /app/app
COPY backend/migrations /app/migrations
COPY backend/alembic.ini /app/alembic.ini
COPY scripts /app/scripts

RUN chown -R soc:soc /app

USER soc

EXPOSE 8000

HEALTHCHECK --interval=20s --timeout=5s --retries=5 \
    CMD curl -fs "http://localhost:8000/api/v1/health/live" || exit 1

# Boot: apply migrations first (idempotent), then start the API with uvicorn.
CMD ["sh", "-c", "python /app/scripts/migrate_schema.py && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
