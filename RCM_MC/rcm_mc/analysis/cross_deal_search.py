"""Cross-deal full-text search (Prompt 62).

"Didn't we see something similar at the Cleveland deal?" Searches
across deal_notes, deal_overrides, risk flags, diligence questions,
and analysis packets. TF-IDF-style keyword scoring with related-term
expansion for RCM jargon.
"""
from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    deal_id: str
    source_type: str      # note | override | risk_flag | question
    text_snippet: str
    relevance_score: float = 0.0
    created_at: str = ""
    author: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deal_id": self.deal_id,
            "source_type": self.source_type,
            "text_snippet": self.text_snippet,
            "relevance_score": float(self.relevance_score),
            "created_at": self.created_at,
            "author": self.author,
        }


# ── Related terms ──────────────────────────────────────────────────

RELATED_TERMS: Dict[str, List[str]] = {
    "denial": ["denial_rate", "appeal", "overturn", "carc", "rework",
               "initial_denial", "final_denial"],
    "ar": ["days_in_ar", "aging", "collections", "follow-up",
           "ar_over_90", "receivable"],
    "coding": ["cdi", "cmi", "case_mix", "drg", "hcc"],
    "collection": ["net_collection_rate", "cost_to_collect",
                    "clean_claim", "first_pass"],
    "payer": ["payer_mix", "commercial", "medicare", "medicaid",
              "managed_care"],
}


def _expand_query(query: str) -> List[str]:
    """Return the original tokens + any related terms."""
    tokens = re.findall(r"\w+", query.lower())
    expanded = list(tokens)
    for t in tokens:
        for key, related in RELATED_TERMS.items():
            if t == key or t in related:
                expanded.extend(related)
                if t != key:
                    expanded.append(key)
    return list(set(expanded))


def _score_text(text: str, tokens: List[str]) -> float:
    """Simple keyword-frequency scoring."""
    if not text or not tokens:
        return 0.0
    text_lower = text.lower()
    hits = sum(1 for t in tokens if t in text_lower)
    if hits == 0:
        return 0.0
    return hits / len(tokens)


# ── Collectors ─────────────────────────────────────────────────────

def _search_notes(
    store: Any, tokens: List[str], deal_ids: Optional[List[str]],
) -> List[SearchResult]:
    results: List[SearchResult] = []
    try:
        from ..deals.deal_notes import list_notes
        df = list_notes(store)
        for _, row in df.iterrows():
            did = str(row.get("deal_id") or "")
            if deal_ids and did not in deal_ids:
                continue
            body = str(row.get("body") or "")
            score = _score_text(body, tokens)
            if score > 0:
                results.append(SearchResult(
                    deal_id=did, source_type="note",
                    text_snippet=body[:200],
                    relevance_score=score,
                    created_at=str(row.get("created_at") or ""),
                    author=str(row.get("author") or ""),
                ))
    except Exception:  # noqa: BLE001
        pass
    return results


def _search_overrides(
    store: Any, tokens: List[str], deal_ids: Optional[List[str]],
) -> List[SearchResult]:
    results: List[SearchResult] = []
    try:
        from ..analysis.deal_overrides import list_overrides
        for row in list_overrides(store):
            did = str(row.get("deal_id") or "")
            if deal_ids and did not in deal_ids:
                continue
            text = f"{row.get('override_key') or ''} {row.get('reason') or ''}"
            score = _score_text(text, tokens)
            if score > 0:
                results.append(SearchResult(
                    deal_id=did, source_type="override",
                    text_snippet=text[:200],
                    relevance_score=score,
                    created_at=str(row.get("set_at") or ""),
                    author=str(row.get("set_by") or ""),
                ))
    except Exception:  # noqa: BLE001
        pass
    return results


def _search_packets(
    store: Any, tokens: List[str], deal_ids: Optional[List[str]],
) -> List[SearchResult]:
    """Search risk flags + diligence questions in latest packets."""
    results: List[SearchResult] = []
    try:
        from ..analysis.analysis_store import list_packets, load_packet_by_id
        rows = list_packets(store)
        seen: set = set()
        for r in rows:
            did = r.get("deal_id") or ""
            if did in seen:
                continue
            seen.add(did)
            if deal_ids and did not in deal_ids:
                continue
            pkt = load_packet_by_id(store, r["id"])
            if pkt is None:
                continue
            for rf in (pkt.risk_flags or []):
                text = f"{rf.title or ''} {rf.detail or rf.explanation or ''}"
                score = _score_text(text, tokens)
                if score > 0:
                    results.append(SearchResult(
                        deal_id=did, source_type="risk_flag",
                        text_snippet=text[:200],
                        relevance_score=score,
                    ))
            for q in (pkt.diligence_questions or []):
                text = f"{q.question or ''} {q.context or ''}"
                score = _score_text(text, tokens)
                if score > 0:
                    results.append(SearchResult(
                        deal_id=did, source_type="question",
                        text_snippet=text[:200],
                        relevance_score=score,
                    ))
    except Exception:  # noqa: BLE001
        pass
    return results


# ── Public entry ──────────────────────────────────────────────────

def search_across_deals(
    store: Any, query: str, *, deal_ids: Optional[List[str]] = None,
    limit: int = 50,
) -> List[SearchResult]:
    """Full-text search across all deal-level content.

    Returns results sorted by relevance descending. Empty query →
    empty results (no crash).
    """
    if not (query or "").strip():
        return []
    tokens = _expand_query(query)
    if not tokens:
        return []
    results: List[SearchResult] = []
    results.extend(_search_notes(store, tokens, deal_ids))
    results.extend(_search_overrides(store, tokens, deal_ids))
    results.extend(_search_packets(store, tokens, deal_ids))
    results.sort(key=lambda r: r.relevance_score, reverse=True)
    return results[:int(limit)]
