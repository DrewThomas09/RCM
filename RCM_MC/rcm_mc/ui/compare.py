"""Side-by-side comparison views with visual diff.

The existing ``deal_comparison.py`` is packet-specific (operates
on ``DealAnalysisPacket`` with hardcoded dimensions). This module
ships the **reusable** comparison primitive that any caller —
hospitals, scenarios, peer cohorts, model versions — can drop in.

Visual diff:

  • Each metric row identifies the winner (best on that metric)
    and renders a small ▲ next to the winning value with a
    green color from the semantic palette.
  • Losing values get a muted color so the eye reads the winner
    first.
  • Differences from a reference column shown as ``+12%`` /
    ``-5%`` deltas.
  • Configurable per-metric direction (``lower_is_better=True``
    for denial rate / DSO, ``False`` for collection rate /
    margin).

Two specialized wrappers wrap the primitive for the canonical
use cases:

  • ``compare_hospitals(hospitals, metrics)`` — N hospitals
    side-by-side on selected RCM metrics.
  • ``compare_scenarios(scenarios, metrics)`` — bull/base/bear
    or sensitivity sweep side-by-side.

Public API::

    from rcm_mc.ui.compare import (
        ComparableEntity,
        ComparisonMetric,
        render_comparison,
        compare_hospitals,
        compare_scenarios,
    )
"""
from __future__ import annotations

import html as _html
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from .colors import STATUS
from .metric_glossary import (
    get_metric_definition, metric_label_with_info,
)


@dataclass
class ComparableEntity:
    """One column in the comparison.

    Attributes:
      label: column header (e.g. 'Aurora', 'Bull case').
      sublabel: optional second-line label (e.g. CCN, scenario
        narrative).
      values: dict of metric_key → value.
      href: optional drilldown URL on the column header.
    """
    label: str
    values: Dict[str, Any]
    sublabel: str = ""
    href: Optional[str] = None


@dataclass
class ComparisonMetric:
    """One row in the comparison."""
    key: str                      # metric_glossary key when applicable
    label: str = ""               # override the registry label
    kind: str = "number"          # number / money / pct / int / text
    lower_is_better: bool = False
    show_in_glossary: bool = True


def _format_value(value: Any, kind: str) -> str:
    if value is None or value == "":
        return "—"
    try:
        if kind == "money":
            v = float(value)
            if abs(v) >= 1e9:
                return f"${v / 1e9:,.2f}B"
            if abs(v) >= 1e6:
                return f"${v / 1e6:,.1f}M"
            if abs(v) >= 1e3:
                return f"${v / 1e3:,.0f}K"
            return f"${v:,.0f}"
        if kind == "pct":
            return f"{float(value) * 100:+.1f}%"
        if kind == "int":
            return f"{int(value):,}"
        if kind == "number":
            v = float(value)
            return (f"{v:,.0f}" if abs(v) >= 100
                    else f"{v:,.3f}")
    except (TypeError, ValueError):
        pass
    return str(value)


def _winner_index(
    values: List[Optional[float]],
    *,
    lower_is_better: bool,
) -> Optional[int]:
    """Index of the best value, or None when all None or tied."""
    numeric = [
        (i, v) for i, v in enumerate(values)
        if v is not None
    ]
    if len(numeric) < 2:
        return None
    if lower_is_better:
        best = min(numeric, key=lambda p: p[1])
    else:
        best = max(numeric, key=lambda p: p[1])
    # Skip if multiple share the best value (a tie has no
    # winner)
    n_best = sum(1 for _, v in numeric
                 if v == best[1])
    if n_best > 1:
        return None
    return best[0]


def _delta_pct(
    value: Optional[float],
    reference: Optional[float],
) -> Optional[float]:
    """Return value/reference - 1, or None when undefined."""
    if (value is None or reference is None
            or reference == 0):
        return None
    return value / reference - 1.0


# ── Renderer ────────────────────────────────────────────────

