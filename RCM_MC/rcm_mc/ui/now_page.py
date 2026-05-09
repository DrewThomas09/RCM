"""30-second view — ``/now``.

PROMPTS.md Phase 4 / Prompt 54: a partner with 30 seconds before a
meeting needs one page that summarises what needs their attention
right now. Five lines, no clicks, fits above the fold on 1280×800.

Lines:

1. Active alerts requiring attention (count + worst severity)
2. Deals with deadlines this week (count + names)
3. Headline metric on each active deal (one line each)
4. Next decision required (next IC, next LP update, next snapshot)
5. Anything weird (newly-flagged risks, freshly-deteriorated health)

The implementation reads from the existing portfolio tables; if a
table is empty the line falls through to a muted "—" placeholder
rather than rendering empty space.
"""
from __future__ import annotations

import html as _html
import sqlite3
from datetime import datetime, timedelta, timezone


def _alerts_line(con: sqlite3.Connection) -> str:
    try:
        rows = con.execute(
            "SELECT severity, COUNT(*) FROM alerts "
            "WHERE acked_at IS NULL GROUP BY severity"
        ).fetchall()
    except sqlite3.OperationalError:
        return "<li class='muted'>Alerts — table not yet created.</li>"
    if not rows:
        return "<li class='muted'>Alerts — none active.</li>"
    by_sev = {r[0]: r[1] for r in rows}
    total = sum(by_sev.values())
    worst = (
        "RED" if "red" in by_sev else
        "AMBER" if "amber" in by_sev else
        "GREEN"
    )
    return (
        f"<li><strong>{total}</strong> active alerts "
        f"<span class='muted'>(worst: {worst})</span></li>"
    )


def _deadlines_line(con: sqlite3.Connection) -> str:
    end = (datetime.now(timezone.utc) + timedelta(days=7)).date().isoformat()
    today = datetime.now(timezone.utc).date().isoformat()
    try:
        rows = con.execute(
            "SELECT deal_id, due_date FROM deal_deadlines "
            "WHERE due_date BETWEEN ? AND ? AND completed_at IS NULL "
            "ORDER BY due_date LIMIT 5",
            (today, end),
        ).fetchall()
    except sqlite3.OperationalError:
        return "<li class='muted'>Deadlines — table not yet created.</li>"
    if not rows:
        return "<li class='muted'>Deadlines — none this week.</li>"
    names = ", ".join(_html.escape(str(r[0])) for r in rows)
    return (
        f"<li><strong>{len(rows)}</strong> deadlines this week "
        f"<span class='muted'>({names})</span></li>"
    )


def _deal_headlines_line(con: sqlite3.Connection) -> str:
    try:
        rows = con.execute(
            "SELECT deal_id, name FROM deals "
            "WHERE archived_at IS NULL "
            "ORDER BY created_at DESC LIMIT 5"
        ).fetchall()
    except sqlite3.OperationalError:
        return "<li class='muted'>Active deals — table not yet created.</li>"
    if not rows:
        return "<li class='muted'>Active deals — none.</li>"
    items = ", ".join(
        f"{_html.escape(r[1] or r[0])}" for r in rows
    )
    return (
        f"<li><strong>{len(rows)}</strong> active deals "
        f"<span class='muted'>({items})</span></li>"
    )


def _next_decision_line(con: sqlite3.Connection) -> str:
    # Pull the closest-future deadline of any kind; if none, fall back
    # to "no decisions queued."
    today = datetime.now(timezone.utc).date().isoformat()
    try:
        r = con.execute(
            "SELECT deal_id, due_date, kind FROM deal_deadlines "
            "WHERE due_date >= ? AND completed_at IS NULL "
            "ORDER BY due_date ASC LIMIT 1",
            (today,),
        ).fetchone()
    except sqlite3.OperationalError:
        return "<li class='muted'>Next decision — pending.</li>"
    if not r:
        return "<li class='muted'>Next decision — none queued.</li>"
    return (
        f"<li>Next decision: <strong>{_html.escape(str(r[2] or r[0]))}"
        f"</strong> on {_html.escape(str(r[1]))}</li>"
    )


def _weird_line(con: sqlite3.Connection) -> str:
    # "Anything weird" reads from the most-recent audit events that
    # carry a "flag"-shaped kind. Fall through gracefully if the
    # audit table doesn't exist yet.
    try:
        r = con.execute(
            "SELECT COUNT(*) FROM audit_events "
            "WHERE kind LIKE 'risk_flag%' "
            "OR kind LIKE 'health_drop%'"
        ).fetchone()
    except sqlite3.OperationalError:
        return "<li class='muted'>No anomalies surfaced.</li>"
    n = r[0] if r else 0
    if not n:
        return "<li class='muted'>No anomalies surfaced.</li>"
    return (
        f"<li>{n} anomalies surfaced "
        f"<span class='muted'>(risk flags + health drops)</span></li>"
    )


def render_now(db_path: str) -> str:
    """Render the 30-second view. Five aggregations, one ``<ul>``."""
    from ._chartis_kit import chartis_shell

    try:
        con = sqlite3.connect(db_path)
        con.execute("PRAGMA busy_timeout = 5000")
        lines = [
            _alerts_line(con),
            _deadlines_line(con),
            _deal_headlines_line(con),
            _next_decision_line(con),
            _weird_line(con),
        ]
        con.close()
    except sqlite3.OperationalError as e:
        lines = [f"<li class='muted'>Database unavailable: {_html.escape(str(e))}</li>"]

    body = (
        '<h1 class="page-title">Now</h1>'
        '<div class="page-subtitle">Everything that needs your '
        'attention before this meeting.</div>'
        '<ul class="now-list" data-now-list>'
        f'{"".join(lines)}'
        '</ul>'
        '<style>'
        '.now-list { list-style:none; padding:0; margin:18px 0; '
        'font-size:15px; line-height:2; }'
        '.now-list .muted { color:var(--sc-text-faint); '
        'font-family:var(--sc-mono); font-size:13px; }'
        '.now-list strong { font-family:var(--sc-mono); '
        'font-variant-numeric:tabular-nums; color:var(--sc-navy); }'
        '</style>'
    )
    return chartis_shell(body, "Now", active_nav="/now")
