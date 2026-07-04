"""Pharma Manufacturing, Pricing & Distribution — /pharma-supply.

Sourced national reference view of the pharma supply side: IRA negotiated
Maximum Fair Prices, the gross-to-net bubble, 340B, the Big Three
wholesalers, and the (genuinely contested) drug-development cost estimates.
Discloses its basis with a ck_source_purpose research header rather than the
illustrative-corpus banner — every figure traces to a named public source.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import (
    P, chartis_shell, ck_page_title, ck_kpi_block, ck_value_anchor,
    ck_bar_row, ck_data_cell, ck_source_purpose, ck_source_link,
)

_SOURCES = (
    "IQVIA Institute (US net medicine spending)",
    "CMS Medicare Drug Price Negotiation (MFP)",
    "Drug Channels Institute (gross-to-net; 340B; wholesalers)",
    "JAMA (Wouters et al.)",
)


def _bar_chart(rows: str, caption: str) -> str:
    return ('<div style="margin-bottom:14px">' + rows +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            f'font-family:JetBrains Mono,monospace">{caption}</div></div>')


def _ira_table(items) -> str:
    text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Drug", "left"), ("Indication", "left"),
            ("Gross Part D ($B)", "right"), ("MFP discount", "right")]
    ths = "".join(ck_data_cell(c, align=a, is_header=True) for c, a in cols)
    _max = max((d.gross_part_d_cost_b for d in items), default=1.0) or 1.0
    trs = []
    for d in items:
        disc_c = pos if d.mfp_discount_pct >= 65 else (acc if d.mfp_discount_pct >= 50 else P["warning"])
        cells = [
            ck_data_cell(_html.escape(d.drug), mono=True, weight=700),
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:280px">{_html.escape(d.indication)}</td>',
            ck_data_cell(f"${d.gross_part_d_cost_b:.1f}B", align="right", mono=True, tone="acc", bar=d.gross_part_d_cost_b / _max * 100),
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{disc_c};font-weight:700">{d.mfp_discount_pct:.0f}%</td>',
        ]
        trs.append(f"<tr>{''.join(cells)}</tr>")
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _gtn_rows(items) -> str:
    rows = []
    for c in items:
        if c.kind == "start":
            rows.append(ck_bar_row(c.label, f"${c.value_b:.0f}", 100.0, tone="navy"))
        elif c.kind == "net":
            rows.append(ck_bar_row(c.label, f"${c.value_b:.0f}", c.value_b, tone="navy"))
        else:
            rows.append(ck_bar_row(c.label, f"−${abs(c.value_b):.0f}", abs(c.value_b), tone="warning"))
    return _bar_chart("".join(rows),
                      "Indexed to WAC list = $100 · reductions (amber) bridge to net (navy) · "
                      "routine branded-specialty spread 40–60%")


def _wholesaler_table(items) -> str:
    text_dim = P["text_dim"]
    cols = [("Wholesaler", "left"), ("FY revenue ($B)", "right"),
            ("Adj. gross margin", "right"), ("Operating margin", "right"), ("Note", "left")]
    ths = "".join(ck_data_cell(c, align=a, is_header=True) for c, a in cols)
    _max = max((w.fy_revenue_b for w in items), default=1.0) or 1.0
    trs = []
    for w in items:
        cells = [
            ck_data_cell(_html.escape(w.name), mono=True, weight=700),
            ck_data_cell(f"${w.fy_revenue_b:,.1f}B", align="right", mono=True, tone="acc", weight=700, bar=w.fy_revenue_b / _max * 100),
            ck_data_cell(f"{w.adj_gross_margin_pct:.2f}%", align="right", mono=True),
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]};font-weight:700">{w.op_margin_pct:.2f}%</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:300px">{_html.escape(w.note)}</td>',
        ]
        trs.append(f"<tr>{''.join(cells)}</tr>")
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _devcost_table(items) -> str:
    text = P["text"]; text_dim = P["text_dim"]
    cols = [("Study", "left"), ("Year", "right"), ("Low ($M)", "right"),
            ("Estimate ($M)", "right"), ("High ($M)", "right")]
    ths = "".join(ck_data_cell(c, align=a, is_header=True) for c, a in cols)
    trs = []
    for e in items:
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text};max-width:340px">{_html.escape(e.study)}</td>',
            ck_data_cell(str(e.year), align="right", mono=True, tone="dim"),
            ck_data_cell(f"${e.low_m:,.0f}", align="right", mono=True, tone="dim"),
            ck_data_cell(f"${e.point_m:,.0f}", align="right", mono=True, tone="acc", weight=700),
            ck_data_cell(f"${e.high_m:,.0f}", align="right", mono=True, tone="dim"),
        ]
        trs.append(f"<tr>{''.join(cells)}</tr>")
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _sources_footer() -> str:
    text_dim = P["text_dim"]; border = P["border"]; panel_alt = P["panel_alt"]; acc = P["accent"]
    links = " · ".join(ck_source_link(s) for s in _SOURCES)
    xlinks = (
        '<a href="/tracker-340b">340B tracker</a> · '
        '<a href="/biosimilars">Biosimilars</a> · '
        '<a href="/drug-shortage">Drug shortages</a> · '
        '<a href="/drug-pricing-340b">Drug pricing &amp; 340B</a>'
    )
    return (f'<div style="background:{panel_alt};border:1px solid {border};'
            f'border-left:3px solid {acc};padding:12px 16px;font-size:11px;'
            f'color:{text_dim};margin-bottom:16px">'
            f'<strong>Primary sources:</strong> {links}.<br>'
            f'<strong>Related pages:</strong> {xlinks}.</div>')


def render_pharma_supply(params: dict = None) -> str:
    from rcm_mc.data_public.pharma_supply import compute_pharma_supply
    r = compute_pharma_supply()

    panel = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]

    page_title = ck_page_title(
        "Pharma Manufacturing, Pricing & Distribution",
        eyebrow="MARKET DATA · PHARMA SUPPLY SIDE",
        meta=(f"US net spend ${r.us_net_spend_b:,.0f}B (+{r.us_net_growth_pct:.1f}%) · "
              f"gross-to-net bubble ${r.gross_to_net_bubble_b:,.0f}B · "
              f"340B ${r.b340_purchases_b:,.1f}B · Big Three ${r.big_three_revenue_b:,.0f}B"),
    )
    disclosure = ck_source_purpose(
        purpose="Map the pharma supply side — pricing, rebates, distribution — for diligence context.",
        universe="research",
        source="IQVIA · CMS · Drug Channels Institute · JAMA",
    )

    anchor = ck_value_anchor(
        "US NET MEDICINE SPEND",
        f"${r.us_net_spend_b:,.0f}B",
        delta=f"+{r.us_net_growth_pct:.1f}% in 2024 (vs 4.9% in 2023) · "
              f"specialty {r.specialty_share_pct:.0f}% of net branded sales",
        opportunity=f"${r.gross_to_net_bubble_b:,.0f}B gross-to-net bubble",
        target=f"global ${r.global_spend_t:.1f}T (ex-COVID, invoice)",
        tone="teal",
    )

    kpi_strip = (
        ck_kpi_block("Global spend", f"${r.global_spend_t:.1f}T", "ex-COVID, invoice (IQVIA)", "") +
        ck_kpi_block("US net spend", f"${r.us_net_spend_b:,.0f}B", "2024 (IQVIA)", f"+{r.us_net_growth_pct:.1f}%") +
        ck_kpi_block("US list spend", f"${r.us_list_spend_t:.1f}T+", "crested $1T in 2024", "") +
        ck_kpi_block("Gross-to-net bubble", f"${r.gross_to_net_bubble_b:,.0f}B", "2024 (DCI)", "") +
        ck_kpi_block("340B purchases", f"${r.b340_purchases_b:,.1f}B", "2024 record (DCI)", f"+{r.b340_growth_pct:.0f}%") +
        ck_kpi_block("Big Three revenue", f"${r.big_three_revenue_b:,.0f}B", "drug distribution 2024", "") +
        ck_kpi_block("Specialty share", f"{r.specialty_share_pct:.0f}%", "of net branded sales", "") +
        ck_kpi_block("IRA drugs (cycle 1)", str(len(r.negotiated)), "MFPs effective 2026-01-01", "")
    )

    ira_chart = _bar_chart(
        "".join(ck_bar_row(
            d.drug, f"{d.mfp_discount_pct:.0f}% off list", d.mfp_discount_pct,
            tone=("positive" if d.mfp_discount_pct >= 65 else "teal" if d.mfp_discount_pct >= 50 else "warning"))
            for d in sorted(r.negotiated, key=lambda x: x.mfp_discount_pct, reverse=True)),
        "Bar = announced discount off list (HHS/CMS, 2024-08-15) · published band 38–79%",
    )
    ira_tbl = _ira_table(r.negotiated)
    gtn_rows = _gtn_rows(r.gross_to_net)
    whole_tbl = _wholesaler_table(r.wholesalers)
    ta_chart = _bar_chart(
        "".join(ck_bar_row(t.name, f"${t.net_spend_b:,.0f}B",
                t.net_spend_b / (max(x.net_spend_b for x in r.therapy_areas) or 1) * 100, tone="navy")
                for t in r.therapy_areas),
        "Bar = global net spend ($B) · top therapy areas (IQVIA)",
    )
    dev_tbl = _devcost_table(r.dev_costs)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div class="ck-page-wrap">
  {page_title}
  {disclosure}
  {anchor}
  {_sources_footer()}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">IRA Negotiated Drugs — Maximum Fair Prices (cycle 1, effective 2026-01-01)</div>{ira_chart}{ira_tbl}
    <div style="font-size:10px;color:{text_dim};margin-top:8px">The 10 drugs were ~20% of gross Part D cost; second-cycle 15 drugs (incl. semaglutide) have MFPs effective 2027-01-01 (CMS est. ~$12B saved had they applied in 2024).</div>
  </div>
  <div style="{cell}"><div style="{h3}">Gross-to-Net Bridge (WAC → net, indexed)</div>{gtn_rows}</div>
  <div style="{cell}"><div style="{h3}">Big Three Wholesalers — Razor-Thin Distribution Margins</div>{whole_tbl}</div>
  <div style="{cell}"><div style="{h3}">Top Therapy Areas — Global Net Spend</div>{ta_chart}</div>
  <div style="{cell}"><div style="{h3}">Drug-Development Cost — A Genuinely Contested Estimate</div>{dev_tbl}
    <div style="font-size:10px;color:{text_dim};margin-top:8px">Estimates span ~$868M–$2.87B. The Tufts figure capitalizes the cost of capital and bakes in failure rates — methodology critics dispute both choices. Treat as a range, not a point.</div>
  </div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Pharma Supply-Side Thesis:</strong> US net medicine spend grew {r.us_net_growth_pct:.1f}% to ${r.us_net_spend_b:,.0f}B in 2024, but the ${r.gross_to_net_bubble_b:,.0f}B gross-to-net bubble grew at its slowest pace in a decade — an early sign the IRA / 340B complex is reshaping net pricing. 340B hit a record ${r.b340_purchases_b:,.1f}B (+{r.b340_growth_pct:.0f}%). Distribution remains a sub-1% operating-margin business on ${r.big_three_revenue_b:,.0f}B of Big-Three revenue, with specialty / cold-chain the growth engine.
  </div>
</div>"""

    from .._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(body, "Pharma Supply", active_nav="/pharma-supply")
