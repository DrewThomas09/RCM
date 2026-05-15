"""Morning-brief panel grid for the /app dashboard.

Ported from the Claude Design home handoff (``HomePage.jsx``'s
DataPanel grid). A row of glance panels built with the
``ck_data_panel`` + ``ck_bar_row`` primitives — the "what does the
portfolio look like right now" read a partner wants first thing
Monday, sitting above the detailed analytical blocks.

Built entirely from the ``rollup`` dict that
``app_page.render_app_page`` already computes — **no store access,
no new queries**, so it has zero impact on the page's documented
3-query perf budget. The detailed blocks below (pipeline funnel,
covenant heatmap, alerts, …) remain the drill-down; this is the
summary-then-detail IA the handoff intends.
"""
from __future__ import annotations

from typing import Any, Dict

from rcm_mc.ui._chartis_kit import ck_bar_row, ck_data_panel

# Canonical stage order for the funnel panel — matches DEAL_STAGES.
_STAGE_ORDER = [
    "sourcing", "screened", "ioi", "loi", "diligence",
    "ic", "closed", "hold", "exit",
]


def render_morning_brief(rollup: Dict[str, Any]) -> str:
    """Render the morning-brief panel grid from an already-computed
    portfolio ``rollup``. Pure presentation — no queries.

    ``rollup`` is the dict returned by
    ``portfolio.portfolio_snapshots.portfolio_rollup`` — keys used:
    ``deal_count``, ``stage_funnel``, ``covenant_trips``,
    ``covenant_tight``, ``concerning_deals``.
    """
    deal_count = int(rollup.get("deal_count", 0) or 0)

    # ── FNL — pipeline funnel as compact bar rows ──
    funnel = rollup.get("stage_funnel") or {}
    funnel_max = max(funnel.values(), default=0) or 1
    funnel_rows = ""
    for stage in _STAGE_ORDER:
        if stage not in funnel:
            continue
        n = int(funnel.get(stage, 0) or 0)
        funnel_rows += ck_bar_row(
            stage.title(), str(n), (n / funnel_max) * 100, tone="teal",
        )
    if not funnel_rows:
        funnel_rows = (
            '<div style="font-size:12px;color:var(--sc-text-faint);">'
            'No deals in the pipeline yet.</div>'
        )
    fnl = ck_data_panel("FNL", "Pipeline Funnel", funnel_rows)

    # ── CVN — portfolio-wide covenant status ──
    trips = int(rollup.get("covenant_trips", 0) or 0)
    tight = int(rollup.get("covenant_tight", 0) or 0)
    safe = max(0, deal_count - trips - tight)
    cvn_max = max(trips, tight, safe, 1)
    cvn_rows = (
        ck_bar_row("Tripped", str(trips),
                   (trips / cvn_max) * 100, tone="negative")
        + ck_bar_row("Tight", str(tight),
                     (tight / cvn_max) * 100, tone="warning")
        + ck_bar_row("Safe", str(safe),
                     (safe / cvn_max) * 100, tone="positive")
    )
    cvn = ck_data_panel("CVN", "Covenant Status · portfolio", cvn_rows)

    # ── SIG — concerning vs clean deals ──
    concerning = int(rollup.get("concerning_deals", 0) or 0)
    clean = max(0, deal_count - concerning)
    sig_max = max(concerning, clean, 1)
    sig_rows = (
        ck_bar_row("Concerning", str(concerning),
                   (concerning / sig_max) * 100, tone="warning")
        + ck_bar_row("Clean", str(clean),
                     (clean / sig_max) * 100, tone="positive")
    )
    sig = ck_data_panel(
        "SIG", "Signal Scan · concerning vs clean", sig_rows,
    )

    return (
        '<section style="margin:0 0 var(--sc-s-5);">'
        '<div style="font-family:var(--sc-sans);font-size:11px;'
        'font-weight:600;letter-spacing:0.18em;text-transform:uppercase;'
        'color:var(--sc-text-dim);margin-bottom:12px;">'
        'Morning brief &middot; what the portfolio looks like right now'
        '</div>'
        '<div style="display:grid;'
        'grid-template-columns:repeat(auto-fit,minmax(280px,1fr));'
        'gap:14px;">'
        f'{fnl}{cvn}{sig}'
        '</div>'
        '</section>'
    )
