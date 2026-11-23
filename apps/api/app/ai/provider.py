from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from typing import Sequence

import httpx

from app.ai.models import AIModelConfig
from app.core.config import get_settings


class AIProvider(ABC):
    """Abstract AI provider interface for model integrations."""

    def __init__(self, config: AIModelConfig | None = None) -> None:
        self.config = config or AIModelConfig(provider='openai', model='gpt-4o-mini', api_key='', base_url='')

    @abstractmethod
    def generate(self, prompt: str, **kwargs: object) -> str:
        raise NotImplementedError('AI provider implementation is not yet active.')


class EmbeddingProvider(ABC):
    """Provider-agnostic interface for generating embeddings."""

    def __init__(self, config: AIModelConfig | None = None) -> None:
        self.config = config or AIModelConfig(provider='openai', model='text-embedding-3-small', api_key='', base_url='')

    @abstractmethod
    def embed_text(self, text: str, **kwargs: object) -> list[float]:
        raise NotImplementedError('Embedding provider implementation is not yet active.')

    @abstractmethod
    def embed_documents(self, documents: Sequence[str], **kwargs: object) -> list[list[float]]:
        raise NotImplementedError('Embedding provider implementation is not yet active.')


class MockEmbeddingProvider(EmbeddingProvider):
    def __init__(self, config: AIModelConfig | None = None) -> None:
        super().__init__(config)
        self.dimension = get_settings().embedding_dimension

    def _vector_for_text(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode('utf-8')).digest()
        values: list[float] = []
        for index in range(self.dimension):
            byte = digest[index % len(digest)]
            values.append(((byte + index * 17) % 251) / 250.0)
        return values

    def embed_text(self, text: str, **kwargs: object) -> list[float]:
        return self._vector_for_text(text)

    def embed_documents(self, documents: Sequence[str], **kwargs: object) -> list[list[float]]:
        return [self._vector_for_text(str(document)) for document in documents]


class OpenAICompatibleEmbeddingProvider(EmbeddingProvider):
    def __init__(self, config: AIModelConfig) -> None:
        super().__init__(config)
        self.base_url = config.base_url or 'https://api.openai.com/v1'

    def embed_text(self, text: str, **kwargs: object) -> list[float]:
        return self.embed_documents([text], **kwargs)[0]

    def embed_documents(self, documents: Sequence[str], **kwargs: object) -> list[list[float]]:
        if not self.config.api_key:
            raise RuntimeError('Embedding API key is not configured.')

        payload = {'model': self.config.model, 'input': list(documents)}
        response = httpx.post(
            f'{self.base_url.rstrip("/")}/embeddings',
            headers={'Authorization': f'Bearer {self.config.api_key}', 'Content-Type': 'application/json'},
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        return [item['embedding'] for item in data.get('data', [])]


class OpenAICompatibleChatProvider(AIProvider):
    def __init__(self, config: AIModelConfig) -> None:
        super().__init__(config)
        self.base_url = config.base_url or 'https://api.openai.com/v1'

    def generate(self, prompt: str, **kwargs: object) -> str:
        if not self.config.api_key:
            raise RuntimeError('AI API key is not configured.')

        payload = {
            'model': self.config.model,
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': kwargs.get('temperature', 0.2),
            'max_tokens': kwargs.get('max_tokens', 512),
        }
        response = httpx.post(
            f'{self.base_url.rstrip("/")}/chat/completions',
            headers={'Authorization': f'Bearer {self.config.api_key}', 'Content-Type': 'application/json'},
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        return data['choices'][0]['message']['content']


def get_embedding_provider() -> EmbeddingProvider:
    settings = get_settings()
    config = AIModelConfig(
        provider=settings.embedding_provider,
        model=settings.embedding_model,
        api_key=settings.ai_api_key,
        base_url=settings.ai_base_url,
    )
    if settings.embedding_provider == 'mock':
        return MockEmbeddingProvider(config)
    if settings.embedding_provider == 'openai':
        if not settings.ai_api_key:
            return MockEmbeddingProvider(config)
        return OpenAICompatibleEmbeddingProvider(config)
    raise ValueError(f'Unsupported embedding provider: {settings.embedding_provider}')


def get_ai_provider() -> AIProvider | None:
    settings = get_settings()
    if not settings.ai_api_key:
        return None
    config = AIModelConfig(
        provider=settings.ai_provider,
        model=settings.ai_model,
        api_key=settings.ai_api_key,
        base_url=settings.ai_base_url,
    )
    if settings.ai_provider == 'openai':
        return OpenAICompatibleChatProvider(config)
    return None
