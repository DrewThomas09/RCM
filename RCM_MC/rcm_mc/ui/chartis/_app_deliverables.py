"""Deliverables — 4-column manifest grid + paired counts table.

Spec: docs/design-handoff/EDITORIAL_STYLE_PORT.md §6.11
Reference: docs/design-handoff/reference/04-command-center.html (deliverables section)

4-column grid of artifacts (HTML / CSV / JSON / XLS), each with kind
pill, filename, size + date. Paired with a manifest counts table.

Source-swap (per Phase 2 conflict C2): the reference HTML pointed at
``output v1/`` but that directory was deleted in the front-page cleanup.
This helper reads from:

  - ``analysis_runs`` SQLite table — most recent runs per deal, gives
    deal_id + run_id + as_of timestamp
  - ``exports/`` filesystem folder (best-effort) — listing of generated
    HTML / XLS / CSV / JSON artifacts

Justification for taking ``store`` directly (per Convention #1):

  Reading ``analysis_runs`` is a narrow query (latest N rows) used
  only by this helper. Pre-computing in the orchestrator wouldn't
  save work since no other helper needs it.

See module-level conventions in _app_kpi_strip.py docstring (1-6).

Empty / sparse states (per Phase 2 review):
  - Zero artifacts → "No deliverables generated yet. Run an analysis
    to populate." with link to /diligence/thesis-pipeline

# TODO(phase 3): wire to live exports/ folder + per-deal artifact
# resolution. Phase 2 ships from analysis_runs only — every recorded
# run becomes one deliverable card pointing at the HTML preview. File-
# system exports (XLS / CSV / JSON) come online once the export
# pipeline writes back to a known location.
"""
from __future__ import annotations

import html as _html
from datetime import datetime
from typing import Any, Dict, List, Optional

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.ui._chartis_kit_editorial import pair_block


def _fetch_recent_runs(
    store: PortfolioStore,
    *,
    limit: int = 8,
) -> List[Dict[str, Any]]:
    """Pull the most recent analysis_runs rows.

    Returns:
        List of dicts: {deal_id, run_id, as_of, created_at, kind}.
        Empty list when zero runs exist or the table is missing.
    """
    try:
        with store.connect() as con:
            rows = con.execute(
                """
                SELECT deal_id, run_id, as_of, created_at, model_version
                  FROM analysis_runs
                 ORDER BY created_at DESC
                 LIMIT ?
                """,
                (limit,),
            ).fetchall()
    except Exception:  # noqa: BLE001 — table may not exist yet
        return []

    out: List[Dict[str, Any]] = []
    for row in rows:
        deal_id = row[0] if not hasattr(row, "keys") else row["deal_id"]
        run_id = row[1] if not hasattr(row, "keys") else row["run_id"]
        as_of = row[2] if not hasattr(row, "keys") else row["as_of"]
        created_at = row[3] if not hasattr(row, "keys") else row["created_at"]
        out.append({
            "deal_id": deal_id,
            "run_id": run_id,
            "as_of": as_of or "",
            "created_at": created_at or "",
            "kind": "HTML",          # Phase 2: every run is an HTML packet preview
        })
    return out


def _format_size_date(created_at: str) -> str:
    """Render the size+date strip on a deliverable card.

    Phase 2 ships date-only (file size from analysis_runs requires
    an extra column or a stat() call on a known path). Phase 3 wires
    real sizes once the exports/ directory is in scope.
    """
    if not created_at:
        return "—"
    try:
        # ISO timestamps like "2026-04-15T12:34:56+00:00"
        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except Exception:  # noqa: BLE001
        return created_at[:10]  # best-effort YYYY-MM-DD prefix


def _render_card(item: Dict[str, Any]) -> str:
    kind = (item.get("kind") or "html").lower()
    deal_id = str(item.get("deal_id") or "")
    run_id = str(item.get("run_id") or "")
    href = (
        f"/analysis/{_html.escape(deal_id)}?run={_html.escape(run_id)}"
        if deal_id else "#"
    )
    name = run_id or deal_id or "(unnamed run)"
    return (
        f'<a class="app-deliv" href="{href}">'
        f'<span class="kind {kind}">{_html.escape(kind.upper())}</span>'
        f'<div class="nm">{_html.escape(name)}</div>'
        '<div class="meta">'
        f'<span>{_html.escape(deal_id)}</span>'
        f'<span>{_html.escape(_format_size_date(str(item.get("created_at") or "")))}</span>'
        '</div>'
        '</a>'
    )


def _render_counts_table(items: List[Dict[str, Any]]) -> str:
    """Paired right-side: kind counts."""
    counts: Dict[str, int] = {}
    for it in items:
        k = (it.get("kind") or "?").upper()
        counts[k] = counts.get(k, 0) + 1
    if not counts:
        body = (
            '<tr><td colspan="2" class="lbl" style="text-align:center;'
            'padding:1rem 0;font-style:italic;color:var(--muted)">'
            'No deliverables yet.</td></tr>'
        )
    else:
        body = "".join(
            f'<tr><td class="lbl">{_html.escape(kind)}</td>'
            f'<td class="r">{count}</td></tr>'
            for kind, count in sorted(counts.items())
        )
    return (
        '<table>'
        '<thead><tr><th>Kind</th><th class="r">Count</th></tr></thead>'
        f'<tbody>{body}</tbody>'
        '</table>'
    )


def render_deliverables(store: PortfolioStore) -> str:
    """4-column manifest grid + paired counts table.

    Args:
        store: PortfolioStore handle. Per Convention #1: justified
            because analysis_runs is a narrow query single-use.
    """
    items = _fetch_recent_runs(store)

    if not items:
        viz_html = (
            '<div class="app-deliv-grid">'
            '<div class="app-deliv-empty" style="grid-column: 1 / -1">'
            'No deliverables generated yet. '
            '<a href="/diligence/thesis-pipeline">Run an analysis</a> '
            'to populate.'
            '</div>'
            '</div>'
        )
    else:
        # Pad to a multiple of 4 with blank cells so the grid stays
        # rectangular even with 5 or 9 items (visual rhythm matters).
        cards = [_render_card(it) for it in items]
        # No padding needed if exactly multiple of 4
        viz_html = (
            f'<div class="app-deliv-grid">{"".join(cards)}</div>'
        )

    return pair_block(
        viz_html,
        label="DELIVERABLES · RECENT MANIFEST",
        source="analysis_runs",
        data_table=_render_counts_table(items),
    )
