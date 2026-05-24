"""SNF / Nursing Home screener + profile — /nursing-homes (SNF vertical).

Reuses the shared sector scaffolds (screener, provider profile, market
intelligence) over the vendored CMS Nursing Home Care Compare — Provider
Information data. Medicare/Medicaid-certified nursing homes only; public
quality/staffing/survey data — not commercial revenue (penalty "fines" are
regulatory, not income), not an investment recommendation.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

from ..data.snf import (
    load_snf_providers,
    load_snf_quality,
    load_snf_summary_by_state,
    snf_providers_for_state,
)
from .sector_provider_profile import render_sector_provider_profile
from .sector_screener import render_sector_screener

_PROVENANCE = ("CMS Nursing Home Care Compare — Provider Information "
               "(NH_ProviderInfo)")
_LIMITATIONS = [
    "Medicare/Medicaid-certified nursing homes only — private-pay-only "
    "facilities are not represented.",
    "Public quality / staffing / survey data — not commercial revenue or "
    "payer mix. “Total fines” is a regulatory penalty figure, not income.",
    "Star ratings are CMS's methodology, refreshed monthly; the health-"
    "inspection component is largely state-survey-driven and can lag.",
]


def _e(s: Any) -> str:
    return _html.escape("" if s is None else str(s))


def _q(q: Dict[str, Optional[float]], key: str, suffix: str = "") -> str:
    v = q.get(key)
    return f"{v:g}{suffix}" if v is not None else "—"


_TABLE_COLS = [
    ("Facility", lambda p, q: f'<a href="/nursing-homes/{_e(p.ccn)}" class="ck-link"><strong>{_e(p.provider_name)}</strong></a>'),
    ("CCN", lambda p, q: f'<a href="/nursing-homes/{_e(p.ccn)}" class="ck-link num">{_e(p.ccn)}</a>'),
    ("County", lambda p, q: _e(p.county) or "—"),
    ("Ownership", lambda p, q: _e(p.ownership) or "—"),
    ("Overall ★", lambda p, q: f'<span class="num">{_q(q, "overall_rating")}</span>'),
    ("Health insp ★", lambda p, q: f'<span class="num">{_q(q, "health_inspection_rating")}</span>'),
    ("Staffing ★", lambda p, q: f'<span class="num">{_q(q, "staffing_rating")}</span>'),
    ("Beds", lambda p, q: f'<span class="num">{p.certified_beds if p.certified_beds is not None else "—"}</span>'),
]


def render_snf(qs: Optional[Dict[str, List[str]]] = None) -> str:
    return render_sector_screener(
        qs=qs,
        route="/nursing-homes",
        title="Nursing Homes (SNF)",
        eyebrow="SNF / NURSING HOME",
        description=(
            "Medicare/Medicaid-certified nursing homes (skilled nursing "
            "facilities), with publicly reported CMS five-star ratings "
            "(overall, health inspection, staffing, quality measures), "
            "staffing hours, certified beds, Special Focus status, and the "
            "enforcement-penalty summary. Use as market and provider "
            "diligence context — not a final investment recommendation."
        ),
        provenance=_PROVENANCE,
        limitations=_LIMITATIONS,
        providers=load_snf_providers(),
        quality=load_snf_quality(),
        summary=load_snf_summary_by_state(),
        count_key="facilities",
        count_label="Facilities",
        avg_key="avg_overall_rating",
        avg_label="overall rating",
        name_attr="provider_name",
        providers_for_state=snf_providers_for_state,
        table_cols=_TABLE_COLS,
        locality_attr="county",
        locality_label="County",
        headline_metric_key="overall_rating",
        headline_suffix="",
    )


def render_snf_profile(ccn: str) -> Optional[str]:
    """Single-facility deep dive — /nursing-homes/<ccn>. None if CCN unknown."""
    return render_sector_provider_profile(
        ccn=ccn,
        route="/nursing-homes",
        eyebrow="NURSING HOME (SNF)",
        kind_singular="facility",
        providers=load_snf_providers(),
        quality=load_snf_quality(),
        name_attr="provider_name",
        identity_rows=lambda p: [
            ("Address", ", ".join(b for b in (p.address, p.city, p.state, p.zip) if b)),
            ("County", p.county),
            ("Ownership", p.ownership),
            ("Certified beds", str(p.certified_beds) if p.certified_beds is not None else ""),
            ("Avg residents/day", f"{p.avg_residents_per_day:g}" if p.avg_residents_per_day is not None else ""),
            ("Special Focus status", p.sff_status or "—"),
            ("Abuse icon flag", p.abuse_icon or "—"),
            ("Ownership changed (12mo)", p.changed_ownership_12mo or "—"),
            ("Medicare/Medicaid since", p.certification_date),
            ("Source", p.source),
            ("Snapshot", p.source_date),
        ],
        headline=("Overall 5-star rating", "overall_rating", ""),
        # Higher-is-better metrics only — the profile's percentile column
        # frames "higher percentile = better vs peers", which is valid for
        # ratings + staffing hours. Lower-is-better signals (fines, payment
        # denials, turnover) are intentionally NOT shown with a percentile
        # to avoid an inverted/misleading read; they're vendored in
        # snf_quality.csv for a future enforcement-detail view.
        metrics=[
            ("Overall 5-star rating", "overall_rating", ""),
            ("Health-inspection rating", "health_inspection_rating", ""),
            ("Staffing rating", "staffing_rating", ""),
            ("Quality-measure (QM) rating", "qm_rating", ""),
            ("RN hours / resident / day", "rn_hprd", ""),
            ("Total nurse hours / resident / day", "total_nurse_hprd", ""),
        ],
        avg_label="overall rating",
        higher_is_better=True,
        provenance=_PROVENANCE,
        limitations=_LIMITATIONS,
        locality_attr="county",
        locality_label="County",
    )
