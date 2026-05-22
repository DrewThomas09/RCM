"""RAG retrieval — embed a query (+ optional route/title) and return the
top local chunks. Read-only; no LLM call here."""
from __future__ import annotations

import os
import sqlite3
from typing import Dict, List, Optional

from . import vector_store
from .embeddings import embed_query
from .types import RagSearchResult, rag_index_path, rag_top_k


def index_exists(path: Optional[str] = None) -> bool:
    return os.path.exists(path or rag_index_path())


def index_status(path: Optional[str] = None) -> Dict[str, object]:
    """Cheap, Ollama-free index health: existence + chunk/embedding counts
    + distinct embedding models. Never raises (a corrupt/locked DB reports
    exists=True with an error note)."""
    p = path or rag_index_path()
    status: Dict[str, object] = {
        "exists": os.path.exists(p), "chunk_count": 0,
        "embedded_count": 0, "embedding_models": [],
    }
    if not status["exists"]:
        return status
    try:
        con = vector_store.connect(p)
        try:
            status["chunk_count"] = vector_store.count_chunks(con)
            status["embedded_count"] = vector_store.count_embedded(con)
            rows = con.execute(
                "SELECT DISTINCT embedding_model FROM guide_rag_chunks"
            ).fetchall()
            status["embedding_models"] = [r[0] for r in rows if r[0]]
        finally:
            con.close()
    except sqlite3.Error as exc:
        status["error"] = f"index unreadable: {exc}"
    return status


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
    # Normalize top_k: ignore <=0 / non-int; cap to a sane ceiling.
    k = top_k if (isinstance(top_k, int) and top_k > 0) else rag_top_k()
    k = min(k, 50)
    vec = embed_query(enriched)
    con = vector_store.connect(index_path)
    try:
        return vector_store.search_similar(con, vec, k)
    finally:
        con.close()
