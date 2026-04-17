"""Styled HTML renderers for known PE JSON payloads (UI-6).

``pe_bridge.json`` / ``pe_returns.json`` / ``pe_covenant.json`` /
``pe_hold_grid.csv`` are machine-readable outputs that, when clicked in
the output-folder index, dump raw JSON at the analyst. This module
renders each into a styled, PE-IC-ready single-page HTML summary.

Design: one function per known schema. Each returns a complete HTML
document (self-contained CSS, no external deps, auto back-link to index).

Scope: **only the canonical PE payloads**. Arbitrary JSONs still render
as raw JSON; this module isn't a generic viewer. The trade-off is a
small fleet of schema-aware renderers vs a weak generic one — the
former is what buyers actually want to read at exit prep.
"""
from __future__ import annotations

import html
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd


# ── Formatting helpers ─────────────────────────────────────────────────────

def _fmt_money(v: Any) -> str:
    if v is None:
        return "—"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "—"
    sign = "-" if f < 0 else ""
    af = abs(f)
    if af >= 1e9:
        return f"{sign}${af/1e9:.2f}B"
    if af >= 1e6:
        return f"{sign}${af/1e6:.0f}M"
    return f"{sign}${af:,.0f}"


def _fmt_pct(v: Any) -> str:
    if v is None:
        return "—"
    try:
        return f"{float(v)*100:.1f}%"
    except (TypeError, ValueError):
        return "—"


def _fmt_multi(v: Any) -> str:
    if v is None:
        return "—"
    try:
        return f"{float(v):.2f}x"
    except (TypeError, ValueError):
        return "—"


def _html_shell(body: str, title: str, *, back_href: str = "index.html") -> str:
    """Thin wrapper around the shared UI-2 shell.

    The JSON renderers build their own ``<h1>`` + ``<div class="subtitle">``
    inside ``body`` because the subtitle text is payload-dependent. We
    suppress the shell's default h1 via ``omit_h1`` so the page doesn't
    render two titles.
    """
    from ._ui_kit import shell
    return shell(
        body=body, title=title, back_href=back_href, omit_h1=True,
    )


# ── Renderers ──────────────────────────────────────────────────────────────

def render_pe_bridge(payload: Dict[str, Any]) -> str:
    """Render pe_bridge.json as a headline-card + waterfall table view."""
    components = payload.get("components") or []
    entry_ebitda = payload.get("entry_ebitda")
    exit_ebitda = payload.get("exit_ebitda") or payload.get("exit_ebitda")
    entry_ev = payload.get("entry_ev")
    exit_ev = payload.get("exit_ev")
    total_value = payload.get("total_value_created")
    hold = payload.get("hold_years")

    kpi_cards = "".join([
        f'<div class="kpi-card"><div class="kpi-value">{_fmt_money(entry_ev)}</div>'
        f'<div class="kpi-label">Entry EV</div></div>',
        f'<div class="kpi-card"><div class="kpi-value">{_fmt_money(exit_ev)}</div>'
        f'<div class="kpi-label">Exit EV</div></div>',
        f'<div class="kpi-card"><div class="kpi-value" style="color: var(--green);">'
        f'{_fmt_money(total_value)}</div>'
        f'<div class="kpi-label">Value Created</div></div>',
        f'<div class="kpi-card"><div class="kpi-value">'
        f'{html.escape(str(hold or "—"))}y</div>'
        f'<div class="kpi-label">Hold Period</div></div>',
    ])

    # Bridge waterfall — each row is a step
    rows = []
    for c in components:
        step = html.escape(str(c.get("step", "")))
        value = _fmt_money(c.get("value"))
        share = c.get("share_of_creation")
        share_str = ""
        if share is not None:
            try:
                share_str = f"{float(share)*100:+.0f}%"
            except (TypeError, ValueError):
                share_str = ""
        note = html.escape(str(c.get("note") or ""))
        endpoint = step in ("Entry EV", "Exit EV")
        weight = "font-weight: 600;" if endpoint else ""
        rows.append(
            f"<tr style='{weight}'>"
            f"<td>{step}</td>"
            f"<td class='num'>{value}</td>"
            f"<td class='num'>{share_str}</td>"
            f"<td class='muted'>{note}</td>"
            f"</tr>"
        )

    body = f"""
    <h1>Value Creation Bridge</h1>
    <div class="subtitle">
      Entry EBITDA {_fmt_money(entry_ebitda)} → Exit EBITDA {_fmt_money(exit_ebitda)}
    </div>

    <div class="kpi-grid">{kpi_cards}</div>

    <div class="card">
      <h2>Waterfall components</h2>
      <table>
        <caption class="sr-only">Value creation bridge components showing step, value, share, and basis.</caption>
        <thead><tr><th scope="col">Step</th><th scope="col">Value</th><th scope="col">Share</th><th scope="col">Basis</th></tr></thead>
        <tbody>{"".join(rows)}</tbody>
      </table>
    </div>
    """
    return _html_shell(body, title="PE Bridge")


