"""Configuracao centralizada via variaveis de ambiente (.env)."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM provider (auto-detecta se nao definir; aceita 'anthropic' | 'gemini')
    llm_provider: str = ""

    # Anthropic
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"

    # Google Gemini (free tier: aistudio.google.com/apikey)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    # JWT
    jwt_secret: str = "dev-secret-troque-em-producao"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24h

    # Banco
    database_url: str = "sqlite:///./assetia.sqlite"

    # Scanner
    default_network: str = "192.168.1.0/24"
    scan_timeout_seconds: int = 3
    max_parallel_pings: int = 64

    # Servidor
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
