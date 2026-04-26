"""Initiative tracker — variance-sorted rows + paired variance-dot-plot.

Spec: docs/design-handoff/EDITORIAL_STYLE_PORT.md §6.9
Reference: docs/design-handoff/reference/04-command-center.html (initiative section)

Variance-sorted rows showing status icon (✓ / ! / ✕), name, deal, actual,
variance %, progress bar. Paired with a variance dot-plot SVG (dots on
−30% … +30% axis) + playbook-signal counts.

Justification for taking ``store`` directly (per Convention #1):

  Initiative variance computation requires per-deal initiative
  actuals + plan derivation (initiative_variance_report). Pre-computing
  for every deal in the orchestrator would mean N queries when only
  a focused subset is rendered. The narrow per-focused-deal query
  pattern is the right shape for this helper.

See module-level conventions in _app_kpi_strip.py docstring (1-6).

Empty / sparse states (per Phase 2 review):
  - No focused deal → cross-portfolio playbook signals (top variances
    across deals). Phase 2 stub: shows empty-state pointing to thesis
    pipeline since cross-portfolio aggregation is Phase 3 work.
  - Focused deal with zero initiatives → "No initiatives recorded yet
    for this deal" + link to add via /diligence/thesis-pipeline.

# TODO(phase 3): cross-portfolio playbook-signal aggregation when
# no deal is focused (top variances across all held deals).
# Phase 2 ships the chrome with placeholder empty-state.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

import pandas as pd

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.ui._chartis_kit_editorial import number_maybe, pair_block


def _status_icon(variance: float) -> tuple[str, str]:
    """Return (icon, css-class) for a variance percentage.

    Conventions: ≤−10% → fail (✕), −10% to +5% → warn (!), >+5% → ok (✓).
    The "ok" threshold being positive is intentional: an initiative
    that's only meeting plan isn't ahead, it's flat. Spec wants the ✓
    reserved for genuinely-ahead lifts.
    """
    if variance <= -10:
        return ("✕", "fail")
    if variance < 5:
        return ("!", "warn")
    return ("✓", "ok")


def _variance_color(variance: float) -> str:
    if variance <= -10:
        return "var(--red)"
    if variance < 5:
        return "var(--amber)"
    return "var(--green)"


def _fetch_initiative_rows(
    store: PortfolioStore,
    deal_id: str,
) -> List[Dict[str, Any]]:
    """Pull initiative variance rows for a single deal.

    Returns:
        List of dicts: {name, deal, actual, variance, progress}.
        Empty list when no initiatives recorded.
    """
    try:
        from rcm_mc.rcm.initiative_tracking import initiative_variance_report
        df = initiative_variance_report(store, deal_id)
    except Exception:  # noqa: BLE001 — variance call may fail on partial data
        return []
    if df is None or df.empty:
        return []
    rows: List[Dict[str, Any]] = []
    for _, r in df.iterrows():
        try:
            actual = float(r.get("actual_cumulative_M") or 0.0)
            plan = float(r.get("plan_cumulative_M") or 0.0)
            variance_pct = (
                ((actual - plan) / plan * 100) if plan else 0.0
            )
            progress_pct = min(100, max(0, (actual / plan * 100) if plan else 0))
        except Exception:  # noqa: BLE001
            continue
        rows.append({
            "name": str(r.get("initiative_name") or r.get("initiative") or ""),
            "deal": deal_id,
            "actual": actual,
            "variance": variance_pct,
            "progress": progress_pct,
        })
    # Sort by absolute variance (worst first) — partner reads top-down
    rows.sort(key=lambda r: -abs(r["variance"]))
    return rows


def _render_init_rows(rows: List[Dict[str, Any]]) -> str:
    head = (
        '<div class="app-init-row head">'
        '<div></div>'
        '<div>Initiative</div>'
        '<div>Deal</div>'
        '<div>Actual</div>'
        '<div>Variance</div>'
        '<div>Progress</div>'
        '</div>'
    )
    if not rows:
        return head + (
            '<div class="app-init-empty">'
            'No initiatives recorded yet. '
            '<a href="/diligence/thesis-pipeline" '
            'style="color:var(--teal-deep);text-decoration:underline">'
            'Run the analysis pipeline</a> to populate.'
            '</div>'
        )
    body = "".join(
        _row_html(r) for r in rows
    )
    return head + body


def _row_html(r: Dict[str, Any]) -> str:
    icon, icon_cls = _status_icon(r["variance"])
    var_color = _variance_color(r["variance"])
    sign = "+" if r["variance"] >= 0 else ""
    actual_html = number_maybe(r["actual"], format="ev")
    return (
        '<div class="app-init-row">'
        f'<div class="ico {icon_cls}">{icon}</div>'
        f'<div class="name">{_html.escape(r["name"])}</div>'
        f'<div class="deal">{_html.escape(r["deal"])}</div>'
        f'<div class="actual">{actual_html}</div>'
        f'<div class="variance" style="color:{var_color}">'
        f'{sign}{r["variance"]:.1f}%</div>'
        f'<div class="progress"><div class="fill" '
        f'style="width:{r["progress"]:.0f}%"></div></div>'
        '</div>'
    )


def _render_variance_dot_plot(rows: List[Dict[str, Any]]) -> str:
    """Mini SVG: dots on a −30% … +30% axis."""
    if not rows:
        return ""
    w, h = 220, 80
    axis_y = h - 20
    # Map variance to x position
    def x_for(variance: float) -> float:
        clamped = max(-30, min(30, variance))
        return 10 + ((clamped + 30) / 60) * (w - 20)

    dots = "".join(
        f'<circle cx="{x_for(r["variance"]):.1f}" cy="{axis_y - 12}" '
        f'r="3" fill="{_variance_color(r["variance"])}" '
        f'opacity="0.7"/>'
        for r in rows
    )
    # Axis line + tick marks at -30, -15, 0, +15, +30
    ticks = ""
    for v in (-30, -15, 0, 15, 30):
        tx = x_for(v)
        ticks += (
            f'<line x1="{tx:.1f}" y1="{axis_y - 4}" '
            f'x2="{tx:.1f}" y2="{axis_y + 4}" '
            f'stroke="var(--border-strong)" stroke-width="1"/>'
            f'<text x="{tx:.1f}" y="{h - 4}" font-size="9" '
            f'text-anchor="middle" fill="var(--muted)" '
            f'font-family="JetBrains Mono, monospace">'
            f'{"+" if v > 0 else ""}{v}%</text>'
        )
    return (
        f'<svg viewBox="0 0 {w} {h}" style="width:100%;height:auto;'
        f'display:block">'
        f'<line x1="10" y1="{axis_y}" x2="{w - 10}" y2="{axis_y}" '
        f'stroke="var(--border-strong)" stroke-width="1"/>'
        f'{ticks}{dots}</svg>'
    )


def _render_signal_counts_table(rows: List[Dict[str, Any]]) -> str:
    """Paired right-side table: variance-band counts."""
    behind = sum(1 for r in rows if r["variance"] <= -10)
    watch = sum(1 for r in rows if -10 < r["variance"] < 5)
    ahead = sum(1 for r in rows if r["variance"] >= 5)
    body = (
        f'<tr><td class="lbl">Behind plan (≤ −10%)</td>'
        f'<td class="r">{behind}</td></tr>'
        f'<tr><td class="lbl">Watch (−10% to +5%)</td>'
        f'<td class="r">{watch}</td></tr>'
        f'<tr><td class="lbl">Ahead (≥ +5%)</td>'
        f'<td class="r">{ahead}</td></tr>'
    )
    plot = _render_variance_dot_plot(rows)
    plot_block = (
        f'<div style="padding:1rem 0 .5rem">{plot}</div>'
        if plot else ""
    )
    return (
        f'{plot_block}'
        '<table>'
        '<thead><tr><th>Signal</th><th class="r">Count</th></tr></thead>'
        f'<tbody>{body}</tbody>'
        '</table>'
    )


def _render_cross_portfolio_rows(df: pd.DataFrame) -> str:
    """Render the cross-portfolio playbook-signals view.

    Per Phase 3 commit 8: when no deal is focused, the initiative
    tracker pivots to "top variances across the portfolio" — one
    row per initiative (NOT per deal-initiative pair), tagged as
    a "playbook gap" when mean variance ≤ -10% across ≥ 2 deals.
    """
    head = (
        '<div class="app-init-row head">'
        '<div></div>'
        '<div>Initiative</div>'
        '<div>Deals</div>'
        '<div>Total $</div>'
        '<div>Mean variance</div>'
        '<div>Signal</div>'
        '</div>'
    )
    if df.empty:
        return head + (
            '<div class="app-init-empty">'
            'No initiative actuals recorded in the trailing 4 quarters. '
            '<a href="/diligence/thesis-pipeline" '
            'style="color:var(--teal-deep);text-decoration:underline">'
            'Run the analysis pipeline</a> to populate.'
            '</div>'
        )
    body_rows: List[str] = []
    for _, r in df.iterrows():
        var = float(r["mean_variance_pct"]) * 100
        icon, icon_cls = _status_icon(var)
        var_color = _variance_color(var)
        sign = "+" if var >= 0 else ""
        actual_html = number_maybe(float(r["total_actual_M"]), format="ev")
        gap_marker = (
            '<span class="pill amber">PLAYBOOK GAP</span>'
            if bool(r.get("is_playbook_gap")) else ""
        )
        body_rows.append(
            '<div class="app-init-row">'
            f'<div class="ico {icon_cls}">{icon}</div>'
            f'<div class="name">{_html.escape(str(r["initiative_name"]))}</div>'
            f'<div class="deal">{int(r["n_deals"])} deal'
            f'{"s" if int(r["n_deals"]) != 1 else ""}</div>'
            f'<div class="actual">{actual_html}</div>'
            f'<div class="variance" style="color:{var_color}">'
            f'{sign}{var:.1f}%</div>'
            f'<div>{gap_marker}</div>'
            '</div>'
        )
    return head + "".join(body_rows)


def render_initiative_tracker(
    store: PortfolioStore,
    deal_id: Optional[str],
) -> str:
    """Variance-sorted initiative rows + paired variance-dot-plot.

    Args:
        store: PortfolioStore handle. (Per Convention #1: justified
            because initiative variance computation needs per-deal
            actuals + plan derivation, narrow query that doesn't batch.)
        deal_id: Focused-deal id from ``?deal=<id>``. None → cross-
            portfolio playbook-signals view (Phase 3 commit 8).
    """
    if not deal_id:
        # Cross-portfolio mode (Phase 3 wired). Default trailing 4Q
        # window per C3 push-back — no-window default surfaces stale
        # signals as current playbook gaps.
        try:
            from rcm_mc.rcm.initiative_tracking import (
                cross_portfolio_initiative_variance,
            )
            xp_df = cross_portfolio_initiative_variance(store)
        except Exception:  # noqa: BLE001 — block must not break the page
            xp_df = pd.DataFrame()

        # Build dot-plot data from the cross-portfolio rows
        if not xp_df.empty:
            dot_rows = [
                {"variance": float(r["mean_variance_pct"]) * 100,
                 "name": str(r["initiative_name"])}
                for _, r in xp_df.iterrows()
            ]
        else:
            dot_rows = []

        viz_html = (
            '<div class="app-init">'
            f'{_render_cross_portfolio_rows(xp_df)}'
            '</div>'
        )

        # Right-side paired counts: signal classification of the
        # cross-portfolio rows
        if xp_df.empty:
            counts_table = (
                '<table>'
                '<thead><tr><th>Signal</th><th class="r">Count</th></tr></thead>'
                '<tbody>'
                '<tr><td class="lbl">Playbook gap (≤ −10%, ≥2 deals)</td>'
                '<td class="r">—</td></tr>'
                '<tr><td class="lbl">Behind plan (single deal)</td>'
                '<td class="r">—</td></tr>'
                '<tr><td class="lbl">Ahead (≥ +5%)</td>'
                '<td class="r">—</td></tr>'
                '</tbody>'
                '</table>'
            )
        else:
            playbook = int(xp_df["is_playbook_gap"].sum())
            behind_single = int(
                ((xp_df["mean_variance_pct"] <= -0.10) &
                 (xp_df["n_deals"] == 1)).sum()
            )
            ahead = int((xp_df["mean_variance_pct"] >= 0.05).sum())
            plot = _render_variance_dot_plot(dot_rows) if dot_rows else ""
            plot_block = (
                f'<div style="padding:1rem 0 .5rem">{plot}</div>'
                if plot else ""
            )
            counts_table = (
                f'{plot_block}'
                '<table>'
                '<thead><tr><th>Signal</th><th class="r">Count</th></tr></thead>'
                '<tbody>'
                '<tr><td class="lbl">Playbook gap (≤ −10%, ≥2 deals)</td>'
                f'<td class="r">{playbook}</td></tr>'
                '<tr><td class="lbl">Behind plan (single deal)</td>'
                f'<td class="r">{behind_single}</td></tr>'
                '<tr><td class="lbl">Ahead (≥ +5%)</td>'
                f'<td class="r">{ahead}</td></tr>'
                '</tbody>'
                '</table>'
            )

        return pair_block(
            viz_html,
            label="CROSS-PORTFOLIO INITIATIVE VARIANCE · 4Q TRAIL",
            source="initiative_actuals",
            data_table=counts_table,
        )

    rows = _fetch_initiative_rows(store, deal_id)

    viz_html = (
        f'<div class="app-init">{_render_init_rows(rows)}</div>'
    )

    return pair_block(
        viz_html,
        label="INITIATIVE VARIANCE · SORTED ABS",
        source="initiative_actuals",
        data_table=_render_signal_counts_table(rows),
    )
