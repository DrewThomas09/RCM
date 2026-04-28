"""Debt Service Coverage Tracker page — /debt-service.

DSCR, interest coverage, leverage multiples, covenant headroom and stress testing.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _dscr_trend_svg(schedule) -> str:
    if not schedule:
        return ""
    w, h = 540, 200
    pad_l, pad_r, pad_t, pad_b = 50, 30, 20, 40
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b

    dscrs = [c.dscr for c in schedule]
    int_covs = [c.interest_coverage for c in schedule]
    max_v = max(max(dscrs), max(int_covs)) * 1.10 if schedule else 4.0

    bg = P["panel"]; acc = P["accent"]; pos = P["positive"]
    warn = P["warning"]; text_faint = P["text_faint"]; border = P["border"]

    def _line(values, color):
        pts = []
        for i, v in enumerate(values):
            x = pad_l + (i / max(len(schedule) - 1, 1)) * inner_w
            y = (h - pad_b) - (v / max_v) * inner_h
            pts.append(f"{x:.1f},{y:.1f}")
        line = f'<polyline points="{" ".join(pts)}" fill="none" stroke="{color}" stroke-width="2"/>'
        circles = "".join(
            f'<circle cx="{x}" cy="{y}" r="3" fill="{color}"/>'
            for p in pts
            for x, y in [map(float, p.split(","))]
        )
        return line

    # Zones
    zones = (
        f'<rect x="{pad_l}" y="{(h - pad_b) - (1.0 / max_v) * inner_h}" '
        f'width="{inner_w}" height="{(1.0 / max_v) * inner_h}" fill="{P["negative"]}" opacity="0.1"/>'
        f'<rect x="{pad_l}" y="{(h - pad_b) - (1.5 / max_v) * inner_h}" '
        f'width="{inner_w}" height="{(0.5 / max_v) * inner_h}" fill="{warn}" opacity="0.08"/>'
    )

    dscr_line = _line(dscrs, acc)
    int_line = _line(int_covs, pos)

    # Year labels
    labels = []
    for i, c in enumerate(schedule):
        x = pad_l + (i / max(len(schedule) - 1, 1)) * inner_w
        labels.append(
            f'<text x="{x:.1f}" y="{h - pad_b + 14}" fill="{text_faint}" font-size="9" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace">Y{c.year}</text>'
        )

    # Y ticks
    ticks = []
    for v in [0, 1.0, 2.0, 3.0]:
        if v <= max_v:
            yp = (h - pad_b) - (v / max_v) * inner_h
            ticks.append(
                f'<line x1="{pad_l - 4}" y1="{yp}" x2="{w - pad_r}" y2="{yp}" stroke="{border}" stroke-width="0.5"/>'
                f'<text x="{pad_l - 6}" y="{yp + 3}" fill="{text_faint}" font-size="9" '
                f'text-anchor="end" font-family="JetBrains Mono,monospace">{v:.1f}x</text>'
            )

    legend = (
        f'<line x1="{pad_l}" y1="10" x2="{pad_l + 20}" y2="10" stroke="{acc}" stroke-width="2"/>'
        f'<text x="{pad_l + 24}" y="13" fill="{P["text_dim"]}" font-size="9" font-family="JetBrains Mono,monospace">DSCR</text>'
        f'<line x1="{pad_l + 70}" y1="10" x2="{pad_l + 90}" y2="10" stroke="{pos}" stroke-width="2"/>'
        f'<text x="{pad_l + 94}" y="13" fill="{P["text_dim"]}" font-size="9" font-family="JetBrains Mono,monospace">Interest Coverage</text>'
    )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + zones + "".join(ticks) + legend + dscr_line + int_line + "".join(labels)
        + f'</svg>'
    )


def _leverage_svg(schedule) -> str:
    if not schedule:
        return ""
    w, h = 540, 180
    pad_l, pad_r, pad_t, pad_b = 50, 30, 20, 40
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b

    max_lev = max(c.total_leverage for c in schedule) * 1.10 if schedule else 6.0

    bg = P["panel"]; acc = P["accent"]; neg = P["negative"]
    warn = P["warning"]; text_faint = P["text_faint"]; border = P["border"]

    n = len(schedule)
    bw = (inner_w - (n - 1) * 6) / n / 2

    bars = []
    for i, c in enumerate(schedule):
        x_base = pad_l + i * ((inner_w) / n)
        # Total leverage bar (bg)
        th_tot = (c.total_leverage / max_lev) * inner_h
        y_tot = (h - pad_b) - th_tot
        # Senior leverage (fg)
        th_sr = (c.sr_leverage / max_lev) * inner_h
        y_sr = (h - pad_b) - th_sr
        bars.append(f'<rect x="{x_base:.1f}" y="{y_tot:.1f}" width="{bw * 2:.1f}" height="{th_tot:.1f}" fill="{warn}" opacity="0.55"/>')
        bars.append(f'<rect x="{x_base:.1f}" y="{y_sr:.1f}" width="{bw * 2:.1f}" height="{th_sr:.1f}" fill="{acc}" opacity="0.85"/>')
        bars.append(
            f'<text x="{x_base + bw:.1f}" y="{y_tot - 4:.1f}" fill="{P["text_dim"]}" font-size="9" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace">{c.total_leverage:.1f}x</text>'
            f'<text x="{x_base + bw:.1f}" y="{h - pad_b + 14}" fill="{text_faint}" font-size="9" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace">Y{c.year}</text>'
        )

    legend = (
        f'<rect x="{pad_l}" y="4" width="10" height="10" fill="{acc}" opacity="0.85"/>'
        f'<text x="{pad_l + 14}" y="13" fill="{P["text_dim"]}" font-size="9" font-family="JetBrains Mono,monospace">Senior Leverage</text>'
        f'<rect x="{pad_l + 100}" y="4" width="10" height="10" fill="{warn}" opacity="0.55"/>'
        f'<text x="{pad_l + 114}" y="13" fill="{P["text_dim"]}" font-size="9" font-family="JetBrains Mono,monospace">Total Leverage</text>'
    )

    ticks = []
    for v in [0, max_lev / 2, max_lev]:
        yp = (h - pad_b) - (v / max_lev) * inner_h
        ticks.append(
            f'<line x1="{pad_l - 4}" y1="{yp}" x2="{w - pad_r}" y2="{yp}" stroke="{border}" stroke-width="0.5"/>'
            f'<text x="{pad_l - 6}" y="{yp + 3}" fill="{text_faint}" font-size="9" '
            f'text-anchor="end" font-family="JetBrains Mono,monospace">{v:.1f}x</text>'
        )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + "".join(ticks) + legend + "".join(bars) +
        f'</svg>'
    )


def _tranche_table(tranches) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    cols = [("Tranche","left"),("Principal ($M)","right"),("Rate","right"),
            ("Amort %/yr","right"),("Balance ($M)","right"),("Interest ($M)","right"),("Amortization ($M)","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, t in enumerate(tranches):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(t.label)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${t.principal_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{t.rate_pct:.2f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{t.amort_pct_per_yr:.2f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${t.balance_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${t.interest_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${t.amortization_mm:,.2f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _covenant_table(covenants) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    status_colors = {"compliant": P["positive"], "tight": P["warning"], "breach": P["negative"]}
    cols = [("Covenant","left"),("Threshold","right"),("Current","right"),
            ("Headroom","right"),("Status","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, c in enumerate(covenants):
        rb = panel_alt if i % 2 == 0 else bg
        color = status_colors.get(c.status, text_dim)
        head_str = f"{c.headroom_pct * 100:+.1f}%" if c.headroom_pct else "0.0%"
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(c.label)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{c.threshold:.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{c.current:.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{color}">{head_str}</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{color};border:1px solid {color};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{c.status}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _stress_table(scenarios) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    cols = [("Scenario","left"),("Rev Shock","right"),("Margin Δ","right"),("Rate Δ","right"),
            ("Stressed EBITDA","right"),("DSCR","right"),("Total Lev","right"),("Result","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, s in enumerate(scenarios):
        rb = panel_alt if i % 2 == 0 else bg
        res_color = P["negative"] if s.breach else P["positive"]
        res_text = "BREACH" if s.breach else "PASS"
        desc = s.breach_description if s.breach else "within covenants"
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(s.label)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.revenue_shock_pct * 100:+.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.margin_shock_pp * 100:+.1f}pp</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.rate_shock_bps:+d}bps</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${s.stressed_ebitda_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{res_color};font-weight:600">{s.stressed_dscr:.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{res_color}">{s.stressed_total_lev:.2f}x</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{res_color};border:1px solid {res_color};border-radius:2px;letter-spacing:0.06em">{res_text}</span> <span style="font-size:10px;color:{text_dim};margin-left:8px">{_html.escape(desc)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _schedule_table(schedule) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    cols = [("Year","left"),("Revenue","right"),("EBITDA","right"),("Cash Int.","right"),
            ("Amort.","right"),("Debt Svc","right"),("DSCR","right"),
            ("Int. Cov","right"),("Sr Lev","right"),("Total Lev","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, c in enumerate(schedule):
        rb = panel_alt if i % 2 == 0 else bg
        dscr_color = pos if c.dscr >= 1.5 else (P["warning"] if c.dscr >= 1.1 else P["negative"])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">Year {c.year}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${c.revenue_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${c.ebitda_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${c.cash_interest_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${c.amortization_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${c.total_debt_service_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{dscr_color};font-weight:600">{c.dscr:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{c.interest_coverage:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{c.sr_leverage:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{c.total_leverage:.2f}x</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def render_debt_service(params: dict = None) -> str:
    params = params or {}

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    def _i(name, default):
        try: return int(params.get(name, default))
        except (ValueError, TypeError): return default

    ev = _f("ev", 300.0)
    mult = _f("mult", 12.0)
    margin = _f("margin", 0.18)
    hold = _i("hold_years", 5)
    growth = _f("growth", 0.05)

    from rcm_mc.data_public.debt_service import compute_debt_service
    r = compute_debt_service(ev_mm=ev, entry_multiple=mult, ebitda_margin=margin,
                              hold_years=hold, revenue_growth_pct=growth)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; neg = P["negative"]; warn = P["warning"]; acc = P["accent"]

    total_debt = sum(t.principal_mm for t in r.tranches)
    current_dscr = r.coverage_schedule[0].dscr if r.coverage_schedule else 0

    kpi_strip = (
        ck_kpi_block("EV", f"${r.ev_mm:,.0f}M", "", "") +
        ck_kpi_block("EBITDA", f"${r.ebitda_mm:,.2f}M", "", "") +
        ck_kpi_block("Size Bucket", r.size_bucket, "", "") +
        ck_kpi_block("Total Debt", f"${total_debt:,.0f}M", "", "") +
        ck_kpi_block("Equity %", f"{r.equity_pct * 100:.1f}%", "", "") +
        ck_kpi_block("Blended Rate", f"{r.blended_rate_pct:.2f}%", "", "") +
        ck_kpi_block("Entry DSCR", f"{current_dscr:.2f}x", "", "") +
        ck_kpi_block("Stress Breaches", str(sum(1 for s in r.stress_scenarios if s.breach)), "", "")
    )

    dscr_svg = _dscr_trend_svg(r.coverage_schedule)
    lev_svg = _leverage_svg(r.coverage_schedule)
    tranche_tbl = _tranche_table(r.tranches)
    cov_tbl = _covenant_table(r.covenants)
    stress_tbl = _stress_table(r.stress_scenarios)
    sched_tbl = _schedule_table(r.coverage_schedule)

    form = f"""
