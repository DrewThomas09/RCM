"""Bloomberg-style analyst workbench renderer for a single deal.

Produces a full HTML page at ``/analysis/<deal_id>`` that renders the
entire :class:`DealAnalysisPacket` across six tabs: Overview, RCM
Profile, EBITDA Bridge, Monte Carlo, Risk & Diligence, Provenance.

Design constraints from the spec:
- Dark theme — ``#0a0e17`` background, ``#111827`` panels, ``#1e293b``
  borders. ``#e2e8f0`` text, ``#94a3b8`` muted.
- JetBrains Mono for numeric cells; inter-system default for body.
- No border-radius > 4px. Dense padding (6px/10px on table cells).
- Zero external dependencies — no charts library, no framework, just
  inline SVG + HTML/CSS for every visualization.
- Interactive: the EBITDA Bridge tab has per-lever sliders that debounce
  300ms, POST to ``/api/analysis/<deal_id>/bridge``, and update the
  waterfall + total in-place via fetch.

This module is the single renderer — every tab reads from the *same*
packet object. If the packet's simulation section is missing the MC
tab renders an empty state, rather than the tab itself disappearing.
Progressive disclosure happens within tabs.
"""
from __future__ import annotations

import html
import json
from typing import Any, Dict, Iterable, List, Optional

from ..analysis.packet import (
    DealAnalysisPacket,
    DiligencePriority,
    MetricSource,
    PercentileSet,
    RiskSeverity,
    SectionStatus,
)


# ── Palette & CSS ────────────────────────────────────────────────────

# Exposed so tests can assert specific tokens are in the output.
PALETTE = {
    "bg":         "#0a0e17",
    "panel":      "#111827",
    "panel_alt":  "#0f172a",
    "border":     "#1e293b",
    "text":       "#e2e8f0",
    "text_dim":   "#94a3b8",
    "text_faint": "#64748b",
    "positive":   "#10b981",
    "negative":   "#ef4444",
    "warning":    "#f59e0b",
    "neutral":    "#6366f1",
    "accent":     "#3b82f6",
    "critical":   "#dc2626",
    "high":       "#f59e0b",
    "medium":     "#eab308",
    "low":        "#64748b",
}


