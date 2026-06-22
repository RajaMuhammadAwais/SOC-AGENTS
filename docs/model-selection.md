# OpenRouter Free Model Selection

Date: 2026-06-11

## Selected model

`nvidia/nemotron-3-super-120b-a12b:free`

## Why this model

- It is an NVIDIA Nemotron model, matching the project requirement for Nemotron as the primary LLM family.
- OpenRouter's live model catalog reports zero prompt and completion pricing for the `:free` variant.
- The model has a 1,000,000 token context window in the catalog.
- The model supports agent-relevant parameters including reasoning, structured outputs, tool choice, and tools.
- A local OpenRouter API smoke test using `backend/.env` returned a completion result from this model.

## Tested candidates

- `nvidia/nemotron-3-ultra-550b-a55b:free`: official free model with strong specs, but the local API request timed out after 120 seconds.
- `nvidia/nemotron-3-super-120b-a12b:free`: official free model, returned a result quickly.
- `stepfun/step-3.7-flash`: official free model, returned an empty message in the local smoke test.
- `nex-agi/nex-n2-pro`: official free model, OpenRouter returned "No endpoints found".
- `nvidia/nemotron-3-nano-30b-a3b:free`: official free model, returned an empty message in the local smoke test.

## Sources

- OpenRouter live models API: https://openrouter.ai/api/v1/models
- OpenRouter chat completions API docs: https://openrouter.ai/docs/api-reference/chat-completion
- OpenRouter Nemotron 3 Ultra model page: https://openrouter.ai/nvidia/nemotron-3-ultra-550b-a55b:free/api
- Pydantic Settings dotenv docs: https://docs.pydantic.dev/latest/concepts/pydantic_settings/#dotenv-env-support
