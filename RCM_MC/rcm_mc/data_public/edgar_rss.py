"""SEC EDGAR Atom-feed adapter for healthcare public-comp filings.

PEDESK Phase 2 (Week 2, Data Ingestion) — Public Comps fix.

The Public Comps page on pedesk.app shipped with stale, hardcoded
earnings data (HCA reported_on=2026-01-29 displayed as the latest
filing while real-life Q1 2026 reports landed ~2026-04-24). This
module wires the SEC EDGAR Atom RSS feed for HCA / THC / CYH so the
page can refresh itself against the canonical filing source.

The fetch is cached on disk (24-hour TTL) and tolerant of network
failure: when the feed is unreachable, we fall back to the YAML data
without raising. EDGAR rate-limits aggressively when accessed without
a User-Agent identifying the requester, so we always send one.

Atom feed URL pattern:
    https://www.sec.gov/cgi-bin/browse-edgar
        ?action=getcompany&CIK={cik}&type={form_type}&dateb=&owner=include
        &count=40&output=atom

Form types of interest:
    10-K   — annual report
    10-Q   — quarterly report
    8-K    — current report (earnings, material events)

Document: https://www.sec.gov/edgar/searchedgar/companysearch
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# CIK numbers (Central Index Key) for the three healthcare operators
# the user explicitly named. CIKs are stable across filings, so this
# mapping is a constant. Sourced from each company's most recent
# cover page on EDGAR.
CIK_MAP: Dict[str, str] = {
    "HCA": "0000860730",   # HCA Healthcare, Inc.
    "THC": "0000070318",   # Tenet Healthcare Corporation
    "CYH": "0001108109",   # Community Health Systems, Inc.
}

EDGAR_USER_AGENT = (
    "PEDESK Healthcare PE Diligence (research) "
    "ops@pedesk.app"
)
EDGAR_BASE = "https://www.sec.gov/cgi-bin/browse-edgar"
DEFAULT_CACHE_TTL_SECS = 86_400  # 24 hours


@dataclass
class EdgarFiling:
    """Single 10-K/10-Q/8-K filing row from the EDGAR Atom feed."""
    ticker: str
    cik: str
    form_type: str
    filed_on: str           # ISO date the filing was accepted by SEC
    period_of_report: Optional[str] = None  # ISO date of fiscal period end
    accession_number: Optional[str] = None
    title: Optional[str] = None
    url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


# ---------------------------------------------------------------------------
# Feed fetcher
# ---------------------------------------------------------------------------


def _cache_dir() -> Path:
    base = os.environ.get(
        "RCM_MC_EDGAR_CACHE",
        os.path.expanduser("~/.rcm_mc/edgar"),
    )
    p = Path(base)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _cached_fetch(url: str, ttl: int = DEFAULT_CACHE_TTL_SECS) -> Optional[str]:
    """GET ``url`` with EDGAR-required user-agent, caching the body on disk.

    Returns the response body text, or None on network failure (so the
    caller can fall through to the bundled YAML without raising and
    crashing the page).
    """
    safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", url)[:200]
    cache_path = _cache_dir() / safe_name
    if cache_path.exists() and (time.time() - cache_path.stat().st_mtime) < ttl:
        try:
            return cache_path.read_text("utf-8")
        except OSError:
            pass
    req = urllib.request.Request(url, headers={"User-Agent": EDGAR_USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, OSError):
        # On transient failure, return any stale cache we have rather
        # than crashing the page; the staleness banner is the partner's
        # signal that the feed is degraded.
        if cache_path.exists():
            try:
                return cache_path.read_text("utf-8")
            except OSError:
                return None
        return None
    try:
        cache_path.write_text(body, encoding="utf-8")
    except OSError:
        pass
    return body


# ---------------------------------------------------------------------------
# Atom XML parsing — narrow regex over the small, well-known shape.
# ---------------------------------------------------------------------------
#
# The EDGAR Atom feed is tiny (40 entries max) and its tag layout is
# stable. We avoid the lxml/feedparser dependency and use a regex
# walker. Each <entry> looks like:
#
#   <entry>
#     <title>10-K - HCA Healthcare, Inc.</title>
#     <link href="https://www.sec.gov/Archives/edgar/data/.../...-index.htm"/>
#     <updated>2026-01-29T16:32:00-05:00</updated>
#     <category term="10-K" />
#     <content>
#       <accession-number>0000860730-26-000007</accession-number>
#       <filing-date>2026-01-29</filing-date>
#       <period-of-report>2025-12-31</period-of-report>
#       <form-type>10-K</form-type>
#     </content>
#   </entry>

_ENTRY_RE = re.compile(r"<entry[^>]*>(.*?)</entry>", re.DOTALL | re.IGNORECASE)
_TAG_RE = re.compile(
    r"<(filing-date|period-of-report|form-type|accession-number)>([^<]+)</",
    re.IGNORECASE,
)
_TITLE_RE = re.compile(r"<title[^>]*>([^<]+)</title>", re.IGNORECASE)
_LINK_RE = re.compile(r'<link[^>]*href="([^"]+)"', re.IGNORECASE)


def _parse_atom(body: str, ticker: str, cik: str) -> List[EdgarFiling]:
    out: List[EdgarFiling] = []
    for entry_block in _ENTRY_RE.findall(body):
        tags = {k.lower(): v.strip() for k, v in _TAG_RE.findall(entry_block)}
        title_m = _TITLE_RE.search(entry_block)
        link_m = _LINK_RE.search(entry_block)
        out.append(EdgarFiling(
            ticker=ticker,
            cik=cik,
            form_type=tags.get("form-type", "").strip().upper(),
            filed_on=tags.get("filing-date", ""),
            period_of_report=tags.get("period-of-report") or None,
            accession_number=tags.get("accession-number") or None,
            title=title_m.group(1).strip() if title_m else None,
            url=link_m.group(1).strip() if link_m else None,
        ))
    return [f for f in out if f.filed_on]


def fetch_filings(
    ticker: str,
    form_types: Optional[List[str]] = None,
    *,
    count: int = 40,
    ttl: int = DEFAULT_CACHE_TTL_SECS,
) -> List[EdgarFiling]:
    """Return recent filings for ``ticker`` from the SEC EDGAR Atom feed.

    ``form_types`` defaults to ``["10-K", "10-Q"]``. Returns an empty
    list when the ticker isn't in :data:`CIK_MAP` or when the network
    is unreachable. Never raises.
    """
    cik = CIK_MAP.get(str(ticker).upper())
    if not cik:
        return []
    forms = [str(f).upper() for f in (form_types or ["10-K", "10-Q"])]
    out: List[EdgarFiling] = []
    for ft in forms:
        url = (
            f"{EDGAR_BASE}?action=getcompany&CIK={cik}"
            f"&type={ft}&dateb=&owner=include&count={int(count)}"
            "&output=atom"
        )
        body = _cached_fetch(url, ttl=ttl)
        if not body:
            continue
        out.extend(_parse_atom(body, ticker.upper(), cik))
    out.sort(key=lambda f: f.filed_on, reverse=True)
    return out


def latest_earnings_filing(
    ticker: str,
    *,
    ttl: int = DEFAULT_CACHE_TTL_SECS,
) -> Optional[EdgarFiling]:
    """Return the most recent 10-K or 10-Q for ``ticker``, or None.

    Convenience wrapper used by the Public Comps earnings calendar
    when refreshing the "X days ago" timestamp against EDGAR rather
    than the bundled YAML.
    """
    filings = fetch_filings(ticker, form_types=["10-K", "10-Q"], ttl=ttl)
    return filings[0] if filings else None


# ---------------------------------------------------------------------------
# Days-since helpers
# ---------------------------------------------------------------------------
#
# The bug the partner saw: market_intel_page rendered "{abs(days)}d
# ago (reported)" using ``days = next_expected - today``, which is
# days-since-NEXT-expected, not days-since-actually-reported. For a
# stale Q4 2025 row dated 2026-01-29 with today=2026-05-06 the
# function returned -7 (next_expected = +90d from reported = 2026-04-29,
# days = -7 → "7d ago (reported)") when the truthful answer is
# "97d ago (reported)". Calling code now uses ``days_since_reported``
# directly off the actual filing date.


def days_since_reported(reported_on: Optional[str], *, today: Optional[datetime] = None) -> Optional[int]:
    """Return integer days between today and ``reported_on``, or None.

    Negative result means the report is in the future (impossible
    for an actual filing — typically signals a data-entry error).
    """
    if not reported_on:
        return None
    try:
        dt = datetime.strptime(str(reported_on)[:10], "%Y-%m-%d")
    except (ValueError, TypeError):
        return None
    now = today or datetime.now(timezone.utc).replace(tzinfo=None)
    if hasattr(now, "tzinfo") and now.tzinfo is not None:
        now = now.replace(tzinfo=None)
    return (now - dt).days


# ---------------------------------------------------------------------------
# Sanity gate for distressed-REIT EBITDA multiples
# ---------------------------------------------------------------------------
#
# MPW (Medical Properties Trust) is a healthcare REIT in a debt
# restructuring. Its disclosed market-cap-implied EV/EBITDA (24.36x
# in the bundled YAML) is implausible — REITs in distress with
# debt/EBITDA > 15x typically trade at low single-digit multiples
# because the equity is being valued out of the money. The likely
# cause is a stale EBITDA figure (pre-restructuring) that didn't get
# rolled forward. Rather than block render on data quality, flag the
# anomaly with a sane ceiling so the comp set isn't visually skewed.

REIT_DISTRESS_DEBT_RATIO = 10.0   # debt/EBITDA threshold for "distressed"
REIT_DISTRESS_EV_EBITDA_CEILING = 12.0


def cap_distressed_reit_multiple(
    ev_ebitda: Optional[float],
    debt_to_ebitda: Optional[float],
    category: Optional[str] = None,
) -> Optional[float]:
    """Flag-and-cap implausibly high EV/EBITDA on distressed healthcare REITs.

    Returns the input multiple unchanged unless ``category`` looks
    like a healthcare REIT *and* ``debt_to_ebitda`` is above the
    distress threshold *and* the disclosed multiple is above the
    distressed-REIT ceiling. In that case, returns the ceiling so the
    comp scatter and category bands aren't dragged by a stale EBITDA
    snapshot that hasn't rolled forward through restructuring.

    The intent is *not* to silently overwrite truthy data — callers
    that want the raw value should still use the original field.
    This is the value used by the heatmap / band aggregations.
    """
    if ev_ebitda is None:
        return ev_ebitda
    cat = (category or "").upper()
    if "REIT" not in cat:
        return ev_ebitda
    try:
        m = float(ev_ebitda)
        d = float(debt_to_ebitda) if debt_to_ebitda is not None else 0.0
    except (TypeError, ValueError):
        return ev_ebitda
    if d >= REIT_DISTRESS_DEBT_RATIO and m > REIT_DISTRESS_EV_EBITDA_CEILING:
        return REIT_DISTRESS_EV_EBITDA_CEILING
    return ev_ebitda


# ---------------------------------------------------------------------------
# Sentiment correction
# ---------------------------------------------------------------------------
#
# Curated news items in news_feed.yaml are tagged with a sentiment
# label. The rule the user surfaced: "credit tightening" can never be
# a "positive" headline at the macro level, even if the specific
# story is about resilience (e.g., "DSO multiples held despite credit
# tightening" — the qualifier is broadly negative for healthcare PE).
# Rather than rewrite the YAML by hand on every edit, we apply a
# load-time override that downgrades positive → mixed when negative
# context phrases are present.

_NEGATIVE_CONTEXT_PHRASES = (
    "credit tightening",
    "credit tighten",
    "downgrade",
    "downgraded",
    "covenant breach",
    "going concern",
    "bankruptcy",
    "chapter 11",
    "restructuring",
    "default",
    "liquidity crisis",
    "ratings downgrade",
)


def correct_sentiment(
    sentiment: str,
    *,
    title: str = "",
    summary: str = "",
) -> str:
    """Downgrade a ``positive`` label to ``mixed`` when the headline or
    summary contains a strongly negative macro phrase.

    Leaves other labels alone. This is a one-way correction: it never
    upgrades a sentiment, only down-shifts an over-optimistic
    classification toward neutral / mixed.
    """
    s = (sentiment or "neutral").lower().strip()
    if s != "positive":
        return s
    haystack = f"{title} {summary}".lower()
    for phrase in _NEGATIVE_CONTEXT_PHRASES:
        if phrase in haystack:
            return "mixed"
    return s


# ---------------------------------------------------------------------------
# Convenience: serialise an EdgarFiling dump for ad-hoc CLI use
# ---------------------------------------------------------------------------


def filings_as_json(ticker: str) -> str:
    return json.dumps(
        [f.to_dict() for f in fetch_filings(ticker)],
        indent=2,
    )
