"""Medtech & Diagnostics Landscape — /medtech-landscape.

Sourced reference view of the medical-device & IVD supply side: top device
makers by revenue, segment market sizes, FDA pathway counts, and the
razor-razorblade recurring-revenue model. Market-size figures shown as
ranges where sources diverge (per the report's caveats). Discloses its
basis with a research source/purpose header.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import (
    P, chartis_shell, ck_page_title, ck_kpi_block, ck_value_anchor,
    ck_bar_row, ck_data_cell, ck_source_purpose, ck_source_link,
)

_SOURCES = (
    "FDA 510(k)/PMA/De Novo databases",
    "AdvaMed",
    "SEC 10-K filings",
)


def _bar_chart(rows: str, caption: str) -> str:
    return ('<div style="margin-bottom:14px">' + rows +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            f'font-family:JetBrains Mono,monospace">{caption}</div></div>')


def _segment_table(items) -> str:
    text_dim = P["text_dim"]
    cols = [("Segment", "left"), ("Market ($B, approx.)", "right"), ("Note", "left")]
    ths = "".join(ck_data_cell(c, align=a, is_header=True) for c, a in cols)
    _max = max((s.market_b for s in items), default=1.0) or 1.0
    trs = []
    for s in items:
        cells = [
            ck_data_cell(_html.escape(s.name), mono=True, weight=700),
            ck_data_cell(f"${s.market_b:,.0f}B", align="right", mono=True, tone="acc", weight=700, bar=s.market_b / _max * 100),
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:380px">{_html.escape(s.note)}</td>',
        ]
        trs.append(f"<tr>{''.join(cells)}</tr>")
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _pathway_table(items) -> str:
    text_dim = P["text_dim"]; acc = P["accent"]
    cols = [("Pathway", "left"), ("Key metric", "center"), ("Note", "left")]
    ths = "".join(ck_data_cell(c, align=a, is_header=True) for c, a in cols)
    trs = []
    for f in items:
        cells = [
            ck_data_cell(_html.escape(f.name), mono=True, weight=700),
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc};font-weight:700">{_html.escape(f.metric)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:420px">{_html.escape(f.note)}</td>',
        ]
        trs.append(f"<tr>{''.join(cells)}</tr>")
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _sources_footer() -> str:
    text_dim = P["text_dim"]; border = P["border"]; panel_alt = P["panel_alt"]; acc = P["accent"]
    links = " · ".join(ck_source_link(s) for s in _SOURCES)
    xlinks = (
        '<a href="/gpo-supply">GPO / IDN contracting</a> · '
        '<a href="/clinical-ai">Clinical AI / FDA AI devices</a> · '
        '<a href="/supply-chain">Supply chain</a>'
    )
    return (f'<div style="background:{panel_alt};border:1px solid {border};'
            f'border-left:3px solid {acc};padding:12px 16px;font-size:11px;'
            f'color:{text_dim};margin-bottom:16px">'
            f'<strong>Primary sources:</strong> {links} · MassDevice Big 100 (aggregated revenue).<br>'
            f'<strong>Related pages:</strong> {xlinks}.</div>')


def render_medtech_landscape(params: dict = None) -> str:
    from rcm_mc.data_public.medtech_landscape import compute_medtech_landscape
    r = compute_medtech_landscape()

    panel = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]

    page_title = ck_page_title(
        "Medtech & Diagnostics Landscape",
        eyebrow="MARKET DATA · MEDICAL DEVICES",
        meta=(f"global ${r.global_market_low_b:,.0f}–{r.global_market_high_b:,.0f}B · "
              f"US ~{r.us_share_pct:.0f}% · top-10 ≈{r.top10_share_pct:.0f}% · "
              f"IVD ${r.ivd_low_b:,.0f}–{r.ivd_high_b:,.0f}B"),
    )
    disclosure = ck_source_purpose(
        purpose="Map the medical-device & diagnostics supply side for diligence context.",
        universe="research",
        source="FDA databases · AdvaMed · SEC 10-Ks · MassDevice Big 100",
    )
    anchor = ck_value_anchor(
        "GLOBAL MEDTECH MARKET",
        f"${r.global_market_low_b:,.0f}–{r.global_market_high_b:,.0f}B",
        delta=f"US ~{r.us_share_pct:.0f}% of global · estimates vary materially by source/definition",
        opportunity=f"Intuitive {r.intuitive_recurring_pct:.0f}% recurring revenue",
        target=f"top-10 ≈{r.top10_share_pct:.0f}% of market",
        tone="teal",
    )
    kpi_strip = (
        ck_kpi_block("Global market", f"${r.global_market_low_b:,.0f}–{r.global_market_high_b:,.0f}B", "range by source", "") +
        ck_kpi_block("US share", f"~{r.us_share_pct:.0f}%", "of global market", "") +
        ck_kpi_block("Top-10 share", f"≈{r.top10_share_pct:.0f}%", "of market", "") +
        ck_kpi_block("R&D intensity", f"{r.rd_intensity_low_pct:.0f}–{r.rd_intensity_high_pct:.0f}%", "of revenue (avg)", "") +
        ck_kpi_block("IVD market", f"${r.ivd_low_b:,.0f}–{r.ivd_high_b:,.0f}B", "2024 range", "") +
        ck_kpi_block("Breakthrough designations", f"{r.breakthrough_designations:,}", "cumulative (CDRH+CBER)", "") +
        ck_kpi_block("…reached market", f"{r.breakthrough_to_market:,}", "of designations", "") +
        ck_kpi_block("Intuitive recurring", f"{r.intuitive_recurring_pct:.0f}%", "of FY2024 revenue", "")
    )
    company_chart = _bar_chart(
        "".join(ck_bar_row(c.name, f"${c.device_revenue_b:,.1f}B",
                c.device_revenue_b / (max(x.device_revenue_b for x in r.companies) or 1) * 100,
                tone="navy")
                for c in r.companies),
        "Bar = 2024 device revenue ($B) · MassDevice Big 100 / aggregated",
    )
    seg_tbl = _segment_table(r.segments)
    path_tbl = _pathway_table(r.pathways)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div class="ck-page-wrap">
  {page_title}
  {disclosure}
  {anchor}
  {_sources_footer()}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Top Device Makers — 2024 Device Revenue</div>{company_chart}</div>
  <div style="{cell}"><div style="{h3}">Segment Market Sizes (approximate, global)</div>{seg_tbl}
    <div style="font-size:10px;color:{text_dim};margin-top:8px">Segment estimates are approximate and vary by methodology; IVD shown at the mid of an $82–101B range. Reagents are ~65–69% of IVD (reagent-rental / razor-razorblade).</div>
  </div>
  <div style="{cell}"><div style="{h3}">FDA Device Pathways</div>{path_tbl}
    <div style="font-size:10px;color:{text_dim};margin-top:8px">Reimbursement follows clearance: CPT (AMA) → HCPCS Level II (CMS) → NTAP / TPT for incremental payment; CMS TCET can speed Medicare coverage for breakthrough devices.</div>
  </div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Medtech Thesis:</strong> The device economy runs on razor-razorblade — place an instrument/system, then sell recurring disposables/implants and service. Intuitive Surgical is the exemplar at {r.intuitive_recurring_pct:.0f}% recurring revenue; IVD runs the same reagent-rental playbook. Gross margins are 60–70%+; R&D runs {r.rd_intensity_low_pct:.0f}–{r.rd_intensity_high_pct:.0f}% of revenue. Contracting flows through GPOs/IDNs — see the GPO/IDN page.
  </div>
</div>"""

    from .._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(body, "Medtech Landscape", active_nav="/medtech-landscape")
