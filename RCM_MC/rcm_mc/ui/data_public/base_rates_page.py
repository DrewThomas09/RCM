"""Base-Rate Engine — /base-rates.

Multi-dimensional percentile cuts (P25/P50/P75/P90) across EV/EBITDA,
EBITDA margin, MOIC, IRR. Filterable by sector, size, region; rolls up
by sector, size bucket, vintage year, commercial-payer-share bucket.
"""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block, ck_data_cell, ck_page_title, ck_bar_row, ck_scatter


def _sector_scatter(items):
    """Quadrant view — entry multiple vs realized MOIC by sector, so
    'cheap-entry / high-return' sectors (upper-left) stand out."""
    import statistics
    pts, xs, ys = [], [], []
    for s in items:
        x = s.median_ev_ebitda; y = s.median_moic
        tn = ('positive' if s.median_irr >= 0.20 else 'teal' if s.median_irr >= 0.15 else 'warning')
        pts.append((x, y, s.sector, tn)); xs.append(x); ys.append(y)
    return ck_scatter(
        pts, x_label='Median entry EV/EBITDA', y_label='Median MOIC',
        x_ref=(statistics.median(xs) if xs else None),
        y_ref=(statistics.median(ys) if ys else None),
        caption='Each dot = a sector · upper-left = cheap entry + high return · tone = median IRR',
    )


def _sector_chart(items):
    """Summary chart — corpus base-rate MOIC by sector (tone by median IRR)."""
    def _tone(s):
        if s.median_irr >= 0.20: return "positive"
        if s.median_irr >= 0.15: return "teal"
        return "warning"
    top = sorted(items, key=lambda s: s.median_moic, reverse=True)[:18]
    mx = max((s.median_moic for s in top), default=0.0) or 1.0
    rows = [ck_bar_row(f"{s.sector} ({s.deal_count} deals)",
            f"{s.median_moic:.2f}x MOIC · {s.median_irr * 100:.0f}% IRR · {s.median_ev_ebitda:.1f}x entry",
            s.median_moic / mx * 100.0, tone=_tone(s)) for s in top]
    return ('<div style="margin-bottom:14px">' + "".join(rows) +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Bar = median MOIC vs best sector '
            '· value = MOIC + IRR + entry multiple · tone = median IRR</div></div>')

_EXPLAINER_CSS = """<style>
.ck-br-explainer{font-family:var(--sc-serif,'Georgia',serif);
  font-size:15px;line-height:1.55;color:var(--sc-text-dim,#465366);
  margin:0 0 var(--sc-s-6,18px) 0;max-width:72ch;}
.ck-br-explainer em{color:var(--sc-teal-ink,#155752);font-style:italic;}
</style>"""


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
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    # Honest thin-sample flag: percentiles over fewer than this many
    # matched deals swing on individual exits, so they're directional
    # only — mark those N cells and footnote it rather than letting an
    # n=4 row read as authoritatively as an n=200 row.
    _THIN_N = 10
    any_thin = False
    trs = []
    for i, r in enumerate(rows):
        rb = panel_alt if i % 2 == 0 else bg
        kind = _percentile_row_kind(r.metric)
        def _cell(v):
            return f'{ck_data_cell(f"""{_fmt(v, kind)}""", align="right", mono=True)}'
        thin = r.n < _THIN_N
        any_thin = any_thin or thin
        n_label = f"{r.n:,} †" if thin else f"{r.n:,}"
        cells = [
            f'{ck_data_cell(f"""{_html.escape(r.metric)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{n_label}""", align="right", mono=True, tone=("neg" if thin else "dim"))}',
            _cell(r.p25),
            f'{ck_data_cell(f"""{_fmt(r.p50, kind)}""", align="right", mono=True, tone="acc", weight=700)}',
            _cell(r.p75),
            f'{ck_data_cell(f"""{_fmt(r.p90, kind)}""", align="right", mono=True, tone="pos")}',
            _cell(r.mean),
            _cell(r.min),
            _cell(r.max),
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    footnote = (
        f'<div style="font-family:var(--sc-mono,monospace);font-size:10.5px;'
        f'color:var(--sc-warning,#b8732a);margin-top:6px;">'
        f'† n &lt; {_THIN_N} — thin sample; percentiles are directional only, '
        f'not a stable benchmark.</div>'
    ) if any_thin else ""
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
            f'{footnote}')


