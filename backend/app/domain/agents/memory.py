"""Episodic memory service for SOC agents (case-based reasoning).

Agents record decisions, executed actions, outcomes, and analyst-confirmed
lessons as typed memories. Memories are embedded (bge-m3 dense vectors) and
stored in the `agent_memories` pgvector column, enabling semantic recall of
similar past investigations when triaging new alerts.

Multi-tenant: every query is scoped to tenant_id.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from pgvector.sqlalchemy import Vector as PgVector
from sqlalchemy import literal, select
from sqlalchemy.ext.asyncio import AsyncSession

# The protocol lives in domain/embeddings.py; runtime implementations are in
# app.infrastructure.embeddings (e.g. BGEM3EmbeddingProvider).
from app.domain.embeddings import EmbeddingProvider, EmbeddingRequest
from app.domain.models import AgentMemory


@dataclass(frozen=True)
class MemoryRecall:
    memory_id: str
    kind: str
    title: str
    narrative: str
    score: float


MAX_RECALL_RESULTS = 5
MEMORY_KINDS = ("decision", "action", "outcome", "lesson")


def memory_narrative_text(memory: AgentMemory) -> str:
    return f"{memory.kind}: {memory.title}. {memory.narrative}"


class MemoryService:
    def __init__(self, embedding_provider: EmbeddingProvider) -> None:
        self._provider = embedding_provider

    async def store(
        self,
        session: AsyncSession,
        tenant_id: str,
        kind: str,
        title: str,
        narrative: str,
        related_ids: dict | None = None,
    ) -> AgentMemory:
        if kind not in MEMORY_KINDS:
            raise ValueError(f"memory kind must be one of {MEMORY_KINDS}")

        embeddings = await self._provider.embed(EmbeddingRequest(texts=[f"{title}. {narrative}"]))
        dense = embeddings[0].dense

        memory = AgentMemory(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            kind=kind,
            title=title[:255],
            narrative=narrative,
            related_ids=related_ids or {},
            vector=dense,
        )
        session.add(memory)
        await session.flush()
        return memory

    async def recall(self, session: AsyncSession, tenant_id: str, query: str, top_k: int = MAX_RECALL_RESULTS) -> list[MemoryRecall]:
        embeddings = await self._provider.embed(EmbeddingRequest(texts=[query]))
        dense = embeddings[0].dense
        # pgvector cosine distance: <=> ; nearest first = smallest distance.
        # Render the dense vector as a literal SQL array cast to vector so
        # asyncpg transmits it with the correct type (a plain Python list is
        # rejected by asyncpg's text encoder).
        vector_literal = literal(dense, PgVector)
        statement = (
            select(
                AgentMemory.id,
                AgentMemory.kind,
                AgentMemory.title,
                AgentMemory.narrative,
                AgentMemory.vector.cosine_distance(vector_literal).label("distance"),
            )
            .where(AgentMemory.tenant_id == tenant_id, AgentMemory.vector.is_not(None))
            .order_by(AgentMemory.vector.cosine_distance(vector_literal))
            .limit(top_k)
        )
        rows = await session.execute(statement)
        results: list[MemoryRecall] = []
        for row in rows:
            results.append(
                MemoryRecall(
                    memory_id=str(row.id),
                    kind=row.kind,
                    title=row.title,
                    narrative=row.narrative,
                    score=round(1.0 - float(row.distance), 4),
                )
            )
        return results

    async def list_memories(self, session: AsyncSession, tenant_id: str, kind: str | None = None) -> list[AgentMemory]:
        statement = select(AgentMemory).where(AgentMemory.tenant_id == tenant_id)
        if kind:
            statement = statement.where(AgentMemory.kind == kind)
        statement = statement.order_by(AgentMemory.created_at.desc())
        result = await session.execute(statement)
        return list(result.scalars().all())