<form method="GET" action="/debt-service" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">EV ($M)
    <input name="ev" value="{ev}" type="number" step="10"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Entry Multiple
    <input name="mult" value="{mult}" type="number" step="0.5"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:70px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">EBITDA Margin
    <input name="margin" value="{margin}" type="number" step="0.01"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:60px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Hold (yrs)
    <input name="hold_years" value="{hold}" type="number" min="2" max="10"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:50px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Revenue Growth
    <input name="growth" value="{growth}" type="number" step="0.01"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:60px"/>
  </label>
  <button type="submit"
    style="background:{border};color:{text};border:1px solid {border};
    padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">Run analysis</button>
</form>"""

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">

  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Debt Service Coverage Tracker</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">
      DSCR, interest coverage, covenant headroom, and stress testing — ${r.ev_mm:,.0f}M deal at {r.entry_multiple:.1f}x — {r.corpus_deal_count:,} corpus deals
    </p>
  </div>

  {form}

  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">
    {kpi_strip}
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">
    <div style="{cell}">
      <div style="{h3}">DSCR &amp; Interest Coverage Trajectory</div>
      {dscr_svg}
    </div>
    <div style="{cell}">
      <div style="{h3}">Leverage Multiple Paydown</div>
      {lev_svg}
    </div>
  </div>

  <div style="{cell}">
    <div style="{h3}">Debt Tranches</div>
    {tranche_tbl}
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">
    <div style="{cell}">
      <div style="{h3}">Covenant Compliance (Entry)</div>
      {cov_tbl}
    </div>
    <div style="{cell}">
      <div style="{h3}">Package Summary</div>
      <div style="font-family:JetBrains Mono,monospace;font-size:11px;color:{text};line-height:1.9">
        <div><span style="color:{text_dim}">Size bucket:</span> {r.size_bucket}</div>
        <div><span style="color:{text_dim}">Entry multiple:</span> {r.entry_multiple:.2f}x</div>
        <div><span style="color:{text_dim}">EBITDA:</span> ${r.ebitda_mm:,.2f}M</div>
        <div><span style="color:{text_dim}">Total debt:</span> ${total_debt:,.0f}M ({(total_debt / r.ev_mm * 100):.1f}% of EV)</div>
        <div><span style="color:{text_dim}">Equity:</span> ${(r.ev_mm - total_debt):,.0f}M ({r.equity_pct * 100:.1f}% of EV)</div>
        <div><span style="color:{text_dim}">Blended cash rate:</span> {r.blended_rate_pct:.2f}%</div>
        <div><span style="color:{text_dim}">Annual cash interest:</span> ${sum(t.interest_mm for t in r.tranches):,.2f}M</div>
        <div><span style="color:{text_dim}">Annual amortization:</span> ${sum(t.amortization_mm for t in r.tranches):,.2f}M</div>
      </div>
    </div>
  </div>

  <div style="{cell}">
    <div style="{h3}">Stress Test Scenarios</div>
    {stress_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Year-by-Year Debt Service Schedule</div>
    {sched_tbl}
  </div>

</div>"""

    return chartis_shell(body, "Debt Service Coverage", active_nav="/debt-service")
