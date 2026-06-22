from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class RerankCandidate:
    id: str
    text: str
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("candidate id must not be empty")
        if not self.text.strip():
            raise ValueError("candidate text must not be empty")


@dataclass(frozen=True)
class RerankRequest:
    query: str
    candidates: Sequence[RerankCandidate]
    top_k: int | None = None
    normalize: bool = True

    def __post_init__(self) -> None:
        if not self.query.strip():
            raise ValueError("query must not be empty")
        if not self.candidates:
            raise ValueError("candidates must not be empty")
        if self.top_k is not None and self.top_k <= 0:
            raise ValueError("top_k must be greater than zero")


@dataclass(frozen=True)
class RerankResult:
    candidate: RerankCandidate
    score: float
    rank: int
    metadata: dict[str, str] = field(default_factory=dict)


class RerankerError(RuntimeError):
    pass


class RerankerConfigurationError(RerankerError):
    pass


class RerankerProvider(Protocol):
    async def rerank(self, request: RerankRequest) -> list[RerankResult]:
        raise NotImplementedError
