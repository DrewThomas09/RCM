"""Deals table — single-line rows with stage / EV / MOIC / IRR / covenant / drift.

Spec: docs/design-handoff/EDITORIAL_STYLE_PORT.md §6.5
Reference: docs/design-handoff/reference/04-command-center.html (deals section)

UNPAIRED block (per spec §6.5 — table is the data; no chart counterpart).
Each row is a click target that sets the focused deal context via
``?deal=<id>``. The focused row gets bg-tint + teal ● indicator.

See module-level conventions in _app_kpi_strip.py docstring (1-6).

Empty / sparse states (per Phase 2 review):
  - Empty portfolio → "No deals yet. Click 'Import Deal' above to add one."
  - Stage filter showing zero rows → "No <stage> deals" inline message;
    the table chrome stays visible so the partner sees the filter is
    in effect
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

import pandas as pd

from rcm_mc.ui._chartis_kit_editorial import (
    covenant_pill,
    number_maybe,
    stage_pill,
)


_STAGE_LABEL: Dict[str, str] = {
    "sourced": "Sourced", "ioi": "IOI", "loi": "LOI", "spa": "SPA",
    "closed": "Closed", "hold": "Hold", "exit": "Exit",
}


def _row_link(deal_id: str, *, selected_stage: Optional[str] = None) -> str:
    """Build the href for a row click — preserves stage filter."""
    parts = [f"deal={_html.escape(deal_id)}", "ui=v3"]
    if selected_stage:
        parts.append(f"stage={_html.escape(selected_stage)}")
    return "/app?" + "&".join(parts)


def _format_drift(value: Any) -> str:
    """Drift is a signed percent. Render with leading + or − and tone."""
    if value is None or pd.isna(value):
        return '<span style="color:var(--faint)">—</span>'
    try:
        f = float(value)
    except (TypeError, ValueError):
        return '<span style="color:var(--faint)">—</span>'
    if f < -10:
        tone = "red"
    elif f < 0:
        tone = "amber"
    else:
        tone = "green"
    return number_maybe(f, format="drift", tone=tone)


def _row_html(
    row: pd.Series,
    *,
    is_focused: bool,
    selected_stage: Optional[str],
) -> str:
    deal_id = str(row.get("deal_id") or "")
    name = str(row.get("name") or row.get("deal_name") or "")
    stage = str(row.get("stage") or "")
    ev = row.get("entry_ev")
    moic = row.get("moic")
    irr = row.get("irr")
    cov = str(row.get("covenant_status") or "")
    drift = row.get("drift_pct")
    headline = str(row.get("headline") or "")

    cls = "focused" if is_focused else ""
    href = _row_link(deal_id, selected_stage=selected_stage)
    # Convention: each cell is wrapped in <a> so the entire row is
    # click-targetable. Single anchor span across cells would require
    # display:contents on <a> which is shaky in older browsers.
    a = lambda inner: (  # noqa: E731 — terse closure for repeated wrap
        f'<a href="{href}">{inner}</a>'
    )

    return (
        f'<tr class="{cls}">'
        f'<td>{a(f"<span class=\"id\">{_html.escape(deal_id)}</span>"
               f"<span class=\"name\">{_html.escape(name)}</span>")}</td>'
        f'<td>{a(stage_pill(_STAGE_LABEL.get(stage, stage.title())))}</td>'
        f'<td class="r">{a(number_maybe(ev, format="ev"))}</td>'
        f'<td class="r">{a(number_maybe(moic, format="moic"))}</td>'
        f'<td class="r">{a(number_maybe(irr, format="pct"))}</td>'
        f'<td>{a(covenant_pill(cov.upper() if cov else ""))}</td>'
        f'<td class="r">{a(_format_drift(drift))}</td>'
        f'<td>{a(_html.escape(headline))}</td>'
        '</tr>'
    )


def render_deals_table(
    deals_df: pd.DataFrame,
    *,
    focused_deal_id: Optional[str] = None,
    selected_stage: Optional[str] = None,
) -> str:
    """Render the deals table — unpaired (per spec §6.5).

    Args:
        deals_df: Output of ``latest_per_deal(store)``. Caller filters
            by stage if needed (commit 9 orchestrator handles that).
        focused_deal_id: Currently-focused deal from ``?deal=<id>``.
        selected_stage: Active stage filter from ``?stage=<id>``.
            Echoed into row links so the focused-deal click preserves
            the filter.

    Returns:
        Complete <table>…</table> wrapped in a stand-alone div with
        the .app-deals-table chrome (header + body + empty-state if
        applicable).
    """
    if deals_df is None or deals_df.empty:
        if selected_stage:
            empty_msg = (
                f"No {_html.escape(selected_stage)} deals — "
                '<a href="/app?ui=v3" style="color:var(--teal-deep);'
                'text-decoration:underline">clear filter</a>'
            )
        else:
            empty_msg = (
                'No deals yet. <a href="/import" style="color:var(--teal-deep);'
                'text-decoration:underline">Add a deal</a> to populate.'
            )
        return (
            '<table class="app-deals-table">'
            '<thead><tr>'
            '<th>Deal</th><th>Stage</th><th class="r">EV</th>'
            '<th class="r">MOIC</th><th class="r">IRR</th>'
            '<th>Covenant</th><th class="r">Drift</th>'
            '<th>Headline</th>'
            '</tr></thead>'
            '<tbody><tr><td colspan="8">'
            f'<div class="empty">{empty_msg}</div>'
            '</td></tr></tbody>'
            '</table>'
        )

    rows: List[str] = []
    for _, row in deals_df.iterrows():
        deal_id = str(row.get("deal_id") or "")
        is_focused = (deal_id == focused_deal_id)
        rows.append(_row_html(
            row, is_focused=is_focused, selected_stage=selected_stage,
        ))

    return (
        '<table class="app-deals-table">'
        '<thead><tr>'
        '<th>Deal</th><th>Stage</th><th class="r">EV</th>'
        '<th class="r">MOIC</th><th class="r">IRR</th>'
        '<th>Covenant</th><th class="r">Drift</th>'
        '<th>Headline</th>'
        '</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody>'
        '</table>'
    )
