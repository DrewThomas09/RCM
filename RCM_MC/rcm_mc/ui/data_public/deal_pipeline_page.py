"""Deal Pipeline Tracker page — /deal-pipeline.

Live pipeline funnel, stage conversion, source channel ROI, sector concentration.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _funnel_svg(stages) -> str:
    if not stages:
        return ""
    w, h = 640, 280
    pad_l, pad_r, pad_t, pad_b = 40, 40, 25, 15
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b
    row_h = inner_h / len(stages)

    max_count = max((s.count for s in stages), default=1)

    bg = P["panel"]; acc = P["accent"]; text_dim = P["text_dim"]
    text_faint = P["text_faint"]; text = P["text"]; border = P["border"]

    bars = []
    for i, s in enumerate(stages):
        y = pad_t + i * row_h
        bar_h = row_h - 6
        bw = (s.count / max_count) * inner_w
        x_center = pad_l + (inner_w - bw) / 2

        # Color intensity decreases down the funnel
        opacity = 0.95 - (i * 0.08)
        color = acc if i < len(stages) - 1 else P["positive"]

        bars.append(
            f'<rect x="{x_center:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{bar_h:.1f}" fill="{color}" opacity="{opacity:.2f}"/>'
            # Stage name on left
            f'<text x="{pad_l - 4}" y="{y + bar_h / 2 + 4:.1f}" fill="{text_dim}" font-size="10" '
            f'text-anchor="end" font-family="JetBrains Mono,monospace">{_html.escape(s.stage)}</text>'
            # Count in center
            f'<text x="{pad_l + inner_w / 2:.1f}" y="{y + bar_h / 2 + 4:.1f}" fill="{text}" font-size="11" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace;font-weight:600">{s.count:,} deals</text>'
            # Conversion on right
            f'<text x="{w - pad_r + 4}" y="{y + bar_h / 2 + 4:.1f}" fill="{text_faint}" font-size="10" '
            f'font-family="JetBrains Mono,monospace">{s.conversion_from_prior * 100:.0f}% · {s.avg_days_in_stage}d</text>'
        )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + "".join(bars) +
        f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Sourced → Close Funnel (count · stage-conversion · days)</text>'
        f'</svg>'
    )


def _channel_roi_svg(channels) -> str:
    if not channels:
        return ""
    w = 520
    row_h = 28
    h = len(channels) * row_h + 30
    pad_l = 170

    max_roi = max((c.roi for c in channels), default=1)

    bg = P["panel"]; pos = P["positive"]; neg = P["negative"]
    text_dim = P["text_dim"]; text_faint = P["text_faint"]

    bars = []
    for i, c in enumerate(channels):
        y = 20 + i * row_h
        bh = 16
        bw = min(1, c.roi / max_roi) * (w - pad_l - 60)
        color = pos if c.roi >= 1 else neg
        bars.append(
            f'<text x="{pad_l - 6}" y="{y + bh - 2}" fill="{text_dim}" font-size="10" '
            f'text-anchor="end" font-family="JetBrains Mono,monospace">{_html.escape(c.channel)}</text>'
            f'<rect x="{pad_l}" y="{y}" width="{bw:.1f}" height="{bh}" fill="{color}" opacity="0.85"/>'
            f'<text x="{pad_l + bw + 4:.1f}" y="{y + bh - 2}" fill="{color}" font-size="10" '
            f'font-family="JetBrains Mono,monospace;font-weight:600">{c.roi:.1f}x ROI</text>'
        )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + "".join(bars) +
        f'<text x="10" y="12" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Source Channel ROI (MOIC gain / sourcing cost)</text>'
        f'</svg>'
    )


def _stage_table(stages) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    cols = [("Stage","left"),("Count","right"),("Conv from Prior","right"),
            ("Cum Conversion","right"),("Avg Days","right"),("Total EV ($M)","right"),("Avg EV ($M)","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, s in enumerate(stages):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:{"600" if i == 0 or i == len(stages) - 1 else "400"}">{_html.escape(s.stage)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{s.count:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.conversion_from_prior * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["positive"]};font-weight:600">{s.cumulative_conversion * 100:.2f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.avg_days_in_stage}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${s.total_ev_mm:,.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${s.avg_ev_mm:,.1f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _channel_table(channels) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Source Channel","left"),("Sourced","right"),("Close Rate","right"),
            ("Closed","right"),("Avg MOIC","right"),("Cost/Close ($K)","right"),
            ("Total Cost ($M)","right"),("ROI","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, c in enumerate(channels):
        rb = panel_alt if i % 2 == 0 else bg
        rc = pos if c.roi >= 1 else neg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(c.channel)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{c.deals_sourced}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{c.close_rate * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">{c.closed_deals}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{c.avg_moic:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${c.cost_per_close_k:,.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${c.total_cost_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{rc};font-weight:600">{c.roi:.1f}x</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _sector_table(sectors) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    cols = [("Sector","left"),("Deals","right"),("Pipeline EV ($M)","right"),
            ("Median EV/EBITDA","right"),("Avg Days","right"),("% of Pipeline","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, s in enumerate(sectors):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(s.sector)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{s.pipeline_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${s.pipeline_ev_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.median_ebitda_mult:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.avg_days_in_pipeline}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{s.pct_of_pipeline * 100:.1f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _deal_table(deals) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    cols = [("Company","left"),("Sector","left"),("Stage","left"),
            ("EV ($M)","right"),("EV/EBITDA","right"),("Days","right"),
            ("Probability","right"),("Channel","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, d in enumerate(deals[:40]):
        rb = panel_alt if i % 2 == 0 else bg
        prob_color = P["positive"] if d.probability >= 0.6 else (P["accent"] if d.probability >= 0.3 else P["warning"])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(d.company)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(d.sector)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(d.stage)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${d.ev_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{d.ev_ebitda:.1f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{d.days_in_pipeline}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{prob_color};font-weight:600">{d.probability * 100:.0f}%</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(d.source_channel)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def render_deal_pipeline(params: dict = None) -> str:
    params = params or {}

    def _i(name, default):
        try: return int(params.get(name, default))
        except (ValueError, TypeError): return default

    sourced = _i("sourced", 800)

    from rcm_mc.data_public.deal_pipeline import compute_deal_pipeline
    r = compute_deal_pipeline(sourced_count=sourced)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Sourced YTD", f"{sourced:,}", "", "") +
        ck_kpi_block("Active Pipeline", f"{r.total_active_deals:,}", "", "") +
        ck_kpi_block("Pipeline EV", f"${r.total_pipeline_ev_mm:,.0f}M", "", "") +
        ck_kpi_block("Prob-Weighted Close", f"${r.weighted_closed_ev_mm:,.0f}M", "", "") +
        ck_kpi_block("End-to-End Conv", f"{r.end_to_end_conversion_pct:.2f}%", "", "") +
        ck_kpi_block("Avg Days (Src→Close)", f"{r.avg_days_source_to_close}", "", "") +
        ck_kpi_block("Source Channels", str(len(r.channels)), "", "") +
        ck_kpi_block("Sectors in Pipeline", str(len(r.sector_breakdown)), "", "")
    )

    funnel_svg = _funnel_svg(r.stages)
    channel_svg = _channel_roi_svg(r.channels)
    stage_tbl = _stage_table(r.stages)
    channel_tbl = _channel_table(r.channels)
    sector_tbl = _sector_table(r.sector_breakdown)
    deal_tbl = _deal_table(r.pipeline_deals)

    form = f"""
