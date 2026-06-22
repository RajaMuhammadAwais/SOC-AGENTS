import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from uuid import UUID

from app.domain.embeddings import EmbeddingProvider
from app.rag.chunking import Document
from app.rag.indexing import PineconeVector, embed_document_chunks, to_pinecone_vectors

DEFAULT_CORPUS_PATH = Path(__file__).with_name("corpus") / "initial_knowledge_base.jsonl"


@dataclass(frozen=True)
class KnowledgeBaseLoadResult:
    documents: int
    chunks: int
    vectors: int


class VectorSink(Protocol):
    async def upsert(self, vectors: list[PineconeVector], *, namespace: str) -> None:
        raise NotImplementedError


def load_corpus_documents(path: Path = DEFAULT_CORPUS_PATH) -> list[Document]:
    documents: list[Document] = []
    with path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, 1):
            if not line.strip():
                continue
            payload = json.loads(line)
            documents.append(_document_from_payload(payload, line_number))
    return documents


async def load_initial_knowledge_base(
    *,
    tenant_id: UUID,
    embedding_provider: EmbeddingProvider,
    vector_sink: VectorSink,
    corpus_path: Path = DEFAULT_CORPUS_PATH,
    namespace: str | None = None,
) -> KnowledgeBaseLoadResult:
    documents = load_corpus_documents(corpus_path)
    vectors: list[PineconeVector] = []
    chunk_count = 0
    for document in documents:
        embedded_chunks = await embed_document_chunks(document, embedding_provider)
        chunk_count += len(embedded_chunks)
        vectors.extend(to_pinecone_vectors(tenant_id, embedded_chunks))
    if vectors:
        await vector_sink.upsert(vectors, namespace=namespace or str(tenant_id))
    return KnowledgeBaseLoadResult(
        documents=len(documents),
        chunks=chunk_count,
        vectors=len(vectors),
    )


def _document_from_payload(payload: dict[str, object], line_number: int) -> Document:
    source_id = _required_str(payload, "source_id", line_number)
    title = _required_str(payload, "title", line_number)
    text = _required_str(payload, "text", line_number)
    metadata = payload.get("metadata", {})
    if not isinstance(metadata, dict):
        raise ValueError(f"metadata must be an object on corpus line {line_number}")
    return Document(
        source_id=source_id,
        title=title,
        text=text,
        metadata={str(key): str(value) for key, value in metadata.items()},
    )


def _required_str(payload: dict[str, object], key: str, line_number: int) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} is required on corpus line {line_number}")
    return value.strip()
