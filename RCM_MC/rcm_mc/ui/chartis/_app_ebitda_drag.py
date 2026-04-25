"""EBITDA drag — stacked horizontal bar + per-component breakdown + paired table.

Spec: docs/design-handoff/EDITORIAL_STYLE_PORT.md §6.8
Reference: docs/design-handoff/reference/04-command-center.html (drag section)

5-segment stacked bar (one segment per drag component) + per-component
rows with swatch + label + % + $. Paired with raw breakdown table +
recovery quarters table.

See module-level conventions in _app_kpi_strip.py docstring (1-6).

Empty / sparse states (per Phase 2 review):
  - No focused deal → "Select a deal above to see drag breakdown."
  - Focused deal with no bridge built yet → "Run the analysis pipeline
    first" with link to /diligence/thesis-pipeline

# TODO(phase 3): wire to DealAnalysisPacket.ebitda_bridge for real
# component-level decomposition. Phase 2 ships the chrome with the
# 5-segment placeholder shape so the visual structure is in place;
# real $ values + recovery quarters land when the packet wiring is
# threaded through the orchestrator.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional, Tuple

from rcm_mc.ui._chartis_kit_editorial import number_maybe, pair_block


# 5 canonical drag components per spec §6.8 + cc-data.jsx. Segment
# colors come from the editorial status palette so the stacked bar
# stays editorial-toned (no rainbow / data-vis palette).
_DRAG_COMPONENTS: List[Dict[str, str]] = [
    {"key": "denial",      "label": "Denial workflow gap", "color": "var(--red)"},
    {"key": "coding",      "label": "Coding / CDI miss",   "color": "var(--amber)"},
    {"key": "ar_aging",    "label": "A/R aging",            "color": "var(--blue)"},
    {"key": "self_pay",    "label": "Self-pay leakage",     "color": "var(--teal-deep)"},
    {"key": "other",       "label": "Other",                "color": "var(--muted)"},
]


def _decompose_drag(
    packet: Optional[Any],
) -> Optional[List[Tuple[str, str, str, float, float]]]:
    """Decompose the bridge into 5 drag components.

    Returns:
        None when no packet OR no bridge available — caller renders
        empty-state.
        Otherwise: list of 5 tuples (key, label, color, pct, dollars_M).

    Phase 2 stub: returns None when packet is None or has no
    ebitda_bridge attribute, OR a placeholder allocation when a
    packet is present so the partner sees the chrome with realistic-
    looking shape. Real per-component decomposition is Phase 3 once
    the bridge data shape is mapped to the 5 spec components.
    """
    if packet is None:
        return None
    bridge = getattr(packet, "ebitda_bridge", None)
    if bridge is None:
        return None
    # # TODO(phase 3): real decomposition. For now we surface a
    # uniform 20% / 20% / 20% / 20% / 20% allocation so the chrome
    # reads as "data present" rather than "all empty" when a packet
    # exists. Visually this signals "we have the bridge but haven't
    # finished decomposing it yet" — Phase 3 replaces with real bands.
    return [
        (c["key"], c["label"], c["color"], 0.20, 0.0)
        for c in _DRAG_COMPONENTS
    ]


def _render_drag_bar(
    components: List[Tuple[str, str, str, float, float]],
) -> str:
    """5-segment stacked horizontal bar."""
    segments = "".join(
        f'<div class="seg" style="width:{pct * 100:.1f}%;'
        f'background:{color};">{int(pct * 100)}%</div>'
        for _, _, color, pct, _ in components
    )
    return f'<div class="app-drag-bar">{segments}</div>'


def _render_drag_rows(
    components: List[Tuple[str, str, str, float, float]],
) -> str:
    """Per-component rows below the bar."""
    rows = "".join(
        f'<div class="row">'
        f'<div class="swatch" style="background:{color}"></div>'
        f'<div class="label">{_html.escape(label)}</div>'
        f'<div class="pct">{pct * 100:.0f}%</div>'
        f'<div class="v">{number_maybe(dollars, format="ev") if dollars else "—"}</div>'
        '</div>'
        for _, label, color, pct, dollars in components
    )
    return f'<div class="app-drag-rows">{rows}</div>'


def _render_breakdown_table(
    components: List[Tuple[str, str, str, float, float]],
) -> str:
    """Paired right-side raw breakdown table."""
    body = "".join(
        f'<tr><td class="lbl">{_html.escape(label)}</td>'
        f'<td class="r">{pct * 100:.1f}%</td>'
        f'<td class="r">'
        f'{number_maybe(dollars, format="ev") if dollars else "—"}'
        f'</td></tr>'
        for _, label, _, pct, dollars in components
    )
    return (
        '<table>'
        '<thead><tr>'
        '<th>Component</th>'
        '<th class="r">% of drag</th>'
        '<th class="r">$ impact</th>'
        '</tr></thead>'
        f'<tbody>{body}</tbody>'
        '</table>'
    )


def render_ebitda_drag(packet: Optional[Any]) -> str:
    """5-segment stacked drag bar + per-component rows + paired breakdown.

    Args:
        packet: DealAnalysisPacket for the focused deal, or None.
            None means no focused deal — empty-state renders.
            packet without ebitda_bridge attribute means the analysis
            hasn't run — different empty-state with run-the-pipeline
            link.

    Returns:
        Complete <div class="pair">…</div>.
    """
    components = _decompose_drag(packet)

    if components is None:
        if packet is None:
            empty_msg = (
                "Select a deal above to see EBITDA drag breakdown."
            )
        else:
            empty_msg = (
                'No bridge data yet. <a href="/diligence/thesis-pipeline">'
                'Run the analysis pipeline</a> to populate.'
            )
        viz_html = (
            f'<div class="app-drag-empty">{empty_msg}</div>'
        )
        empty_table = (
            '<table>'
            '<thead><tr>'
            '<th>Component</th>'
            '<th class="r">% of drag</th>'
            '<th class="r">$ impact</th>'
            '</tr></thead>'
            '<tbody>'
            '<tr><td colspan="3" class="lbl" style="text-align:center;'
            'padding:1rem 0;font-style:italic;color:var(--muted);">'
            f'{empty_msg}</td></tr>'
            '</tbody>'
            '</table>'
        )
        return pair_block(
            viz_html,
            label="EBITDA DRAG · 5-COMPONENT DECOMP",
            source="ebitda_bridge",
            data_table=empty_table,
        )

    viz_html = (
        f'<h3 style="margin:0 0 .25rem;font-family:\'Source Serif 4\',serif;'
        f'font-weight:400;font-size:1.2rem;color:var(--ink);">Drag decomposition</h3>'
        f'<p style="color:var(--muted);font-size:.82rem;margin:0 0 1rem;">'
        f'Median per-hospital impact across simulations</p>'
        f'{_render_drag_bar(components)}'
        f'{_render_drag_rows(components)}'
    )

    return pair_block(
        viz_html,
        label="EBITDA DRAG · 5-COMPONENT DECOMP",
        source="ebitda_bridge",
        data_table=_render_breakdown_table(components),
    )
