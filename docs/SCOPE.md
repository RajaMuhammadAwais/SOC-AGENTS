# Project Scope: SOC-AGENTS

**Document purpose.** This is the authoritative, end-to-end scope document for the SOC-AGENTS platform. It defines what the platform does, the boundaries it deliberately does not cross, its non-functional requirements, and the phased roadmap that turns the design into a production deployment. Treat this document as the contract between contributors and the project: anything shipped should map to a scope item here, and anything not listed here is out of scope until formally added.

## 1. Vision and mission

SOC-AGENTS exists to give small and mid-sized security teams the capabilities of a professional SIEM/SOC stack — event ingestion, Sigma-rule detection, incident correlation, risk scoring, investigation, and autonomous response — without the cost and lock-in of commercial platforms. The guiding conviction is that detection should be **evidence-based** (every alert traceable to a human-readable Sigma rule), autonomy should be **auditable** (agents act only inside governed decision lanes), and multi-tenancy should be **architectural** (enforced at the data layer, not an afterthought).

## 2. In scope

### 2.1 Event pipeline (Phase 2 — implemented)

The ingestion and detection pipeline is the backbone of the platform. Raw events arrive through data sources (CSV files today, arbitrary log formats through the upload API), pass through a deterministic normalization stage that maps vendor-specific fields to a canonical event schema, and are de-duplicated with idempotent writes so re-uploads never create duplicate evidence. Normalized events are then evaluated against the rule set by the Sigma compilation engine, which converts Sigma YAML rules into executable queries. Matches become alerts carrying the rule identity, MITRE ATT&CK mapping, and severity. A correlation stage groups related alerts into incidents by correlation key and temporal proximity, merging occurrences and tracking first/last-seen timestamps, and a risk-scoring stage computes a 0–1000 risk score with confidence and a plain-language explanation. This entire chain has been verified end-to-end: a CSV upload produces normalized events, Sigma-detected alerts, risk-scored findings, and auto-grouped incidents.

### 2.2 Autonomous agent layer (Phase 3 — implemented)

Eight LangGraph agent graphs operate over the platform's data: **alert triage**, **investigation**, **threat hunting**, **risk scoring**, **report generation**, **response**, **threat intelligence**, and a **supervisor** that routes work. Three subsystems make these agents genuinely autonomous while remaining governed. The **skill registry** declares each action an agent can take as a typed skill with a risk class and an execution policy. The **episodic memory service** records agent decisions, actions, outcomes, and analyst-confirmed lessons as embeddings in pgvector so agents can semantically recall similar past investigations. The **knowledge service** maintains a tenant-scoped corpus of playbooks and runbooks, chunked, embedded with bge-m3, and retrieved through HNSW hybrid search for grounded (RAG) reasoning. The **autonomy policy engine** evaluates every proposed autonomous action against the tenant's maturity level and returns `allow`, `require_approval`, or `deny`, routing human-required actions into time-boxed decision lanes with fail-safe-deny on timeout.

### 2.3 Platform services (Phase 1 — implemented)

The platform base comprises multi-tenant JWT authentication with refresh tokens and MFA-ready TOTP, tenant-scoped roles with seventeen fine-grained permissions, a REST API with fourteen route groups (auth, users, roles, alerts, incidents, investigations, agents, reports, threat intelligence, data sources, ingestion, search, settings, realtime), structured middleware (logging, error handling, rate limiting), a 28-table PostgreSQL schema with pgvector, Redis for caching and rate-limit tokens, Docker Compose with health-gated service startup, and a GitHub Actions CI pipeline running lint, type-check, unit, and integration jobs.

### 2.4 Frontend console (Phase 4 — in progress)

The Next.js console currently provides authentication and data source management with multipart CSV upload. The remaining workspaces — dashboard, alerts, incidents, investigations, AI agents, users, and settings — follow the API contract already shipped and are the immediate next milestone.

## 3. Out of scope (deliberate boundaries)

The following are explicitly **not** part of this project, and contributors should not add them without a scope amendment. First, **log collection agents**: the platform ingests what external systems ship to it (CSV, files, API) and does not run its own endpoint collectors or ship its own OS agents — that responsibility belongs to existing EDR/syslog infrastructure. Second, **commercial SOAR integrations**: outbound automation targets webhooks and generic endpoints only; vendor-specific integrations (Palo Alto, CrowdStrike SDKs, and so on) are integration plugins, not core scope. Third, **endpoint telemetry**: file integrity monitoring, process telemetry collection, and network sensor management are out of scope. Fourth, **managed-service operations**: this is self-hosted software, not a managed detection offering. Finally, **ML-based anomaly detection models** are out of scope for the detection stage: detection is rule-based by design to keep alerts auditable and explainable, and ML components are confined to ranking, embedding, and language tasks.

## 4. Non-functional requirements

| Requirement | Target | Enforcement |
|---|---|---|
| Multi-tenancy | Full tenant isolation on every read/write | Scoped queries in repositories; tenant ID enforced in API auth layer |
| Security | OWASP API Security Top 10 coverage, Argon2 hashing, JWT/refresh, MFA-ready | Security middleware; ruff bandit-equivalent lint; secrets never in repo |
| Autonomy safety | Fail-safe-deny; every autonomous action audit-logged | Policy engine + decision lanes; deterministic evaluation |
| Reliability | Idempotent ingestion; health checks on all services | Dedup keys; Docker healthchecks; /health/ready endpoint |
| Performance | Sub-second rule evaluation on uploaded batches; HNSW hybrid search < 100 ms at 10k documents | Indexing (HNSW on vector columns); async pipeline |
| Testability | Unit suite ~100 tests; integration job with real Postgres/Redis | CI workflow |
| Deployability | Single-command `docker compose up`; idempotent migrations | Compose profiles; migrate_schema.py checkfirst |
| Observability | Structured logging, readiness probes | structlog; health routes |

## 5. Phase roadmap

| Phase | Status | Deliverables |
|---|---|---|
| 1 — Foundation | Done | Schema, auth/RBAC, Docker, k8s manifests, CI, API contract docs |
| 2 — Event pipeline | Done | Normalization, Sigma detection, correlation, risk scoring, E2E verification |
| 3 — Agent layer | Done | LangGraph agents, autonomy policy, skills, memory, knowledge, seed scripts |
| 4 — Console | In progress | Alerts, incidents, investigations, AI agents, users, settings workspaces |
| 5 — Intelligence & reporting | Planned | Threat intel enrichment UI, MITRE heatmap, report generation, analytics dashboard |
| 6 — Hardening | Planned | Prometheus/Grafana observability, Playwright E2E, load testing (k6), security audit |
| 7 — Ecosystem | Future | Plugin API for data-source connectors and SOAR targets, community rule exchange |

## 6. Governance of scope changes

Scope amendments are proposed as pull requests that edit this document and are reviewed against three questions: does the change preserve evidence-based detection, does it preserve auditable autonomy, and does it preserve tenant isolation? Features that fail any of these tests are rejected or re-architected before merge.
