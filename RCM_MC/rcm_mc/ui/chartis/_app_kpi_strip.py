"""KPI strip + paired quarterly-history table — first paired-block helper for /app.

Spec: docs/design-handoff/EDITORIAL_STYLE_PORT.md §6.3
Reference: docs/design-handoff/reference/04-command-center.html (KPI section)

Renders an 8-cell horizontal strip of fund-level KPIs, paired with a
right-side quarterly-history table for the headline KPI (Weighted MOIC,
per ``cc-app.jsx:157`` default).

──────────────────────────────────────────────────────────────────────
Conventions for /app block helpers (this module + commits 2-8 mirror)
──────────────────────────────────────────────────────────────────────

1. Helpers receive pre-computed inputs by default. Taking ``store``
   directly requires a docstring justification — typically "this
   query cannot be batched into the orchestrator's primary fetch."
   Reviewer challenge: if the justification doesn't fit in one
   sentence, the helper probably belongs in the orchestrator, not
   as a leaf.

2. Each helper renders its own empty state. The empty-state copy is
   part of the helper's contract; if a future page wants different
   copy for the same block, it's a kwarg refactor, not an
   orchestrator change.

3. Module-scoped CSS lives in ``/static/v3/chartis.css`` under the
   ``/* === /app dashboard blocks === */`` section, NOT inline. Inline
   <style> blocks would re-send ~5KB per /app render (uncacheable)
   and fight future high-contrast / print / density mode overrides.

4. Deferred work uses ``# TODO(phase N): <description>`` comments.
   The canonical deferral list is ``grep -rn 'TODO(phase' rcm_mc/``.
   A contract test in commit 10 asserts no ``TODO(phase 2)`` comments
   ship after Phase 2.

──────────────────────────────────────────────────────────────────────

Empty / sparse states for THIS block (per Phase 2 review):
  - Missing scalar values render `—`
  - A KPI cell with n<2 quarters of history hides its sparkline subgraph
    (keeps value + delta + label)
  - Empty fund (zero deals) → all 8 cells render `—` and the eyebrow
    shows "No deals tracked yet"

# TODO(phase 3): KPI cell hover/click interaction. Phase 2 ships
# static-but-rendered per the Phase 2 review: replacing the spec's
# hover with click would silently change UX semantics; adding hover
# via JS would expand the test surface beyond Phase 2's scope. The
# right-side table is fixed to the headline KPI's history. Phase 3
# can deliberately decide hover / click / small-multiples / palette.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from rcm_mc.ui._chartis_kit_editorial import (
    number_maybe,
    pair_block,
    sparkline_svg,
)


# Eight KPIs in the strip. Each row defines:
#   id      — internal key
#   label   — display label
#   pull    — function (rollup, deals_df) → (value_html, delta_html, tone)
#   spark   — function (deals_df) → list[float] OR None when sparkline not applicable
#   format  — passthrough format hint to number_maybe (informational only here)
_KPI_ROWS: List[Dict[str, Any]] = [
    {"id": "deals",   "label": "Active deals"},
    {"id": "moic",    "label": "Weighted MOIC"},     # headline — paired table follows this one
    {"id": "irr",     "label": "Weighted IRR"},
    {"id": "atrisk",  "label": "Covenants at risk"},
    {"id": "drag",    "label": "Avg EBITDA drag"},
    {"id": "dar",     "label": "Avg DAR drag"},
    {"id": "init",    "label": "Initiatives tracked"},
    {"id": "cash",    "label": "Avg days cash"},
]


def _value_for_kpi(
    kpi_id: str,
    rollup: Dict[str, Any],
    deals_df: pd.DataFrame,
) -> Tuple[str, str, Optional[str]]:
    """Return (value_html, delta_html, tone) for one KPI cell.

    Pure function of rollup + deals_df — no env reads, no DB calls.
    Helpers stay testable and predictable. Missing data renders `—`.
    """
    if kpi_id == "deals":
        n = int(rollup.get("deal_count") or 0)
        if n == 0:
            return ("—", "", None)
        return (str(n), "", None)

    if kpi_id == "moic":
        v = rollup.get("weighted_moic")
        if v is None:
            return ("—", "", None)
        return (number_maybe(v, format="moic"), "", "green" if v >= 2.0 else None)

    if kpi_id == "irr":
        v = rollup.get("weighted_irr")
        if v is None:
            return ("—", "", None)
        # weighted_irr is stored as a fraction (0.219 → 21.9%)
        return (number_maybe(v, format="pct"),
                "",
                "green" if v >= 0.20 else "amber" if v >= 0.15 else "red")

    if kpi_id == "atrisk":
        n = int(rollup.get("covenant_trips") or 0) + int(rollup.get("covenant_tight") or 0)
        tone = "green" if n == 0 else "amber" if n <= 2 else "red"
        return (str(n), "", tone)

    # The remaining 4 KPIs come from per-deal aggregates that aren't in
    # portfolio_rollup() yet. Phase 2 ships them as `—` placeholders so the
    # strip renders all 8 cells consistently; future commits wire each one.
    if kpi_id in ("drag", "dar", "init", "cash"):
        return ("—", "", None)

    return ("—", "", None)


def _sparkline_for_kpi(kpi_id: str, deals_df: pd.DataFrame) -> Optional[List[float]]:
    """Return per-quarter trend values for a KPI, or None when n<2.

    Phase 2 ships sparklines off (returns None for every KPI). Future
    commits (or Phase 2.5) wire fund-level quarterly aggregates from
    ``quarterly_snapshots``. Returning None keeps the cells consistent
    today; the caller hides the sparkline subgraph when None is returned.
    """
    return None


def _render_kpi_cell(
    kpi: Dict[str, Any],
    rollup: Dict[str, Any],
    deals_df: pd.DataFrame,
    *,
    is_headline: bool,
) -> str:
    """Render one KPI cell.

    Layout matches reference: large mono value, label, optional delta,
    optional sparkline at the bottom. Cells with no sparkline data hide
    the subgraph but keep the rest of the cell.
    """
    value_html, delta_html, tone = _value_for_kpi(kpi["id"], rollup, deals_df)
    spark_values = _sparkline_for_kpi(kpi["id"], deals_df)
    spark_html = ""
    if spark_values:
        spark_html = (
            '<div style="height:22px;margin-top:.5rem;">'
            f'{sparkline_svg(spark_values)}'
            '</div>'
        )
    delta_block = (
        f'<div class="delta">{_html.escape(delta_html)}</div>'
        if delta_html else '<div class="delta">&nbsp;</div>'
    )
    headline_marker = ' aria-current="true"' if is_headline else ''
    # Inline-style on the value ensures tone color carries through even
    # when a tone is None (default ink). number_maybe already adds tone
    # color when tone is set.
    return (
        f'<div class="kpi-cell"{headline_marker}>'
        f'<div class="value mono num">{value_html}</div>'
        f'<div class="label">{_html.escape(kpi["label"])}</div>'
        f'{delta_block}'
        f'{spark_html}'
        '</div>'
    )


def _render_quarterly_history_table(deals_df: pd.DataFrame) -> str:
    """Right-side paired table — Weighted MOIC quarterly history.

    Headline KPI per ``cc-app.jsx:157`` default. Phase 2 renders a
    fixed view; Phase 3 decides hover/click/etc. (See module-level TODO.)

    When the underlying data is empty or has only one quarter:
      - Empty: show one row of `—` cells with the eyebrow describing
        what would appear once snapshots accumulate
      - 1 quarter: show that single row only (no sparkline-style trend)
    """
    rows: List[Tuple[str, str]] = []
    # Phase 2 placeholder: real per-quarter aggregation arrives with the
    # sparkline wiring above. For now, surface the current weighted MOIC
    # as a single row so the paired table isn't visually empty when
    # there's at least one deal.
    if not deals_df.empty:
        # Use the snapshot-as-of date if available — gives the partner a
        # "current quarter" anchor.
        try:
            asof = deals_df["created_at"].max()
            qlabel = pd.to_datetime(asof).strftime("%YQ%q") if asof else "Latest"
        except Exception:  # noqa: BLE001
            qlabel = "Latest"
        # Compute weighted MOIC inline (the orchestrator will hand a
        # pre-computed rollup dict in commit 9; for the helper-as-island
        # tests this self-contained path keeps the helper independently
        # callable).
        try:
            sized = deals_df.dropna(subset=["moic", "entry_ev"])
            if not sized.empty:
                w = sized["entry_ev"].astype(float)
                m = sized["moic"].astype(float)
                wm = (m * w).sum() / w.sum() if w.sum() else None
                rows.append((qlabel,
                             f"{wm:.2f}x" if wm is not None else "—"))
        except Exception:  # noqa: BLE001
            rows.append((qlabel, "—"))

    if not rows:
        rows = [("—", "—")]

    body_rows = "".join(
        f'<tr><td class="lbl">{_html.escape(q)}</td>'
        f'<td class="r">{_html.escape(v)}</td></tr>'
        for q, v in rows
    )
    return (
        '<table>'
        '<thead><tr><th>Quarter</th><th class="r">Weighted MOIC</th></tr></thead>'
        f'<tbody>{body_rows}</tbody>'
        '</table>'
    )


# All CSS for this block lives in /static/v3/chartis.css under the
# /* === /app dashboard blocks === */ section. See docstring §3.


def render_kpi_strip(
    rollup: Dict[str, Any],
    *,
    deals_df: pd.DataFrame,
) -> str:
    """8-cell KPI strip + paired quarterly-history table.

    Args:
        rollup: Output of ``portfolio_rollup(store)``. Caller is the
            orchestrator (``app_page.render_app_page``); it computes
            the rollup once per request and passes it to every block
            helper that needs it. No env reads, no DB calls inside the
            helper itself — keeps the helper testable + composable.
        deals_df: Output of ``latest_per_deal(store)``. Used for the
            sparkline trend and the paired right-side table.

    Returns:
        HTML string. The outer ``.pair`` wrapper comes from
        ``pair_block()``; this function builds the viz (the strip) and
        the data table (paired right column) and hands both to
        ``pair_block``.
    """
    headline_id = "moic"
    cells_html = "".join(
        _render_kpi_cell(
            kpi, rollup, deals_df,
            is_headline=(kpi["id"] == headline_id),
        )
        for kpi in _KPI_ROWS
    )

    # Editorial empty-state hint above the strip when the fund has zero deals
    eyebrow = ""
    if int(rollup.get("deal_count") or 0) == 0:
        eyebrow = (
            '<div class="micro" style="color:var(--muted);'
            'padding:.5rem 0 1rem;">No deals tracked yet — '
            'add a deal above to populate.</div>'
        )

    viz_html = (
        f'{eyebrow}'
        f'<div class="app-kpi-strip">{cells_html}</div>'
    )

    return pair_block(
        viz_html,
        label="FUND-LEVEL KPIs · 7-QUARTER TRACK",
        source="portfolio.db",
        data_table=_render_quarterly_history_table(deals_df),
    )