_WORKBENCH_CSS = f"""
:root {{
  --wb-bg: {PALETTE['bg']};
  --wb-panel: {PALETTE['panel']};
  --wb-panel-alt: {PALETTE['panel_alt']};
  --wb-border: {PALETTE['border']};
  --wb-text: {PALETTE['text']};
  --wb-text-dim: {PALETTE['text_dim']};
  --wb-text-faint: {PALETTE['text_faint']};
  --wb-positive: {PALETTE['positive']};
  --wb-negative: {PALETTE['negative']};
  --wb-warning: {PALETTE['warning']};
  --wb-neutral: {PALETTE['neutral']};
  --wb-accent: {PALETTE['accent']};
}}

* {{ box-sizing: border-box; }}
body.analysis-workbench {{
  margin: 0; padding: 0;
  background: var(--wb-bg);
  color: var(--wb-text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter,
               Helvetica, Arial, sans-serif;
  font-size: 13px;
  line-height: 1.45;
  -webkit-font-smoothing: antialiased;
}}
.analysis-workbench .num,
.analysis-workbench td.num,
.analysis-workbench .kpi-value,
.analysis-workbench .hero-number {{
  font-family: "JetBrains Mono", "SF Mono", Menlo, Consolas,
               "Liberation Mono", monospace;
  font-variant-numeric: tabular-nums;
}}

/* Sticky header + tab nav */
.analysis-workbench .wb-header {{
  position: sticky; top: 0; z-index: 20;
  background: var(--wb-panel);
  border-bottom: 1px solid var(--wb-border);
  padding: 10px 16px;
}}
.analysis-workbench .wb-header-row {{
  display: flex; align-items: center; gap: 16px;
}}
.analysis-workbench .wb-deal-name {{
  font-size: 18px; font-weight: 600; letter-spacing: -0.01em;
  color: var(--wb-text);
}}
.analysis-workbench .wb-breadcrumb {{
  font-size: 11px; color: var(--wb-text-dim);
  text-transform: uppercase; letter-spacing: 0.06em;
  margin-bottom: 4px;
}}
.analysis-workbench .wb-breadcrumb a {{
  color: var(--wb-text-dim); text-decoration: none;
}}
.analysis-workbench .wb-breadcrumb a:hover {{ color: var(--wb-text); }}
.analysis-workbench .wb-action-bar {{
  margin-left: auto; display: flex; gap: 6px;
}}
.analysis-workbench .wb-btn {{
  background: var(--wb-panel-alt);
  border: 1px solid var(--wb-border);
  color: var(--wb-text);
  padding: 5px 12px; border-radius: 3px;
  font-size: 12px; cursor: pointer;
  text-decoration: none; display: inline-block;
}}
.analysis-workbench .wb-btn:hover {{ background: var(--wb-border); }}
.analysis-workbench .wb-btn-primary {{
  background: var(--wb-accent); border-color: var(--wb-accent);
}}

/* Tab nav */
.analysis-workbench .wb-tabs {{
  position: sticky; top: 58px; z-index: 15;
  background: var(--wb-bg);
  border-bottom: 1px solid var(--wb-border);
  display: flex; gap: 2px; padding: 0 16px;
}}
.analysis-workbench .wb-tab {{
  background: transparent; border: none; color: var(--wb-text-dim);
  padding: 10px 14px; font-size: 12px; cursor: pointer;
  border-bottom: 2px solid transparent;
  text-transform: uppercase; letter-spacing: 0.04em;
}}
.analysis-workbench .wb-tab:hover {{ color: var(--wb-text); }}
.analysis-workbench .wb-tab.active {{
  color: var(--wb-text); border-bottom-color: var(--wb-accent);
}}
.analysis-workbench .wb-tab-panel {{ display: none; padding: 14px 16px; }}
.analysis-workbench .wb-tab-panel.active {{ display: block; }}

/* Cards / panels */
.analysis-workbench .wb-card {{
  background: var(--wb-panel);
  border: 1px solid var(--wb-border);
  border-radius: 3px;
  padding: 12px 14px;
  margin-bottom: 10px;
}}
.analysis-workbench .wb-card-title {{
  font-size: 11px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.08em;
  color: var(--wb-text-dim); margin-bottom: 8px;
}}
.analysis-workbench .wb-grid {{
  display: grid; grid-template-columns: 60% 40%;
  gap: 10px;
}}
.analysis-workbench .wb-grid-5050 {{
  display: grid; grid-template-columns: 1fr 1fr; gap: 10px;
}}

/* Badges */
.analysis-workbench .wb-badge {{
  display: inline-block; padding: 1px 7px; border-radius: 3px;
  font-size: 11px; font-weight: 600;
}}
.analysis-workbench .wb-badge-critical {{
  background: rgba(220,38,38,0.18); color: {PALETTE['critical']};
}}
.analysis-workbench .wb-badge-high {{
  background: rgba(245,158,11,0.18); color: {PALETTE['high']};
}}
.analysis-workbench .wb-badge-medium {{
  background: rgba(234,179,8,0.14); color: {PALETTE['medium']};
}}
.analysis-workbench .wb-badge-low {{
  background: rgba(100,116,139,0.14); color: {PALETTE['low']};
}}
.analysis-workbench .wb-badge-grade-A {{
  background: rgba(16,185,129,0.18); color: {PALETTE['positive']};
}}
.analysis-workbench .wb-badge-grade-B {{
  background: rgba(59,130,246,0.18); color: {PALETTE['accent']};
}}
.analysis-workbench .wb-badge-grade-C {{
  background: rgba(245,158,11,0.18); color: {PALETTE['high']};
}}
.analysis-workbench .wb-badge-grade-D {{
  background: rgba(220,38,38,0.18); color: {PALETTE['critical']};
}}

/* Tables */
.analysis-workbench table.wb-table {{
  width: 100%; border-collapse: collapse;
  font-size: 13px;
}}
.analysis-workbench .wb-table th {{
  text-align: left; padding: 6px 10px;
  background: var(--wb-panel-alt);
  border-bottom: 1px solid var(--wb-border);
  color: var(--wb-text-dim);
  font-size: 10px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.06em;
}}
.analysis-workbench .wb-table td {{
  padding: 6px 10px;
  border-bottom: 1px solid var(--wb-border);
}}
.analysis-workbench .wb-table tbody tr:nth-child(even) {{
  background: var(--wb-panel-alt);
}}
.analysis-workbench .wb-table tbody tr:hover {{ background: var(--wb-border); }}
.analysis-workbench .wb-table td.num {{ text-align: right; }}
.analysis-workbench .wb-table td.center {{ text-align: center; }}
.analysis-workbench .wb-group-header td {{
  background: var(--wb-bg);
  color: var(--wb-text-dim);
  font-size: 11px; text-transform: uppercase;
  letter-spacing: 0.08em; padding: 8px 10px;
  font-weight: 600;
}}

/* Color semantics */
.analysis-workbench .pos {{ color: var(--wb-positive); }}
.analysis-workbench .neg {{ color: var(--wb-negative); }}
.analysis-workbench .warn {{ color: var(--wb-warning); }}
.analysis-workbench .dim {{ color: var(--wb-text-dim); }}
.analysis-workbench .hero-number {{ font-size: 28px; font-weight: 700; }}
.analysis-workbench .kpi-value {{ font-size: 20px; font-weight: 600; }}
.analysis-workbench .kpi-label {{
  font-size: 10px; color: var(--wb-text-dim);
  text-transform: uppercase; letter-spacing: 0.06em;
}}

/* Radial progress (completeness) */
.analysis-workbench .radial {{
  width: 90px; height: 90px; position: relative;
  display: inline-block; vertical-align: middle;
}}
.analysis-workbench .radial svg {{ transform: rotate(-90deg); }}
.analysis-workbench .radial .radial-label {{
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  font-family: "JetBrains Mono", monospace;
  font-size: 18px; font-weight: 700;
}}

/* Waterfall */
.analysis-workbench .waterfall {{ display: flex; flex-direction: column; gap: 2px; }}
.analysis-workbench .wf-row {{
  display: grid; grid-template-columns: 160px 1fr 110px;
  gap: 8px; align-items: center;
  padding: 4px 0; font-size: 12px;
}}
.analysis-workbench .wf-bar {{
  height: 16px; border-radius: 2px;
  background: var(--wb-accent);
}}
.analysis-workbench .wf-bar.pos {{ background: var(--wb-positive); }}
.analysis-workbench .wf-bar.neg {{ background: var(--wb-negative); }}
.analysis-workbench .wf-bar.anchor {{ background: var(--wb-text-dim); }}
.analysis-workbench .wf-track {{ position: relative; height: 16px; background: var(--wb-panel-alt); }}
.analysis-workbench .wf-track .wf-bar {{
  position: absolute; top: 0;
}}

/* Sliders */
.analysis-workbench .slider-row {{
  display: grid; grid-template-columns: 160px 1fr 80px 60px;
  align-items: center; gap: 10px; padding: 6px 0;
  font-size: 12px;
}}
.analysis-workbench input[type="range"].wb-slider {{
  width: 100%; accent-color: var(--wb-accent);
}}
.analysis-workbench .slider-label {{ color: var(--wb-text-dim); }}
.analysis-workbench .slider-target {{
  font-family: "JetBrains Mono", monospace; color: var(--wb-text);
}}
.analysis-workbench .slider-delta {{
  font-family: "JetBrains Mono", monospace; font-size: 11px;
}}

/* Histogram (inline SVG wrapper) */
.analysis-workbench .histo svg {{ display: block; width: 100%; height: auto; }}

/* Tornado */
.analysis-workbench .tornado-row {{
  display: grid; grid-template-columns: 180px 1fr 90px;
  gap: 8px; padding: 3px 0; font-size: 12px;
  align-items: center;
}}
.analysis-workbench .tornado-bar {{
  height: 14px; background: var(--wb-accent); border-radius: 2px;
}}

/* Risk cards */
.analysis-workbench .risk-card {{
  border-left: 3px solid var(--wb-accent);
  padding: 8px 12px; margin-bottom: 6px;
  background: var(--wb-panel);
}}
.analysis-workbench .risk-card.severity-CRITICAL {{ border-left-color: {PALETTE['critical']}; }}
.analysis-workbench .risk-card.severity-HIGH {{ border-left-color: {PALETTE['high']}; }}
.analysis-workbench .risk-card.severity-MEDIUM {{ border-left-color: {PALETTE['medium']}; }}
.analysis-workbench .risk-card.severity-LOW {{ border-left-color: {PALETTE['low']}; }}
.analysis-workbench .risk-title {{ font-weight: 600; font-size: 13px; }}
.analysis-workbench .risk-detail {{ font-size: 12px; color: var(--wb-text-dim); margin-top: 3px; }}

/* Diligence question */
.analysis-workbench .dq-card {{
  padding: 8px 12px; margin-bottom: 6px;
  background: var(--wb-panel-alt);
  border: 1px solid var(--wb-border);
  border-radius: 2px;
}}
.analysis-workbench .dq-priority {{
  display: inline-block; padding: 1px 6px;
  margin-right: 8px; border-radius: 3px;
  font-family: "JetBrains Mono", monospace;
  font-size: 10px; font-weight: 700;
}}
.analysis-workbench .dq-P0 {{ background: rgba(220,38,38,0.18); color: {PALETTE['critical']}; }}
.analysis-workbench .dq-P1 {{ background: rgba(245,158,11,0.18); color: {PALETTE['high']}; }}
.analysis-workbench .dq-P2 {{ background: rgba(100,116,139,0.14); color: {PALETTE['low']}; }}

/* Provenance list */
.analysis-workbench .prov-row {{
  display: grid; grid-template-columns: 220px 120px 1fr;
  gap: 8px; padding: 6px 0;
  border-bottom: 1px solid var(--wb-border); font-size: 12px;
}}
.analysis-workbench .prov-source-icon {{
  display: inline-block; width: 18px; text-align: center;
  margin-right: 4px;
}}

/* Heatmap */
.analysis-workbench .heatmap {{
  display: grid; gap: 2px;
  font-family: "JetBrains Mono", monospace; font-size: 11px;
}}
.analysis-workbench .heatmap-cell {{
  padding: 6px 10px; text-align: center;
  background: var(--wb-panel-alt);
}}
.analysis-workbench details summary {{ cursor: pointer; padding: 4px 0; }}

/* Scenarios tab — side-by-side cards + pairwise matrix + overlay */
.analysis-workbench .scenario-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px; margin-bottom: 16px;
}}
.analysis-workbench .scenario-card {{
  background: var(--wb-panel-alt);
  border: 1px solid var(--wb-border);
  padding: 12px; border-radius: 4px;
}}
.analysis-workbench .scenario-card.recommended {{
  border: 2px solid var(--wb-accent);
  box-shadow: 0 0 0 1px var(--wb-accent) inset;
}}
.analysis-workbench .scenario-name {{
  font-weight: 600; font-size: 14px; margin-bottom: 8px;
  display: flex; align-items: center; gap: 6px;
}}
.analysis-workbench .scenario-rec-badge {{
  background: var(--wb-accent); color: white;
  font-size: 10px; padding: 1px 6px; border-radius: 3px;
  letter-spacing: 0.04em; text-transform: uppercase;
}}
.analysis-workbench .scenario-kpi {{
  display: grid; grid-template-columns: 1fr auto; gap: 4px;
  font-size: 12px; padding: 2px 0;
}}
.analysis-workbench .scenario-kpi .dim {{ color: var(--wb-text-dim); }}
.analysis-workbench .scenario-drivers {{
  margin-top: 8px; font-size: 11px; color: var(--wb-text-dim);
}}
.analysis-workbench .scenario-drivers ol {{
  margin: 4px 0 0; padding-left: 18px;
}}
.analysis-workbench .scenario-mini {{
  margin-top: 8px;
}}
.analysis-workbench .scenario-mini svg {{
  display: block; width: 100%; height: 60px;
}}
.analysis-workbench .pairwise-matrix {{
  border-collapse: collapse; margin-top: 8px;
  font-size: 12px;
}}
.analysis-workbench .pairwise-matrix th,
.analysis-workbench .pairwise-matrix td {{
  padding: 6px 10px; text-align: right;
  border: 1px solid var(--wb-border);
  font-family: "JetBrains Mono", monospace;
}}
.analysis-workbench .pairwise-matrix th {{
  background: var(--wb-panel); font-weight: 600;
  color: var(--wb-text-dim); text-transform: uppercase;
  font-size: 10px; letter-spacing: 0.04em;
}}
.analysis-workbench .pairwise-matrix td.pw-self {{
  color: var(--wb-text-faint);
}}
.analysis-workbench .pairwise-matrix td.pw-high {{
  background: rgba(16,185,129,0.18); color: var(--wb-positive);
}}
.analysis-workbench .pairwise-matrix td.pw-low {{
  background: rgba(239,68,68,0.18); color: var(--wb-negative);
}}
.analysis-workbench .scenario-overlay-svg {{
  width: 100%; height: 200px; display: block;
  background: var(--wb-panel-alt);
  border: 1px solid var(--wb-border);
}}
.analysis-workbench .scenario-empty {{
  padding: 24px; text-align: center;
  color: var(--wb-text-dim); font-size: 13px;
}}
.analysis-workbench .scenario-add-form {{
  display: grid; grid-template-columns: 1fr 1fr; gap: 8px;
  padding: 12px; background: var(--wb-panel-alt);
  border: 1px solid var(--wb-border); border-radius: 4px;
  margin-top: 12px;
}}
.analysis-workbench .scenario-add-form.hidden {{ display: none; }}
.analysis-workbench .scenario-add-form label {{
  font-size: 11px; color: var(--wb-text-dim);
  display: flex; flex-direction: column; gap: 2px;
}}
.analysis-workbench .scenario-add-form input {{
  background: var(--wb-panel); color: var(--wb-text);
  border: 1px solid var(--wb-border); padding: 4px 8px;
  font-family: "JetBrains Mono", monospace; font-size: 12px;
}}
.analysis-workbench .scenario-add-form .full-row {{ grid-column: 1 / -1; }}
.analysis-workbench .scenario-palette-0 {{ --sc-color: {PALETTE['accent']}; }}
.analysis-workbench .scenario-palette-1 {{ --sc-color: {PALETTE['positive']}; }}
.analysis-workbench .scenario-palette-2 {{ --sc-color: {PALETTE['warning']}; }}
.analysis-workbench .scenario-palette-3 {{ --sc-color: {PALETTE['negative']}; }}
.analysis-workbench .scenario-swatch {{
  display: inline-block; width: 10px; height: 10px;
  background: var(--sc-color); border-radius: 2px;
}}

/* ── Prompt 32: Inline explain panel ──────────────────────── */
.analysis-workbench .wb-explain-panel {{
  position: fixed; top: 0; right: -400px; width: 380px; height: 100vh;
  background: var(--wb-panel); border-left: 1px solid var(--wb-border);
  z-index: 50; padding: 20px; overflow-y: auto;
  transition: right 0.25s ease-in-out;
  box-shadow: -4px 0 16px rgba(0,0,0,0.3);
}}
.analysis-workbench .wb-explain-panel.open {{ right: 0; }}
.analysis-workbench .wb-explain-panel .ep-close {{
  position: absolute; top: 12px; right: 16px; cursor: pointer;
  font-size: 18px; color: var(--wb-text-dim); background: none; border: none;
}}
.analysis-workbench .wb-explain-panel .ep-title {{
  font-size: 16px; font-weight: 600; margin-bottom: 12px;
  padding-right: 30px;
}}
.analysis-workbench .wb-explain-panel .ep-section {{
  margin-bottom: 14px; font-size: 12px;
}}
.analysis-workbench .wb-explain-panel .ep-label {{
  font-size: 10px; color: var(--wb-text-dim); text-transform: uppercase;
  letter-spacing: .06em; margin-bottom: 4px;
}}
.analysis-workbench .wb-explain-panel .ep-bar {{
  background: var(--wb-border); height: 8px; border-radius: 4px;
  overflow: hidden; margin-top: 4px;
}}
.analysis-workbench .wb-explain-panel .ep-bar > div {{
  height: 100%; border-radius: 4px;
}}
.analysis-workbench [data-explain] {{ cursor: pointer; }}
.analysis-workbench [data-explain]:hover {{ text-decoration: underline; }}

/* ── Prompt 56: Mobile-responsive breakpoints ────────────────── */
@media (max-width: 768px) {{
  .analysis-workbench .wb-tabs {{ flex-wrap: wrap; gap: 2px; }}
  .analysis-workbench .wb-tab {{ font-size: 10px; padding: 6px 8px; }}
  .analysis-workbench .wb-header-row {{ flex-wrap: wrap; gap: 8px; }}
  .analysis-workbench .wb-deal-name {{ font-size: 16px; }}
  .analysis-workbench .wb-grid {{ grid-template-columns: 1fr; }}
  .analysis-workbench .wb-grid-5050 {{ grid-template-columns: 1fr; }}
  .analysis-workbench .wb-table {{ font-size: 11px; display: block; overflow-x: auto; }}
  .analysis-workbench .scenario-grid {{ grid-template-columns: 1fr; }}
  .analysis-workbench .hero-number {{ font-size: 28px; }}
  .analysis-workbench .wb-action-bar {{ flex-wrap: wrap; }}
  .analysis-workbench input.wb-slider {{ min-height: 48px; }}
}}
@media (min-width: 769px) and (max-width: 1024px) {{
  .analysis-workbench .wb-grid {{ grid-template-columns: 1fr 1fr; }}
  .analysis-workbench .scenario-grid {{ grid-template-columns: 1fr 1fr; }}
}}

/* ── Print-friendly stylesheet ────────────────────────────────── */
@media print {{
  body {{ background: white !important; color: black !important; padding: 0 !important; }}
  nav, .wb-action-bar, .wb-tabs, .skip-link, footer,
  .breadcrumb, button, .wb-explain-panel {{ display: none !important; }}
  .analysis-workbench {{
    background: white !important; color: black !important;
    border: none !important; box-shadow: none !important;
  }}
  .analysis-workbench .wb-section {{ display: block !important; page-break-inside: avoid; }}
  .analysis-workbench .wb-card {{
    background: white !important; border: 1px solid #ccc !important;
    box-shadow: none !important; break-inside: avoid;
  }}
  .analysis-workbench .wb-deal-name {{ color: black !important; }}
  .analysis-workbench .wb-grid {{ grid-template-columns: 1fr 1fr; }}
  .analysis-workbench .hero-number {{ color: black !important; }}
  table {{ border-collapse: collapse; }}
  th {{ background: #f0f0f0 !important; color: black !important; }}
  td, th {{ border: 1px solid #ccc !important; }}
  a {{ color: black !important; text-decoration: underline; }}
  a[href]:after {{ content: " (" attr(href) ")"; font-size: 0.8em; color: #666; }}
}}
"""


# ── Value formatting ─────────────────────────────────────────────────

def _fmt_money(v: Optional[float]) -> str:
    if v is None or v != v:
        return "—"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "—"
    if abs(f) >= 1e9:
        return f"${f / 1e9:.2f}B"
    if abs(f) >= 1e6:
        return f"${f / 1e6:.1f}M"
    if abs(f) >= 1e3:
        return f"${f / 1e3:,.0f}K"
    return f"${f:,.0f}"


