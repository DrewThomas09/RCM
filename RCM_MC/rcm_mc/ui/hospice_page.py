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
from .sector_screener import render_sector_screener


def _e(s: Any) -> str:
    return _html.escape("" if s is None else str(s))


def _q(q: Dict[str, Optional[float]], key: str, suffix: str = "") -> str:
    v = q.get(key)
    return f"{v:g}{suffix}" if v is not None else "—"


_TABLE_COLS = [
    ("Hospice", lambda p, q: f'<strong>{_e(p.facility_name)}</strong>'),
    ("CCN", lambda p, q: f'<span class="num">{_e(p.ccn)}</span>'),
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
        provenance=("CMS Provider Data Catalog — Hospice General Information "
                    "(yc9t-dgbk) + Hospice Provider Data (252m-zfp9)"),
        limitations=[
            "Medicare-certified hospices only.",
            "Public quality data, not target-company financials.",
            "CAHPS hospice-survey scores and length-of-stay / live-discharge "
            "economics are not in these public quality files.",
        ],
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
