"""Deterministic chunking for RAG documents.

Registry entries (page/metric/data-source/policy) are short and become a
single chunk each — splitting them would only fragment a coherent
definition. Longer docs are split on paragraph/heading boundaries into
~500-900-word chunks with light overlap. Chunk text + a content hash make
re-indexing idempotent.
"""
from __future__ import annotations

import hashlib
import re
from typing import List

from .types import RagChunk, RagDocument

# ~600 words ≈ 3600 chars; cap a touch higher so most registry/doc
# sections stay whole.
_MAX_CHARS = 4200
_OVERLAP_CHARS = 300
_SINGLE_CHUNK_TYPES = {"page_context", "metric", "data_source", "guide_policy"}


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _chunk_for(doc: RagDocument, text: str, section: str = None) -> RagChunk:
    return RagChunk(
        source_id=doc.source_id,
        source_type=doc.source_type,
        title=doc.title,
        text=text,
        content_hash=_hash(f"{doc.source_id}|{section or ''}|{text}"),
        route=doc.route,
        metric_id=doc.metric_id,
        data_source_id=doc.data_source_id,
        file_path=doc.file_path,
        section=section or doc.section,
        source_confidence=doc.source_confidence,
        data_confidence=doc.data_confidence,
    )


def _split_long(text: str) -> List[str]:
    """Greedy paragraph-packed split into <=_MAX_CHARS pieces with overlap."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: List[str] = []
    cur = ""
    for p in paras:
        if len(p) > _MAX_CHARS:
            # A single huge paragraph — hard-wrap it.
            if cur:
                chunks.append(cur); cur = ""
            for i in range(0, len(p), _MAX_CHARS - _OVERLAP_CHARS):
                chunks.append(p[i:i + _MAX_CHARS])
            continue
        if cur and len(cur) + len(p) + 2 > _MAX_CHARS:
            chunks.append(cur)
            tail = cur[-_OVERLAP_CHARS:] if len(cur) > _OVERLAP_CHARS else ""
            cur = (tail + "\n\n" + p).strip()
        else:
            cur = (cur + "\n\n" + p).strip() if cur else p
    if cur:
        chunks.append(cur)
    return chunks or [text]


def chunk_document(doc: RagDocument) -> List[RagChunk]:
    text = (doc.text or "").strip()
    if not text:
        return []
    if doc.source_type in _SINGLE_CHUNK_TYPES or len(text) <= _MAX_CHARS:
        return [_chunk_for(doc, text)]
    pieces = _split_long(text)
    out: List[RagChunk] = []
    for i, piece in enumerate(pieces):
        out.append(_chunk_for(doc, piece, section=f"part {i + 1}/{len(pieces)}"))
    return out


def chunk_documents(docs: List[RagDocument]) -> List[RagChunk]:
    out: List[RagChunk] = []
    for d in docs:
        out.extend(chunk_document(d))
    return out
