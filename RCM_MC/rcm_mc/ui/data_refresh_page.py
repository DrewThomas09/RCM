"""Data refresh UI — `/data/refresh`.

Table of known sources with current freshness + per-source Refresh
buttons + a Refresh All button. Clicks enqueue background jobs via
``POST /api/data/refresh/<source>/async``; status chips update in
place by polling ``GET /api/jobs/<id>`` every 2 s.

Single-dyno-friendly: the inline JS doesn't need websockets, the
backend runs the refresh on the in-process job worker thread (lazy-
started on first submit, see ``infra.job_queue``).

Public API:
    render_data_refresh_page(db_path: str) -> str
"""
from __future__ import annotations

import html as _html
from datetime import datetime, timezone
from typing import Any, Dict, List


def _freshness_chip(last_refreshed_iso: str | None) -> str:
    if not last_refreshed_iso:
        return ('<span style="display:inline-block;padding:2px 8px;'
                'border-radius:4px;background:#f3f4f6;color:#6b7280;'
                'font-size:11px;">never</span>')
    try:
        ts = datetime.fromisoformat(last_refreshed_iso.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
    except ValueError:
        return ('<span style="color:#6b7280;font-size:11px;">'
                'unparseable</span>')
    days = (datetime.now(timezone.utc) - ts).days
    if days < 7:
        bg, fg = "#d1fae5", "#065f46"
    elif days < 30:
        bg, fg = "#fef3c7", "#92400e"
    else:
        bg, fg = "#fee2e2", "#991b1b"
    return (f'<span style="display:inline-block;padding:2px 8px;'
            f'border-radius:4px;background:{bg};color:{fg};'
            f'font-size:11px;font-weight:500;">{days}d ago</span>')


def _source_row(source_name: str, status: Dict[str, Any]) -> str:
    name = _html.escape(source_name)
    last = status.get("last_refresh_at")
    records = int(status.get("record_count") or 0)
    st = str(status.get("status") or "unknown")
    return (
        f'<tr data-source="{name}">'
        f'<td style="font-weight:500;">{name}</td>'
        f'<td>{_freshness_chip(last)}</td>'
        f'<td style="color:#6b7280;font-size:12px;font-variant-numeric:tabular-nums;">'
        f'{records:,}</td>'
        f'<td style="color:#6b7280;font-size:12px;">{_html.escape(st)}</td>'
        f'<td class="job-status" style="font-size:12px;">—</td>'
        f'<td style="text-align:right;">'
        f'<button class="refresh-btn" data-source="{name}" '
        f'style="background:#1F4E78;color:#fff;border:none;padding:5px 12px;'
        f'border-radius:4px;font-size:12px;cursor:pointer;">Refresh</button>'
        f'</td>'
        f'</tr>'
    )


# Inline JS — deliberately small; polls /api/jobs/<id> every 2 s.
_CLIENT_JS = r"""
(function() {
    function setStatus(row, html) {
        const cell = row.querySelector('.job-status');
        if (cell) cell.innerHTML = html;
    }
    function disableButton(row, text) {
        const btn = row.querySelector('.refresh-btn');
        if (btn) { btn.disabled = true; btn.textContent = text; btn.style.opacity = '0.6'; }
    }
    function enableButton(row) {
        const btn = row.querySelector('.refresh-btn');
        if (btn) { btn.disabled = false; btn.textContent = 'Refresh'; btn.style.opacity = '1'; }
    }
    function poll(jobId, row) {
        fetch('/api/jobs/' + encodeURIComponent(jobId), {credentials: 'same-origin'})
            .then(r => r.json())
            .then(j => {
                if (j.status === 'queued') {
                    setStatus(row, '<span style="color:#6b7280;">● queued</span>');
                    setTimeout(() => poll(jobId, row), 2000);
                } else if (j.status === 'running') {
                    setStatus(row, '<span style="color:#f59e0b;">● running</span>');
                    setTimeout(() => poll(jobId, row), 2000);
                } else if (j.status === 'done') {
                    const rc = (j.result && j.result.total_records) || 0;
                    setStatus(row, '<span style="color:#10b981;">✓ done — ' + rc.toLocaleString() + ' rows</span>');
                    enableButton(row);
                    // Reload freshness chip after 1 s so the table shows the fresh timestamp
                    setTimeout(() => window.location.reload(), 1200);
                } else if (j.status === 'failed') {
                    const err = (j.error || '').split('\n')[0].slice(0, 80);
                    setStatus(row, '<span style="color:#ef4444;" title="' + err.replace(/"/g, '&quot;') + '">✗ failed</span>');
                    enableButton(row);
                } else {
                    setStatus(row, '<span style="color:#6b7280;">' + j.status + '</span>');
                    setTimeout(() => poll(jobId, row), 2000);
                }
            })
            .catch(err => {
                setStatus(row, '<span style="color:#ef4444;">poll error</span>');
                enableButton(row);
            });
    }
    function submitRefresh(source, row) {
        disableButton(row, 'submitting…');
        setStatus(row, '<span style="color:#6b7280;">● submitting…</span>');
        fetch('/api/data/refresh/' + encodeURIComponent(source) + '/async', {
            method: 'POST',
            credentials: 'same-origin',
            headers: {'Content-Type': 'application/json'},
        })
            .then(r => r.json().then(j => ({status: r.status, body: j})))
            .then(({status, body}) => {
                if (status === 202 && body.job_id) {
                    disableButton(row, 'refreshing…');
                    poll(body.job_id, row);
                } else if (status === 429) {
                    setStatus(row, '<span style="color:#f59e0b;">rate limited (' + (body.detail?.retry_after_seconds || '?') + 's)</span>');
                    enableButton(row);
                } else {
                    setStatus(row, '<span style="color:#ef4444;">' + (body.error || 'error') + '</span>');
                    enableButton(row);
                }
            })
            .catch(err => {
                setStatus(row, '<span style="color:#ef4444;">network error</span>');
                enableButton(row);
            });
    }
    document.addEventListener('click', function(e) {
        const btn = e.target.closest('.refresh-btn');
        if (!btn || btn.disabled) return;
        const row = btn.closest('tr[data-source]');
        const source = btn.getAttribute('data-source') || row.getAttribute('data-source');
        if (source) submitRefresh(source, row);
    });
})();
"""


def render_data_refresh_page(db_path: str) -> str:
    from ._chartis_kit import chartis_shell
    from . import _web_components as _wc

    header = _wc.page_header(
        "Data refresh",
        subtitle=("Pull fresh data from CMS HCRIS, Care Compare, IRS 990, "
                  "and other public sources. Each refresh runs in the "
                  "background — click, wait for the status chip, done. "
                  "Rate-limited to 1 refresh per source per hour."),
        crumbs=[("Dashboard", "/dashboard"), ("Data refresh", None)],
    )

    # Pull status rows from the data_source_status table.
    rows_html: List[str] = []
    known: List[str] = []
    try:
        from ..data.data_refresh import KNOWN_SOURCES, get_status
        from ..portfolio.store import PortfolioStore
        store = PortfolioStore(db_path)
        existing = {r["source_name"]: r for r in get_status(store)}
        known = list(KNOWN_SOURCES)
        for name in known:
            rows_html.append(_source_row(name, existing.get(name, {})))
    except Exception as exc:  # noqa: BLE001
        err_card = _wc.section_card(
            "Data source status unavailable",
            (f'<p>Could not load data-source status '
             f'(<code>{_html.escape(type(exc).__name__)}</code>). '
             f'The <code>data_source_status</code> table may not exist yet — '
             f'run <code>rcm-mc data refresh</code> once from the CLI to '
             f'populate it.</p>'),
        )
        body = (
            _wc.web_styles()
            + _wc.responsive_container(header + err_card)
        )
        return chartis_shell(body, "Data refresh",
                             active_nav="/data/refresh")

    table = (
        '<input type="search" class="wc-filter" '
        'data-filter-for="data-sources" '
        'placeholder="Filter sources…" aria-label="Filter sources">'
        '<table class="wc-table wc-sortable" id="data-sources">'
        '<thead><tr>'
        '<th data-col="0" title="Data source identifier">Source</th>'
        '<th data-col="1" title="Days since last successful refresh">Freshness</th>'
        '<th data-col="2" class="wc-hide-sm" title="Row count at last refresh">Rows</th>'
        '<th data-col="3" class="wc-hide-sm" title="OK / STALE / ERROR">Status</th>'
        '<th data-col="4" title="Current async refresh job state">Job</th>'
        '<th data-col="5" style="text-align:right;">Action</th>'
        '</tr></thead><tbody>' + "".join(rows_html) + '</tbody></table>'
    )

    actions = (
        '<div style="margin-top:20px;">'
        '<button class="refresh-btn wc-btn wc-btn-primary" data-source="all" '
        'style="background:#064e3b;border-color:#064e3b;">'
        'Refresh all sources</button>'
        '<span id="refresh-all-spinner" class="wc-spinner" '
        'style="margin-left:12px;"></span>'
        '<span style="color:#6b7280;font-size:12px;margin-left:12px;">'
        'Triggers a background job per source; watch the Job column above.'
        '</span></div>'
    )

    sources_card = _wc.section_card("Known data sources", table + actions,
                                    pad=True)

    body = (
        _wc.web_styles()
        + _wc.responsive_container(header + sources_card)
        + _wc.sortable_table_js()
        + _wc.spinner_js()
        + f'<script>{_CLIENT_JS}</script>'
    )
    return chartis_shell(body, "Data refresh",
                         active_nav="/data/refresh")