def render_comparison(
    entities: List[ComparableEntity],
    metrics: List[ComparisonMetric],
    *,
    title: Optional[str] = None,
    reference_index: int = 0,
    show_deltas: bool = True,
    inject_css: bool = True,
) -> str:
    """Render an N-column side-by-side comparison.

    Args:
      entities: 2+ entities (the columns).
      metrics: metrics to compare (the rows).
      title: optional header above the table.
      reference_index: which column to use as the reference for
        delta computation. Default 0 (leftmost).
      show_deltas: when True, non-reference columns show their
        delta vs reference next to the value.
      inject_css: include the small stylesheet.

    Returns: HTML string.
    """
    if len(entities) < 2:
        raise ValueError("Need ≥2 entities to compare")
    n_cols = len(entities)

    css = (
        '<style>'
        '.cmp-table{width:100%;border-collapse:collapse;'
        'background:#1f2937;border:1px solid #374151;'
        'border-radius:8px;overflow:hidden;}'
        '.cmp-table th,.cmp-table td{padding:10px 14px;'
        'text-align:right;font-variant-numeric:tabular-nums;'
        'border-bottom:1px solid #374151;color:#d1d5db;}'
        '.cmp-table th.cmp-header{background:#111827;'
        'text-align:right;font-size:11px;text-transform:'
        'uppercase;letter-spacing:0.05em;color:#9ca3af;}'
        '.cmp-table th.cmp-metric{text-align:left;color:#f3f4f6;'
        'font-size:13px;font-weight:500;}'
        '.cmp-table th.cmp-metric-header{text-align:left;}'
        '.cmp-table .cmp-sublabel{display:block;'
        'font-size:10px;color:#9ca3af;font-weight:400;'
        'text-transform:none;letter-spacing:0;'
        'margin-top:2px;}'
        '.cmp-winner{color:#10b981;font-weight:600;}'
        '.cmp-loser{color:#9ca3af;}'
        '.cmp-delta{font-size:10px;color:#9ca3af;'
        'margin-left:6px;}'
        '.cmp-delta.up{color:#10b981;}'
        '.cmp-delta.down{color:#ef4444;}'
        '.cmp-arrow{margin-right:4px;font-size:10px;}'
        '.cmp-table a{color:#60a5fa;'
        'text-decoration:none;}'
        '.cmp-table a:hover{text-decoration:underline;}'
        '</style>') if inject_css else ""

    # Header row
    header_cells: List[str] = [
        '<th class="cmp-header cmp-metric-header">Metric</th>'
    ]
    for e in entities:
        label_html = _html.escape(e.label)
        if e.href:
            label_html = (
                f'<a href="{_html.escape(e.href)}">'
                f'{label_html}</a>')
        sub_html = (
            f'<span class="cmp-sublabel">'
            f'{_html.escape(e.sublabel)}</span>'
            if e.sublabel else "")
        header_cells.append(
            f'<th class="cmp-header">{label_html}'
            f'{sub_html}</th>')
    header_row = (
        '<tr>' + "".join(header_cells) + '</tr>')

    # Data rows
    data_rows: List[str] = []
    for m in metrics:
        # Resolve the row label — use the registry when the
        # metric is in the glossary, else the override or the key
        defn = get_metric_definition(m.key)
        if (m.show_in_glossary and defn is not None
                and not m.label):
            label_html = metric_label_with_info(
                m.key, label=defn.label,
                inject_css=False)
        else:
            display_label = (
                m.label or m.key.replace("_", " ").title())
            label_html = _html.escape(display_label)

        # Pull numeric values once
        raw_values: List[Optional[float]] = []
        for e in entities:
            v = e.values.get(m.key)
            try:
                raw_values.append(
                    float(v) if v is not None else None)
            except (TypeError, ValueError):
                raw_values.append(None)
        winner_idx = _winner_index(
            raw_values, lower_is_better=m.lower_is_better)

        cells: List[str] = [
            f'<th class="cmp-metric">{label_html}</th>'
        ]
        ref = (raw_values[reference_index]
               if reference_index < len(raw_values)
               else None)
        for i, e in enumerate(entities):
            v = e.values.get(m.key)
            formatted = _format_value(v, m.kind)
            css_class = ""
            arrow = ""
            if winner_idx == i:
                css_class = "cmp-winner"
                arrow = (
                    '<span class="cmp-arrow">▲</span>')
            elif winner_idx is not None:
                css_class = "cmp-loser"

            delta_html = ""
            if (show_deltas and i != reference_index
                    and m.kind in (
                        "number", "money", "pct", "int")):
                d = _delta_pct(raw_values[i], ref)
                if d is not None and abs(d) >= 0.001:
                    direction = ("up"
                                 if d > 0 else "down")
                    # When lower is better, an up delta is a
                    # *worse* outcome, so flip the color
                    if m.lower_is_better:
                        direction = ("down" if d > 0
                                     else "up")
                    delta_html = (
                        f'<span class="cmp-delta '
                        f'{direction}">{d * 100:+.1f}%'
                        f'</span>')
            cells.append(
                f'<td class="{css_class}">{arrow}{formatted}'
                f'{delta_html}</td>')
        data_rows.append(
            '<tr>' + "".join(cells) + '</tr>')

    title_html = (
        f'<h3 style="margin:0 0 10px 0;font-size:14px;'
        f'color:#f3f4f6;font-weight:600;">'
        f'{_html.escape(title)}</h3>'
        if title else "")

    return (
        css
        + title_html
        + '<table class="cmp-table">'
        + '<thead>' + header_row + '</thead>'
        + '<tbody>' + "".join(data_rows) + '</tbody>'
        + '</table>'
    )