def _sector_table(rows) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Sector","left"),("Deals","right"),("Med EV ($M)","right"),("Med EV/EBITDA","right"),
            ("Med EV/Rev","right"),("Med EBITDA Margin","right"),("Med MOIC","right"),("Med IRR","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, s in enumerate(rows[:40]):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(s.sector[:36])}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{s.deal_count}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${s.median_ev_mm:,.1f}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{s.median_ev_ebitda:,.2f}x""", align="right", mono=True, tone="acc", weight=700)}',
            f'{ck_data_cell(f"""{s.median_ev_revenue:,.2f}x""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{s.median_ebitda_margin * 100:.1f}%""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{s.median_moic:.2f}x""", align="right", mono=True, tone="pos", weight=600)}',
            f'{ck_data_cell(f"""{s.median_irr * 100:.1f}%""", align="right", mono=True)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _size_table(rows) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Size Bucket","left"),("Deals","right"),("Med EV/EBITDA","right"),
            ("Med EBITDA Margin","right"),("Med MOIC","right"),("Med Hold Years","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, s in enumerate(rows):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(s.bucket)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{s.deal_count}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{s.median_ev_ebitda:,.2f}x""", align="right", mono=True, tone="acc", weight=700)}',
            f'{ck_data_cell(f"""{s.median_ebitda_margin * 100:.1f}%""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{s.median_moic:.2f}x""", align="right", mono=True, tone="pos", weight=600)}',
            f'{ck_data_cell(f"""{s.median_hold_years:,.1f}y""", align="right", mono=True, tone="dim")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _vintage_table(rows) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Year","left"),("Deals","right"),("Med EV/EBITDA","right"),("Med EBITDA Margin","right"),("Med MOIC","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, v in enumerate(rows):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{v.year}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{v.deal_count}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{v.median_ev_ebitda:,.2f}x""", align="right", mono=True, tone="acc", weight=700)}',
            f'{ck_data_cell(f"""{v.median_ebitda_margin * 100:.1f}%""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{v.median_moic:.2f}x""", align="right", mono=True, tone="pos", weight=600)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _comm_table(rows) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Commercial Share Bucket","left"),("Deals","right"),("Med EV/EBITDA","right"),("Med EBITDA Margin","right"),("Med MOIC","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, c in enumerate(rows):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.comm_bucket)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{c.deal_count}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{c.median_ev_ebitda:,.2f}x""", align="right", mono=True, tone="acc", weight=700)}',
            f'{ck_data_cell(f"""{c.median_ebitda_margin * 100:.1f}%""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{c.median_moic:.2f}x""", align="right", mono=True, tone="pos", weight=600)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


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
    sec_chart = _sector_chart(r.sector_rollups)
    sec_scatter = _sector_scatter(r.sector_rollups)
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

    page_title = ck_page_title(
        "Base-Rate Engine",
        eyebrow="BASE RATES",
        meta=(
            f"P25/P50/P75/P90 across EV/EBITDA, margin, MOIC, IRR · "
            f"{r.total_matching:,} matching deals · {r.corpus_deal_count:,} corpus deals"
        ),
    )
    br_explainer = (
        '<p class="ck-br-explainer">'
        "<em>What the base rates reveal on this deal.</em> "
        "Multi-dimensional percentile cuts across EV/EBITDA, EBITDA margin, MOIC, and IRR — "
        "filterable by sector, size, and region, with roll-ups by sector, size bucket, "
        "vintage, and commercial-payer-share bucket."
        "</p>"
    )
    body = page_title + br_explainer + f"""
<div class="ck-page-wrap">
  {form}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  <div style="background:{panel_alt};border:1px solid {border};padding:10px 14px;margin-bottom:16px;font-size:11px;font-family:JetBrains Mono,monospace;color:{text_dim}">
    <strong style="color:{acc}">FILTER:</strong> {_html.escape(filter_desc)} &nbsp;|&nbsp;
    <strong style="color:{text}">{r.total_matching:,}</strong> matching deals of {r.corpus_deal_count:,} total
  </div>
  <div style="{cell}"><div style="{h3}">Vintage Trend — Median EV/EBITDA by Year</div>{svg}</div>
  <div style="{cell}"><div style="{h3}">Percentile Distribution — All Metrics</div>{pct_tbl}</div>
  <div style="{cell}"><div style="{h3}">Sector Rollups — Top 40 by Deal Count</div>{sec_chart}{sec_scatter}{sec_tbl}</div>
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

    from rcm_mc.ui._chartis_kit import ck_illustrative_note as _ckn
    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from ._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(_ckn("base rates (illustrative seed corpus)") + body, "Base Rates", active_nav="/base-rates",
        extra_css=_EXPLAINER_CSS)
