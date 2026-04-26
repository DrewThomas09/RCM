"""/app dashboard orchestrator.

Top-level renderer for the editorial /app dashboard. Calls each block
helper once, in spec §6 order, with the same pre-computed inputs the
helpers' own docstrings declare. Returns full HTML wrapped in
editorial_chartis_shell.

Layout, top-down (matches reference/04-command-center.html — single
flat scroll, NO section headers).

Per Phase 2 review (W4): section-header IA aid was DROPPED. Reasoning:

  1. The reference HTML / cc-app.jsx is single-flat-scroll. Per the
     bundle-README rule established in Phase 1, reference HTML is
     byte-for-byte ground truth. Adding sections would be smuggling
     an IA decision into a styling commit (same pattern as the C4
     hover-vs-click push-back from Phase 2's API review).

  2. Deals + focused-deal blocks are the same conceptual surface —
     selecting a deal in the table is what makes downstream blocks
     render meaningfully. A section break between them would impose
     a false visual separation between cause and effect.

# TODO(phase 3): consider scroll-aid affordance (sticky TOC?
# scroll-spy?) IF post-launch usage shows partners getting lost in
# the dashboard. Don't pre-emptively add IA structure that wasn't
# asked for; add it informed by real usage data.

Routing notes (W2 — focused_row vs deal_id):

  ``focused_row`` is passed to helpers that render chrome-level data
  already in ``deals_df`` (the focused-deal context bar). ``deal_id``
  (string) is passed to helpers that query ``store`` for per-deal
  data not in the cross-deal aggregate (covenant heatmap, EBITDA
  drag, initiative tracker). This isn't inconsistency — it's the
  Q2 escape-hatch convention from the API surface review applied
  at the orchestrator level.

Stage-filter behavior (W3):

  ``?stage=<id>`` narrows the deals table; the pipeline funnel
  always shows the full pipeline with the selected stage highlighted.
  Rationale: the funnel provides CONTEXT for the filter, not a target
  of the filter. A user who clicked "Hold" still wants to see "Hold
  is 4 of 17 deals across the pipeline" — that's the value of the
  funnel still being there.
"""
from __future__ import annotations

from typing import Any, Optional

import pandas as pd

from rcm_mc.portfolio.portfolio_snapshots import (
    DEAL_STAGES,
    latest_per_deal,
    portfolio_rollup,
)
from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.ui._chartis_kit import editorial_chartis_shell
from rcm_mc.ui._chartis_kit_editorial import editorial_page_head

from ._app_alerts import render_alerts
from ._app_covenant_heatmap import render_covenant_heatmap
from ._app_deals_table import render_deals_table
from ._app_deliverables import render_deliverables
from ._app_ebitda_drag import render_ebitda_drag
from ._app_focused_deal_bar import render_focused_deal_bar
from ._app_initiative_tracker import render_initiative_tracker
from ._app_kpi_strip import render_kpi_strip
from ._app_pipeline_funnel import render_pipeline_funnel


