from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "dealcompass-api"
    app_env: str = "local"
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/dealcompass"
    frontend_origin: str = "http://localhost:5173"
    worker_poll_interval_seconds: float = 2

    # Provider-agnostic LLM config (defaults to OpenRouter)
    llm_provider: str = "openrouter"
    llm_api_key: str = ""
    llm_model: str = ""
    llm_base_url: str = ""

    # OpenRouter primary config
    openrouter_api_key: str = ""
    openrouter_model: str = "anthropic/claude-sonnet-4.5"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    google_maps_api_key: str = ""
    apify_token: str = ""
    dapta_api_key: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def resolved_llm_api_key(self) -> str:
        return self.llm_api_key or self.openrouter_api_key

    @property
    def resolved_llm_model(self) -> str:
        return self.llm_model or self.openrouter_model

    @property
    def resolved_llm_base_url(self) -> str:
        if self.llm_base_url:
            return self.llm_base_url
        if self.llm_provider.lower() == "openrouter":
            return self.openrouter_base_url
        return "https://api.openai.com/v1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
