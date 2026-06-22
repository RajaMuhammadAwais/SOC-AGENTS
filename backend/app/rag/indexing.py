from dataclasses import dataclass
from uuid import UUID

from app.domain.embeddings import EmbeddingProvider, EmbeddingRequest
from app.rag.chunking import Chunk, Document, chunk_document
from app.rag.hybrid import SparseVector


@dataclass(frozen=True)
class EmbeddedChunk:
    chunk: Chunk
    dense: list[float]
    sparse: SparseVector | None


@dataclass(frozen=True)
class PineconeVector:
    id: str
    values: list[float]
    sparse_values: dict[str, list[int] | list[float]] | None
    metadata: dict[str, str]


async def embed_document_chunks(
    document: Document,
    embedding_provider: EmbeddingProvider,
    *,
    max_chars: int = 1800,
    overlap_chars: int = 200,
) -> list[EmbeddedChunk]:
    chunks = chunk_document(document, max_chars=max_chars, overlap_chars=overlap_chars)
    if not chunks:
        return []
    embeddings = await embedding_provider.embed(
        EmbeddingRequest(texts=[chunk.text for chunk in chunks], return_sparse=True)
    )
    return [
        EmbeddedChunk(chunk=chunk, dense=embedding.dense, sparse=embedding.sparse)
        for chunk, embedding in zip(chunks, embeddings, strict=True)
    ]


def to_pinecone_vectors(
    tenant_id: UUID,
    embedded_chunks: list[EmbeddedChunk],
) -> list[PineconeVector]:
    vectors: list[PineconeVector] = []
    for embedded in embedded_chunks:
        sparse_values = None
        if embedded.sparse is not None:
            sparse_values = {
                "indices": embedded.sparse.indices,
                "values": embedded.sparse.values,
            }
        vectors.append(
            PineconeVector(
                id=embedded.chunk.chunk_id,
                values=embedded.dense,
                sparse_values=sparse_values,
                metadata={
                    **embedded.chunk.metadata,
                    "tenant_id": str(tenant_id),
                    "source_id": embedded.chunk.source_id,
                    "title": embedded.chunk.title,
                    "text": embedded.chunk.text,
                },
            )
        )
    return vectors
