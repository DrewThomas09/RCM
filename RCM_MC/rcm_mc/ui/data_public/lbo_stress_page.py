"""LBO Model Stress Test — /lbo-stress."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _sensitivity_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]; warn = P["warning"]
    cols = [("Exit Multiple","right"),("Exit EBITDA ($M)","right"),("Exit EV ($M)","right"),
            ("Net Debt ($M)","right"),("Equity Proceeds ($M)","right"),("MOIC","right"),("IRR %","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        m_c = pos if s.moic >= 2.5 else (acc if s.moic >= 1.8 else warn)
        i_c = pos if s.irr_pct >= 0.20 else (acc if s.irr_pct >= 0.12 else warn)
        cells = [
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{s.exit_multiple:.1f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${s.exit_ebitda_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">${s.exit_ev_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["negative"]}">${s.net_debt_at_exit_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${s.equity_proceeds_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{m_c};font-weight:700">{s.moic:,.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{i_c};font-weight:700">{s.irr_pct * 100:+.1f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _tornado_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; acc = P["accent"]
    cols = [("Driver","left"),("Downside","center"),("Base","center"),("Upside","center"),
            ("Down MOIC","right"),("Base MOIC","right"),("Up MOIC","right"),("Swing MOIC","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    sorted_items = sorted(items, key=lambda t: abs(t.swing_moic), reverse=True)
    for i, t in enumerate(sorted_items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = pos if abs(t.swing_moic) <= 0.50 else (acc if abs(t.swing_moic) <= 1.0 else neg)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(t.driver)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg}">{_html.escape(t.downside_value)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{_html.escape(t.base_value)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">{_html.escape(t.upside_value)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg}">{t.downside_moic:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{t.base_moic:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">{t.upside_moic:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{s_c};font-weight:700">{t.swing_moic:+.2f}x</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _covenant_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Year","left"),("EBITDA ($M)","right"),("Total Debt ($M)","right"),("Leverage","right"),
            ("Interest Coverage","right"),("Compliance","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        l_c = pos if c.leverage < 6.0 else (P["warning"] if c.leverage < 6.25 else neg)
        comp_c = pos if c.in_compliance else neg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{c.year}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${c.ebitda_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${c.total_debt_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{l_c};font-weight:700">{c.leverage:,.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">{c.interest_coverage:,.2f}x</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{comp_c};font-weight:700">{"YES" if c.in_compliance else "BREACH"}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _bridge_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; acc = P["accent"]
    cols = [("Component","left"),("Contribution ($M)","right"),("Contribution MOIC","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, b in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        c_c = pos if b.contribution_mm >= 0 else neg
        is_final = "MOIC" in b.component
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:{"700" if is_final else "600"}">{_html.escape(b.component)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{c_c};font-weight:700">${b.contribution_mm:+,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{b.contribution_pct:+.2f}x</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _scenarios_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; acc = P["accent"]
    cols = [("Scenario","left"),("Exit EBITDA ($M)","right"),("Exit Multiple","right"),("Equity ($M)","right"),
            ("MOIC","right"),("IRR","right"),("Probability","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        m_c = pos if s.moic >= 2.5 else (acc if s.moic >= 1.8 else (text_dim if s.moic >= 1.0 else neg))
        i_c = pos if s.irr_pct >= 0.20 else (acc if s.irr_pct >= 0.12 else (text_dim if s.irr_pct >= 0 else neg))
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(s.scenario)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${s.exit_ebitda_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{s.exit_multiple:,.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${s.exit_proceeds_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{m_c};font-weight:700">{s.moic:,.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{i_c};font-weight:700">{s.irr_pct * 100:+.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.probability_pct * 100:.0f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _tornado_svg(items) -> str:
    if not items: return ""
    # Sort by swing magnitude
    sorted_items = sorted(items, key=lambda t: abs(t.swing_moic), reverse=True)
    w, h = 560, 280
    pad_l = 180
    pad_r = 20
    pad_t = 30
    pad_b = 30
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b
    max_swing = max(abs(t.swing_moic) for t in sorted_items) + 0.1
    bg = P["panel"]; pos = P["positive"]; neg = P["negative"]; text = P["text"]; text_dim = P["text_dim"]
    bar_h = min(22, (inner_h - (len(sorted_items) - 1) * 4) / len(sorted_items))
    center_x = pad_l + inner_w / 2
    elts = [f'<rect width="{w}" height="{h}" fill="{bg}"/>']
    elts.append(f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Tornado Chart: MOIC Sensitivity by Driver</text>')
    elts.append(f'<line x1="{center_x:.1f}" y1="{pad_t}" x2="{center_x:.1f}" y2="{h - pad_b}" stroke="{text_dim}" stroke-width="1" stroke-dasharray="3,3"/>')
    for i, t in enumerate(sorted_items):
        y = pad_t + i * (bar_h + 4)
        # Label
        elts.append(f'<text x="{pad_l - 8}" y="{y + bar_h * 0.7}" fill="{text_dim}" font-size="10" text-anchor="end" font-family="JetBrains Mono,monospace">{_html.escape(t.driver[:22])}</text>')
        # Downside bar
        down_swing = t.base_moic - t.downside_moic
        down_w = (down_swing / max_swing) * (inner_w / 2)
        if down_swing > 0:
            elts.append(f'<rect x="{center_x - down_w:.1f}" y="{y}" width="{down_w:.1f}" height="{bar_h:.1f}" fill="{neg}" opacity="0.85"/>')
            elts.append(f'<text x="{center_x - down_w - 4:.1f}" y="{y + bar_h * 0.7}" fill="{neg}" font-size="9" text-anchor="end" font-family="JetBrains Mono,monospace">{t.downside_moic:.2f}x</text>')
        # Upside bar
        up_swing = t.upside_moic - t.base_moic
        up_w = (up_swing / max_swing) * (inner_w / 2)
        if up_swing > 0:
            elts.append(f'<rect x="{center_x:.1f}" y="{y}" width="{up_w:.1f}" height="{bar_h:.1f}" fill="{pos}" opacity="0.85"/>')
            elts.append(f'<text x="{center_x + up_w + 4:.1f}" y="{y + bar_h * 0.7}" fill="{pos}" font-size="9" font-family="JetBrains Mono,monospace">{t.upside_moic:.2f}x</text>')
    return f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">{"".join(elts)}</svg>'


def render_lbo_stress(params: dict = None) -> str:
    from rcm_mc.data_public.lbo_stress import compute_lbo_stress
    r = compute_lbo_stress()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    b = r.base
    expected_moic = sum(s.moic * s.probability_pct for s in r.scenarios) / sum(s.probability_pct for s in r.scenarios)
    expected_irr = sum(s.irr_pct * s.probability_pct for s in r.scenarios) / sum(s.probability_pct for s in r.scenarios)

    kpi_strip = (
        ck_kpi_block("Purchase Price", f"${b.purchase_price_mm:,.0f}M", "", "") +
        ck_kpi_block("Entry Multiple", f"{b.entry_multiple:,.2f}x", "", "") +
        ck_kpi_block("Equity Check", f"${b.equity_check_mm:,.0f}M", "", "") +
        ck_kpi_block("Initial Leverage", f"{b.initial_leverage:,.2f}x", "", "") +
        ck_kpi_block("Base MOIC", f"{b.projected_moic:,.2f}x", "", "") +
        ck_kpi_block("Base IRR", f"{b.projected_irr_pct * 100:.1f}%", "", "") +
        ck_kpi_block("Expected MOIC", f"{expected_moic:,.2f}x", "(prob-weighted)", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    svg = _tornado_svg(r.tornado)
    s_tbl = _sensitivity_table(r.sensitivity_grid)
    t_tbl = _tornado_table(r.tornado)
    c_tbl = _covenant_table(r.covenant_path)
    b_tbl = _bridge_table(r.returns_bridge)
    sc_tbl = _scenarios_table(r.scenarios)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    top_driver = max(r.tornado, key=lambda t: abs(t.swing_moic))
    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">LBO Model Stress Test</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">Sensitivity analysis · tornado drivers · covenant path · returns bridge · scenario probability weighting — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Tornado Chart — MOIC Sensitivity by Driver</div>{svg}</div>
  <div style="{cell}"><div style="{h3}">Exit Multiple Sensitivity Grid</div>{s_tbl}</div>
  <div style="{cell}"><div style="{h3}">Driver Sensitivity Detail</div>{t_tbl}</div>
  <div style="{cell}"><div style="{h3}">Covenant Compliance Path</div>{c_tbl}</div>
  <div style="{cell}"><div style="{h3}">Returns Bridge — Entry Equity to Exit Proceeds</div>{b_tbl}</div>
  <div style="{cell}"><div style="{h3}">Scenario Outcomes &amp; Probability Weighting</div>{sc_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">LBO Stress Thesis:</strong> Base case {b.projected_moic:,.2f}x MOIC / {b.projected_irr_pct * 100:.1f}% IRR over {b.projected_exit_year - 2026} years.
    Tornado analysis ranks {top_driver.driver} as the highest-sensitivity driver (swing: {top_driver.swing_moic:+.2f}x MOIC across downside-to-upside).
    EBITDA growth trajectory (18% CAGR base case, 12-24% sensitivity range) and exit multiple (14.0x base, 12-16x range) are the primary return drivers.
    Covenant path holds in compliance through year 6 at 2.15x leverage reduction; interest coverage remains >3.0x.
    Probability-weighted expected MOIC {expected_moic:,.2f}x / IRR {expected_irr * 100:.1f}% reflects 40% base case, 25% upside, 25% downside scenarios.
    Material downside (MOIC < 1.0x) probability 10%; Home Run IRR > 30% probability 5%.
  </div>
</div>"""

    return chartis_shell(body, "LBO Stress Test", active_nav="/lbo-stress")
