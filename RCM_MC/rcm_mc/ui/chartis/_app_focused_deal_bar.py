"""Focused-deal context bar — chrome between deals table and downstream sections.

Spec: docs/design-handoff/EDITORIAL_STYLE_PORT.md §6.6
Reference: docs/design-handoff/reference/04-command-center.html (deal-bar section)

UNPAIRED chrome (per spec §6.6 — neither viz nor data table; metadata strip).

Shows the focused deal's id + name + stage + EV + MOIC/IRR with
prev/next switch links on the right. Downstream sections (covenant
heatmap, EBITDA drag, initiative tracker) read from the focused deal.

See module-level conventions in _app_kpi_strip.py docstring (1-6).

Empty / sparse states:
  - No focused deal → bar hidden entirely (returns ""). Downstream
    blocks render their own empty states with "Select a deal above"
    eyebrows.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

import pandas as pd

from rcm_mc.ui._chartis_kit_editorial import number_maybe


_STAGE_LABEL: Dict[str, str] = {
    "sourced": "Sourced", "ioi": "IOI", "loi": "LOI", "spa": "SPA",
    "closed": "Closed", "hold": "Hold", "exit": "Exit",
}


def _build_switch_links(
    deal_row: pd.Series,
    *,
    held_deals: Optional[pd.DataFrame] = None,
    selected_stage: Optional[str] = None,
) -> str:
    """Render prev/next switch links (between held deals).

    When held_deals isn't passed, returns an empty switcher (just
    "← Back to deals" link). When passed, computes prev/next based
    on the focused deal's position in the held-deals list.
    """
    base_query: List[str] = ["ui=v3"]
    if selected_stage:
        base_query.append(f"stage={_html.escape(selected_stage)}")

    deal_id = str(deal_row.get("deal_id") or "")

    if held_deals is None or held_deals.empty:
        # Switcher disabled — just a back link
        return (
            '<div class="switch">'
            f'<a href="/app?{"&".join(base_query)}">← Clear focus</a>'
            '</div>'
        )

    ids = list(held_deals["deal_id"].astype(str))
    if deal_id not in ids:
        # Focused deal not in held-deals list (e.g., it's in IOI/LOI).
        # Show clear-focus only.
        return (
            '<div class="switch">'
            f'<a href="/app?{"&".join(base_query)}">← Clear focus</a>'
            '</div>'
        )

    idx = ids.index(deal_id)
    prev_id = ids[idx - 1] if idx > 0 else None
    next_id = ids[idx + 1] if idx + 1 < len(ids) else None

    parts: List[str] = []
    if prev_id:
        prev_q = base_query + [f"deal={_html.escape(prev_id)}"]
        parts.append(f'<a href="/app?{"&".join(prev_q)}">← Prev</a>')
    if next_id:
        next_q = base_query + [f"deal={_html.escape(next_id)}"]
        parts.append(f'<a href="/app?{"&".join(next_q)}">Next →</a>')
    parts.append(f'<a href="/app?{"&".join(base_query)}">Clear focus</a>')

    return f'<div class="switch">{"".join(parts)}</div>'


def render_focused_deal_bar(
    deal_row: Optional[pd.Series],
    *,
    held_deals: Optional[pd.DataFrame] = None,
    selected_stage: Optional[str] = None,
) -> str:
    """Chrome bar showing the focused deal's metadata.

    Args:
        deal_row: The focused deal as a single Series. None → returns "".
            The orchestrator looks up the row from deals_df via
            ``?deal=<id>`` and passes it here pre-resolved.
        held_deals: Subset of deals where stage == "hold" — used for
            prev/next switcher. Optional; if absent, switcher reduces
            to a "Clear focus" link.
        selected_stage: Active stage filter — preserved in switcher
            links so cycling between focused deals doesn't lose the
            stage filter context.

    Returns:
        <div class="app-focused-deal-bar">…</div> OR "" when no
        focused deal (caller decides nothing else needs to render).
    """
    if deal_row is None:
        return ""
    try:
        if isinstance(deal_row, pd.DataFrame) and deal_row.empty:
            return ""
    except Exception:  # noqa: BLE001
        pass

    deal_id = str(deal_row.get("deal_id") or "")
    name = str(deal_row.get("name") or deal_row.get("deal_name") or "")
    stage = str(deal_row.get("stage") or "")
    ev = deal_row.get("entry_ev")
    moic = deal_row.get("moic")
    irr = deal_row.get("irr")

    stage_label = _STAGE_LABEL.get(stage, stage.title()) if stage else "—"

    return (
        '<div class="app-focused-deal-bar">'
        '<div class="ctx">'
        f'<span class="id">{_html.escape(deal_id)}</span>'
        f'<span class="name">{_html.escape(name)}</span>'
        f'<span class="meta">STAGE <span class="v">'
        f'{_html.escape(stage_label)}</span></span>'
        f'<span class="meta">EV <span class="v">'
        f'{number_maybe(ev, format="ev")}</span></span>'
        f'<span class="meta">MOIC <span class="v">'
        f'{number_maybe(moic, format="moic")}</span></span>'
        f'<span class="meta">IRR <span class="v">'
        f'{number_maybe(irr, format="pct")}</span></span>'
        '</div>'
        f'{_render_export_buttons(deal_id)}'
        f'{_build_switch_links(deal_row, held_deals=held_deals, selected_stage=selected_stage)}'
        '</div>'
    )


def _render_export_buttons(deal_id: str) -> str:
    """3-button export group on the focused-deal context bar.

    Each button is an anchor that hits ``/api/analysis/<deal_id>/export``
    with a format query param. The endpoint streams the file with a
    ``Content-Disposition: attachment`` header so the browser saves
    rather than navigates. Every export writes a generated_exports
    audit row server-side.

    Buttons:
      - HTML report      → format=html  (full DealAnalysisPacket as HTML)
      - IC packet HTML   → format=html  with ?packet=ic   (or alias)
      - Deal Excel       → format=xlsx  (multi-sheet workbook)

    Note: the existing /api/analysis endpoint takes ``format`` only,
    not a packet-variant flag. The 'IC packet' button just uses the
    same html format — Phase 4 polish can add a per-variant query
    param if partner usage signals a need to differentiate.
    """
    if not deal_id:
        return ""
    deal_q = _html.escape(deal_id, quote=True)
    base = f"/api/analysis/{deal_q}/export"
    return (
        '<div class="exports">'
        f'<a class="exp-btn" href="{base}?format=html" '
        'title="Download the full deal-analysis report as HTML">'
        '⇣ HTML</a>'
        f'<a class="exp-btn" href="{base}?format=xlsx" '
        'title="Download the deal workbook as Excel">'
        '⇣ Excel</a>'
        f'<a class="exp-btn" href="{base}?format=json" '
        'title="Download the raw DealAnalysisPacket as JSON">'
        '⇣ JSON</a>'
        '</div>'
    )
