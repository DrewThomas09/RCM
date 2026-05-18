"""Debt Covenant Headroom Monitor — /covenant-headroom."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import (
    P, chartis_shell, ck_data_cell, ck_kpi_block, ck_page_title, ck_paired_block,
)


def _stress_paired_rows(items) -> tuple:
    """Stress-scenarios data for the stress-SVG's paired dataset.

    Returns ``(headers, rows, hot_rows)`` for ``ck_paired_block``.
    Six columns mirror the old _stress_table. ``hot_rows`` marks the
    worst scenario (lowest headroom_pct) — the row a partner needs
    to see first. Superseded the pre-rendered _stress_table when
    /covenant-headroom adopted the handoff's paired primitive.
    """
    headers = [
        "Scenario", "EBITDA Delta", "Projected EBITDA ($M)",
        "Projected Leverage", "Status", "Headroom",
    ]
    rows: list = []
    headrooms: list = []
    for s in items:
        rows.append([
            s.scenario,
            f"{s.ebitda_delta_pct * 100:+.1f}%",
            f"${s.projected_ebitda_mm:,.2f}",
            f"{s.projected_leverage:,.2f}x",
            s.covenant_status,
            f"{s.headroom_pct * 100:+.1f}%",
        ])
        headrooms.append(s.headroom_pct)
    hot = (
        [headrooms.index(min(headrooms))] if headrooms else []
    )
    return headers, rows, hot


def _covenants_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]; acc = P["accent"]
    cols = [("Covenant","left"),("Actual","right"),("Limit","right"),("Direction","center"),
            ("Headroom","right"),("Risk","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    risk_c = {"low": pos, "medium": warn, "high": neg}
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        rc = risk_c.get(c.breach_risk, text_dim)
        hr_c = pos if c.headroom_pct > 0.25 else (warn if c.headroom_pct > 0.10 else neg)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.name)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{c.actual:,.2f}""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{c.limit:,.2f}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(c.direction)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{hr_c};font-weight:700">{c.headroom_pct * 100:+.1f}%</td>',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{rc};border:1px solid {rc};border-radius:2px;letter-spacing:0.06em">{_html.escape(c.breach_risk)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _tranches_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; neg = P["negative"]; acc = P["accent"]
    cols = [("Tranche","left"),("Balance ($M)","right"),("Rate Type","left"),("Spread (bps)","right"),
            ("All-In Rate","right"),("Maturity","right"),("Covenant Type","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, t in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(t.tranche)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""${t.balance_mm:,.2f}""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{_html.escape(t.rate_type)}""", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{t.spread_bps if t.spread_bps else "—"}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{t.all_in_rate_pct:,.2f}%""", align="right", mono=True, tone="neg", weight=600)}',
            f'{ck_data_cell(f"""{t.maturity_year}""", align="right", mono=True, tone="acc")}',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(t.covenant_type)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _cure_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Cure Right","left"),("Equity Needed ($M)","right"),("Mechanism","left"),
            ("Time (days)","right"),("Rate Penalty","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.covenant)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""${c.cure_equity_needed_mm:,.2f}""", align="right", mono=True, tone="acc", weight=600)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.cure_mechanism)}</td>',
            f'{ck_data_cell(f"""{c.time_to_cure_days}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["negative"]}">{c.penalty_interest_bps}bps</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _amort_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; acc = P["accent"]
    cols = [("Year","left"),("Opening ($M)","right"),("Mandatory ($M)","right"),
            ("Cash Sweep ($M)","right"),("Voluntary ($M)","right"),("Closing ($M)","right"),("Interest ($M)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, a in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{a.year}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""${a.opening_balance_mm:,.2f}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${a.mandatory_amort_mm:,.2f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${a.excess_cash_sweep_mm:,.2f}""", align="right", mono=True, tone="pos")}',
            f'{ck_data_cell(f"""${a.voluntary_prepay_mm:,.2f}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""${a.closing_balance_mm:,.2f}""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""${a.interest_expense_mm:,.2f}""", align="right", mono=True, tone="neg")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _stress_svg(stress) -> str:
    if not stress: return ""
    w, h = 560, 220
    pad_l, pad_r, pad_t, pad_b = 50, 20, 30, 70
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b
    max_v = max(s.projected_leverage for s in stress) or 1
    covenant_line = 6.25
    bg = P["panel"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    text_dim = P["text_dim"]; text_faint = P["text_faint"]
    n = len(stress)
    bar_w = (inner_w - (n - 1) * 10) / n
    covenant_y = (h - pad_b) - (covenant_line / max(max_v, covenant_line) * inner_h)
    bars = [f'<line x1="{pad_l}" y1="{covenant_y:.1f}" x2="{pad_l + inner_w}" y2="{covenant_y:.1f}" stroke="{neg}" stroke-width="1.5" stroke-dasharray="4,4"/>'
            f'<text x="{pad_l + inner_w - 5}" y="{covenant_y - 3:.1f}" fill="{neg}" font-size="9" text-anchor="end" font-family="JetBrains Mono,monospace;font-weight:700">covenant 6.25x</text>']
    for i, s in enumerate(stress):
        x = pad_l + i * (bar_w + 10)
        bh = s.projected_leverage / max(max_v, covenant_line) * inner_h
        y = (h - pad_b) - bh
        color = pos if s.projected_leverage < 5.75 else (warn if s.projected_leverage < 6.25 else neg)
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" fill="{color}" opacity="0.85"/>'
            f'<text x="{x + bar_w / 2:.1f}" y="{y - 4:.1f}" fill="{color}" font-size="10" text-anchor="middle" font-family="JetBrains Mono,monospace;font-weight:700">{s.projected_leverage:.2f}x</text>'
            f'<text x="{x + bar_w / 2:.1f}" y="{h - pad_b + 14}" fill="{text_faint}" font-size="8" text-anchor="middle" font-family="JetBrains Mono,monospace">{_html.escape(s.scenario[:18])}</text>'
            f'<text x="{x + bar_w / 2:.1f}" y="{h - pad_b + 26}" fill="{text_faint}" font-size="8" text-anchor="middle" font-family="JetBrains Mono,monospace">{s.ebitda_delta_pct * 100:+.0f}% EBITDA</text>'
        )
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
            f'<rect width="{w}" height="{h}" fill="{bg}"/>{"".join(bars)}'
            f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Stress-Test Leverage vs Covenant (6.25x max)</text></svg>')


