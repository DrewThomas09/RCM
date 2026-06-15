"""RCM & Claims Transaction Infrastructure — /rcm-infrastructure.

Sourced reference view of the revenue-cycle / clearinghouse layer: US RCM
market-size estimates (a wide range by definition), the HIPAA EDI transaction
set, clearinghouse volumes, KPI benchmarks, and the Change Healthcare
cyberattack. Discloses its basis with a research source/purpose header.
Deal-level RCM red flags live on /rcm-red-flags.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import (
    P, chartis_shell, ck_page_title, ck_kpi_block, ck_value_anchor,
    ck_bar_row, ck_data_cell, ck_source_purpose, ck_source_link,
)

_SOURCES = (
    "HDA (Healthcare Distribution Alliance)",
    "CAQH Index",
    "Washington Publishing Company (CARC/RARC)",
)


def _bar_chart(rows: str, caption: str) -> str:
    return ('<div style="margin-bottom:14px">' + rows +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            f'font-family:JetBrains Mono,monospace">{caption}</div></div>')


def _estimate_table(items) -> str:
    text_dim = P["text_dim"]
    cols = [("Source", "left"), ("US RCM market ($B)", "right"), ("Definition", "left")]
    ths = "".join(ck_data_cell(c, align=a, is_header=True) for c, a in cols)
    _max = max((e.us_market_b for e in items), default=1.0) or 1.0
    trs = []
    for e in items:
        cells = [
            ck_data_cell(_html.escape(e.source), mono=True, weight=600),
            ck_data_cell(f"${e.us_market_b:,.1f}B", align="right", mono=True, tone="acc", weight=700, bar=e.us_market_b / _max * 100),
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:380px">{_html.escape(e.note)}</td>',
        ]
        trs.append(f"<tr>{''.join(cells)}</tr>")
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _edi_table(items) -> str:
    text = P["text"]; acc = P["accent"]
    cols = [("Transaction", "left"), ("Function", "left")]
    ths = "".join(ck_data_cell(c, align=a, is_header=True) for c, a in cols)
    trs = []
    for t in items:
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{_html.escape(t.code)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text}">{_html.escape(t.function)}</td>',
        ]
        trs.append(f"<tr>{''.join(cells)}</tr>")
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _kpi_table(items) -> str:
    text = P["text"]
    cols = [("KPI", "left"), ("Industry target / benchmark", "right")]
    ths = "".join(ck_data_cell(c, align=a, is_header=True) for c, a in cols)
    trs = []
    for k in items:
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text}">{_html.escape(k.metric)}</td>',
            ck_data_cell(_html.escape(k.target), align="right", mono=True, tone="pos", weight=600),
        ]
        trs.append(f"<tr>{''.join(cells)}</tr>")
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _sources_footer() -> str:
    text_dim = P["text_dim"]; border = P["border"]; panel_alt = P["panel_alt"]; acc = P["accent"]
    links = " · ".join(ck_source_link(s) for s in _SOURCES)
    xlinks = (
        '<a href="/rcm-red-flags">RCM red flags</a> · '
        '<a href="/revenue-leakage">Revenue leakage</a> · '
        '<a href="/specialty-benchmarks">Specialty benchmarks</a>'
    )
    return (f'<div style="background:{panel_alt};border:1px solid {border};'
            f'border-left:3px solid {acc};padding:12px 16px;font-size:11px;'
            f'color:{text_dim};margin-bottom:16px">'
            f'<strong>Primary sources:</strong> {links}.<br>'
            f'<strong>Related pages:</strong> {xlinks}.</div>')


def render_rcm_infrastructure(params: dict = None) -> str:
    from rcm_mc.data_public.rcm_infrastructure import compute_rcm_infrastructure
    r = compute_rcm_infrastructure()

    panel = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]

    page_title = ck_page_title(
        "RCM & Claims Transaction Infrastructure",
        eyebrow="MARKET DATA · RCM INFRASTRUCTURE",
        meta=(f"US RCM ${r.market_low_b:,.0f}–{r.market_high_b:,.0f}B (by definition) · "
              f"Change Healthcare ~{r.change_transactions_b:,.0f}B transactions/yr"),
    )
    disclosure = ck_source_purpose(
        purpose="Map the revenue-cycle & claims-clearing layer for diligence context.",
        universe="research",
        source="HDA · CAQH · HIPAA X12 v5010 · WPC",
    )
    anchor = ck_value_anchor(
        "US RCM MARKET",
        f"${r.market_low_b:,.0f}–{r.market_high_b:,.0f}B",
        delta=f"range reflects software-only vs services-inclusive definitions · "
              f"services {r.services_share_low_pct:.0f}–{r.services_share_high_pct:.0f}% of market",
        opportunity=f"in-house still {r.inhouse_low_pct:.0f}–{r.inhouse_high_pct:.0f}% of operations",
        target="cloud/SaaS fastest-growing (~12–14% CAGR)",
        tone="teal",
    )
    kpi_strip = (
        ck_kpi_block("US RCM market", f"${r.market_low_b:,.0f}–{r.market_high_b:,.0f}B", "2024 range", "") +
        ck_kpi_block("Services share", f"{r.services_share_low_pct:.0f}–{r.services_share_high_pct:.0f}%", "of market", "") +
        ck_kpi_block("In-house ops", f"{r.inhouse_low_pct:.0f}–{r.inhouse_high_pct:.0f}%", "outsourcing growing fastest", "") +
        ck_kpi_block("Change Healthcare", f"~{r.change_transactions_b:,.0f}B", "transactions/yr (largest)", "") +
        ck_kpi_block("Clean claim target", ">95%", "industry standard", "") +
        ck_kpi_block("Days in A/R target", "<40–50", "industry standard", "") +
        ck_kpi_block("Cost-to-collect", "~2–4%", "of net patient revenue", "") +
        ck_kpi_block("Prior-auth electronic", "~35%", "278 adoption (2024)", "")
    )
    est_chart = _bar_chart(
        "".join(ck_bar_row(e.source, f"${e.us_market_b:,.1f}B",
                e.us_market_b / (max(x.us_market_b for x in r.estimates) or 1) * 100,
                tone=("warning" if e.us_market_b > 100 else "teal"))
                for e in sorted(r.estimates, key=lambda x: x.us_market_b)),
        "Bar = US RCM market estimate ($B) · the 3x spread is a definition gap, not a data gap",
    )
    est_tbl = _estimate_table(r.estimates)
    edi_tbl = _edi_table(r.edi)
    ch_chart = _bar_chart(
        "".join(ck_bar_row(c.name, f"~{c.annual_transactions_b:,.1f}B/yr",
                c.annual_transactions_b / (max(x.annual_transactions_b for x in r.clearinghouses) or 1) * 100,
                tone="navy")
                for c in sorted(r.clearinghouses, key=lambda x: x.annual_transactions_b, reverse=True)),
        "Bar = annual clearinghouse transaction volume (B) · industry ~30B+ total",
    )
    kpi_tbl = _kpi_table(r.kpis)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div class="ck-page-wrap">
  {page_title}
  {disclosure}
  {anchor}
  {_sources_footer()}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">US RCM Market — Estimates by Source (show the range, not a point)</div>{est_chart}{est_tbl}</div>
  <div style="{cell}"><div style="{h3}">HIPAA EDI Transaction Set (ANSI X12 v5010)</div>{edi_tbl}
    <div style="font-size:10px;color:{text_dim};margin-top:8px">CARC/RARC adjustment codes (e.g. CO-45 contractual write-off, PR-1 deductible) are maintained by the Washington Publishing Company.</div>
  </div>
  <div style="{cell}"><div style="{h3}">Major Clearinghouses — Annual Transaction Volume</div>{ch_chart}</div>
  <div style="{cell}"><div style="{h3}">RCM KPI Benchmarks</div>{kpi_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">RCM Infrastructure Thesis:</strong> The US RCM market spans ${r.market_low_b:,.0f}–{r.market_high_b:,.0f}B depending on whether you count software only or services-inclusive — always show the range. Claims clear through a concentrated clearinghouse layer; the Feb-2024 Change Healthcare cyberattack disrupted ~1-in-3 US patient records and forced >$9B in UHG advance funding, reshaping the infrastructure and accelerating multi-clearinghouse redundancy. Outsourced + cloud/SaaS RCM are the fastest-growing slices.
  </div>
</div>"""

    from .._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(body, "RCM Infrastructure", active_nav="/rcm-infrastructure")
