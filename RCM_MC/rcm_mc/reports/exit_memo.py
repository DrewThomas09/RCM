"""Exit-readiness memo generator (Brick 55).

At exit prep, a PE firm's job is to prove the track record to the next
owner. This module produces a self-contained HTML memo consuming:

- The deal's most-recent snapshot (entry underwriting: entry EV, hold
  years, underwritten MOIC/IRR, equity structure)
- The full quarterly actuals history (track record vs plan)
- The cumulative drift trajectory (the "we delivered on what we said" proof)
- The latest HCRIS peer percentile (remaining opportunity for the next owner)

Memo sections mirror what a buyer's QoE team asks during exit:

  1. Deal facts        — identity + entry underwrite
  2. Track record      — actual vs plan by quarter
  3. Current pace      — latest quarter + cumulative drift
  4. Remaining upside  — still-closeable gaps (peer-relative)
  5. Risk factors      — covenant headroom, concerning signals

Runs offline, produces a single HTML file an analyst can email directly.
No Chart.js / D3 — inline SVG + styles. Deliberately narrow RCM focus:
does not venture into QoE adjustments, multi-platform roll-ups, or any
non-RCM diligence concerns.
"""
from __future__ import annotations

import html
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import pandas as pd

from ..pe.hold_tracking import cumulative_drift, variance_report
from ..rcm.initiative_tracking import initiative_variance_report
from ..portfolio.store import PortfolioStore
from ..portfolio.portfolio_snapshots import list_snapshots


# ── Shared palette (matches partner brief + dashboard) ──
_PALETTE = {
    "bg": "#FAFAFA", "card": "#FFFFFF", "border": "#E5E7EB",
    "text": "#111827", "muted": "#6B7280", "accent": "#1F4E78",
    "green": "#10B981", "amber": "#F59E0B", "red": "#EF4444",
}


def _fmt_money(v: Any) -> str:
    if v is None or (isinstance(v, float) and v != v):
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
    if v is None or (isinstance(v, float) and v != v):
        return "—"
    try:
        return f"{float(v)*100:+.1f}%"
    except (TypeError, ValueError):
        return "—"


def _color_for_severity(sev: str) -> str:
    return {
        "on_track":  _PALETTE["green"],
        "lagging":   _PALETTE["amber"],
        "off_track": _PALETTE["red"],
        "no_plan":   _PALETTE["muted"],
    }.get(sev, _PALETTE["muted"])


# ── Section renderers ──────────────────────────────────────────────────────

def _render_deal_facts(snapshot: pd.Series) -> str:
    """Top block: deal identity + frozen entry underwrite."""
    rows = [
        ("Deal ID",          html.escape(str(snapshot.get("deal_id") or "?"))),
        ("Current stage",    html.escape(str(snapshot.get("stage") or "?")).title()),
        ("Entry EBITDA",     _fmt_money(snapshot.get("entry_ebitda"))),
        ("Entry EV",         _fmt_money(snapshot.get("entry_ev"))),
        ("Entry multiple",   f"{float(snapshot['entry_multiple']):.1f}x"
                             if pd.notna(snapshot.get("entry_multiple")) else "—"),
        ("Hold (years)",     f"{float(snapshot['hold_years']):g}"
                             if pd.notna(snapshot.get("hold_years")) else "—"),
        ("Underwritten MOIC", f"{float(snapshot['moic']):.2f}x"
                              if pd.notna(snapshot.get("moic")) else "—"),
        ("Underwritten IRR", (f"{float(snapshot['irr'])*100:.1f}%"
                              if pd.notna(snapshot.get("irr")) else "—")),
    ]
    cells = "".join(
        f"<tr><td class='label'>{label}</td><td class='val'>{val}</td></tr>"
        for label, val in rows
    )
    return (
        '<div class="card"><h2>Deal facts</h2>'
        f'<table class="facts-table">{cells}</table>'
        '</div>'
    )


