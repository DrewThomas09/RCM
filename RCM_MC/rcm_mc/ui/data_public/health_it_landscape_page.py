"""Health IT, EHR & Interoperability — /health-it-landscape.

Sourced reference view of the health-IT supply side: acute-care EHR share
(KLAS), digital-health venture funding (Rock Health), and TEFCA / QHIN
interoperability. Discloses its basis with a research source/purpose header;
FDA-cleared clinical AI detail lives on /clinical-ai.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import (
    P, chartis_shell, ck_page_title, ck_kpi_block, ck_value_anchor,
    ck_bar_row, ck_data_cell, ck_source_purpose, ck_source_link,
)

_SOURCES = (
    "KLAS Research (EHR market share)",
    "Rock Health (digital-health funding)",
    "ONC / The Sequoia Project (TEFCA / QHINs)",
)


def _bar_chart(rows: str, caption: str) -> str:
    return ('<div style="margin-bottom:14px">' + rows +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            f'font-family:JetBrains Mono,monospace">{caption}</div></div>')


def _vendor_table(items) -> str:
    text_dim = P["text_dim"]
    cols = [("Vendor", "left"), ("Hospital share", "right"), ("Note", "left")]
    ths = "".join(ck_data_cell(c, align=a, is_header=True) for c, a in cols)
    _max = max((v.hospital_share_pct for v in items), default=1.0) or 1.0
    trs = []
    for v in items:
        cells = [
            ck_data_cell(_html.escape(v.name), mono=True, weight=700),
            ck_data_cell(f"{v.hospital_share_pct:.1f}%", align="right", mono=True, tone="acc", weight=700, bar=v.hospital_share_pct / _max * 100),
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:420px">{_html.escape(v.note)}</td>',
        ]
        trs.append(f"<tr>{''.join(cells)}</tr>")
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _qhin_table(items) -> str:
    text_dim = P["text_dim"]
    cols = [("QHIN", "left"), ("Designated", "right")]
    ths = "".join(ck_data_cell(c, align=a, is_header=True) for c, a in cols)
    trs = []
    for q in items:
        tone = "pos" if q.designated.startswith("2023") else "dim"
        cells = [
            ck_data_cell(_html.escape(q.name), mono=True, weight=600),
            ck_data_cell(_html.escape(q.designated), align="right", mono=True, tone=tone),
        ]
        trs.append(f"<tr>{''.join(cells)}</tr>")
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _funding_chart(items) -> str:
    _max = max((f.vc_b for f in items), default=1.0) or 1.0
    rows = []
    for f in sorted(items, key=lambda x: x.year):
        dealtxt = f" · {f.deals} deals" if f.deals else ""
        tone = "positive" if f.year == 2021 else "teal"
        rows.append(ck_bar_row(str(f.year), f"${f.vc_b:.1f}B{dealtxt}", f.vc_b / _max * 100, tone=tone))
    return _bar_chart("".join(rows),
                      "Bar = US digital-health VC ($B) · Rock Health · 2021 was the peak ($29.2B)")


def _sources_footer() -> str:
    text_dim = P["text_dim"]; border = P["border"]; panel_alt = P["panel_alt"]; acc = P["accent"]
    links = " · ".join(ck_source_link(s) for s in _SOURCES)
    xlinks = (
        '<a href="/clinical-ai">Clinical AI / FDA AI devices</a> · '
        '<a href="/tech-stack">Tech stack</a> · '
        '<a href="/hcit-platform">HCIT platform</a>'
    )
    return (f'<div style="background:{panel_alt};border:1px solid {border};'
            f'border-left:3px solid {acc};padding:12px 16px;font-size:11px;'
            f'color:{text_dim};margin-bottom:16px">'
            f'<strong>Primary sources:</strong> {links}.<br>'
            f'<strong>Related pages:</strong> {xlinks}.</div>')


def render_health_it_landscape(params: dict = None) -> str:
    from rcm_mc.data_public.health_it_landscape import compute_health_it_landscape
    r = compute_health_it_landscape()

    panel = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]

    page_title = ck_page_title(
        "Health IT, EHR & Interoperability",
        eyebrow="MARKET DATA · HEALTH IT",
        meta=(f"Epic {r.epic_share_pct:.1f}% · Oracle {r.oracle_share_pct:.1f}% · "
              f"digital-health VC ${r.digital_health_vc_b:.1f}B / {r.digital_health_deals} deals · "
              f"{r.qhins_live} QHINs"),
    )
    disclosure = ck_source_purpose(
        purpose="Map the health-IT supply side — EHR concentration, funding, interoperability.",
        universe="research",
        source="KLAS · Rock Health · ONC / Sequoia Project",
    )
    anchor = ck_value_anchor(
        "EPIC ACUTE-CARE EHR SHARE",
        f"{r.epic_share_pct:.1f}%",
        delta=f"won ~70% of 2024 hospital EHR decisions · Oracle (Cerner) {r.oracle_share_pct:.1f}%",
        opportunity=f"${r.digital_health_vc_b:.1f}B digital-health VC (2024)",
        target=f"{r.ai_funding_share_pct:.0f}% of funding AI-enabled",
        tone="teal",
    )
    kpi_strip = (
        ck_kpi_block("Epic share", f"{r.epic_share_pct:.1f}%", "acute-care hospitals (KLAS)", "") +
        ck_kpi_block("Oracle (Cerner)", f"{r.oracle_share_pct:.1f}%", "net −74 hospitals 2024", "") +
        ck_kpi_block("Digital-health VC", f"${r.digital_health_vc_b:.1f}B", "2024 (Rock Health)", "") +
        ck_kpi_block("VC deals", str(r.digital_health_deals), "2024", "") +
        ck_kpi_block("AI-enabled funding", f"{r.ai_funding_share_pct:.0f}%", "of 2024 funding", "") +
        ck_kpi_block("QHINs designated", str(r.qhins_live), "TEFCA live", "") +
        ck_kpi_block("Common Agreement", "v2.0", "requires FHIR support", "") +
        ck_kpi_block("M&A (2024)", "118 deals", "decade low", "")
    )
    vendor_chart = _bar_chart(
        "".join(ck_bar_row(v.name, f"{v.hospital_share_pct:.1f}%", v.hospital_share_pct, tone="navy")
                for v in r.vendors),
        "Bar = acute-care hospital EHR share % (KLAS, end-2024)",
    )
    vendor_tbl = _vendor_table(r.vendors)
    funding_chart = _funding_chart(r.funding)
    qhin_tbl = _qhin_table(r.qhin_list)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div class="ck-page-wrap">
  {page_title}
  {disclosure}
  {anchor}
  {_sources_footer()}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Acute-Care EHR Market Share (KLAS, end-2024)</div>{vendor_chart}{vendor_tbl}</div>
  <div style="{cell}"><div style="{h3}">US Digital-Health Venture Funding</div>{funding_chart}
    <div style="font-size:10px;color:{text_dim};margin-top:8px">2024: ${r.digital_health_vc_b:.1f}B across {r.digital_health_deals} deals; average deal $20.4M (vs $39.5M in 2021). AI-enabled startups were {r.ai_funding_share_pct:.0f}% of funding.</div>
  </div>
  <div style="{cell}"><div style="{h3}">TEFCA — Designated QHINs</div>{qhin_tbl}
    <div style="font-size:10px;color:{text_dim};margin-top:8px">First 5 QHINs designated 2023-12-12; Common Agreement v2.0 (2024) requires FHIR; QHIN-to-QHIN FHIR exchange piloted in 2025. Recognized Coordinating Entity: The Sequoia Project.</div>
  </div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Health-IT Thesis:</strong> EHR is a durable near-duopoly — Epic ({r.epic_share_pct:.1f}%) was the only vendor to gain hospitals in 2024 and won ~70% of decisions; Oracle is integrating Cerner against falling loyalty scores. Digital-health funding has normalized to ~${r.digital_health_vc_b:.1f}B (off the $29.2B 2021 peak), now {r.ai_funding_share_pct:.0f}% AI-enabled and early-stage heavy. TEFCA/QHIN interoperability is live but FHIR-based QHIN exchange is still maturing.
  </div>
</div>"""

    from .._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(body, "Health IT Landscape", active_nav="/health-it-landscape")