def _fmt_pct(v: Optional[float], *, one_dp: bool = True) -> str:
    if v is None or v != v:
        return "—"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "—"
    fmt = "{:.1f}%" if one_dp else "{:.0f}%"
    return fmt.format(f)


def _fmt_signed_pct(v: Optional[float]) -> str:
    if v is None:
        return "—"
    sign = "+" if v > 0 else ""
    return f"{sign}{v:.1f}%"


def _fmt_num(v: Optional[float], *, dp: int = 2) -> str:
    if v is None or v != v:
        return "—"
    try:
        return f"{float(v):.{dp}f}"
    except (TypeError, ValueError):
        return "—"


def _fmt_moic(v: Optional[float]) -> str:
    if v is None:
        return "—"
    return f"{float(v):.2f}x"


def _esc(s: Any) -> str:
    return html.escape("" if s is None else str(s))


# ── Section renderers ────────────────────────────────────────────────

def _render_header(packet: DealAnalysisPacket) -> str:
    grade = packet.completeness.grade or "—"
    grade_class = f"wb-badge-grade-{grade}" if grade in ("A", "B", "C", "D") else "wb-badge-low"
    as_of = packet.as_of.isoformat() if packet.as_of else "current"
    cov = _fmt_pct(packet.completeness.coverage_pct * 100)
    freshness = "fresh" if not packet.completeness.stale_fields else \
                f"{len(packet.completeness.stale_fields)} stale"
    return f"""
    <div class="wb-header">
      <div class="wb-breadcrumb">
        <a href="/home">home</a> &nbsp;›&nbsp;
        <a href="/analysis">analysis</a> &nbsp;›&nbsp;
        <a href="/deal/{_esc(packet.deal_id)}">{_esc(packet.deal_name or packet.deal_id)}</a>
        &nbsp;›&nbsp; analysis
      </div>
      <div class="wb-header-row">
        <div class="wb-deal-name">{_esc(packet.deal_name or packet.deal_id)}</div>
        <span class="wb-badge {grade_class}">completeness: {grade}</span>
        <span class="dim">coverage {cov}</span>
        <span class="dim">as-of {_esc(as_of)}</span>
        <span class="dim">{_esc(freshness)}</span>
        <div class="wb-action-bar">
          <form method="POST" action="/api/analysis/{_esc(packet.deal_id)}/rebuild" style="display:inline;">
            <button class="wb-btn wb-btn-primary" type="submit">Rebuild</button>
          </form>
          <a class="wb-btn wb-btn-primary" href="/models/dcf/{_esc(packet.deal_id)}">DCF</a>
          <a class="wb-btn wb-btn-primary" href="/models/lbo/{_esc(packet.deal_id)}">LBO</a>
          <a class="wb-btn" href="/models/financials/{_esc(packet.deal_id)}">Financials</a>
          <a class="wb-btn" href="/api/analysis/{_esc(packet.deal_id)}">JSON</a>
          <a class="wb-btn" href="/api/analysis/{_esc(packet.deal_id)}/diligence-questions">Diligence CSV</a>
          <a class="wb-btn" href="/api/deals/{_esc(packet.deal_id)}/package">Download ZIP</a>
          <span style="flex:1;"></span>
          <form method="POST" action="/api/deals/{_esc(packet.deal_id)}/archive" style="display:inline;">
            <button class="wb-btn" type="submit"
                    onclick="return confirm('Archive this deal? It will be hidden from the dashboard.');"
                    style="color:#f59e0b;" aria-label="Archive this deal">Archive</button>
          </form>
          <button class="wb-btn" type="button"
                  onclick="if(confirm('Permanently delete this deal and ALL associated data? This cannot be undone.')){{fetch('/api/deals/{_esc(packet.deal_id)}',{{method:'DELETE'}}).then(r=>r.json()).then(d=>{{if(d.deleted){{if(window.rcmToast)rcmToast('Deal deleted','success');setTimeout(function(){{window.location='/';}},500);}}}}).catch(function(){{if(window.rcmToast)rcmToast('Delete failed','error');}});}}"
                  style="color:#ef4444;" aria-label="Permanently delete this deal">Delete</button>
          <span class="dim" style="font-size:0.7rem;margin-left:8px;" title="Press ? for keyboard shortcuts">⌨ ?=help</span>
        </div>
      </div>
    </div>
    """


def _render_tab_nav() -> str:
    tabs = [
        ("overview",   "Overview"),
        ("profile",    "RCM Profile"),
        ("bridge",     "EBITDA Bridge"),
        ("mc",         "Monte Carlo"),
        ("scenarios",  "Scenarios"),
        ("risk",       "Risk & Diligence"),
        ("provenance", "Provenance"),
    ]
    buttons = "\n".join(
        f'<button class="wb-tab{" active" if i == 0 else ""}" data-tab="{k}">{v}</button>'
        for i, (k, v) in enumerate(tabs)
    )
    return f'<div class="wb-tabs">{buttons}</div>'


# Overview --------------------------------------------------------------

def _render_overview(packet: DealAnalysisPacket) -> str:
    cov_pct = float(packet.completeness.coverage_pct or 0.0)
    missing = [m for m in packet.completeness.missing_fields[:5]]
    missing_html = "".join(
        f'<li><span class="dim">#{m.ebitda_sensitivity_rank}</span> '
        f'{_esc(m.display_name or m.metric_key)} '
        f'<span class="dim">[{_esc(m.category)}]</span></li>'
        for m in missing
    ) or '<li class="dim">all required metrics observed</li>'

    key_findings = []
    for rf in packet.risk_flags[:5]:
        sev = rf.severity.value if hasattr(rf.severity, "value") else str(rf.severity)
        key_findings.append(
            f'<li><span class="wb-badge wb-badge-{sev.lower()}">{sev}</span> '
            f'{_esc(rf.title or rf.detail[:80])}</li>'
        )
    findings_html = "\n".join(key_findings) or '<li class="dim">no risk flags</li>'

    peers = packet.comparables.peers if packet.comparables else []
    top_peer = peers[0] if peers else None
    if peers:
        avg_sim = sum(p.similarity_score for p in peers) / len(peers)
        comp_summary = (
            f"{len(peers)} hospitals · avg similarity "
            f'<span class="num">{avg_sim:.2f}</span>'
            + (f' · top peer <span class="num">{_esc(top_peer.id)}</span>'
               if top_peer else "")
        )
    else:
        comp_summary = '<span class="dim">no comparable set available</span>'

    # Hero number — EBITDA total impact from bridge.
    total_impact = float(packet.ebitda_bridge.total_ebitda_impact or 0.0)
    ev_at_multiple = packet.ebitda_bridge.ev_impact_at_multiple or {}
    ev_bits = " · ".join(
        f'<span class="dim">{k}</span> {_fmt_money(v)}'
        for k, v in list(ev_at_multiple.items())[:3]
    ) or '<span class="dim">no EV computed</span>'

    # Returns distribution (MOIC) mini-summary if MC available.
    mc = packet.simulation
    moic_block = '<span class="dim">Monte Carlo not run</span>'
    if mc is not None and mc.status == SectionStatus.OK:
        moic_block = (
            f'<div><span class="kpi-label">MOIC P10 / P50 / P90</span></div>'
            f'<div class="num">'
            f'{_fmt_moic(mc.moic.p10)} · {_fmt_moic(mc.moic.p50)} · {_fmt_moic(mc.moic.p90)}'
            f'</div>'
        )

    # Risk summary badges.
    sev_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for rf in packet.risk_flags:
        val = rf.severity.value if hasattr(rf.severity, "value") else str(rf.severity)
        sev_counts[val] = sev_counts.get(val, 0) + 1
    risk_badges = " ".join(
        f'<span class="wb-badge wb-badge-{sev.lower()}">{sev}: {n}</span>'
        for sev, n in sev_counts.items() if n > 0
    ) or '<span class="dim">no risk flags</span>'

    # Radial progress SVG.
    radius = 40
    circ = 2 * 3.14159 * radius
    dash = circ * cov_pct
    radial_svg = (
        f'<svg width="90" height="90" viewBox="0 0 90 90">'
        f'<circle cx="45" cy="45" r="{radius}" fill="none" '
        f'stroke="{PALETTE["border"]}" stroke-width="8"/>'
        f'<circle cx="45" cy="45" r="{radius}" fill="none" '
        f'stroke="{PALETTE["accent"]}" stroke-width="8" '
        f'stroke-dasharray="{dash:.1f} {circ:.1f}" stroke-linecap="round"/>'
        f'</svg>'
    )
    radial_label = f'<div class="radial-label">{int(cov_pct*100)}%</div>'

    return f"""
    <div class="wb-tab-panel active" data-panel="overview">
      <div class="wb-grid">
        <div>
          <div class="wb-card">
            <div class="wb-card-title">Completeness</div>
            <div style="display:flex;gap:14px;align-items:center;">
              <div class="radial">{radial_svg}{radial_label}</div>
              <div>
                <div class="kpi-value">{packet.completeness.observed_count}/{packet.completeness.total_metrics}</div>
                <div class="kpi-label">metrics observed · grade {packet.completeness.grade or "—"}</div>
              </div>
            </div>
            <div class="wb-card-title" style="margin-top:12px;">Top missing metrics (by EBITDA sensitivity)</div>
            <ol style="padding-left:20px; margin:4px 0;">{missing_html}</ol>
          </div>
          <div class="wb-card">
            <div class="wb-card-title">Key Findings</div>
            <ul style="padding-left:18px; margin:4px 0;">{findings_html}</ul>
          </div>
          <div class="wb-card">
            <div class="wb-card-title">Comparable Set</div>
            <div>{comp_summary}</div>
          </div>
        </div>
        <div>
          <div class="wb-card">
            <div class="kpi-label">EBITDA Opportunity</div>
            <div class="hero-number pos">{_fmt_money(total_impact)}</div>
            <div class="dim" style="font-size:11px;margin-top:4px;">
              current → target (moderate tier)
            </div>
            <div style="margin-top:10px;font-size:12px;">{ev_bits}</div>
          </div>
          <div class="wb-card">
            <div class="wb-card-title">Returns</div>
            {moic_block}
          </div>
          <div class="wb-card">
            <div class="wb-card-title">Risk Summary</div>
            <div>{risk_badges}</div>
          </div>
          {_render_next_actions(packet)}
        </div>
      </div>
    </div>
    """


# RCM Profile -----------------------------------------------------------

_SOURCE_ICON = {
    MetricSource.OBSERVED:  "👤",
    MetricSource.PREDICTED: "🔮",
    MetricSource.BENCHMARK: "📊",
    MetricSource.UNKNOWN:   "·",
}


def _metric_category_for(metric_key: str) -> str:
    try:
        from ..analysis.completeness import RCM_METRIC_REGISTRY
        return (RCM_METRIC_REGISTRY.get(metric_key) or {}).get("category") or "other"
    except Exception:  # noqa: BLE001
        return "other"


