# Deployment Guide

This document covers deploying SOC-AGENTS locally, in staging, and in production using the provided Docker Compose stack, plus the CI pipeline, environment reference, production checklist, and secrets management policy.

## 1. Local development (no containers)

Requires Python 3.12+, Node 22+, PostgreSQL 16 with the `pgvector` extension, and Redis 7.

```bash
# Backend
python -m venv .venv && source .venv/bin/activate
cd backend && pip install -e ".[dev,embeddings]" && cd ..

# Database (idempotent; creates tables and extensions, never drops data)
python scripts/migrate_schema.py

# Demo data (idempotent; creates tenant, roles, demo user, Sigma rules)
python scripts/seed_demo_tenant.py
python scripts/seed_detection_rules.py

# Run
cd backend && fastapi dev app/main.py --port 8000

# Frontend console
cd frontend && pnpm install && pnpm dev   # or npm run dev
```

## 2. Docker Compose

`infra/docker-compose.yml` defines the full stack. Services are health-gated: the seed service waits for a healthy Postgres, and the API and console wait for their dependencies.

```bash
# Start everything (builds images, runs migrations on boot)
docker compose -f infra/docker-compose.yml up --build -d

# One-shot demo seeding (creates the acme tenant and demo rules)
docker compose -f infra/docker-compose.yml --profile seed run seed

# View logs
docker compose -f infra/docker-compose.yml logs -f api
```

| Service | Image | Port | Notes |
|---|---|---|---|
| `postgres` | `pgvector/pgvector:pg16` | 5432 | Init SQL mounts `infra/init/` to create extensions; resource-limited |
| `redis` | `redis:7-alpine` | 6379 | Cache and rate-limit buckets |
| `api` | built from `backend/Dockerfile` | 8000 | Non-root user, `/api/v1/health/live` healthcheck, runs migrations on boot |
| `console` | built from `frontend/Dockerfile` | 3000 | Production Next.js build, non-root user |
| `seed` (profile) | same as `api` | — | One-shot, exits after seeding |

Build contexts are slimmed by `.dockerignore` (design notes, caches, and build artifacts are excluded from both image builds).

## 3. CI pipeline

`.github/workflows/ci.yml` runs on every push and pull request with three jobs:

| Job | Steps |
|---|---|
| `backend` | Checkout, Python 3.12, `pip install -e ".[dev]"`, ruff lint, mypy type-check (`backend/app` + `scripts`), unit suite (`pytest -m "not integration and not slow"`) |
| `frontend` | Node 22, `npm ci`, typecheck, `npm run build` |
| `backend-integration` | Postgres 16 + pgvector and Redis service containers with health gates, extension provisioning, schema migration, demo seeding, then `pytest -m integration` |

New backend code must pass lint, type-check, and unit tests locally before pushing; integration tests require a real database and are covered by CI.

## 4. Environment reference

All configuration is pydantic-settings in `backend/app/core/config.py`, read from environment variables. Required in production:

| Variable | Purpose | Example |
|---|---|---|
| `APP_ENV` | `local`, `test`, `staging`, `production` | `production` |
| `DATABASE_URL` | Async PostgreSQL DSN | `postgresql+asyncpg://soc:<secret>@db:5432/soc` |
| `REDIS_URL` | Redis DSN | `redis://redis:6379/0` |
| `JWT_SECRET_KEY` | Token signing secret (min. 32 chars recommended) | from secret manager |
| `CORS_ALLOWED_ORIGINS` | Comma-separated console origins | `https://soc.example.com` |
| `JWT_REFRESH_SECRET_KEY` | Refresh-token signing secret | from secret manager |
| `EMBEDDING_PROVIDER` | Embedding backend | `bge-m3` (local) or provider |
| `LLM_MODEL` | Agent/reporting model | e.g. `nvidia/llama-3.1-nemotron-70b-instruct` |
| `OPENROUTER_API_KEY` | LLM API key (if using OpenRouter provider) | from secret manager |
| `RATE_LIMIT_ENABLED` | Token-bucket rate limiting | `true` |

The configuration module refuses to start in `APP_ENV=production` while `JWT_SECRET_KEY` is the placeholder value — deployments cannot silently run with demo secrets.

## 5. Production checklist

Before exposing the platform externally: rotate demo credentials or skip demo seeding entirely; set `APP_ENV=production` with secrets from a manager (Vault, cloud KMS, or CI/CD secrets — never files in the repo); terminate TLS at a reverse proxy or load balancer (the API itself serves plain HTTP by design); pin database credentials to a least-privilege role; enable Postgres WAL backups and schedule `pg_dump` snapshots; verify CORS allows only the console origin; enable rate limiting (`RATE_LIMIT_ENABLED=true`, the default); and run the integration suite once against the production schema after migration.

## 6. Secrets management

The project's secrets policy is deliberately minimal and absolute. **Secrets are never committed.** There is no `.env` file tracked by git, no credential literals in code, no keys in documentation examples, and no credentials in test fixtures (tests use explicit placeholders such as `test-token`, and the single TOTP fixture is the public RFC 6238 test vector). The only intentionally-shipped credentials are the demo seed's analyst account, which exists solely for local evaluation, is documented as demo-only in the README, and can be overridden via the `DEMO_PASSWORD` environment variable.

Operational secrets (database passwords, JWT signing keys, LLM provider API keys) enter the system exclusively through environment variables supplied by the orchestrator — `docker compose` `environment:` entries backed by the host's secret store, Kubernetes sealed secrets, or a CI/CD platform's secrets facility. A pre-commit secrets scan (e.g., `gitleaks` or `detect-secrets`) is recommended for contributors; the heuristic entropy scanner used during the open-source audit lives alongside the project tooling and can be re-run at any time. If a secret is ever committed, rotate it immediately and scrub history — do not attempt to patch over it.

## 7. Kubernetes

Manifests in `infra/k8s/` cover deployments, services, ingress, and ConfigMaps for each component. Apply in order: namespace → ConfigMap/Secret → database (or managed Postgres) → migrations Job → API → console. The container images built by the Compose stack push cleanly to any registry and are compatible with the k8s manifests without modification.
