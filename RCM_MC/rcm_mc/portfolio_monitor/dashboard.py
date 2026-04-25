"""Portfolio monitoring dashboard renderer."""
from __future__ import annotations

import html as _html
from typing import List

from .variance import AssetVariance, PortfolioVariance


_CSS = """
:root {
  --c-bg: #0a0e17; --c-panel: #111827;
  --c-panel-alt: #0f172a; --c-border: #1e293b;
  --c-text: #e2e8f0; --c-dim: #94a3b8; --c-faint: #64748b;
  --c-pos: #10b981; --c-neg: #ef4444; --c-warn: #f59e0b;
  --c-watch: #eab308; --c-blue: #3b82f6;
  --c-mono: 'JetBrains Mono', 'SF Mono', monospace;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: var(--c-bg); color: var(--c-text);
  font-family: 'Inter', -apple-system, sans-serif;
  font-size: 12px; padding: 24px;
  font-variant-numeric: tabular-nums;
}
.pm-wrap { max-width: 1500px; margin: 0 auto; }
.pm-title {
  font-family: var(--c-mono); font-size: 11px;
  text-transform: uppercase; letter-spacing: 0.18em;
  color: var(--c-dim); margin-bottom: 6px;
}
.pm-h1 {
  font-size: 22px; font-weight: 700; margin-bottom: 16px;
}
.pm-kpis {
  display: grid; gap: 8px; margin-bottom: 16px;
  grid-template-columns: repeat(5, 1fr);
}
.pm-kpi {
  background: var(--c-panel); border: 1px solid var(--c-border);
  padding: 12px 14px;
}
.pm-kpi-label {
  font-family: var(--c-mono); font-size: 9px;
  text-transform: uppercase; letter-spacing: 0.1em;
  color: var(--c-dim); margin-bottom: 6px;
}
.pm-kpi-val {
  font-family: var(--c-mono); font-size: 18px;
  font-weight: 700;
}
.pm-kpi-val.pos { color: var(--c-pos); }
.pm-kpi-val.neg { color: var(--c-neg); }
.pm-bridge {
  background: var(--c-panel); border: 1px solid var(--c-border);
  padding: 14px; margin-bottom: 16px;
}
.pm-bridge h3 {
  font-family: var(--c-mono); font-size: 10px;
  text-transform: uppercase; letter-spacing: 0.1em;
  color: var(--c-dim); margin-bottom: 8px;
}
.pm-bridge-row {
  display: flex; align-items: center; gap: 12px;
  margin: 4px 0; font-size: 11px;
}
.pm-bridge-bar {
  height: 14px; flex: 1; max-width: 600px;
  background: var(--c-panel-alt); position: relative;
}
.pm-bridge-fill {
  height: 100%; transition: width 0.2s;
}
.pm-bridge-label {
  width: 140px; color: var(--c-dim); font-family: var(--c-mono);
  font-size: 10px; text-transform: uppercase;
  letter-spacing: 0.05em;
}
.pm-bridge-val {
  font-family: var(--c-mono); font-size: 11px;
  width: 100px; text-align: right;
}
table.pm-tbl {
  width: 100%; border-collapse: collapse;
  background: var(--c-panel); border: 1px solid var(--c-border);
}
table.pm-tbl th, table.pm-tbl td {
  padding: 8px 10px; text-align: left;
  border-bottom: 1px solid var(--c-border); font-size: 11px;
}
table.pm-tbl th {
  font-family: var(--c-mono); font-size: 9px;
  text-transform: uppercase; letter-spacing: 0.08em;
  color: var(--c-dim); background: var(--c-panel-alt);
}
table.pm-tbl td.num { text-align: right; }
.pm-status {
  font-family: var(--c-mono); font-size: 9px;
  text-transform: uppercase; letter-spacing: 0.1em;
  padding: 2px 6px; border-radius: 2px; font-weight: 700;
}
.pm-status.early_warning { background: rgba(239,68,68,0.15);
                           color: var(--c-neg); }
.pm-status.watch         { background: rgba(234,179,8,0.15);
                           color: var(--c-watch); }
.pm-status.on_track      { background: rgba(16,185,129,0.15);
                           color: var(--c-pos); }
.pm-status.outperforming { background: rgba(59,130,246,0.15);
                           color: var(--c-blue); }
.pm-comp-rel.pos { color: var(--c-pos); }
.pm-comp-rel.neg { color: var(--c-neg); }
"""


def _format_money(mm: float) -> str:
    if mm is None:
        return "—"
    if abs(mm) >= 1000:
        return f"${mm/1000:.2f}B"
    if abs(mm) >= 1:
        return f"${mm:.1f}M"
    return f"${mm*1000:.0f}K"


def _format_pct(p: float) -> str:
    sign = "+" if p > 0 else ""
    return f"{sign}{p*100:.1f}%"