# ── Specialized wrappers ────────────────────────────────────

# Default RCM metrics for hospital comparison. Order matches the
# partner's mental scan: lever effectiveness, then volume, then
# financial.
HOSPITAL_DEFAULT_METRICS = [
    ComparisonMetric(
        "denial_rate", kind="pct",
        lower_is_better=True),
    ComparisonMetric(
        "days_in_ar", kind="number",
        lower_is_better=True),
    ComparisonMetric(
        "net_collection_rate", kind="pct",
        lower_is_better=False),
    ComparisonMetric(
        "clean_claim_rate", kind="pct",
        lower_is_better=False),
    ComparisonMetric(
        "operating_margin", kind="pct",
        lower_is_better=False),
    ComparisonMetric(
        "ebitda_margin", kind="pct",
        lower_is_better=False),
    ComparisonMetric(
        "occupancy_rate", kind="pct",
        lower_is_better=False),
]


def compare_hospitals(
    hospitals: List[Dict[str, Any]],
    *,
    metrics: Optional[List[ComparisonMetric]] = None,
    title: Optional[str] = "Hospital comparison",
    inject_css: bool = True,
) -> str:
    """Render an N-hospital side-by-side comparison.

    Args:
      hospitals: list of dicts with at least 'name' (or 'label')
        plus per-metric values keyed by metric.key.
        Optionally 'ccn', 'state', 'href'.
      metrics: override metric list. Default = the canonical
        7-metric RCM scan.
      title: card heading.

    Returns: HTML string.
    """
    if len(hospitals) < 2:
        raise ValueError(
            "Need ≥2 hospitals to compare")
    metrics = metrics or HOSPITAL_DEFAULT_METRICS
    entities = []
    for h in hospitals:
        label = h.get("name") or h.get("label") or "—"
        sub_parts = []
        if h.get("ccn"):
            sub_parts.append(f"CCN {h['ccn']}")
        if h.get("state"):
            sub_parts.append(h["state"])
        entities.append(ComparableEntity(
            label=label,
            sublabel=" · ".join(sub_parts),
            values=h,
            href=h.get("href")))
    return render_comparison(
        entities, metrics,
        title=title, inject_css=inject_css)


def compare_scenarios(
    scenarios: List[Dict[str, Any]],
    *,
    metrics: Optional[List[ComparisonMetric]] = None,
    title: Optional[str] = "Scenario comparison",
    reference_index: int = 0,
    inject_css: bool = True,
) -> str:
    """Render an N-scenario side-by-side comparison.

    Common shape: bull / base / bear scenarios from a Monte
    Carlo or improvement-potential model. Reference column
    defaults to leftmost — pass reference_index=1 to anchor
    deltas against the base case.

    Args:
      scenarios: list of dicts with 'name' (or 'label') plus
        per-metric values. Optionally 'description'.
      metrics: override metric list. No default — caller
        supplies the relevant scenario metrics.
      title: card heading.
      reference_index: which scenario column to use as the
        delta reference.
    """
    if len(scenarios) < 2:
        raise ValueError(
            "Need ≥2 scenarios to compare")
    if metrics is None or not metrics:
        raise ValueError(
            "Scenario comparison needs an explicit "
            "metrics list — there's no canonical default")
    entities = [
        ComparableEntity(
            label=(s.get("name") or s.get("label") or "—"),
            sublabel=s.get("description", ""),
            values=s,
            href=s.get("href"))
        for s in scenarios
    ]
    return render_comparison(
        entities, metrics,
        title=title,
        reference_index=reference_index,
        inject_css=inject_css)
