"""Shared "explain this number" tooltip helper for the v3 UI.

Phase 4C of the v3 transformation campaign requires that every
numeric on a page that has provenance gets a tooltip or
expand-on-click that shows the provenance graph explanation
from rcm_mc/provenance/explain.py.

This module ships ``provenance_tooltip(label, value, ...)`` —
a single helper that wraps a partner-displayed value in a
hover-card showing the provenance explanation, upstream
sources, and node type. Pure HTML + CSS (no JavaScript), same
as the metric_glossary tooltip pattern. Falls through to
plain escaped text when no graph or no entry is available
(no broken tooltips ever shipped).

Why a shared helper:
  - Single source of truth for the hover visual + card layout
    so the look is consistent across every metric on every
    page.
  - Single place to handle the "no provenance available"
    fallthrough so callers don't need a try/except per cell.
  - Single CSS injection so callers can pass inject_css=False
    on subsequent calls within one render to avoid duplicate
    <style> blocks.

Public API:
    provenance_tooltip(label, value, *, graph=None,
                       metric_key=None, inject_css=True) -> str
"""
from __future__ import annotations

import html as _html
from typing import Any, Optional


# Pure HTML+CSS tooltip — hover the icon, the card appears.
# Mimics the existing metric_glossary tooltip CSS so the
# visual feels native.
_TT_CSS = """<style>
.prov-tt {position:relative;display:inline-flex;align-items:baseline;gap:4px;}
.prov-tt-icon {display:inline-block;width:13px;height:13px;line-height:13px;
  text-align:center;border-radius:50%;background:var(--cad-bg3,#1a1a1a);
  color:var(--cad-text3,#888);font-size:9px;font-weight:600;
  font-family:var(--cad-mono,monospace);cursor:help;
  border:1px solid var(--cad-border,#333);}
/* display:none (not visibility:hidden) when closed so the absolutely-
   positioned 320px card does NOT extend the page's scrollWidth — a
   hidden-but-laid-out card anchored on a right-edge KPI pushed every
   hospital/regression page ~64px wide at 1280 (and ~107px at 768).
   max-width clamps the card to the viewport so it never overflows on
   narrow widths. Colors moved off the stale dark --cad-bg2 fallback
   (#0e0e0e, which rendered dark-on-dark under the editorial theme) to
   the white editorial card to match .ck-prov-tt-card. */
.prov-tt-card {display:none;position:absolute;z-index:1000;
  bottom:calc(100% + 6px);left:0;width:max-content;
  max-width:min(320px, calc(100vw - 28px));
  background:#fff;border:1px solid var(--sc-rule,#d6cfc0);
  border-radius:2px;padding:10px 12px;font-size:11.5px;line-height:1.45;
  color:var(--sc-text,#1a2332);box-shadow:var(--sc-shadow-2,0 6px 24px rgba(6,22,38,0.08));
  pointer-events:none;}
.prov-tt:hover .prov-tt-card,
.prov-tt:focus-within .prov-tt-card {display:block;}
.prov-tt-label {font-weight:600;color:var(--cad-text,#e6e6e6);
  margin-bottom:4px;}
.prov-tt-type {font-family:var(--cad-mono,monospace);font-size:9.5px;
  letter-spacing:0.08em;color:var(--cad-text3,#888);text-transform:uppercase;
  margin-bottom:6px;}
.prov-tt-prose {color:var(--cad-text2,#bbb);margin-bottom:6px;}
.prov-tt-upstream-h {font-family:var(--cad-mono,monospace);font-size:9.5px;
  letter-spacing:0.08em;color:var(--cad-text3,#888);text-transform:uppercase;
  margin-top:6px;margin-bottom:3px;}
.prov-tt-upstream {list-style:none;padding:0;margin:0;}
.prov-tt-upstream li {font-size:11px;color:var(--cad-text2,#bbb);
  padding:1px 0;}
.prov-tt-upstream code {font-family:var(--cad-mono,monospace);font-size:10px;
  color:var(--cad-text3,#888);}
</style>"""


