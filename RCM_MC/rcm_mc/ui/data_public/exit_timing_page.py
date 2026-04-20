"""Exit Timing Analysis page — /exit-timing.

Shows when healthcare PE deals exit by sector, vintage, and payer mix.
Key questions for LP diligence: What is the distribution of hold periods?
Which sectors hold longer? Does hold duration correlate with MOIC? What
fraction of deals are still unrealized past typical hold windows?

All analytics run directly on the 635-deal public corpus.
Charts: inline SVG histograms and scatter plots, Bloomberg terminal style.
"""
from __future__ import annotations

import html as _html
import importlib
import math
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Corpus loader
# ---------------------------------------------------------------------------

def _load_corpus() -> List[Dict[str, Any]]:
    from rcm_mc.data_public.deals_corpus import _SEED_DEALS
    from rcm_mc.data_public.extended_seed import EXTENDED_SEED_DEALS
    result = list(_SEED_DEALS) + list(EXTENDED_SEED_DEALS)
    for i in range(2, 32):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            result += list(getattr(mod, f"EXTENDED_SEED_DEALS_{i}"))
        except (ImportError, AttributeError):
            pass
    return result


def _realized(deals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [d for d in deals if d.get("hold_years") is not None and d.get("realized_moic") is not None]


def _percentile(vals: List[float], p: float) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    idx = p / 100 * (len(s) - 1)
    lo, hi = int(idx), min(int(idx) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (idx - lo)


# ---------------------------------------------------------------------------
# Inline SVG helpers
# ---------------------------------------------------------------------------

def _pct(v: float, lo: float, hi: float) -> float:
    if hi <= lo:
        return 0.5
    return max(0.0, min(1.0, (v - lo) / (hi - lo)))


def _hold_histogram(
    hold_vals: List[float],
    width: int = 580,
    height: int = 130,
    bins: int = 20,
    lo: float = 0.0,
    hi: float = 12.0,
) -> str:
    """Histogram of hold years, inline SVG."""
    pad_l, pad_r, pad_t, pad_b = 28, 10, 8, 22
    pw = width - pad_l - pad_r
    ph = height - pad_t - pad_b

    bin_w = (hi - lo) / bins
    counts = [0] * bins
    for v in hold_vals:
        idx = int((v - lo) / bin_w)
        idx = max(0, min(bins - 1, idx))
        counts[idx] += 1
    max_c = max(counts) if counts else 1

    bars = []
    for i, c in enumerate(counts):
        bx = pad_l + i * pw / bins
        bh = (c / max_c) * ph
        by = pad_t + ph - bh
        bars.append(
            f'<rect x="{bx:.1f}" y="{by:.1f}" width="{pw/bins - 1:.1f}" height="{bh:.1f}" '
            f'fill="#1d4ed8" opacity="0.8"/>'
        )

    def tx(xv: float) -> float:
        return pad_l + _pct(xv, lo, hi) * pw

    axes = (
        f'<line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{pad_t+ph}" stroke="#334155" stroke-width="1"/>'
        f'<line x1="{pad_l}" y1="{pad_t+ph}" x2="{pad_l+pw}" y2="{pad_t+ph}" stroke="#334155" stroke-width="1"/>'
    )

    # Median + P25/P75 verticals
    if hold_vals:
        p25 = _percentile(hold_vals, 25)
        p50 = _percentile(hold_vals, 50)
        p75 = _percentile(hold_vals, 75)
        overlays = (
            f'<line x1="{tx(p25):.1f}" y1="{pad_t}" x2="{tx(p25):.1f}" y2="{pad_t+ph}" '
            f'stroke="#64748b" stroke-width="0.8" stroke-dasharray="3,3"/>'
            f'<line x1="{tx(p50):.1f}" y1="{pad_t}" x2="{tx(p50):.1f}" y2="{pad_t+ph}" '
            f'stroke="#f59e0b" stroke-width="1.2" stroke-dasharray="4,3"/>'
            f'<text x="{tx(p50)+2:.1f}" y="{pad_t+9}" font-size="7" fill="#f59e0b">P50={p50:.1f}yr</text>'
            f'<line x1="{tx(p75):.1f}" y1="{pad_t}" x2="{tx(p75):.1f}" y2="{pad_t+ph}" '
            f'stroke="#64748b" stroke-width="0.8" stroke-dasharray="3,3"/>'
        )
    else:
        overlays = ""

    ticks = "".join(
        f'<text x="{tx(xv):.1f}" y="{pad_t+ph+13}" font-size="7.5" fill="#64748b" text-anchor="middle">{xv:.0f}yr</text>'
        for xv in range(0, int(hi) + 1, 2)
    )
    n_lbl = f'<text x="{pad_l+3}" y="{pad_t+9}" font-size="7.5" fill="#475569">n={len(hold_vals)}</text>'

    return (
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'xmlns="http://www.w3.org/2000/svg" style="display:block;">'
        + axes + "".join(bars) + overlays + ticks + n_lbl + "</svg>"
    )


def _hold_moic_scatter(
    pts: List[Tuple[float, float]],  # (hold_yr, moic)
    width: int = 340,
    height: int = 180,
) -> str:
    """Scatter of hold_yr vs MOIC with trend line, inline SVG."""
    if not pts:
        return ""
    pad_l, pad_r, pad_t, pad_b = 32, 10, 10, 24
    pw = width - pad_l - pad_r
    ph = height - pad_t - pad_b
    x_lo, x_hi = 0.5, 12.0
    y_lo, y_hi = 0.0, 6.5

    def tx(x: float) -> float:
        return pad_l + _pct(x, x_lo, x_hi) * pw

    def ty(y: float) -> float:
        return pad_t + (1.0 - _pct(y, y_lo, y_hi)) * ph

    dots = "".join(
        f'<circle cx="{tx(x):.1f}" cy="{ty(y):.1f}" r="2.2" fill="#3b82f6" fill-opacity="0.6"/>'
        for x, y in pts
        if x_lo <= x <= x_hi and y_lo <= y <= y_hi
    )

    # Trend line
    n = len(pts)
    sx = sum(p[0] for p in pts)
    sy = sum(p[1] for p in pts)
    sxy = sum(p[0] * p[1] for p in pts)
    sxx = sum(p[0] ** 2 for p in pts)
    denom = n * sxx - sx * sx
    trend_line = ""
    if abs(denom) > 1e-9:
        m = (n * sxy - sx * sy) / denom
        b = (sy - m * sx) / n
        y1, y2 = m * x_lo + b, m * x_hi + b
        trend_line = (
            f'<line x1="{tx(x_lo):.1f}" y1="{ty(y1):.1f}" '
            f'x2="{tx(x_hi):.1f}" y2="{ty(y2):.1f}" '
            f'stroke="#f59e0b" stroke-width="1.2" stroke-dasharray="4,3"/>'
        )

    axes = (
        f'<line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{pad_t+ph}" stroke="#334155" stroke-width="1"/>'
        f'<line x1="{pad_l}" y1="{pad_t+ph}" x2="{pad_l+pw}" y2="{pad_t+ph}" stroke="#334155" stroke-width="1"/>'
    )

    be_y = ty(1.0)
    be_line = (
        f'<line x1="{pad_l}" y1="{be_y:.1f}" x2="{pad_l+pw}" y2="{be_y:.1f}" '
        f'stroke="#ef4444" stroke-width="0.8" stroke-dasharray="3,4" opacity="0.4"/>'
    )

    x_ticks = "".join(
        f'<text x="{tx(xv):.1f}" y="{pad_t+ph+13}" font-size="7.5" fill="#64748b" text-anchor="middle">{xv:.0f}yr</text>'
        for xv in [1, 3, 5, 7, 9, 11]
    )
    y_ticks = "".join(
        f'<text x="{pad_l-4}" y="{ty(yv)+3:.1f}" font-size="7.5" fill="#64748b" text-anchor="end">{yv:.0f}x</text>'
        for yv in [0, 1, 2, 3, 4, 5, 6]
    )
    labels = (
        f'<text x="{pad_l+pw/2:.1f}" y="{height-2}" font-size="8" fill="#94a3b8" text-anchor="middle">Hold Years</text>'
        f'<text x="8" y="{pad_t+ph/2:.1f}" font-size="8" fill="#94a3b8" text-anchor="middle" '
        f'transform="rotate(-90,8,{pad_t+ph/2:.1f})">MOIC</text>'
    )
    n_lbl = f'<text x="{pad_l+4}" y="{pad_t+9}" font-size="7.5" fill="#475569">n={len(pts)}</text>'

    return (
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'xmlns="http://www.w3.org/2000/svg" style="display:block;">'
        + axes + be_line + trend_line + dots + x_ticks + y_ticks + labels + n_lbl
        + "</svg>"
    )


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

def _sector_hold_stats(deals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Per-sector hold period statistics."""
    sectors: Dict[str, List[float]] = {}
    sector_moics: Dict[str, List[float]] = {}
    for d in _realized(deals):
        s = d.get("sector") or "Unknown"
        h = float(d["hold_years"])
        m = float(d["realized_moic"])
        sectors.setdefault(s, []).append(h)
        sector_moics.setdefault(s, []).append(m)

    rows = []
    for s, holds in sorted(sectors.items()):
        if len(holds) < 3:
            continue
        moics = sector_moics.get(s, [])
        rows.append({
            "sector": s,
            "n": len(holds),
            "hold_p25": _percentile(sorted(holds), 25),
            "hold_p50": _percentile(sorted(holds), 50),
            "hold_p75": _percentile(sorted(holds), 75),
            "moic_p50": _percentile(sorted(moics), 50) if moics else None,
            "irr_penalty": None,  # could compute but complex
        })
    rows.sort(key=lambda r: r["hold_p50"])
    return rows


def _vintage_unrealized(deals: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    """For each entry year, what fraction are still unrealized?"""
    result = {}
    years = sorted({d.get("year") or d.get("entry_year") for d in deals
                    if (d.get("year") or d.get("entry_year")) and
                    (d.get("year") or d.get("entry_year")) >= 2010})
    for yr in years:
        yr_deals = [d for d in deals if (d.get("year") or d.get("entry_year")) == yr]
        total = len(yr_deals)
        realized_n = sum(1 for d in yr_deals if d.get("realized_moic") is not None)
        result[yr] = {
            "year": yr,
            "total": total,
            "realized": realized_n,
            "unrealized": total - realized_n,
            "pct_realized": realized_n / total if total else 0.0,
        }
    return result


def _overall_stats(deals: List[Dict[str, Any]]) -> Dict[str, Any]:
    realized = _realized(deals)
    holds = sorted([float(d["hold_years"]) for d in realized])
    moics = [float(d["realized_moic"]) for d in realized]
    short = sum(1 for h in holds if h < 3.5)
    mid = sum(1 for h in holds if 3.5 <= h < 6.0)
    long_ = sum(1 for h in holds if h >= 6.0)

    # MOIC by hold bucket
    def bucket_moic(lo, hi):
        m = [float(d["realized_moic"]) for d in realized
             if lo <= float(d["hold_years"]) < hi]
        return _percentile(sorted(m), 50) if m else None

    return {
        "realized_with_hold": len(holds),
        "hold_p25": _percentile(holds, 25),
        "hold_p50": _percentile(holds, 50),
        "hold_p75": _percentile(holds, 75),
        "hold_p90": _percentile(holds, 90),
        "short_n": short,
        "mid_n": mid,
        "long_n": long_,
        "short_moic_p50": bucket_moic(0, 3.5),
        "mid_moic_p50": bucket_moic(3.5, 6.0),
        "long_moic_p50": bucket_moic(6.0, 20.0),
        "holds": holds,
        "scatter_pts": [(float(d["hold_years"]), float(d["realized_moic"])) for d in realized
                        if float(d["hold_years"]) >= 0.5],
    }


# ---------------------------------------------------------------------------
# HTML sections
# ---------------------------------------------------------------------------

def _kpi_bar(stats: Dict[str, Any]) -> str:
    from rcm_mc.ui._chartis_kit import ck_kpi_block
    m_sh = stats["short_moic_p50"]
    m_mi = stats["mid_moic_p50"]
    m_lo = stats["long_moic_p50"]

    def moic_html(v):
        if v is None:
            return '<span class="faint">—</span>'
        color = "#22c55e" if v >= 2.5 else ("#f59e0b" if v >= 1.5 else "#ef4444")
        return f'<span class="mn" style="color:{color}">{v:.2f}×</span>'

    return (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block("Realized w/ Hold Data",
                       f'<span class="mn">{stats["realized_with_hold"]}</span>', "corpus deals")
        + ck_kpi_block("P50 Hold Period",
                       f'<span class="mn">{stats["hold_p50"]:.1f}yr</span>',
                       f'IQR {stats["hold_p25"]:.1f}–{stats["hold_p75"]:.1f}yr')
        + ck_kpi_block("Short Hold P50 MOIC",
                       moic_html(m_sh), f'<3.5yr · n={stats["short_n"]}')
        + ck_kpi_block("Mid Hold P50 MOIC",
                       moic_html(m_mi), f'3.5–6yr · n={stats["mid_n"]}')
        + ck_kpi_block("Long Hold P50 MOIC",
                       moic_html(m_lo), f'>6yr · n={stats["long_n"]}')
        + '</div>'
    )


def _hold_distribution_panel(stats: Dict[str, Any]) -> str:
    svg_hist = _hold_histogram(stats["holds"])
    svg_scatter = _hold_moic_scatter(stats["scatter_pts"])
    return f"""
<div class="ck-panel">
  <div class="ck-panel-title">Hold Period Distribution — Corpus Realized Deals</div>
  <div style="padding:14px 16px;display:grid;grid-template-columns:580px 1fr;gap:24px;">
    <div>
      <div style="font-family:var(--ck-mono);font-size:9px;letter-spacing:0.1em;
                  text-transform:uppercase;color:var(--ck-text-faint);margin-bottom:6px;">
        Hold Period Histogram (n={len(stats['holds'])})
      </div>
      {svg_hist}
      <div style="font-size:9.5px;color:var(--ck-text-faint);margin-top:5px;">
        Amber dashed = P50 hold · gray dashed = P25/P75
      </div>
    </div>
    <div>
      <div style="font-family:var(--ck-mono);font-size:9px;letter-spacing:0.1em;
                  text-transform:uppercase;color:var(--ck-text-faint);margin-bottom:6px;">
        Hold Years vs Realized MOIC
      </div>
      {svg_scatter}
      <div style="font-size:9.5px;color:var(--ck-text-faint);margin-top:5px;">
        Amber trend · red dashed = 1.0× breakeven
      </div>
    </div>
  </div>
</div>"""


def _sector_table_panel(rows: List[Dict[str, Any]]) -> str:
    tbody = []
    for i, r in enumerate(rows):
        stripe = ' style="background:#0f172a"' if i % 2 == 1 else ""
        moic_color = "#22c55e" if (r["moic_p50"] or 0) >= 2.5 else ("#f59e0b" if (r["moic_p50"] or 0) >= 1.5 else "#ef4444")
        moic_html = (
            f'<span style="font-family:var(--ck-mono);font-variant-numeric:tabular-nums;color:{moic_color}">'
            f'{r["moic_p50"]:.2f}×</span>'
            if r["moic_p50"] else '<span style="color:var(--ck-text-faint)">—</span>'
        )
        tbody.append(f"""
<tr{stripe}>
  <td class="dim" style="font-size:11px;">{_html.escape(r['sector'])}</td>
  <td class="mono dim" style="text-align:right;">{r['n']}</td>
  <td class="mono" style="text-align:right;font-variant-numeric:tabular-nums;">{r['hold_p25']:.1f}yr</td>
  <td class="mono" style="text-align:right;font-variant-numeric:tabular-nums;color:#f59e0b;font-weight:600;">{r['hold_p50']:.1f}yr</td>
  <td class="mono" style="text-align:right;font-variant-numeric:tabular-nums;">{r['hold_p75']:.1f}yr</td>
  <td style="text-align:right;">{moic_html}</td>
</tr>""")
    return f"""
<div class="ck-panel">
  <div class="ck-panel-title">Hold Period by Sector (≥3 realized deals, sorted by P50 hold)</div>
  <div class="ck-table-wrap">
    <table class="ck-table" style="table-layout:fixed;">
      <colgroup>
        <col style="width:220px"><col style="width:50px">
        <col style="width:80px"><col style="width:80px"><col style="width:80px"><col style="width:80px">
      </colgroup>
      <thead>
        <tr>
          <th>Sector</th><th style="text-align:right;">N</th>
          <th style="text-align:right;">P25 Hold</th>
          <th style="text-align:right;">P50 Hold</th>
          <th style="text-align:right;">P75 Hold</th>
          <th style="text-align:right;">P50 MOIC</th>
        </tr>
      </thead>
      <tbody>{''.join(tbody)}</tbody>
    </table>
  </div>
</div>"""


def _vintage_panel(vintage_data: Dict[int, Dict[str, Any]]) -> str:
    """Mini bar chart showing realization rates by vintage year."""
    years = sorted(vintage_data.keys())
    if not years:
        return ""

    width, height = 680, 130
    pad_l, pad_r, pad_t, pad_b = 32, 12, 10, 28
    pw = width - pad_l - pad_r
    ph = height - pad_t - pad_b
    bar_w = pw / len(years) - 2

    bars = []
    for i, yr in enumerate(years):
        vd = vintage_data[yr]
        pct = vd["pct_realized"]
        bx = pad_l + i * (pw / len(years))
        bh = pct * ph
        by = pad_t + ph - bh
        color = "#22c55e" if pct >= 0.80 else ("#f59e0b" if pct >= 0.50 else "#3b82f6")
        bars.append(
            f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" '
            f'fill="{color}" opacity="0.75"/>'
        )
        bars.append(
            f'<text x="{bx + bar_w/2:.1f}" y="{pad_t+ph+14}" font-size="7" '
            f'fill="#64748b" text-anchor="middle">{str(yr)[2:]}</text>'
        )

    # 80% line
    line_y = pad_t + ph - 0.8 * ph
    overlay = (
        f'<line x1="{pad_l}" y1="{line_y:.1f}" x2="{pad_l+pw}" y2="{line_y:.1f}" '
        f'stroke="#22c55e" stroke-width="0.8" stroke-dasharray="3,3" opacity="0.5"/>'
        f'<text x="{pad_l+pw+2}" y="{line_y+3:.1f}" font-size="7" fill="#22c55e" opacity="0.7">80%</text>'
    )
    axes = (
        f'<line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{pad_t+ph}" stroke="#334155" stroke-width="1"/>'
        f'<line x1="{pad_l}" y1="{pad_t+ph}" x2="{pad_l+pw}" y2="{pad_t+ph}" stroke="#334155" stroke-width="1"/>'
    )
    y_ticks = "".join(
        f'<text x="{pad_l-4}" y="{pad_t+ph-pv*ph+3:.1f}" font-size="7.5" fill="#64748b" text-anchor="end">{pv*100:.0f}%</text>'
        for pv in [0.25, 0.50, 0.75, 1.0]
    )

    svg = (
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'xmlns="http://www.w3.org/2000/svg" style="display:block;">'
        + axes + overlay + "".join(bars) + y_ticks + "</svg>"
    )

    return f"""
<div class="ck-panel">
  <div class="ck-panel-title">Realization Rate by Vintage Year (2010+)</div>
  <div style="padding:14px 16px 10px;">
    {svg}
    <div style="margin-top:6px;font-size:9.5px;color:var(--ck-text-faint);">
      Green = ≥80% of vintage realized · amber = 50–80% · blue = &lt;50% (recent vintages still maturing)
    </div>
  </div>
</div>"""


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------

def render_exit_timing() -> str:
    from rcm_mc.ui._chartis_kit import chartis_shell, ck_section_header

    deals = _load_corpus()
    stats = _overall_stats(deals)
    sector_rows = _sector_hold_stats(deals)
    vintage_data = _vintage_unrealized(deals)

    kpis = _kpi_bar(stats)
    section_dist = ck_section_header("HOLD PERIOD DISTRIBUTION", "corpus realized deals")
    dist_panel = _hold_distribution_panel(stats)
    section_sector = ck_section_header("SECTOR HOLD PERIODS", "by healthcare subsector, sorted shortest to longest")
    sector_panel = _sector_table_panel(sector_rows)
    section_vintage = ck_section_header("VINTAGE REALIZATION RATES", "% of deals per year that have exited")
    vintage_panel = _vintage_panel(vintage_data)

    body = kpis + section_dist + dist_panel + section_sector + sector_panel + section_vintage + vintage_panel

    return chartis_shell(
        body,
        title="Exit Timing Analysis",
        active_nav="/exit-timing",
        subtitle=(
            f"{stats['realized_with_hold']} realized deals with hold data · "
            f"P50 hold {stats['hold_p50']:.1f}yr · "
            f"IQR {stats['hold_p25']:.1f}–{stats['hold_p75']:.1f}yr"
        ),
    )
