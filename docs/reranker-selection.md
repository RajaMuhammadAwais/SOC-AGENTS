# BGE Reranker Integration

Date: 2026-06-11

## Selected reranker

`BAAI/bge-reranker-v2-m3`

## Why this model

- It is the reranker required by the project design.
- The official model card positions it as the lightweight multilingual BGE reranker.
- It supports the FlagEmbedding `FlagReranker` API used by the backend adapter.
- The adapter uses `compute_score(..., normalize=True)` so relevance scores are normalized for downstream ranking.
- It pairs with BGE-M3 embeddings for hybrid retrieval followed by reranking.

## Implementation

- Runtime provider: `bge-reranker-v2-m3`
- Model: `BAAI/bge-reranker-v2-m3`
- Optional backend extra: `embeddings`
- Adapter: `BGERerankerProvider`
- RAG helper: `rerank_retrieved_evidence`
- Token handling: reads `HF_TOKEN` from `backend/.env` and sets it before lazy model loading.

## Sources

- Hugging Face model card: https://huggingface.co/BAAI/bge-reranker-v2-m3
- Official FlagEmbedding repository: https://github.com/FlagOpen/FlagEmbedding
