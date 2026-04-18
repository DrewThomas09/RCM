"""Peer Valuation Analyzer page — /peer-valuation.

Football-field valuation range from trading comps, precedent transactions,
control premium, size premium.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _football_field_svg(ranges) -> str:
    """Classic football-field valuation range."""
    if not ranges:
        return ""
    w, h = 640, max(220, 40 * len(ranges) + 60)
    pad_l, pad_r, pad_t, pad_b = 200, 40, 35, 30
    inner_w = w - pad_l - pad_r
    row_h = (h - pad_t - pad_b) / len(ranges)

    # Global min/max EV across ranges
    all_vals = []
    for r in ranges:
        all_vals.extend([r.low_ev_mm, r.high_ev_mm])
    min_v = min(all_vals) * 0.85 if all_vals else 0
    max_v = max(all_vals) * 1.05 if all_vals else 1
    span = max_v - min_v or 1

    bg = P["panel"]; acc = P["accent"]; pos = P["positive"]
    text_dim = P["text_dim"]; text_faint = P["text_faint"]; border = P["border"]

    def _x(val):
        return pad_l + (val - min_v) / span * inner_w

    bars = []
    for i, r in enumerate(ranges):
        y = pad_t + i * row_h + 4
        bar_h = row_h - 16
        x_low = _x(r.low_ev_mm)
        x_med = _x(r.median_ev_mm)
        x_high = _x(r.high_ev_mm)
        bw = x_high - x_low

        bars.append(
            f'<text x="{pad_l - 8}" y="{y + bar_h / 2 + 4}" fill="{text_dim}" font-size="10" '
            f'text-anchor="end" font-family="JetBrains Mono,monospace">{_html.escape(r.methodology[:28])}</text>'
            # Range bar
            f'<rect x="{x_low:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{bar_h:.1f}" fill="{acc}" opacity="0.35"/>'
            # Median line
            f'<line x1="{x_med:.1f}" y1="{y:.1f}" x2="{x_med:.1f}" y2="{y + bar_h:.1f}" stroke="{P["text"]}" stroke-width="2"/>'
            # Labels
            f'<text x="{x_low:.1f}" y="{y - 3:.1f}" fill="{text_faint}" font-size="9" text-anchor="middle" font-family="JetBrains Mono,monospace">${r.low_ev_mm:,.0f}</text>'
            f'<text x="{x_med:.1f}" y="{y - 3:.1f}" fill="{P["text"]}" font-size="9" text-anchor="middle" font-family="JetBrains Mono,monospace;font-weight:600">${r.median_ev_mm:,.0f}</text>'
            f'<text x="{x_high:.1f}" y="{y - 3:.1f}" fill="{text_faint}" font-size="9" text-anchor="middle" font-family="JetBrains Mono,monospace">${r.high_ev_mm:,.0f}</text>'
        )

    # X-axis ticks
    ticks = []
    for tv in [min_v, (min_v + max_v) / 2, max_v]:
        x = _x(tv)
        ticks.append(
            f'<line x1="{x:.1f}" y1="{pad_t}" x2="{x:.1f}" y2="{h - pad_b}" stroke="{border}" stroke-width="0.5" stroke-dasharray="2,3" opacity="0.4"/>'
            f'<text x="{x:.1f}" y="{h - pad_b + 14}" fill="{text_faint}" font-size="9" text-anchor="middle" '
            f'font-family="JetBrains Mono,monospace">${tv:,.0f}M</text>'
        )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + "".join(ticks) + "".join(bars) +
        f'<text x="10" y="18" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Football Field — Implied Enterprise Value ($M)</text>'
        f'</svg>'
    )


def _comps_table(comps) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    size_colors = {"Large-cap": P["positive"], "Mid-cap": P["accent"], "Small-cap": P["warning"]}
    cols = [("Company","left"),("Market Cap ($M)","right"),("EV/EBITDA","right"),
            ("EV/Revenue","right"),("P/E","right"),("EBITDA Margin","right"),("Size","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, c in enumerate(comps):
        rb = panel_alt if i % 2 == 0 else bg
        sc = size_colors.get(c.size_category, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(c.company)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${c.market_cap_mm:,.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]};font-weight:600">{c.ev_ebitda:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{c.ev_revenue:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{c.pe_ratio:.1f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{c.ebitda_margin * 100:.1f}%</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em">{c.size_category}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _precedent_table(precedents) -> str:
    if not precedents:
        return f'<p style="color:{P["text_dim"]};font-size:11px;padding:12px 0">No precedent transactions found in corpus for this sector.</p>'
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    cols = [("Target","left"),("Acquirer","left"),("Year","right"),
            ("EV ($M)","right"),("EV/EBITDA","right"),("Sector","left"),("Status","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, p in enumerate(precedents):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(p.target_company)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(p.acquirer)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{p.year}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${p.ev_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]};font-weight:600">{p.ev_ebitda:.2f}x</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.sector)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.status)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _ranges_table(ranges) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    cols = [("Methodology","left"),("Low EV","right"),("Median EV","right"),("High EV","right"),
            ("Low Mult","right"),("Median Mult","right"),("High Mult","right"),("Basis","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, r in enumerate(ranges):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(r.methodology)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${r.low_ev_mm:,.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">${r.median_ev_mm:,.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${r.high_ev_mm:,.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{r.low_multiple:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]};font-weight:600">{r.median_multiple:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{r.high_multiple:.2f}x</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:260px">{_html.escape(r.basis)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _size_premium_table(sizes) -> str:
    if not sizes:
        return f'<p style="color:{P["text_dim"]};font-size:11px;padding:12px 0">Insufficient precedent transactions for size bucket analysis.</p>'
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    cols = [("Size Bucket","left"),("Median Multiple","right"),("N Transactions","right"),("Premium to Small","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, s in enumerate(sizes):
        rb = panel_alt if i % 2 == 0 else bg
        prem_c = pos if s.premium_to_small > 0 else P["text_faint"]
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(s.size_bucket)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]};font-weight:600">{s.median_mult:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.n_transactions}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{prem_c};font-weight:600">{s.premium_to_small * 100:+.1f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def render_peer_valuation(params: dict = None) -> str:
    params = params or {}
    sector = params.get("sector", "Physician Services") or "Physician Services"

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    ebitda = _f("ebitda", 25.0)
    revenue = _f("revenue", 140.0)

    from rcm_mc.data_public.peer_valuation import compute_peer_valuation
    r = compute_peer_valuation(sector=sector, target_ebitda_mm=ebitda, target_revenue_mm=revenue)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Sector", sector, "", "") +
        ck_kpi_block("Target EBITDA", f"${r.target_ebitda_mm:,.1f}M", "", "") +
        ck_kpi_block("Target Revenue", f"${r.target_revenue_mm:,.1f}M", "", "") +
        ck_kpi_block("Low EV", f"${r.implied_ev_low_mm:,.0f}M", "", "") +
        ck_kpi_block("Median EV", f"${r.implied_ev_median_mm:,.0f}M", "", "") +
        ck_kpi_block("High EV", f"${r.implied_ev_high_mm:,.0f}M", "", "") +
        ck_kpi_block("Implied Mult", f"{r.current_implied_mult:.2f}x", "", "") +
        ck_kpi_block("Precedents", str(len(r.precedent_transactions)), "", "")
    )

    field_svg = _football_field_svg(r.valuation_ranges)
    comps_tbl = _comps_table(r.trading_comps)
    precedent_tbl = _precedent_table(r.precedent_transactions)
    ranges_tbl = _ranges_table(r.valuation_ranges)
    size_tbl = _size_premium_table(r.size_premiums)

    form = f"""
