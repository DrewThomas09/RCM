"""Competitive Intelligence page — /competitive-intel.

Competitor landscape, strategic moves, gap analysis, share shift opportunities.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _share_landscape_svg(competitors, our_share: float) -> str:
    if not competitors:
        return ""
    w, h = 540, max(180, len(competitors) * 28 + 70)
    pad_l, pad_r, pad_t = 200, 80, 40
    inner_w = w - pad_l - pad_r
    row_h = 24

    bg = P["panel"]; text_dim = P["text_dim"]; text_faint = P["text_faint"]
    threat_colors = {"high": P["negative"], "medium": P["warning"], "low": P["text_faint"]}

    sorted_c = sorted(competitors, key=lambda c: -c.est_market_share_pct)
    max_share = max([c.est_market_share_pct for c in sorted_c] + [our_share]) or 1

    bars = []
    # Our share row first
    y_us = pad_t
    us_w = our_share / max_share * inner_w
    bars.append(
        f'<text x="{pad_l - 6}" y="{y_us + 16}" fill="{P["accent"]}" font-size="11" '
        f'text-anchor="end" font-family="JetBrains Mono,monospace;font-weight:600">OUR POSITION</text>'
        f'<rect x="{pad_l}" y="{y_us + 4}" width="{us_w:.1f}" height="14" fill="{P["accent"]}" opacity="0.95"/>'
        f'<text x="{pad_l + us_w + 4:.1f}" y="{y_us + 16}" fill="{P["accent"]}" font-size="10" '
        f'font-family="JetBrains Mono,monospace;font-weight:600">{our_share:.2f}%</text>'
    )

    # Divider
    bars.append(f'<line x1="{pad_l - 10}" y1="{y_us + 28}" x2="{w - 10}" y2="{y_us + 28}" stroke="{P["border"]}" stroke-width="1"/>')

    for i, c in enumerate(sorted_c):
        y = y_us + 34 + i * row_h
        bw = c.est_market_share_pct / max_share * inner_w
        tc = threat_colors.get(c.threat_level, text_dim)
        bars.append(
            f'<text x="{pad_l - 6}" y="{y + 14}" fill="{text_dim}" font-size="10" '
            f'text-anchor="end" font-family="JetBrains Mono,monospace">{_html.escape(c.name[:26])}</text>'
            f'<rect x="{pad_l}" y="{y + 2}" width="{bw:.1f}" height="14" fill="{tc}" opacity="0.75"/>'
            f'<text x="{pad_l + bw + 4:.1f}" y="{y + 14}" fill="{P["text_dim"]}" font-size="10" '
            f'font-family="JetBrains Mono,monospace">{c.est_market_share_pct:.1f}% · {_html.escape(c.ownership[:14])}</text>'
        )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + "".join(bars) +
        f'<text x="10" y="20" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Competitive Share Landscape</text>'
        f'</svg>'
    )


def _gap_svg(vs_us) -> str:
    if not vs_us:
        return ""
    w, h = 540, max(200, len(vs_us) * 24 + 30)
    pad_l, pad_r, pad_t = 220, 70, 20
    inner_w = w - pad_l - pad_r
    row_h = 20

    bg = P["panel"]; text_dim = P["text_dim"]; text_faint = P["text_faint"]
    acc = P["accent"]; neg = P["negative"]

    bars = []
    for i, v in enumerate(vs_us):
        y = pad_t + i * row_h + 8
        bh = 12
        # Our score (accent, left portion)
        our_w = v.our_score / 100 * inner_w
        comp_w = v.top_competitor_score / 100 * inner_w
        bars.append(
            f'<text x="{pad_l - 6}" y="{y + bh - 1}" fill="{text_dim}" font-size="10" '
            f'text-anchor="end" font-family="JetBrains Mono,monospace">{_html.escape(v.dimension[:28])}</text>'
            # Competitor bar (background)
            f'<rect x="{pad_l}" y="{y}" width="{comp_w:.1f}" height="{bh}" fill="{text_faint}" opacity="0.35"/>'
            # Our bar (accent)
            f'<rect x="{pad_l}" y="{y}" width="{our_w:.1f}" height="{bh}" fill="{acc}" opacity="0.85"/>'
            # Labels
            f'<text x="{pad_l + comp_w + 4:.1f}" y="{y + bh - 1}" fill="{text_faint}" font-size="9" '
            f'font-family="JetBrains Mono,monospace">{v.our_score} vs {v.top_competitor_score} ({v.gap:+d})</text>'
        )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + "".join(bars) +
        f'</svg>'
    )


def _competitors_table(competitors) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    threat_colors = {"high": P["negative"], "medium": P["warning"], "low": P["text_faint"]}
    strat_colors = {"scale": P["negative"], "focused": P["accent"], "tech": P["positive"]}
    cols = [("Competitor","left"),("Ownership","left"),("Share %","right"),("Footprint","left"),
            ("Est Rev ($M)","right"),("Positioning","left"),("Strategy","left"),("Threat","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, c in enumerate(competitors):
        rb = panel_alt if i % 2 == 0 else bg
        tc = threat_colors.get(c.threat_level, text_dim)
        sc = strat_colors.get(c.competitive_strategy, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(c.name)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(c.ownership)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{c.est_market_share_pct:.1f}%</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.footprint)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${c.est_revenue_mm:,.0f}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:200px">{_html.escape(c.positioning)}</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em">{c.competitive_strategy}</span></td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{tc};border:1px solid {tc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{c.threat_level}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _moves_table(moves) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    threat_colors = {"high": P["negative"], "medium": P["warning"], "low": P["text_faint"]}
    cols = [("Quarter","left"),("Company","left"),("Move Type","left"),
            ("Value ($M)","right"),("Description","left"),("Threat","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, m in enumerate(moves):
        rb = panel_alt if i % 2 == 0 else bg
        tc = threat_colors.get(m.threat_to_us, text_dim)
        val_str = f"${m.value_mm:,.1f}" if m.value_mm > 0 else (f"${-m.value_mm:,.1f} (impairment)" if m.value_mm < 0 else "—")
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(m.quarter)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(m.company)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(m.move_type)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{val_str}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:320px">{_html.escape(m.description)}</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{tc};border:1px solid {tc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{m.threat_to_us}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _vs_us_table(vs_us) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    cols = [("Dimension","left"),("Our Score","right"),("Top Competitor","right"),
            ("Gap","right"),("Recommended Action","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, v in enumerate(vs_us):
        rb = panel_alt if i % 2 == 0 else bg
        gc = P["negative"] if v.gap <= -25 else (P["warning"] if v.gap <= -10 else P["positive"])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(v.dimension)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]};font-weight:600">{v.our_score}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{v.top_competitor_score}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{gc};font-weight:600">{v.gap:+d}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(v.action)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _opps_table(opps) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    feas_colors = {"high": pos, "medium": P["accent"], "low": P["warning"]}
    cols = [("Segment","left"),("Current Leader","left"),("Displacement Target","right"),
            ("Revenue Opp ($M)","right"),("Time Horizon","left"),("Feasibility","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, o in enumerate(opps):
        rb = panel_alt if i % 2 == 0 else bg
        fc = feas_colors.get(o.feasibility, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(o.segment)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(o.current_leader)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{o.displacement_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">${o.implied_revenue_mm:,.2f}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(o.time_horizon)}</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{fc};border:1px solid {fc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{o.feasibility}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def render_competitive_intel(params: dict = None) -> str:
    params = params or {}
    sector = params.get("sector", "Physician Services") or "Physician Services"

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    revenue = _f("revenue", 80.0)
    share = _f("share", 0.8)

    from rcm_mc.data_public.competitive_intel import compute_competitive_intel
    r = compute_competitive_intel(sector=sector, revenue_mm=revenue, our_market_share_pct=share)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Sector", sector, "", "") +
        ck_kpi_block("Our Share", f"{r.our_market_share_est:.2f}%", "", "") +
        ck_kpi_block("Top-5 Share", f"{r.top_5_share:.1f}%", "", "") +
        ck_kpi_block("Market HHI", f"{r.market_hhi:,}", "", "") +
        ck_kpi_block("Intensity", f"{r.competitive_intensity_score}/100", "", "") +
        ck_kpi_block("Competitors", str(len(r.competitors)), "", "") +
        ck_kpi_block("Recent Moves", str(len(r.recent_moves)), "", "") +
        ck_kpi_block("Share Opps", str(len(r.share_opportunities)), "", "")
    )

    landscape_svg = _share_landscape_svg(r.competitors, r.our_market_share_est)
    gap_svg = _gap_svg(r.vs_us)
    comp_tbl = _competitors_table(r.competitors)
    moves_tbl = _moves_table(r.recent_moves)
    vs_tbl = _vs_us_table(r.vs_us)
    opps_tbl = _opps_table(r.share_opportunities)

    form = f"""