<form method="GET" action="/deal-pipeline" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Sourced YTD
    <input name="sourced" value="{sourced}" type="number" step="50"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/>
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
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Deal Pipeline Tracker</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">
      Sourcing funnel, stage conversion, channel ROI, sector concentration — {r.corpus_deal_count:,} corpus deals
    </p>
  </div>

  {form}

  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">
    {kpi_strip}
  </div>

  <div style="{cell}">
    <div style="{h3}">Sourcing Funnel</div>
    {funnel_svg}
  </div>

  <div style="{cell}">
    <div style="{h3}">Stage Conversion Detail</div>
    {stage_tbl}
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">
    <div style="{cell}">
      <div style="{h3}">Source Channel ROI</div>
      {channel_svg}
    </div>
    <div style="{cell}">
      <div style="{h3}">Sector Concentration</div>
      {sector_tbl}
    </div>
  </div>

  <div style="{cell}">
    <div style="{h3}">Source Channel Performance</div>
    {channel_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Active Pipeline — Top 40 Deals</div>
    {deal_tbl}
  </div>

  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};
    padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Pipeline Thesis:</strong>
    {sourced:,} deals sourced YTD → {r.end_to_end_conversion_pct:.1f}% end-to-end conversion.
    Proprietary and Portfolio Follow-on channels dominate ROI; broad auctions remain cheapest but lowest quality.
    ${r.weighted_closed_ev_mm:,.0f}M probability-weighted close in active pipeline.
  </div>

</div>"""

    return chartis_shell(body, "Deal Pipeline Tracker", active_nav="/deal-pipeline")
