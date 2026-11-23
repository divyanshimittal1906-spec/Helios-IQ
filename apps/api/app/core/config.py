from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = Field(default='development', alias='APP_ENV')
    secret_key: str = Field(default='', alias='SECRET_KEY')
    jwt_secret_key: str = Field(default='', alias='JWT_SECRET_KEY')
    auth_secret: str = Field(default='', alias='AUTH_SECRET')
    jwt_algorithm: str = Field(default='HS256', alias='JWT_ALGORITHM')
    access_token_expire_minutes: int = Field(default=15, alias='ACCESS_TOKEN_EXPIRE_MINUTES')
    refresh_token_expire_days: int = Field(default=7, alias='REFRESH_TOKEN_EXPIRE_DAYS')
    cookie_secure: bool | None = Field(default=None, alias='COOKIE_SECURE')
    cookie_samesite: str = Field(default='lax', alias='COOKIE_SAMESITE')
    cors_origins: List[str] = Field(
        default_factory=lambda: ['http://localhost:3000', 'http://127.0.0.1:3000'],
        alias='CORS_ORIGINS',
    )
    allow_sqlite_fallback: bool = Field(default=True, alias='ALLOW_SQLITE_FALLBACK')
    database_url: str = Field(default='postgresql+psycopg://postgres:postgres@localhost:5432/helios_iq', alias='DATABASE_URL')
    redis_url: str = Field(default='redis://localhost:6379/0', alias='REDIS_URL')
    ai_api_key: str = Field(default='', alias='AI_API_KEY')
    ai_model: str = Field(default='gpt-4o-mini', alias='AI_MODEL')
    ai_base_url: str = Field(default='', alias='AI_BASE_URL')
    ai_provider: str = Field(default='openai', alias='AI_PROVIDER')
    embedding_provider: str = Field(default='openai', alias='EMBEDDING_PROVIDER')
    embedding_model: str = Field(default='text-embedding-3-small', alias='EMBEDDING_MODEL')
    embedding_dimension: int = Field(default=1536, alias='EMBEDDING_DIMENSION')
    embedding_max_retries: int = Field(default=2, alias='EMBEDDING_MAX_RETRIES')
    rag_top_k: int = Field(default=5, alias='RAG_TOP_K')
    rag_max_context_chunks: int = Field(default=5, alias='RAG_MAX_CONTEXT_CHUNKS')
    rag_max_context_tokens: int = Field(default=2000, alias='RAG_MAX_CONTEXT_TOKENS')
    allowed_hosts: List[str] = Field(default_factory=lambda: ['localhost', '127.0.0.1'], alias='ALLOWED_HOSTS')
    max_document_size: int = Field(default=10 * 1024 * 1024, alias='MAX_DOCUMENT_SIZE')
    chunk_size: int = Field(default=1200, alias='CHUNK_SIZE')
    chunk_overlap: int = Field(default=200, alias='CHUNK_OVERLAP')
    document_storage_path: str = Field(default='storage/documents', alias='DOCUMENT_STORAGE_PATH')

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() in ('production', 'prod')

    @property
    def is_cookie_secure(self) -> bool:
        if self.cookie_secure is not None:
            return self.cookie_secure
        return self.is_production

    def get_jwt_secret(self) -> str:
        candidate = self.jwt_secret_key or self.auth_secret or self.secret_key
        if self.is_production:
            if not candidate or candidate.strip() in ('change-me', 'default-secret', 'insecure-secret'):
                raise ValueError('Production environment requires a strong, explicit JWT_SECRET_KEY or AUTH_SECRET.')
            return candidate.strip()
        if not candidate or candidate.strip() in ('change-me', 'default-secret'):
            return 'dev-insecure-secret-key-helios-iq-development-only-replace-in-prod'
        return candidate.strip()


@lru_cache
def get_settings() -> Settings:
    return Settings()

