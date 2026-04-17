"""SeekingChartis unified shell v2 — Seeking Alpha-inspired layout.

Replaces the simple top-nav shell with a full application layout:
- Sticky top bar with logo, search, notifications
- Left nav rail (collapsible)
- Main content area
- Optional right contextual rail

Every page renders inside this shell for brand consistency.
"""
from __future__ import annotations

import html as _html
from datetime import datetime, timezone
from typing import Optional

from .brand import BRAND, LOGO_SVG, WORDMARK_SVG, PALETTE, TYPOGRAPHY, NAV_ITEMS, NAV_ICONS


_SHELL_CSS = f"""
:root {{
  --cad-bg: {PALETTE['bg']};
  --cad-bg2: {PALETTE['bg_secondary']};
  --cad-bg3: {PALETTE['bg_tertiary']};
  --cad-border: {PALETTE['border']};
  --cad-border-lt: {PALETTE['border_light']};
  --cad-text: {PALETTE['text_primary']};
  --cad-text2: {PALETTE['text_secondary']};
  --cad-text3: {PALETTE['text_muted']};
  --cad-link: {PALETTE['text_link']};
  --cad-brand: {PALETTE['brand_primary']};
  --cad-accent: {PALETTE['brand_accent']};
  --cad-amber: {PALETTE['accent_amber']};
  --cad-pos: {PALETTE['positive']};
  --cad-neg: {PALETTE['negative']};
  --cad-warn: {PALETTE['warning']};
  --cad-font: {TYPOGRAPHY['font_sans']};
  --cad-mono: {TYPOGRAPHY['font_mono']};
  --cad-serif: {TYPOGRAPHY['font_serif']};
  --cad-nav-w: 216px;
  --cad-nav-collapsed: 56px;
  --cad-topbar-h: 44px;
  --cad-ticker-h: 26px;
  --cad-statusbar-h: 22px;
}}

* {{ box-sizing: border-box; margin: 0; padding: 0; }}

body.caduceus {{
  background: var(--cad-bg);
  color: var(--cad-text);
  font-family: var(--cad-font);
  font-size: 12.5px;
  line-height: 1.5;
  letter-spacing: 0;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  overflow: hidden;
  height: 100vh;
  font-feature-settings: "ss01", "cv11", "tnum";
}}

a {{ color: var(--cad-link); }}

/* ── Top Bar ── */
.cad-topbar {{
  position: fixed; top: 0; left: 0; right: 0;
  height: var(--cad-topbar-h);
  background: linear-gradient(180deg, #0d1320 0%, var(--cad-bg2) 100%);
  border-bottom: 1px solid var(--cad-border);
  display: flex; align-items: center;
  padding: 0 14px;
  z-index: 100;
  gap: 14px;
}}
.cad-topbar-logo {{
  display: flex; align-items: center; gap: 8px;
  text-decoration: none;
  flex-shrink: 0;
  padding-right: 12px;
  border-right: 1px solid var(--cad-border);
  height: 100%;
}}
.cad-topbar-logo span.cad-wordmark {{
  font-family: var(--cad-font);
  font-size: 13.5px;
  font-weight: 700;
  color: var(--cad-text);
  letter-spacing: 0.12em;
  text-transform: uppercase;
}}
.cad-topbar-version {{
  font-family: var(--cad-mono);
  font-size: 9px;
  padding: 1px 5px;
  background: transparent;
  color: var(--cad-amber);
  border: 1px solid var(--cad-border-lt);
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}}
.cad-fnkeys {{
  display: flex; align-items: center; gap: 2px;
  font-family: var(--cad-mono);
  font-size: 10.5px;
  color: var(--cad-text2);
  flex-shrink: 0;
}}
.cad-fnkey {{
  display: inline-flex; align-items: center; gap: 4px;
  padding: 3px 8px;
  color: var(--cad-text2);
  text-decoration: none;
  letter-spacing: 0.04em;
  border-right: 1px solid var(--cad-border);
}}
.cad-fnkey:last-child {{ border-right: none; }}
.cad-fnkey:hover {{ color: var(--cad-amber); }}
.cad-fnkey kbd {{
  color: var(--cad-amber);
  font-weight: 600;
  font-size: 9.5px;
  letter-spacing: 0.05em;
}}
.cad-search {{
  flex: 1;
  max-width: 420px;
  margin: 0 auto;
}}
.cad-search input {{
  width: 100%;
  padding: 5px 10px 5px 26px;
  border: 1px solid var(--cad-border);
  background: #04060a;
  color: var(--cad-text);
  font-size: 11.5px;
  font-family: var(--cad-mono);
  outline: none;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}}
.cad-search {{ position: relative; }}
.cad-search::before {{
  content: "⌕"; position: absolute; left: 8px; top: 50%;
  transform: translateY(-50%); color: var(--cad-text3);
  font-size: 13px; pointer-events: none;
}}
.cad-search input:focus {{
  border-color: var(--cad-amber);
  box-shadow: 0 0 0 1px var(--cad-amber);
}}
.cad-search input::placeholder {{ color: var(--cad-text3); text-transform: uppercase; }}
.cad-topbar-right {{
  display: flex; align-items: center; gap: 10px;
  flex-shrink: 0;
  height: 100%;
}}
.cad-topbar-right a {{
  color: var(--cad-text2);
  text-decoration: none;
  font-size: 15px;
  display: inline-flex; align-items: center;
  padding: 0 6px;
}}
.cad-topbar-right a:hover {{ color: var(--cad-amber); }}
.cad-live {{
  display: inline-flex; align-items: center; gap: 6px;
  font-family: var(--cad-mono);
  font-size: 10px;
  color: var(--cad-pos);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  padding: 0 8px;
  border-left: 1px solid var(--cad-border);
  border-right: 1px solid var(--cad-border);
  height: 100%;
}}
.cad-live-dot {{
  width: 6px; height: 6px; background: var(--cad-pos);
  box-shadow: 0 0 6px var(--cad-pos);
  animation: cadPulse 2s ease-in-out infinite;
}}
@keyframes cadPulse {{
  0%, 100% {{ opacity: 1; }}
  50% {{ opacity: 0.45; }}
}}

/* ── Ticker Bar ── */
.cad-ticker {{
  position: fixed; top: var(--cad-topbar-h); left: 0; right: 0;
  height: var(--cad-ticker-h);
  background: #03050a;
  border-bottom: 1px solid var(--cad-border);
  overflow: hidden;
  z-index: 99;
  display: flex; align-items: center;
  font-size: 11px;
  font-family: var(--cad-mono);
  padding: 0 14px;
  white-space: nowrap;
  letter-spacing: 0.02em;
}}
.cad-ticker-label {{
  color: var(--cad-amber);
  font-size: 9.5px;
  font-weight: 700;
  letter-spacing: 0.15em;
  padding-right: 12px;
  margin-right: 12px;
  border-right: 1px solid var(--cad-border);
  text-transform: uppercase;
}}
.cad-tick {{
  display: inline-flex; gap: 6px; align-items: center;
  padding: 0 14px 0 0;
  margin-right: 14px;
  border-right: 1px solid var(--cad-border);
}}
.cad-tick:last-child {{ border-right: none; }}
.cad-tick-sym {{ color: var(--cad-text); font-weight: 600; letter-spacing: 0.05em; }}
.cad-tick-up {{ color: var(--cad-pos); }}
.cad-tick-up::before {{ content: "▲ "; font-size: 8px; }}
.cad-tick-down {{ color: var(--cad-neg); }}
.cad-tick-down::before {{ content: "▼ "; font-size: 8px; }}
.cad-tick-flat {{ color: var(--cad-text2); }}

/* ── Left Nav Rail ── */
.cad-nav {{
  position: fixed;
  top: calc(var(--cad-topbar-h) + var(--cad-ticker-h));
  left: 0; bottom: var(--cad-statusbar-h);
  width: var(--cad-nav-w);
  background: var(--cad-bg2);
  border-right: 1px solid var(--cad-border);
  display: flex; flex-direction: column;
  padding: 4px 0 0 0;
  z-index: 98;
  overflow-y: auto;
}}
.cad-nav::-webkit-scrollbar {{ width: 6px; }}
.cad-nav::-webkit-scrollbar-thumb {{ background: var(--cad-border); }}
.cad-nav-item {{
  display: flex; align-items: center; gap: 10px;
  padding: 6px 14px 6px 11px;
  color: var(--cad-text2);
  text-decoration: none;
  font-size: 12px;
  font-weight: 500;
  border-left: 3px solid transparent;
  transition: background-color 0.1s, color 0.1s;
  letter-spacing: 0.01em;
}}
.cad-nav-item:hover {{
  background: var(--cad-bg3);
  color: var(--cad-text);
}}
.cad-nav-item.active {{
  color: var(--cad-amber);
  border-left-color: var(--cad-amber);
  background: rgba(232,163,61,0.06);
  font-weight: 600;
}}
.cad-nav-icon {{
  width: 16px; text-align: center;
  font-size: 12px;
  color: var(--cad-text3);
}}
.cad-nav-item.active .cad-nav-icon {{ color: var(--cad-amber); }}
.cad-nav-section {{
  padding: 11px 14px 4px;
  font-size: 9px;
  color: var(--cad-text3);
  text-transform: uppercase;
  letter-spacing: 0.18em;
  font-weight: 700;
  margin-top: 4px;
  border-top: 1px solid var(--cad-border);
}}
.cad-nav-section:first-child {{ border-top: none; margin-top: 0; }}
.cad-nav-spacer {{ flex: 1; min-height: 8px; }}
.cad-nav-footer {{
  padding: 10px 14px;
  font-family: var(--cad-mono);
  font-size: 9.5px;
  color: var(--cad-text3);
  border-top: 1px solid var(--cad-border);
  line-height: 1.6;
  letter-spacing: 0.02em;
}}

/* ── Main Content ── */
.cad-main {{
  margin-top: calc(var(--cad-topbar-h) + var(--cad-ticker-h));
  margin-left: var(--cad-nav-w);
  margin-bottom: var(--cad-statusbar-h);
  padding: 20px 28px 24px;
  height: calc(100vh - var(--cad-topbar-h) - var(--cad-ticker-h) - var(--cad-statusbar-h));
  overflow-y: auto;
}}
.cad-main::-webkit-scrollbar {{ width: 8px; }}
.cad-main::-webkit-scrollbar-track {{ background: var(--cad-bg); }}
.cad-main::-webkit-scrollbar-thumb {{ background: var(--cad-border); }}
.cad-main::-webkit-scrollbar-thumb:hover {{ background: var(--cad-border-lt); }}
.cad-content {{ max-width: 1280px; }}

/* ── Status Bar (bottom) ── */
.cad-statusbar {{
  position: fixed; bottom: 0; left: 0; right: 0;
  height: var(--cad-statusbar-h);
  background: #030509;
  border-top: 1px solid var(--cad-border);
  display: flex; align-items: center;
  padding: 0 12px;
  z-index: 97;
  font-family: var(--cad-mono);
  font-size: 10px;
  color: var(--cad-text3);
  letter-spacing: 0.04em;
  gap: 0;
  text-transform: uppercase;
}}
.cad-status-item {{
  display: inline-flex; align-items: center; gap: 6px;
  padding: 0 12px;
  height: 100%;
  border-right: 1px solid var(--cad-border);
}}
.cad-status-item:first-child {{ padding-left: 4px; }}
.cad-status-key {{ color: var(--cad-text3); }}
.cad-status-val {{ color: var(--cad-text); font-weight: 600; }}
.cad-status-val.amber {{ color: var(--cad-amber); }}
.cad-status-val.pos {{ color: var(--cad-pos); }}
.cad-status-spacer {{ flex: 1; }}

/* ── Cards ── */
.cad-card {{
  background: var(--cad-bg2);
  border: 1px solid var(--cad-border);
  border-radius: 0;
  padding: 12px 16px 14px;
  margin-bottom: 10px;
  position: relative;
}}
.cad-card > h2:first-child,
.cad-card > h3:first-child {{
  margin: -12px -16px 12px -16px;
  padding: 7px 16px;
  border-bottom: 1px solid var(--cad-border);
  background: var(--cad-bg3);
  font-size: 10.5px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--cad-text);
}}
.cad-card h2 {{
  font-size: 12.5px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--cad-text);
  margin-bottom: 10px;
}}
.cad-card h3 {{
  font-size: 12.5px;
  font-weight: 600;
  color: var(--cad-text2);
  margin-bottom: 8px;
  letter-spacing: 0.04em;
}}

/* ── KPI Grid ── */
.cad-kpi-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(176px, 1fr));
  gap: 0;
  margin-bottom: 16px;
  border: 1px solid var(--cad-border);
  background: var(--cad-bg2);
}}
.cad-kpi {{
  background: var(--cad-bg2);
  border-right: 1px solid var(--cad-border);
  border-bottom: 1px solid var(--cad-border);
  padding: 10px 14px 12px;
  position: relative;
}}
.cad-kpi:hover {{ background: var(--cad-bg3); }}
.cad-kpi-value {{
  font-family: var(--cad-mono);
  font-size: 18px;
  font-weight: 600;
  color: var(--cad-text);
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.01em;
  line-height: 1.2;
}}
.cad-kpi-label {{
  font-size: 9.5px;
  color: var(--cad-text3);
  text-transform: uppercase;
  letter-spacing: 0.14em;
  margin-top: 6px;
  font-weight: 600;
}}
.cad-kpi-delta {{
  font-family: var(--cad-mono);
  font-size: 10.5px;
  margin-top: 2px;
  letter-spacing: 0.02em;
}}
.cad-kpi-delta.up {{ color: var(--cad-pos); }}
.cad-kpi-delta.down {{ color: var(--cad-neg); }}

/* ── Tables ── */
.cad-table {{ width: 100%; border-collapse: collapse; }}
.cad-table th {{
  text-align: left;
  font-size: 9.5px;
  color: var(--cad-text3);
  text-transform: uppercase;
  letter-spacing: 0.12em;
  padding: 7px 12px;
  border-bottom: 1px solid var(--cad-border-lt);
  border-top: 1px solid var(--cad-border);
  font-weight: 700;
  background: var(--cad-bg3);
}}
.cad-table td {{
  padding: 6px 12px;
  font-size: 12px;
  border-bottom: 1px solid var(--cad-border);
  color: var(--cad-text);
}}
.cad-table td.num {{
  font-family: var(--cad-mono);
  font-variant-numeric: tabular-nums;
  text-align: right;
  letter-spacing: 0.01em;
}}
.cad-table tbody tr:nth-child(even) {{ background: rgba(255,255,255,0.012); }}
.cad-table tbody tr:hover {{ background: var(--cad-bg3); }}
.cad-table a {{ color: var(--cad-link); text-decoration: none; }}
.cad-table a:hover {{ color: var(--cad-amber); text-decoration: underline; }}

/* ── Badges ── */
.cad-badge {{
  display: inline-block;
  padding: 2px 6px;
  border-radius: 0;
  font-size: 9.5px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-family: var(--cad-mono);
  border: 1px solid transparent;
}}
.cad-badge-green {{ background: rgba(34,197,94,0.12); color: #22c55e; border-color: rgba(34,197,94,0.3); }}
.cad-badge-amber {{ background: rgba(232,163,61,0.12); color: var(--cad-amber); border-color: rgba(232,163,61,0.3); }}
.cad-badge-red {{ background: rgba(239,68,68,0.12); color: #ef4444; border-color: rgba(239,68,68,0.3); }}
.cad-badge-blue {{ background: rgba(91,155,213,0.12); color: #5b9bd5; border-color: rgba(91,155,213,0.3); }}
.cad-badge-muted {{ background: var(--cad-bg3); color: var(--cad-text3); border-color: var(--cad-border); }}

/* ── Buttons ── */
.cad-btn {{
  display: inline-flex; align-items: center; gap: 5px;
  padding: 5px 12px;
  border-radius: 0;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid var(--cad-border-lt);
  background: var(--cad-bg3);
  color: var(--cad-text);
  transition: all 0.1s;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  font-family: var(--cad-font);
}}
.cad-btn:hover {{ background: var(--cad-bg2); border-color: var(--cad-amber); color: var(--cad-amber); }}
.cad-btn-primary {{
  background: var(--cad-accent);
  color: white;
  border-color: var(--cad-accent);
}}
.cad-btn-primary:hover {{ background: var(--cad-amber); border-color: var(--cad-amber); color: #000; }}

/* ── Typography ── */
.cad-h1 {{
  font-family: var(--cad-font);
  font-size: 15px;
  font-weight: 700;
  color: var(--cad-text);
  margin-bottom: 2px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}}
.cad-subtitle {{
  color: var(--cad-text3);
  font-size: 10.5px;
  margin-bottom: 16px;
  letter-spacing: 0.06em;
  font-family: var(--cad-mono);
  text-transform: uppercase;
}}
.cad-muted {{ color: var(--cad-text3); }}
.cad-mono {{ font-family: var(--cad-mono); font-variant-numeric: tabular-nums; }}

/* ── Page header rule ── */
.cad-content > .cad-h1 {{
  padding-bottom: 6px;
  border-bottom: 1px solid var(--cad-border);
  margin-bottom: 4px;
}}
.cad-content > .cad-subtitle {{
  margin-bottom: 18px;
  padding-top: 4px;
}}

/* ── Sparklines ── */
.cad-spark {{
  display: inline-block;
  vertical-align: middle;
  height: 18px;
}}
.cad-spark-line {{ fill: none; stroke-width: 1.2; }}
.cad-spark.pos .cad-spark-line {{ stroke: var(--cad-pos); }}
.cad-spark.neg .cad-spark-line {{ stroke: var(--cad-neg); }}
.cad-spark.flat .cad-spark-line {{ stroke: var(--cad-text3); }}
.cad-spark-area {{ opacity: 0.18; }}

/* ── Section code chip (right of card heading) ── */
.cad-section-code {{
  font-family: var(--cad-mono);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.15em;
  color: var(--cad-amber);
  padding: 1px 5px;
  border: 1px solid var(--cad-border-lt);
  background: #03050a;
  text-transform: uppercase;
}}

/* ── Heatmap cell shades (green -> red gradient for %ile data) ── */
.cad-heat-1 {{ background: rgba(34,197,94,0.16); color: #a8e4b6; }}
.cad-heat-2 {{ background: rgba(34,197,94,0.08); color: var(--cad-text); }}
.cad-heat-3 {{ background: rgba(148,163,184,0.06); color: var(--cad-text); }}
.cad-heat-4 {{ background: rgba(245,158,11,0.10); color: #fde4b1; }}
.cad-heat-5 {{ background: rgba(239,68,68,0.16); color: #fca5a5; }}

/* ── Command palette (Cmd+K / Ctrl+K) ── */
.cad-palette-backdrop {{
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.7); backdrop-filter: blur(2px);
  display: none; align-items: flex-start; justify-content: center;
  z-index: 9998; padding-top: 14vh;
}}
.cad-palette-backdrop.open {{ display: flex; }}
.cad-palette {{
  width: min(640px, 92vw);
  background: var(--cad-bg2);
  border: 1px solid var(--cad-border-lt);
  box-shadow: 0 20px 60px rgba(0,0,0,0.8);
  display: flex; flex-direction: column;
  max-height: 70vh;
}}
.cad-palette-input {{
  width: 100%;
  padding: 14px 16px;
  background: transparent;
  border: none;
  border-bottom: 1px solid var(--cad-border);
  color: var(--cad-text);
  font-family: var(--cad-mono);
  font-size: 14px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  outline: none;
}}
.cad-palette-input::placeholder {{ color: var(--cad-text3); }}
.cad-palette-results {{
  overflow-y: auto;
  flex: 1;
  padding: 4px 0;
}}
.cad-palette-item {{
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 16px;
  color: var(--cad-text2);
  text-decoration: none;
  font-size: 12.5px;
  cursor: pointer;
  border-left: 3px solid transparent;
}}
.cad-palette-item.sel {{
  background: var(--cad-bg3);
  color: var(--cad-text);
  border-left-color: var(--cad-amber);
}}
.cad-palette-item-label {{ display: flex; align-items: center; gap: 10px; }}
.cad-palette-item-cat {{
  font-family: var(--cad-mono);
  font-size: 9px;
  color: var(--cad-text3);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  padding: 1px 5px;
  border: 1px solid var(--cad-border);
}}
.cad-palette-hint {{
  font-family: var(--cad-mono);
  font-size: 9.5px;
  color: var(--cad-text3);
  letter-spacing: 0.08em;
  padding: 8px 16px;
  border-top: 1px solid var(--cad-border);
  display: flex; gap: 18px;
  text-transform: uppercase;
}}
.cad-palette-hint kbd {{
  color: var(--cad-amber);
  border: 1px solid var(--cad-border-lt);
  padding: 1px 5px;
  font-family: var(--cad-mono);
}}

/* ── Form controls (professional terminal style) ── */
.cad-field {{
  display: flex; flex-direction: column;
  gap: 3px;
}}
.cad-field label, .cad-label {{
  font-family: var(--cad-mono);
  font-size: 9.5px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--cad-text3);
}}
.cad-input, .cad-select {{
  padding: 5px 9px;
  border: 1px solid var(--cad-border);
  background: #03050a;
  color: var(--cad-text);
  font-family: var(--cad-mono);
  font-size: 11.5px;
  letter-spacing: 0.02em;
  border-radius: 0;
  outline: none;
  min-height: 28px;
  transition: border-color 0.1s, box-shadow 0.1s;
}}
.cad-input:focus, .cad-select:focus {{
  border-color: var(--cad-amber);
  box-shadow: inset 0 0 0 1px var(--cad-amber);
}}
.cad-input::placeholder {{ color: var(--cad-text3); text-transform: uppercase; font-size: 10.5px; letter-spacing: 0.04em; }}
.cad-select {{
  appearance: none;
  background-image: linear-gradient(45deg, transparent 50%, var(--cad-text3) 50%),
    linear-gradient(135deg, var(--cad-text3) 50%, transparent 50%);
  background-position: calc(100% - 12px) 55%, calc(100% - 7px) 55%;
  background-size: 5px 5px, 5px 5px;
  background-repeat: no-repeat;
  padding-right: 22px;
}}
.cad-form-row {{
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: flex-end;
}}

/* ── Ticker-style ID (monospace, tracked, pro feel) ── */
.cad-ticker-id {{
  font-family: var(--cad-mono);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--cad-text);
  background: #03050a;
  padding: 2px 6px;
  border: 1px solid var(--cad-border);
}}
.cad-ticker-id:hover {{ border-color: var(--cad-amber); color: var(--cad-amber); }}

/* ── Sticky table headers (append class="cad-table-sticky" to parent) ── */
.cad-table-sticky {{ position: relative; }}
.cad-table-sticky .cad-table thead th {{
  position: sticky; top: 0; z-index: 2;
}}

/* ── Crosshair row highlight ── */
.cad-table tbody tr {{ cursor: default; }}
.cad-table.crosshair tbody tr:hover td {{
  box-shadow: inset 0 1px 0 var(--cad-amber), inset 0 -1px 0 var(--cad-amber);
}}

/* ── Pill delta (monospace, tight, bloomberg-style) ── */
.cad-delta {{
  display: inline-block;
  font-family: var(--cad-mono);
  font-size: 10px;
  letter-spacing: 0.02em;
  padding: 0 3px;
  margin-left: 3px;
}}
.cad-delta.pos {{ color: var(--cad-pos); }}
.cad-delta.neg {{ color: var(--cad-neg); }}

/* ── Inline sparkbar (for horizontal bar in tables) ── */
.cad-bar {{
  display: inline-block;
  height: 6px;
  background: var(--cad-border);
  vertical-align: middle;
  position: relative;
  width: 60px;
}}
.cad-bar-fill {{
  position: absolute; left: 0; top: 0; bottom: 0;
  background: var(--cad-accent);
}}
.cad-bar-fill.pos {{ background: var(--cad-pos); }}
.cad-bar-fill.neg {{ background: var(--cad-neg); }}

/* ── Print ── */
@media print {{
  .cad-topbar, .cad-ticker, .cad-nav, .cad-statusbar {{ display: none !important; }}
  .cad-main {{ margin: 0 !important; padding: 16px !important; height: auto !important; }}
  body.caduceus {{ background: white !important; color: black !important; overflow: visible !important; height: auto !important; }}
  .cad-card {{ border: 1px solid #ccc !important; background: white !important; }}
  .cad-table th {{ background: #f0f0f0 !important; color: black !important; }}
}}

/* ── Responsive ── */
@media (max-width: 900px) {{
  .cad-fnkeys {{ display: none; }}
}}
@media (max-width: 768px) {{
  .cad-nav {{ width: var(--cad-nav-collapsed); }}
  .cad-nav-item span {{ display: none; }}
  .cad-main {{ margin-left: var(--cad-nav-collapsed); padding: 14px; }}
  .cad-ticker-label {{ display: none; }}
}}
"""


