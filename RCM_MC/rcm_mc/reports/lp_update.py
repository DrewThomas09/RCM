"""Standalone LP-update HTML builder (Brick 120).

The HTTP route in :mod:`rcm_mc.server` already renders an LP update,
but it reads ``self.path`` and writes to ``self.wfile``. To schedule
daily LP updates via external cron (launchd / unix cron) we need a
pure function that returns the HTML string.

This module extracts the composition logic so both callers share it.
Zero new data — just stitches together ``portfolio_rollup``,
``evaluate_active``, ``build_digest``, and ``cohort_rollup``.

Public API::

    build_lp_update_html(store, *, days=30, title="LP Update") -> str
"""
from __future__ import annotations

import html
import urllib.parse
from datetime import datetime, timedelta, timezone

from ..ui._ui_kit import shell
from ..alerts.alerts import evaluate_active
from ..analysis.cohorts import cohort_rollup
from ..portfolio.store import PortfolioStore
from ..portfolio.portfolio_digest import build_digest, digest_to_frame
from ..portfolio.portfolio_snapshots import portfolio_rollup


def _fmt(v, pct: bool = False, suffix: str = "") -> str:
    if v is None:
        return "—"
    if isinstance(v, float) and v != v:
        return "—"
    if pct:
        return f"{float(v)*100:.1f}%"
    return f"{float(v):.2f}{suffix}"


def build_lp_update_html(
    store: PortfolioStore,
    *,
    days: int = 30,
    title: str = "LP Update",
) -> str:
    """Return a full HTML document for the LP update, partner-ready."""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime(
        "%Y-%m-%d",
    )
    rollup = portfolio_rollup(store)
    alerts = evaluate_active(store)
    events_df = digest_to_frame(build_digest(store, since=since))
    cohorts_df = cohort_rollup(store)

    headline = (
        f'<div class="kpi-grid">'
        f'<div class="kpi-card"><div class="kpi-value">'
        f'{rollup["deal_count"]}</div>'
        f'<div class="kpi-label">Active deals</div></div>'
        f'<div class="kpi-card"><div class="kpi-value">'
        f'{_fmt(rollup.get("weighted_moic"), suffix="x")}</div>'
        f'<div class="kpi-label">Weighted MOIC</div></div>'
        f'<div class="kpi-card"><div class="kpi-value">'
        f'{_fmt(rollup.get("weighted_irr"), pct=True)}</div>'
        f'<div class="kpi-label">Weighted IRR</div></div>'
        f'<div class="kpi-card"><div class="kpi-value">'
        f'{rollup["covenant_trips"]}</div>'
        f'<div class="kpi-label">Covenant trips</div></div>'
        f'</div>'
    )

    red = [a for a in alerts if a.severity == "red"]
    amber = [a for a in alerts if a.severity == "amber"]
    rows = []
    for a in red + amber:
        cls = "badge-red" if a.severity == "red" else "badge-amber"
        rows.append(
            f"<li style='padding: 0.4rem 0; border-bottom: 1px solid "
            f"var(--border);'>"
            f"<span class='badge {cls}'>{a.severity.upper()}</span> "
            f"<strong>{html.escape(a.deal_id)}</strong> — "
            f"{html.escape(a.title)} "
            f"<span class='muted' style='font-size: 0.85rem;'>"
            f"{html.escape(a.detail)}</span></li>"
        )
    alerts_html = (
        f'<div class="card"><h2>Active alerts '
        f'({len(red)} red / {len(amber)} amber)</h2>'
        f'<ul style="list-style: none; padding: 0; margin: 0;">'
        f'{"".join(rows)}</ul></div>'
        if rows else
        '<div class="card"><h2>Active alerts</h2>'
        '<p class="muted">None — portfolio is clean.</p></div>'
    )

    if events_df.empty:
        activity_html = (
            f'<div class="card"><h2>Recent activity</h2>'
            f'<p class="muted">No material changes in the last '
            f'{days} days.</p></div>'
        )
    else:
        act_rows = []
        for _, r in events_df.head(30).iterrows():
            act_rows.append(
                f"<tr>"
                f"<td class='muted' style='font-size: 0.8rem;'>"
                f"{html.escape(str(r['timestamp'])[:10])}</td>"
                f"<td><strong>{html.escape(str(r['deal_id']))}</strong></td>"
                f"<td>{html.escape(str(r['change_type']))}</td>"
                f"<td class='muted' style='font-size: 0.85rem;'>"
                f"{html.escape(str(r['detail']))}</td>"
                f"</tr>"
            )
        activity_html = (
            f'<div class="card"><h2>Recent activity (last {days} days, '
            f'{len(events_df)} events)</h2>'
            f'<table><thead><tr>'
            f'<th>Date</th><th>Deal</th><th>Change</th><th>Detail</th>'
            f'</tr></thead><tbody>{"".join(act_rows)}</tbody></table></div>'
        )

    if cohorts_df.empty:
        cohort_html = ""
    else:
        cohort_rows = []
        for _, r in cohorts_df.iterrows():
            cohort_rows.append(
                f"<tr>"
                f"<td><strong>{html.escape(str(r['tag']))}</strong></td>"
                f"<td class='num'>{int(r['deal_count'])}</td>"
                f"<td class='num'>{_fmt(r['weighted_moic'], suffix='x')}</td>"
                f"<td class='num'>{_fmt(r['weighted_irr'], pct=True)}</td>"
                f"<td class='num'>{int(r['covenant_trips'])}</td>"
                f"</tr>"
            )
        cohort_html = (
            f'<div class="card"><h2>Cohort breakdown</h2>'
            f'<table><thead><tr>'
            f'<th>Cohort</th><th>Deals</th><th>W. MOIC</th>'
            f'<th>W. IRR</th><th>Trips</th>'
            f'</tr></thead><tbody>{"".join(cohort_rows)}</tbody></table></div>'
        )

    body = headline + alerts_html + activity_html + cohort_html
    return shell(
        body=body, title=title,
        subtitle=f"Portfolio snapshot · window {days} days",
    )
