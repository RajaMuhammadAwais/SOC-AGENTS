from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol

from app.rag.hybrid import SparseVector


@dataclass(frozen=True)
class EmbeddingRequest:
    texts: Sequence[str]
    return_sparse: bool = True

    def __post_init__(self) -> None:
        if not self.texts:
            raise ValueError("texts must not be empty")
        if any(not text.strip() for text in self.texts):
            raise ValueError("texts must not contain empty values")


@dataclass(frozen=True)
class TextEmbedding:
    dense: list[float]
    sparse: SparseVector | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.dense:
            raise ValueError("dense vector must not be empty")


class EmbeddingError(RuntimeError):
    pass


class EmbeddingConfigurationError(EmbeddingError):
    pass


class EmbeddingProvider(Protocol):
    async def embed(self, request: EmbeddingRequest) -> list[TextEmbedding]:
        raise NotImplementedError
