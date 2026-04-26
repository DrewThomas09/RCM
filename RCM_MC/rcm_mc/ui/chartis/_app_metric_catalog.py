"""MetricCatalog — "Every number on this page" cross-reference block.

Direct port of the MetricCatalog component from cc-app.jsx. Renders 4
columns of metric:value pairs grouped by category (RETURNS / RCM DRAG /
COVENANTS / INITIATIVES). Each column has a header showing the category
name + a fund/deal-level badge. Each row is a label + a tabular-num value.

The numbers themselves are sourced from the rollup + focused-deal packet
that the /app page already fetches — this helper is purely presentational.

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
    focused_packet: Optional[Mapping[str, Any]] = None,
) -> str:
    """Render the 4-column metric catalog.

    Args:
        rollup: Output of portfolio_rollup() — used for fund-level metrics
            (Weighted MOIC / IRR / DPI / TVPI). When None, fund column shows
            "—" placeholders.
        focused_packet: Output of _resolve_focused_packet() — used for
            deal-level metrics (RCM drag, covenants, initiatives). When
            None, deal columns show "—".

    Returns:
        HTML string. Section header + 4-column catalog grid.
    """
    groups = _build_groups(rollup, focused_packet)
    cols_html = "".join(_render_col(g) for g in groups)
    return (
        '<div class="sect">'
        '<div>'
        '<div class="micro">METRIC CATALOG</div>'
        '<h2>Every number<br/>on this page</h2>'
        '</div>'
        '<p class="desc">Cross-reference of fund- and deal-level metrics '
        'with their visualization anchors below. Click any row to scroll '
        'to its source.</p>'
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
    focused: Optional[Mapping[str, Any]],
) -> Sequence[_Group]:
    """Pull values out of rollup + focused packet into the 4 groups.

    When data is missing, renders "—". This matches the "honest partial
    wiring" rule — show the row, footnote the gap, never fake numbers.
    """
    return [
        ("RETURNS", "fund", [
            ("Weighted MOIC", _fmt_moic(_get(rollup, "weighted_moic"))),
            ("Weighted IRR",  _fmt_pct(_get(rollup, "weighted_irr"))),
            ("DPI",           _fmt_moic(_get(rollup, "weighted_dpi"))),
            ("TVPI",          _fmt_moic(_get(rollup, "weighted_tvpi"))),
        ]),
        ("RCM DRAG", "deal", [
            ("Denial write-off",     _fmt_dollars(_packet_metric(focused, "denial_writeoff"))),
            ("DAR carry cost",       _fmt_dollars(_packet_metric(focused, "dar_carry_cost"))),
            ("Underpayment leakage", _fmt_dollars(_packet_metric(focused, "underpayment_leakage"))),
            ("Recovery cost",        _fmt_dollars(_packet_metric(focused, "recovery_cost"))),
        ]),
        ("COVENANTS", "deal", [
            ("Net leverage",     _fmt_covenant(focused, "net_leverage")),
            ("Interest coverage",_fmt_covenant(focused, "interest_coverage")),
            ("Days cash",        _fmt_covenant(focused, "days_cash")),
            ("EBITDA / Plan",    _fmt_covenant(focused, "ebitda_plan")),
        ]),
        ("INITIATIVES", "deal", [
            ("Coding & CDI",       _fmt_signed_pct(_initiative_variance(focused, "coding_cdi"))),
            ("Prior auth reform",  _fmt_signed_pct(_initiative_variance(focused, "prior_auth"))),
            ("Denials workflow",   _fmt_signed_pct(_initiative_variance(focused, "denials"))),
            ("Underpay recovery",  _fmt_signed_pct(_initiative_variance(focused, "underpay_recovery"))),
        ]),
    ]


# ── tiny extractors / formatters ─────────────────────────────────────

_DASH = "—"


def _get(d: Optional[Mapping[str, Any]], key: str) -> Any:
    if not d:
        return None
    return d.get(key) if isinstance(d, Mapping) else None


def _packet_metric(packet: Optional[Mapping[str, Any]], key: str) -> Any:
    """Fetch a per-metric impact dollar amount from the focused packet."""
    if not packet:
        return None
    impacts = packet.get("per_metric_impacts") if isinstance(packet, Mapping) else None
    if not isinstance(impacts, Mapping):
        return None
    return impacts.get(key)


def _initiative_variance(packet: Optional[Mapping[str, Any]], key: str) -> Any:
    """Fetch initiative variance fraction (e.g., -0.10 → -10.0%)."""
    if not packet:
        return None
    inits = packet.get("initiatives") if isinstance(packet, Mapping) else None
    if not isinstance(inits, Mapping):
        return None
    val = inits.get(key)
    return val if val is not None else None


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


def _fmt_signed_pct(v: Any) -> str:
    if v is None or v == "":
        return _DASH
    try:
        f = float(v)
    except (TypeError, ValueError):
        return _DASH
    if f != f:
        return _DASH
    sign = "+" if f >= 0 else ""
    return f"{sign}{f * 100:.1f}%"


def _fmt_dollars(v: Any) -> str:
    if v is None or v == "":
        return _DASH
    try:
        f = float(v)
    except (TypeError, ValueError):
        return _DASH
    if f != f:
        return _DASH
    af = abs(f)
    if af >= 1_000_000_000:
        return f"${f / 1_000_000_000:.1f}B".replace(".0B", "B")
    if af >= 1_000_000:
        return f"${f / 1_000_000:.1f}M".replace(".0M", "M")
    if af >= 1_000:
        return f"${f / 1_000:.1f}K".replace(".0K", "K")
    return f"${f:,.0f}"


def _fmt_covenant(packet: Optional[Mapping[str, Any]], metric: str) -> str:
    """Render '<value> · <band>' for a covenant metric, or '—'.

    Pulls from focused packet's covenant_status. Bands: SAFE/WATCH/TRIP.
    """
    if not packet:
        return _DASH
    covs = packet.get("covenants") if isinstance(packet, Mapping) else None
    if not isinstance(covs, Mapping):
        return _DASH
    entry = covs.get(metric)
    if not isinstance(entry, Mapping):
        return _DASH
    val = entry.get("value")
    band = entry.get("band") or ""
    if val is None:
        return _DASH
    try:
        f = float(val)
    except (TypeError, ValueError):
        return _DASH
    if f != f:
        return _DASH
    # Format value per metric type — leverage = "x", coverage = "x",
    # days_cash = "d", ebitda_plan = "%"
    if metric == "days_cash":
        v_str = f"{f:.0f}d"
    elif metric == "ebitda_plan":
        v_str = f"{f * 100:.0f}%" if f <= 1 else f"{f:.0f}%"
    else:
        v_str = f"{f:.1f}x"
    return f"{v_str} · {band.upper()}" if band else v_str
