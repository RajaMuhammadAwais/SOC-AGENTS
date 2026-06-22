import asyncio
from collections.abc import Mapping
from typing import Any

from app.core.config import Settings
from app.domain.embeddings import (
    EmbeddingConfigurationError,
    EmbeddingProvider,
    EmbeddingRequest,
    TextEmbedding,
)
from app.rag.hybrid import SparseVector


class BGEM3EmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        *,
        model_name: str,
        batch_size: int,
        max_length: int,
        use_fp16: bool,
        model: Any | None = None,
    ) -> None:
        self.model_name = model_name
        self.batch_size = batch_size
        self.max_length = max_length
        self.use_fp16 = use_fp16
        self._model = model

    @classmethod
    def from_settings(cls, settings: Settings) -> "BGEM3EmbeddingProvider":
        return cls(
            model_name=settings.embedding_model,
            batch_size=settings.embedding_batch_size,
            max_length=settings.embedding_max_length,
            use_fp16=settings.bge_m3_use_fp16,
        )

    async def embed(self, request: EmbeddingRequest) -> list[TextEmbedding]:
        return await asyncio.to_thread(self._embed_sync, request)

    def _embed_sync(self, request: EmbeddingRequest) -> list[TextEmbedding]:
        model = self._get_model()
        output = model.encode(
            list(request.texts),
            batch_size=self.batch_size,
            max_length=self.max_length,
            return_dense=True,
            return_sparse=request.return_sparse,
            return_colbert_vecs=False,
        )
        dense_vectors = output.get("dense_vecs")
        if dense_vectors is None:
            raise EmbeddingConfigurationError("BGE-M3 output did not include dense_vecs")

        sparse_vectors = output.get("lexical_weights") if request.return_sparse else None
        embeddings: list[TextEmbedding] = []
        for index, dense_vector in enumerate(dense_vectors):
            sparse = None
            if sparse_vectors is not None:
                sparse = _to_sparse_vector(sparse_vectors[index])
            embeddings.append(
                TextEmbedding(
                    dense=[float(value) for value in dense_vector],
                    sparse=sparse,
                    metadata={"model": self.model_name},
                )
            )
        return embeddings

    def _get_model(self) -> Any:
        if self._model is None:
            try:
                from FlagEmbedding import BGEM3FlagModel
            except ImportError as exc:
                raise EmbeddingConfigurationError(
                    "FlagEmbedding is required for BGE-M3 embeddings. "
                    "Install the backend embeddings extra before enabling this provider."
                ) from exc
            self._model = BGEM3FlagModel(self.model_name, use_fp16=self.use_fp16)
        return self._model


def _to_sparse_vector(weights: Mapping[Any, Any]) -> SparseVector:
    items: list[tuple[int, float]] = []
    for raw_index, raw_value in weights.items():
        index = _coerce_sparse_index(raw_index)
        if index is None:
            continue
        value = float(raw_value)
        if value != 0:
            items.append((index, value))
    items.sort(key=lambda item: item[0])
    return SparseVector(
        indices=[index for index, _ in items],
        values=[value for _, value in items],
    )


def _coerce_sparse_index(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None
