"""Local, read-only RAG layer for the PEdesk Guide.

Indexes in-repo Guide context (page/metric/data-source registries, the
read-only policy, and curated methodology docs) into a local SQLite
vector store using local Ollama embeddings. No cloud calls, no user
uploads, no conversation memory. Disabled by default
(PEDESK_GUIDE_RAG_ENABLED).
"""
from .types import (
    RagChunk,
    RagDocument,
    RagSearchResult,
    is_rag_enabled,
    rag_embed_model,
    rag_index_path,
    rag_top_k,
)

__all__ = [
    "RagChunk",
    "RagDocument",
    "RagSearchResult",
    "is_rag_enabled",
    "rag_embed_model",
    "rag_index_path",
    "rag_top_k",
]
