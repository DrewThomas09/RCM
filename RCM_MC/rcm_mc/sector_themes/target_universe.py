"""Thesis-aligned target universe builder.

Given a thesis (one or more theme_ids the partner is bullish on)
and a corpus of candidate deals, return the deals whose theme
match exceeds a minimum threshold, ranked by composite score.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from .corpus import Document
from .themes import score_deal_against_themes


@dataclass
class TargetUniverseEntry:
    doc_id: str
    composite_score: float
    matched_themes: List[Dict[str, Any]] = field(default_factory=list)


def build_target_universe(
    documents: Iterable[Document],
    thesis_theme_ids: List[str],
    *,
    min_composite: float = 0.10,
    top_n: int = 50,
) -> List[TargetUniverseEntry]:
    """Score each deal against the thesis themes, return the
    top-N with composite score ≥ ``min_composite``.

    Composite score = sum over thesis_themes of theme_score —
    reward deals that hit MULTIPLE thesis themes (multi-theme
    deals are usually better positioned than single-theme ones).
    """
    thesis_set = set(thesis_theme_ids)
    out: List[TargetUniverseEntry] = []
    for doc in documents:
        matches = score_deal_against_themes(doc.text)
        relevant = [m for m in matches if m.theme_id in thesis_set]
        if not relevant:
            continue
        composite = sum(m.score for m in relevant)
        if composite < min_composite:
            continue
        out.append(TargetUniverseEntry(
            doc_id=doc.doc_id,
            composite_score=round(composite, 4),
            matched_themes=[
                {"theme_id": m.theme_id, "label": m.label,
                 "score": m.score}
                for m in relevant
            ],
        ))
    out.sort(key=lambda e: e.composite_score, reverse=True)
    return out[:top_n]
