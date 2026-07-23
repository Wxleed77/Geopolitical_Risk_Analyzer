from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    database_url: str = "sqlite:///./dev.db"
    chroma_persist_dir: str = "./data/chroma"
    news_api_key: str = ""
    eia_api_key: str = ""
    admin_api_key: str = ""

    # LLM provider - OpenRouter (OpenAI-compatible endpoint) used instead of
    # paid Anthropic API for the agent/critic layer (M3+).
    llm_base_url: str = "https://openrouter.ai/api/v1"
    llm_api_key: str = ""
    llm_model: str = "meta-llama/llama-3.3-70b-instruct:free"


@lru_cache
def get_settings() -> Settings:
    return Settings()
