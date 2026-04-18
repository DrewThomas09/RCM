"""Debt Covenant Headroom Monitor — /covenant-headroom."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _covenants_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]; acc = P["accent"]
    cols = [("Covenant","left"),("Actual","right"),("Limit","right"),("Direction","center"),
            ("Headroom","right"),("Risk","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    risk_c = {"low": pos, "medium": warn, "high": neg}
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        rc = risk_c.get(c.breach_risk, text_dim)
        hr_c = pos if c.headroom_pct > 0.25 else (warn if c.headroom_pct > 0.10 else neg)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(c.name)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{c.actual:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{c.limit:,.2f}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(c.direction)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{hr_c};font-weight:700">{c.headroom_pct * 100:+.1f}%</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{rc};border:1px solid {rc};border-radius:2px;letter-spacing:0.06em">{_html.escape(c.breach_risk)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _tranches_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; neg = P["negative"]; acc = P["accent"]
    cols = [("Tranche","left"),("Balance ($M)","right"),("Rate Type","left"),("Spread (bps)","right"),
            ("All-In Rate","right"),("Maturity","right"),("Covenant Type","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, t in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(t.tranche)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">${t.balance_mm:,.2f}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(t.rate_type)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{t.spread_bps if t.spread_bps else "—"}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:600">{t.all_in_rate_pct:,.2f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{t.maturity_year}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(t.covenant_type)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _stress_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Scenario","left"),("EBITDA Delta","right"),("Projected EBITDA ($M)","right"),
            ("Projected Leverage","right"),("Status","center"),("Headroom","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    status_c = {"in compliance": pos, "tight / monitoring": warn, "technical breach": warn, "material breach": neg}
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        sc = status_c.get(s.covenant_status, text_dim)
        hr_c = pos if s.headroom_pct > 0.15 else (warn if s.headroom_pct > 0 else neg)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(s.scenario)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg if s.ebitda_delta_pct < 0 else text_dim}">{s.ebitda_delta_pct * 100:+.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${s.projected_ebitda_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{s.projected_leverage:,.2f}x</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em">{_html.escape(s.covenant_status)}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{hr_c};font-weight:600">{s.headroom_pct * 100:+.1f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _cure_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Cure Right","left"),("Equity Needed ($M)","right"),("Mechanism","left"),
            ("Time (days)","right"),("Rate Penalty","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(c.covenant)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:600">${c.cure_equity_needed_mm:,.2f}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.cure_mechanism)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{c.time_to_cure_days}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["negative"]}">{c.penalty_interest_bps}bps</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _amort_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; acc = P["accent"]
    cols = [("Year","left"),("Opening ($M)","right"),("Mandatory ($M)","right"),
            ("Cash Sweep ($M)","right"),("Voluntary ($M)","right"),("Closing ($M)","right"),("Interest ($M)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, a in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{a.year}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${a.opening_balance_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${a.mandatory_amort_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">${a.excess_cash_sweep_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">${a.voluntary_prepay_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">${a.closing_balance_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg}">${a.interest_expense_mm:,.2f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


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
    st_tbl = _stress_table(r.stress_scenarios)
    cu_tbl = _cure_table(r.cure_rights)
    am_tbl = _amort_table(r.amort_schedule)

    form = f"""
<form method="GET" action="/covenant-headroom" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">EBITDA TTM ($M)<input name="ebitda" value="{ebitda}" type="number" step="5" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:90px"/></label>
  <label style="font-size:11px;color:{text_dim}">Total Debt ($M)<input name="debt" value="{debt}" type="number" step="25" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:90px"/></label>
  <button type="submit" style="background:{border};color:{text};border:1px solid {border};padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">Run</button>
</form>"""

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Debt Covenant Headroom Monitor</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">Covenant compliance · stress scenarios · cure rights · amortization schedule · maturity wall — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  {form}
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Stress-Test Leverage vs Covenant</div>{svg}</div>
  <div style="{cell}"><div style="{h3}">Covenant Compliance Matrix</div>{cov_tbl}</div>
  <div style="{cell}"><div style="{h3}">Capital Structure — Tranche by Tranche</div>{tr_tbl}</div>
  <div style="{cell}"><div style="{h3}">EBITDA Stress Scenarios — Covenant Impact</div>{st_tbl}</div>
  <div style="{cell}"><div style="{h3}">Cure Rights Available</div>{cu_tbl}</div>
  <div style="{cell}"><div style="{h3}">Debt Amortization Schedule</div>{am_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {status_c};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Covenant Thesis:</strong> Platform at {r.total_leverage:.2f}x leverage on ${r.platform_ebitda_ttm_mm:,.1f}M TTM EBITDA; ${r.total_debt_mm:,.1f}M aggregate debt at {r.blended_rate_pct:.2f}% blended rate.
    Covenant posture is <strong style="color:{status_c}">{_html.escape(r.overall_status)}</strong>; next test {r.next_test_date}.
    Stress test shows breach threshold at roughly -17% EBITDA miss. Cure rights of ~${r.cure_rights[0].cure_equity_needed_mm:,.1f}M equity contribution available from LP pro-rata,
    providing meaningful buffer against technical breach. Cash sweep mechanism expected to pay down ${sum(a.excess_cash_sweep_mm for a in r.amort_schedule):,.1f}M over life of facility — material delevering path.
  </div>
</div>"""

    return chartis_shell(body, "Covenant Headroom", active_nav="/covenant-headroom")
