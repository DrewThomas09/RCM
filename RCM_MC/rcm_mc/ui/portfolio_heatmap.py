"""Portfolio health heatmap (Prompt 36).

Route: ``GET /portfolio/heatmap``. Rows = deals, columns = top-8
metrics. Cells coloured by the metric's percentile rank vs the
comparable cohort. Trend arrows from sequential analysis runs.
Portfolio summary row at the bottom.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional

from ..analysis.packet import DealAnalysisPacket


_TOP_METRICS = [
    "denial_rate", "final_denial_rate", "days_in_ar", "ar_over_90_pct",
    "net_collection_rate", "clean_claim_rate", "cost_to_collect",
    "case_mix_index",
]

_PALETTE = {
    "good": "#10b981",
    "neutral": "#f59e0b",
    "bad": "#ef4444",
    "bg": "#0a0e17",
    "panel": "#111827",
    "border": "#1e293b",
    "text": "#e2e8f0",
    "dim": "#94a3b8",
}

_LOWER_IS_BETTER = frozenset({
    "denial_rate", "final_denial_rate", "days_in_ar", "ar_over_90_pct",
    "cost_to_collect",
})


def _esc(s: Any) -> str:
    return html.escape("" if s is None else str(s))


def _cell_color(metric: str, percentile: Optional[float]) -> str:
    """Green if the hospital is at a "good" percentile, red if bad.

    "Good" depends on direction: lower-is-better metrics are green
    at low percentiles and red at high. Vice versa for higher-is-
    better metrics. ``None`` → grey (no data).
    """
    if percentile is None:
        return _PALETTE["dim"]
    lower = metric in _LOWER_IS_BETTER
    if lower:
        if percentile < 0.3:
            return _PALETTE["good"]
        if percentile > 0.7:
            return _PALETTE["bad"]
    else:
        if percentile > 0.7:
            return _PALETTE["good"]
        if percentile < 0.3:
            return _PALETTE["bad"]
    return _PALETTE["neutral"]


def _trend_arrow(
    metric: str, deltas: Optional[Dict[str, float]],
) -> str:
    """Tiny arrow from the portfolio_monitor delta."""
    if not deltas or metric not in deltas:
        return ""
    d = deltas[metric]
    lower = metric in _LOWER_IS_BETTER
    improving = (d < 0) if lower else (d > 0)
    arrow = "↑" if improving else "↓"
    color = _PALETTE["good"] if improving else _PALETTE["bad"]
    return f'<span style="color:{color};margin-left:2px;">{arrow}</span>'


def render_heatmap(
    packets: List[DealAnalysisPacket],
    *,
    deltas: Optional[Dict[str, Dict[str, float]]] = None,
) -> str:
    """Full-page heatmap HTML.

    ``deltas`` maps ``deal_id`` → ``{metric: value_change}`` from
    :func:`rcm_mc.portfolio.portfolio_monitor.compute_deltas`.
    """
    from ._chartis_kit import chartis_shell

    if not packets:
        return chartis_shell(
            '<div class="cad-card"><p style="color:var(--cad-text3);">No deals to display. '
            '<a href="/import" style="color:var(--cad-link);">Create your first deal &rarr;</a></p></div>',
            "Portfolio Heatmap",
            subtitle="No deals yet",
        )

    deltas = deltas or {}

    header = "".join(
        f'<th>{_esc(m.replace("_", " "))}</th>' for m in _TOP_METRICS
    )
    rows_html: List[str] = []
    for p in packets:
        cells: List[str] = []
        profile = p.rcm_profile or {}
        deal_deltas = deltas.get(p.deal_id) or {}
        for m in _TOP_METRICS:
            pm = profile.get(m)
            if pm is None:
                cells.append(
                    f'<td style="background:{_PALETTE["panel"]};'
                    f'color:{_PALETTE["dim"]};">—</td>'
                )
                continue
            pct = pm.benchmark_percentile
            bg = _cell_color(m, pct)
            val = f"{pm.value:.1f}"
            arrow = _trend_arrow(m, deal_deltas)
            cells.append(
                f'<td style="background:{bg}20;color:{_PALETTE["text"]};">'
                f'{val}{arrow}</td>'
            )
        grade = (p.completeness.grade if p.completeness else "—")
        grade_color = {
            "A": _PALETTE["good"], "B": "#3b82f6",
            "C": _PALETTE["neutral"], "D": _PALETTE["bad"],
        }.get(grade, _PALETTE["dim"])
        rows_html.append(
            f'<tr>'
            f'<td><a href="/analysis/{_esc(p.deal_id)}" '
            f'style="color:{_PALETTE["text"]};text-decoration:none;">'
            f'{_esc(p.deal_name or p.deal_id)}</a></td>'
            f'<td style="color:{grade_color};font-weight:600;">{grade}</td>'
            + "".join(cells) + '</tr>'
        )

    css = """
    .heatmap-table { width:100%; border-collapse:collapse; font-size:12px;
      font-family:"JetBrains Mono",monospace; }
    .heatmap-table th { background:#111827; color:#94a3b8; padding:6px 8px;
      text-align:center; text-transform:uppercase; font-size:10px;
      letter-spacing:.04em; border-bottom:1px solid #1e293b; }
    .heatmap-table td { padding:6px 8px; text-align:center;
      border-bottom:1px solid #1e293b; }
    .heatmap-table td:first-child { text-align:left; }
    """
    table = (
        '<table class="heatmap-table">'
        f'<thead><tr><th>Deal</th><th>Grade</th>{header}</tr></thead>'
        f'<tbody>{"".join(rows_html)}</tbody></table>'
    )
    body = f'<div class="cad-card">{table}</div>'
    return chartis_shell(body, "Portfolio Heatmap",
                    active_nav="/portfolio",
                    subtitle=f"{len(packets)} deals — cells coloured by percentile rank",
                    extra_css=css)
