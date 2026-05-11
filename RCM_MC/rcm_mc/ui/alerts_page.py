"""Portfolio-wide alert review page — the partner's "where does this
need attention" workflow surface.

Place in the mesh
-----------------
A partner reaches this page three ways:
  1. The "Active alerts" panel on /home — the panel header deep-links
     into /alerts with the relevant severity pre-filtered.
  2. ⌘K command palette ("alerts") — global keyboard navigation.
  3. /portfolio breadcrumb — /alerts sits inside the Portfolio
     section of the Platform Index even though it isn't a top-level
     nav link. The editorial topbar holds at five primary links
     (Home / Pipeline / Library / Research / Portfolio) to preserve
     the chartis.com 5-link rhythm.

Connectivity chain — verified 2026-04-28 cycle 1 step 8:
  imports → resolve. alerts.alerts (evaluate_active, evaluate_all);
            alerts.alert_acks (trigger_key_for); alerts.alert_history
            (age_hint); deals.deal_owners (deals_by_owner);
            portfolio.store (PortfolioStore); _chartis_kit
            (chartis_shell + ck_severity_panel + ck_affirm_empty +
            ck_arrow_link + ck_eyebrow).
  route   → server.py dispatcher inlines the call to render_alerts
            (commit 0b875f8); the v3 inventory classifier reaches
            this module via the .ui import in the dispatcher block,
            which is why it classifies as v5 not (inline) unknown.
  shell   → chartis_shell wraps every response. No legacy shell().
  ck-only → uses ck_severity_panel / ck_affirm_empty / ck_arrow_link
            / ck_eyebrow — no bespoke <div class="card"> blocks since
            commit 9da9d1b.
  packet  → N/A. alerts is portfolio-level, not deal-specific, so
            the DealAnalysisPacket invariant is exempt by design
            (same exemption as /v3-status, /v5-status, /audit,
            /watchlist).

Module exposes a single entry point:

    render_alerts(store, *, show_all, owner_filter) -> str

Returns a full HTML string ready for ``_send_html``. Caller is
responsible for parsing the query string and constructing the
``store`` (the route handler in ``server.py`` does both — the store
is the only sqlite owner per the CLAUDE.md invariant).
"""
from __future__ import annotations

import html
import urllib.parse
from typing import Dict, List, Optional

from ..alerts.alerts import evaluate_active, evaluate_all
from ..alerts.alert_acks import trigger_key_for
from ..alerts.alert_history import age_hint
from ..deals.deal_owners import deals_by_owner
from ..portfolio.store import PortfolioStore
from ._chartis_kit import (
    chartis_shell,
    ck_affirm_empty,
    ck_arrow_link,
    ck_kpi_block,
    ck_next_section,
    ck_page_title,
    ck_provenance_tooltip,
)


_SEV_META = {
    "red":   ("RED", "Critical — covenant breach, covenant tripped, "
                     "or stage regress."),
    "amber": ("AMBER", "Warning — tight covenants, EBITDA miss, or "
                       "concerning-signal cluster."),
    "info":  ("INFO", "Informational — stage advance or new note."),
}

_SEV_TONE_COLOR = {
    "red":   "var(--sc-negative,#b5321e)",
    "amber": "var(--sc-warning,#b8732a)",
    "info":  "var(--sc-teal,#155752)",
}


def _name_lookup(store: PortfolioStore) -> Dict[str, str]:
    """Best-effort deal_id → friendly name. Empty dict on any error
    so a stale schema can't 500 the alerts page."""
    out: Dict[str, str] = {}
    try:
        with store.connect() as con:
            for r in con.execute("SELECT deal_id, name FROM deals"):
                if r["name"]:
                    out[r["deal_id"]] = r["name"]
    except Exception:  # noqa: BLE001
        pass
    return out


