"""Geographic portfolio map (Prompt 69 UI).

Route: GET /portfolio/map. Renders an inline SVG map of the US with
deal markers positioned at state centroids. Color = deal stage,
size = EBITDA opportunity. State shading by CON status.
"""
from __future__ import annotations

import html
import math
from typing import Any, Dict, List, Optional, Tuple


def _esc(s: Any) -> str:
    return html.escape("" if s is None else str(s))


# Simplified Albers projection for continental US.
# Maps (lat, lon) → (x, y) in a 960×600 viewport.
def _project(lat: float, lon: float) -> Tuple[float, float]:
    """Cheap Albers-ish projection. Not cartographically precise but
    good enough to place state-centroid dots on an SVG."""
    # Center: 39°N, 98°W. Scale by eye to fill 960×600.
    x = (lon + 98) * 12.0 + 480
    y = -(lat - 39) * 16.0 + 300
    return (max(20, min(940, x)), max(20, min(580, y)))


# CON state shading colors.
_CON_FILL = {True: "var(--paper-pure)", False: "var(--bg)"}

_STAGE_COLORS = {
    "pipeline": "var(--muted)",
    "diligence": "var(--teal)",
    "ic": "var(--amber)",
    "hold": "var(--green)",
    "exit": "var(--ink-2)",
}


def render_portfolio_map(
    deals: List[Dict[str, Any]],
    *,
    con_states: Optional[Dict[str, bool]] = None,
) -> str:
    """Full-page HTML with an inline SVG US map + deal markers."""
    from ._chartis_kit import (
        chartis_shell, ck_eyebrow, ck_fmt_num, ck_kpi_block,
        ck_next_section, ck_provenance_tooltip,
    )

    # State background rectangles (simplified — just shade CON vs non-CON).
    state_bg = ""
    if con_states:
        try:
            from ..data.geo_lookup import STATE_CENTROIDS
            for st, has_con in con_states.items():
                coords = STATE_CENTROIDS.get(st)
                if not coords:
                    continue
                x, y = _project(coords[0], coords[1])
                fill = _CON_FILL.get(has_con, "var(--bg)")
                state_bg += (
                    f'<circle cx="{x:.0f}" cy="{y:.0f}" r="18" '
                    f'fill="{fill}" opacity="0.4"/>'
                )
        except Exception:  # noqa: BLE001
            pass

    # Deal markers.
    markers = ""
    for d in deals:
        lat = float(d.get("lat") or 0)
        lon = float(d.get("lon") or 0)
        if lat == 0 and lon == 0:
            # Try state centroid fallback.
            state = str(d.get("state") or "").upper()
            try:
                from ..data.geo_lookup import STATE_CENTROIDS
                coords = STATE_CENTROIDS.get(state, (0, 0))
                lat, lon = coords
            except Exception:  # noqa: BLE001
                continue
            if lat == 0:
                continue
        x, y = _project(lat, lon)
        ebitda = float(d.get("ebitda_opportunity") or 0)
        radius = max(6, min(20, 6 + ebitda / 5e6))
        stage = str(d.get("stage") or "diligence")
        color = _STAGE_COLORS.get(stage, "var(--teal)")
        name = _esc(d.get("name") or d.get("deal_id") or "")
        markers += (
            f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{radius:.0f}" '
            f'fill="{color}" opacity="0.8" '
            f'style="cursor:pointer;">'
            f'<title>{name} ({stage})</title>'
            f'</circle>'
        )

    if not markers:
        markers = (
            '<text x="480" y="300" text-anchor="middle" '
            'fill="var(--muted)" font-size="14">No deals to display</text>'
        )

    # Legend.
    legend_y = 520
    legend = ""
    for i, (stage, color) in enumerate(_STAGE_COLORS.items()):
        lx = 60 + i * 120
        legend += (
            f'<circle cx="{lx}" cy="{legend_y}" r="5" fill="{color}"/>'
            f'<text x="{lx + 10}" y="{legend_y + 4}" fill="var(--muted)" '
            f'font-size="10">{stage}</text>'
        )

    svg = (
        '<svg viewBox="0 0 960 600" '
        'style="width:100%;max-width:960px;height:auto;'
        'background:var(--bg);border:1px solid var(--paper-pure);border-radius:4px;">'
        f'{state_bg}{markers}{legend}'
        '</svg>'
    )

    css = """
    .map-wrap { max-width:960px; margin:0 auto; }
    """
    # Cycle 46 — KPI strip + provenance + editorial chrome.
    n_states = len({d.get("state") for d in deals if d.get("state")})
    n_con = sum(1 for s, v in (con_states or {}).items() if v)
    deals_value = ck_provenance_tooltip(
        "Deals plotted",
        ck_fmt_num(len(deals)),
        explainer=(
            f"Each circle is one deal positioned at the state "
            f"centroid. Circle size encodes EBITDA opportunity; "
            f"color encodes deal stage (pipeline / diligence / "
            f"IC / hold / exit)."
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
    body = f"""
    {ck_eyebrow("Portfolio Map")}
    <h2>Portfolio Map</h2>
    {kpi_strip}
    <div class="muted" style="margin-bottom:12px;">
      {len(deals)} deal(s) plotted. Circle size = EBITDA opportunity.
      Color = deal stage.
    </div>
    <div class="map-wrap">{svg}</div>
    {next_up}
    """
    return chartis_shell(body, "Portfolio Map",
                    active_nav="/portfolio",
                    subtitle=f"{len(deals)} deals mapped",
                    extra_css=css,
                    editorial_intro={
                        "eyebrow": "PORTFOLIO MAP",
                        "headline": "Where the portfolio actually is.",
                        "italic_word": "where",
                        "body": (
                            "Geographic distribution of active deals. "
                            "Use the map to read regulatory exposure "
                            "(CON jurisdictions) and to spot "
                            "concentration risk in single-payer "
                            "regimes."
                        ),
                    })
