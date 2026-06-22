from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID


class RetrievalMode(str, Enum):
    semantic = "semantic"
    lexical = "lexical"
    hybrid = "hybrid"


@dataclass(frozen=True)
class KnowledgeChunk:
    chunk_id: str
    source_id: str
    title: str
    text: str
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievalQuery:
    tenant_id: UUID
    query: str
    mode: RetrievalMode = RetrievalMode.hybrid
    alpha: float = 0.5
    top_k: int = 10

    def __post_init__(self) -> None:
        if not 0 <= self.alpha <= 1:
            raise ValueError("alpha must be between 0 and 1")
        if self.top_k <= 0 or self.top_k > 100:
            raise ValueError("top_k must be between 1 and 100")


@dataclass(frozen=True)
class RetrievedEvidence:
    chunk_id: str
    score: float
    title: str
    text: str
    citation: dict[str, str]


class RetrievalService:
    async def search(self, query: RetrievalQuery) -> list[RetrievedEvidence]:
        raise NotImplementedError
