"""Sector Intelligence landing — /sector-intelligence.

A read-only directory of the healthcare-services sectors PEdesk covers (or
plans to). Honest by construction: only **Hospitals** is Live today (it
links to real routes); every other sector is tagged **Roadmap** with its
phase + data-status, and carries NO link to a non-existent page. The build
plan lives in docs/PEDESK_SECTOR_INTELLIGENCE_ROADMAP.md.

No data loaders, no new datasets — this is a navigation/status surface.
"""
from __future__ import annotations

import html as _html
from typing import List, Optional, Tuple

from ._chartis_kit import chartis_shell, ck_page_title, ck_section_intro

# (sector, status, phase, data_status, [(link_label, route)])
# status: "live" (real routes) | "roadmap" (planned — no dead links)
_SECTORS: List[Tuple[str, str, str, str, List[Tuple[str, str]]]] = [
    ("Hospitals", "live", "Live",
     "Strong public data (HCRIS + Care Compare + geocoded points).",
     [("Market data", "/market-data/map"),
      ("Portfolio map", "/portfolio/map"),
      ("HCRIS X-Ray", "/diligence/hcris-xray")]),
    ("Home Health", "live", "Live",
     "Medicare-certified agencies + quality (star rating, improvement, DTC). "
     "CMS public data, not target financials.",
     [("Home Health screener", "/home-health")]),
    ("Hospice", "live", "Live",
     "Medicare-certified hospices + HIS quality (Care Index, composite, "
     "visits in last days). CMS public data, not target financials.",
     [("Hospice screener", "/hospice")]),
    ("Outpatient / ASC", "roadmap", "Phase 3",
     "Medicare proxy (Part B + OPPS + ASC quality). Commercial volume unobserved.",
     []),
    ("Physician Groups", "roadmap", "Phase 3",
     "Provider universe (NPPES) + Medicare Part B volume proxy.", []),
    ("Dental / DSO", "roadmap", "Phase 4",
     "Provider-supply only (NPPES + HPSA). Routine commercial dental revenue "
     "not observable in CMS data.", []),
    ("Infusion / DME", "roadmap", "Phase 5",
     "Supplier universe + drug/service-mix proxy (NPPES + DMEPOS + Part B "
     "J-codes). Not full revenue.", []),
    ("SNF / Nursing Home", "roadmap", "Phase 6",
     "Strong CMS data (Nursing Home Compare: ratings, staffing, inspections).",
     []),
    ("Dialysis", "roadmap", "Phase 6",
     "Strong CMS data (Dialysis Facility Compare: quality, ownership, geo).",
     []),
]

_STATUS_COLOR = {
    "live": "var(--sc-positive,#0a8a5f)",
    "roadmap": "var(--sc-text-faint,#8a8170)",
}


def _card(sector: str, status: str, phase: str, data_status: str,
          links: List[Tuple[str, str]]) -> str:
    color = _STATUS_COLOR.get(status, _STATUS_COLOR["roadmap"])
    tag = _html.escape(phase)
    links_html = ""
    if links:
        links_html = '<div style="margin-top:8px;display:flex;gap:12px;flex-wrap:wrap;">' + "".join(
            f'<a href="{_html.escape(r, quote=True)}" class="ck-link" '
            f'style="font-size:12px;">{_html.escape(lbl)} &rarr;</a>'
            for lbl, r in links
        ) + '</div>'
    return (
        '<div style="border:1px solid var(--sc-rule,#d6cfc0);border-radius:4px;'
        'padding:14px 16px;background:#fff;">'
        '<div style="display:flex;align-items:baseline;justify-content:space-between;gap:8px;">'
        f'<span style="font-family:var(--sc-sans);font-weight:600;font-size:15px;'
        f'color:var(--sc-navy,#0b2341);">{_html.escape(sector)}</span>'
        f'<span style="font-family:var(--sc-mono,monospace);font-size:10px;'
        f'font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:{color};">'
        f'<span style="display:inline-block;width:7px;height:7px;border-radius:50%;'
        f'background:{color};margin-right:5px;"></span>{tag}</span></div>'
        f'<div style="font-size:12px;line-height:1.5;color:var(--sc-text-dim,#465366);'
        f'margin-top:6px;">{_html.escape(data_status)}</div>'
        f'{links_html}'
        '</div>'
    )


def render_sector_intelligence() -> str:
    """Render the Sector Intelligence directory (read-only, honest status)."""
    cards = "".join(_card(*s) for s in _SECTORS)
    grid = (
        '<div style="display:grid;grid-template-columns:repeat(auto-fill,'
        'minmax(260px,1fr));gap:12px;margin-top:8px;">' + cards + '</div>'
    )
    n_live = sum(1 for s in _SECTORS if s[1] == "live")
    body = (
        ck_page_title(
            "Sector Intelligence",
            eyebrow="SECTOR INTELLIGENCE",
            meta=f"{n_live} live · {len(_SECTORS) - n_live} on the roadmap · "
                 "healthcare-services coverage",
        )
        + ck_section_intro(
            eyebrow="COVERAGE",
            headline="The healthcare-services sectors PEdesk covers.",
            italic_word="covers",
            body=(
                "PE deal flow spans far more than hospitals. This is the "
                "honest coverage map: only sectors marked Live have data and "
                "pages today; the rest are planned, each labeled with the "
                "public data it can (and can't) answer. Build plan: "
                "docs/PEDESK_SECTOR_INTELLIGENCE_ROADMAP.md."
            ),
        )
        + grid
        + '<p style="font-size:11px;color:var(--sc-text-faint,#8a8170);'
        'margin-top:14px;">Roadmap sectors are not yet built — no page is '
        'linked until its data is sourced and vendored, the same way the '
        'hospital sector was.</p>'
    )
    return chartis_shell(
        body, "Sector Intelligence", active_nav="/sector-intelligence",
    )
