You are a Principal AI Architect, Principal Cyber Security Engineer, Senior Software Engineer, DevSecOps Architect, and Enterprise Solution Architect.

Your objective is to design and build a production-ready Enterprise Autonomous AI Security Operations Center (AI SOC) platform that combines SIEM, SOAR, Threat Intelligence, RAG, and Multi-Agent AI into a single scalable system.

## Mission

Build a Fortune-500-level AI SOC platform that can:

* Detect attacks
* Investigate incidents
* Correlate logs
* Perform threat hunting
* Generate executive reports
* Recommend or execute automated responses

The project must follow enterprise software engineering standards and should be production deployable.

---

# Technology Stack

## Frontend

* Next.js 15
* React
* TypeScript
* TailwindCSS
* Shadcn UI
* Framer Motion
* TanStack Query

---

## Backend

* FastAPI
* Python 3.12
* REST API
* WebSocket
* Async architecture

---

## AI Framework

Use LangGraph as the orchestration framework.

Every capability should be implemented as an independent AI agent.

---

## LLM

Primary Model:

Nemotron

System should also support:

* Qwen 3
* Llama
* DeepSeek

Model selection must be configurable.

---

## Embedding Model

Use:

bge-m3

---

## Reranker

Use:

bge-reranker-v2-m3

---

## Vector Database

Use Pinecone as the production vector database.

Store:

* CVEs
* MITRE ATT&CK
* NIST documentation
* Internal policies
* Incident playbooks
* Threat intelligence
* Historical investigations

Implement:

* semantic search
* hybrid search
* metadata filtering
* namespace support

---

## Databases

PostgreSQL

Redis

---

## Authentication

JWT

RBAC

Refresh Tokens

MFA-ready architecture

Audit logging

---

## Deployment

Docker

Docker Compose

Kubernetes-ready

GitHub Actions CI/CD

---

# AI Agents

Implement these independent agents:

## 1 Alert Triage Agent

Responsibilities:

* Remove duplicate alerts
* Prioritize alerts
* Reduce false positives
* Categorize incidents

---

## 2 Threat Intelligence Agent

Tasks:

* IOC enrichment
* IP reputation
* Domain reputation
* Hash lookup
* CVE lookup
* MITRE ATT&CK mapping

---

## 3 Investigation Agent

Tasks:

* Correlate logs
* Build attack timeline
* Explain attack chain
* Determine affected assets
* Identify initial access
* Identify lateral movement

---

## 4 Threat Hunting Agent

Tasks:

Search:

* Similar attacks
* Similar users
* Similar endpoints
* Similar IPs

Find hidden attacks automatically.

---

## 5 Risk Scoring Agent

Generate:

Risk Score (0-100)

Explain:

* Why score is high
* Confidence level
* Business impact

---

## 6 Report Generation Agent

Generate:

Executive Summary

Technical Report

Incident Timeline

MITRE Mapping

Root Cause Analysis

Recommendations

---

## 7 Response Agent

Recommend or execute:

* Block IP
* Disable account
* Isolate endpoint
* Notify SOC
* Create incident ticket

---

## Supported Data Sources

Windows Logs

Linux Syslogs

Firewall Logs

VPN Logs

CloudTrail

Azure Logs

Kubernetes Audit Logs

Web Server Logs

EDR Logs

Identity Logs

Microsoft 365

---

# Dashboard

## Executive Dashboard

Overall Risk

Critical Incidents

Business Impact

Compliance

---

## SOC Dashboard

Live Alerts

Attack Timeline

Threat Intelligence

Investigation Queue

---

## Analytics

Daily attacks

Weekly trends

Monthly trends

MITRE ATT&CK heatmap

Top attacker IPs

Top targeted assets

---

# RAG Pipeline

Document Ingestion

↓

Chunking

↓

bge-m3 Embeddings

↓

Pinecone

↓

Hybrid Retrieval

↓

bge-reranker-v2-m3

↓

Nemotron

↓

Final Response

Implement citations and explainability for retrieved knowledge.

---

# Natural Language Capabilities

Support prompts like:

"Show all critical incidents today"

"Explain this attack"

"Generate executive report"

"Summarize failed logins"

"Which endpoints are compromised?"

"What MITRE techniques are involved?"

