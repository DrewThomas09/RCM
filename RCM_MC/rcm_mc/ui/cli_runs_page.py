"""CLI run history browser — `/cli-runs`.

Surfaces the simulation-run audit log written by ``rcm-mc`` runs
(infra/run_history.record_run -> ``<outdir>/runs.sqlite``). Until
this page existed the history was CLI-only; partners wanting to
see what they'd run had to drop into the terminal.

Why this page is exempt from the DealAnalysisPacket invariant:
    The CLI run history is per-outdir simulation metadata, not
    per-deal analytical content. Each row is "this rcm-mc command
    ran with this seed against this actual.yaml hash and produced
    this distribution shape." There is no deal_id; the source of
    truth is ``<outdir>/runs.sqlite``, a standalone DB outside the
    portfolio store. Same shape as /v3-status, /data/catalog,
    /models/* — portfolio-wide / system-wide metadata.

Why this page does NOT bypass PortfolioStore:
    runs.sqlite is intentionally separate from portfolio.db (per
    rcm_mc/infra/run_history.py:_get_db_path). It is part of the
    CLI-output bundle, not the portfolio. PortfolioStore's
    invariant says "every read of the portfolio DB goes through
    PortfolioStore" — runs.sqlite is not the portfolio DB. The
    sqlite3.connect inside infra/run_history.py is therefore not
    one of the 33 documented dispatcher bypasses; it's per design.

Public API::

    render_cli_runs_page(outdir, limit=50) -> str
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

from ..infra.run_history import list_runs
from ._chartis_kit import chartis_shell
from ._ui_kit import fmt_iso_date, fmt_num


_HARD_LIMIT = 500
_DEFAULT_LIMIT = 50


def _row(r: Dict[str, Any]) -> str:
    """One CLI run as a table row.

    The dict keys mirror the runs.sqlite schema. Numeric cells use
    the .num utility class (and .num.mono for tight alignment on
    the EBITDA-drag distribution columns); the timestamp truncates
    to the date so the column doesn't blow up the layout.
    """
    rid = fmt_num(r.get("id"))
    ts_raw = r.get("timestamp", "") or ""
    ts = fmt_iso_date(ts_raw)
    hospital = _html.escape(str(r.get("hospital_name") or "—")[:48])
    n_sims = fmt_num(r.get("n_sims"))
    seed = fmt_num(r.get("seed"))
    drag_mean = (
        f'<span class="num mono">{r["ebitda_drag_mean"]:+.3f}</span>'
        if r.get("ebitda_drag_mean") not in (None, 0.0)
        else '<span class="num">—</span>'
    )
    drag_p10 = (
        f'<span class="num mono">{r["ebitda_drag_p10"]:+.3f}</span>'
        if r.get("ebitda_drag_p10") not in (None, 0.0)
        else '<span class="num">—</span>'
    )
    drag_p90 = (
        f'<span class="num mono">{r["ebitda_drag_p90"]:+.3f}</span>'
        if r.get("ebitda_drag_p90") not in (None, 0.0)
        else '<span class="num">—</span>'
    )
    actual_hash = _html.escape(str(r.get("actual_config_hash") or "—")[:16])
    bench_hash = _html.escape(str(r.get("benchmark_config_hash") or "—")[:16])
    notes = _html.escape(str(r.get("notes") or "")[:60])

    return (
        '<tr>'
        f'<td style="padding:.6rem 1rem;">{rid}</td>'
        f'<td style="padding:.6rem 1rem;">{ts}</td>'
        f'<td style="padding:.6rem 1rem;">{hospital}</td>'
        f'<td style="padding:.6rem 1rem;text-align:right;">{n_sims}</td>'
        f'<td style="padding:.6rem 1rem;text-align:right;">{seed}</td>'
        f'<td style="padding:.6rem 1rem;text-align:right;">{drag_mean}</td>'
        f'<td style="padding:.6rem 1rem;text-align:right;">{drag_p10}</td>'
        f'<td style="padding:.6rem 1rem;text-align:right;">{drag_p90}</td>'
        f'<td style="padding:.6rem 1rem;font-size:.7rem;'
        f'color:var(--muted,#9ca3af);">'
        f'<code>{actual_hash}</code> / <code>{bench_hash}</code></td>'
        f'<td style="padding:.6rem 1rem;color:var(--muted,#9ca3af);'
        f'font-size:.8rem;">{notes}</td>'
        '</tr>'
    )


def _empty_state(reason: str) -> str:
    return (
        '<div style="background:var(--paper,#111827);'
        'border:1px solid var(--border,#374151);border-radius:8px;'
        'padding:2.5rem;text-align:center;color:var(--muted,#9ca3af);">'
        f'{_html.escape(reason)}'
        '</div>'
    )


def render_cli_runs_page(
    outdir: Optional[str], *, limit: int = _DEFAULT_LIMIT,
) -> str:
    """Render the CLI run-history page.

    ``outdir`` is the server's configured output root (the same one
    `/outputs/*` serves static files from). When None, the page shows
    a configuration hint instead of crashing. ``limit`` is clamped to
    [1, _HARD_LIMIT] by the caller via _clamp_int.
    """
    if not outdir:
        body = (
            '<section style="max-width:62rem;">'
            '<h1 style="margin:0 0 .5rem 0;">CLI Run History</h1>'
            '<p style="max-width:48rem;color:var(--muted,#9ca3af);'
            'margin:0 0 1rem 0;">'
            'Every <code>rcm-mc</code> simulation run gets logged to '
            '<code>&lt;outdir&gt;/runs.sqlite</code>. This page surfaces '
            'that log in a sortable table.</p>'
            + _empty_state(
                "No outputs directory configured. Start the server with "
                "--outdir <path> or set the outdir argument on build_server "
                "to enable this page."
            )
            + '</section>'
        )
        return chartis_shell(
            body,
            "CLI Run History",
            subtitle="rcm-mc simulation log",
        )

    runs = list_runs(outdir, limit=limit)

    if not runs:
        catalog_body = _empty_state(
            "No CLI runs recorded yet. Run "
            "`rcm-mc --actual <path> --benchmark <path>` to populate "
            "the history."
        )
    else:
        rows = "".join(_row(r) for r in runs)
        catalog_body = (
            '<table style="width:100%;border-collapse:collapse;'
            'border:1px solid var(--border,#374151);'
            'background:var(--paper,#1f2937);border-radius:8px;'
            'overflow:hidden;">'
            '<thead>'
            '<tr style="border-bottom:1px solid var(--border,#374151);">'
            '<th class="micro" style="padding:.55rem 1rem;text-align:left;">ID</th>'
            '<th class="micro" style="padding:.55rem 1rem;text-align:left;">When</th>'
            '<th class="micro" style="padding:.55rem 1rem;text-align:left;">Hospital</th>'
            '<th class="micro" style="padding:.55rem 1rem;text-align:right;">Sims</th>'
            '<th class="micro" style="padding:.55rem 1rem;text-align:right;">Seed</th>'
            '<th class="micro" style="padding:.55rem 1rem;text-align:right;">Drag mean</th>'
            '<th class="micro" style="padding:.55rem 1rem;text-align:right;">P10</th>'
            '<th class="micro" style="padding:.55rem 1rem;text-align:right;">P90</th>'
            '<th class="micro" style="padding:.55rem 1rem;text-align:left;">Hashes (actual / bench)</th>'
            '<th class="micro" style="padding:.55rem 1rem;text-align:left;">Notes</th>'
            '</tr></thead>'
            f'<tbody>{rows}</tbody></table>'
        )

    body = (
        '<section style="max-width:80rem;">'
        '<div style="display:flex;justify-content:space-between;'
        'align-items:baseline;margin-bottom:.75rem;">'
        '<h1 style="margin:0;">CLI Run History</h1>'
        f'<span class="micro" style="color:var(--muted,#9ca3af);">'
        f'{fmt_num(len(runs))} runs · most recent first · '
        f'limit {fmt_num(limit)}</span>'
        '</div>'
        '<p style="max-width:48rem;color:var(--muted,#9ca3af);'
        'margin:0 0 1rem 0;">'
        'Every <code>rcm-mc</code> simulation run logged in '
        '<code>&lt;outdir&gt;/runs.sqlite</code>. Drag mean / P10 / P90 '
        'are the EBITDA-drag percentiles from the run\'s Monte Carlo '
        'distribution; hashes truncate the SHA-256 of the actual.yaml / '
        'benchmark.yaml at run time so a re-run of identical configs '
        'shows the same hash pair.</p>'
        + catalog_body
        + '</section>'
    )

    return chartis_shell(
        body,
        "CLI Run History",
        subtitle="rcm-mc simulation log",
    )
