# SOC-AGENTS

**An open-source, autonomous AI Security Operations Center (SOC) platform** combining a modern SIEM event pipeline, Sigma-rule detection, AI-driven risk scoring, and a multi-agent autonomous layer with skill-based execution policies, pgvector-backed memory and knowledge, all on multi-tenant, production-grade infrastructure.

![Python](https://img.shields.io/badge/python-3.12+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+%20pgvector-orange)
![License](https://img.shields.io/badge/license-Apache--2.0-green)

---

## What this project is

SOC-AGENTS is an end-to-end security operations platform for teams that want professional SIEM/SOC capabilities without the proprietary SIEM price tag. Raw security events from any source (CSV, log files, EDR exports, cloud audit trails) are normalized into a canonical schema, evaluated against Sigma detection rules, correlated into incidents, and risk-scored — while autonomous AI agents triage, investigate, hunt, and respond according to an auditable autonomy policy.

The platform is deliberately built around three professional principles:

1. **Evidence-based detection.** Detections are written as Sigma rules with deterministic compilation, not opaque ML black boxes. Every alert traces back to a human-readable rule.
2. **Auditable autonomy.** AI agents can act without a human in the loop — but only inside time-boxed decision lanes, bounded by risk-class policies, and every action is audit-logged. The platform implements the full HITL / HOTL / HOOTL oversight spectrum.
3. **Multi-tenant isolation from day one.** Every tenant's events, alerts, incidents, agent memories, and knowledge base are scoped to that tenant at the data layer.

## Feature overview

| Domain | Capability | Status |
|---|---|---|
| Event pipeline | CSV/log ingestion, canonical normalization, deduplication, idempotent writes | Implemented, E2E-verified |
| Detection | Sigma rule authoring, compilation to queries, evaluation, severity mapping | Implemented (MITRE ATT&CK metadata) |
| Correlation | Temporal/correlation-key grouping of alerts into incidents, occurrence merge | Implemented |
| Risk scoring | 0–1000 risk score with confidence and plain-language explanation | Implemented |
| Agents | Alert triage, investigation, threat hunting, risk scoring, report generation, response, threat intel, supervisor | Implemented (LangGraph) |
| Autonomy | Skill registry, 5 autonomy maturity levels (L0–L4), time-boxed decision lanes, fail-safe-deny | Implemented |
| Memory | Episodic agent memory (decisions, actions, outcomes, lessons) with pgvector semantic recall | Implemented |
| Knowledge | Playbook/runbook document store with bge-m3 embedding, HNSW hybrid search (RAG) | Implemented |
| Auth & RBAC | JWT access/refresh, MFA-ready TOTP, tenant-scoped roles and fine-grained permissions | Implemented |
| Frontend console | Login, data source management (CSV upload), executive dashboard | Partial (see Roadmap) |
| Deployment | Docker Compose, GitHub Actions CI (unit, lint, typecheck, integration), k8s manifests | Implemented |

## Architecture at a glance

```
┌────────────┐      ┌──────────────────────────────────────────────┐
│  Sources   │      │  backend (FastAPI, async Python)             │
│ CSV / logs │ ───▶ │  ingestion ─▶ normalize ─▶ Sigma detect      │
│ EDR / cloud│      │  ─▶ correlate ─▶ risk score ─▶ alerts / inc. │
└────────────┘      │              ▲                │              │
                    │              │       ┌────────▼──────────┐   │
┌────────────┐      │     agents   │       │  autonomy policy  │   │
│  Agents    │ ◀──▶ │  triage /    │       │  L0–L4, lanes,    │   │
│ LangGraph  │      │  hunting /   │       │  skill registry   │   │
└────────────┘      │  investigation│      └───────────────────┘   │
                    │  + memory/knowledge (pgvector RAG)           │
┌────────────┐      └────────────────┬─────────────────────────────┘
│  Postgres  │ ◀────────────────────┘
│ + pgvector │   Redis (cache, rate-limit)
└────────────┘
                    ┌──────────────────────────────┐
                    │  frontend (Next.js console)  │
                    └──────────────────────────────┘
```

## Project scope (summary)

The full scope document lives at [`docs/SCOPE.md`](docs/SCOPE.md). In short, the platform covers the complete SOC lifecycle — **ingestion, normalization, detection, alerting, correlation, investigation, threat hunting, threat intelligence enrichment, risk scoring, executive reporting, and autonomous response** — while deliberately scoping **out** log-agent collection (agents ship logs to the platform rather than the platform running collectors), commercial SOAR integrations (webhook/outbound integrations only), and endpoint telemetry agents.

## Quick start

### Local development

```bash
# 1. Prerequisites: Python 3.12+, Node 22+, PostgreSQL 16 (pgvector), Redis 7
# 2. Backend
python -m venv .venv && source .venv/bin/activate
cd backend && pip install -e ".[dev,embeddings]"
cd ..

# 3. Provision the database (idempotent)
python scripts/migrate_schema.py

# 4. Seed demo tenant and detection rules
python scripts/seed_demo_tenant.py
python scripts/seed_detection_rules.py

# 5. Run the API
cd backend && fastapi dev app/main.py --port 8000
```

### Demo credentials

The demo seed creates tenant `acme` with a single analyst account. **These are demo-only credentials; rotate them in any non-demo environment.**

| Item | Value |
|---|---|
| Tenant slug | `acme` |
| Email | `analyst@acme.local` |
| Password | `StrongPass1234!` (override with `DEMO_PASSWORD` env) |
| Role | analyst (alerts, incidents, investigations, agents) |

### Docker Compose

```bash
docker compose -f infra/docker-compose.yml up --build
# one-shot demo seeding
docker compose -f infra/docker-compose.yml --profile seed run seed
```

The stack brings up the API on port 8000, the console on port 3000, PostgreSQL 16 with pgvector, and Redis. Migrations run automatically on API boot; health checks gate service startup.

## Repository layout

```
SOC-AGENTS/
├── backend/                # FastAPI service
│   ├── app/
│   │   ├── api/v1/routes/  # REST endpoints (auth, alerts, incidents, agents, ...)
│   │   ├── agents/         # LangGraph agent graphs (triage, hunting, ...)
│   │   ├── core/           # config, security (JWT/TOTP), permissions, middleware
│   │   ├── domain/         # models, pipeline, policy/autonomy, rag, agents-memory
│   │   └── infrastructure/ # db, redis, embeddings, llm, vector (pgvector/pinecone)
│   ├── tests/              # 24 test modules, ~100 passing tests
│   └── Dockerfile
├── frontend/               # Next.js SOC console
├── scripts/                # migrate_schema.py, seed_*.py (idempotent)
├── infra/                  # docker-compose.yml, k8s/, init SQL
├── docs/                   # SCOPE, ARCHITECTURE, AUTONOMOUS_AGENTS, DEPLOYMENT
└── todo.md                 # project progress tracker
```

## Environment configuration

All configuration flows through `backend/app/core/config.py` (pydantic-settings). Required values in production:

| Variable | Purpose | Default |
|---|---|---|
| `APP_ENV` | `local` / `test` / `staging` / `production` | `local` |
| `DATABASE_URL` | PostgreSQL DSN (asyncpg) | — |
| `REDIS_URL` | Redis DSN | — |
| `JWT_SECRET_KEY` | Signing secret for access tokens | `change-me-local-only` (rejected in production) |
| `CORS_ALLOWED_ORIGINS` | Comma-separated console origins | `http://localhost:3000` |
| `EMBEDDING_PROVIDER` / `EMBEDDING_MODEL` | Embeddings for memory/RAG | `bge-m3` / `BAAI/bge-m3` |
| `RATE_LIMIT_ENABLED` | Token-bucket rate limiting | `true` |

The API refuses to start in `APP_ENV=production` with the placeholder JWT secret — configure `JWT_SECRET_KEY` from a secret manager before going live.

## Security model

The platform enforces tenant isolation through scoped database queries (no shared-schema leakage), Argon2 password hashing, JWT with refresh tokens, MFA-ready TOTP with RFC 6238 compliance, and fine-grained permissions bound to tenant-local roles. The autonomy layer adds a second enforcement surface: skills are declared with a risk class (`informational`, `low`, `elevated`, `critical`) and an execution policy (`allow`, `require_approval`, `deny`); the policy engine evaluates every autonomous action and routes high-risk actions to time-boxed human decision lanes with fail-safe-deny on timeout. See [`docs/AUTONOMOUS_AGENTS.md`](docs/AUTONOMOUS_AGENTS.md) for the full model and [`SECURITY.md`](SECURITY.md) for the disclosure policy.

A secrets sweep before open-sourcing confirmed the repository contains **no production credentials**: all secrets are environment-provided, defaults are clearly marked placeholders, and the demo password is documented as demo-only. See the [secrets management section](docs/DEPLOYMENT.md) for how to keep it that way.

## Testing

```bash
cd backend
pytest -m "not integration and not slow"   # unit suite (~101 tests)
pytest -m integration                      # requires Postgres + Redis
```

CI runs lint (ruff), type-check (mypy), the unit suite, frontend typecheck/build, and a full integration job with service containers on every push and pull request (`.github/workflows/ci.yml`).

## Roadmap

| Phase | Focus | Highlights |
|---|---|---|
| 1 | Foundation | Schema, auth/RBAC, Docker, CI, API contracts |
| 2 | Event pipeline | Normalization, Sigma detection, correlation, risk scoring |
| 3 | Agent layer | LangGraph agents, autonomy policy, skills, memory, knowledge |
| 4 | Console (next) | Alerts, incidents, investigations, AI agents, users, settings pages |
| 5 | Intelligence | Threat intel enrichment, MITRE mapping, report generation UI |
| 6 | Hardening | Observability (Prometheus/Grafana), E2E tests, load testing |

## License

This project is licensed under the **Apache License 2.0** — see [`LICENSE`](LICENSE) for the full text and [`LICENSE.md`](LICENSE.md) for a short summary, including how third-party components are licensed. Contributions are welcome; see [SECURITY.md](SECURITY.md) and [CONTRIBUTING.md](CONTRIBUTING.md).

## Documentation index

| Document | Purpose |
|---|---|
| [`docs/SCOPE.md`](docs/SCOPE.md) | Complete end-to-end project scope, boundaries, and non-functional requirements |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System architecture, event pipeline, and data flows |
| [`docs/AUTONOMOUS_AGENTS.md`](docs/AUTONOMOUS_AGENTS.md) | Agent memory, knowledge, skills, and the autonomy policy engine |
| [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) | Docker, CI/CD, environment reference, and secrets management |
| [`SECURITY.md`](SECURITY.md) | Vulnerability disclosure policy |
| [`docs/api-spec.md`](docs/api-spec.md) | REST API contract |
| [`docs/database-schema.md`](docs/database-schema.md) | Database model reference |