def _render_track_record(var_df: pd.DataFrame) -> str:
    """Quarterly actual-vs-plan table. One row per (quarter, KPI) pair."""
    if var_df is None or var_df.empty:
        return (
            '<div class="card"><h2>Track record</h2>'
            '<p style="color: var(--muted);">No quarterly actuals recorded '
            'for this deal — cannot build track record.</p></div>'
        )

    # One column per quarter, one row per KPI (pivoted for readability)
    kpis_order = [
        k for k in ("ebitda", "net_patient_revenue", "idr_blended",
                    "fwr_blended", "dar_clean_days")
        if k in set(var_df["kpi"])
    ]
    quarters = sorted(var_df["quarter"].unique())

    header_cells = (
        '<th>KPI</th>'
        + "".join(f'<th>{html.escape(q)}</th>' for q in quarters)
    )
    body_rows = []
    for kpi in kpis_order:
        row_kpi = var_df[var_df["kpi"] == kpi].set_index("quarter")
        cells = [f'<td><strong>{html.escape(kpi)}</strong></td>']
        for q in quarters:
            if q in row_kpi.index:
                r = row_kpi.loc[q]
                sev = str(r.get("severity") or "no_plan")
                color = _color_for_severity(sev)
                var_pct = r.get("variance_pct")
                var_str = "—" if (var_pct is None or (isinstance(var_pct, float) and var_pct != var_pct)) else _fmt_pct(var_pct)
                cells.append(
                    f'<td style="color: {color}; font-weight: 600; text-align: center;">'
                    f'{var_str}</td>'
                )
            else:
                cells.append('<td style="color: var(--muted); text-align: center;">—</td>')
        body_rows.append(f'<tr>{"".join(cells)}</tr>')

    return (
        '<div class="card"><h2>Track record — actual vs plan (variance %)</h2>'
        '<p style="color: var(--muted); font-size: 0.85rem;">'
        'Green = on track (|Δ|&lt;5%), amber = lagging, red = off track. '
        'Each cell is one quarter\'s variance.'
        '</p>'
        '<table class="track-table">'
        f'<thead><tr>{header_cells}</tr></thead>'
        f'<tbody>{"".join(body_rows)}</tbody>'
        '</table></div>'
    )


def _render_current_pace(drift_df: pd.DataFrame) -> str:
    """Latest quarter + cumulative drift."""
    if drift_df is None or drift_df.empty:
        return ""
    latest = drift_df.iloc[-1]
    cum = latest["cumulative_drift"]
    cum_pct = (cum * 100) if cum is not None and cum == cum else None

    color = _color_for_severity(
        "off_track" if (cum is not None and abs(cum) >= 0.15)
        else ("lagging" if (cum is not None and abs(cum) >= 0.05) else "on_track")
    )
    cum_str = "—" if cum_pct is None else f"{cum_pct:+.1f}%"

    return (
        '<div class="card"><h2>Current pace</h2>'
        f'<p style="font-size: 1.1rem; margin: 0;">'
        f'Latest quarter <strong>{html.escape(str(latest["quarter"]))}</strong>: '
        f'EBITDA {_fmt_money(latest.get("actual"))} '
        f'vs plan {_fmt_money(latest.get("plan"))} '
        f'(<span style="color: {color}; font-weight: 600;">{_fmt_pct(latest.get("variance_pct"))}</span>).'
        '</p>'
        f'<p style="font-size: 1.1rem; margin: 0.5rem 0 0 0;">'
        f'Cumulative drift over <strong>{len(drift_df)}</strong> quarters: '
        f'<span style="color: {color}; font-weight: 600;">{cum_str}</span>'
        '</p>'
        '</div>'
    )


def _render_initiative_attribution(init_df: pd.DataFrame) -> str:
    """Per-initiative cumulative actual vs plan — tells the buyer which RCM
    levers the current owner actually pulled.

    Rendered only when initiative actuals exist. Sorted by variance (worst
    first) so a buyer scanning the memo sees the lagging levers — those
    are the "remaining upside" we'd emphasize in a sell-side pitch.
    """
    if init_df is None or init_df.empty:
        return ""

    rows = []
    for _, r in init_df.iterrows():
        color = _color_for_severity(str(r.get("severity") or "no_plan"))
        actual_str = f"${r['cumulative_actual']/1e6:.2f}M"
        plan_v = r.get("cumulative_plan")
        if plan_v is None or (isinstance(plan_v, float) and plan_v != plan_v):
            plan_str = "—"
            var_str = "—"
        else:
            plan_str = f"${plan_v/1e6:.2f}M"
            vp = r.get("variance_pct")
            var_str = ("—" if vp is None or (isinstance(vp, float) and vp != vp)
                       else f"{vp*100:+.1f}%")
        qtrs = int(r["quarters_active"])
        rows.append(
            f"<tr>"
            f"<td><strong>{html.escape(str(r['initiative_id']))}</strong></td>"
            f"<td class='val' style='text-align:right;'>{actual_str}</td>"
            f"<td class='val' style='text-align:right;'>{plan_str}</td>"
            f"<td style='text-align:right; color:{color}; font-weight:600;'>{var_str}</td>"
            f"<td style='text-align:right;'>{qtrs}</td>"
            f"</tr>"
        )
    return (
        '<div class="card"><h2>Initiative attribution — what drove the EBITDA delivery</h2>'
        '<p style="color: var(--muted); font-size: 0.85rem;">'
        'Cumulative actual vs pro-rated plan per RCM initiative. '
        'Lagging initiatives represent remaining upside for the next owner.'
        '</p>'
        '<table class="track-table">'
        '<thead><tr>'
        '<th>Initiative</th>'
        '<th style="text-align:right;">Actual</th>'
        '<th style="text-align:right;">Plan</th>'
        '<th style="text-align:right;">Variance</th>'
        '<th style="text-align:right;">Quarters</th>'
        '</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody>'
        '</table></div>'
    )