def _ticker_html() -> str:
    """Static placeholder ticker — replaced by live data when available."""
    ticks = [
        ("HCA", "+0.34%", "up"), ("THC", "-0.89%", "down"),
        ("UHS", "+1.12%", "up"), ("CYH", "-0.21%", "down"),
        ("10Y TSY", "4.23%", "flat"), ("HOSP MULT", "11.2x", "flat"),
        ("S&P HC", "+0.18%", "up"), ("SENT", "0.62", "flat"),
    ]
    items = ['<span class="cad-ticker-label">MKT</span>']
    for sym, val, direction in ticks:
        cls = f"cad-tick-{direction}"
        items.append(
            f'<span class="cad-tick">'
            f'<span class="cad-tick-sym">{sym}</span>'
            f'<span class="{cls}">{val}</span>'
            f'</span>'
        )
    return "".join(items)


def _fnkeys_html() -> str:
    """Bloomberg-style function-key hints in top bar."""
    keys = [
        ("H", "HOME", "/home"),
        ("A", "ANALYSIS", "/analysis"),
        ("P", "PORTFOLIO", "/portfolio"),
        ("S", "SCREEN", "/predictive-screener"),
        ("M", "MARKET", "/market-data/map"),
    ]
    parts = []
    for k, label, href in keys:
        parts.append(
            f'<a class="cad-fnkey" href="{href}" title="g+{k.lower()}">'
            f'<kbd>{k}</kbd><span>{label}</span></a>'
        )
    return "".join(parts)


