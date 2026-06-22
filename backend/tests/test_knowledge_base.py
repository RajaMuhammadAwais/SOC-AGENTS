from pathlib import Path
from uuid import uuid4

import pytest

from app.domain.embeddings import EmbeddingRequest, TextEmbedding
from app.rag.hybrid import SparseVector
from app.rag.indexing import PineconeVector
from app.rag.knowledge_base import load_corpus_documents, load_initial_knowledge_base


class StubEmbeddingProvider:
    async def embed(self, request: EmbeddingRequest) -> list[TextEmbedding]:
        return [
            TextEmbedding(
                dense=[1.0, 0.0],
                sparse=SparseVector(indices=[index], values=[1.0]),
            )
            for index, _ in enumerate(request.texts)
        ]


class StubVectorSink:
    def __init__(self) -> None:
        self.calls: list[tuple[list[PineconeVector], str]] = []

    async def upsert(self, vectors: list[PineconeVector], *, namespace: str) -> None:
        self.calls.append((vectors, namespace))


def test_load_corpus_documents_reads_seed_corpus() -> None:
    documents = load_corpus_documents()

    assert {document.metadata["kind"] for document in documents} == {
        "cve",
        "mitre_attack",
        "nist",
        "playbook",
    }
    assert all(document.metadata["source_url"] for document in documents)


def test_load_corpus_documents_rejects_missing_required_field(tmp_path: Path) -> None:
    corpus_path = tmp_path / "bad.jsonl"
    corpus_path.write_text('{"source_id":"x","title":"Missing text"}\n', encoding="utf-8")

    with pytest.raises(ValueError, match="text is required"):
        load_corpus_documents(corpus_path)


@pytest.mark.asyncio
async def test_load_initial_knowledge_base_embeds_and_upserts_vectors() -> None:
    tenant_id = uuid4()
    sink = StubVectorSink()

    result = await load_initial_knowledge_base(
        tenant_id=tenant_id,
        embedding_provider=StubEmbeddingProvider(),
        vector_sink=sink,
    )

    assert result.documents == 4
    assert result.chunks == 4
    assert result.vectors == 4
    assert sink.calls[0][1] == str(tenant_id)
    first_vector = sink.calls[0][0][0]
    assert first_vector.metadata["tenant_id"] == str(tenant_id)
    assert first_vector.metadata["kind"] == "cve"
    assert first_vector.metadata["source_url"] == "https://nvd.nist.gov/developers/vulnerabilities"
    assert first_vector.sparse_values == {"indices": [0], "values": [1.0]}