---

# Database Design

Generate:

ER Diagram

Normalized schema

Indexes

Partitioning strategy

Migration scripts

---

# Backend

Generate:

Folder structure

Clean Architecture

Repository Pattern

Dependency Injection

Service Layer

Middleware

Exception Handling

Logging

Validation

Rate Limiting

---

# Frontend

Generate:

Enterprise dashboard

Authentication pages

SOC analyst workspace

Investigation screen

Threat intelligence screen

Settings

Dark mode

Responsive design

---

# APIs

Generate complete REST API documentation including:

Authentication

Incidents

Logs

Threat Intelligence

Reports

Agents

Users

RBAC

---

# Security

Implement:

OWASP best practices

CSRF protection

XSS prevention

SQL Injection prevention

Secrets management

Encryption at rest

Encryption in transit

Audit logs

---

# Observability

Prometheus

Grafana

Structured logging

Health checks

Metrics

Tracing

---

# Testing

Unit tests

Integration tests

End-to-end tests

Load testing

Security testing

---

# DevOps

Docker

Docker Compose

Kubernetes manifests

GitHub Actions

Environment configuration

Production deployment

Monitoring

Rollback strategy

---

# Code Requirements

Follow:

SOLID

Clean Architecture

Enterprise Design Patterns

Modular code

Scalable architecture

Maintainable code

Production quality documentation

No toy examples.

Generate complete implementation step-by-step, one module at a time, maintaining a consistent folder structure and coding standards throughout the project.

---

# Research-Backed Implementation Baseline

Status: Draft 1
Last reviewed: 2026-06-11
Scope: Production-ready autonomous AI Security Operations Center platform.

This document is the implementation baseline for the project. When code is added, use this file with `todo.md` as the source of truth. If a library, language, or framework is introduced, read its official documentation first and record any material design decision here.

## Research Baseline

Primary sources reviewed on 2026-06-11:

- Next.js official docs: latest documented version is 16.2.9; App Router is the newer router with React Server Components support. https://nextjs.org/docs
- FastAPI official docs: Python type hints, OpenAPI compatibility, dependency injection, security, middleware, WebSockets, testing, and Docker deployment are first-class documentation areas. https://fastapi.tiangolo.com/
- FastAPI OAuth2/JWT guide for token authentication patterns. https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
- Python official docs: current documentation line is Python 3.14.6. https://docs.python.org/3/
- LangGraph official docs: low-level orchestration runtime for long-running, stateful agents with durable execution, streaming, human-in-the-loop, and persistence. https://docs.langchain.com/oss/python/langgraph/overview
- LangGraph persistence docs: use checkpointers for thread-scoped graph state and stores for long-term cross-thread memory. https://docs.langchain.com/oss/python/langgraph/persistence
- Pinecone hybrid search docs: combine semantic and lexical search; single-index dense+sparse is simpler, but alpha weighting is required because sparse and dense scores are not naturally comparable. https://docs.pinecone.io/guides/search/hybrid-search
- NIST Cybersecurity Framework 2.0: Govern, Identify, Protect, Detect, Respond, Recover and risk-management profiles. https://www.nist.gov/cyberframework
- OWASP API Security Top 10 2023: authorization, authentication, resource limits, SSRF, misconfiguration, inventory, and unsafe third-party API consumption risks. https://owasp.org/API-Security/editions/2023/en/0x11-t10/
- MITRE ATT&CK: adversary tactics and techniques knowledge base for threat modeling, detection mapping, and investigation context. https://attack.mitre.org/

## Product Goals

Build an enterprise SOC platform that ingests security telemetry, normalizes it, correlates events into alerts and incidents, enriches entities with threat intelligence, orchestrates AI-assisted investigations, and supports human-approved response actions.

The platform must support:

- High-volume event ingestion from common SOC sources.
- Alert triage, deduplication, prioritization, and incident grouping.
- Human-readable evidence chains and citations for AI outputs.
- MITRE ATT&CK mapping across alerts, incidents, and reports.
- Strong tenant isolation, RBAC, audit logging, and API security.
- Deployment from local Docker Compose to Kubernetes.

Non-goals for early phases:

- Fully autonomous remediation without human approval.
- Vendor-specific EDR deep integrations before the ingestion contract is stable.
- Training custom LLMs before retrieval, evaluation, and safety controls exist.

