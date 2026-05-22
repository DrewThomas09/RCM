"""Local embedding helpers for RAG (Ollama nomic-embed-text by default).

Thin wrapper over ``ollama_client.embed_texts`` plus a stdlib cosine
similarity. No cloud calls. Raises ``ollama_client.OllamaError`` upward
when the local embedding model is unavailable so callers can return a
clean error instead of crashing.
"""
from __future__ import annotations

import math
from typing import List

from .. import ollama_client
from .types import rag_embed_model

OllamaError = ollama_client.OllamaError


def embed_texts(texts: List[str], model: str = None) -> List[List[float]]:
    return ollama_client.embed_texts(texts, model or rag_embed_model())


def embed_query(text: str, model: str = None) -> List[float]:
    vecs = embed_texts([text], model=model)
    if not vecs:
        raise OllamaError("Embedding returned no vector for the query.")
    return vecs[0]


def cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))