def render_app_page(
    *,
    store: PortfolioStore,
    focused_deal_id: Optional[str] = None,
    selected_stage: Optional[str] = None,
    phi_mode: Optional[str] = None,
    user: Optional[str] = None,
) -> str:
    """Compose the editorial /app dashboard.

    Args:
        store: Portfolio data handle.
        focused_deal_id: From ``?deal=<id>``. None when no deal selected.
        selected_stage: From ``?stage=<id>``. None when no filter active.
            Pre-validated against ``DEAL_STAGES`` by the route handler.
        phi_mode: Read from ``RCM_MC_PHI_MODE`` env in the route handler.
            Per Phase 1 correction: helpers don't read globals.
        user: Current user identifier (placeholder; not yet rendered).

    Returns:
        Complete HTML string (editorial chrome + 9 blocks).
    """
    # PERF BUDGET: 3 queries max per /app render.
    # Adding a 4th requires perf budget review.
    rollup = portfolio_rollup(store)              # query 1
    deals_df = latest_per_deal(store)             # query 2
    focused_packet = _resolve_focused_packet(     # query 3 (only if focused)
        store, focused_deal_id,
    )

    # Resolve focused row from already-fetched deals_df — no extra query.
    focused_row = _resolve_focused_row(deals_df, focused_deal_id)

    # Stage filter applies to the deals table only, NOT the funnel
    # (per W3 docstring above — funnel-as-context, not target).
    table_df = (
        deals_df[deals_df["stage"].astype(str) == selected_stage]
        if (selected_stage and not deals_df.empty) else deals_df
    )

    # held_deals subset for prev/next switcher in focused-deal bar
    held_deals = (
        deals_df[deals_df["stage"].astype(str).isin(["hold", "exit"])]
        if not deals_df.empty else None
    )

    # As-of for the page-head meta column. Use the most recent snapshot
    # if any deals tracked; else "—".
    asof_str = "—"
    try:
        if not deals_df.empty and "created_at" in deals_df.columns:
            ts = deals_df["created_at"].max()
            if ts:
                asof_str = str(ts)[:10]
    except Exception:  # noqa: BLE001 — page-head meta must not break the render
        pass

    page_head_html = editorial_page_head(
        eyebrow=[
            ("PORTFOLIO & DILIGENCE", None),
            ("FUND II", None),
            ("/COMMAND-CENTER", "slug"),
        ],
        title="Command center",
        lede=(
            "Hold-period rollup, active diligence, screening flow — "
            "one canvas."
        ),
        meta=[
            ("ID", "CCF-FUND2"),
            ("STATUS", "LIVE"),
            ("AS OF", asof_str),
        ],
    )

    # Single flat scroll — 9 blocks in spec §6 order.
    # No section headers (per W4 push-back).
    body_parts = [
        page_head_html,
        # Top: portfolio rollup
        render_kpi_strip(rollup, deals_df=deals_df),
        render_pipeline_funnel(
            rollup,
            selected_stage=selected_stage,
            focused_deal_id=focused_deal_id,
        ),
        # Middle: deals + focus
        render_deals_table(
            table_df,
            focused_deal_id=focused_deal_id,
            selected_stage=selected_stage,
        ),
        render_focused_deal_bar(
            focused_row,
            held_deals=held_deals,
            selected_stage=selected_stage,
        ),
        # Focused-deal analytics
        render_covenant_heatmap(store, focused_deal_id),
        render_ebitda_drag(focused_packet),
        render_initiative_tracker(store, focused_deal_id),
        # Cross-deal
        render_alerts(store),
        # Deliverables scoped to focused deal when one is selected;
        # cross-deal latest otherwise. Phase 3 wired generated_exports
        # as the primary source (per Q3.5 canonical-path migration).
        render_deliverables(store, deal_id=focused_deal_id),
    ]

    return editorial_chartis_shell(
        '<div class="page">' + "".join(body_parts) + '</div>',
        title="Command center",
        active_nav="PORTFOLIO",
        breadcrumbs=[
            ("Home", "/"),
            ("Portfolio & diligence", None),
            ("Command center", None),
        ],
        show_chrome=True,
        show_phi_banner=True,
        phi_mode=phi_mode,
    )


# ── Helpers (file-private) ─────────────────────────────────────────

def _resolve_focused_row(
    deals_df: pd.DataFrame,
    focused_deal_id: Optional[str],
) -> Optional[pd.Series]:
    """Single-parse-point: resolve the focused deal row from deals_df.

    Helpers like _app_focused_deal_bar take a row; helpers like
    _app_covenant_heatmap take just the id (per W2 above). One lookup
    here serves the row-takers; the id-takers receive the raw string.
    """
    if not focused_deal_id or deals_df is None or deals_df.empty:
        return None
    try:
        match = deals_df[
            deals_df["deal_id"].astype(str) == str(focused_deal_id)
        ]
    except Exception:  # noqa: BLE001
        return None
    if match.empty:
        return None
    return match.iloc[0]


def _resolve_focused_packet(
    store: PortfolioStore,
    focused_deal_id: Optional[str],
) -> Optional[Any]:
    """Lazy-load the DealAnalysisPacket for the focused deal.

    Counts as the 3rd of the 3-query perf budget (and only fires when a
    deal is focused — un-focused renders stay at 2 queries).

    Caching: ``analysis_store.get_or_build_packet`` has internal TTL
    cache so repeat hits on the same deal hit RAM, not SQLite.
    Returns None on absence (un-analyzed deal).
    """
    if not focused_deal_id:
        return None
    try:
        from rcm_mc.analysis.analysis_store import get_or_build_packet
        return get_or_build_packet(store, focused_deal_id)
    except Exception:  # noqa: BLE001 — packet absence is expected for un-analyzed deals
        return None


def validate_stage(value: Optional[str]) -> Optional[str]:
    """Public helper used by the route handler to validate ``?stage=``.

    Returns the value when it's in DEAL_STAGES; otherwise None (no
    filter applied). Centralized here so the route handler doesn't
    have to import DEAL_STAGES separately.
    """
    if value and value in DEAL_STAGES:
        return value
    return None