def _render_next_actions(packet: DealAnalysisPacket) -> str:
    """'What Should I Do Next?' card — 3 prioritized actions based
    on the packet's current state (Prompt 32 enhancement).

    Associates see this and know exactly what to click — no guessing.
    """
    actions: List[str] = []
    deal_id = _esc(packet.deal_id)

    # Low completeness → upload data.
    grade = getattr(packet.completeness, "grade", "") or ""
    if grade in ("C", "D") or not grade:
        actions.append(
            f'<div>📊 <strong>Upload more data</strong> — completeness is '
            f'{grade or "?"}, which limits prediction accuracy. '
            f'<a href="/new-deal/step3?deal_id={deal_id}">Upload files →</a></div>'
        )

    # Critical risks → review.
    critical_count = sum(
        1 for rf in (packet.risk_flags or [])
        if (rf.severity.value if hasattr(rf.severity, "value") else str(rf.severity)) == "CRITICAL"
    )
    if critical_count > 0:
        actions.append(
            f'<div>🔴 <strong>Review {critical_count} critical risk(s)</strong> — '
            f'click the Risk & Diligence tab to see details and address '
            f'the top-priority flags.</div>'
        )

    # No MC → run simulation.
    if packet.simulation is None or (
        hasattr(packet.simulation, "status")
        and str(getattr(packet.simulation.status, "value", ""))
        not in ("OK",)
    ):
        actions.append(
            f'<div>🎲 <strong>Run Monte Carlo</strong> — no simulation on '
            f'this analysis yet. '
            f'<a href="/api/analysis/{deal_id}/simulate/v2" '
            f'style="color:{PALETTE["accent"]};">Run now →</a></div>'
        )

    # Missing diligence questions answered → export package.
    if packet.diligence_questions and not actions:
        actions.append(
            f'<div>📦 <strong>Generate IC package</strong> — analysis is '
            f'complete. '
            f'<a href="/api/analysis/{deal_id}/export?format=package" '
            f'style="color:{PALETTE["accent"]};">Export →</a></div>'
        )

    if not actions:
        actions.append(
            '<div style="color:#10b981;">✓ <strong>Looking good</strong> '
            '— completeness, risks, and simulation are all in order.</div>'
        )

    body = "\n".join(actions[:3])
    return f"""
    <div class="wb-card">
      <div class="wb-card-title">What Should I Do Next?</div>
      <div style="display:flex;flex-direction:column;gap:8px;font-size:12px;">{body}</div>
    </div>
    """


def _render_trend_cell(forecast: Dict[str, Any]) -> str:
    """Inline trend arrow + tiny sparkline SVG for one metric.

    Renders alongside the metric name in the RCM Profile table. Arrow
    is ↑ / ↓ / → colored by direction:

    - green for "improving"
    - red for "deteriorating"
    - grey for "stable" or low-n series

    The SVG is a 60×20 sparkline of the historical series (no
    interactivity — click the metric name for the full explain
    panel). Historical + forecast dashed continuation is sized so the
    row height stays the same as metric rows without a forecast.
    """
    trend = (forecast or {}).get("trend") or {}
    direction = trend.get("direction") or "stable"
    slope = float(trend.get("slope_per_period") or 0)
    n = int(trend.get("n_periods") or 0)
    historical = forecast.get("historical") or []
    forecasted = forecast.get("forecasted") or []

    arrow = {"improving": "↑", "deteriorating": "↓"}.get(direction, "→")
    color = {
        "improving": PALETTE["positive"],
        "deteriorating": PALETTE["negative"],
    }.get(direction, PALETTE["text_faint"])
    tooltip = (
        f"{direction}, {slope:+.3f}/period across {n} periods"
    )

    # Tiny sparkline.
    sparkline = ""
    if historical:
        vals = [float(row.get("value") or 0) for row in historical]
        fut_vals = [float(row.get("value") or 0) for row in forecasted]
        full = vals + fut_vals
        if full:
            lo = min(full)
            hi = max(full)
            span = hi - lo if (hi - lo) > 0 else 1.0
            w, h = 60, 20
            n_total = len(full) - 1 if len(full) > 1 else 1
            def _pt(i: int, v: float) -> str:
                x = (i / max(1, n_total)) * (w - 2) + 1
                y = h - 2 - ((v - lo) / span) * (h - 4)
                return f"{x:.1f},{y:.1f}"
            hist_pts = " ".join(_pt(i, v) for i, v in enumerate(vals))
            offset = len(vals) - 1
            fut_pts = " ".join(
                _pt(offset + i + 1, v) for i, v in enumerate(fut_vals)
            )
            last_hist_pt = _pt(offset, vals[-1]) if vals else ""
            dashed_pts = f"{last_hist_pt} {fut_pts}".strip() if fut_vals else ""
            sparkline = (
                f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
                f'style="vertical-align:middle;margin-left:4px;">'
                f'<polyline points="{hist_pts}" fill="none" '
                f'stroke="{color}" stroke-width="1.2"/>'
                + (f'<polyline points="{dashed_pts}" fill="none" '
                   f'stroke="{color}" stroke-dasharray="2,2" '
                   f'stroke-width="1"/>' if dashed_pts else "")
                + "</svg>"
            )

    return (
        f'<span class="dim" style="margin-left:6px;color:{color};" '
        f'title="{_esc(tooltip)}">{arrow}</span>{sparkline}'
    )


def _render_rcm_profile(packet: DealAnalysisPacket) -> str:
    try:
        from ..analysis.completeness import RCM_METRIC_REGISTRY
    except Exception:  # noqa: BLE001
        RCM_METRIC_REGISTRY = {}

    # Group rows by category. Iterate in registry order so categories
    # have a stable sort key even if some are missing.
    rows_by_category: Dict[str, List[str]] = {}
    for metric_key in packet.rcm_profile:
        cat = _metric_category_for(metric_key)
        rows_by_category.setdefault(cat, []).append(metric_key)

    category_order = ["denials", "collections", "ar", "claims", "coding", "financial", "other"]
    parts: List[str] = []
    parts.append(
        '<table class="wb-table"><thead><tr>'
        '<th>Metric</th><th>Current</th><th class="center">Src</th>'
        '<th class="num">P25</th><th class="num">P50</th><th class="num">P75</th>'
        '<th class="num">Δ vs P50</th><th>Confidence</th>'
        '</tr></thead><tbody>'
    )
    for cat in category_order:
        keys = rows_by_category.get(cat) or []
        if not keys:
            continue
        parts.append(f'<tr class="wb-group-header"><td colspan="8">{_esc(cat.upper())}</td></tr>')
        for metric_key in keys:
            pm = packet.rcm_profile[metric_key]
            meta = RCM_METRIC_REGISTRY.get(metric_key) or {}
            p25, p50, p75 = meta.get("benchmark_p25"), meta.get("benchmark_p50"), meta.get("benchmark_p75")
            unit = meta.get("unit") or ""
            delta = None
            cell_class = "dim"
            if p50 is not None:
                try:
                    delta = float(pm.value) - float(p50)
                    # Direction: lower is better for rate/days metrics
                    lower_better = cat in ("denials", "ar") or metric_key in (
                        "cost_to_collect", "bad_debt_rate", "ar_over_90_pct",
                        "charge_lag_days", "claim_rejection_rate",
                        "late_charge_pct",
                    )
                    better = (delta < 0) if lower_better else (delta > 0)
                    if abs(delta) < 1e-9:
                        cell_class = "dim"
                    else:
                        cell_class = "pos" if better else "neg"
                except (TypeError, ValueError):
                    delta = None
            value_fmt = (
                _fmt_pct(pm.value) if unit == "pct"
                else (f"{pm.value:.1f}d" if unit == "days"
                      else (_fmt_money(pm.value) if unit == "dollars"
                            else _fmt_num(pm.value, dp=2)))
            )
            src_icon = _SOURCE_ICON.get(pm.source, "·")
            quality = pm.quality or ""
            conf_bar = _quality_bar(quality)
            # Prompt 27: inline trend arrow + sparkline for metrics
            # with uploaded history.
            forecast = (packet.metric_forecasts or {}).get(metric_key)
            trend_html = _render_trend_cell(forecast) if forecast else ""
            # Prompt 28: ⚠ when the completeness anomalies list
            # flagged this metric.
            anomaly_html = ""
            for a in (packet.completeness.anomalies or []):
                if a.get("metric_key") != metric_key:
                    continue
                tone = {
                    "CRITICAL": PALETTE["critical"],
                    "HIGH": PALETTE["high"],
                    "MEDIUM": PALETTE["medium"],
                }.get(a.get("severity", "MEDIUM"), PALETTE["low"])
                anomaly_html = (
                    f'<span style="color:{tone};margin-left:4px;" '
                    f'title="{_esc(a.get("explanation") or "")}">⚠</span>'
                )
                break
            parts.append(
                '<tr>'
                f'<td><a href="#prov-{_esc(metric_key)}" class="dim" style="text-decoration:none;">{_esc(metric_key)}</a>{anomaly_html}{trend_html}</td>'
                f'<td class="num {cell_class}">{value_fmt}</td>'
                f'<td class="center" title="{_esc(pm.source.value)}">'
                f'<span role="img" aria-label="{_esc(pm.source.value)}">{src_icon}</span></td>'
                f'<td class="num dim">{_fmt_num(p25, dp=1) if p25 is not None else "—"}</td>'
                f'<td class="num dim">{_fmt_num(p50, dp=1) if p50 is not None else "—"}</td>'
                f'<td class="num dim">{_fmt_num(p75, dp=1) if p75 is not None else "—"}</td>'
                f'<td class="num {cell_class}">{_fmt_signed_pct(delta) if delta is not None else "—"}</td>'
                f'<td>{conf_bar}</td>'
                '</tr>'
            )
    parts.append('</tbody></table>')

    # Payer-performance heatmap (simple grid).
    heatmap_html = _render_payer_heatmap(packet)

    return f"""
    <div class="wb-tab-panel" data-panel="profile">
      <div class="wb-card">
        <div class="wb-card-title">Metric detail</div>
        {''.join(parts)}
      </div>
      <div class="wb-card">
        <div class="wb-card-title">Payer performance matrix</div>
        {heatmap_html}
      </div>
    </div>
    """


def _quality_bar(q: str) -> str:
    colors = {"high": PALETTE["positive"], "medium": PALETTE["warning"], "low": PALETTE["negative"]}
    w = {"high": 60, "medium": 40, "low": 20}.get(q, 10)
    c = colors.get(q, PALETTE["text_faint"])
    return (
        f'<div style="display:inline-block;width:64px;background:{PALETTE["border"]};'
        f'height:6px;vertical-align:middle;">'
        f'<div style="width:{w}px;height:6px;background:{c};"></div></div>'
    )


def _render_payer_heatmap(packet: DealAnalysisPacket) -> str:
    """Render denial_rate_* metrics by payer in a small grid."""
    payers = [
        ("Medicare FFS", "denial_rate_medicare_ffs"),
        ("Medicare Advantage", "denial_rate_medicare_advantage"),
        ("Commercial", "denial_rate_commercial"),
        ("Medicaid", "denial_rate_medicaid"),
    ]
    cells = []
    for label, metric_key in payers:
        pm = packet.rcm_profile.get(metric_key)
        if pm is None:
            val_html = '<span class="dim">—</span>'
            cell_style = f"background:{PALETTE['panel_alt']};"
        else:
            v = float(pm.value)
            # Color scale: green if <5, amber if <10, red otherwise.
            if v < 5.0:
                cell_style = f"background:rgba(16,185,129,0.18);color:{PALETTE['positive']};"
            elif v < 10.0:
                cell_style = f"background:rgba(245,158,11,0.18);color:{PALETTE['warning']};"
            else:
                cell_style = f"background:rgba(239,68,68,0.18);color:{PALETTE['negative']};"
            val_html = f'<span class="num">{_fmt_pct(v)}</span>'
        cells.append(
            f'<div class="heatmap-cell" style="{cell_style}">'
            f'<div style="font-size:10px;color:{PALETTE["text_dim"]};">{_esc(label)}</div>'
            f'{val_html}</div>'
        )
    return (
        '<div class="heatmap" style="grid-template-columns:repeat(4,1fr);">'
        + "".join(cells)
        + "</div>"
    )


# EBITDA Bridge tab -----------------------------------------------------

