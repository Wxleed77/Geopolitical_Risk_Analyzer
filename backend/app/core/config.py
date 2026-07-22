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
    anthropic_api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
