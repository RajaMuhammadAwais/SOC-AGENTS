"""Semantic knowledge-base service for SOC agents.

Knowledge documents (playbooks, runbooks, MITRE tactics guidance, lessons
learned) are chunked, embedded (bge-m3) and stored in the existing
`vector_chunks` pgvector table with HNSW index. Agents ground their reasoning
via hybrid retrieval (RAG) scoped to the requesting tenant.

Follows the established retrieval contract:
- app.domain.rag.RetrievalQuery / RetrievalService / RetrievedEvidence
- app.rag.pipeline.generate_rag_answer
- app.rag.indexing (embed_document_chunks, to_pinecone_vectors)
- app.infrastructure.vector.pgvector_client.PgvectorSink
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.embeddings import EmbeddingProvider, EmbeddingRequest
from app.domain.models import KnowledgeDocument
from app.domain.rag import (
    RetrievalQuery,
    RetrievalService,
    RetrievedEvidence,
)
from app.infrastructure.vector.pgvector_client import PgvectorSink
from app.rag.chunking import Document
from app.rag.indexing import embed_document_chunks, to_pinecone_vectors


class KnowledgeService:
    def __init__(self, embedding_provider: EmbeddingProvider) -> None:
        self._embedding = embedding_provider

    async def upsert_document(
        self,
        session: AsyncSession,
        tenant_id: str,
        title: str,
        category: str,
        body: str,
        tags: list[str] | None = None,
    ) -> KnowledgeDocument:
        existing = (
            await session.execute(
                select(KnowledgeDocument).where(
                    KnowledgeDocument.tenant_id == tenant_id,
                    KnowledgeDocument.title == title[:512],
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            existing.body = body
            existing.category = category
            existing.tags = tags or []
            existing.indexed = False
            document = existing
        else:
            document = KnowledgeDocument(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                title=title[:512],
                category=category,
                body=body,
                tags=tags or [],
            )
            session.add(document)
        await session.flush()
        return document

    async def index_document(self, session: AsyncSession, tenant_id: str, document_id: str) -> int:
        document = await session.get(KnowledgeDocument, document_id)
        if document is None or str(document.tenant_id) != tenant_id:
            raise ValueError("knowledge document not found for tenant")

        embedded_chunks = await embed_document_chunks(
            document=Document(
                source_id=f"knowledge:{document_id}",
                title=document.title,
                text=document.body,
                metadata={"category": document.category, "tags": ",".join(document.tags or [])},
            ),
            embedding_provider=self._embedding,
        )
        if not embedded_chunks:
            document.indexed = True
            return 0

        vectors = to_pinecone_vectors(tenant_id=uuid.UUID(tenant_id), embedded_chunks=embedded_chunks)
        sink = PgvectorSink(session)
        await sink.upsert(vectors, namespace=tenant_id)
        document.indexed = True
        return len(vectors)


class KnowledgeRetrievalService(RetrievalService):
    """Tenant-scoped RetrievalService backed by PgvectorSink hybrid search."""

    def __init__(self, sink: PgvectorSink, embedding_provider: EmbeddingProvider) -> None:
        self._sink = sink
        self._embedding = embedding_provider

    async def search(self, query: RetrievalQuery) -> list[RetrievedEvidence]:
        embeddings = await self._embedding.embed(
            EmbeddingRequest(texts=[query.query], return_sparse=True)
        )
        dense = embeddings[0].dense

        rows = await self._sink.hybrid_search(
            tenant_id=str(query.tenant_id),
            query_vector=dense,
            query_text=query.query,
            limit=query.top_k,
            alpha=query.alpha,
        )
        return [
            RetrievedEvidence(
                chunk_id=row["id"],
                score=float(row["similarity"] or 0.0),
                title=row["title"],
                text=row["text"],
                citation={
                    key: value
                    for key, value in (row.get("metadata") or {}).items()
                    if isinstance(value, str)
                },
            )
            for row in rows
        ]