def _render_bridge(packet: DealAnalysisPacket) -> str:
    br = packet.ebitda_bridge
    if br.status != SectionStatus.OK or not br.per_metric_impacts:
        return f"""
        <div class="wb-tab-panel" data-panel="bridge">
          <div class="wb-card">
            <div class="wb-card-title">EBITDA bridge</div>
            <div class="dim">Bridge not available: {_esc(br.reason or "no impacts computed")}</div>
          </div>
        </div>
        """

    # Sliders (left)
    slider_rows = []
    assumptions_payload: List[Dict[str, Any]] = []
    for imp in br.per_metric_impacts:
        # Range and step inferred from metric type.
        lo, hi, step = _slider_range(imp.metric_key, imp.current_value, imp.target_value)
        slider_id = f"slider-{imp.metric_key}"
        assumptions_payload.append({
            "metric": imp.metric_key,
            "current": imp.current_value,
            "target": imp.target_value,
            "lo": lo, "hi": hi, "step": step,
        })
        slider_rows.append(
            f'<div class="slider-row" data-metric="{_esc(imp.metric_key)}">'
            f'<div class="slider-label">{_esc(imp.metric_key)}</div>'
            f'<input type="range" class="wb-slider" id="{slider_id}" '
            f'min="{lo}" max="{hi}" step="{step}" value="{imp.target_value}" '
            f'data-current="{imp.current_value}" data-metric="{_esc(imp.metric_key)}">'
            f'<div class="slider-target" id="{slider_id}-val">{imp.target_value:.2f}</div>'
            f'<div class="slider-delta dim" id="{slider_id}-delta">—</div>'
            f'</div>'
        )

    # Waterfall (right)
    waterfall = _render_waterfall(br)

    # Sensitivity tornado
    tornado = _render_tornado(br)

    summary_line = (
        f'Improving from current to target adds '
        f'<span class="pos num">{_fmt_money(br.total_ebitda_impact)}</span> to EBITDA '
        f'(<span class="num">{br.margin_improvement_bps:+d}</span> bps margin). '
    )
    ev = br.ev_impact_at_multiple or {}
    if ev:
        ev_bits = " · ".join(f"{k} → <span class='num'>{_fmt_money(v)}</span>"
                              for k, v in ev.items())
        summary_line += f"Enterprise value uplift: {ev_bits}."

    # JSON bootstrap for slider JS. We POST this exact shape to
    # /api/analysis/<deal_id>/bridge when sliders move.
    bootstrap = json.dumps({
        "deal_id": packet.deal_id,
        "assumptions": assumptions_payload,
    })

    return f"""
    <div class="wb-tab-panel" data-panel="bridge">
      <div class="wb-grid-5050">
        <div class="wb-card">
          <div class="wb-card-title">Target sliders</div>
          <div style="margin-bottom:8px;">
            <button class="wb-btn" data-preset="conservative">Conservative</button>
            <button class="wb-btn" data-preset="moderate">Moderate</button>
            <button class="wb-btn" data-preset="aggressive">Aggressive</button>
            <button class="wb-btn" data-preset="reset">Reset</button>
          </div>
          {''.join(slider_rows)}
        </div>
        <div class="wb-card">
          <div class="wb-card-title">Waterfall</div>
          <div id="wb-waterfall">{waterfall}</div>
        </div>
      </div>
      <div class="wb-card">
        <div class="wb-card-title">Sensitivity tornado</div>
        {tornado}
      </div>
      <div class="wb-card">
        <div id="wb-bridge-summary">{summary_line}</div>
      </div>
      <script id="wb-bridge-bootstrap" type="application/json">{_esc(bootstrap)}</script>
    </div>
    """


def _slider_range(metric: str, current: float, target: float) -> tuple:
    """Choose a sensible slider min/max/step per metric unit."""
    try:
        from ..analysis.completeness import RCM_METRIC_REGISTRY
        meta = RCM_METRIC_REGISTRY.get(metric) or {}
        unit = meta.get("unit") or ""
        lo_r, hi_r = meta.get("valid_range") or (0, 100)
    except Exception:  # noqa: BLE001
        unit, lo_r, hi_r = "", 0, 100
    if unit == "pct":
        return (0, 100, 0.1)
    if unit == "days":
        return (max(0, lo_r), min(365, hi_r), 1)
    if unit == "index":
        return (max(0, lo_r), min(5, hi_r), 0.01)
    if unit == "dollars":
        return (0, max(current, target) * 3 or 1e6, 1_000_000)
    return (lo_r, hi_r, 0.1)


def _render_waterfall(br) -> str:
    # Find max abs width for scaling.
    rows = []
    steps = []
    running = float(br.current_ebitda)
    steps.append(("Current EBITDA", running, "anchor"))
    for imp in br.per_metric_impacts:
        running += imp.ebitda_impact
        kind = "pos" if imp.ebitda_impact >= 0 else "neg"
        steps.append((imp.metric_key, imp.ebitda_impact, kind))
    steps.append(("Target EBITDA", br.target_ebitda, "anchor"))

    max_abs = max((abs(v) for _, v, _ in steps if v), default=1.0)
    for label, val, kind in steps:
        bar_pct = max(1.0, (abs(val) / max_abs) * 100) if max_abs else 0
        rows.append(
            f'<div class="wf-row">'
            f'<div>{_esc(label)}</div>'
            f'<div class="wf-track">'
            f'<div class="wf-bar {kind}" style="width:{bar_pct:.1f}%"></div>'
            f'</div>'
            f'<div class="num" style="text-align:right;">{_fmt_money(val)}</div>'
            f'</div>'
        )
    return f'<div class="waterfall">{"".join(rows)}</div>'


def _render_tornado(br) -> str:
    impacts = [(imp.metric_key, imp.ebitda_impact) for imp in br.per_metric_impacts]
    impacts.sort(key=lambda r: abs(r[1]), reverse=True)
    if not impacts:
        return '<div class="dim">no impacts</div>'
    max_abs = max(abs(v) for _, v in impacts) or 1.0
    rows = []
    for metric, val in impacts:
        width = (abs(val) / max_abs) * 100
        cls = "pos" if val >= 0 else "neg"
        rows.append(
            f'<div class="tornado-row">'
            f'<div>{_esc(metric)}</div>'
            f'<div class="tornado-bar {cls}" style="width:{width:.1f}%;background:'
            f'{PALETTE["positive"] if val >= 0 else PALETTE["negative"]};"></div>'
            f'<div class="num {cls}" style="text-align:right;">{_fmt_money(val)}</div>'
            f'</div>'
        )
    return "".join(rows)


# Monte Carlo tab -------------------------------------------------------

def _render_mc(packet: DealAnalysisPacket) -> str:
    mc = packet.simulation
    if mc is None or mc.status != SectionStatus.OK:
        reason = mc.reason if mc else "simulation not run"
        return f"""
        <div class="wb-tab-panel" data-panel="mc">
          <div class="wb-card">
            <div class="wb-card-title">Monte Carlo</div>
            <div class="dim">Simulation unavailable: {_esc(reason)}</div>
          </div>
        </div>
        """

    uplift = mc.ebitda_uplift
    histo_svg = _render_histogram_svg(uplift)
    stats = (
        f'<table class="wb-table" style="max-width:420px;">'
        f'<tbody>'
        + "".join(
            f'<tr><td class="dim">{label}</td><td class="num">{_fmt_money(val)}</td></tr>'
            for label, val in [
                ("P10", uplift.p10), ("P25", uplift.p25), ("P50", uplift.p50),
                ("P75", uplift.p75), ("P90", uplift.p90),
            ]
        )
        + "</tbody></table>"
    )

    moic_bits: List[str] = []
    # MOIC table: the packet's MC section in SimulationSummary only
    # holds a PercentileSet, not the raw probability_of_target_moic
    # dict. We reconstruct the dict from the percentile set if the
    # mc.moic is populated.
    moic_summary = (
        f'<div class="kpi-label">MOIC bands</div>'
        f'<div class="num">P10 {_fmt_moic(mc.moic.p10)} · '
        f'P50 {_fmt_moic(mc.moic.p50)} · '
        f'P90 {_fmt_moic(mc.moic.p90)}</div>'
    )

    # Variance contribution tornado.
    vc = mc.variance_contribution_by_metric or {}
    var_rows = []
    if vc:
        total = sum(vc.values()) or 1.0
        ordered = sorted(vc.items(), key=lambda kv: abs(kv[1]), reverse=True)
        for metric, share in ordered:
            pct = (share / total) * 100.0
            var_rows.append(
                f'<div class="tornado-row">'
                f'<div>{_esc(metric)}</div>'
                f'<div class="tornado-bar" style="width:{pct:.1f}%;'
                f'background:{PALETTE["neutral"]};"></div>'
                f'<div class="num">{pct:.1f}%</div>'
                f'</div>'
            )
    var_html = "".join(var_rows) or '<div class="dim">no variance decomposition</div>'

    n_sims = mc.n_sims or 0
    conv = mc.convergence_check or {}
    conv_status = "converged" if conv.get("converged") else "not converged"
    return f"""
    <div class="wb-tab-panel" data-panel="mc">
      <div class="wb-card">
        <div class="wb-card-title">EBITDA impact distribution ({n_sims:,} sims · {conv_status})</div>
        <div class="histo">{histo_svg}</div>
      </div>
      <div class="wb-grid-5050">
        <div class="wb-card">
          <div class="wb-card-title">Summary stats</div>
          {stats}
        </div>
        <div class="wb-card">
          <div class="wb-card-title">Returns</div>
          {moic_summary}
        </div>
      </div>
      <div class="wb-card">
        <div class="wb-card-title">Variance contribution</div>
        {var_html}
      </div>
    </div>
    """


def _render_histogram_svg(ps: PercentileSet) -> str:
    """Minimal inline SVG approximating the distribution from the 5-point
    PercentileSet. We don't have the raw draws in the packet; draw a
    piecewise-linear density instead using those five anchors."""
    # Guard against degenerate zero-width distributions.
    p10 = float(ps.p10 or 0.0)
    p50 = float(ps.p50 or 0.0)
    p90 = float(ps.p90 or 0.0)
    if p10 == 0 and p50 == 0 and p90 == 0:
        return '<div class="dim" style="padding:12px;">no distribution data</div>'
    span = max(p90 - p10, 1.0)
    width, height = 720, 160
    xs = [p10, ps.p25 or (p10 + 0.25 * span), p50, ps.p75 or (p50 + 0.25 * span), p90]
    x_pct = [(x - p10) / span for x in xs]
    # Vertical lines for P10/P50/P90.
    lines = ""
    for label, x in (("P10", 0.0), ("P50", (p50 - p10) / span), ("P90", 1.0)):
        x_px = x * (width - 80) + 40
        lines += (
            f'<line x1="{x_px}" x2="{x_px}" y1="20" y2="{height-24}" '
            f'stroke="{PALETTE["text_faint"]}" stroke-dasharray="3,3"/>'
            f'<text x="{x_px}" y="{height-6}" fill="{PALETTE["text_dim"]}" '
            f'text-anchor="middle" font-size="10">{label}</text>'
        )
    # Density curve — use 5 anchors and linear interpolation for bars.
    bars = ""
    n_bars = 24
    for i in range(n_bars):
        pos = (i + 0.5) / n_bars
        # Triangular "density": peak near P50, tails to P10 / P90.
        anchor_idx = min(len(x_pct) - 1,
                         max(0, next((k for k, v in enumerate(x_pct)
                                       if v > pos), len(x_pct) - 1) - 1))
        density = 1.0 - abs(pos - x_pct[2]) * 1.6  # peak at P50
        density = max(0.1, min(1.0, density))
        bar_h = density * (height - 40)
        x_px = pos * (width - 80) + 40 - (width - 80) / n_bars / 2
        bar_w = (width - 80) / n_bars - 1
        y = height - 20 - bar_h
        bars += (
            f'<rect x="{x_px:.1f}" y="{y:.1f}" width="{bar_w:.1f}" '
            f'height="{bar_h:.1f}" fill="{PALETTE["accent"]}" opacity="0.55"/>'
        )
    return (
        f'<svg viewBox="0 0 {width} {height}" preserveAspectRatio="none" '
        f'style="width:100%;height:160px;">'
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="{PALETTE["panel_alt"]}"/>'
        f'{bars}{lines}'
        f'</svg>'
    )


# Scenarios tab ---------------------------------------------------------

