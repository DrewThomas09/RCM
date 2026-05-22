"""RAG retrieval — embed a query (+ optional route/title) and return the
top local chunks. Read-only; no LLM call here."""
from __future__ import annotations

import os
from typing import List, Optional

from . import vector_store
from .embeddings import embed_query
from .types import RagSearchResult, rag_index_path, rag_top_k


def index_exists(path: Optional[str] = None) -> bool:
    return os.path.exists(path or rag_index_path())


def search(query: str, top_k: Optional[int] = None,
           route: Optional[str] = None, page_title: Optional[str] = None,
           index_path: Optional[str] = None) -> List[RagSearchResult]:
    """Return the top matching chunks for ``query``.

    Raises ``ollama_client.OllamaError`` if the embedding model is
    unavailable. Returns ``[]`` if the index is empty/missing.
    """
    q = (query or "").strip()
    if not q:
        return []
    if not index_exists(index_path):
        return []
    # Light query expansion: route + page title sharpen retrieval toward
    # the page the user is on without overwhelming the question.
    enriched = q
    extra = " ".join(x for x in (page_title, route) if x)
    if extra:
        enriched = f"{q}\n(context: {extra})"
    vec = embed_query(enriched)
    con = vector_store.connect(index_path)
    try:
        return vector_store.search_similar(con, vec, top_k or rag_top_k())
    finally:
        con.close()
