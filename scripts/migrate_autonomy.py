"""Schema migration for the autonomous agent capability layer.

Adds three tables:
- agent_skills: declarative capability registry (procedural memory)
- knowledge_documents: curated semantic knowledge (RAG corpus)
- agent_memories: episodic memory with pgvector embedding column

Idempotent: safe to run multiple times against the same database.

Run with the sandbox PostgreSQL connection:
    env APP_ENV=local DATABASE_URL=postgresql+asyncpg://soc:soc@localhost:5432/soc \
        /home/ubuntu/soc_venv/bin/python scripts/migrate_autonomy.py
"""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


DDL: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS agent_skills (
        id UUID PRIMARY KEY,
        tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        name VARCHAR(160) NOT NULL,
        description TEXT NOT NULL,
        risk_class VARCHAR(32) NOT NULL,
        execution_policy VARCHAR(32) NOT NULL DEFAULT 'allow',
        required_permission VARCHAR(160) NOT NULL,
        parameters_schema JSONB NOT NULL DEFAULT '{}',
        enabled BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_agent_skills_tenant ON agent_skills (tenant_id);
    """,
    """
    CREATE TABLE IF NOT EXISTS knowledge_documents (
        id UUID PRIMARY KEY,
        tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        title VARCHAR(512) NOT NULL,
        category VARCHAR(120) NOT NULL DEFAULT 'playbook',
        body TEXT NOT NULL,
        tags JSONB NOT NULL DEFAULT '[]',
        indexed BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_knowledge_documents_tenant ON knowledge_documents (tenant_id);
    """,
    """
    CREATE TABLE IF NOT EXISTS agent_memories (
        id UUID PRIMARY KEY,
        tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        kind VARCHAR(60) NOT NULL,
        title VARCHAR(255) NOT NULL,
        narrative TEXT NOT NULL,
        related_ids JSONB NOT NULL DEFAULT '{}',
        vector VECTOR(1024),
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_agent_memories_tenant ON agent_memories (tenant_id);
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_agent_memories_tenant_kind ON agent_memories (tenant_id, kind);
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_agent_memories_vector
        ON agent_memories USING hnsw (vector vector_cosine_ops) WITH (m = 16, ef_construction = 128);
    """,
]


async def main() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL environment variable is required")
    engine = create_async_engine(database_url, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession)
    async with engine.begin() as conn:
        pass
    async with async_session() as session:
        for statement in DDL:
            await session.execute(text(statement))
        await session.commit()
    print("Autonomy schema migration applied successfully.")


if __name__ == "__main__":
    asyncio.run(main())