def sparkline(
    values: "list[float] | tuple[float, ...]",
    *,
    width: int = 64,
    height: int = 18,
    direction: Optional[str] = None,
) -> str:
    """Render an inline SVG sparkline. Returns empty string for <2 points.

    direction: "up" | "down" | "flat" | None (auto-detect from first vs last).
    """
    if not values:
        return ""
    try:
        xs = [float(v) for v in values if v is not None]
    except (TypeError, ValueError):
        return ""
    if len(xs) < 2:
        return ""
    lo, hi = min(xs), max(xs)
    span = hi - lo or 1.0
    n = len(xs)
    if direction is None:
        if xs[-1] > xs[0]:
            direction = "pos"
        elif xs[-1] < xs[0]:
            direction = "neg"
        else:
            direction = "flat"
    else:
        direction = {"up": "pos", "down": "neg"}.get(direction, direction)
    pts = []
    for i, v in enumerate(xs):
        x = (i / (n - 1)) * (width - 2) + 1
        y = height - 1 - ((v - lo) / span) * (height - 2)
        pts.append(f"{x:.1f},{y:.1f}")
    polyline = " ".join(pts)
    # Area polygon for subtle fill
    area = f"{polyline} {width-1:.1f},{height-1:.1f} 1,{height-1:.1f}"
    return (
        f'<svg class="cad-spark {direction}" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" preserveAspectRatio="none" '
        f'aria-hidden="true">'
        f'<polygon class="cad-spark-line cad-spark-area" points="{area}" />'
        f'<polyline class="cad-spark-line" points="{polyline}" />'
        f'</svg>'
    )