_SCENARIO_PALETTE_COLORS = (
    PALETTE["accent"], PALETTE["positive"],
    PALETTE["warning"], PALETTE["negative"],
)


def _scenario_top_drivers(
    scenario: Dict[str, Any], limit: int = 3,
) -> List[str]:
    """Pick the top-N variance-contribution metrics from one
    ``MonteCarloResult.to_dict()``. Skips entries that tie to zero —
    partners don't want to see "metric_foo: 0%" noise."""
    vc = scenario.get("variance_contribution") or {}
    if not vc:
        return []
    ordered = sorted(
        ((k, float(v)) for k, v in vc.items()),
        key=lambda kv: abs(kv[1]), reverse=True,
    )
    return [k for k, v in ordered[:limit] if abs(v) > 1e-6]


def _render_scenario_mini_histogram(
    scenario: Dict[str, Any], palette_idx: int,
) -> str:
    """Tiny (200×60) SVG histogram rendered per scenario card.

    Uses the ``histogram_data`` bin list from ``MonteCarloResult`` if
    present, else falls back to a triangular approximation from the
    EBITDA percentile set. Same visual language as the main MC tab
    but scaled down to fit inside a card.
    """
    bins = scenario.get("histogram_data") or []
    if bins:
        color = _SCENARIO_PALETTE_COLORS[
            palette_idx % len(_SCENARIO_PALETTE_COLORS)
        ]
        counts = [float(b.get("count") or 0) for b in bins]
        max_count = max(counts) if counts else 1.0
        if max_count <= 0:
            max_count = 1.0
        width, height = 200, 60
        bar_w = width / max(1, len(counts))
        rects: List[str] = []
        for i, c in enumerate(counts):
            h = (c / max_count) * (height - 6)
            rects.append(
                f'<rect x="{i * bar_w:.1f}" y="{height - h:.1f}" '
                f'width="{bar_w - 0.5:.1f}" height="{h:.1f}" '
                f'fill="{color}" opacity="0.75"/>'
            )
        return (
            f'<svg viewBox="0 0 {width} {height}" preserveAspectRatio="none">'
            + "".join(rects) + '</svg>'
        )
    # Fallback: use ebitda_impact percentile triangle.
    eb = scenario.get("ebitda_impact") or {}
    return _render_scenario_fallback_mini(eb, palette_idx)


def _render_scenario_fallback_mini(
    ps: Dict[str, Any], palette_idx: int,
) -> str:
    """Triangular density from a 5-percentile dict — for scenarios
    saved before the histogram_data field was populated."""
    p10 = float(ps.get("p10") or 0.0)
    p50 = float(ps.get("p50") or 0.0)
    p90 = float(ps.get("p90") or 0.0)
    if p10 == p50 == p90 == 0.0:
        return ""
    span = max(p90 - p10, 1.0)
    color = _SCENARIO_PALETTE_COLORS[palette_idx % len(_SCENARIO_PALETTE_COLORS)]
    width, height = 200, 60
    n_bars = 18
    peak = (p50 - p10) / span
    bars: List[str] = []
    for i in range(n_bars):
        pos = (i + 0.5) / n_bars
        density = 1.0 - abs(pos - peak) * 1.8
        density = max(0.08, min(1.0, density))
        h = density * (height - 6)
        x = pos * width - width / n_bars / 2
        bars.append(
            f'<rect x="{x:.1f}" y="{height - h:.1f}" '
            f'width="{width / n_bars - 1:.1f}" height="{h:.1f}" '
            f'fill="{color}" opacity="0.75"/>'
        )
    return (
        f'<svg viewBox="0 0 {width} {height}" preserveAspectRatio="none">'
        + "".join(bars) + '</svg>'
    )


def _render_scenario_card(
    name: str, scenario: Dict[str, Any],
    *, recommended: bool, palette_idx: int,
) -> str:
    eb = scenario.get("ebitda_impact") or {}
    moic = scenario.get("moic") or {}
    drivers = _scenario_top_drivers(scenario)
    drivers_html = (
        '<ol>'
        + "".join(f'<li>{_esc(d)}</li>' for d in drivers)
        + '</ol>'
        if drivers else
        '<div class="dim">no variance drivers</div>'
    )
    badge = (
        '<span class="scenario-rec-badge">recommended</span>'
        if recommended else ''
    )
    class_list = (
        f"scenario-card scenario-palette-{palette_idx}"
        + (" recommended" if recommended else "")
    )
    mini = _render_scenario_mini_histogram(scenario, palette_idx)
    return f"""
    <div class="{class_list}">
      <div class="scenario-name">
        <span class="scenario-swatch"></span>
        {_esc(name)}{badge}
      </div>
      <div class="scenario-kpi"><span class="dim">P10 EBITDA</span>
        <span class="num">{_fmt_money(eb.get("p10"))}</span></div>
      <div class="scenario-kpi"><span class="dim">P50 EBITDA</span>
        <span class="num">{_fmt_money(eb.get("p50"))}</span></div>
      <div class="scenario-kpi"><span class="dim">P90 EBITDA</span>
        <span class="num">{_fmt_money(eb.get("p90"))}</span></div>
      <div class="scenario-kpi"><span class="dim">P50 MOIC</span>
        <span class="num">{_fmt_moic(moic.get("p50"))}</span></div>
      <div class="scenario-mini">{mini}</div>
      <div class="scenario-drivers">top variance drivers:{drivers_html}</div>
    </div>
    """


def _render_pairwise_matrix(
    names: List[str],
    pairwise: Dict[str, float],
) -> str:
    """Grid of P(row > col). Cell for ``row == col`` renders as an
    em-dash to avoid implying a winner over itself. Cells above 60%
    are green-tinted; below 40% red-tinted."""
    if not names or not pairwise:
        return '<div class="dim">no pairwise comparison yet</div>'

    header_cells = "".join(f'<th>{_esc(n)}</th>' for n in names)
    rows: List[str] = []
    for a in names:
        cells: List[str] = [f'<th>{_esc(a)}</th>']
        for b in names:
            if a == b:
                cells.append('<td class="pw-self">—</td>')
                continue
            key = f"{a}__vs__{b}"
            prob = pairwise.get(key)
            if prob is None:
                cells.append('<td class="dim">—</td>')
                continue
            cls = "pw-high" if prob >= 0.60 else (
                "pw-low" if prob <= 0.40 else ""
            )
            cells.append(
                f'<td class="{cls}">{prob * 100:.0f}%</td>'
            )
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return (
        '<table class="pairwise-matrix">'
        f'<thead><tr><th>P(row &gt; col)</th>{header_cells}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table>'
    )


def _render_scenario_overlay_svg(
    comparison: Dict[str, Any],
) -> str:
    """Superimposed histograms, one color per scenario, 40% opacity.

    All scenarios share the x-axis derived from the overall min/max
    EBITDA across every scenario's histogram_data. One ``<path>``
    per scenario so tests can count scenario entries by counting
    ``d="M"`` path starts.
    """
    scenarios = comparison.get("per_scenario") or {}
    if not scenarios:
        return ""
    # Collect every bin across every scenario to determine the
    # shared x-axis. If a scenario has no histogram_data, skip it —
    # the card still shows the triangular mini as a fallback.
    all_bins: List[Tuple[str, List[Dict[str, Any]]]] = []
    for name, sc in scenarios.items():
        bins = sc.get("histogram_data") or []
        if bins:
            all_bins.append((name, bins))
    if not all_bins:
        return ""
    x_min = min(
        float(b.get("bin_edge_low") or 0.0)
        for _, bins in all_bins for b in bins
    )
    x_max = max(
        float(b.get("bin_edge_high") or 0.0)
        for _, bins in all_bins for b in bins
    )
    x_span = max(x_max - x_min, 1.0)
    max_count = max(
        float(b.get("count") or 0.0)
        for _, bins in all_bins for b in bins
    )
    if max_count <= 0:
        max_count = 1.0

    width, height = 720, 200
    paths: List[str] = []
    legend_bits: List[str] = []
    for idx, (name, bins) in enumerate(all_bins):
        color = _SCENARIO_PALETTE_COLORS[idx % len(_SCENARIO_PALETTE_COLORS)]
        # Build a filled polygon: (x_lo, baseline) → zig-zag of bin
        # heights → (x_hi, baseline).
        points: List[str] = []
        baseline_y = height - 20
        for b in bins:
            lo = float(b.get("bin_edge_low") or 0.0)
            hi = float(b.get("bin_edge_high") or 0.0)
            cnt = float(b.get("count") or 0.0)
            h = (cnt / max_count) * (height - 40)
            x_lo_px = (lo - x_min) / x_span * (width - 40) + 20
            x_hi_px = (hi - x_min) / x_span * (width - 40) + 20
            y_px = baseline_y - h
            points.append(f"{x_lo_px:.1f},{y_px:.1f}")
            points.append(f"{x_hi_px:.1f},{y_px:.1f}")
        if not points:
            continue
        d_parts = [
            f"M {points[0].split(',')[0]},{baseline_y:.1f}",
            "L " + " L ".join(points),
            f"L {points[-1].split(',')[0]},{baseline_y:.1f}",
            "Z",
        ]
        d = " ".join(d_parts)
        paths.append(
            f'<path d="{d}" fill="{color}" fill-opacity="0.40" '
            f'stroke="{color}" stroke-opacity="0.85" stroke-width="1.2"/>'
        )
        legend_bits.append(
            f'<span style="display:inline-flex;align-items:center;gap:4px;'
            f'margin-right:12px;"><span style="display:inline-block;'
            f'width:10px;height:10px;background:{color};opacity:0.7;">'
            f'</span>{_esc(name)}</span>'
        )
    legend = (
        f'<div style="margin-top:6px;font-size:11px;">{"".join(legend_bits)}</div>'
    )
    axis = (
        f'<line x1="20" x2="{width - 20}" y1="{height - 20}" '
        f'y2="{height - 20}" stroke="{PALETTE["text_faint"]}"/>'
        f'<text x="20" y="{height - 4}" fill="{PALETTE["text_dim"]}" '
        f'font-size="10">{_fmt_money(x_min)}</text>'
        f'<text x="{width - 20}" y="{height - 4}" fill="{PALETTE["text_dim"]}" '
        f'text-anchor="end" font-size="10">{_fmt_money(x_max)}</text>'
    )
    return (
        f'<svg class="scenario-overlay-svg" viewBox="0 0 {width} {height}" '
        f'preserveAspectRatio="none">{"".join(paths)}{axis}</svg>'
        f'{legend}'
    )


