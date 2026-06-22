from uuid import uuid4

import pytest

from app.domain.llm import LLMRequest, LLMResponse
from app.domain.rag import RetrievalQuery, RetrievedEvidence
from app.domain.reranking import RerankRequest, RerankResult
from app.rag.pipeline import build_grounded_messages, generate_rag_answer


class StubRetrievalService:
    def __init__(self, evidence: list[RetrievedEvidence]) -> None:
        self.evidence = evidence
        self.queries: list[RetrievalQuery] = []

    async def search(self, query: RetrievalQuery) -> list[RetrievedEvidence]:
        self.queries.append(query)
        return self.evidence


class StubLLMClient:
    def __init__(self) -> None:
        self.requests: list[LLMRequest] = []

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        return LLMResponse(
            content="The alert maps to credential access based on failed logins [1].",
            model="test-model",
            provider="test",
            usage={"total_tokens": 42},
        )


class StubReranker:
    def __init__(self) -> None:
        self.requests: list[RerankRequest] = []

    async def rerank(self, request: RerankRequest) -> list[RerankResult]:
        self.requests.append(request)
        return [
            RerankResult(candidate=request.candidates[1], score=0.91, rank=1),
            RerankResult(candidate=request.candidates[0], score=0.41, rank=2),
        ]


def _evidence() -> list[RetrievedEvidence]:
    return [
        RetrievedEvidence(
            chunk_id="chunk-a",
            score=0.2,
            title="Windows Login Playbook",
            text="Successful login after repeated failures can indicate credential access.",
            citation={"source_id": "playbook-1", "section": "login"},
        ),
        RetrievedEvidence(
            chunk_id="chunk-b",
            score=0.3,
            title="MITRE Credential Access",
            text="Credential access includes attempts to steal account names and passwords.",
            citation={"source_id": "mitre-ta0006"},
        ),
    ]


@pytest.mark.asyncio
async def test_generate_rag_answer_uses_retrieval_reranking_and_citations() -> None:
    query = RetrievalQuery(tenant_id=uuid4(), query="Explain failed logins", top_k=2)
    retrieval = StubRetrievalService(_evidence())
    llm = StubLLMClient()
    reranker = StubReranker()

    answer = await generate_rag_answer(
        query=query,
        retrieval_service=retrieval,
        llm_client=llm,
        reranker=reranker,
    )

    assert answer.answer.endswith("[1].")
    assert [citation.chunk_id for citation in answer.citations] == ["chunk-b", "chunk-a"]
    assert answer.citations[0].metadata["rerank_rank"] == "1"
    assert answer.explanation["reranked"] == "true"
    assert answer.model == "test-model"
    assert answer.usage == {"total_tokens": 42}
    assert retrieval.queries == [query]
    assert reranker.requests[0].top_k == 2
    assert "Evidence:" in llm.requests[0].messages[1].content


@pytest.mark.asyncio
async def test_generate_rag_answer_returns_grounded_empty_response_without_llm_call() -> None:
    query = RetrievalQuery(tenant_id=uuid4(), query="Unknown CVE")
    retrieval = StubRetrievalService([])
    llm = StubLLMClient()

    answer = await generate_rag_answer(
        query=query,
        retrieval_service=retrieval,
        llm_client=llm,
    )

    assert answer.answer == "No supporting evidence was found for this question."
    assert answer.citations == []
    assert answer.explanation["evidence_count"] == "0"
    assert llm.requests == []


def test_build_grounded_messages_formats_evidence_with_citation_numbers() -> None:
    messages = build_grounded_messages("What happened?", _evidence())

    assert messages[0].role == "system"
    assert "Use only the provided evidence" in messages[0].content
    assert "[1] title=Windows Login Playbook" in messages[1].content
    assert "source=playbook-1" in messages[1].content
    assert "[2] title=MITRE Credential Access" in messages[1].content