_ALERTS_CSS = """
<style>
  .ck-alerts-card{padding:0;overflow:hidden;margin:0 0 20px;}
  .ck-alerts-card-red    { border-left:3px solid var(--sc-negative,#b5321e); }
  .ck-alerts-card-amber  { border-left:3px solid var(--sc-warning,#b8732a); }
  .ck-alerts-card-info   { border-left:3px solid var(--sc-teal,#155752); }
  .ck-alerts-head{display:flex;align-items:baseline;justify-content:space-between;
    gap:12px;padding:18px 22px 12px;
    border-bottom:1px solid var(--sc-rule,#d6cfc3);}
  .ck-alerts-head h2{font-family:var(--sc-serif,Georgia,serif);
    font-weight:500;font-size:20px;color:var(--sc-navy,#0b2341);
    margin:0;letter-spacing:-0.01em;}
  .ck-alerts-head .meta{font-family:var(--sc-mono,monospace);font-size:11px;
    color:var(--sc-text-faint,#7a8699);letter-spacing:0.08em;
    text-transform:uppercase;}
  .ck-alerts-list{list-style:none;padding:0;margin:0;}
  .ck-alert-row{display:flex;align-items:center;gap:12px;flex-wrap:wrap;
    padding:12px 22px;border-bottom:1px solid var(--sc-rule,#d6cfc3);
    font-size:13px;}
  .ck-alert-row:last-child{border-bottom:0;}
  .ck-alert-sev{font-family:var(--sc-mono,monospace);font-weight:700;
    font-size:10.5px;letter-spacing:0.1em;text-transform:uppercase;}
  .ck-alert-deal{color:var(--sc-navy,#0b2341);font-weight:600;
    text-decoration:none;}
  .ck-alert-deal:hover{color:var(--sc-teal,#155752);}
  .ck-alert-slug{font-family:var(--sc-mono,monospace);font-size:10.5px;
    color:var(--sc-text-faint,#7a8699);letter-spacing:0.04em;}
  .ck-alert-title{color:var(--sc-text,#1a2332);font-weight:600;}
  .ck-alert-detail{color:var(--sc-text-dim,#465366);font-size:12.5px;
    flex-basis:100%;margin-top:4px;}
  .ck-alert-age{font-family:var(--sc-mono,monospace);font-size:10.5px;
    color:var(--sc-text-faint,#7a8699);letter-spacing:0.04em;}
  .ck-alert-returning{font-family:var(--sc-mono,monospace);font-size:10px;
    letter-spacing:0.08em;text-transform:uppercase;
    color:var(--sc-warning,#b8732a);font-weight:700;}
  .ck-alert-ack-form{display:inline-flex;gap:6px;align-items:center;
    margin:0 0 0 auto;}
  .ck-alert-snooze{padding:5px 10px;
    border:1px solid var(--sc-rule,#d6cfc3);background:#fff;
    font-family:var(--sc-sans,Inter,sans-serif);font-size:11.5px;
    color:var(--sc-text,#1a2332);border-radius:2px;}
  .ck-alert-go{padding:5px 12px;background:#fff;
    border:1px solid var(--sc-rule,#d6cfc3);
    font-family:var(--sc-sans,Inter,sans-serif);font-size:10.5px;
    font-weight:700;letter-spacing:0.08em;text-transform:uppercase;
    color:var(--sc-navy,#0b2341);cursor:pointer;border-radius:2px;}
  .ck-alert-go:hover{background:var(--sc-bone,#ece6db);
    border-color:var(--sc-teal,#155752);color:var(--sc-teal,#155752);}

  .ck-alerts-filter-row{display:flex;align-items:center;gap:10px;
    margin:0 0 24px;flex-wrap:wrap;}
  .ck-alerts-filter-form{display:inline-flex;align-items:center;gap:8px;
    background:#fff;border:1px solid var(--sc-rule,#d6cfc3);
    border-radius:2px;padding:6px 10px;}
  .ck-alerts-filter-label{font-family:var(--sc-mono,monospace);font-size:10.5px;
    font-weight:700;letter-spacing:0.1em;text-transform:uppercase;
    color:var(--sc-text-dim,#465366);}
  .ck-alerts-filter-form input{padding:5px 10px;border:0;
    font-family:var(--sc-sans,Inter,sans-serif);font-size:13px;
    background:transparent;color:var(--sc-text,#1a2332);width:10rem;outline:none;}
  .ck-alerts-filter-form button{padding:5px 12px;
    background:var(--sc-navy,#0b2341);color:#fff;border:0;
    font-family:var(--sc-sans,Inter,sans-serif);font-size:10.5px;
    font-weight:700;letter-spacing:0.08em;text-transform:uppercase;
    cursor:pointer;border-radius:2px;}
  .ck-alerts-filter-form button:hover{background:var(--sc-teal,#155752);}
  .ck-alerts-toggle{font-family:var(--sc-mono,monospace);font-size:11px;
    font-weight:700;letter-spacing:0.08em;text-transform:uppercase;
    color:var(--sc-teal-ink,#0f5e5a);text-decoration:none;
    padding:6px 12px;border:1px solid var(--sc-teal-ink,#0f5e5a);
    border-radius:2px;}
  .ck-alerts-toggle:hover{background:var(--sc-teal,#155752);color:#fff;}
</style>
"""


