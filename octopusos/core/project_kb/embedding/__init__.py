"""Embedding Provider 模块

提供向量 embedding 生成能力，支持多种 provider:
- local: sentence-transformers (本地)
- openai: OpenAI embeddings (未来扩展)
"""

from octopusos.core.project_kb.embedding.provider import IEmbeddingProvider
from octopusos.core.project_kb.embedding.factory import create_provider
from octopusos.core.project_kb.embedding.manager import EmbeddingManager

__all__ = [
    "IEmbeddingProvider",
    "create_provider",
    "EmbeddingManager",
]
