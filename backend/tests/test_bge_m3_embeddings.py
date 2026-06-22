import pytest

from app.domain.embeddings import EmbeddingRequest
from app.infrastructure.embeddings.bge_m3 import BGEM3EmbeddingProvider


class FakeBGEM3Model:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def encode(self, texts: list[str], **kwargs: object) -> dict[str, object]:
        self.calls.append({"texts": texts, **kwargs})
        return {
            "dense_vecs": [[1, 2, 3], [4, 5, 6]],
            "lexical_weights": [
                {"5": 0.25, 2: 0.75, "token": 1.0},
                {"9": 0.5},
            ],
        }


@pytest.mark.asyncio
async def test_bge_m3_embedding_provider_returns_dense_and_sparse_vectors() -> None:
    model = FakeBGEM3Model()
    provider = BGEM3EmbeddingProvider(
        model_name="BAAI/bge-m3",
        batch_size=12,
        max_length=8192,
        use_fp16=True,
        model=model,
    )

    embeddings = await provider.embed(EmbeddingRequest(texts=["alpha", "beta"]))

    assert embeddings[0].dense == [1.0, 2.0, 3.0]
    assert embeddings[0].sparse is not None
    assert embeddings[0].sparse.indices == [2, 5]
    assert embeddings[0].sparse.values == [0.75, 0.25]
    assert embeddings[0].metadata == {"model": "BAAI/bge-m3"}
    assert model.calls[0]["return_dense"] is True
    assert model.calls[0]["return_sparse"] is True
    assert model.calls[0]["return_colbert_vecs"] is False


def test_embedding_request_rejects_empty_texts() -> None:
    with pytest.raises(ValueError, match="texts must not contain empty values"):
        EmbeddingRequest(texts=["valid", " "])