## Architecture Principles

- Security by default: every endpoint requires authentication unless explicitly marked public; every object access is tenant-scoped and permission-checked.
- Clean architecture: API routes call services; services coordinate domain logic; repositories isolate database access; integrations isolate external systems.
- Async I/O by default on the backend for database, cache, vector DB, LLM, and enrichment calls.
- Explicit agent graphs: use LangGraph state machines for multi-step workflows instead of unbounded agent loops.
- Human approval gates: any containment or destructive response action requires review, role authorization, and audit logging.
- Explainability: AI-generated triage, risk scores, reports, and recommendations must include source evidence, confidence, and reasoning summaries.
- Observability first: traces, structured logs, metrics, health checks, and audit trails are required platform features.
- Evaluation-driven AI: prompts, retrieval, agent routing, and scoring rules must be tested with representative alert datasets.

## Technology Decisions

### Frontend

Use Next.js App Router with React, TypeScript, Tailwind CSS, and shadcn/ui.

Decision:

- Target Next.js 16 for new implementation because the official docs list 16.2.9 as the current latest version. `todo.md` says Next.js 15, but the design should follow the current stable docs unless a deployment or dependency blocker appears.
- Use Server Components for data-heavy read views where possible.
- Use Client Components only for interactive state such as filters, live timelines, tables, graph exploration, and forms.
- Use TanStack Query for client-side server-state caching where WebSocket/live updates or complex mutations are needed.
- Use strict TypeScript, typed API clients generated from OpenAPI, and runtime validation for untrusted data.

Frontend structure:

```text
frontend/
  app/
    (auth)/
    (dashboard)/
    api/
  components/
    layout/
    ui/
    soc/
    investigation/
    threat-intel/
  lib/
    api/
    auth/
    telemetry/
    validation/
  tests/
```

### Backend

Use FastAPI with Python, async SQLAlchemy, Pydantic, PostgreSQL, Redis, and OpenAPI.

Decision:

- Start with Python 3.12 if dependency support is the priority; move to Python 3.14 only after FastAPI, SQLAlchemy, LangGraph, Pinecone, and deployment images are verified against it. The docs line is current at Python 3.14.6, but enterprise stability matters more than version novelty.
- Use `fastapi[standard]` installation pattern from official FastAPI docs when scaffolding.
- Use FastAPI dependencies for authentication, authorization, tenant context, database sessions, and service injection.
- Use Pydantic models for request/response schemas and domain-safe validation.
- Generate OpenAPI docs and use them as the contract for frontend clients and integration tests.

Backend structure:

```text
backend/
  app/
    main.py
    api/
      v1/
        auth.py
        alerts.py
        incidents.py
        investigations.py
        threat_intel.py
        reports.py
        agents.py
        ingestion.py
    core/
      config.py
      security.py
      logging.py
      errors.py
      permissions.py
    domain/
      alerts/
      incidents/
      investigations/
      threat_intel/
      reports/
      users/
      agents/
    infrastructure/
      db/
      redis/
      vector/
      llm/
      integrations/
    workers/
    tests/
```

### Datastores

Use PostgreSQL as the system of record, Redis for cache/session/rate-limit coordination, and Pinecone for vector retrieval.

PostgreSQL:

- Use UUID primary keys for externally visible resources.
- Add `tenant_id` to tenant-scoped tables and enforce tenant filters in repositories.
- Partition high-volume event tables by time.
- Use JSONB for raw vendor payloads, but extract indexed fields needed for query, correlation, and joins.
- Add audit tables for all sensitive reads, writes, role changes, and response actions.

Redis:

- Short-lived access token denylist and refresh token rotation metadata where needed.
- Rate limiting counters.
- WebSocket fanout and live dashboard event buffering.
- Short-lived enrichment cache for external threat intel lookups.

Pinecone:

- Use hybrid retrieval for SOC knowledge because exact terms such as CVE IDs, hashes, commands, and MITRE technique IDs matter alongside semantic matches.
- Prefer a single dense+sparse index first for lower operational overhead.
- Apply explicit alpha weighting at query time and evaluate alpha values against a labeled SOC relevance set.
- Add reranking for top-k results before sending context to LLMs.

