# RAG Pipeline

Date: 2026-06-11

## Pipeline

1. Retrieve tenant-scoped evidence with `RetrievalService`.
2. Optionally rerank evidence with `BGERerankerProvider`.
3. Build a grounded prompt from retrieved evidence.
4. Generate the answer through the configured LLM client.
5. Return answer text, citations, evidence, model metadata, usage, and explainability fields.

## Grounding Rules

- The LLM prompt instructs the model to use only supplied evidence.
- If evidence is insufficient, the model must say what is missing.
- Evidence is numbered and source metadata is preserved.
- The response object includes citations independent of whether the model emits citation markers.
- Explainability records retrieval mode, alpha, top-k, evidence count, and whether reranking was applied.

## Sources

- Pinecone RAG/search workflow docs: https://docs.pinecone.io/guides/get-started/overview
- OpenRouter chat completions API docs: https://openrouter.ai/docs/api-reference/chat-completion
