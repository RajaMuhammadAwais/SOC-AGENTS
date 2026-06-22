from collections.abc import Sequence
from dataclasses import dataclass

import httpx

from app.core.config import Settings
from app.domain.llm import (
    LLMConfigurationError,
    LLMMessage,
    LLMProviderError,
    LLMRequest,
    LLMResponse,
)


@dataclass(frozen=True)
class OpenRouterClient:
    api_key: str
    base_url: str
    default_model: str
    fallback_models: Sequence[str]
    timeout_seconds: float = 60.0
    referer: str = "http://localhost"
    app_title: str = "Enterprise AI SOC"
    transport: httpx.AsyncBaseTransport | None = None

    @classmethod
    def from_settings(cls, settings: Settings) -> "OpenRouterClient":
        if not settings.openrouter_api_key:
            raise LLMConfigurationError("OPENROUTER_API_KEY is required")
        return cls(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url.rstrip("/"),
            default_model=settings.openrouter_model,
            fallback_models=settings.openrouter_fallback_model_list,
            timeout_seconds=settings.openrouter_timeout_seconds,
            referer=settings.openrouter_referer,
            app_title=settings.app_name,
        )

    async def complete(self, request: LLMRequest) -> LLMResponse:
        models = self._candidate_models(request.model)
        failures: list[str] = []
        async with httpx.AsyncClient(
            timeout=self.timeout_seconds,
            transport=self.transport,
        ) as client:
            for model in models:
                try:
                    return await self._complete_once(client, request, model)
                except LLMProviderError as exc:
                    failures.append(f"{model}: {exc}")
        raise LLMProviderError("all OpenRouter models failed: " + "; ".join(failures))

    def _candidate_models(self, requested_model: str | None) -> list[str]:
        candidates = [requested_model or self.default_model, *self.fallback_models]
        deduped: list[str] = []
        for model in candidates:
            if model and model not in deduped:
                deduped.append(model)
        return deduped

    async def _complete_once(
        self,
        client: httpx.AsyncClient,
        request: LLMRequest,
        model: str,
    ) -> LLMResponse:
        payload: dict[str, object] = {
            "model": model,
            "messages": [self._serialize_message(message) for message in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        if request.response_format is not None:
            payload["response_format"] = dict(request.response_format)
        if request.metadata:
            payload["metadata"] = dict(request.metadata)

        try:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            )
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"request failed: {exc.__class__.__name__}") from exc

        if response.status_code >= 400:
            raise LLMProviderError(self._error_message(response))

        body = response.json()
        choices = body.get("choices") or []
        if not choices:
            raise LLMProviderError("response did not include choices")
        message = choices[0].get("message") or {}
        content = message.get("content") or ""
        if not content.strip():
            raise LLMProviderError("response content was empty")

        return LLMResponse(
            content=content,
            model=body.get("model") or model,
            provider="openrouter",
            finish_reason=choices[0].get("finish_reason"),
            usage=body.get("usage") or {},
        )

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.referer,
            "X-Title": self.app_title,
        }

    @staticmethod
    def _serialize_message(message: LLMMessage) -> dict[str, str]:
        return {"role": message.role, "content": message.content}

    @staticmethod
    def _error_message(response: httpx.Response) -> str:
        try:
            body = response.json()
        except ValueError:
            return f"status {response.status_code}"
        error = body.get("error")
        if isinstance(error, dict) and error.get("message"):
            return f"status {response.status_code}: {error['message']}"
        return f"status {response.status_code}"