def _palette_html() -> str:
    """Bloomberg-style Cmd+K command palette."""
    # Curated nav targets + model shortcuts
    entries = [
        ("NAV", "Home", "/home"),
        ("NAV", "Deal Screener", "/predictive-screener"),
        ("NAV", "Hospital Screener", "/screen"),
        ("NAV", "Market Data", "/market-data/map"),
        ("NAV", "News & Research", "/news"),
        ("NAV", "Pipeline", "/pipeline"),
        ("NAV", "Deals", "/portfolio"),
        ("NAV", "Monitor", "/portfolio/monitor"),
        ("NAV", "Team", "/team"),
        ("NAV", "Import Deal", "/import"),
        ("ANL", "Regression", "/portfolio/regression"),
        ("ANL", "ML Insights", "/ml-insights"),
        ("ANL", "Quant Lab", "/quant-lab"),
        ("ANL", "Model Validation", "/model-validation"),
        ("ANL", "Scenarios", "/scenarios"),
        ("REF", "Methodology", "/methodology"),
        ("REF", "Data Sources", "/data"),
        ("REF", "API Docs", "/api/docs"),
        ("REF", "Settings", "/settings"),
        ("REF", "Alerts", "/alerts"),
    ]
    items = []
    for cat, label, href in entries:
        items.append(
            f'<a class="cad-palette-item" data-label="{_html.escape(label.lower())}" '
            f'href="{href}">'
            f'<span class="cad-palette-item-label">{_html.escape(label)}</span>'
            f'<span class="cad-palette-item-cat">{cat}</span></a>'
        )
    return (
        '<div class="cad-palette-backdrop" id="cad-palette-bd" role="dialog" aria-hidden="true">'
        '<div class="cad-palette">'
        '<input type="text" class="cad-palette-input" id="cad-palette-input" '
        'placeholder="Type a command or page…" aria-label="Command palette">'
        f'<div class="cad-palette-results" id="cad-palette-results">{"".join(items)}</div>'
        '<div class="cad-palette-hint">'
        '<span><kbd>↑↓</kbd> Navigate</span>'
        '<span><kbd>⏎</kbd> Open</span>'
        '<span><kbd>Esc</kbd> Close</span>'
        '</div>'
        '</div></div>'
    )