def _toggle_link(show_all: bool, owner_filter: Optional[str]) -> str:
    base_qs: Dict[str, str] = {}
    if owner_filter:
        base_qs["owner"] = owner_filter
    if show_all:
        href = "/alerts" + (
            "?" + urllib.parse.urlencode(base_qs) if base_qs else ""
        )
        label = "Show active only"
    else:
        href = "/alerts?" + urllib.parse.urlencode(dict(base_qs, show="all"))
        label = "Show acknowledged + all"
    return (
        f'<a href="{html.escape(href)}" class="ck-alerts-toggle">'
        f'{html.escape(label)}</a>'
    )


def _owner_form(show_all: bool, owner_filter: Optional[str]) -> str:
    """Editorial filter row — bone-bordered owner input with mono label
    and navy → teal Apply button. Sits inline with the show/all toggle
    so the partner's filter controls share one row."""
    # Pre-build the show-all hidden input outside the f-string so the
    # nested escaped quotes don't trip Python 3.11's parser
    # ("SyntaxError: f-string expression part cannot include a
    # backslash"). PEP 701 lifted the restriction in 3.12+, but CI
    # also runs against 3.11 — keep this 3.10–3.11 compatible.
    show_all_hidden = (
        '<input type="hidden" name="show" value="all">'
        if show_all else ""
    )
    return (
        '<form class="ck-alerts-filter-form" method="GET" action="/alerts">'
        '<span class="ck-alerts-filter-label">Owner</span>'
        f'<input type="text" name="owner" '
        f'value="{html.escape(owner_filter or "")}" '
        'placeholder="initials e.g. AT" maxlength="40">'
        f'{show_all_hidden}'
        '<button type="submit">Apply</button>'
        '</form>'
    )


def _row(a, name_map: Dict[str, str]) -> str:
    """Editorial alert row — matches the .ck-deal-alert-row chrome on
    the per-deal alerts panel so the inline + standalone views read as
    the same surface."""
    tk = trigger_key_for(a)
    age = age_hint(a.first_seen_at)
    age_html = (
        f'<span class="ck-alert-age">seen {html.escape(age)}</span>'
        if age else ""
    )
    returning_html = (
        '<span class="ck-alert-returning" '
        'title="Returned after snooze expired">↩ returning</span>'
        if getattr(a, "returning", False) else ""
    )
    sev_color = _SEV_TONE_COLOR.get(
        a.severity, "var(--sc-text-faint,#7a8699)",
    )
    deal_name = name_map.get(a.deal_id, a.deal_id)
    deal_link = (
        f'<a class="ck-alert-deal" '
        f'href="/deal/{urllib.parse.quote(a.deal_id)}">'
        f'{html.escape(deal_name)}</a>'
    )
    slug_html = (
        f'<span class="ck-alert-slug">{html.escape(a.deal_id)}</span>'
        if deal_name != a.deal_id else ""
    )
    ack_form = (
        f'<form method="POST" action="/api/alerts/ack" '
        f'class="ck-alert-ack-form">'
        f'<input type="hidden" name="kind" value="{html.escape(a.kind)}">'
        f'<input type="hidden" name="deal_id" '
        f'value="{html.escape(a.deal_id)}">'
        f'<input type="hidden" name="trigger_key" '
        f'value="{html.escape(tk)}">'
        f'<select name="snooze_days" aria-label="Snooze duration" '
        f'class="ck-alert-snooze">'
        f'<option value="0">Ack</option>'
        f'<option value="7">Snooze 7d</option>'
        f'<option value="30">Snooze 30d</option>'
        f'</select>'
        f'<button type="submit" class="ck-alert-go">Apply</button>'
        f'</form>'
    )
    return (
        '<li class="ck-alert-row">'
        f'<span class="ck-alert-sev" style="color:{sev_color};">'
        f'{html.escape(a.severity.upper())}</span>'
        f'{deal_link}'
        f'{slug_html}'
        f'<span class="ck-alert-title">{html.escape(a.title)}</span>'
        f'{returning_html}'
        f'{age_html}'
        f'{ack_form}'
        f'<div class="ck-alert-detail">{html.escape(a.detail)}</div>'
        '</li>'
    )