def _fmt_upstream_value(val: Any, unit: str) -> str:
    """Render an upstream node's numeric value alongside its unit
    in the tooltip card. Mirrors explain.py's `_fmt` shape but
    returns a string suitable for inline HTML."""
    if val is None:
        return "n/a"
    try:
        v = float(val)
    except (TypeError, ValueError):
        return _html.escape(str(val))
    if unit == "pct":
        return f"{v:.1f}%"
    if unit == "USD":
        if abs(v) >= 1e6:
            return f"${v / 1e6:.1f}M"
        if abs(v) >= 1e3:
            return f"${v / 1e3:.0f}K"
        return f"${v:,.0f}"
    if unit == "days":
        return f"{v:.0f}d"
    if unit == "fraction":
        return f"{v * 100:.1f}%"
    if unit:
        return f"{v:.2f} {_html.escape(unit)}"
    return f"{v:.2f}"


def provenance_tooltip(
    label: str,
    value: str,
    *,
    graph: Optional[Any] = None,
    metric_key: Optional[str] = None,
    inject_css: bool = True,
) -> str:
    """Render a value with optional hover-tooltip showing the
    provenance graph explanation.

    Args:
        label: User-visible label of the numeric (e.g.,
            "Operating Margin"). Will be HTML-escaped.
        value: Pre-formatted string value the page is about
            to display (e.g., "12.4%"). Will be HTML-escaped.
        graph: Optional ProvenanceGraph for the deal/page
            context. When None, no tooltip is shown.
        metric_key: Optional metric key recognised by
            provenance.explain.explain_for_ui. When None or
            unresolved, no tooltip is shown.
        inject_css: When True (default), the <style> block is
            inlined before the tooltip. Pages rendering many
            tooltips should pass False on all but the first
            call to avoid duplicate <style> blocks.

    Returns:
        HTML string. With graph + metric_key resolved, returns
        a `<span class="prov-tt">` wrapper containing the
        value + an info icon + a hidden card with the
        explanation. With either missing or the lookup
        failing, returns plain escaped value text — no
        broken tooltips, no exceptions.
    """
    # Cycle 46 — return SafeHtml so callers passing the result
    # through _esc()-using helpers (ck_kpi_block, etc.) don't
    # double-escape the tooltip markup.
    from ._chartis_kit import SafeHtml
    safe_value = _html.escape(value)
    if graph is None or not metric_key:
        return SafeHtml(safe_value)

    # Lazy import — pages without provenance should never pay
    # for the explainer at module-load time.
    try:
        from ..provenance.explain import explain_for_ui
        info = explain_for_ui(graph, metric_key)
    except Exception:
        return SafeHtml(safe_value)

    if not isinstance(info, dict) or "error" in info:
        # Metric not in graph, CCD chain incomplete, or any
        # other lookup failure → degrade silently to plain
        # value rather than ship a broken-looking tooltip.
        return SafeHtml(safe_value)

    css = _TT_CSS if inject_css else ""

    full_prose = str(info.get("explanation_full") or "").strip()
    node_type = str(info.get("node_type") or "").strip()
    upstream = info.get("upstream") or []

    # Card header
    card_parts = [
        f'<div class="prov-tt-label">{_html.escape(label)}</div>',
    ]
    if node_type:
        card_parts.append(
            f'<div class="prov-tt-type">{_html.escape(node_type)}</div>'
        )
    if full_prose:
        card_parts.append(
            f'<div class="prov-tt-prose">{_html.escape(full_prose)}</div>'
        )

    # Upstream list (cap at 5 entries to keep card compact —
    # explain_for_ui already caps at 10)
    if upstream:
        items = []
        for u in upstream[:5]:
            u_label = _html.escape(str(u.get("label") or u.get("id") or ""))
            u_val = _fmt_upstream_value(u.get("value"), str(u.get("unit") or ""))
            u_src = _html.escape(str(u.get("source") or ""))
            src_clause = (
                f' <code>{u_src}</code>' if u_src else ""
            )
            items.append(
                f'<li>{u_label} — {u_val}{src_clause}</li>'
            )
        card_parts.append(
            '<div class="prov-tt-upstream-h">Upstream</div>'
            '<ul class="prov-tt-upstream">'
            f'{"".join(items)}</ul>'
        )

    return SafeHtml(
        f'{css}<span class="prov-tt">'
        f'<span>{safe_value}</span>'
        f'<span class="prov-tt-icon" tabindex="0" '
        f'aria-label="Show provenance for {_html.escape(label)}">i</span>'
        f'<span class="prov-tt-card">{"".join(card_parts)}</span>'
        f'</span>'
    )
