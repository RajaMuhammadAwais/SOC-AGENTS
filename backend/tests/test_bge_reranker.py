import os

import pytest

from app.domain.reranking import RerankCandidate, RerankRequest
from app.infrastructure.reranking.bge import BGERerankerProvider


class FakeRerankerModel:
    def __init__(self, scores: list[float]) -> None:
        self.scores = scores
        self.calls: list[dict[str, object]] = []

    def compute_score(self, pairs: list[list[str]], **kwargs: object) -> list[float]:
        self.calls.append({"pairs": pairs, **kwargs})
        return self.scores


@pytest.mark.asyncio
async def test_bge_reranker_orders_candidates_by_score() -> None:
    model = FakeRerankerModel(scores=[0.2, 0.95, 0.5])
    provider = BGERerankerProvider(
        model_name="BAAI/bge-reranker-v2-m3",
        batch_size=12,
        max_length=8192,
        use_fp16=True,
        model=model,
    )

    results = await provider.rerank(
        RerankRequest(
            query="powershell encoded command",
            candidates=[
                RerankCandidate(id="a", text="benign login"),
                RerankCandidate(id="b", text="encoded powershell execution"),
                RerankCandidate(id="c", text="suspicious process launch"),
            ],
            top_k=2,
        )
    )

    assert [result.candidate.id for result in results] == ["b", "c"]
    assert [result.rank for result in results] == [1, 2]
    assert results[0].metadata == {"model": "BAAI/bge-reranker-v2-m3"}
    assert model.calls[0]["normalize"] is True
    assert model.calls[0]["max_length"] == 8192


def test_rerank_request_rejects_empty_query() -> None:
    with pytest.raises(ValueError, match="query must not be empty"):
        RerankRequest(query=" ", candidates=[RerankCandidate(id="a", text="text")])


def test_bge_reranker_sets_hf_token_before_lazy_model_load(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HF_TOKEN", raising=False)
    provider = BGERerankerProvider(
        model_name="BAAI/bge-reranker-v2-m3",
        batch_size=12,
        max_length=8192,
        use_fp16=True,
        hf_token="test-token",
        model=FakeRerankerModel(scores=[0.7]),
    )

    provider._get_model()

    assert os.environ["HF_TOKEN"] == "test-token"
