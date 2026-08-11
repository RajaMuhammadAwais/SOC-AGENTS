# Architecture: SOC-AGENTS

This document describes the platform's architecture: the service topology, the event pipeline that turns raw security data into risk-scored incidents, the autonomous agent layer built on top of it, and the deployment topology. It is grounded in the current codebase, not the initial design docs.

## 1. Service topology

The platform is a two-service system around two durable datastores.

| Component | Technology | Responsibility |
|---|---|---|
| Backend API | FastAPI (async, Python 3.12) | All domain logic, REST API, WebSocket pushes, pipeline execution, agent orchestration |
| Frontend console | Next.js App Router, React 19, Tailwind 4, shadcn/ui | SOC analyst workspace: auth, data sources, (forthcoming) alerts/incidents/investigations/agents |
| PostgreSQL 16 + pgvector | Relational + vector | Schema of 28 tables: tenants, users, roles, permissions, events, alerts, incidents, rules, agent memories, knowledge chunks (HNSW index), audit log |
| Redis 7 | Cache and guardrails | Session/refresh token storage, rate-limit token buckets, transient state |

The backend is organized on clean-architecture lines. `app.api` holds route definitions and Pydantic request/response schemas only; `app.domain` owns models, business rules (pipeline, autonomy policy, RAG, agent memory/knowledge services), and the repository contracts; `app.infrastructure` provides the concrete implementations (database sessions, Redis client, embedding and LLM providers, vector store sinks). Cross-cutting concerns — JWT/TOTP security, permission resolution, middleware (logging, error handling, rate limiting), and a central pydantic-settings configuration module — live in `app.core`.

## 2. The event pipeline

The pipeline is a deterministic, staged chain executed per uploaded event batch, orchestrated by `app.domain.pipeline.service`. Every stage failure is recorded and raised as a structured error — the pipeline never swallows failures silently.

```
raw payload ─▶ validate ─▶ store raw event ─▶ normalize ─▶ detect (Sigma)
        ─▶ create/update alert ─▶ correlate into incident ─▶ risk score
        ─▶ extract observables ─▶ audit log ─▶ WebSocket publish
```

**Validation and raw storage.** Uploaded payloads are validated against the source's schema contract; failures raise `IngestionValidationError` and are returned to the caller. Every accepted payload is first stored as a `RawEvent` (immutable evidence) before any transformation, preserving the forensic original.

**Normalization.** Vendor-specific payloads map to the canonical `NormalizedEvent` schema (event type, actor, target, source/destination IPs, hashes, timestamps, severity hints). Deduplication uses a hash of the canonical fields so repeated uploads of the same event are idempotent.

**Detection.** `app.domain.pipeline.detection` evaluates normalized events against compiled Sigma rules. Rules are authored as Sigma YAML in the admin console, deterministically compiled to query expressions, and stored on `DetectionRule` (including a cached `compiled_query`). Matches produce alerts carrying the rule identity, MITRE ATT&CK tactic/technique mapping, and the rule's severity.

**Correlation.** Alerts are grouped into incidents by correlation key (shared actor/target/rule family) within a rolling time window. Repeated matching alerts increment an incident's occurrence count and update its first/last-seen timestamps rather than spawning new incidents, so a brute-force campaign reads as one incident with a count, not thousands of noise rows.

**Risk scoring.** `assess_alert` computes a 0–1000 risk score from the rule severity, occurrence history, asset context, and detection confidence, and emits a plain-language explanation of why the score is what it is — an analyst should never receive a number they cannot defend.

**Observables extraction.** A syntactic pass extracts candidate IOCs (MD5/SHA1/SHA256, URLs, domains, IPs) from payloads into the `Observables` table; reputation assessment belongs to the threat-intelligence stage, not to extraction.

**Realtime.** Stage completions publish through the WebSocket layer (`/ws/realtime`) so the console can live-update without polling.

## 3. The autonomous agent layer

Eight LangGraph agent graphs sit above the pipeline: triage, investigation, threat hunting, risk scoring, report generation, response, threat intelligence, and a supervisor that routes work to specialists. Three subsystems give these agents durable, governed autonomy.

**Skills.** Every action an agent can take — query threat intelligence, enrich an IOC, recommend a block — is declared in the `agent_skills` registry with a name, description, required permissions, a **risk class** (`informational`, `low`, `elevated`, `critical`), and an **execution policy** (`allow`, `require_approval`, `deny`). Skills are the procedural memory of the system: agents execute them without re-deriving logic each time.

