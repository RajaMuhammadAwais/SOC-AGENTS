"""Integration tests for the agent episodic memory service.

Requires the sandbox PostgreSQL (pgvector enabled) reachable at DATABASE_URL.
Tests embedding-then-storage and semantic recall ordering.
"""
import asyncio
import os
import uuid

import pytest

from app.domain.agents.memory import MemoryService, memory_narrative_text
from app.domain.models import AgentMemory
from app.infrastructure.db.session import get_db_session
from app.infrastructure.embeddings import BGEM3EmbeddingProvider

pytestmark = [
    pytest.mark.skipif(
        os.environ.get("APP_ENV") != "local",
        reason="requires local postgres with pgvector",
    )
]

TENANT_SLUG = "acme"
ACME_TENANT_ID = os.environ.get("TEST_TENANT_ID", "")


async def _resolve_acme_tenant() -> str:
    """Resolve the acme tenant from the database (created by seed_demo_tenant.py)."""
    from sqlalchemy import text

    async for session in get_db_session():
        async with session:
            row = await session.execute(
                text("SELECT id FROM tenants WHERE slug = :slug"), {"slug": TENANT_SLUG}
            )
            tenant = row.scalar_one_or_none()
            await session.commit()
            if tenant:
                return str(tenant)
            raise RuntimeError("acme tenant missing; run scripts/seed_demo_tenant.py")


def _provider() -> BGEM3EmbeddingProvider:
    return BGEM3EmbeddingProvider.from_settings(
        __import__("app.core.config", fromlist=["Settings"]).Settings()
    )


async def _run(coro):
    return await coro


@pytest.mark.asyncio
async def test_memory_store_and_recall_ordering():
    provider = _provider()
    service = MemoryService(provider)
    tenant_id = await _resolve_acme_tenant()

    async for session in get_db_session():
        async with session:
            # Seed two distinct memories: one about SSH brute force, one about phishing.
            await service.store(
                session=session,
                tenant_id=tenant_id,
                kind="lesson",
                title="SSH brute force usually resolves within an hour",
                narrative="Repeated failed SSH logins from residential proxies stopped after the firewall rule blocked the subnet.",
                related_ids={"source": "test"},
            )
            await service.store(
                session=session,
                tenant_id=tenant_id,
                kind="decision",
                title="Phishing domain reported to registrar",
                narrative="The look-alike domain mimicking the corporate login page was reported to the registrar and sinkholed.",
                related_ids={"source": "test"},
            )
            await session.commit()

            # Querying about authentication brute force should rank the SSH lesson higher.
            recalls = await service.recall(session, tenant_id, "authentication brute force attempts", top_k=2)
            assert len(recalls) >= 2
            assert "SSH" in recalls[0].narrative, "semantic recall should rank the SSH lesson first"
            assert 0.0 <= recalls[0].score <= 1.0


@pytest.mark.asyncio
async def test_memory_kind_validation():
    """Kind validation is deterministic and does not touch the database."""
    provider = _provider()
    service = MemoryService(provider)
    async for session in get_db_session():
        async with session:
            with pytest.raises(ValueError):
                await service.store(
                    session=session,
                    tenant_id="00000000-0000-0000-0000-000000000000",
                    kind="invalid_kind",
                    title="t",
                    narrative="n",
                )


def test_memory_narrative_text_format() -> None:
    memory = AgentMemory(kind="lesson", title="Blocked subnet", narrative="Subnet blocked after brute force")
    text = memory_narrative_text(memory)
    assert text.startswith("lesson: ")
