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
from .sector_screener import render_sector_screener


def _e(s: Any) -> str:
    return _html.escape("" if s is None else str(s))


def _q(q: Dict[str, Optional[float]], key: str, suffix: str = "") -> str:
    v = q.get(key)
    return f"{v:g}{suffix}" if v is not None else "—"


_TABLE_COLS = [
    ("Agency", lambda p, q: f'<strong>{_e(p.provider_name)}</strong>'),
    ("CCN", lambda p, q: f'<span class="num">{_e(p.ccn)}</span>'),
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
        provenance="CMS Provider Data Catalog — Home Health Care Agencies (6jpm-sxkc)",
        limitations=[
            "Medicare-certified agencies only — commercial / private-pay home "
            "care is not represented.",
            "Public quality data, not target-company financials.",
            "Claims-based acute-care-hospitalization / ED-use measures are a "
            "separate CMS dataset, not shown here.",
        ],
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
