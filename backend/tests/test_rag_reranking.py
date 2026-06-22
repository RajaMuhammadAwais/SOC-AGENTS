import pytest

from app.domain.rag import RetrievedEvidence
from app.domain.reranking import RerankRequest, RerankResult
from app.rag.reranking import rerank_retrieved_evidence


class StubReranker:
    def __init__(self) -> None:
        self.requests: list[RerankRequest] = []

    async def rerank(self, request: RerankRequest) -> list[RerankResult]:
        self.requests.append(request)
        return [
            RerankResult(
                candidate=request.candidates[1],
                score=0.9,
                rank=1,
                metadata={"model": "m"},
            ),
            RerankResult(
                candidate=request.candidates[0],
                score=0.4,
                rank=2,
                metadata={"model": "m"},
            ),
        ]


@pytest.mark.asyncio
async def test_rerank_retrieved_evidence_preserves_evidence_and_updates_scores() -> None:
    evidence = [
        RetrievedEvidence(
            chunk_id="a",
            score=0.2,
            title="A",
            text="benign activity",
            citation={"source": "playbook"},
        ),
        RetrievedEvidence(
            chunk_id="b",
            score=0.3,
            title="B",
            text="encoded powershell",
            citation={"source": "mitre"},
        ),
    ]
    reranker = StubReranker()

    reranked = await rerank_retrieved_evidence(
        query="powershell",
        evidence=evidence,
        reranker=reranker,
        top_k=2,
    )

    assert [item.chunk_id for item in reranked] == ["b", "a"]
    assert [item.score for item in reranked] == [0.9, 0.4]
    assert reranked[0].citation["source"] == "mitre"
    assert reranked[0].citation["reranker_model"] == "m"
    assert reranked[0].citation["rerank_rank"] == "1"
    assert reranker.requests[0].top_k == 2


@pytest.mark.asyncio
async def test_rerank_retrieved_evidence_returns_empty_for_no_evidence() -> None:
    reranked = await rerank_retrieved_evidence(
        query="powershell",
        evidence=[],
        reranker=StubReranker(),
    )

    assert reranked == []