## Core Domain Model

Initial tables:

- `tenants`: organization boundary.
- `users`: identity records.
- `roles`: role definitions.
- `permissions`: permission names.
- `user_roles`: user-to-role assignments scoped by tenant.
- `api_keys`: service ingestion credentials.
- `assets`: hosts, users, cloud resources, containers, identities.
- `data_sources`: configured log and alert sources.
- `raw_events`: immutable incoming telemetry.
- `normalized_events`: parsed events with common schema fields.
- `alerts`: deduplicated security alerts.
- `incidents`: grouped alert investigations.
- `incident_alerts`: incident-alert join table.
- `observables`: IPs, domains, URLs, hashes, users, files, registry keys.
- `threat_intel_enrichments`: reputation, CVE, geolocation, ASN, malware, and source metadata.
- `investigations`: agent/human investigation sessions.
- `investigation_evidence`: cited facts used in findings.
- `agent_runs`: LangGraph run metadata, status, model, cost, and trace IDs.
- `agent_steps`: step-level state transitions and tool calls.
- `response_actions`: recommended or executed actions.
- `reports`: executive, technical, RCA, and compliance reports.
- `audit_logs`: immutable security and administrative audit records.

Core relationships:

- Tenant owns users, data sources, assets, alerts, incidents, investigations, reports, and audit logs.
- Incident groups many alerts.
- Alert links to normalized events and observables.
- Investigation links to one incident and many evidence records.
- Agent run links to investigation, incident, and agent steps.
- Response action links to incident, recommendation, approver, executor, and audit log.

## API Design

API version root: `/api/v1`.

Endpoint groups:

- `/auth`: login, refresh, logout, MFA challenge, current user.
- `/users`: user management.
- `/roles`: role and permission management.
- `/ingestion`: event, alert, and source ingestion.
- `/alerts`: alert queue, filters, assignment, status changes.
- `/incidents`: incident lifecycle, severity, status, ownership, evidence.
- `/investigations`: timelines, correlations, agent sessions, evidence graph.
- `/threat-intel`: observable enrichment and history.
- `/agents`: run agent workflows, stream state, approve gates.
- `/reports`: generate, list, export, and approve reports.
- `/settings`: tenant settings, source config, response policies.
- `/health`: liveness and readiness.

API rules:

- Use OpenAPI tags and response models for every endpoint.
- Use cursor pagination for event, alert, and audit listings.
- Use idempotency keys for ingestion and response-action requests.
- Use optimistic concurrency or version fields for incident updates.
- Never expose raw secrets or full tokens in responses or logs.
- Validate every object-level authorization check, especially IDs supplied by clients.

## Authentication And Authorization

Authentication:

- JWT access tokens with short TTL.
- Refresh token rotation with reuse detection.
- MFA-ready login flow.
- Service API keys for ingestion only, scoped to data sources and tenants.

Authorization:

- RBAC with permission strings such as `alerts:read`, `incidents:update`, `response:approve`, `admin:roles`.
- Object-level authorization on every tenant-scoped resource.
- Administrative functions isolated from analyst functions.
- Break-glass roles require reason capture and audit logging.

Security controls mapped from OWASP API Top 10:

- Broken object-level authorization: repository tenant filters and service-level permission checks.
- Broken authentication: short-lived access tokens, refresh rotation, password hashing, MFA-ready design.
- Object property authorization: separate public/internal response schemas and field-level update allowlists.
- Resource consumption: rate limits, body size limits, queue quotas, and bounded agent/tool execution.
- Function authorization: route-level permissions and explicit admin route grouping.
- SSRF: block arbitrary URL fetches; use allowlisted enrichment providers.
- Misconfiguration: secure defaults, dependency scanning, no debug endpoints in production.
- Inventory management: OpenAPI as API inventory, versioning, and deprecation policy.
- Unsafe third-party APIs: schema validation, timeouts, retries, circuit breakers, and provenance tracking.

## AI And RAG Design

Knowledge sources:

- MITRE ATT&CK techniques, tactics, mitigations, detections, and data sources.
- NIST CSF 2.0 references and internal policies.
- CVE/NVD data and vendor advisories.
- Internal incident playbooks and post-incident reports.
- Product-specific parser and response-action runbooks.