def render_covenant_headroom(params: dict = None) -> str:
    params = params or {}

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    ebitda = _f("ebitda", 55.0)
    debt = _f("debt", 275.0)

    from rcm_mc.data_public.covenant_headroom import compute_covenant_headroom
    r = compute_covenant_headroom(ebitda_ttm_mm=ebitda, total_debt_mm=debt)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]; neg = P["negative"]; warn = P["warning"]

    status_c = pos if r.overall_status == "healthy" else (warn if r.overall_status == "monitoring" else neg)

    kpi_strip = (
        ck_kpi_block("EBITDA TTM", f"${r.platform_ebitda_ttm_mm:,.1f}M", "", "") +
        ck_kpi_block("Total Debt", f"${r.total_debt_mm:,.1f}M", "", "") +
        ck_kpi_block("Leverage", f"{r.total_leverage:.2f}x", "", "") +
        ck_kpi_block("Blended Rate", f"{r.blended_rate_pct:.2f}%", "", "") +
        ck_kpi_block("Next Test", r.next_test_date, "", "") +
        ck_kpi_block("Overall", r.overall_status.upper(), "", "") +
        ck_kpi_block("Covenants", str(len(r.covenants)), "", "") +
        ck_kpi_block("Corpus", f"{r.corpus_deal_count:,}", "", "")
    )

    svg = _stress_svg(r.stress_scenarios)
    cov_tbl = _covenants_table(r.covenants)
    tr_tbl = _tranches_table(r.tranches)
    cu_tbl = _cure_table(r.cure_rights)
    am_tbl = _amort_table(r.amort_schedule)

    # Signature paired viz+dataset: the stress-test leverage SVG on
    # the left, the same scenarios as a table on the right, one rule.
    # hot_rows marks the worst-headroom scenario — the row that
    # actually trips covenants under stress.
    stress_viz = (
        f'<div style="font-size:9px;color:{P["text_dim"]};'
        f'font-family:JetBrains Mono,monospace;letter-spacing:0.1em;'
        f'text-transform:uppercase;font-weight:700;margin-bottom:8px;">'
        'Stress-test leverage vs covenant</div>'
        f'{svg}'
    )
    st_headers, st_rows, st_hot = _stress_paired_rows(r.stress_scenarios)
    stress_paired = ck_paired_block(
        stress_viz,
        data_label="EBITDA stress scenarios &middot; covenant impact",
        data_source="data_public/covenant_headroom.py",
        headers=st_headers,
        rows=st_rows,
        hot_rows=st_hot,
    )

    form = f"""
<form method="GET" action="/covenant-headroom" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">EBITDA TTM ($M)<input name="ebitda" value="{ebitda}" type="number" step="5" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:90px"/></label>
  <label style="font-size:11px;color:{text_dim}">Total Debt ($M)<input name="debt" value="{debt}" type="number" step="25" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:90px"/></label>
  <button type="submit" style="background:{border};color:{text};border:1px solid {border};padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">Run analysis</button>
</form>"""

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    # B11 sweep batch 2 PR 4/10 — bespoke .ck-page-h1 → ck_page_title.
    # Capital-structure page filtered by EBITDA TTM + total debt form
    # inputs. Meta surfaces the load-bearing leverage stats + the
    # overall compliance status (healthy / monitoring / breach) which
    # is the page's single most important read for partners
    # evaluating debt-side risk.
    page_title = ck_page_title(
        "Debt Covenant Headroom Monitor",
        eyebrow="COVENANT HEADROOM",
        meta=(
            f"${r.platform_ebitda_ttm_mm:,.1f}M EBITDA TTM · "
            f"${r.total_debt_mm:,.1f}M debt · "
            f"{r.total_leverage:.2f}x leverage · "
            f"status: {r.overall_status.upper()}"
        ),
    )
    body = f"""
<div class="ck-page-wrap">
  {page_title}
  {form}
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  {stress_paired}
  <div style="{cell}"><div style="{h3}">Covenant Compliance Matrix</div>{cov_tbl}</div>
  <div style="{cell}"><div style="{h3}">Capital Structure — Tranche by Tranche</div>{tr_tbl}</div>
  <div style="{cell}"><div style="{h3}">Cure Rights Available</div>{cu_tbl}</div>
  <div style="{cell}"><div style="{h3}">Debt Amortization Schedule</div>{am_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {status_c};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Covenant Thesis:</strong> Platform at {r.total_leverage:.2f}x leverage on ${r.platform_ebitda_ttm_mm:,.1f}M TTM EBITDA; ${r.total_debt_mm:,.1f}M aggregate debt at {r.blended_rate_pct:.2f}% blended rate.
    Covenant posture is <strong style="color:{status_c}">{_html.escape(r.overall_status)}</strong>; next test {r.next_test_date}.
    Stress test shows breach threshold at roughly -17% EBITDA miss. Cure rights of ~${r.cure_rights[0].cure_equity_needed_mm:,.1f}M equity contribution available from LP pro-rata,
    providing meaningful buffer against technical breach. Cash sweep mechanism expected to pay down ${sum(a.excess_cash_sweep_mm for a in r.amort_schedule):,.1f}M over life of facility — material delevering path.
  </div>
</div>"""

    return chartis_shell(body, "Covenant Headroom", active_nav="/covenant-headroom",
        editorial_intro={
            "eyebrow": "COVENANT HEADROOM",
            "headline": "What the covenant headroom page reveals on this deal.",
            "italic_word": "reveals",
        })
