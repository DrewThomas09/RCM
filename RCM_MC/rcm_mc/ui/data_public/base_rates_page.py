"""Base-Rate Engine — /base-rates.

Multi-dimensional percentile cuts (P25/P50/P75/P90) across EV/EBITDA,
EBITDA margin, MOIC, IRR. Filterable by sector, size, region; rolls up
by sector, size bucket, vintage year, commercial-payer-share bucket.
"""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _fmt(v, kind):
    if kind == "pct":
        return f"{v * 100:.2f}%"
    if kind == "pct1":
        return f"{v * 100:.1f}%"
    if kind == "dollar":
        return f"${v:,.2f}"
    if kind == "mult":
        return f"{v:,.2f}x"
    if kind == "yrs":
        return f"{v:,.1f}y"
    return f"{v:,.2f}"


def _percentile_row_kind(metric: str) -> str:
    if "Margin" in metric or "IRR" in metric or "Commercial" in metric:
        return "pct"
    if "EV/EBITDA" in metric or "MOIC" in metric:
        return "mult"
    if "Hold Years" in metric:
        return "yrs"
    if "$M" in metric:
        return "dollar"
    return "num"


def _percentile_table(rows) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Metric","left"),("N","right"),("P25","right"),("P50 (Median)","right"),
            ("P75","right"),("P90","right"),("Mean","right"),("Min","right"),("Max","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, r in enumerate(rows):
        rb = panel_alt if i % 2 == 0 else bg
        kind = _percentile_row_kind(r.metric)
        def _cell(v):
            return f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_fmt(v, kind)}</td>'
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(r.metric)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{r.n:,}</td>',
            _cell(r.p25),
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{_fmt(r.p50, kind)}</td>',
            _cell(r.p75),
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">{_fmt(r.p90, kind)}</td>',
            _cell(r.mean),
            _cell(r.min),
            _cell(r.max),
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _sector_table(rows) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Sector","left"),("Deals","right"),("Med EV ($M)","right"),("Med EV/EBITDA","right"),
            ("Med EV/Rev","right"),("Med EBITDA Margin","right"),("Med MOIC","right"),("Med IRR","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, s in enumerate(rows[:40]):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(s.sector[:36])}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.deal_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${s.median_ev_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{s.median_ev_ebitda:,.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.median_ev_revenue:,.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.median_ebitda_margin * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">{s.median_moic:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{s.median_irr * 100:.1f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _size_table(rows) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Size Bucket","left"),("Deals","right"),("Med EV/EBITDA","right"),
            ("Med EBITDA Margin","right"),("Med MOIC","right"),("Med Hold Years","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, s in enumerate(rows):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(s.bucket)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.deal_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{s.median_ev_ebitda:,.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.median_ebitda_margin * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">{s.median_moic:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.median_hold_years:,.1f}y</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _vintage_table(rows) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Year","left"),("Deals","right"),("Med EV/EBITDA","right"),("Med EBITDA Margin","right"),("Med MOIC","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, v in enumerate(rows):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{v.year}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{v.deal_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{v.median_ev_ebitda:,.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{v.median_ebitda_margin * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">{v.median_moic:.2f}x</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _comm_table(rows) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Commercial Share Bucket","left"),("Deals","right"),("Med EV/EBITDA","right"),("Med EBITDA Margin","right"),("Med MOIC","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(rows):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(c.comm_bucket)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{c.deal_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{c.median_ev_ebitda:,.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{c.median_ebitda_margin * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">{c.median_moic:.2f}x</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _vintage_svg(rows) -> str:
    if not rows: return ""
    w, h = 560, 200
    pad_l, pad_r, pad_t, pad_b = 50, 20, 20, 40
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b
    max_v = max(r.median_ev_ebitda for r in rows) or 1
    min_v = min(r.median_ev_ebitda for r in rows) or 0
    bg = P["panel"]; acc = P["accent"]; text_dim = P["text_dim"]; text_faint = P["text_faint"]
    n = len(rows)
    x_step = inner_w / max(n - 1, 1)
    pts = []
    circles = []
    labels = []
    for i, r in enumerate(rows):
        x = pad_l + i * x_step
        y_norm = (r.median_ev_ebitda - min_v) / (max_v - min_v + 0.01)
        y = (h - pad_b) - y_norm * inner_h
        pts.append(f"{x:.1f},{y:.1f}")
        circles.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{acc}"/>')
        labels.append(
            f'<text x="{x:.1f}" y="{y - 8:.1f}" fill="{text_dim}" font-size="9" text-anchor="middle" font-family="JetBrains Mono,monospace">{r.median_ev_ebitda:.2f}x</text>'
            f'<text x="{x:.1f}" y="{h - pad_b + 14:.1f}" fill="{text_faint}" font-size="9" text-anchor="middle" font-family="JetBrains Mono,monospace">{r.year}</text>'
        )
    path = f'<polyline points="{" ".join(pts)}" fill="none" stroke="{acc}" stroke-width="2" opacity="0.7"/>'
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
            f'<rect width="{w}" height="{h}" fill="{bg}"/>{path}{"".join(circles)}{"".join(labels)}'
            f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Median EV/EBITDA by Vintage Year</text></svg>')


def render_base_rates(params: dict = None) -> str:
    params = params or {}

    sector = params.get("sector", "")
    size_bucket = params.get("size_bucket", "")
    region = params.get("region", "")

    from rcm_mc.data_public.market_rates import compute_market_rates
    r = compute_market_rates(sector=sector, size_bucket=size_bucket, region=region)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    p50_ev = next((p for p in r.percentile_rows if p.metric == "EV ($M)"), None)
    p50_mult = next((p for p in r.percentile_rows if p.metric == "EV/EBITDA (x)"), None)
    p50_moic = next((p for p in r.percentile_rows if p.metric == "MOIC (x)"), None)
    p50_irr = next((p for p in r.percentile_rows if p.metric == "IRR"), None)
    p50_margin = next((p for p in r.percentile_rows if p.metric == "EBITDA Margin"), None)

    kpi_strip = (
        ck_kpi_block("Matching Deals", f"{r.total_matching:,}", "", "") +
        ck_kpi_block("Median EV", f"${p50_ev.p50:,.0f}M" if p50_ev else "—", "", "") +
        ck_kpi_block("Median EV/EBITDA", f"{p50_mult.p50:,.2f}x" if p50_mult else "—", "", "") +
        ck_kpi_block("P75 EV/EBITDA", f"{p50_mult.p75:,.2f}x" if p50_mult else "—", "", "") +
        ck_kpi_block("Median EBITDA Mgn", f"{p50_margin.p50 * 100:.1f}%" if p50_margin else "—", "", "") +
        ck_kpi_block("Median MOIC", f"{p50_moic.p50:,.2f}x" if p50_moic else "—", "", "") +
        ck_kpi_block("Median IRR", f"{p50_irr.p50 * 100:.1f}%" if p50_irr else "—", "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    size_buckets = ["< $100M (small)", "$100-250M (mid)", "$250-500M (upper-mid)", "$500M-1B (large)", "$1B+ (mega)"]
    regions = ["US", "Northeast", "Southeast", "Midwest", "West", "Southwest", "National", "Pacific"]
    sector_opts = '<option value="">— all sectors —</option>' + "".join(
        f'<option value="{_html.escape(s)}"{" selected" if s == sector else ""}>{_html.escape(s)}</option>'
        for s in ("Primary Care", "ASC", "Behavioral Health", "Dental", "Dermatology", "Physical Therapy",
                  "Cardiology", "Oncology", "Home Health", "Hospice", "Fertility / IVF", "Dialysis", "Orthopedics",
                  "Urology", "MSK", "Ophthalmology", "Urgent Care", "Telehealth")
    )
    size_opts = '<option value="">— all sizes —</option>' + "".join(
        f'<option value="{_html.escape(b)}"{" selected" if b == size_bucket else ""}>{_html.escape(b)}</option>' for b in size_buckets
    )
    region_opts = '<option value="">— all regions —</option>' + "".join(
        f'<option value="{_html.escape(rg)}"{" selected" if rg == region else ""}>{_html.escape(rg)}</option>' for rg in regions
    )

    form = f"""
<form method="GET" action="/base-rates" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Sector<select name="sector" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;min-width:140px">{sector_opts}</select></label>
  <label style="font-size:11px;color:{text_dim}">Size<select name="size_bucket" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;min-width:140px">{size_opts}</select></label>
  <label style="font-size:11px;color:{text_dim}">Region<select name="region" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;min-width:100px">{region_opts}</select></label>
  <button type="submit" style="background:{border};color:{text};border:1px solid {border};padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">Filter</button>
</form>"""

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    svg = _vintage_svg(r.vintage_rollups)
    pct_tbl = _percentile_table(r.percentile_rows)
    sec_tbl = _sector_table(r.sector_rollups)
    size_tbl = _size_table(r.size_rollups)
    vin_tbl = _vintage_table(r.vintage_rollups)
    com_tbl = _comm_table(r.comm_rollups)

    filter_desc_parts = []
    if sector: filter_desc_parts.append(f"sector={sector}")
    if size_bucket: filter_desc_parts.append(f"size={size_bucket}")
    if region: filter_desc_parts.append(f"region={region}")
    filter_desc = " · ".join(filter_desc_parts) if filter_desc_parts else "no filter (full corpus)"

    p50v = p50_mult.p50 if p50_mult else 12.0
    p75v = p50_mult.p75 if p50_mult else 14.0
    p90v = p50_mult.p90 if p50_mult else 16.0

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Base-Rate Engine</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">P25/P50/P75/P90 percentile cuts across EV/EBITDA, margin, MOIC, IRR — filterable by sector / size / region — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  {form}
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="background:{panel_alt};border:1px solid {border};padding:10px 14px;margin-bottom:16px;font-size:11px;font-family:JetBrains Mono,monospace;color:{text_dim}">
    <strong style="color:{acc}">FILTER:</strong> {_html.escape(filter_desc)} &nbsp;|&nbsp;
    <strong style="color:{text}">{r.total_matching:,}</strong> matching deals of {r.corpus_deal_count:,} total
  </div>
  <div style="{cell}"><div style="{h3}">Vintage Trend — Median EV/EBITDA by Year</div>{svg}</div>
  <div style="{cell}"><div style="{h3}">Percentile Distribution — All Metrics</div>{pct_tbl}</div>
  <div style="{cell}"><div style="{h3}">Sector Rollups — Top 40 by Deal Count</div>{sec_tbl}</div>
  <div style="{cell}"><div style="{h3}">Size Bucket Rollups</div>{size_tbl}</div>
  <div style="{cell}"><div style="{h3}">Vintage Year Rollups</div>{vin_tbl}</div>
  <div style="{cell}"><div style="{h3}">Commercial-Payer-Share Rollups</div>{com_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Base-Rate Interpretation:</strong> For this filter, the median PE healthcare transaction closed at {p50v:.2f}x EV/EBITDA,
    P75 {p75v:.2f}x, P90 {p90v:.2f}x. Sector premia matter — health IT trades &gt; 18x while dialysis and basic physician services sit 9-11x.
    Commercial-heavy payer mix commands 2-3x EV/EBITDA premium over Medicare-heavy comparables. Use these percentiles to sanity-check any target's ask
    price — a single comp's multiple is noise; the P50/P75 spread across comparable filters is signal.
  </div>
</div>"""

    return chartis_shell(body, "Base Rates", active_nav="/base-rates")
