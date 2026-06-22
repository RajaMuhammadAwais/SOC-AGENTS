from functools import lru_cache

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = Field(default="local", alias="APP_ENV")
    app_name: str = Field(default="Enterprise AI SOC", alias="APP_NAME")
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")

    database_url: str = Field(
        default="postgresql+asyncpg://soc:soc@localhost:5432/soc",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    jwt_issuer: str = Field(default="enterprise-ai-soc", alias="JWT_ISSUER")
    jwt_audience: str = Field(default="enterprise-ai-soc-api", alias="JWT_AUDIENCE")
    jwt_secret_key: str = Field(default="change-me-local-only", alias="JWT_SECRET_KEY")
    access_token_ttl_seconds: int = Field(default=900, alias="ACCESS_TOKEN_TTL_SECONDS")
    refresh_token_ttl_seconds: int = Field(default=2_592_000, alias="REFRESH_TOKEN_TTL_SECONDS")

    pinecone_api_key: str | None = Field(default=None, alias="PINECONE_API_KEY")
    pinecone_index: str = Field(default="soc-knowledge", alias="PINECONE_INDEX")
    pinecone_cloud: str = Field(default="aws", alias="PINECONE_CLOUD")
    pinecone_region: str = Field(default="us-east-1", alias="PINECONE_REGION")
    embedding_dimension: int = Field(default=1024, alias="EMBEDDING_DIMENSION")
    embedding_provider: str = Field(default="bge-m3", alias="EMBEDDING_PROVIDER")
    embedding_model: str = Field(default="BAAI/bge-m3", alias="EMBEDDING_MODEL")
    embedding_batch_size: int = Field(default=12, gt=0, alias="EMBEDDING_BATCH_SIZE")
    embedding_max_length: int = Field(default=8192, gt=0, alias="EMBEDDING_MAX_LENGTH")
    bge_m3_use_fp16: bool = Field(default=True, alias="BGE_M3_USE_FP16")
    huggingface_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "HF_TOKEN",
            "HUGGINGFACE_HUB_TOKEN",
            "HUGGING_FACE_HUB_TOKEN",
        ),
    )
    reranker_provider: str = Field(default="bge-reranker-v2-m3", alias="RERANKER_PROVIDER")
    reranker_model: str = Field(default="BAAI/bge-reranker-v2-m3", alias="RERANKER_MODEL")
    reranker_batch_size: int = Field(default=12, gt=0, alias="RERANKER_BATCH_SIZE")
    reranker_max_length: int = Field(default=8192, gt=0, alias="RERANKER_MAX_LENGTH")
    bge_reranker_use_fp16: bool = Field(default=True, alias="BGE_RERANKER_USE_FP16")
    openrouter_api_key: str | None = Field(default=None, alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        alias="OPENROUTER_BASE_URL",
    )
    openrouter_model: str = Field(
        default="nvidia/nemotron-3-super-120b-a12b:free",
        alias="OPENROUTER_MODEL",
    )
    openrouter_fallback_models: str = Field(
        default="nvidia/nemotron-3-nano-30b-a3b:free",
        alias="OPENROUTER_FALLBACK_MODELS",
    )
    openrouter_timeout_seconds: float = Field(
        default=60.0,
        gt=0,
        alias="OPENROUTER_TIMEOUT_SECONDS",
    )
    openrouter_referer: str = Field(default="http://localhost", alias="OPENROUTER_REFERER")
    llm_provider: str = Field(default="openrouter", alias="LLM_PROVIDER")
    llm_model: str = Field(
        default="nvidia/nemotron-3-super-120b-a12b:free",
        alias="LLM_MODEL",
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")
    rate_limit_requests: int = Field(default=120, alias="RATE_LIMIT_REQUESTS")
    rate_limit_window_seconds: int = Field(default=60, alias="RATE_LIMIT_WINDOW_SECONDS")

    @field_validator("app_env")
    @classmethod
    def validate_app_env(cls, value: str) -> str:
        allowed = {"local", "test", "staging", "production"}
        if value not in allowed:
            msg = f"APP_ENV must be one of {sorted(allowed)}"
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.app_env == "production" and self.jwt_secret_key == "change-me-local-only":
            raise ValueError("JWT_SECRET_KEY must be set from a secret manager in production")
        return self

    @property
    def openrouter_fallback_model_list(self) -> list[str]:
        return [
            model.strip()
            for model in self.openrouter_fallback_models.split(",")
            if model.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
