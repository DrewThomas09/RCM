"""Deal-screening dashboard renderer — Bloomberg-like surface.

Self-contained HTML page (no external CSS/JS) showing the
filterable deal universe. Layout:

  • Cover row: KPI tiles (universe size, median uplift,
    high-confidence count, top sector by uplift)
  • Filter strip: sector dropdown, size range, confidence
    floor, exclude-topic chips
  • Sortable table: deal name, sector, revenue, EBITDA,
    predicted uplift, confidence band, risk factors
  • Each row click-throughs to /diligence/synthesis/<deal_id>
    (the IC binder route)
"""
from __future__ import annotations

import html as _html
from typing import List, Optional

from .filter import DealFilter
from .predict import ScreeningResult


_CSS = """
:root {
  --c-bg: #0a0e17; --c-panel: #111827; --c-panel-alt: #0f172a;
  --c-border: #1e293b; --c-text: #e2e8f0; --c-dim: #94a3b8;
  --c-faint: #64748b; --c-accent: #3b82f6;
  --c-pos: #10b981; --c-neg: #ef4444; --c-warn: #f59e0b;
  --c-mono: 'JetBrains Mono', 'SF Mono', 'Fira Code', monospace;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: var(--c-bg); color: var(--c-text);
  font-family: 'Inter', -apple-system, BlinkMacSystemFont,
                'Segoe UI', Roboto, sans-serif;
  font-size: 12px; padding: 24px;
  font-variant-numeric: tabular-nums;
}
.scr-wrap { max-width: 1500px; margin: 0 auto; }
.scr-title {
  font-family: var(--c-mono); font-size: 11px;
  text-transform: uppercase; letter-spacing: 0.18em;
  color: var(--c-dim); margin-bottom: 6px;
}
.scr-h1 {
  font-size: 22px; font-weight: 700;
  letter-spacing: -0.01em; margin-bottom: 16px;
}
.scr-kpis {
  display: grid; gap: 8px; margin-bottom: 16px;
  grid-template-columns: repeat(4, 1fr);
}
.scr-kpi {
  background: var(--c-panel); border: 1px solid var(--c-border);
  padding: 12px 14px;
}
.scr-kpi-label {
  font-family: var(--c-mono); font-size: 9px;
  text-transform: uppercase; letter-spacing: 0.1em;
  color: var(--c-dim); margin-bottom: 6px;
}
.scr-kpi-val {
  font-family: var(--c-mono); font-size: 20px;
  font-weight: 700; color: var(--c-text);
}
.scr-kpi-sub {
  font-family: var(--c-mono); font-size: 10px;
  color: var(--c-faint); margin-top: 4px;
}
.scr-filters {
  background: var(--c-panel); border: 1px solid var(--c-border);
  padding: 10px 14px; display: flex; gap: 12px;
  align-items: center; margin-bottom: 12px; flex-wrap: wrap;
  font-size: 11px;
}
.scr-filters label {
  color: var(--c-dim); font-family: var(--c-mono);
  text-transform: uppercase; letter-spacing: 0.06em;
  font-size: 9px;
}
.scr-filters select, .scr-filters input {
  background: var(--c-panel-alt); color: var(--c-text);
  border: 1px solid var(--c-border); padding: 4px 8px;
  font-family: var(--c-mono); font-size: 11px; border-radius: 2px;
}
.scr-filters button {
  background: var(--c-accent); color: var(--c-text); border: none;
  padding: 5px 14px; font-family: var(--c-mono); font-size: 11px;
  cursor: pointer; border-radius: 2px;
}
table.scr-tbl {
  width: 100%; border-collapse: collapse;
  background: var(--c-panel); border: 1px solid var(--c-border);
}
table.scr-tbl th, table.scr-tbl td {
  padding: 8px 10px; text-align: left;
  border-bottom: 1px solid var(--c-border); font-size: 11px;
}
table.scr-tbl th {
  font-family: var(--c-mono); font-size: 9px;
  text-transform: uppercase; letter-spacing: 0.08em;
  color: var(--c-dim); background: var(--c-panel-alt);
}
table.scr-tbl tr:hover td { background: var(--c-panel-alt); }
table.scr-tbl td.num { text-align: right; }
.scr-band {
  font-family: var(--c-mono); font-size: 9px;
  text-transform: uppercase; letter-spacing: 0.1em;
  padding: 2px 6px; border-radius: 2px; font-weight: 700;
}
.scr-band.high   { background: rgba(16,185,129,0.15);
                   color: var(--c-pos); }
.scr-band.medium { background: rgba(245,158,11,0.15);
                   color: var(--c-warn); }
.scr-band.low    { background: rgba(239,68,68,0.15);
                   color: var(--c-neg); }
.scr-risks {
  font-size: 10px; color: var(--c-dim); line-height: 1.5;
}
.scr-empty {
  text-align: center; padding: 40px; color: var(--c-dim);
  font-family: var(--c-mono); font-size: 11px;
}
"""


def _format_money(mm: float) -> str:
    if mm is None:
        return "—"
    if abs(mm) >= 1000:
        return f"${mm/1000:.2f}B"
    if abs(mm) >= 1:
        return f"${mm:.1f}M"
    return f"${mm*1000:.0f}K"