<form method="GET" action="/competitive-intel" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Sector
    <input name="sector" value="{_html.escape(sector)}"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:180px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Our Revenue ($M)
    <input name="revenue" value="{revenue}" type="number" step="10"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Our Share %
    <input name="share" value="{share}" type="number" step="0.1"
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
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Competitive Intelligence Dashboard</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">
      Competitor landscape, strategic moves, gap analysis, share-shift opportunities for {_html.escape(sector)} — {r.corpus_deal_count:,} corpus deals
    </p>
  </div>

  {form}

  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">
    {kpi_strip}
  </div>

  <div style="{cell}">
    <div style="{h3}">Competitive Share Landscape</div>
    {landscape_svg}
  </div>

  <div style="{cell}">
    <div style="{h3}">Gap Analysis — Us vs Top Competitor</div>
    {gap_svg}
  </div>

  <div style="{cell}">
    <div style="{h3}">Competitor Detail</div>
    {comp_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Recent Strategic Moves</div>
    {moves_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Dimensional Gap Analysis</div>
    {vs_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Share-Shift Opportunities</div>
    {opps_tbl}
  </div>

  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};
    padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Competitive Thesis:</strong>
    Market intensity {r.competitive_intensity_score}/100 with HHI of {r.market_hhi:,}. Our {r.our_market_share_est:.2f}%
    share vs top-5 combined {r.top_5_share:.1f}% — fragmented enough for roll-up thesis.
    Key gaps: scale, geography, brand. Top opportunity: commercial self-insured employer
    (${r.share_opportunities[0].implied_revenue_mm:,.0f}M addressable if feasible).
  </div>

</div>"""

    return chartis_shell(body, "Competitive Intel", active_nav="/competitive-intel")
