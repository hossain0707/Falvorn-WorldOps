"""Validated runtime configuration; keep secrets out of repositories."""
from functools import lru_cache
from typing import Literal
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    app_env: Literal['development', 'test', 'production'] = 'development'
    database_url: str = 'sqlite:///./worldops.db'
    api_key: str = ''
    read_only_api_key: str = ''
    cors_origins: str = 'http://localhost:8000,http://127.0.0.1:8000'
    max_agents_per_world: int = 50
    max_model_calls_per_world: int = 10000
    llm_api_key: str = ''
    llm_base_url: str = 'https://api.openai.com/v1'
    llm_allowed_models: str = 'gpt-4.1-mini,gpt-4o-mini'
    llm_timeout_seconds: float = 20.0
    webhook_url: str = ''
    webhook_signing_secret: str = ''
    polling_interval_seconds: float = 3.0

    @model_validator(mode='after')
    def production_guards(self):
        if self.app_env == 'production':
            if len(self.api_key) < 24:
                raise ValueError('Production API_KEY must be at least 24 characters')
            if self.read_only_api_key and (len(self.read_only_api_key) < 24 or self.read_only_api_key == self.api_key):
                raise ValueError('READ_ONLY_API_KEY must be 24+ characters and different from API_KEY')
            if not self.database_url.startswith('postgresql+psycopg://'):
                raise ValueError('Production requires PostgreSQL / psycopg database URL')
            if '*' in self.cors_origins:
                raise ValueError('Wildcard CORS not allowed in production')
            if self.webhook_url and (not self.webhook_url.startswith('https://') or len(self.webhook_signing_secret) < 24):
                raise ValueError('Outbound webhooks require HTTPS and a signing secret (24+ chars)')
        return self

    @property
    def allowed_models(self):
        return {s.strip() for s in self.llm_allowed_models.split(',') if s.strip()}

    @property
    def origins(self):
        return [x.strip() for x in self.cors_origins.split(',') if x.strip()]

@lru_cache
def get_settings() -> Settings:
    return Settings()
