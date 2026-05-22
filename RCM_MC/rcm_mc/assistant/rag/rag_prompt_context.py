"""Format retrieved RAG chunks for the prompt + the response metadata.

The retrieved context is SUPPORTING material — the prompt builder makes
clear the current-route packet is primary. Chunks are length-capped so a
few hundred chars per source flow into the prompt, not whole documents.
"""
from __future__ import annotations

from typing import Dict, List

from .types import RagSearchResult

_PER_CHUNK_CHARS = 600


def format_rag_context(results: List[RagSearchResult]) -> str:
    """Render retrieved chunks as an 'Additional local Guide context'
    block, or '' when there is nothing to add."""
    if not results:
        return ""
    lines = [
        "=== Additional local Guide context (retrieved) ===",
        "Supporting reference from the PEdesk Guide knowledge base "
        "(registries, policy, methodology docs). The current-page context "
        "above is primary; use these only to add definitions, methodology, "
        "or related-source explanations. They are NOT this deal's data "
        "unless their own text says so.",
    ]
    for i, r in enumerate(results, 1):
        body = " ".join((r.text or "").split())
        if len(body) > _PER_CHUNK_CHARS:
            body = body[: _PER_CHUNK_CHARS - 1].rstrip() + "…"
        lines.append(f"[{i}] {r.source_label()}: {body}")
    return "\n".join(lines)


def rag_sources_used(results: List[RagSearchResult]) -> List[Dict[str, object]]:
    """Compact, safe per-source metadata for the API response."""
    out: List[Dict[str, object]] = []
    for r in results:
        out.append({
            "title": r.title,
            "source_type": r.source_type,
            "route": r.route,
            "metric_id": r.metric_id,
            "data_source_id": r.data_source_id,
            "score": r.score,
        })
    return out


def citation_line(results: List[RagSearchResult]) -> str:
    """A plain-text 'Guide context used: …' line for the prompt."""
    if not results:
        return ""
    labels = "; ".join(r.source_label() for r in results)
    return f"Guide context used: {labels}."
