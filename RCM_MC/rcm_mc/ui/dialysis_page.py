"""Dialysis screener + profile — /dialysis (Dialysis vertical).

Reuses the shared sector scaffolds over the vendored CMS Dialysis Facility
Compare data. Medicare-certified dialysis facilities only; public five-star +
risk-adjusted outcome rates — not commercial revenue, not an investment
recommendation. Outcome rates (mortality/hospitalization/readmission/
transfusion) are LOWER-is-better risk-adjusted estimates; they appear in the
screener table as raw values but are deliberately kept out of the profile's
"higher-percentile-is-better" metric table to avoid an inverted read.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

from ..data.dialysis import (
    dialysis_providers_for_state,
    load_dialysis_providers,
    load_dialysis_quality,
    load_dialysis_summary_by_state,
)
from .sector_provider_profile import render_sector_provider_profile
from .sector_screener import render_sector_screener

_PROVENANCE = ("CMS Dialysis Facility Compare — Listing by Facility "
               "(DFC_FACILITY)")
_LIMITATIONS = [
    "Medicare-certified dialysis facilities only.",
    "Public five-star + risk-adjusted outcome rates — not commercial revenue "
    "or payer mix.",
    "Outcome rates (mortality / hospitalization / readmission / transfusion) "
    "are LOWER-is-better risk-adjusted estimates with confidence intervals; "
    "read them as risk signals, not a standalone quality verdict.",
]


def _e(s: Any) -> str:
    return _html.escape("" if s is None else str(s))


def _q(q: Dict[str, Optional[float]], key: str, suffix: str = "") -> str:
    v = q.get(key)
    return f"{v:g}{suffix}" if v is not None else "—"


_TABLE_COLS = [
    ("Facility", lambda p, q: f'<a href="/dialysis/{_e(p.ccn)}" class="ck-link"><strong>{_e(p.facility_name)}</strong></a>'),
    ("CCN", lambda p, q: f'<a href="/dialysis/{_e(p.ccn)}" class="ck-link num">{_e(p.ccn)}</a>'),
    ("County", lambda p, q: _e(p.county) or "—"),
    ("Ownership", lambda p, q: _e(p.ownership) or "—"),
    ("5-star", lambda p, q: f'<span class="num">{_q(q, "five_star")}</span>'),
    ("Mortality", lambda p, q: f'<span class="num">{_q(q, "mortality_rate")}</span>'),
    ("Hosp. rate", lambda p, q: f'<span class="num">{_q(q, "hospitalization_rate")}</span>'),
    ("Stations", lambda p, q: f'<span class="num">{p.dialysis_stations if p.dialysis_stations is not None else "—"}</span>'),
]


def render_dialysis(qs: Optional[Dict[str, List[str]]] = None) -> str:
    return render_sector_screener(
        qs=qs,
        route="/dialysis",
        title="Dialysis Facilities",
        eyebrow="DIALYSIS",
        description=(
            "Medicare-certified dialysis facilities, with publicly reported "
            "CMS overall five-star ratings, dialysis-station counts, "
            "ownership/chain, modality offerings, and risk-adjusted outcome "
            "rates (mortality, hospitalization, readmission, transfusion). "
            "Use as market and provider diligence context — not a final "
            "investment recommendation."
        ),
        provenance=_PROVENANCE,
        limitations=_LIMITATIONS,
        providers=load_dialysis_providers(),
        quality=load_dialysis_quality(),
        summary=load_dialysis_summary_by_state(),
        count_key="facilities",
        count_label="Facilities",
        avg_key="avg_five_star",
        avg_label="five-star",
        name_attr="facility_name",
        providers_for_state=dialysis_providers_for_state,
        table_cols=_TABLE_COLS,
        locality_attr="county",
        locality_label="County",
        headline_metric_key="five_star",
        headline_suffix="",
    )


def render_dialysis_profile(ccn: str) -> Optional[str]:
    """Single-facility deep dive — /dialysis/<ccn>. None if CCN unknown."""
    return render_sector_provider_profile(
        ccn=ccn,
        route="/dialysis",
        eyebrow="DIALYSIS FACILITY",
        kind_singular="facility",
        providers=load_dialysis_providers(),
        quality=load_dialysis_quality(),
        name_attr="facility_name",
        identity_rows=lambda p: [
            ("Address", ", ".join(b for b in (p.address, p.city, p.state, p.zip) if b)),
            ("County", p.county),
            ("Ownership", p.ownership),
            ("Chain", (p.chain_org or "—") if (p.chain_owned or "").upper().startswith("Y") else "Independent"),
            ("Dialysis stations", str(p.dialysis_stations) if p.dialysis_stations is not None else ""),
            ("In-center hemodialysis", p.offers_in_center_hd or "—"),
            ("Peritoneal dialysis", p.offers_peritoneal or "—"),
            ("Home hemodialysis training", p.offers_home_hd or "—"),
            ("Medicare-certified", p.certification_date),
            ("Source", p.source),
            ("Snapshot", p.source_date),
        ],
        headline=("Overall 5-star rating", "five_star", ""),
        # Higher-is-better only: the percentile column frames "higher = better".
        # The risk-adjusted outcome rates are LOWER-is-better, so they're shown
        # in the screener table (raw) but excluded from the percentile table.
        metrics=[
            ("Overall 5-star rating", "five_star", ""),
        ],
        avg_label="five-star",
        higher_is_better=True,
        provenance=_PROVENANCE,
        limitations=_LIMITATIONS,
        locality_attr="county",
        locality_label="County",
    )
