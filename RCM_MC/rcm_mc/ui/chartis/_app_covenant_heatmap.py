"""Covenant heatmap — 6 covenants × 8 quarters + paired state-counts table.

Spec: docs/design-handoff/EDITORIAL_STYLE_PORT.md §6.7
Reference: docs/design-handoff/reference/04-command-center.html (covenants section)

Per-deal heatmap. Each cell colored by ``safe`` / ``watch`` / ``trip``
band backed by the deal's underlying metric. Trend column on the
right shows movement from Q-1 → Q.

──────────────────────────────────────────────────────────────────────
Phase 3 commit 7: HONEST PARTIAL WIRING (per Q3.2 + Decision C1)
──────────────────────────────────────────────────────────────────────

The data-model gap surfaced during Phase 3 inventory:
``deal_snapshots`` schema only carries 1 of the 6 spec covenants —
``covenant_leverage`` (Net Leverage) + ``covenant_status`` (a single
band string). The other 5 spec covenants (Interest Coverage, Days
Cash on Hand, EBITDA / Plan, Denial Rate, A/R Days) have no per-
quarter columns in the DB.

Phase 3 wires the 1 row that has real data; the other 5 stay as `—`
cells with a footnote explaining what's tracked vs. what isn't.

Why this over synthesizing the missing 5 from related metrics:

  A demo is the wrong place to invent data. Five honest "—" cells
  with a clear footnote communicate trustworthiness, not
  incompleteness. Synthesizing covenant numbers from
  ``observed_metrics`` would let a partner make a decision based on
  a derived "Coverage Ratio" they thought was real, then later
  ask "where did that come from?" — that's a credibility-ending
  moment.

Q4.5 (registered in commit 11 of UI_REWORK_PLAN.md) tracks the
schema work: add ``covenant_metrics`` table or extend
``deal_snapshots`` with named covenant columns.

Justification for taking ``store`` directly (per Convention #1):

  Covenant cell derivation requires per-quarter snapshot lookups
  for the focused deal. Pre-computing this in the orchestrator
  would mean fetching ALL deals' quarterly snapshots even when
  only one deal is focused — wasted I/O. The narrow
  per-focused-deal query pattern is the right shape for this
  helper.

See module-level conventions in _app_kpi_strip.py docstring (1-6).

Empty / sparse states:
  - No focused deal → grid hidden; eyebrow shows
    "Select a deal in the table above to populate."
  - Pre-snapshot deal (zero deal_snapshots rows) → 6×8 grid with
    all `—` cells + eyebrow "Awaiting first quarterly snapshot."
  - Net Leverage row populates with real bands when 1+ snapshots
    exist; the other 5 rows always render `—` until the schema
    grows (Q4.5).
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


# Net Leverage band thresholds. Conservative defaults per spec §6.7
# (≤ 6.5x trip floor). Watch zone is 0.5x of cushion below trip.
# Per-deal overrides via covenant_thresholds() — Phase 3 ships
# spec defaults; Q4.5 wires per-deal config when the schema grows.
_NET_LEVERAGE_TRIP = 6.5
_NET_LEVERAGE_WATCH = 6.0


def _band_for_net_leverage(value: Optional[float]) -> Tuple[str, str]:
    """Map a net-leverage ratio to (band, label) for a heatmap cell.

    Returns ("empty", "—") for None/missing. Otherwise:
      ratio ≤ 6.0x → safe
      6.0x <  ratio ≤ 6.5x → watch
      ratio > 6.5x → trip
    """
    if value is None:
        return ("empty", "—")
    try:
        v = float(value)
    except (TypeError, ValueError):
        return ("empty", "—")
    label = f"{v:.1f}x"
    if v <= _NET_LEVERAGE_WATCH:
        return ("safe", label)
    if v <= _NET_LEVERAGE_TRIP:
        return ("watch", label)
    return ("trip", label)


def _quarter_label_from_iso(iso_str: str) -> str:
    """Compress an ISO timestamp like '2026-04-15T...' into 'Q2'26'.

    Defensive — bad inputs fall back to the raw string. Phase 3 keeps
    this helper local; if other helpers need quarter labels Phase 4
    can promote it to infra/.
    """
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        q = (dt.month - 1) // 3 + 1
        return f"Q{q}'{dt.year % 100:02d}"
    except Exception:  # noqa: BLE001 — bad input → fall back
        return (iso_str[:7] if iso_str else "—")


def _fetch_leverage_history(
    store: PortfolioStore,
    deal_id: str,
) -> List[Tuple[str, Optional[float]]]:
    """Last 8 quarterly net-leverage points for the focused deal.

    Reads from ``deal_snapshots.covenant_leverage`` ordered by
    ``created_at`` DESC, takes the 8 most recent, then re-orders
    chronologically (oldest → newest) so the heatmap reads
    left-to-right in time order.

    Returns:
        List of (quarter_label, ratio_or_None) — exactly 8 entries
        when 8+ snapshots exist; fewer entries when the deal has
        less history. Caller pads with empties if fewer than 8.
    """
    try:
        with store.connect() as con:
            rows = con.execute(
                """
                SELECT created_at, covenant_leverage
                  FROM deal_snapshots
                 WHERE deal_id = ?
                 ORDER BY created_at DESC
                 LIMIT 8
                """,
                (deal_id,),
            ).fetchall()
    except Exception:  # noqa: BLE001 — table may not exist
        return []

    # Re-order chronologically and unpack
    history: List[Tuple[str, Optional[float]]] = []
    for row in reversed(list(rows)):
        created_at = row[0] if not hasattr(row, "keys") else row["created_at"]
        cov_lev = row[1] if not hasattr(row, "keys") else row["covenant_leverage"]
        history.append((
            _quarter_label_from_iso(str(created_at) if created_at else ""),
            float(cov_lev) if cov_lev is not None else None,
        ))
    return history


def covenant_grid(
    store: PortfolioStore,
    deal_id: str,
) -> List[Dict[str, Any]]:
    """Derive the 6-covenant × 8-quarter grid for a focused deal.

    Q4.5 expansion (2026-04-27): all 6 covenants now read from the
    new ``covenant_metrics`` table via ``list_covenant_history``.
    Net Leverage retains its legacy ``deal_snapshots.covenant_leverage``
    fallback for deals migrated pre-Q4.5 — when no covenant_metrics
    rows exist for Net Leverage, the legacy column wins. New writes
    must go to covenant_metrics; the legacy column is read-only.

    Returns:
        List of 6 dicts (one per covenant) shaped:
            {
              "name": str,
              "sub": str (threshold description),
              "cells": List[Tuple[band, label]] — 8 entries, band in
                       {"safe", "watch", "trip", "empty"},
              "trend": str (e.g. "+0.2x" or "—"),
              "wired": bool (True when ≥1 cell in cells is non-empty),
            }
    """
    from rcm_mc.portfolio.covenant_metrics import (
        band_for_metric, format_value, list_covenant_history,
    )

    rows: List[Dict[str, Any]] = []
    for cov in _COVENANTS:
        name = cov["name"]
        history = list_covenant_history(store, deal_id, name, limit=8)

        # Legacy fallback: pre-Q4.5 deals stored Net Leverage in
        # deal_snapshots.covenant_leverage. If no covenant_metrics
        # rows exist for this covenant, fall back to that column.
        if not history and name == "Net Leverage":
            legacy = _fetch_leverage_history(store, deal_id)
            if legacy:
                cells: List[Tuple[str, str]] = []
                if len(legacy) < 8:
                    cells.extend([("empty", "—")] * (8 - len(legacy)))
                for _, ratio in legacy:
                    cells.append(_band_for_net_leverage(ratio))
                nonempty = [r for _, r in legacy if r is not None]
                trend = "—"
                if len(nonempty) >= 2:
                    delta = nonempty[-1] - nonempty[-2]
                    sign = "+" if delta >= 0 else ""
                    trend = f"{sign}{delta:.1f}x"
                rows.append({
                    "name": name, "sub": cov["sub"],
                    "cells": cells, "trend": trend, "wired": True,
                })
                continue

        if not history:
            rows.append({
                "name": name, "sub": cov["sub"],
                "cells": [("empty", "—") for _ in range(8)],
                "trend": "—", "wired": False,
            })
            continue

        # Q4.5 path: render from covenant_metrics history
        cells: List[Tuple[str, str]] = []
        if len(history) < 8:
            cells.extend([("empty", "—")] * (8 - len(history)))
        for m in history:
            band = band_for_metric(
                m.value, m.threshold, m.watch_threshold, m.direction,
            )
            cells.append((band, format_value(m.value, name)))
        # Trend: latest two non-empty values
        nonempty_vals = [m.value for m in history if m.value is not None]
        trend = "—"
        if len(nonempty_vals) >= 2:
            delta = nonempty_vals[-1] - nonempty_vals[-2]
            sign = "+" if delta >= 0 else ""
            # Format the delta in the covenant's natural unit
            if name in ("Net Leverage", "Interest Coverage"):
                trend = f"{sign}{delta:.1f}x"
            elif name in ("Days Cash on Hand", "Days in A/R"):
                trend = f"{sign}{delta:.0f}d"
            elif name in ("EBITDA / Plan", "Denial Rate"):
                trend = f"{sign}{delta * 100:.1f}%"
            else:
                trend = f"{sign}{delta:.2f}"
        rows.append({
            "name": name, "sub": cov["sub"],
            "cells": cells, "trend": trend, "wired": True,
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

    # Determine quarter labels: Net Leverage row's history if available,
    # else placeholder quarters. Same labels apply to every row (the
    # heatmap is a single time axis across all covenants).
    history = _fetch_leverage_history(store, deal_id)
    if history:
        # Pad-left with placeholder quarters when fewer than 8 snapshots
        actual_labels = [q for q, _ in history]
        if len(actual_labels) < 8:
            quarters = (
                _PLACEHOLDER_QUARTERS[: 8 - len(actual_labels)]
                + actual_labels
            )
        else:
            quarters = actual_labels
    else:
        quarters = _PLACEHOLDER_QUARTERS

    # Pre-snapshot detection: every cell is empty (no Net Leverage data
    # AND the other 5 rows are inherently empty in Phase 3). Eyebrow
    # surfaces this distinctly from the "5 of 6 not tracked" footnote.
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

    # Q4.5 footnote — surface the partial-wiring honestly. Counts the
    # "wired" rows so the copy stays accurate if Phase 4 adds the
    # missing covenants one at a time.
    wired_count = sum(1 for r in rows if r.get("wired"))
    total_count = len(rows)
    footnote = ""
    if wired_count < total_count and not all_empty:
        unwired_count = total_count - wired_count
        footnote = (
            '<div class="micro" style="color:var(--muted);'
            'padding:1rem 0 .5rem;font-style:italic;">'
            f'{wired_count} of {total_count} covenants tracked '
            '(Net Leverage). Remaining covenants render `—` until '
            'the schema grows — see Q4.5 in <code style="font-style:normal">'
            'docs/UI_REWORK_PLAN.md</code>.'
            '</div>'
        )

    viz_html = (
        f'{eyebrow}'
        f'{_render_heat_grid(rows, quarters=quarters)}'
        f'{footnote}'
    )

    return pair_block(
        viz_html,
        label="COVENANT BANDS · 6 × 8Q",
        source="deal_snapshots",
        data_table=_render_state_counts_table(rows),
    )
