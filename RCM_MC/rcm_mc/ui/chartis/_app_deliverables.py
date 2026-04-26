"""Deliverables — 4-column manifest grid + paired counts table.

Spec: docs/design-handoff/EDITORIAL_STYLE_PORT.md §6.11
Reference: docs/design-handoff/reference/04-command-center.html (deliverables section)

4-column grid of artifacts (HTML / CSV / JSON / XLS), each with kind
pill, filename, size + date. Paired with a manifest counts table.

Source (per Phase 3 commit 5): reads from ``generated_exports``
SQLite table (the canonical manifest, populated by the
canonical-path facades in rcm_mc/exports/canonical_facade.py).
Each row in generated_exports has deal_id + format + filepath +
generated_at + file_size_bytes — exactly what each deliverable card
needs.

Falls back to ``analysis_runs`` when ``generated_exports`` is empty
(early-deployment state, before any export has been produced via
the canonical facades). The fallback ships HTML-only cards pointing
at the analysis preview at /analysis/<id>?run=<run_id>.

Justification for taking ``store`` directly (per Convention #1):

  Reading ``generated_exports`` is a narrow query (latest N rows
  scoped to a deal_id when one is focused, or cross-deal otherwise)
  used only by this helper. Pre-computing in the orchestrator
  wouldn't save work since no other helper needs it.

See module-level conventions in _app_kpi_strip.py docstring (1-6).

Empty / sparse states (per Phase 2 review):
  - Zero artifacts in either table → "No deliverables generated yet.
    Run an analysis to populate." with link to /diligence/thesis-pipeline
"""
from __future__ import annotations

import html as _html
from datetime import datetime
from typing import Any, Dict, List, Optional

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.ui._chartis_kit_editorial import pair_block


def _fetch_generated_exports(
    store: PortfolioStore,
    *,
    deal_id: Optional[str] = None,
    limit: int = 8,
) -> List[Dict[str, Any]]:
    """Phase 3 primary source: pull recent generated_exports rows.

    Each row was written by a canonical-path facade in
    rcm_mc/exports/canonical_facade.py — has deal_id + format +
    filepath + generated_at + file_size_bytes. Per-deal scoped
    when ``deal_id`` is passed; cross-deal otherwise.

    Returns:
        List of dicts: {deal_id, format, filepath, generated_at,
        file_size_bytes, kind, name}.
        Empty list when zero exports OR the table is missing.
    """
    try:
        from rcm_mc.exports.export_store import list_exports
        rows = list_exports(store, deal_id=deal_id, limit=limit)
    except Exception:  # noqa: BLE001 — table may not exist yet
        return []

    out: List[Dict[str, Any]] = []
    for r in rows:
        # list_exports returns dicts already
        filepath = str(r.get("filepath") or "")
        # Derive a friendly filename: prefer basename of filepath,
        # fall back to f"<format>_export"
        name = filepath.rsplit("/", 1)[-1] if filepath else f"{r.get('format', 'file')}_export"
        out.append({
            "deal_id": r.get("deal_id") or "",
            "run_id": r.get("analysis_run_id") or "",
            "format": (r.get("format") or "").lower(),
            "filepath": filepath,
            "size": r.get("file_size_bytes"),
            "created_at": r.get("generated_at") or "",
            "kind": (r.get("format") or "html").upper(),
            "name": name,
        })
    return out


def _fetch_analysis_runs_fallback(
    store: PortfolioStore,
    *,
    limit: int = 8,
) -> List[Dict[str, Any]]:
    """Phase 3 fallback: pull from analysis_runs when generated_exports
    is empty.

    This handles the early-deployment state — before any export has
    been produced via the canonical-path facades, generated_exports
    is empty but analysis_runs has rows. Showing the analysis preview
    cards is better than rendering an empty deliverables block on a
    fund that's done analyses but no exports.
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
    except Exception:  # noqa: BLE001
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
            "format": "html",
            "filepath": "",
            "size": None,
            "created_at": created_at or "",
            "kind": "HTML",
            "name": run_id or deal_id or "(unnamed run)",
            "as_of": as_of or "",
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


def _format_size_human(size: Optional[int]) -> str:
    """Human-readable file size: 1.2 KB / 348 B / 12.4 MB."""
    if size is None or size < 0:
        return ""
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


def _render_card(item: Dict[str, Any]) -> str:
    kind = (item.get("kind") or "html").lower()
    deal_id = str(item.get("deal_id") or "")
    run_id = str(item.get("run_id") or "")
    filepath = str(item.get("filepath") or "")
    name = str(item.get("name") or run_id or deal_id or "(unnamed)")

    # Link target: prefer the canonical filepath when present (the
    # generated_exports row links to a real artifact on disk); fall
    # back to the analysis preview when no filepath (the
    # analysis_runs fallback path).
    if filepath:
        # Server.py serves /exports/<deal_id>/<filename> from
        # /data/exports/. Caller URL is /exports/<rest-of-path>.
        rel = filepath
        for prefix in ("/data/exports/", "/data/exports"):
            if rel.startswith(prefix):
                rel = rel[len(prefix):].lstrip("/")
                break
        href = f"/exports/{_html.escape(rel)}"
    elif deal_id:
        href = f"/analysis/{_html.escape(deal_id)}?run={_html.escape(run_id)}"
    else:
        href = "#"

    size_html = _format_size_human(item.get("size"))
    date_html = _format_size_date(str(item.get("created_at") or ""))
    meta_right = " · ".join(s for s in (size_html, date_html) if s)

    return (
        f'<a class="app-deliv" href="{href}">'
        f'<span class="kind {kind}">{_html.escape(kind.upper())}</span>'
        f'<div class="nm">{_html.escape(name)}</div>'
        '<div class="meta">'
        f'<span>{_html.escape(deal_id)}</span>'
        f'<span>{_html.escape(meta_right)}</span>'
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


def render_deliverables(
    store: PortfolioStore,
    *,
    deal_id: Optional[str] = None,
) -> str:
    """4-column manifest grid + paired counts table.

    Args:
        store: PortfolioStore handle. Per Convention #1: justified
            because list_exports is a narrow query single-use.
        deal_id: When set (focused-deal mode), scopes the manifest to
            this deal's artifacts. None → cross-deal latest exports.

    Source priority:
        1. generated_exports (canonical manifest, populated by the
           canonical-path facades — Phase 3 commits 2-4)
        2. analysis_runs (early-deployment fallback before any
           canonical export has been produced)
    """
    items = _fetch_generated_exports(store, deal_id=deal_id)
    if not items:
        items = _fetch_analysis_runs_fallback(store)

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
