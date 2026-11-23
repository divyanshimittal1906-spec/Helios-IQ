from dataclasses import dataclass
from typing import Literal

ProviderType = Literal['openai', 'azure-openai']


@dataclass(frozen=True)
class AIModelConfig:
    provider: ProviderType
    model: str
    api_key: str
    base_url: str = ''