def _statusbar_html() -> str:
    """Bloomberg-style bottom status bar — session, clock, data vintage."""
    return (
        '<div class="cad-status-item">'
        '<span class="cad-status-key">SESSION</span>'
        '<span class="cad-status-val pos" id="cad-sess">ACTIVE</span>'
        '</div>'
        '<div class="cad-status-item">'
        '<span class="cad-status-key">DATA</span>'
        '<span class="cad-status-val">HCRIS FY2022</span>'
        '</div>'
        '<div class="cad-status-item">'
        '<span class="cad-status-key">HOSPITALS</span>'
        '<span class="cad-status-val">6,123</span>'
        '</div>'
        '<div class="cad-status-item">'
        '<span class="cad-status-key">MODELS</span>'
        '<span class="cad-status-val">17</span>'
        '</div>'
        '<div class="cad-status-spacer"></div>'
        '<div class="cad-status-item">'
        '<span class="cad-status-key">LATENCY</span>'
        '<span class="cad-status-val" id="cad-latency">—</span>'
        '</div>'
        '<div class="cad-status-item">'
        '<span class="cad-status-key">UTC</span>'
        '<span class="cad-status-val amber" id="cad-clock">—</span>'
        '</div>'
        '<div class="cad-status-item">'
        '<span class="cad-status-key">BUILD</span>'
        '<span class="cad-status-val">v1.0</span>'
        '</div>'
    )


