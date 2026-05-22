"""MetricCatalog — fund-level returns cross-reference block.

Renders the fund-level return metrics the /app page can source from
``portfolio_rollup`` (Weighted MOIC / IRR). Each row is a label + a
tabular-num value.

History: this block originally tried to show 4 columns (RETURNS / RCM
DRAG / COVENANTS / INITIATIVES), but the deal-level columns couldn't be
sourced from the data this helper receives — covenant data lives in the
``covenant_metrics`` table, initiative variance needs ``store``, DPI/TVPI
are never computed — so they rendered as dead ``—``. Per the
simplify-to-what-it-can-source decision, the catalog now shows only the
live RETURNS metrics; the deal-level data is shown live in the dedicated
EBITDA-drag / covenant-heatmap / initiative-tracker blocks on the same
page.

CSS lives in static/v3/chartis.css under the METRIC CATALOG header.
"""
from __future__ import annotations

import html as _html
from typing import Any, Mapping, Optional, Sequence, Tuple

# Each group is (label, level, items) where items is a sequence of
# (label, value_str) pairs. level is "fund" or "deal" — controls badge tint.
_GroupItems = Sequence[Tuple[str, str]]
_Group = Tuple[str, str, _GroupItems]


def render_metric_catalog(
    *,
    rollup: Optional[Mapping[str, Any]] = None,
    focused_packet: Optional[Mapping[str, Any]] = None,  # noqa: ARG001 — kept for signature compat; deal-level data is shown in dedicated blocks
) -> str:
    """Render the fund-level returns catalog.

    Args:
        rollup: Output of portfolio_rollup() — the fund-level return
            metrics (Weighted MOIC / IRR). When None, shows "—".
        focused_packet: accepted for backwards compatibility but no longer
            used (the deal-level columns it backed couldn't be sourced
            here; that data is shown in the EBITDA-drag / covenant-heatmap
            / initiative-tracker blocks instead).

    Returns:
        HTML string. Section header + the RETURNS column.
    """
    groups = _build_groups(rollup)
    cols_html = "".join(_render_col(g) for g in groups)
    return (
        '<div class="sect">'
        '<div>'
        '<div class="micro">METRIC CATALOG</div>'
        '<h2>Fund returns<br/>at a glance</h2>'
        '</div>'
        '<p class="desc">Fund-level return metrics. Deal-level drag, '
        'covenants, and initiative variance are shown live in the '
        'dedicated blocks below.</p>'
        '</div>'
        f'<div class="catalog">{cols_html}</div>'
    )


def _render_col(group: _Group) -> str:
    title, level, items = group
    rows_html = "".join(
        f'<tr><td class="lbl">{_html.escape(label)}</td>'
        f'<td class="r v">{_html.escape(value)}</td></tr>'
        for label, value in items
    )
    level_class = "fund" if level == "fund" else "deal"
    level_label = "FUND" if level == "fund" else "DEAL"
    return (
        '<div class="cat-col">'
        '<div class="cat-h">'
        f'<span class="ttl">{_html.escape(title)}</span>'
        f'<span class="lvl {level_class}">{level_label}</span>'
        '</div>'
        f'<table><tbody>{rows_html}</tbody></table>'
        '</div>'
    )


def _build_groups(
    rollup: Optional[Mapping[str, Any]],
) -> Sequence[_Group]:
    """Pull the fund-level return metrics out of the rollup.

    Only the metrics the rollup actually computes are shown (Weighted
    MOIC / IRR). Missing → "—" — never a faked number.
    """
    return [
        ("RETURNS", "fund", [
            ("Weighted MOIC", _fmt_moic(_get(rollup, "weighted_moic"))),
            ("Weighted IRR",  _fmt_pct(_get(rollup, "weighted_irr"))),
        ]),
    ]


# ── tiny extractors / formatters ─────────────────────────────────────

_DASH = "—"


def _get(d: Optional[Mapping[str, Any]], key: str) -> Any:
    if not d:
        return None
    return d.get(key) if isinstance(d, Mapping) else None


def _fmt_moic(v: Any) -> str:
    if v is None or v == "":
        return _DASH
    try:
        f = float(v)
    except (TypeError, ValueError):
        return _DASH
    if f != f:
        return _DASH
    return f"{f:.2f}x"


def _fmt_pct(v: Any) -> str:
    if v is None or v == "":
        return _DASH
    try:
        f = float(v)
    except (TypeError, ValueError):
        return _DASH
    if f != f:
        return _DASH
    return f"{f * 100:.1f}%"
