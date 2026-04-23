"""Corpus red-flag panel injector for /analysis/<deal_id>.

Produces a self-contained HTML panel (dark Bloomberg-style) that can be
injected into the existing analysis workbench page just before </body>.
The panel is a fixed-bottom drawer that shows corpus-calibrated red flags
for the current deal without modifying analysis_workbench.py.

Public API:
    render_corpus_flags_panel(deal: dict) -> str
    inject_into_workbench(workbench_html: str, deal: dict) -> str
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

from ..brand import PALETTE as _BRAND_PALETTE

# Phase 7: severity colours pull from the flag-aware central palette
# so the red-flag drawer flips with CHARTIS_UI_V2. Key names
# preserved so every _SEVERITY_COLOR["critical"] reference below is
# unchanged.
_SEVERITY_COLOR = {
    "critical": _BRAND_PALETTE["critical"],
    "high":     _BRAND_PALETTE["high"],
    "medium":   _BRAND_PALETTE["medium"],
    "low":      _BRAND_PALETTE["low"],
}

_SEVERITY_BG = {
    "critical": "rgba(220,38,38,0.08)",
    "high": "rgba(234,88,12,0.08)",
    "medium": "rgba(202,138,4,0.06)",
    "low": "rgba(71,85,105,0.06)",
}

_CATEGORY_LABEL = {
    "ENTRY_RISK": "ENTRY",
    "PAYER": "PAYER",
    "SECTOR": "SECTOR",
    "LEVERAGE": "LEVERAGE",
    "HOLD": "HOLD",
    "SIZING": "SIZING",
}

_PANEL_CSS = """
<style id="ck-corpus-flags-css">
.ckf-drawer {
  position: fixed;
  bottom: 0; left: 0; right: 0; z-index: 9000;
  background: #0b0f18;
  border-top: 1px solid #1e293b;
  font-family: 'JetBrains Mono', 'SF Mono', monospace;
  font-size: 11px;
  max-height: 42px;
  transition: max-height 0.2s ease;
  overflow: hidden;
}
.ckf-drawer.open { max-height: 420px; overflow-y: auto; }
.ckf-header {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 16px; cursor: pointer;
  background: #0b0f18; border-bottom: 1px solid #1e293b;
  position: sticky; top: 0; z-index: 1;
}
.ckf-header:hover { background: #111827; }
.ckf-title {
  font-size: 10px; letter-spacing: 0.12em; text-transform: uppercase;
  color: #64748b; font-weight: 600;
}
.ckf-badge {
  display: inline-block; padding: 1px 6px; border-radius: 2px;
  font-size: 9.5px; font-weight: 700; letter-spacing: 0.05em;
}
.ckf-badge-critical { background: rgba(220,38,38,0.15); color: #dc2626; }
.ckf-badge-high     { background: rgba(234,88,12,0.15);  color: #ea580c; }
.ckf-badge-medium   { background: rgba(202,138,4,0.15);  color: #ca8a04; }
.ckf-badge-low      { background: rgba(71,85,105,0.15);  color: #94a3b8; }
.ckf-badge-ok       { background: rgba(34,197,94,0.12);  color: #22c55e; }
.ckf-body { padding: 10px 16px 14px; }
.ckf-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(280px,1fr)); gap: 8px;
  margin-top: 8px;
}
.ckf-flag {
  background: var(--flag-bg, #111827);
  border: 1px solid var(--flag-border, #1e293b);
  border-left: 3px solid var(--flag-color, #334155);
  padding: 8px 10px; border-radius: 0 3px 3px 0;
}
.ckf-flag-cat {
  font-size: 8.5px; letter-spacing: 0.12em; text-transform: uppercase;
  color: #475569; margin-bottom: 3px;
}
.ckf-flag-headline {
  font-size: 11px; color: #e2e8f0; line-height: 1.4; margin-bottom: 4px;
  font-weight: 500;
}
.ckf-flag-detail {
  font-size: 10px; color: #64748b; line-height: 1.5;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-variant-numeric: normal; white-space: normal;
}
.ckf-flag-risk {
  margin-top: 5px; font-size: 9.5px;
  font-family: 'JetBrains Mono', monospace; font-variant-numeric: tabular-nums;
  color: #ea580c;
}
.ckf-ok { color: #22c55e; font-size: 11px; padding: 8px 0; }
.ckf-meta {
  font-size: 9px; color: #334155; margin-top: 10px; letter-spacing: 0.08em;
}
.ckf-toggle { margin-left: auto; color: #334155; font-size: 14px; }
.ckf-summary { display:flex; gap:8px; align-items:center; flex-wrap: wrap; }
</style>
"""

_PANEL_JS = """
<script id="ck-corpus-flags-js">
(function(){
  var drawer = document.getElementById('ckf-drawer');
  var toggle = document.getElementById('ckf-toggle');
  if (!drawer) return;
  drawer.querySelector('.ckf-header').addEventListener('click', function(){
    var open = drawer.classList.toggle('open');
    toggle.textContent = open ? '▲' : '▼';
  });
})();
</script>
"""


def _sev_badge(severity: str, label: Optional[str] = None) -> str:
    cls = f"ckf-badge ckf-badge-{severity}"
    text = _html.escape(label or severity.upper())
    return f'<span class="{cls}">{text}</span>'


def _flag_card(flag: Any) -> str:
    color = _SEVERITY_COLOR.get(flag.severity, "#475569")
    bg = _SEVERITY_BG.get(flag.severity, "rgba(71,85,105,0.06)")
    cat_label = _CATEGORY_LABEL.get(flag.category, flag.category)
    risk_html = ""
    if flag.ebitda_at_risk_mm is not None:
        risk_html = (
            f'<div class="ckf-flag-risk">'
            f'EBITDA at risk: <strong>${flag.ebitda_at_risk_mm:.1f}M</strong></div>'
        )
    return (
        f'<div class="ckf-flag" style="--flag-color:{color};--flag-bg:{bg};--flag-border:{color}33;">'
        f'<div class="ckf-flag-cat">{_sev_badge(flag.severity)} &nbsp;{_html.escape(cat_label)}</div>'
        f'<div class="ckf-flag-headline">{_html.escape(flag.headline)}</div>'
        f'<div class="ckf-flag-detail">{_html.escape(flag.detail)}</div>'
        f'{risk_html}'
        f'</div>'
    )


def render_corpus_flags_panel(deal: Dict[str, Any]) -> str:
    """Render the full corpus red-flag panel HTML for injection into any page."""
    from rcm_mc.data_public.corpus_red_flags import detect_corpus_red_flags, flag_summary

    flags = detect_corpus_red_flags(deal)
    summary = flag_summary(flags)
    deal_name = deal.get("name") or deal.get("deal_name") or deal.get("deal_id") or "Deal"

    # Summary badges for collapsed header
    by_sev = summary["by_severity"]
    badge_parts = []
    for sev in ("critical", "high", "medium", "low"):
        n = by_sev.get(sev, 0)
        if n > 0:
            badge_parts.append(_sev_badge(sev, f"{n} {sev}"))
    if not badge_parts:
        badge_parts.append('<span class="ckf-badge ckf-badge-ok">CLEAR</span>')

    total_risk = summary.get("total_ebitda_at_risk_mm")
    risk_summary = (
        f'&nbsp;·&nbsp; <span style="color:#ea580c;font-family:\'JetBrains Mono\',monospace;'
        f'font-variant-numeric:tabular-nums">${total_risk:.1f}M EBITDA at risk</span>'
        if total_risk else ""
    )

    # Body
    if flags:
        flags_html = f'<div class="ckf-grid">{"".join(_flag_card(f) for f in flags)}</div>'
    else:
        flags_html = '<div class="ckf-ok">No corpus red flags detected. Entry characteristics are within normal ranges.</div>'

    body_html = (
        f'<div class="ckf-body">'
        f'<div style="font-size:9px;color:#334155;margin-bottom:6px;letter-spacing:0.08em;">'
        f'CORPUS RED FLAGS — {_html.escape(str(deal_name)).upper()} — '
        f'{summary["total_flags"]} flag{"s" if summary["total_flags"] != 1 else ""} '
        f'from {615} realized corpus deals'
        f'</div>'
        f'{flags_html}'
        f'<div class="ckf-meta">Source: SeekingChartis corpus · {615} deals · '
        f'corpus-OLS calibration · flags are indicative, not dispositive</div>'
        f'</div>'
    )

    panel = (
        _PANEL_CSS
        + f'<div class="ckf-drawer" id="ckf-drawer">'
        f'<div class="ckf-header">'
        f'<span class="ckf-title">Corpus Red Flags</span>'
        f'<div class="ckf-summary">{"".join(badge_parts)}</div>'
        f'{risk_summary}'
        f'<span class="ckf-toggle" id="ckf-toggle">▼</span>'
        f'</div>'
        f'{body_html}'
        f'</div>'
        + _PANEL_JS
    )

    return panel


def inject_into_workbench(workbench_html: str, deal: Dict[str, Any]) -> str:
    """Inject the corpus flags panel just before </body> in the workbench HTML."""
    try:
        panel = render_corpus_flags_panel(deal)
    except Exception:
        return workbench_html  # Never break the main page

    marker = "</body>"
    idx = workbench_html.rfind(marker)
    if idx == -1:
        return workbench_html + panel
    return workbench_html[:idx] + panel + workbench_html[idx:]
