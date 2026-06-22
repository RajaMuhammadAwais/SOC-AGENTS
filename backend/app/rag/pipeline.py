from dataclasses import dataclass, field

from app.domain.llm import LLMClient, LLMMessage, LLMRequest
from app.domain.rag import RetrievalQuery, RetrievalService, RetrievedEvidence
from app.domain.reranking import RerankerProvider
from app.rag.reranking import rerank_retrieved_evidence


@dataclass(frozen=True)
class RAGCitation:
    index: int
    chunk_id: str
    title: str
    score: float
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class RAGAnswer:
    answer: str
    citations: list[RAGCitation]
    evidence: list[RetrievedEvidence]
    explanation: dict[str, str]
    model: str | None = None
    usage: dict[str, object] = field(default_factory=dict)


async def generate_rag_answer(
    *,
    query: RetrievalQuery,
    retrieval_service: RetrievalService,
    llm_client: LLMClient,
    reranker: RerankerProvider | None = None,
) -> RAGAnswer:
    evidence = await retrieval_service.search(query)
    was_reranked = False
    if reranker is not None and evidence:
        evidence = await rerank_retrieved_evidence(
            query=query.query,
            evidence=evidence,
            reranker=reranker,
            top_k=query.top_k,
        )
        was_reranked = True

    citations = _build_citations(evidence)
    if not evidence:
        return RAGAnswer(
            answer="No supporting evidence was found for this question.",
            citations=[],
            evidence=[],
            explanation=_build_explanation(query, evidence_count=0, was_reranked=was_reranked),
        )

    response = await llm_client.complete(
        LLMRequest(
            messages=build_grounded_messages(query.query, evidence),
            temperature=0,
            max_tokens=1200,
            metadata={
                "tenant_id": str(query.tenant_id),
                "rag_mode": query.mode.value,
                "evidence_count": str(len(evidence)),
            },
        )
    )
    return RAGAnswer(
        answer=response.content,
        citations=citations,
        evidence=evidence,
        explanation=_build_explanation(
            query,
            evidence_count=len(evidence),
            was_reranked=was_reranked,
        ),
        model=response.model,
        usage=dict(response.usage),
    )


def build_grounded_messages(question: str, evidence: list[RetrievedEvidence]) -> list[LLMMessage]:
    context = "\n\n".join(_format_evidence(index, item) for index, item in enumerate(evidence, 1))
    return [
        LLMMessage(
            role="system",
            content=(
                "You are an enterprise SOC RAG assistant. Use only the provided evidence. "
                "If the evidence is insufficient, say what is missing. Cite every factual "
                "claim with bracketed citation numbers like [1]. Do not reveal hidden reasoning."
            ),
        ),
        LLMMessage(
            role="user",
            content=f"Question:\n{question}\n\nEvidence:\n{context}",
        ),
    ]


def _format_evidence(index: int, evidence: RetrievedEvidence) -> str:
    source = evidence.citation.get("source_id") or evidence.citation.get("source") or "unknown"
    return (
        f"[{index}] title={evidence.title}; chunk_id={evidence.chunk_id}; "
        f"source={source}; score={evidence.score:.4f}\n{evidence.text}"
    )


def _build_citations(evidence: list[RetrievedEvidence]) -> list[RAGCitation]:
    return [
        RAGCitation(
            index=index,
            chunk_id=item.chunk_id,
            title=item.title,
            score=item.score,
            metadata=item.citation,
        )
        for index, item in enumerate(evidence, 1)
    ]


def _build_explanation(
    query: RetrievalQuery,
    *,
    evidence_count: int,
    was_reranked: bool,
) -> dict[str, str]:
    return {
        "retrieval_mode": query.mode.value,
        "alpha": str(query.alpha),
        "top_k": str(query.top_k),
        "evidence_count": str(evidence_count),
        "reranked": str(was_reranked).lower(),
    }
