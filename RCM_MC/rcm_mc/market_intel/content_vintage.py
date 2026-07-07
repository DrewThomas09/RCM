"""Vintage / staleness accessor for the curated market-intel YAMLs.

Every content file in this package carries ``last_reviewed`` and
``source_urls`` headers, but no loader exposed them — pages rendered
generic "verify against the current release" text with no date, and the
fixtures aged silently (the PE-transaction library's newest deal fixes
the sponsor-activity window, so an un-refreshed file eventually reads
as "no sponsor activity" — a stale fixture presented as a market fact).

This mirrors ``rcm_mc.diligence.regulatory.regulatory_content_freshness_report``
so one assertion can lock the curation cadence across all seven YAMLs.
Default ``max_age_days`` is 120: the fixtures declare monthly/quarterly
refresh cadences, so a file two quarters past review is stale for any
partner-facing number.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

CONTENT_DIR = Path(__file__).parent / "content"

#: Every curated YAML the package ships. Names are file stems.
CONTENT_FILES = (
    "labor_market",
    "ma_penetration",
    "news_feed",
    "pe_transactions",
    "public_comps",
    "rate_updates",
    "transaction_multiples",
)

#: Two quarters — see module docstring.
DEFAULT_MAX_AGE_DAYS = 120


def content_vintage(
    name: str,
    max_age_days: int = DEFAULT_MAX_AGE_DAYS,
    today: Optional[date] = None,
) -> Dict[str, Any]:
    """Return ``{last_reviewed, source_urls, age_days, stale, error}``
    for one content file.

    Fails closed: a missing file, missing/malformed ``last_reviewed``,
    or unparseable YAML reports ``stale=True`` with an ``error`` string
    rather than pretending freshness. ``today`` is injectable so the
    staleness clock is testable; the default is the UTC date (naive
    ``date.today()`` drifts with the box's timezone).
    """
    today = today or datetime.now(timezone.utc).date()
    out: Dict[str, Any] = {
        "name": name,
        "last_reviewed": None,
        "source_urls": [],
        "age_days": None,
        "stale": True,
        "error": None,
    }
    path = CONTENT_DIR / f"{name}.yaml"
    if not path.exists():
        out["error"] = "missing"
        return out
    try:
        data = yaml.safe_load(path.read_text("utf-8")) or {}
    except yaml.YAMLError as exc:
        out["error"] = str(exc)
        return out
    out["source_urls"] = list(data.get("source_urls") or [])
    lr = data.get("last_reviewed")
    if not lr:
        out["error"] = "no last_reviewed field"
        return out
    try:
        reviewed = date.fromisoformat(str(lr))
    except ValueError:
        out["last_reviewed"] = str(lr)
        out["error"] = "malformed last_reviewed"
        return out
    age = (today - reviewed).days
    out["last_reviewed"] = str(lr)
    out["age_days"] = age
    out["stale"] = age > max_age_days
    return out


def content_freshness_report(
    max_age_days: int = DEFAULT_MAX_AGE_DAYS,
    today: Optional[date] = None,
) -> Dict[str, Dict[str, Any]]:
    """``{name: content_vintage(name)}`` for every shipped YAML."""
    return {
        name: content_vintage(name, max_age_days=max_age_days, today=today)
        for name in CONTENT_FILES
    }