Ingestion pipeline:

1. Load document metadata and source provenance.
2. Normalize content into markdown/plain text.
3. Chunk by semantic sections with stable IDs.
4. Generate dense embeddings and sparse vectors.
5. Store source, title, version, URL, timestamp, tenant scope, and hash metadata.
6. Evaluate retrieval quality with labeled SOC queries before production promotion.

Retrieval policy:

- Use hybrid dense+sparse retrieval by default.
- Tune alpha values per query type:
  - Dense-leaning for natural-language investigation questions.
  - Balanced for playbook and report generation.
  - Sparse-leaning for hashes, CVEs, technique IDs, commands, and exact indicators.
- Rerank top candidates.
- Pass only cited, permission-allowed chunks to the LLM.
- Require generated answers to include evidence references.

LLM policy:

- Make model provider configurable.
- Treat Nemotron as primary only after latency, cost, privacy, and quality evaluation.
- Keep fallbacks for Qwen, Llama, and DeepSeek behind the same interface.
- Do not allow model output to execute response actions directly.
- Log prompt template version, model, retrieval IDs, token usage, latency, and evaluation signals.

## Agent Design

Use LangGraph for all multi-step agents.

Agent state must include:

- `tenant_id`
- `incident_id` or `alert_id`
- current objective
- evidence IDs
- retrieved document IDs
- intermediate findings
- confidence
- required approvals
- next action
- terminal status

Agents:

- Alert Triage Agent: deduplicate, categorize, assign severity, map likely MITRE tactics/techniques.
- Threat Intelligence Agent: enrich observables, map CVEs, reputation, ASN, geolocation, malware family.
- Investigation Agent: build timelines, correlate entities, identify likely attack chain, produce evidence graph.
- Threat Hunting Agent: search for similar behavior across assets, users, and time windows.
- Risk Scoring Agent: produce 0-100 risk score with confidence and factor breakdown.
- Report Generation Agent: generate executive, technical, RCA, and compliance reports with citations.
- Response Agent: recommend actions and prepare execution plans; execution requires approval.

LangGraph usage:

- Use checkpointers for investigation thread state.
- Use stores for durable cross-thread memory such as analyst preferences and reusable lessons learned.
- Add interrupt/human-in-the-loop gates before response actions and before reports are marked final.
- Keep graph edges explicit and test each node in isolation.
- Persist graph state IDs in `agent_runs`.

## Frontend Experience

The UI should be a dense operational SOC application, not a marketing site.

Primary views:

- Executive Dashboard: risk posture, active critical incidents, SLA, compliance indicators.
- SOC Dashboard: live alert queue, severity distribution, source health, triage throughput.
- Incident Workspace: timeline, evidence, affected assets, observables, agent findings, response plan.
- Investigation Graph: entity and event relationships with filters.
- Threat Intel Workspace: observable lookup, enrichment history, reputation and source confidence.
- Analytics: trends, MITRE ATT&CK heatmap, false positive rates, MTTD, MTTR.
- Reports: generated reports, approvals, export history.
- Settings: data sources, roles, response policies, model settings, audit.

UI rules:

- Use tables, split panes, tabs, filters, command menus, and timelines for analyst workflows.
- Keep visual styling restrained, high-contrast, and scan-friendly.
- Use icons for common toolbar actions.
- Do not hide critical status behind decorative cards.
- Every AI output must show evidence, confidence, and review state.
- Live updates must not reorder analyst work unexpectedly; preserve user-selected filters and row focus.

## Observability

Structured logs:

- JSON logs with request ID, tenant ID, user ID, route, status, duration, and trace ID.
- Never log credentials, tokens, raw secrets, or sensitive payloads.

Metrics:

- API latency, error rate, throughput.
- Ingestion lag and parse failure rate.
- Alert deduplication rate and incident grouping rate.
- Agent run latency, success/failure rate, approval rate, token cost.
- RAG retrieval hit rate, rerank latency, citation coverage.
- Queue depth for ingestion and agent tasks.

Tracing:

- OpenTelemetry for backend requests, database calls, Redis calls, vector search, LLM calls, and agent steps.
- Link frontend user actions to backend request IDs where practical.

Health checks:

- Liveness: process is running.
- Readiness: database, Redis, vector DB, and worker dependencies are reachable.