def _nav_html(active_path: str = "/") -> str:
    """Build the left navigation rail with section separators."""
    items = []
    for nav in NAV_ITEMS:
        if nav.get("separator"):
            items.append(
                f'<div class="cad-nav-section">{nav["label"]}</div>'
            )
            continue
        href = nav.get("href", "/")
        active = " active" if (
            active_path == href
            or (href != "/home" and active_path.startswith(href))
        ) else ""
        icon = NAV_ICONS.get(nav.get("icon", ""), "")
        items.append(
            f'<a class="cad-nav-item{active}" href="{href}">'
            f'<span class="cad-nav-icon">{icon}</span>'
            f'<span>{nav["label"]}</span></a>'
        )
    return "\n".join(items)


def shell_v2(
    body: str,
    title: str,
    *,
    active_nav: str = "/",
    subtitle: Optional[str] = None,
    extra_css: str = "",
    extra_js: str = "",
    show_ticker: bool = True,
) -> str:
    """Render a page inside the SeekingChartis unified shell."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    ticker = (
        f'<div class="cad-ticker">{_ticker_html()}</div>'
        if show_ticker else ""
    )

    subtitle_html = (
        f'<div class="cad-subtitle">{_html.escape(subtitle)}</div>'
        if subtitle else ""
    )

    csrf_js = (
        "(function(){"
        "function c(n){var m=document.cookie.match("
        "new RegExp('(?:^|; )'+n+'=([^;]*)'));"
        "return m?decodeURIComponent(m[1]):null;}"
        "document.addEventListener('submit',function(e){"
        "var t=c('rcm_csrf');if(!t)return;"
        "var f=e.target;if(!f||f.tagName!=='FORM')return;"
        "if(f.method&&f.method.toLowerCase()!=='post')return;"
        "var x=f.querySelector('input[name=csrf_token]');"
        "if(!x){x=document.createElement('input');x.type='hidden';"
        "x.name='csrf_token';f.appendChild(x);}x.value=t;},true);"
        "var of=window.fetch;if(of){window.fetch=function(u,o){"
        "o=o||{};var t=c('rcm_csrf');"
        "if(t&&o.method&&o.method.toUpperCase()!=='GET'){"
        "o.headers=o.headers||{};"
        "if(!o.headers['X-CSRF-Token'])o.headers['X-CSRF-Token']=t;}"
        "return of(u,o);};}"
        "})();"
    )

    badge_js = (
        "(function(){"
        "fetch('/api/alerts/active-count').then(function(r){return r.json();})"
        ".then(function(d){var b=document.getElementById('cad-alert-count');"
        "if(b&&d.count>0){b.textContent=d.count;b.style.display='inline';}}"
        ").catch(function(){});"
        "})();"
    )

    return (
        '<!DOCTYPE html>\n'
        f'<html lang="en"><head><meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{_html.escape(title)} — SeekingChartis</title>'
        f'<link rel="preconnect" href="https://fonts.googleapis.com">'
        f'<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        f'<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&'
        f'family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">'
        f'<link rel="manifest" href="/manifest.json">'
        f'<meta name="theme-color" content="#1F4E78">'
        f'<style>{_SHELL_CSS}{extra_css}</style>'
        f'</head><body class="caduceus">'

        # Top bar
        f'<header class="cad-topbar">'
        f'<a href="/home" class="cad-topbar-logo">{LOGO_SVG}'
        f'<span class="cad-wordmark">SeekingChartis</span>'
        f'<span class="cad-topbar-version">v{BRAND["version"]}</span></a>'
        f'<nav class="cad-fnkeys" aria-label="Function keys">{_fnkeys_html()}</nav>'
        f'<form class="cad-search" action="/search" method="GET">'
        f'<input type="text" name="q" placeholder="Search deals, hospitals, tickers…" '
        f'aria-label="Search"></form>'
        f'<div class="cad-topbar-right">'
        f'<span class="cad-live" title="Live market data feed">'
        f'<span class="cad-live-dot"></span>LIVE</span>'
        f'<a href="/alerts" title="Alerts">&#128276;'
        f'<span id="cad-alert-count" style="display:none;background:#ef4444;'
        f'color:white;padding:0 5px;font-size:9.5px;font-family:var(--cad-mono);'
        f'font-weight:700;vertical-align:top;margin-left:2px;"></span></a>'
        f'<a href="/api/docs" title="API Docs">&#128218;</a>'
        f'</div></header>'

        # Ticker
        f'{ticker}'

        # Left nav
        f'<nav class="cad-nav" aria-label="Main navigation">'
        f'{_nav_html(active_nav)}'
        f'<div class="cad-nav-spacer"></div>'
        f'<div class="cad-nav-footer">'
        f'{BRAND["footer_text"]}<br>'
        f'<span style="color:var(--cad-text3);font-size:9px;">Data: HCRIS FY2022 | '
        f'6,123 hospitals</span></div>'
        f'</nav>'

        # Main content
        f'<main class="cad-main">'
        f'<div class="cad-content">'
        f'<h1 class="cad-h1">{_html.escape(title)}</h1>'
        f'{subtitle_html}'
        f'{body}'
        f'</div></main>'

        # Bottom status bar
        f'<footer class="cad-statusbar" role="status">'
        f'{_statusbar_html()}'
        f'</footer>'

        # Command palette (Cmd+K)
        f'{_palette_html()}'

        f'<script>{csrf_js}{badge_js}'
        # Live UTC clock + request-latency in status bar
        f'(function(){{'
        f'var c=document.getElementById("cad-clock");'
        f'function pad(n){{return n<10?"0"+n:""+n;}}'
        f'function tick(){{if(!c)return;var d=new Date();'
        f'c.textContent=pad(d.getUTCHours())+":"+pad(d.getUTCMinutes())+":"+pad(d.getUTCSeconds());}}'
        f'tick();setInterval(tick,1000);'
        f'var L=document.getElementById("cad-latency");'
        f'if(L&&window.performance&&performance.timing){{'
        f'var t=performance.timing;var ms=t.responseEnd-t.requestStart;'
        f'if(ms>0&&ms<60000)L.textContent=ms+"ms";}}'
        f'}})();'
        f'(function(){{'
        f'var si=document.querySelector(".cad-search input[name=q]");'
        f'if(!si)return;'
        f'var dd=document.createElement("div");'
        f'dd.style.cssText="position:absolute;top:100%;left:0;right:0;'
        f'background:var(--cad-bg2);border:1px solid var(--cad-border);'
        f'border-radius:0 0 8px 8px;max-height:300px;overflow-y:auto;'
        f'display:none;z-index:200;";'
        f'si.parentNode.style.position="relative";'
        f'si.parentNode.appendChild(dd);'
        f'var timer=null;'
        f'si.addEventListener("input",function(){{'
        f'clearTimeout(timer);'
        f'var q=si.value.trim();'
        f'if(q.length<2){{dd.style.display="none";return;}}'
        f'timer=setTimeout(function(){{'
        f'fetch("/api/deals/search?q="+encodeURIComponent(q)+"&limit=8")'
        f'.then(function(r){{return r.json();}})'
        f'.then(function(d){{'
        f'var items=d.results||d.deals||[];'
        f'if(!items.length){{dd.style.display="none";return;}}'
        f'dd.innerHTML="";'
        f'items.forEach(function(h){{'
        f'var did=h.deal_id||h.id||"";if(!did)return;'
        f'var a=document.createElement("a");'
        f'a.href=h.type==="hospital"?"/hospital/"+did:"/deal/"+did;'
        f'a.style.cssText="display:block;padding:8px 12px;color:var(--cad-text);'
        f'text-decoration:none;font-size:12.5px;border-bottom:1px solid var(--cad-border);";'
        f'a.textContent=(h.name||h.deal_id||"")+(h.type==="hospital"?" (HCRIS)":"");'
        f'a.onmouseenter=function(){{this.style.background="var(--cad-bg3)";}};'
        f'a.onmouseleave=function(){{this.style.background="";}};'
        f'dd.appendChild(a);'
        f'}});dd.style.display="block";}}'
        f').catch(function(){{}});'
        f'}},200);'
        f'}});'
        f'document.addEventListener("click",function(e){{'
        f'if(!si.parentNode.contains(e.target))dd.style.display="none";'
        f'}});'
        f'}})();'
        # Keyboard navigation: ? for help, g+key for go-to, / for search
        f'(function(){{'
        f'var gMode=false,gTimer=null;'
        f'var shortcuts={{"h":"/home","a":"/analysis","n":"/news","m":"/market-data/map",'
        f'"s":"/screen","p":"/portfolio","l":"/library","r":"/portfolio/regression",'
        f'"i":"/import","d":"/api/docs"}};'
        f'document.addEventListener("keydown",function(e){{'
        f'if(e.target.tagName==="INPUT"||e.target.tagName==="TEXTAREA"||e.target.tagName==="SELECT")return;'
        f'if(e.key==="/"){{e.preventDefault();var si=document.querySelector(".cad-search input");if(si)si.focus();return;}}'
        f'if(e.key==="?"){{e.preventDefault();'
        f'var helpExists=document.getElementById("cad-kb-help");'
        f'if(helpExists){{helpExists.remove();return;}}'
        f'var h=document.createElement("div");h.id="cad-kb-help";'
        f'h.style.cssText="position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);'
        f'background:var(--cad-bg2);border:1px solid var(--cad-border);border-radius:12px;'
        f'padding:24px 32px;z-index:9999;min-width:320px;box-shadow:0 8px 32px rgba(0,0,0,0.5);";'
        f'h.innerHTML="<h2 style=\\"margin-bottom:12px;font-size:15px;\\">Keyboard Shortcuts</h2>'
        f'<div style=\\"font-size:12.5px;line-height:2;\\">'
        f'<div><kbd style=\\"background:var(--cad-bg3);padding:2px 6px;border-radius:3px;font-family:var(--cad-mono);\\">?</kbd> This help</div>'
        f'<div><kbd style=\\"background:var(--cad-bg3);padding:2px 6px;border-radius:3px;font-family:var(--cad-mono);\\">/</kbd> Focus search</div>'
        f'<div><kbd style=\\"background:var(--cad-bg3);padding:2px 6px;border-radius:3px;font-family:var(--cad-mono);\\">g h</kbd> Go to Home</div>'
        f'<div><kbd style=\\"background:var(--cad-bg3);padding:2px 6px;border-radius:3px;font-family:var(--cad-mono);\\">g a</kbd> Go to Analysis</div>'
        f'<div><kbd style=\\"background:var(--cad-bg3);padding:2px 6px;border-radius:3px;font-family:var(--cad-mono);\\">g m</kbd> Go to Market Data</div>'
        f'<div><kbd style=\\"background:var(--cad-bg3);padding:2px 6px;border-radius:3px;font-family:var(--cad-mono);\\">g n</kbd> Go to News</div>'
        f'<div><kbd style=\\"background:var(--cad-bg3);padding:2px 6px;border-radius:3px;font-family:var(--cad-mono);\\">g p</kbd> Go to Portfolio</div>'
        f'<div><kbd style=\\"background:var(--cad-bg3);padding:2px 6px;border-radius:3px;font-family:var(--cad-mono);\\">g r</kbd> Go to Regression</div>'
        f'<div><kbd style=\\"background:var(--cad-bg3);padding:2px 6px;border-radius:3px;font-family:var(--cad-mono);\\">g s</kbd> Go to Screener</div>'
        f'<div><kbd style=\\"background:var(--cad-bg3);padding:2px 6px;border-radius:3px;font-family:var(--cad-mono);\\">g l</kbd> Go to Library</div>'
        f'<div><kbd style=\\"background:var(--cad-bg3);padding:2px 6px;border-radius:3px;font-family:var(--cad-mono);\\">g i</kbd> Go to Import</div>'
        f'</div>'
        f'<div style=\\"margin-top:12px;text-align:right;\\">'
        f'<button onclick=\\"this.parentNode.parentNode.remove()\\" '
        f'style=\\"background:var(--cad-accent);color:white;border:none;padding:6px 16px;'
        f'border-radius:6px;cursor:pointer;\\">Close</button></div>";'
        f'document.body.appendChild(h);return;}}'
        f'if(e.key==="g"&&!gMode){{gMode=true;clearTimeout(gTimer);gTimer=setTimeout(function(){{gMode=false;}},800);return;}}'
        f'if(gMode){{gMode=false;clearTimeout(gTimer);var dest=shortcuts[e.key];'
        f'if(dest){{e.preventDefault();window.location.href=dest;}}}}'
        f'}});'
        f'}})();'
        # Command palette (Cmd+K / Ctrl+K)
        f'(function(){{'
        f'var bd=document.getElementById("cad-palette-bd");'
        f'var inp=document.getElementById("cad-palette-input");'
        f'var res=document.getElementById("cad-palette-results");'
        f'if(!bd||!inp||!res)return;'
        f'var items=Array.prototype.slice.call(res.querySelectorAll(".cad-palette-item"));'
        f'var sel=0;'
        f'function render(q){{'
        f'q=(q||"").trim().toLowerCase();'
        f'var shown=0;sel=0;'
        f'items.forEach(function(el,i){{'
        f'var lbl=el.getAttribute("data-label")||"";'
        f'var match=!q||lbl.indexOf(q)!==-1;'
        f'el.style.display=match?"flex":"none";'
        f'el.classList.remove("sel");'
        f'if(match&&shown===0){{el.classList.add("sel");sel=i;}}'
        f'if(match)shown++;'
        f'}});'
        f'}}'
        f'function open(){{bd.classList.add("open");bd.setAttribute("aria-hidden","false");'
        f'inp.value="";render("");setTimeout(function(){{inp.focus();}},10);}}'
        f'function close(){{bd.classList.remove("open");bd.setAttribute("aria-hidden","true");}}'
        f'function move(dir){{'
        f'var visible=items.filter(function(el){{return el.style.display!=="none";}});'
        f'if(!visible.length)return;'
        f'var curIdx=visible.findIndex(function(el){{return el.classList.contains("sel");}});'
        f'if(curIdx<0)curIdx=0;'
        f'visible[curIdx].classList.remove("sel");'
        f'curIdx=(curIdx+dir+visible.length)%visible.length;'
        f'visible[curIdx].classList.add("sel");'
        f'visible[curIdx].scrollIntoView({{block:"nearest"}});}}'
        f'function pick(){{'
        f'var s=res.querySelector(".cad-palette-item.sel");'
        f'if(s&&s.style.display!=="none"){{window.location.href=s.getAttribute("href");}}}}'
        f'document.addEventListener("keydown",function(e){{'
        f'var cmd=e.metaKey||e.ctrlKey;'
        f'if(cmd&&(e.key==="k"||e.key==="K")){{e.preventDefault();'
        f'if(bd.classList.contains("open")){{close();}}else{{open();}}return;}}'
        f'if(!bd.classList.contains("open"))return;'
        f'if(e.key==="Escape"){{e.preventDefault();close();}}'
        f'else if(e.key==="ArrowDown"){{e.preventDefault();move(1);}}'
        f'else if(e.key==="ArrowUp"){{e.preventDefault();move(-1);}}'
        f'else if(e.key==="Enter"){{e.preventDefault();pick();}}'
        f'}});'
        f'inp.addEventListener("input",function(){{render(inp.value);}});'
        f'res.addEventListener("click",function(e){{var a=e.target.closest(".cad-palette-item");if(a){{close();}}}});'
        f'bd.addEventListener("click",function(e){{if(e.target===bd)close();}});'
        f'}})();'
        f'{extra_js}</script>'
        f'</body></html>\n'
    )
