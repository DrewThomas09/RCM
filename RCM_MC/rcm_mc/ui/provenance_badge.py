"""Provenance badges — click to see source / methodology /
confidence / sample size on every modeled number.

The platform already has a strong provenance system in
``rcm_mc.provenance.tracker``: every modeled scalar can be wrapped
in a ``DataPoint`` carrying source, source_detail, confidence,
as_of_date, and an upstream chain. The directive asks for the UI
half — a small icon next to each number that reveals all of it
on click.

This module ships:

  • ``provenance_badge(data_point, value_html=None)`` — renders a
    value (or just an icon) with a click-to-expand popover
    containing the full provenance card.
  • ``provenance_icon_only(data_point)`` — just the icon, no
    value. Used in column headers or alongside externally-rendered
    values.
  • Source-aware icons: 🛢 for raw data, ◇ for benchmark
    medians, ◈ for predicted, Σ for calculated, ⌬ for Monte
    Carlo. Single-glyph Unicode (consistent with empty_states).
  • Confidence badge color via the semantic palette: ≥0.85 green,
    ≥0.60 amber, <0.60 red.

Pure HTML + CSS, no JS — uses the ``<details>`` element for
click-to-expand. Works without JavaScript and survives static
HTML exports.

Public API::

    from rcm_mc.ui.provenance_badge import (
        provenance_badge,
        provenance_icon_only,
        SOURCE_ICONS,
    )
"""
from __future__ import annotations

import html as _html
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


# Icon per Source. Single-glyph Unicode keeps deployments
# portable (no SVG asset bundling).
SOURCE_ICONS: Dict[str, str] = {
    "USER_INPUT":           "✎",
    "HCRIS":                "🛢",
    "IRS990":               "📑",
    "REGRESSION_PREDICTED": "◈",
    "BENCHMARK_MEDIAN":     "◇",
    "MONTE_CARLO_P50":      "⌬",
    "CALCULATED":           "Σ",
}

# Human-readable labels for the popover heading.
SOURCE_LABELS: Dict[str, str] = {
    "USER_INPUT":           "User input",
    "HCRIS":                "HCRIS public data",
    "IRS990":               "IRS Form 990",
    "REGRESSION_PREDICTED":
        "Regression prediction",
    "BENCHMARK_MEDIAN":     "Peer benchmark median",
    "MONTE_CARLO_P50":      "Monte Carlo simulation",
    "CALCULATED":           "Calculated downstream",
}


def _confidence_kind(conf: Optional[float]) -> str:
    """Map a confidence score to a status kind."""
    if conf is None:
        return "neutral"
    if conf >= 0.85:
        return "positive"
    if conf >= 0.60:
        return "watch"
    return "negative"


def _confidence_color(conf: Optional[float]) -> str:
    """Hex color matching the kind."""
    return {
        "positive": "var(--green)",
        "watch": "var(--amber)",
        "negative": "var(--red)",
        "neutral": "var(--faint)",
    }[_confidence_kind(conf)]


# Stylesheet — namespaced under .pv-, idempotent because
# class-based.
_CSS = """
<style>
.pv{display:inline-flex;align-items:baseline;gap:4px;}
.pv-icon{display:inline-block;width:14px;height:14px;
  border-radius:50%;background:var(--border);color:var(--faint);
  font-size:10px;font-weight:600;line-height:14px;
  text-align:center;cursor:pointer;font-family:system-ui;
  user-select:none;border:none;padding:0;}
.pv-icon:hover{background:var(--blue);color:var(--blue-soft);}
details.pv-details{display:inline;}
details.pv-details > summary{display:inline-block;
  list-style:none;cursor:pointer;}
details.pv-details > summary::-webkit-details-marker{
  display:none;}
.pv-card{position:absolute;display:block;
  background:var(--bg);border:1px solid var(--border);
  border-radius:6px;padding:14px 16px;width:320px;
  font-size:12px;line-height:1.5;
  box-shadow:0 8px 24px rgba(0,0,0,0.55);z-index:1500;
  color:var(--ink);font-weight:normal;
  text-align:left;}
.pv-card h4{margin:0 0 8px 0;font-size:11px;
  color:var(--blue-soft);text-transform:uppercase;
  letter-spacing:0.06em;font-weight:600;
  display:flex;align-items:center;gap:8px;}
.pv-card-row{display:flex;justify-content:space-between;
  margin-top:6px;color:var(--faint);font-size:11px;}
.pv-card-row > strong{color:var(--ink);font-weight:500;
  font-variant-numeric:tabular-nums;}
.pv-card .pv-detail{color:var(--border);margin:8px 0 0 0;}
.pv-conf{display:inline-block;padding:1px 8px;
  border-radius:4px;font-size:10px;font-weight:600;
  font-variant-numeric:tabular-nums;}
.pv-upstream{margin-top:10px;padding-top:8px;
  border-top:1px solid var(--border);}
.pv-upstream-label{font-size:10px;color:var(--teal);
  text-transform:uppercase;letter-spacing:0.06em;
  margin-bottom:4px;}
.pv-upstream li{font-size:11px;color:var(--faint);
  margin-left:14px;}
</style>
"""


