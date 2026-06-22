import asyncio
import os
from typing import Any

from app.core.config import Settings
from app.domain.reranking import (
    RerankerConfigurationError,
    RerankerProvider,
    RerankRequest,
    RerankResult,
)


class BGERerankerProvider(RerankerProvider):
    def __init__(
        self,
        *,
        model_name: str,
        batch_size: int,
        max_length: int,
        use_fp16: bool,
        hf_token: str | None = None,
        model: Any | None = None,
    ) -> None:
        self.model_name = model_name
        self.batch_size = batch_size
        self.max_length = max_length
        self.use_fp16 = use_fp16
        self.hf_token = hf_token
        self._model = model

    @classmethod
    def from_settings(cls, settings: Settings) -> "BGERerankerProvider":
        return cls(
            model_name=settings.reranker_model,
            batch_size=settings.reranker_batch_size,
            max_length=settings.reranker_max_length,
            use_fp16=settings.bge_reranker_use_fp16,
            hf_token=settings.huggingface_token,
        )

    async def rerank(self, request: RerankRequest) -> list[RerankResult]:
        return await asyncio.to_thread(self._rerank_sync, request)

    def _rerank_sync(self, request: RerankRequest) -> list[RerankResult]:
        model = self._get_model()
        pairs = [[request.query, candidate.text] for candidate in request.candidates]
        raw_scores = model.compute_score(
            pairs,
            batch_size=self.batch_size,
            max_length=self.max_length,
            normalize=request.normalize,
        )
        scores = _normalize_scores(raw_scores)
        ranked = sorted(
            zip(request.candidates, scores, strict=True),
            key=lambda item: item[1],
            reverse=True,
        )
        if request.top_k is not None:
            ranked = ranked[: request.top_k]
        return [
            RerankResult(
                candidate=candidate,
                score=float(score),
                rank=index + 1,
                metadata={"model": self.model_name},
            )
            for index, (candidate, score) in enumerate(ranked)
        ]

    def _get_model(self) -> Any:
        if self.hf_token:
            os.environ["HF_TOKEN"] = self.hf_token
        if self._model is None:
            try:
                from FlagEmbedding import FlagReranker
            except ImportError as exc:
                raise RerankerConfigurationError(
                    "FlagEmbedding is required for BGE reranking. "
                    "Install the backend embeddings extra before enabling this provider."
                ) from exc
            self._model = FlagReranker(self.model_name, use_fp16=self.use_fp16)
        return self._model


def _normalize_scores(scores: Any) -> list[float]:
    if isinstance(scores, int | float):
        return [float(scores)]
    return [float(score) for score in scores]