def render_monitor_dashboard(
    pv: PortfolioVariance,
    *,
    title: str = "Portfolio Monitor",
) -> str:
    """Render the dashboard HTML."""
    parts: List[str] = []
    parts.append("<!DOCTYPE html>")
    parts.append('<html lang="en"><head><meta charset="utf-8">')
    parts.append(f"<title>{_html.escape(title)} — "
                 f"{_html.escape(pv.fund_name)}</title>")
    parts.append(f"<style>{_CSS}</style></head><body>")
    parts.append('<div class="pm-wrap">')
    parts.append(
        '<div class="pm-title">RCM-MC PORTFOLIO MONITOR</div>')
    parts.append(
        f'<h1 class="pm-h1">{_html.escape(pv.fund_name)} — '
        f'{pv.n_assets} assets</h1>')

    # KPIs
    var_class = ("pos" if pv.total_variance_mm >= 0 else "neg")
    parts.append('<div class="pm-kpis">')
    for label, val, cls in (
        ("Plan EBITDA",
         _format_money(pv.total_plan_ebitda_mm), ""),
        ("Actual EBITDA",
         _format_money(pv.total_actual_ebitda_mm), ""),
        ("Variance",
         _format_money(pv.total_variance_mm), var_class),
        ("Variance %",
         _format_pct(pv.total_variance_pct), var_class),
        ("Early-warning count",
         str(pv.by_status.get("early_warning", 0)),
         "neg" if pv.by_status.get("early_warning", 0) > 0
         else ""),
    ):
        parts.append(
            f'<div class="pm-kpi">'
            f'<div class="pm-kpi-label">{label}</div>'
            f'<div class="pm-kpi-val {cls}">{val}</div></div>')
    parts.append('</div>')

    # Bridge
    parts.append('<div class="pm-bridge">')
    parts.append('<h3>Projected-vs-Actual EBITDA Bridge</h3>')
    bridge = pv.bridge_breakdown
    max_abs = max(
        abs(bridge.get("outperforming_contribution_mm", 0)),
        abs(bridge.get("on_track_contribution_mm", 0)),
        abs(bridge.get("watch_contribution_mm", 0)),
        abs(bridge.get("early_warning_contribution_mm", 0)),
        1.0,
    )
    color_map = {
        "outperforming": "#3b82f6",
        "on_track": "#10b981",
        "watch": "#eab308",
        "early_warning": "#ef4444",
    }
    label_map = {
        "outperforming": "Outperforming (>+5%)",
        "on_track": "On track (±5%)",
        "watch": "Watch (-5% to -10%)",
        "early_warning": "Early warning (<-10%)",
    }
    for status in ("outperforming", "on_track", "watch",
                   "early_warning"):
        v = bridge.get(f"{status}_contribution_mm", 0.0)
        width_pct = abs(v) / max_abs * 100
        parts.append(
            f'<div class="pm-bridge-row">'
            f'<div class="pm-bridge-label">'
            f'{label_map[status]}</div>'
            f'<div class="pm-bridge-bar">'
            f'<div class="pm-bridge-fill" '
            f'style="width:{width_pct:.1f}%; '
            f'background:{color_map[status]};"></div>'
            f'</div>'
            f'<div class="pm-bridge-val">'
            f'{_format_money(v)}</div></div>')
    parts.append('</div>')

    # Asset table
    parts.append('<table class="pm-tbl">')
    parts.append(
        '<thead><tr>'
        '<th>Deal</th><th>Sector</th>'
        '<th class="num">Plan EBITDA</th>'
        '<th class="num">Actual</th>'
        '<th class="num">Variance</th>'
        '<th class="num">Variance %</th>'
        '<th class="num">Comp-relative</th>'
        '<th>Status</th><th>Notes</th>'
        '</tr></thead><tbody>')
    for av in pv.asset_variances:
        comp_class = ("pos" if av.comp_relative >= 0 else "neg")
        var_class = ("pos" if av.ebitda_variance_mm >= 0
                     else "neg")
        parts.append(
            f'<tr>'
            f'<td><strong>{_html.escape(av.name)}</strong>'
            f'<br><span style="color:var(--c-faint);'
            f'font-family:var(--c-mono);font-size:10px">'
            f'{_html.escape(av.deal_id)}</span></td>'
            f'<td>{_html.escape(av.sector)}</td>'
            f'<td class="num">'
            f'{_format_money(av.plan_ebitda_mm)}</td>'
            f'<td class="num">'
            f'{_format_money(av.actual_ebitda_mm)}</td>'
            f'<td class="num pm-comp-rel {var_class}">'
            f'{_format_money(av.ebitda_variance_mm)}</td>'
            f'<td class="num pm-comp-rel {var_class}">'
            f'{_format_pct(av.ebitda_variance_pct)}</td>'
            f'<td class="num pm-comp-rel {comp_class}">'
            f'{_format_pct(av.comp_relative)}</td>'
            f'<td><span class="pm-status {av.status}">'
            f'{av.status.replace("_", " ")}</span></td>'
            f'<td style="color:var(--c-dim);font-size:10px">'
            f'{_html.escape(av.notes)}</td>'
            f'</tr>')
    parts.append('</tbody></table>')

    parts.append('</div></body></html>')
    return "\n".join(parts)
