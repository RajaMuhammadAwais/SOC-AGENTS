from app.domain.rag import RetrievedEvidence
from app.domain.reranking import RerankCandidate, RerankerProvider, RerankRequest


async def rerank_retrieved_evidence(
    *,
    query: str,
    evidence: list[RetrievedEvidence],
    reranker: RerankerProvider,
    top_k: int | None = None,
) -> list[RetrievedEvidence]:
    if not evidence:
        return []
    results = await reranker.rerank(
        RerankRequest(
            query=query,
            candidates=[
                RerankCandidate(
                    id=item.chunk_id,
                    text=item.text,
                    metadata=item.citation,
                )
                for item in evidence
            ],
            top_k=top_k,
            normalize=True,
        )
    )
    evidence_by_id = {item.chunk_id: item for item in evidence}
    reranked: list[RetrievedEvidence] = []
    for result in results:
        item = evidence_by_id[result.candidate.id]
        reranked.append(
            RetrievedEvidence(
                chunk_id=item.chunk_id,
                score=result.score,
                title=item.title,
                text=item.text,
                citation={
                    **item.citation,
                    "reranker_model": result.metadata.get("model", ""),
                    "rerank_rank": str(result.rank),
                },
            )
        )
    return reranked