**Memory.** `MemoryService` records episodic memories — decisions, actions, outcomes, and analyst-confirmed lessons — as bge-m3 embeddings in the `agent_memories` pgvector table, all scoped to the tenant. At triage time agents semantically recall up to five similar past investigations (`vector <=> query` nearest-neighbor), grounding judgment in case history rather than a cold start.

**Knowledge.** `KnowledgeService` maintains tenant-scoped playbooks and runbooks (`knowledge_documents`), chunked and indexed with hybrid (keyword + HNSW semantic) retrieval through the existing `vector_chunks` table. Agent answers are generated through the RAG pipeline with cited evidence, keeping hallucination liability low.

**The autonomy policy engine.** `app.domain.policy.autonomy` implements the decision-lane model. The oversight level is a property of the *decision*, not of the agent: every proposed execution is evaluated against the tenant's autonomy maturity level and the skill's risk class.

| Autonomy level | Autonomous risk classes | Character |
|---|---|---|
| L0 manual | none | Analysts execute everything |
| L1 advisory | none | Agents recommend only |
| L2 supervised | informational | Audit-only autonomous actions |
| L3 guarded | informational, low | Reversible actions allowed |
| L4 autonomous | informational, low, elevated | Policy-allow skills execute without approval |

The evaluation order is deterministic: a skill-level `deny` always wins; `require_approval` always routes to a human lane; otherwise the maturity level's allow-set applies; finally, an optional confidence floor escalates uncertain detections to a human. Human lanes are **time-boxed** (informational 0 s, low 60 s, elevated 120 s, critical 300 s) with **fail-safe-deny** on timeout — a missed window is a refusal, never an implicit approval. Every autonomous execution is audit-logged with its decision reason.

## 4. Security architecture

Authentication uses JWK-capable JWT access tokens with refresh tokens, Argon2 password hashing, and RFC 6238-compliant TOTP for MFA readiness. Authorization resolves a tenant-scoped principal against seventeen permissions bound to roles; every route enforces permission checks through a principal dependency. Tenant isolation is structural: repositories scope every query by `tenant_id`, so there is no shared-schema leakage path at the API layer. Rate limiting uses Redis token buckets keyed per tenant and endpoint, and CORS is an explicit allow-list validated at startup.

The secrets posture is simple and strict: all secrets are environment-provided (no `.env` files in the repository, no credentials in code or docs), the JWT default is a clearly named placeholder that the configuration module refuses in `APP_ENV=production`, and the demo seed's credentials are documented as demo-only.

## 5. Deployment topology

| Environment | Mechanism |
|---|---|
| Local development | `fastapi dev`, `pnpm dev`, direct Postgres/Redis |
| Staging/production | `infra/docker-compose.yml`: API (non-root, healthcheck-gated), console, pgvector, Redis, one-shot `seed` profile service |
| Kubernetes | Manifests in `infra/k8s/` (deployments, services, ingress, configmaps) |
| CI | GitHub Actions: unit (ruff + mypy + ~101 pytest), frontend typecheck/build, integration job with service containers |

Migrations (`scripts/migrate_schema.py`) are idempotent (`checkfirst`) and run at application boot inside the container, so deployments need no separate migration step. Extensions (`pgcrypto`, `pgvector`) are provisioned by the init SQL mounted into the database container.

## 6. Key design decisions

**Why rules, not ML, for detection.** Alerts must be explainable and contestable in a security operation; a Sigma rule is a human-readable artifact that can be reviewed, versioned, and tuned. Machine learning is deliberately confined to ranking, embedding, and language tasks where its uncertainty does not create undetectable blind spots.

**Why autonomy is policy-driven, not model-driven.** Letting an LLM decide its own permissions is a known failure mode of autonomous agents (blast radius, prompt injection). SOC-AGENTS makes the permission boundary deterministic code that no model output can override: the policy engine is evaluated in pure Python from declared data.

**Why pgvector over a managed vector service.** The knowledge and memory stores are tenant-scoped relational metadata plus vectors; a managed vector database would split the unit of consistency. Self-hosted pgvector keeps retrieval, filtering, and garbage collection transactional. (Pinecone remains supported as an alternative sink via the vector-provider abstraction.)
