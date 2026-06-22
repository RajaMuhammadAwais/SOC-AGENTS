# API Specification

Status: Draft 1
Base path: `/api/v1`

All tenant-scoped endpoints require authentication, tenant context, RBAC permission checks,
and object-level authorization.

## Endpoint Groups

| Group | Purpose |
| --- | --- |
| `/auth` | Login, refresh, logout, MFA challenge, current user |
| `/users` | User management |
| `/roles` | Role and permission management |
| `/ingestion` | Events, alerts, and source ingestion |
| `/alerts` | Alert queue, filters, assignment, status changes |
| `/incidents` | Incident lifecycle, severity, ownership, evidence |
| `/investigations` | Timelines, correlations, agent sessions |
| `/threat-intel` | Observable enrichment |
| `/agents` | Run and stream agent workflows |
| `/reports` | Generate, list, export, approve reports |
| `/settings` | Tenant settings, source configuration, response policy |
| `/health` | Liveness and readiness |

## Cross-Cutting Rules

- Use cursor pagination on high-cardinality lists.
- Use idempotency keys for ingestion and response actions.
- Use typed request and response schemas for every operation.
- Return trace IDs in error responses.
- Do not return secrets, raw tokens, or hidden authorization fields.
- Every endpoint must declare required permissions in code and OpenAPI metadata.

## Initial OpenAPI Targets

| Method | Path | Permission | Notes |
| --- | --- | --- | --- |
| `GET` | `/health/live` | Public | Process liveness |
| `GET` | `/health/ready` | Public | Dependency readiness |
| `POST` | `/auth/login` | Public | Password plus MFA-ready challenge |
| `POST` | `/auth/refresh` | Public | Refresh token rotation |
| `POST` | `/ingestion/events` | `ingestion:write` | Idempotent event ingest |
| `GET` | `/alerts` | `alerts:read` | Cursor-paginated queue |
| `PATCH` | `/alerts/{alert_id}` | `alerts:update` | Status, owner, severity updates |
| `POST` | `/incidents` | `incidents:create` | Create incident from alerts |
| `GET` | `/incidents/{incident_id}` | `incidents:read` | Incident details and evidence |
| `POST` | `/agents/triage-runs` | `agents:run` | Starts alert triage graph |
| `POST` | `/response-actions/{action_id}/approve` | `response:approve` | Human approval gate |
