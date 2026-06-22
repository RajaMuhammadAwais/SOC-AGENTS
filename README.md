# Enterprise AI SOC Platform

Production-oriented AI Security Operations Center platform combining SIEM, SOAR, threat intelligence, RAG, and multi-agent investigation workflows.

## Current Phase

Phase 1 foundation is in progress. The repository now contains:

- `design.md`: high-level requirements plus research-backed implementation baseline.
- `docs/api-spec.md`: REST API contract outline.
- `docs/database-schema.md`: initial database model and ER diagram.
- `backend/`: FastAPI service skeleton.
- `frontend/`: Next.js App Router skeleton.
- `infra/`: local Docker Compose baseline.

## Research Rule

Before adding a language, framework, or major library, read the official docs and record material decisions in `design.md` or an ADR. Current baseline sources include FastAPI, Next.js, Python, LangGraph, Pinecone, NIST CSF 2.0, OWASP API Security Top 10, and MITRE ATT&CK.

## Local Development

Dependencies are not installed yet. After dependency installation is approved:

```bash
cd backend
python -m venv .venv
pip install -e ".[dev]"
fastapi dev app/main.py
```

```bash
cd frontend
npm install
npm run dev
```

Use `.env.example` as the safe template. Do not commit `.env`.
