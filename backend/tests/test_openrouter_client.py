import json

import httpx
import pytest

from app.domain.llm import LLMMessage, LLMProviderError, LLMRequest
from app.infrastructure.llm.openrouter import OpenRouterClient


@pytest.mark.asyncio
async def test_openrouter_client_posts_chat_completion_payload() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://openrouter.ai/api/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer test-key"
        payload = json.loads(request.content)
        assert payload["model"] == "nvidia/nemotron-3-super-120b-a12b:free"
        assert payload["messages"] == [{"role": "user", "content": "Triage this alert"}]
        return httpx.Response(
            200,
            json={
                "model": payload["model"],
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": "triage complete"},
                    }
                ],
                "usage": {"total_tokens": 12},
            },
        )

    client = OpenRouterClient(
        api_key="test-key",
        base_url="https://openrouter.ai/api/v1",
        default_model="nvidia/nemotron-3-super-120b-a12b:free",
        fallback_models=[],
        transport=httpx.MockTransport(handler),
    )

    response = await client.complete(
        LLMRequest(messages=[LLMMessage(role="user", content="Triage this alert")])
    )

    assert response.content == "triage complete"
    assert response.provider == "openrouter"
    assert response.usage["total_tokens"] == 12


@pytest.mark.asyncio
async def test_openrouter_client_uses_fallback_after_provider_error() -> None:
    seen_models: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        seen_models.append(payload["model"])
        if len(seen_models) == 1:
            return httpx.Response(503, json={"error": {"message": "provider unavailable"}})
        return httpx.Response(
            200,
            json={
                "model": payload["model"],
                "choices": [{"message": {"content": "fallback result"}}],
            },
        )

    client = OpenRouterClient(
        api_key="test-key",
        base_url="https://openrouter.ai/api/v1",
        default_model="primary-model",
        fallback_models=["fallback-model"],
        transport=httpx.MockTransport(handler),
    )

    response = await client.complete(
        LLMRequest(messages=[LLMMessage(role="user", content="Investigate")])
    )

    assert seen_models == ["primary-model", "fallback-model"]
    assert response.model == "fallback-model"


@pytest.mark.asyncio
async def test_openrouter_client_rejects_empty_provider_content() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": ""}}]})

    client = OpenRouterClient(
        api_key="test-key",
        base_url="https://openrouter.ai/api/v1",
        default_model="primary-model",
        fallback_models=[],
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(LLMProviderError, match="response content was empty"):
        await client.complete(LLMRequest(messages=[LLMMessage(role="user", content="Investigate")]))