def render_pe_returns(payload: Dict[str, Any]) -> str:
    """Render pe_returns.json as a MOIC/IRR headline card view."""
    moic = payload.get("moic")
    irr = payload.get("irr")
    equity = payload.get("entry_equity")
    proceeds = payload.get("exit_proceeds")
    hold = payload.get("hold_years")

    moic_color = (
        "var(--green)" if (moic is not None and float(moic) >= 2.5)
        else "var(--amber)" if (moic is not None and float(moic) >= 2.0)
        else "var(--red)" if moic is not None else "var(--muted)"
    )
    irr_color = (
        "var(--green)" if (irr is not None and float(irr) >= 0.25)
        else "var(--amber)" if (irr is not None and float(irr) >= 0.18)
        else "var(--red)" if irr is not None else "var(--muted)"
    )

    body = f"""
    <h1>Equity Returns</h1>
    <div class="subtitle">{html.escape(str(hold or "—"))}-year hold · equity deployed vs. proceeds</div>

    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-value" style="color: {moic_color};">{_fmt_multi(moic)}</div>
        <div class="kpi-label">MOIC</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-value" style="color: {irr_color};">{_fmt_pct(irr)}</div>
        <div class="kpi-label">IRR</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-value">{_fmt_money(equity)}</div>
        <div class="kpi-label">Entry Equity</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-value">{_fmt_money(proceeds)}</div>
        <div class="kpi-label">Exit Proceeds</div>
      </div>
    </div>

    <div class="card muted" style="font-size: 0.88rem;">
      MOIC thresholds: ≥2.5x green · ≥2.0x amber · &lt;2.0x red ·
      IRR thresholds: ≥25% green · ≥18% amber · &lt;18% red.
    </div>
    """
    return _html_shell(body, title="PE Returns")


def render_pe_covenant(payload: Dict[str, Any]) -> str:
    """Render pe_covenant.json as a leverage-status card view."""
    ebitda = payload.get("ebitda")
    debt = payload.get("debt")
    actual = payload.get("actual_leverage")
    covenant = payload.get("covenant_max_leverage")
    headroom = payload.get("covenant_headroom_turns")
    cushion_pct = payload.get("ebitda_cushion_pct")
    trip_at = payload.get("covenant_trips_at_ebitda")
    interest_cov = payload.get("interest_coverage")

    try:
        h = float(headroom) if headroom is not None else None
    except (TypeError, ValueError):
        h = None
    if h is None:
        status, cls = "UNKNOWN", "badge-amber"
    elif h >= 1.0:
        status, cls = "SAFE", "badge-green"
    elif h >= 0:
        status, cls = "TIGHT", "badge-amber"
    else:
        status, cls = "TRIPPED", "badge-red"

    cushion_str = (
        _fmt_pct(cushion_pct) if cushion_pct is not None else "—"
    )

    body = f"""
    <h1>Covenant Headroom</h1>
    <div class="subtitle">
      Actual {_fmt_multi(actual)} vs. covenant max {_fmt_multi(covenant)}
      · <span class="badge {cls}">{status}</span>
    </div>

    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-value">{_fmt_multi(actual)}</div>
        <div class="kpi-label">Actual Leverage</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-value">{_fmt_multi(covenant)}</div>
        <div class="kpi-label">Covenant Maximum</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-value">{f'{h:+.2f}x' if h is not None else '—'}</div>
        <div class="kpi-label">Headroom</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-value">{cushion_str}</div>
        <div class="kpi-label">EBITDA Cushion</div>
      </div>
    </div>

    <div class="card">
      <h2>Detail</h2>
      <table>
        <caption class="sr-only">Covenant detail values for EBITDA, total debt, covenant trip point, and interest coverage.</caption>
        <tr><th scope="row">EBITDA</th><td class="num">{_fmt_money(ebitda)}</td></tr>
        <tr><th scope="row">Total debt</th><td class="num">{_fmt_money(debt)}</td></tr>
        <tr><th scope="row">Trips at EBITDA ≤</th><td class="num">{_fmt_money(trip_at)}</td></tr>
        <tr><th scope="row">Interest coverage</th>
            <td class="num">{_fmt_multi(interest_cov) if interest_cov else '—'}</td></tr>
      </table>
    </div>
    """
    return _html_shell(body, title="PE Covenant")


