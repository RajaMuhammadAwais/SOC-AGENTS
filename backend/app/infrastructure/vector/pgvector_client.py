"""pgvector-backed vector storage for SOC knowledge retrieval.

Stores chunk embeddings (dense 1024-d from bge-m3, sparse values for lexical
hybrid search) in the `vector_chunks` table and exposes tenant-scoped
similarity / keyword / hybrid retrieval.

Table layout
    vector_chunks (
        id           uuid PK          -- stable chunk id (sha256[:32])
        tenant_id    uuid             -- isolation key (namespace)
        source_id    text             -- owning document/source reference
        title        text
        text         text
        keywords     tsvector         -- lexical index
        dense_vector vector(1024)     -- pgvector HNSW index
        sparse_indices int[]
        sparse_values  real[]
        metadata     jsonb
    )

The HNSW index uses cosine distance, matching bge-m3's normalized embeddings.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

VECTOR_DIMENSION = 1024


@dataclass(frozen=True)
class VectorRow:
    id: str
    tenant_id: str
    source_id: str
    title: str
    text: str
    metadata: dict[str, str]
    score: float


CREATE_EXTENSION = "CREATE EXTENSION IF NOT EXISTS vector"

CREATE_TABLE = f"""
CREATE TABLE IF NOT EXISTS vector_chunks (
    id uuid NOT NULL PRIMARY KEY,
    tenant_id uuid NOT NULL,
    source_id text NOT NULL,
    title text NOT NULL,
    text text NOT NULL,
    keywords tsvector GENERATED ALWAYS AS (to_tsvector('english', text)) STORED,
    dense_vector vector({VECTOR_DIMENSION}) NOT NULL,
    sparse_indices int[] NULL,
    sparse_values real[] NULL,
    metadata jsonb NOT NULL DEFAULT '{{}}'::jsonb
)
"""

CREATE_INDEXES = [
    # pgvector HNSW (cosine <=>) — built in the background for large tables.
    """CREATE INDEX IF NOT EXISTS ix_vector_chunks_dense_hnsw
        ON vector_chunks USING hnsw (dense_vector vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)""",
    """CREATE INDEX IF NOT EXISTS ix_vector_chunks_tenant
        ON vector_chunks (tenant_id)""",
    """CREATE INDEX IF NOT EXISTS ix_vector_chunks_keywords
        ON vector_chunks USING gin (keywords)""",
]


async def initialize_vector_schema(session: AsyncSession) -> None:
    """Create the pgvector extension, table and indexes if missing."""
    await session.execute(text(CREATE_EXTENSION))
    await session.execute(text(CREATE_TABLE))
    for statement in CREATE_INDEXES:
        await session.execute(text(statement))
    await session.commit()


class PgvectorSink:
    """Tenant-namespace upsert and retrieval over `vector_chunks`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(
        self,
        vectors: list[VectorRecord],
        namespace: str | None = None,
    ) -> int:
        """Insert or update chunks. `namespace` is coerced into tenant_id on rows missing it."""
        if not vectors:
            return 0
        upsert = text(
            """
            INSERT INTO vector_chunks
                (id, tenant_id, source_id, title, text, sparse_indices, sparse_values, metadata, dense_vector)
            VALUES
                (:id, :tenant_id, :source_id, :title, :text, :sparse_indices,
                 :sparse_values, :metadata::jsonb, :dense_vector::vector)
            ON CONFLICT (id) DO UPDATE SET
                source_id = EXCLUDED.source_id,
                title = EXCLUDED.title,
                text = EXCLUDED.text,
                sparse_indices = EXCLUDED.sparse_indices,
                sparse_values = EXCLUDED.sparse_values,
                metadata = EXCLUDED.metadata,
                dense_vector = EXCLUDED.dense_vector
            """
        )
        rows = [
            {
                "id": vec.id,
                "tenant_id": vec.tenant_id or namespace,
                "source_id": vec.source_id,
                "title": vec.title,
                "text": vec.text,
                "sparse_indices": vec.sparse_indices,
                "sparse_values": vec.sparse_values,
                "metadata": dict(vec.metadata) if vec.metadata else {},
                "dense_vector": vec.values,
            }
            for vec in vectors
        ]
        for vec in rows:
            if vec["tenant_id"] is None:
                raise ValueError("vector row is missing tenant_id and no namespace given")
        await self._session.execute(upsert, rows)
        await self._session.commit()
        return len(rows)

    async def similarity_search(
        self,
        tenant_id: str,
        query_vector: list[float],
        limit: int = 10,
        metadata_filter: dict[str, str] | None = None,
    ) -> list[VectorRow]:
        where = "tenant_id = :tenant_id AND dense_vector IS NOT NULL"
        filters, params = self._metadata_filters(metadata_filter)
        params.update({"tenant_id": tenant_id, "query_vector": query_vector, "limit": limit})
        statement = text(
            f"""
            SELECT id, tenant_id, source_id, title, text, metadata,
                   1 - (dense_vector <=> :query_vector::vector) AS score
            FROM vector_chunks
            WHERE {where}{filters}
            ORDER BY dense_vector <=> :query_vector::vector
            LIMIT :limit
            """
        )
        return await self._execute_rows(statement, params)

    async def keyword_search(
        self,
        tenant_id: str,
        query_text: str,
        limit: int = 10,
        metadata_filter: dict[str, str] | None = None,
    ) -> list[VectorRow]:
        where = "tenant_id = :tenant_id"
        filters, params = self._metadata_filters(metadata_filter)
        params.update({"tenant_id": tenant_id, "query_text": query_text, "limit": limit})
        statement = text(
            f"""
            SELECT id, tenant_id, source_id, title, text, metadata,
                   ts_rank_cd(keywords, plainto_tsquery('english', :query_text)) AS score
            FROM vector_chunks
            WHERE {where}{filters}
            ORDER BY ts_rank_cd(keywords, plainto_tsquery('english', :query_text)) DESC
            LIMIT :limit
            """
        )
        return await self._execute_rows(statement, params)

    async def hybrid_search(
        self,
        tenant_id: str,
        query_vector: list[float],
        query_text: str,
        limit: int = 10,
        alpha: float = 0.5,
        metadata_filter: dict[str, str] | None = None,
    ) -> list[VectorRow]:
        """Reciprocal-rank-fusion hybrid retrieval over dense + lexical scores."""
        where = "tenant_id = :tenant_id"
        filters, params = self._metadata_filters(metadata_filter)
        params.update(
            {
                "tenant_id": tenant_id,
                "query_vector": query_vector,
                "query_text": query_text,
                "limit": limit * 3,
            }
        )
        dense_cte = f"""dense AS (
            SELECT id, ROW_NUMBER() OVER (ORDER BY dense_vector <=> :query_vector::vector) AS rank
            FROM vector_chunks WHERE {where}{filters} AND dense_vector IS NOT NULL
            LIMIT :limit
        )"""
        lexical_cte = f"""lexical AS (
            SELECT id, ROW_NUMBER() OVER (
                ORDER BY ts_rank_cd(keywords, plainto_tsquery('english', :query_text)) DESC
            ) AS rank
            FROM vector_chunks WHERE {where}{filters}
            LIMIT :limit
        )"""
        statement = text(
            f"""
            WITH {dense_cte}, {lexical_cte},
            fused AS (
                SELECT
                    COALESCE(d.id, l.id) AS id,
                    ((:alpha) / (COALESCE(d.rank, 2 * :limit)) +
                     ((1 - :alpha) / COALESCE(l.rank, 2 * :limit))) AS rrf
                FROM dense d FULL OUTER JOIN lexical l ON d.id = l.id
            )
            SELECT vc.id, vc.tenant_id, vc.source_id, vc.title, vc.text, vc.metadata,
                   fused.rrf AS score
            FROM fused
            JOIN vector_chunks vc ON vc.id = fused.id
            ORDER BY fused.rrf DESC
            LIMIT :limit
            """
        )
        return await self._execute_rows(statement, params)

    # ------------------------------------------------------------------
    async def _execute_rows(self, statement: text, params: dict[str, Any]) -> list[VectorRow]:
        rows = await self._session.execute(statement, params)
        results: list[VectorRow] = []
        for row in rows:
            results.append(
                VectorRow(
                    id=row.id,
                    tenant_id=str(row.tenant_id),
                    source_id=row.source_id,
                    title=row.title,
                    text=row.text,
                    metadata=dict(row.metadata or {}),
                    score=float(row.score or 0.0),
                )
            )
        return results

    @staticmethod
    def _metadata_filters(
        metadata_filter: dict[str, str] | None,
    ) -> tuple[str, dict[str, str]]:
        if not metadata_filter:
            return "", {}
        clauses = [
            f"metadata->>{key!r} = :filter_{idx}" for idx, key in enumerate(metadata_filter)
        ]
        params = {f"filter_{idx}": value for idx, value in enumerate(metadata_filter.values())}
        return " AND " + " AND ".join(clauses), params


from app.rag.indexing import PineconeVector  # noqa: E402  (type alias only)

VectorRecord = PineconeVector
