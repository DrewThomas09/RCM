"""Types + config for the local PEdesk Guide RAG layer.

All read-only and local: documents come from the in-repo registries and
docs, embeddings come from a local Ollama model, and the index is a local
SQLite file. No cloud calls, no user uploads, no conversation memory.

Config (env; RAG is OFF by default — the v1 behavior is unchanged unless
an operator opts in AND has built a local index):

  PEDESK_GUIDE_RAG_ENABLED      true/false  (default: false)
  PEDESK_GUIDE_RAG_EMBED_MODEL  default nomic-embed-text
  PEDESK_GUIDE_RAG_INDEX_PATH   default .pedesk_guide_rag.sqlite3
  PEDESK_GUIDE_RAG_TOP_K        default 5
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

DEFAULT_EMBED_MODEL = "nomic-embed-text"
DEFAULT_INDEX_PATH = ".pedesk_guide_rag.sqlite3"
DEFAULT_TOP_K = 5


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    return (os.environ.get(name) or "").strip() or default


def is_rag_enabled() -> bool:
    return (_env("PEDESK_GUIDE_RAG_ENABLED", "") or "").lower() in (
        "1", "true", "yes", "on",
    )


def rag_embed_model() -> str:
    return _env("PEDESK_GUIDE_RAG_EMBED_MODEL", DEFAULT_EMBED_MODEL) or DEFAULT_EMBED_MODEL


def rag_index_path() -> str:
    return _env("PEDESK_GUIDE_RAG_INDEX_PATH", DEFAULT_INDEX_PATH) or DEFAULT_INDEX_PATH


def rag_top_k() -> int:
    raw = _env("PEDESK_GUIDE_RAG_TOP_K")
    if not raw:
        return DEFAULT_TOP_K
    try:
        return max(1, min(20, int(raw)))
    except ValueError:
        return DEFAULT_TOP_K


@dataclass
class RagDocument:
    """A read-only source document before chunking (one per entity/file)."""

    source_id: str
    source_type: str  # page_context | metric | data_source | guide_policy | doc
    title: str
    text: str
    route: Optional[str] = None
    metric_id: Optional[str] = None
    data_source_id: Optional[str] = None
    file_path: Optional[str] = None
    section: Optional[str] = None
    source_confidence: Optional[str] = None
    data_confidence: Optional[str] = None


@dataclass
class RagChunk:
    """A chunk of a document, carrying its source metadata + content hash."""

    source_id: str
    source_type: str
    title: str
    text: str
    content_hash: str
    route: Optional[str] = None
    metric_id: Optional[str] = None
    data_source_id: Optional[str] = None
    file_path: Optional[str] = None
    section: Optional[str] = None
    source_confidence: Optional[str] = None
    data_confidence: Optional[str] = None

    def metadata(self) -> Dict[str, object]:
        return {
            "source_id": self.source_id,
            "source_type": self.source_type,
            "title": self.title,
            "route": self.route,
            "metric_id": self.metric_id,
            "data_source_id": self.data_source_id,
            "file_path": self.file_path,
            "section": self.section,
            "source_confidence": self.source_confidence,
            "data_confidence": self.data_confidence,
        }


@dataclass
class RagSearchResult:
    """A retrieved chunk + its similarity score + a snippet."""

    title: str
    source_type: str
    text: str
    score: float
    route: Optional[str] = None
    metric_id: Optional[str] = None
    data_source_id: Optional[str] = None
    source_id: Optional[str] = None
    section: Optional[str] = None

    def snippet(self, max_chars: int = 320) -> str:
        t = " ".join((self.text or "").split())
        return t if len(t) <= max_chars else t[: max_chars - 1].rstrip() + "…"

    def source_label(self) -> str:
        kind = {
            "page_context": "Page",
            "metric": "Metric Registry",
            "data_source": "Data Source Registry",
            "guide_policy": "Guide Policy",
            "doc": "Doc",
        }.get(self.source_type, self.source_type)
        return f"{kind} — {self.title}"
