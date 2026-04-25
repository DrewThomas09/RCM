"""Covenant heatmap — 6 covenants × 8 quarters + paired state-counts table.

Spec: docs/design-handoff/EDITORIAL_STYLE_PORT.md §6.7
Reference: docs/design-handoff/reference/04-command-center.html (covenants section)

Per-deal heatmap. Each cell colored by ``safe`` / ``watch`` / ``trip`` band
backed by the deal's underlying metric (Net Leverage, Interest Coverage,
Days Cash, EBITDA / Plan, Denial Rate, A/R Days). Trend column on the
right shows movement from Q-1 → Q.

Justification for taking ``store`` directly (per Convention #1):

  This helper takes ``store`` because covenant cell derivation requires
  per-quarter snapshot lookups for the focused deal (8 quarters × 6
  metrics = up to 48 lookups). Pre-computing this in the orchestrator
  would mean fetching ALL deals' quarterly snapshots even when only
  one deal is focused — wasted I/O. The narrow per-focused-deal query
  pattern is the right shape for this helper.

See module-level conventions in _app_kpi_strip.py docstring (1-6).

Empty / sparse states (per Phase 2 review):
  - No focused deal → grid hidden; eyebrow shows
    "Select a deal in the table above to populate."
  - Pre-snapshot deal (zero quarterly rows) → 6×8 grid with all `—`
    cells + eyebrow "Awaiting first quarterly snapshot."
  - Partial data → known cells colored; missing cells render `—` in faint

# TODO(phase 3): wire covenant_grid() to real per-deal snapshot data.
# Phase 2 ships the chrome with placeholder `—` cells (the data shape
# exists in quarterly_snapshots; we're not deriving the bands yet).
# Activating real bands needs the threshold mapping per covenant
# (Net Leverage cap from deal_sim_inputs, Interest Coverage floor,
# etc.) which is per-deal config data not yet surfaced for v3.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional, Tuple

from rcm_mc.ui._chartis_kit_editorial import pair_block
from rcm_mc.portfolio.store import PortfolioStore


# 6 covenants × 8 quarters per spec §6.7. The covenant set + their
# threshold descriptions are documented in the spec; the threshold
# mapping itself (per-deal config) is wired in Phase 3.
_COVENANTS: List[Dict[str, str]] = [
    {"name": "Net Leverage",        "sub": "≤ 6.5x"},
    {"name": "Interest Coverage",   "sub": "≥ 2.0x"},
    {"name": "Days Cash on Hand",   "sub": "≥ 60 days"},
    {"name": "EBITDA / Plan",       "sub": "≥ 90%"},
    {"name": "Denial Rate",         "sub": "≤ 8.5%"},
    {"name": "Days in A/R",         "sub": "≤ 50 days"},
]

# 8 quarters of column labels — placeholder until real quarterly_snapshots
# wiring lands. Same shape as cc-data.jsx's PORTFOLIO.covenants.quarters.
_PLACEHOLDER_QUARTERS: List[str] = [
    "Q3'24", "Q4'24", "Q1'25", "Q2'25",
    "Q3'25", "Q4'25", "Q1'26", "Q2'26",
]


def covenant_grid(
    store: PortfolioStore,
    deal_id: str,
) -> List[Dict[str, Any]]:
    """Derive the 6-covenant × 8-quarter grid for a focused deal.

    Returns:
        List of 6 dicts (one per covenant) shaped:
            {
              "name": str,
              "sub": str (threshold description),
              "cells": List[Tuple[band, label]] — 8 entries, band in
                       {"safe", "watch", "trip", "empty"},
              "trend": str (e.g. "+0.2x" or "—"),
            }

    Phase 2 stub: returns 6 covenant rows with all-empty cells until
    the per-deal threshold mapping is wired. This keeps the heatmap
    chrome rendering correctly while flagging the unfinished derivation.
    See module-level # TODO(phase 3) — same comment lives there.
    """
    # TODO(phase 3): wire to quarterly_snapshots + per-deal thresholds.
    rows: List[Dict[str, Any]] = []
    for cov in _COVENANTS:
        rows.append({
            "name": cov["name"],
            "sub": cov["sub"],
            "cells": [("empty", "—") for _ in range(8)],
            "trend": "—",
        })
    return rows


def _render_state_counts_table(rows: List[Dict[str, Any]]) -> str:
    """Paired right-side table — count of safe/watch/trip per covenant."""
    body_rows: List[str] = []
    for row in rows:
        cells = row.get("cells", [])
        safe = sum(1 for band, _ in cells if band == "safe")
        watch = sum(1 for band, _ in cells if band == "watch")
        trip = sum(1 for band, _ in cells if band == "trip")
        body_rows.append(
            f'<tr><td class="lbl">{_html.escape(row["name"])}</td>'
            f'<td class="r">{safe}</td>'
            f'<td class="r">{watch}</td>'
            f'<td class="r">{trip}</td></tr>'
        )
    return (
        '<table>'
        '<thead><tr>'
        '<th>Covenant</th>'
        '<th class="r">Safe</th>'
        '<th class="r">Watch</th>'
        '<th class="r">Trip</th>'
        '</tr></thead>'
        f'<tbody>{"".join(body_rows)}</tbody>'
        '</table>'
    )


def _render_heat_grid(
    rows: List[Dict[str, Any]],
    *,
    quarters: List[str],
) -> str:
    """6×8 heatmap viz."""
    # Header row
    head_cells = "".join(
        f'<div class="cell">{_html.escape(q)}</div>'
        for q in quarters
    )
    head = (
        '<div class="row head">'
        '<div class="cell first">Covenant</div>'
        f'{head_cells}'
        '<div class="cell trend">Trend</div>'
        '</div>'
    )

    # Data rows
    data_rows: List[str] = []
    for row in rows:
        cells_html = "".join(
            f'<div class="cell {band}">{_html.escape(label)}</div>'
            for band, label in row["cells"]
        )
        data_rows.append(
            '<div class="row">'
            f'<div class="name">{_html.escape(row["name"])}'
            f'<span class="sub">{_html.escape(row["sub"])}</span></div>'
            f'{cells_html}'
            f'<div class="trend">{_html.escape(row["trend"])}</div>'
            '</div>'
        )

    return (
        '<div class="app-cov-heat">'
        f'{head}'
        f'{"".join(data_rows)}'
        '</div>'
    )


def render_covenant_heatmap(
    store: PortfolioStore,
    deal_id: Optional[str],
) -> str:
    """6-covenant × 8-quarter heatmap + paired state-counts table.

    Args:
        store: PortfolioStore handle. (Per Convention #1: justified
            because covenant cell derivation needs per-deal quarterly
            snapshot lookups, narrow query that doesn't batch.)
        deal_id: Focused-deal id from ``?deal=<id>``. None → renders
            empty-state eyebrow, no grid.

    Returns:
        Complete <div class="pair">…</div>.
    """
    # No focused deal — chrome with eyebrow only.
    if not deal_id:
        viz_html = (
            '<div class="micro" style="color:var(--muted);'
            'padding:.5rem 0 1rem;">Select a deal in the table above '
            'to populate the covenant heatmap.</div>'
            '<div class="app-cov-heat">'
            '<div class="empty-state">No deal focused.</div>'
            '</div>'
        )
        empty_table = (
            '<table>'
            '<thead><tr>'
            '<th>Covenant</th>'
            '<th class="r">Safe</th>'
            '<th class="r">Watch</th>'
            '<th class="r">Trip</th>'
            '</tr></thead>'
            '<tbody>'
            '<tr><td colspan="4" class="lbl" style="text-align:center;'
            'padding:1rem 0;font-style:italic;color:var(--muted);">'
            'No deal focused</td></tr>'
            '</tbody>'
            '</table>'
        )
        return pair_block(
            viz_html,
            label="COVENANT BANDS · 6 × 8Q",
            source="quarterly_snapshots",
            data_table=empty_table,
        )

    rows = covenant_grid(store, deal_id)

    # Pre-snapshot detection: if every cell is empty, show the
    # "Awaiting first quarterly snapshot" eyebrow.
    all_empty = all(
        all(band == "empty" for band, _ in row["cells"])
        for row in rows
    )
    eyebrow = ""
    if all_empty:
        eyebrow = (
            '<div class="micro" style="color:var(--muted);'
            'padding:.5rem 0 1rem;">Awaiting first quarterly snapshot '
            f'for <span class="mono" style="color:var(--teal-deep)">'
            f'{_html.escape(deal_id)}</span>. Run an analysis to populate.</div>'
        )

    viz_html = (
        f'{eyebrow}'
        f'{_render_heat_grid(rows, quarters=_PLACEHOLDER_QUARTERS)}'
    )

    return pair_block(
        viz_html,
        label="COVENANT BANDS · 6 × 8Q",
        source="quarterly_snapshots",
        data_table=_render_state_counts_table(rows),
    )