def render_screening_dashboard(
    results: List[ScreeningResult],
    *,
    flt: Optional[DealFilter] = None,
    title: str = "Deal Screening Universe",
) -> str:
    """Render the full HTML dashboard given the universe +
    optional filter state."""
    flt = flt or DealFilter()

    # KPIs
    n = len(results)
    if n == 0:
        median_uplift = 0.0
        high_count = 0
        top_sector = "—"
    else:
        sorted_uplift = sorted(
            r.predicted_ebitda_uplift_mm for r in results)
        median_uplift = sorted_uplift[n // 2]
        high_count = sum(
            1 for r in results
            if r.confidence_band == "high")
        # Top sector by total uplift
        sector_totals = {}
        for r in results:
            sector_totals[r.sector] = (
                sector_totals.get(r.sector, 0)
                + r.predicted_ebitda_uplift_mm)
        if sector_totals:
            top_sector = max(
                sector_totals, key=sector_totals.get)
        else:
            top_sector = "—"

    # ── Body assembly ──────────────────────────────────────
    parts: List[str] = []
    parts.append("<!DOCTYPE html>")
    parts.append('<html lang="en"><head><meta charset="utf-8">')
    parts.append(f"<title>{_html.escape(title)}</title>")
    parts.append(f"<style>{_CSS}</style></head><body>")
    parts.append('<div class="scr-wrap">')
    parts.append('<div class="scr-title">RCM-MC SCREENING</div>')
    parts.append(f'<h1 class="scr-h1">{_html.escape(title)}</h1>')

    # KPIs
    parts.append('<div class="scr-kpis">')
    for label, val, sub in (
        ("Universe size", str(n), "candidates after filter"),
        ("Median uplift", _format_money(median_uplift),
         "EBITDA $ per deal"),
        ("High confidence", str(high_count),
         f"of {n} ({(high_count/n*100 if n else 0):.0f}%)"),
        ("Top sector", _html.escape(top_sector),
         "by total uplift"),
    ):
        parts.append(
            f'<div class="scr-kpi">'
            f'<div class="scr-kpi-label">{label}</div>'
            f'<div class="scr-kpi-val">{val}</div>'
            f'<div class="scr-kpi-sub">{sub}</div></div>')
    parts.append('</div>')

    # Filter strip
    sector_options = sorted({r.sector for r in results})
    parts.append(
        '<form class="scr-filters" method="GET" '
        'action="/screening/dashboard">')
    parts.append('<label>Sector</label>')
    parts.append('<select name="sector">')
    parts.append('<option value="">All</option>')
    cur_sector = (flt.sectors[0] if flt.sectors else "")
    for s in sector_options:
        sel = " selected" if s == cur_sector else ""
        parts.append(
            f'<option value="{_html.escape(s)}"{sel}>'
            f'{_html.escape(s)}</option>')
    parts.append('</select>')
    parts.append('<label>EBITDA $M ≥</label>')
    parts.append(
        f'<input name="size_min" type="number" step="1" '
        f'value="{flt.size_min_mm or ""}" '
        f'style="width:80px;">')
    parts.append('<label>EBITDA $M ≤</label>')
    parts.append(
        f'<input name="size_max" type="number" step="1" '
        f'value="{flt.size_max_mm or ""}" '
        f'style="width:80px;">')
    parts.append('<label>Conf ≥</label>')
    parts.append(
        f'<input name="confidence_floor" type="number" '
        f'step="0.05" min="0" max="1" '
        f'value="{flt.confidence_floor}" '
        f'style="width:80px;">')
    parts.append('<label>Exclude</label>')
    parts.append(
        f'<input name="exclude" type="text" '
        f'value="{_html.escape(",".join(flt.exclude_topics))}" '
        f'placeholder="risk substrings, comma-separated" '
        f'style="width:240px;">')
    parts.append('<button type="submit">Apply</button>')
    parts.append('</form>')

    # Table
    if n == 0:
        parts.append(
            '<div class="scr-empty">No deals match the current '
            'filter. Loosen the filter or expand the corpus.</div>')
    else:
        parts.append('<table class="scr-tbl">')
        parts.append(
            '<thead><tr>'
            '<th>Deal</th><th>Sector</th>'
            '<th class="num">Revenue</th>'
            '<th class="num">EBITDA</th>'
            '<th class="num">Uplift</th>'
            '<th class="num">Improvement %</th>'
            '<th>Conf.</th>'
            '<th>Top Risk Factors</th>'
            '</tr></thead><tbody>')
        for r in results:
            link = (f"/diligence/synthesis/"
                    f"{_html.escape(r.deal_id)}")
            risks_html = (
                "<br>".join(
                    _html.escape(rf) for rf in r.risk_factors)
                if r.risk_factors
                else '<span style="color:var(--c-faint)">—</span>')
            parts.append(
                f'<tr onclick="window.location=\'{link}\'" '
                f'style="cursor:pointer;">'
                f'<td><strong>{_html.escape(r.name)}</strong>'
                f'<br><span style="color:var(--c-faint);'
                f'font-family:var(--c-mono);font-size:10px">'
                f'{_html.escape(r.deal_id)}</span></td>'
                f'<td>{_html.escape(r.sector)}</td>'
                f'<td class="num">'
                f'{_format_money(r.revenue_mm)}</td>'
                f'<td class="num">'
                f'{_format_money(r.ebitda_mm)}</td>'
                f'<td class="num"><strong>'
                f'{_format_money(r.predicted_ebitda_uplift_mm)}'
                f'</strong></td>'
                f'<td class="num">'
                f'{r.predicted_improvement_pct*100:.1f}%</td>'
                f'<td><span class="scr-band '
                f'{r.confidence_band}">{r.confidence_band}</span>'
                f'</td>'
                f'<td class="scr-risks">{risks_html}</td>'
                f'</tr>')
        parts.append('</tbody></table>')

    parts.append('</div></body></html>')
    return "\n".join(parts)