<form method="GET" action="/peer-valuation" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Sector
    <input name="sector" value="{_html.escape(sector)}"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:180px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Target EBITDA ($M)
    <input name="ebitda" value="{ebitda}" type="number" step="1"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:70px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Target Revenue ($M)
    <input name="revenue" value="{revenue}" type="number" step="10"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/>
  </label>
  <button type="submit"
    style="background:{border};color:{text};border:1px solid {border};
    padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">Run</button>
</form>"""

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">

  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Peer Valuation Analyzer</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">
      Trading comps + precedent transactions + control premium = football-field valuation for {_html.escape(sector)} — {r.corpus_deal_count:,} corpus deals
    </p>
  </div>

  {form}

  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">
    {kpi_strip}
  </div>

  <div style="{cell}">
    <div style="{h3}">Football Field — Implied EV Range</div>
    {field_svg}
  </div>

  <div style="{cell}">
    <div style="{h3}">Valuation Range Detail</div>
    {ranges_tbl}
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">
    <div style="{cell}">
      <div style="{h3}">Public Trading Comps ({len(r.trading_comps)})</div>
      {comps_tbl}
    </div>
    <div style="{cell}">
      <div style="{h3}">Size Premium Analysis</div>
      {size_tbl}
    </div>
  </div>

  <div style="{cell}">
    <div style="{h3}">Precedent Transactions from Corpus ({len(r.precedent_transactions)})</div>
    {precedent_tbl}
  </div>

  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};
    padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Valuation Thesis:</strong>
    Implied EV range ${r.implied_ev_low_mm:,.0f}M – ${r.implied_ev_high_mm:,.0f}M (median ${r.implied_ev_median_mm:,.0f}M)
    at {r.current_implied_mult:.2f}x EBITDA. Public trading comps anchor the low end; precedent transactions
    set the typical control price; size premium typically adds 10-20% for $500M+ platforms.
  </div>

</div>"""

    return chartis_shell(body, "Peer Valuation", active_nav="/peer-valuation")
