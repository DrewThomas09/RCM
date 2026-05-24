"""Home Health screener — /home-health (Sector Intelligence Phase 2B)."""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

from ..data.home_health import (
    home_health_providers_for_state,
    load_home_health_providers,
    load_home_health_quality,
    load_home_health_summary_by_state,
)
from .sector_provider_profile import render_sector_provider_profile
from .sector_screener import render_sector_screener

_PROVENANCE = "CMS Provider Data Catalog — Home Health Care Agencies (6jpm-sxkc)"
_LIMITATIONS = [
    "Medicare-certified agencies only — commercial / private-pay home "
    "care is not represented.",
    "Public quality data, not target-company financials.",
    "Claims-based acute-care-hospitalization / ED-use measures are a "
    "separate CMS dataset, not shown here.",
]


def _e(s: Any) -> str:
    return _html.escape("" if s is None else str(s))


def _q(q: Dict[str, Optional[float]], key: str, suffix: str = "") -> str:
    v = q.get(key)
    return f"{v:g}{suffix}" if v is not None else "—"


_TABLE_COLS = [
    ("Agency", lambda p, q: f'<a href="/home-health/{_e(p.ccn)}" class="ck-link"><strong>{_e(p.provider_name)}</strong></a>'),
    ("CCN", lambda p, q: f'<a href="/home-health/{_e(p.ccn)}" class="ck-link num">{_e(p.ccn)}</a>'),
    ("Ownership", lambda p, q: _e(p.ownership) or "—"),
    ("Star", lambda p, q: f'<span class="num">{_q(q, "star_rating")}</span>'),
    ("Timely care", lambda p, q: f'<span class="num">{_q(q, "timely_initiation_pct", "%")}</span>'),
    ("Improved ambulation", lambda p, q: f'<span class="num">{_q(q, "improve_ambulation_pct", "%")}</span>'),
    ("Discharge to community", lambda p, q: f'<span class="num">{_q(q, "discharge_to_community_rate")}</span>'),
]


def render_home_health(qs: Optional[Dict[str, List[str]]] = None) -> str:
    return render_sector_screener(
        qs=qs,
        route="/home-health",
        title="Home Health Agencies",
        eyebrow="HOME HEALTH",
        description=(
            "Medicare-certified home health agencies, with publicly reported "
            "quality (star rating, timely initiation of care, functional "
            "improvement, discharge to community). Use as market and provider "
            "diligence context — not a final investment recommendation."
        ),
        provenance=_PROVENANCE,
        limitations=_LIMITATIONS,
        providers=load_home_health_providers(),
        quality=load_home_health_quality(),
        summary=load_home_health_summary_by_state(),
        count_key="agencies",
        count_label="Agencies",
        avg_key="avg_star_rating",
        avg_label="star rating",
        name_attr="provider_name",
        providers_for_state=home_health_providers_for_state,
        table_cols=_TABLE_COLS,
    )


def render_home_health_profile(ccn: str) -> Optional[str]:
    """Single-agency deep dive — /home-health/<ccn>. None if CCN unknown."""
    return render_sector_provider_profile(
        ccn=ccn,
        route="/home-health",
        eyebrow="HOME HEALTH AGENCY",
        kind_singular="agency",
        providers=load_home_health_providers(),
        quality=load_home_health_quality(),
        name_attr="provider_name",
        identity_rows=lambda p: [
            ("Address", ", ".join(b for b in (p.address, p.city, p.state, p.zip) if b)),
            ("Ownership", p.ownership),
            ("Medicare-certified", p.certification_date),
            ("Source", p.source),
            ("Snapshot", p.source_date),
        ],
        headline=("Quality star rating", "star_rating", ""),
        metrics=[
            ("Quality star rating", "star_rating", ""),
            ("Timely initiation of care", "timely_initiation_pct", "%"),
            ("Improved in ambulation", "improve_ambulation_pct", "%"),
            ("Improved bed transfer", "improve_bed_transfer_pct", "%"),
            ("Improved bathing", "improve_bathing_pct", "%"),
            ("Discharge to community", "discharge_to_community_rate", ""),
        ],
        avg_label="star rating",
        higher_is_better=True,
        provenance=_PROVENANCE,
        limitations=_LIMITATIONS,
    )