def _render_scenarios(packet: DealAnalysisPacket) -> str:
    """Render the Scenarios tab.

    When no comparison has been run we show an empty state with an
    "Add Scenario" button. The JS in ``_WORKBENCH_JS`` picks up
    ``data-scenario-trigger`` clicks, opens the form panel, and
    submits to ``/api/analysis/<id>/simulate/compare``.

    Partner flow: open Scenarios → click Add → fill a per-lever
    target override → hit Run → page re-fetches the comparison and
    re-renders the tab.
    """
    comparison = packet.scenario_comparison or {}
    per_scenario = comparison.get("per_scenario") or {}
    names = list(per_scenario.keys())
    recommended = comparison.get("recommended_scenario") or ""
    rationale = comparison.get("rationale") or ""
    pairwise = comparison.get("pairwise_overlap") or {}

    # Card grid ------------------------------------------------------
    if names:
        cards_html = "".join(
            _render_scenario_card(
                name, per_scenario[name],
                recommended=(name == recommended),
                palette_idx=i,
            )
            for i, name in enumerate(names)
        )
    else:
        cards_html = (
            '<div class="scenario-empty">'
            'No scenarios compared yet. Click <b>+ Add Scenario</b> '
            'to run a side-by-side vs. the current MC output.'
            '</div>'
        )

    # Pairwise + rationale ------------------------------------------
    pairwise_html = _render_pairwise_matrix(names, pairwise)
    rationale_html = (
        f'<div class="dim" style="margin-top:8px;font-size:12px;">'
        f'{_esc(rationale)}</div>' if rationale else ''
    )

    # Overlay histogram ---------------------------------------------
    overlay_html = _render_scenario_overlay_svg(comparison) or (
        '<div class="dim">distributions unavailable — run MC first</div>'
    )

    # Add-scenario form — skeleton (JS wires submit). Pre-populated
    # from the current bridge's per-metric targets so analysts have a
    # starting point instead of an empty text field.
    target_defaults = {
        imp.metric_key: float(imp.target_value)
        for imp in (packet.ebitda_bridge.per_metric_impacts or [])
    }
    form_inputs: List[str] = [
        '<label class="full-row">Scenario name'
        '<input type="text" id="scenario-name-input" placeholder="e.g. management plan"/>'
        '</label>'
    ]
    for metric, tgt in target_defaults.items():
        form_inputs.append(
            f'<label>{_esc(metric)} target'
            f'<input type="number" step="0.01" '
            f'data-scenario-target="{_esc(metric)}" value="{tgt:.2f}"/>'
            f'</label>'
        )
    form_inputs.append(
        '<div class="full-row">'
        '<button class="wb-btn wb-btn-primary" type="button" '
        'data-scenario-submit>Run scenario</button>'
        '<button class="wb-btn" type="button" data-scenario-cancel>'
        'Cancel</button>'
        '</div>'
    )
    form_html = (
        '<div class="scenario-add-form hidden" id="scenario-add-form">'
        + "".join(form_inputs) +
        '</div>'
    )

    return f"""
    <div class="wb-tab-panel" data-panel="scenarios"
         data-deal-id="{_esc(packet.deal_id)}">
      <div class="wb-card">
        <div class="wb-card-title">
          Scenario comparison
          <button class="wb-btn" type="button"
                  data-scenario-trigger style="float:right;">
            + Add Scenario
          </button>
        </div>
        <div class="scenario-grid">{cards_html}</div>
        {form_html}
      </div>
      <div class="wb-card">
        <div class="wb-card-title">Pairwise win probability</div>
        {pairwise_html}
        {rationale_html}
      </div>
      <div class="wb-card">
        <div class="wb-card-title">Overlay distribution</div>
        {overlay_html}
      </div>
    </div>
    """


# Risk & Diligence tab --------------------------------------------------

def _render_regulatory_card(packet: DealAnalysisPacket) -> str:
    """Regulatory Environment card (Prompt 24) — CON / Medicaid /
    market badges + the one-paragraph narrative.

    Rendered at the top of the Risk & Diligence tab when
    ``packet.regulatory_context`` is populated. Skipped silently
    when the deal has no state.
    """
    ctx = packet.regulatory_context or {}
    if not ctx:
        return ""

    def _badge(label: str, tone: str) -> str:
        return (
            f'<span class="wb-badge wb-badge-{tone}">{_esc(label)}</span>'
        )

    con_status = ctx.get("con_status") or "NO_CON"
    con_impl = ctx.get("con_implication") or "none"
    medicaid_risk = ctx.get("medicaid_risk") or "LOW"
    market_risk = ctx.get("market_risk") or "LOW"
    payer = ctx.get("payer_profile") or {}
    expanded = bool(payer.get("medicaid_expanded"))

    if con_status == "CON_MORATORIUM":
        con_badge = _badge("CON moratorium", "medium")
    elif con_status == "CON_ACTIVE":
        tone = "low" if con_impl == "competitive_moat" else "medium"
        con_badge = _badge("CON active", tone)
    else:
        con_badge = _badge("no CON", "low")

    medicaid_badge = _badge(
        "Medicaid expanded" if expanded else "no Medicaid expansion",
        "low" if expanded else "medium",
    )
    medicaid_risk_badge = _badge(
        f"rate risk: {medicaid_risk.lower()}",
        {"HIGH": "high", "MEDIUM": "medium", "LOW": "low"}.get(
            medicaid_risk, "low",
        ),
    )
    market_badge = _badge(
        f"market: {market_risk.lower()}",
        {"HIGH": "medium", "MEDIUM": "low", "LOW": "low"}.get(
            market_risk, "low",
        ),
    )

    narrative = _esc(ctx.get("narrative") or "")
    state = _esc(ctx.get("state") or "")
    return f"""
    <div class="wb-card" style="margin-bottom:14px;">
      <div class="wb-card-title">Regulatory Environment — {state}</div>
      <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px;">
        {con_badge}{medicaid_badge}{medicaid_risk_badge}{market_badge}
      </div>
      <div class="dim" style="font-size:12px;line-height:1.5;">
        {narrative or '<span class="dim">(no narrative available)</span>'}
      </div>
    </div>
    """


def _render_risk_diligence(packet: DealAnalysisPacket) -> str:
    # Regulatory environment card (Prompt 24) — optional, rendered
    # above the flag/questions grid when the packet has a state.
    regulatory_card = _render_regulatory_card(packet)

    # Risk flags (left).
    risk_html = []
    for rf in packet.risk_flags:
        sev = rf.severity.value if hasattr(rf.severity, "value") else str(rf.severity)
        ear = _fmt_money(rf.ebitda_at_risk) if rf.ebitda_at_risk else ""
        ear_line = (f'<div class="dim" style="font-size:11px;">EBITDA at risk: '
                    f'<span class="num">{ear}</span></div>') if ear else ""
        triggers = ", ".join(rf.trigger_metrics or []) or (rf.trigger_metric or "")
        risk_html.append(
            f'<div class="risk-card severity-{sev}">'
            f'<span class="wb-badge wb-badge-{sev.lower()}">{sev}</span> '
            f'<span class="risk-title">{_esc(rf.title or "flag")}</span>'
            f'<div class="risk-detail">{_esc(rf.detail or rf.explanation)}</div>'
            f'{ear_line}'
            + (f'<div class="dim" style="font-size:11px;">Trigger: {_esc(triggers)}</div>'
               if triggers else "")
            + '</div>'
        )
    risk_block = "\n".join(risk_html) or '<div class="dim">no risk flags</div>'

    # Diligence questions (right).
    dq_by_priority: Dict[str, List[str]] = {"P0": [], "P1": [], "P2": []}
    for q in packet.diligence_questions:
        pri = q.priority.value if hasattr(q.priority, "value") else str(q.priority)
        dq_by_priority.setdefault(pri, []).append(
            f'<div class="dq-card">'
            f'<span class="dq-priority dq-{pri}">{pri}</span>'
            f'<span class="wb-badge wb-badge-low" style="margin-right:6px;">{_esc(q.category or "—")}</span>'
            f'<div style="margin-top:4px;">{_esc(q.question)}</div>'
            + (f'<div class="dim" style="font-size:11px;margin-top:3px;">Trigger: {_esc(q.trigger or q.trigger_reason)}</div>'
               if (q.trigger or q.trigger_reason) else "")
            + '</div>'
        )
    dq_html = ""
    for pri in ("P0", "P1", "P2"):
        if dq_by_priority[pri]:
            dq_html += (
                f'<div class="wb-card-title" style="margin-top:8px;">{pri} — {len(dq_by_priority[pri])} questions</div>'
                + "\n".join(dq_by_priority[pri])
            )
    dq_block = dq_html or '<div class="dim">no diligence questions</div>'

    return f"""
    <div class="wb-tab-panel" data-panel="risk">
      {regulatory_card}
      <div class="wb-grid">
        <div>
          <div class="wb-card">
            <div class="wb-card-title">Risk flags ({len(packet.risk_flags)})</div>
            {risk_block}
          </div>
        </div>
        <div>
          <div class="wb-card">
            <div class="wb-card-title">Diligence questions ({len(packet.diligence_questions)})</div>
            {dq_block}
            <div style="margin-top:10px;">
              <a class="wb-btn" href="/api/analysis/{_esc(packet.deal_id)}/diligence-questions">Export JSON</a>
            </div>
          </div>
        </div>
      </div>
    </div>
    """


# Provenance tab --------------------------------------------------------

def _render_provenance(packet: DealAnalysisPacket) -> str:
    # Group nodes by prefix so the tree view matches the rich-graph
    # builder's ID scheme.
    groups: Dict[str, List[Any]] = {}
    for nid, node in (packet.provenance.nodes or {}).items():
        prefix = nid.split(":", 1)[0] if ":" in nid else "other"
        groups.setdefault(prefix, []).append((nid, node))

    blocks: List[str] = []
    for prefix in ("observed", "predicted", "bridge", "comparables", "mc", "target", "profile", "other"):
        nodes = groups.get(prefix) or []
        if not nodes:
            continue
        rows = []
        for nid, node in sorted(nodes, key=lambda t: t[0]):
            rows.append(
                f'<div class="prov-row" id="prov-{_esc(nid)}">'
                f'<div><span class="dim">{_esc(nid)}</span></div>'
                f'<div class="num">{_fmt_num(node.value, dp=2)}</div>'
                f'<div class="dim">{_esc(node.source)} · conf '
                f'<span class="num">{node.confidence:.2f}</span>'
                + (f' · {_esc(node.source_detail)}' if node.source_detail else "")
                + '</div></div>'
            )
        blocks.append(
            f'<details open><summary class="wb-card-title">{prefix.upper()} ({len(nodes)})</summary>'
            f'{"".join(rows)}</details>'
        )
    body = "\n".join(blocks) or '<div class="dim">no provenance captured</div>'
    return f"""
    <div class="wb-tab-panel" data-panel="provenance">
      <div class="wb-card">
        <div class="wb-card-title">Provenance graph ({len(packet.provenance.nodes)} nodes)</div>
        {body}
      </div>
    </div>
    """


# ── JavaScript ───────────────────────────────────────────────────────