## Deployment Design

Local development:

- Docker Compose for PostgreSQL, Redis, backend, frontend, workers, and optional observability stack.
- Seed scripts for demo tenants, users, data sources, and sample alerts.

Production:

- Kubernetes deployments for frontend, backend API, workers, scheduler, and WebSocket service.
- Horizontal scaling for stateless API and workers.
- PostgreSQL managed service preferred.
- Redis managed service preferred.
- Secrets from a secret manager, not committed files.
- TLS at ingress.
- Network policies between services.
- Separate namespaces/environments for dev, staging, and production.

CI/CD:

- Lint, typecheck, tests, build, dependency audit, container scan.
- Database migrations run as a controlled deployment step.
- Preview deployments for frontend.
- Staging smoke tests before production.

## Testing Strategy

Backend:

- Unit tests for services, parsers, permissions, and risk scoring.
- Repository tests with a real PostgreSQL test database.
- API integration tests generated from OpenAPI expectations.
- Security tests for auth, tenant isolation, object-level access, rate limits, and SSRF controls.

Frontend:

- Component tests for critical UI states.
- API client contract tests.
- Playwright E2E for login, alert triage, incident investigation, report generation, and approval flow.
- Accessibility checks on primary workflows.

AI/RAG:

- Retrieval benchmark set with SOC queries and expected evidence.
- Golden tests for prompt templates and output schemas.
- Agent graph tests for success, failure, retry, and human approval branches.
- Red-team tests for prompt injection and unsafe tool use.

Performance:

- Load test ingestion and alert queue APIs.
- Measure dashboard query latency under realistic data volume.
- Measure agent concurrency and cost ceilings.

## Coding Standards

General:

- Read official docs before adding a new language, framework, or major library.
- Prefer current stable versions, but do not upgrade past ecosystem support.
- Keep design decisions in this file or an ADR.
- Write code that is explicit, typed, testable, and observable.
- No toy examples in production paths.

Python:

- Use type hints everywhere.
- Use async only when the call stack and libraries support async I/O.
- Keep route handlers thin.
- Use services for business logic and repositories for data access.
- Use Pydantic schemas at boundaries.
- Use Alembic for migrations.
- Use Ruff or equivalent linting/formatting once the backend is scaffolded.

TypeScript/React:

- Use strict TypeScript.
- Prefer Server Components for read-heavy screens.
- Keep Client Components focused and small.
- Use generated API types from OpenAPI.
- Validate external data at runtime.
- Avoid global mutable client state for server data; use TanStack Query where appropriate.

SQL:

- Every tenant-scoped query must filter by `tenant_id`.
- Add indexes based on query patterns, not guesswork.
- Use migrations for all schema changes.
- Avoid ad hoc JSONB-only modeling for fields that need filtering, joining, or reporting.

Security:

- Secrets only through environment variables or secret manager.
- No credentials in code, logs, tests, or docs.
- Hash passwords with a modern password hashing scheme.
- All response actions require authorization, approval, and audit logging.
- All third-party calls need timeouts, retries, and circuit breakers.

## Initial Implementation Order

1. Create repository structure and developer documentation.
2. Scaffold FastAPI backend with health checks, config, structured logging, and OpenAPI.
3. Add PostgreSQL, Redis, migrations, and base domain models.
4. Implement auth, RBAC, tenant context, and audit logging.
5. Implement ingestion contract and normalized event schema.
6. Build alert and incident APIs.
7. Scaffold Next.js frontend with authenticated layout and SOC dashboard shell.
8. Add RAG ingestion/retrieval prototype with evaluation harness.
9. Add LangGraph triage and investigation workflows with persisted state.
10. Add CI, Docker Compose, tests, and deployment manifests.

## Open Decisions

- Final Python runtime version after dependency verification: Python 3.12 for stability vs Python 3.14 for latest runtime.
- Primary LLM provider and fallback order after quality, latency, cost, and privacy evaluation.
- Pinecone single hybrid index vs separate dense/sparse indexes after labeled retrieval benchmark.
- WebSocket vs Server-Sent Events for live UI updates after dashboard interaction design.
- Initial normalized event schema: ECS-compatible, OCSF-compatible, or custom SOC schema.
