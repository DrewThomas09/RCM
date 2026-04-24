"""Curated news-feed loader + target-relevance filter."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import yaml


CONTENT_DIR = Path(__file__).parent / "content"


@dataclass
class NewsItem:
    date: str
    title: str
    source: str
    url: str
    summary: str
    tickers: List[str] = field(default_factory=list)
    specialty: Optional[str] = None
    sentiment: str = "neutral"           # positive | negative | neutral
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


def _load() -> Dict[str, Any]:
    return yaml.safe_load(
        (CONTENT_DIR / "news_feed.yaml").read_text("utf-8")
    )


def _all_items() -> List[NewsItem]:
    out: List[NewsItem] = []
    for row in _load().get("items") or ():
        out.append(NewsItem(
            date=str(row.get("date", "")),
            title=str(row.get("title", "")),
            source=str(row.get("source", "")),
            url=str(row.get("url", "")),
            summary=str(row.get("summary", "")),
            tickers=list(row.get("tickers") or ()),
            specialty=row.get("specialty"),
            sentiment=str(row.get("sentiment", "neutral")),
            tags=list(row.get("tags") or ()),
        ))
    # Sort newest-first.
    out.sort(key=lambda i: i.date, reverse=True)
    return out


def news_for_target(
    *,
    specialty: Optional[str] = None,
    tickers: Optional[Iterable[str]] = None,
    tags: Optional[Iterable[str]] = None,
    limit: int = 20,
) -> List[NewsItem]:
    """Filter the feed by target context.

    If nothing is supplied, returns the newest ``limit`` items.
    Otherwise filters to items matching ANY supplied filter (union).
    """
    items = _all_items()
    sp = (specialty or "").upper()
    tickers_set = {str(t).upper() for t in (tickers or ())}
    tags_set = {str(t).lower() for t in (tags or ())}
    if not (sp or tickers_set or tags_set):
        return items[:limit]
    out: List[NewsItem] = []
    for it in items:
        match = False
        if sp and (it.specialty or "").upper() == sp:
            match = True
        if not match and tickers_set & {t.upper() for t in it.tickers}:
            match = True
        if not match and tags_set & {str(t).lower() for t in it.tags}:
            match = True
        if match:
            out.append(it)
    return out[:limit]


def sector_sentiment(specialty: str) -> Optional[str]:
    """Return the curated sector-sentiment label for a specialty
    (positive / negative / neutral / mixed) or None when the
    specialty isn't on the lattice."""
    data = _load()
    return (data.get("sector_sentiment") or {}).get(
        (specialty or "").upper(),
    )
