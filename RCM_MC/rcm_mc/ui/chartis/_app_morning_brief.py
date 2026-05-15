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

import html as _html
from typing import Any, Dict

from rcm_mc.ui._chartis_kit import ck_bar_row, ck_data_panel

# Canonical stage order for the funnel panel — matches DEAL_STAGES.
_STAGE_ORDER = [
    "sourcing", "screened", "ioi", "loi", "diligence",
    "ic", "closed", "hold", "exit",
]


def _dls_panel(deals_df) -> str:
    """DLS — recent deals, from the already-loaded ``deals_df``.

    Shows up to 6 most-recent deals (name / stage / MOIC); each row
    links to the deal hub. ``deals_df`` is the ``latest_per_deal``
    frame ``render_app_page`` already holds — ``None``/empty is
    tolerated, and any row-level error degrades to the empty state
    rather than breaking /app.
    """
    rows_html = ""
    try:
        if deals_df is not None and not deals_df.empty:
            df = deals_df
            if "created_at" in df.columns:
                df = df.sort_values("created_at", ascending=False)
            for _, row in df.head(6).iterrows():
                deal_id = str(row.get("deal_id", "") or "")
                name = str(row.get("name", "") or deal_id or "—")
                stage = str(row.get("stage", "") or "—")
                moic_raw = row.get("moic")
                try:
                    moic = (
                        f"{float(moic_raw):.2f}x"
                        if moic_raw is not None and str(moic_raw) != "nan"
                        else "—"
                    )
                except (TypeError, ValueError):
                    moic = "—"
                href = f"/deal/{_html.escape(deal_id, quote=True)}"
                rows_html += (
                    '<div style="display:grid;'
                    'grid-template-columns:1fr auto 56px;gap:10px;'
                    'align-items:baseline;padding:6px 0;font-size:12px;'
                    'border-bottom:1px solid var(--sc-rule);">'
                    f'<a href="{href}" style="color:var(--sc-teal-ink);'
                    'font-weight:500;text-decoration:none;overflow:hidden;'
                    'text-overflow:ellipsis;white-space:nowrap;">'
                    f'{_html.escape(name)}</a>'
                    '<span style="font-family:var(--sc-mono);font-size:10px;'
                    'letter-spacing:0.08em;text-transform:uppercase;'
                    f'color:var(--sc-text-dim);">{_html.escape(stage)}</span>'
                    '<span style="font-family:var(--sc-mono);text-align:right;'
                    'font-weight:600;font-variant-numeric:tabular-nums;'
                    f'color:var(--sc-text);">{_html.escape(moic)}</span>'
                    '</div>'
                )
    except Exception:  # noqa: BLE001 — a glance panel must never break /app
        rows_html = ""
    if not rows_html:
        rows_html = (
            '<div style="font-size:12px;color:var(--sc-text-faint);">'
            'No deals tracked yet.</div>'
        )
    return ck_data_panel("DLS", "Recent Deals", rows_html)


def render_morning_brief(rollup: Dict[str, Any], deals_df=None) -> str:
    """Render the morning-brief panel grid from an already-computed
    portfolio ``rollup`` (+ ``deals_df`` for the DLS panel). Pure
    presentation — no queries.

    ``rollup`` is the dict returned by
    ``portfolio.portfolio_snapshots.portfolio_rollup`` — keys used:
    ``deal_count``, ``stage_funnel``, ``covenant_trips``,
    ``covenant_tight``, ``concerning_deals``. ``deals_df`` is the
    ``latest_per_deal`` frame; ``None`` is tolerated.
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

    # ── DLS — recent deals (uses the already-loaded deals_df) ──
    dls = _dls_panel(deals_df)

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
        f'{fnl}{cvn}{sig}{dls}'
        '</div>'
        '</section>'
    )