def _render_risk_factors(snapshot: pd.Series) -> str:
    """Covenant headroom + concerning signals — the "what could surprise buyer" box."""
    cov = snapshot.get("covenant_status")
    concerning = snapshot.get("concerning_signals")
    concerning = int(concerning) if pd.notna(concerning) else 0

    items = []
    if cov and str(cov) != "SAFE":
        color = _color_for_severity("off_track" if cov == "TRIPPED" else "lagging")
        items.append(
            f'<li><strong style="color: {color};">Covenant {html.escape(str(cov))}</strong> '
            f'(leverage {float(snapshot["covenant_leverage"]):.2f}x).</li>'
            if pd.notna(snapshot.get("covenant_leverage")) else
            f'<li><strong style="color: {color};">Covenant {html.escape(str(cov))}</strong>.</li>'
        )
    if concerning > 0:
        items.append(
            f'<li><strong>{concerning}</strong> concerning trend signal{"s" if concerning != 1 else ""} '
            'flagged on target HCRIS.</li>'
        )
    if not items:
        return (
            '<div class="card"><h2>Risk factors</h2>'
            '<p style="color: var(--green); font-weight: 600;">'
            'No material risk flags — covenant SAFE, no concerning HCRIS trend signals.'
            '</p></div>'
        )
    return (
        '<div class="card"><h2>Risk factors</h2>'
        f'<ul>{"".join(items)}</ul></div>'
    )


# ── Top-level builder ──────────────────────────────────────────────────────

_CSS = """
:root { --bg: #FAFAFA; --card: #FFFFFF; --border: #E5E7EB;
        --text: #111827; --muted: #6B7280; --accent: #1F4E78;
        --green: #10B981; --amber: #F59E0B; --red: #EF4444; }
* { box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
       margin: 0; padding: 2rem; background: var(--bg); color: var(--text); }
.container { max-width: 900px; margin: 0 auto; }
h1 { color: var(--accent); margin: 0 0 0.25rem 0; }
.subtitle { color: var(--muted); margin-bottom: 2rem; }
.card { background: var(--card); border: 1px solid var(--border);
        border-radius: 8px; padding: 1.5rem; margin-bottom: 1.5rem; }
.card h2 { margin-top: 0; color: var(--accent); }
.facts-table, .track-table { width: 100%; border-collapse: collapse; }
.facts-table td { padding: 0.4rem 0.5rem; border-bottom: 1px solid var(--border); }
.facts-table td.label { color: var(--muted); width: 45%; }
.facts-table td.val { font-weight: 600; font-variant-numeric: tabular-nums; }
.track-table th, .track-table td { padding: 0.5rem; border-bottom: 1px solid var(--border);
        font-variant-numeric: tabular-nums; }
.track-table th { text-align: center; color: var(--muted); font-weight: 600;
        background: #F3F4F6; }
.track-table th:first-child, .track-table td:first-child { text-align: left; }
ul { padding-left: 1.25rem; }
footer { color: var(--muted); font-size: 0.8rem; margin-top: 2rem; text-align: center; }
"""


def build_exit_memo(
    store: PortfolioStore,
    deal_id: str,
    out_path: str,
    title: Optional[str] = None,
) -> str:
    """Write exit-readiness HTML memo to ``out_path``. Returns the path.

    Raises ``ValueError`` if the deal has no snapshots (can't build a memo
    for a deal we've never seen).
    """
    snaps = list_snapshots(store, deal_id=deal_id)
    if snaps.empty:
        raise ValueError(f"No snapshots for deal {deal_id!r} — cannot build memo")
    snapshot = snaps.iloc[0]

    var_df = variance_report(store, deal_id)
    drift_df = cumulative_drift(store, deal_id, kpi="ebitda")
    init_df = initiative_variance_report(store, deal_id)

    body = f"""
    <div class="container">
      <h1>{html.escape(title or f'Exit-Readiness Memo — {deal_id}')}</h1>
      <div class="subtitle">
        Prepared {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} ·
        Hold-period track record for buyer diligence
      </div>

      {_render_deal_facts(snapshot)}
      {_render_track_record(var_df)}
      {_render_current_pace(drift_df)}
      {_render_initiative_attribution(init_df)}
      {_render_risk_factors(snapshot)}

      <footer>
        Generated by rcm-mc portfolio exit-memo · Track record sourced from
        deal snapshots + quarterly actuals in this portfolio store.
      </footer>
    </div>
    """

    html_doc = f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<title>{html.escape(title or f'Exit Memo — {deal_id}')}</title>
<style>{_CSS}</style>
</head><body>
{body}
</body></html>
"""
    from ..ui._html_polish import polish_tables_in_html
    html_doc = polish_tables_in_html(html_doc)

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_doc)
    return out_path
