"""Live market-sentiment check — on-demand fetch of public news feeds.

The Public Market Intel page's "market read" is corpus-derived (bundled
comps + transactions, quarterly cadence). Partners asked for a way to ask
"what is the market saying RIGHT NOW?" — this module answers it honestly:

* ``fetch_live_headlines()`` pulls public Google News RSS feeds for a
  fixed set of healthcare-PE queries via stdlib ``urllib`` (no new deps,
  short timeout). No API keys, no scraping behind auth — RSS only.
* ``score_sentiment()`` applies a transparent keyword lexicon to the
  fetched headlines and returns the counts WITH the matched terms, so a
  partner can audit exactly why the needle reads where it does.
* Failure is honest: no network (air-gapped install, egress-blocked box)
  → ``{"ok": False, "error": ...}`` — the page falls back to the
  corpus-derived read and says so. Nothing is fabricated or cached as if
  it were live.
"""
from __future__ import annotations

import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List

# Fixed query set — healthcare-PE diligence framing, not user input
# (nothing user-controlled is interpolated into the fetch URLs).
_QUERIES = [
    "healthcare private equity",
    "hospital merger acquisition",
    "health system EBITDA margin",
]

_RSS_BASE = "https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"

# Transparent sentiment lexicon — deliberately small and auditable.
# Each match is reported back to the partner; this is a coarse needle,
# not an NLP model, and the page labels it as such.
_POSITIVE = (
    "record", "growth", "expand", "surge", "rally", "upgrade",
    "beat", "strong", "rebound", "recovery", "acquisition", "acquire",
    "invest", "raise", "ipo", "profit", "gain", "deal close",
)
_NEGATIVE = (
    "bankrupt", "default", "layoff", "closure", "close", "cut",
    "lawsuit", "probe", "investigation", "fraud", "decline", "drop",
    "miss", "downgrade", "loss", "warn", "strike", "shortfall",
    "denial", "writedown", "distress",
)

_TITLE_RE = re.compile(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>",
                       re.IGNORECASE | re.DOTALL)


def fetch_live_headlines(*, timeout: float = 6.0,
                         max_per_query: int = 12) -> List[str]:
    """Fetch current headlines from public RSS. Raises on total failure."""
    headlines: List[str] = []
    last_err: Exception | None = None
    for q in _QUERIES:
        url = _RSS_BASE.format(q=urllib.parse.quote(q))
        req = urllib.request.Request(
            url, headers={"User-Agent": "rcm-mc-sentiment/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read(512_000).decode("utf-8", "replace")
        except Exception as exc:  # noqa: BLE001 — collected, surfaced below
            last_err = exc
            continue
        titles = _TITLE_RE.findall(raw)
        # First <title> is the feed's own name — skip it.
        for t in titles[1:max_per_query + 1]:
            t = re.sub(r"\s+", " ", t).strip()
            if t and t not in headlines:
                headlines.append(t)
    if not headlines:
        raise (last_err or RuntimeError("no headlines returned"))
    return headlines


def score_sentiment(headlines: List[str]) -> Dict[str, Any]:
    """Keyword-lexicon sentiment over headlines. Transparent by design."""
    pos_hits: List[str] = []
    neg_hits: List[str] = []
    for h in headlines:
        hl = h.lower()
        for w in _POSITIVE:
            if w in hl:
                pos_hits.append(w)
        for w in _NEGATIVE:
            if w in hl:
                neg_hits.append(w)
    n_pos, n_neg = len(pos_hits), len(neg_hits)
    score = (n_pos - n_neg) / max(1, n_pos + n_neg)
    if score >= 0.25:
        label = "constructive"
    elif score <= -0.25:
        label = "risk-off"
    else:
        label = "mixed / neutral"
    return {
        "label": label,
        "score": round(score, 2),
        "n_positive": n_pos,
        "n_negative": n_neg,
        # De-dup but keep order — the audit trail for the needle.
        "positive_terms": sorted(set(pos_hits)),
        "negative_terms": sorted(set(neg_hits)),
    }


def live_sentiment_snapshot() -> Dict[str, Any]:
    """One-shot: fetch + score. Returns ok=False (never raises) on failure
    so the HTTP route can stay a thin pass-through."""
    try:
        headlines = fetch_live_headlines()
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "error": (
                "Live fetch unavailable "
                f"({type(exc).__name__}). This install may not have "
                "outbound network access — the corpus-derived market "
                "read on the page remains the best available view."
            ),
        }
    out = score_sentiment(headlines)
    out.update({
        "ok": True,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "n_headlines": len(headlines),
        "headlines": headlines[:10],
        "source": "Google News RSS (public) · keyword lexicon",
    })
    return out