def render_pe_hold_grid(rows: List[Dict[str, Any]]) -> str:
    """Render pe_hold_grid CSV rows as a 2D pivot (hold × multiple → IRR/MOIC)."""
    if not rows:
        body = '<h1>Hold-period sensitivity</h1><p class="muted">No data.</p>'
        return _html_shell(body, title="Hold-period sensitivity")

    years = sorted({int(r["hold_years"]) for r in rows})
    multiples = sorted({float(r["exit_multiple"]) for r in rows})
    by_key = {(int(r["hold_years"]), float(r["exit_multiple"])): r for r in rows}

    header_cells = "".join(
        f'<th scope="col" class="num">{m:.1f}x</th>' for m in multiples
    )
    body_rows = []
    for y in years:
        cells = [f'<th scope="row"><strong>{y}y</strong></th>']
        for m in multiples:
            r = by_key.get((y, m))
            if r is None:
                cells.append('<td class="num muted">—</td>')
                continue
            irr = r.get("irr")
            moic = r.get("moic")
            try:
                irr_str = f"{float(irr)*100:+.0f}%" if irr is not None else "—"
            except (TypeError, ValueError):
                irr_str = "—"
            try:
                moic_str = f"{float(moic):.2f}x" if moic is not None else "—"
            except (TypeError, ValueError):
                moic_str = "—"
            flag = " ⚠" if r.get("underwater") else ""
            cells.append(
                f'<td class="num">'
                f'<div style="font-weight: 600;">{irr_str}{flag}</div>'
                f'<div class="muted" style="font-size: 0.8rem;">{moic_str}</div>'
                f'</td>'
            )
        body_rows.append(f"<tr>{''.join(cells)}</tr>")

    body = f"""
    <h1>Hold-period × exit-multiple sensitivity</h1>
    <div class="subtitle">IRR (top) / MOIC (bottom) per scenario</div>

    <div class="card">
      <table>
        <caption class="sr-only">Sensitivity grid by hold period and exit multiple, with IRR and MOIC in each scenario cell.</caption>
        <thead><tr><th scope="col">Hold</th>{header_cells}</tr></thead>
        <tbody>{"".join(body_rows)}</tbody>
      </table>
      <p class="muted" style="font-size: 0.82rem; margin-top: 1rem;">
        ⚠ indicates underwater scenarios (exit equity &lt; 0).
      </p>
    </div>
    """
    return _html_shell(body, title="Hold-period sensitivity")


# ── File → HTML orchestration ──────────────────────────────────────────────

# Dispatch by filename — keeps this module declarative about which schemas
# it knows. Unknown filenames fall back to raw-JSON rendering.
_RENDERERS = {
    "pe_bridge.json":   render_pe_bridge,
    "pe_returns.json":  render_pe_returns,
    "pe_covenant.json": render_pe_covenant,
}


def render_pe_file(path: str) -> Optional[str]:
    """Load a known PE payload and return rendered HTML, or None if unknown.

    Handles both JSON (bridge/returns/covenant) and the hold-grid CSV.
    """
    name = os.path.basename(path).lower()
    if name in _RENDERERS:
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
        return _RENDERERS[name](payload)
    if name == "pe_hold_grid.csv":
        df = pd.read_csv(path)
        return render_pe_hold_grid(df.to_dict(orient="records"))
    return None


def wrap_pe_artifacts_in_folder(folder: str) -> List[str]:
    """Write an HTML companion for each known PE artifact in ``folder``.

    Returns paths written. Skips when an HTML of the same stem already
    exists (lets hand-crafted renders coexist). Never raises on unreadable
    files — a corrupt JSON just gets skipped with the error swallowed.
    """
    if not os.path.isdir(folder):
        return []
    written: List[str] = []
    for name in os.listdir(folder):
        path = os.path.join(folder, name)
        if not os.path.isfile(path):
            continue
        lower = name.lower()
        if lower not in _RENDERERS and lower != "pe_hold_grid.csv":
            continue
        stem, _ = os.path.splitext(name)
        out_path = os.path.join(folder, stem + ".html")
        if os.path.isfile(out_path):
            continue
        try:
            html_doc = render_pe_file(path)
            if html_doc is None:
                continue
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(html_doc)
            written.append(out_path)
        except (OSError, json.JSONDecodeError, ValueError, KeyError):
            continue
    return written
