"""Pipeline funnel + paired conversion table.

Spec: docs/design-handoff/EDITORIAL_STYLE_PORT.md §6.4
Reference: docs/design-handoff/reference/04-command-center.html (pipeline section)

7 stages (Sourced → Hold → Exit) per ``DEAL_STAGES``. "Screened" from
``cc-data.jsx`` is dropped (per Phase 2 conflict C1) — the DB doesn't
track it. Each stage is a clickable link that filters the deals table
beneath via ``?stage=<id>``. Bar widths are stage-relative; conversion
in the paired table is to-prior-stage.

See module-level conventions in _app_kpi_strip.py docstring (1-6).

Empty / sparse states (per Phase 2 review):
  - Stages with zero deals render the bar at 0px width with the stage
    name only (no count badge).
  - Empty fund (rollup deal_count == 0) → 7 zero-bars + "Add a deal
    to populate the funnel." eyebrow with link to /import
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional, Tuple

from rcm_mc.portfolio.portfolio_snapshots import DEAL_STAGES
from rcm_mc.ui._chartis_kit_editorial import pair_block


# Stage display labels — DB stores lowercase; UI capitalizes per spec.
_STAGE_LABEL: Dict[str, str] = {
    "sourced": "Sourced",
    "ioi": "IOI",
    "loi": "LOI",
    "spa": "SPA",
    "closed": "Closed",
    "hold": "Hold",
    "exit": "Exit",
}


def _conversion_rows(
    funnel: Dict[str, int],
) -> List[Tuple[str, str, str]]:
    """Compute (label, count, conversion%) rows for the paired table.

    Conversion is to-prior-stage (deals at stage N / deals at stage N-1).
    First stage has no prior, renders ``—``.
    """
    rows: List[Tuple[str, str, str]] = []
    prior: Optional[int] = None
    for stage in DEAL_STAGES:
        n = int(funnel.get(stage, 0))
        if prior is None:
            conv = "—"
        elif prior == 0:
            conv = "—"
        else:
            conv = f"{(n / prior) * 100:.0f}%"
        rows.append((_STAGE_LABEL.get(stage, stage.title()), str(n), conv))
        prior = n
    return rows


def _render_conversion_table(funnel: Dict[str, int]) -> str:
    rows = _conversion_rows(funnel)
    body = "".join(
        f'<tr><td class="lbl">{_html.escape(label)}</td>'
        f'<td class="r">{_html.escape(count)}</td>'
        f'<td class="r">{_html.escape(conv)}</td></tr>'
        for label, count, conv in rows
    )
    return (
        '<table>'
        '<thead><tr><th>Stage</th><th class="r">Count</th>'
        '<th class="r">Conv.</th></tr></thead>'
        f'<tbody>{body}</tbody>'
        '</table>'
    )


def _render_funnel_viz(
    funnel: Dict[str, int],
    *,
    selected_stage: Optional[str] = None,
) -> str:
    """7-stage horizontal grid with clickable links.

    Bar widths are stage-relative — max(funnel) is the 100% baseline.
    A stage with the highest count anchors the bar; others scale
    proportionally. Zero-deal stages render a 0% bar (visually invisible)
    so the row stays consistent.
    """
    max_count = max((int(v) for v in funnel.values()), default=0)
    cells: List[str] = []
    for stage in DEAL_STAGES:
        n = int(funnel.get(stage, 0))
        pct = (n / max_count * 100) if max_count else 0
        is_active = (selected_stage == stage)
        active_cls = " active" if is_active else ""
        # Linking: ?stage=<id> — clicking again from active stage returns
        # to "all deals". Achieved with selected_stage logic in the
        # orchestrator: when ?stage matches the click target, drop the
        # query param. For Phase 2 we keep it simple — every click sets;
        # a "Clear filter" affordance in the deals table provides the
        # exit path.
        href = f'/app?stage={_html.escape(stage)}'
        # If we have a focused-deal context, preserve it in the link.
        # That's a future commit's concern — orchestrator will pass it
        # via a kwarg. # TODO(phase 2): preserve ?deal=<id> across stage
        # clicks once the orchestrator threads it through.
        label = _STAGE_LABEL.get(stage, stage.title())
        count_html = (
            f'<div class="count num">{n}</div>'
            if n > 0 else
            '<div class="count num" style="color:var(--faint)">0</div>'
        )
        cells.append(
            f'<a class="stage{active_cls}" href="{href}">'
            f'<div class="name">{_html.escape(label)}</div>'
            f'{count_html}'
            f'<div class="bar"><div class="fill" '
            f'style="width:{pct:.1f}%"></div></div>'
            '</a>'
        )
    return f'<div class="app-pipeline-funnel">{"".join(cells)}</div>'


def render_pipeline_funnel(
    rollup: Dict[str, Any],
    *,
    selected_stage: Optional[str] = None,
) -> str:
    """7-stage funnel + paired conversion-percentage table.

    Args:
        rollup: ``portfolio_rollup(store)`` output. Reads ``stage_funnel``.
        selected_stage: Currently-active stage filter from ``?stage=<id>``.
            Passed through from the orchestrator. None = no filter.

    Returns:
        Complete <div class="pair">…</div> ready to drop into /app.
    """
    funnel = rollup.get("stage_funnel") or {}
    deal_count = int(rollup.get("deal_count") or 0)

    # Editorial empty-state hint above the funnel when zero deals
    eyebrow = ""
    if deal_count == 0:
        eyebrow = (
            '<div class="micro" style="color:var(--muted);'
            'padding:.5rem 0 1rem;">No deals yet — '
            '<a href="/import" style="color:var(--teal-deep)">Add a deal</a> '
            'to populate the funnel.</div>'
        )

    viz_html = (
        f'{eyebrow}'
        f'{_render_funnel_viz(funnel, selected_stage=selected_stage)}'
    )

    return pair_block(
        viz_html,
        label="PIPELINE FUNNEL · STAGE-RELATIVE",
        source="portfolio.db",
        data_table=_render_conversion_table(funnel),
    )
