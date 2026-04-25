"""Emerging-theme heatmap — theme × time period.

Walks the corpus, scores every document against the theme anchors,
buckets by date period (year or quarter), and reports the per-
period theme density. Output is a (theme × period) matrix the
partner uses to spot themes whose density is rising fastest.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Tuple

from .corpus import Document
from .themes import THEME_ANCHORS, score_deal_against_themes, ThemeAnchor


def _period_for(date_str: str, granularity: str = "year") -> str:
    """Bucket date into a period key. Granularity 'year' or 'quarter'."""
    if not date_str or len(date_str) < 4:
        return "unknown"
    year = date_str[:4]
    if granularity == "year":
        return year
    if granularity == "quarter" and len(date_str) >= 7:
        try:
            month = int(date_str[5:7])
            q = (month - 1) // 3 + 1
            return f"{year}Q{q}"
        except ValueError:
            return year
    return year


def emerging_theme_heatmap(
    documents: Iterable[Document],
    *,
    granularity: str = "year",
    custom_anchors: Optional[Dict[str, ThemeAnchor]] = None,
) -> Dict[str, Dict[str, float]]:
    """Build the (theme × period) heatmap.

    Returns: {theme_id → {period → average_score}}
    The average score per (theme, period) is the mean keyword
    density across documents in that period that mentioned the
    theme at all (zero-score documents are excluded so themes
    don't get diluted by unrelated coverage).
    """
    sums: Dict[Tuple[str, str], float] = defaultdict(float)
    counts: Dict[Tuple[str, str], int] = defaultdict(int)

    for doc in documents:
        period = _period_for(doc.date, granularity)
        matches = score_deal_against_themes(
            doc.text, custom_anchors=custom_anchors)
        for m in matches:
            key = (m.theme_id, period)
            sums[key] += m.score
            counts[key] += 1

    heatmap: Dict[str, Dict[str, float]] = {}
    for (theme_id, period), total in sums.items():
        n = max(1, counts[(theme_id, period)])
        heatmap.setdefault(theme_id, {})[period] = round(
            total / n, 4)
    return heatmap
