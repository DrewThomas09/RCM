"""Hospice screener — /hospice (Sector Intelligence Phase 2B)."""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

from ..data.hospice import (
    hospice_providers_for_state,
    load_hospice_providers,
    load_hospice_quality,
    load_hospice_summary_by_state,
)
from .sector_provider_profile import render_sector_provider_profile
from .sector_screener import render_sector_screener

_PROVENANCE = ("CMS Provider Data Catalog — Hospice General Information "
               "(yc9t-dgbk) + Hospice Provider Data (252m-zfp9)")
_LIMITATIONS = [
    "Medicare-certified hospices only.",
    "Public quality data, not target-company financials.",
    "CAHPS hospice-survey scores and length-of-stay / live-discharge "
    "economics are not in these public quality files.",
]


def _e(s: Any) -> str:
    return _html.escape("" if s is None else str(s))


def _q(q: Dict[str, Optional[float]], key: str, suffix: str = "") -> str:
    v = q.get(key)
    return f"{v:g}{suffix}" if v is not None else "—"


_TABLE_COLS = [
    ("Hospice", lambda p, q: f'<a href="/hospice/{_e(p.ccn)}" class="ck-link"><strong>{_e(p.facility_name)}</strong></a>'),
    ("CCN", lambda p, q: f'<a href="/hospice/{_e(p.ccn)}" class="ck-link num">{_e(p.ccn)}</a>'),
    ("County", lambda p, q: _e(p.county) or "—"),
    ("Ownership", lambda p, q: _e(p.ownership) or "—"),
    ("Care Index", lambda p, q: f'<span class="num">{_q(q, "care_index_overall")}</span>'),
    ("Composite process", lambda p, q: f'<span class="num">{_q(q, "composite_process", "%")}</span>'),
    ("Visits last days", lambda p, q: f'<span class="num">{_q(q, "visits_last_days", "%")}</span>'),
]


def render_hospice(qs: Optional[Dict[str, List[str]]] = None) -> str:
    return render_sector_screener(
        qs=qs,
        route="/hospice",
        title="Hospice Providers",
        eyebrow="HOSPICE",
        description=(
            "Medicare-certified hospices, with publicly reported HIS quality "
            "(Hospice Care Index, composite process measure, visits in the "
            "last days of life, screening). Use as market and provider "
            "diligence context — not a final investment recommendation."
        ),
        provenance=_PROVENANCE,
        limitations=_LIMITATIONS,
        providers=load_hospice_providers(),
        quality=load_hospice_quality(),
        summary=load_hospice_summary_by_state(),
        count_key="hospices",
        count_label="Hospices",
        avg_key="avg_care_index",
        avg_label="Care Index",
        name_attr="facility_name",
        providers_for_state=hospice_providers_for_state,
        table_cols=_TABLE_COLS,
    )


def render_hospice_profile(ccn: str) -> Optional[str]:
    """Single-hospice deep dive — /hospice/<ccn>. None if CCN unknown."""
    return render_sector_provider_profile(
        ccn=ccn,
        route="/hospice",
        eyebrow="HOSPICE PROVIDER",
        kind_singular="hospice",
        providers=load_hospice_providers(),
        quality=load_hospice_quality(),
        name_attr="facility_name",
        identity_rows=lambda p: [
            ("Address", ", ".join(b for b in (p.address, p.city, p.state, p.zip) if b)),
            ("County", p.county),
            ("Ownership", p.ownership),
            ("Medicare-certified", p.certification_date),
            ("Source", p.source),
            ("Snapshot", p.source_date),
        ],
        headline=("Hospice Care Index", "care_index_overall", ""),
        metrics=[
            ("Hospice Care Index", "care_index_overall", ""),
            ("Composite process measure", "composite_process", "%"),
            ("Visits in last days of life", "visits_last_days", "%"),
            ("Pain screening", "pain_screening", "%"),
            ("Treatment preferences", "treatment_preferences", "%"),
            ("Beliefs / values addressed", "beliefs_values", "%"),
        ],
        avg_label="Care Index",
        higher_is_better=True,
        provenance=_PROVENANCE,
        limitations=_LIMITATIONS,
    )
