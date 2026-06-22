from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal, Protocol

LLMRole = Literal["system", "user", "assistant", "tool"]


@dataclass(frozen=True)
class LLMMessage:
    role: LLMRole
    content: str

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise ValueError("message content must not be empty")


@dataclass(frozen=True)
class LLMRequest:
    messages: Sequence[LLMMessage]
    model: str | None = None
    temperature: float = 0.2
    max_tokens: int = 1024
    response_format: Mapping[str, object] | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.messages:
            raise ValueError("messages must not be empty")
        if not 0 <= self.temperature <= 2:
            raise ValueError("temperature must be between 0 and 2")
        if self.max_tokens <= 0:
            raise ValueError("max_tokens must be greater than zero")


@dataclass(frozen=True)
class LLMResponse:
    content: str
    model: str
    provider: str
    finish_reason: str | None = None
    usage: Mapping[str, object] = field(default_factory=dict)


class LLMError(RuntimeError):
    pass


class LLMConfigurationError(LLMError):
    pass


class LLMProviderError(LLMError):
    pass


class LLMClient(Protocol):
    async def complete(self, request: LLMRequest) -> LLMResponse:
        raise NotImplementedError
