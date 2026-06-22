from uuid import uuid4

import pytest

from app.domain.embeddings import EmbeddingRequest, TextEmbedding
from app.rag.chunking import Document
from app.rag.hybrid import SparseVector
from app.rag.indexing import embed_document_chunks, to_pinecone_vectors


class StubEmbeddingProvider:
    def __init__(self) -> None:
        self.requests: list[EmbeddingRequest] = []

    async def embed(self, request: EmbeddingRequest) -> list[TextEmbedding]:
        self.requests.append(request)
        return [
            TextEmbedding(
                dense=[float(index), 1.0],
                sparse=SparseVector(indices=[index], values=[0.5]),
            )
            for index, _ in enumerate(request.texts)
        ]


@pytest.mark.asyncio
async def test_embed_document_chunks_uses_chunk_texts_and_sparse_embeddings() -> None:
    provider = StubEmbeddingProvider()
    document = Document(
        source_id="nist-800-53",
        title="NIST 800-53",
        text="a" * 90,
        metadata={"source": "nist"},
    )

    embedded = await embed_document_chunks(
        document,
        provider,
        max_chars=50,
        overlap_chars=10,
    )

    assert len(embedded) == 2
    assert provider.requests[0].return_sparse is True
    assert provider.requests[0].texts[0] == embedded[0].chunk.text
    assert embedded[1].dense == [1.0, 1.0]
    assert embedded[1].sparse is not None
    assert embedded[1].sparse.indices == [1]


@pytest.mark.asyncio
async def test_to_pinecone_vectors_preserves_citation_metadata() -> None:
    provider = StubEmbeddingProvider()
    document = Document(
        source_id="playbook-1",
        title="Incident Playbook",
        text="isolate endpoint then preserve evidence",
        metadata={"source": "playbook"},
    )

    embedded = await embed_document_chunks(document, provider)
    vectors = to_pinecone_vectors(uuid4(), embedded)

    assert vectors[0].id
    assert vectors[0].values == [0.0, 1.0]
    assert vectors[0].sparse_values == {"indices": [0], "values": [0.5]}
    assert vectors[0].metadata["source_id"] == "playbook-1"
    assert vectors[0].metadata["title"] == "Incident Playbook"
    assert vectors[0].metadata["text"] == "isolate endpoint then preserve evidence"
