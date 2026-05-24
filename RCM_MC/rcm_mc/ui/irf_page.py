"""IRF screener + profile — /inpatient-rehab (IRF vertical).

Reuses the shared sector scaffolds over the vendored CMS IRF Compare data.
Medicare-certified IRFs only (~1.2k — small universe, benchmark with care).
Headline = discharge-to-community risk-standardized rate (higher better).
Readmission + MSPB are lower-is-better and stay out of the percentile table.
Public quality only — not commercial revenue, not an investment recommendation.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

from ..data.irf import (
    irf_providers_for_state, load_irf_providers, load_irf_quality,
    load_irf_summary_by_state,
)
from .sector_provider_profile import render_sector_provider_profile
from .sector_screener import render_sector_screener

_PROVENANCE = ("CMS Inpatient Rehabilitation Facility Compare — General "
               "Information + Provider Data")
_LIMITATIONS = [
    "Medicare-certified inpatient rehabilitation facilities only (~1,200 — a "
    "small national universe; per-state samples can be very small).",
    "Public quality measures only — not commercial revenue or payer mix.",
    "Readmission (PPR) and Medicare-spending-per-beneficiary are LOWER-is-"
    "better, risk-standardized estimates; read as risk signals, not verdicts.",
]


def _e(s): return _html.escape("" if s is None else str(s))
def _q(q, k, suf=""):
    v = q.get(k); return f"{v:g}{suf}" if v is not None else "—"


_TABLE_COLS = [
    ("Facility", lambda p, q: f'<a href="/inpatient-rehab/{_e(p.ccn)}" class="ck-link"><strong>{_e(p.provider_name)}</strong></a>'),
    ("CCN", lambda p, q: f'<a href="/inpatient-rehab/{_e(p.ccn)}" class="ck-link num">{_e(p.ccn)}</a>'),
    ("County", lambda p, q: _e(p.county) or "—"),
    ("Ownership", lambda p, q: _e(p.ownership) or "—"),
    ("Disch→community", lambda p, q: f'<span class="num">{_q(q, "dtc_rs_rate", "%")}</span>'),
    ("Readmission", lambda p, q: f'<span class="num">{_q(q, "readmission_rsrr", "%")}</span>'),
    ("MSPB", lambda p, q: f'<span class="num">{_q(q, "mspb_score")}</span>'),
]


def render_irf(qs: Optional[Dict[str, List[str]]] = None) -> str:
    return render_sector_screener(
        qs=qs, route="/inpatient-rehab", title="Inpatient Rehab (IRF)",
        eyebrow="INPATIENT REHAB / IRF",
        description=(
            "Medicare-certified inpatient rehabilitation facilities, with "
            "publicly reported CMS measures — discharge to community "
            "(risk-standardized), potentially-preventable readmissions, and "
            "Medicare spending per beneficiary. Use as market and provider "
            "diligence context — not a final investment recommendation."
        ),
        provenance=_PROVENANCE, limitations=_LIMITATIONS,
        providers=load_irf_providers(), quality=load_irf_quality(),
        summary=load_irf_summary_by_state(),
        count_key="facilities", count_label="Facilities",
        avg_key="avg_dtc", avg_label="discharge-to-community %",
        name_attr="provider_name",
        providers_for_state=irf_providers_for_state, table_cols=_TABLE_COLS,
        locality_attr="county", locality_label="County",
        headline_metric_key="dtc_rs_rate", headline_suffix="%",
    )


def render_irf_profile(ccn: str) -> Optional[str]:
    return render_sector_provider_profile(
        ccn=ccn, route="/inpatient-rehab", eyebrow="INPATIENT REHAB FACILITY",
        kind_singular="facility",
        providers=load_irf_providers(), quality=load_irf_quality(),
        name_attr="provider_name",
        identity_rows=lambda p: [
            ("Address", ", ".join(b for b in (p.address, p.city, p.state, p.zip) if b)),
            ("County", p.county), ("Ownership", p.ownership),
            ("Medicare-certified", p.certification_date),
            ("Source", p.source), ("Snapshot", p.source_date),
        ],
        headline=("Discharge to community (risk-std)", "dtc_rs_rate", "%"),
        # Higher-is-better only. Readmission + MSPB are lower-is-better →
        # shown in the screener table (raw) but kept out of the percentile.
        metrics=[("Discharge to community (risk-std)", "dtc_rs_rate", "%")],
        avg_label="discharge-to-community %", higher_is_better=True,
        provenance=_PROVENANCE, limitations=_LIMITATIONS,
        locality_attr="county", locality_label="County",
    )
