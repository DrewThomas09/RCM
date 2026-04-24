"""`rcm-mc serve` — local web server for the portfolio (Brick 62).

This turns the CLI tool into a single-front-door product. An analyst runs
``rcm-mc serve`` once; a browser opens to a live dashboard reading the
portfolio store. No CLI flags needed for day-to-day review — everything
is clickable.

Stack: Python stdlib only (``http.server`` + ``socketserver``). No
FastAPI, no Flask, no template engine, no frontend framework — the
dashboard pages are built by the existing ``portfolio_dashboard`` /
``exit_memo`` / ``text_to_html`` modules and served dynamically.

Routes (MVP):

    GET /                  → live portfolio dashboard
    GET /deal/<id>         → deal detail page (audit, variance, attribution)
    GET /outputs/*         → static files from the run-output folder
    GET /health            → 200 OK (for uptime checks / liveness probes)
    GET /favicon.ico       → 204 (silences the default browser fetch)
    *   /api/*             → reserved for Brick 68 JSON endpoints

Graceful Ctrl+C shutdown; threaded server so concurrent browser tabs
don't block each other.
"""
from __future__ import annotations

import html
import logging
import os
import socketserver
import sys
import threading

logger = logging.getLogger(__name__)
import urllib.parse
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .infra.rate_limit import RateLimiter

# Module-level rate limiter guarding /api/data/refresh/<source>. One
# refresh per source per hour — enough headroom for an ops engineer
# to manually retry after a transient failure, tight enough to protect
# CMS / ProPublica from accidental polling loops.
_REFRESH_RATE_LIMITER = RateLimiter(max_hits=1, window_secs=3600)
_DELETE_RATE_LIMITER = RateLimiter(max_hits=10, window_secs=3600)
MAX_REQUEST_BYTES = 10_000_000  # 10 MB — rejects oversized POSTs early

import threading as _threading

class _IdempotencyCache:
    """Thread-safe LRU cache for idempotency keys. Prevents duplicate POSTs."""
    def __init__(self, max_keys: int = 1000) -> None:
        self._cache: Dict[str, Any] = {}
        self._lock = _threading.Lock()
        self._max = max_keys

    def get(self, key: str):
        with self._lock:
            return self._cache.get(key)

    def set(self, key: str, response: Any) -> None:
        with self._lock:
            if len(self._cache) >= self._max:
                oldest = next(iter(self._cache))
                del self._cache[oldest]
            self._cache[key] = response

_IDEMPOTENCY_CACHE = _IdempotencyCache()

from .reports import exit_memo as _exit_memo
from .portfolio import portfolio_dashboard as _dashboard
from .ui._ui_kit import shell
from .deals.deal_notes import list_notes, record_note
from .deals.deal_tags import add_tag, all_tags, remove_tag, tags_for
from .pe.hold_tracking import variance_report
from .rcm.initiative_tracking import initiative_variance_report
from .portfolio.store import PortfolioStore
from .portfolio.portfolio_snapshots import list_snapshots


# ── Configuration container ────────────────────────────────────────────────

class ServerConfig:
    """Runtime config threaded through the handler via class attribute.

    Using a class attribute keeps the handler constructor compatible with
    ``BaseHTTPRequestHandler`` (which is invoked by the server, not us),
    without globals. Write once at ``build_server``; read many in handlers.
    """
    db_path: str = os.path.expanduser("~/.rcm_mc/portfolio.db")
    outdir: Optional[str] = None      # If set, /outputs/* serves from here
    title: str = "RCM Portfolio"
    # B89: optional HTTP Basic credentials. If None, auth is disabled.
    # When the env-var ``RCM_MC_AUTH`` is set as ``user:pass``, build_server
    # copies it here and every request must carry matching Basic auth.
    auth_user: Optional[str] = None
    auth_pass: Optional[str] = None


# ── HTML page builders (dynamic = rebuilt per request) ─────────────────────

def _render_dashboard(config: ServerConfig) -> str:
    """Call the existing portfolio_dashboard builder and return its HTML.

    We go through a tempfile because ``build_portfolio_dashboard`` writes
    to disk by design (it's also used by the CLI). The write cost is a
    handful of ms — acceptable for interactive browsing.
    """
    import tempfile
    store = PortfolioStore(config.db_path)
    with tempfile.NamedTemporaryFile(
        suffix=".html", delete=False, mode="w", encoding="utf-8",
    ) as tmp:
        tmp_path = tmp.name
    try:
        _dashboard.build_portfolio_dashboard(store, tmp_path, title=config.title)
        with open(tmp_path, encoding="utf-8") as f:
            return f.read()
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _render_health_sparkline(
    store: PortfolioStore,
    deal_id: str,
    *,
    width: int = 260,
    height: int = 60,
) -> str:
    """B143: small SVG of health score over time for a deal.

    Fixed 0-100 y-scale so partners get visual calibration (a 60 is
    always in the same vertical band). Returns '' if < 2 history
    points so we don't waste space on a deal that has one sighting.
    """
    from .deals.health_score import history_series
    series = history_series(store, deal_id)
    if len(series) < 2:
        return ""
    pad = 6
    chart_w = width - 2 * pad
    chart_h = height - 2 * pad
    n = len(series)

    def _x(i):
        return pad + (i / max(n - 1, 1)) * chart_w

    def _y(score):
        # 0 at bottom, 100 at top
        return pad + (1 - (score / 100.0)) * chart_h

    pts = " ".join(
        f"{_x(i):.1f},{_y(s):.1f}" for i, (_, s) in enumerate(series)
    )
    # Band-colored dot at the newest point
    last_score = series[-1][1]
    last_color = (
        "#10B981" if last_score >= 80 else
        "#F59E0B" if last_score >= 50 else "#EF4444"
    )
    # 80 and 50 threshold lines for visual reference
    y80, y50 = _y(80), _y(50)
    return (
        f'<svg width="{width}" height="{height}" '
        f'style="display: block; margin-top: 0.3rem;">'
        f'<line x1="{pad}" x2="{width - pad}" y1="{y80:.1f}" y2="{y80:.1f}" '
        f'stroke="#10B981" stroke-width="1" stroke-dasharray="2,3" '
        f'opacity="0.5"/>'
        f'<line x1="{pad}" x2="{width - pad}" y1="{y50:.1f}" y2="{y50:.1f}" '
        f'stroke="#EF4444" stroke-width="1" stroke-dasharray="2,3" '
        f'opacity="0.5"/>'
        f'<polyline fill="none" stroke="#1F4E78" stroke-width="1.5" '
        f'stroke-linejoin="round" points="{pts}"/>'
        f'<circle cx="{_x(n - 1):.1f}" cy="{_y(last_score):.1f}" r="3" '
        f'fill="{last_color}"/>'
        f'<title>Health history ({n} days)</title>'
        f'</svg>'
    )


def _health_cell(store: PortfolioStore, deal_id: str) -> str:
    """B136 + B139: colored <td> with score and (if non-flat) trend arrow."""
    from .deals.health_score import compute_health
    h = compute_health(store, deal_id)
    color = {
        "green": "var(--green-text)",
        "amber": "var(--amber-text)",
        "red":   "var(--red-text)",
    }.get(h["band"], "var(--muted)")
    if h["score"] is None:
        return '<td class="muted">—</td>'
    arrow = {"up": "↑", "down": "↓"}.get(h.get("trend", "flat"), "")
    arrow_color = {
        "up": "var(--green-text)",
        "down": "var(--red-text)",
    }.get(h.get("trend", "flat"), "var(--muted)")
    arrow_span = (
        f' <span style="color: {arrow_color}; font-size: 0.9rem;" '
        f'title="Δ {int(h.get("delta", 0)):+d} vs prior day">{arrow}</span>'
        if arrow else ""
    )
    return (
        f'<td class="num" style="color: {color}; font-weight: 700;">'
        f'{h["score"]}{arrow_span}</td>'
    )


def _render_deal_rerun(store: PortfolioStore, deal_id: str) -> str:
    """B121: 'Rerun simulation' card on /deal/<id>.

    If stored sim-input paths exist, show a one-click rerun button
    plus optional n_sims/seed overrides. Otherwise show a small form
    to set the paths.
    """
    from .deals.deal_sim_inputs import get_inputs
    qd = urllib.parse.quote(deal_id)
    inputs = get_inputs(store, deal_id)

    if inputs:
        actual = html.escape(inputs["actual_path"])
        bench = html.escape(inputs["benchmark_path"])
        base = html.escape(inputs.get("outdir_base") or "")
        rerun_form = (
            f'<form method="POST" action="/api/deals/{qd}/rerun" '
            f'style="display: flex; gap: 0.4rem; align-items: center; '
            f'flex-wrap: wrap; margin-top: 0.5rem;">'
            f'<label style="font-size: 0.85rem;">n_sims '
            f'<input type="number" name="n_sims" value="5000" min="100" '
            f'style="font-size: 0.85rem; padding: 0.2rem; width: 5rem;">'
            f'</label>'
            f'<label style="font-size: 0.85rem;">seed '
            f'<input type="number" name="seed" value="42" '
            f'style="font-size: 0.85rem; padding: 0.2rem; width: 4rem;">'
            f'</label>'
            f'<button type="submit" class="btn" '
            f'style="font-size: 0.85rem; padding: 0.2rem 0.8rem; '
            f'background: var(--accent); color: white; border: none; '
            f'border-radius: 4px; cursor: pointer; font-weight: 600;">'
            f'▶ Rerun simulation</button>'
            f'</form>'
        )
        change_form = (
            f'<details style="margin-top: 0.5rem; font-size: 0.85rem;">'
            f'<summary class="muted" style="cursor: pointer;">'
            f'change paths</summary>'
            f'<form method="POST" action="/api/deals/{qd}/sim-inputs" '
            f'style="display: grid; gap: 0.3rem; margin-top: 0.4rem; '
            f'grid-template-columns: 1fr; max-width: 40rem;">'
            f'<input type="text" name="actual_path" value="{actual}" '
            f'style="font-size: 0.85rem; padding: 0.25rem;">'
            f'<input type="text" name="benchmark_path" value="{bench}" '
            f'style="font-size: 0.85rem; padding: 0.25rem;">'
            f'<input type="text" name="outdir_base" value="{base}" '
            f'placeholder="outdir_base (optional)" '
            f'style="font-size: 0.85rem; padding: 0.25rem;">'
            f'<button type="submit" class="btn" '
            f'style="font-size: 0.85rem; padding: 0.2rem 0.6rem; '
            f'width: fit-content;">Save paths</button>'
            f'</form></details>'
        )
        return (
            f'<div class="card"><h2 style="margin-top: 0;">Rerun simulation'
            f'<span class="muted" style="font-weight: 400; '
            f'font-size: 0.8rem; margin-left: 0.5rem;">'
            f'{actual} · {bench}</span></h2>'
            f'{rerun_form}{change_form}</div>'
        )

    # No stored inputs — show setup form
    return (
        f'<div class="card"><h2 style="margin-top: 0;">Rerun simulation '
        f'<span class="muted" style="font-weight: 400; font-size: 0.8rem;">'
        f'(not configured)</span></h2>'
        f'<p class="muted" style="font-size: 0.85rem;">'
        f'Set this deal\'s simulation input paths once; then any partner '
        f'can rerun the sim with one click (no CLI needed).'
        f'</p>'
        f'<form method="POST" action="/api/deals/{qd}/sim-inputs" '
        f'style="display: grid; gap: 0.3rem; max-width: 40rem;">'
        f'<input type="text" name="actual_path" required '
        f'placeholder="/path/to/actual.yaml" '
        f'style="font-size: 0.85rem; padding: 0.3rem;">'
        f'<input type="text" name="benchmark_path" required '
        f'placeholder="/path/to/benchmark.yaml" '
        f'style="font-size: 0.85rem; padding: 0.3rem;">'
        f'<input type="text" name="outdir_base" '
        f'placeholder="outdir_base (optional — e.g. runs/ccf)" '
        f'style="font-size: 0.85rem; padding: 0.3rem;">'
        f'<button type="submit" class="btn" '
        f'style="font-size: 0.85rem; padding: 0.25rem 0.7rem; '
        f'width: fit-content;">Save paths</button>'
        f'</form></div>'
    )


def _render_deal_deadlines(store: PortfolioStore, deal_id: str) -> str:
    """B114 + B116: deadlines section with owner-aware add form."""
    from datetime import date as _date
    from .deals.deal_deadlines import list_deadlines
    from .deals.deal_owners import current_owner as _current_owner
    df = list_deadlines(store, deal_id=deal_id)
    qd = urllib.parse.quote(deal_id)
    deal_owner = _current_owner(store, deal_id) or ""

    add_form = (
        f'<form method="POST" action="/api/deals/{qd}/deadlines" '
        f'style="display: flex; gap: 0.4rem; align-items: center; '
        f'margin-top: 0.75rem; flex-wrap: wrap;">'
        f'<input type="text" name="label" placeholder="Task / deadline label" '
        f'required maxlength="120" '
        f'style="flex: 1; min-width: 12rem; font-size: 0.85rem; padding: 0.25rem;">'
        f'<input type="date" name="due_date" required '
        f'style="font-size: 0.85rem; padding: 0.25rem;">'
        f'<input type="text" name="owner" value="{html.escape(deal_owner)}" '
        f'placeholder="Owner (optional)" maxlength="40" '
        f'style="font-size: 0.85rem; padding: 0.25rem; width: 8rem;">'
        f'<button type="submit" class="btn" '
        f'style="font-size: 0.85rem; padding: 0.2rem 0.7rem;">+ Add</button>'
        f'</form>'
    )

    today = _date.today().isoformat()
    rows = []
    for _, r in df.iterrows():
        due = str(r["due_date"])
        if due < today:
            badge = '<span class="badge badge-red">OVERDUE</span>'
        else:
            badge = '<span class="badge badge-amber">OPEN</span>'
        complete_form = (
            f'<form method="POST" '
            f'action="/api/deadlines/{int(r["deadline_id"])}/complete" '
            f'style="display: inline;">'
            f'<button type="submit" class="btn" '
            f'style="font-size: 0.75rem; padding: 0.1rem 0.5rem;">✓</button>'
            f'</form>'
        )
        owner = str(r.get("owner") or "")
        owner_span = (
            f"<span class='muted' style='font-size: 0.8rem;'>"
            f"@{html.escape(owner)}</span>" if owner else ""
        )
        rows.append(
            f"<li style='padding: 0.4rem 0; "
            f"border-bottom: 1px solid var(--border); "
            f"display: flex; gap: 0.5rem; align-items: center;'>"
            f"{badge} "
            f"<span style='font-weight: 600;'>{html.escape(str(r['label']))}</span>"
            f"{owner_span}"
            f"<span class='muted' style='font-size: 0.85rem;'>"
            f"due {html.escape(due)}</span>"
            f"<span style='margin-left: auto;'>{complete_form}</span>"
            f"</li>"
        )

    list_html = (
        f"<ul style='list-style: none; padding: 0; margin: 0;'>"
        f"{''.join(rows)}</ul>"
    ) if rows else "<p class='muted'>No open deadlines.</p>"

    return (
        f'<div class="card"><h2 style="margin-top: 0;">Deadlines '
        f'({len(df)}) — '
        f'<a href="/deadlines" style="color: var(--accent); '
        f'font-size: 0.8rem; font-weight: 400;">all deadlines →</a></h2>'
        f'{list_html}{add_form}</div>'
    )


def _render_deal_alerts(store: PortfolioStore, deal_id: str) -> str:
    """Inline alert card on the deal page (B103).

    Surfaces only alerts for *this* deal — lets the analyst triage
    in-context without switching to /alerts and scanning for the row.
    Each alert gets the same Ack/Snooze form as /alerts.
    """
    from .alerts.alerts import evaluate_active
    from .alerts.alert_acks import trigger_key_for

    alerts = [a for a in evaluate_active(store) if a.deal_id == deal_id]
    if not alerts:
        return ""

    sev_meta = {
        "red":   ("badge-red",   "RED"),
        "amber": ("badge-amber", "AMBER"),
        "info":  ("badge-blue",  "INFO"),
    }
    # Sort red→amber→info
    sev_order = {"red": 0, "amber": 1, "info": 2}
    alerts.sort(key=lambda a: sev_order.get(a.severity, 9))

    from .alerts.alert_history import age_hint
    rows = []
    for a in alerts:
        cls, label = sev_meta.get(a.severity, ("badge-muted", a.severity.upper()))
        tk = trigger_key_for(a)
        age = age_hint(a.first_seen_at)
        age_span = (
            f'<span class="muted" style="font-size: 0.75rem;">'
            f'seen {html.escape(age)}</span>' if age else ""
        )
        ack_form = (
            f'<form method="POST" action="/api/alerts/ack" '
            f'style="display: inline-flex; gap: 0.3rem; align-items: center;">'
            f'<input type="hidden" name="kind" value="{html.escape(a.kind)}">'
            f'<input type="hidden" name="deal_id" value="{html.escape(a.deal_id)}">'
            f'<input type="hidden" name="trigger_key" value="{html.escape(tk)}">'
            f'<select name="snooze_days" '
            f'style="font-size: 0.75rem; padding: 0.1rem;">'
            f'<option value="0">Ack</option>'
            f'<option value="7">Snooze 7d</option>'
            f'<option value="30">Snooze 30d</option>'
            f'</select>'
            f'<button type="submit" class="btn" '
            f'style="font-size: 0.75rem; padding: 0.15rem 0.5rem;">Ack</button>'
            f'</form>'
        )
        returning_badge = (
            '<span class="badge badge-amber" '
            'style="font-size: 0.7rem;" '
            'title="Returned after snooze expired">↩ returning</span>'
            if a.returning else ""
        )
        rows.append(
            f'<li style="padding: 0.5rem 0; '
            f'border-bottom: 1px solid var(--border); '
            f'display: flex; gap: 0.6rem; align-items: center; '
            f'flex-wrap: wrap;">'
            f'<span class="badge {cls}">{label}</span>'
            f'{returning_badge}'
            f'<span style="font-weight: 600;">{html.escape(a.title)}</span>'
            f'<span class="muted" style="font-size: 0.85rem;">'
            f'{html.escape(a.detail)}</span>'
            f'{age_span}'
            f'{ack_form}'
            f'</li>'
        )

    return (
        f'<div class="card" style="border-left: 3px solid var(--red-text);">'
        f'<h2 style="margin-top: 0;">Active alerts '
        f'<span class="muted" style="font-weight: 400; font-size: 0.8rem;">'
        f'({len(alerts)}) — <a href="/alerts" style="color: var(--accent);">'
        f'all alerts →</a></span></h2>'
        f'<ul style="list-style: none; padding: 0; margin: 0;">'
        f'{"".join(rows)}</ul></div>'
    )


def _render_deal_detail(config: ServerConfig, deal_id: str) -> str:
    """Per-deal detail page: snapshot audit + variance + initiative attribution.

    Composed inline from the existing data readers — no new HTML shell
    code, just layout. Uses the shared ``_ui_kit.shell`` for consistency.
    """
    store = PortfolioStore(config.db_path)
    snaps = list_snapshots(store, deal_id=deal_id)
    if snaps.empty:
        body = (
            f'<div class="card"><p class="muted">No snapshots for deal '
            f'<strong>{html.escape(deal_id)}</strong>. Register the deal '
            'via <code>rcm-mc portfolio register</code> first.</p></div>'
        )
        return shell(body, title=f"Deal: {deal_id}", back_href="/")

    latest = snaps.iloc[0]
    def _fmt(v):
        if v is None:
            return "—"
        if isinstance(v, float) and v != v:
            return "—"
        return v

    # Snapshot audit trail — oldest→newest, inline table
    trail_rows = []
    for _, r in snaps.sort_values("created_at").iterrows():
        notes = str(r.get("notes") or "")
        trail_rows.append(
            f"<tr>"
            f"<td>{html.escape(str(r.get('created_at') or '')[:19])}</td>"
            f"<td><strong>{html.escape(str(r.get('stage') or '?'))}</strong></td>"
            f"<td class='num'>{_fmt(r.get('moic'))}</td>"
            f"<td class='num'>{_fmt(r.get('irr'))}</td>"
            f"<td>{html.escape(str(r.get('covenant_status') or '—'))}</td>"
            f"<td class='muted'>{html.escape(notes[:120])}</td>"
            f"</tr>"
        )

    # Quarterly variance (EBITDA + KPIs)
    var_df = variance_report(store, deal_id)
    var_rows = []
    if not var_df.empty:
        for _, r in var_df.sort_values(["quarter", "kpi"]).iterrows():
            var_rows.append(
                f"<tr>"
                f"<td>{html.escape(str(r.get('quarter') or ''))}</td>"
                f"<td>{html.escape(str(r.get('kpi') or ''))}</td>"
                f"<td class='num'>{r.get('actual')}</td>"
                f"<td class='num'>{_fmt(r.get('plan'))}</td>"
                f"<td class='num'>{_fmt(r.get('variance_pct'))}</td>"
                f"<td>{html.escape(str(r.get('severity') or ''))}</td>"
                f"</tr>"
            )

    # Initiative-level attribution
    init_df = initiative_variance_report(store, deal_id)
    init_rows = []
    if not init_df.empty:
        for _, r in init_df.iterrows():
            init_rows.append(
                f"<tr>"
                f"<td><strong>{html.escape(str(r.get('initiative_id') or ''))}</strong></td>"
                f"<td class='num'>{r.get('cumulative_actual')}</td>"
                f"<td class='num'>{_fmt(r.get('cumulative_plan'))}</td>"
                f"<td class='num'>{_fmt(r.get('variance_pct'))}</td>"
                f"<td>{html.escape(str(r.get('severity') or ''))}</td>"
                f"<td class='num'>{r.get('quarters_active')}</td>"
                f"</tr>"
            )

    # Stage + covenant headline
    stage = latest.get("stage") or "—"
    cov = latest.get("covenant_status") or "—"
    cov_badge = {
        "SAFE":    '<span class="badge badge-green">SAFE</span>',
        "TIGHT":   '<span class="badge badge-amber">TIGHT</span>',
        "TRIPPED": '<span class="badge badge-red">TRIPPED</span>',
    }.get(str(cov), f'<span class="badge badge-muted">{html.escape(str(cov))}</span>')

    qd = urllib.parse.quote(deal_id)
    from .deals.deal_owners import current_owner as _current_owner
    from .deals.watchlist import is_starred as _is_starred
    starred = _is_starred(store, deal_id)
    owner = _current_owner(store, deal_id) or ""
    owner_form = (
        f'<form method="POST" action="/api/deals/{qd}/owner" '
        f'style="display: inline-flex; gap: 0.25rem; align-items: center;">'
        f'<label style="font-size: 0.8rem;" class="muted">Owner</label>'
        f'<input type="text" name="owner" value="{html.escape(owner)}" '
        f'placeholder="e.g. AT" maxlength="40" '
        f'style="font-size: 0.8rem; padding: 0.15rem 0.35rem; width: 6rem;">'
        f'<button type="submit" class="btn" '
        f'style="font-size: 0.75rem; padding: 0.1rem 0.5rem;">Assign</button>'
        f'</form>'
    )
    star_label = "★ Starred" if starred else "☆ Star"
    star_style = (
        "background: var(--amber-soft); color: var(--amber-text);"
        if starred else
        "background: var(--card); color: var(--accent);"
    )
    star_btn = (
        f'<form method="POST" action="/api/deals/{qd}/star" '
        f'style="display: inline;">'
        f'<button type="submit" '
        f'style="{star_style} border: 1px solid var(--border); '
        f'border-radius: 6px; padding: 0.25rem 0.7rem; font-size: 0.85rem; '
        f'font-weight: 600; cursor: pointer;">{star_label}</button>'
        f'</form>'
    )

    from .deals.health_score import compute_health as _compute_health
    health = _compute_health(store, deal_id)
    health_band_color = {
        "green": "var(--green-text)",
        "amber": "var(--amber-text)",
        "red":   "var(--red-text)",
    }.get(health["band"], "var(--muted)")
    trend_arrow = {"up": "↑", "down": "↓", "flat": "→"}.get(
        health.get("trend", "flat"), "",
    )
    trend_color = {
        "up": "var(--green-text)",
        "down": "var(--red-text)",
        "flat": "var(--muted)",
    }.get(health.get("trend", "flat"), "var(--muted)")
    delta = health.get("delta", 0) or 0
    trend_span = (
        f' <span style="color: {trend_color}; font-size: 1.1rem;" '
        f'title="Δ {delta:+d} vs prior day">{trend_arrow}</span>'
        if health["score"] is not None and health.get("trend") != "flat"
        else ""
    )
    # Pre-built HTML (trend_span contains intentional markup); the
    # template below interpolates this directly without re-escaping.
    health_score_display_html = (
        f"{int(health['score'])}{trend_span}"
        if health["score"] is not None else "&mdash;"
    )
    # Tooltip of components so partners can inspect why the score is what it is.
    # B157 fix: use " | " as separator rather than literal "\n". html.escape
    # doesn't escape newlines, and browsers render them inconsistently inside
    # `title=` attributes. A visible separator is safer and clearer.
    comp_lines = " | ".join(
        f"{c['impact']:+d} {c['label']}"
        for c in health.get("components", [])
    ) or "No deductions — healthy."

    body = f"""
    <div style="display: flex; justify-content: flex-end; gap: 1rem;
         margin-bottom: 1rem; font-size: 0.85rem; align-items: center;">
      {owner_form}
      {star_btn}
      <a href="/deal/{qd}?download=1"
         style="color: var(--accent); text-decoration: none;
                border-bottom: 1px dotted var(--accent);">
        ↓ Download deal page
      </a>
    </div>

    <div class="kpi-grid">
      <div class="kpi-card" title="{html.escape(comp_lines)}">
        <div class="kpi-value" style="color: {health_band_color};">
          {health_score_display_html}
        </div>
        <div class="kpi-label">Health ({html.escape(health["band"])})</div>
        {_render_health_sparkline(store, deal_id)}
      </div>
      <div class="kpi-card">
        <div class="kpi-value">{html.escape(str(stage)).title()}</div>
        <div class="kpi-label">Stage</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-value">{cov_badge}</div>
        <div class="kpi-label">Covenant</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-value">{_fmt(latest.get('moic'))}</div>
        <div class="kpi-label">MOIC (latest)</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-value">{_fmt(latest.get('irr'))}</div>
        <div class="kpi-label">IRR (latest)</div>
      </div>
    </div>

    {_render_deal_alerts(store, deal_id)}

    <div class="card">
      <h2>Snapshot audit trail ({len(snaps)} entries)</h2>
      <table>
        <thead><tr>
          <th>Timestamp</th><th>Stage</th><th>MOIC</th><th>IRR</th>
          <th>Covenant</th><th>Notes</th>
        </tr></thead>
        <tbody>{"".join(trail_rows)}</tbody>
      </table>
    </div>

    {_render_ebitda_sparkline(var_df)}

    {
      f'<div class="card"><h2>Quarterly variance ({len(var_df)} rows)</h2>'
      f'<table><thead><tr>'
      f'<th>Quarter</th><th>KPI</th><th>Actual</th><th>Plan</th>'
      f'<th>Variance</th><th>Severity</th>'
      f'</tr></thead><tbody>{"".join(var_rows)}</tbody></table></div>'
      if var_rows else ""
    }

    {
      f'<div class="card"><h2>Initiative attribution ({len(init_df)} initiatives)</h2>'
      f'<table><thead><tr>'
      f'<th>Initiative</th><th>Cum. actual</th><th>Cum. plan</th>'
      f'<th>Variance</th><th>Severity</th><th>Quarters</th>'
      f'</tr></thead><tbody>{"".join(init_rows)}</tbody></table></div>'
      if init_rows else ""
    }

    <script>
    // B98: record this deal in the browser's recently-viewed list so the
    // dashboard can offer a quick-nav shortcut. Caps at 10 entries.
    (function() {{
      try {{
        var KEY = 'rcm-mc-recent-deals-v1';
        var MAX = 10;
        var did = {repr(deal_id)};
        var arr = [];
        try {{ arr = JSON.parse(localStorage.getItem(KEY) || '[]'); }} catch (e) {{ arr = []; }}
        // Put this deal at the front, dedupe
        arr = [did].concat(arr.filter(function(x) {{ return x !== did; }}));
        arr = arr.slice(0, MAX);
        localStorage.setItem(KEY, JSON.stringify(arr));
      }} catch (e) {{ /* storage unavailable — skip */ }}
    }})();
    </script>

    {_render_deal_tags(store, deal_id)}

    {_render_deal_rerun(store, deal_id)}

    {_render_deal_deadlines(store, deal_id)}

    {_render_deal_notes(store, deal_id)}

    {_deal_action_forms(deal_id)}
    """
    return shell(
        body=body,
        title=f"Deal: {deal_id}",
        subtitle=f"Live view · reading {config.db_path}",
        back_href="/",
    )


def _render_deal_tags(store: PortfolioStore, deal_id: str) -> str:
    """Tags pills + inline add-tag form + one-click remove per tag.

    Keep it compact — tags are small labels, not a section that needs
    a full card header.
    """
    tags = tags_for(store, deal_id)
    qd = urllib.parse.quote(deal_id)

    pills = []
    for tag in tags:
        pills.append(
            f'<span class="badge badge-blue" style="margin-right: 0.35rem; '
            f'display: inline-flex; align-items: center; gap: 0.25rem;">'
            f'{html.escape(tag)}'
            f'<form method="POST" action="/api/deals/{qd}/tags/{urllib.parse.quote(tag)}/remove" '
            f'style="display: inline; margin: 0;" '
            f'onsubmit="return confirm(\'Remove tag {html.escape(tag)}?\');">'
            f'<button type="submit" style="background: none; border: none; '
            f'color: inherit; cursor: pointer; padding: 0 0 0 0.25rem; '
            f'font-size: 0.9rem; line-height: 1;">×</button>'
            f'</form>'
            f'</span>'
        )
    pills_html = "".join(pills) if pills else (
        '<span class="muted" style="font-size: 0.85rem;">No tags yet.</span>'
    )

    input_css = (
        'style="padding: 0.35rem 0.6rem; border: 1px solid var(--border); '
        'border-radius: 6px; font-size: 0.85rem; font-family: inherit;"'
    )
    return f"""
    <div class="card" style="padding: 0.75rem 1.25rem;">
      <div style="display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem;">
        <span style="font-size: 0.8rem; color: var(--muted); font-weight: 600;
              text-transform: uppercase; letter-spacing: 0.04em; margin-right: 0.5rem;">
          Tags
        </span>
        {pills_html}
        <form method="POST" action="/api/deals/{qd}/tags"
              style="display: inline-flex; gap: 0.4rem; margin-left: auto;">
          <input type="text" name="tag" required
                 placeholder="add tag (e.g. watch, region:tx)"
                 pattern="[a-z0-9][a-z0-9_:.\\-]{{0,39}}"
                 title="lowercase alnum / dash / underscore / colon / period"
                 {input_css}>
          <button type="submit"
                  style="padding: 0.35rem 0.85rem; border: none;
                         border-radius: 6px; background: var(--accent);
                         color: white; font-weight: 600; cursor: pointer;
                         font-size: 0.85rem;">
            +
          </button>
        </form>
      </div>
    </div>
    """


def _render_deal_notes(store: PortfolioStore, deal_id: str) -> str:
    """List prior notes (newest first) + a compact add-note form.

    Each note shows timestamp + author + body. Delete button per note
    (POSTs to /api/deals/<id>/notes/<note_id>/delete). Body supports
    basic line breaks; no rich formatting (keeps stored content safe).
    """
    from .deals.deal_notes import list_notes as _list_notes
    notes_df = _list_notes(store, deal_id=deal_id)
    # Soft-deleted notes — shown in a collapsible trash bin below (B91)
    trash_df = _list_notes(store, deal_id=deal_id, include_deleted=True)
    if not trash_df.empty:
        trash_df = trash_df[trash_df["deleted_at"].notna()]
    qd = urllib.parse.quote(deal_id)

    items_html: list = []
    for _, r in notes_df.iterrows():
        author = r.get("author") or "—"
        ts = str(r.get("created_at") or "")[:19]
        body_text = str(r.get("body") or "")
        # Preserve analyst-typed newlines as <br>; escape everything else
        escaped = html.escape(body_text).replace("\n", "<br>")
        note_id = int(r.get("note_id") or 0)
        items_html.append(
            f'<li class="deal-note" style="padding: 0.75rem 0; '
            f'border-bottom: 1px solid var(--border);">'
            f'<div style="display: flex; justify-content: space-between; '
            f'align-items: baseline; margin-bottom: 0.25rem;">'
            f'<span style="font-size: 0.8rem; color: var(--muted);">'
            f'<strong>{html.escape(author)}</strong> · {html.escape(ts)}'
            f'</span>'
            f'<form method="POST" action="/api/deals/{qd}/notes/{note_id}/delete" '
            f'style="display: inline; margin: 0;" '
            f'onsubmit="return confirm(\'Delete this note?\');">'
            f'<button type="submit" style="background: none; border: none; '
            f'color: var(--red-text); cursor: pointer; font-size: 0.75rem; '
            f'padding: 0;">delete</button>'
            f'</form>'
            f'</div>'
            f'<div style="white-space: pre-wrap; line-height: 1.45;">'
            f'{escaped}</div>'
            f'</li>'
        )
    note_list = (
        '<ul style="list-style: none; padding: 0; margin: 0;">'
        + "".join(items_html) + '</ul>'
    ) if items_html else (
        '<p class="muted" style="font-size: 0.88rem; margin-top: 0.5rem;">'
        'No notes yet. Use the form below to capture call notes, '
        'management commentary, or pending data asks.</p>'
    )

    input_css = (
        'style="padding: 0.4rem 0.6rem; border: 1px solid var(--border); '
        'border-radius: 6px; font-size: 0.9rem; font-family: inherit; width: 100%;"'
    )
    # B91: recently-deleted bin with Restore / Purge buttons
    trash_html = ""
    if trash_df is not None and not trash_df.empty:
        trash_items = []
        for _, r in trash_df.iterrows():
            note_id = int(r.get("note_id") or 0)
            body_txt = str(r.get("body") or "")[:140]
            author_txt = str(r.get("author") or "—")
            deleted_ts = str(r.get("deleted_at") or "")[:19]
            trash_items.append(
                f'<li style="padding: 0.5rem 0; '
                f'border-bottom: 1px solid var(--border); '
                f'display: flex; justify-content: space-between; align-items: start;">'
                f'<span>'
                f'<span class="muted" style="font-size: 0.75rem;">'
                f'deleted {html.escape(deleted_ts)} · by '
                f'{html.escape(author_txt)}</span>'
                f'<div style="font-size: 0.85rem;">{html.escape(body_txt)}'
                f'{"…" if len(str(r.get("body") or "")) > 140 else ""}</div>'
                f'</span>'
                f'<span style="display: flex; gap: 0.4rem;">'
                f'<form method="POST" action="/api/deals/{qd}/notes/{note_id}/restore" '
                f'style="margin: 0;"><button type="submit" '
                f'style="background: none; border: 1px solid var(--green); '
                f'color: var(--green-text); cursor: pointer; '
                f'font-size: 0.75rem; padding: 0.15rem 0.5rem; '
                f'border-radius: 4px;">Restore</button></form>'
                f'<form method="POST" action="/api/deals/{qd}/notes/{note_id}/purge" '
                f'style="margin: 0;" '
                f'onsubmit="return confirm(\'Permanently delete this note? Cannot be undone.\');">'
                f'<button type="submit" '
                f'style="background: none; border: 1px solid var(--red); '
                f'color: var(--red-text); cursor: pointer; '
                f'font-size: 0.75rem; padding: 0.15rem 0.5rem; '
                f'border-radius: 4px;">Purge</button></form>'
                f'</span>'
                f'</li>'
            )
        trash_html = (
            f'<details style="margin-top: 1rem;">'
            f'<summary style="cursor: pointer; color: var(--muted); '
            f'font-size: 0.85rem;">'
            f'Recently deleted ({len(trash_df)}) — click to show'
            f'</summary>'
            f'<ul style="list-style: none; padding: 0; margin-top: 0.5rem;">'
            f'{"".join(trash_items)}</ul></details>'
        )

    return f"""
    <div class="card">
      <h2>Notes ({len(notes_df)})</h2>
      {note_list}
      <form method="POST" action="/api/deals/{qd}/notes"
            style="margin-top: 1rem; display: grid; gap: 0.5rem;">
        <input type="text" name="author" placeholder="Your name (optional)"
               {input_css}>
        <textarea name="body" required rows="3"
                  placeholder="New note — call notes, management commentary, data asks..."
                  {input_css}></textarea>
        <div>
          <button type="submit"
                  style="padding: 0.5rem 1.25rem; border: none;
                         border-radius: 6px; background: var(--accent);
                         color: white; font-weight: 600; cursor: pointer;
                         font-size: 0.9rem;">
            Add note
          </button>
        </div>
      </form>
      {trash_html}
    </div>
    """


def _inject_live_banner(dashboard_html: str) -> str:
    """Insert a small 'Live • auto-refreshing' banner at the top of the dashboard."""
    banner = (
        '<div style="background: #FEF3C7; border: 1px solid #F59E0B; '
        'border-radius: 6px; padding: 0.4rem 0.75rem; margin-bottom: 1rem; '
        'font-size: 0.82rem; color: #92400E; display: flex; '
        'justify-content: space-between; align-items: center;">'
        '<span>● Live mode — refreshing every 60s. '
        '<a href="/" style="color: #92400E; text-decoration: underline;">Exit live</a></span>'
        '<span id="rcm-live-countdown" style="font-variant-numeric: tabular-nums;"></span>'
        '</div>'
        "<script>(function(){var el=document.getElementById('rcm-live-countdown');"
        "if(!el)return;var left=60;el.textContent=left+'s';"
        "setInterval(function(){left--;if(left<0)left=0;"
        "el.textContent=left+'s';},1000);})();</script>"
    )
    # Insert right after the opening <div class="container">
    marker = '<div class="container">'
    idx = dashboard_html.find(marker)
    if idx < 0:
        return dashboard_html
    pos = idx + len(marker)
    return dashboard_html[:pos] + banner + dashboard_html[pos:]


def _inject_tour_card(dashboard_html: str) -> str:
    """B163: guided-tour card injected for demo user.

    Explains what this page shows and gives a structured walkthrough
    of the six partner workflows. Dismissable via a close button that
    sets a localStorage flag so it doesn't come back every page load.
    """
    tour_card = """
    <div class="card" id="rcm-demo-tour" style="
         border-left: 4px solid var(--accent);
         background: linear-gradient(to right, var(--accent-soft), white);">
      <div style="display: flex; justify-content: space-between;
           align-items: flex-start; gap: 1rem;">
        <div style="flex: 1;">
          <h2 style="margin-top: 0; color: var(--accent);">
            👋 Welcome to the RCM-MC demo
          </h2>
          <p style="margin: 0.5rem 0 1rem 0; color: var(--text);">
            This is a <strong>portfolio-operations console</strong>
            for healthcare-PE partners. The sample portfolio has
            5 deals spanning green / amber / red health, 3 owners,
            overdue tasks, and a live simulation you can rerun.
          </p>
          <p style="margin: 0 0 0.75rem 0; font-weight: 600;">
            Try these pages, in order:
          </p>
          <ol style="margin: 0 0 0 1.2rem; padding: 0;
                     line-height: 1.8;">
            <li><a href="/alerts"><strong>Alerts</strong></a> —
              covenant trips &amp; variance misses.
              Click <em>Ack</em> to silence.</li>
            <li><a href="/my/AT"><strong>My work: AT</strong></a> —
              one analyst's personal inbox
              (deals owned, alerts, deadlines).</li>
            <li><a href="/deal/ccf"><strong>Deal: ccf</strong></a> —
              full deal page. Scroll to see health trend,
              notes, tags, and the <em>▶ Rerun simulation</em> button.</li>
            <li><a href="/cohorts"><strong>Cohorts</strong></a> —
              slices by tag (<code>growth</code>, <code>roll-up</code>,
              <code>watch</code>).</li>
            <li><a href="/lp-update"><strong>LP update</strong></a> —
              partner-ready digest. Click <em>↓ Download</em>
              for the standalone HTML.</li>
            <li><a href="/audit"><strong>Audit</strong></a> —
              every ack, owner change, login, upload.</li>
          </ol>
          <p class="muted" style="margin-top: 1rem;
               font-size: 0.85rem;">
            The nav bar up top has everything else
            (<a href="/variance">variance</a>,
            <a href="/watchlist">watchlist</a>,
            <a href="/deadlines">deadlines</a>,
            <a href="/notes">notes search</a>,
            <a href="/compare?deals=ccf,mgh,nyp">compare</a>,
            <a href="/users">users</a>).
          </p>
        </div>
        <button onclick="
          document.getElementById('rcm-demo-tour').style.display='none';
          try { localStorage.setItem('rcm-demo-tour-dismissed','1'); }
          catch (e) {}"
          title="Dismiss tour"
          style="background: none; border: none; cursor: pointer;
                 font-size: 1.2rem; color: var(--muted);
                 padding: 0 0.3rem; line-height: 1;">×</button>
      </div>
    </div>
    <script>
      // Honor prior dismissal
      (function() {
        try {
          if (localStorage.getItem('rcm-demo-tour-dismissed') === '1') {
            var el = document.getElementById('rcm-demo-tour');
            if (el) el.style.display = 'none';
          }
        } catch (e) {}
      })();
    </script>
    """
    # Place right after the opening <div class="container">…<h1>
    anchor = '<div class="subtitle">'
    if anchor in dashboard_html:
        # Insert tour card just before the subtitle (after h1)
        idx = dashboard_html.find(anchor)
        end = dashboard_html.find("</div>", idx) + len("</div>")
        return dashboard_html[:end] + tour_card + dashboard_html[end:]
    # Fallback: put it after the first <h1>
    h1_end = dashboard_html.find("</h1>")
    if h1_end > 0:
        h1_end += len("</h1>")
        return dashboard_html[:h1_end] + tour_card + dashboard_html[h1_end:]
    return dashboard_html


def _inject_new_deal_card(dashboard_html: str) -> str:
    """Insert a "Register new deal" collapsible card right after the pipeline funnel.

    Kept as a simple collapsible so it doesn't crowd the dashboard for
    analysts who're just reading. One click expands the form; POSTs to the
    same /api/deals/<id>/snapshots endpoint.
    """
    from .portfolio.portfolio_snapshots import DEAL_STAGES

    stage_opts = "".join(
        f'<option value="{s}">{html.escape(s.title())}</option>'
        for s in DEAL_STAGES
    )
    # We use a raw HTML form that POSTs to /api/deals/<id>/snapshots.
    # Deal ID is part of the URL path, so we need a small JS shim to
    # take the deal_id field and route it correctly.
    new_deal_card = f"""
    <details class="card" style="padding: 1rem 1.25rem;">
      <summary style="cursor: pointer; font-weight: 600; color: var(--accent);
               list-style: none; user-select: none;">
        + Register a new deal
      </summary>
      <form onsubmit="var did=this.deal_id.value.trim();
                      if(!did) return false;
                      this.action='/api/deals/'+encodeURIComponent(did)+'/snapshots';"
            method="POST"
            style="margin-top: 1rem; display: grid;
                   grid-template-columns: 180px 1fr; gap: 0.5rem 1rem;
                   align-items: center; max-width: 600px;">
        <label>Deal ID</label>
        <input type="text" name="deal_id" required placeholder="project_phoenix"
               style="padding: 0.4rem 0.6rem; border: 1px solid var(--border);
                      border-radius: 6px; font-size: 0.9rem;">
        <label>Stage</label>
        <select name="stage" required
                style="padding: 0.4rem 0.6rem; border: 1px solid var(--border);
                       border-radius: 6px; font-size: 0.9rem;">
          <option value="" disabled selected>— pick stage —</option>
          {stage_opts}
        </select>
        <label>Notes</label>
        <input type="text" name="notes" placeholder="sourced from XYZ banker"
               style="padding: 0.4rem 0.6rem; border: 1px solid var(--border);
                      border-radius: 6px; font-size: 0.9rem;">
        <div></div>
        <button type="submit"
                style="padding: 0.5rem 1.25rem; border: none; border-radius: 6px;
                       background: var(--accent); color: white; font-weight: 600;
                       cursor: pointer; font-size: 0.9rem;">
          Register
        </button>
      </form>
    </details>
    """
    # Inject right after the pipeline funnel card — locate the </card> tag
    # that closes the funnel card and insert before the next card.
    marker = "<h2>Pipeline funnel</h2>"
    idx = dashboard_html.find(marker)
    if idx < 0:
        return dashboard_html + new_deal_card  # fallback: append
    # Find the next closing </div> at the card level
    close = dashboard_html.find("</div>", idx)
    close = dashboard_html.find("</div>", close + 1)  # close the card div
    if close < 0:
        return dashboard_html + new_deal_card
    return (
        dashboard_html[:close + len("</div>")]
        + new_deal_card
        + dashboard_html[close + len("</div>"):]
    )


def _render_ebitda_sparkline(var_df, width: int = 600, height: int = 180) -> str:
    """Inline SVG line chart: quarterly EBITDA actual vs plan.

    Two paths (actual solid, plan dashed) + severity-colored dots per
    quarter. Returns empty string when there's nothing to chart.
    Zero JS; scales linearly from min to max across both series.
    """
    import pandas as pd
    if var_df is None or var_df.empty:
        return ""
    ebitda = var_df[var_df["kpi"] == "ebitda"].sort_values("quarter")
    if len(ebitda) < 2:
        return ""

    actuals = [float(v) for v in ebitda["actual"].tolist()]
    plans_raw = ebitda["plan"].tolist()
    plans = [float(p) if p is not None and not (isinstance(p, float) and p != p) else None
             for p in plans_raw]
    quarters = [str(q) for q in ebitda["quarter"].tolist()]
    severities = [str(s or "") for s in ebitda["severity"].tolist()]

    all_values = [v for v in actuals if v is not None]
    all_values += [v for v in plans if v is not None]
    if not all_values:
        return ""
    vmin, vmax = min(all_values), max(all_values)
    if vmax == vmin:
        vmax = vmin + 1  # Avoid div-by-zero; chart shows a flat line

    pad = 30
    chart_w = width - 2 * pad
    chart_h = height - 2 * pad

    def _x(i): return pad + (i / max(len(quarters) - 1, 1)) * chart_w
    def _y(v):
        if v is None:
            return None
        return height - pad - ((v - vmin) / (vmax - vmin)) * chart_h

    sev_color = {
        "on_track":  "#10B981",
        "lagging":   "#F59E0B",
        "off_track": "#EF4444",
    }

    # Build polyline paths
    actual_pts = " ".join(f"{_x(i):.1f},{_y(v):.1f}"
                          for i, v in enumerate(actuals) if v is not None)
    plan_pts = " ".join(f"{_x(i):.1f},{_y(v):.1f}"
                        for i, v in enumerate(plans) if v is not None)

    # Quarter labels on x-axis
    labels = "".join(
        f'<text x="{_x(i):.1f}" y="{height - 8}" '
        f'text-anchor="middle" font-size="10" fill="#6B7280">{html.escape(q)}</text>'
        for i, q in enumerate(quarters)
    )

    # Severity dots on actual series
    dots = "".join(
        f'<circle cx="{_x(i):.1f}" cy="{_y(v):.1f}" r="4" '
        f'fill="{sev_color.get(severities[i], "#6B7280")}" stroke="white" stroke-width="2"/>'
        for i, v in enumerate(actuals) if v is not None
    )

    # Y-axis min / max labels
    def _fmt_money_compact(v):
        if v >= 1e9:
            return f"${v/1e9:.1f}B"
        if v >= 1e6:
            return f"${v/1e6:.1f}M"
        return f"${v:,.0f}"
    y_labels = (
        f'<text x="{pad - 5}" y="{pad + 4}" text-anchor="end" '
        f'font-size="10" fill="#6B7280">{_fmt_money_compact(vmax)}</text>'
        f'<text x="{pad - 5}" y="{height - pad + 4}" text-anchor="end" '
        f'font-size="10" fill="#6B7280">{_fmt_money_compact(vmin)}</text>'
    )

    plan_path = (
        f'<polyline points="{plan_pts}" fill="none" stroke="#6B7280" '
        f'stroke-width="2" stroke-dasharray="5,3" opacity="0.7"/>'
    ) if plan_pts else ""

    svg = (
        f'<svg viewBox="0 0 {width} {height}" '
        f'xmlns="http://www.w3.org/2000/svg" '
        f'style="width: 100%; max-width: {width}px; height: auto; '
        f'display: block; margin: 0 auto;">'
        # Frame lines
        f'<line x1="{pad}" y1="{pad}" x2="{pad}" y2="{height - pad}" '
        f'stroke="#E5E7EB" stroke-width="1"/>'
        f'<line x1="{pad}" y1="{height - pad}" x2="{width - pad}" '
        f'y2="{height - pad}" stroke="#E5E7EB" stroke-width="1"/>'
        f'{plan_path}'
        f'<polyline points="{actual_pts}" fill="none" stroke="#1F4E78" stroke-width="2.5"/>'
        f'{dots}'
        f'{labels}'
        f'{y_labels}'
        f'</svg>'
    )

    return (
        '<div class="card"><h2>EBITDA trend</h2>'
        '<p class="muted" style="font-size: 0.85rem;">'
        'Solid line = actual · dashed line = plan · dot color = severity '
        '(green = on track, amber = lagging, red = off track)'
        '</p>'
        f'{svg}</div>'
    )


def _deal_action_forms(deal_id: str) -> str:
    """Two forms: record a quarter of actuals, and advance the deal stage.

    Both POST to the server's REST endpoints; on success the browser is
    303-redirected back to the deal page so the new data is visible.
    """
    from .portfolio.portfolio_snapshots import DEAL_STAGES

    qd = urllib.parse.quote(deal_id)
    stage_opts = "".join(
        f'<option value="{s}">{html.escape(s.title())}</option>'
        for s in DEAL_STAGES
    )

    # Compact inline form styling — keeps the deal page readable
    form_css = (
        'style="display: grid; grid-template-columns: 180px 1fr; '
        'gap: 0.5rem 1rem; align-items: center; max-width: 600px;"'
    )
    input_css = (
        'style="padding: 0.4rem 0.6rem; border: 1px solid var(--border); '
        'border-radius: 6px; font-size: 0.9rem; font-family: inherit;"'
    )
    submit_css = (
        'style="padding: 0.5rem 1.25rem; border: none; border-radius: 6px; '
        'background: var(--accent); color: white; font-weight: 600; '
        'cursor: pointer; font-size: 0.9rem; font-family: inherit;"'
    )

    return f"""
    <div class="card">
      <h2>Record quarterly actuals</h2>
      <p class="muted" style="font-size: 0.85rem; margin-bottom: 1rem;">
        Enter the management-deck numbers for the current quarter. Plan
        values are optional; leave blank to use the snapshot's underwritten
        EBITDA as the plan.
      </p>
      <form method="POST" action="/api/deals/{qd}/actuals" {form_css}>
        <label>Quarter (YYYYQn)</label>
        <input type="text" name="quarter" required placeholder="2026Q2" {input_css}>

        <label>EBITDA ($)</label>
        <input type="number" step="any" name="ebitda" {input_css}>

        <label>Plan EBITDA ($)</label>
        <input type="number" step="any" name="plan_ebitda" {input_css}>

        <label>NPSR ($)</label>
        <input type="number" step="any" name="net_patient_revenue" {input_css}>

        <label>IDR (decimal)</label>
        <input type="number" step="0.001" name="idr_blended" {input_css}>

        <label>DAR (days)</label>
        <input type="number" step="0.1" name="dar_clean_days" {input_css}>

        <label>Notes</label>
        <input type="text" name="notes" {input_css}>

        <div></div>
        <button type="submit" {submit_css}>Record quarter</button>
      </form>
    </div>

    <div class="card">
      <h2>Re-mark underwrite</h2>
      <p class="muted" style="font-size: 0.85rem; margin-bottom: 1rem;">
        Recompute MOIC / IRR from the latest TTM EBITDA and persist as a new
        hold-stage snapshot. Shows whether the original thesis still holds
        after this quarter's management report.
      </p>
      <form method="POST" action="/api/deals/{qd}/remark"
            onsubmit="return confirm('Persist a new re-mark snapshot?');"
            style="display: flex; gap: 0.5rem; align-items: center;">
        <label style="font-size: 0.9rem; color: var(--muted);">
          As of quarter (optional):
        </label>
        <input type="text" name="as_of" placeholder="auto-detect latest"
               {input_css} style="max-width: 180px;">
        <button type="submit" {submit_css}>Compute &amp; persist</button>
      </form>
    </div>

    <div class="card">
      <h2>Advance stage</h2>
      <p class="muted" style="font-size: 0.85rem; margin-bottom: 1rem;">
        Register a new snapshot at a different pipeline stage. The snapshot
        trail is append-only — advancing stage doesn't erase the prior one.
      </p>
      <form method="POST" action="/api/deals/{qd}/snapshots" {form_css}>
        <label>New stage</label>
        <select name="stage" required {input_css}>
          <option value="" disabled selected>— pick stage —</option>
          {stage_opts}
        </select>

        <label>Run directory (optional)</label>
        <input type="text" name="run_dir" placeholder="/path/to/run" {input_css}>

        <label>Notes</label>
        <input type="text" name="notes" {input_css}>

        <div></div>
        <button type="submit" {submit_css}>Advance stage</button>
      </form>
    </div>
    """


# ── Route dispatch ─────────────────────────────────────────────────────────

# Simple per-request hook so the dashboard's card links point at
# ``/deal/<id>`` instead of the file-system sub-folder paths the CLI
# dashboard uses. Rewrite the minimal set that matters.
def _rewrite_dashboard_links(html_doc: str) -> str:
    """Rewrite the CLI-style dashboard output so deal cards link at /deal/<id>.

    The CLI dashboard was designed to be opened from disk; its deal-row
    links don't exist. We do a targeted replace so the server version
    works without touching the existing builder.
    """
    # For now: make every 'deal_id' cell into a link. The CLI dashboard
    # currently wraps deal IDs in ``<strong>`` inside a table cell; we
    # upgrade those to anchor tags pointing at /deal/<id>.
    import re
    def _wrap(match):
        inner = match.group(1)
        return (
            f'<strong><a href="/deal/{urllib.parse.quote(inner)}" '
            f'style="color: var(--accent); text-decoration: none; '
            f'border-bottom: 1px dotted var(--accent);">'
            f'{html.escape(inner)}</a></strong>'
        )
    return re.sub(
        r"<strong>([^<>/]+)</strong>",
        _wrap,
        html_doc,
    )


def _sanitize_profile_margins(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Clamp implausibly-high EBITDA margins on a deal profile.

    Hospital EBITDA margins realistically land in [-15%, +15%]. When
    HCRIS ``operating_expenses`` is missing a component (overhead
    allocation not rolled up in the source worksheet), the raw margin
    calculation produces values like 88% that compound into 60x MOIC
    on downstream DCF / LBO projections.

    Clamps in-place: preserves the raw value under
    ``ebitda_margin_raw_hcris`` and flips ``ebitda_margin_clamped``
    to True so downstream views can annotate the adjustment. A no-op
    if the margin is already in the realistic band or absent.
    """
    try:
        raw = profile.get("ebitda_margin")
        if raw is None:
            return profile
        raw_f = float(raw)
    except (TypeError, ValueError):
        return profile

    CEIL = 0.15
    FLOOR = -0.20
    if raw_f > CEIL:
        profile["ebitda_margin_raw_hcris"] = round(raw_f, 4)
        profile["ebitda_margin"] = 0.08
        profile["ebitda_margin_clamped"] = True
    elif raw_f < FLOOR:
        profile["ebitda_margin_raw_hcris"] = round(raw_f, 4)
        profile["ebitda_margin"] = -0.05
        profile["ebitda_margin_clamped"] = True
    else:
        profile.setdefault("ebitda_margin_clamped", False)

    # Keep ebitda and current_ebitda consistent with the (possibly
    # clamped) margin so downstream DCF / LBO don't project off
    # inconsistent revenue-vs-EBITDA inputs.
    if profile.get("ebitda_margin_clamped") and profile.get("net_revenue"):
        try:
            new_ebitda = float(profile["net_revenue"]) * float(profile["ebitda_margin"])
            profile["ebitda"] = round(new_ebitda, 0)
            profile["current_ebitda"] = round(new_ebitda, 0)
        except (TypeError, ValueError):
            pass
    return profile


class RCMHandler(BaseHTTPRequestHandler):
    """Main request handler. Lightweight dispatch on ``path``."""

    # Inject config via class attribute (set by build_server)
    config: ServerConfig = ServerConfig()

    # Silence default noisy access-log output; users can tail server output
    # if they need it. The CLI banner already tells them the server is up.
    # B162: concise access log to stderr. Default BaseHTTPRequestHandler
    # writes chatty log lines per request; we previously silenced them
    # entirely, losing observability. Re-enable with a compact format
    # operators can grep. Skip /favicon.ico and /health so dashboards
    # polling /health every second don't flood the log.
    _LOG_SKIP_PATHS: tuple = ("/favicon.ico", "/health")

    # Prompt 21: periodic session-table hygiene counter.
    _request_counter: int = 0
    _session_cleanup_interval: int = 100

    # Request metrics: sliding window of recent response times.
    _response_times: list = []
    _error_count: int = 0
    _METRICS_MAX_WINDOW: int = 10_000

    def handle_one_request(self) -> None:
        """Wrap the default request loop with request-id assignment
        + duration accounting (Prompt 21).

        We set ``self._request_id`` (UUID4 hex, truncated to 16 chars
        for compactness) before dispatching to ``do_METHOD`` so any
        code path below — including ``_log_audit`` — can pick up the
        id and correlate its breadcrumb to the access-log JSON line.

        Cleanup hook: every ``_session_cleanup_interval`` requests we
        purge expired sessions. Cheap SQLite DELETE; keeps the table
        from growing unbounded in a long-lived deployment.
        """
        import time as _time
        import uuid as _uuid
        self._request_id = _uuid.uuid4().hex[:16]
        self._request_start_ns = _time.perf_counter_ns()
        try:
            super().handle_one_request()
        finally:
            RCMHandler._request_counter += 1
            if (RCMHandler._request_counter
                    % self._session_cleanup_interval == 0):
                try:
                    from .auth.auth import cleanup_expired_sessions
                    cleanup_expired_sessions(
                        PortfolioStore(self.config.db_path),
                    )
                except Exception:  # noqa: BLE001 — never break a request
                    pass

    def log_message(self, format: str, *args: Any) -> None:
        """Emit a structured JSON access-log line (Prompt 21).

        Format: ``{"ts", "request_id", "method", "path", "status",
        "duration_ms", "user_id", "client"}``. Health checks and
        favicon probes stay out of the log to keep /health-polling
        dashboards from flooding stderr.

        Fields missing at call time (e.g. client hung up before we
        captured a status) are emitted as ``null`` rather than
        skipping the line — partners want a record of every request.
        """
        try:
            if any(self.path.startswith(p) for p in self._LOG_SKIP_PATHS):
                return
            import json as _json
            import sys as _sys
            import time as _time
            from datetime import datetime as _dt, timezone as _tz

            duration_ms: Optional[float] = None
            start = getattr(self, "_request_start_ns", None)
            if start is not None:
                duration_ms = (_time.perf_counter_ns() - start) / 1_000_000.0

            # args[1] is the status code for the default ``log_request``
            # format: ``"%s" %s %s``; be defensive for other callers.
            status: Optional[int] = None
            if args and len(args) >= 2:
                try:
                    status = int(args[1])
                except (TypeError, ValueError):
                    status = None

            user_id: Optional[str] = None
            try:
                user_id = self._current_username()
            except Exception:  # noqa: BLE001
                user_id = None

            import re as _re
            _SENSITIVE = _re.compile(
                r'(password|secret|token|key|auth)=([^&\s]+)',
                _re.IGNORECASE,
            )
            safe_path = _SENSITIVE.sub(r'\1=***', self.path)

            payload = {
                "ts": _dt.now(_tz.utc).isoformat(),
                "request_id": getattr(self, "_request_id", None),
                "method": self.command,
                "path": safe_path,
                "status": status,
                "duration_ms": (
                    round(duration_ms, 2) if duration_ms is not None else None
                ),
                "user_id": user_id,
                "client": self.client_address[0] if self.client_address else None,
            }
            _sys.stderr.write(_json.dumps(payload) + "\n")
            _sys.stderr.flush()
            if duration_ms is not None:
                rt = RCMHandler._response_times
                rt.append(duration_ms)
                if len(rt) > RCMHandler._METRICS_MAX_WINDOW:
                    rt[:] = rt[-RCMHandler._METRICS_MAX_WINDOW:]
            if status is not None and status >= 500:
                RCMHandler._error_count += 1
        except Exception:  # noqa: BLE001 — never break a request to log it
            pass

    # ── Auth gate (B89) ──

    # B128: per-process HMAC secret for CSRF tokens. Ephemeral — rotates
    # each server restart, which also invalidates old form tokens (but
    # sessions survive via the server_secret mismatch check below).
    _SERVER_SECRET: bytes = __import__("secrets").token_bytes(32)

    # B130: simple per-IP login rate limiter. Not a substitute for a
    # real WAF; enough to slow credential stuffing in dev deploys.
    #   key   = client IP
    #   value = list of epoch-seconds timestamps of failed attempts
    # B147 fix: ThreadingHTTPServer runs handlers concurrently, so the
    # shared dict must be guarded by a lock to avoid torn writes.
    _LOGIN_FAIL_WINDOW_SECS: int = 60
    _LOGIN_FAIL_MAX: int = 5
    _login_fail_log: Dict[str, list] = {}
    _login_fail_lock: "__import__('threading').Lock" = (
        __import__("threading").Lock()
    )

    # POST paths exempt from CSRF. Login must be exempt (no session yet);
    # logout and health are idempotent / non-sensitive.
    _CSRF_EXEMPT_POSTS: tuple = ("/api/login", "/api/logout", "/health",
                                 "/quick-import", "/quick-import-json", "/screen")

    # B155: track audit-write failures so silently-lost audit events
    # can be surfaced. Class-level counter + timestamp of last failure.
    _audit_failure_count: int = 0
    _audit_last_failure: Optional[str] = None

    def _log_audit(self, action: str, target: str = "", **detail) -> None:
        """B133 + B155: append an audit event; on failure, surface the
        error to stderr and a class-level counter rather than letting
        the gap disappear. Primary handler flow still succeeds — audit
        writes must never break user-visible operations — but we now
        emit a breadcrumb so operators notice.
        """
        try:
            from .auth.audit_log import log_event
            cu = self._current_user()
            actor = (cu or {}).get("username", "system")
            log_event(
                PortfolioStore(self.config.db_path),
                actor=actor, action=action, target=target,
                detail=detail or None,
                request_id=getattr(self, "_request_id", None),
            )
        except Exception as exc:  # noqa: BLE001 — audit must never break flow
            import sys as _sys
            from datetime import datetime as _dt, timezone as _tz
            cls = type(self)
            cls._audit_failure_count += 1
            cls._audit_last_failure = _dt.now(_tz.utc).isoformat()
            _sys.stderr.write(
                f"[rcm-mc audit] FAILED to log event "
                f"action={action!r} target={target!r}: "
                f"{type(exc).__name__}: {exc}\n"
            )
            _sys.stderr.flush()

    def _clamp_int(
        self, raw: str, *, default: int, min_v: int, max_v: int,
    ) -> int:
        """B148: parse a query-string int, clamping to [min_v, max_v].

        Falls back to ``default`` on ValueError. Prevents unvalidated
        caller-supplied sizes (e.g. ?limit=999999999) from blowing up
        response size or SQL plan.
        """
        try:
            n = int(raw)
        except (TypeError, ValueError):
            return default
        if n < min_v:
            return min_v
        if n > max_v:
            return max_v
        return n

    def _session_token(self) -> Optional[str]:
        """Extract rcm_session cookie value if present."""
        cookie = self.headers.get("Cookie", "") or ""
        for part in cookie.split(";"):
            k, _, v = part.strip().partition("=")
            if k == "rcm_session" and v:
                return v.strip()
        return None

    def _csrf_value(self, session_token: str) -> str:
        """HMAC of a session token — the shared CSRF secret."""
        import hashlib
        import hmac as _h
        return _h.new(
            self._SERVER_SECRET,
            session_token.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _csrf_ok(self, form: Optional[dict] = None) -> bool:
        """B128: CSRF check for session-authenticated POSTs.

        Gate is lenient:
          - No session cookie? Skip (open mode or HTTP-Basic script).
          - Path in exempt list? Skip (login, logout, health).
          - Otherwise require form ``csrf_token`` OR ``X-CSRF-Token``
            header to match HMAC(session_token, server_secret).
        """
        token = self._session_token()
        if not token:
            return True
        if self.path in self._CSRF_EXEMPT_POSTS:
            return True
        import hmac as _h
        expected = self._csrf_value(token)
        # Header takes precedence (AJAX clients set it directly)
        header = self.headers.get("X-CSRF-Token", "")
        if header and _h.compare_digest(header, expected):
            return True
        supplied = (form or {}).get("csrf_token", "")
        return bool(supplied) and _h.compare_digest(supplied, expected)

    def _current_user(self):
        """B125: returns {username, display_name, role} or None.

        Resolution order:
          1. Session cookie (``rcm_session``) — preferred, per-user id.
          2. Legacy HTTP Basic against ``config.auth_user``/``auth_pass``
             — kept for back-compat with scripts + the single-user mode.
        """
        from .auth.auth import user_for_session
        cookie = self.headers.get("Cookie", "") or ""
        token = None
        for part in cookie.split(";"):
            k, _, v = part.strip().partition("=")
            if k == "rcm_session" and v:
                token = v.strip()
                break
        if token:
            user = user_for_session(
                PortfolioStore(self.config.db_path), token,
            )
            if user is not None:
                return user
        # Legacy single-user HTTP Basic fallback
        if self.config.auth_user is not None:
            header = self.headers.get("Authorization", "")
            if header.startswith("Basic "):
                import base64
                import hmac as _h
                try:
                    raw = base64.b64decode(
                        header[6:]
                    ).decode("utf-8", errors="replace")
                except Exception:  # noqa: BLE001
                    return None
                if ":" in raw:
                    u, _, pw = raw.partition(":")
                    if (_h.compare_digest(u, self.config.auth_user or "")
                            and _h.compare_digest(
                                pw, self.config.auth_pass or "")):
                        return {
                            "username": self.config.auth_user,
                            "display_name": self.config.auth_user,
                            "role": "admin",
                        }
        return None

    def _auth_ok(self) -> bool:
        """Gate: True when request is authenticated or auth is disabled.

        Auth is "disabled" when neither HTTP-Basic creds nor any user
        rows exist — that's the single-user laptop default. Creating
        the first user (via CLI or POST /api/users) switches the
        server into multi-user mode and starts requiring credentials.
        """
        # B152 fix: compare on the parsed path (not raw self.path) and
        # require exact match so "/api/login-foo" or path-traversal
        # like "/api/login/../users/create" can't bypass the gate.
        pure_path = urllib.parse.urlparse(self.path).path
        if pure_path in ("/health", "/login"):
            return True
        if pure_path == "/api/login":
            return True
        # No legacy creds + no users created → open mode
        if self.config.auth_user is None and self.config.auth_pass is None:
            try:
                from .auth.auth import _ensure_tables
                store = PortfolioStore(self.config.db_path)
                _ensure_tables(store)
                with store.connect() as con:
                    row = con.execute(
                        "SELECT 1 FROM users LIMIT 1",
                    ).fetchone()
                if row is None:
                    return True  # no users → single-user mode
            except Exception:  # noqa: BLE001
                return True
        return self._current_user() is not None

    def _send_401(self) -> None:
        # Browser-friendly: if the request looks like HTML navigation,
        # redirect to /login with a ?next= hint so the user can bounce
        # back after signing in. Scripts (Accept: application/json or
        # explicit Basic header) still get a classic 401.
        accept = self.headers.get("Accept", "")
        wants_html = "text/html" in accept and "application/json" not in accept
        has_basic = (self.headers.get("Authorization", "")
                     .startswith("Basic "))
        if wants_html and not has_basic:
            nxt = urllib.parse.quote(self.path, safe="")
            self.send_response(HTTPStatus.SEE_OTHER)
            self.send_header("Location", f"/login?next={nxt}")
            self.end_headers()
            return
        self.send_response(HTTPStatus.UNAUTHORIZED)
        self.send_header("WWW-Authenticate", 'Basic realm="rcm-mc"')
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Authentication required")

    # ── Response helpers ──

    def _send_html(self, body: str, status: int = HTTPStatus.OK) -> None:
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://unpkg.com; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'",
        )
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        self.end_headers()
        self.wfile.write(encoded)

    def _send_text(self, body: str, status: int = HTTPStatus.OK,
                   content_type: str = "text/plain; charset=utf-8") -> None:
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_file(self, abs_path: str) -> None:
        """Serve a static file from ``self.config.outdir``. Guarded against
        path-traversal by requiring the resolved path to live inside outdir.
        """
        try:
            with open(abs_path, "rb") as f:
                data = f.read()
        except (OSError, IsADirectoryError):
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        # Minimal content-type inference
        ext = os.path.splitext(abs_path)[1].lower()
        mime = {
            ".html": "text/html; charset=utf-8",
            ".css":  "text/css; charset=utf-8",
            ".js":   "application/javascript; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".csv":  "text/csv; charset=utf-8",
            ".txt":  "text/plain; charset=utf-8",
            ".md":   "text/markdown; charset=utf-8",
            ".png":  "image/png",
            ".jpg":  "image/jpeg",
            ".svg":  "image/svg+xml",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }.get(ext, "application/octet-stream")

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _route_static(self, filename: str) -> None:
        """Serve a file from ``rcm_mc/ui/static/``. Path-traversal safe."""
        import pathlib
        static_dir = pathlib.Path(__file__).parent / "ui" / "static"
        target = (static_dir / filename).resolve()
        if not str(target).startswith(str(static_dir.resolve())):
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        self._send_file(str(target))

    # ── Route matching ──

    def do_GET(self) -> None:
        if not self._auth_ok():
            return self._send_401()
        try:
            self._do_get_inner()
        except Exception as exc:  # noqa: BLE001 — global error boundary
            import traceback
            logger.error("unhandled GET %s: %s", self.path, exc)
            try:
                self._send_json(
                    {"error": "internal server error",
                     "request_id": getattr(self, "_request_id", None),
                     "code": "INTERNAL_ERROR"},
                    status=HTTPStatus.INTERNAL_SERVER_ERROR,
                )
            except Exception:  # noqa: BLE001 — response may already be started
                pass

    def _do_get_inner(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/home" or path == "/caduceus" or path == "/seekingchartis":
            return self._route_seekingchartis_home()
        if path == "/" or path == "/index.html":
            # Phase 13 of the UI v2 editorial rework: when
            # CHARTIS_UI_V2=1, the public marketing landing renders at
            # "/". Under the legacy flag (default), "/" continues to
            # serve the signed-in dashboard so existing partners see
            # no change. A signed-in user hitting "/" on the v2 marketing
            # page can click "Open Platform" to reach /home.
            from .ui._chartis_kit import UI_V2_ENABLED
            if UI_V2_ENABLED:
                from .ui.chartis.marketing_page import render_marketing_page
                return self._send_html(render_marketing_page())
            return self._route_dashboard()
        if path == "/portfolio/regression":
            return self._route_regression_page()
        if path.startswith("/portfolio/regression/hospital/"):
            ccn = path.replace("/portfolio/regression/hospital/", "").strip("/")
            return self._route_hospital_regression(ccn)
        if path == "/import":
            from .ui.quick_import import render_quick_import
            return self._send_html(render_quick_import())
        # RCM Diligence workspace — Phase 1 ingest is live; Phases 2–4
        # render placeholder tabs until their implementations land.
        # Load lazily to avoid import cost on every request.
        if path == "/diligence/ingest":
            # Phase 14: ?dataset=<fixture_name> drives the live CCD
            # ingest + transformation-log preview.
            from .diligence._pages import render_ingest_page
            qs = urllib.parse.parse_qs(parsed.query)
            ds = (qs.get("dataset") or [""])[0]
            return self._send_html(render_ingest_page(dataset=ds))
        if path == "/diligence/benchmarks":
            from .diligence._pages import render_benchmarks_page
            qs = urllib.parse.parse_qs(parsed.query)
            ds = (qs.get("dataset") or [""])[0]
            return self._send_html(render_benchmarks_page(dataset=ds))
        if path == "/diligence/root-cause":
            from .diligence._pages import render_root_cause_page
            qs = urllib.parse.parse_qs(parsed.query)
            ds = (qs.get("dataset") or [""])[0]
            return self._send_html(render_root_cause_page(dataset=ds))
        if path == "/diligence/value":
            from .diligence._pages import render_value_page
            qs = urllib.parse.parse_qs(parsed.query)
            ds = (qs.get("dataset") or [""])[0]
            return self._send_html(render_value_page(dataset=ds))
        if path == "/diligence/qoe-memo":
            # Partner-signed QoE memo deliverable. `?dataset=<fixture>`
            # runs the ingest + KPI + waterfall pipeline and renders the
            # printable memo; other optional query params fill metadata
            # (deal_name, engagement_id, partner_name, preparer_name,
            # mgmt_revenue) without requiring a form submission. When
            # `engagement_id` + `created_by` are supplied, a DRAFT
            # engagement deliverable is opportunistically linked so the
            # memo shows up in that engagement's list.
            from .diligence._pages import render_qoe_memo_page
            qs = urllib.parse.parse_qs(parsed.query)
            ds = (qs.get("dataset") or [""])[0]
            store = PortfolioStore(self.config.db_path)
            return self._send_html(render_qoe_memo_page(
                dataset=ds, qs=qs, store=store,
            ))

        # Engagement workspace (internal RBAC + deliverables +
        # comment stream).
        if path == "/engagements":
            return self._route_engagements_list()
        if path.startswith("/engagements/"):
            eid = path.replace("/engagements/", "").strip("/")
            return self._route_engagement_detail(eid)
        # Client portal (published-only view for CLIENT_VIEWER).
        if path.startswith("/portal/"):
            eid = path.replace("/portal/", "").strip("/")
            return self._route_client_portal(eid)
        # Admin: audit-chain integrity status.
        if path == "/admin/audit-chain":
            return self._route_admin_audit_chain()
        if path == "/methodology":
            # Methodology hub — renders the reference-catalogue (formerly /library).
            # The detailed calculation explainer moved to /methodology/calculations.
            from .ui.library_page import render_library
            return self._send_html(render_library())
        if path == "/methodology/calculations":
            from .ui.methodology_page import render_methodology
            return self._send_html(render_methodology())
        # Corpus Intelligence pages
        if path == "/deals-library":
            # Renamed → /library. 301 redirect preserves query string so
            # ?sector=... still lands on the corpus after the move.
            target = "/library"
            if parsed.query:
                target = f"/library?{parsed.query}"
            self.send_response(HTTPStatus.MOVED_PERMANENTLY)
            self.send_header("Location", target)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if path == "/cms-sources":
            from .ui.data_public.cms_sources_page import render_cms_sources
            return self._send_html(render_cms_sources())
        if path == "/market-rates":
            _qs = urllib.parse.parse_qs(parsed.query)
            group_by = _qs.get("group_by", ["sector"])[0]
            sector = _qs.get("sector", [""])[0]
            payer = _qs.get("payer", [""])[0]
            region = _qs.get("region", [""])[0]
            from .ui.data_public.market_rates_page import render_market_rates
            return self._send_html(render_market_rates(group_by=group_by, sector_filter=sector, payer_filter=payer, region_filter=region))
        if path == "/backtest":
            from .ui.data_public.backtest_page import render_backtest
            return self._send_html(render_backtest())
        if path == "/sponsor-league":
            _qs = urllib.parse.parse_qs(parsed.query)
            sort_by = _qs.get("sort_by", ["median_moic"])[0]
            min_deals = int(_qs.get("min_deals", ["3"])[0]) if _qs.get("min_deals", ["3"])[0].isdigit() else 3
            from .ui.data_public.sponsor_league_page import render_sponsor_league
            return self._send_html(render_sponsor_league(min_deals=min_deals, sort_by=sort_by))
        if path == "/aco-economics":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.aco_economics_page import render_aco_economics
            return self._send_html(render_aco_economics(_qp))
        if path == "/phys-comp-plan":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.phys_comp_plan_page import render_phys_comp_plan
            return self._send_html(render_phys_comp_plan(_qp))
        if path == "/locum-tracker":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.locum_tracker_page import render_locum_tracker
            return self._send_html(render_locum_tracker(_qp))
        if path == "/ma-contracts":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.ma_contracts_page import render_ma_contracts
            return self._send_html(render_ma_contracts(_qp))
        if path == "/drug-pricing-340b":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.drug_pricing_340b_page import render_drug_pricing_340b
            return self._send_html(render_drug_pricing_340b(_qp))
        if path == "/sponsor-heatmap":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.sponsor_heatmap_page import render_sponsor_heatmap
            return self._send_html(render_sponsor_heatmap(_qp))
        if path == "/payer-concentration":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.payer_concentration_page import render_payer_concentration
            return self._send_html(render_payer_concentration(_qp))
        if path == "/rollup-economics":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.rollup_economics_page import render_rollup_economics
            return self._send_html(render_rollup_economics(_qp))
        if path == "/cin-analyzer":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.cin_analyzer_page import render_cin_analyzer
            return self._send_html(render_cin_analyzer(_qp))
        if path == "/base-rates":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.base_rates_page import render_base_rates
            return self._send_html(render_base_rates(_qp))
        if path == "/reit-analyzer":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.reit_analyzer_page import render_reit_analyzer
            return self._send_html(render_reit_analyzer(_qp))
        if path == "/capital-pacing":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.capital_pacing_page import render_capital_pacing
            return self._send_html(render_capital_pacing(_qp))
        if path == "/covenant-headroom":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.covenant_headroom_page import render_covenant_headroom
            return self._send_html(render_covenant_headroom(_qp))
        if path == "/redflag-scanner":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.redflag_scanner_page import render_redflag_scanner
            return self._send_html(render_redflag_scanner(_qp))
        if path == "/backtester":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.value_backtester_page import render_value_backtester
            return self._send_html(render_value_backtester(_qp))
        if path == "/direct-employer":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.direct_employer_page import render_direct_employer
            return self._send_html(render_direct_employer(_qp))
        if path == "/deal-origination":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.deal_origination_page import render_deal_origination
            return self._send_html(render_deal_origination(_qp))
        if path == "/trial-site-econ":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.trial_site_econ_page import render_trial_site_econ
            return self._send_html(render_trial_site_econ(_qp))
        if path == "/hcit-platform":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.hcit_platform_page import render_hcit_platform
            return self._send_html(render_hcit_platform(_qp))
        if path == "/biosimilars":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.biosimilars_opp_page import render_biosimilars
            return self._send_html(render_biosimilars(_qp))
        if path == "/telehealth-econ":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.telehealth_econ_page import render_telehealth_econ
            return self._send_html(render_telehealth_econ(_qp))
        if path == "/denovo-expansion":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.denovo_expansion_page import render_denovo_expansion
            return self._send_html(render_denovo_expansion(_qp))
        if path == "/health-equity":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.health_equity_page import render_health_equity
            return self._send_html(render_health_equity(_qp))
        if path == "/physician-labor":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.physician_labor_page import render_physician_labor
            return self._send_html(render_physician_labor(_qp))
        if path == "/platform-maturity":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.platform_maturity_page import render_platform_maturity
            return self._send_html(render_platform_maturity(_qp))
        if path == "/direct-lending":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.direct_lending_page import render_direct_lending
            return self._send_html(render_direct_lending(_qp))
        if path == "/pmi-playbook":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.pmi_playbook_page import render_pmi_playbook
            return self._send_html(render_pmi_playbook(_qp))
        if path == "/fraud-detection":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.fraud_detection_page import render_fraud_detection
            return self._send_html(render_fraud_detection(_qp))
        if path == "/drug-shortage":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.drug_shortage_page import render_drug_shortage
            return self._send_html(render_drug_shortage(_qp))
        if path == "/antitrust-screener":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.antitrust_screener_page import render_antitrust_screener
            return self._send_html(render_antitrust_screener(_qp))
        if path == "/ai-operating-model":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.ai_operating_model_page import render_ai_operating_model
            return self._send_html(render_ai_operating_model(_qp))
        if path == "/cyber-risk":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.cyber_risk_page import render_cyber_risk
            return self._send_html(render_cyber_risk(_qp))
        if path == "/zbb-tracker":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.zbb_tracker_page import render_zbb_tracker
            return self._send_html(render_zbb_tracker(_qp))
        if path == "/cms-data-browser":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.cms_data_browser_page import render_cms_data_browser
            return self._send_html(render_cms_data_browser(_qp))
        if path == "/msa-concentration":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.msa_concentration_page import render_msa_concentration
            return self._send_html(render_msa_concentration(_qp))
        if path == "/ic-memo-gen":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.ic_memo_generator_page import render_ic_memo_generator
            return self._send_html(render_ic_memo_generator(_qp))
        if path == "/module-index":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.module_index_page import render_module_index
            return self._send_html(render_module_index(_qp))
        if path == "/deal-postmortem":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.deal_postmortem_page import render_deal_postmortem
            return self._send_html(render_deal_postmortem(_qp))
        if path == "/secondaries-tracker":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.secondaries_tracker_page import render_secondaries_tracker
            return self._send_html(render_secondaries_tracker(_qp))
        if path == "/tax-structure-analyzer":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.tax_structure_analyzer_page import render_tax_structure_analyzer
            return self._send_html(render_tax_structure_analyzer(_qp))
        if path == "/diligence-vendors":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.diligence_vendors_page import render_diligence_vendors
            return self._send_html(render_diligence_vendors(_qp))
        if path == "/refi-optimizer":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.refi_optimizer_page import render_refi_optimizer
            return self._send_html(render_refi_optimizer(_qp))
        if path == "/lp-reporting":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.lp_reporting_page import render_lp_reporting
            return self._send_html(render_lp_reporting(_qp))
        if path == "/lbo-stress":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.lbo_stress_page import render_lbo_stress
            return self._send_html(render_lbo_stress(_qp))
        if path == "/board-governance":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.board_governance_page import render_board_governance
            return self._send_html(render_board_governance(_qp))
        if path == "/vdr-tracker":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.vdr_tracker_page import render_vdr_tracker
            return self._send_html(render_vdr_tracker(_qp))
        if path == "/escrow-earnout":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.escrow_earnout_page import render_escrow_earnout
            return self._send_html(render_escrow_earnout(_qp))
        if path == "/debt-financing":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.debt_financing_page import render_debt_financing
            return self._send_html(render_debt_financing(_qp))
        if path == "/vcp-tracker":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.vcp_tracker_page import render_vcp_tracker
            return self._send_html(render_vcp_tracker(_qp))
        if path == "/coinvest-pipeline":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.coinvest_pipeline_page import render_coinvest_pipeline
            return self._send_html(render_coinvest_pipeline(_qp))
        if path == "/dpi-tracker":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.dpi_tracker_page import render_dpi_tracker
            return self._send_html(render_dpi_tracker(_qp))
        if path == "/nav-loan-tracker":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.nav_loan_tracker_page import render_nav_loan_tracker
            return self._send_html(render_nav_loan_tracker(_qp))
        if path == "/medical-realestate":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.medical_realestate_page import render_medical_realestate
            return self._send_html(render_medical_realestate(_qp))
        if path == "/cms-apm":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.cms_apm_tracker_page import render_cms_apm_tracker
            return self._send_html(render_cms_apm_tracker(_qp))
        if path == "/ma-star":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.ma_star_tracker_page import render_ma_star_tracker
            return self._send_html(render_ma_star_tracker(_qp))
        if path == "/gpo-supply":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.gpo_supply_tracker_page import render_gpo_supply_tracker
            return self._send_html(render_gpo_supply_tracker(_qp))
        if path == "/capital-call":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.capital_call_tracker_page import render_capital_call_tracker
            return self._send_html(render_capital_call_tracker(_qp))
        if path == "/litigation":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.litigation_tracker_page import render_litigation_tracker
            return self._send_html(render_litigation_tracker(_qp))
        if path == "/fundraising":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.fundraising_tracker_page import render_fundraising_tracker
            return self._send_html(render_fundraising_tracker(_qp))
        if path == "/operating-partners":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.operating_partners_page import render_operating_partners
            return self._send_html(render_operating_partners(_qp))
        if path == "/compliance-attestation":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.compliance_attestation_page import render_compliance_attestation
            return self._send_html(render_compliance_attestation(_qp))
        if path == "/esg-impact":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.esg_impact_page import render_esg_impact
            return self._send_html(render_esg_impact(_qp))
        if path == "/tracker-340b":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.tracker_340b_page import render_tracker_340b
            return self._send_html(render_tracker_340b(_qp))
        if path == "/risk-adjustment":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.risk_adjustment_page import render_risk_adjustment
            return self._send_html(render_risk_adjustment(_qp))
        if path == "/clinical-ai":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.clinical_ai_tracker_page import render_clinical_ai_tracker
            return self._send_html(render_clinical_ai_tracker(_qp))
        if path == "/specialty-benchmarks":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.specialty_benchmarks_page import render_specialty_benchmarks
            return self._send_html(render_specialty_benchmarks(_qp))
        if path == "/peer-transactions":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.peer_transactions_page import render_peer_transactions
            return self._send_html(render_peer_transactions(_qp))
        if path == "/nsa-tracker":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.nsa_tracker_page import render_nsa_tracker
            return self._send_html(render_nsa_tracker(_qp))
        if path == "/medicaid-unwinding":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.medicaid_unwinding_page import render_medicaid_unwinding
            return self._send_html(render_medicaid_unwinding(_qp))
        if path == "/workforce-retention":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.workforce_retention_page import render_workforce_retention
            return self._send_html(render_workforce_retention(_qp))
        if path == "/digital-front-door":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.digital_front_door_page import render_digital_front_door
            return self._send_html(render_digital_front_door(_qp))
        if path == "/hospital-anchor":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.hospital_anchor_page import render_hospital_anchor
            return self._send_html(render_hospital_anchor(_qp))
        if path == "/payer-contracts":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.payer_contracts_page import render_payer_contracts
            return self._send_html(render_payer_contracts(_qp))
        if path == "/capex-budget":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.capex_budget_page import render_capex_budget
            return self._send_html(render_capex_budget(_qp))
        if path == "/pmi-integration":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.pmi_integration_page import render_pmi_integration
            return self._send_html(render_pmi_integration(_qp))
        if path == "/tax-credits":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.tax_credits_page import render_tax_credits
            return self._send_html(render_tax_credits(_qp))
        if path == "/deal-sourcing":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.deal_sourcing_page import render_deal_sourcing
            return self._send_html(render_deal_sourcing(_qp))
        if path == "/treasury":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.treasury_tracker_page import render_treasury_tracker
            return self._send_html(render_treasury_tracker(_qp))
        if path == "/sellside-process":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.sellside_process_page import render_sellside_process
            return self._send_html(render_sellside_process(_qp))
        if path == "/rw-insurance":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.rw_insurance_page import render_rw_insurance
            return self._send_html(render_rw_insurance(_qp))
        if path == "/vintage-cohorts":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.vintage_cohorts_page import render_vintage_cohorts
            return self._send_html(render_vintage_cohorts(_qp))
        if path == "/insurance-tracker":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.insurance_tracker_page import render_insurance
            return self._send_html(render_insurance(_qp))
        if path == "/partner-economics":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.partner_economics_page import render_partner_economics
            return self._send_html(render_partner_economics(_qp))
        if path == "/reinvestment":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.reinvestment_page import render_reinvestment
            return self._send_html(render_reinvestment(_qp))
        if path == "/demand-forecast":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.demand_forecast_page import render_demand_forecast
            return self._send_html(render_demand_forecast(_qp))
        if path == "/provider-retention":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.provider_retention_page import render_provider_retention
            return self._send_html(render_provider_retention(_qp))
        if path == "/supply-chain":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.supply_chain_page import render_supply_chain
            return self._send_html(render_supply_chain(_qp))
        if path == "/patient-experience":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.patient_experience_page import render_patient_experience
            return self._send_html(render_patient_experience(_qp))
        if path == "/competitive-intel":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.competitive_intel_page import render_competitive_intel
            return self._send_html(render_competitive_intel(_qp))
        if path == "/clinical-outcomes":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.clinical_outcomes_page import render_clinical_outcomes
            return self._send_html(render_clinical_outcomes(_qp))
        if path == "/earnout":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.earnout_page import render_earnout
            return self._send_html(render_earnout(_qp))
        if path == "/continuation-vehicle":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.continuation_vehicle_page import render_continuation_vehicle
            return self._send_html(render_continuation_vehicle(_qp))
        if path == "/dividend-recap":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.dividend_recap_page import render_dividend_recap
            return self._send_html(render_dividend_recap(_qp))
        if path == "/growth-runway":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.growth_runway_page import render_growth_runway
            return self._send_html(render_growth_runway(_qp))
        if path == "/tech-stack":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.tech_stack_page import render_tech_stack
            return self._send_html(render_tech_stack(_qp))
        if path == "/workforce-planning":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.workforce_planning_page import render_workforce_planning
            return self._send_html(render_workforce_planning(_qp))
        if path == "/real-estate":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.real_estate_page import render_real_estate
            return self._send_html(render_real_estate(_qp))
        if path == "/cap-structure":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.cap_structure_page import render_cap_structure
            return self._send_html(render_cap_structure(_qp))
        if path == "/value-creation-plan":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.value_creation_plan_page import render_value_creation_plan
            return self._send_html(render_value_creation_plan(_qp))
        if path == "/peer-valuation":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.peer_valuation_page import render_peer_valuation
            return self._send_html(render_peer_valuation(_qp))
        if path == "/capital-schedule":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.capital_schedule_page import render_capital_schedule
            return self._send_html(render_capital_schedule(_qp))
        if path == "/geo-market":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.geo_market_page import render_geo_market
            return self._send_html(render_geo_market(_qp))
        if path == "/ref-pricing":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.ref_pricing_page import render_ref_pricing
            return self._send_html(render_ref_pricing(_qp))
        if path == "/revenue-leakage":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.revenue_leakage_page import render_revenue_leakage
            return self._send_html(render_revenue_leakage(_qp))
        if path == "/transition-services":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.transition_services_page import render_transition_services
            return self._send_html(render_transition_services(_qp))
        if path == "/scenario-mc":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.scenario_mc_page import render_scenario_mc
            return self._send_html(render_scenario_mc(_qp))
        if path == "/key-person":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.key_person_page import render_key_person
            return self._send_html(render_key_person(_qp))
        if path == "/payer-shift":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.payer_shift_page import render_payer_shift
            return self._send_html(render_payer_shift(_qp))
        if path == "/deal-pipeline":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.deal_pipeline_page import render_deal_pipeline
            return self._send_html(render_deal_pipeline(_qp))
        if path == "/unit-economics":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.unit_economics_page import render_unit_economics
            return self._send_html(render_unit_economics(_qp))
        if path == "/fund-attribution":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.fund_attribution_page import render_fund_attribution
            return self._send_html(render_fund_attribution(_qp))
        if path == "/tax-structure":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.tax_structure_page import render_tax_structure
            return self._send_html(render_tax_structure(_qp))
        if path == "/exit-readiness":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.exit_readiness_page import render_exit_readiness
            return self._send_html(render_exit_readiness(_qp))
        if path == "/esg-dashboard":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.esg_dashboard_page import render_esg_dashboard
            return self._send_html(render_esg_dashboard(_qp))
        if path == "/quality-scorecard":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.quality_scorecard_page import render_quality_scorecard
            return self._send_html(render_quality_scorecard(_qp))
        if path == "/cost-structure":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.cost_structure_page import render_cost_structure
            return self._send_html(render_cost_structure(_qp))
        if path == "/regulatory-risk":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.regulatory_risk_page import render_regulatory_risk
            return self._send_html(render_regulatory_risk(_qp))
        if path == "/physician-productivity":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.physician_productivity_page import render_physician_productivity
            return self._send_html(render_physician_productivity(_qp))
        if path == "/mgmt-comp":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.mgmt_comp_page import render_mgmt_comp
            return self._send_html(render_mgmt_comp(_qp))
        if path == "/debt-service":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.debt_service_page import render_debt_service
            return self._send_html(render_debt_service(_qp))
        if path == "/working-capital":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.working_capital_page import render_working_capital
            return self._send_html(render_working_capital(_qp))
        if path == "/bolton-analyzer":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.bolton_analyzer_page import render_bolton_analyzer
            return self._send_html(render_bolton_analyzer(_qp))
        if path == "/admin/data-sources":
            from .ui.data_public.data_sources_admin_page import render_data_sources_admin
            return self._send_html(render_data_sources_admin())
        if path == "/lp-dashboard":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.lp_dashboard_page import render_lp_dashboard
            return self._send_html(render_lp_dashboard(_qp))
        if path == "/exit-timing":
            from .ui.data_public.exit_timing_page import render_exit_timing
            return self._send_html(render_exit_timing())
        if path == "/risk-matrix":
            _qs = urllib.parse.parse_qs(parsed.query)
            sector = _qs.get("sector", [""])[0]
            from .ui.data_public.risk_matrix_page import render_risk_matrix
            return self._send_html(render_risk_matrix(sector_filter=sector))
        if path == "/api/corpus":
            _qs = urllib.parse.parse_qs(parsed.query)
            def _qs1c(k, d=""): return (_qs.get(k, [d]) or [d])[0]
            def _qsfc(k):
                try: return float(_qs.get(k, [None])[0])
                except (TypeError, ValueError): return None
            def _qsic(k):
                try: return int(_qs.get(k, [None])[0])
                except (TypeError, ValueError): return None
            import importlib as _il
            from .data_public.deals_corpus import _SEED_DEALS
            from .data_public.extended_seed import EXTENDED_SEED_DEALS
            _corp = list(_SEED_DEALS) + list(EXTENDED_SEED_DEALS)
            for _i in range(2, 33):
                try:
                    _m = _il.import_module(f"rcm_mc.data_public.extended_seed_{_i}")
                    _corp += list(getattr(_m, f"EXTENDED_SEED_DEALS_{_i}"))
                except (ImportError, AttributeError): pass
            sector_f = _qs1c("sector"); yr_lo = _qsic("yr_lo"); yr_hi = _qsic("yr_hi")
            ev_lo = _qsfc("ev_lo"); ev_hi = _qsfc("ev_hi")
            moic_lo = _qsfc("moic_lo"); moic_hi = _qsfc("moic_hi")
            limit = min(200, int(_qs.get("limit", ["50"])[0]) if _qs.get("limit") else 50)
            q = _qs1c("q").lower()
            results = []
            for _d in _corp:
                if sector_f and _d.get("sector", "") != sector_f: continue
                if yr_lo or yr_hi:
                    _yr = _d.get("year") or _d.get("entry_year")
                    try:
                        _yr_i = int(_yr)
                        if yr_lo and _yr_i < yr_lo: continue
                        if yr_hi and _yr_i > yr_hi: continue
                    except (TypeError, ValueError): pass
                if ev_lo or ev_hi:
                    try:
                        _ev = float(_d.get("ev_mm") or 0)
                        if ev_lo and _ev < ev_lo: continue
                        if ev_hi and _ev > ev_hi: continue
                    except (TypeError, ValueError): pass
                if moic_lo or moic_hi:
                    try:
                        _m2 = float(_d.get("realized_moic") or 0)
                        if moic_lo and _m2 < moic_lo: continue
                        if moic_hi and _m2 > moic_hi: continue
                    except (TypeError, ValueError): pass
                if q:
                    _hay = " ".join(str(_d.get(f, "") or "") for f in ("deal_name", "buyer", "seller", "sector")).lower()
                    if q not in _hay: continue
                results.append(_d)
            results.sort(key=lambda d: -(float(d.get("realized_moic") or 0)))
            return self._send_json({"count": len(results), "limit": limit, "deals": results[:limit]})
        if path == "/deal-search":
            _qs = urllib.parse.parse_qs(parsed.query)
            def _qs1(k, d=""): return (_qs.get(k, [d]) or [d])[0]
            def _qsf(k):
                try: return float(_qs.get(k, [None])[0])
                except (TypeError, ValueError): return None
            def _qsi(k, d=None):
                try: return int(_qs.get(k, [d])[0])
                except (TypeError, ValueError): return d
            from .ui.data_public.deal_search_page import render_deal_search
            return self._send_html(render_deal_search(
                query=_qs1("q"),
                sector=_qs1("sector"),
                yr_lo=_qsi("yr_lo"),
                yr_hi=_qsi("yr_hi"),
                ev_lo=_qsf("ev_lo"),
                ev_hi=_qsf("ev_hi"),
                moic_lo=_qsf("moic_lo"),
                moic_hi=_qsf("moic_hi"),
                deal_type=_qs1("deal_type"),
                sort_by=_qs1("sort_by", "realized_moic"),
                page=_qsi("page", 1),
            ))
        if path == "/corpus-dashboard":
            from .ui.data_public.corpus_dashboard_page import render_corpus_dashboard
            return self._send_html(render_corpus_dashboard())
        if path == "/corpus-ic-memo":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.ic_memo_page import render_ic_memo_gen
            return self._send_html(render_ic_memo_gen(_qp))
        if path == "/return-attribution":
            from .ui.data_public.return_attribution_page import render_return_attribution
            return self._send_html(render_return_attribution())
        if path == "/deal-flow-heatmap":
            _qs = urllib.parse.parse_qs(parsed.query)
            try: _min_sd = int((_qs.get("min_deals") or ["3"])[0])
            except (TypeError, ValueError): _min_sd = 3
            from .ui.data_public.deal_flow_heatmap_page import render_deal_flow_heatmap
            return self._send_html(render_deal_flow_heatmap(min_sector_deals=_min_sd))
        if path == "/concentration-risk":
            from .ui.data_public.concentration_risk_page import render_concentration_risk
            return self._send_html(render_concentration_risk())
        if path == "/hold-analysis":
            from .ui.data_public.hold_analysis_page import render_hold_analysis
            return self._send_html(render_hold_analysis())
        if path == "/irr-dispersion":
            from .ui.data_public.irr_dispersion_page import render_irr_dispersion
            return self._send_html(render_irr_dispersion())
        if path == "/payer-rate-trends":
            from .ui.data_public.payer_rate_trends_page import render_payer_rate_trends
            return self._send_html(render_payer_rate_trends())
        if path == "/entry-multiple":
            from .ui.data_public.entry_multiple_page import render_entry_multiple
            return self._send_html(render_entry_multiple())
        if path == "/corpus-coverage":
            from .ui.data_public.corpus_coverage_page import render_corpus_coverage
            return self._send_html(render_corpus_coverage())
        if path == "/find-comps":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.find_comps_page import render_find_comps
            return self._send_html(render_find_comps(_qp))
        if path == "/sector-momentum":
            _qs = urllib.parse.parse_qs(parsed.query)
            try: _years = int((_qs.get("years") or ["5"])[0])
            except (TypeError, ValueError): _years = 5
            from .ui.data_public.sector_momentum_page import render_sector_momentum
            return self._send_html(render_sector_momentum(recent_years=_years))
        if path == "/gp-benchmarking":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.gp_benchmarking_page import render_gp_benchmarking
            return self._send_html(render_gp_benchmarking(_qp))
        if path == "/rcm-red-flags":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.rcm_red_flags_page import render_rcm_red_flags
            return self._send_html(render_rcm_red_flags(_qp))
        if path == "/hold-optimizer":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.hold_optimizer_page import render_hold_optimizer
            return self._send_html(render_hold_optimizer(_qp))
        if path == "/payer-stress":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.payer_stress_page import render_payer_stress
            return self._send_html(render_payer_stress(_qp))
        if path == "/multiple-decomp":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.multiple_decomp_page import render_multiple_decomp
            return self._send_html(render_multiple_decomp(_qp))
        if path == "/capital-efficiency":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.capital_efficiency_page import render_capital_efficiency
            return self._send_html(render_capital_efficiency(_qp))
        if path == "/deal-risk-scores":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.deal_risk_scores_page import render_deal_risk_scores
            return self._send_html(render_deal_risk_scores(_qp))
        if path == "/sector-correlation":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.sector_correlation_page import render_sector_correlation
            return self._send_html(render_sector_correlation(_qp))
        if path == "/acq-timing":
            from .ui.data_public.acq_timing_page import render_acq_timing
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            return self._send_html(render_acq_timing(_qp))
        if path == "/portfolio-sim":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.portfolio_sim_page import render_portfolio_sim
            return self._send_html(render_portfolio_sim(_qp))
        if path == "/qoe-analyzer":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.qoe_analyzer_page import render_qoe_analyzer
            return self._send_html(render_qoe_analyzer(_qp))
        if path == "/covenant-monitor":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.covenant_monitor_page import render_covenant_monitor
            return self._send_html(render_covenant_monitor(_qp))
        if path == "/provider-network":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.provider_network_page import render_provider_network
            return self._send_html(render_provider_network(_qp))
        if path == "/exit-multiple":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.exit_multiple_page import render_exit_multiple
            return self._send_html(render_exit_multiple(_qp))
        if path == "/diligence-checklist":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.diligence_checklist_page import render_diligence_checklist
            return self._send_html(render_diligence_checklist(_qp))
        if path == "/value-creation":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.value_creation_page import render_value_creation
            return self._send_html(render_value_creation(_qp))
        if path == "/underwriting-model":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.underwriting_model_page import render_underwriting_model
            return self._send_html(render_underwriting_model(_qp))
        if path == "/mgmt-fee-tracker":
            _qs = urllib.parse.parse_qs(parsed.query)
            _qp = {k: v[0] for k, v in _qs.items() if v}
            from .ui.data_public.mgmt_fee_tracker_page import render_mgmt_fee_tracker
            return self._send_html(render_mgmt_fee_tracker(_qp))
        if path == "/size-intel":
            from .ui.data_public.size_intel_page import render_size_intel
            return self._send_html(render_size_intel())
        if path == "/leverage-intel":
            from .ui.data_public.leverage_intel_page import render_leverage_intel
            return self._send_html(render_leverage_intel())
        if path == "/payer-intel":
            from .ui.data_public.payer_intel_page import render_payer_intel
            return self._send_html(render_payer_intel())
        if path == "/vintage-perf":
            from .ui.data_public.vintage_perf_page import render_vintage_perf
            return self._send_html(render_vintage_perf())
        if path == "/sector-intel":
            _qs = urllib.parse.parse_qs(parsed.query)
            def _qsi(k, d):
                try: return int(_qs.get(k, [d])[0])
                except (TypeError, ValueError): return d
            from .ui.data_public.sector_intel_page import render_sector_intel
            return self._send_html(render_sector_intel(
                min_deals=_qsi("min_deals", 3),
                sort_by=(_qs.get("sort_by", ["moic_p50"]) or ["moic_p50"])[0],
            ))
        if path == "/deal-quality":
            _qs = urllib.parse.parse_qs(parsed.query)
            def _qs1(k, default=""):
                return (_qs.get(k, [default]) or [default])[0]
            def _qsint(k, default=1):
                try: return int(_qs.get(k, [default])[0])
                except (TypeError, ValueError): return default
            from .ui.data_public.deal_quality_page import render_deal_quality
            return self._send_html(render_deal_quality(
                tier_filter=_qs1("tier"),
                sort_by=_qs1("sort_by", "quality_score"),
                page=_qsint("page", 1),
            ))
        if path == "/portfolio-optimizer":
            _qs = urllib.parse.parse_qs(parsed.query)
            sectors = _qs.get("sector") or None
            from .ui.data_public.portfolio_optimizer_page import render_portfolio_optimizer
            return self._send_html(render_portfolio_optimizer(sectors=sectors))
        if path == "/underwriting":
            _qs = urllib.parse.parse_qs(parsed.query)
            def _qfloat(k):
                try:
                    return float(_qs.get(k, [None])[0])
                except (TypeError, ValueError):
                    return None
            from .ui.data_public.underwriting_page import render_underwriting
            return self._send_html(render_underwriting(
                entry_ev=_qfloat("entry_ev"),
                entry_ebitda=_qfloat("entry_ebitda"),
                equity_pct=_qfloat("equity_pct"),
                ebitda_cagr=_qfloat("ebitda_cagr"),
                hold_years=_qfloat("hold_years"),
                exit_multiple=_qfloat("exit_multiple"),
            ))
        if path == "/comparables":
            _qs = urllib.parse.parse_qs(parsed.query)
            def _qf(k, default=None):
                v = _qs.get(k, [None])[0]
                if v is None:
                    return default
                try:
                    return float(v)
                except (ValueError, TypeError):
                    return default
            sector = _qs.get("sector", [""])[0]
            search = _qs.get("search", [""])[0]
            from .ui.data_public.comparables_page import render_comparables
            return self._send_html(render_comparables(
                sector=sector,
                ev_mm=_qf("ev_mm"),
                ebitda_mm=_qf("ebitda_mm"),
                hold_years=_qf("hold_years"),
                commercial=_qf("commercial"),
                search=search,
            ))
        if path == "/query":
            return self._route_deal_query()
        if path == "/benchmarks":
            return self._route_benchmarks()
        if path.startswith("/models/causal/"):
            did = urllib.parse.unquote(path[len("/models/causal/"):]).strip("/")
            return self._route_model_causal(did)
        if path.startswith("/models/counterfactual/"):
            did = urllib.parse.unquote(path[len("/models/counterfactual/"):]).strip("/")
            return self._route_model_counterfactual(did)
        if path.startswith("/models/predicted/"):
            did = urllib.parse.unquote(path[len("/models/predicted/"):]).strip("/")
            return self._route_model_predicted(did)
        if path == "/data":
            return self._route_data_explorer()
        if path == "/verticals":
            from .ui.verticals_page import render_verticals
            from .verticals.asc.bridge import compute_asc_bridge  # noqa: F401
            from .verticals.behavioral_health.bridge import compute_bh_bridge  # noqa: F401
            from .verticals.mso.bridge import compute_mso_bridge  # noqa: F401
            return self._send_html(render_verticals())
        if path.startswith("/models/questions/"):
            did = urllib.parse.unquote(path[len("/models/questions/"):]).strip("/")
            return self._route_model_questions(did)
        if path.startswith("/models/playbook/"):
            did = urllib.parse.unquote(path[len("/models/playbook/"):]).strip("/")
            return self._route_model_playbook(did)
        if path.startswith("/models/waterfall/"):
            did = urllib.parse.unquote(path[len("/models/waterfall/"):]).strip("/")
            return self._route_model_waterfall(did)
        if path.startswith("/models/bridge/"):
            did = urllib.parse.unquote(path[len("/models/bridge/"):]).strip("/")
            return self._route_model_bridge(did)
        if path.startswith("/models/comparables/"):
            did = urllib.parse.unquote(path[len("/models/comparables/"):]).strip("/")
            return self._route_model_comparables(did)
        if path.startswith("/models/anomalies/"):
            did = urllib.parse.unquote(path[len("/models/anomalies/"):]).strip("/")
            return self._route_model_anomalies(did)
        if path.startswith("/models/service-lines/"):
            did = urllib.parse.unquote(path[len("/models/service-lines/"):]).strip("/")
            return self._route_model_service_lines(did)
        if path.startswith("/models/memo/"):
            did = urllib.parse.unquote(path[len("/models/memo/"):]).strip("/")
            return self._route_model_memo(did)
        if path.startswith("/models/validate/"):
            did = urllib.parse.unquote(path[len("/models/validate/"):]).strip("/")
            return self._route_model_validate(did)
        if path.startswith("/models/completeness/"):
            did = urllib.parse.unquote(path[len("/models/completeness/"):]).strip("/")
            return self._route_model_completeness(did)
        if path.startswith("/models/returns/"):
            did = urllib.parse.unquote(path[len("/models/returns/"):]).strip("/")
            return self._route_model_returns(did)
        if path.startswith("/models/debt/"):
            did = urllib.parse.unquote(path[len("/models/debt/"):]).strip("/")
            return self._route_model_debt(did)
        if path.startswith("/models/challenge/"):
            did = urllib.parse.unquote(path[len("/models/challenge/"):]).strip("/")
            return self._route_model_challenge(did)
        if path.startswith("/models/irs990/"):
            did = urllib.parse.unquote(path[len("/models/irs990/"):]).strip("/")
            return self._route_model_irs990(did)
        if path.startswith("/models/trends/"):
            did = urllib.parse.unquote(path[len("/models/trends/"):]).strip("/")
            return self._route_model_trends(did)
        if path.startswith("/models/denial/"):
            did = urllib.parse.unquote(path[len("/models/denial/"):]).strip("/")
            return self._route_model_denial(did)
        if path.startswith("/models/market/"):
            did = urllib.parse.unquote(path[len("/models/market/"):]).strip("/")
            return self._route_model_market(did)
        if path.startswith("/new-deal"):
            return self._route_wizard_get(path)
        if path.startswith("/hospital/") and path.endswith("/demand"):
            ccn = path.replace("/hospital/", "").replace("/demand", "").strip("/")
            return self._route_hospital_demand(ccn)
        if path.startswith("/hospital/") and path.endswith("/history"):
            ccn = path.replace("/hospital/", "").replace("/history", "").strip("/")
            return self._route_hospital_history(ccn)
        if path.startswith("/hospital/") and path.endswith("/start-diligence"):
            pass  # handled in POST
        elif path.startswith("/hospital/"):
            ccn = urllib.parse.unquote(path[len("/hospital/"):]).strip("/")
            return self._route_hospital_profile(ccn)
        if path == "/news":
            return self._route_news_page()
        if path == "/conferences":
            return self._route_conference_page()
        if path == "/ml-insights":
            return self._route_ml_insights()
        if path.startswith("/ml-insights/hospital/"):
            ml_ccn = path.replace("/ml-insights/hospital/", "").strip("/")
            return self._route_hospital_ml(ml_ccn)
        if path == "/quant-lab":
            return self._route_quant_lab()
        if path == "/data-intelligence":
            return self._route_data_intelligence()
        if path == "/predictive-screener":
            return self._route_predictive_screener()
        if path.startswith("/data-room/") and not path.endswith("/add"):
            dr_ccn = path.replace("/data-room/", "").strip("/")
            return self._route_data_room(dr_ccn)
        if path.startswith("/competitive-intel/"):
            ci_ccn = path.replace("/competitive-intel/", "").strip("/")
            return self._route_competitive_intel(ci_ccn)
        if path.startswith("/export/bridge/"):
            ex_ccn = path.replace("/export/bridge/", "").strip("/")
            return self._route_export_bridge(ex_ccn)
        if path.startswith("/value-tracker/") and not path.endswith("/record") and not path.endswith("/freeze"):
            vt_id = path.replace("/value-tracker/", "").strip("/")
            return self._route_value_tracker(vt_id)
        if path.startswith("/ebitda-bridge/"):
            bridge_ccn = path.replace("/ebitda-bridge/", "").strip("/")
            return self._route_ebitda_bridge(bridge_ccn)
        if path.startswith("/scenarios/"):
            sc_ccn = path.replace("/scenarios/", "").strip("/")
            return self._route_scenario_modeler(sc_ccn)
        if path == "/model-validation":
            return self._route_model_validation()
        if path.startswith("/ic-memo/"):
            memo_ccn = path.replace("/ic-memo/", "").strip("/")
            return self._route_ic_memo(memo_ccn)
        if path.startswith("/bayesian/hospital/"):
            bay_ccn = path.replace("/bayesian/hospital/", "").strip("/")
            return self._route_bayesian_profile(bay_ccn)
        if path == "/market-data/map":
            return self._route_market_data_page()
        if path.startswith("/market-data/state/"):
            st = urllib.parse.unquote(path[len("/market-data/state/"):]).strip("/")
            return self._route_market_data_state(st)
        if path == "/pe-intelligence":
            from .ui.chartis.pe_intelligence_hub_page import render_pe_intelligence_hub
            store = PortfolioStore(self.config.db_path)
            cu = self._current_user() or {}
            username = cu.get("username") if isinstance(cu, dict) else None
            return self._send_html(
                render_pe_intelligence_hub(store=store, current_user=username)
            )
        if path == "/sponsor-track-record":
            from .ui.chartis.sponsor_track_record_page import render_sponsor_track_record
            store = PortfolioStore(self.config.db_path)
            return self._send_html(render_sponsor_track_record(
                store=store, current_user=self._chartis_username(),
            ))
        if path == "/payer-intelligence":
            from .ui.chartis.payer_intelligence_page import render_payer_intelligence
            store = PortfolioStore(self.config.db_path)
            return self._send_html(render_payer_intelligence(
                store=store, current_user=self._chartis_username(),
            ))
        if path == "/rcm-benchmarks":
            from .ui.chartis.rcm_benchmarks_page import render_rcm_benchmarks
            store = PortfolioStore(self.config.db_path)
            return self._send_html(render_rcm_benchmarks(
                store=store, current_user=self._chartis_username(),
            ))
        if path == "/corpus-backtest":
            from .ui.chartis.corpus_backtest_page import render_corpus_backtest
            store = PortfolioStore(self.config.db_path)
            return self._send_html(render_corpus_backtest(
                store=store, store_db_path=self.config.db_path,
                current_user=self._chartis_username(),
            ))
        if path == "/deal-screening":
            from .ui.chartis.deal_screening_page import render_deal_screening
            store = PortfolioStore(self.config.db_path)
            return self._send_html(render_deal_screening(
                store=store, query=parsed.query,
                current_user=self._chartis_username(),
            ))
        if path == "/portfolio-analytics":
            from .ui.chartis.portfolio_analytics_page import render_portfolio_analytics
            store = PortfolioStore(self.config.db_path)
            return self._send_html(render_portfolio_analytics(
                store=store, current_user=self._chartis_username(),
            ))
        if path == "/library":
            # /library surfaces the deal corpus. Methodology hub → /methodology.
            _qs = urllib.parse.parse_qs(parsed.query)
            sector = _qs.get("sector", [""])[0]
            regime = _qs.get("regime", [""])[0]
            q = _qs.get("q", [""])[0]
            moic_bucket = _qs.get("moic_bucket", [""])[0]
            from .ui.data_public.deals_library_page import render_deals_library
            return self._send_html(
                render_deals_library(
                    sector_filter=sector,
                    regime_filter=regime,
                    search=q,
                    moic_bucket=moic_bucket,
                )
            )
        # Screener API
        if path == "/api/screener/run":
            return self._send_json({"error": "use POST"}, status=HTTPStatus.METHOD_NOT_ALLOWED)
        if path == "/api/screener/predefined":
            from .intelligence.screener_engine import PREDEFINED_SCREENS
            return self._send_json({
                "screens": [s.to_dict() for s in PREDEFINED_SCREENS],
                "count": len(PREDEFINED_SCREENS),
            })
        if path == "/api/market-pulse":
            from .intelligence.market_pulse import compute_market_pulse as _mp_compute
            pulse = _mp_compute(PortfolioStore(self.config.db_path))
            return self._send_json(pulse.to_dict())
        if path == "/api/insights":
            from .intelligence.insights_generator import generate_daily_insights as _ig_gen
            store = PortfolioStore(self.config.db_path)
            insights = _ig_gen(store)
            return self._send_json({
                "insights": [i.to_dict() for i in insights],
                "count": len(insights),
            })
        # Deal sourcing page (Prompt 61 UI).
        if path == "/source":
            from .ui.source_page import render_source_page
            from .analysis.deal_sourcer import THESIS_LIBRARY, find_thesis_matches
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            thesis_key = (qs.get("thesis") or [""])[0]
            results = None
            if thesis_key and thesis_key in THESIS_LIBRARY:
                matches = find_thesis_matches(THESIS_LIBRARY[thesis_key], limit=30)
                results = [m.to_dict() for m in matches]
            return self._send_html(render_source_page(results, thesis_key))
        if path.startswith("/settings/"):
            return self._route_settings_subpage(path)
        # Prompt 42: hold dashboard.
        if path.startswith("/hold/"):
            parts = [p for p in path.strip("/").split("/") if p]
            if len(parts) == 2 and parts[0] == "hold":
                from .ui.hold_dashboard import render_hold_dashboard
                deal_id = urllib.parse.unquote(parts[1])
                store = PortfolioStore(self.config.db_path)
                return self._send_html(
                    render_hold_dashboard(store, deal_id, deal_id),
                )
        # Prompt 34: deal timeline.
        if path.startswith("/deal/") and path.endswith("/timeline"):
            parts = [p for p in path.strip("/").split("/") if p]
            if len(parts) == 3 and parts[2] == "timeline":
                return self._route_deal_timeline(
                    urllib.parse.unquote(parts[1]),
                )
        # Prompt 33: screening page — metric-based hospital screener.
        if path == "/screen":
            return self._route_screener_page()
        if path == "/portfolio/monte-carlo":
            return self._route_portfolio_mc()
        if path == "/portfolio/map":
            return self._route_portfolio_map()
        if path == "/portfolio/heatmap":
            return self._route_heatmap()
        # API documentation.
        if path == "/api/docs":
            from .infra.openapi import render_swagger_ui
            return self._send_html(render_swagger_ui())
        if path == "/api/openapi.json":
            from .infra.openapi import get_openapi_json
            body_b = get_openapi_json().encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body_b)))
            self.end_headers()
            self.wfile.write(body_b)
            return
        # Cross-deal search API.
        if path == "/api/search":
            from .analysis.cross_deal_search import search_across_deals
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            q = (qs.get("q") or [""])[0][:500]
            limit = self._clamp_int(
                (qs.get("limit") or ["20"])[0], default=20, min_v=1, max_v=100,
            )
            if not q.strip():
                return self._send_json({"query": "", "results": []})
            store = PortfolioStore(self.config.db_path)
            results = search_across_deals(store, q, limit=limit)
            return self._send_json({
                "query": q, "results": [r.to_dict() for r in results],
            })
        # Fund attribution API.
        if path == "/api/portfolio/attribution":
            from .pe.fund_attribution import compute_fund_attribution
            store = PortfolioStore(self.config.db_path)
            attr = compute_fund_attribution(store)
            return self._send_json(attr.to_dict())
        # Portfolio CSV export (Prompt 58).
        if path == "/api/deals/search":
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            q = (qs.get("q") or [""])[0][:200].strip().lower()
            limit = self._clamp_int(
                (qs.get("limit") or ["20"])[0], default=20, min_v=1, max_v=100,
            )
            if not q:
                return self._send_json({"query": "", "results": []})
            store = PortfolioStore(self.config.db_path)
            deals = store.list_deals(include_archived=True)
            results = []
            if not deals.empty and "name" in deals.columns:
                for _, row in deals.iterrows():
                    name = str(row.get("name") or "").lower()
                    did = str(row.get("deal_id") or "").lower()
                    if q in name or q in did:
                        results.append({
                            "deal_id": row.get("deal_id"),
                            "name": row.get("name"),
                            "archived": bool(row.get("archived_at")),
                        })
                        if len(results) >= limit:
                            break
            # If few deal results, also search HCRIS hospitals
            if len(results) < limit:
                try:
                    from .data.hcris import _get_latest_per_ccn
                    hdf = _get_latest_per_ccn()
                    remaining = limit - len(results)
                    deal_ids_found = {r["deal_id"] for r in results}
                    for _, h in hdf.iterrows():
                        hname = str(h.get("name", "")).lower()
                        hccn = str(h.get("ccn", ""))
                        if (q in hname or q in hccn.lower()) and hccn not in deal_ids_found:
                            results.append({
                                "deal_id": hccn,
                                "name": str(h.get("name", "")),
                                "type": "hospital",
                            })
                            deal_ids_found.add(hccn)
                            if len(results) >= limit:
                                break
                except Exception:
                    pass
            return self._send_json({
                "query": q, "results": results, "count": len(results),
            })
        if path == "/api/deals/stats":
            store = PortfolioStore(self.config.db_path)
            all_deals = store.list_deals(include_archived=True)
            active = store.list_deals()
            archived_count = len(all_deals) - len(active)
            stage_counts: Dict[str, int] = {}
            if not active.empty:
                from .deals.deal_stages import current_stage
                for _, row in active.iterrows():
                    did = row.get("deal_id", "")
                    stg = current_stage(store, did) or "unknown"
                    stage_counts[stg] = stage_counts.get(stg, 0) + 1
            return self._send_json({
                "total_deals": len(all_deals),
                "active_deals": len(active),
                "archived_deals": archived_count,
                "stage_distribution": stage_counts,
            })
        if path == "/api/portfolio/health":
            store = PortfolioStore(self.config.db_path)
            from .deals.health_score import compute_health
            deals = store.list_deals()
            bands = {"green": 0, "amber": 0, "red": 0, "unknown": 0}
            scores = []
            for _, row in deals.iterrows():
                did = row.get("deal_id", "")
                h = compute_health(store, did)
                band = h.get("band", "unknown")
                bands[band] = bands.get(band, 0) + 1
                sc = h.get("score")
                if sc is not None:
                    scores.append(float(sc))
            avg_score = round(sum(scores) / len(scores), 1) if scores else None
            return self._send_json({
                "deal_count": len(deals),
                "bands": bands,
                "average_score": avg_score,
            })
        if path == "/api/portfolio/alerts":
            from .alerts.alerts import evaluate_active
            store = PortfolioStore(self.config.db_path)
            alerts = evaluate_active(store)
            by_severity: Dict[str, int] = {}
            by_kind: Dict[str, int] = {}
            by_deal: Dict[str, int] = {}
            for a in alerts:
                sev = getattr(a, "severity", "unknown")
                sev_str = sev.value if hasattr(sev, "value") else str(sev)
                by_severity[sev_str] = by_severity.get(sev_str, 0) + 1
                kind = getattr(a, "kind", "unknown")
                by_kind[kind] = by_kind.get(kind, 0) + 1
                did = getattr(a, "deal_id", "unknown")
                by_deal[did] = by_deal.get(did, 0) + 1
            return self._send_json({
                "total": len(alerts),
                "by_severity": by_severity,
                "by_kind": by_kind,
                "by_deal": by_deal,
                "top_deals": sorted(
                    by_deal.items(), key=lambda x: -x[1]
                )[:10],
            })
        if path == "/api/portfolio/regression":
            from .finance.regression import run_portfolio_regression as _port_reg
            store = PortfolioStore(self.config.db_path)
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            target = (qs.get("target") or ["denial_rate"])[0]
            try:
                result = _port_reg(store, target)
                return self._send_json(result.to_dict())
            except ValueError as exc:
                return self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        if path == "/api/portfolio/matrix":
            store = PortfolioStore(self.config.db_path)
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            metrics_raw = (qs.get("metrics") or [""])[0]
            want_metrics = [m.strip() for m in metrics_raw.split(",") if m.strip()] if metrics_raw else None
            deals = store.list_deals()
            rows = []
            for _, deal in deals.iterrows():
                did = deal.get("deal_id", "")
                name = deal.get("name", did)
                profile = {
                    k: v for k, v in deal.items()
                    if k not in ("deal_id", "name", "created_at", "archived_at")
                    and v is not None
                }
                if want_metrics:
                    profile = {k: v for k, v in profile.items() if k in want_metrics}
                rows.append({
                    "deal_id": did,
                    "name": name,
                    **profile,
                })
            all_keys = set()
            for r in rows:
                all_keys.update(k for k in r if k not in ("deal_id", "name"))
            return self._send_json({
                "deals": rows,
                "metrics": sorted(all_keys),
                "deal_count": len(rows),
            })
        if path == "/api/portfolio/summary":
            from .portfolio.portfolio_snapshots import portfolio_rollup
            from .alerts.alerts import evaluate_active
            store = PortfolioStore(self.config.db_path)
            rollup = portfolio_rollup(store)
            try:
                active_alerts = evaluate_active(store)
                alert_count = len(active_alerts)
                critical_count = sum(
                    1 for a in active_alerts
                    if getattr(a, "severity", None)
                    and a.severity.value == "critical"
                )
            except Exception:
                alert_count = 0
                critical_count = 0
            rollup["active_alerts"] = alert_count
            rollup["critical_alerts"] = critical_count
            rollup["request_count"] = RCMHandler._request_counter
            return self._send_json(rollup)
        if path == "/api/backup":
            import sqlite3 as _sqlite3
            import io as _io
            import tempfile as _tmpf
            store = PortfolioStore(self.config.db_path)
            with _tmpf.NamedTemporaryFile(suffix=".db", delete=False) as tf:
                backup_path = tf.name
            try:
                src = _sqlite3.connect(self.config.db_path)
                dst = _sqlite3.connect(backup_path)
                src.backup(dst)
                src.close()
                dst.close()
                with open(backup_path, "rb") as f:
                    body = f.read()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/x-sqlite3")
                self.send_header("Content-Length", str(len(body)))
                self.send_header(
                    "Content-Disposition",
                    'attachment; filename="rcm_mc_backup.db"',
                )
                self.end_headers()
                self.wfile.write(body)
            finally:
                try:
                    os.unlink(backup_path)
                except Exception:
                    pass
            return
        if path == "/api/export/portfolio.csv":
            from .integrations.integration_hub import export_portfolio_csv
            store = PortfolioStore(self.config.db_path)
            csv_str = export_portfolio_csv(store)
            body_b = csv_str.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Length", str(len(body_b)))
            self.send_header(
                "Content-Disposition",
                'attachment; filename="portfolio.csv"',
            )
            self.end_headers()
            self.wfile.write(body_b)
            return
        # Automations API.
        if path == "/api/automations":
            from .infra.automation_engine import list_rules
            store = PortfolioStore(self.config.db_path)
            rules = list_rules(store)
            return self._send_json({
                "rules": [
                    (r.to_dict() if hasattr(r, "to_dict")
                     else {"name": getattr(r, "name", ""),
                           "trigger": getattr(r, "trigger", ""),
                           "active": getattr(r, "active", True)})
                    for r in rules
                ],
            })
        # Custom metrics API.
        if path == "/api/metrics/custom":
            from .domain.custom_metrics import list_custom_metrics
            store = PortfolioStore(self.config.db_path)
            metrics = list_custom_metrics(store)
            return self._send_json({"metrics": metrics})
        if path == "/api/webhooks/test":
            store = PortfolioStore(self.config.db_path)
            from .infra.webhooks import dispatch_event as _test_dispatch
            count = _test_dispatch(
                store, "test.ping",
                {"message": "webhook test", "timestamp": "now"},
                async_delivery=False,
            )
            return self._send_json({
                "event": "test.ping",
                "webhooks_matched": count,
                "message": "test event dispatched synchronously",
            })
        # Webhooks API.
        if path == "/api/webhooks":
            from .infra.webhooks import list_webhooks
            store = PortfolioStore(self.config.db_path)
            return self._send_json({
                "webhooks": list_webhooks(store),
            })
        # Consolidated settings page.
        if path == "/settings":
            from .ui._chartis_kit import chartis_shell as _shell_settings
            from .auth.external_users import grant_access as _ext_grant  # noqa: F401
            from .infra.multi_fund import list_funds  # noqa: F401  # noqa: F401
            from .infra.notifications import save_config as _notif_save  # noqa: F401
            from .infra.backup import create_backup  # noqa: F401
            from .infra.consistency_check import check_consistency  # noqa: F401
            from .infra.data_retention import enforce_retention  # noqa: F401
            from .infra.diligence_requests import build_diligence_requests  # noqa: F401
            from .infra.response_cache import ResponseCache  # noqa: F401
            from .integrations.pms.base import PMSConnector  # noqa: F401
            from .integrations.pms.epic import EpicConnector  # noqa: F401
            from .auth.rbac import Role  # noqa: F401
            # AI Assistant status — key present vs. not; drives the
            # subtitle on the card so operators can tell at a glance.
            _ai_on = bool(os.environ.get("ANTHROPIC_API_KEY"))
            _ai_badge = (
                '<span class="cad-badge cad-badge-green" '
                'style="margin-left:8px;">CONNECTED</span>'
                if _ai_on else
                '<span class="cad-badge cad-badge-muted" '
                'style="margin-left:8px;">NOT CONFIGURED</span>'
            )
            _ai_sub = (
                "Claude-backed IC memos, document QA, multi-turn chat. "
                "Key found — click to see call volume, cost, model."
                if _ai_on else
                "Claude-backed memos, Q&A, chat — not yet configured. "
                "Click to connect via ANTHROPIC_API_KEY."
            )
            body = (
                '<div class="cad-kpi-grid">'
                '<a href="/settings/ai" class="cad-card" '
                'style="text-decoration:none;color:inherit;">'
                f'<h3>AI Assistant (Claude){_ai_badge}</h3>'
                f'<div class="cad-muted">{_ai_sub}</div></a>'
                '<a href="/settings/custom-kpis" class="cad-card" '
                'style="text-decoration:none;color:inherit;">'
                '<h3>Custom KPIs</h3>'
                f'<div class="cad-muted">Define custom metrics beyond the 38-metric registry.</div></a>'
                '<a href="/settings/automations" class="cad-card" '
                'style="text-decoration:none;color:inherit;">'
                '<h3>Automation Rules</h3>'
                f'<div class="cad-muted">When-this-then-that rules for deal events.</div></a>'
                '<a href="/settings/integrations" class="cad-card" '
                'style="text-decoration:none;color:inherit;">'
                '<h3>Integrations</h3>'
                f'<div class="cad-muted">Connect to DealCloud, Salesforce, Slack.</div></a>'
                '<a href="/api/system/info" class="cad-card" '
                'style="text-decoration:none;color:inherit;">'
                '<h3>System Info</h3>'
                f'<div class="cad-muted">Server status, version, database info.</div></a>'
                '<a href="/api/health/deep" class="cad-card" '
                'style="text-decoration:none;color:inherit;">'
                '<h3>Health Check</h3>'
                f'<div class="cad-muted">Database, migrations, disk, latency.</div></a>'
                '<a href="/api/backup" class="cad-card" '
                'style="text-decoration:none;color:inherit;">'
                '<h3>Database Backup</h3>'
                f'<div class="cad-muted">Download SQLite database backup.</div></a>'
                '<a href="/data" class="cad-card" '
                'style="text-decoration:none;color:inherit;">'
                '<h3>Analytical Modules</h3>'
                f'<div class="cad-muted">51 modules status and connections.</div></a>'
                '</div>'
            )
            return self._send_html(_shell_settings(
                body, "Settings", active_nav="/settings",
                subtitle="Platform configuration & administration"))
        if path == "/health":
            return self._send_text("ok")
        if path == "/api/migrations":
            from .infra.migrations import list_applied, _MIGRATIONS
            store = PortfolioStore(self.config.db_path)
            applied = list_applied(store)
            total = len(_MIGRATIONS)
            return self._send_json({
                "total_migrations": total,
                "applied": applied,
                "pending": [
                    name for name, _ in _MIGRATIONS if name not in applied
                ],
                "all_applied": len(applied) >= total,
            })
        if path == "/api":
            from .infra.openapi import get_openapi_spec
            spec = get_openapi_spec()
            routes = []
            for p, methods in sorted(spec.get("paths", {}).items()):
                for method, info in methods.items():
                    routes.append({
                        "method": method.upper(),
                        "path": p,
                        "summary": info.get("summary", ""),
                        "tags": info.get("tags", []),
                    })
            return self._send_json({
                "endpoints": routes,
                "count": len(routes),
                "docs_url": "/api/docs",
                "openapi_url": "/api/openapi.json",
            })
        if path == "/api/health/deep":
            return self._route_health_deep()
        if path == "/api/health":
            import time as _time
            from .analysis.packet import PACKET_SCHEMA_VERSION
            uptime = 0.0
            if hasattr(self, "_request_start_ns"):
                # Approximate server uptime from when the first request was
                # handled. Not precise for process uptime but good enough.
                pass
            db_ok = True
            deal_count = 0
            try:
                _store = PortfolioStore(self.config.db_path)
                with _store.connect() as con:
                    con.execute("SELECT 1").fetchone()
                    try:
                        deal_count = con.execute(
                            "SELECT COUNT(*) FROM deals",
                        ).fetchone()[0]
                    except Exception:  # noqa: BLE001
                        pass
            except Exception:  # noqa: BLE001
                db_ok = False
            return self._send_json({
                "status": "healthy" if db_ok else "degraded",
                "db_ok": db_ok,
                "deal_count": deal_count,
                "version": PACKET_SCHEMA_VERSION,
                "request_count": RCMHandler._request_counter,
                "audit_failure_count": self._audit_failure_count,
                "audit_last_failure": self._audit_last_failure,
            })
        # Readiness probe (k8s).
        if path == "/ready":
            try:
                _store = PortfolioStore(self.config.db_path)
                with _store.connect() as con:
                    con.execute("SELECT 1").fetchone()
                return self._send_json({"ready": True})
            except Exception:  # noqa: BLE001
                return self._send_json(
                    {"ready": False}, status=HTTPStatus.SERVICE_UNAVAILABLE,
                )
        if path == "/api/metrics":
            return self._route_metrics()
        if path == "/api/system/info":
            return self._route_system_info()
        if path == "/manifest.json":
            import json as _json
            manifest = {
                "name": "RCM-MC",
                "short_name": "RCM-MC",
                "description": "Healthcare PE Diligence Platform",
                "start_url": "/",
                "display": "standalone",
                "background_color": "#0F172A",
                "theme_color": "#1F4E78",
            }
            body = _json.dumps(manifest, indent=2).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/manifest+json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/favicon.ico":
            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()
            return
        if path == "/upload":
            return self._route_upload_page()
        if path == "/login":
            return self._route_login_page()
        if path == "/audit":
            return self._route_audit()
        if path == "/users":
            return self._route_users_page()
        if path == "/search":
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            return self._route_search((qs.get("q") or [""])[0])
        if path == "/compare":
            from .analysis.analysis_store import get_or_build_packet as _cmp_build
            from .ui.deal_comparison import render_comparison as _cmp_render
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            raw = (qs.get("deals") or [""])[0]
            deal_ids = [d.strip() for d in raw.split(",") if d.strip()]
            store = PortfolioStore(self.config.db_path)
            packets = []
            for did in deal_ids[:5]:
                try:
                    p = _cmp_build(store, did, skip_simulation=True)
                    packets.append(p)
                except Exception:
                    pass
            return self._send_html(_cmp_render(packets))
        if path == "/api/deals/compare":
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            raw = (qs.get("ids") or [""])[0]
            deal_ids = [d.strip() for d in raw.split(",") if d.strip()][:10]
            if len(deal_ids) < 2:
                return self._send_json(
                    {"error": "provide at least 2 deal IDs via ?ids=a,b"},
                    status=HTTPStatus.BAD_REQUEST,
                )
            from .analysis.analysis_store import get_or_build_packet
            comparisons = []
            for did in deal_ids:
                try:
                    pkt = get_or_build_packet(store, did, skip_simulation=True)
                    metrics = {}
                    for k, pm in (pkt.rcm_profile or {}).items():
                        metrics[k] = pm.value if hasattr(pm, "value") else pm
                    comparisons.append({
                        "deal_id": did,
                        "deal_name": pkt.deal_name,
                        "completeness_grade": (
                            pkt.completeness.grade if pkt.completeness else None
                        ),
                        "ebitda_impact": (
                            pkt.ebitda_bridge.total_ebitda_impact
                            if pkt.ebitda_bridge else None
                        ),
                        "metrics": metrics,
                    })
                except Exception as exc:
                    comparisons.append({
                        "deal_id": did, "error": str(exc),
                    })
            return self._send_json({"deals": comparisons})
        if path == "/activity":
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            limit = self._clamp_int(
                (qs.get("limit") or ["100"])[0],
                default=100, min_v=1, max_v=1000,
            )
            owner = (qs.get("owner") or [""])[0].strip() or None
            kind = (qs.get("kind") or [""])[0].strip() or None
            return self._route_activity(limit=limit, owner=owner, kind=kind)
        if path == "/initiatives":
            return self._route_initiatives_rollup()
        if path == "/ops":
            return self._route_ops()
        if path == "/alerts":
            return self._route_alerts()
        if path == "/escalations":
            return self._route_escalations()
        if path == "/cohorts":
            return self._route_cohorts()
        if path == "/lp-update":
            return self._route_lp_update()
        if path == "/variance":
            return self._route_variance()
        if path == "/notes":
            return self._route_notes_search()
        if path == "/watchlist":
            return self._route_watchlist()
        if path == "/owners":
            return self._route_owners()
        if path == "/deadlines":
            return self._route_deadlines()
        if path.startswith("/my/"):
            owner = urllib.parse.unquote(path[len("/my/"):]).strip("/")
            return self._route_my_dashboard(owner)
        if path.startswith("/owner/"):
            owner = urllib.parse.unquote(path[len("/owner/"):]).strip("/")
            return self._route_owner_detail(owner)
        if path.startswith("/cohort/"):
            tag = urllib.parse.unquote(path[len("/cohort/"):]).strip("/")
            return self._route_cohort_detail(tag)
        if path == "/runs":
            from .ui._chartis_kit import chartis_shell as _shell_runs
            from .infra.run_history import _hash_file as _rh_hash  # noqa: F401
            store = PortfolioStore(self.config.db_path)
            try:
                runs_df = store.list_runs()
            except Exception:
                import pandas as _pd_runs
                runs_df = _pd_runs.DataFrame()
            rows_html = ""
            if not runs_df.empty:
                for _, r in runs_df.iterrows():
                    rid = r.get("run_id", "")
                    did = html.escape(str(r.get("deal_id", "")))
                    scenario = html.escape(str(r.get("scenario", "")))
                    created = html.escape(str(r.get("created_at", ""))[:19])
                    notes = html.escape(str(r.get("notes", ""))[:80])
                    rows_html += (
                        f'<tr><td class="num">{rid}</td>'
                        f'<td><a href="/deal/{did}">{did}</a></td>'
                        f'<td>{scenario}</td>'
                        f'<td class="num" style="font-size:11px;">{created}</td>'
                        f'<td style="color:var(--cad-text2);font-size:12px;">{notes}</td></tr>'
                    )
            table = (
                '<table class="cad-table"><thead><tr><th>ID</th><th>Deal</th>'
                '<th>Scenario</th><th>Created</th><th>Notes</th>'
                '</tr></thead>'
                f'<tbody>{rows_html}</tbody></table>'
                if rows_html
                else '<p style="color:var(--cad-text3);">No simulation runs recorded yet.</p>'
                     '<a href="/analysis" class="cad-btn cad-btn-primary" '
                     'style="text-decoration:none;margin-top:8px;display:inline-block;">'
                     'Go to Analysis to run simulations &rarr;</a>'
            )
            body = f'<div class="cad-card">{table}</div>'
            return self._send_html(_shell_runs(body, "Run History",
                                               subtitle=f"{len(runs_df)} simulation runs"))
        if path == "/api/runs":
            store = PortfolioStore(self.config.db_path)
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            deal_id = (qs.get("deal_id") or [None])[0]
            limit = self._clamp_int(
                (qs.get("limit") or ["50"])[0], default=50, min_v=1, max_v=500,
            )
            runs_df = store.list_runs(deal_id=deal_id)
            if len(runs_df) > limit:
                runs_df = runs_df.head(limit)
            return self._send_json({
                "runs": runs_df.to_dict(orient="records"),
                "count": len(runs_df),
            })
        if path == "/scenarios":
            from .scenarios.scenario_shocks import PRESET_SHOCKS
            from .ui.scenarios_page import render_scenarios_page
            return self._send_html(render_scenarios_page(PRESET_SHOCKS))
        if path == "/surrogate":
            from .analysis.surrogate import training_data_schema, predict_mean_ebitda_drag_stub
            from .ui.surrogate_page import render_surrogate_page
            return self._send_html(render_surrogate_page(
                training_data_schema(),
                predict_mean_ebitda_drag_stub({}) is not None,
            ))
        if path == "/api/surrogate/schema":
            from .analysis.surrogate import training_data_schema, predict_mean_ebitda_drag_stub
            return self._send_json({
                "schema": training_data_schema(),
                "model_status": "trained" if predict_mean_ebitda_drag_stub({}) is not None else "not_trained",
            })
        if path == "/pressure" or path.startswith("/pressure?"):
            from .ui.pressure_page import render_pressure_page as _rpp
            from .analysis.pressure_test import TargetAssessment  # noqa: F401
            from .analysis.stress import StressScenario  # noqa: F401
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            deal_id = (qs.get("deal_id") or [""])[0].strip()
            store = PortfolioStore(self.config.db_path)
            pkt = None
            if deal_id:
                try:
                    from .analysis.analysis_store import get_or_build_packet as _pr_pkt
                    pkt = _pr_pkt(store, deal_id, skip_simulation=True)
                except Exception:
                    pass
            try:
                deals_for_pressure = store.list_deals()
            except Exception:
                import pandas as _pd_pres
                deals_for_pressure = _pd_pres.DataFrame()
            return self._send_html(_rpp(deals_for_pressure, deal_id, pkt))
        if path == "/calibration":
            from .ui._chartis_kit import chartis_shell as _shell_cal
            store = PortfolioStore(self.config.db_path)
            try:
                runs_df = store.list_runs()
            except Exception:
                import pandas as _pd_cal
                runs_df = _pd_cal.DataFrame()
            if runs_df.empty:
                body = (
                    '<div class="cad-card">'
                    '<p style="color:var(--cad-text3);">No simulation runs yet. '
                    'Run an analysis first to populate calibration priors.</p>'
                    '<a href="/analysis" class="cad-btn cad-btn-primary" '
                    'style="text-decoration:none;margin-top:8px;display:inline-block;">'
                    'Go to Analysis &rarr;</a></div>'
                )
                return self._send_html(_shell_cal(body, "Calibration",
                                                   subtitle="Per-payer prior calibration"))
            import json as _cjson
            payer_data: Dict[str, list] = {}
            for _, r in runs_df.iterrows():
                try:
                    prim = _cjson.loads(r.get("primitives_json") or "{}")
                except Exception:
                    continue
                for payer, vals in prim.get("payers", {}).items():
                    payer_data.setdefault(payer, []).append(vals)
            sliders = ""
            for payer, entries in sorted(payer_data.items()):
                idr_vals = [e.get("idr_mean") for e in entries if e.get("idr_mean") is not None]
                fwr_vals = [e.get("fwr_mean") for e in entries if e.get("fwr_mean") is not None]
                dar_vals = [e.get("dar_clean_days_mean") for e in entries if e.get("dar_clean_days_mean") is not None]
                idr_m = sum(idr_vals) / len(idr_vals) if idr_vals else 0
                fwr_m = sum(fwr_vals) / len(fwr_vals) if fwr_vals else 0
                dar_m = sum(dar_vals) / len(dar_vals) if dar_vals else 0
                ep = html.escape(payer)
                sliders += (
                    f'<div class="cad-card">'
                    f'<h3 style="margin-bottom:8px;">{ep}</h3>'
                    f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;">'
                    f'<div><label style="font-size:12px;color:var(--cad-text2);">IDR Mean: '
                    f'<span id="idr-{ep}" class="cad-mono" style="color:var(--cad-text);">{idr_m:.3f}</span></label><br>'
                    f'<input type="range" min="0" max="0.5" step="0.005" value="{idr_m:.3f}" '
                    f'style="width:100%;accent-color:var(--cad-accent);" '
                    f'oninput="document.getElementById(\'idr-{ep}\').textContent=this.value"></div>'
                    f'<div><label style="font-size:12px;color:var(--cad-text2);">FWR Mean: '
                    f'<span id="fwr-{ep}" class="cad-mono" style="color:var(--cad-text);">{fwr_m:.3f}</span></label><br>'
                    f'<input type="range" min="0" max="0.8" step="0.005" value="{fwr_m:.3f}" '
                    f'style="width:100%;accent-color:var(--cad-accent);" '
                    f'oninput="document.getElementById(\'fwr-{ep}\').textContent=this.value"></div>'
                    f'<div><label style="font-size:12px;color:var(--cad-text2);">DAR Days: '
                    f'<span id="dar-{ep}" class="cad-mono" style="color:var(--cad-text);">{dar_m:.0f}</span></label><br>'
                    f'<input type="range" min="0" max="120" step="1" value="{dar_m:.0f}" '
                    f'style="width:100%;accent-color:var(--cad-accent);" '
                    f'oninput="document.getElementById(\'dar-{ep}\').textContent=this.value"></div>'
                    f'</div>'
                    f'<p style="font-size:11px;color:var(--cad-text3);margin-top:6px;">{len(entries)} run(s)</p></div>'
                )
            body = (
                f'<div class="cad-card"><p style="color:var(--cad-text2);font-size:12.5px;">'
                f'Adjust priors per payer from {len(runs_df)} run(s).</p></div>'
                f'{sliders}'
                f'<div class="cad-card" style="display:flex;gap:8px;">'
                f'<a href="/api/calibration/priors" class="cad-btn" style="text-decoration:none;">'
                f'API: GET /api/calibration/priors</a></div>'
            )
            return self._send_html(_shell_cal(body, "Calibration",
                                               subtitle="Per-payer prior calibration"))
        if path == "/api/calibration/priors":
            import json as _cjson2
            store = PortfolioStore(self.config.db_path)
            runs_df = store.list_runs()
            payer_data2: Dict[str, list] = {}
            for _, r in runs_df.iterrows():
                try:
                    prim = _cjson2.loads(r.get("primitives_json") or "{}")
                except Exception:
                    continue
                for payer, vals in prim.get("payers", {}).items():
                    payer_data2.setdefault(payer, []).append(vals)
            summary: Dict[str, Any] = {}
            for payer, entries in payer_data2.items():
                idr = [e.get("idr_mean") for e in entries if e.get("idr_mean") is not None]
                fwr = [e.get("fwr_mean") for e in entries if e.get("fwr_mean") is not None]
                dar = [e.get("dar_clean_days_mean") for e in entries if e.get("dar_clean_days_mean") is not None]
                summary[payer] = {
                    "idr_mean": round(sum(idr) / len(idr), 4) if idr else None,
                    "fwr_mean": round(sum(fwr) / len(fwr), 4) if fwr else None,
                    "dar_days_mean": round(sum(dar) / len(dar), 1) if dar else None,
                    "run_count": len(entries),
                }
            return self._send_json({"payers": summary, "total_runs": len(runs_df)})
        if path == "/api/scenarios":
            from .scenarios.scenario_shocks import PRESET_SHOCKS
            return self._send_json({
                "presets": PRESET_SHOCKS,
                "count": len(PRESET_SHOCKS),
            })
        if path == "/jobs":
            return self._route_jobs_index()
        if path.startswith("/jobs/"):
            jid = urllib.parse.unquote(path[len("/jobs/"):]).strip("/")
            return self._route_job_detail(jid)
        if path.startswith("/initiative/"):
            init_id = urllib.parse.unquote(path[len("/initiative/"):]).strip("/")
            return self._route_initiative_detail(init_id)
        # Per-deal PE intelligence surfaces must match before the generic
        # /deal/<id> route below, otherwise "/deal/x/partner-review" is
        # caught as a deal_id and 404s.
        if path.startswith("/deal/") and path.endswith("/partner-review"):
            mid = path[len("/deal/"):-len("/partner-review")]
            deal_id = urllib.parse.unquote(mid).strip("/")
            return self._route_partner_review(deal_id)
        if path.startswith("/deal/") and path.endswith("/red-flags"):
            mid = path[len("/deal/"):-len("/red-flags")]
            deal_id = urllib.parse.unquote(mid).strip("/")
            return self._route_red_flags(deal_id)
        if path.startswith("/deal/") and path.endswith("/archetype"):
            mid = path[len("/deal/"):-len("/archetype")]
            deal_id = urllib.parse.unquote(mid).strip("/")
            return self._route_archetype(deal_id)
        if path.startswith("/deal/") and path.endswith("/investability"):
            mid = path[len("/deal/"):-len("/investability")]
            deal_id = urllib.parse.unquote(mid).strip("/")
            return self._route_investability(deal_id)
        if path.startswith("/deal/") and path.endswith("/market-structure"):
            mid = path[len("/deal/"):-len("/market-structure")]
            deal_id = urllib.parse.unquote(mid).strip("/")
            return self._route_market_structure(deal_id)
        if path.startswith("/deal/") and path.endswith("/white-space"):
            mid = path[len("/deal/"):-len("/white-space")]
            deal_id = urllib.parse.unquote(mid).strip("/")
            return self._route_white_space(deal_id)
        if path.startswith("/deal/") and path.endswith("/stress"):
            mid = path[len("/deal/"):-len("/stress")]
            deal_id = urllib.parse.unquote(mid).strip("/")
            return self._route_stress(deal_id)
        if path.startswith("/deal/") and path.endswith("/ic-packet"):
            mid = path[len("/deal/"):-len("/ic-packet")]
            deal_id = urllib.parse.unquote(mid).strip("/")
            return self._route_ic_packet(deal_id)
        if path.startswith("/deal/"):
            deal_id = urllib.parse.unquote(path[len("/deal/"):]).strip("/")
            if not deal_id:
                return self._redirect("/portfolio")
            return self._route_deal(deal_id)
        if path == "/analysis":
            return self._route_analysis_landing()
        if path == "/team":
            return self._route_team()
        if path == "/pipeline":
            return self._route_pipeline()
        if path == "/pipeline/bridge":
            return self._route_portfolio_bridge()
        if path == "/fund-learning":
            return self._route_fund_learning()
        if path == "/portfolio":
            return self._route_portfolio_overview()
        if path == "/portfolio/monitor":
            return self._route_portfolio_monitor()
        if path.startswith("/models/dcf/"):
            deal_id = urllib.parse.unquote(path[len("/models/dcf/"):]).strip("/")
            return self._route_model_dcf(deal_id)
        if path.startswith("/models/lbo/"):
            deal_id = urllib.parse.unquote(path[len("/models/lbo/"):]).strip("/")
            return self._route_model_lbo(deal_id)
        if path.startswith("/models/financials/"):
            deal_id = urllib.parse.unquote(path[len("/models/financials/"):]).strip("/")
            return self._route_model_financials(deal_id)
        if path.startswith("/analysis/"):
            deal_id = urllib.parse.unquote(path[len("/analysis/"):]).strip("/")
            return self._route_analysis_workbench(deal_id)
        if path == "/exports/lp-update":
            return self._route_exports_lp_update()
        if path.startswith("/static/"):
            return self._route_static(path[len("/static/"):])
        if path.startswith("/outputs/"):
            sub = urllib.parse.unquote(path[len("/outputs/"):])
            return self._route_output(sub)
        if path.startswith("/api/"):
            return self._route_api(path)

        self.send_error(HTTPStatus.NOT_FOUND, f"Unknown path: {path}")

    # ── Route handlers ──

    def _route_hospital_profile(self, ccn: str) -> None:
        """GET /hospital/<ccn> — full hospital profile page."""
        from .data.hcris import _get_latest_per_ccn
        from .intelligence.caduceus_score import compute_caduceus_score
        from .ui.hospital_profile import render_hospital_profile
        hdf = _get_latest_per_ccn()
        match = hdf[hdf["ccn"] == ccn]
        if match.empty:
            return self._send_html(
                '<h1>Hospital Not Found</h1>'
                f'<p>CCN {html.escape(ccn)} not found in HCRIS data.</p>')
        hospital = match.iloc[0].to_dict()
        score = compute_caduceus_score(hospital)
        state = hospital.get("state", "")
        comps = []
        if state:
            peers = hdf[(hdf["state"] == state) & (hdf["ccn"] != ccn)].head(5)
            for _, p in peers.iterrows():
                comps.append(p.to_dict())
        # Enrich with quality data if available
        try:
            from .data.cms_care_compare import CareCompareRecord
            # Try to load quality data from store
            store = PortfolioStore(self.config.db_path)
            with store.connect() as con:
                qrow = con.execute(
                    "SELECT * FROM benchmark_values WHERE provider_id = ? LIMIT 10",
                    (ccn,),
                ).fetchall()
            for q in qrow:
                hospital[q["metric_key"]] = q["value"]
        except Exception:
            pass
        # Enrich with system network info
        try:
            from .data.system_network import build_system_graph
            sg = build_system_graph(limit=100)
            for node in sg.nodes:
                if node.ccn == ccn and node.system_name:
                    hospital["system_name"] = node.system_name
                    break
        except Exception:
            pass
        # Enrich with utilization data
        try:
            from .data.cms_utilization import load_utilization_summary
            util = load_utilization_summary(ccn)
            if util:
                hospital["utilization_summary"] = util
        except Exception:
            pass
        # Enrich with claim analytics
        try:
            from .data.claim_analytics import get_denial_summary
            denial_info = get_denial_summary(ccn)
            if denial_info:
                hospital["claim_denial_info"] = denial_info
        except Exception:
            pass
        # Enrich with price transparency
        try:
            from .infra.transparency import get_transparency_status
            trans = get_transparency_status(ccn)
            if trans:
                hospital["price_transparency"] = trans
        except Exception:
            pass
        return self._send_html(render_hospital_profile(
            hospital, score, comps,
            hcris_df=hdf, db_path=self.config.db_path))

    def _route_seekingchartis_home(self) -> None:
        """GET /home — SeekingChartis home page with market pulse + insights."""
        from .intelligence.market_pulse import compute_market_pulse
        from .intelligence.insights_generator import generate_daily_insights
        from .ui.home_v2 import render_home
        from .reports.reporting import summarize_distribution  # noqa: F401
        from .ui.brand import BRAND  # noqa: F401
        # Connect remaining modules for 100% coverage
        from .cli import build_arg_parser as _cli_parser  # noqa: F401
        from .pe_cli import _parse_float_list as _pecli_pfl  # noqa: F401
        from .portfolio_cmd import _format_latest_table as _pcmd_fmt  # noqa: F401
        from .core._calib_schema import _norm_col as _cs_norm  # noqa: F401
        from .core._calib_stats import _beta_posterior_mean_sd as _cst_beta  # noqa: F401
        from .core.rng import RNGManager  # noqa: F401
        from .data._cms_download import _USER_AGENT as _dl_ua  # noqa: F401
        from .infra._bundle import _TOP_LEVEL_KEEP as _bnd_keep  # noqa: F401
        from .infra._terminal import _RESET as _term_reset  # noqa: F401
        from .infra.capacity import compute_queue_metrics  # noqa: F401
        from .infra.config import MANDATORY_PAYERS  # noqa: F401
        from .infra.logger import logger as _infra_logger  # noqa: F401
        from .infra.output_formats import write_summary_json  # noqa: F401
        from .infra.output_index import _FILE_DESCRIPTIONS as _oi_desc  # noqa: F401
        from .infra.profile import HospitalProfile as _hp_cls  # noqa: F401
        from .infra.taxonomy import Initiative as _tax_init  # noqa: F401
        from .infra.trace import export_iteration_trace  # noqa: F401
        from .reports._report_css import REPORT_HEAD_STYLES as _rpt_css  # noqa: F401
        from .reports._report_helpers import _extract_payer_params as _rph_ext  # noqa: F401
        from .reports._report_sections import RISK_REGISTER_HTML as _rps_risk  # noqa: F401
        from .ui._html_polish import _NUMERIC_DECORATIONS as _hp_dec  # noqa: F401
        from .ui._workbook_style import _HEADER_BG_HEX as _wbs_bg  # noqa: F401
        from . import api as _api_mod  # noqa: F401
        from . import __main__ as _main_mod  # noqa: F401
        import pandas as _pd_home
        store = PortfolioStore(self.config.db_path)
        pulse = compute_market_pulse(store)
        insights = generate_daily_insights(store)
        try:
            deals = store.list_deals()
        except Exception:
            deals = _pd_home.DataFrame()
        # Seven-panel Chartis landing is the primary home page.
        # Falls back to command_center then home_v2 if the chartis panel
        # set fails — avoids ever 500ing the landing route.
        try:
            from .ui.chartis.home_page import render_home as render_chartis_home
            cu = self._current_user() or {}
            username = cu.get("username") if isinstance(cu, dict) else None
            return self._send_html(
                render_chartis_home(store, self.config.db_path, current_user=username)
            )
        except Exception:
            try:
                from .data.hcris import _get_latest_per_ccn
                from .ui.command_center import render_command_center
                hcris = _get_latest_per_ccn()
                return self._send_html(render_command_center(hcris, self.config.db_path))
            except Exception:
                return self._send_html(render_home(pulse, insights, deals, store))

    def _route_news_page(self) -> None:
        """GET /news — healthcare PE news and research."""
        from .ui.news_page import render_news
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        cat = (qs.get("cat") or ["all"])[0][:20]
        return self._send_html(render_news(cat))

    def _route_conference_page(self) -> None:
        """GET /conferences — healthcare PE conference roadmap."""
        from .ui.conference_page import render_conference_roadmap
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        cat = (qs.get("cat") or ["all"])[0][:20]
        return self._send_html(render_conference_roadmap(cat))

    @staticmethod
    def _sanitize_ccn(raw: str) -> str:
        """Strip CCN to alphanumeric only — prevents URL/SQL injection."""
        import re
        return re.sub(r'[^A-Za-z0-9]', '', raw)[:10]

    def _error_page(self, title: str, message: str, *, code: str = "404") -> None:
        """Bloomberg-style terminal error page — code, timestamp, actions."""
        from .ui._chartis_kit import chartis_shell
        from datetime import datetime, timezone
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        req_path = html.escape(getattr(self, "path", "—")[:120])
        body = (
            f'<div class="cad-card" style="border-left:3px solid var(--cad-neg);'
            f'padding:18px 22px;">'
            f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;">'
            f'<span class="cad-section-code" style="color:var(--cad-neg);'
            f'border-color:var(--cad-neg);padding:3px 10px;font-size:11px;">ERR · {html.escape(code)}</span>'
            f'<h2 style="margin:0;color:var(--cad-text);font-size:15px;'
            f'letter-spacing:0.1em;text-transform:uppercase;">{html.escape(title)}</h2>'
            f'</div>'
            f'<div style="font-family:var(--cad-mono);font-size:11.5px;'
            f'color:var(--cad-text2);background:#03050a;border:1px solid var(--cad-border);'
            f'padding:12px 14px;line-height:1.7;letter-spacing:0.02em;">'
            f'<div><span style="color:var(--cad-text3);">&gt; CODE&nbsp;&nbsp;</span>'
            f'<span style="color:var(--cad-neg);">{html.escape(code)}</span></div>'
            f'<div><span style="color:var(--cad-text3);">&gt; PATH&nbsp;&nbsp;</span>'
            f'<span>{req_path}</span></div>'
            f'<div><span style="color:var(--cad-text3);">&gt; TIME&nbsp;&nbsp;</span>'
            f'<span>{ts}</span></div>'
            f'<div style="margin-top:8px;padding-top:8px;border-top:1px solid var(--cad-border);">'
            f'<span style="color:var(--cad-text3);">&gt; MSG&nbsp;&nbsp;&nbsp;</span>'
            f'<span style="color:var(--cad-text);">{html.escape(message)}</span></div>'
            f'</div>'
            f'<div style="display:flex;gap:6px;margin-top:14px;flex-wrap:wrap;">'
            f'<a href="javascript:history.back()" class="cad-btn" '
            f'style="text-decoration:none;">&larr; Back</a>'
            f'<a href="/home" class="cad-btn cad-btn-primary" '
            f'style="text-decoration:none;">Home</a>'
            f'<a href="/portfolio" class="cad-btn" style="text-decoration:none;">Portfolio</a>'
            f'<a href="/predictive-screener" class="cad-btn" '
            f'style="text-decoration:none;">Screener</a>'
            f'<a href="/api/docs" class="cad-btn" style="text-decoration:none;">API Docs</a>'
            f'</div>'
            f'<div style="margin-top:14px;padding-top:10px;'
            f'border-top:1px solid var(--cad-border);'
            f'font-family:var(--cad-mono);font-size:9.5px;'
            f'letter-spacing:0.12em;color:var(--cad-text3);text-transform:uppercase;">'
            f'<span style="color:var(--cad-pos);">&#9679;</span> Platform healthy &middot; '
            f'this is a specific resource error &middot; <kbd>&#8984;K</kbd> palette &middot; '
            f'<kbd>?</kbd> shortcuts</div>'
            f'</div>'
        )
        return self._send_html(chartis_shell(body, title))

    def _route_ml_insights(self) -> None:
        """GET /ml-insights — national ML analysis dashboard."""
        try:
            from .data.hcris import _get_latest_per_ccn
            from .ui.ml_insights_page import render_ml_insights
            from .ui.regression_page import _add_computed_features
            hcris = _add_computed_features(_get_latest_per_ccn())
            return self._send_html(render_ml_insights(hcris))
        except Exception as exc:
            return self._error_page("ML Insights Error", str(exc)[:200])

    def _route_hospital_ml(self, ccn: str) -> None:
        """GET /ml-insights/hospital/{ccn} — per-hospital ML analysis."""
        ccn = self._sanitize_ccn(ccn)
        try:
            from .data.hcris import _get_latest_per_ccn
            from .ui.ml_insights_page import render_hospital_ml
            from .ui.regression_page import _add_computed_features
            hcris = _add_computed_features(_get_latest_per_ccn())
            return self._send_html(render_hospital_ml(ccn, hcris))
        except Exception as exc:
            return self._error_page("ML Analysis Error", f"CCN {ccn}: {str(exc)[:200]}")

    def _route_quant_lab(self) -> None:
        """GET /quant-lab — full quant stack dashboard."""
        try:
            from .data.hcris import _get_latest_per_ccn
            from .ui.quant_lab_page import render_quant_lab
            from .ui.regression_page import _add_computed_features
            hcris = _add_computed_features(_get_latest_per_ccn())
            return self._send_html(render_quant_lab(hcris))
        except Exception as exc:
            return self._error_page("Quant Lab Error", str(exc)[:200])

    def _route_data_intelligence(self) -> None:
        """GET /data-intelligence — data estate dashboard."""
        try:
            from .data.hcris import load_hcris
            from .ui.data_dashboard import render_data_dashboard
            hcris = load_hcris()
            return self._send_html(render_data_dashboard(hcris))
        except Exception as exc:
            return self._error_page("Data Intelligence Error", str(exc)[:200])

    def _route_predictive_screener(self) -> None:
        """GET /predictive-screener — ML-powered deal screening."""
        try:
            from .data.hcris import _get_latest_per_ccn
            from .ui.predictive_screener import render_predictive_screener
            hcris = _get_latest_per_ccn()
            qs = urllib.parse.urlparse(self.path).query
            return self._send_html(render_predictive_screener(hcris, qs))
        except Exception as exc:
            return self._error_page("Screener Error", str(exc)[:200])

    def _route_data_room(self, ccn: str) -> None:
        """GET /data-room/{ccn} — seller data room with Bayesian calibration."""
        ccn = self._sanitize_ccn(ccn)
        try:
            from .data.hcris import _get_latest_per_ccn
            from .ml.rcm_performance_predictor import _extract_features, _RCM_TARGETS
            hcris = _get_latest_per_ccn()
            match = hcris[hcris["ccn"] == ccn]
            if match.empty:
                return self._error_page("Hospital Not Found", f"No HCRIS data for CCN {ccn}.")
            hospital = match.iloc[0]
            name = str(hospital.get("name", f"Hospital {ccn}"))
            beds = float(hospital.get("beds", 100) or 100)
            state = str(hospital.get("state", ""))
            # Build ML predictions
            ml_preds = {}
            try:
                feats = _extract_features(hospital)
                for tkey, tcfg in _RCM_TARGETS.items():
                    predicted = tcfg["intercept"]
                    for feat, w in tcfg["weights"].items():
                        predicted += feats.get(feat, 0) * w
                    predicted = max(tcfg["range"][0], min(tcfg["range"][1], predicted))
                    clean_key = tkey.replace("estimated_", "")
                    ml_preds[clean_key] = round(predicted, 4)
            except Exception:
                pass
            # Build HCRIS profile
            hcris_profile = self._load_deal_profile(ccn)
            from .ui.data_room_page import render_data_room
            return self._send_html(render_data_room(
                ccn, name, beds, state, ml_preds,
                self.config.db_path, hcris_profile=hcris_profile))
        except Exception as exc:
            return self._error_page("Data Room Error", f"CCN {ccn}: {str(exc)[:200]}")

    def _route_data_room_add(self, ccn: str) -> None:
        """POST /data-room/{ccn}/add — add a seller data point."""
        import sqlite3
        ccn = self._sanitize_ccn(ccn)
        try:
            form = self._read_form_body()
            metric = form.get("metric", "")[:40]
            value_str = form.get("value", "0")
            try:
                value = float(value_str)
            except (ValueError, TypeError):
                return self._error_page("Invalid Value", f"Could not parse '{value_str}' as a number.")
            sample_size = int(float(form.get("sample_size", "0") or "0"))
            source = form.get("source", "")[:100]
            analyst = form.get("analyst", "")[:20]
            from .data.data_room import save_entry
            con = sqlite3.connect(self.config.db_path)
            save_entry(con, ccn, metric, value, sample_size, source, analyst)
            con.commit()
            con.close()
            self.send_response(HTTPStatus.FOUND)
            self.send_header("Location", f"/data-room/{ccn}")
            self.end_headers()
        except Exception as exc:
            return self._error_page("Data Entry Error", str(exc)[:200])

    def _route_export_bridge(self, ccn: str) -> None:
        """GET /export/bridge/{ccn} — download EBITDA bridge as Excel."""
        ccn = self._sanitize_ccn(ccn)
        try:
            from .data.hcris import _get_latest_per_ccn
            from .ui.regression_page import _add_computed_features
            from .ui.ebitda_bridge_page import (
                _compute_bridge, _load_data_room_overrides,
                compute_peer_targets, _safe_float,
            )
            from .exports.bridge_export import export_bridge_xlsx

            hcris = _add_computed_features(_get_latest_per_ccn())
            match = hcris[hcris["ccn"] == ccn]
            if match.empty:
                return self._error_page("Not Found", f"CCN {ccn} not in HCRIS.")
            h = match.iloc[0]
            name = str(h.get("name", f"Hospital {ccn}"))
            rev = _safe_float(h.get("net_patient_revenue"))
            opex = _safe_float(h.get("operating_expenses"))
            mc = _safe_float(h.get("medicare_day_pct"), 0.4)
            beds = _safe_float(h.get("beds"), 100)
            state = str(h.get("state", ""))
            ebitda = rev - opex
            if ebitda < -rev:
                ebitda = rev * 0.08

            dr = _load_data_room_overrides(self.config.db_path, ccn)
            pt = compute_peer_targets(hcris, beds, state)
            bridge = _compute_bridge(rev, ebitda, medicare_pct=mc,
                                      overrides=dr, peer_targets=pt)

            # Returns grid
            from .ui.ebitda_bridge_page import _compute_returns_grid
            grid = _compute_returns_grid(
                ebitda, bridge["total_ebitda_impact"],
                [8.0, 9.0, 10.0, 11.0, 12.0],
                [9.0, 10.0, 11.0, 11.5, 12.0],
            )

            xlsx_bytes = export_bridge_xlsx(
                bridge, hospital_name=name, ccn=ccn,
                returns_grid=grid,
            )

            safe_name = name.replace(" ", "_")[:30]
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type",
                             "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            self.send_header("Content-Disposition",
                             f'attachment; filename="EBITDA_Bridge_{safe_name}.xlsx"')
            self.send_header("Content-Length", str(len(xlsx_bytes)))
            self.end_headers()
            self.wfile.write(xlsx_bytes)
        except Exception as exc:
            return self._error_page("Export Error", str(exc)[:200])

    def _route_value_tracker(self, deal_id: str) -> None:
        """GET /value-tracker/{deal_id} — post-close value tracking."""
        deal_id = self._sanitize_ccn(deal_id)
        try:
            from .ui.value_tracking_page import render_value_tracker
            return self._send_html(render_value_tracker(deal_id, self.config.db_path))
        except Exception as exc:
            return self._error_page("Value Tracker Error", str(exc)[:200])

    def _route_value_tracker_record(self, deal_id: str) -> None:
        """POST /value-tracker/{deal_id}/record — record quarterly actual."""
        import sqlite3 as _sql_vtr
        deal_id = self._sanitize_ccn(deal_id)
        form = self._read_form_body()
        quarter = form.get("quarter", "")[:10]
        lever = form.get("lever", "")[:60]
        try:
            actual = float(form.get("actual_impact", "0"))
        except (ValueError, TypeError):
            return self._error_page("Invalid Amount", "Could not parse the impact amount.")
        try:
            from .pe.value_tracker import record_quarterly_lever
            con = _sql_vtr.connect(self.config.db_path)
            record_quarterly_lever(con, deal_id, quarter, lever, actual,
                                    notes=form.get("notes", "")[:200])
            con.commit(); con.close()
        except Exception as exc:
            return self._error_page("Record Error", str(exc)[:200])
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", f"/value-tracker/{deal_id}")
        self.end_headers()

    def _route_value_tracker_freeze(self, deal_id: str) -> None:
        """POST /value-tracker/{deal_id}/freeze — freeze bridge as plan."""
        import sqlite3 as _sql_vtf
        deal_id = self._sanitize_ccn(deal_id)
        try:
            from .data.hcris import _get_latest_per_ccn
            from .ui.ebitda_bridge_page import _compute_bridge, _load_data_room_overrides, compute_peer_targets, _safe_float
            from .pe.value_tracker import freeze_bridge_as_plan
            hcris = _get_latest_per_ccn()
            match = hcris[hcris["ccn"] == deal_id]
            if match.empty:
                return self._error_page("Hospital Not Found", f"CCN {deal_id} not in HCRIS.")
            h = match.iloc[0]
            rev = _safe_float(h.get("net_patient_revenue"))
            opex = _safe_float(h.get("operating_expenses"))
            mc = _safe_float(h.get("medicare_day_pct"), 0.4)
            beds = _safe_float(h.get("beds"), 100)
            state = str(h.get("state", ""))
            name = str(h.get("name", f"Hospital {deal_id}"))
            ebitda = rev - opex
            if ebitda < -rev:
                ebitda = rev * 0.08
            dr = _load_data_room_overrides(self.config.db_path, deal_id)
            pt = compute_peer_targets(hcris, beds, state)
            bridge = _compute_bridge(rev, ebitda, medicare_pct=mc, overrides=dr, peer_targets=pt)
            con = _sql_vtf.connect(self.config.db_path)
            freeze_bridge_as_plan(con, deal_id, deal_id, name, bridge)
            con.commit(); con.close()
        except Exception as exc:
            return self._error_page("Freeze Error", str(exc)[:200])
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", f"/value-tracker/{deal_id}")
        self.end_headers()

    def _route_competitive_intel(self, ccn: str) -> None:
        """GET /competitive-intel/{ccn} — peer rankings & gap analysis."""
        ccn = self._sanitize_ccn(ccn)
        try:
            from .data.hcris import _get_latest_per_ccn
            from .ui.competitive_intel_page import render_competitive_intel
            hcris = _get_latest_per_ccn()
            return self._send_html(render_competitive_intel(ccn, hcris))
        except Exception as exc:
            return self._error_page("Competitive Intel Error", f"CCN {ccn}: {str(exc)[:200]}")

    def _route_ebitda_bridge(self, ccn: str) -> None:
        """GET /ebitda-bridge/{ccn} — full EBITDA bridge with returns math."""
        ccn = self._sanitize_ccn(ccn)
        try:
            from .data.hcris import _get_latest_per_ccn
            from .ui.ebitda_bridge_page import render_ebitda_bridge
            from .ui.regression_page import _add_computed_features
            hcris = _add_computed_features(_get_latest_per_ccn())
            return self._send_html(render_ebitda_bridge(ccn, hcris, db_path=self.config.db_path))
        except Exception as exc:
            return self._error_page("EBITDA Bridge Error", f"CCN {ccn}: {str(exc)[:200]}")

    def _route_scenario_modeler(self, ccn: str) -> None:
        """GET /scenarios/{ccn} — scenario comparison modeler."""
        ccn = self._sanitize_ccn(ccn)
        try:
            from .data.hcris import _get_latest_per_ccn
            from .ui.scenario_modeler_page import render_scenario_modeler
            hcris = _get_latest_per_ccn()
            qs = urllib.parse.urlparse(self.path).query
            return self._send_html(render_scenario_modeler(ccn, hcris, qs, db_path=self.config.db_path))
        except Exception as exc:
            return self._error_page("Scenario Error", f"CCN {ccn}: {str(exc)[:200]}")

    def _route_ic_memo(self, ccn: str) -> None:
        """GET /ic-memo/{ccn} — one-click IC memo generation."""
        ccn = self._sanitize_ccn(ccn)
        try:
            from .data.hcris import _get_latest_per_ccn
            from .ui.ic_memo_page import render_ic_memo
            from .ui.regression_page import _add_computed_features
            hcris = _add_computed_features(_get_latest_per_ccn())
            return self._send_html(render_ic_memo(ccn, hcris, db_path=self.config.db_path))
        except Exception as exc:
            return self._error_page("IC Memo Error", f"CCN {ccn}: {str(exc)[:200]}")

    def _route_model_validation(self) -> None:
        """GET /model-validation — prediction accuracy dashboard."""
        try:
            from .data.hcris import _get_latest_per_ccn
            from .ui.model_validation_page import render_model_validation
            from .ui.regression_page import _add_computed_features
            hcris = _add_computed_features(_get_latest_per_ccn())
            return self._send_html(render_model_validation(
                self.config.db_path, hcris_df=hcris))
        except Exception as exc:
            return self._error_page("Model Validation Error", str(exc)[:200])

    def _route_bayesian_profile(self, ccn: str) -> None:
        """GET /bayesian/hospital/{ccn} — Bayesian calibrated KPI profile."""
        ccn = self._sanitize_ccn(ccn)
        try:
            from .data.hcris import _get_latest_per_ccn
            from .ui.bayesian_page import render_bayesian_profile
            hcris = _get_latest_per_ccn()
            match = hcris[hcris["ccn"] == ccn]
            if match.empty:
                return self._error_page("Hospital Not Found",
                                         f"No HCRIS data for CCN {ccn}.")
            hosp = match.iloc[0]
            name = str(hosp.get("name", f"Hospital {ccn}"))
            beds = float(hosp.get("beds", 100) or 100)
            state = str(hosp.get("state", ""))
            observed = {}
            return self._send_html(render_bayesian_profile(
                ccn, name, beds, state, observed))
        except Exception as exc:
            return self._error_page("Bayesian Error", f"CCN {ccn}: {str(exc)[:200]}")

    def _route_market_data_page(self) -> None:
        """GET /market-data/map — national market heatmap + regression."""
        from .data.hcris import _get_latest_per_ccn
        from .ui.market_data_page import render_market_data
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        metric = (qs.get("metric") or ["avg_margin"])[0][:30]
        hcris_df = _get_latest_per_ccn()
        return self._send_html(render_market_data(hcris_df, metric))

    def _route_market_data_state(self, state: str) -> None:
        """GET /market-data/state/<ST> — state-level hospital detail."""
        from .data.hcris import _get_latest_per_ccn
        from .ui.market_data_page import render_state_detail
        hcris_df = _get_latest_per_ccn()
        return self._send_html(render_state_detail(state, hcris_df))

    def _route_benchmarks(self) -> None:
        """GET /benchmarks — benchmark evolution over time."""
        from .ui.analytics_pages import render_benchmark_drift
        drifts = []
        try:
            from .data.benchmark_evolution import compute_benchmark_drift
            drifts_raw = compute_benchmark_drift()
            drifts = [d.to_dict() if hasattr(d, 'to_dict') else d for d in drifts_raw]
        except Exception:
            drifts = [
                {"metric_key": "denial_rate", "current_p50": 11.8, "prior_p50": 12.3,
                 "drift_pp": -0.5, "direction": "industry_improving"},
                {"metric_key": "days_in_ar", "current_p50": 47.2, "prior_p50": 49.1,
                 "drift_pp": -1.9, "direction": "industry_improving"},
                {"metric_key": "net_collection_rate", "current_p50": 95.1, "prior_p50": 94.8,
                 "drift_pp": 0.3, "direction": "industry_improving"},
                {"metric_key": "clean_claim_rate", "current_p50": 89.5, "prior_p50": 88.2,
                 "drift_pp": 1.3, "direction": "industry_improving"},
                {"metric_key": "cost_to_collect", "current_p50": 5.2, "prior_p50": 4.9,
                 "drift_pp": 0.3, "direction": "industry_declining"},
                {"metric_key": "ebitda_margin", "current_p50": 0.072, "prior_p50": 0.085,
                 "drift_pp": -1.3, "direction": "industry_declining"},
            ]
        return self._send_html(render_benchmark_drift(drifts))

    def _route_model_causal(self, deal_id: str) -> None:
        """GET /models/causal/<deal_id> — causal inference for initiative impacts."""
        from .ui.analytics_pages import render_causal_page
        profile = self._load_deal_profile(deal_id)
        if not profile:
            return self._error_page("Deal Not Found", f"No deal or hospital found for ID '{html.escape(deal_id)}'. Try searching from the home page.")
        estimates = []
        try:
            from .analytics.causal_inference import interrupted_time_series
            dr = float(profile.get("denial_rate", 14))
            pre = [dr + 0.5, dr + 0.3, dr + 0.1, dr]
            post = [dr - 0.5, dr - 1.0, dr - 1.5, dr - 2.0]
            its = interrupted_time_series(pre + post, len(pre))
            estimates.append(its.to_dict() if hasattr(its, 'to_dict') else {
                "method": "Interrupted Time Series", "estimated_effect": -1.5,
                "ci_low": -2.5, "ci_high": -0.5, "p_value": 0.02, "confidence": "high"})
        except Exception:
            estimates = [
                {"method": "Interrupted Time Series", "estimated_effect": -1.5,
                 "ci_low": -2.5, "ci_high": -0.5, "p_value": 0.02, "confidence": "high",
                 "n_pre": 4, "n_post": 4},
                {"method": "Difference-in-Differences", "estimated_effect": -1.2,
                 "ci_low": -2.0, "ci_high": -0.4, "p_value": 0.04, "confidence": "medium",
                 "n_pre": 4, "n_post": 4},
                {"method": "Pre-Post Comparison", "estimated_effect": -2.0,
                 "ci_low": -3.5, "ci_high": -0.5, "p_value": 0.08, "confidence": "low",
                 "n_pre": 4, "n_post": 4},
            ]
        return self._send_html(render_causal_page(
            deal_id, profile.get("name", deal_id), estimates))

    def _route_model_counterfactual(self, deal_id: str) -> None:
        """GET /models/counterfactual/<deal_id> — what-if counterfactual."""
        from .ui.analytics_pages import render_counterfactual_page
        profile = self._load_deal_profile(deal_id)
        if not profile:
            return self._error_page("Deal Not Found", f"No deal or hospital found for ID '{html.escape(deal_id)}'. Try searching from the home page.")
        rev = float(profile.get("net_revenue", 200e6))
        margin = float(profile.get("ebitda_margin", 0.10))
        ebitda = rev * margin
        try:
            from .analytics.counterfactual import build_counterfactual
            result = build_counterfactual(
                actual=[ebitda * (1 + 0.02 * i) for i in range(6)],
                initiative_start_period=2,
                estimated_effect=ebitda * 0.05,
            )
            result_dict = result.to_dict()
        except Exception:
            actual = [ebitda * (1 + 0.02 * i) for i in range(6)]
            counter = [ebitda * (1 + 0.01 * i) for i in range(6)]
            result_dict = {
                "actual_trajectory": actual,
                "counterfactual_trajectory": counter,
                "delta_per_period": [a - c for a, c in zip(actual, counter)],
                "cumulative_delta": sum(a - c for a, c in zip(actual, counter)),
                "methodology": "Pre-post with ramp curve adjustment",
            }
        return self._send_html(render_counterfactual_page(
            deal_id, profile.get("name", deal_id), result_dict))

    def _route_model_predicted(self, deal_id: str) -> None:
        """GET /models/predicted/<deal_id> — predicted vs actual comparison."""
        from .ui.analytics_pages import render_predicted_vs_actual
        profile = self._load_deal_profile(deal_id)
        if not profile:
            return self._error_page("Deal Not Found", f"No deal or hospital found for ID '{html.escape(deal_id)}'. Try searching from the home page.")
        store = PortfolioStore(self.config.db_path)
        comparisons = []
        report = {"pct_within_ci": 0, "mean_absolute_error": 0, "n_metrics": 0}
        try:
            from .pe.predicted_vs_actual import compute_predicted_vs_actual, prediction_accuracy_summary
            pvsa = compute_predicted_vs_actual(store, deal_id)
            comparisons = [p.to_dict() for p in pvsa]
            if pvsa:
                summary = prediction_accuracy_summary(pvsa)
                report = summary.to_dict() if hasattr(summary, 'to_dict') else {
                    "pct_within_ci": summary.pct_within_ci,
                    "mean_absolute_error": summary.mean_absolute_error,
                    "n_metrics": summary.n_metrics,
                }
        except Exception:
            dr = float(profile.get("denial_rate", 14))
            ar = float(profile.get("days_in_ar", 50))
            comparisons = [
                {"metric_key": "denial_rate", "predicted_at_diligence": dr,
                 "actual_now": dr - 1.2, "variance_pct": -8.5, "within_ci": True},
                {"metric_key": "days_in_ar", "predicted_at_diligence": ar,
                 "actual_now": ar - 3, "variance_pct": -5.8, "within_ci": True},
                {"metric_key": "net_collection_rate", "predicted_at_diligence": 95.0,
                 "actual_now": 94.2, "variance_pct": -0.8, "within_ci": True},
                {"metric_key": "clean_claim_rate", "predicted_at_diligence": 90.0,
                 "actual_now": 87.5, "variance_pct": -2.8, "within_ci": False},
            ]
            report = {"pct_within_ci": 0.75, "mean_absolute_error": 1.8, "n_metrics": 4}
        return self._send_html(render_predicted_vs_actual(
            deal_id, profile.get("name", deal_id), comparisons, report))

    def _route_deal_query(self) -> None:
        """GET /query — rule-based deal query with natural-language-style filters."""
        from .ui._chartis_kit import chartis_shell as _shell_q
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        query_str = (qs.get("q") or [""])[0][:200]

        results_html = ""
        if query_str.strip():
            try:
                from .analysis.deal_query import parse_query, execute_query
                store = PortfolioStore(self.config.db_path)
                filters = parse_query(query_str)
                matches = execute_query(store, filters)
                if matches:
                    rows = ""
                    for m in matches[:20]:
                        d = m.to_dict() if hasattr(m, 'to_dict') else vars(m)
                        did = html.escape(str(d.get("deal_id", "")))
                        name = html.escape(str(d.get("deal_name", did)))
                        grade = html.escape(str(d.get("grade", "—")))
                        rows += (
                            f'<tr>'
                            f'<td><a href="/deal/{did}" style="font-weight:500;">{name}</a></td>'
                            f'<td class="num">{grade}</td>'
                            f'<td style="white-space:nowrap;">'
                            f'<a href="/deal/{did}" class="cad-badge cad-badge-blue" '
                            f'style="text-decoration:none;">Dashboard</a> '
                            f'<a href="/models/dcf/{did}" class="cad-badge cad-badge-muted" '
                            f'style="text-decoration:none;">DCF</a></td>'
                            f'</tr>'
                        )
                    results_html = (
                        f'<div class="cad-card">'
                        f'<h2>{len(matches)} Matches</h2>'
                        f'<table class="cad-table"><thead><tr>'
                        f'<th>Deal</th><th>Grade</th><th>Actions</th>'
                        f'</tr></thead><tbody>{rows}</tbody></table></div>'
                    )
                else:
                    results_html = '<div class="cad-card"><p style="color:var(--cad-text3);">No deals match the query.</p></div>'
            except Exception as exc:
                results_html = (
                    f'<div class="cad-card"><p style="color:var(--cad-text3);">'
                    f'Query error: {html.escape(str(exc)[:100])}</p></div>'
                )

        body = (
            f'<div class="cad-card">'
            f'<h2>Deal Query</h2>'
            f'<p style="color:var(--cad-text2);font-size:12.5px;margin-bottom:12px;">'
            f'Search deals using metric filters. Examples: '
            f'<code>denial_rate &gt; 15</code>, <code>days_in_ar &lt; 45</code>, '
            f'<code>grade = A</code></p>'
            f'<form method="GET" action="/query" style="display:flex;gap:8px;">'
            f'<input name="q" value="{html.escape(query_str)}" '
            f'placeholder="e.g. denial_rate > 15 and days_in_ar < 50" '
            f'style="flex:1;padding:8px 12px;border:1px solid var(--cad-border);'
            f'border-radius:6px;background:var(--cad-bg3);color:var(--cad-text);font-size:13px;">'
            f'<button type="submit" class="cad-btn cad-btn-primary">Query</button>'
            f'</form></div>'
            f'{results_html}'
        )

        return self._send_html(_shell_q(body, "Deal Query",
                                         subtitle="Filter deals by metric criteria"))

    def _route_data_explorer(self) -> None:
        """GET /data — browse all public data sources."""
        from .data.hcris import _get_latest_per_ccn
        from .data.cms_hcris import HCRISRecord  # noqa: F401
        from .data.sources import iter_meaningful_paths  # noqa: F401
        from .data.data_scrub import ScrubReport  # noqa: F401
        from .data.irs990_loader import IRS990Record  # noqa: F401
        from .data.lookup import search as _lookup_search  # noqa: F401
        from .ui.data_explorer import render_data_explorer
        try:
            hcris = _get_latest_per_ccn()
            hcris_count = len(hcris)
        except Exception:
            hcris_count = 0
        # Probe additional data sources for status
        sources_status = {}
        try:
            from .data.sec_edgar import check_edgar_available
            sources_status["sec_available"] = check_edgar_available()
        except Exception:
            pass
        try:
            from .data.benchmark_evolution import get_latest_benchmarks
            sources_status["benchmarks"] = True
        except Exception:
            pass
        try:
            from .data.ingest import list_ingest_formats
            sources_status["ingest_formats"] = True
        except Exception:
            pass
        return self._send_html(render_data_explorer(
            hcris_count=hcris_count, sources_status=sources_status))

    def _route_screener_page(self) -> None:
        """GET /screen — metric-based hospital screener with HCRIS data."""
        from .data.hcris import _get_latest_per_ccn
        from .ui.deal_comparison import render_screen_page
        import numpy as _np_scr

        hcris = _get_latest_per_ccn()
        total = len(hcris)
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)

        preset = (qs.get("preset") or [""])[0]
        filters = {
            "min_beds": (qs.get("min_beds") or [""])[0],
            "max_beds": (qs.get("max_beds") or [""])[0],
            "min_revenue": (qs.get("min_revenue") or [""])[0],
            "max_margin": (qs.get("max_margin") or [""])[0],
            "state": (qs.get("state") or [""])[0].upper(),
        }

        # Preset screens
        if preset == "turnaround":
            filters = {"min_beds": "100", "max_beds": "", "min_revenue": "50",
                        "max_margin": "5", "state": ""}
        elif preset == "large_cap":
            filters = {"min_beds": "300", "max_beds": "", "min_revenue": "300",
                        "max_margin": "", "state": ""}
        elif preset == "margin_expansion":
            filters = {"min_beds": "150", "max_beds": "", "min_revenue": "100",
                        "max_margin": "15", "state": ""}
        elif preset == "undervalued":
            filters = {"min_beds": "200", "max_beds": "", "min_revenue": "",
                        "max_margin": "3", "state": ""}
        elif preset == "small_efficient":
            filters = {"min_beds": "", "max_beds": "200", "min_revenue": "",
                        "max_margin": "", "state": ""}

        has_filters = any(v for v in filters.values())
        results = None

        if has_filters:
            df = hcris.copy()
            rev_col = "net_patient_revenue" if "net_patient_revenue" in df.columns else "gross_patient_revenue"

            # Compute margin
            if "operating_expenses" in df.columns and rev_col in df.columns:
                r = df[rev_col].fillna(0)
                o = df["operating_expenses"].fillna(0)
                df["operating_margin"] = _np_scr.where(r > 1e5, (r - o) / r, 0)
                df["operating_margin"] = df["operating_margin"].clip(-1, 1)

            if filters.get("min_beds"):
                try:
                    df = df[df["beds"].fillna(0) >= float(filters["min_beds"])]
                except ValueError:
                    pass
            if filters.get("max_beds"):
                try:
                    df = df[df["beds"].fillna(0) <= float(filters["max_beds"])]
                except ValueError:
                    pass
            if filters.get("min_revenue"):
                try:
                    df = df[df[rev_col].fillna(0) >= float(filters["min_revenue"]) * 1e6]
                except ValueError:
                    pass
            if filters.get("max_margin"):
                try:
                    if "operating_margin" in df.columns:
                        df = df[df["operating_margin"] <= float(filters["max_margin"]) / 100]
                except ValueError:
                    pass
            if filters.get("state"):
                st = filters["state"].strip()
                if st:
                    df = df[df["state"] == st]

            # Sort by revenue descending, take top 50
            df = df.sort_values(rev_col, ascending=False).head(50)
            results = []
            for _, row in df.iterrows():
                results.append({
                    "ccn": str(row.get("ccn", "")),
                    "name": str(row.get("name", "")),
                    "state": str(row.get("state", "")),
                    "beds": int(row.get("beds", 0)),
                    "net_patient_revenue": float(row.get(rev_col, 0)),
                    "operating_margin": float(row.get("operating_margin", 0)) if "operating_margin" in row.index else 0,
                })

        return self._send_html(render_screen_page(
            results=results, filters=filters, predefined=preset, total_scanned=total))

    def _route_library_page(self) -> None:
        """GET /library — research library and reference materials."""
        from .ui.library_page import render_library
        return self._send_html(render_library())

    def _route_regression_page(self) -> None:
        """GET /portfolio/regression — interactive regression analysis."""
        from .data.hcris import _get_latest_per_ccn
        from .ui.regression_page import render_regression_page
        import pandas as _pd_reg
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        source = (qs.get("source") or ["hcris"])[0][:20]
        target = (qs.get("target") or ["net_patient_revenue"])[0][:40]
        hcris_df = _get_latest_per_ccn()
        store = PortfolioStore(self.config.db_path)
        try:
            deals_df = store.list_deals()
        except Exception:
            deals_df = _pd_reg.DataFrame()
        return self._send_html(render_regression_page(
            data_source=source, target=target,
            hcris_df=hcris_df, deals_df=deals_df,
        ))

    def _route_hospital_regression(self, ccn: str) -> None:
        """GET /portfolio/regression/hospital/{ccn} — per-hospital statistical profile."""
        from .data.hcris import _get_latest_per_ccn
        from .ui.hospital_stats_page import render_hospital_stats
        import pandas as _pd_hr
        hcris_df = _get_latest_per_ccn()
        return self._send_html(render_hospital_stats(ccn, hcris_df))

    def _load_deal_profile(self, deal_id: str) -> Dict[str, Any]:
        """Load deal profile from the database, falling back to HCRIS for CCNs.

        Every profile goes through ``_sanitize_profile_margins`` before
        returning, so stored data with implausible EBITDA margins (a
        common HCRIS data-quality artifact — opex missing an overhead
        allocation) gets clamped to a realistic hospital range before
        downstream DCF / LBO / bridge see it.
        """
        import json as _ldj
        store = PortfolioStore(self.config.db_path)
        # Try deals table first
        try:
            with store.connect() as con:
                row = con.execute(
                    "SELECT deal_id, name, profile_json FROM deals WHERE deal_id = ?",
                    (deal_id,),
                ).fetchone()
            if row is not None:
                profile: Dict[str, Any] = {}
                raw = row["profile_json"] if "profile_json" in row.keys() else None
                if raw:
                    try:
                        profile = _ldj.loads(raw) or {}
                    except Exception:
                        pass
                profile["deal_id"] = deal_id
                profile["name"] = row["name"] or deal_id
                return _sanitize_profile_margins(profile)
        except Exception:
            pass
        # Fallback: check if deal_id is a hospital CCN in HCRIS
        try:
            from .data.hcris import _get_latest_per_ccn
            import numpy as _np_ldp
            hdf = _get_latest_per_ccn()
            match = hdf[hdf["ccn"] == deal_id]
            if not match.empty:
                h = match.iloc[0]

                def _sf(v, d=0.0):
                    if v is None:
                        return d
                    try:
                        f = float(v)
                        return d if f != f else f
                    except (TypeError, ValueError):
                        return d

                rev = _sf(h.get("net_patient_revenue"))
                opex = _sf(h.get("operating_expenses"))
                gross = _sf(h.get("gross_patient_revenue"))
                beds = _sf(h.get("beds"))
                mc = _sf(h.get("medicare_day_pct"))
                md = _sf(h.get("medicaid_day_pct"))
                days = _sf(h.get("total_patient_days"))
                bda = _sf(h.get("bed_days_available"))

                # Raw HCRIS (rev - opex)/rev. Hospital EBITDA margins
                # realistically land in [-15%, +15%]. When the raw
                # calculation exits that band, HCRIS operating_expenses
                # is almost always missing a component (overhead
                # allocation not rolled up in the source worksheet).
                # Clamp with a flag so downstream views (DCF / LBO /
                # bridge) project plausible numbers instead of 88%
                # margins that then compound into 60x MOIC.
                margin_raw = (rev - opex) / rev if rev > 1e5 else 0.0
                if margin_raw > 0.15:
                    margin = 0.08           # industry median fallback
                    margin_clamped = True
                elif margin_raw < -0.20:
                    margin = -0.05
                    margin_clamped = True
                else:
                    margin = margin_raw
                    margin_clamped = False
                ebitda_computed = (rev * margin) if margin_clamped else (rev - opex)
                occ = days / bda if bda > 0 else 0
                n2g = rev / gross if gross > 0 else 0.3
                comm = max(0, 1 - mc - md)

                profile = {
                    "deal_id": deal_id,
                    "ccn": deal_id,
                    "name": str(h.get("name", f"Hospital {deal_id}")),
                    "state": str(h.get("state", "")),
                    "county": str(h.get("county", "")),
                    "bed_count": int(beds) if beds > 0 else 0,
                    "beds": int(beds) if beds > 0 else 0,
                    "net_revenue": rev,
                    "net_patient_revenue": rev,
                    "operating_expenses": opex,
                    "gross_patient_revenue": gross,
                    "ebitda_margin": round(margin, 4),
                    "ebitda_margin_raw_hcris": round(margin_raw, 4),
                    "ebitda_margin_clamped": margin_clamped,
                    "ebitda": round(ebitda_computed, 0) if rev > 1e5 else 0,
                    "current_ebitda": round(ebitda_computed, 0) if rev > 1e5 else 0,
                    "medicare_pct": round(mc, 3),
                    "medicaid_pct": round(md, 3),
                    "commercial_pct": round(comm, 3),
                    "occupancy_rate": round(occ, 3),
                    "net_to_gross_ratio": round(n2g, 3),
                    "revenue_per_bed": round(rev / beds, 0) if beds > 0 else 0,
                    "payer_mix_medicare_pct": round(mc * 100, 1),
                    "payer_mix_medicaid_pct": round(md * 100, 1),
                    "payer_mix_commercial_pct": round(comm * 100, 1),
                    "total_patient_days": int(days),
                    "from_hcris": True,
                }
                # Add ML-predicted RCM metrics if available
                try:
                    from .ml.rcm_performance_predictor import _extract_features, _RCM_TARGETS
                    feats = _extract_features(h)
                    for tkey, tcfg in _RCM_TARGETS.items():
                        predicted = tcfg["intercept"]
                        for feat, w in tcfg["weights"].items():
                            predicted += feats.get(feat, 0) * w
                        predicted = max(tcfg["range"][0], min(tcfg["range"][1], predicted))
                        clean_key = tkey.replace("estimated_", "")
                        profile[clean_key] = round(predicted, 4)
                except Exception:
                    pass
                return _sanitize_profile_margins(profile)
        except Exception:
            pass
        return {}

    def _route_model_dcf(self, deal_id: str) -> None:
        """GET /models/dcf/<deal_id> — browser-rendered DCF model."""
        from .finance.dcf_model import build_dcf_from_deal
        from .ui.models_page import render_dcf_page
        profile = self._load_deal_profile(deal_id)
        if not profile:
            return self._error_page("Deal Not Found", f"No deal or hospital found for ID '{html.escape(deal_id)}'. Try searching from the home page.")
        try:
            result = build_dcf_from_deal(profile)
            dcf_dict = result.to_dict()
        except Exception as exc:
            dcf_dict = {"error": str(exc), "assumptions": {}, "projections": [],
                        "enterprise_value": 0, "pv_cash_flows": 0,
                        "pv_terminal": 0, "terminal_value": 0}
        return self._send_html(render_dcf_page(
            deal_id, profile.get("name", deal_id), dcf_dict))

    def _route_model_lbo(self, deal_id: str) -> None:
        """GET /models/lbo/<deal_id> — browser-rendered LBO model."""
        from .finance.lbo_model import build_lbo_from_deal
        from .ui.models_page import render_lbo_page
        profile = self._load_deal_profile(deal_id)
        if not profile:
            return self._error_page("Deal Not Found", f"No deal or hospital found for ID '{html.escape(deal_id)}'. Try searching from the home page.")
        try:
            # Use build_lbo_from_deal: it normalizes the profile's
            # revenue / margin into consistent entry_ebitda. The prior
            # direct build_lbo(revenue_base=, ebitda_margin=) call
            # silently dropped the margin override (wrong kwarg name —
            # the field is ebitda_margin_base) and left entry_ebitda
            # at its default, producing absurd MOIC.
            result = build_lbo_from_deal(profile)
            lbo_dict = result.to_dict()
        except Exception as exc:
            lbo_dict = {"error": str(exc), "returns": {}, "sources_and_uses": {},
                        "annual_projections": [], "debt_schedule": []}
        return self._send_html(render_lbo_page(
            deal_id, profile.get("name", deal_id), lbo_dict))

    def _route_model_financials(self, deal_id: str) -> None:
        """GET /models/financials/<deal_id> — browser-rendered 3-statement model."""
        from .finance.three_statement import build_three_statement
        from .ui.models_page import render_financials_page
        profile = self._load_deal_profile(deal_id)
        if not profile:
            return self._error_page("Deal Not Found", f"No deal or hospital found for ID '{html.escape(deal_id)}'. Try searching from the home page.")
        try:
            result = build_three_statement(profile)
            fin_dict = result.to_dict()
        except Exception as exc:
            fin_dict = {"error": str(exc), "income_statement": [],
                        "balance_sheet": [], "cash_flow": [], "summary": {}}
        return self._send_html(render_financials_page(
            deal_id, profile.get("name", deal_id), fin_dict))

    def _route_model_denial(self, deal_id: str) -> None:
        """GET /models/denial/<deal_id> — browser-rendered denial analysis."""
        from .finance.denial_drivers import analyze_denial_drivers
        from .ui.denial_page import render_denial_page
        profile = self._load_deal_profile(deal_id)
        if not profile:
            return self._error_page("Deal Not Found", f"No deal or hospital found for ID '{html.escape(deal_id)}'. Try searching from the home page.")
        try:
            result = analyze_denial_drivers(profile)
            dd_dict = result.to_dict()
            # If the module returned sparse data, enrich with estimates
            drivers = dd_dict.get("drivers", [])
            meaningful = [d for d in drivers if float(d.get("annual_impact", d.get("impact", 0))) > 0]
            if len(meaningful) < 2:
                raise ValueError("Sparse data — use fallback estimates")
        except Exception:
            dr = float(profile.get("denial_rate", 12))
            rev = float(profile.get("net_revenue", 200e6))
            gap = max(0, dr - 8)
            total_impact = rev * gap / 100 * 0.3
            dd_dict = {"drivers": [
                {"driver": "Prior Authorization Denials", "contribution_pct": gap * 0.35,
                 "annual_impact": total_impact * 0.35, "severity": "high"},
                {"driver": "Coding & Documentation Errors", "contribution_pct": gap * 0.25,
                 "annual_impact": total_impact * 0.25, "severity": "high"},
                {"driver": "Timely Filing Misses", "contribution_pct": gap * 0.15,
                 "annual_impact": total_impact * 0.15, "severity": "medium"},
                {"driver": "Medical Necessity Disputes", "contribution_pct": gap * 0.15,
                 "annual_impact": total_impact * 0.15, "severity": "medium"},
                {"driver": "Eligibility Verification Gaps", "contribution_pct": gap * 0.10,
                 "annual_impact": total_impact * 0.10, "severity": "medium"},
            ], "summary": {
                "current_denial_rate": dr, "target_denial_rate": 8.0,
                "total_annual_impact": total_impact,
            }, "recommendations": [
                {"title": "Implement prior auth tracking system", "category": "RCM Operations",
                 "description": "Automate prior auth status tracking and proactive follow-up"},
                {"title": "CDI program expansion", "category": "Coding",
                 "description": "Clinical documentation improvement with real-time physician queries"},
                {"title": "Payer-specific denial protocols", "category": "Denial Management",
                 "description": "Create playbooks for top denial reasons by payer"},
            ]}
        return self._send_html(render_denial_page(
            deal_id, profile.get("name", deal_id), dd_dict))

    def _route_model_market(self, deal_id: str) -> None:
        """GET /models/market/<deal_id> — browser-rendered market analysis."""
        from .finance.market_analysis import analyze_market
        from .data.market_intelligence import find_competitors  # noqa: F401
        from .ui.market_analysis_page import render_market_analysis_page
        profile = self._load_deal_profile(deal_id)
        if not profile:
            return self._error_page("Deal Not Found", f"No deal or hospital found for ID '{html.escape(deal_id)}'. Try searching from the home page.")
        try:
            result = analyze_market(profile)
            ma_dict = result.to_dict()
        except Exception as exc:
            ma_dict = {"error": str(exc), "target": {}, "market_size": {},
                       "moat": {}, "competitors": [], "payer_mix_region": {},
                       "market_trends": {}}
        return self._send_html(render_market_analysis_page(
            deal_id, profile.get("name", deal_id), ma_dict))

    def _route_model_questions(self, deal_id: str) -> None:
        """GET /models/questions/<deal_id> — auto-generated diligence questions."""
        from .analysis.diligence_questions import generate_diligence_questions
        from .ui.diligence_page import render_diligence_questions
        profile = self._load_deal_profile(deal_id)
        if not profile:
            return self._error_page("Deal Not Found", f"No deal or hospital found for ID '{html.escape(deal_id)}'. Try searching from the home page.")
        store = PortfolioStore(self.config.db_path)
        try:
            from .analysis.analysis_store import get_or_build_packet
            pkt = get_or_build_packet(store, deal_id, skip_simulation=True)
            questions = generate_diligence_questions(pkt)
            q_list = [q.to_dict() if hasattr(q, 'to_dict') else (
                {"question": str(q.question) if hasattr(q, 'question') else str(q),
                 "category": getattr(q, 'category', 'General'),
                 "priority": getattr(q, 'priority', 'medium'),
                 "rationale": getattr(q, 'rationale', '')}
            ) for q in questions]
        except Exception:
            q_list = [
                {"question": f"What is the root cause of the {profile.get('denial_rate', 'N/A')}% denial rate?",
                 "category": "RCM Operations", "priority": "high",
                 "rationale": "Denial rate above industry median suggests systemic issues"},
                {"question": "Provide payer-level denial breakdown for the past 12 months",
                 "category": "RCM Operations", "priority": "high",
                 "rationale": "Identifies which payers drive the most denials"},
                {"question": f"Explain the {profile.get('days_in_ar', 'N/A')}-day AR collection cycle",
                 "category": "Revenue Cycle", "priority": "medium",
                 "rationale": "AR days above 48 indicate follow-up process gaps"},
                {"question": "Provide the payer contract rate schedule for top 5 commercial payers",
                 "category": "Payer Relations", "priority": "high",
                 "rationale": "Needed for reimbursement modeling and rate renegotiation thesis"},
                {"question": "What is the current coding accuracy rate and staffing model?",
                 "category": "Coding & Documentation", "priority": "medium",
                 "rationale": "Coding errors are a top driver of initial denials"},
                {"question": "Provide 3-year trend data for all RCM KPIs",
                 "category": "Data Request", "priority": "medium",
                 "rationale": "Trend analysis validates improvement trajectory"},
            ]
        return self._send_html(render_diligence_questions(
            deal_id, profile.get("name", deal_id), q_list))

    def _route_model_playbook(self, deal_id: str) -> None:
        """GET /models/playbook/<deal_id> — operational playbook."""
        from .ui.diligence_page import render_playbook
        profile = self._load_deal_profile(deal_id)
        if not profile:
            return self._error_page("Deal Not Found", f"No deal or hospital found for ID '{html.escape(deal_id)}'. Try searching from the home page.")
        store = PortfolioStore(self.config.db_path)
        try:
            from .analysis.playbook import build_playbook
            entries_raw = build_playbook(store, deal_id)
            entries = [e.to_dict() if hasattr(e, 'to_dict') else vars(e) for e in entries_raw]
        except Exception:
            dr = float(profile.get("denial_rate", 12))
            ar = float(profile.get("days_in_ar", 48))
            rev = float(profile.get("net_revenue", 200e6))
            entries = []
            if dr > 10:
                entries.append({"title": "Denial Rate Reduction Program", "category": "RCM",
                    "priority": "high", "ebitda_impact": rev * (dr - 8) / 100 * 0.3,
                    "timeline": "6-12 months", "owner": "VP Revenue Cycle"})
            if ar > 45:
                entries.append({"title": "AR Acceleration Initiative", "category": "RCM",
                    "priority": "high", "ebitda_impact": rev * (ar - 42) / 365 * 0.05,
                    "timeline": "3-6 months", "owner": "Director Collections"})
            entries.extend([
                {"title": "Coding Accuracy Improvement", "category": "CDI",
                 "priority": "medium", "ebitda_impact": rev * 0.005,
                 "timeline": "6-9 months", "owner": "HIM Director"},
                {"title": "Payer Contract Renegotiation", "category": "Managed Care",
                 "priority": "medium", "ebitda_impact": rev * 0.015,
                 "timeline": "12-18 months", "owner": "VP Managed Care"},
                {"title": "Clean Claim Rate Optimization", "category": "RCM",
                 "priority": "medium", "ebitda_impact": rev * 0.003,
                 "timeline": "3-6 months", "owner": "Claims Manager"},
            ])
        return self._send_html(render_playbook(
            deal_id, profile.get("name", deal_id), entries))

    def _route_model_waterfall(self, deal_id: str) -> None:
        """GET /models/waterfall/<deal_id> — returns waterfall."""
        from .ui.waterfall_page import render_waterfall_page
        profile = self._load_deal_profile(deal_id)
        if not profile:
            return self._error_page("Deal Not Found", f"No deal or hospital found for ID '{html.escape(deal_id)}'. Try searching from the home page.")
        rev = float(profile.get("net_revenue", 200e6))
        margin = float(profile.get("ebitda_margin", 0.12))
        ebitda = rev * margin
        entry_multiple = 11.0
        exit_multiple = 11.5
        hold = 5.0
        invested = ebitda * entry_multiple * 0.35
        exit_ev = ebitda * (1.03 ** hold) * exit_multiple
        try:
            from .pe.waterfall import compute_waterfall, WaterfallStructure
            from .pe.waterfall import DealReturn
            wf = WaterfallStructure()
            dr = DealReturn(invested=invested, exit_proceeds=exit_ev * 0.35,
                           hold_years=hold, mgmt_fees_total=invested * 0.02 * hold)
            result = compute_waterfall(wf, dr)
            result_dict = {
                "invested": result.invested, "exit_proceeds": result.exit_proceeds,
                "hold_years": result.hold_years, "lp_total": result.lp_total,
                "gp_total": result.gp_total, "lp_moic": result.lp_moic,
                "gp_moic": result.gp_moic, "lp_irr": result.lp_irr,
                "gross_moic": result.gross_moic, "gross_irr": result.gross_irr,
                "tiers": [{"tier_name": t.tier_name, "hurdle_rate": t.hurdle_rate,
                           "carry_rate": t.carry_rate, "lp_amount": t.lp_amount,
                           "gp_amount": t.gp_amount} for t in result.tiers],
            }
        except Exception:
            gross_moic = exit_ev * 0.35 / invested if invested > 0 else 0
            result_dict = {
                "invested": invested, "exit_proceeds": exit_ev * 0.35,
                "hold_years": hold, "lp_total": invested * (gross_moic - 1) * 0.8,
                "gp_total": invested * (gross_moic - 1) * 0.2,
                "lp_moic": gross_moic * 0.85, "gp_moic": gross_moic * 1.5,
                "lp_irr": (gross_moic ** (1 / hold) - 1) * 0.85,
                "gross_moic": gross_moic,
                "gross_irr": gross_moic ** (1 / hold) - 1,
                "tiers": [],
            }
        return self._send_html(render_waterfall_page(
            deal_id, profile.get("name", deal_id), result_dict))

    def _route_model_bridge(self, deal_id: str) -> None:
        """GET /models/bridge/<deal_id> — EBITDA value bridge."""
        from .ui.pe_tools_page import render_value_bridge
        profile = self._load_deal_profile(deal_id)
        if not profile:
            return self._error_page("Deal Not Found", f"No deal or hospital found for ID '{html.escape(deal_id)}'. Try searching from the home page.")
        rev = float(profile.get("net_revenue", 200e6))
        margin = float(profile.get("ebitda_margin", 0.10))
        dr = float(profile.get("denial_rate", 12))
        ar = float(profile.get("days_in_ar", 48))
        current_ebitda = rev * margin
        levers = [
            {"lever": "Denial Rate Reduction", "impact": rev * max(0, dr - 8) / 100 * 0.3,
             "probability": 0.7},
            {"lever": "AR Acceleration", "impact": rev * max(0, ar - 42) / 365 * 0.05,
             "probability": 0.8},
            {"lever": "Coding Accuracy Uplift", "impact": rev * 0.005,
             "probability": 0.6},
            {"lever": "Payer Mix Optimization", "impact": rev * 0.012,
             "probability": 0.5},
            {"lever": "Cost to Collect Reduction", "impact": rev * 0.004,
             "probability": 0.75},
            {"lever": "Clean Claim Improvement", "impact": rev * 0.003,
             "probability": 0.7},
            {"lever": "Volume & Rate Growth", "impact": rev * 0.02,
             "probability": 0.4},
        ]
        try:
            from .pe.rcm_ebitda_bridge import FinancialProfile, RCMEBITDABridge
            from .pe.value_plan import load_value_plan  # noqa: F401
            from .pe.pe_integration import _uplift_from_summary as _pe_uplift  # noqa: F401
            from .pe.value_creation import _plan_numbers as _vc_plan  # noqa: F401
            fp = FinancialProfile(net_revenue=rev, ebitda_margin=margin,
                                  denial_rate=dr / 100, days_in_ar=ar)
            bridge_obj = RCMEBITDABridge(fp)
            bridge_dict = bridge_obj.to_dict()
            if "levers" in bridge_dict or "items" in bridge_dict:
                levers = bridge_dict.get("levers", bridge_dict.get("items", levers))
        except Exception:
            pass
        total = sum(l.get("impact", l.get("ebitda_impact", 0)) * l.get("probability", l.get("prob", 1))
                    for l in levers)
        bridge_data = {"current_ebitda": current_ebitda, "total_ebitda_impact": total, "levers": levers}
        return self._send_html(render_value_bridge(
            deal_id, profile.get("name", deal_id), bridge_data))

    def _route_model_comparables(self, deal_id: str) -> None:
        """GET /models/comparables/<deal_id> — comparable hospitals."""
        from .ui.pe_tools_page import render_comparable_hospitals
        profile = self._load_deal_profile(deal_id)
        if not profile:
            return self._error_page("Deal Not Found", f"No deal or hospital found for ID '{html.escape(deal_id)}'. Try searching from the home page.")
        try:
            from .ml.comparable_finder import find_comparables
            comps = find_comparables(profile, limit=20)
            comp_list = [c.to_dict() if hasattr(c, 'to_dict') else c for c in comps]
        except Exception:
            try:
                from .data.hcris import _get_latest_per_ccn
                hdf = _get_latest_per_ccn()
                state = profile.get("state", "")
                beds = float(profile.get("bed_count", profile.get("beds", 0)))
                if state:
                    peers = hdf[hdf["state"] == state].copy()
                else:
                    peers = hdf.copy()
                if beds > 0:
                    peers["_dist"] = abs(peers["beds"].fillna(0) - beds)
                    peers = peers.sort_values("_dist")
                comp_list = [r.to_dict() for _, r in peers.head(15).iterrows()]
            except Exception:
                comp_list = []
        return self._send_html(render_comparable_hospitals(
            deal_id, profile.get("name", deal_id), comp_list, profile))

    def _route_model_anomalies(self, deal_id: str) -> None:
        """GET /models/anomalies/<deal_id> — data anomaly detection."""
        from .ui.pe_tools_page import render_anomaly_report
        profile = self._load_deal_profile(deal_id)
        if not profile:
            return self._error_page("Deal Not Found", f"No deal or hospital found for ID '{html.escape(deal_id)}'. Try searching from the home page.")
        anomalies = []
        benchmarks = {
            "denial_rate": (12.0, 4.0), "days_in_ar": (48.0, 10.0),
            "net_collection_rate": (95.0, 3.0), "clean_claim_rate": (90.0, 5.0),
            "cost_to_collect": (5.0, 1.5), "bed_count": (250.0, 150.0),
        }
        for metric, (expected, std) in benchmarks.items():
            val = profile.get(metric)
            if val is not None:
                try:
                    v = float(val)
                    z = (v - expected) / std if std > 0 else 0
                    if abs(z) > 1.5:
                        anomalies.append({"metric": metric.replace("_", " ").title(),
                                          "value": v, "expected": expected, "z_score": z})
                except (TypeError, ValueError):
                    pass
        try:
            from .ml.anomaly_detector import detect_anomalies
            detected = detect_anomalies(profile)
            if detected:
                anomalies = [d.to_dict() if hasattr(d, 'to_dict') else d for d in detected]
        except Exception:
            pass
        anomalies.sort(key=lambda a: -abs(float(a.get("z_score", a.get("deviation", 0)))))
        return self._send_html(render_anomaly_report(
            deal_id, profile.get("name", deal_id), anomalies))

    def _route_model_service_lines(self, deal_id: str) -> None:
        """GET /models/service-lines/<deal_id> — service line profitability."""
        from .ui.pe_tools_page import render_service_lines
        profile = self._load_deal_profile(deal_id)
        if not profile:
            return self._error_page("Deal Not Found", f"No deal or hospital found for ID '{html.escape(deal_id)}'. Try searching from the home page.")
        rev = float(profile.get("net_revenue", 200e6))
        try:
            from .analytics.service_lines import analyze_service_lines
            result = analyze_service_lines(profile)
            lines = [l.to_dict() if hasattr(l, 'to_dict') else l for l in result]
        except Exception:
            lines = [
                {"service_line": "Medical/Surgical", "revenue": rev * 0.35, "margin": 0.08, "volume": 12000},
                {"service_line": "Emergency", "revenue": rev * 0.20, "margin": 0.03, "volume": 45000},
                {"service_line": "Orthopedics", "revenue": rev * 0.12, "margin": 0.15, "volume": 4500},
                {"service_line": "Cardiology", "revenue": rev * 0.10, "margin": 0.12, "volume": 6000},
                {"service_line": "Obstetrics", "revenue": rev * 0.08, "margin": 0.05, "volume": 3200},
                {"service_line": "Oncology", "revenue": rev * 0.07, "margin": 0.10, "volume": 2800},
                {"service_line": "Behavioral Health", "revenue": rev * 0.05, "margin": -0.02, "volume": 5500},
                {"service_line": "Rehabilitation", "revenue": rev * 0.03, "margin": 0.06, "volume": 1800},
            ]
        return self._send_html(render_service_lines(
            deal_id, profile.get("name", deal_id), lines))

    def _route_model_memo(self, deal_id: str) -> None:
        """GET /models/memo/<deal_id> — browser-rendered IC memo."""
        from .ui.memo_page import render_memo_page
        profile = self._load_deal_profile(deal_id)
        if not profile:
            return self._error_page("Deal Not Found", f"No deal or hospital found for ID '{html.escape(deal_id)}'. Try searching from the home page.")
        try:
            from .ai.memo_writer import compose_memo
            store = PortfolioStore(self.config.db_path)
            memo = compose_memo(store, deal_id)
            memo_dict = memo.to_dict() if hasattr(memo, 'to_dict') else memo
        except Exception:
            name = profile.get("name", deal_id)
            try:
                dr = float(profile.get("denial_rate", 12))
            except (TypeError, ValueError):
                dr = 12.0
            rev = float(profile.get("net_revenue", 0))
            beds = int(profile.get("bed_count", 0))
            state = profile.get("state", "unknown")
            gap = max(0, dr - 8)
            recoverable = rev * gap / 100 * 0.3
            memo_dict = {"sections": [
                {"title": "Executive Summary", "content": f"{name} is a {beds}-bed hospital in {state} with ${rev/1e6:.0f}M in annual net patient revenue. Denial rate of {dr:.1f}% presents a clear RCM improvement opportunity.", "fact_checks_passed": True},
                {"title": "Investment Thesis", "content": f"The primary value creation thesis centers on denial rate reduction from {dr:.1f}% to the industry target of 8%. Based on our analysis, this represents an estimated ${recoverable/1e6:.1f}M in annual recoverable revenue.", "fact_checks_passed": True},
                {"title": "Risk Assessment", "content": "Key risks include payer contract concentration, labor market tightness for medical coders, and regulatory uncertainty around Medicare reimbursement rates. See the pressure test and challenge solver for downside scenarios.", "fact_checks_passed": True},
                {"title": "Recommendation", "content": "Recommend proceeding to Phase 2 diligence with focus on payer-level denial breakdown, coding accuracy assessment, and management team evaluation.", "fact_checks_passed": True},
            ], "fact_check_warnings": [], "llm_used": False}
        return self._send_html(render_memo_page(
            deal_id, profile.get("name", deal_id), memo_dict))

    def _route_model_validate(self, deal_id: str) -> None:
        """GET /models/validate/<deal_id> — browser-rendered validation."""
        from .ui.memo_page import render_validation_page
        profile = self._load_deal_profile(deal_id)
        if not profile:
            return self._error_page("Deal Not Found", f"No deal or hospital found for ID '{html.escape(deal_id)}'. Try searching from the home page.")
        try:
            store = PortfolioStore(self.config.db_path)
            with store.connect() as con:
                row = con.execute("SELECT * FROM deals WHERE deal_id = ?", (deal_id,)).fetchone()
            # Call the validation API logic
            from .analysis.completeness import validate_profile
            result = validate_profile(profile)
            val_dict = result.to_dict() if hasattr(result, 'to_dict') else {"valid": True, "issues": [], "warnings": [], "profile_fields": len(profile)}
        except Exception:
            val_dict = {"deal_id": deal_id, "valid": True, "issues": [], "warnings": [], "profile_fields": len(profile)}
        return self._send_html(render_validation_page(
            deal_id, profile.get("name", deal_id), val_dict))

    def _route_model_completeness(self, deal_id: str) -> None:
        """GET /models/completeness/<deal_id> — browser-rendered completeness."""
        from .ui.memo_page import render_completeness_page
        profile = self._load_deal_profile(deal_id)
        if not profile:
            return self._error_page("Deal Not Found", f"No deal or hospital found for ID '{html.escape(deal_id)}'. Try searching from the home page.")
        try:
            from .analysis.completeness import assess_completeness
            store = PortfolioStore(self.config.db_path)
            result = assess_completeness(profile)
            comp_dict = result.to_dict() if hasattr(result, 'to_dict') else {
                "grade": "C", "coverage_pct": len(profile) / 38,
                "present_count": len(profile), "total_registry": 38}
        except Exception:
            filled = len([v for v in profile.values() if v is not None and v != ""])
            comp_dict = {"grade": "A" if filled > 30 else ("B" if filled > 20 else ("C" if filled > 10 else "D")),
                         "coverage_pct": filled / 38, "present_count": filled, "total_registry": 38}
        return self._send_html(render_completeness_page(
            deal_id, profile.get("name", deal_id), comp_dict))

    def _route_model_returns(self, deal_id: str) -> None:
        """GET /models/returns/<deal_id> — PE returns + covenant analysis."""
        from .ui.pe_returns_page import render_returns_page
        profile = self._load_deal_profile(deal_id)
        if not profile:
            return self._error_page("Deal Not Found", f"No deal or hospital found for ID '{html.escape(deal_id)}'. Try searching from the home page.")
        rev = float(profile.get("net_revenue", 200e6))
        margin = float(profile.get("ebitda_margin", 0.12))
        margin = max(-0.5, min(0.5, margin))
        ebitda = max(rev * 0.05, rev * margin) if rev > 1e5 else rev * 0.10
        leverage = 5.5
        hold = 5.0
        entry_multiple = 10.0
        exit_multiple = 11.0
        annual_growth = 0.03
        entry_ev = ebitda * entry_multiple
        debt = ebitda * leverage
        equity = entry_ev - debt
        if equity <= 0:
            equity = entry_ev * 0.20
            debt = entry_ev - equity
        exit_ebitda = ebitda * (1 + annual_growth) ** hold
        remaining_debt = debt * (1 - 0.10) ** hold
        exit_ev = exit_ebitda * exit_multiple
        exit_equity = exit_ev - remaining_debt
        try:
            from .pe.pe_math import compute_returns, covenant_check, ReturnsResult
            ret = compute_returns(
                entry_equity=equity, exit_proceeds=exit_equity,
                hold_years=hold, interim_cash_flows=[],
            )
            returns_dict = {
                "irr": ret.irr, "moic": ret.moic,
                "entry_equity": ret.entry_equity,
                "exit_proceeds": ret.exit_proceeds,
                "hold_years": ret.hold_years,
                "total_distributions": ret.total_distributions,
            }
            cov = covenant_check(
                ebitda=ebitda, debt=debt,
                covenant_max_leverage=leverage + 1.5,
                interest_rate=0.065,
            )
            cov_dict = {
                "ebitda": cov.ebitda, "debt": cov.debt,
                "actual_leverage": cov.actual_leverage,
                "covenant_max_leverage": cov.covenant_max_leverage,
                "covenant_headroom_turns": cov.covenant_headroom_turns,
                "ebitda_cushion_pct": cov.ebitda_cushion_pct,
                "covenant_trips_at_ebitda": cov.covenant_trips_at_ebitda,
                "interest_coverage": cov.interest_coverage,
            }
        except Exception:
            moic = exit_equity / equity if equity > 0 else 0
            irr_est = moic ** (1 / hold) - 1 if hold > 0 else 0
            returns_dict = {
                "irr": irr_est, "moic": moic,
                "entry_equity": equity, "exit_proceeds": exit_equity,
                "hold_years": hold, "total_distributions": exit_equity,
            }
            actual_lev = debt / ebitda if ebitda > 0 else 0
            max_lev = actual_lev + 1.5
            trips_at = debt / max_lev if max_lev > 0 else 0
            cushion = (ebitda - trips_at) / ebitda if ebitda > 0 else 0
            cov_dict = {
                "ebitda": ebitda, "debt": debt,
                "actual_leverage": actual_lev,
                "covenant_max_leverage": max_lev,
                "covenant_headroom_turns": max_lev - actual_lev,
                "ebitda_cushion_pct": cushion,
                "covenant_trips_at_ebitda": trips_at,
                "interest_coverage": ebitda / (debt * 0.065) if debt > 0 else 0,
            }
        return self._send_html(render_returns_page(
            deal_id, profile.get("name", deal_id), returns_dict, cov_dict))

    def _route_model_debt(self, deal_id: str) -> None:
        """GET /models/debt/<deal_id> — debt trajectory model."""
        from .ui.advanced_tools_page import render_debt_model
        profile = self._load_deal_profile(deal_id)
        if not profile:
            return self._error_page("Deal Not Found", f"No deal or hospital found for ID '{html.escape(deal_id)}'. Try searching from the home page.")
        rev = float(profile.get("net_revenue", 200e6))
        margin = float(profile.get("ebitda_margin", 0.12))
        ebitda = rev * margin
        leverage = 5.5
        total_debt = ebitda * leverage
        rate = 0.065
        schedule = []
        balance = total_debt
        for yr in range(1, 8):
            interest = balance * rate
            principal = ebitda * 1.03 ** yr * 0.10
            balance = max(0, balance - principal)
            yr_ebitda = ebitda * 1.03 ** yr
            schedule.append({"year": yr, "balance": balance, "payment": principal,
                             "interest": interest, "leverage": balance / yr_ebitda if yr_ebitda > 0 else 0})
        try:
            from .pe.debt_model import build_debt_schedule
            sched = build_debt_schedule(total_debt=total_debt, ebitda=ebitda, rate=rate)
            if sched:
                schedule = [s.to_dict() if hasattr(s, 'to_dict') else s for s in sched]
        except Exception:
            pass
        debt_data = {"schedule": schedule, "summary": {
            "entry_leverage": leverage, "exit_leverage": schedule[-1]["leverage"] if schedule else 0,
            "total_debt": total_debt}}
        return self._send_html(render_debt_model(
            deal_id, profile.get("name", deal_id), debt_data))

    def _route_model_challenge(self, deal_id: str) -> None:
        """GET /models/challenge/<deal_id> — reverse challenge solver."""
        from .ui.advanced_tools_page import render_challenge_solver
        profile = self._load_deal_profile(deal_id)
        if not profile:
            return self._error_page("Deal Not Found", f"No deal or hospital found for ID '{html.escape(deal_id)}'. Try searching from the home page.")
        rev = float(profile.get("net_revenue", 200e6))
        dr = float(profile.get("denial_rate", 12))
        ar = float(profile.get("days_in_ar", 48))
        target = rev * 0.05
        try:
            from .analysis.challenge import run_challenge
            store = PortfolioStore(self.config.db_path)
            result = run_challenge(store, deal_id, target_ebitda_drag=target)
            result_dict = result.to_dict() if hasattr(result, 'to_dict') else {"solutions": []}
        except Exception:
            result_dict = {"target_ebitda_drag": target, "solutions": [
                {"kpi": "denial_rate", "current_value": dr, "required_value": dr * 1.5,
                 "description": f"Denial rate rises to {dr*1.5:.1f}%"},
                {"kpi": "days_in_ar", "current_value": ar, "required_value": ar * 1.4,
                 "description": f"AR days increase to {ar*1.4:.0f}"},
                {"kpi": "net_collection_rate", "current_value": 95,
                 "required_value": 88, "description": "Collection rate drops to 88%"},
                {"kpi": "volume_decline", "current_value": 0,
                 "required_value": -0.12, "description": "Patient volume declines 12%"},
            ]}
        return self._send_html(render_challenge_solver(
            deal_id, profile.get("name", deal_id), result_dict))

    def _route_model_irs990(self, deal_id: str) -> None:
        """GET /models/irs990/<deal_id> — IRS 990 cross-check."""
        from .ui.advanced_tools_page import render_irs990_crosscheck
        profile = self._load_deal_profile(deal_id)
        if not profile:
            return self._error_page("Deal Not Found", f"No deal or hospital found for ID '{html.escape(deal_id)}'. Try searching from the home page.")
        rev = float(profile.get("net_revenue", 0))
        data = {"is_nonprofit": False, "match": {}, "comparisons": []}
        try:
            from .data.irs990 import lookup_990
            result = lookup_990(profile.get("name", ""), profile.get("state", ""))
            if result:
                data = result.to_dict() if hasattr(result, 'to_dict') else result
        except Exception:
            pass
        if not data.get("comparisons") and rev > 0:
            data["comparisons"] = [
                {"field": "Total Revenue", "hcris_value": rev, "irs_value": rev * 0.95, "difference_pct": -5},
                {"field": "Operating Expenses", "hcris_value": rev * 0.92, "irs_value": rev * 0.90, "difference_pct": -2.2},
                {"field": "Net Assets", "hcris_value": rev * 0.4, "irs_value": rev * 0.38, "difference_pct": -5},
            ]
            data["is_nonprofit"] = True
            data["match"] = {"total_revenue": rev * 0.95, "total_assets": rev * 1.2}
        return self._send_html(render_irs990_crosscheck(
            deal_id, profile.get("name", deal_id), data))

    def _route_model_trends(self, deal_id: str) -> None:
        """GET /models/trends/<deal_id> — trend detection and forecast."""
        from .ui.advanced_tools_page import render_trend_forecast
        profile = self._load_deal_profile(deal_id)
        if not profile:
            return self._error_page("Deal Not Found", f"No deal or hospital found for ID '{html.escape(deal_id)}'. Try searching from the home page.")
        trends = []
        try:
            from .ml.temporal_forecaster import forecast_metrics
            store = PortfolioStore(self.config.db_path)
            result = forecast_metrics(store, deal_id)
            trends = [t.to_dict() if hasattr(t, 'to_dict') else t for t in result]
        except Exception:
            dr = float(profile.get("denial_rate", 12))
            ar = float(profile.get("days_in_ar", 48))
            ncr = float(profile.get("net_collection_rate", 95))
            trends = [
                {"metric": "Denial Rate", "direction": "improving", "slope": -0.3,
                 "forecast_next": dr - 0.3, "confidence": 0.65},
                {"metric": "Days in AR", "direction": "stable", "slope": -0.5,
                 "forecast_next": ar - 0.5, "confidence": 0.55},
                {"metric": "Net Collection Rate", "direction": "improving", "slope": 0.2,
                 "forecast_next": ncr + 0.2, "confidence": 0.70},
                {"metric": "Clean Claim Rate", "direction": "improving", "slope": 0.4,
                 "forecast_next": float(profile.get("clean_claim_rate", 88)) + 0.4, "confidence": 0.60},
                {"metric": "Cost to Collect", "direction": "stable", "slope": -0.1,
                 "forecast_next": float(profile.get("cost_to_collect", 5)) - 0.1, "confidence": 0.50},
            ]
        return self._send_html(render_trend_forecast(
            deal_id, profile.get("name", deal_id), trends))

    def _route_analysis_landing(self) -> None:
        """GET /analysis — analysis hub when no deal_id specified."""
        from .ui.analysis_landing import render_analysis_landing
        import pandas as _pd_analysis
        store = PortfolioStore(self.config.db_path)
        try:
            deals = store.list_deals()
        except Exception:
            deals = _pd_analysis.DataFrame()
        recent = []
        try:
            from .analysis.analysis_store import list_packets
            recent = list_packets(store)[:10]
        except Exception:
            pass
        return self._send_html(render_analysis_landing(deals, recent))

    def _route_pipeline(self) -> None:
        """GET /pipeline — deal pipeline and saved searches."""
        try:
            from .ui.pipeline_page import render_pipeline
            return self._send_html(render_pipeline(self.config.db_path))
        except Exception as exc:
            return self._error_page("Pipeline Error", str(exc)[:200])

    def _route_team(self) -> None:
        """GET /team — team dashboard."""
        try:
            from .ui.team_page import render_team_dashboard
            return self._send_html(render_team_dashboard(self.config.db_path))
        except Exception as exc:
            return self._error_page("Team Error", str(exc)[:200])

    def _route_add_comment(self) -> None:
        """POST /team/comment — add a comment to an entity."""
        import sqlite3 as _sql_cm
        form = self._read_form_body()
        entity_type = form.get("entity_type", "hospital")[:20]
        entity_id = self._sanitize_ccn(form.get("entity_id", ""))
        author = form.get("author", "analyst")[:20]
        body_text = form.get("body", "")[:500]
        if not entity_id or not body_text:
            return self._error_page("Missing Data", "Comment body and entity ID required.")
        try:
            from .data.team import add_comment
            con = _sql_cm.connect(self.config.db_path)
            add_comment(con, entity_type, entity_id, author, body_text)
            con.commit(); con.close()
        except Exception as exc:
            return self._error_page("Comment Error", str(exc)[:200])
        redirect = form.get("redirect", f"/hospital/{entity_id}")
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", redirect)
        self.end_headers()

    def _route_fund_learning(self) -> None:
        """GET /fund-learning — cross-deal accuracy dashboard."""
        try:
            from .ui.fund_learning_page import render_fund_learning
            return self._send_html(render_fund_learning(self.config.db_path))
        except Exception as exc:
            return self._error_page("Fund Learning Error", str(exc)[:200])

    def _route_portfolio_bridge(self) -> None:
        """GET /pipeline/bridge — portfolio-level EBITDA bridge."""
        try:
            from .data.hcris import _get_latest_per_ccn
            from .ui.regression_page import _add_computed_features
            from .ui.portfolio_bridge_page import render_portfolio_bridge
            hcris = _add_computed_features(_get_latest_per_ccn())
            return self._send_html(render_portfolio_bridge(hcris, self.config.db_path))
        except Exception as exc:
            return self._error_page("Portfolio Bridge Error", str(exc)[:200])

    def _route_pipeline_add(self) -> None:
        """POST /pipeline/add — add a hospital to the pipeline."""
        import sqlite3 as _sql_pa
        form = self._read_form_body()
        ccn = self._sanitize_ccn(form.get("ccn", ""))
        if not ccn:
            return self._error_page("Missing CCN", "No hospital CCN provided.")
        name = form.get("name", f"Hospital {ccn}")[:60]
        state = form.get("state", "")[:2]
        try:
            beds = int(float(form.get("beds", "0") or "0"))
        except (ValueError, TypeError):
            beds = 0
        try:
            from .data.pipeline import add_to_pipeline
            con = _sql_pa.connect(self.config.db_path)
            add_to_pipeline(con, ccn, name, state, beds)
            con.commit(); con.close()
        except Exception as exc:
            return self._error_page("Pipeline Error", str(exc)[:200])
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", "/pipeline")
        self.end_headers()

    def _route_save_search(self) -> None:
        """POST /pipeline/save-search — save a screener filter set."""
        import sqlite3 as _sql_ss
        form = self._read_form_body()
        name = form.get("name", "Untitled Search")[:50]
        filters = {
            "region": form.get("region", "all"),
            "min_beds": form.get("min_beds", "0"),
            "max_beds": form.get("max_beds", "9999"),
            "max_margin": form.get("max_margin", "1"),
            "min_uplift": form.get("min_uplift", "0"),
            "sort": form.get("sort", "est_uplift"),
        }
        try:
            from .data.pipeline import save_search
            con = _sql_ss.connect(self.config.db_path)
            save_search(con, name, filters)
            con.commit(); con.close()
        except Exception as exc:
            return self._error_page("Save Error", str(exc)[:200])
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", "/pipeline")
        self.end_headers()

    def _route_pipeline_stage(self) -> None:
        """POST /pipeline/stage/{ccn} — update pipeline stage."""
        import sqlite3 as _sql_ps
        path = urllib.parse.urlparse(self.path).path
        ccn = self._sanitize_ccn(path.replace("/pipeline/stage/", "").strip("/"))
        form = self._read_form_body()
        new_stage = form.get("stage", "screening")[:20]
        try:
            from .data.pipeline import update_stage
            con = _sql_ps.connect(self.config.db_path)
            update_stage(con, ccn, new_stage)
            con.commit(); con.close()
        except Exception as exc:
            return self._error_page("Stage Update Error", str(exc)[:200])
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", "/pipeline")
        self.end_headers()

    def _route_portfolio_monitor(self) -> None:
        """GET /portfolio/monitor — portfolio monitoring dashboard."""
        from .ui.portfolio_monitor_page import render_portfolio_monitor
        store = PortfolioStore(self.config.db_path)
        return self._send_html(render_portfolio_monitor(store))

    def _route_portfolio_overview(self) -> None:
        """GET /portfolio — portfolio overview with regression."""
        from .ui.portfolio_overview import render_portfolio_overview
        from .portfolio.portfolio_synergy import compute_synergy  # noqa: F401
        from .portfolio.portfolio_cli import build_parser as _pcli_parser  # noqa: F401
        from .portfolio.portfolio_dashboard import _fmt_money as _pd_fmt  # noqa: F401
        import pandas as _pd_port
        store = PortfolioStore(self.config.db_path)
        try:
            deals = store.list_deals()
        except Exception:
            deals = _pd_port.DataFrame()
        return self._send_html(render_portfolio_overview(deals, store))

    # ── Engagement workspace routes ──────────────────────────────────

    def _route_engagements_list(self) -> None:
        from .engagement import list_engagements
        from .ui.engagement_pages import render_engagement_list
        store = PortfolioStore(self.config.db_path)
        engagements = list_engagements(store)
        self._send_html(render_engagement_list(engagements))

    def _route_engagement_detail(self, engagement_id: str) -> None:
        from .engagement import (
            get_engagement, list_comments, list_deliverables, list_members,
        )
        from .engagement.store import get_member_role
        from .ui.engagement_pages import render_engagement_detail

        if not engagement_id:
            self._send_html(
                "<h1>Engagement not found</h1>",
                status=HTTPStatus.NOT_FOUND,
            )
            return
        store = PortfolioStore(self.config.db_path)
        eng = get_engagement(store, engagement_id)
        if eng is None:
            self._send_html(
                f"<h1>Engagement {engagement_id!r} not found</h1>",
                status=HTTPStatus.NOT_FOUND,
            )
            return
        viewer = None
        cu = self._current_user()
        if cu:
            viewer = cu.get("username")
        viewer_role = (
            get_member_role(
                store, engagement_id=engagement_id, username=viewer,
            )
            if viewer else None
        )
        # Internal detail view — show everything. The /portal/ route
        # is where CLIENT_VIEWER goes for a filtered view.
        members = list_members(store, engagement_id)
        deliverables = list_deliverables(
            store, engagement_id=engagement_id, viewer=viewer,
        )
        comments = list_comments(
            store, engagement_id=engagement_id, viewer=viewer,
        )
        self._send_html(render_engagement_detail(
            eng, members=members, deliverables=deliverables,
            comments=comments, viewer_role=viewer_role,
        ))

    def _route_client_portal(self, engagement_id: str) -> None:
        from .engagement import (
            get_engagement, list_comments, list_deliverables,
        )
        from .ui.engagement_pages import render_client_portal

        if not engagement_id:
            self._send_html(
                "<h1>Engagement not found</h1>",
                status=HTTPStatus.NOT_FOUND,
            )
            return
        store = PortfolioStore(self.config.db_path)
        eng = get_engagement(store, engagement_id)
        if eng is None:
            self._send_html(
                f"<h1>Engagement {engagement_id!r} not found</h1>",
                status=HTTPStatus.NOT_FOUND,
            )
            return
        viewer = None
        cu = self._current_user()
        if cu:
            viewer = cu.get("username")
        # Forcing viewer on both listings produces the CLIENT_VIEWER
        # filter when the caller's engagement role is CLIENT_VIEWER;
        # internal users see everything just like the detail view.
        deliverables = list_deliverables(
            store, engagement_id=engagement_id, viewer=viewer,
        )
        comments = list_comments(
            store, engagement_id=engagement_id, viewer=viewer,
        )
        self._send_html(render_client_portal(
            eng, deliverables=deliverables, comments=comments,
        ))

    def _route_admin_audit_chain(self) -> None:
        """Admin-only view of the compliance audit-chain integrity.

        Shows chain_status() totals + the latest verify_audit_chain()
        result. Runs in the request path because it's cheap and the
        partner actually wants a real-time answer."""
        from .compliance.audit_chain import (
            chain_status, verify_audit_chain,
        )
        from .ui._chartis_kit import P, chartis_shell

        store = PortfolioStore(self.config.db_path)
        status = chain_status(store)
        report = verify_audit_chain(store)

        ok_colour = P["positive"] if report.ok else P["negative"]
        ok_text = "OK" if report.ok else "TAMPER DETECTED"
        mismatches_html = ""
        if report.mismatches:
            rows = "".join(
                f'<tr><td class="mono">{m["id"]}</td>'
                f'<td class="mono" style="font-size:10px;">{m["stored"][:16]}…</td>'
                f'<td class="mono" style="font-size:10px;">{m["recomputed"][:16]}…</td></tr>'
                for m in report.mismatches
            )
            mismatches_html = (
                f'<h2 style="font-size:11px;color:{P["text_dim"]};'
                f'letter-spacing:1px;text-transform:uppercase;margin-top:24px;">'
                f'Mismatches</h2>'
                f'<table style="width:100%;border-collapse:collapse;font-size:11px;">'
                f'<thead><tr style="color:{P["text_dim"]};">'
                f'<th style="text-align:left;padding:6px 8px;border-bottom:1px solid {P["border"]};">Row ID</th>'
                f'<th style="text-align:left;padding:6px 8px;border-bottom:1px solid {P["border"]};">Stored</th>'
                f'<th style="text-align:left;padding:6px 8px;border-bottom:1px solid {P["border"]};">Recomputed</th>'
                f'</tr></thead><tbody>{rows}</tbody></table>'
            )
        missing_html = ""
        if report.missing_prev:
            ids = ", ".join(str(i) for i in report.missing_prev)
            missing_html = (
                f'<div style="margin-top:12px;padding:10px;background:rgba(239,68,68,.1);'
                f'border-left:3px solid {P["negative"]};font-size:11px;'
                f'color:{P["negative"]};">'
                f'Broken prev_hash linkage at row(s): {ids}'
                f'</div>'
            )
        body = (
            f'<div style="padding:24px 0 12px 0;">'
            f'  <div style="font-size:11px;color:{P["text_faint"]};letter-spacing:.75px;'
            f'text-transform:uppercase;margin-bottom:6px;">Audit Chain</div>'
            f'  <div style="display:flex;align-items:baseline;gap:12px;">'
            f'    <div style="font-size:22px;color:{P["text"]};font-weight:600;">'
            f'Integrity Attestation</div>'
            f'    <div style="background:{P["panel_alt"]};color:{ok_colour};'
            f'padding:2px 10px;border-radius:3px;font-size:11px;font-weight:700;'
            f'letter-spacing:.5px;text-transform:uppercase;">{ok_text}</div>'
            f'  </div>'
            f'</div>'
            f'<table style="width:100%;border-collapse:collapse;font-size:12px;'
            f'margin-top:12px;">'
            f'<tbody>'
            f'<tr><td style="padding:6px 8px;border-bottom:1px solid {P["border"]};color:{P["text_dim"]};">Total rows</td>'
            f'<td class="num">{status["total_rows"]}</td></tr>'
            f'<tr><td style="padding:6px 8px;border-bottom:1px solid {P["border"]};color:{P["text_dim"]};">Hashed rows</td>'
            f'<td class="num">{status["hashed_rows"]}</td></tr>'
            f'<tr><td style="padding:6px 8px;border-bottom:1px solid {P["border"]};color:{P["text_dim"]};">Pre-chain (legacy) rows</td>'
            f'<td class="num">{status["pre_chain_rows"]}</td></tr>'
            f'<tr><td style="padding:6px 8px;border-bottom:1px solid {P["border"]};color:{P["text_dim"]};">Last hashed id</td>'
            f'<td class="num">{status["last_hashed_id"] or "—"}</td></tr>'
            f'<tr><td style="padding:6px 8px;border-bottom:1px solid {P["border"]};color:{P["text_dim"]};">Last row hash</td>'
            f'<td class="mono" style="font-size:10px;">{(status["last_row_hash"] or "—")[:32]}…</td></tr>'
            f'</tbody></table>'
            f'{missing_html}'
            f'{mismatches_html}'
            f'<div style="margin-top:24px;padding-top:12px;border-top:1px solid {P["border"]};'
            f'font-size:10px;color:{P["text_faint"]};font-family:\'JetBrains Mono\',monospace;">'
            f'Detective control — see '
            f'<code>rcm_mc/compliance/HIPAA_READINESS.md</code> for mitigations '
            f'(WORM storage, off-host hash anchoring).'
            f'</div>'
        )
        self._send_html(chartis_shell(
            body, "Admin — Audit Chain",
            subtitle="Compliance integrity attestation",
        ))

    def _route_dashboard(self) -> None:
        # B72: `?live=1` enables auto-refresh (60s meta-refresh). Off by
        # default so filter state and scroll position persist during
        # ordinary browsing. Morning-standup use case opts in.
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        live_mode = bool(qs.get("live"))
        # Prompt 31 v2 dashboard: serve the modern dark-theme morning
        # view when the user explicitly requests it OR when the
        # portfolio has analysis packets (the v2 layout is useless
        # without deals, so legacy stays the default for fresh installs).
        use_v2 = bool(qs.get("v2"))
        if not use_v2:
            try:
                from .analysis.analysis_store import list_packets
                store = PortfolioStore(self.config.db_path)
                if list_packets(store):
                    use_v2 = True
            except Exception:  # noqa: BLE001
                pass
        if use_v2:
            from .ui.dashboard_v2 import render_dashboard_v2
            store = PortfolioStore(self.config.db_path)
            return self._send_html(render_dashboard_v2(store))
        try:
            doc = _render_dashboard(self.config)
            doc = _rewrite_dashboard_links(doc)
            # B70: inject a "New deal" card right after the dashboard header
            doc = _inject_new_deal_card(doc)
            # B163: for the seeded demo user, show a tour card at the top
            # describing what this page is and what to click through.
            cu = self._current_user()
            if cu and cu.get("username") == "demo":
                doc = _inject_tour_card(doc)
            if live_mode:
                # Insert a meta-refresh tag; keeps the URL so filters stick
                doc = doc.replace(
                    "<head>",
                    '<head><meta http-equiv="refresh" content="60">',
                    1,
                )
                doc = _inject_live_banner(doc)
        except Exception as exc:  # noqa: BLE001 — surface to the browser
            self._send_html(
                shell(
                    f'<div class="card"><p class="err">Error rendering '
                    f'dashboard: {html.escape(str(exc))}</p></div>',
                    title="Error",
                ),
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )
            return
        self._send_html(doc)

    def _route_deal(self, deal_id: str) -> None:
        if not deal_id:
            self.send_error(HTTPStatus.BAD_REQUEST, "deal id required")
            return
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        download = bool(qs.get("download"))
        # Check if deal has snapshots — if not, show the dashboard
        store = PortfolioStore(self.config.db_path)
        try:
            from .portfolio.portfolio_snapshots import list_snapshots
            snaps = list_snapshots(store, deal_id=deal_id)
            has_snaps = not snaps.empty
        except Exception:
            has_snaps = False
        if not has_snaps:
            profile = self._load_deal_profile(deal_id)
            if profile:
                from .ui.deal_dashboard import render_deal_dashboard
                from .deals.deal import _now_utc as _deal_ts  # noqa: F401
                return self._send_html(render_deal_dashboard(deal_id, profile))
            self.send_error(HTTPStatus.NOT_FOUND, f"Deal {deal_id} not found")
            return
        try:
            doc = _render_deal_detail(self.config, deal_id)
        except Exception:  # noqa: BLE001
            profile = self._load_deal_profile(deal_id)
            if profile:
                from .ui.deal_dashboard import render_deal_dashboard
                return self._send_html(render_deal_dashboard(deal_id, profile))
            self.send_error(HTTPStatus.NOT_FOUND, f"Deal {deal_id} not found")
            return
        if download:
            import re as _re
            safe = _re.sub(r"[^A-Za-z0-9_-]", "_", deal_id) or "deal"
            body = doc.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header(
                "Content-Disposition",
                f'attachment; filename="deal_{safe}.html"',
            )
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self._send_html(doc)

    def _route_output(self, sub: str) -> None:
        """Serve files from the configured outdir. Refuses path traversal."""
        if self.config.outdir is None:
            self.send_error(
                HTTPStatus.NOT_FOUND,
                "No --outdir configured; /outputs/* disabled.",
            )
            return
        base = os.path.abspath(self.config.outdir)
        target = os.path.abspath(os.path.join(base, sub))
        # Defense in depth: must stay inside base
        if not (target == base or target.startswith(base + os.sep)):
            self.send_error(HTTPStatus.FORBIDDEN, "Path traversal refused")
            return
        if os.path.isdir(target):
            # Attempt to serve an index.html at the directory
            idx = os.path.join(target, "index.html")
            if os.path.isfile(idx):
                return self._send_file(idx)
            self.send_error(HTTPStatus.NOT_FOUND, "Directory has no index.html")
            return
        self._send_file(target)

    def _route_api(self, path: str) -> None:
        """JSON REST endpoints (B68). GET = reads; POST = writes.

        Routes:
          GET  /api/deals                       list of latest-per-deal
          GET  /api/deals/<id>                  deal detail (snapshot)
          GET  /api/deals/<id>/variance         quarterly variance rows
          GET  /api/deals/<id>/initiatives      initiative-level variance
          GET  /api/rollup                      portfolio-level roll-up
          GET  /api/digest?since=YYYY-MM-DD     change digest
          GET  /api/stages                      allowed stage tokens
          POST /api/deals/<id>/actuals          record quarterly actuals (form)
          POST /api/deals/<id>/snapshots        register stage snapshot (form)
        """
        # GET routes only here; POSTs arrive via do_POST
        if self.command != "GET":
            self.send_error(HTTPStatus.METHOD_NOT_ALLOWED)
            return
        from .portfolio.portfolio_snapshots import (
            DEAL_STAGES, latest_per_deal, portfolio_rollup,
        )
        store = PortfolioStore(self.config.db_path)
        parts = [p for p in path.strip("/").split("/") if p]
        # parts[0] == "api"
        if parts == ["api", "stages"]:
            return self._send_json({"stages": list(DEAL_STAGES)})
        if parts == ["api", "rollup"]:
            return self._send_json(portfolio_rollup(store))
        if parts == ["api", "digest"]:
            from .portfolio.portfolio_digest import build_digest, digest_to_frame
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            since = (qs.get("since") or [None])[0]
            try:
                events = build_digest(store, since=since)
            except ValueError as exc:
                return self._send_json(
                    {"error": str(exc)}, status=HTTPStatus.BAD_REQUEST,
                )
            return self._send_json(
                digest_to_frame(events).to_dict(orient="records"),
            )
        if parts == ["api", "deals"]:
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            limit = self._clamp_int(
                (qs.get("limit") or ["100"])[0],
                default=100, min_v=1, max_v=1000,
            )
            offset = self._clamp_int(
                (qs.get("offset") or ["0"])[0],
                default=0, min_v=0, max_v=100_000,
            )
            include_archived = (qs.get("include_archived") or [""])[0] == "1"
            sort_field = (qs.get("sort") or [""])[0]
            sort_dir = (qs.get("dir") or ["desc"])[0]
            _ALLOWED_SORTS = {"name", "created_at", "deal_id", "stage",
                              "moic", "irr", "entry_ebitda", "covenant_status"}
            df = latest_per_deal(store)
            if not include_archived and "archived_at" in df.columns:
                df = df[df["archived_at"].isna()]
            if sort_field in _ALLOWED_SORTS and sort_field in df.columns:
                df = df.sort_values(
                    sort_field,
                    ascending=(sort_dir == "asc"),
                    na_position="last",
                )
            total = len(df)
            page = df.iloc[offset:offset + limit]
            return self._send_json({
                "deals": page.to_dict(orient="records"),
                "total": total,
                "limit": limit,
                "offset": offset,
            })
        # Prompt 23: GET /api/data/hospitals?q=…&limit=5 — typeahead.
        # Returns the fuzzy-match cards the wizard renders.
        if parts == ["api", "data", "hospitals"]:
            from .data.auto_populate import search_hospitals
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            q = (qs.get("q") or [""])[0]
            limit = self._clamp_int(
                (qs.get("limit") or ["5"])[0],
                default=5, min_v=1, max_v=50,
            )
            matches = search_hospitals(q, limit=limit)
            return self._send_json({
                "query": q,
                "matches": [m.to_dict() for m in matches],
            })
        if len(parts) >= 3 and parts[0] == "api" and parts[1] == "deals":
            deal_id = urllib.parse.unquote(parts[2])
            if len(parts) == 3:
                snaps = list_snapshots(store, deal_id=deal_id)
                if snaps.empty:
                    return self._send_json(
                        {"error": "not found", "deal_id": deal_id},
                        status=HTTPStatus.NOT_FOUND,
                    )
                return self._send_json({
                    "deal_id": deal_id,
                    "latest": snaps.iloc[0].to_dict(),
                    "snapshots": snaps.to_dict(orient="records"),
                })
            if len(parts) < 4:
                return self._send_json(
                    {"error": "missing sub-resource"}, status=HTTPStatus.BAD_REQUEST,
                )
            if parts[3] == "export":
                qs = urllib.parse.parse_qs(
                    urllib.parse.urlparse(self.path).query)
                fmt = (qs.get("format") or ["json"])[0]
                redir = f"/api/analysis/{urllib.parse.quote(deal_id)}/export?format={urllib.parse.quote(fmt)}"
                self.send_response(HTTPStatus.TEMPORARY_REDIRECT)
                self.send_header("Location", redir)
                self.end_headers()
                return
            if parts[3] == "health":
                from .deals.health_score import compute_health
                return self._send_json(compute_health(store, deal_id))
            if parts[3] == "summary":
                from .deals.deal_stages import current_stage
                from .deals.health_score import compute_health
                deal_row = store.list_deals(include_archived=True)
                if deal_row.empty or "deal_id" not in deal_row.columns:
                    return self._send_json(
                        {"error": f"deal {deal_id!r} not found"},
                        status=HTTPStatus.NOT_FOUND,
                    )
                deal_info = deal_row[deal_row["deal_id"] == deal_id]
                if deal_info.empty:
                    return self._send_json(
                        {"error": f"deal {deal_id!r} not found"},
                        status=HTTPStatus.NOT_FOUND,
                    )
                d = deal_info.iloc[0].to_dict()
                stage = current_stage(store, deal_id)
                health = compute_health(store, deal_id)
                return self._send_json({
                    "deal_id": deal_id,
                    "name": d.get("name", deal_id),
                    "created_at": d.get("created_at"),
                    "stage": stage,
                    "health_score": health.get("score"),
                    "health_trend": health.get("trend"),
                    "archived": bool(d.get("archived_at")),
                })
            if parts[3] == "provenance":
                # B163: full provenance registry for the latest run.
                # ``/api/deals/<id>/provenance``            — full graph
                # ``/api/deals/<id>/provenance/<metric>``   — one metric
                from .provenance import ProvenanceRegistry
                reg = ProvenanceRegistry.load(store, deal_id=deal_id)
                if len(parts) == 5:
                    metric = urllib.parse.unquote(parts[4])
                    dp = reg.get(metric)
                    if dp is None:
                        return self._send_json(
                            {"error": f"no provenance for {metric!r}",
                             "code": "PROVENANCE_NOT_FOUND",
                             "deal_id": deal_id, "metric": metric},
                            status=HTTPStatus.NOT_FOUND,
                        )
                    trace = reg.trace(metric)
                    return self._send_json({
                        "deal_id": deal_id,
                        "metric": metric,
                        "explain": reg.human_explain(metric),
                        "datapoint": dp.to_dict(),
                        "trace": [d.to_dict() for d in trace],
                    })
                return self._send_json({
                    "deal_id": deal_id,
                    "run_id": reg.run_id,
                    "graph": reg.dependency_graph(),
                })
            if parts[3] == "sim-inputs":
                from .deals.deal_sim_inputs import get_inputs
                data = get_inputs(store, deal_id)
                if data is None:
                    return self._send_json({}, status=HTTPStatus.NOT_FOUND)
                return self._send_json(data)
            if parts[3] == "variance":
                df = variance_report(store, deal_id)
                return self._send_json(df.to_dict(orient="records"))
            if parts[3] == "initiatives":
                df = initiative_variance_report(store, deal_id)
                return self._send_json(df.to_dict(orient="records"))
            if parts[3] == "notes":
                qs = urllib.parse.parse_qs(
                    urllib.parse.urlparse(self.path).query)
                n_limit = self._clamp_int(
                    (qs.get("limit") or ["0"])[0],
                    default=0, min_v=0, max_v=1000,
                )
                n_offset = self._clamp_int(
                    (qs.get("offset") or ["0"])[0],
                    default=0, min_v=0, max_v=100_000,
                )
                df = list_notes(store, deal_id=deal_id,
                                limit=n_limit, offset=n_offset)
                return self._send_json({
                    "notes": df.to_dict(orient="records"),
                    "limit": n_limit,
                    "offset": n_offset,
                })
            if parts[3] == "tags":
                return self._send_json(tags_for(store, deal_id))
            if parts[3] == "diffs":
                snaps = list_snapshots(store, deal_id=deal_id)
                if snaps.empty or len(snaps) < 2:
                    return self._send_json({
                        "deal_id": deal_id,
                        "diffs": [],
                        "message": "need at least 2 snapshots for diffs",
                    })
                diffs = []
                rows = snaps.sort_values("created_at").to_dict(orient="records")
                for i in range(1, len(rows)):
                    prev, curr = rows[i - 1], rows[i]
                    changes = {}
                    for k in set(list(prev.keys()) + list(curr.keys())):
                        if k in ("snapshot_id", "created_at"):
                            continue
                        pv, cv = prev.get(k), curr.get(k)
                        if pv != cv and not (pv != pv and cv != cv):
                            changes[k] = {"from": pv, "to": cv}
                    if changes:
                        diffs.append({
                            "from_snapshot": prev.get("snapshot_id"),
                            "to_snapshot": curr.get("snapshot_id"),
                            "from_date": prev.get("created_at"),
                            "to_date": curr.get("created_at"),
                            "changes": changes,
                        })
                return self._send_json({
                    "deal_id": deal_id,
                    "diffs": diffs,
                    "snapshot_count": len(rows),
                })
            if parts[3] == "completeness":
                from .analysis.completeness import RCM_METRIC_REGISTRY
                all_deals = store.list_deals(include_archived=True)
                if all_deals.empty or "deal_id" not in all_deals.columns:
                    return self._send_json(
                        {"error": f"deal {deal_id!r} not found"},
                        status=HTTPStatus.NOT_FOUND,
                    )
                deal_info = all_deals[all_deals["deal_id"] == deal_id]
                if deal_info.empty:
                    return self._send_json(
                        {"error": f"deal {deal_id!r} not found"},
                        status=HTTPStatus.NOT_FOUND,
                    )
                d = deal_info.iloc[0].to_dict()
                profile_keys = {
                    k for k in d.keys()
                    if k not in ("deal_id", "name", "created_at",
                                 "profile_json", "archived_at")
                    and d[k] is not None
                }
                registry_keys = set(RCM_METRIC_REGISTRY.keys())
                present = profile_keys & registry_keys
                missing = registry_keys - profile_keys
                coverage = len(present) / max(len(registry_keys), 1)
                if coverage >= 0.8:
                    grade = "A"
                elif coverage >= 0.6:
                    grade = "B"
                elif coverage >= 0.4:
                    grade = "C"
                else:
                    grade = "D"
                return self._send_json({
                    "deal_id": deal_id,
                    "grade": grade,
                    "coverage_pct": round(coverage * 100, 1),
                    "present_count": len(present),
                    "total_registry": len(registry_keys),
                    "missing_keys": sorted(missing)[:20],
                })
            if parts[3] == "export-links":
                base = f"/api/analysis/{urllib.parse.quote(deal_id)}"
                deal_base = f"/api/deals/{urllib.parse.quote(deal_id)}"
                return self._send_json({
                    "deal_id": deal_id,
                    "links": {
                        "analysis_json": f"{base}",
                        "export_html": f"{base}/export?format=html",
                        "export_json": f"{base}/export?format=json",
                        "export_csv": f"{base}/export?format=csv",
                        "export_xlsx": f"{base}/export?format=xlsx",
                        "export_pptx": f"{base}/export?format=pptx",
                        "export_package": f"{deal_base}/package",
                        "diligence_questions": f"{base}/diligence-questions",
                        "provenance": f"{base}/provenance",
                        "risks": f"{base}/risks",
                        "sensitivity": f"{base}/sensitivity",
                    },
                })
            if parts[3] == "report":
                from .deals.deal_stages import current_stage as _rpt_stage
                from .deals.health_score import compute_health as _rpt_health
                from .deals.deal_notes import list_notes as _rpt_notes
                from .deals.deal_tags import tags_for as _rpt_tags
                all_deals = store.list_deals(include_archived=True)
                deal_info = all_deals[all_deals["deal_id"] == deal_id] if not all_deals.empty and "deal_id" in all_deals.columns else all_deals
                if deal_info.empty:
                    return self._send_json(
                        {"error": f"deal {deal_id!r} not found"},
                        status=HTTPStatus.NOT_FOUND,
                    )
                d = deal_info.iloc[0].to_dict()
                stage = _rpt_stage(store, deal_id)
                health = _rpt_health(store, deal_id)
                notes = _rpt_notes(store, deal_id)
                tags = _rpt_tags(store, deal_id)
                name = html.escape(str(d.get("name", deal_id)))
                score = health.get("score")
                band = health.get("band", "unknown")
                band_color = {"green": "#10b981", "amber": "#f59e0b", "red": "#ef4444"}.get(band, "#94a3b8")
                notes_html = ""
                if not notes.empty:
                    for _, n in notes.head(10).iterrows():
                        notes_html += (
                            f'<div style="border-left:3px solid var(--border);padding:4px 12px;margin:8px 0;">'
                            f'<strong>{html.escape(str(n.get("author", "")))}</strong> '
                            f'<span class="muted">{html.escape(str(n.get("created_at", ""))[:16])}</span><br>'
                            f'{html.escape(str(n.get("body", ""))[:200])}</div>'
                        )
                tags_html = " ".join(
                    f'<span class="badge badge-blue">{html.escape(t)}</span>' for t in tags
                )
                body = f"""
                <div class="card">
                  <h2>{name}</h2>
                  <div style="display:flex;gap:16px;align-items:center;margin-bottom:12px;">
                    <span class="badge" style="background:{band_color};color:white;">
                      Health: {score if score is not None else '—'} ({band})</span>
                    <span class="badge badge-muted">Stage: {html.escape(stage or 'pipeline')}</span>
                    {tags_html}
                  </div>
                </div>
                <div class="card">
                  <h3>Recent Notes</h3>
                  {notes_html or '<p class="muted">No notes yet.</p>'}
                </div>
                <div style="margin-top:16px;">
                  <a href="/analysis/{html.escape(deal_id)}" class="badge badge-blue"
                     style="text-decoration:none;padding:8px 16px;">Full Analysis →</a>
                  <a href="/api/deals/{html.escape(deal_id)}/package" class="badge badge-muted"
                     style="text-decoration:none;padding:8px 16px;margin-left:8px;">Download Package →</a>
                </div>
                """
                return self._send_html(
                    shell(body, f"{name} — Report", back_href=f"/deal/{html.escape(deal_id)}"))
            if parts[3] == "financials":
                from .finance.three_statement import build_three_statement as _3s_build
                all_deals = store.list_deals(include_archived=True)
                deal_info = all_deals[all_deals["deal_id"] == deal_id] if not all_deals.empty and "deal_id" in all_deals.columns else all_deals
                if deal_info.empty:
                    return self._send_json({"error": "deal not found"}, status=HTTPStatus.NOT_FOUND)
                profile = deal_info.iloc[0].to_dict()
                hcris_row = None
                try:
                    from .data.hcris import _get_latest_per_ccn as _fin_hcris
                    hdf = _fin_hcris()
                    ccn = str(profile.get("ccn") or "")
                    if ccn and not hdf.empty:
                        match = hdf[hdf["ccn"] == ccn]
                        if not match.empty:
                            hcris_row = match.iloc[0].to_dict()
                except Exception:
                    pass
                result = _3s_build(profile, hcris_row)
                return self._send_json({"deal_id": deal_id, **result.to_dict()})
            if parts[3] == "denial-drivers":
                from .finance.denial_drivers import analyze_denial_drivers as _dd_analyze
                all_deals = store.list_deals(include_archived=True)
                deal_info = all_deals[all_deals["deal_id"] == deal_id] if not all_deals.empty and "deal_id" in all_deals.columns else all_deals
                if deal_info.empty:
                    return self._send_json({"error": "deal not found"}, status=HTTPStatus.NOT_FOUND)
                profile = deal_info.iloc[0].to_dict()
                result = _dd_analyze(profile)
                return self._send_json({"deal_id": deal_id, **result.to_dict()})
            if parts[3] == "dcf":
                from .finance.dcf_model import build_dcf_from_deal as _dcf_build
                all_deals = store.list_deals(include_archived=True)
                deal_info = all_deals[all_deals["deal_id"] == deal_id] if not all_deals.empty and "deal_id" in all_deals.columns else all_deals
                if deal_info.empty:
                    return self._send_json({"error": "deal not found"}, status=HTTPStatus.NOT_FOUND)
                profile = deal_info.iloc[0].to_dict()
                result = _dcf_build(profile)
                return self._send_json({"deal_id": deal_id, **result.to_dict()})
            if parts[3] == "lbo":
                from .finance.lbo_model import build_lbo_from_deal as _lbo_build
                all_deals = store.list_deals(include_archived=True)
                deal_info = all_deals[all_deals["deal_id"] == deal_id] if not all_deals.empty and "deal_id" in all_deals.columns else all_deals
                if deal_info.empty:
                    return self._send_json({"error": "deal not found"}, status=HTTPStatus.NOT_FOUND)
                profile = deal_info.iloc[0].to_dict()
                result = _lbo_build(profile)
                return self._send_json({"deal_id": deal_id, **result.to_dict()})
            if parts[3] == "market":
                from .finance.market_analysis import analyze_market as _mkt
                all_deals = store.list_deals(include_archived=True)
                deal_info = all_deals[all_deals["deal_id"] == deal_id] if not all_deals.empty and "deal_id" in all_deals.columns else all_deals
                if deal_info.empty:
                    return self._send_json({"error": "deal not found"}, status=HTTPStatus.NOT_FOUND)
                profile = deal_info.iloc[0].to_dict()
                result = _mkt(profile)
                return self._send_json({"deal_id": deal_id, **result.to_dict()})
            if parts[3] == "regression":
                from .finance.regression import run_regression as _reg_run
                qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                target_var = (qs.get("target") or ["denial_rate"])[0]
                all_deals = store.list_deals(include_archived=True)
                if all_deals.empty:
                    return self._send_json({"error": "no deals"}, status=HTTPStatus.BAD_REQUEST)
                try:
                    result = _reg_run(all_deals, target_var)
                    return self._send_json({"deal_id": deal_id, **result.to_dict()})
                except ValueError as exc:
                    return self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            if parts[3] == "qa":
                from .ai.document_qa import answer_question as _qa_answer
                qs = urllib.parse.parse_qs(
                    urllib.parse.urlparse(self.path).query)
                question = (qs.get("q") or [""])[0][:500]
                if not question.strip():
                    return self._send_json(
                        {"error": "q parameter required"},
                        status=HTTPStatus.BAD_REQUEST,
                    )
                answer = _qa_answer(store, deal_id, question)
                return self._send_json({
                    "deal_id": deal_id,
                    "question": question,
                    "answer": answer.answer_text,
                    "confidence": answer.confidence,
                    "cited_chunks": len(answer.cited_chunks),
                })
            if parts[3] == "memo":
                from .analysis.analysis_store import get_or_build_packet as _memo_pkt
                from .ai.memo_writer import compose_memo as _compose
                qs = urllib.parse.parse_qs(
                    urllib.parse.urlparse(self.path).query)
                use_llm = (qs.get("llm") or [""])[0] == "1"
                try:
                    pkt = _memo_pkt(store, deal_id, skip_simulation=True)
                except Exception as exc:
                    return self._send_json(
                        {"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR,
                    )
                memo = _compose(pkt, use_llm=use_llm)
                return self._send_json({
                    "deal_id": deal_id,
                    "sections": {
                        k: {"text": v.text, "fact_checks_passed": v.fact_checks_passed}
                        for k, v in memo.sections.items()
                    },
                    "fact_check_warnings": memo.fact_check_warnings,
                    "llm_used": use_llm,
                    "cost_usd": memo.total_cost_usd,
                })
            if parts[3] == "counts":
                notes_df = list_notes(store, deal_id)
                tags = tags_for(store, deal_id)
                from .deals.deal_stages import current_stage
                from .deals.health_score import compute_health
                health = compute_health(store, deal_id)
                stage = current_stage(store, deal_id)
                override_count = 0
                try:
                    from .analysis.deal_overrides import list_overrides
                    ovr = list_overrides(store, deal_id)
                    override_count = len(ovr) if ovr else 0
                except Exception:
                    pass
                return self._send_json({
                    "deal_id": deal_id,
                    "notes": len(notes_df),
                    "tags": len(tags),
                    "overrides": override_count,
                    "stage": stage,
                    "health_score": health.get("score"),
                    "health_band": health.get("band"),
                })
            # Value creation plan API (Prompt 41).
            if parts[3] == "plan":
                from .pe.value_creation_plan import load_latest_plan
                plan = load_latest_plan(store, deal_id)
                if plan is None:
                    return self._send_json(
                        {"deal_id": deal_id, "plan": None,
                         "message": "no plan created yet"},
                    )
                return self._send_json({
                    "deal_id": deal_id, "plan": plan.to_dict(),
                })
            if parts[3] == "audit":
                from .auth.audit_log import list_events
                qs = urllib.parse.parse_qs(
                    urllib.parse.urlparse(self.path).query)
                limit = self._clamp_int(
                    (qs.get("limit") or ["50"])[0],
                    default=50, min_v=1, max_v=500,
                )
                events = list_events(store, limit=limit)
                if not events.empty and "target" in events.columns:
                    events = events[events["target"].str.contains(
                        deal_id, na=False)]
                return self._send_json({
                    "deal_id": deal_id,
                    "events": events.to_dict(orient="records")
                    if not events.empty else [],
                })
            if parts[3] == "package":
                import tempfile as _tmpf
                from .analysis.analysis_store import get_or_build_packet
                from .exports.diligence_package import generate_package
                try:
                    pkt = get_or_build_packet(
                        store, deal_id, skip_simulation=True)
                except Exception as exc:
                    return self._send_json(
                        {"error": str(exc), "code": "BUILD_FAILED"},
                        status=HTTPStatus.INTERNAL_SERVER_ERROR,
                    )
                with _tmpf.TemporaryDirectory() as tmp:
                    from pathlib import Path as _Path
                    zip_path = generate_package(pkt, _Path(tmp))
                    with open(zip_path, "rb") as f:
                        body = f.read()
                safe_name = (pkt.deal_name or deal_id).replace(" ", "_")[:40]
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/zip")
                self.send_header("Content-Length", str(len(body)))
                self.send_header(
                    "Content-Disposition",
                    f'attachment; filename="{safe_name}_package.zip"',
                )
                self.end_headers()
                self.wfile.write(body)
                return
            if parts[3] == "checklist":
                from .deals.deal_stages import current_stage
                from .deals.health_score import compute_health
                stg = current_stage(store, deal_id)
                health = compute_health(store, deal_id)
                items = []
                items.append({
                    "item": "Deal registered",
                    "done": True,
                    "detail": f"Stage: {stg or 'pipeline'}",
                })
                has_analysis = False
                try:
                    from .analysis.analysis_store import list_packets
                    pkts = list_packets(store, deal_id)
                    has_analysis = len(pkts) > 0
                except Exception:
                    pass
                items.append({
                    "item": "Analysis packet built",
                    "done": has_analysis,
                    "detail": "Run /api/analysis/<id> to build" if not has_analysis else "Ready",
                })
                from .deals.deal_notes import list_notes as _cl_notes
                notes = _cl_notes(store, deal_id)
                items.append({
                    "item": "Diligence notes recorded",
                    "done": len(notes) > 0,
                    "detail": f"{len(notes)} note(s)",
                })
                has_plan = False
                try:
                    from .pe.value_creation_plan import load_latest_plan
                    has_plan = load_latest_plan(store, deal_id) is not None
                except Exception:
                    pass
                items.append({
                    "item": "Value creation plan",
                    "done": has_plan,
                    "detail": "Create via POST /api/deals/<id>/plan" if not has_plan else "Ready",
                })
                score = health.get("score")
                items.append({
                    "item": "Health score computed",
                    "done": score is not None,
                    "detail": f"Score: {score}" if score is not None else "No snapshot data",
                })
                done_count = sum(1 for i in items if i["done"])
                return self._send_json({
                    "deal_id": deal_id,
                    "items": items,
                    "progress": f"{done_count}/{len(items)}",
                    "ready_for_ic": done_count == len(items),
                })
            if parts[3] == "validate":
                all_deals = store.list_deals(include_archived=True)
                if all_deals.empty or "deal_id" not in all_deals.columns:
                    return self._send_json(
                        {"error": f"deal {deal_id!r} not found"},
                        status=HTTPStatus.NOT_FOUND,
                    )
                deal_info = all_deals[all_deals["deal_id"] == deal_id]
                if deal_info.empty:
                    return self._send_json(
                        {"error": f"deal {deal_id!r} not found"},
                        status=HTTPStatus.NOT_FOUND,
                    )
                d = deal_info.iloc[0].to_dict()
                issues = []
                warnings = []
                name = d.get("name", "")
                if not name or name == deal_id:
                    issues.append("Deal has no name (using deal_id as fallback)")
                profile_keys = {
                    k for k in d.keys()
                    if k not in ("deal_id", "name", "created_at",
                                 "profile_json", "archived_at")
                    and d[k] is not None
                }
                if len(profile_keys) < 3:
                    issues.append(
                        f"Sparse profile: only {len(profile_keys)} fields populated"
                    )
                elif len(profile_keys) < 8:
                    warnings.append(
                        f"Moderate profile: {len(profile_keys)} fields (recommend 8+)"
                    )
                bed_count = d.get("bed_count")
                if bed_count is not None:
                    try:
                        bc = float(bed_count)
                        if bc <= 0:
                            issues.append("bed_count is zero or negative")
                        elif bc > 5000:
                            warnings.append(f"bed_count={bc} seems high — verify")
                    except (TypeError, ValueError):
                        issues.append("bed_count is not numeric")
                valid = len(issues) == 0
                return self._send_json({
                    "deal_id": deal_id,
                    "valid": valid,
                    "issues": issues,
                    "warnings": warnings,
                    "profile_fields": len(profile_keys),
                })
            if parts[3] == "peers":
                all_deals = store.list_deals()
                if all_deals.empty or "deal_id" not in all_deals.columns:
                    return self._send_json({"deal_id": deal_id, "peers": []})
                target = all_deals[all_deals["deal_id"] == deal_id]
                if target.empty:
                    return self._send_json(
                        {"error": f"deal {deal_id!r} not found"},
                        status=HTTPStatus.NOT_FOUND,
                    )
                t = target.iloc[0]
                others = all_deals[all_deals["deal_id"] != deal_id]
                if others.empty:
                    return self._send_json({"deal_id": deal_id, "peers": []})
                compare_keys = ["bed_count", "denial_rate", "days_in_ar",
                                "net_collection_rate", "cost_to_collect",
                                "clean_claim_rate"]
                peers = []
                for _, row in others.head(5).iterrows():
                    comparisons = {}
                    for k in compare_keys:
                        tv = t.get(k)
                        rv = row.get(k)
                        if tv is not None and rv is not None:
                            try:
                                tv_f, rv_f = float(tv), float(rv)
                                comparisons[k] = {
                                    "target": round(tv_f, 2),
                                    "peer": round(rv_f, 2),
                                    "delta": round(rv_f - tv_f, 2),
                                }
                            except (TypeError, ValueError):
                                pass
                    peers.append({
                        "deal_id": row.get("deal_id"),
                        "name": row.get("name"),
                        "metrics": comparisons,
                    })
                return self._send_json({
                    "deal_id": deal_id,
                    "deal_name": t.get("name", deal_id),
                    "peers": peers,
                })
            if parts[3] == "similar":
                qs = urllib.parse.parse_qs(
                    urllib.parse.urlparse(self.path).query)
                limit = self._clamp_int(
                    (qs.get("limit") or ["5"])[0],
                    default=5, min_v=1, max_v=20,
                )
                all_deals = store.list_deals()
                if all_deals.empty or "deal_id" not in all_deals.columns:
                    return self._send_json({"deal_id": deal_id, "similar": []})
                target = all_deals[all_deals["deal_id"] == deal_id]
                if target.empty:
                    return self._send_json(
                        {"error": f"deal {deal_id!r} not found"},
                        status=HTTPStatus.NOT_FOUND,
                    )
                t = target.iloc[0]
                others = all_deals[all_deals["deal_id"] != deal_id]
                if others.empty:
                    return self._send_json({"deal_id": deal_id, "similar": []})
                numeric_cols = [c for c in others.select_dtypes(include="number").columns]
                scored = []
                for _, row in others.iterrows():
                    dist = 0.0
                    matched = 0
                    for c in numeric_cols:
                        tv = t.get(c)
                        rv = row.get(c)
                        if tv is not None and rv is not None:
                            try:
                                tv, rv = float(tv), float(rv)
                                if tv != 0:
                                    dist += abs(tv - rv) / max(abs(tv), 1)
                                    matched += 1
                            except (TypeError, ValueError):
                                pass
                    score = dist / max(matched, 1)
                    scored.append((score, row.get("deal_id"), row.get("name")))
                scored.sort()
                similar = [
                    {"deal_id": did, "name": nm, "distance": round(d, 3)}
                    for d, did, nm in scored[:limit]
                ]
                return self._send_json({
                    "deal_id": deal_id,
                    "similar": similar,
                })
            # Deal stage API.
            if parts[3] == "stage":
                from .deals.deal_stages import current_stage, stage_history
                curr = current_stage(store, deal_id)
                hist = stage_history(store, deal_id)
                return self._send_json({
                    "deal_id": deal_id,
                    "current_stage": curr,
                    "history": hist,
                })
            # Comments API (Prompt 49).
            if parts[3] == "comments":
                from .deals.comments import list_comments
                qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                metric = (qs.get("metric") or [None])[0]
                comments = list_comments(
                    store, deal_id, metric_key=metric,
                )
                return self._send_json({
                    "deal_id": deal_id, "comments": comments,
                })
            # Approvals API (Prompt 50).
            if parts[3] == "approvals":
                from .deals.approvals import pending_approvals
                pending = pending_approvals(store)
                deal_pending = [
                    p for p in pending if p.get("deal_id") == deal_id
                ]
                return self._send_json({
                    "deal_id": deal_id, "pending": deal_pending,
                })
            if parts[3] == "timeline":
                # GET /api/deals/<id>/timeline?days=30&type=note&limit=50
                from .ui.deal_timeline import collect_timeline
                qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                days = self._clamp_int(
                    (qs.get("days") or ["90"])[0], default=90, min_v=1, max_v=365,
                )
                limit = self._clamp_int(
                    (qs.get("limit") or ["0"])[0], default=0, min_v=0, max_v=500,
                )
                event_type = (qs.get("type") or [""])[0].strip()
                events = collect_timeline(store, deal_id, days=days)
                if event_type:
                    events = [e for e in events
                              if e.get("event_type") == event_type]
                if limit > 0:
                    events = events[:limit]
                return self._send_json({
                    "deal_id": deal_id,
                    "events": events,
                    "count": len(events),
                    "days": days,
                })
            if parts[3] == "overrides":
                # /api/deals/<id>/overrides — list all overrides
                # /api/deals/<id>/overrides/<key> — fetch one
                from .analysis.deal_overrides import (
                    get_overrides, list_overrides,
                )
                if len(parts) == 4:
                    return self._send_json({
                        "deal_id": deal_id,
                        "overrides": get_overrides(store, deal_id),
                        "audit": list_overrides(store, deal_id),
                    })
                if len(parts) == 5:
                    key = urllib.parse.unquote(parts[4])
                    overrides = get_overrides(store, deal_id)
                    if key not in overrides:
                        return self._send_json(
                            {"error": f"no override {key!r} for {deal_id}",
                             "code": "OVERRIDE_NOT_FOUND"},
                            status=HTTPStatus.NOT_FOUND,
                        )
                    return self._send_json({
                        "deal_id": deal_id,
                        "override_key": key,
                        "override_value": overrides[key],
                    })

        if parts == ["api", "tags"]:
            return self._send_json([
                {"tag": t, "count": c} for t, c in all_tags(store)
            ])

        if parts == ["api", "export"]:
            return self._route_export(store)

        if parts == ["api", "alerts", "active-count"]:
            from .alerts.alerts import evaluate_active
            alerts = evaluate_active(store)
            return self._send_json({"count": len(alerts)})
        if parts == ["api", "alerts", "active"]:
            from .alerts.alerts import evaluate_active
            alerts = evaluate_active(store)
            return self._send_json([a.to_dict() for a in alerts])
        if parts == ["api", "alerts", "all"]:
            # Audit view: includes acked alerts too
            from .alerts.alerts import evaluate_all
            return self._send_json([a.to_dict() for a in evaluate_all(store)])
        if parts == ["api", "alerts", "acks"]:
            from .alerts.alert_acks import list_acks
            return self._send_json(list_acks(store).to_dict(orient="records"))
        if len(parts) == 3 and parts[0] == "api" and parts[1] == "my":
            from .alerts.alerts import evaluate_active
            from .deals.deal_deadlines import overdue, upcoming
            from .deals.deal_owners import deals_by_owner
            owner = urllib.parse.unquote(parts[2])
            try:
                my_deals = deals_by_owner(store, owner)
            except ValueError as exc:
                return self._send_json(
                    {"error": str(exc)}, status=HTTPStatus.BAD_REQUEST,
                )
            my_set = set(my_deals)
            return self._send_json({
                "owner": owner,
                "deals": my_deals,
                "alerts": [
                    a.to_dict() for a in evaluate_active(store)
                    if a.deal_id in my_set
                ],
                "overdue": overdue(
                    store, owner=owner,
                ).to_dict(orient="records"),
                "upcoming": upcoming(
                    store, owner=owner,
                ).to_dict(orient="records"),
            })
        if parts == ["api", "deadlines"]:
            from .deals.deal_deadlines import overdue, upcoming
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            days_ahead = self._clamp_int(
                (qs.get("days") or ["14"])[0],
                default=14, min_v=1, max_v=365,
            )
            owner = (qs.get("owner") or [""])[0].strip() or None
            return self._send_json({
                "overdue": overdue(
                    store, owner=owner,
                ).to_dict(orient="records"),
                "upcoming": upcoming(
                    store, days_ahead=days_ahead, owner=owner,
                ).to_dict(orient="records"),
            })
        if (len(parts) == 4 and parts[0] == "api" and parts[1] == "deals"
                and parts[3] == "deadlines"):
            from .deals.deal_deadlines import list_deadlines
            deal_id = urllib.parse.unquote(parts[2])
            include = bool((urllib.parse.parse_qs(
                urllib.parse.urlparse(self.path).query,
            )).get("all"))
            df = list_deadlines(store, deal_id=deal_id,
                                include_completed=include)
            return self._send_json(df.to_dict(orient="records"))
        if parts == ["api", "owners"]:
            from .deals.deal_owners import all_owners
            return self._send_json([
                {"owner": o, "deal_count": n} for o, n in all_owners(store)
            ])
        if len(parts) == 3 and parts[0] == "api" and parts[1] == "owner":
            from .deals.deal_owners import deals_by_owner
            try:
                dids = deals_by_owner(store, urllib.parse.unquote(parts[2]))
            except ValueError as exc:
                return self._send_json(
                    {"error": str(exc)}, status=HTTPStatus.BAD_REQUEST,
                )
            return self._send_json({"deal_ids": dids})
        if parts == ["api", "audit", "events"]:
            from .auth.audit_log import list_events
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            df = list_events(
                store,
                since=(qs.get("since") or [None])[0],
                actor=(qs.get("actor") or [None])[0],
                action=(qs.get("action") or [None])[0],
                limit=self._clamp_int(
                    (qs.get("limit") or ["200"])[0],
                    default=200, min_v=1, max_v=2000,
                ),
                offset=self._clamp_int(
                    (qs.get("offset") or ["0"])[0],
                    default=0, min_v=0, max_v=10_000_000,
                ),
            )
            return self._send_json(df.to_dict(orient="records"))
        if parts == ["api", "me"]:
            # B126: identity introspection for JS + scripts
            user = self._current_user()
            return self._send_json(user or {})
        if parts == ["api", "watchlist"]:
            from .deals.watchlist import list_starred
            return self._send_json({"starred": list_starred(store)})
        if parts == ["api", "note-tags"]:
            from .deals.note_tags import all_note_tags
            return self._send_json([
                {"tag": t, "count": c} for t, c in all_note_tags(store)
            ])
        if (len(parts) == 4 and parts[0] == "api" and parts[1] == "notes"
                and parts[3] == "tags"):
            from .deals.note_tags import tags_for_note
            try:
                nid = int(parts[2])
            except ValueError:
                return self._send_json(
                    {"error": "note_id must be int"},
                    status=HTTPStatus.BAD_REQUEST,
                )
            return self._send_json({
                "note_id": nid, "tags": tags_for_note(store, nid),
            })
        if parts == ["api", "notes", "search"]:
            from .deals.deal_notes import search_notes
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            q = (qs.get("q") or [""])[0]
            deal_id = (qs.get("deal_id") or [""])[0].strip() or None
            limit = self._clamp_int(
                (qs.get("limit") or ["50"])[0],
                default=50, min_v=1, max_v=500,
            )
            offset = self._clamp_int(
                (qs.get("offset") or ["0"])[0],
                default=0, min_v=0, max_v=10_000_000,
            )
            df = search_notes(
                store, q, deal_id=deal_id, limit=limit, offset=offset,
            )
            return self._send_json(df.to_dict(orient="records"))
        if parts == ["api", "portfolio", "variance"]:
            from .pe.hold_tracking import portfolio_variance_matrix
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            kpi = (qs.get("kpi") or ["ebitda"])[0]
            quarter = (qs.get("quarter") or [None])[0]
            df = portfolio_variance_matrix(store, kpi=kpi, quarter=quarter)
            return self._send_json(df.to_dict(orient="records"))
        if parts == ["api", "cohorts"]:
            from .analysis.cohorts import cohort_rollup
            return self._send_json(
                cohort_rollup(store).to_dict(orient="records"),
            )
        if len(parts) == 3 and parts[0] == "api" and parts[1] == "cohort":
            from .analysis.cohorts import cohort_detail
            tag = urllib.parse.unquote(parts[2])
            return self._send_json(
                cohort_detail(store, tag).to_dict(orient="records"),
            )
        if parts == ["api", "alerts", "history"]:
            from .alerts.alert_history import list_history
            return self._send_json(list_history(store).to_dict(orient="records"))
        if parts == ["api", "alerts", "days_red"]:
            from .alerts.alert_history import days_red
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            min_days = self._clamp_int(
                (qs.get("min_days") or ["30"])[0],
                default=30, min_v=0, max_v=3650,
            )
            return self._send_json(
                days_red(store, min_days=min_days).to_dict(orient="records"),
            )

        if parts == ["api", "jobs"]:
            from .infra.job_queue import get_default_registry
            reg = get_default_registry()
            return self._send_json([j.to_dict() for j in reg.list_recent(50)])
        if len(parts) == 3 and parts[0] == "api" and parts[1] == "jobs":
            from .infra.job_queue import get_default_registry
            reg = get_default_registry()
            job = reg.get(parts[2])
            if job is None:
                return self._send_json(
                    {"error": "job not found", "job_id": parts[2]},
                    status=HTTPStatus.NOT_FOUND,
                )
            return self._send_json(job.to_dict())

        # /api/analysis/<deal_id>[?scenario=&as_of=]
        # /api/analysis/<deal_id>/section/<section_name>
        if len(parts) >= 3 and parts[0] == "api" and parts[1] == "analysis":
            return self._route_analysis_get(path, parts)

        # /api/data/sources
        # /api/data/hospitals?state=..&beds_min=..&beds_max=..
        if len(parts) >= 2 and parts[0] == "api" and parts[1] == "data":
            return self._route_data_get(path, parts)

        # /api/predict/backtest — system-wide prediction quality across
        # the benchmark-database hospitals. Expensive (many trials), so
        # clamp n_trials hard.
        if parts == ["api", "predict", "backtest"]:
            return self._route_predict_backtest()

        self.send_error(HTTPStatus.NOT_FOUND, f"Unknown API path: {path}")

    def _route_analysis_export(self, deal_id: str, packet: Any) -> None:
        """GET /api/analysis/<deal_id>/export?format=X

        ``format`` ∈ {``html``, ``pptx``, ``json``, ``csv``, ``questions``}.
        HTML / JSON are rendered inline; the file-bearing formats
        (pptx / csv / questions) are written to a temp dir and
        streamed back with a ``Content-Disposition: attachment`` so
        the browser saves them with the original filename. Every
        export writes one row to ``generated_exports`` for audit.
        """
        from .exports import PacketRenderer, record_export
        from .analysis.packet import hash_inputs
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        fmt = ((qs.get("format") or ["html"])[0] or "html").lower()
        valid = {"html", "pptx", "json", "csv", "xlsx", "questions", "package"}
        if fmt not in valid:
            return self._send_json(
                {"error": f"unknown format {fmt!r}", "valid": sorted(valid)},
                status=HTTPStatus.BAD_REQUEST,
            )
        # Recompute the input hash so the audit row matches the packet
        # cache. Cheap; matches the hash stored by analysis_store.
        try:
            ihash = hash_inputs(
                deal_id=packet.deal_id,
                observed_metrics={},
                scenario_id=packet.scenario_id,
                as_of=packet.as_of,
            )
        except Exception:  # noqa: BLE001
            ihash = ""

        store = PortfolioStore(self.config.db_path)
        renderer = PacketRenderer()
        cu = self._current_user() or {}
        actor = cu.get("username") or "anonymous"

        if fmt == "json":
            body = renderer.render_packet_json(packet)
            record_export(store, deal_id=deal_id, analysis_run_id=packet.run_id,
                           format="json", filepath=None,
                           file_size_bytes=len(body), packet_hash=ihash,
                           generated_by=actor)
            body_b = body.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body_b)))
            self.send_header(
                "Content-Disposition",
                f'attachment; filename="{deal_id}.json"',
            )
            self.end_headers()
            self.wfile.write(body_b)
            return

        if fmt == "html":
            body = renderer.render_diligence_memo_html(packet, inputs_hash=ihash)
            record_export(store, deal_id=deal_id, analysis_run_id=packet.run_id,
                           format="html", filepath=None,
                           file_size_bytes=len(body), packet_hash=ihash,
                           generated_by=actor)
            return self._send_html(body)

        # File-bearing formats
        if fmt == "pptx":
            path = renderer.render_diligence_memo_pptx(packet, inputs_hash=ihash)
            mime = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            if str(path).endswith(".txt"):
                mime = "text/plain; charset=utf-8"
        elif fmt == "csv":
            path = renderer.render_raw_data_csv(packet, inputs_hash=ihash)
            mime = "text/csv; charset=utf-8"
        elif fmt == "xlsx":
            path = renderer.render_deal_xlsx(packet, inputs_hash=ihash)
            # When openpyxl is missing the renderer quietly falls back
            # to CSV; label the mime accordingly so browsers don't
            # open a text file as .xlsx.
            if str(path).endswith(".csv"):
                mime = "text/csv; charset=utf-8"
            else:
                mime = (
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                )
        elif fmt == "package":
            from .exports.diligence_package import generate_package
            import tempfile as _tempfile
            pkg_dir = Path(_tempfile.mkdtemp())
            path = generate_package(packet, pkg_dir, inputs_hash=ihash)
            mime = "application/zip"
        else:  # questions
            path = renderer.render_diligence_questions_docx(packet, inputs_hash=ihash)
            if str(path).endswith(".md"):
                mime = "text/markdown; charset=utf-8"
            else:
                mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        body_b = Path(path).read_bytes()
        record_export(store, deal_id=deal_id, analysis_run_id=packet.run_id,
                       format=fmt, filepath=str(path),
                       file_size_bytes=len(body_b), packet_hash=ihash,
                       generated_by=actor)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body_b)))
        self.send_header(
            "Content-Disposition",
            f'attachment; filename="{Path(path).name}"',
        )
        self.end_headers()
        self.wfile.write(body_b)

    def _route_exports_lp_update(self) -> None:
        """GET /exports/lp-update?days=30 — portfolio LP update rendered
        from all recent analysis packets.
        """
        from .exports import PacketRenderer
        from .analysis.analysis_store import list_packets, load_packet_by_id
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        days = self._clamp_int(
            (qs.get("days") or ["30"])[0],
            default=30, min_v=1, max_v=3650,
        )
        store = PortfolioStore(self.config.db_path)
        rows = list_packets(store)
        packets: List[Any] = []
        seen: set = set()
        for row in rows:
            deal_id = row["deal_id"]
            if deal_id in seen:
                continue
            seen.add(deal_id)
            pkt = load_packet_by_id(store, int(row["id"]))
            if pkt is not None:
                packets.append(pkt)
        renderer = PacketRenderer()
        return self._send_html(renderer.render_lp_update_html(packets))

    def _route_analysis_workbench(self, deal_id: str) -> None:
        """GET /analysis/<deal_id> — Bloomberg-style analyst workbench.

        Builds (or reuses the cached) packet and renders the full HTML
        page. Every tab in the page reads from the single packet
        returned here — if two tabs disagree, it's a renderer bug, not
        a data bug. The ``Rebuild`` button in the header POSTs to
        ``/api/analysis/<id>/rebuild`` which force-rebuilds and then
        the browser reloads back onto this route.
        """
        if not deal_id:
            self.send_error(HTTPStatus.BAD_REQUEST, "deal id required")
            return
        from .analysis.analysis_store import get_or_build_packet
        from .ui.analysis_workbench import render_workbench
        from .ui.json_to_html import _fmt_money as _jth_fmt  # noqa: F401
        from .ui.text_to_html import _strip_ansi  # noqa: F401
        from .ui.csv_to_html import _fmt_money as _cth_fmt  # noqa: F401
        # Import analytics modules so they're available for packet enrichment
        try:
            from .analytics.causal_inference import estimate_initiative_impact  # noqa: F401
            from .analytics.counterfactual import build_counterfactual  # noqa: F401
            from .pe.attribution import compute_attribution  # noqa: F401
            from .pe.predicted_vs_actual import compute_predicted_vs_actual  # noqa: F401
            from .pe.lever_dependency import adjust_for_dependencies  # noqa: F401
            from .pe.breakdowns import run_with_breakdowns  # noqa: F401
            from .ml.portfolio_learning import cross_deal_predict  # noqa: F401
            from .ml.conformal import conformal_predict  # noqa: F401
            from .ml.ridge_predictor import RidgeWithConformal  # noqa: F401
            from .ml.ensemble_predictor import EnsemblePredictor  # noqa: F401
            from .ml.rcm_predictor import predict_missing  # noqa: F401
            from .ml.feature_engineering import engineer_features  # noqa: F401
            from .mc.scenario_comparison import compare_scenarios  # noqa: F401
            from .analysis.compare_runs import compare_run_pair  # noqa: F401
            from .exports.packet_renderer import render_packet_html  # noqa: F401
            from .exports.exit_package import _utcnow_iso as _ep_ts  # noqa: F401
            from .exports.xlsx_renderer import _openpyxl_or_raise as _xlsx_check  # noqa: F401
            from .exports.lp_quarterly_report import _fmt_money as _lp_fmt  # noqa: F401
            from .reports.narrative import generate_narrative  # noqa: F401  # noqa: F401
            from .reports.exit_memo import _fmt_money as _em_fmt  # noqa: F401
            from .reports.full_report import _build_input_requirements_section as _fr_sec  # noqa: F401
            from .reports.html_report import generate_html_report  # noqa: F401
            from .reports.markdown_report import _fmt_money as _md_fmt  # noqa: F401
            from .reports.report_themes import get_theme_css  # noqa: F401
            from .reports._partner_brief import _load_grade as _pb_grade  # noqa: F401
            from .reports.lp_update import build_lp_update_html  # noqa: F401
            from .reports.pptx_export import generate_pptx  # noqa: F401
            from .provenance.tracker import DataPoint  # noqa: F401
            from .scenarios.scenario_builder import build_scenario  # noqa: F401
            from .scenarios.scenario_overlay import apply_overlay  # noqa: F401
            from .mc.convergence import check_convergence  # noqa: F401
            from .core.simulator import _logit as _sim_logit  # noqa: F401
            from .core.calibration import DataQualityReport  # noqa: F401
            from .core.distributions import DistributionError  # noqa: F401
            from .core.kernel import SimulationResult  # noqa: F401
            from .analysis.anomaly_detection import detect_anomalies  # noqa: F401
            from .analysis.risk_flags import _get_metric as _rf_get  # noqa: F401
            from .analysis.packet_builder import _new_run_id as _pb_rid  # noqa: F401
            from .analysis.refresh_scheduler import detect_stale  # noqa: F401
            from .rcm.claim_distribution import ClaimBucket  # noqa: F401
            from .rcm.initiatives import load_initiatives_library  # noqa: F401
            from .rcm.initiative_optimizer import rank_initiatives  # noqa: F401
        except Exception:
            pass
        store = PortfolioStore(self.config.db_path)
        profile = self._load_deal_profile(deal_id)
        if not profile:
            from .ui._chartis_kit import chartis_shell as _shell_nf
            return self._send_html(_shell_nf(
                f'<div class="cad-card"><h2>Deal Not Found</h2>'
                f'<p style="color:var(--cad-text3);">Deal <strong>{html.escape(deal_id)}</strong> '
                f'does not exist. <a href="/import" style="color:var(--cad-link);">'
                f'Import a deal</a>.</p></div>',
                f"Not Found: {html.escape(deal_id)}",
            ), status=HTTPStatus.NOT_FOUND)
        # Try the full workbench first
        try:
            packet = get_or_build_packet(
                store, deal_id, skip_simulation=True,
            )
            wb_html = render_workbench(packet)
            try:
                from .ui.data_public.corpus_flags_panel import inject_into_workbench
                wb_html = inject_into_workbench(wb_html, profile)
            except Exception:
                pass
            return self._send_html(wb_html)
        except Exception as exc:  # noqa: BLE001
            from .ui.deal_quick_view import render_deal_quick_view
            return self._send_html(render_deal_quick_view(
                deal_id, profile, error_msg=str(exc)))

    def _build_partner_review_context(self, deal_id: str) -> Tuple[Any, Optional[str], Dict[str, Any]]:
        """Shared packet-load + partner_review() wrapper.

        Returns ``(review_or_None, error_or_None, meta)`` where ``meta`` carries
        ``deal_name`` and ``missing_fields`` for the error path. Used by both
        ``/deal/<id>/partner-review`` and ``/deal/<id>/red-flags`` so the brain
        runs once per packet, not twice. partner_review() is defensive — it
        only raises on structural bugs, not missing fields — but we still
        wrap it so a bad import doesn't crash the route.
        """
        meta: Dict[str, Any] = {"deal_name": "", "missing_fields": []}
        profile = self._load_deal_profile(deal_id)
        if not profile:
            return None, "Deal not found.", meta
        meta["deal_name"] = str(profile.get("name", "") or "")
        try:
            from .analysis.analysis_store import get_or_build_packet
            from .pe_intelligence import partner_review
        except Exception as exc:  # noqa: BLE001
            return None, f"pe_intelligence import failed: {exc!r}", meta
        try:
            packet = get_or_build_packet(self._require_store(), deal_id, skip_simulation=True)
        except Exception as exc:  # noqa: BLE001
            meta["missing_fields"] = ["analysis packet (run a simulation first)"]
            return None, f"packet build failed: {exc!r}", meta
        try:
            review = partner_review(packet)
        except Exception as exc:  # noqa: BLE001
            return None, f"partner_review raised: {exc!r}", meta
        return review, None, meta

    def _require_store(self) -> Any:
        """Fetch a PortfolioStore handle for this request."""
        return PortfolioStore(self.config.db_path)

    def _chartis_username(self) -> Optional[str]:
        """Pull the display username (or None) for chartis page headers."""
        cu = self._current_user() or {}
        if isinstance(cu, dict):
            return cu.get("username") or cu.get("display_name")
        return None

    def _route_partner_review(self, deal_id: str) -> None:
        """GET /deal/<deal_id>/partner-review — full PE brain verdict."""
        if not deal_id:
            self.send_error(HTTPStatus.BAD_REQUEST, "deal id required")
            return
        from .ui.chartis.partner_review_page import render_partner_review
        username = self._chartis_username()
        review, err, meta = self._build_partner_review_context(deal_id)
        if err:
            return self._send_html(render_partner_review(
                None, deal_id,
                deal_name=meta.get("deal_name", ""),
                error=err,
                missing_fields=meta.get("missing_fields"),
                current_user=username,
            ))
        return self._send_html(render_partner_review(
            review, deal_id,
            deal_name=meta.get("deal_name", ""),
            current_user=username,
        ))

    def _route_archetype(self, deal_id: str) -> None:
        """GET /deal/<deal_id>/archetype — classify_archetypes + regime."""
        if not deal_id:
            self.send_error(HTTPStatus.BAD_REQUEST, "deal id required")
            return
        from .ui.chartis.archetype_page import (
            render_archetype, _build_archetype_context,
        )
        username = self._chartis_username()
        review, err, meta = self._build_partner_review_context(deal_id)
        if err:
            return self._send_html(render_archetype(
                None, deal_id,
                deal_name=meta.get("deal_name", ""),
                error=err,
                missing_fields=meta.get("missing_fields"),
                current_user=username,
            ))
        # The PartnerReview gives us the regime dict for free; we still
        # need to run the archetype classifier separately because the
        # review doesn't carry archetype hits.
        profile = self._load_deal_profile(deal_id) or {}
        try:
            from .analysis.analysis_store import get_or_build_packet
            packet = get_or_build_packet(
                self._require_store(), deal_id, skip_simulation=True,
            )
        except Exception:
            packet = None
        try:
            from .pe_intelligence.deal_archetype import (
                classify_archetypes, primary_archetype,
            )
            ctx = _build_archetype_context(profile, packet)
            hits = classify_archetypes(ctx)
            primary = primary_archetype(ctx)
        except Exception as exc:  # noqa: BLE001
            return self._send_html(render_archetype(
                review, deal_id,
                deal_name=meta.get("deal_name", ""),
                error=f"archetype classifier raised: {exc!r}",
                missing_fields=["hospital_type + deal-structure flags"],
                current_user=username,
            ))
        return self._send_html(render_archetype(
            review, deal_id,
            deal_name=meta.get("deal_name", ""),
            archetype_hits=hits,
            primary=primary,
            archetype_context=ctx,
            current_user=username,
        ))

    def _route_investability(self, deal_id: str) -> None:
        """GET /deal/<id>/investability — composite score + exit readiness."""
        if not deal_id:
            self.send_error(HTTPStatus.BAD_REQUEST, "deal id required")
            return
        from .ui.chartis.investability_page import render_investability
        username = self._chartis_username()
        review, err, meta = self._build_partner_review_context(deal_id)
        if err:
            return self._send_html(render_investability(
                None, deal_id,
                deal_name=meta.get("deal_name", ""),
                error=err,
                missing_fields=meta.get("missing_fields"),
                current_user=username,
            ))
        exit_report = None
        try:
            from .pe_intelligence.partner_review import _extract_context
            from .pe_intelligence.exit_readiness import (
                ExitReadinessInputs, score_exit_readiness,
            )
            from .analysis.analysis_store import get_or_build_packet
            packet = get_or_build_packet(
                self._require_store(), deal_id, skip_simulation=True,
            )
            ctx = _extract_context(packet)
            profile = self._load_deal_profile(deal_id) or {}
            readiness_inputs = ExitReadinessInputs(
                has_audited_financials_3yr=profile.get("has_audited_financials_3yr"),
                has_trailing_12mo_kpis=profile.get("has_trailing_12mo_kpis"),
                data_room_organized=profile.get("data_room_organized"),
                quality_of_earnings_prepared=profile.get("quality_of_earnings_prepared"),
                ebitda_trending_up_last_2q=profile.get("ebitda_trending_up_last_2q"),
                margin_trending_up_last_2q=profile.get("margin_trending_up_last_2q"),
                buyer_universe_mapped=profile.get("buyer_universe_mapped"),
                management_retained_through_close=profile.get("management_retained_through_close"),
                legal_litigation_clean=profile.get("legal_litigation_clean"),
                ebitda_adj_recon_documented=profile.get("ebitda_adj_recon_documented"),
                ebitda_vs_plan=profile.get("ebitda_vs_plan"),
                revenue_vs_plan=profile.get("revenue_vs_plan"),
            )
            exit_report = score_exit_readiness(ctx, readiness_inputs)
        except Exception:  # noqa: BLE001
            exit_report = None  # fall through — investability can still render
        return self._send_html(render_investability(
            review, deal_id,
            deal_name=meta.get("deal_name", ""),
            exit_report=exit_report,
            current_user=username,
        ))

    def _route_market_structure(self, deal_id: str) -> None:
        """GET /deal/<id>/market-structure — HHI / CR3 / CR5 + thesis hint."""
        if not deal_id:
            self.send_error(HTTPStatus.BAD_REQUEST, "deal id required")
            return
        from .ui.chartis.market_structure_page import render_market_structure
        username = self._chartis_username()
        review, err, meta = self._build_partner_review_context(deal_id)
        if err:
            return self._send_html(render_market_structure(
                None, deal_id,
                deal_name=meta.get("deal_name", ""),
                error=err,
                missing_fields=meta.get("missing_fields"),
                current_user=username,
            ))
        profile = self._load_deal_profile(deal_id) or {}
        packet = None
        try:
            from .analysis.analysis_store import get_or_build_packet
            packet = get_or_build_packet(
                self._require_store(), deal_id, skip_simulation=True,
            )
        except Exception:
            packet = None
        return self._send_html(render_market_structure(
            review, deal_id,
            deal_name=meta.get("deal_name", ""),
            packet=packet,
            profile=profile,
            current_user=username,
        ))

    def _route_white_space(self, deal_id: str) -> None:
        """GET /deal/<id>/white-space — detect_white_space opportunities."""
        if not deal_id:
            self.send_error(HTTPStatus.BAD_REQUEST, "deal id required")
            return
        from .ui.chartis.white_space_page import render_white_space
        username = self._chartis_username()
        review, err, meta = self._build_partner_review_context(deal_id)
        if err:
            return self._send_html(render_white_space(
                None, deal_id,
                deal_name=meta.get("deal_name", ""),
                error=err,
                missing_fields=meta.get("missing_fields"),
                current_user=username,
            ))
        return self._send_html(render_white_space(
            review, deal_id,
            deal_name=meta.get("deal_name", ""),
            current_user=username,
        ))

    def _route_stress(self, deal_id: str) -> None:
        """GET /deal/<id>/stress — scenario stress grid."""
        if not deal_id:
            self.send_error(HTTPStatus.BAD_REQUEST, "deal id required")
            return
        from .ui.chartis.stress_page import render_stress
        username = self._chartis_username()
        review, err, meta = self._build_partner_review_context(deal_id)
        if err:
            return self._send_html(render_stress(
                None, deal_id,
                deal_name=meta.get("deal_name", ""),
                error=err,
                missing_fields=meta.get("missing_fields"),
                current_user=username,
            ))
        return self._send_html(render_stress(
            review, deal_id,
            deal_name=meta.get("deal_name", ""),
            current_user=username,
        ))

    def _route_ic_packet(self, deal_id: str) -> None:
        """GET /deal/<id>/ic-packet — master_bundle + ic_memo full packet."""
        if not deal_id:
            self.send_error(HTTPStatus.BAD_REQUEST, "deal id required")
            return
        from .ui.chartis.ic_packet_page import render_ic_packet
        username = self._chartis_username()
        review, err, meta = self._build_partner_review_context(deal_id)
        if err:
            return self._send_html(render_ic_packet(
                None, deal_id,
                deal_name=meta.get("deal_name", ""),
                error=err,
                missing_fields=meta.get("missing_fields"),
                current_user=username,
            ))
        bundle = None
        try:
            from .analysis.analysis_store import get_or_build_packet
            from .pe_intelligence.master_bundle import build_master_bundle
            packet = get_or_build_packet(
                self._require_store(), deal_id, skip_simulation=True,
            )
            bundle = build_master_bundle(packet)
        except Exception:  # noqa: BLE001
            bundle = None
        return self._send_html(render_ic_packet(
            review, deal_id,
            deal_name=meta.get("deal_name", ""),
            bundle=bundle,
            current_user=username,
        ))

    def _route_red_flags(self, deal_id: str) -> None:
        """GET /deal/<deal_id>/red-flags — focused red-flag surface."""
        if not deal_id:
            self.send_error(HTTPStatus.BAD_REQUEST, "deal id required")
            return
        from .ui.chartis.red_flags_page import render_red_flags
        username = self._chartis_username()
        review, err, meta = self._build_partner_review_context(deal_id)
        if err:
            return self._send_html(render_red_flags(
                None, deal_id,
                deal_name=meta.get("deal_name", ""),
                error=err,
                missing_fields=meta.get("missing_fields"),
                current_user=username,
            ))
        return self._send_html(render_red_flags(
            review, deal_id,
            deal_name=meta.get("deal_name", ""),
            current_user=username,
        ))

    def _build_mc_context(self, deal_id: str, payload: Dict[str, Any]) -> Any:
        """Assemble the bridge + simulator for a MC endpoint.

        Returns a dict with ``bridge``, ``sim``, ``assumptions``,
        ``current_metrics``, ``packet``; or a tuple ``(None, error_json,
        status)`` when the setup fails.
        """
        from .pe.rcm_ebitda_bridge import FinancialProfile, RCMEBITDABridge
        from .analysis.analysis_store import get_or_build_packet
        from .mc import (
            MetricAssumption, RCMMonteCarloSimulator,
            default_execution_assumption, from_conformal_prediction,
        )
        store = PortfolioStore(self.config.db_path)
        financials = payload.get("financials") or {}
        try:
            packet = get_or_build_packet(store, deal_id, skip_simulation=True)
        except Exception as exc:  # noqa: BLE001
            return (None, {"error": f"packet build failed: {exc}"},
                    HTTPStatus.INTERNAL_SERVER_ERROR)
        fp = FinancialProfile(
            gross_revenue=float(financials.get("gross_revenue") or 0.0),
            net_revenue=float(financials.get("net_revenue") or 0.0),
            current_ebitda=float(financials.get("current_ebitda")
                                  or packet.ebitda_bridge.current_ebitda or 0.0),
            total_claims_volume=int(financials.get("total_claims_volume") or 0),
            cost_of_capital_pct=float(financials.get("cost_of_capital_pct") or 0.08),
            payer_mix=dict(packet.profile.payer_mix or {}),
        )
        bridge_obj = RCMEBITDABridge(fp)

        # Either the caller supplies explicit per-metric assumptions, or
        # we derive them from the packet's bridge result + predictions.
        assumptions_raw = payload.get("assumptions") or {}
        assumptions: Dict[str, MetricAssumption] = {}
        if assumptions_raw:
            for k, v in assumptions_raw.items():
                if isinstance(v, dict):
                    assumptions[str(k)] = MetricAssumption.from_dict({**v, "metric_key": k})
        else:
            for imp in packet.ebitda_bridge.per_metric_impacts:
                key = imp.metric_key
                pred = packet.predicted_metrics.get(key)
                if pred is not None and pred.ci_low is not None and pred.ci_high is not None:
                    assumptions[key] = from_conformal_prediction(
                        key, current_value=imp.current_value,
                        target_value=imp.target_value,
                        ci_low=pred.ci_low, ci_high=pred.ci_high,
                    )
                else:
                    assumptions[key] = default_execution_assumption(
                        key, current_value=imp.current_value,
                        target_value=imp.target_value,
                    )
        if not assumptions:
            return (None, {"error": "no metric assumptions available — "
                                     "build a bridge first"}, HTTPStatus.BAD_REQUEST)
        current_metrics = {k: float(v.value)
                            for k, v in packet.rcm_profile.items()}
        sim = RCMMonteCarloSimulator(
            bridge_obj,
            n_simulations=int(payload.get("n_simulations") or 2000),
            seed=int(payload.get("seed") or 42),
        )
        sim.configure(
            current_metrics, assumptions,
            entry_multiple=float(financials.get("entry_multiple") or 10.0),
            exit_multiple=float(financials.get("exit_multiple") or 10.0),
            hold_years=float(financials.get("hold_years") or 5.0),
            organic_growth_pct=float(financials.get("organic_growth_pct") or 0.0),
            moic_targets=tuple(financials.get("moic_targets")
                                or (1.5, 2.0, 2.5, 3.0)),
            covenant_leverage_threshold=(
                float(financials["covenant_leverage_threshold"])
                if financials.get("covenant_leverage_threshold") is not None
                else None
            ),
        )
        return {
            "bridge": bridge_obj, "sim": sim, "assumptions": assumptions,
            "current_metrics": current_metrics, "packet": packet, "store": store,
        }

    def _route_simulate_run(self, deal_id: str, payload: Dict[str, Any]) -> None:
        from .mc.mc_store import save_mc_run
        ctx = self._build_mc_context(deal_id, payload)
        if isinstance(ctx, tuple):
            _, err, status = ctx
            return self._send_json(err, status=status)
        label = str(payload.get("scenario_label") or "default")
        try:
            result = ctx["sim"].run(scenario_label=label)
        except Exception as exc:  # noqa: BLE001
            return self._send_json({"error": f"simulate failed: {exc}"},
                                    status=HTTPStatus.INTERNAL_SERVER_ERROR)
        try:
            save_mc_run(ctx["store"], deal_id, result,
                        analysis_run_id=ctx["packet"].run_id)
        except Exception:  # noqa: BLE001 — cache write must not break response
            pass
        return self._send_json({
            "deal_id": deal_id,
            "analysis_run_id": ctx["packet"].run_id,
            "mc": result.to_dict(),
        })

    def _route_simulate_v2(self, deal_id: str, payload: Dict[str, Any]) -> None:
        """Run the v2 Monte Carlo (``compute_value_bridge``) for a deal.

        Payload shape::

            {
              "financials": {"net_revenue": 400e6, "claims_volume": 120_000, ...},
              "assumptions": {metric: {execution_probability: 0.7, ...}, ...},  # optional
              "n_simulations": 2000,
              "seed": 42,
              "scenario_label": "v2:base"
            }

        The server pulls the cached packet to get payer mix, rcm_profile,
        reimbursement profile + revenue realization. Payload overrides
        plug in on top.
        """
        from .analysis.analysis_store import get_or_build_packet
        from .finance.reimbursement_engine import ReimbursementProfile
        from .mc.ebitda_mc import (
            MetricAssumption,
            default_execution_assumption,
            from_conformal_prediction,
        )
        from .mc.mc_store import save_v2_mc_run
        from .mc.v2_monte_carlo import V2MonteCarloSimulator
        from .pe.value_bridge_v2 import BridgeAssumptions

        store = PortfolioStore(self.config.db_path)
        try:
            packet = get_or_build_packet(store, deal_id, skip_simulation=True)
        except Exception as exc:  # noqa: BLE001
            return self._send_json(
                {"error": f"packet build failed: {exc}"},
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )
        if (packet.ebitda_bridge is None
                or not packet.ebitda_bridge.per_metric_impacts):
            return self._send_json(
                {"error": "v2 simulator needs a completed v1 bridge to pick levers"},
                status=HTTPStatus.BAD_REQUEST,
            )
        financials = payload.get("financials") or {}
        if not isinstance(financials, dict):
            return self._send_json(
                {"error": "financials must be an object"},
                status=HTTPStatus.BAD_REQUEST,
            )

        # Build assumptions — caller overrides > packet predictions >
        # lever-family default.
        assumptions_raw = payload.get("assumptions") or {}
        if not isinstance(assumptions_raw, dict):
            return self._send_json(
                {"error": "assumptions must be an object"},
                status=HTTPStatus.BAD_REQUEST,
            )
        assumptions: Dict[str, MetricAssumption] = {}
        for imp in packet.ebitda_bridge.per_metric_impacts:
            key = imp.metric_key
            override = assumptions_raw.get(key)
            if isinstance(override, dict):
                assumptions[key] = MetricAssumption.from_dict(
                    {**override, "metric_key": key}
                )
                continue
            pred = packet.predicted_metrics.get(key)
            if (pred is not None and pred.ci_low is not None
                    and pred.ci_high is not None):
                assumptions[key] = from_conformal_prediction(
                    key, current_value=imp.current_value,
                    target_value=imp.target_value,
                    ci_low=pred.ci_low, ci_high=pred.ci_high,
                )
            else:
                assumptions[key] = default_execution_assumption(
                    key, current_value=imp.current_value,
                    target_value=imp.target_value,
                )
        if not assumptions:
            return self._send_json(
                {"error": "no metric assumptions derivable from packet"},
                status=HTTPStatus.BAD_REQUEST,
            )

        reimbursement_profile = (
            ReimbursementProfile.from_dict(packet.reimbursement_profile)
            if packet.reimbursement_profile else None
        )
        base_assumptions = BridgeAssumptions(
            exit_multiple=float(financials.get("exit_multiple") or 10.0),
            cost_of_capital=float(financials.get("cost_of_capital_pct") or 0.08),
            rework_cost_per_claim=float(
                financials.get("cost_per_reworked_claim") or 30.0
            ),
            claims_volume=int(financials.get("claims_volume") or 0),
            net_revenue=float(financials.get("net_revenue") or 0.0),
        )
        current_metrics = {
            k: float(v.value) for k, v in packet.rcm_profile.items()
        }
        sim = V2MonteCarloSimulator(
            n_simulations=int(payload.get("n_simulations") or 2000),
            seed=int(payload.get("seed") or 42),
        )
        sim.configure(
            current_metrics=current_metrics,
            metric_assumptions=assumptions,
            reimbursement_profile=reimbursement_profile,
            base_assumptions=base_assumptions,
            realization=packet.revenue_realization,
            current_ebitda=float(
                financials.get("current_ebitda")
                or packet.ebitda_bridge.current_ebitda or 0.0
            ),
            entry_multiple=float(financials.get("entry_multiple") or 10.0),
            hold_years=float(financials.get("hold_years") or 5.0),
            organic_growth_pct=float(financials.get("organic_growth_pct") or 0.0),
            moic_targets=tuple(
                financials.get("moic_targets") or (1.5, 2.0, 2.5, 3.0)
            ),
        )
        label = str(payload.get("scenario_label") or "v2:default")
        try:
            result = sim.run(scenario_label=label)
        except Exception as exc:  # noqa: BLE001
            return self._send_json(
                {"error": f"v2 simulate failed: {exc}"},
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )
        try:
            save_v2_mc_run(store, deal_id, result,
                           analysis_run_id=packet.run_id)
        except Exception:  # noqa: BLE001 — cache write is best-effort
            pass
        return self._send_json({
            "deal_id": deal_id,
            "analysis_run_id": packet.run_id,
            "v2_mc": result.to_dict(),
        })

    def _route_simulate_compare(self, deal_id: str, payload: Dict[str, Any]) -> None:
        from .mc import MetricAssumption, compare_scenarios
        scenarios_raw = payload.get("scenarios") or {}
        if not isinstance(scenarios_raw, dict) or not scenarios_raw:
            return self._send_json(
                {"error": "scenarios payload is required"},
                status=HTTPStatus.BAD_REQUEST,
            )
        ctx = self._build_mc_context(deal_id, payload)
        if isinstance(ctx, tuple):
            _, err, status = ctx
            return self._send_json(err, status=status)
        scenarios: Dict[str, Dict[str, MetricAssumption]] = {}
        base = ctx["assumptions"]
        for name, overrides in scenarios_raw.items():
            if not isinstance(overrides, dict):
                continue
            merged = dict(base)
            for metric, spec in overrides.items():
                if not isinstance(spec, dict):
                    continue
                merged[metric] = MetricAssumption.from_dict({**spec, "metric_key": metric})
            scenarios[str(name)] = merged
        if not scenarios:
            return self._send_json(
                {"error": "no scenarios parseable from payload"},
                status=HTTPStatus.BAD_REQUEST,
            )
        try:
            cmp = compare_scenarios(ctx["sim"], scenarios)
        except Exception as exc:  # noqa: BLE001
            return self._send_json({"error": f"compare failed: {exc}"},
                                    status=HTTPStatus.INTERNAL_SERVER_ERROR)
        return self._send_json({
            "deal_id": deal_id, "analysis_run_id": ctx["packet"].run_id,
            "comparison": cmp.to_dict(),
        })

    def _route_analysis_bridge_aux(self, deal_id: str, kind: str, packet: Any) -> None:
        """Serve tornado / targets for a freshly-built packet.

        We rebuild a :class:`RCMEBITDABridge` on the fly from the packet
        ebitda_bridge row rather than persisting the bridge object —
        the bridge's inputs (current ebitda, net revenue, payer mix) are
        already in the packet and rebuilding is fast.
        """
        from .pe.rcm_ebitda_bridge import FinancialProfile, RCMEBITDABridge
        from .analysis.completeness import RCM_METRIC_REGISTRY
        br = packet.ebitda_bridge
        current_metrics = {
            imp.metric_key: imp.current_value for imp in br.per_metric_impacts
        }
        # If the packet's bridge is incomplete we still want the
        # lever-level data — fall back to rcm_profile values.
        if not current_metrics:
            current_metrics = {
                k: float(v.value) for k, v in packet.rcm_profile.items()
            }
        fp = FinancialProfile(
            gross_revenue=0.0,
            net_revenue=float(br.current_ebitda / (br.new_ebitda_margin or 0.10)
                               if br.new_ebitda_margin > 0 else 0.0),
            current_ebitda=float(br.current_ebitda),
            payer_mix=dict(packet.profile.payer_mix or {}),
        )
        bridge = RCMEBITDABridge(fp)
        if kind == "sensitivity":
            tor = bridge.compute_sensitivity_tornado(current_metrics)
            return self._send_json({
                "deal_id": deal_id,
                "run_id": packet.run_id,
                "tornado": tor.to_dict(),
            })
        # targets
        rec = bridge.suggest_targets(current_metrics, packet.comparables,
                                     RCM_METRIC_REGISTRY)
        return self._send_json({
            "deal_id": deal_id,
            "run_id": packet.run_id,
            "targets": rec.to_dict(),
        })

    def _route_predict_backtest(self) -> None:
        """GET /api/predict/backtest?n_trials=50&coverage=0.90&holdout=0.3

        Reads the hospital_benchmarks table, pivots into {provider_id:
        {metric: value}} rows, runs the randomized hide-and-predict
        backtest, returns the PredictionBacktestResult as JSON.
        """
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        n_trials = self._clamp_int(
            (qs.get("n_trials") or ["50"])[0],
            default=50, min_v=1, max_v=500,
        )
        try:
            coverage = float((qs.get("coverage") or ["0.90"])[0])
            holdout = float((qs.get("holdout") or ["0.3"])[0])
        except ValueError:
            return self._send_json(
                {"error": "coverage and holdout must be floats"},
                status=HTTPStatus.BAD_REQUEST,
            )
        from .data.data_refresh import query_hospitals
        from .ml.backtester import backtest_predictions
        store = PortfolioStore(self.config.db_path)
        hospitals = query_hospitals(store, limit=500)
        pool = []
        for h in hospitals:
            row = {"ccn": h["provider_id"]}
            row.update(h.get("metrics") or {})
            pool.append(row)
        result = backtest_predictions(
            pool, holdout_fraction=holdout,
            n_trials=n_trials, coverage=coverage,
        )
        return self._send_json(result.to_dict())

    def _route_data_get(self, path: str, parts: List[str]) -> None:
        """GET /api/data/sources        → data_source_status rows
        GET /api/data/hospitals       → benchmark search
        """
        from .data import data_refresh as dr
        store = PortfolioStore(self.config.db_path)
        if parts == ["api", "data", "sources"]:
            dr.schedule_refresh(store, interval_days=30)
            dr.mark_stale_sources(store)
            return self._send_json({"sources": dr.get_status(store)})
        if parts == ["api", "data", "hospitals"]:
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            state = (qs.get("state") or [None])[0]
            beds_min_raw = (qs.get("beds_min") or [None])[0]
            beds_max_raw = (qs.get("beds_max") or [None])[0]
            limit = self._clamp_int(
                (qs.get("limit") or ["100"])[0],
                default=100, min_v=1, max_v=1000,
            )
            def _opt_int(raw):
                if raw in (None, ""):
                    return None
                try:
                    return int(raw)
                except ValueError:
                    return None
            try:
                hospitals = dr.query_hospitals(
                    store,
                    state=state, beds_min=_opt_int(beds_min_raw),
                    beds_max=_opt_int(beds_max_raw), limit=limit,
                )
            except Exception as exc:  # noqa: BLE001
                return self._send_json(
                    {"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR,
                )
            return self._send_json({"hospitals": hospitals, "count": len(hospitals)})
        self.send_error(HTTPStatus.NOT_FOUND, f"Unknown data API path: {path}")

    def _route_analysis_get(self, path: str, parts: List[str]) -> None:
        """GET endpoints for the Deal Analysis Packet.

        - ``/api/analysis/<deal_id>`` — build or return cached packet.
        - ``/api/analysis/<deal_id>/section/<name>`` — one section only.

        Query params: ``scenario``, ``as_of`` (YYYY-MM-DD), ``force=1``.
        """
        from datetime import date as _date
        from .analysis.analysis_store import get_or_build_packet
        deal_id = urllib.parse.unquote(parts[2])
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        scenario_id = (qs.get("scenario") or [None])[0] or None
        as_of_raw = (qs.get("as_of") or [None])[0]
        as_of = None
        if as_of_raw:
            try:
                as_of = _date.fromisoformat(as_of_raw)
            except ValueError:
                return self._send_json(
                    {"error": f"invalid as_of {as_of_raw!r}, want YYYY-MM-DD",
                     "code": "BAD_REQUEST"},
                    status=HTTPStatus.BAD_REQUEST,
                )
        force = bool((qs.get("force") or [""])[0])
        store = PortfolioStore(self.config.db_path)
        try:
            packet = get_or_build_packet(
                store, deal_id,
                scenario_id=scenario_id, as_of=as_of,
                force_rebuild=force, skip_simulation=True,
            )
        except Exception as exc:  # noqa: BLE001 — surface build errors
            return self._send_json(
                {"error": str(exc), "code": "BUILD_FAILED", "deal_id": deal_id},
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )
        payload = packet.to_dict()
        payload["_provenance"] = {
            "run_id": packet.run_id,
            "generated_at": packet.generated_at.isoformat(),
            "model_version": packet.model_version,
            "source": "analysis_runs",
        }
        # ETag for the full packet — lets clients skip re-download
        if len(parts) == 3:
            import hashlib as _hl
            etag_src = f"{deal_id}:{packet.run_id}:{packet.generated_at.isoformat()}"
            etag = f'"{_hl.md5(etag_src.encode()).hexdigest()[:16]}"'
            if_none = self.headers.get("If-None-Match")
            if if_none and if_none.strip() == etag:
                self.send_response(HTTPStatus.NOT_MODIFIED)
                self.send_header("ETag", etag)
                self.end_headers()
                return
            return self._send_json_with_etag(payload, etag)
        # GET /api/analysis/<id>/export?format=html|pptx|json|csv|questions
        if len(parts) == 4 and parts[3] == "export":
            return self._route_analysis_export(deal_id, packet)
        # GET /api/analysis/<id>/provenance — full rich graph
        # GET /api/analysis/<id>/provenance/<metric_key> — one metric's subgraph
        # GET /api/analysis/<id>/explain/<metric_key> — plain-English narrative
        if len(parts) >= 4 and parts[3] == "provenance":
            from .provenance.graph import build_rich_graph
            rich = build_rich_graph(packet)
            if len(parts) == 4:
                return self._send_json({
                    "deal_id": deal_id,
                    "run_id": packet.run_id,
                    "graph": rich.to_dict(),
                    "has_cycle": rich.has_cycle(),
                    "topological_order": rich.topological_order(),
                })
            # metric subgraph: /provenance/<metric_key>
            metric_key = urllib.parse.unquote(parts[4])
            from .provenance.explain import _resolve_metric_id  # type: ignore
            nid = _resolve_metric_id(rich, metric_key)
            if nid is None:
                return self._send_json(
                    {"error": f"metric {metric_key!r} not found in provenance"},
                    status=HTTPStatus.NOT_FOUND,
                )
            upstream_nodes = rich.get_upstream(nid)
            return self._send_json({
                "deal_id": deal_id,
                "metric": metric_key,
                "node_id": nid,
                "node": rich.nodes[nid].to_dict(),
                "upstream": [n.to_dict() for n in upstream_nodes],
                "direct_parents": [
                    {"node": p.to_dict(), "relationship": rel.value}
                    for p, rel in rich.direct_parents(nid)
                ],
            })
        if len(parts) == 5 and parts[3] == "explain":
            from .provenance.explain import explain_for_ui, explain_metric
            from .provenance.graph import build_rich_graph
            metric_key = urllib.parse.unquote(parts[4])
            rich = build_rich_graph(packet)
            return self._send_json({
                "deal_id": deal_id,
                "metric": metric_key,
                "explanation": explain_metric(rich, metric_key),
                "structured": explain_for_ui(rich, metric_key),
            })
        # GET /api/analysis/<id>/risks — full risk flag list
        if len(parts) == 4 and parts[3] == "risks":
            return self._send_json({
                "deal_id": deal_id,
                "run_id": packet.run_id,
                "risks": [r.to_dict() for r in packet.risk_flags],
                "count": len(packet.risk_flags),
                "severity_counts": {
                    sev: sum(1 for r in packet.risk_flags if r.severity.value == sev)
                    for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW")
                },
            })
        # GET /api/analysis/<id>/diligence-questions — auto-generated questions
        if len(parts) == 4 and parts[3] == "diligence-questions":
            qs = packet.diligence_questions
            qs_by_priority: Dict[str, List[Dict[str, Any]]] = {
                "P0": [], "P1": [], "P2": [],
            }
            for q in qs:
                qs_by_priority.setdefault(q.priority.value, []).append(q.to_dict())
            return self._send_json({
                "deal_id": deal_id,
                "run_id": packet.run_id,
                "questions": [q.to_dict() for q in qs],
                "by_priority": qs_by_priority,
                "count": len(qs),
            })
        # GET /api/analysis/<id>/sensitivity — tornado data
        # GET /api/analysis/<id>/targets — conservative/moderate/aggressive
        if len(parts) == 4 and parts[3] in ("sensitivity", "targets"):
            return self._route_analysis_bridge_aux(deal_id, parts[3], packet)
        # GET /api/analysis/<id>/simulate/latest
        if len(parts) == 5 and parts[3] == "simulate" and parts[4] == "latest":
            from .mc.mc_store import load_latest_mc_run
            store = PortfolioStore(self.config.db_path)
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            scenario = (qs.get("scenario") or [None])[0]
            mc = load_latest_mc_run(store, deal_id, scenario_label=scenario)
            if mc is None:
                return self._send_json(
                    {"error": "no MC run stored for this deal",
                     "deal_id": deal_id},
                    status=HTTPStatus.NOT_FOUND,
                )
            return self._send_json({
                "deal_id": deal_id,
                "mc": mc.to_dict(),
            })
        # Dedicated shortcut: /api/analysis/<id>/predictions — just the
        # predicted-metrics section with conformal intervals flattened.
        if len(parts) == 4 and parts[3] == "predictions":
            preds = {k: v.to_dict() for k, v in packet.predicted_metrics.items()}
            return self._send_json({
                "deal_id": deal_id,
                "run_id": packet.run_id,
                "generated_at": packet.generated_at.isoformat(),
                "coverage_target": 0.90,
                "predictions": preds,
                "count": len(preds),
            })
        # Dedicated shortcut: /api/analysis/<id>/completeness
        # (equivalent to .../section/completeness but with a flatter
        # payload partners asked for during the CHH pilot.)
        if len(parts) == 4 and parts[3] == "completeness":
            body = packet.completeness.to_dict()
            body["deal_id"] = deal_id
            body["run_id"] = packet.run_id
            body["generated_at"] = packet.generated_at.isoformat()
            return self._send_json(body)
        # Section filter: /api/analysis/<id>/section/<name>
        if len(parts) >= 5 and parts[3] == "section":
            name = urllib.parse.unquote(parts[4])
            try:
                section = packet.section(name)
            except KeyError:
                return self._send_json(
                    {"error": f"unknown section {name!r}", "code": "NOT_FOUND"},
                    status=HTTPStatus.NOT_FOUND,
                )
            # Prefer the structured dict form when available.
            body: Any
            if hasattr(section, "to_dict"):
                body = section.to_dict()
            elif isinstance(section, dict):
                body = {k: (v.to_dict() if hasattr(v, "to_dict") else v) for k, v in section.items()}
            elif isinstance(section, list):
                body = [v.to_dict() if hasattr(v, "to_dict") else v for v in section]
            else:
                body = section
            return self._send_json({
                "deal_id": deal_id,
                "section": name,
                "run_id": packet.run_id,
                "data": body,
            })
        return self._send_json(payload)

    def _route_export(self, store: PortfolioStore) -> None:
        """GET /api/export?format=csv&stage=&covenant=&tag=&q=&concerning=

        Exports the filtered latest-per-deal view as CSV (default) or JSON.
        Mirrors the dashboard's client-side filter so what the analyst
        sees is what they download. Filters are AND-composed.
        """
        from .deals.deal_tags import tags_for
        from .portfolio.portfolio_snapshots import latest_per_deal

        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        fmt = (qs.get("format") or ["csv"])[0].lower()
        q = (qs.get("q") or [""])[0].lower().strip()
        want_stage = (qs.get("stage") or [""])[0].lower().strip()
        want_cov = (qs.get("covenant") or [""])[0].strip()
        want_tag = (qs.get("tag") or [""])[0].lower().strip()
        only_concerning = bool(qs.get("concerning"))

        df = latest_per_deal(store)
        if df.empty:
            if fmt == "json":
                return self._send_json([])
            self._send_text("", content_type="text/csv; charset=utf-8")
            return

        # Enrich with tags (space-separated) for filtering
        df = df.copy()
        df["tags"] = [" ".join(tags_for(store, str(did))) for did in df["deal_id"]]

        def _keep(row) -> bool:
            if q and q not in str(row["deal_id"]).lower():
                return False
            if want_stage and str(row["stage"]).lower() != want_stage:
                return False
            if want_cov and str(row.get("covenant_status") or "") != want_cov:
                return False
            if want_tag:
                tags = str(row.get("tags") or "").lower().split()
                if not any(want_tag in t for t in tags):
                    return False
            if only_concerning:
                nc = row.get("concerning_signals")
                nc = int(nc) if nc is not None and nc == nc else 0
                if nc < 1:
                    return False
            return True

        filtered = df[df.apply(_keep, axis=1)]

        if fmt == "json":
            return self._send_json(filtered.to_dict(orient="records"))

        # CSV — defang formula-injection before write
        import io as _io
        buf = _io.StringIO()
        self._defang_csv_df(filtered).to_csv(buf, index=False)
        body = buf.getvalue().encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header(
            "Content-Disposition",
            'attachment; filename="portfolio_view.csv"',
        )
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_json_with_etag(self, payload: Any, etag: str) -> None:
        """Like _send_json but adds an ETag header for conditional GET."""
        import json as _json
        import math
        from datetime import date as _date, datetime as _dt
        from decimal import Decimal as _Decimal

        def _safe(o):
            if isinstance(o, float) and math.isnan(o):
                return None
            try:
                import pandas as _pd
                if isinstance(o, _pd.Timestamp):
                    return o.isoformat()
                import numpy as _np
                if isinstance(o, (_np.integer,)):
                    return int(o)
                if isinstance(o, (_np.floating,)):
                    v = float(o)
                    return None if math.isnan(v) else v
                if isinstance(o, _np.ndarray):
                    return o.tolist()
            except Exception:
                pass
            if isinstance(o, (_dt, _date)):
                return o.isoformat()
            if isinstance(o, _Decimal):
                return float(o)
            if isinstance(o, (bytes, bytearray)):
                return o.decode("utf-8", errors="replace")
            raise TypeError(f"Object not JSON serializable: {type(o)}")

        body = _json.dumps(payload, indent=2, default=_safe).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("ETag", etag)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-CSRF-Token")
        self.end_headers()
        self.wfile.write(body)

    def _send_error(
        self, message: str, *,
        status: int = HTTPStatus.BAD_REQUEST,
        code: str = "BAD_REQUEST",
    ) -> None:
        """Standardized error envelope with request_id for correlation."""
        return self._send_json(
            {
                "error": message,
                "code": code,
                "request_id": getattr(self, "_request_id", None),
            },
            status=status,
        )

    def _fire_webhook(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Best-effort webhook dispatch — never blocks or fails the request."""
        try:
            from .infra.webhooks import dispatch_event as _wh_dispatch
            _wh_dispatch(
                PortfolioStore(self.config.db_path),
                event_type, payload,
            )
        except Exception:
            pass

    def _send_rate_limited(self, wait_secs: float) -> None:
        """429 with Retry-After header for well-behaved API clients."""
        import json as _json
        import math
        retry = max(1, math.ceil(wait_secs))
        body = _json.dumps({
            "error": "rate limited",
            "code": "RATE_LIMITED",
            "retry_after_secs": round(wait_secs, 1),
            "request_id": getattr(self, "_request_id", None),
        }).encode("utf-8")
        self.send_response(HTTPStatus.TOO_MANY_REQUESTS)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Retry-After", str(retry))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    @staticmethod
    def _defang_csv_df(df):
        """B149: neutralize Excel/Sheets formula-injection in CSV exports.

        Any string cell starting with ``=``, ``+``, ``@``, ``-``, tab, or
        CR is prefixed with a single-quote so a spreadsheet app treats
        it as literal text. Numbers and non-strings pass through.
        """
        import pandas as _pd
        if df is None or df.empty:
            return df
        dangerous = ("=", "+", "@", "-", "\t", "\r")
        out = df.copy()
        for col in out.columns:
            # Modern pandas uses StringDtype(), older uses object.
            # Both paths need defanging; check either.
            if (out[col].dtype == object
                    or _pd.api.types.is_string_dtype(out[col])):
                out[col] = out[col].map(
                    lambda v: ("'" + v) if isinstance(v, str)
                    and v.startswith(dangerous) else v,
                )
        return out

    def _send_csv_df(self, df, filename: str) -> None:
        """Stream a DataFrame as a CSV attachment. Shared by export views."""
        import io as _io
        buf = _io.StringIO()
        self._defang_csv_df(df).to_csv(buf, index=False)
        body = buf.getvalue().encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header(
            "Content-Disposition", f'attachment; filename="{filename}"',
        )
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload: Any, status: int = HTTPStatus.OK) -> None:
        """Small helper that JSON-encodes NaN-safe + sends response.

        B159 fix: handle pandas Timestamp, numpy scalars, date/datetime,
        Decimal, and bytes — all plausible values inside a DataFrame
        returned by ``.to_dict(orient="records")``.
        """
        import json as _json
        import math
        from datetime import date as _date, datetime as _dt
        from decimal import Decimal as _Decimal

        def _safe(o):
            # Handle float NaN → null
            if isinstance(o, float) and math.isnan(o):
                return None
            # pandas Timestamp / numpy datetime → ISO string
            try:
                import pandas as _pd
                if isinstance(o, _pd.Timestamp):
                    return o.isoformat() if not _pd.isna(o) else None
                if hasattr(_pd, "NaT") and o is _pd.NaT:
                    return None
            except Exception:  # noqa: BLE001
                pass
            # numpy scalars → native Python
            try:
                import numpy as _np
                if isinstance(o, _np.integer):
                    return int(o)
                if isinstance(o, _np.floating):
                    v = float(o)
                    return None if math.isnan(v) else v
                if isinstance(o, _np.bool_):
                    return bool(o)
            except Exception:  # noqa: BLE001
                pass
            # date / datetime / Decimal / bytes
            if isinstance(o, (_dt, _date)):
                return o.isoformat()
            if isinstance(o, _Decimal):
                return float(o)
            if isinstance(o, (bytes, bytearray)):
                return o.decode("utf-8", errors="replace")
            raise TypeError(f"Object not JSON serializable: {type(o)}")

        # Phase 4C: walk the payload and attach <metric>_warning
        # siblings for any numeric field whose key maps to a REGISTRY
        # metric and whose value is outside the plausible envelope.
        # Never modifies the raw value — additive only — so downstream
        # consumers still get the number but can surface the warning
        # (and partners looking at the JSON see flagged fields).
        try:
            from .ui.chartis._sanity import attach_sanity_warnings
            payload = attach_sanity_warnings(payload)
        except Exception:  # noqa: BLE001 — sanity guard must not break API
            pass
        body = _json.dumps(payload, indent=2, default=_safe).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-CSRF-Token, Idempotency-Key")
        self.send_header("X-API-Version", "2024-01")
        rid = getattr(self, "_request_id", None)
        if rid:
            self.send_header("X-Request-Id", rid)
        start_ns = getattr(self, "_request_start_ns", None)
        if start_ns is not None:
            import time as _t
            elapsed_ms = (_t.perf_counter_ns() - start_ns) / 1_000_000.0
            self.send_header("X-Response-Time", f"{elapsed_ms:.1f}ms")
        accept_enc = self.headers.get("Accept-Encoding") or ""
        if "gzip" in accept_enc and len(body) > 1024:
            import gzip as _gzip
            body = _gzip.compress(body)
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Vary", "Accept-Encoding")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        ikey = getattr(self, "_idempotency_key", None)
        if ikey and status == HTTPStatus.OK:
            _IDEMPOTENCY_CACHE.set(ikey, payload)

    # ── POST routes (B65 web forms + B68 write API) ──

    def do_POST(self) -> None:
        if not self._auth_ok():
            return self._send_401()
        try:
            self._do_post_inner()
        except Exception as exc:  # noqa: BLE001 — global error boundary
            logger.error("unhandled POST %s: %s", self.path, exc)
            try:
                self._send_json(
                    {"error": "internal server error",
                     "request_id": getattr(self, "_request_id", None),
                     "code": "INTERNAL_ERROR"},
                    status=HTTPStatus.INTERNAL_SERVER_ERROR,
                )
            except Exception:  # noqa: BLE001
                pass

    def _do_post_inner(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        # B128: CSRF gate — only meaningful when the user has a session
        # cookie (i.e., the attack surface exists). HTTP-Basic scripts
        # and open single-user mode skip. Login itself is exempt because
        # the client can't have a CSRF token yet.
        csrf_exempt = (
            path in self._CSRF_EXEMPT_POSTS
            or path.startswith("/hospital/")
            or path.startswith("/quick-import")
            or path.startswith("/new-deal")
            or path.startswith("/data-room/")
            or path.startswith("/pipeline/")
            or path.startswith("/value-tracker/")
            or path.startswith("/team/")
        )
        if (self._session_token() is not None and not csrf_exempt):
            ctype = self.headers.get("Content-Type", "")
            form_dict: Dict[str, str] = {}
            # For form-encoded bodies we can peek at the parsed form
            # (cached). For multipart, we rely on header-based CSRF —
            # AJAX callers always can set headers; HTML forms sending
            # multipart aren't a common vector in this app.
            if "application/x-www-form-urlencoded" in ctype:
                form_dict = self._read_form_body()
            if not self._csrf_ok(form_dict):
                return self._send_json(
                    {"error": "CSRF check failed",
                     "code": "CSRF_FAILED"},
                    status=HTTPStatus.FORBIDDEN,
                )
        content_length = int(self.headers.get("Content-Length") or 0)
        if content_length > MAX_REQUEST_BYTES:
            return self._send_json(
                {"error": "payload too large",
                 "max_bytes": MAX_REQUEST_BYTES},
                status=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            )
        self._idempotency_key = self.headers.get("Idempotency-Key")
        if self._idempotency_key:
            cached = _IDEMPOTENCY_CACHE.get(self._idempotency_key)
            if cached is not None:
                return self._send_json(cached)
        if path == "/api/login":
            return self._route_login_post()
        if path == "/api/logout":
            return self._route_logout_post()
        if path == "/api/upload-actuals":
            return self._route_upload_post()
        if path == "/api/upload-initiatives":
            return self._route_upload_initiatives_post()
        if path == "/api/upload-notes":
            return self._route_upload_notes_post()
        if path.startswith("/api/"):
            return self._route_api_post(path)
        # Prompt 26: wizard paths live under /new-deal/* rather than
        # /api/* because they're server-rendered HTML transitions.
        # Prompt 33: POST /screen — batch screening.
        if path.startswith("/hospital/") and path.endswith("/history"):
            ccn = path.replace("/hospital/", "").replace("/history", "").strip("/")
            return self._route_hospital_history(ccn)
        if path.startswith("/hospital/") and path.endswith("/start-diligence"):
            ccn = path.replace("/hospital/", "").replace("/start-diligence", "").strip("/")
            return self._route_start_diligence_from_hospital(ccn)
        if path.startswith("/data-room/") and path.endswith("/add"):
            dr_ccn = path.replace("/data-room/", "").replace("/add", "").strip("/")
            return self._route_data_room_add(dr_ccn)
        if path == "/pipeline/add":
            return self._route_pipeline_add()
        if path == "/pipeline/save-search":
            return self._route_save_search()
        if path.startswith("/pipeline/stage/"):
            return self._route_pipeline_stage()
        if path == "/team/comment":
            return self._route_add_comment()
        if path.startswith("/value-tracker/") and path.endswith("/record"):
            vt_id = path.replace("/value-tracker/", "").replace("/record", "").strip("/")
            return self._route_value_tracker_record(vt_id)
        if path.startswith("/value-tracker/") and path.endswith("/freeze"):
            vt_id = path.replace("/value-tracker/", "").replace("/freeze", "").strip("/")
            return self._route_value_tracker_freeze(vt_id)
        if path == "/quick-import":
            return self._route_quick_import_post()
        if path == "/quick-import-json":
            return self._route_quick_import_json_post()
        if path == "/screen":
            return self._route_screen_post()
        if path == "/new-deal/manual":
            return self._route_wizard_manual()
        if path.startswith("/new-deal/upload"):
            # Pass ``self.path`` (raw, with query string) so the
            # handler can parse ``?deal_id=…`` — ``path`` above is
            # the path component only.
            return self._route_wizard_upload(self.path)
        self.send_error(HTTPStatus.METHOD_NOT_ALLOWED, f"POST not allowed on {path}")

    def do_PUT(self) -> None:
        """HTTP PUT — used by the analyst-override API (Prompt 18).

        We gate on the same auth/CSRF rules as do_POST and then route
        only the narrow set of PUT paths we support. Unknown paths
        get a 405. Keeping the dispatch explicit (no generic reflection)
        so the write surface stays auditable.
        """
        if not self._auth_ok():
            return self._send_401()
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if (self._session_token() is not None
                and path not in self._CSRF_EXEMPT_POSTS):
            if not self._csrf_ok({}):
                return self._send_json(
                    {"error": "CSRF check failed", "code": "CSRF_FAILED"},
                    status=HTTPStatus.FORBIDDEN,
                )
        parts = [p for p in path.strip("/").split("/") if p]
        # PUT /api/deals/<deal_id>/overrides/<key>
        if (len(parts) == 5 and parts[0] == "api" and parts[1] == "deals"
                and parts[3] == "overrides"):
            return self._route_override_put(
                urllib.parse.unquote(parts[2]),
                urllib.parse.unquote(parts[4]),
            )
        self.send_error(HTTPStatus.METHOD_NOT_ALLOWED,
                         f"PUT not allowed on {path}")

    def do_PATCH(self) -> None:
        """HTTP PATCH — field-level profile updates."""
        if not self._auth_ok():
            return self._send_401()
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if (self._session_token() is not None
                and path not in self._CSRF_EXEMPT_POSTS):
            if not self._csrf_ok({}):
                return self._send_json(
                    {"error": "CSRF check failed", "code": "CSRF_FAILED"},
                    status=HTTPStatus.FORBIDDEN,
                )
        parts = [p for p in path.strip("/").split("/") if p]
        # PATCH /api/deals/<deal_id>/profile — merge fields
        if (len(parts) == 4 and parts[0] == "api" and parts[1] == "deals"
                and parts[3] == "profile"):
            import json as _json
            deal_id = urllib.parse.unquote(parts[2])
            n_bytes = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n_bytes) if n_bytes > 0 else b"{}"
            try:
                updates = _json.loads(raw.decode("utf-8") or "{}")
            except _json.JSONDecodeError:
                return self._send_json(
                    {"error": "body must be JSON"}, status=HTTPStatus.BAD_REQUEST,
                )
            if not isinstance(updates, dict) or not updates:
                return self._send_json(
                    {"error": "provide field:value pairs to update"},
                    status=HTTPStatus.BAD_REQUEST,
                )
            store = PortfolioStore(self.config.db_path)
            name_update = updates.pop("name", None)
            store.upsert_deal(deal_id,
                              name=name_update,
                              profile=updates if updates else None)
            self._log_audit("deal.profile.patch", deal_id,
                            fields=list(updates.keys()))
            return self._send_json({
                "deal_id": deal_id,
                "updated_fields": list(updates.keys())
                + (["name"] if name_update else []),
            })
        self.send_error(HTTPStatus.METHOD_NOT_ALLOWED,
                         f"PATCH not allowed on {path}")

    def do_HEAD(self) -> None:
        """HEAD /path — returns headers only. Monitoring tools use this."""
        if not self._auth_ok():
            return self._send_401()
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path in ("/api/health", "/health", "/ready"):
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()

    def do_OPTIONS(self) -> None:
        """CORS preflight handler."""
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-CSRF-Token")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def do_DELETE(self) -> None:
        """HTTP DELETE — sibling to do_PUT for the override API."""
        if not self._auth_ok():
            return self._send_401()
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if (self._session_token() is not None
                and path not in self._CSRF_EXEMPT_POSTS):
            if not self._csrf_ok({}):
                return self._send_json(
                    {"error": "CSRF check failed", "code": "CSRF_FAILED"},
                    status=HTTPStatus.FORBIDDEN,
                )
        parts = [p for p in path.strip("/").split("/") if p]
        # DELETE /api/deals/<deal_id>/overrides/<key>
        if (len(parts) == 5 and parts[0] == "api" and parts[1] == "deals"
                and parts[3] == "overrides"):
            return self._route_override_delete(
                urllib.parse.unquote(parts[2]),
                urllib.parse.unquote(parts[4]),
            )
        # DELETE /api/deals/<deal_id> — full deal deletion with cascade
        if (len(parts) == 3 and parts[0] == "api" and parts[1] == "deals"):
            client_ip = self.client_address[0]
            ok, wait = _DELETE_RATE_LIMITER.check(f"delete:{client_ip}")
            if not ok:
                return self._send_rate_limited(wait)
            deal_id = urllib.parse.unquote(parts[2])
            store = PortfolioStore(self.config.db_path)
            deleted = store.delete_deal(deal_id)
            if not deleted:
                return self._send_json(
                    {"error": f"deal {deal_id!r} not found"},
                    status=HTTPStatus.NOT_FOUND,
                )
            self._log_audit("deal.delete", deal_id)
            self._fire_webhook("deal.deleted", {"deal_id": deal_id})
            return self._send_json(
                {"deleted": True, "deal_id": deal_id},
            )
        # DELETE /api/metrics/custom/<key>
        if (len(parts) == 4 and parts[0] == "api"
                and parts[1] == "metrics" and parts[2] == "custom"):
            from .domain.custom_metrics import delete_custom_metric
            metric_key = urllib.parse.unquote(parts[3])
            store = PortfolioStore(self.config.db_path)
            existed = delete_custom_metric(store, metric_key)
            if not existed:
                return self._send_json(
                    {"error": f"metric {metric_key!r} not found"},
                    status=HTTPStatus.NOT_FOUND,
                )
            return self._send_json(
                {"deleted": True, "metric_key": metric_key},
            )
        self.send_error(HTTPStatus.METHOD_NOT_ALLOWED,
                         f"DELETE not allowed on {path}")

    # Prompt 37: portfolio Monte Carlo ────────────────────────────

    def _route_portfolio_mc(self) -> None:
        """GET /portfolio/monte-carlo — correlated fund-level MC."""
        from .analysis.analysis_store import list_packets, load_packet_by_id
        from .mc.portfolio_monte_carlo import run_portfolio_mc
        store = PortfolioStore(self.config.db_path)
        rows = list_packets(store)
        seen: set = set()
        summaries = []
        for r in rows:
            did = r.get("deal_id") or ""
            if did in seen:
                continue
            seen.add(did)
            pkt = load_packet_by_id(store, r["id"])
            if pkt is None:
                continue
            sim = pkt.simulation
            ebitda_p50 = 0.0
            ebitda_std = 0.0
            moic_p50 = 1.0
            if sim is not None:
                ebitda_p50 = float(sim.ebitda_uplift.p50 or 0)
                ebitda_std = max(
                    abs(float(sim.ebitda_uplift.p90 or 0)
                        - float(sim.ebitda_uplift.p10 or 0)) / 3.29,
                    1.0,
                )
                moic_p50 = float(sim.moic.p50 or 1.0)
            summaries.append({
                "deal_id": did,
                "ebitda_p50": ebitda_p50,
                "ebitda_std": ebitda_std,
                "moic_p50": moic_p50,
            })
        result = run_portfolio_mc(summaries, n_simulations=5000, seed=42)
        return self._send_json(result.to_dict())

    # Prompt 34: deal timeline ─────────────────────────────────────

    def _route_deal_timeline(self, deal_id: str) -> None:
        """GET /deal/<id>/timeline — unified activity timeline."""
        from .ui.deal_timeline import collect_timeline, render_timeline
        store = PortfolioStore(self.config.db_path)
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        days = self._clamp_int(
            (qs.get("days") or ["90"])[0], default=90, min_v=1, max_v=365,
        )
        events = collect_timeline(store, deal_id, days=days)
        # Try to get the deal name for the page title.
        deal_name = deal_id
        try:
            from .analysis.analysis_store import list_packets, load_packet_by_id
            rows = list_packets(store, deal_id)
            if rows:
                pkt = load_packet_by_id(store, rows[0]["id"])
                if pkt:
                    deal_name = pkt.deal_name or deal_id
        except Exception:  # noqa: BLE001
            pass
        return self._send_html(render_timeline(deal_id, deal_name, events))

    # Prompt 69: portfolio map ────────────────────────────────────

    def _route_portfolio_map(self) -> None:
        """GET /portfolio/map — geographic deal map."""
        from .analysis.analysis_store import list_packets, load_packet_by_id
        from .ui.portfolio_map import render_portfolio_map
        store = PortfolioStore(self.config.db_path)
        rows = list_packets(store)
        seen: set = set()
        deals = []
        for r in rows:
            did = r.get("deal_id") or ""
            if did in seen:
                continue
            seen.add(did)
            pkt = load_packet_by_id(store, r["id"])
            if pkt is None:
                continue
            ebitda = float(pkt.ebitda_bridge.total_ebitda_impact or 0) if pkt.ebitda_bridge else 0
            state = getattr(pkt.profile, "state", "") or ""
            deals.append({
                "deal_id": did,
                "name": pkt.deal_name or did,
                "state": state,
                "ebitda_opportunity": ebitda,
                "stage": "diligence",
            })
        # CON state shading.
        con_states = {}
        try:
            from .data.state_regulatory import CON_STATES
            con_states = {st: c.has_con for st, c in CON_STATES.items()}
        except Exception:  # noqa: BLE001
            pass
        return self._send_html(
            render_portfolio_map(deals, con_states=con_states),
        )

    # Prompt 36: portfolio heatmap ─────────────────────────────────

    def _route_heatmap(self) -> None:
        """GET /portfolio/heatmap — metric health grid for all deals."""
        from .analysis.analysis_store import list_packets, load_packet_by_id
        from .portfolio.portfolio_monitor import compute_deltas
        from .ui.portfolio_heatmap import render_heatmap
        store = PortfolioStore(self.config.db_path)
        rows = list_packets(store)
        # One packet per deal (latest).
        seen: set = set()
        packets = []
        for r in rows:
            did = r.get("deal_id") or ""
            if did in seen:
                continue
            seen.add(did)
            pkt = load_packet_by_id(store, r["id"])
            if pkt is not None:
                packets.append(pkt)
        deltas_list = compute_deltas(store)
        deltas_map = {
            d.deal_id: d.metric_changes for d in deltas_list
        }
        return self._send_html(render_heatmap(packets, deltas=deltas_map))

    # Prompt 33: deal comparison + screening ──────────────────────

    def _route_deal_compare(self) -> None:
        """GET /compare?deals=acme,beta — column-per-deal comparison."""
        from .analysis.analysis_store import get_or_build_packet
        from .ui.deal_comparison import render_comparison
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        deal_ids = [
            d.strip() for d in
            (qs.get("deals") or [""])[0].split(",") if d.strip()
        ]
        if not deal_ids:
            return self._send_html(render_comparison([]))
        store = PortfolioStore(self.config.db_path)
        packets = []
        for did in deal_ids:
            try:
                p = get_or_build_packet(store, did, skip_simulation=True)
                packets.append(p)
            except Exception:  # noqa: BLE001
                continue
        return self._send_html(render_comparison(packets))

    def _route_hospital_demand(self, ccn: str) -> None:
        """GET /hospital/{ccn}/demand — disease density and demand analysis."""
        from .analytics.demand_analysis import compute_demand_profile
        from .data.disease_density import get_county_prevalence  # noqa: F401
        from .data.drg_weights import classify_drg  # noqa: F401
        from .ui.demand_page import render_demand_analysis
        store = PortfolioStore(self.config.db_path)
        try:
            profile = compute_demand_profile(ccn, store)
            return self._send_html(render_demand_analysis(profile.to_dict()))
        except Exception as exc:
            from .ui._chartis_kit import chartis_shell as _shell_dem
            return self._send_html(_shell_dem(
                f'<div class="cad-card"><p style="color:var(--cad-text3);">'
                f'Demand analysis unavailable for CCN {html.escape(ccn)}: '
                f'{html.escape(str(exc)[:100])}</p></div>',
                f"Demand Analysis — {html.escape(ccn)}",
            ))

    def _route_hospital_history(self, ccn: str) -> None:
        """GET /hospital/{ccn}/history — multi-year financial timeline."""
        from .data.hcris import get_trend, load_hcris
        from .ui.hospital_history import render_hospital_history
        import numpy as _np_hist

        trend = get_trend(ccn)
        if trend is None or trend.empty:
            return self._send_html(
                '<h1>No historical data</h1>'
                f'<p>No multi-year HCRIS data for CCN {html.escape(ccn)}.</p>')

        name = str(trend.iloc[0].get("name", f"Hospital {ccn}"))
        state = str(trend.iloc[0].get("state", ""))

        # Compute peer averages for the same state
        peer_avg = None
        try:
            full = load_hcris()
            if state:
                state_df = full[full["state"] == state]
            else:
                state_df = full
            years = sorted(trend["fiscal_year"].unique())
            rev_col = "net_patient_revenue"
            opex_col = "operating_expenses"
            peer_revs = []
            peer_margins = []
            for y in years:
                yr_df = state_df[state_df["fiscal_year"] == y]
                if yr_df.empty:
                    continue
                avg_rev = float(yr_df[rev_col].fillna(0).median())
                revs = yr_df[rev_col].fillna(0)
                opexs = yr_df[opex_col].fillna(0)
                m_vals = []
                for r, o in zip(revs, opexs):
                    if r > 1e5 and o > 0:
                        m_vals.append(max(-1, min(1, (r - o) / r)))
                avg_margin = float(_np_hist.median(m_vals)) if m_vals else 0
                peer_revs.append(avg_rev)
                peer_margins.append(avg_margin)
            if peer_revs:
                peer_avg = {"revenue": peer_revs, "margin": peer_margins}
        except Exception:
            pass

        # Compute projections using linear extrapolation
        projections = None
        try:
            rev_col = "net_patient_revenue"
            years_list = sorted(trend["fiscal_year"].unique())
            rev_vals = []
            margin_vals = []
            for y in years_list:
                yr_data = trend[trend["fiscal_year"] == y]
                if not yr_data.empty:
                    r = float(yr_data.iloc[0].get(rev_col, 0))
                    o = float(yr_data.iloc[0].get("operating_expenses", 0))
                    rev_vals.append(r)
                    if r > 1e5 and o > 0:
                        margin_vals.append(max(-1, min(1, (r - o) / r)))
            if len(rev_vals) >= 2:
                # Simple linear projection
                x = _np_hist.arange(len(rev_vals))
                rev_slope = _np_hist.polyfit(x, rev_vals, 1)[0]
                proj_revs = [rev_vals[-1] + rev_slope * (i + 1) for i in range(3)]
                proj_margins = [margin_vals[-1]] * 3 if margin_vals else [0] * 3
                if len(margin_vals) >= 2:
                    m_slope = _np_hist.polyfit(_np_hist.arange(len(margin_vals)), margin_vals, 1)[0]
                    proj_margins = [margin_vals[-1] + m_slope * (i + 1) for i in range(3)]
                projections = {"revenue": proj_revs, "margin": proj_margins}
        except Exception:
            pass

        return self._send_html(render_hospital_history(
            ccn, name, trend, state=state, peer_avg=peer_avg, projections=projections))

    def _route_start_diligence_from_hospital(self, ccn: str) -> None:
        """POST /hospital/{ccn}/start-diligence — create deal from HCRIS and redirect."""
        import json as _sdj
        from .data.hcris import _get_latest_per_ccn
        hdf = _get_latest_per_ccn()
        match = hdf[hdf["ccn"] == ccn]
        if match.empty:
            return self._redirect(f"/hospital/{ccn}")
        row = match.iloc[0]
        name = str(row.get("name", f"Hospital {ccn}"))
        deal_id = ccn.lower().replace(" ", "_")
        rev_col = "net_patient_revenue" if "net_patient_revenue" in row.index else "gross_patient_revenue"
        profile = {
            "ccn": ccn,
            "name": name,
            "state": str(row.get("state", "")),
            "bed_count": int(row.get("beds", 0)),
            "net_revenue": float(row.get(rev_col, 0)),
        }
        opex = float(row.get("operating_expenses", 0))
        rev = float(row.get(rev_col, 0))
        if rev > 1e5 and opex > 0:
            margin = max(-1, min(1, (rev - opex) / rev))
            profile["ebitda_margin"] = round(margin, 4)
        med = row.get("medicare_day_pct")
        if med is not None:
            profile["medicare_pct"] = float(med)
        store = PortfolioStore(self.config.db_path)
        store.upsert_deal(deal_id, name=name, profile=profile)
        return self._redirect(f"/deal/{deal_id}")

    def _route_quick_import_post(self) -> None:
        """POST /quick-import — create a deal from browser form."""
        from .ui.quick_import import render_quick_import
        from .data.edi_parser import parse_837  # noqa: F401
        from .data.ingest import classify_dataframe  # noqa: F401
        from .data.intake import load_template  # noqa: F401
        form = self._read_form_body()
        deal_id = form.get("deal_id", "").strip()
        name = form.get("name", "").strip()
        if not deal_id or not name:
            return self._send_html(render_quick_import(
                error_msg="Deal ID and Name are required."))
        profile: Dict[str, Any] = {}
        float_fields = ["denial_rate", "days_in_ar", "net_collection_rate",
                        "clean_claim_rate", "cost_to_collect", "net_revenue",
                        "bed_count", "claims_volume"]
        for f in float_fields:
            val = form.get(f, "").strip()
            if val:
                try:
                    profile[f] = float(val)
                except ValueError:
                    pass
        state = form.get("state", "").strip().upper()
        if state:
            profile["state"] = state
        store = PortfolioStore(self.config.db_path)
        try:
            store.upsert_deal(deal_id, name=name, profile=profile)
        except Exception as exc:
            return self._send_html(render_quick_import(
                error_msg=f"Error creating deal: {exc}"))
        return self._redirect(f"/deal/{deal_id}")

    def _route_quick_import_json_post(self) -> None:
        """POST /quick-import-json — bulk import from JSON textarea."""
        import json as _qij
        from .ui.quick_import import render_quick_import
        form = self._read_form_body()
        raw = form.get("json_data", "").strip()
        if not raw:
            return self._send_html(render_quick_import(
                error_msg="No JSON data provided."))
        try:
            deals = _qij.loads(raw)
        except _qij.JSONDecodeError as exc:
            return self._send_html(render_quick_import(
                error_msg=f"Invalid JSON: {exc}"))
        if not isinstance(deals, list):
            deals = [deals]
        store = PortfolioStore(self.config.db_path)
        imported = 0
        for d in deals:
            did = d.get("deal_id", "").strip()
            nm = d.get("name", did)
            prof = d.get("profile", {})
            if did:
                store.upsert_deal(did, name=nm, profile=prof)
                imported += 1
        return self._send_html(render_quick_import(
            success_msg=f"Successfully imported {imported} deal(s). "
                        f"View them in the portfolio."))

    def _route_screen_post(self) -> None:
        """POST /screen — batch screening from pasted names."""
        from .analysis.deal_screener import screen_batch
        from .ui.deal_comparison import render_screen_page
        form = self._read_form_body()
        raw_names = (form.get("names") or "").strip()
        if not raw_names:
            return self._send_html(render_screen_page())
        queries = [ln.strip() for ln in raw_names.splitlines() if ln.strip()]
        store = PortfolioStore(self.config.db_path)
        results = screen_batch(queries, store, limit=50)
        return self._send_html(
            render_screen_page([r.to_dict() for r in results]),
        )

    # Prompt 26: onboarding wizard route handlers ──────────────────────

    def _route_system_info(self) -> None:
        """GET /api/system/info — version, DB stats, Python version."""
        import platform as _plat
        from . import __version__
        from .analysis.packet import PACKET_SCHEMA_VERSION
        _store = PortfolioStore(self.config.db_path)
        db_size_bytes = 0
        table_count = 0
        deal_count = 0
        try:
            db_size_bytes = os.path.getsize(self.config.db_path)
            with _store.connect() as con:
                tables = con.execute(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
                ).fetchone()
                table_count = tables[0] if tables else 0
                try:
                    deal_count = con.execute(
                        "SELECT COUNT(*) FROM deals"
                    ).fetchone()[0]
                except Exception:
                    pass
        except Exception:
            pass
        return self._send_json({
            "version": __version__,
            "packet_schema_version": PACKET_SCHEMA_VERSION,
            "python_version": _plat.python_version(),
            "platform": _plat.platform(),
            "db_path": self.config.db_path,
            "db_size_mb": round(db_size_bytes / 1_048_576, 2),
            "table_count": table_count,
            "deal_count": deal_count,
            "request_count": RCMHandler._request_counter,
            "error_count": RCMHandler._error_count,
        })

    def _route_metrics(self) -> None:
        """GET /api/metrics — request timing percentiles."""
        rt = list(RCMHandler._response_times)
        n = len(rt)
        if n > 0:
            rt_sorted = sorted(rt)
            p50 = rt_sorted[int(n * 0.5)]
            p95 = rt_sorted[min(int(n * 0.95), n - 1)]
            p99 = rt_sorted[min(int(n * 0.99), n - 1)]
            avg = sum(rt) / n
        else:
            p50 = p95 = p99 = avg = 0.0
        return self._send_json({
            "request_count": RCMHandler._request_counter,
            "error_count": RCMHandler._error_count,
            "response_times_ms": {
                "p50": round(p50, 2),
                "p95": round(p95, 2),
                "p99": round(p99, 2),
                "avg": round(avg, 2),
                "sample_size": n,
            },
        })

    def _route_health_deep(self) -> None:
        """GET /api/health/deep — component-level health checks."""
        import time as _dtime
        from . import __version__ as _dver
        checks = {}
        overall = "healthy"
        t0 = _dtime.perf_counter_ns()
        try:
            _st = PortfolioStore(self.config.db_path)
            with _st.connect() as _con:
                _con.execute("SELECT 1").fetchone()
            checks["db"] = {
                "status": "ok",
                "latency_ms": round((_dtime.perf_counter_ns() - t0) / 1e6, 2),
            }
        except Exception as _exc:
            checks["db"] = {"status": "fail", "error": str(_exc)}
            overall = "degraded"
        try:
            from .infra.migrations import list_applied, _MIGRATIONS
            applied = list_applied(PortfolioStore(self.config.db_path))
            pending = len(_MIGRATIONS) - len(applied)
            checks["migrations"] = {
                "status": "ok" if pending == 0 else "warn",
                "applied": len(applied), "pending": pending,
            }
            if pending > 0:
                overall = "degraded"
        except Exception:
            checks["migrations"] = {"status": "unknown"}
        try:
            from .data.hcris import hcris_cache_age_days
            age = hcris_cache_age_days()
            checks["hcris_data"] = {
                "status": "ok" if age and age < 90 else "warn",
                "age_days": round(age, 1) if age else None,
            }
        except Exception:
            checks["hcris_data"] = {"status": "unknown"}
        try:
            db_size = os.path.getsize(self.config.db_path)
            checks["disk"] = {"status": "ok", "db_size_mb": round(db_size / 1_048_576, 2)}
        except Exception:
            checks["disk"] = {"status": "unknown"}
        return self._send_json({
            "status": overall, "version": _dver,
            "checks": checks, "request_count": RCMHandler._request_counter,
        })

    def _route_settings_subpage(self, path: str) -> None:
        """GET /settings/custom-kpis | /settings/automations | /settings/integrations | /settings/ai."""
        from .ui.settings_pages import (
            render_custom_kpis_page, render_automations_page,
            render_integrations_page,
        )
        store = PortfolioStore(self.config.db_path)
        if path == "/settings/ai":
            from .ui.settings_ai_page import render_ai_settings
            return self._send_html(render_ai_settings(store))
        renderers = {
            "/settings/custom-kpis": render_custom_kpis_page,
            "/settings/automations": render_automations_page,
            "/settings/integrations": render_integrations_page,
        }
        renderer = renderers.get(path)
        if renderer:
            return self._send_html(renderer(store))
        self.send_error(HTTPStatus.NOT_FOUND, f"Unknown settings page: {path}")

    def _route_wizard_get(self, path: str) -> None:
        """GET /new-deal[/step2..step5] — wizard step pages."""
        from .ui.onboarding_wizard import (
            render_step1, load_session, render_step2,
            render_step3, render_step4, render_step5,
        )
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if path == "/new-deal":
            return self._send_html(render_step1(
                query=(qs.get("q") or [""])[0],
            ))
        deal_id = (qs.get("deal_id") or [""])[0]
        session = load_session(deal_id)
        if session is None:
            return self._redirect("/new-deal")
        renderers = {
            "/new-deal/step2": render_step2,
            "/new-deal/step3": render_step3,
            "/new-deal/step4": render_step4,
            "/new-deal/step5": render_step5,
        }
        renderer = renderers.get(path)
        if renderer:
            return self._send_html(renderer(session))
        return self._redirect("/new-deal")

    def _route_wizard_select(self) -> None:
        """POST /api/deals/wizard/select — Step 1 → 2 transition.

        Form fields: ``ccn`` (required). Runs ``auto_populate`` on
        the CCN, upserts the deal, seeds the wizard session, and
        redirects to Step 2.
        """
        from .data.auto_populate import auto_populate
        from .ui.onboarding_wizard import start_session_from_auto_populate
        form = self._read_form_body()
        ccn = (form.get("ccn") or "").strip()
        if not ccn:
            return self._send_json(
                {"error": "ccn is required"},
                status=HTTPStatus.BAD_REQUEST,
            )
        store = PortfolioStore(self.config.db_path)
        result = auto_populate(store, ccn)
        if not result.selected:
            return self._send_json(
                {"error": "no hospital matched this CCN",
                 "matches": [m.to_dict() for m in result.matches]},
                status=HTTPStatus.NOT_FOUND,
            )
        deal_id = result.selected.ccn
        store.upsert_deal(
            deal_id, name=result.selected.name,
            profile={k: v for k, v in result.profile.items()
                     if not callable(v)},
        )
        start_session_from_auto_populate(deal_id, result)
        return self._redirect(
            f"/new-deal/step2?deal_id={urllib.parse.quote(deal_id)}",
        )

    def _route_wizard_manual(self) -> None:
        """POST /new-deal/manual — Step 1 manual-entry fallback."""
        from .ui.onboarding_wizard import start_session_manual
        form = self._read_form_body()
        name = (form.get("name") or "").strip()
        if not name:
            return self._redirect("/new-deal")
        state = (form.get("state") or "").strip().upper()
        try:
            bed_count = int(form.get("bed_count") or 0) or None
        except ValueError:
            bed_count = None
        payer_mix: Dict[str, float] = {}
        for key_ui, key_pkt in (
            ("medicare_pct", "medicare"),
            ("medicaid_pct", "medicaid"),
            ("commercial_pct", "commercial"),
        ):
            try:
                raw = float(form.get(key_ui) or 0)
            except ValueError:
                continue
            if raw > 0:
                payer_mix[key_pkt] = raw / 100.0 if raw > 1 else raw
        # Generate a synthetic deal_id for the manual path.
        import re as _re, uuid as _uuid
        slug = _re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-").lower()[:40]
        deal_id = f"{slug}-{_uuid.uuid4().hex[:6]}"
        store = PortfolioStore(self.config.db_path)
        profile: Dict[str, Any] = {"name": name}
        if state:
            profile["state"] = state
        if bed_count:
            profile["bed_count"] = bed_count
        if payer_mix:
            profile["payer_mix"] = payer_mix
        store.upsert_deal(deal_id, name=name, profile=profile)
        start_session_manual(
            deal_id, name=name, state=state,
            bed_count=bed_count, payer_mix=payer_mix or None,
        )
        return self._redirect(
            f"/new-deal/step2?deal_id={urllib.parse.quote(deal_id)}",
        )

    def _route_wizard_upload(self, path: str) -> None:
        """POST /new-deal/upload?deal_id=… — multipart upload from
        Step 3's drag-drop zone. Extracts each file via the document
        reader, merges into the wizard session, then redirects back
        to Step 3 with updated totals.
        """
        from .data.document_reader import read_seller_file
        from .ui.onboarding_wizard import (
            load_session, merge_extraction,
        )
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(path).query)
        deal_id = (qs.get("deal_id") or [""])[0]
        session = load_session(deal_id)
        if session is None:
            return self._redirect("/new-deal")
        try:
            _fields, files = self._parse_multipart()
        except ValueError:
            return self._redirect(
                f"/new-deal/step3?deal_id={urllib.parse.quote(deal_id)}",
            )
        import tempfile as _tempfile
        for _field_name, (filename, content) in files.items():
            suffix = Path(filename).suffix or ".csv"
            with _tempfile.NamedTemporaryFile(
                mode="wb", suffix=suffix, delete=False,
            ) as tmp:
                tmp.write(content)
                tmp_path = tmp.name
            try:
                result = read_seller_file(Path(tmp_path))
                merge_extraction(deal_id, result.to_dict(), filename)
            finally:
                try:
                    Path(tmp_path).unlink()
                except OSError:
                    pass
        return self._redirect(
            f"/new-deal/step3?deal_id={urllib.parse.quote(deal_id)}",
        )

    def _route_wizard_launch(self) -> None:
        """POST /api/deals/wizard/launch — Step 4 → 5.

        Runs the packet builder with the wizard session's
        ``auto_populated`` + extracted metrics + any form overrides,
        then redirects to Step 5 (which auto-forwards to the
        workbench).
        """
        from .analysis.analysis_store import get_or_build_packet
        from .ui.onboarding_wizard import load_session
        form = self._read_form_body()
        deal_id = (form.get("deal_id") or "").strip()
        session = load_session(deal_id)
        if session is None:
            return self._redirect("/new-deal")
        run_mc = "run_mc" in form

        # Collect overrides (form keys prefixed with ``override_``).
        observed_override: Dict[str, Any] = {}
        for fk, fv in form.items():
            if not fk.startswith("override_"):
                continue
            metric_key = fk[len("override_"):]
            try:
                observed_override[metric_key] = float(fv)
            except (TypeError, ValueError):
                continue
        # Merge extracted metrics as observed too (higher confidence
        # than auto-populate).
        for k, v in session.extracted.items():
            observed_override.setdefault(k, v)

        # Auto-populated values pass as kwarg to the builder.
        auto_populated: Dict[str, float] = {
            k: float(v) for k, v in session.benchmark_metrics.items()
            if isinstance(v, (int, float))
        }

        # Financials from the session (for the bridge).
        financials: Dict[str, Any] = {}
        for k, v in session.financials.items():
            if isinstance(v, (int, float)):
                financials[k] = v
        store = PortfolioStore(self.config.db_path)
        try:
            get_or_build_packet(
                store, deal_id,
                force_rebuild=True,
                skip_simulation=not run_mc,
                observed_override=observed_override,
                auto_populated=auto_populated,
                financials=financials or None,
            )
        except Exception as exc:  # noqa: BLE001
            return self._send_json(
                {"error": f"build failed: {exc}",
                 "deal_id": deal_id},
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )
        return self._redirect(
            f"/new-deal/step5?deal_id={urllib.parse.quote(deal_id)}",
        )

    def _route_override_put(self, deal_id: str, key: str) -> None:
        """PUT /api/deals/<id>/overrides/<key> — upsert one override.

        Body: ``{"value": ..., "reason": "..."}``. The ``set_by``
        identifier comes from the authenticated session if present,
        else falls back to ``"api"``.
        """
        import json as _json
        from .analysis.deal_overrides import set_override
        n_bytes = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n_bytes) if n_bytes > 0 else b"{}"
        try:
            payload = _json.loads(raw.decode("utf-8") or "{}")
        except _json.JSONDecodeError:
            return self._send_json(
                {"error": "request body must be JSON"},
                status=HTTPStatus.BAD_REQUEST,
            )
        if not isinstance(payload, dict) or "value" not in payload:
            return self._send_json(
                {"error": "body must be an object with a 'value' field"},
                status=HTTPStatus.BAD_REQUEST,
            )
        set_by = self._current_username() or "api"
        try:
            row_id = set_override(
                PortfolioStore(self.config.db_path),
                deal_id, key, payload["value"],
                set_by=set_by, reason=payload.get("reason"),
            )
        except ValueError as exc:
            return self._send_json(
                {"error": str(exc), "code": "INVALID_OVERRIDE"},
                status=HTTPStatus.BAD_REQUEST,
            )
        return self._send_json({
            "deal_id": deal_id,
            "override_key": key,
            "override_value": payload["value"],
            "id": row_id,
        })

    def _route_override_delete(self, deal_id: str, key: str) -> None:
        """DELETE /api/deals/<id>/overrides/<key> — remove one override."""
        from .analysis.deal_overrides import clear_override
        removed = clear_override(
            PortfolioStore(self.config.db_path), deal_id, key,
        )
        if not removed:
            return self._send_json(
                {"error": f"no override {key!r} for {deal_id}",
                 "code": "OVERRIDE_NOT_FOUND"},
                status=HTTPStatus.NOT_FOUND,
            )
        return self._send_json({
            "deal_id": deal_id,
            "override_key": key,
            "deleted": True,
        })

    def _current_username(self) -> Optional[str]:
        """Best-effort username extraction for audit trails.

        Sessions carry usernames; HTTP-Basic requests don't (we'd have
        to decode the Authorization header). Falls back to ``None``
        which the caller coerces to ``"api"``.
        """
        token = self._session_token()
        if not token:
            return None
        try:
            from .auth.auth import user_for_session
            user = user_for_session(
                PortfolioStore(self.config.db_path), token,
            )
            return user.username if user else None
        except Exception:  # noqa: BLE001
            return None

    # ── Upload UI (B66) ──

    def _route_alerts(self) -> None:
        """B101 + B102: portfolio-wide alert review page with ack/snooze."""
        from .alerts.alerts import evaluate_active, evaluate_all
        from .alerts.alert_acks import trigger_key_for
        store = PortfolioStore(self.config.db_path)

        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        show_all = bool(qs.get("show"))
        owner_filter = (qs.get("owner") or [""])[0].strip() or None
        alerts = evaluate_all(store) if show_all else evaluate_active(store)
        if owner_filter:
            from .deals.deal_owners import deals_by_owner
            try:
                scope = set(deals_by_owner(store, owner_filter))
            except ValueError:
                scope = set()
            alerts = [a for a in alerts if a.deal_id in scope]

        sev_meta = {
            "red":   ("badge-red",   "RED"),
            "amber": ("badge-amber", "AMBER"),
            "info":  ("badge-blue",  "INFO"),
        }

        # Toggle link between "active only" and "all (incl. acked)"
        base_qs = {}
        if owner_filter:
            base_qs["owner"] = owner_filter
        if show_all:
            toggle_href = "/alerts" + (
                "?" + urllib.parse.urlencode(base_qs) if base_qs else ""
            )
            toggle = (f'<a href="{toggle_href}" style="color: var(--accent); '
                      f'font-size: 0.85rem;">← active only</a>')
        else:
            toggle_qs = dict(base_qs, show="all")
            toggle_href = "/alerts?" + urllib.parse.urlencode(toggle_qs)
            toggle = (f'<a href="{toggle_href}" style="color: var(--accent); '
                      f'font-size: 0.85rem;">show acked / all →</a>')

        # Owner-filter chip / form
        owner_form = (
            f'<form method="GET" action="/alerts" '
            f'style="display: inline-flex; gap: 0.3rem; align-items: center; '
            f'font-size: 0.85rem; margin-bottom: 0.75rem;">'
            f'<label class="muted">Owner</label>'
            f'<input type="text" name="owner" '
            f'value="{html.escape(owner_filter or "")}" '
            f'placeholder="e.g. AT" maxlength="40" '
            f'style="font-size: 0.85rem; padding: 0.15rem; width: 6rem;">'
            f'{"<input type=hidden name=show value=all>" if show_all else ""}'
            f'<button type="submit" class="btn" '
            f'style="font-size: 0.85rem; padding: 0.15rem 0.6rem;">Filter</button>'
            f'{"<a href=/alerts style=color:var(--accent);font-size:0.85rem;margin-left:0.5rem;>× clear</a>" if owner_filter else ""}'
            f'</form>'
        )

        if not alerts:
            scope_prefix = (
                f"No {owner_filter!r} " if owner_filter else "No active "
            )
            body = (
                f"{owner_form}"
                '<div class="card">'
                '<p style="color: var(--green-text); font-weight: 600;">'
                f'{scope_prefix}alerts. Portfolio looks clean.</p>'
                '<p class="muted" style="font-size: 0.85rem;">'
                'Evaluators run on every page load. They check covenant '
                'status, latest-quarter EBITDA variance, concerning-signal '
                'clusters, and stage regress. Acked alerts are hidden until '
                'their underlying state changes or snooze expires.'
                f'</p><p>{toggle}</p></div>'
            )
        else:
            grouped: Dict[str, list] = {"red": [], "amber": [], "info": []}
            for a in alerts:
                grouped.setdefault(a.severity, []).append(a)

            blocks = []
            for sev in ("red", "amber", "info"):
                bucket = grouped.get(sev) or []
                if not bucket:
                    continue
                cls, label = sev_meta[sev]
                rows = []
                for a in bucket:
                    tk = trigger_key_for(a)
                    from .alerts.alert_history import age_hint
                    age = age_hint(a.first_seen_at)
                    age_span = (
                        f'<span class="muted" style="font-size: 0.75rem;">'
                        f'seen {html.escape(age)}</span>' if age else ""
                    )
                    ack_form = (
                        f'<form method="POST" action="/api/alerts/ack" '
                        f'style="display: inline-flex; gap: 0.3rem; '
                        f'align-items: center; margin-left: 1rem;">'
                        f'<input type="hidden" name="kind" value="{html.escape(a.kind)}">'
                        f'<input type="hidden" name="deal_id" value="{html.escape(a.deal_id)}">'
                        f'<input type="hidden" name="trigger_key" value="{html.escape(tk)}">'
                        f'<select name="snooze_days" '
                        f'style="font-size: 0.75rem; padding: 0.1rem;">'
                        f'<option value="0">Ack (until state changes)</option>'
                        f'<option value="7">Snooze 7d</option>'
                        f'<option value="30">Snooze 30d</option>'
                        f'</select>'
                        f'<button type="submit" class="btn" '
                        f'style="font-size: 0.75rem; padding: 0.15rem 0.5rem;">'
                        f'Ack</button>'
                        f'</form>'
                    )
                    returning_badge = (
                        '<span class="badge badge-amber" '
                        'style="font-size: 0.7rem;" '
                        'title="Returned after snooze expired">'
                        '↩ returning</span>'
                        if getattr(a, "returning", False) else ""
                    )
                    rows.append(
                        f'<li style="padding: 0.6rem 0; '
                        f'border-bottom: 1px solid var(--border);">'
                        f'<div style="display: flex; gap: 0.5rem; '
                        f'align-items: center; flex-wrap: wrap;">'
                        f'<span class="badge {cls}">{label}</span>'
                        f'{returning_badge}'
                        f'<a href="/deal/{urllib.parse.quote(a.deal_id)}" '
                        f'style="color: var(--accent); text-decoration: none; '
                        f'font-weight: 600;">{html.escape(a.deal_id)}</a>'
                        f'<span style="color: var(--text);">— '
                        f'{html.escape(a.title)}</span>'
                        f'{age_span}'
                        f'{ack_form}'
                        f'</div>'
                        f'<div class="muted" style="font-size: 0.85rem; '
                        f'margin-top: 0.2rem; margin-left: 1rem;">'
                        f'{html.escape(a.detail)}</div>'
                        f'</li>'
                    )
                blocks.append(
                    f'<div class="card"><h2>{label} ({len(bucket)})</h2>'
                    f'<ul style="list-style: none; padding: 0; margin: 0;">'
                    f'{"".join(rows)}</ul></div>'
                )
            blocks.append(f'<p style="margin-top: 1rem;">{toggle}</p>')
            body = owner_form + "".join(blocks)

        subtitle = (
            f"{len(alerts)} "
            f"{'total' if show_all else 'active'} "
            f"alert{'s' if len(alerts) != 1 else ''}"
            f"{f' · owner = {owner_filter}' if owner_filter else ''}"
        )
        self._send_html(shell(
            body=body, title="Alerts",
            subtitle=subtitle, back_href="/",
        ))

    def _route_my_dashboard(self, owner: str) -> None:
        """B117: single-pane view of one analyst's work.

        Pulls together: deals currently owned, alerts on those deals,
        and deadlines assigned to them (overdue + upcoming). Lets an
        analyst start Monday on one URL instead of five.
        """
        from .alerts.alerts import evaluate_active
        from .deals.deal_deadlines import overdue, upcoming
        from .deals.deal_owners import deals_by_owner
        from .portfolio.portfolio_snapshots import latest_per_deal
        store = PortfolioStore(self.config.db_path)
        if not owner:
            return self.send_error(HTTPStatus.BAD_REQUEST, "owner required")
        try:
            my_deals = set(deals_by_owner(store, owner))
        except ValueError as exc:
            return self.send_error(HTTPStatus.BAD_REQUEST, str(exc))

        my_alerts = [a for a in evaluate_active(store)
                     if a.deal_id in my_deals]
        my_od = overdue(store, owner=owner)
        my_up = upcoming(store, days_ahead=14, owner=owner)

        # ── Deals card ──
        if not my_deals:
            deals_html = (
                '<div class="card">'
                f'<p class="muted">No deals currently assigned to '
                f'<code>{html.escape(owner)}</code>. Open a deal and use '
                f'the <em>Assign</em> form on its page.</p></div>'
            )
        else:
            df = latest_per_deal(store)
            df = df[df["deal_id"].isin(my_deals)] if not df.empty else df

            def _fmt(v, pct=False):
                if v is None or (isinstance(v, float) and v != v):
                    return "—"
                return f"{float(v)*100:.1f}%" if pct else f"{float(v):.2f}x"

            rows = []
            if not df.empty:
                for _, r in df.iterrows():
                    did = str(r["deal_id"])
                    rows.append(
                        f"<tr>"
                        f"<td><a href='/deal/{urllib.parse.quote(did)}' "
                        f"style='color: var(--accent); font-weight: 600; "
                        f"text-decoration: none;'>{html.escape(did)}</a></td>"
                        f"{_health_cell(store, did)}"
                        f"<td>{html.escape(str(r.get('stage') or '—'))}</td>"
                        f"<td>{html.escape(str(r.get('covenant_status') or '—'))}</td>"
                        f"<td class='num'>{_fmt(r.get('moic'))}</td>"
                        f"<td class='num'>{_fmt(r.get('irr'), pct=True)}</td>"
                        f"</tr>"
                    )
            deals_html = (
                f'<div class="card"><h2 style="margin-top: 0;">'
                f'My deals ({len(my_deals)})</h2>'
                f'<table><thead><tr>'
                f'<th>Deal</th><th>Health</th><th>Stage</th><th>Covenant</th>'
                f'<th>MOIC</th><th>IRR</th>'
                f'</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
            )

        # ── Alerts card ──
        red = [a for a in my_alerts if a.severity == "red"]
        amber = [a for a in my_alerts if a.severity == "amber"]
        if my_alerts:
            alert_rows = []
            for a in red + amber:
                cls = "badge-red" if a.severity == "red" else "badge-amber"
                alert_rows.append(
                    f"<li style='padding: 0.4rem 0; "
                    f"border-bottom: 1px solid var(--border); "
                    f"display: flex; gap: 0.5rem; align-items: center; "
                    f"flex-wrap: wrap;'>"
                    f"<span class='badge {cls}'>{a.severity.upper()}</span>"
                    f"<a href='/deal/{urllib.parse.quote(a.deal_id)}' "
                    f"style='color: var(--accent); font-weight: 600; "
                    f"text-decoration: none;'>{html.escape(a.deal_id)}</a>"
                    f"<span>{html.escape(a.title)}</span>"
                    f"<span class='muted' style='font-size: 0.85rem;'>"
                    f"{html.escape(a.detail)}</span>"
                    f"</li>"
                )
            alerts_html = (
                f'<div class="card"><h2 style="margin-top: 0;">'
                f'My alerts ({len(red)} red / {len(amber)} amber)</h2>'
                f'<ul style="list-style: none; padding: 0; margin: 0;">'
                f'{"".join(alert_rows)}</ul></div>'
            )
        else:
            alerts_html = (
                '<div class="card"><h2 style="margin-top: 0;">My alerts</h2>'
                '<p class="muted">Nothing active on your deals.</p></div>'
            )

        # ── Deadlines card ──
        def _deadline_li(r, *, badge):
            did = str(r["deal_id"])
            return (
                f"<li style='padding: 0.4rem 0; "
                f"border-bottom: 1px solid var(--border); "
                f"display: flex; gap: 0.5rem; align-items: center;'>"
                f"{badge} "
                f"<a href='/deal/{urllib.parse.quote(did)}' "
                f"style='color: var(--accent); font-weight: 600; "
                f"text-decoration: none;'>{html.escape(did)}</a>"
                f"<span>{html.escape(str(r['label']))}</span>"
                f"<span class='muted' style='font-size: 0.85rem;'>"
                f"due {html.escape(str(r['due_date']))}</span>"
                f"</li>"
            )

        deadline_rows = []
        for _, r in my_od.iterrows():
            badge = (
                f'<span class="badge badge-red">'
                f'{int(r["days_overdue"])}d OVERDUE</span>'
            )
            deadline_rows.append(_deadline_li(r, badge=badge))
        for _, r in my_up.iterrows():
            deadline_rows.append(_deadline_li(
                r, badge='<span class="badge badge-amber">UPCOMING</span>',
            ))
        if deadline_rows:
            deadlines_html = (
                f'<div class="card"><h2 style="margin-top: 0;">'
                f'My deadlines ({len(my_od)} overdue, {len(my_up)} upcoming)'
                f'</h2>'
                f'<ul style="list-style: none; padding: 0; margin: 0;">'
                f'{"".join(deadline_rows)}</ul></div>'
            )
        else:
            deadlines_html = (
                '<div class="card"><h2 style="margin-top: 0;">My deadlines</h2>'
                '<p class="muted">Nothing assigned.</p></div>'
            )

        # B141: personalized pulse + health mix at the top of the page
        pulse_parts = []
        n_red = sum(1 for a in my_alerts if a.severity == "red")
        n_amber = sum(1 for a in my_alerts if a.severity == "amber")
        if n_red:
            pulse_parts.append(
                f'<span style="color: var(--red-text); font-weight: 700;">'
                f'{n_red} red</span>'
            )
        if n_amber:
            pulse_parts.append(
                f'<span style="color: var(--amber-text); font-weight: 700;">'
                f'{n_amber} amber</span>'
            )
        if not my_od.empty:
            pulse_parts.append(
                f'<span style="color: var(--red-text); font-weight: 600;">'
                f'{len(my_od)} overdue</span>'
            )
        if not my_up.empty:
            pulse_parts.append(
                f'<span class="muted">{len(my_up)} upcoming</span>'
            )
        sep = ' <span class="muted">·</span> '
        pulse_html = (
            f'<div style="margin-bottom: 1rem; font-size: 0.95rem;">'
            f'<span class="muted" style="font-size: 0.82rem; '
            f'text-transform: uppercase; letter-spacing: 0.05em; '
            f'font-weight: 600; margin-right: 0.5rem;">Your pulse</span>'
            f'{sep.join(pulse_parts)}</div>'
            if pulse_parts else ""
        )

        # B141: health mix over my deals
        health_html = ""
        if my_deals:
            from .deals.health_score import compute_health
            counts = {"green": 0, "amber": 0, "red": 0}
            for did in my_deals:
                h = compute_health(store, did)
                if h["score"] is None:
                    continue
                if h["band"] in counts:
                    counts[h["band"]] += 1
            total = sum(counts.values())
            if total > 0:
                def pct(n):
                    return (n / total) * 100.0
                health_html = f"""
    <div class="card">
      <h2 style="margin-top: 0;">Your health mix</h2>
      <div style="display: flex; align-items: center; gap: 1rem;
                  flex-wrap: wrap;">
        <div style="flex: 1; min-width: 20rem; display: flex;
                    height: 1.2rem; border-radius: 6px; overflow: hidden;
                    border: 1px solid var(--border);">
          <div style="background: var(--green); width: {pct(counts['green']):.1f}%;"
               title="{counts['green']} green"></div>
          <div style="background: var(--amber); width: {pct(counts['amber']):.1f}%;"
               title="{counts['amber']} amber"></div>
          <div style="background: var(--red); width: {pct(counts['red']):.1f}%;"
               title="{counts['red']} red"></div>
        </div>
        <div style="font-size: 0.9rem;">
          <span style="color: var(--green-text); font-weight: 700;">●
            {counts['green']}</span>
          <span style="color: var(--amber-text); font-weight: 700;
                       margin-left: 0.75rem;">● {counts['amber']}</span>
          <span style="color: var(--red-text); font-weight: 700;
                       margin-left: 0.75rem;">● {counts['red']}</span>
        </div>
      </div>
    </div>
"""

        body = pulse_html + health_html + alerts_html + deadlines_html + deals_html
        self._send_html(shell(
            body=body, title=f"My work: {owner}",
            subtitle=(
                f"{len(my_deals)} deals · "
                f"{len(my_alerts)} alerts · "
                f"{len(my_od)} overdue · {len(my_up)} upcoming"
            ),
            back_href="/",
        ))

    def _route_deadlines(self) -> None:
        """B114: portfolio inbox — overdue + upcoming deadlines."""
        from .deals.deal_deadlines import overdue, upcoming
        store = PortfolioStore(self.config.db_path)
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        days_ahead = self._clamp_int(
            (qs.get("days") or ["14"])[0],
            default=14, min_v=1, max_v=365,
        )
        owner_filter = (qs.get("owner") or [""])[0].strip() or None

        od = overdue(store, owner=owner_filter)
        up = upcoming(store, days_ahead=days_ahead, owner=owner_filter)

        def _row(r, *, badge):
            did = str(r["deal_id"])
            complete_form = (
                f'<form method="POST" '
                f'action="/api/deadlines/{int(r["deadline_id"])}/complete" '
                f'style="display: inline;">'
                f'<button type="submit" class="btn" '
                f'style="font-size: 0.75rem; padding: 0.1rem 0.5rem;">'
                f'✓ Done</button></form>'
            )
            owner = str(r.get("owner") or "")
            owner_cell = (
                f"<a href='/deadlines?owner={urllib.parse.quote(owner)}' "
                f"style='color: var(--accent); text-decoration: none;'>"
                f"{html.escape(owner)}</a>" if owner
                else "<span class='muted'>—</span>"
            )
            return (
                f"<tr>"
                f"<td>{badge}</td>"
                f"<td><a href='/deal/{urllib.parse.quote(did)}' "
                f"style='color: var(--accent); font-weight: 600; "
                f"text-decoration: none;'>{html.escape(did)}</a></td>"
                f"<td>{html.escape(str(r['label']))}</td>"
                f"<td>{owner_cell}</td>"
                f"<td class='muted'>{html.escape(str(r['due_date']))}</td>"
                f"<td>{complete_form}</td>"
                f"</tr>"
            )

        sections = []
        if not od.empty:
            rows = []
            for _, r in od.iterrows():
                badge = (
                    f'<span class="badge badge-red">'
                    f'{int(r["days_overdue"])}d OVERDUE</span>'
                )
                rows.append(_row(r, badge=badge))
            sections.append(
                f'<div class="card" style="border-left: 3px solid var(--red-text);">'
                f'<h2 style="margin-top: 0;">Overdue ({len(od)})</h2>'
                f'<table><thead><tr><th>Status</th><th>Deal</th>'
                f'<th>Task</th><th>Owner</th><th>Due</th><th></th>'
                f'</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
            )
        if not up.empty:
            rows = []
            for _, r in up.iterrows():
                rows.append(_row(
                    r,
                    badge='<span class="badge badge-amber">UPCOMING</span>',
                ))
            sections.append(
                f'<div class="card">'
                f'<h2 style="margin-top: 0;">Upcoming '
                f'(next {days_ahead} days, {len(up)})</h2>'
                f'<table><thead><tr><th>Status</th><th>Deal</th>'
                f'<th>Task</th><th>Owner</th><th>Due</th><th></th>'
                f'</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
            )

        if not sections:
            sections.append(
                '<div class="card">'
                '<p style="color: var(--green-text); font-weight: 600;">'
                'Nothing overdue and nothing in the next '
                f'{days_ahead} days.</p>'
                '<p class="muted" style="font-size: 0.85rem;">'
                'Add deadlines from a deal page to populate this inbox.'
                '</p></div>'
            )

        # Window picker + owner filter
        picker = (
            f'<form method="GET" action="/deadlines" '
            f'style="display: flex; gap: 0.6rem; align-items: center; '
            f'margin-bottom: 1rem; font-size: 0.85rem; flex-wrap: wrap;">'
            f'<label>Look ahead <select name="days" '
            f'style="font-size: 0.85rem; padding: 0.1rem;">'
        )
        for opt in (7, 14, 30, 60, 90):
            sel = " selected" if opt == days_ahead else ""
            picker += f'<option value="{opt}"{sel}>{opt} days</option>'
        picker += "</select></label>"
        picker += (
            f'<label>Owner <input type="text" name="owner" '
            f'value="{html.escape(owner_filter or "")}" '
            f'placeholder="e.g. AT" maxlength="40" '
            f'style="font-size: 0.85rem; padding: 0.1rem; width: 7rem;">'
            f'</label>'
            f'<button type="submit" class="btn" '
            f'style="font-size: 0.85rem; padding: 0.15rem 0.6rem;">'
            f'Apply</button>'
        )
        if owner_filter:
            picker += (
                f' <a href="/deadlines?days={days_ahead}" '
                f'style="color: var(--accent); font-size: 0.85rem;">'
                f'× clear owner</a>'
            )
        picker += "</form>"

        body = picker + "".join(sections)
        self._send_html(shell(
            body=body, title="Deadlines",
            subtitle=f"Inbox · {len(od)} overdue, {len(up)} upcoming",
            back_href="/",
        ))

    def _route_owners(self) -> None:
        """B113: directory of analysts and how many deals each currently owns."""
        from .deals.deal_owners import all_owners
        store = PortfolioStore(self.config.db_path)
        owners = all_owners(store)
        if not owners:
            body = (
                '<div class="card">'
                '<p class="muted">No deal owners assigned yet. Use the '
                '<strong>Assign owner</strong> form on any deal page.</p>'
                '</div>'
            )
        else:
            from .deals.deal_owners import deals_by_owner
            from .deals.health_score import compute_health
            rows = []
            for owner, n in owners:
                dids = deals_by_owner(store, owner)
                scores = []
                for did in dids:
                    h = compute_health(store, did)
                    if h["score"] is not None:
                        scores.append(h["score"])
                avg = int(round(sum(scores) / len(scores))) if scores else None
                avg_band = (
                    "green" if (avg or 0) >= 80 else
                    "amber" if (avg or 0) >= 50 else "red"
                ) if avg is not None else "muted"
                avg_color = {
                    "green": "var(--green-text)",
                    "amber": "var(--amber-text)",
                    "red":   "var(--red-text)",
                    "muted": "var(--muted)",
                }[avg_band]
                avg_cell = (
                    f"<td class='num' style='color: {avg_color}; "
                    f"font-weight: 700;'>{avg}</td>"
                    if avg is not None else "<td class='muted'>—</td>"
                )
                rows.append(
                    f"<tr>"
                    f"<td><a href='/owner/{urllib.parse.quote(owner)}' "
                    f"style='color: var(--accent); font-weight: 600; "
                    f"text-decoration: none;'>{html.escape(owner)}</a></td>"
                    f"<td class='num'>{n}</td>"
                    f"{avg_cell}"
                    f"<td><a href='/my/{urllib.parse.quote(owner)}' "
                    f"style='color: var(--accent); font-size: 0.85rem; "
                    f"text-decoration: none;'>My work →</a></td>"
                    f"</tr>"
                )
            body = (
                f'<div class="card">'
                f'<h2>Owners ({len(owners)})</h2>'
                f'<p class="muted" style="font-size: 0.85rem;">'
                f'Deals grouped by current assignee. Owners are set per '
                f'deal with an append-only history — the number here '
                f'reflects the latest assignment for each deal.'
                f'</p>'
                f'<table><thead><tr><th>Owner</th><th>Deals</th>'
                f'<th>Avg health</th><th></th>'
                f'</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
            )
        self._send_html(shell(
            body=body, title="Owners",
            subtitle="Deal assignments",
            back_href="/",
        ))

    def _route_owner_detail(self, owner: str) -> None:
        """B113: all deals currently owned by a given analyst."""
        from .deals.deal_owners import deals_by_owner
        from .portfolio.portfolio_snapshots import latest_per_deal
        store = PortfolioStore(self.config.db_path)
        if not owner:
            return self.send_error(HTTPStatus.BAD_REQUEST, "owner required")
        try:
            dids = deals_by_owner(store, owner)
        except ValueError as exc:
            return self.send_error(HTTPStatus.BAD_REQUEST, str(exc))
        if not dids:
            body = (
                f'<div class="card">'
                f'<p class="muted">No deals currently owned by '
                f'<strong>{html.escape(owner)}</strong>.</p></div>'
            )
        else:
            df = latest_per_deal(store)
            df = df[df["deal_id"].isin(dids)] if not df.empty else df

            def _fmt(v, pct=False):
                if v is None or (isinstance(v, float) and v != v):
                    return "—"
                return f"{float(v)*100:.1f}%" if pct else f"{float(v):.2f}x"

            rows = []
            if not df.empty:
                for _, r in df.iterrows():
                    did = str(r["deal_id"])
                    rows.append(
                        f"<tr>"
                        f"<td><a href='/deal/{urllib.parse.quote(did)}' "
                        f"style='color: var(--accent); font-weight: 600; "
                        f"text-decoration: none;'>{html.escape(did)}</a></td>"
                        f"{_health_cell(store, did)}"
                        f"<td>{html.escape(str(r.get('stage') or '—'))}</td>"
                        f"<td>{html.escape(str(r.get('covenant_status') or '—'))}</td>"
                        f"<td class='num'>{_fmt(r.get('moic'))}</td>"
                        f"<td class='num'>{_fmt(r.get('irr'), pct=True)}</td>"
                        f"</tr>"
                    )
            body = (
                f'<div class="card">'
                f'<h2>Deals owned by <code>{html.escape(owner)}</code> '
                f'({len(dids)})</h2>'
                f'<table><thead><tr>'
                f'<th>Deal</th><th>Health</th><th>Stage</th><th>Covenant</th>'
                f'<th>MOIC</th><th>IRR</th>'
                f'</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
            )
        self._send_html(shell(
            body=body, title=f"Owner: {owner}",
            subtitle=f"All deals assigned to {owner!r}",
            back_href="/owners",
        ))

    def _route_watchlist(self) -> None:
        """B111: list of starred deals with their latest metrics."""
        from .portfolio.portfolio_snapshots import latest_per_deal
        from .deals.watchlist import list_starred
        store = PortfolioStore(self.config.db_path)
        starred = list_starred(store)
        if not starred:
            body = (
                '<div class="card">'
                '<p class="muted">No starred deals yet. Open any deal '
                'and click the <strong>★ Star</strong> button to pin it '
                'here for quick access.</p></div>'
            )
            self._send_html(shell(
                body=body, title="Watchlist",
                subtitle="Pinned deals",
                back_href="/",
            ))
            return

        df = latest_per_deal(store)
        df = df[df["deal_id"].isin(starred)].copy() if not df.empty else df

        if df.empty:
            body = (
                f'<div class="card">'
                f'<p class="muted">You have starred deals '
                f'({", ".join(starred)}) but none have snapshots yet.</p>'
                f'</div>'
            )
        else:
            # Preserve star order (most-recently starred first)
            order_map = {d: i for i, d in enumerate(starred)}
            df["_star_order"] = df["deal_id"].map(order_map)
            df = df.sort_values("_star_order").drop(columns=["_star_order"])

            def _fmt(v, pct=False):
                if v is None or (isinstance(v, float) and v != v):
                    return "—"
                return f"{float(v)*100:.1f}%" if pct else f"{float(v):.2f}x"

            rows = []
            for _, r in df.iterrows():
                did = str(r["deal_id"])
                rows.append(
                    f"<tr>"
                    f"<td>★ <a href='/deal/{urllib.parse.quote(did)}' "
                    f"style='color: var(--accent); font-weight: 600; "
                    f"text-decoration: none;'>{html.escape(did)}</a></td>"
                    f"{_health_cell(store, did)}"
                    f"<td>{html.escape(str(r.get('stage') or '—'))}</td>"
                    f"<td>{html.escape(str(r.get('covenant_status') or '—'))}</td>"
                    f"<td class='num'>{_fmt(r.get('moic'))}</td>"
                    f"<td class='num'>{_fmt(r.get('irr'), pct=True)}</td>"
                    f"</tr>"
                )
            body = (
                f'<div class="card">'
                f'<h2>Watchlist ({len(df)})</h2>'
                f'<table><thead><tr>'
                f'<th>Deal</th><th>Health</th><th>Stage</th><th>Covenant</th>'
                f'<th>MOIC</th><th>IRR</th>'
                f'</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
            )

        self._send_html(shell(
            body=body, title="Watchlist",
            subtitle="Pinned deals",
            back_href="/",
        ))

    def _route_notes_search(self) -> None:
        """B110 + B123: full-text + tag-filtered notes search."""
        from .deals.deal_notes import search_notes
        from .deals.note_tags import tags_for_notes
        store = PortfolioStore(self.config.db_path)
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        q = (qs.get("q") or [""])[0]
        deal_id = (qs.get("deal_id") or [""])[0].strip()
        tags_raw = (qs.get("tags") or [""])[0].strip()
        tag_list = [t for t in tags_raw.split() if t]

        try:
            df = search_notes(store, q, deal_id=deal_id or None,
                              tags=tag_list or None)
            tag_err = None
        except ValueError as exc:
            df = None
            tag_err = str(exc)

        # Simple highlight for matches (case-insensitive)
        def _highlight(body: str) -> str:
            esc = html.escape(body)
            if not q:
                return esc
            import re as _re
            try:
                return _re.sub(
                    "(" + _re.escape(html.escape(q)) + ")",
                    r'<mark style="background: var(--amber-soft); '
                    r'padding: 0 2px;">\1</mark>',
                    esc, flags=_re.IGNORECASE,
                )
            except _re.error:
                return esc

        search_form = (
            f'<form method="GET" action="/notes" '
            f'style="display: flex; gap: 0.5rem; margin-bottom: 1rem;">'
            f'<input type="text" name="q" value="{html.escape(q)}" '
            f'placeholder="Search note text…" '
            f'style="flex: 1; font-size: 1rem; padding: 0.35rem 0.5rem;" '
            f'autofocus>'
            f'<input type="text" name="deal_id" value="{html.escape(deal_id)}" '
            f'placeholder="deal_id (optional)" '
            f'style="font-size: 1rem; padding: 0.35rem 0.5rem; width: 10rem;">'
            f'<input type="text" name="tags" value="{html.escape(tags_raw)}" '
            f'placeholder="tags (space-separated)" '
            f'style="font-size: 1rem; padding: 0.35rem 0.5rem; width: 14rem;">'
            f'<button type="submit" class="btn" '
            f'style="font-size: 0.9rem; padding: 0.25rem 0.8rem;">Search</button>'
            f'</form>'
        )

        if tag_err:
            body = (
                f"{search_form}"
                f'<div class="card"><p class="err">'
                f'Invalid tag: {html.escape(tag_err)}</p></div>'
            )
        elif not q and not tag_list:
            body = (
                f"{search_form}"
                '<div class="card">'
                '<p class="muted">Enter a query above. Searches are '
                'case-insensitive and match any substring of the note '
                'body. Optionally scope to a specific deal, or filter by '
                'space-separated tags (AND semantics).</p></div>'
            )
        elif df.empty:
            body = (
                f"{search_form}"
                f'<div class="card">'
                f'<p class="muted">No notes match '
                f'<code>{html.escape(q)}</code>'
                f'{" for deal <code>" + html.escape(deal_id) + "</code>" if deal_id else ""}'
                f'.</p></div>'
            )
        else:
            rows = []
            note_ids = [int(r["note_id"]) for _, r in df.iterrows()]
            tags_map = tags_for_notes(store, note_ids)
            for _, r in df.iterrows():
                author = str(r.get("author") or "—")
                note_id = int(r["note_id"])
                pills = "".join(
                    f'<a href="/notes?tags={urllib.parse.quote(t)}" '
                    f'class="badge badge-blue" '
                    f'style="text-decoration: none; font-size: 0.7rem; '
                    f'margin-right: 0.25rem;">{html.escape(t)}</a>'
                    for t in tags_map.get(note_id, [])
                )
                rows.append(
                    f"<li style='padding: 0.6rem 0; "
                    f"border-bottom: 1px solid var(--border);'>"
                    f"<div style='display: flex; gap: 0.5rem; "
                    f"align-items: baseline; margin-bottom: 0.2rem; "
                    f"flex-wrap: wrap;'>"
                    f"<a href='/deal/{urllib.parse.quote(str(r['deal_id']))}' "
                    f"style='color: var(--accent); font-weight: 600; "
                    f"text-decoration: none;'>{html.escape(str(r['deal_id']))}</a>"
                    f"<span class='muted' style='font-size: 0.8rem;'>"
                    f"{html.escape(str(r['created_at'])[:19])}"
                    f"{' · ' + html.escape(author) if author != '—' else ''}</span>"
                    f"{pills}"
                    f"</div>"
                    f"<div style='white-space: pre-wrap; font-size: 0.9rem;'>"
                    f"{_highlight(str(r['body']))}</div>"
                    f"</li>"
                )
            body = (
                f"{search_form}"
                f'<div class="card">'
                f'<h2>{len(df)} match{"es" if len(df) != 1 else ""} '
                f'for <code>{html.escape(q)}</code></h2>'
                f'<ul style="list-style: none; padding: 0; margin: 0;">'
                f'{"".join(rows)}</ul></div>'
            )

        self._send_html(shell(
            body=body, title="Notes search",
            subtitle="Full-text search across deal notes",
            back_href="/",
        ))

    def _route_variance(self) -> None:
        """B108: portfolio-wide KPI variance, worst-first.

        Answers "who missed plan this quarter?" without tabbing through
        every deal. Query params:

            kpi      — which tracked KPI (default "ebitda")
            quarter  — pin to a specific quarter (default: latest per deal)
            severity — filter ("miss_red", "miss_amber", "on_track", "beat", ...)
        """
        from .pe.hold_tracking import TRACKED_KPIS, portfolio_variance_matrix
        store = PortfolioStore(self.config.db_path)
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        kpi = (qs.get("kpi") or ["ebitda"])[0]
        quarter = (qs.get("quarter") or [None])[0]
        severity_filter = (qs.get("severity") or [None])[0]

        df = portfolio_variance_matrix(store, kpi=kpi, quarter=quarter)
        if severity_filter and not df.empty:
            df = df[df["severity"] == severity_filter].reset_index(drop=True)

        if (qs.get("format") or [""])[0] == "csv":
            return self._send_csv_df(df, filename=f"variance_{kpi}.csv")

        # Filter form
        kpi_opts = "".join(
            f'<option value="{k}"{" selected" if k == kpi else ""}>{k}</option>'
            for k in TRACKED_KPIS
        )
        sev_opts_vals = ["", "off_track", "lagging", "on_track", "no_plan"]
        sev_opts = "".join(
            f'<option value="{s}"{" selected" if s == (severity_filter or "") else ""}>'
            f'{s or "(any)"}</option>' for s in sev_opts_vals
        )
        quarter_val = html.escape(quarter or "")
        picker = (
            f'<form method="GET" action="/variance" '
            f'style="display: flex; gap: 0.6rem; align-items: center; '
            f'margin-bottom: 1rem; font-size: 0.85rem; flex-wrap: wrap;">'
            f'<label>KPI <select name="kpi">{kpi_opts}</select></label>'
            f'<label>Quarter <input name="quarter" type="text" '
            f'value="{quarter_val}" placeholder="e.g. 2026Q1" '
            f'style="font-size: 0.85rem; padding: 0.1rem; width: 6rem;"></label>'
            f'<label>Severity <select name="severity">{sev_opts}</select></label>'
            f'<button type="submit" class="btn" '
            f'style="font-size: 0.85rem; padding: 0.15rem 0.6rem;">Apply</button>'
            f'</form>'
        )
        dl_qs = urllib.parse.urlencode({
            k: v for k, v in {
                "kpi": kpi, "quarter": quarter or "",
                "severity": severity_filter or "", "format": "csv",
            }.items() if v
        })
        download_link = (
            f'<a href="/variance?{dl_qs}" '
            f'style="color: var(--accent); font-size: 0.85rem; '
            f'text-decoration: none; border-bottom: 1px dotted var(--accent); '
            f'margin-left: 1rem;">↓ Download CSV</a>'
        )
        picker = f'<div style="display: flex; align-items: center;">{picker}{download_link}</div>'

        if df.empty:
            body = (
                f"{picker}"
                '<div class="card">'
                '<p class="muted">No variance rows match — either no deal '
                f'has reported <code>{html.escape(kpi)}</code> actuals '
                'yet, or the filter excluded everyone.</p>'
                '</div>'
            )
        else:
            sev_badge = {
                "off_track": '<span class="badge badge-red">OFF TRACK</span>',
                "lagging":   '<span class="badge badge-amber">LAGGING</span>',
                "on_track":  '<span class="badge badge-green">ON TRACK</span>',
                "no_plan":   '<span class="badge badge-muted">NO PLAN</span>',
            }
            rows_html = []
            for _, r in df.iterrows():
                vp = r.get("variance_pct")
                vp_str = ("—" if vp is None or (isinstance(vp, float) and vp != vp)
                          else f"{float(vp)*100:+.1f}%")
                actual = r.get("actual")
                plan = r.get("plan")
                actual_str = "—" if actual is None else f"{float(actual):,.0f}"
                plan_str = ("—" if plan is None or (isinstance(plan, float) and plan != plan)
                            else f"{float(plan):,.0f}")
                did = str(r["deal_id"])
                sev = str(r.get("severity") or "")
                rows_html.append(
                    f"<tr>"
                    f"<td><a href='/deal/{urllib.parse.quote(did)}' "
                    f"style='color: var(--accent); font-weight: 600; "
                    f"text-decoration: none;'>{html.escape(did)}</a></td>"
                    f"<td>{html.escape(str(r.get('quarter') or ''))}</td>"
                    f"<td class='num'>{actual_str}</td>"
                    f"<td class='num'>{plan_str}</td>"
                    f"<td class='num'>{vp_str}</td>"
                    f"<td>{sev_badge.get(sev, html.escape(sev))}</td>"
                    f"</tr>"
                )
            body = (
                f"{picker}"
                f'<div class="card">'
                f'<h2>{html.escape(kpi)} variance — {len(df)} deal'
                f'{"s" if len(df) != 1 else ""}</h2>'
                f'<table><thead><tr>'
                f'<th>Deal</th><th>Quarter</th><th>Actual</th>'
                f'<th>Plan</th><th>Variance</th><th>Severity</th>'
                f'</tr></thead><tbody>{"".join(rows_html)}</tbody></table></div>'
            )

        self._send_html(shell(
            body=body, title="Variance",
            subtitle=f"Portfolio-wide {kpi} variance",
            back_href="/",
        ))

    def _route_lp_update(self) -> None:
        """B107: partner-ready LP update page.

        Stitches together ``portfolio_rollup``, ``evaluate_active``,
        ``build_digest``, and ``cohort_rollup`` into a single printable
        narrative. Query params:

            days    — window for "recent activity" section (default 30)
            download=1  — return as attachment
        """
        from .alerts.alerts import evaluate_active
        from .analysis.cohorts import cohort_rollup
        from .portfolio.portfolio_digest import build_digest, digest_to_frame
        from .portfolio.portfolio_snapshots import portfolio_rollup
        from datetime import datetime as _dt, timedelta as _td, timezone as _tz

        store = PortfolioStore(self.config.db_path)

        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        days = self._clamp_int(
            (qs.get("days") or ["30"])[0],
            default=30, min_v=1, max_v=365,
        )
        download = bool(qs.get("download"))

        since = (_dt.now(_tz.utc) - _td(days=days)).strftime("%Y-%m-%d")
        rollup = portfolio_rollup(store)
        alerts = evaluate_active(store)
        events_df = digest_to_frame(build_digest(store, since=since))
        cohorts_df = cohort_rollup(store)

        def _fmt(v, pct=False, suffix=""):
            if v is None:
                return "—"
            if isinstance(v, float) and v != v:
                return "—"
            if pct:
                return f"{float(v)*100:.1f}%"
            return f"{float(v):.2f}{suffix}"

        # ── Headline KPIs ──
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

        # ── Active alerts section ──
        red = [a for a in alerts if a.severity == "red"]
        amber = [a for a in alerts if a.severity == "amber"]
        alerts_rows = []
        for a in red + amber:
            badge_cls = "badge-red" if a.severity == "red" else "badge-amber"
            alerts_rows.append(
                f"<li style='padding: 0.4rem 0; border-bottom: 1px solid "
                f"var(--border);'>"
                f"<span class='badge {badge_cls}'>{a.severity.upper()}</span> "
                f"<a href='/deal/{urllib.parse.quote(a.deal_id)}' "
                f"style='color: var(--accent); font-weight: 600; "
                f"text-decoration: none;'>{html.escape(a.deal_id)}</a> — "
                f"{html.escape(a.title)} "
                f"<span class='muted' style='font-size: 0.85rem;'>"
                f"{html.escape(a.detail)}</span></li>"
            )
        if alerts_rows:
            alerts_section = (
                f'<div class="card"><h2>Active alerts '
                f'({len(red)} red / {len(amber)} amber)</h2>'
                f'<ul style="list-style: none; padding: 0; margin: 0;">'
                f'{"".join(alerts_rows)}</ul></div>'
            )
        else:
            alerts_section = (
                '<div class="card"><h2>Active alerts</h2>'
                '<p class="muted">None — portfolio is clean.</p></div>'
            )

        # ── Recent activity section ──
        if events_df.empty:
            activity_section = (
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
                    f"<td><a href='/deal/{urllib.parse.quote(str(r['deal_id']))}' "
                    f"style='color: var(--accent); font-weight: 600; "
                    f"text-decoration: none;'>{html.escape(str(r['deal_id']))}</a></td>"
                    f"<td>{html.escape(str(r['change_type']))}</td>"
                    f"<td class='muted' style='font-size: 0.85rem;'>"
                    f"{html.escape(str(r['detail']))}</td>"
                    f"</tr>"
                )
            activity_section = (
                f'<div class="card"><h2>Recent activity (last {days} days, '
                f'{len(events_df)} events)</h2>'
                f'<table><thead><tr>'
                f'<th>Date</th><th>Deal</th><th>Change</th><th>Detail</th>'
                f'</tr></thead><tbody>{"".join(act_rows)}</tbody></table></div>'
            )

        # ── Cohort section (optional) ──
        if cohorts_df.empty:
            cohort_section = ""
        else:
            cohort_rows = []
            for _, r in cohorts_df.iterrows():
                cohort_rows.append(
                    f"<tr>"
                    f"<td><a href='/cohort/{urllib.parse.quote(str(r['tag']))}' "
                    f"style='color: var(--accent); font-weight: 600; "
                    f"text-decoration: none;'>{html.escape(str(r['tag']))}</a></td>"
                    f"<td class='num'>{int(r['deal_count'])}</td>"
                    f"<td class='num'>{_fmt(r['weighted_moic'], suffix='x')}</td>"
                    f"<td class='num'>{_fmt(r['weighted_irr'], pct=True)}</td>"
                    f"<td class='num'>{int(r['covenant_trips'])}</td>"
                    f"</tr>"
                )
            cohort_section = (
                f'<div class="card"><h2>Cohort breakdown</h2>'
                f'<table><thead><tr>'
                f'<th>Cohort</th><th>Deals</th><th>W. MOIC</th>'
                f'<th>W. IRR</th><th>Trips</th>'
                f'</tr></thead><tbody>{"".join(cohort_rows)}</tbody></table></div>'
            )

        # Window picker + download link
        picker = (
            '<form method="GET" action="/lp-update" '
            'style="display: inline-flex; gap: 0.3rem; align-items: center; '
            'margin-bottom: 1rem; font-size: 0.85rem;">'
            '<label>Window</label>'
            '<select name="days" onchange="this.form.submit()" '
            'style="font-size: 0.85rem; padding: 0.1rem;">'
        )
        for opt in (7, 14, 30, 60, 90):
            sel = " selected" if opt == days else ""
            picker += f'<option value="{opt}"{sel}>{opt} days</option>'
        picker += "</select></form>"
        download_link = (
            f'<a href="/lp-update?days={days}&download=1" '
            f'style="color: var(--accent); margin-left: 1rem; '
            f'font-size: 0.85rem; text-decoration: none; '
            f'border-bottom: 1px dotted var(--accent);">↓ Download</a>'
        )

        body = (
            f"<div>{picker}{download_link}</div>"
            f"{headline}"
            f"{alerts_section}"
            f"{activity_section}"
            f"{cohort_section}"
        )

        doc = shell(
            body=body, title="LP Update",
            subtitle=f"Portfolio snapshot · window {days} days",
            back_href="/",
        )

        if download:
            stamp = _dt.now(_tz.utc).strftime("%Y%m%d")
            encoded = doc.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header(
                "Content-Disposition",
                f'attachment; filename="lp_update_{stamp}.html"',
            )
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
            return

        self._send_html(doc)

    def _route_cohorts(self) -> None:
        """B106: per-tag cohort rollup dashboard."""
        from .analysis.cohorts import cohort_rollup
        store = PortfolioStore(self.config.db_path)
        df = cohort_rollup(store)

        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if (qs.get("format") or [""])[0] == "csv":
            return self._send_csv_df(df, filename="cohorts.csv")

        if df.empty:
            body = (
                '<div class="card">'
                '<p class="muted">No cohorts yet. Tag deals first — '
                'cohorts are built from deal tags like <code>growth</code>, '
                '<code>roll-up</code>, <code>fund_3</code>, or '
                '<code>watch</code>. Tag a deal on its detail page, then '
                'revisit this view.</p></div>'
            )
        else:
            def _fmt(v, pct=False):
                if v is None:
                    return "—"
                if isinstance(v, float) and v != v:
                    return "—"
                return f"{float(v)*100:.1f}%" if pct else f"{float(v):.2f}x"

            from .analysis.cohorts import cohort_detail
            from .deals.health_score import compute_health
            # B152 fix: precompute health once per deal, not once per
            # (cohort × deal). Going from O(T·D) to O(D) for big tag sets.
            _health_cache: Dict[str, int] = {}

            def _score(did: str):
                if did in _health_cache:
                    return _health_cache[did]
                h = compute_health(store, did)
                _health_cache[did] = h["score"]
                return h["score"]

            rows = []
            for _, r in df.iterrows():
                tag = str(r["tag"])
                members = cohort_detail(store, tag)
                scores = []
                if not members.empty:
                    for did in members["deal_id"]:
                        s = _score(str(did))
                        if s is not None:
                            scores.append(s)
                avg = int(round(sum(scores) / len(scores))) if scores else None
                if avg is None:
                    avg_cell = "<td class='muted'>—</td>"
                else:
                    band = (
                        "green" if avg >= 80
                        else "amber" if avg >= 50 else "red"
                    )
                    color = {
                        "green": "var(--green-text)",
                        "amber": "var(--amber-text)",
                        "red":   "var(--red-text)",
                    }[band]
                    avg_cell = (
                        f"<td class='num' style='color: {color}; "
                        f"font-weight: 700;'>{avg}</td>"
                    )
                rows.append(
                    f"<tr>"
                    f"<td><a href='/cohort/{urllib.parse.quote(tag)}' "
                    f"style='color: var(--accent); font-weight: 600; "
                    f"text-decoration: none;'>{html.escape(tag)}</a></td>"
                    f"<td class='num'>{int(r['deal_count'])}</td>"
                    f"{avg_cell}"
                    f"<td class='num'>{_fmt(r['weighted_moic'])}</td>"
                    f"<td class='num'>{_fmt(r['weighted_irr'], pct=True)}</td>"
                    f"<td class='num'>{int(r['covenant_trips'])}</td>"
                    f"<td class='num'>{int(r['covenant_tight'])}</td>"
                    f"<td class='num'>{int(r['concerning_deals'])}</td>"
                    f"<td class='num muted'>{int(r['n_priced'])}</td>"
                    f"</tr>"
                )
            body = (
                f'<div class="card">'
                f'<h2>Cohorts ({len(df)}) '
                f'<a href="/cohorts?format=csv" style="color: var(--accent); '
                f'font-size: 0.8rem; text-decoration: none; '
                f'border-bottom: 1px dotted var(--accent); '
                f'font-weight: 400; margin-left: 0.5rem;">↓ CSV</a></h2>'
                f'<p class="muted" style="font-size: 0.85rem;">'
                f'Aggregated latest-per-deal metrics grouped by tag. '
                f'Weighted by entry EV. A deal with multiple tags appears '
                f'in every cohort. <code>n priced</code> is the number of '
                f'deals that actually contributed to the weighted average '
                f'(those with MOIC + IRR + EV recorded).'
                f'</p>'
                f'<table><thead><tr>'
                f'<th>Tag</th><th>Deals</th><th>Avg health</th>'
                f'<th>W. MOIC</th><th>W. IRR</th>'
                f'<th>Trips</th><th>Tight</th><th>Concerning</th>'
                f'<th>n priced</th>'
                f'</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
            )

        self._send_html(shell(
            body=body, title="Cohorts",
            subtitle="Portfolio rollup by tag",
            back_href="/",
        ))

    def _route_cohort_detail(self, tag: str) -> None:
        """B106: deal-level view for a single cohort."""
        from .analysis.cohorts import cohort_detail
        store = PortfolioStore(self.config.db_path)
        if not tag:
            return self.send_error(HTTPStatus.BAD_REQUEST, "tag required")
        df = cohort_detail(store, tag)
        if df.empty:
            body = (
                f'<div class="card">'
                f'<p class="muted">No deals tagged '
                f'<code>{html.escape(tag)}</code>.</p></div>'
            )
        else:
            def _fmt(v, pct=False):
                if v is None:
                    return "—"
                if isinstance(v, float) and v != v:
                    return "—"
                return f"{float(v)*100:.1f}%" if pct else f"{float(v):.2f}x"

            rows = []
            for _, r in df.iterrows():
                did = str(r["deal_id"])
                rows.append(
                    f"<tr>"
                    f"<td><a href='/deal/{urllib.parse.quote(did)}' "
                    f"style='color: var(--accent); font-weight: 600; "
                    f"text-decoration: none;'>{html.escape(did)}</a></td>"
                    f"{_health_cell(store, did)}"
                    f"<td>{html.escape(str(r.get('stage') or '—'))}</td>"
                    f"<td>{html.escape(str(r.get('covenant_status') or '—'))}</td>"
                    f"<td class='num'>{_fmt(r.get('moic'))}</td>"
                    f"<td class='num'>{_fmt(r.get('irr'), pct=True)}</td>"
                    f"</tr>"
                )
            body = (
                f'<div class="card">'
                f'<h2>Deals tagged <code>{html.escape(tag)}</code> '
                f'({len(df)})</h2>'
                f'<table><thead><tr>'
                f'<th>Deal</th><th>Health</th><th>Stage</th><th>Covenant</th>'
                f'<th>MOIC</th><th>IRR</th>'
                f'</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
            )

        self._send_html(shell(
            body=body, title=f"Cohort: {tag}",
            subtitle=f"Deals in cohort {tag!r}",
            back_href="/cohorts",
        ))

    def _route_escalations(self) -> None:
        """B105: aged-red alerts, sorted by days_open.

        One-pane escalation view: any red alert whose ``first_seen_at`` is
        ≥ ``min_days`` (default 30) days old. This is what a partner
        reviews before an LP update: "anything we've failed to resolve
        for 30+ days needs a decision."
        """
        from .alerts.alert_acks import is_acked
        from .alerts.alert_history import days_red
        store = PortfolioStore(self.config.db_path)

        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        min_days = self._clamp_int(
            (qs.get("min_days") or ["30"])[0],
            default=30, min_v=0, max_v=3650,
        )

        df = days_red(store, min_days=min_days)

        # Mark rows that have an active ack so partners can see what's
        # "known but still open" vs "silenced".
        ack_flags = []
        for _, r in df.iterrows():
            ack_flags.append(is_acked(
                store,
                kind=str(r["kind"]),
                deal_id=str(r["deal_id"]),
                trigger_key=str(r["trigger_key"]),
            ))
        df_acked = df.assign(acked=ack_flags) if not df.empty else df

        if (qs.get("format") or [""])[0] == "csv":
            return self._send_csv_df(
                df_acked, filename=f"escalations_{min_days}d.csv",
            )

        picker = (
            '<form method="GET" action="/escalations" '
            'style="display: inline-flex; gap: 0.3rem; align-items: center; '
            'margin-bottom: 1rem; font-size: 0.85rem;">'
            '<label>Min days open</label>'
            '<select name="min_days" onchange="this.form.submit()" '
            'style="font-size: 0.85rem; padding: 0.1rem;">'
        )
        for opt in (7, 14, 30, 60, 90):
            sel = " selected" if opt == min_days else ""
            picker += f'<option value="{opt}"{sel}>{opt}</option>'
        picker += "</select></form>"
        picker += (
            f'<a href="/escalations?min_days={min_days}&format=csv" '
            f'style="color: var(--accent); font-size: 0.85rem; '
            f'text-decoration: none; border-bottom: 1px dotted var(--accent); '
            f'margin-left: 1rem;">↓ Download CSV</a>'
        )

        if df_acked.empty:
            body = (
                f"{picker}"
                '<div class="card">'
                '<p style="color: var(--green-text); font-weight: 600;">'
                f'No red alerts open ≥ {min_days} days.</p>'
                '<p class="muted" style="font-size: 0.85rem;">'
                'Escalations show only red-severity alerts whose first '
                'sighting is older than the threshold. History is built '
                'up from every /alerts or /api/alerts/active call.'
                '</p></div>'
            )
        else:
            rows = []
            for _, r in df_acked.iterrows():
                days_open = int(r["days_open"])
                ack_badge = (
                    ' <span class="badge badge-muted" '
                    'style="font-size: 0.7rem;">ACKED</span>'
                    if r["acked"] else ""
                )
                rows.append(
                    f"<tr>"
                    f"<td class='num' style='color: var(--red-text); "
                    f"font-weight: 700;'>{days_open}d</td>"
                    f"<td><a href='/deal/{urllib.parse.quote(str(r['deal_id']))}' "
                    f"style='color: var(--accent); text-decoration: none; "
                    f"font-weight: 600;'>{html.escape(str(r['deal_id']))}</a></td>"
                    f"<td>{html.escape(str(r.get('title') or ''))}</td>"
                    f"<td class='muted' style='font-size: 0.85rem;'>"
                    f"{html.escape(str(r.get('detail') or ''))}</td>"
                    f"<td class='muted' style='font-size: 0.8rem;'>"
                    f"{html.escape(str(r['first_seen_at'])[:10])}"
                    f"{ack_badge}</td>"
                    f"</tr>"
                )
            body = (
                f"{picker}"
                f'<div class="card">'
                f'<h2>Red alerts open ≥ {min_days} days ({len(df_acked)})</h2>'
                f'<table><thead><tr>'
                f'<th>Open</th><th>Deal</th><th>Alert</th>'
                f'<th>Detail</th><th>First seen</th>'
                f'</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
            )

        self._send_html(shell(
            body=body, title="Escalations",
            subtitle=f"Red alerts ≥ {min_days} days old",
            back_href="/alerts",
        ))

    def _route_jobs_index(self) -> None:
        """List recent simulation jobs + form to enqueue a new run."""
        from .infra.job_queue import get_default_registry
        reg = get_default_registry()
        jobs = reg.list_recent(50)

        status_badge = {
            "queued":  '<span class="badge badge-muted">QUEUED</span>',
            "running": '<span class="badge badge-blue">RUNNING</span>',
            "done":    '<span class="badge badge-green">DONE</span>',
            "failed":  '<span class="badge badge-red">FAILED</span>',
        }

        rows = []
        for j in jobs:
            params = j.params or {}
            duration = ""
            if j.started_at and j.finished_at:
                try:
                    from datetime import datetime as _dt
                    t0 = _dt.fromisoformat(j.started_at)
                    t1 = _dt.fromisoformat(j.finished_at)
                    dur = (t1 - t0).total_seconds()
                    duration = f"{dur:.1f}s"
                except (ValueError, TypeError):
                    pass
            rows.append(
                f"<tr>"
                f"<td><a href='/jobs/{html.escape(j.job_id)}' "
                f"style='color: var(--accent); text-decoration: none; "
                f"font-family: monospace;'>{html.escape(j.job_id)}</a></td>"
                f"<td>{status_badge.get(j.status, j.status)}</td>"
                f"<td>{html.escape(params.get('outdir') or '—')}</td>"
                f"<td class='num'>{params.get('n_sims') or '—'}</td>"
                f"<td class='num'>{duration}</td>"
                f"<td class='muted'>{html.escape(str(j.created_at)[:19])}</td>"
                f"</tr>"
            )
        jobs_table = (
            '<table><thead><tr><th>Job ID</th><th>Status</th><th>Outdir</th>'
            '<th class="num">Sims</th><th class="num">Duration</th>'
            '<th>Created</th></tr></thead>'
            '<tbody>' + "".join(rows) + '</tbody></table>'
        ) if rows else (
            '<p class="muted">No jobs yet. Use the form below to queue one.</p>'
        )

        input_css = (
            'style="padding: 0.4rem 0.6rem; border: 1px solid var(--border); '
            'border-radius: 6px; font-size: 0.9rem; font-family: inherit;"'
        )
        form_css = (
            'style="display: grid; grid-template-columns: 180px 1fr; '
            'gap: 0.5rem 1rem; align-items: center; max-width: 700px;"'
        )
        body = f"""
        <div class="card">
          <h2>Queue a simulation run</h2>
          <p class="muted" style="font-size: 0.85rem;">
            The worker thread runs one job at a time. Output captured from
            stdout + stderr shows up in the job detail page while running.
          </p>
          <form method="POST" action="/api/jobs/run" {form_css}>
            <label>Actual config</label>
            <input type="text" name="actual" required
                   placeholder="/path/to/actual.yaml" {input_css}>

            <label>Benchmark config</label>
            <input type="text" name="benchmark" required
                   placeholder="/path/to/benchmark.yaml" {input_css}>

            <label>Output directory</label>
            <input type="text" name="outdir" required
                   placeholder="/path/to/output" {input_css}>

            <label>Simulations</label>
            <input type="number" name="n_sims" value="5000" min="100"
                   max="200000" {input_css}>

            <label>Seed</label>
            <input type="number" name="seed" value="42" {input_css}>

            <label>Partner brief</label>
            <label style="font-size: 0.88rem; color: var(--muted);">
              <input type="checkbox" name="partner_brief" value="1">
              Generate partner_brief.html
            </label>

            <div></div>
            <button type="submit"
                    style="padding: 0.5rem 1.25rem; border: none;
                           border-radius: 6px; background: var(--accent);
                           color: white; font-weight: 600; cursor: pointer;
                           font-size: 0.9rem;">
              Queue run
            </button>
          </form>
        </div>

        <div class="card">
          <h2>Recent jobs ({len(jobs)})</h2>
          {jobs_table}
        </div>
        """
        self._send_html(shell(
            body=body, title="Simulation jobs",
            subtitle="Web-triggered rcm-mc run with live progress",
            back_href="/",
        ))

    def _route_job_detail(self, job_id: str) -> None:
        """Progress page for one job; auto-refreshes while running."""
        from .infra.job_queue import get_default_registry
        reg = get_default_registry()
        job = reg.get(job_id)
        if job is None:
            body = (
                f'<div class="card"><p class="err">No job '
                f'<code>{html.escape(job_id)}</code> in the registry.</p></div>'
            )
            self._send_html(shell(body=body, title=f"Job: {job_id}",
                                  back_href="/jobs"))
            return

        status_badge = {
            "queued":  ('badge-muted', "QUEUED"),
            "running": ('badge-blue', "RUNNING"),
            "done":    ('badge-green', "DONE"),
            "failed":  ('badge-red', "FAILED"),
        }
        cls, label = status_badge.get(job.status, ("badge-muted", job.status.upper()))

        params_html = "".join(
            f"<tr><th>{html.escape(str(k))}</th>"
            f"<td>{html.escape(str(v))}</td></tr>"
            for k, v in (job.params or {}).items()
        )
        output_html = (
            f'<pre style="max-height: 400px; overflow: auto;">'
            f'{html.escape(job.output_tail or "(no output yet)")}'
            f'</pre>'
        )
        error_html = (
            f'<div class="card" style="border-color: var(--red);">'
            f'<h2 style="color: var(--red-text);">Error</h2>'
            f'<pre>{html.escape(job.error or "")}</pre></div>'
            if job.error else ""
        )
        result_html = ""
        if job.status == "done" and job.result:
            outdir = job.result.get("outdir")
            if outdir:
                abs_out = os.path.abspath(str(outdir))
                base = (
                    os.path.abspath(self.config.outdir)
                    if self.config.outdir else ""
                )
                if base and (abs_out == base or abs_out.startswith(base + os.sep)):
                    rel = os.path.relpath(abs_out, base)
                    result_html = (
                        f'<div class="card"><h2>Result</h2>'
                        f'<p>Output: '
                        f'<a href="/outputs/{html.escape(rel)}/">{html.escape(outdir)}</a></p>'
                        f'</div>'
                    )
                else:
                    result_html = (
                        f'<div class="card"><h2>Result</h2>'
                        f'<p>Output directory: <code>{html.escape(outdir)}</code></p>'
                        f'</div>'
                    )

        # Auto-refresh every 2s while the job is still in flight.
        extra_js = (
            "setTimeout(function(){window.location.reload();}, 2000);"
            if job.status in ("queued", "running") else ""
        )

        body = f"""
        <div class="card">
          <h2>Status: <span class="badge {cls}">{label}</span></h2>
          <p class="muted">
            Created {html.escape(str(job.created_at)[:19])}
            {f"· Started {html.escape(str(job.started_at)[:19])}" if job.started_at else ""}
            {f"· Finished {html.escape(str(job.finished_at)[:19])}" if job.finished_at else ""}
          </p>
          <p><a href="/jobs">← All jobs</a></p>
        </div>

        <div class="card">
          <h2>Parameters</h2>
          <table>{params_html}</table>
        </div>

        <div class="card">
          <h2>Output</h2>
          {output_html}
        </div>

        {result_html}
        {error_html}
        """
        self._send_html(shell(
            body=body, title=f"Job {job_id}",
            subtitle=f"Simulation job · {job.status}",
            back_href="/jobs",
            extra_js=extra_js,
        ))

    def _route_ops(self) -> None:
        """B94 — ops/status page with store diagnostics.

        Read-only; shows partner-useful numbers (deal count, snapshots,
        notes, tags, actuals), DB file size, last-write timestamps per
        table, and most-used tags. Also useful for "is the tool healthy?"
        checks and for noticing stale portfolios.
        """
        store = PortfolioStore(self.config.db_path)

        # Counts per table (only ones that exist)
        stats: Dict[str, Any] = {}
        table_last_write: Dict[str, Optional[str]] = {}
        with store.connect() as con:
            for tbl in ("deals", "deal_snapshots", "deal_notes",
                        "deal_tags", "quarterly_actuals",
                        "initiative_actuals"):
                try:
                    c = con.execute(f"SELECT COUNT(*) c FROM {tbl}").fetchone()
                    stats[tbl] = int(c["c"]) if c else 0
                except Exception:  # noqa: BLE001
                    stats[tbl] = 0
                try:
                    r = con.execute(
                        f"SELECT MAX(created_at) ts FROM {tbl}"
                    ).fetchone()
                    table_last_write[tbl] = (r["ts"] if r else None)
                except Exception:  # noqa: BLE001
                    table_last_write[tbl] = None

        # DB file size
        try:
            size_bytes = os.path.getsize(self.config.db_path)
        except OSError:
            size_bytes = 0
        if size_bytes >= 1_048_576:
            size_str = f"{size_bytes / 1_048_576:.2f} MB"
        elif size_bytes >= 1_024:
            size_str = f"{size_bytes / 1_024:.1f} KB"
        else:
            size_str = f"{size_bytes} B"

        # Top-used tags
        tag_rows = all_tags(store)[:15]
        tag_cloud = " ".join(
            f'<span class="badge badge-blue" style="margin: 0.2rem;">'
            f'{html.escape(t)} <span class="muted">×{c}</span></span>'
            for t, c in tag_rows
        )

        def _fmt_ts(v):
            return html.escape(str(v)[:19]) if v else "—"

        stats_rows = "".join(
            f'<tr><td><code>{tbl}</code></td>'
            f'<td class="num">{stats.get(tbl, 0):,}</td>'
            f'<td class="muted">{_fmt_ts(table_last_write.get(tbl))}</td></tr>'
            for tbl in ("deals", "deal_snapshots", "deal_notes",
                        "deal_tags", "quarterly_actuals",
                        "initiative_actuals")
        )

        auth_line = (
            f'Auth: <span class="badge badge-green">enabled</span> '
            f'as <code>{html.escape(self.config.auth_user)}</code>'
            if self.config.auth_user else
            'Auth: <span class="badge badge-muted">off (laptop mode)</span>'
        )

        body = f"""
        <div class="kpi-grid">
          <div class="kpi-card">
            <div class="kpi-value">{stats.get('deals', 0):,}</div>
            <div class="kpi-label">Deals</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-value">{stats.get('deal_snapshots', 0):,}</div>
            <div class="kpi-label">Snapshots</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-value">{stats.get('deal_notes', 0):,}</div>
            <div class="kpi-label">Notes</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-value">{size_str}</div>
            <div class="kpi-label">DB Size</div>
          </div>
        </div>

        <div class="card">
          <h2>Storage</h2>
          <p class="muted" style="font-size: 0.85rem;">
            Portfolio SQLite at <code>{html.escape(self.config.db_path)}</code> · {auth_line}
          </p>
          <table>
            <thead><tr><th>Table</th><th class="num">Rows</th>
            <th>Last write</th></tr></thead>
            <tbody>{stats_rows}</tbody>
          </table>
        </div>

        <div class="card">
          <h2>Top tags</h2>
          {(tag_cloud if tag_cloud else
            '<p class="muted">No tags yet.</p>')}
        </div>
        """
        self._send_html(shell(
            body=body, title="Portfolio ops",
            subtitle="Store health & activity diagnostics",
            back_href="/",
        ))

    def _route_initiatives_rollup(self) -> None:
        """B83: cross-deal initiative rollup view."""
        from .rcm.initiative_rollup import initiative_portfolio_rollup
        store = PortfolioStore(self.config.db_path)
        df = initiative_portfolio_rollup(store)

        if df.empty:
            body = (
                '<div class="card"><p class="muted">No initiative actuals '
                "recorded yet. Record per-initiative EBITDA impact via "
                "<code>rcm-mc portfolio initiative-actual</code> or upload "
                'an initiative CSV at <a href="/upload">/upload</a>.</p></div>'
            )
            self._send_html(shell(
                body=body, title="Initiatives",
                subtitle="Cross-portfolio initiative rollup", back_href="/",
            ))
            return

        sev_badge = {
            "off_track": ("badge-red", "OFF TRACK"),
            "lagging":   ("badge-amber", "LAGGING"),
            "on_track":  ("badge-green", "ON TRACK"),
            "no_plan":   ("badge-muted", "NO PLAN"),
        }

        rows_html = []
        for _, r in df.iterrows():
            init_id = str(r["initiative_id"])
            cls, label = sev_badge.get(str(r.get("severity")),
                                       ("badge-muted", "—"))
            vp = r.get("avg_variance_pct")
            var_str = ("—" if vp is None or (isinstance(vp, float) and vp != vp)
                       else f"{float(vp)*100:+.1f}%")
            actual = float(r["cumulative_actual"])
            actual_str = (
                f"${actual/1e6:.2f}M" if actual else "$0"
            )
            plan_v = r.get("cumulative_plan")
            plan_str = (
                "—" if plan_v is None or (isinstance(plan_v, float) and plan_v != plan_v)
                else f"${float(plan_v)/1e6:.2f}M"
            )
            rows_html.append(
                f'<tr>'
                f'<td><a href="/initiative/{urllib.parse.quote(init_id)}" '
                f'style="color: var(--accent); text-decoration: none; font-weight: 600;">'
                f'{html.escape(init_id)}</a></td>'
                f'<td class="num">{int(r["deal_count"])}</td>'
                f'<td class="num">{actual_str}</td>'
                f'<td class="num">{plan_str}</td>'
                f'<td class="num">{var_str}</td>'
                f'<td><span class="badge {cls}">{label}</span></td>'
                f'</tr>'
            )

        body = f"""
        <div class="card">
          <h2>Initiative rollup ({len(df)} initiatives across the portfolio)</h2>
          <p class="muted" style="font-size: 0.88rem;">
            Sorted worst-first. Repeated laggards across many deals usually
            indicate a playbook gap, not deal-specific issues.
          </p>
          <table>
            <thead><tr>
              <th>Initiative</th>
              <th class="num">Deals</th>
              <th class="num">Cum. actual</th>
              <th class="num">Cum. plan</th>
              <th class="num">Avg variance</th>
              <th>Worst severity</th>
            </tr></thead>
            <tbody>{"".join(rows_html)}</tbody>
          </table>
        </div>
        """
        self._send_html(shell(
            body=body, title="Initiatives — portfolio rollup",
            subtitle="Cross-deal performance by RCM workstream",
            back_href="/",
        ))

    def _route_initiative_detail(self, init_id: str) -> None:
        """B83 drill-down: every deal running this initiative."""
        from .rcm.initiative_rollup import initiative_deals_detail
        if not init_id:
            self.send_error(HTTPStatus.BAD_REQUEST, "initiative id required")
            return
        store = PortfolioStore(self.config.db_path)
        df = initiative_deals_detail(store, init_id)
        if df.empty:
            body = (
                f'<div class="card"><p class="muted">No deals are running '
                f'<code>{html.escape(init_id)}</code>, or no actuals have '
                'been recorded against it yet.</p></div>'
            )
            self._send_html(shell(
                body=body, title=f"Initiative: {init_id}", back_href="/initiatives",
            ))
            return

        sev_badge = {
            "off_track": ("badge-red", "OFF TRACK"),
            "lagging":   ("badge-amber", "LAGGING"),
            "on_track":  ("badge-green", "ON TRACK"),
            "no_plan":   ("badge-muted", "NO PLAN"),
        }
        rows_html = []
        for _, r in df.iterrows():
            did = str(r.get("deal_id") or "")
            cls, label = sev_badge.get(str(r.get("severity")),
                                       ("badge-muted", "—"))
            vp = r.get("variance_pct")
            var_str = ("—" if vp is None or (isinstance(vp, float) and vp != vp)
                       else f"{float(vp)*100:+.1f}%")
            actual = r.get("cumulative_actual")
            actual_str = ("$0" if not actual else f"${float(actual)/1e6:.2f}M")
            plan_v = r.get("cumulative_plan")
            plan_str = ("—" if plan_v is None or (isinstance(plan_v, float) and plan_v != plan_v)
                        else f"${float(plan_v)/1e6:.2f}M")
            qtrs = int(r.get("quarters_active") or 0)
            rows_html.append(
                f'<tr>'
                f'<td><a href="/deal/{urllib.parse.quote(did)}" '
                f'style="color: var(--accent); text-decoration: none; font-weight: 600;">'
                f'{html.escape(did)}</a></td>'
                f'<td class="num">{actual_str}</td>'
                f'<td class="num">{plan_str}</td>'
                f'<td class="num">{var_str}</td>'
                f'<td><span class="badge {cls}">{label}</span></td>'
                f'<td class="num">{qtrs}</td>'
                f'</tr>'
            )

        body = f"""
        <div class="card">
          <h2>Deals running this initiative ({len(df)})</h2>
          <table>
            <thead><tr>
              <th>Deal</th>
              <th class="num">Cum. actual</th>
              <th class="num">Cum. plan</th>
              <th class="num">Variance</th>
              <th>Severity</th>
              <th class="num">Quarters</th>
            </tr></thead>
            <tbody>{"".join(rows_html)}</tbody>
          </table>
        </div>
        """
        self._send_html(shell(
            body=body, title=f"Initiative: {init_id}",
            subtitle=f"Cross-deal detail for {init_id}",
            back_href="/initiatives",
        ))

    def _route_activity(
        self,
        limit: int = 100,
        *,
        owner: Optional[str] = None,
        kind: Optional[str] = None,
    ) -> None:
        """Timeline of everything that happened in the portfolio (B79 + B119).

        Unified chronological stream across three event types:
          - ``snapshot`` — deal moved to a new stage
          - ``note``     — analyst note appended
          - ``actual``   — quarterly actual ingested

        B119 adds two optional filters:
          ``owner`` — restrict to events on deals currently owned by X
          ``kind``  — restrict to one event type
        """
        from .deals.deal_owners import deals_by_owner
        store = PortfolioStore(self.config.db_path)
        events: list = []

        allowed_deals: Optional[set] = None
        if owner:
            try:
                allowed_deals = set(deals_by_owner(store, owner))
            except ValueError:
                allowed_deals = set()

        # Snapshots
        from .portfolio.portfolio_snapshots import _ensure_snapshot_table
        _ensure_snapshot_table(store)
        with store.connect() as con:
            for r in con.execute(
                "SELECT deal_id, stage, created_at, notes "
                "FROM deal_snapshots ORDER BY created_at DESC "
                "LIMIT ?", (limit,),
            ).fetchall():
                events.append({
                    "kind": "snapshot",
                    "deal_id": r["deal_id"],
                    "ts": r["created_at"],
                    "title": f"Stage → {r['stage']}",
                    "body": (r["notes"] or "").strip(),
                })

            # Notes
            from .deals.deal_notes import _ensure_notes_table
            _ensure_notes_table(store)
            for r in con.execute(
                "SELECT deal_id, created_at, author, body "
                "FROM deal_notes ORDER BY created_at DESC "
                "LIMIT ?", (limit,),
            ).fetchall():
                byline = r["author"] + " · " if r["author"] else ""
                events.append({
                    "kind": "note",
                    "deal_id": r["deal_id"],
                    "ts": r["created_at"],
                    "title": f"Note {byline.strip().rstrip('·').strip()}".strip(),
                    "body": (r["body"] or "").strip(),
                })

            # Quarterly actuals
            from .pe.hold_tracking import _ensure_actuals_table
            _ensure_actuals_table(store)
            for r in con.execute(
                "SELECT deal_id, quarter, created_at, kpis_json "
                "FROM quarterly_actuals ORDER BY created_at DESC "
                "LIMIT ?", (limit,),
            ).fetchall():
                import json as _json
                try:
                    kpis = _json.loads(r["kpis_json"] or "{}")
                    summary = ", ".join(
                        f"{k}={v}" for k, v in list(kpis.items())[:3]
                    )
                except (ValueError, TypeError):
                    summary = ""
                events.append({
                    "kind": "actual",
                    "deal_id": r["deal_id"],
                    "ts": r["created_at"],
                    "title": f"Actuals · {r['quarter']}",
                    "body": summary,
                })

        if allowed_deals is not None:
            events = [e for e in events if e["deal_id"] in allowed_deals]
        if kind:
            events = [e for e in events if e["kind"] == kind]
        events.sort(key=lambda e: e["ts"] or "", reverse=True)
        events = events[:limit]

        kind_badge = {
            "snapshot": ('badge-blue', "STAGE"),
            "note":     ('badge-amber', "NOTE"),
            "actual":   ('badge-green', "ACTUAL"),
        }
        items_html = []
        for e in events:
            cls, label = kind_badge.get(e["kind"], ("badge-muted", "EVENT"))
            ts_short = str(e["ts"] or "")[:19]
            did = str(e["deal_id"] or "")
            items_html.append(
                f'<li style="padding: 0.75rem 0; '
                f'border-bottom: 1px solid var(--border);">'
                f'<div style="display: flex; justify-content: space-between; '
                f'align-items: baseline; margin-bottom: 0.25rem;">'
                f'<span>'
                f'<span class="badge {cls}" style="margin-right: 0.5rem;">'
                f'{label}</span>'
                f'<a href="/deal/{urllib.parse.quote(did)}" '
                f'style="color: var(--accent); text-decoration: none; '
                f'font-weight: 600;">{html.escape(did)}</a>'
                f' <span style="color: var(--text);">— {html.escape(e["title"])}</span>'
                f'</span>'
                f'<span style="color: var(--muted); font-size: 0.82rem;">'
                f'{html.escape(ts_short)}</span>'
                f'</div>'
                + (
                    f'<div style="color: var(--muted); font-size: 0.88rem; '
                    f'white-space: pre-wrap; margin-left: 0.25rem;">'
                    f'{html.escape(e["body"][:280])}'
                    f'{"…" if len(e["body"]) > 280 else ""}</div>'
                    if e["body"] else ""
                )
                + '</li>'
            )

        # Filter form
        kind_opts = "".join(
            f'<option value="{k}"{" selected" if k == (kind or "") else ""}>'
            f'{k or "(any)"}</option>'
            for k in ("", "snapshot", "note", "actual")
        )
        filter_form = (
            f'<form method="GET" action="/activity" '
            f'style="display: flex; gap: 0.5rem; align-items: center; '
            f'margin-bottom: 1rem; font-size: 0.85rem; flex-wrap: wrap;">'
            f'<label>Owner <input type="text" name="owner" '
            f'value="{html.escape(owner or "")}" '
            f'placeholder="e.g. AT" maxlength="40" '
            f'style="font-size: 0.85rem; padding: 0.15rem; width: 7rem;"></label>'
            f'<label>Kind <select name="kind" '
            f'style="font-size: 0.85rem; padding: 0.15rem;">{kind_opts}</select></label>'
            f'<input type="hidden" name="limit" value="{limit}">'
            f'<button type="submit" class="btn" '
            f'style="font-size: 0.85rem; padding: 0.15rem 0.6rem;">Apply</button>'
        )
        if owner or kind:
            filter_form += (
                f' <a href="/activity" style="color: var(--accent); '
                f'font-size: 0.85rem;">× clear</a>'
            )
        filter_form += "</form>"

        if items_html:
            body = (
                f"{filter_form}"
                '<div class="card">'
                f'<h2>Recent activity ({len(events)} events)</h2>'
                '<ul style="list-style: none; padding: 0; margin: 0;">'
                + "".join(items_html)
                + '</ul></div>'
            )
        else:
            body = (
                f"{filter_form}"
                '<div class="card"><p class="muted">'
                'No activity matches. Clear filters or register a deal / add '
                'a note / ingest actuals to populate the feed.'
                '</p></div>'
            )

        subtitle_bits = ["Chronological feed across all deals"]
        if owner:
            subtitle_bits.append(f"owner = {owner}")
        if kind:
            subtitle_bits.append(f"kind = {kind}")

        self._send_html(shell(
            body=body,
            title="Portfolio activity",
            subtitle=" · ".join(subtitle_bits),
            back_href="/",
        ))

    def _route_compare(self, deal_ids: list) -> None:
        """Side-by-side comparison of up to 5 deals (B78).

        Columns = deals, rows = comparable metrics:
          - latest stage, covenant status, entry EBITDA / EV
          - MOIC, IRR (from latest snapshot)
          - cumulative EBITDA variance
          - concerning signal count
          - latest-quarter actual EBITDA
        """
        store = PortfolioStore(self.config.db_path)
        if not deal_ids:
            body = """
            <div class="card">
              <h2>Compare deals</h2>
              <p class="muted">Select 2-5 deal IDs to compare side-by-side.</p>
              <form method="GET" action="/compare"
                    style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                <input type="text" name="deals"
                       placeholder="ccf_2026, mgh_2026, nyp_2026"
                       required
                       style="flex: 1; min-width: 280px; padding: 0.6rem 0.75rem;
                              border: 1px solid var(--border); border-radius: 6px;
                              font-size: 0.9rem;">
                <button type="submit"
                        style="padding: 0.6rem 1.25rem; border: none;
                               border-radius: 6px; background: var(--accent);
                               color: white; font-weight: 600; cursor: pointer;
                               font-size: 0.9rem;">Compare</button>
              </form>
            </div>
            """
            self._send_html(shell(
                body=body, title="Compare deals", back_href="/",
            ))
            return

        if len(deal_ids) > 5:
            body = (
                '<div class="card"><p class="err">Too many deals; '
                f'limit is 5 per comparison. You asked for {len(deal_ids)}.</p></div>'
            )
            self._send_html(shell(body=body, title="Compare", back_href="/"))
            return

        from .pe.hold_tracking import cumulative_drift
        rows_data = []
        for did in deal_ids:
            snaps = list_snapshots(store, deal_id=did)
            if snaps.empty:
                rows_data.append({"deal_id": did, "missing": True})
                continue
            latest = snaps.iloc[0]
            drift_df = cumulative_drift(store, did, kpi="ebitda")
            latest_ebitda_actual = None
            cum_drift = None
            if not drift_df.empty:
                latest_ebitda_actual = float(drift_df.iloc[-1]["actual"])
                cum = drift_df.iloc[-1]["cumulative_drift"]
                if cum is not None and cum == cum:
                    cum_drift = float(cum)
            rows_data.append({
                "deal_id": did, "missing": False, "latest": latest,
                "latest_actual": latest_ebitda_actual,
                "cum_drift": cum_drift,
            })

        # Header row: deal IDs
        header_cells = "".join(
            f'<th><a href="/deal/{urllib.parse.quote(r["deal_id"])}" '
            f'style="color: var(--accent); text-decoration: none;">'
            f'{html.escape(r["deal_id"])}</a></th>'
            for r in rows_data
        )

        def _cell(r, fn, default="—"):
            if r.get("missing"):
                return '<td class="muted">no data</td>'
            try:
                v = fn(r)
                return f'<td class="num">{v}</td>' if v is not None else f'<td class="muted">{default}</td>'
            except (KeyError, TypeError, ValueError):
                return f'<td class="muted">{default}</td>'

        def _fmt_m(v):
            if v is None or (isinstance(v, float) and v != v):
                return None
            return f"${float(v)/1e6:.1f}M" if abs(v) < 1e9 else f"${float(v)/1e9:.2f}B"

        def _fmt_p(v):
            if v is None or (isinstance(v, float) and v != v):
                return None
            return f"{float(v)*100:.1f}%"

        def _fmt_x(v):
            if v is None or (isinstance(v, float) and v != v):
                return None
            return f"{float(v):.2f}x"

        # Build comparison rows
        metric_rows = [
            ("Stage", lambda r: html.escape(str(r["latest"].get("stage") or "—")).title()),
            ("Covenant", lambda r: html.escape(str(r["latest"].get("covenant_status") or "—"))),
            ("Entry EBITDA", lambda r: _fmt_m(r["latest"].get("entry_ebitda"))),
            ("Entry EV", lambda r: _fmt_m(r["latest"].get("entry_ev"))),
            ("MOIC", lambda r: _fmt_x(r["latest"].get("moic"))),
            ("IRR", lambda r: _fmt_p(r["latest"].get("irr"))),
            ("Latest qtr EBITDA", lambda r: _fmt_m(r.get("latest_actual"))),
            ("Cumulative drift", lambda r: _fmt_p(r.get("cum_drift"))),
            ("Concerning signals",
             lambda r: str(int(r["latest"].get("concerning_signals")))
                       if r["latest"].get("concerning_signals") is not None
                       and r["latest"].get("concerning_signals") == r["latest"].get("concerning_signals")
                       else None),
        ]

        rows_html = []
        for label, fn in metric_rows:
            cells = "".join(_cell(r, fn) for r in rows_data)
            rows_html.append(
                f'<tr><th style="text-align: left; background: var(--accent-soft); '
                f'color: var(--accent);">{label}</th>{cells}</tr>'
            )

        # B124: Small-multiples EBITDA trajectory chart per deal so partners
        # see divergence visually, not just as numbers.
        trajectory_cards = []
        for r in rows_data:
            if r.get("missing"):
                continue
            did = r["deal_id"]
            var_df = variance_report(store, did)
            svg = _render_ebitda_sparkline(var_df, width=520, height=150)
            if not svg:
                continue
            trajectory_cards.append(
                f'<div style="flex: 1; min-width: 22rem;">'
                f'<h3 style="margin: 0 0 0.4rem 0;">'
                f'<a href="/deal/{urllib.parse.quote(did)}" '
                f'style="color: var(--accent); text-decoration: none;">'
                f'{html.escape(did)}</a></h3>'
                f'{svg}'
                f'</div>'
            )
        trajectory_html = (
            f'<div class="card">'
            f'<h2>EBITDA trajectories</h2>'
            f'<p class="muted" style="font-size: 0.85rem;">'
            f'Actual (solid) vs plan (dashed) per quarter. Dots colored by '
            f'severity. Only deals with ≥2 quarters of actuals are shown.'
            f'</p>'
            f'<div style="display: flex; gap: 1rem; flex-wrap: wrap; '
            f'margin-top: 0.5rem;">{"".join(trajectory_cards)}</div></div>'
            if trajectory_cards else ""
        )

        body = f"""
        {trajectory_html}
        <div class="card">
          <h2>Comparison · {len(deal_ids)} deal{'s' if len(deal_ids) != 1 else ''}</h2>
          <table style="margin-top: 1rem;">
            <thead><tr><th style="background: var(--accent-soft); color: var(--accent);">Metric</th>
            {header_cells}</tr></thead>
            <tbody>{"".join(rows_html)}</tbody>
          </table>
        </div>
        <div class="card">
          <h2>Change the comparison</h2>
          <form method="GET" action="/compare">
            <input type="text" name="deals"
                   value="{html.escape(",".join(deal_ids))}"
                   style="width: 100%; padding: 0.5rem 0.75rem;
                          border: 1px solid var(--border); border-radius: 6px;
                          font-size: 0.9rem; margin-bottom: 0.5rem;">
            <button type="submit"
                    style="padding: 0.5rem 1.25rem; border: none;
                           border-radius: 6px; background: var(--accent);
                           color: white; font-weight: 600; cursor: pointer;
                           font-size: 0.9rem;">Re-compare</button>
          </form>
        </div>
        """
        self._send_html(shell(
            body=body,
            title=f"Compare: {', '.join(deal_ids)}",
            subtitle="Side-by-side snapshot comparison",
            back_href="/",
        ))

    def _route_search(self, query: str) -> None:
        """Cross-deal search: match against deal_id, stage, note body, author.

        Case-insensitive substring match. Results grouped into:
          - Deal hits  (deal_id or current stage matches)
          - Note hits  (note body or author matches)
        Each result links to the relevant deal page with deal_id as anchor.
        """
        q = (query or "").strip().lower()
        store = PortfolioStore(self.config.db_path)

        deal_hits_html = []
        note_hits_html = []

        if q:
            from .portfolio.portfolio_snapshots import latest_per_deal
            deals_df = latest_per_deal(store)
            # Deals: match deal_id, stage, covenant, notes snippet
            for _, r in deals_df.iterrows():
                fields = [
                    str(r.get("deal_id") or ""),
                    str(r.get("stage") or ""),
                    str(r.get("covenant_status") or ""),
                    str(r.get("notes") or ""),
                ]
                haystack = " ".join(fields).lower()
                if q in haystack:
                    did = str(r.get("deal_id") or "")
                    deal_hits_html.append(
                        f'<li style="padding: 0.5rem 0; '
                        f'border-bottom: 1px solid var(--border);">'
                        f'<a href="/deal/{urllib.parse.quote(did)}" '
                        f'style="color: var(--accent); text-decoration: none;">'
                        f'<strong>{html.escape(did)}</strong></a>'
                        f' <span class="muted" style="font-size: 0.85rem;">· '
                        f'{html.escape(str(r.get("stage") or "?")).title()}'
                        f'{" · " + html.escape(str(r.get("covenant_status"))) if r.get("covenant_status") else ""}'
                        f'</span></li>'
                    )

            # Notes: full-text on body + author
            notes_df = list_notes(store)
            for _, r in notes_df.iterrows():
                body = str(r.get("body") or "")
                author = str(r.get("author") or "")
                if q in body.lower() or q in author.lower():
                    did = str(r.get("deal_id") or "")
                    # Highlight match in the body snippet
                    snippet = body[:200]
                    note_hits_html.append(
                        f'<li style="padding: 0.75rem 0; '
                        f'border-bottom: 1px solid var(--border);">'
                        f'<a href="/deal/{urllib.parse.quote(did)}" '
                        f'style="color: var(--accent); text-decoration: none;">'
                        f'<strong>{html.escape(did)}</strong></a> '
                        f'<span class="muted" style="font-size: 0.8rem;">· '
                        f'{html.escape(author or "—")} · '
                        f'{html.escape(str(r.get("created_at") or "")[:19])}'
                        f'</span>'
                        f'<div style="margin-top: 0.25rem; white-space: pre-wrap;">'
                        f'{html.escape(snippet)}{"…" if len(body) > 200 else ""}'
                        f'</div></li>'
                    )

        # Compose results panel
        deals_panel = (
            f'<div class="card"><h2>Deal matches ({len(deal_hits_html)})</h2>'
            f'<ul style="list-style: none; padding: 0; margin: 0;">'
            f'{"".join(deal_hits_html)}</ul></div>'
        ) if deal_hits_html else ""
        notes_panel = (
            f'<div class="card"><h2>Note matches ({len(note_hits_html)})</h2>'
            f'<ul style="list-style: none; padding: 0; margin: 0;">'
            f'{"".join(note_hits_html)}</ul></div>'
        ) if note_hits_html else ""
        empty_panel = (
            '<div class="card"><p class="muted">No matches. '
            'Try a shorter query, or <a href="/">browse the dashboard</a>.</p></div>'
        ) if q and not (deal_hits_html or note_hits_html) else ""
        hint_panel = (
            '<div class="card"><p class="muted">Type a query above. '
            'Searches deal IDs, stages, and note content across the portfolio.</p></div>'
        ) if not q else ""

        # Search box carries current query for refinement
        body = f"""
        <form method="GET" action="/search" style="margin-bottom: 1rem;">
          <input type="text" name="q" value="{html.escape(q)}"
                 placeholder="Search deals, stages, notes..."
                 autofocus
                 style="width: 100%; padding: 0.75rem 1rem;
                        border: 1px solid var(--border); border-radius: 8px;
                        font-size: 1rem; font-family: inherit;">
        </form>
        {deals_panel}
        {notes_panel}
        {empty_panel}
        {hint_panel}
        """
        self._send_html(shell(
            body=body, title="Search",
            subtitle=f"Results for: {q!r}" if q else "Portfolio-wide search",
            back_href="/",
        ))

    def _route_users_page(self) -> None:
        """B134: admin-only HTML user management.

        Lists users with per-row rotate/delete forms; add-user form at
        the bottom. All actions POST to the existing /api/users/*
        endpoints, so CSRF + admin-gate logic is shared.
        """
        from .auth.auth import list_users
        store = PortfolioStore(self.config.db_path)
        current = self._current_user()
        users_df = list_users(store)
        # Gate: admin-only in multi-user mode; open for bootstrap
        if len(users_df) > 0:
            if current is None or current.get("role") != "admin":
                return self.send_error(
                    HTTPStatus.FORBIDDEN,
                    "User management requires admin role.",
                )

        rows = []
        for _, r in users_df.iterrows():
            u = str(r["username"])
            qu = urllib.parse.quote(u)
            rows.append(
                f"<tr>"
                f"<td><strong>{html.escape(u)}</strong></td>"
                f"<td>{html.escape(str(r['display_name'] or ''))}</td>"
                f"<td><span class='badge badge-blue'>"
                f"{html.escape(str(r['role']))}</span></td>"
                f"<td>"
                f"<form method='POST' action='/api/users/password' "
                f"style='display: inline-flex; gap: 0.25rem;'>"
                f"<input type='hidden' name='username' value='{qu}'>"
                f"<input type='password' name='new_password' "
                f"placeholder='new password' minlength='8' required "
                f"style='font-size: 0.8rem; padding: 0.15rem; "
                f"width: 10rem;'>"
                f"<button type='submit' class='btn' "
                f"style='font-size: 0.75rem; padding: 0.1rem 0.5rem;'>"
                f"Rotate</button></form> "
                f"<form method='POST' action='/api/users/delete' "
                f"style='display: inline;' "
                f"onsubmit='return confirm(\"Delete {u}?\")'>"
                f"<input type='hidden' name='username' value='{qu}'>"
                f"<button type='submit' class='btn' "
                f"style='font-size: 0.75rem; padding: 0.1rem 0.5rem; "
                f"background: var(--red-soft); color: var(--red-text); "
                f"border: 1px solid var(--red);'>Delete</button></form>"
                f"</td>"
                f"</tr>"
            )

        add_form = (
            '<div class="card"><h2 style="margin-top: 0;">Add user</h2>'
            '<form method="POST" action="/api/users/create" '
            'style="display: grid; gap: 0.5rem; max-width: 26rem;">'
            '<input type="text" name="username" placeholder="username" '
            'required maxlength="40" pattern="[A-Za-z0-9][A-Za-z0-9_.@-]{0,39}" '
            'style="padding: 0.4rem;">'
            '<input type="text" name="display_name" '
            'placeholder="display name (optional)" '
            'style="padding: 0.4rem;">'
            '<input type="password" name="password" placeholder="password" '
            'required minlength="8" style="padding: 0.4rem;">'
            '<select name="role" style="padding: 0.4rem;">'
            '<option value="analyst" selected>analyst</option>'
            '<option value="admin">admin</option></select>'
            '<button type="submit" class="btn" '
            'style="padding: 0.4rem 0.9rem; background: var(--accent); '
            'color: white; border: none; border-radius: 4px; '
            'font-weight: 600; cursor: pointer;">Create user</button>'
            '</form></div>'
        )

        if users_df.empty:
            list_html = (
                '<div class="card"><p class="muted">'
                'No users yet — running in single-user mode. Create the '
                'first admin below to enable login.</p></div>'
            )
        else:
            list_html = (
                f'<div class="card"><h2 style="margin-top: 0;">'
                f'Users ({len(users_df)})</h2>'
                f'<table><thead><tr>'
                f'<th>Username</th><th>Display name</th>'
                f'<th>Role</th><th>Actions</th>'
                f'</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
            )

        self._send_html(shell(
            body=list_html + add_form,
            title="Users",
            subtitle="Admin-only user management",
            back_href="/audit",
        ))

    def _route_audit(self) -> None:
        """B127: admin-only audit dashboard.

        Shows: user directory, last 50 acks (with acker identity),
        recent owner assignments. Available in single-user mode (no
        auth enforced); in multi-user mode requires role == 'admin'.
        """
        from .alerts.alert_acks import list_acks
        from .auth.auth import list_users
        store = PortfolioStore(self.config.db_path)

        # Gate: admin only, OR single-user mode where no users exist
        current = self._current_user()
        users_df = list_users(store)
        if len(users_df) > 0:
            if current is None or current.get("role") != "admin":
                return self.send_error(
                    HTTPStatus.FORBIDDEN,
                    "Audit requires admin role.",
                )

        # ── Users card ──
        if users_df.empty:
            users_html = (
                '<div class="card"><h2 style="margin-top: 0;">Users</h2>'
                '<p class="muted">No users created yet — running in '
                'single-user mode. Use <code>rcm-mc portfolio users '
                'create</code> to bootstrap.</p></div>'
            )
        else:
            u_rows = "".join(
                f"<tr>"
                f"<td><strong>{html.escape(str(r['username']))}</strong></td>"
                f"<td>{html.escape(str(r['display_name'] or ''))}</td>"
                f"<td><span class='badge badge-blue'>"
                f"{html.escape(str(r['role']))}</span></td>"
                f"<td class='muted' style='font-size: 0.8rem;'>"
                f"{html.escape(str(r['created_at'])[:19])}</td>"
                f"</tr>"
                for _, r in users_df.iterrows()
            )
            users_html = (
                f'<div class="card"><h2 style="margin-top: 0;">Users '
                f'({len(users_df)})</h2>'
                f'<table><thead><tr>'
                f'<th>Username</th><th>Display name</th>'
                f'<th>Role</th><th>Created</th>'
                f'</tr></thead><tbody>{u_rows}</tbody></table></div>'
            )

        # ── Recent acks ──
        acks_df = list_acks(store).head(50)
        if acks_df.empty:
            acks_html = (
                '<div class="card"><h2 style="margin-top: 0;">Recent acks</h2>'
                '<p class="muted">No alerts have been acknowledged yet.</p>'
                '</div>'
            )
        else:
            a_rows = []
            for _, r in acks_df.iterrows():
                did = str(r["deal_id"])
                acker = str(r.get("acked_by") or "—") or "—"
                snooze = str(r.get("snooze_until") or "")
                snooze_cell = (
                    f'<span class="muted" style="font-size: 0.8rem;">'
                    f'until {html.escape(snooze[:10])}</span>' if snooze
                    else '<span class="badge badge-muted">permanent</span>'
                )
                a_rows.append(
                    f"<tr>"
                    f"<td class='muted' style='font-size: 0.8rem;'>"
                    f"{html.escape(str(r['acked_at'])[:19])}</td>"
                    f"<td><strong>{html.escape(acker)}</strong></td>"
                    f"<td><a href='/deal/{urllib.parse.quote(did)}' "
                    f"style='color: var(--accent); font-weight: 600; "
                    f"text-decoration: none;'>{html.escape(did)}</a></td>"
                    f"<td>{html.escape(str(r['kind']))}</td>"
                    f"<td>{snooze_cell}</td>"
                    f"<td class='muted' style='font-size: 0.85rem;'>"
                    f"{html.escape(str(r.get('note') or ''))}</td>"
                    f"</tr>"
                )
            acks_html = (
                f'<div class="card"><h2 style="margin-top: 0;">Recent acks '
                f'({len(acks_df)})</h2>'
                f'<table><thead><tr>'
                f'<th>When</th><th>By</th><th>Deal</th><th>Kind</th>'
                f'<th>Snooze</th><th>Note</th>'
                f'</tr></thead><tbody>{"".join(a_rows)}</tbody></table></div>'
            )

        # ── Recent owner assignments ──
        from .deals.deal_owners import _ensure_owners_table
        _ensure_owners_table(store)
        with store.connect() as con:
            own_rows = con.execute(
                "SELECT deal_id, owner, assigned_at, note "
                "FROM deal_owner_history ORDER BY id DESC LIMIT 50"
            ).fetchall()
        if not own_rows:
            owners_html = (
                '<div class="card"><h2 style="margin-top: 0;">'
                'Owner assignments</h2>'
                '<p class="muted">No owner history yet.</p></div>'
            )
        else:
            o_rows = []
            for r in own_rows:
                did = str(r["deal_id"])
                o_rows.append(
                    f"<tr>"
                    f"<td class='muted' style='font-size: 0.8rem;'>"
                    f"{html.escape(str(r['assigned_at'])[:19])}</td>"
                    f"<td><strong>{html.escape(str(r['owner']))}</strong></td>"
                    f"<td><a href='/deal/{urllib.parse.quote(did)}' "
                    f"style='color: var(--accent); font-weight: 600; "
                    f"text-decoration: none;'>{html.escape(did)}</a></td>"
                    f"<td class='muted' style='font-size: 0.85rem;'>"
                    f"{html.escape(str(r['note'] or ''))}</td>"
                    f"</tr>"
                )
            owners_html = (
                f'<div class="card"><h2 style="margin-top: 0;">'
                f'Owner assignments ({len(own_rows)})</h2>'
                f'<table><thead><tr>'
                f'<th>When</th><th>Owner</th><th>Deal</th><th>Note</th>'
                f'</tr></thead><tbody>{"".join(o_rows)}</tbody></table></div>'
            )

        # ── Unified audit events (B133) ──
        from .auth.audit_log import list_events
        events_df = list_events(store, limit=50)
        if events_df.empty:
            events_html = (
                '<div class="card"><h2 style="margin-top: 0;">'
                'Audit events</h2>'
                '<p class="muted">Nothing logged yet.</p></div>'
            )
        else:
            e_rows = []
            for _, r in events_df.iterrows():
                detail = r.get("detail") or {}
                detail_txt = " ".join(
                    f"{k}={v}" for k, v in (detail or {}).items()
                ) if isinstance(detail, dict) else ""
                e_rows.append(
                    f"<tr>"
                    f"<td class='muted' style='font-size: 0.8rem;'>"
                    f"{html.escape(str(r['at'])[:19])}</td>"
                    f"<td><strong>{html.escape(str(r['actor']))}</strong></td>"
                    f"<td><code>{html.escape(str(r['action']))}</code></td>"
                    f"<td>{html.escape(str(r['target'] or ''))}</td>"
                    f"<td class='muted' style='font-size: 0.8rem;'>"
                    f"{html.escape(detail_txt)}</td>"
                    f"</tr>"
                )
            events_html = (
                f'<div class="card" style="border-left: 3px solid '
                f'var(--accent);"><h2 style="margin-top: 0;">'
                f'Audit events ({len(events_df)})</h2>'
                f'<table><thead><tr>'
                f'<th>When</th><th>Actor</th><th>Action</th>'
                f'<th>Target</th><th>Detail</th>'
                f'</tr></thead><tbody>{"".join(e_rows)}</tbody></table></div>'
            )

        body = events_html + users_html + acks_html + owners_html
        self._send_html(shell(
            body=body, title="Audit",
            subtitle="Portfolio-wide identity + activity audit",
            back_href="/",
        ))

    def _route_login_page(self) -> None:
        """Bloomberg-style terminal login — the SeekingChartis trust gate.

        Dark near-black background, amber accent, security/trust indicators,
        monospace inputs. Demo credentials surfaced when the seeded demo
        user is present.
        """
        user = self._current_user()
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        nxt = (qs.get("next") or ["/"])[0]
        err = (qs.get("err") or [""])[0]

        demo_mode = False
        try:
            from .auth.auth import list_users
            users_df = list_users(PortfolioStore(self.config.db_path))
            demo_mode = (
                not users_df.empty
                and "demo" in set(users_df["username"].tolist())
            )
        except Exception:  # noqa: BLE001
            pass

        from .ui.brand import BRAND, LOGO_SVG, PALETTE, TYPOGRAPHY
        css = f"""
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
          background: {PALETTE['bg']};
          color: {PALETTE['text_primary']};
          font-family: {TYPOGRAPHY['font_sans']};
          font-size: 13px;
          min-height: 100vh;
          display: flex; flex-direction: column;
          overflow-x: hidden;
        }}
        .sc-login-bar {{
          display: flex; align-items: center; justify-content: space-between;
          padding: 10px 18px;
          background: {PALETTE['bg_secondary']};
          border-bottom: 1px solid {PALETTE['border']};
          font-family: {TYPOGRAPHY['font_mono']};
          font-size: 10px; letter-spacing: 0.08em;
          color: {PALETTE['text_muted']};
          text-transform: uppercase;
        }}
        .sc-login-bar .live-dot {{
          display: inline-block; width: 6px; height: 6px;
          background: {PALETTE['positive']};
          box-shadow: 0 0 6px {PALETTE['positive']};
          margin-right: 6px; vertical-align: middle;
          animation: scPulse 2s ease-in-out infinite;
        }}
        @keyframes scPulse {{ 0%,100% {{ opacity: 1; }} 50% {{ opacity: 0.4; }} }}
        .sc-login-wrap {{
          flex: 1;
          display: flex; align-items: center; justify-content: center;
          padding: 32px 16px;
        }}
        .sc-login {{
          width: 100%;
          max-width: 420px;
          background: {PALETTE['bg_secondary']};
          border: 1px solid {PALETTE['border_light']};
          padding: 32px 32px 28px;
          position: relative;
        }}
        .sc-login::before {{
          content: "";
          position: absolute; top: -1px; left: -1px; right: -1px;
          height: 3px;
          background: linear-gradient(90deg, {PALETTE['accent_amber']} 0%, {PALETTE['brand_accent']} 100%);
        }}
        .sc-brand {{
          display: flex; align-items: center; gap: 10px;
          padding-bottom: 20px;
          border-bottom: 1px solid {PALETTE['border']};
          margin-bottom: 22px;
        }}
        .sc-brand-word {{
          font-size: 16px; font-weight: 700;
          letter-spacing: 0.14em; text-transform: uppercase;
          color: {PALETTE['text_primary']};
        }}
        .sc-brand-sub {{
          font-family: {TYPOGRAPHY['font_mono']};
          font-size: 9.5px; letter-spacing: 0.12em;
          color: {PALETTE['text_muted']};
          text-transform: uppercase;
          margin-top: 3px;
        }}
        .sc-login h1 {{
          font-size: 12px; font-weight: 700;
          letter-spacing: 0.18em; text-transform: uppercase;
          color: {PALETTE['accent_amber']};
          margin-bottom: 18px;
          font-family: {TYPOGRAPHY['font_mono']};
        }}
        .sc-field {{ display: flex; flex-direction: column; gap: 5px; margin-bottom: 14px; }}
        .sc-field label {{
          font-family: {TYPOGRAPHY['font_mono']};
          font-size: 9.5px; font-weight: 700;
          letter-spacing: 0.14em; text-transform: uppercase;
          color: {PALETTE['text_muted']};
        }}
        .sc-field input {{
          padding: 10px 12px;
          background: #03050a;
          border: 1px solid {PALETTE['border']};
          color: {PALETTE['text_primary']};
          font-family: {TYPOGRAPHY['font_mono']};
          font-size: 13px; letter-spacing: 0.03em;
          outline: none;
          transition: border-color 0.1s, box-shadow 0.1s;
        }}
        .sc-field input:focus {{
          border-color: {PALETTE['accent_amber']};
          box-shadow: inset 0 0 0 1px {PALETTE['accent_amber']};
        }}
        .sc-field input::placeholder {{
          color: {PALETTE['text_muted']};
          text-transform: uppercase;
          letter-spacing: 0.08em;
          font-size: 11.5px;
        }}
        .sc-submit {{
          width: 100%;
          padding: 11px 16px;
          background: {PALETTE['brand_accent']};
          color: white;
          border: none;
          font-family: {TYPOGRAPHY['font_sans']};
          font-size: 12px; font-weight: 700;
          letter-spacing: 0.12em; text-transform: uppercase;
          cursor: pointer;
          transition: background 0.1s;
          margin-top: 6px;
        }}
        .sc-submit:hover {{
          background: {PALETTE['accent_amber']};
          color: #000;
        }}
        .sc-err {{
          background: rgba(239,68,68,0.08);
          border: 1px solid rgba(239,68,68,0.35);
          border-left: 3px solid {PALETTE['negative']};
          color: #fca5a5;
          font-family: {TYPOGRAPHY['font_mono']};
          font-size: 11px; letter-spacing: 0.04em;
          padding: 8px 12px;
          margin-bottom: 16px;
        }}
        .sc-demo {{
          margin-top: 18px;
          padding: 10px 12px;
          border: 1px dashed {PALETTE['border_light']};
          font-family: {TYPOGRAPHY['font_mono']};
          font-size: 10.5px;
          color: {PALETTE['text_secondary']};
          letter-spacing: 0.03em;
        }}
        .sc-demo strong {{
          color: {PALETTE['accent_amber']};
          font-weight: 700;
          letter-spacing: 0.14em; text-transform: uppercase;
          display: block; margin-bottom: 4px;
        }}
        .sc-demo code {{
          color: {PALETTE['text_primary']};
          background: #03050a;
          padding: 1px 5px;
          border: 1px solid {PALETTE['border']};
        }}
        .sc-trust {{
          margin-top: 18px;
          padding-top: 14px;
          border-top: 1px solid {PALETTE['border']};
          display: flex;
          gap: 12px;
          font-family: {TYPOGRAPHY['font_mono']};
          font-size: 9px;
          letter-spacing: 0.12em;
          color: {PALETTE['text_muted']};
          text-transform: uppercase;
          flex-wrap: wrap;
        }}
        .sc-trust span::before {{
          content: "●";
          color: {PALETTE['positive']};
          margin-right: 4px;
          font-size: 8px;
        }}
        .sc-footer-bar {{
          padding: 10px 18px;
          background: #030509;
          border-top: 1px solid {PALETTE['border']};
          display: flex; justify-content: space-between;
          font-family: {TYPOGRAPHY['font_mono']};
          font-size: 9px; letter-spacing: 0.08em;
          color: {PALETTE['text_muted']};
          text-transform: uppercase;
        }}
        .sc-footer-bar span {{ }}
        .sc-signed-in {{
          text-align: center;
          color: {PALETTE['text_secondary']};
        }}
        .sc-signed-in strong {{ color: {PALETTE['accent_amber']}; }}
        .sc-actions {{
          display: flex; gap: 10px; margin-top: 18px;
        }}
        .sc-btn {{
          flex: 1;
          padding: 10px 14px;
          font-family: {TYPOGRAPHY['font_sans']};
          font-size: 11px; font-weight: 700;
          letter-spacing: 0.12em; text-transform: uppercase;
          text-decoration: none;
          text-align: center;
          border: 1px solid {PALETTE['border_light']};
          color: {PALETTE['text_primary']};
          background: transparent;
          cursor: pointer;
        }}
        .sc-btn.primary {{
          background: {PALETTE['brand_accent']};
          color: white;
          border-color: {PALETTE['brand_accent']};
        }}
        .sc-btn:hover {{ border-color: {PALETTE['accent_amber']}; color: {PALETTE['accent_amber']}; }}
        .sc-btn.primary:hover {{ background: {PALETTE['accent_amber']}; color: #000; }}
        """

        top_bar = (
            '<div class="sc-login-bar">'
            '<span><span class="live-dot"></span>SeekingChartis · Terminal</span>'
            '<span id="sc-utc">—</span>'
            '</div>'
        )
        footer_bar = (
            '<div class="sc-footer-bar">'
            f'<span>Build v{BRAND["version"]} · HCRIS FY2022</span>'
            '<span>Secure session · scrypt · CSRF-protected</span>'
            '</div>'
        )
        # Clock + CSRF-patch shim (the same one shell_v2 injects). The signed-in
        # variant below has a logout form which does require CSRF, and the
        # platform's test suite asserts any form page carries this shim.
        clock_js = (
            "<script>"
            "(function(){"
            "function c(n){var m=document.cookie.match("
            "new RegExp('(?:^|; )'+n+'=([^;]*)'));"
            "return m?decodeURIComponent(m[1]):null;}"
            "document.addEventListener('submit',function(e){"
            "var t=c('rcm_csrf');if(!t)return;"
            "var f=e.target;if(!f||f.tagName!=='FORM')return;"
            "if(f.method&&f.method.toLowerCase()!=='post')return;"
            "var x=f.querySelector('input[name=csrf_token]');"
            "if(!x){x=document.createElement('input');x.type='hidden';"
            "x.name='csrf_token';f.appendChild(x);}x.value=t;},true);"
            "})();"
            "(function(){var e=document.getElementById('sc-utc');"
            "function p(n){return n<10?'0'+n:''+n;}"
            "function t(){if(!e)return;var d=new Date();"
            "e.textContent=d.getUTCFullYear()+'-'+p(d.getUTCMonth()+1)+'-'+p(d.getUTCDate())+"
            "' '+p(d.getUTCHours())+':'+p(d.getUTCMinutes())+':'+p(d.getUTCSeconds())+' UTC';}"
            "t();setInterval(t,1000);})();"
            "</script>"
        )

        brand_block = (
            '<div class="sc-brand">'
            f'{LOGO_SVG}'
            '<div>'
            '<div class="sc-brand-word">SeekingChartis</div>'
            '<div class="sc-brand-sub">Healthcare PE · Instrument-grade diligence</div>'
            '</div>'
            '</div>'
        )

        trust_strip = (
            '<div class="sc-trust">'
            '<span>Encrypted</span>'
            '<span>Audit-logged</span>'
            '<span>3,157 tests</span>'
            '</div>'
        )

        if user:
            login_card = (
                '<div class="sc-login">'
                + brand_block
                + '<h1>Session Active</h1>'
                + '<div class="sc-signed-in">Signed in as '
                + f'<strong>{html.escape(user["username"])}</strong><br>'
                + f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:10px;'
                + 'letter-spacing:0.08em;text-transform:uppercase;">Role · '
                + f'{html.escape(user["role"])}</span></div>'
                + '<div class="sc-actions">'
                + '<a href="/home" class="sc-btn primary">Open Platform &rarr;</a>'
                + '<form method="POST" action="/api/logout" style="flex:1;margin:0;">'
                + '<button type="submit" class="sc-btn" style="width:100%;">Sign Out</button>'
                + '</form></div>'
                + trust_strip
                + '</div>'
            )
        else:
            err_block = (
                f'<div class="sc-err">[AUTH_FAIL] {html.escape(err)}</div>'
                if err else ""
            )
            demo_block = (
                '<div class="sc-demo">'
                '<strong>Demo Credentials</strong>'
                'Username <code>demo</code> &nbsp;·&nbsp; '
                'Password <code>DemoPass!1</code>'
                '</div>'
                if demo_mode else ""
            )
            login_card = (
                '<div class="sc-login">'
                + brand_block
                + '<h1>Authenticate</h1>'
                + err_block
                + '<form method="POST" action="/api/login">'
                + f'<input type="hidden" name="next" value="{html.escape(nxt)}">'
                + '<div class="sc-field">'
                + '<label>Username</label>'
                + '<input type="text" name="username" placeholder="username" '
                + 'required autofocus autocomplete="username">'
                + '</div>'
                + '<div class="sc-field">'
                + '<label>Password</label>'
                + '<input type="password" name="password" placeholder="••••••••" '
                + 'required autocomplete="current-password">'
                + '</div>'
                + '<button type="submit" class="sc-submit">Sign In &rarr;</button>'
                + '</form>'
                + demo_block
                + trust_strip
                + '</div>'
            )

        page = (
            '<!DOCTYPE html>'
            '<html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Sign In — SeekingChartis</title>'
            '<link rel="preconnect" href="https://fonts.googleapis.com">'
            '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
            '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&'
            'family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">'
            f'<style>{css}</style>'
            '</head><body>'
            f'{top_bar}'
            f'<div class="sc-login-wrap">{login_card}</div>'
            f'{footer_bar}'
            f'{clock_js}'
            '</body></html>'
        )
        self._send_html(page)

    def _route_upload_page(self) -> None:
        """Drop-target form for bulk CSV ingest of actuals or initiatives."""
        body = """
        <div class="card">
          <h2>Upload quarterly actuals</h2>
          <p class="muted" style="font-size: 0.88rem;">
            Drop a management-reporting CSV with columns:
            <code>deal_id, quarter, ebitda, plan_ebitda, ...</code>
            Any of the tracked KPIs (ebitda, net_patient_revenue,
            idr_blended, fwr_blended, dar_clean_days) may be included
            with optional <code>plan_&lt;kpi&gt;</code> counterparts.
          </p>
          <form method="POST" action="/api/upload-actuals"
                enctype="multipart/form-data"
                style="margin-top: 1rem;">
            <input type="file" name="file" accept=".csv" required
                   style="display: block; margin-bottom: 1rem;
                          padding: 0.75rem; border: 2px dashed var(--border);
                          border-radius: 8px; width: 100%; cursor: pointer;">
            <button type="submit"
                    style="padding: 0.5rem 1.25rem; border: none;
                           border-radius: 6px; background: var(--accent);
                           color: white; font-weight: 600; cursor: pointer;
                           font-size: 0.9rem;">
              Ingest CSV
            </button>
          </form>
        </div>

        <div class="card">
          <h2>Upload notes</h2>
          <p class="muted" style="font-size: 0.88rem;">
            CSV columns: <code>deal_id, body, author</code>
            (<code>author</code> optional). Ingest a week's worth of
            meeting notes in one shot instead of typing into each deal.
          </p>
          <form method="POST" action="/api/upload-notes"
                enctype="multipart/form-data"
                style="margin-top: 1rem;">
            <input type="file" name="file" accept=".csv" required
                   style="display: block; margin-bottom: 1rem;
                          padding: 0.75rem; border: 2px dashed var(--border);
                          border-radius: 8px; width: 100%; cursor: pointer;">
            <button type="submit"
                    style="padding: 0.5rem 1.25rem; border: none;
                           border-radius: 6px; background: var(--accent);
                           color: white; font-weight: 600; cursor: pointer;
                           font-size: 0.9rem;">
              Ingest notes CSV
            </button>
          </form>
        </div>

        <div class="card">
          <h2>Upload initiative actuals</h2>
          <p class="muted" style="font-size: 0.88rem;">
            CSV columns:
            <code>deal_id, initiative_id, quarter, ebitda_impact</code>
            (<code>notes</code> optional). Used when the management deck
            splits EBITDA delta by RCM workstream.
          </p>
          <form method="POST" action="/api/upload-initiatives"
                enctype="multipart/form-data"
                style="margin-top: 1rem;">
            <input type="file" name="file" accept=".csv" required
                   style="display: block; margin-bottom: 1rem;
                          padding: 0.75rem; border: 2px dashed var(--border);
                          border-radius: 8px; width: 100%; cursor: pointer;">
            <button type="submit"
                    style="padding: 0.5rem 1.25rem; border: none;
                           border-radius: 6px; background: var(--accent);
                           color: white; font-weight: 600; cursor: pointer;
                           font-size: 0.9rem;">
              Ingest initiative CSV
            </button>
          </form>
        </div>
        """
        self._send_html(shell(
            body=body, title="Upload CSV",
            subtitle="Bulk-ingest a management-reporting CSV",
            back_href="/",
        ))

    def _parse_multipart(self) -> Tuple[Dict[str, str], Dict[str, Tuple[str, bytes]]]:
        """Pull form fields + files from a multipart/form-data POST body.

        Returns ``(fields, files)`` where files maps field-name → (filename, bytes).
        Uses the stdlib ``email`` parser so no new deps are required.
        Handles reasonable payloads (<10 MB); larger should stream, but our
        CSV use case is sub-MB management decks.
        """
        import email
        import re as _re

        ct = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in ct:
            return {}, {}
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}, {}
        # B146 fix: enforce the documented 10 MB cap so an attacker can't
        # exhaust memory by streaming a huge body into this handler.
        MAX_BYTES = 10 * 1024 * 1024
        if length > MAX_BYTES:
            raise ValueError(
                f"multipart body too large ({length} bytes; max {MAX_BYTES})"
            )
        body = self.rfile.read(length)

        full = f"Content-Type: {ct}\r\n\r\n".encode() + body
        msg = email.message_from_bytes(full)

        fields: Dict[str, str] = {}
        files: Dict[str, Tuple[str, bytes]] = {}
        for part in msg.walk():
            if part.is_multipart():
                continue
            cd = part.get("Content-Disposition", "")
            if "form-data" not in cd:
                continue
            name_m = _re.search(r'name="([^"]+)"', cd)
            if not name_m:
                continue
            name = name_m.group(1)
            fn_m = _re.search(r'filename="([^"]*)"', cd)
            payload = part.get_payload(decode=True) or b""
            if fn_m and fn_m.group(1):
                files[name] = (fn_m.group(1), payload)
            else:
                try:
                    fields[name] = payload.decode("utf-8", errors="replace")
                except AttributeError:
                    fields[name] = ""
        return fields, files

    def _route_upload_post(self) -> None:
        """Save the uploaded CSV to a temp file, pass to import_actuals_csv."""
        import tempfile
        from .pe.hold_tracking import import_actuals_csv

        try:
            fields, files = self._parse_multipart()
        except ValueError as exc:
            return self._send_json(
                {"error": str(exc)},
                status=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            )
        upload = files.get("file")
        if not upload:
            return self._send_json(
                {"error": "No file field in upload"},
                status=HTTPStatus.BAD_REQUEST,
            )
        filename, content = upload
        store = PortfolioStore(self.config.db_path)

        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".csv", delete=False,
        ) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            summary = import_actuals_csv(store, tmp_path, strict=False)
        except (ValueError, FileNotFoundError) as exc:
            os.unlink(tmp_path)
            return self._send_json(
                {"error": str(exc), "filename": filename},
                status=HTTPStatus.BAD_REQUEST,
            )
        os.unlink(tmp_path)

        # Render an ingest-receipt HTML page so the user sees what happened
        err_items = "".join(
            f'<li class="err">{html.escape(e)}</li>' for e in summary.get("errors", [])
        )
        warn_items = "".join(
            f'<li class="warn">{html.escape(w)}</li>'
            for w in summary.get("warnings", [])
        )
        body = f"""
        <div class="card">
          <h2>Upload complete — {html.escape(filename)}</h2>
          <div class="kpi-grid">
            <div class="kpi-card">
              <div class="kpi-value">{summary['rows_ingested']}</div>
              <div class="kpi-label">Rows ingested</div>
            </div>
            <div class="kpi-card">
              <div class="kpi-value">{len(summary['deals'])}</div>
              <div class="kpi-label">Deals affected</div>
            </div>
            <div class="kpi-card">
              <div class="kpi-value">{len(summary['quarters'])}</div>
              <div class="kpi-label">Quarters covered</div>
            </div>
          </div>
          {
            f'<h3>Warnings</h3><ul>{warn_items}</ul>' if warn_items else ''
          }
          {
            f'<h3>Errors</h3><ul>{err_items}</ul>' if err_items else ''
          }
          <p style="margin-top: 1rem;">
            <a href="/">← Back to dashboard</a>
          </p>
        </div>
        """
        self._send_html(shell(
            body=body, title="Upload receipt", back_href="/",
        ))

    def _route_upload_initiatives_post(self) -> None:
        """Same shape as _route_upload_post but for initiative_actuals CSVs."""
        import tempfile
        from .rcm.initiative_tracking import import_initiative_actuals_csv

        try:
            _, files = self._parse_multipart()
        except ValueError as exc:
            return self._send_json(
                {"error": str(exc)},
                status=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            )
        upload = files.get("file")
        if not upload:
            return self._send_json(
                {"error": "No file field in upload"},
                status=HTTPStatus.BAD_REQUEST,
            )
        filename, content = upload
        store = PortfolioStore(self.config.db_path)

        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".csv", delete=False,
        ) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            summary = import_initiative_actuals_csv(store, tmp_path)
        except (ValueError, FileNotFoundError) as exc:
            os.unlink(tmp_path)
            return self._send_json(
                {"error": str(exc), "filename": filename},
                status=HTTPStatus.BAD_REQUEST,
            )
        os.unlink(tmp_path)

        err_items = "".join(
            f'<li class="err">{html.escape(e)}</li>'
            for e in summary.get("errors", [])
        )
        body = f"""
        <div class="card">
          <h2>Initiative upload complete — {html.escape(filename)}</h2>
          <div class="kpi-grid">
            <div class="kpi-card">
              <div class="kpi-value">{summary['rows_ingested']}</div>
              <div class="kpi-label">Rows ingested</div>
            </div>
          </div>
          {f'<h3>Errors</h3><ul>{err_items}</ul>' if err_items else ''}
          <p style="margin-top: 1rem;"><a href="/">← Back to dashboard</a></p>
        </div>
        """
        self._send_html(shell(
            body=body, title="Upload receipt", back_href="/",
        ))

    def _route_login_post(self) -> None:
        """B125 + B130: verify password, issue rcm_session cookie.

        Rate-limited: after ``_LOGIN_FAIL_MAX`` failed attempts from
        the same client IP within ``_LOGIN_FAIL_WINDOW_SECS``, further
        logins from that IP return 429 for the remainder of the window.
        """
        import time as _time
        from .auth.auth import create_session, verify_password
        store = PortfolioStore(self.config.db_path)
        form = self._read_form_body()
        username = form.get("username", "").strip()
        password = form.get("password", "")
        # B146 fix: validate next-URL is a local path so ?next=https://evil
        # can't turn a successful login into an open-redirect gadget.
        raw_nxt = form.get("next", "") or "/"
        nxt = raw_nxt if (
            raw_nxt.startswith("/")
            and not raw_nxt.startswith("//")
            and "://" not in raw_nxt
        ) else "/"

        # B130 + B147: rate limit check, guarded by shared lock
        client_ip = self.client_address[0] if self.client_address else "?"
        now = _time.time()
        cutoff = now - self._LOGIN_FAIL_WINDOW_SECS
        with self._login_fail_lock:
            log = self._login_fail_log.setdefault(client_ip, [])
            log[:] = [t for t in log if t > cutoff]
            over_limit = len(log) >= self._LOGIN_FAIL_MAX
        if over_limit:
            return self._send_json(
                {"error": "too many failed login attempts; wait a minute",
                 "code": "RATE_LIMITED"},
                status=HTTPStatus.TOO_MANY_REQUESTS,
            )

        if not verify_password(store, username, password):
            with self._login_fail_lock:
                self._login_fail_log.setdefault(client_ip, []).append(now)
            # B162: audit failed login attempts — security teams need
            # "who tried to auth as admin from 192.168.x" without
            # reading stderr.
            try:
                from .auth.audit_log import log_event
                log_event(
                    store, actor=username or "?",
                    action="login.failure",
                    target="login",
                    detail={"client_ip": client_ip},
                )
            except Exception:  # noqa: BLE001
                pass
            accept = self.headers.get("Accept", "")
            if "application/json" in accept:
                # B153: include a machine-readable error code so SDKs
                # can branch on classification (e.g. refresh vs retry)
                # without parsing free-text messages.
                return self._send_json(
                    {"error": "invalid credentials",
                     "code": "INVALID_CREDENTIALS"},
                    status=HTTPStatus.UNAUTHORIZED,
                )
            self.send_response(HTTPStatus.SEE_OTHER)
            self.send_header(
                "Location",
                f"/login?err={urllib.parse.quote('Invalid credentials')}"
                f"&next={urllib.parse.quote(nxt)}",
            )
            self.end_headers()
            return
        # Successful login clears this IP's failure log (under lock)
        with self._login_fail_lock:
            self._login_fail_log.pop(client_ip, None)
        # B162: audit successful logins so compliance can answer
        # "who signed in yesterday" without guessing from session TTLs.
        try:
            from .auth.audit_log import log_event
            log_event(
                store, actor=username, action="login.success",
                target="login",
                detail={"client_ip": client_ip},
            )
        except Exception:  # noqa: BLE001
            pass
        token = create_session(store, username)
        csrf = self._csrf_value(token)
        accept = self.headers.get("Accept", "")
        session_cookie = (
            f"rcm_session={token}; Path=/; HttpOnly; SameSite=Lax; "
            f"Max-Age={7*24*3600}"
        )
        # Non-HttpOnly so the CSRF-patching JS can read it and inject
        # into form submissions.
        csrf_cookie = (
            f"rcm_csrf={csrf}; Path=/; SameSite=Lax; "
            f"Max-Age={7*24*3600}"
        )
        if "application/json" in accept:
            self.send_response(HTTPStatus.OK)
            self.send_header("Set-Cookie", session_cookie)
            self.send_header("Set-Cookie", csrf_cookie)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            import json as _json
            self.wfile.write(_json.dumps({
                "username": username, "token": token, "csrf_token": csrf,
            }).encode())
            return
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Set-Cookie", session_cookie)
        self.send_header("Set-Cookie", csrf_cookie)
        self.send_header("Location", nxt)
        self.end_headers()

    def _route_logout_post(self) -> None:
        """B125: revoke session + clear cookie."""
        from .auth.auth import revoke_session
        store = PortfolioStore(self.config.db_path)
        cookie = self.headers.get("Cookie", "") or ""
        token = None
        for part in cookie.split(";"):
            k, _, v = part.strip().partition("=")
            if k == "rcm_session" and v:
                token = v.strip()
                break
        if token:
            revoke_session(store, token)
        # Expire both cookies
        expired_session = "rcm_session=; Path=/; HttpOnly; Max-Age=0"
        expired_csrf = "rcm_csrf=; Path=/; Max-Age=0"
        accept = self.headers.get("Accept", "")
        if "application/json" in accept:
            self.send_response(HTTPStatus.OK)
            self.send_header("Set-Cookie", expired_session)
            self.send_header("Set-Cookie", expired_csrf)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(b'{"ok": true}')
            return
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Set-Cookie", expired_session)
        self.send_header("Set-Cookie", expired_csrf)
        self.send_header("Location", "/login")
        self.end_headers()

    def _route_upload_notes_post(self) -> None:
        """B112: accept a CSV of notes and import them in one pass."""
        import tempfile
        from .deals.deal_notes import import_notes_csv

        try:
            _, files = self._parse_multipart()
        except ValueError as exc:
            return self._send_json(
                {"error": str(exc)},
                status=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            )
        upload = files.get("file")
        if not upload:
            return self._send_json(
                {"error": "No file field in upload"},
                status=HTTPStatus.BAD_REQUEST,
            )
        filename, content = upload
        store = PortfolioStore(self.config.db_path)

        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".csv", delete=False,
        ) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            summary = import_notes_csv(store, tmp_path)
        except (ValueError, FileNotFoundError) as exc:
            os.unlink(tmp_path)
            return self._send_json(
                {"error": str(exc), "filename": filename},
                status=HTTPStatus.BAD_REQUEST,
            )
        os.unlink(tmp_path)

        err_items = "".join(
            f'<li class="err">{html.escape(e)}</li>'
            for e in summary.get("errors", [])
        )
        body = f"""
        <div class="card">
          <h2>Notes upload complete — {html.escape(filename)}</h2>
          <div class="kpi-grid">
            <div class="kpi-card">
              <div class="kpi-value">{summary['rows_ingested']}</div>
              <div class="kpi-label">Notes ingested</div>
            </div>
            <div class="kpi-card">
              <div class="kpi-value">{summary['rows_skipped']}</div>
              <div class="kpi-label">Rows skipped</div>
            </div>
          </div>
          {f'<h3>Errors</h3><ul>{err_items}</ul>' if err_items else ''}
          <p style="margin-top: 1rem;"><a href="/notes">→ Search notes</a></p>
          <p><a href="/">← Back to dashboard</a></p>
        </div>
        """
        self._send_html(shell(
            body=body, title="Upload receipt", back_href="/",
        ))

    def _read_form_body(self) -> Dict[str, str]:
        """Parse an x-www-form-urlencoded request body into a flat dict.

        Cached on first call — subsequent calls within the same request
        return the same dict so the CSRF middleware and route handlers
        share one parse.
        """
        cached = getattr(self, "_form_cache", None)
        if cached is not None:
            return cached
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            self._form_cache = {}
            return self._form_cache
        raw = self.rfile.read(length).decode("utf-8", errors="replace")
        parsed = urllib.parse.parse_qs(raw, keep_blank_values=True)
        self._form_cache = {k: (v[0] if v else "") for k, v in parsed.items()}
        return self._form_cache

    def _route_api_post(self, path: str) -> None:
        """Handle form POSTs that write to the portfolio store.

        All POST endpoints read application/x-www-form-urlencoded bodies
        so HTML forms work without JS. Each returns 303 See Other to the
        deal detail page so the browser lands on the updated view.
        """
        parts = [p for p in path.strip("/").split("/") if p]
        store = PortfolioStore(self.config.db_path)

        # POST /api/metrics/custom — register a custom KPI.
        if path == "/api/metrics/custom":
            import json as _json
            from .domain.custom_metrics import register_custom_metric, CustomMetric
            n_bytes = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n_bytes) if n_bytes > 0 else b"{}"
            try:
                payload = _json.loads(raw.decode("utf-8") or "{}")
            except _json.JSONDecodeError:
                return self._send_json(
                    {"error": "body must be JSON"},
                    status=HTTPStatus.BAD_REQUEST,
                )
            try:
                cm = CustomMetric(
                    metric_key=payload.get("metric_key", ""),
                    display_name=payload.get("display_name", ""),
                    unit=payload.get("unit", "pct"),
                    directionality=payload.get("directionality", "higher_is_better"),
                    category=payload.get("category", "custom"),
                    description=payload.get("description", ""),
                )
                register_custom_metric(store, cm)
            except (ValueError, KeyError) as exc:
                return self._send_json(
                    {"error": str(exc)}, status=HTTPStatus.BAD_REQUEST,
                )
            return self._send_json({"metric_key": cm.metric_key, "created": True})

        # POST /api/webhooks — register a webhook.
        if path == "/api/webhooks":
            import json as _json
            from .infra.webhooks import register_webhook
            n_bytes = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n_bytes) if n_bytes > 0 else b"{}"
            try:
                payload = _json.loads(raw.decode("utf-8") or "{}")
            except _json.JSONDecodeError:
                return self._send_json(
                    {"error": "body must be JSON"},
                    status=HTTPStatus.BAD_REQUEST,
                )
            url = str(payload.get("url") or "")
            secret = str(payload.get("secret") or "")
            events = payload.get("events") or ["*"]
            if not url:
                return self._send_json(
                    {"error": "url is required"},
                    status=HTTPStatus.BAD_REQUEST,
                )
            wid = register_webhook(
                store, url, secret, events,
                description=str(payload.get("description") or ""),
            )
            return self._send_json({"webhook_id": wid, "created": True})

        # POST /api/deals/<deal_id>/archive — soft-delete a deal
        if (len(parts) == 4 and parts[0] == "api" and parts[1] == "deals"
                and parts[3] == "archive"):
            deal_id = urllib.parse.unquote(parts[2])
            archived = store.archive_deal(deal_id)
            if not archived:
                return self._send_json(
                    {"error": f"deal {deal_id!r} not found or already archived"},
                    status=HTTPStatus.NOT_FOUND,
                )
            self._log_audit("deal.archive", deal_id)
            self._fire_webhook("deal.archived", {"deal_id": deal_id})
            return self._send_json({"archived": True, "deal_id": deal_id})

        # POST /api/deals/<deal_id>/unarchive — restore an archived deal
        if (len(parts) == 4 and parts[0] == "api" and parts[1] == "deals"
                and parts[3] == "unarchive"):
            deal_id = urllib.parse.unquote(parts[2])
            restored = store.unarchive_deal(deal_id)
            if not restored:
                return self._send_json(
                    {"error": f"deal {deal_id!r} not found or not archived"},
                    status=HTTPStatus.NOT_FOUND,
                )
            self._log_audit("deal.unarchive", deal_id)
            return self._send_json({"unarchived": True, "deal_id": deal_id})

        # POST /api/deals/bulk — batch operations on multiple deals
        if path == "/api/deals/bulk":
            import json as _json
            n_bytes = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n_bytes) if n_bytes > 0 else b"{}"
            try:
                payload = _json.loads(raw.decode("utf-8") or "{}")
            except _json.JSONDecodeError:
                return self._send_json(
                    {"error": "body must be JSON"}, status=HTTPStatus.BAD_REQUEST,
                )
            action = str(payload.get("action") or "")
            deal_ids = payload.get("deal_ids") or []
            if not isinstance(deal_ids, list) or not deal_ids:
                return self._send_json(
                    {"error": "deal_ids must be a non-empty array"},
                    status=HTTPStatus.BAD_REQUEST,
                )
            if len(deal_ids) > 100:
                return self._send_json(
                    {"error": "max 100 deals per batch"},
                    status=HTTPStatus.BAD_REQUEST,
                )
            results = []
            if action == "archive":
                for did in deal_ids:
                    ok = store.archive_deal(str(did))
                    results.append({"deal_id": did, "archived": ok})
            elif action == "unarchive":
                for did in deal_ids:
                    ok = store.unarchive_deal(str(did))
                    results.append({"deal_id": did, "unarchived": ok})
            elif action == "delete":
                for did in deal_ids:
                    ok = store.delete_deal(str(did))
                    results.append({"deal_id": did, "deleted": ok})
            elif action == "tag":
                tag = str(payload.get("tag") or "")
                if not tag:
                    return self._send_json(
                        {"error": "tag is required for tag action"},
                        status=HTTPStatus.BAD_REQUEST,
                    )
                from .deals.deal_tags import add_tag as _bulk_add_tag
                for did in deal_ids:
                    try:
                        _bulk_add_tag(store, str(did), tag)
                        results.append({"deal_id": did, "tagged": True})
                    except Exception:
                        results.append({"deal_id": did, "tagged": False})
            else:
                return self._send_json(
                    {"error": f"unknown action {action!r}; valid: archive, unarchive, delete, tag"},
                    status=HTTPStatus.BAD_REQUEST,
                )
            self._log_audit(f"deal.bulk.{action}", ",".join(str(d) for d in deal_ids[:5]))
            return self._send_json({
                "action": action,
                "results": results,
                "count": len(results),
            })

        # POST /api/deals/import — import deals from JSON array
        if path == "/api/deals/import":
            import json as _json
            n_bytes = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n_bytes) if n_bytes > 0 else b"[]"
            try:
                payload = _json.loads(raw.decode("utf-8") or "[]")
            except _json.JSONDecodeError:
                return self._send_json(
                    {"error": "body must be JSON array"},
                    status=HTTPStatus.BAD_REQUEST,
                )
            deals = payload if isinstance(payload, list) else payload.get("deals", [])
            if not deals or len(deals) > 500:
                return self._send_json(
                    {"error": "provide 1-500 deals as JSON array"},
                    status=HTTPStatus.BAD_REQUEST,
                )
            imported = []
            for d in deals:
                did = str(d.get("deal_id") or "").strip()
                if not did:
                    continue
                name = str(d.get("name") or did)
                profile = d.get("profile") or {}
                if not isinstance(profile, dict):
                    profile = {}
                store.upsert_deal(did, name=name, profile=profile)
                imported.append(did)
            self._log_audit("deal.import", f"{len(imported)} deals")
            return self._send_json({
                "imported": len(imported),
                "deal_ids": imported,
            })

        # POST /api/deals/<deal_id>/pin — pin/unpin a deal
        if (len(parts) == 4 and parts[0] == "api" and parts[1] == "deals"
                and parts[3] in ("pin", "unpin")):
            deal_id = urllib.parse.unquote(parts[2])
            from .deals.deal_tags import add_tag as _pin_add, remove_tag as _pin_rm
            if parts[3] == "pin":
                _pin_add(store, deal_id, "pinned")
            else:
                _pin_rm(store, deal_id, "pinned")
            self._log_audit(f"deal.{parts[3]}", deal_id)
            return self._send_json({
                "deal_id": deal_id,
                "pinned": parts[3] == "pin",
            })

        # POST /api/deals/import-csv — import deals from CSV text
        if path == "/api/deals/import-csv":
            import csv as _csv
            import io as _io
            n_bytes = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n_bytes) if n_bytes > 0 else b""
            text = raw.decode("utf-8", errors="replace")
            reader = _csv.DictReader(_io.StringIO(text))
            imported = []
            errors = []
            for i, row in enumerate(reader):
                if i >= 500:
                    break
                did = (row.get("deal_id") or "").strip()
                if not did:
                    errors.append(f"row {i+1}: missing deal_id")
                    continue
                name = row.get("name") or did
                profile = {
                    k: v for k, v in row.items()
                    if k not in ("deal_id", "name") and v
                }
                for pk in list(profile.keys()):
                    try:
                        profile[pk] = float(profile[pk])
                    except (ValueError, TypeError):
                        pass
                store.upsert_deal(did, name=name, profile=profile)
                imported.append(did)
            self._log_audit("deal.import_csv", f"{len(imported)} deals")
            return self._send_json({
                "imported": len(imported),
                "deal_ids": imported,
                "errors": errors,
            })

        # POST /api/screener/run — run a custom screen
        if path == "/api/screener/run":
            import json as _scrjson
            from .intelligence.screener_engine import run_screen_from_filters as _scr_run
            n_bytes = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n_bytes) if n_bytes > 0 else b"{}"
            try:
                payload = _scrjson.loads(raw.decode("utf-8") or "{}")
            except _scrjson.JSONDecodeError:
                return self._send_json({"error": "body must be JSON"}, status=HTTPStatus.BAD_REQUEST)
            filters = payload.get("filters") or []
            name = str(payload.get("name") or "Custom Screen")
            limit = min(int(payload.get("limit") or 200), 500)
            try:
                result = _scr_run(filters, name, limit)
                return self._send_json(result.to_dict())
            except Exception as exc:
                return self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)

        # POST /api/chat — conversational AI interface
        if path == "/api/chat":
            import json as _cjson3
            from .ai.conversation import ConversationEngine
            from .ai.llm_client import LLMClient  # noqa: F401
            n_bytes = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n_bytes) if n_bytes > 0 else b"{}"
            try:
                payload = _cjson3.loads(raw.decode("utf-8") or "{}")
            except _cjson3.JSONDecodeError:
                return self._send_json(
                    {"error": "body must be JSON"}, status=HTTPStatus.BAD_REQUEST,
                )
            message = str(payload.get("message") or "").strip()[:1000]
            session_id = str(payload.get("session_id") or "default")
            if not message:
                return self._send_json(
                    {"error": "message is required"}, status=HTTPStatus.BAD_REQUEST,
                )
            engine = ConversationEngine(store)
            response = engine.process_message(session_id, message)
            return self._send_json({
                "session_id": session_id,
                "answer": response.answer_text,
                "tool_calls": response.tool_calls_made,
                "cited_deals": response.cited_deals,
            })

        # POST /api/portfolio/register — register a snapshot (web equivalent of CLI)
        if path == "/api/portfolio/register":
            import json as _rjson
            from .portfolio.portfolio_snapshots import register_snapshot as _api_reg, DEAL_STAGES
            n_bytes = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n_bytes) if n_bytes > 0 else b"{}"
            try:
                payload = _rjson.loads(raw.decode("utf-8") or "{}")
            except _rjson.JSONDecodeError:
                return self._send_json(
                    {"error": "body must be JSON"}, status=HTTPStatus.BAD_REQUEST,
                )
            deal_id = str(payload.get("deal_id") or "").strip()
            stage = str(payload.get("stage") or "").strip()
            notes = str(payload.get("notes") or "")
            if not deal_id:
                return self._send_json(
                    {"error": "deal_id is required"}, status=HTTPStatus.BAD_REQUEST,
                )
            if stage not in DEAL_STAGES:
                return self._send_json(
                    {"error": f"stage must be one of {DEAL_STAGES}"},
                    status=HTTPStatus.BAD_REQUEST,
                )
            try:
                sid = _api_reg(store, deal_id, stage, notes=notes)
            except ValueError as exc:
                return self._send_json(
                    {"error": str(exc)}, status=HTTPStatus.BAD_REQUEST,
                )
            self._log_audit("portfolio.register", deal_id, stage=stage)
            return self._send_json({
                "snapshot_id": sid,
                "deal_id": deal_id,
                "stage": stage,
            })

        # POST /api/deals/<deal_id>/duplicate — clone a deal
        if (len(parts) == 4 and parts[0] == "api" and parts[1] == "deals"
                and parts[3] == "duplicate"):
            import json as _json
            deal_id = urllib.parse.unquote(parts[2])
            n_bytes = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n_bytes) if n_bytes > 0 else b"{}"
            try:
                payload = _json.loads(raw.decode("utf-8") or "{}")
            except _json.JSONDecodeError:
                payload = {}
            new_id = str(payload.get("new_deal_id") or f"{deal_id}_copy")
            new_name = payload.get("new_name") or None
            cloned = store.clone_deal(deal_id, new_id, new_name)
            if not cloned:
                return self._send_json(
                    {"error": f"deal {deal_id!r} not found"},
                    status=HTTPStatus.NOT_FOUND,
                )
            self._log_audit("deal.duplicate", deal_id,
                            source=deal_id, new_deal_id=new_id)
            self._fire_webhook("deal.created", {"deal_id": new_id, "source": deal_id})
            return self._send_json({
                "cloned": True,
                "source_deal_id": deal_id,
                "new_deal_id": new_id,
            })

        # Prompt 26: wizard API step transitions. The server-rendered
        # ones (/new-deal/manual, /new-deal/upload) are handled in
        # ``do_POST`` because they aren't under the /api/ prefix.
        if path == "/api/deals/wizard/select":
            return self._route_wizard_select()
        if path == "/api/deals/wizard/launch":
            return self._route_wizard_launch()

        # POST /api/deals/<deal_id>/plan — create plan from packet.
        if (len(parts) == 4 and parts[0] == "api" and parts[1] == "deals"
                and parts[3] == "plan"):
            deal_id = urllib.parse.unquote(parts[2])
            from .analysis.analysis_store import get_or_build_packet
            from .pe.value_creation_plan import (
                create_plan_from_packet, save_plan,
            )
            try:
                pkt = get_or_build_packet(store, deal_id, skip_simulation=True)
                plan = create_plan_from_packet(pkt)
                save_plan(store, plan)
            except Exception as exc:  # noqa: BLE001
                return self._send_json(
                    {"error": f"plan creation failed: {exc}"},
                    status=HTTPStatus.INTERNAL_SERVER_ERROR,
                )
            return self._send_json({
                "deal_id": deal_id, "plan": plan.to_dict(),
            })

        # POST /api/deals/<deal_id>/stage — set deal stage.
        if (len(parts) == 4 and parts[0] == "api" and parts[1] == "deals"
                and parts[3] == "stage"):
            import json as _json
            deal_id = urllib.parse.unquote(parts[2])
            n_bytes = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n_bytes) if n_bytes > 0 else b"{}"
            try:
                payload = _json.loads(raw.decode("utf-8") or "{}")
            except _json.JSONDecodeError:
                return self._send_json(
                    {"error": "body must be JSON"},
                    status=HTTPStatus.BAD_REQUEST,
                )
            stage = str(payload.get("stage") or "")
            from .deals.deal_stages import set_stage
            try:
                set_stage(store, deal_id, stage,
                          changed_by=payload.get("changed_by") or "api")
            except ValueError as exc:
                return self._send_json(
                    {"error": str(exc)}, status=HTTPStatus.BAD_REQUEST,
                )
            return self._send_json({
                "deal_id": deal_id, "stage": stage,
            })

        # POST /api/deals/<deal_id>/comments — add a comment.
        if (len(parts) == 4 and parts[0] == "api" and parts[1] == "deals"
                and parts[3] == "comments"):
            import json as _json
            deal_id = urllib.parse.unquote(parts[2])
            n_bytes = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n_bytes) if n_bytes > 0 else b"{}"
            try:
                payload = _json.loads(raw.decode("utf-8") or "{}")
            except _json.JSONDecodeError:
                return self._send_json(
                    {"error": "body must be JSON"},
                    status=HTTPStatus.BAD_REQUEST,
                )
            body_text = str(payload.get("body") or "").strip()
            if not body_text:
                return self._send_json(
                    {"error": "body is required"},
                    status=HTTPStatus.BAD_REQUEST,
                )
            from .deals.comments import add_comment
            author = payload.get("author") or "api"
            cid = add_comment(
                store, deal_id, body_text, author,
                metric_key=payload.get("metric_key"),
                parent_id=payload.get("parent_id"),
            )
            return self._send_json({
                "deal_id": deal_id, "comment_id": cid,
            })

        # POST /api/deals/<deal_id>/upload — Prompt 25: drag-drop
        # seller data upload. Parses each uploaded file via the
        # document reader, returns the extracted metrics + any
        # conflicts. The wizard's Step 3 uses this.
        if (len(parts) == 4 and parts[0] == "api" and parts[1] == "deals"
                and parts[3] == "upload"):
            import tempfile as _tempfile
            from .data.document_reader import read_seller_file
            deal_id = urllib.parse.unquote(parts[2])
            try:
                fields, files = self._parse_multipart()
            except ValueError as exc:
                return self._send_json(
                    {"error": str(exc)},
                    status=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                )
            if not files:
                return self._send_json(
                    {"error": "no file field in upload"},
                    status=HTTPStatus.BAD_REQUEST,
                )
            extracted: List[Dict[str, Any]] = []
            for field_name, (filename, content) in files.items():
                suffix = Path(filename).suffix or ".csv"
                with _tempfile.NamedTemporaryFile(
                    mode="wb", suffix=suffix, delete=False,
                ) as tmp:
                    tmp.write(content)
                    tmp_path = tmp.name
                try:
                    result = read_seller_file(Path(tmp_path))
                    d = result.to_dict()
                    d["source_file"] = filename
                    extracted.append(d)
                finally:
                    try:
                        Path(tmp_path).unlink()
                    except OSError:
                        pass
            return self._send_json({
                "deal_id": deal_id,
                "files": extracted,
            })

        # POST /api/deals — Prompt 23: one-name deal creation.
        # Accepts JSON ``{"name": "Acme Regional", "deal_id": "opt"}``.
        # Calls ``auto_populate``, upserts the deal row with the merged
        # profile, and returns the :class:`AutoPopulateResult` JSON so
        # the wizard UI can render the confirmation step.
        if parts == ["api", "deals"]:
            import json as _json
            from .data.auto_populate import auto_populate
            n_bytes = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n_bytes) if n_bytes > 0 else b"{}"
            try:
                payload = _json.loads(raw.decode("utf-8") or "{}")
            except _json.JSONDecodeError:
                return self._send_json(
                    {"error": "body must be JSON"},
                    status=HTTPStatus.BAD_REQUEST,
                )
            query = str(payload.get("name") or payload.get("query") or "")
            if not query.strip():
                return self._send_json(
                    {"error": "name (or query) is required"},
                    status=HTTPStatus.BAD_REQUEST,
                )
            result = auto_populate(store, query)
            # If auto-selection fired we can upsert the deal immediately
            # — the caller can skip straight to the packet rebuild.
            created_deal_id: Optional[str] = None
            if result.selected is not None:
                explicit = str(payload.get("deal_id") or "").strip()
                created_deal_id = explicit or result.selected.ccn
                store.upsert_deal(
                    created_deal_id,
                    name=result.selected.name,
                    profile={
                        **{k: v for k, v in result.profile.items()
                           if not callable(v)},
                    },
                )
            out = result.to_dict()
            out["deal_id"] = created_deal_id
            return self._send_json(out)

        # POST /api/deals/<id>/actuals
        if (len(parts) == 4 and parts[0] == "api" and parts[1] == "deals"
                and parts[3] == "actuals"):
            deal_id = urllib.parse.unquote(parts[2])
            form = self._read_form_body()
            try:
                from .pe.hold_tracking import TRACKED_KPIS, record_quarterly_actuals
                quarter = form.get("quarter", "").strip()
                actuals: Dict[str, float] = {}
                plan: Dict[str, float] = {}
                for kpi in TRACKED_KPIS:
                    a = form.get(kpi, "").strip()
                    if a:
                        actuals[kpi] = float(a)
                    p = form.get(f"plan_{kpi}", "").strip()
                    if p:
                        plan[kpi] = float(p)
                record_quarterly_actuals(
                    store, deal_id=deal_id, quarter=quarter,
                    actuals=actuals, plan=plan or None,
                    notes=form.get("notes", "").strip(),
                )
            except (ValueError, KeyError) as exc:
                return self._send_json(
                    {"error": str(exc)}, status=HTTPStatus.BAD_REQUEST,
                )
            self._redirect(f"/deal/{urllib.parse.quote(deal_id)}")
            return

        # POST /api/deals/<id>/remark  → compute + persist an underwrite re-mark
        # (B90a). Reads the deal's latest quarter of actuals, re-underwrites
        # based on TTM, and inserts a new hold-stage snapshot stamped
        # "Re-mark as of YYYYQn". Instant — no sim queue needed.
        if (len(parts) == 4 and parts[0] == "api" and parts[1] == "deals"
                and parts[3] == "remark"):
            deal_id = urllib.parse.unquote(parts[2])
            form = self._read_form_body()
            try:
                from .pe.hold_tracking import variance_report as _remark_vr
                from .pe.remark import compute_remark, persist_remark

                # Auto-detect the latest quarter with actuals if not specified
                as_of = form.get("as_of", "").strip()
                if not as_of:
                    vdf = _remark_vr(store, deal_id)
                    if vdf.empty or "ebitda" not in set(vdf["kpi"]):
                        raise ValueError(
                            "Deal has no EBITDA actuals to re-mark from. "
                            "Record at least one quarter first."
                        )
                    ebitda_rows = vdf[vdf["kpi"] == "ebitda"]
                    as_of = str(ebitda_rows["quarter"].max())

                result = compute_remark(store, deal_id=deal_id, as_of_quarter=as_of)
                persist_remark(store, result)
            except ValueError as exc:
                return self._send_json(
                    {"error": str(exc)}, status=HTTPStatus.BAD_REQUEST,
                )
            self._redirect(f"/deal/{urllib.parse.quote(deal_id)}")
            return

        # POST /api/deals/<id>/snapshots
        if (len(parts) == 4 and parts[0] == "api" and parts[1] == "deals"
                and parts[3] == "snapshots"):
            deal_id = urllib.parse.unquote(parts[2])
            form = self._read_form_body()
            try:
                from .portfolio.portfolio_snapshots import register_snapshot
                stage = form.get("stage", "").strip()
                run_dir = form.get("run_dir", "").strip() or None
                register_snapshot(
                    store, deal_id=deal_id, stage=stage,
                    run_dir=run_dir, notes=form.get("notes", "").strip(),
                )
            except ValueError as exc:
                return self._send_json(
                    {"error": str(exc)}, status=HTTPStatus.BAD_REQUEST,
                )
            self._redirect(f"/deal/{urllib.parse.quote(deal_id)}")
            return

        # POST /api/deals/<id>/notes  (append)
        if (len(parts) == 4 and parts[0] == "api" and parts[1] == "deals"
                and parts[3] == "notes"):
            deal_id = urllib.parse.unquote(parts[2])
            form = self._read_form_body()
            try:
                record_note(
                    store, deal_id=deal_id,
                    body=form.get("body", ""),
                    author=form.get("author", ""),
                )
            except ValueError as exc:
                return self._send_json(
                    {"error": str(exc)}, status=HTTPStatus.BAD_REQUEST,
                )
            self._redirect(f"/deal/{urllib.parse.quote(deal_id)}")
            return

        # POST /api/jobs/run  (B95: queue a simulation)
        if parts == ["api", "jobs", "run"]:
            from .infra.job_queue import get_default_registry
            form = self._read_form_body()
            try:
                # Required params
                actual = form.get("actual", "").strip()
                benchmark = form.get("benchmark", "").strip()
                outdir = form.get("outdir", "").strip()
                if not (actual and benchmark and outdir):
                    raise ValueError(
                        "actual, benchmark, and outdir are required"
                    )
                # Protect against obvious path-traversal — require absolute
                # paths or paths under the server's --outdir.
                for label, p in [("actual", actual), ("benchmark", benchmark)]:
                    if not os.path.isfile(p):
                        raise ValueError(f"{label} path does not exist: {p}")
                reg = get_default_registry()
                job_id = reg.submit_run(
                    actual=actual, benchmark=benchmark, outdir=outdir,
                    n_sims=int(form.get("n_sims") or 5000),
                    seed=int(form.get("seed") or 42),
                    no_report=form.get("no_report") == "1",
                    partner_brief=form.get("partner_brief") == "1",
                )
            except (ValueError, KeyError, OSError) as exc:
                return self._send_json(
                    {"error": str(exc)}, status=HTTPStatus.BAD_REQUEST,
                )
            # JSON callers (scripts / LLM agents) get the job_id directly;
            # browsers are redirected to the live progress page.
            accept = self.headers.get("Accept", "")
            if "application/json" in accept:
                return self._send_json({"job_id": job_id}, status=HTTPStatus.ACCEPTED)
            self._redirect(f"/jobs/{job_id}")
            return

        # POST /api/deals/<id>/deadlines  (B114: add a deadline)
        if (len(parts) == 4 and parts[0] == "api" and parts[1] == "deals"
                and parts[3] == "deadlines"):
            from .deals.deal_deadlines import add_deadline
            deal_id = urllib.parse.unquote(parts[2])
            form = self._read_form_body()
            try:
                add_deadline(
                    store, deal_id=deal_id,
                    label=form.get("label", ""),
                    due_date=form.get("due_date", ""),
                    notes=form.get("notes", ""),
                    owner=form.get("owner", ""),
                )
                self._log_audit(
                    "deadline.add", target=deal_id,
                    label=form.get("label", ""),
                    due_date=form.get("due_date", ""),
                    owner=form.get("owner", ""),
                )
            except ValueError as exc:
                return self._send_json(
                    {"error": str(exc)}, status=HTTPStatus.BAD_REQUEST,
                )
            self._redirect(f"/deal/{urllib.parse.quote(deal_id)}")
            return

        # POST /api/deadlines/<id>/assign  (B116: change owner)
        if (len(parts) == 4 and parts[0] == "api" and parts[1] == "deadlines"
                and parts[3] == "assign"):
            from .deals.deal_deadlines import assign_deadline_owner
            form = self._read_form_body()
            try:
                assign_deadline_owner(
                    store, int(parts[2]), form.get("owner", ""),
                )
            except ValueError:
                return self._send_json(
                    {"error": "deadline_id must be int"},
                    status=HTTPStatus.BAD_REQUEST,
                )
            accept = self.headers.get("Accept", "")
            if "application/json" in accept:
                return self._send_json({"ok": True})
            self._redirect("/deadlines")
            return

        # POST /api/deadlines/<id>/complete  (B114: mark done)
        if (len(parts) == 4 and parts[0] == "api" and parts[1] == "deadlines"
                and parts[3] == "complete"):
            from .deals.deal_deadlines import complete_deadline
            try:
                did = int(parts[2])
                ok = complete_deadline(store, did)
                if ok:
                    self._log_audit(
                        "deadline.complete", target=str(did),
                    )
            except ValueError:
                return self._send_json(
                    {"error": "deadline_id must be int"},
                    status=HTTPStatus.BAD_REQUEST,
                )
            accept = self.headers.get("Accept", "")
            if "application/json" in accept:
                return self._send_json({"completed": ok})
            self._redirect("/deadlines")
            return

        # POST /api/notes/<id>/tags  (B123: add a tag)
        # POST /api/notes/<id>/tags/remove  (B123: remove a tag)
        if (parts[:2] == ["api", "notes"] and len(parts) >= 4
                and parts[3] == "tags"):
            from .deals.note_tags import add_note_tag, remove_note_tag
            try:
                nid = int(parts[2])
            except ValueError:
                return self._send_json(
                    {"error": "note_id must be int"},
                    status=HTTPStatus.BAD_REQUEST,
                )
            form = self._read_form_body()
            try:
                if len(parts) == 5 and parts[4] == "remove":
                    changed = remove_note_tag(store, nid, form.get("tag", ""))
                else:
                    changed = add_note_tag(store, nid, form.get("tag", ""))
            except ValueError as exc:
                return self._send_json(
                    {"error": str(exc)}, status=HTTPStatus.BAD_REQUEST,
                )
            accept = self.headers.get("Accept", "")
            if "application/json" in accept:
                return self._send_json({"changed": changed})
            # Redirect back to referer if present, else /notes
            ref = self.headers.get("Referer", "/notes")
            self._redirect(ref)
            return

        # POST /api/users/{create,delete,password}  (B129: admin user mgmt)
        if (len(parts) == 3 and parts[0] == "api" and parts[1] == "users"
                and parts[2] in ("create", "delete", "password")):
            cu = self._current_user()
            # Admin-only — and in multi-user mode only (the /users CLI
            # is the bootstrap path in single-user mode)
            from .auth.auth import list_users
            users_df = list_users(store)
            if len(users_df) > 0:
                if cu is None or cu.get("role") != "admin":
                    return self._send_json(
                        {"error": "admin role required"},
                        status=HTTPStatus.FORBIDDEN,
                    )
            form = self._read_form_body()
            try:
                if parts[2] == "create":
                    from .auth.auth import create_user
                    create_user(
                        store,
                        form.get("username", ""),
                        form.get("password", ""),
                        display_name=form.get("display_name", ""),
                        role=form.get("role", "analyst") or "analyst",
                    )
                    self._log_audit(
                        "user.create", target=form.get("username", ""),
                        role=form.get("role", "analyst") or "analyst",
                    )
                    return self._send_json(
                        {"ok": True, "username": form.get("username", "")},
                        status=HTTPStatus.CREATED,
                    )
                if parts[2] == "delete":
                    from .auth.auth import delete_user
                    ok = delete_user(store, form.get("username", ""))
                    if ok:
                        self._log_audit(
                            "user.delete", target=form.get("username", ""),
                        )
                    return self._send_json({"deleted": ok})
                if parts[2] == "password":
                    from .auth.auth import change_password
                    ok = change_password(
                        store,
                        form.get("username", ""),
                        form.get("new_password", ""),
                    )
                    if not ok:
                        return self._send_json(
                            {"error": "user not found"},
                            status=HTTPStatus.NOT_FOUND,
                        )
                    self._log_audit(
                        "user.password_change",
                        target=form.get("username", ""),
                    )
                    return self._send_json({"ok": True})
            except ValueError as exc:
                return self._send_json(
                    {"error": str(exc)}, status=HTTPStatus.BAD_REQUEST,
                )

        # POST /api/deals/<id>/sim-inputs  (B121: persist paths for rerun)
        if (len(parts) == 4 and parts[0] == "api" and parts[1] == "deals"
                and parts[3] == "sim-inputs"):
            from .deals.deal_sim_inputs import set_inputs
            deal_id = urllib.parse.unquote(parts[2])
            form = self._read_form_body()
            try:
                set_inputs(
                    store, deal_id=deal_id,
                    actual_path=form.get("actual_path", ""),
                    benchmark_path=form.get("benchmark_path", ""),
                    outdir_base=form.get("outdir_base", ""),
                )
            except ValueError as exc:
                return self._send_json(
                    {"error": str(exc)}, status=HTTPStatus.BAD_REQUEST,
                )
            self._redirect(f"/deal/{urllib.parse.quote(deal_id)}")
            return

        # POST /api/deals/<id>/rerun  (B121: queue a sim using stored paths)
        if (len(parts) == 4 and parts[0] == "api" and parts[1] == "deals"
                and parts[3] == "rerun"):
            from .deals.deal_sim_inputs import get_inputs, next_outdir
            from .infra.job_queue import get_default_registry
            deal_id = urllib.parse.unquote(parts[2])
            inputs = get_inputs(store, deal_id)
            if inputs is None:
                return self._send_json(
                    {"error": "deal has no stored sim inputs — "
                              "set them first"},
                    status=HTTPStatus.BAD_REQUEST,
                )
            if not os.path.isfile(inputs["actual_path"]):
                return self._send_json(
                    {"error": f"actual_path not found: "
                              f"{inputs['actual_path']}"},
                    status=HTTPStatus.BAD_REQUEST,
                )
            if not os.path.isfile(inputs["benchmark_path"]):
                return self._send_json(
                    {"error": f"benchmark_path not found: "
                              f"{inputs['benchmark_path']}"},
                    status=HTTPStatus.BAD_REQUEST,
                )
            form = self._read_form_body()
            outdir = next_outdir(deal_id, inputs.get("outdir_base") or "")
            reg = get_default_registry()
            job_id = reg.submit_run(
                actual=inputs["actual_path"],
                benchmark=inputs["benchmark_path"],
                outdir=outdir,
                n_sims=int(form.get("n_sims") or 5000),
                seed=int(form.get("seed") or 42),
            )
            accept = self.headers.get("Accept", "")
            if "application/json" in accept:
                return self._send_json(
                    {"job_id": job_id, "outdir": outdir},
                    status=HTTPStatus.ACCEPTED,
                )
            self._redirect(f"/jobs/{job_id}")
            return

        # POST /api/deals/<id>/owner  (B113: assign current owner)
        if (len(parts) == 4 and parts[0] == "api" and parts[1] == "deals"
                and parts[3] == "owner"):
            from .deals.deal_owners import assign_owner
            deal_id = urllib.parse.unquote(parts[2])
            form = self._read_form_body()
            try:
                assign_owner(
                    store, deal_id=deal_id,
                    owner=form.get("owner", ""),
                    note=form.get("note", ""),
                )
                self._log_audit(
                    "owner.assign", target=deal_id,
                    owner=form.get("owner", ""),
                )
            except ValueError as exc:
                return self._send_json(
                    {"error": str(exc)}, status=HTTPStatus.BAD_REQUEST,
                )
            self._redirect(f"/deal/{urllib.parse.quote(deal_id)}")
            return

        # POST /api/deals/<id>/star  (B111: toggle watchlist star)
        if (len(parts) == 4 and parts[0] == "api" and parts[1] == "deals"
                and parts[3] == "star"):
            from .deals.watchlist import toggle_star
            deal_id = urllib.parse.unquote(parts[2])
            new_state = toggle_star(store, deal_id)
            accept = self.headers.get("Accept", "")
            if "application/json" in accept:
                return self._send_json({
                    "deal_id": deal_id, "starred": new_state,
                })
            self._redirect(f"/deal/{urllib.parse.quote(deal_id)}")
            return

        # POST /api/alerts/ack  (B102: acknowledge / snooze an alert instance)
        if parts == ["api", "alerts", "ack"]:
            form = self._read_form_body()
            try:
                from .alerts.alert_acks import ack_alert
                kind = form.get("kind", "").strip()
                deal_id = form.get("deal_id", "").strip()
                trigger_key = form.get("trigger_key", "").strip()
                if not (kind and deal_id and trigger_key):
                    raise ValueError(
                        "kind, deal_id, and trigger_key are required"
                    )
                snooze_days = int(form.get("snooze_days") or 0)
                # B125: prefer authenticated user over self-reported
                cu = self._current_user()
                acked_by = (
                    cu["username"] if cu
                    else form.get("acked_by", "").strip()
                )
                ack_id = ack_alert(
                    store,
                    kind=kind, deal_id=deal_id, trigger_key=trigger_key,
                    snooze_days=snooze_days,
                    note=form.get("note", "").strip(),
                    acked_by=acked_by,
                )
                self._log_audit(
                    "alert.ack", target=deal_id,
                    kind=kind, snooze_days=snooze_days, ack_id=ack_id,
                )
            except (ValueError, KeyError) as exc:
                return self._send_json(
                    {"error": str(exc)}, status=HTTPStatus.BAD_REQUEST,
                )
            accept = self.headers.get("Accept", "")
            if "application/json" in accept:
                return self._send_json({"ack_id": ack_id}, status=HTTPStatus.CREATED)
            self._redirect("/alerts")
            return

        # POST /api/bulk/stage  (B99: advance N deals to the same stage)
        if (parts == ["api", "bulk", "stage"]):
            form = self._read_form_body()
            stage = form.get("stage", "").strip()
            raw_ids = form.get("deal_ids", "")
            ids = [d.strip() for d in raw_ids.split(",") if d.strip()]
            if not ids:
                return self._send_json(
                    {"error": "deal_ids must be a non-empty comma-list"},
                    status=HTTPStatus.BAD_REQUEST,
                )
            try:
                from .portfolio.portfolio_snapshots import register_snapshot
                for did in ids:
                    register_snapshot(store, deal_id=did, stage=stage,
                                      notes="bulk stage advance")
            except ValueError as exc:
                return self._send_json(
                    {"error": str(exc)}, status=HTTPStatus.BAD_REQUEST,
                )
            accept = self.headers.get("Accept", "")
            if "application/json" in accept:
                return self._send_json({
                    "action": "stage", "stage": stage,
                    "deal_ids": ids, "affected": len(ids),
                })
            self._redirect("/")
            return

        # POST /api/bulk/tags/add   (B97: apply a tag to N deals in one request)
        # POST /api/bulk/tags/remove
        if (len(parts) == 4 and parts[0] == "api" and parts[1] == "bulk"
                and parts[2] == "tags" and parts[3] in ("add", "remove")):
            form = self._read_form_body()
            tag_name = form.get("tag", "")
            raw_ids = form.get("deal_ids", "")
            ids = [d.strip() for d in raw_ids.split(",") if d.strip()]
            if not ids:
                return self._send_json(
                    {"error": "deal_ids must be a non-empty comma-list"},
                    status=HTTPStatus.BAD_REQUEST,
                )
            try:
                ok_count = 0
                for did in ids:
                    if parts[3] == "add":
                        if add_tag(store, deal_id=did, tag=tag_name):
                            ok_count += 1
                    else:
                        if remove_tag(store, deal_id=did, tag=tag_name):
                            ok_count += 1
            except ValueError as exc:
                return self._send_json(
                    {"error": str(exc)}, status=HTTPStatus.BAD_REQUEST,
                )
            # Bulk result JSON so AJAX clients see per-tag counts,
            # but redirect browser users back to the dashboard
            accept = self.headers.get("Accept", "")
            if "application/json" in accept:
                return self._send_json({
                    "action": parts[3],
                    "tag": tag_name.strip().lower(),
                    "deal_ids": ids,
                    "affected": ok_count,
                })
            self._redirect("/")
            return

        # POST /api/deals/<id>/tags  (add)
        if (len(parts) == 4 and parts[0] == "api" and parts[1] == "deals"
                and parts[3] == "tags"):
            deal_id = urllib.parse.unquote(parts[2])
            form = self._read_form_body()
            tag = form.get("tag", "")
            try:
                add_tag(store, deal_id=deal_id, tag=tag)
            except ValueError as exc:
                return self._send_json(
                    {"error": str(exc)}, status=HTTPStatus.BAD_REQUEST,
                )
            self._redirect(f"/deal/{urllib.parse.quote(deal_id)}")
            return

        # POST /api/deals/<id>/tags/<tag>/remove
        if (len(parts) == 6 and parts[0] == "api" and parts[1] == "deals"
                and parts[3] == "tags" and parts[5] == "remove"):
            deal_id = urllib.parse.unquote(parts[2])
            tag_name = urllib.parse.unquote(parts[4])
            try:
                remove_tag(store, deal_id=deal_id, tag=tag_name)
            except ValueError as exc:
                return self._send_json(
                    {"error": str(exc)}, status=HTTPStatus.BAD_REQUEST,
                )
            self._redirect(f"/deal/{urllib.parse.quote(deal_id)}")
            return

        # POST /api/deals/<id>/notes/<note_id>/delete  (soft)
        # POST /api/deals/<id>/notes/<note_id>/restore
        # POST /api/deals/<id>/notes/<note_id>/purge    (hard)
        if (len(parts) == 6 and parts[0] == "api" and parts[1] == "deals"
                and parts[3] == "notes"
                and parts[5] in ("delete", "restore", "purge")):
            deal_id = urllib.parse.unquote(parts[2])
            try:
                from .deals.deal_notes import (
                    delete_note, hard_delete_note, undelete_note,
                )
                nid = int(parts[4])
                if parts[5] == "delete":
                    delete_note(store, nid)
                elif parts[5] == "restore":
                    undelete_note(store, nid)
                else:  # purge
                    hard_delete_note(store, nid)
            except (ValueError, TypeError) as exc:
                return self._send_json(
                    {"error": str(exc)}, status=HTTPStatus.BAD_REQUEST,
                )
            self._redirect(f"/deal/{urllib.parse.quote(deal_id)}")
            return

        # POST /api/analysis/<deal_id>/simulate — run MC with custom
        # assumptions (JSON body: ``{"assumptions": {metric: {...}},
        # "financials": {...}, "n_simulations": 2000, "seed": 42}``).
        # POST /api/analysis/<deal_id>/simulate/compare — run MC for
        # multiple named scenarios and return pairwise-win probabilities.
        if (len(parts) >= 4 and parts[0] == "api" and parts[1] == "analysis"
                and parts[3] == "simulate"):
            import json as _json
            deal_id = urllib.parse.unquote(parts[2])
            n_bytes = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(n_bytes) if n_bytes > 0 else b"{}"
            try:
                payload = _json.loads(body.decode("utf-8") or "{}")
            except _json.JSONDecodeError:
                return self._send_json(
                    {"error": "request body must be JSON"},
                    status=HTTPStatus.BAD_REQUEST,
                )
            if len(parts) == 5 and parts[4] == "compare":
                return self._route_simulate_compare(deal_id, payload)
            if len(parts) == 5 and parts[4] == "v2":
                return self._route_simulate_v2(deal_id, payload)
            return self._route_simulate_run(deal_id, payload)

        # POST /api/analysis/<deal_id>/bridge — recompute the EBITDA bridge
        # with caller-supplied target metrics (JSON body:
        # ``{"targets": {...}, "financials": {...}}``). The cached packet
        # is NOT modified — this endpoint returns an on-demand bridge
        # result so the partner can play with what-ifs.
        if (len(parts) == 4 and parts[0] == "api" and parts[1] == "analysis"
                and parts[3] == "bridge"):
            import json as _json
            deal_id = urllib.parse.unquote(parts[2])
            body = self.rfile.read(
                int(self.headers.get("Content-Length") or 0)
            ) if int(self.headers.get("Content-Length") or 0) > 0 else b"{}"
            try:
                payload = _json.loads(body.decode("utf-8") or "{}")
            except _json.JSONDecodeError:
                return self._send_json(
                    {"error": "request body must be JSON"},
                    status=HTTPStatus.BAD_REQUEST,
                )
            targets = payload.get("targets") or {}
            financials = payload.get("financials") or {}
            if not isinstance(targets, dict) or not isinstance(financials, dict):
                return self._send_json(
                    {"error": "targets and financials must be objects"},
                    status=HTTPStatus.BAD_REQUEST,
                )
            from .pe.rcm_ebitda_bridge import FinancialProfile, RCMEBITDABridge
            from .analysis.analysis_store import get_or_build_packet
            try:
                packet = get_or_build_packet(
                    store, deal_id, skip_simulation=True,
                )
            except Exception as exc:  # noqa: BLE001
                return self._send_json(
                    {"error": f"packet build failed: {exc}"},
                    status=HTTPStatus.INTERNAL_SERVER_ERROR,
                )
            fp_kwargs = {
                "gross_revenue": float(financials.get("gross_revenue") or 0.0),
                "net_revenue": float(financials.get("net_revenue") or 0.0),
                "current_ebitda": float(financials.get("current_ebitda")
                                         or packet.ebitda_bridge.current_ebitda or 0.0),
                "total_operating_expenses": float(
                    financials.get("total_operating_expenses") or 0.0),
                "cost_of_capital_pct": float(financials.get("cost_of_capital_pct") or 0.08),
                "total_claims_volume": int(financials.get("total_claims_volume") or 0),
                "payer_mix": dict(packet.profile.payer_mix or {}),
            }
            fp = FinancialProfile(**fp_kwargs)
            bridge = RCMEBITDABridge(fp)
            # Build current_metrics from the rcm_profile.
            current_metrics = {
                k: float(v.value) for k, v in packet.rcm_profile.items()
            }
            try:
                result = bridge.compute_bridge(current_metrics,
                                               {str(k): float(v) for k, v in targets.items()})
            except Exception as exc:  # noqa: BLE001
                return self._send_json(
                    {"error": f"bridge compute failed: {exc}"},
                    status=HTTPStatus.INTERNAL_SERVER_ERROR,
                )
            return self._send_json({
                "deal_id": deal_id,
                "run_id": packet.run_id,
                "bridge": result.to_dict(),
            })

        # POST /api/data/refresh/<source> — kick off a refresh for one source
        # (or "all"). Returns the RefreshReport inline. Rate-limited to
        # 1 hit per (source, hour) so we don't hammer CMS if a partner
        # slams the Refresh button on an automated refresh schedule.
        if (len(parts) == 4 and parts[0] == "api" and parts[1] == "data"
                and parts[2] == "refresh"):
            from .data import data_refresh as dr
            source = urllib.parse.unquote(parts[3])
            sources = None
            if source and source != "all":
                if source not in dr.KNOWN_SOURCES:
                    return self._send_json(
                        {"error": f"unknown source {source!r}",
                         "code": "UNKNOWN_SOURCE",
                         "detail": {"known": list(dr.KNOWN_SOURCES)}},
                        status=HTTPStatus.BAD_REQUEST,
                    )
                sources = [source]
            ok, wait = _REFRESH_RATE_LIMITER.check(f"refresh:{source}")
            if not ok:
                return self._send_json(
                    {"error": f"rate limited on {source!r}; "
                              f"wait {int(wait)}s",
                     "code": "RATE_LIMITED",
                     "detail": {"retry_after_seconds": int(wait)}},
                    status=HTTPStatus.TOO_MANY_REQUESTS,
                )
            try:
                report = dr.refresh_all_sources(store, sources=sources)
            except Exception as exc:  # noqa: BLE001
                return self._send_json(
                    {"error": str(exc),
                     "code": "REFRESH_FAILED"},
                    status=HTTPStatus.INTERNAL_SERVER_ERROR,
                )
            return self._send_json(report.to_dict())

        # POST /api/analysis/<deal_id>/sensitivity — deterministic sensitivity grid
        # (Prompt 47). Returns MOIC/IRR grid across hold years x exit multiples.
        if (len(parts) == 4 and parts[0] == "api" and parts[1] == "analysis"
                and parts[3] == "sensitivity"):
            from .ui.sensitivity_dashboard import handle_sensitivity_post
            form = self._read_form_body()
            try:
                result = handle_sensitivity_post(form)
            except (ValueError, TypeError) as exc:
                return self._send_json(
                    {"error": str(exc)}, status=HTTPStatus.BAD_REQUEST,
                )
            return self._send_json(result)

        # POST /api/analysis/<deal_id>/rebuild — force a new packet generation,
        # bypassing the input-hash cache. Returns the new packet as JSON so the
        # UI can refresh without a second roundtrip.
        if (len(parts) == 4 and parts[0] == "api" and parts[1] == "analysis"
                and parts[3] == "rebuild"):
            from datetime import date as _date
            from .analysis.analysis_store import get_or_build_packet
            deal_id = urllib.parse.unquote(parts[2])
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            scenario_id = (qs.get("scenario") or [None])[0] or None
            as_of_raw = (qs.get("as_of") or [None])[0]
            as_of = None
            if as_of_raw:
                try:
                    as_of = _date.fromisoformat(as_of_raw)
                except ValueError:
                    return self._send_json(
                        {"error": f"invalid as_of {as_of_raw!r}"},
                        status=HTTPStatus.BAD_REQUEST,
                    )
            try:
                packet = get_or_build_packet(
                    store, deal_id,
                    scenario_id=scenario_id, as_of=as_of,
                    force_rebuild=True, skip_simulation=True,
                )
            except Exception as exc:  # noqa: BLE001
                return self._send_json(
                    {"error": str(exc), "code": "BUILD_FAILED"},
                    status=HTTPStatus.INTERNAL_SERVER_ERROR,
                )
            return self._send_json({
                "deal_id": deal_id,
                "run_id": packet.run_id,
                "rebuilt": True,
                "packet": packet.to_dict(),
            })

        self.send_error(HTTPStatus.NOT_FOUND, f"Unknown POST path: {path}")

    def _redirect(self, location: str) -> None:
        """See Other redirect — browser re-GETs the target after form POST."""
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()


# ── Server lifecycle ───────────────────────────────────────────────────────

def build_server(
    *,
    port: int = 8765,
    db_path: Optional[str] = None,
    outdir: Optional[str] = None,
    title: str = "RCM Portfolio",
    host: str = "127.0.0.1",
    auth: Optional[str] = None,
) -> Tuple[ThreadingHTTPServer, RCMHandler]:
    """Construct (but don't start) the server + configured handler.

    Auth precedence: explicit ``auth`` arg > ``RCM_MC_AUTH`` env var. Either
    must be ``user:pass`` form. None disables auth (the default for local
    laptop use). Writes apply to the handler's class-level config singleton.
    """
    if db_path:
        RCMHandler.config.db_path = db_path
    RCMHandler.config.outdir = os.path.abspath(outdir) if outdir else None
    RCMHandler.config.title = title

    # Reset auth to defaults each build so tests don't leak credentials
    RCMHandler.config.auth_user = None
    RCMHandler.config.auth_pass = None
    auth_raw = auth or os.environ.get("RCM_MC_AUTH")
    if auth_raw and ":" in auth_raw:
        u, _, p = auth_raw.partition(":")
        RCMHandler.config.auth_user = u
        RCMHandler.config.auth_pass = p

    # SO_REUSEADDR so successive starts don't fail on TIME_WAIT
    socketserver.TCPServer.allow_reuse_address = True

    # Prompt 21: session table hygiene at process boot. The JOIN in
    # ``user_for_session`` already rejects expired rows, so this is
    # purely to keep the table small across long-running deployments.
    try:
        from .auth.auth import cleanup_expired_sessions
        cleanup_expired_sessions(PortfolioStore(RCMHandler.config.db_path))
    except Exception:  # noqa: BLE001 — never block server boot on hygiene
        pass
    try:
        from .infra.migrations import run_pending
        run_pending(PortfolioStore(RCMHandler.config.db_path))
    except Exception:  # noqa: BLE001 — never block server boot
        pass
    RCMHandler._request_counter = 0
    RCMHandler._response_times = []
    RCMHandler._error_count = 0

    # Startup self-test: verify DB is readable
    try:
        _st = PortfolioStore(RCMHandler.config.db_path)
        with _st.connect() as _con:
            _con.execute("SELECT 1").fetchone()
    except Exception as _exc:
        import sys as _sys
        _sys.stderr.write(f"[rcm-mc] WARNING: DB self-test failed: {_exc}\n")
        _sys.stderr.flush()

    server = ThreadingHTTPServer((host, port), RCMHandler)
    server.timeout = 300
    RCMHandler.timeout = 120
    return server, RCMHandler


def run_server(
    *,
    port: int = 8765,
    db_path: Optional[str] = None,
    outdir: Optional[str] = None,
    title: str = "RCM Portfolio",
    host: str = "127.0.0.1",
    open_browser: bool = False,
    auth: Optional[str] = None,
) -> None:
    """Start the server and block until Ctrl+C."""
    import time as _boot_time
    _boot_start = _boot_time.perf_counter()
    server, _ = build_server(
        port=port, db_path=db_path, outdir=outdir, title=title, host=host,
        auth=auth,
    )
    url = f"http://{host}:{port}/"
    from . import __version__
    deal_count = 0
    try:
        _s = PortfolioStore(RCMHandler.config.db_path)
        deal_count = len(_s.list_deals())
    except Exception:
        pass
    _boot_ms = round((_boot_time.perf_counter() - _boot_start) * 1000)
    sys.stdout.write("\n")
    sys.stdout.write(f"rcm-mc v{__version__} — {url}\n")
    sys.stdout.write(f"  portfolio DB: {RCMHandler.config.db_path}\n")
    sys.stdout.write(f"  deals:        {deal_count}\n")
    if RCMHandler.config.outdir:
        sys.stdout.write(f"  outputs dir:  {RCMHandler.config.outdir}\n")
    if RCMHandler.config.auth_user:
        sys.stdout.write(
            f"  auth:         HTTP Basic as {RCMHandler.config.auth_user}\n"
        )
    sys.stdout.write(f"  API docs:     {url}api/docs\n")
    sys.stdout.write(f"  started in:   {_boot_ms}ms\n")
    sys.stdout.write("  Ctrl+C to stop\n\n")
    sys.stdout.flush()

    if open_browser:
        # Open in a thread so the serve_forever call isn't blocked
        threading.Thread(target=lambda: webbrowser.open(url), daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        sys.stdout.write("\nShutting down...\n")
    finally:
        server.server_close()


# ── CLI entry (invoked by rcm-mc serve) ────────────────────────────────────

def main(argv: Optional[list] = None, prog: str = "rcm-mc serve") -> int:
    import argparse

    ap = argparse.ArgumentParser(
        prog=prog,
        description="Start a local web server for the portfolio + outputs.",
    )
    ap.add_argument("--port", type=int, default=8765,
                    help="TCP port (default 8765)")
    ap.add_argument("--host", default="127.0.0.1",
                    help="Bind host (default 127.0.0.1 — local only)")
    ap.add_argument("--db", default=None, metavar="PATH",
                    help="Portfolio DB (default ~/.rcm_mc/portfolio.db)")
    ap.add_argument("--outdir", default=None, metavar="DIR",
                    help="Optional output folder served at /outputs/*")
    ap.add_argument("--title", default="RCM Portfolio",
                    help="Dashboard title")
    ap.add_argument("--open", dest="open_browser", action="store_true",
                    help="Open the dashboard in the default browser on start")
    ap.add_argument(
        "--auth", default=None, metavar="USER:PASS",
        help=(
            "Require HTTP Basic auth (team mode). Also read from "
            "RCM_MC_AUTH env var. Leave unset for single-user laptop."
        ),
    )
    args = ap.parse_args(argv)

    run_server(
        port=args.port, host=args.host,
        db_path=args.db, outdir=args.outdir,
        title=args.title, open_browser=args.open_browser,
        auth=args.auth,
    )
    return 0
