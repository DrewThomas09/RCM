"""Geographic portfolio map.

Route: GET /portfolio/map. Renders the reusable US state tile-grid
cartogram (rcm_mc.ui.us_map), shading each state by the number of
portfolio deals located there and flagging Certificate-of-Need (CON)
jurisdictions. Local/static — no external map tiles or APIs.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional


def _esc(s: Any) -> str:
    return html.escape("" if s is None else str(s))


_EXPLAINER_CSS = """
.ck-pm-explainer{font-family:var(--sc-serif);font-size:15px;line-height:1.6;
color:var(--sc-text-dim);max-width:68ch;
margin:var(--sc-s-4) 0 var(--sc-s-6);}
.ck-pm-explainer em{color:var(--sc-teal-ink);font-style:italic;}
.ck-pm-selected{font-family:var(--sc-sans);font-size:13px;
color:var(--sc-text-dim);margin:10px 0 0;min-height:1.2em;}
"""


def render_portfolio_map(
    deals: List[Dict[str, Any]],
    *,
    con_states: Optional[Dict[str, bool]] = None,
) -> str:
    """Full-page HTML with the reusable US state tile-grid map."""
    from ._chartis_kit import (
        chartis_shell, ck_fmt_num, ck_kpi_block,
        ck_next_section, ck_page_title, ck_provenance_tooltip,
    )
    from .us_map import render_us_state_map

    # Per-state deal count — the metric the map shades by.
    state_counts: Dict[str, int] = {}
    for d in deals:
        st = str(d.get("state") or "").upper()
        if st:
            state_counts[st] = state_counts.get(st, 0) + 1

    con_set = {str(s).upper() for s, v in (con_states or {}).items() if v}
    # CON note shows on every state's tooltip where flagged (incl. states
    # with deals); states with no deals still render as honest "no data".
    notes = {st: "Certificate-of-Need (CON) jurisdiction" for st in con_set}

    map_html = render_us_state_map(
        state_counts,
        metric_label="deals",
        state_notes=notes,
        accent_states=con_set,
        accent_label="Certificate-of-Need (CON) state",
        empty_message=(
            "No state-level portfolio data is available yet. When deals "
            "carry a state (or facility geography), this map shows "
            "geographic exposure and concentration across markets."
        ),
    )
    selected_panel = (
        '<p class="ck-pm-selected" data-us-map-selected>'
        'Click a state to see its portfolio detail.</p>'
        if state_counts else ''
    )

    css = ".map-wrap { max-width:620px; margin:0 auto; }"
    n_states = len(state_counts)
    n_con = sum(1 for s, v in (con_states or {}).items() if v)
    deals_value = ck_provenance_tooltip(
        "Deals plotted",
        ck_fmt_num(len(deals)),
        explainer=(
            "Portfolio deals with a state, counted per state. The map is a "
            "state tile-grid cartogram — each cell is one state, shaded by "
            "its deal count; deeper teal = more deals. States with no deals "
            "show as 'no data'."
        ),
    )
    states_value = ck_provenance_tooltip(
        "States represented",
        ck_fmt_num(n_states),
        explainer=(
            f"Unique states with at least one deal in the "
            f"portfolio. {n_con} states are flagged as "
            f"Certificate-of-Need (CON) jurisdictions, where "
            f"market entry is regulated."
        ),
        inject_css=False,
    )
    kpi_strip = (
        '<div class="ck-kpi-grid" style="grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:14px;">'
        + ck_kpi_block("Deals Mapped", deals_value, "with state data")
        + ck_kpi_block("States", states_value, "with portfolio presence")
        + ck_kpi_block("CON States", ck_fmt_num(n_con), "regulated entry")
        + '</div>'
    )

    next_up = ck_next_section(
        "Open the portfolio heatmap",
        "/portfolio/heatmap",
        eyebrow="Continue —",
        italic_word="heatmap",
    )
    title_block = ck_page_title(
        "Portfolio Map",
        eyebrow="PORTFOLIO MAP",
        meta=(
            f"{len(deals)} deals · {n_states} states · {n_con} CON jurisdictions"
            if deals else "no deals yet"
        ),
    )
    explainer_html = (
        '<p class="ck-pm-explainer">'
        '<em>Where the portfolio sits, state by state.</em> '
        "A state tile-grid cartogram: every state is an equal-size cell in "
        "its approximate geographic position, shaded by how many portfolio "
        "deals sit there. Cells outlined in amber are Certificate-of-Need "
        "(CON) jurisdictions, where new market entry requires regulatory "
        "approval. Hover a state for its detail; click to select it. "
        "Equal-size cells keep large states from dominating the read — this "
        "is a metric map, not a coastline map."
        '</p>'
    )
    body = (
        title_block
        + explainer_html
        + kpi_strip
        + f'<div class="map-wrap">{map_html}</div>'
        + selected_panel
        + next_up
    )
    return chartis_shell(body, "Portfolio Map",
                    active_nav="/portfolio",
                    extra_css=css + _EXPLAINER_CSS)