_WORKBENCH_JS = r"""
(function(){
  // Tab switching
  const tabs = document.querySelectorAll('.analysis-workbench .wb-tab');
  const panels = document.querySelectorAll('.analysis-workbench .wb-tab-panel');
  tabs.forEach(t => t.addEventListener('click', () => {
    const k = t.dataset.tab;
    tabs.forEach(x => x.classList.toggle('active', x === t));
    panels.forEach(p => p.classList.toggle('active', p.dataset.panel === k));
  }));

  // Keyboard shortcuts: 1-7 switch tabs, Alt+← / Alt+→ prev/next
  const tabKeys = Array.from(tabs);
  document.addEventListener('keydown', e => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    const n = parseInt(e.key);
    if (n >= 1 && n <= tabKeys.length) {
      tabKeys[n-1].click();
      e.preventDefault();
      return;
    }
    if (e.altKey && (e.key === 'ArrowLeft' || e.key === 'ArrowRight')) {
      const cur = tabKeys.findIndex(t => t.classList.contains('active'));
      const next = e.key === 'ArrowRight'
        ? Math.min(cur + 1, tabKeys.length - 1)
        : Math.max(cur - 1, 0);
      tabKeys[next].click();
      e.preventDefault();
    }
    if (e.key === '?' && !e.ctrlKey && !e.metaKey) {
      alert('Keyboard shortcuts:\\n1-7: Switch tabs\\nAlt+←/→: Prev/next tab');
      e.preventDefault();
    }
  });

  // Bridge sliders
  const bootstrap = document.getElementById('wb-bridge-bootstrap');
  if (!bootstrap) return;
  let payload;
  try { payload = JSON.parse(bootstrap.textContent); }
  catch (_) { return; }
  const dealId = payload.deal_id;
  const assumptions = new Map();
  for (const a of payload.assumptions) assumptions.set(a.metric, a);

  function fmtMoney(v){
    if (v == null) return '—';
    const s = v < 0 ? '-' : '';
    v = Math.abs(v);
    if (v >= 1e9) return s + '$' + (v/1e9).toFixed(2) + 'B';
    if (v >= 1e6) return s + '$' + (v/1e6).toFixed(1) + 'M';
    if (v >= 1e3) return s + '$' + Math.round(v/1e3).toLocaleString() + 'K';
    return s + '$' + Math.round(v).toLocaleString();
  }

  function renderWaterfall(bridge){
    const root = document.getElementById('wb-waterfall');
    if (!root || !bridge || !bridge.per_metric_impacts) return;
    const steps = [];
    let running = bridge.current_ebitda || 0;
    steps.push({label:'Current EBITDA', value: running, kind:'anchor'});
    for (const imp of bridge.per_metric_impacts) {
      steps.push({label: imp.metric_key,
                  value: imp.ebitda_impact,
                  kind: imp.ebitda_impact >= 0 ? 'pos' : 'neg'});
      running += imp.ebitda_impact;
    }
    steps.push({label:'Target EBITDA', value: bridge.target_ebitda || running, kind:'anchor'});
    const maxAbs = Math.max(1, ...steps.map(s => Math.abs(s.value || 0)));
    root.innerHTML = '<div class="waterfall">' +
      steps.map(s => {
        const pct = Math.max(1, Math.abs(s.value || 0) / maxAbs * 100);
        return '<div class="wf-row">' +
          '<div>' + s.label + '</div>' +
          '<div class="wf-track"><div class="wf-bar ' + s.kind +
          '" style="width:' + pct.toFixed(1) + '%"></div></div>' +
          '<div class="num" style="text-align:right;">' + fmtMoney(s.value) + '</div>' +
          '</div>';
      }).join('') + '</div>';
    const summary = document.getElementById('wb-bridge-summary');
    if (summary) {
      summary.innerHTML =
        'Improving from current to target adds ' +
        '<span class="pos num">' + fmtMoney(bridge.total_ebitda_impact) +
        '</span> to EBITDA (<span class="num">' +
        (bridge.margin_improvement_bps >= 0 ? '+' : '') +
        bridge.margin_improvement_bps + '</span> bps margin).';
    }
  }

  let debounceTimer = null;
  function postBridge(){
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      const targets = {};
      assumptions.forEach((_, metric) => {
        const el = document.getElementById('slider-' + metric);
        if (el) targets[metric] = parseFloat(el.value);
      });
      fetch('/api/analysis/' + encodeURIComponent(dealId) + '/bridge', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({targets: targets, financials: {}})
      })
        .then(r => r.ok ? r.json() : null)
        .then(d => { if (d && d.bridge) renderWaterfall(d.bridge); })
        .catch(() => {});
    }, 300);
  }

  document.querySelectorAll('.analysis-workbench input.wb-slider').forEach(el => {
    el.addEventListener('input', () => {
      const metric = el.dataset.metric;
      const cur = parseFloat(el.dataset.current);
      const tgt = parseFloat(el.value);
      const valEl = document.getElementById('slider-' + metric + '-val');
      const delEl = document.getElementById('slider-' + metric + '-delta');
      if (valEl) valEl.textContent = tgt.toFixed(2);
      if (delEl) {
        const d = tgt - cur;
        const sign = d >= 0 ? '+' : '';
        delEl.textContent = sign + d.toFixed(2);
        delEl.className = 'slider-delta num ' + (d >= 0 ? 'pos' : 'neg');
      }
      postBridge();
    });
  });

  // Presets just trigger a recompute; caller UI would seed slider values
  // (preset math not wired — placeholder so the button clicks are visible).
  document.querySelectorAll('.analysis-workbench [data-preset]').forEach(btn => {
    btn.addEventListener('click', () => { postBridge(); });
  });

  // Scenarios tab — add-scenario form.
  const scenarioPanel = document.querySelector(
    '.analysis-workbench [data-panel="scenarios"]'
  );
  if (scenarioPanel) {
    const dealForScenarios = scenarioPanel.dataset.dealId;
    const form = document.getElementById('scenario-add-form');
    const trigger = scenarioPanel.querySelector('[data-scenario-trigger]');
    const cancel = scenarioPanel.querySelector('[data-scenario-cancel]');
    const submit = scenarioPanel.querySelector('[data-scenario-submit]');
    const nameInput = document.getElementById('scenario-name-input');
    if (trigger && form) {
      trigger.addEventListener('click', () => {
        form.classList.toggle('hidden');
        if (nameInput) nameInput.focus();
      });
    }
    if (cancel && form) {
      cancel.addEventListener('click', () => form.classList.add('hidden'));
    }
    if (submit && nameInput) {
      submit.addEventListener('click', () => {
        const name = (nameInput.value || '').trim();
        if (!name) { nameInput.focus(); return; }
        const overrides = {};
        form.querySelectorAll('[data-scenario-target]').forEach(inp => {
          const metric = inp.dataset.scenarioTarget;
          const val = parseFloat(inp.value);
          if (!isNaN(val)) {
            // Use the same MetricAssumption shape the API accepts.
            overrides[metric] = {
              target_value: val,
              execution_distribution: 'beta',
              execution_probability: 0.7,
              execution_params: {alpha: 7.0, beta: 3.0},
              uncertainty_source: 'none'
            };
          }
        });
        submit.disabled = true;
        submit.textContent = 'Running…';
        fetch('/api/analysis/' + encodeURIComponent(dealForScenarios)
              + '/simulate/compare', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            scenarios: { [name]: overrides },
            financials: {}
          })
        })
          .then(r => r.ok ? r.json() : Promise.reject(r.status))
          .then(() => { window.location.reload(); })
          .catch(() => {
            submit.disabled = false;
            submit.textContent = 'Run scenario';
          });
      });
    }
  }
})();
"""


# ── Full-page render ────────────────────────────────────────────────

def _build_explain_data(packet: DealAnalysisPacket) -> str:
    """Build a JSON blob with per-metric explain info for the slide-in
    panel (Prompt 32). The JS picks this up and populates the panel
    when the user clicks a ``[data-explain]`` element."""
    import json as _json
    try:
        from ..analysis.completeness import RCM_METRIC_REGISTRY
    except Exception:  # noqa: BLE001
        RCM_METRIC_REGISTRY = {}
    data: Dict[str, Any] = {}
    for key, pm in (packet.rcm_profile or {}).items():
        meta = RCM_METRIC_REGISTRY.get(key) or {}
        # Find matching bridge impact.
        impact = 0.0
        for imp in (packet.ebitda_bridge.per_metric_impacts or []):
            if imp.metric_key == key:
                impact = float(imp.ebitda_impact or 0)
                break
        # Find matching diligence question.
        question = ""
        for q in (packet.diligence_questions or []):
            if q.trigger_metric == key:
                question = q.question or ""
                break
        data[key] = {
            "display_name": meta.get("display_name") or key,
            "source": pm.source.value if hasattr(pm.source, "value") else str(pm.source),
            "value": float(pm.value),
            "benchmark_p50": meta.get("benchmark_p50"),
            "percentile": pm.benchmark_percentile,
            "ebitda_sensitivity_rank": meta.get("ebitda_sensitivity_rank"),
            "ebitda_impact": impact,
            "category": meta.get("category") or "",
            "diligence_question": question,
        }
    return _json.dumps(data, default=str)


_EXPLAIN_JS = r"""
(function(){
  var panel = document.getElementById('wb-explain-panel');
  var titleEl = document.getElementById('ep-title');
  var bodyEl = document.getElementById('ep-body');
  var closeBtn = document.getElementById('ep-close');
  var dataEl = document.getElementById('wb-explain-data');
  var data = {};
  try { data = JSON.parse(dataEl ? dataEl.textContent : '{}'); } catch(_){}

  function fmtMoney(v){
    if(v==null)return'—';v=Math.abs(v);
    if(v>=1e9)return'$'+(v/1e9).toFixed(2)+'B';
    if(v>=1e6)return'$'+(v/1e6).toFixed(1)+'M';
    if(v>=1e3)return'$'+Math.round(v/1e3).toLocaleString()+'K';
    return'$'+Math.round(v).toLocaleString();
  }

  function open(metric){
    var d = data[metric];
    if(!d){titleEl.textContent=metric;bodyEl.innerHTML='<div class="dim">No data for this metric.</div>';panel.classList.add('open');return;}
    titleEl.textContent = d.display_name || metric;
    var pct = d.percentile != null ? (d.percentile*100).toFixed(0)+'th' : '—';
    var barPct = d.percentile != null ? Math.round(d.percentile*100) : 50;
    var barColor = barPct > 70 ? '#10b981' : (barPct < 30 ? '#ef4444' : '#f59e0b');
    bodyEl.innerHTML =
      '<div class="ep-section"><div class="ep-label">Source</div><span style="background:#1e293b;padding:2px 8px;border-radius:3px;font-size:11px;">'+d.source+'</span></div>'+
      '<div class="ep-section"><div class="ep-label">Current value</div><div class="num" style="font-size:18px;">'+d.value.toFixed(2)+'</div></div>'+
      '<div class="ep-section"><div class="ep-label">Benchmark P50</div><div>'+(d.benchmark_p50!=null?d.benchmark_p50.toFixed(1):'—')+'</div>'+
      '<div class="ep-label" style="margin-top:6px;">Percentile rank: '+pct+'</div>'+
      '<div class="ep-bar"><div style="width:'+barPct+'%;background:'+barColor+';"></div></div></div>'+
      '<div class="ep-section"><div class="ep-label">EBITDA sensitivity</div><div>#'+(d.ebitda_sensitivity_rank||'—')+' · impact '+fmtMoney(d.ebitda_impact)+'</div></div>'+
      (d.diligence_question ? '<div class="ep-section"><div class="ep-label">Diligence question</div><div style="font-style:italic;">'+d.diligence_question+'</div></div>' : '');
    panel.classList.add('open');
  }

  if(closeBtn) closeBtn.addEventListener('click', function(){ panel.classList.remove('open'); });
  document.addEventListener('click', function(e){
    var el = e.target.closest('[data-explain]');
    if(!el) return;
    e.preventDefault();
    open(el.dataset.explain);
  });
  // Also open on metric name links in the profile table.
  document.querySelectorAll('.analysis-workbench a[href^="#prov-"]').forEach(function(a){
    a.dataset.explain = a.href.split('#prov-')[1] || '';
  });
})();
"""


def render_workbench(packet: DealAnalysisPacket) -> str:
    """Produce the full ``<!doctype html>`` document for
    ``/analysis/<deal_id>``. One call, one packet, one rendered page.

    Wrapped in chartis_shell for consistency with the rest of the
    platform. The custom _WORKBENCH_CSS is passed via extra_css so
    the tab layout + explain-panel styling persists; _WORKBENCH_JS
    and _EXPLAIN_JS go through extra_js.
    """
    from ._chartis_kit import chartis_shell
    header = _render_header(packet)
    nav = _render_tab_nav()
    body_inner = (
        _render_overview(packet)
        + _render_rcm_profile(packet)
        + _render_bridge(packet)
        + _render_mc(packet)
        + _render_scenarios(packet)
        + _render_risk_diligence(packet)
        + _render_provenance(packet)
    )
    # Prompt 32: build the explain-panel data blob + the empty panel div.
    explain_data = _build_explain_data(packet)
    explain_panel = (
        '<div class="wb-explain-panel" id="wb-explain-panel">'
        '<button class="ep-close" id="ep-close" aria-label="Close panel">&times;</button>'
        '<div class="ep-title" id="ep-title"></div>'
        '<div id="ep-body"></div>'
        '</div>'
        f'<script id="wb-explain-data" type="application/json">'
        f'{_esc(explain_data)}</script>'
    )
    shell_body = (
        f'<div class="analysis-workbench-scope">{header}{nav}{body_inner}'
        f'{explain_panel}</div>'
    )
    return chartis_shell(
        shell_body,
        f"{packet.deal_name or packet.deal_id} — Analysis Workbench",
        extra_css=_WORKBENCH_CSS,
        extra_js=_WORKBENCH_JS + _EXPLAIN_JS,
    )