def _datapoint_attr(dp: Any, name: str,
                    default: Any = None) -> Any:
    """Pull an attribute from either a DataPoint or a plain
    dict (for callers shaping their own payloads)."""
    if isinstance(dp, dict):
        return dp.get(name, default)
    return getattr(dp, name, default)


def _source_value(dp: Any) -> str:
    """Return the source as a string regardless of whether dp
    holds a Source enum or a raw string."""
    src = _datapoint_attr(dp, "source", "")
    val = getattr(src, "value", src)
    return str(val) if val else ""


def _render_card(dp: Any) -> str:
    """Render the popover card content."""
    src_value = _source_value(dp)
    icon = SOURCE_ICONS.get(src_value, "?")
    label = SOURCE_LABELS.get(src_value, src_value or "—")
    detail = (_datapoint_attr(dp, "source_detail", "")
              or "")
    conf = _datapoint_attr(dp, "confidence", None)
    as_of = _datapoint_attr(dp, "as_of_date", None)
    sample_size = _datapoint_attr(dp, "sample_size", None)
    upstream = _datapoint_attr(dp, "upstream", []) or []

    rows: List[str] = []
    if as_of:
        rows.append(
            f'<div class="pv-card-row">'
            f'<span>As of</span>'
            f'<strong>{_html.escape(str(as_of))}</strong>'
            f'</div>')
    if sample_size is not None:
        rows.append(
            f'<div class="pv-card-row">'
            f'<span>Sample size</span>'
            f'<strong>n = {int(sample_size):,}</strong>'
            f'</div>')
    if conf is not None:
        kind = _confidence_kind(conf)
        bg = {
            "positive": "var(--green)",
            "watch": "var(--amber)",
            "negative": "var(--red)",
            "neutral": "var(--border)",
        }[kind]
        fg = {
            "positive": "var(--green-soft)",
            "watch": "var(--amber-soft)",
            "negative": "var(--red-soft)",
            "neutral": "var(--faint)",
        }[kind]
        rows.append(
            f'<div class="pv-card-row">'
            f'<span>Confidence</span>'
            f'<span class="pv-conf" style="background:'
            f'{bg};color:{fg};">{conf * 100:.0f}%</span>'
            f'</div>')

    detail_html = ""
    if detail:
        detail_html = (
            f'<div class="pv-detail">'
            f'{_html.escape(str(detail))}</div>')

    upstream_html = ""
    if upstream:
        items = "".join([
            f'<li>{_html.escape(str(_datapoint_attr(u, "metric_name", "—")))} '
            f'<em>({SOURCE_LABELS.get(_source_value(u), "—")})</em>'
            f'</li>'
            for u in upstream[:6]
        ])
        upstream_html = (
            f'<div class="pv-upstream">'
            f'<div class="pv-upstream-label">'
            f'Upstream</div>'
            f'<ul style="margin:0;padding:0;'
            f'list-style:disc;">{items}</ul></div>')

    return (
        f'<div class="pv-card">'
        f'<h4><span>{icon}</span>'
        f'<span>{_html.escape(label)}</span></h4>'
        + detail_html + "".join(rows) + upstream_html
        + '</div>')


def provenance_icon_only(
    dp: Any,
    *,
    inject_css: bool = True,
) -> str:
    """Render just the provenance icon — used in column headers
    and inline alongside externally-rendered values.

    Click expands a `<details>` element with the full card.
    """
    src_value = _source_value(dp)
    icon = SOURCE_ICONS.get(src_value, "?")
    css = _CSS if inject_css else ""
    return (
        css
        + f'<details class="pv-details">'
        f'<summary>'
        f'<span class="pv-icon" '
        f'aria-label="View provenance">{icon}</span>'
        f'</summary>'
        + _render_card(dp)
        + '</details>')


def provenance_badge(
    dp: Any,
    *,
    value_html: Optional[str] = None,
    inject_css: bool = True,
) -> str:
    """Render a value next to a clickable provenance icon.

    Args:
      dp: a DataPoint (or dict with the same fields).
      value_html: pre-formatted value HTML to render. When None,
        falls back to the DataPoint's .value attribute formatted
        with three decimals.
      inject_css: include the stylesheet (default True; pass
        False on subsequent badges in the same page to dedupe).

    Returns: HTML snippet.
    """
    if value_html is None:
        v = _datapoint_attr(dp, "value", None)
        if v is None:
            value_html = "—"
        else:
            try:
                value_html = f"{float(v):.3f}"
            except (TypeError, ValueError):
                value_html = str(v)
    return (
        (_CSS if inject_css else "")
        + f'<span class="pv">'
        f'<span style="font-variant-numeric:'
        f'tabular-nums;">{value_html}</span>'
        + provenance_icon_only(dp, inject_css=False)
        + '</span>')
