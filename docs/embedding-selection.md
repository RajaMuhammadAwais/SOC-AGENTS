# BGE-M3 Embedding Integration

Date: 2026-06-11

## Selected embedding model

`BAAI/bge-m3`

## Why this model

- It is the embedding model required by the project design.
- The official model card lists a 1024-dimensional embedding size, matching `EMBEDDING_DIMENSION=1024`.
- BGE-M3 supports dense retrieval, sparse lexical retrieval, and multi-vector retrieval from one model family.
- It supports long inputs up to 8192 tokens, which fits SOC knowledge-base documents such as CVEs, MITRE, NIST, policies, and playbooks.
- The official BGE-M3 recommendation for RAG is hybrid retrieval followed by reranking, which matches this platform's RAG plan.

## Implementation

- Runtime provider: `bge-m3`
- Model: `BAAI/bge-m3`
- Optional backend extra: `embeddings`
- Adapter: `BGEM3EmbeddingProvider`
- Output: dense vector plus optional sparse lexical vector

The adapter lazily imports `FlagEmbedding` so normal backend startup and tests do not download model weights. Production deployments that perform embedding generation should install the backend with the `embeddings` extra.

## Sources

- Hugging Face model card: https://huggingface.co/BAAI/bge-m3
- Official FlagEmbedding repository: https://github.com/FlagOpen/FlagEmbedding
- BGE-M3 paper: https://arxiv.org/abs/2402.03216