def render_alerts(
    store: PortfolioStore,
    *,
    show_all: bool = False,
    owner_filter: Optional[str] = None,
) -> str:
    """Full HTML for /alerts via chartis_shell.

    Migrated from ``server._route_alerts`` (Phase 2). Behavior is
    unchanged: red → amber → info ordering, ack/snooze POST form,
    optional owner filter, active/all toggle.
    """
    alerts = evaluate_all(store) if show_all else evaluate_active(store)
    if owner_filter:
        try:
            scope = set(deals_by_owner(store, owner_filter))
        except ValueError:
            scope = set()
        alerts = [a for a in alerts if a.deal_id in scope]

    name_map = _name_lookup(store)
    grouped: Dict[str, List] = {"red": [], "amber": [], "info": []}
    for a in alerts:
        grouped.setdefault(a.severity, []).append(a)
    n_red = len(grouped.get("red") or [])
    n_amber = len(grouped.get("amber") or [])
    n_info = len(grouped.get("info") or [])

    # Page header
    title_html = ck_page_title(
        "Alerts",
        eyebrow=("ACKNOWLEDGED + ALL" if show_all else "PORTFOLIO ALERTS"),
        meta=(
            f"{len(alerts):,} {'total' if show_all else 'active'} "
            f"alert{'s' if len(alerts) != 1 else ''}"
            + (f" · owner = {html.escape(owner_filter)}"
               if owner_filter else "")
        ),
    )

    # KPI strip — total, red, amber, info
    kpi_html = (
        '<div class="ck-kpi-grid" style="margin:0 0 24px;">'
        + ck_kpi_block(
            "Total" if not show_all else "Total (incl. acked)",
            f"{len(alerts):,}",
            sub=("active alerts" if not show_all
                 else "acknowledged + active"),
        )
        + ck_kpi_block(
            "Critical", f"{n_red}",
            sub="covenant trip / breach",
        )
        + ck_kpi_block(
            "Warning", f"{n_amber}",
            sub="tight covenant / EBITDA miss",
        )
        + ck_kpi_block(
            "Info", f"{n_info}",
            sub="stage advance / new note",
        )
        + '</div>'
    )

    filter_row = (
        '<div class="ck-alerts-filter-row">'
        + _owner_form(show_all, owner_filter)
        + (
            f'<a class="ck-alert-go" href="/alerts" '
            f'style="text-decoration:none;">Clear filter</a>'
            if owner_filter else ""
        )
        + _toggle_link(show_all, owner_filter)
        + '</div>'
    )

    if not alerts:
        if owner_filter:
            empty_headline = (
                f"No alerts for owner '{html.escape(owner_filter)}'"
            )
            empty_body = (
                "Either this owner has no deals assigned, or the deals "
                "they own are all clean. Try clearing the filter to "
                "see the full portfolio view."
            )
        else:
            empty_headline = "Portfolio is clean"
            empty_body = (
                "Zero active alerts across the portfolio. "
                "All covenants in headroom, no quarterly misses outside "
                "tolerance, no concerning-signal clusters."
            )
        if show_all:
            cta_text = "Show active only"
            cta_href = "/alerts" + (
                f"?owner={urllib.parse.quote(owner_filter)}"
                if owner_filter else ""
            )
        else:
            cta_text = "Show acknowledged + all"
            qs = {"show": "all"}
            if owner_filter:
                qs["owner"] = owner_filter
            cta_href = "/alerts?" + urllib.parse.urlencode(qs)
        body = (
            _ALERTS_CSS
            + title_html
            + kpi_html
            + filter_row
            + ck_affirm_empty(
                headline=empty_headline,
                body=empty_body,
                cta_text=cta_text,
                cta_href=cta_href,
            )
        )
    else:
        blocks: List[str] = []
        for sev in ("red", "amber", "info"):
            bucket = grouped.get(sev) or []
            if not bucket:
                continue
            label, _description = _SEV_META[sev]
            rows = "".join(_row(a, name_map) for a in bucket)
            blocks.append(
                f'<section class="cad-card ck-alerts-card ck-alerts-card-{sev}">'
                '<header class="ck-alerts-head">'
                f'<h2>{html.escape(label.title())} '
                f'({"critical" if sev == "red" else "warning" if sev == "amber" else "informational"})</h2>'
                f'<span class="meta">{len(bucket)} '
                f'alert{"s" if len(bucket) != 1 else ""}</span>'
                '</header>'
                f'<ul class="ck-alerts-list">{rows}</ul>'
                '</section>'
            )
        body = (
            _ALERTS_CSS
            + title_html
            + kpi_html
            + filter_row
            + "".join(blocks)
            + ck_next_section(
                "Open the portfolio for context",
                "/portfolio",
                eyebrow="Continue —",
                italic_word="portfolio",
            )
        )

    return chartis_shell(
        body, "Alerts", active_nav="/alerts",
        subtitle=(
            f"{len(alerts)} "
            f"{'total' if show_all else 'active'} "
            f"alert{'s' if len(alerts) != 1 else ''}"
            f"{f' · owner = {html.escape(owner_filter)}' if owner_filter else ''}"
        ),
    )
