"""Private Credit / Direct Lending Tracker — /direct-lending."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_bar_row, ck_kpi_block, ck_data_cell, ck_page_title, ck_illustrative_note, ck_value_anchor
from rcm_mc.ui.data_public._benchmark_panels import data_required_panel


def _facilities_chart(items) -> str:
    """Lead chart for the facility table — facilities ranked by amount
    outstanding so the weight of the loan book reads at a glance. Bar =
    share of total outstanding; value = outstanding ($M); tone marks
    documentation (teal cov-lite · amber maintenance). Full grid below.
    """
    total = sum(f.outstanding_mm for f in items) or 1.0
    ranked = sorted(items, key=lambda f: f.outstanding_mm, reverse=True)
    rows = []
    for f in ranked:
        tone = "teal" if f.cov_lite else "warning"
        rows.append(ck_bar_row(
            f.lender, f"${f.outstanding_mm:,.0f}M",
            f.outstanding_mm / total * 100.0, tone=tone))
    return (
        '<div style="margin-bottom:14px">'
        f'{"".join(rows)}'
        '<div style="font-size:10px;color:var(--sc-text-faint);'
        'margin-top:6px;font-family:JetBrains Mono,monospace">'
        'Bar = share of total outstanding · value = outstanding ($M) · '
        'tone = documentation (teal cov-lite · amber maintenance)</div>'
        '</div>')


def _facilities_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; acc = P["accent"]
    cols = [("Lender","left"),("Type","center"),("Commit ($M)","right"),("Outstanding ($M)","right"),
            ("Spread (bps)","right"),("All-In Rate","right"),("Tenor (yr)","right"),("Cov-Lite","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, f in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(f.lender)}""", mono=True, weight=600)}',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(f.lender_type)}</td>',
            f'{ck_data_cell(f"""${f.commitment_mm:,.2f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${f.outstanding_mm:,.2f}""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{f.spread_sofr_bps}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{f.all_in_rate_pct:.2f}%""", align="right", mono=True, tone="neg", weight=700)}',
            f'{ck_data_cell(f"""{f.tenor_years}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{pos if f.cov_lite else text_dim};font-weight:700">{"YES" if f.cov_lite else "NO"}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _rates_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]
    cols = [("Deal Size","left"),("Unitranche (bps)","right"),("First-Lien TL (bps)","right"),
            ("Second-Lien (bps)","right"),("Typical OID","right"),("Closing Fee (bps)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, r in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(r.deal_size_bucket)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{r.unitranche_spread_bps}""", align="right", mono=True, tone="acc", weight=700)}',
            f'{ck_data_cell(f"""{r.first_lien_tl_spread_bps}""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["negative"]}">{r.second_lien_spread_bps}</td>',
            f'{ck_data_cell(f"""{r.typical_oid_pct * 100:.2f}%""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{r.avg_closing_fee_bps}""", align="right", mono=True, tone="dim")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _matrix_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Sponsor","left"),("Primary Lender","left"),("Deals LTM","right"),
            ("Total Committed ($M)","right"),("Avg Leverage","right"),("Tier","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    tier_c = {"platinum": pos, "captive": pos, "gold": acc, "silver": text_dim}
    for i, m in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        tc = tier_c.get(m.relationship_tier, text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(m.sponsor)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{_html.escape(m.primary_lender)}""", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{m.deals_financed_ltm}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${m.total_committed_mm:,.2f}""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""{m.avg_leverage:.2f}x""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{tc};border:1px solid {tc};border-radius:2px;letter-spacing:0.06em">{_html.escape(m.relationship_tier)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _defaults_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Period","left"),("HC Default %","right"),("Overall Default %","right"),
            ("Amend-Extend Volume","right"),("Covenant Breach","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, d in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        hc_c = neg if d.healthcare_default_rate_pct >= 0.04 else warn
        cells = [
            f'{ck_data_cell(f"""{_html.escape(d.period)}""", mono=True, weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{hc_c};font-weight:700">{d.healthcare_default_rate_pct * 100:.2f}%</td>',
            f'{ck_data_cell(f"""{d.overall_default_rate_pct * 100:.2f}%""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{d.amend_extend_volume_pct * 100:.1f}%""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{warn}">{d.covenant_breach_count}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _marks_chart(items) -> str:
    """Summary chart — portfolio par balance by sector (tone by watch-list/mark)."""
    def _tone(m):
        if m.watch_list_flag: return "negative"
        if m.unrealized_loss_mm > 0: return "warning"
        return "teal"
    top = sorted(items, key=lambda m: m.par_balance_mm, reverse=True)
    total = sum(m.par_balance_mm for m in top) or 1.0
    rows = [ck_bar_row(f"{m.sector}",
            f"${m.par_balance_mm:,.0f}M @ {m.current_mark_pct * 100:.1f}",
            m.par_balance_mm / total * 100.0, tone=_tone(m)) for m in top]
    return ('<div style="margin-bottom:14px">' + "".join(rows) +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Bar = share of par balance by sector '
            '· value = par ($M) @ mark · tone = watch-list / unrealized loss</div></div>')


def _marks_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Sector","left"),("Par Balance ($M)","right"),("Current Mark","right"),("Unrealized Loss ($M)","right"),("Watch List","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, m in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        mark_c = pos if m.current_mark_pct >= 98 else (warn if m.current_mark_pct >= 92 else neg)
        wl_c = neg if m.watch_list_flag else text_dim
        cells = [
            f'{ck_data_cell(f"""{_html.escape(m.sector)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""${m.par_balance_mm:,.2f}""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{mark_c};font-weight:700">{m.current_mark_pct:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg if m.unrealized_loss_mm > 0 else pos};font-weight:600">${m.unrealized_loss_mm:+,.2f}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{wl_c};font-weight:700">{"YES" if m.watch_list_flag else "NO"}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_direct_lending(params: dict = None) -> str:
    from rcm_mc.data_public.direct_lending import compute_direct_lending
    r = compute_direct_lending()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    latest_hc_default_pct = r.defaults[-1].healthcare_default_rate_pct if r.defaults else 0
    watch_count = sum(1 for m in r.marks if m.watch_list_flag)

    kpi_strip = (
        ck_kpi_block("Facilities", str(r.total_facilities), "", "") +
        ck_kpi_block("Total Outstanding", f"${r.total_outstanding_mm:,.0f}M", "", "") +
        ck_kpi_block("Blended Rate", f"{r.blended_all_in_rate_pct:.2f}%", "", "") +
        ck_kpi_block("Weighted Leverage", f"{r.weighted_leverage:.2f}x", "", "") +
        ck_kpi_block("Cov-Lite %", f"{r.cov_lite_pct * 100:.1f}%", "", "") +
        ck_kpi_block("Latest HC Default", f"{latest_hc_default_pct * 100:.2f}%", "", "") +
        ck_kpi_block("Watch-List Sectors", str(watch_count), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    f_chart = _facilities_chart(r.facilities)
    f_tbl = _facilities_table(r.facilities)
    value_anchor = ck_value_anchor(
        "Direct Lending Book",
        f"${r.total_outstanding_mm:,.0f}M outstanding",
        delta=f"{r.total_facilities} facilities · {r.blended_all_in_rate_pct:.2f}% all-in · {r.weighted_leverage:.2f}x leverage · {r.cov_lite_pct * 100:.0f}% cov-lite",
        tone="navy",
    )
    rt_tbl = _rates_table(r.rates)
    m_tbl = _matrix_table(r.matrix)
    d_tbl = _defaults_table(r.defaults)
    mk_tbl = _marks_table(r.marks)
    mk_chart = _marks_chart(r.marks)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    page_title = ck_page_title(
        "Private Credit / Direct Lending Tracker",
        eyebrow="DIRECT LENDING",
        meta=f"${r.total_outstanding_mm:,.0f}M outstanding across {r.total_facilities} facilities · {r.blended_all_in_rate_pct:.2f}% blended all-in at {r.weighted_leverage:.2f}x leverage · {r.cov_lite_pct * 100:.1f}% cov-lite · {latest_hc_default_pct * 100:.2f}% latest HC default with {watch_count} watch-list sectors",
    )

    body = f"""
<div class="ck-page-wrap">
  {page_title}
  {data_required_panel(P, title="Direct Lending", needed=[("borrower","borrower (PII)"),("facility","facility"),("commitment","commitment $"),("spread_bps","spread bps"),("covenant","covenant"),("status","performing / watch / default")], template="direct_lending_template.csv", request_from="Credit / private-credit team", activates="loan-book spread, covenant, and default tracking", guide_hint="What loan-book data do I need to upload?")}
  {ck_illustrative_note("figures")}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  {value_anchor}
  <div style="{cell}"><div style="{h3}">Active Facility Portfolio</div>{f_chart}{f_tbl}</div>
  <div style="{cell}"><div style="{h3}">Market-Rate Spread Matrix by Deal Size</div>{rt_tbl}</div>
  <div style="{cell}"><div style="{h3}">Sponsor-Lender Relationship Matrix</div>{m_tbl}</div>
  <div style="{cell}"><div style="{h3}">Default Rate Trend — Healthcare vs Overall</div>{d_tbl}</div>
  <div style="{cell}"><div style="{h3}">Portfolio Marks by Sector</div>{mk_chart}{mk_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Direct Lending Thesis:</strong> ${r.total_outstanding_mm:,.0f}M outstanding across {r.total_facilities} facilities at {r.blended_all_in_rate_pct:.2f}% blended all-in rate.
    Weighted leverage {r.weighted_leverage:.2f}x; cov-lite penetration {r.cov_lite_pct * 100:.1f}% — structural flexibility but reduced lender protection.
    Healthcare default rate trailing overall market at ~4% (vs 3.5% all-in); peak at 2025Q2, now moderating.
    {watch_count} watch-list sectors identified — behavioral, home-health/hospice, skilled nursing, and standalone telehealth showing sub-95 marks.
    Captive lenders (KKR, Bain) maintain tightest relationships; Ares and Blue Owl are the go-to for larger deals.
    Amend-and-extend volume has normalized at ~12%, down from 14% peak. Spread compression in largest deals (&lt;425bps for $250M+ EBITDA) signals market thaw.
  </div>
</div>"""

    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from .._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(body, "Direct Lending", active_nav="/direct-lending",
        editorial_intro={
            "eyebrow": "DIRECT LENDING",
            "headline": "What the direct lending page reveals on this deal.",
            "italic_word": "reveals",
        })
