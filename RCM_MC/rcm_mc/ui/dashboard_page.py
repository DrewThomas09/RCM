"""Dashboard — private-web-app landing page.

Renders four sections composed from existing data sources:

1. **Available analyses** — curated user-triggerable routes with
   descriptions + fixture links so analysts can immediately run them.

2. **Recent results** — in-process job queue (``infra.job_queue``)
   + on-disk run history (``infra.run_history``).

3. **System status** — platform version, uptime, DB reachability,
   migration state, job-queue worker health, PHI posture.

4. **Data freshness** — per-source last-refreshed timestamps from
   the ``data_source_status`` table (``data.data_refresh``). Color-
   coded traffic lights: green < 7 d, amber 7-30 d, red > 30 d.

All four sections render graceful empty states (fresh Heroku deploy
has zero deals, zero runs, zero data refreshes).

Public API:
    render_dashboard(db_path: str, *, started_at: datetime | None = None) -> str
"""
from __future__ import annotations

import html as _html
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


# ── Curated analyses catalog ───────────────────────────────────────
# Not the full 40-module module_index — a focused subset of the
# highest-signal user-triggerable analyses. Each entry is a single
# click away, with a fixture parameter when one applies.

_CURATED_ANALYSES: List[Dict[str, str]] = [
    {
        "name": "Thesis Pipeline",
        "route": "/diligence/thesis-pipeline?dataset=hospital_04_mixed_payer",
        "category": "One-click diligence",
        "desc": "Run the full 19-step diligence chain on a fixture in ~170 ms.",
        "runtime": "~170 ms",
    },
    {
        "name": "HCRIS Peer X-Ray",
        "route": "/diligence/hcris-xray?ccn=010001",
        "category": "Screening",
        "desc": "Benchmark a hospital vs 25–50 bed/state/region-matched peers across 15 metrics.",
        "runtime": "~250 ms cold, ~7 ms cached",
    },
    {
        "name": "Bear Case Auto-Generator",
        "route": "/diligence/bear-case?dataset=hospital_04_mixed_payer",
        "category": "Synthesis",
        "desc": "Evidence-synthesized bear case from 8 source modules with citation keys.",
        "runtime": "~100 ms",
    },
    {
        "name": "Regulatory Calendar × Kill-Switch",
        "route": "/diligence/regulatory-calendar",
        "category": "Risk",
        "desc": "11 CMS/OIG/FTC events mapped to named thesis drivers. First-kill dates.",
        "runtime": "~50 ms",
    },
    {
        "name": "Covenant Stress Lab",
        "route": "/diligence/covenant-stress",
        "category": "Financial",
        "desc": "500-path × 20-quarter breach probability × 4 covenants.",
        "runtime": "~3–7 s",
    },
    {
        "name": "Payer Mix Stress",
        "route": "/diligence/payer-stress",
        "category": "Risk",
        "desc": "500-path rate-shock MC over 19 curated payers + HHI amplifier.",
        "runtime": "~2–5 s",
    },
    {
        "name": "Bridge Auto-Auditor",
        "route": "/diligence/bridge-audit",
        "category": "Diligence",
        "desc": "Paste banker bridge, get risk-adjusted rebuild vs ~3,000 historical outcomes.",
        "runtime": "~4 s",
    },
    {
        "name": "Deal Autopsy",
        "route": "/diligence/deal-autopsy",
        "category": "Pattern match",
        "desc": "9-dim signature match against 12 named historical failures.",
        "runtime": "~50 ms",
    },
    {
        "name": "Corpus Browser",
        "route": "/sponsor-league",
        "category": "Market intel",
        "desc": "173 corpus-browser pages: sponsor league, vintage cohorts, payer intelligence, etc.",
        "runtime": "varies",
    },
    {
        "name": "IC Packet Builder",
        "route": "/diligence/ic-packet",
        "category": "Deliverable",
        "desc": "Print-ready IC memo bundling every diligence module.",
        "runtime": "~500 ms",
    },
]


# ── Utility: freshness bucket ──────────────────────────────────────

def _freshness_bucket(last_refreshed_iso: Optional[str]) -> tuple[str, str]:
    """Classify an ISO timestamp into (level, label) — level ∈ {ok/stale/cold/never}."""
    if not last_refreshed_iso:
        return ("never", "never refreshed")
    try:
        ts = datetime.fromisoformat(last_refreshed_iso.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
    except ValueError:
        return ("never", "unparseable")
    days = (datetime.now(timezone.utc) - ts).days
    if days < 7:
        return ("ok", f"{days}d ago")
    if days < 30:
        return ("stale", f"{days}d ago")
    return ("cold", f"{days}d ago")


def _dot(level: str) -> str:
    colors = {"ok": "#10b981", "stale": "#f59e0b",
              "cold": "#ef4444", "never": "#6b7280"}
    c = colors.get(level, "#6b7280")
    return (f'<span style="display:inline-block;width:8px;height:8px;'
            f'border-radius:50%;background:{c};margin-right:6px;"></span>')


# ── Section renderers ──────────────────────────────────────────────

def _render_analyses_section() -> str:
    from . import _web_components as _wc

    rows: List[List[str]] = []
    for a in _CURATED_ANALYSES:
        rows.append([
            (f'<a href="{_html.escape(a["route"])}" '
             f'style="color:#1F4E78;font-weight:500;">'
             f'{_html.escape(a["name"])}</a>'),
            f'<span style="color:#6b7280;">{_html.escape(a["category"])}</span>',
            _html.escape(a["desc"]),
            (f'<span style="color:#6b7280;">'
             f'{_html.escape(a["runtime"])}</span>'),
        ])
    table = _wc.sortable_table(
        ["Analysis", "Category", "What it does", "Runtime"],
        rows, id="dashboard-analyses", hide_columns_sm=[1, 3],
        filterable=True, filter_placeholder="Filter analyses…",
    )
    return _wc.section_card("What you can run", table, pad=False)


def _workflow_badge_counts(db_path: str) -> Dict[str, Optional[int]]:
    """Read live counts for the Daily workflow surfaces.

    Each value is the number a partner cares about for the morning
    sweep: open alerts to triage, overdue deadlines to chase, deals
    on the watchlist, etc. Failures degrade silently to ``None`` so a
    missing table on a fresh DB doesn't break the dashboard render.
    """
    counts: Dict[str, Optional[int]] = {}
    try:
        from ..portfolio.store import PortfolioStore
        store = PortfolioStore(db_path)
    except Exception:  # noqa: BLE001
        return counts

    def _safe(key: str, fn) -> None:
        try:
            counts[key] = int(fn())
        except Exception:  # noqa: BLE001 — every count is best-effort
            counts[key] = None

    try:
        from ..alerts.alerts import active_count
        _safe("alerts", lambda: active_count(store))
    except Exception:  # noqa: BLE001 — module import itself can fail
        counts["alerts"] = None

    try:
        from ..deals.deal_deadlines import overdue
        _safe("overdue_deadlines", lambda: len(overdue(store)))
    except Exception:  # noqa: BLE001
        counts["overdue_deadlines"] = None

    try:
        from ..deals.watchlist import list_starred
        _safe("watchlist", lambda: len(list_starred(store)))
    except Exception:  # noqa: BLE001
        counts["watchlist"] = None

    try:
        from ..data.pipeline import list_searches
        import sqlite3 as _sql
        with _sql.connect(db_path) as con:
            con.row_factory = _sql.Row
            _safe("saved_searches", lambda: len(list_searches(con)))
    except Exception:  # noqa: BLE001
        counts["saved_searches"] = None

    return counts


def _badge(n: Optional[int], *, level: str = "neutral") -> str:
    """Inline count chip rendered next to a workflow label."""
    if n is None or n <= 0:
        return ""
    palette = {
        "ok": ("#d1fae5", "#065f46"),
        "warn": ("#fef3c7", "#92400e"),
        "alert": ("#fee2e2", "#991b1b"),
        "neutral": ("#e0e7ff", "#3730a3"),
    }
    bg, fg = palette.get(level, palette["neutral"])
    return (
        f'<span style="display:inline-block;margin-left:8px;'
        f'padding:1px 8px;background:{bg};color:{fg};'
        f'border-radius:9999px;font-size:11px;font-weight:600;'
        f'font-variant-numeric:tabular-nums;">{n}</span>'
    )


def _since_yesterday_events(db_path: str,
                            *, window_hours: int = 24) -> List[Dict[str, str]]:
    """Gather a cross-source change list for the "Since yesterday" card.

    Reads the four time-tagged tables that exist on a live install:
      - alert_history (new alerts fired in the window)
      - analysis_runs (packets built)
      - data_source_status (data refreshed)
      - audit_events (login/create/update events, scoped to non-GET)

    Each event is normalized into a dict with keys:
      ``at`` (ISO timestamp), ``icon``, ``label`` (≤ 80 chars),
      ``href`` (optional), ``kind`` (category for grouping).

    Every source is best-effort — a missing table on a fresh DB just
    returns no events from that source. Caller can render the empty
    state as "no changes in the last 24 hours."
    """
    import sqlite3 as _sql
    from datetime import datetime as _dt, timezone as _tz, timedelta as _td

    cutoff = (_dt.now(_tz.utc) - _td(hours=window_hours)).isoformat()
    events: List[Dict[str, str]] = []

    def _q(sql: str, params: tuple) -> List[Any]:
        try:
            with _sql.connect(db_path) as con:
                con.row_factory = _sql.Row
                return list(con.execute(sql, params).fetchall())
        except Exception:  # noqa: BLE001 — missing table / permission / race
            return []

    # Alerts fired. Pull `kind` + `trigger_key` so the UI can emit an
    # inline ack form per row — the three together identify a specific
    # alert instance for POST /api/alerts/ack.
    for r in _q(
        "SELECT first_seen_at AS at, kind, deal_id, trigger_key, "
        "title, severity "
        "FROM alert_history WHERE first_seen_at >= ? "
        "ORDER BY first_seen_at DESC LIMIT 10",
        (cutoff,),
    ):
        events.append({
            "at": r["at"] or "",
            "icon": "🔔",
            "kind": "alert",
            "label": f'{r["severity"].upper()}: {r["title"]}'[:80],
            "href": f"/deal/{r['deal_id']}" if r["deal_id"] else "/alerts",
            # Ack-form fields
            "alert_kind": r["kind"] or "",
            "alert_deal_id": r["deal_id"] or "",
            "alert_trigger_key": r["trigger_key"] or "",
        })

    # Data refreshes
    for r in _q(
        "SELECT last_refresh_at AS at, source_name, record_count, status "
        "FROM data_source_status WHERE last_refresh_at >= ? "
        "ORDER BY last_refresh_at DESC",
        (cutoff,),
    ):
        status = (r["status"] or "").lower()
        icon = "✓" if status in ("ok", "success") else "!"
        records = r["record_count"] or 0
        events.append({
            "at": r["at"] or "",
            "icon": icon,
            "kind": "refresh",
            "label": f"{r['source_name']} refreshed — {records:,} rows",
            "href": "/data/refresh",
        })

    # Packets built
    for r in _q(
        "SELECT created_at AS at, deal_id, model_version "
        "FROM analysis_runs WHERE created_at >= ? "
        "ORDER BY created_at DESC LIMIT 10",
        (cutoff,),
    ):
        events.append({
            "at": r["at"] or "",
            "icon": "📋",
            "kind": "packet",
            "label": f"Packet built for {r['deal_id']} "
                     f"(v{r['model_version']})"[:80],
            "href": f"/analysis/{r['deal_id']}",
        })

    # High-signal audit events only: logins, user management, exports
    high_signal_actions = (
        "login.success", "user.create", "user.delete",
        "backup.create", "deal.create", "deal.archive",
    )
    placeholders = ",".join("?" * len(high_signal_actions))
    for r in _q(
        f"SELECT at, actor, action, target FROM audit_events "
        f"WHERE at >= ? AND action IN ({placeholders}) "
        f"ORDER BY at DESC LIMIT 10",
        (cutoff, *high_signal_actions),
    ):
        action = r["action"] or ""
        if action == "login.success":
            icon, label = "→", f"{r['actor']} signed in"
        elif action.startswith("user."):
            icon = "👤"
            verb = action.split(".", 1)[1]
            label = f"{r['actor']} {verb}d user {r['target']}"[:80]
        elif action == "backup.create":
            icon, label = "💾", f"{r['actor']} ran a backup"
        elif action.startswith("deal."):
            icon = "📁"
            verb = action.split(".", 1)[1]
            label = f"{r['actor']} {verb}d deal {r['target']}"[:80]
        else:
            icon, label = "·", f"{r['actor']}: {action}"
        events.append({
            "at": r["at"] or "",
            "icon": icon,
            "kind": "audit",
            "label": label,
            "href": "",
        })

    # Newest first, capped
    events.sort(key=lambda e: e["at"] or "", reverse=True)
    return events[:20]


def _compute_sharpest_insight(db_path: str) -> Optional[Dict[str, Any]]:
    """Pick the single most-notable cross-portfolio signal to headline
    the dashboard. The "wow" moment on morning open.

    Ranks candidate insights by how surprising / actionable they are
    and returns the top one. Each insight has:
      - ``headline`` (≤ 100 chars, the number a partner would say out loud)
      - ``body`` (≤ 200 chars, the one-line "so what")
      - ``href`` (where to click to see the detail)
      - ``tone`` ("alert", "warn", "positive", "neutral")
      - ``kind`` (category key for the template)

    Returns None if nothing interesting — dashboard then omits the
    section (silence > noise).
    """
    try:
        from ..portfolio.store import PortfolioStore
        from .portfolio_risk_scan_page import _gather_per_deal
        store = PortfolioStore(db_path)
        deals = _gather_per_deal(db_path)
    except Exception:  # noqa: BLE001
        return None
    if not deals:
        return None

    insights: List[Dict[str, Any]] = []

    # Insight 1: Chain-concentration discovery. "You have N deals
    # in the same chain" — a partner may not realize how much
    # sector-weighted exposure they're running.
    chain_counts: Dict[str, List[Dict[str, Any]]] = {}
    for d in deals:
        c = (d.get("chain") or "").strip()
        if c:
            chain_counts.setdefault(c, []).append(d)
    for chain, members in chain_counts.items():
        if len(members) >= 2:
            names = ", ".join(m["name"] for m in members[:3])
            if len(members) > 3:
                names += f", +{len(members) - 3} more"
            insights.append({
                "headline": (
                    f"You have {len(members)} deals in the "
                    f"{chain} chain"
                ),
                "body": (
                    f"Same corporate parent → correlated covenant, "
                    f"sponsor, and regulatory exposure. "
                    f"Deals: {names}."
                ),
                "href": "/portfolio/risk-scan",
                "tone": "warn",
                "kind": "chain_concentration",
                "score": 40 + 10 * len(members),
            })

    # Insight 2: Covenant-tripped headline — the scariest signal.
    tripped = [d for d in deals
               if (d.get("covenant_status") or "").upper() == "TRIPPED"]
    if tripped:
        t = tripped[0]
        insights.append({
            "headline": (
                f"Covenant TRIPPED on {t['name']}"
            ),
            "body": (
                f"Deal {t['deal_id']} is over its leverage cap — "
                f"action today. "
                + (f"{len(tripped)-1} other deal{'s' if len(tripped) > 2 else ''} also tripped."
                   if len(tripped) > 1 else "")
            ),
            "href": f"/deal/{t['deal_id']}",
            "tone": "alert",
            "kind": "covenant_tripped",
            "score": 100,
        })

    # Insight 3: Stale-snapshot warning — the tool is rendering old
    # numbers. Partners should refresh before making a decision.
    stale = [d for d in deals
             if d.get("snap_age_days") is not None
             and d["snap_age_days"] > 30]
    if len(stale) >= 3:
        worst = max(stale, key=lambda x: x.get("snap_age_days") or 0)
        insights.append({
            "headline": (
                f"{len(stale)} deals haven't refreshed in over 30 days"
            ),
            "body": (
                f"Oldest: {worst['name']} "
                f"({worst['snap_age_days']}d stale). "
                f"Current numbers may be outdated."
            ),
            "href": "/data/refresh",
            "tone": "warn",
            "kind": "stale_portfolio",
            "score": 25 + len(stale) * 3,
        })

    # Insight 4: All-green reassurance — when nothing is firing,
    # say so. Partners appreciate a no-alarms morning read.
    no_flags = [d for d in deals
                if (d.get("alerts") or 0) == 0
                and (d.get("overdue_deadlines") or 0) == 0
                and (d.get("covenant_status") or "").upper()
                    not in ("TRIPPED", "TIGHT")]
    if len(deals) >= 3 and len(no_flags) == len(deals):
        insights.append({
            "headline": f"All {len(deals)} deals are healthy this morning",
            "body": (
                "No covenant breaks, no overdue deadlines, no open "
                "alerts. Great week to focus on the pipeline."
            ),
            "href": "/pipeline",
            "tone": "positive",
            "kind": "all_green",
            "score": 15,
        })

    # Insight 5: High-priority pileup — multiple deals at once.
    flagged = [d for d in deals
               if (d.get("alerts") or 0) > 0
               or (d.get("overdue_deadlines") or 0) > 0
               or (d.get("covenant_status") or "").upper() == "TRIPPED"]
    if len(flagged) >= 3 and len(deals) >= 5:
        pct = int(100 * len(flagged) / len(deals))
        insights.append({
            "headline": (
                f"{len(flagged)} of {len(deals)} deals "
                f"({pct}%) need attention"
            ),
            "body": (
                f"Worst deal: {flagged[0]['name']}. "
                f"See the portfolio risk scan for the full triage."
            ),
            "href": "/portfolio/risk-scan",
            "tone": "alert" if pct > 30 else "warn",
            "kind": "attention_pileup",
            "score": 30 + pct,
        })

    if not insights:
        return None
    insights.sort(key=lambda i: i.get("score", 0), reverse=True)
    return insights[0]


def _render_headline_insight_section(db_path: str) -> str:
    """One-glance insight card — the "wow" that justifies the morning
    visit. Rendered immediately after the header, before every other
    section, so it's the first thing a partner sees."""
    from . import _web_components as _wc
    ins = _compute_sharpest_insight(db_path)
    if ins is None:
        return ""

    # Tone-driven palette — alert is screaming red, positive is
    # affirming green, warn is attention-grabbing amber, neutral
    # is the brand navy.
    palette = {
        "alert":    ("#fef2f2", "#fee2e2", "#991b1b", "⚠"),
        "warn":     ("#fffbeb", "#fef3c7", "#92400e", "●"),
        "positive": ("#f0fdf4", "#d1fae5", "#065f46", "✓"),
        "neutral":  ("#f0f6fc", "#d0e3f0", "#1F4E78", "◆"),
    }
    bg, border, fg, icon = palette.get(
        ins.get("tone", "neutral"), palette["neutral"])
    href = ins.get("href") or "#"
    headline = _html.escape(ins.get("headline", ""))
    body = _html.escape(ins.get("body", ""))

    return (
        f'<a href="{_html.escape(href)}" '
        f'style="display:block;text-decoration:none;'
        f'margin:4px 0 16px;padding:18px 22px;background:{bg};'
        f'border:1px solid {border};border-left:4px solid {fg};'
        f'border-radius:8px;color:{fg};'
        f'transition:transform 0.1s, border-color 0.1s;" '
        f'onmouseover="this.style.transform=\'translateX(2px)\';" '
        f'onmouseout="this.style.transform=\'\';">'
        f'<div style="display:flex;align-items:baseline;gap:12px;">'
        f'<span style="font-size:20px;flex-shrink:0;">{icon}</span>'
        f'<div style="flex:1;">'
        f'<div style="font-size:10px;font-weight:600;'
        f'text-transform:uppercase;letter-spacing:0.08em;opacity:0.75;">'
        f'Sharpest insight · today</div>'
        f'<div style="font-size:18px;font-weight:600;'
        f'margin-top:4px;color:{fg};">{headline}</div>'
        f'<div style="font-size:13px;margin-top:6px;opacity:0.85;">'
        f'{body}</div>'
        f'</div>'
        f'<span style="flex-shrink:0;opacity:0.5;font-size:18px;">→</span>'
        f'</div></a>'
    )


def _render_since_yesterday_section(db_path: str) -> str:
    """One-screen "what changed since yesterday" roll-up.

    The differentiator vs. a static spreadsheet: a partner opens the
    tool and sees, without clicking, what happened while they were
    away. Alerts that fired overnight, data sources that refreshed,
    packets that ran, team activity — all chronological.
    """
    from . import _web_components as _wc

    events = _since_yesterday_events(db_path, window_hours=24)

    if not events:
        body = (
            '<p style="margin:0;color:#6b7280;">'
            'Nothing happened in the last 24 hours. '
            'When alerts fire, data refreshes, or a teammate runs a '
            'packet, the summary shows up here.</p>'
        )
        return _wc.section_card("Since yesterday", body, pad=True)

    rows: List[str] = []
    for ev in events:
        ts = _html.escape(str(ev.get("at", ""))[:19])
        icon = _html.escape(ev.get("icon", "·"))
        label = _html.escape(ev.get("label", ""))
        href = ev.get("href") or ""
        if href:
            label = (f'<a href="{_html.escape(href)}" '
                     f'style="color:#1F4E78;text-decoration:none;">'
                     f'{label}</a>')

        # Inline ack button for alert rows — one-click dismissal
        # without navigating away. CSRF auto-injected by the shell's
        # form-patching JS. Redirect back to /dashboard so the
        # user's scroll position + the other events are preserved.
        ack_form = ""
        if ev.get("kind") == "alert":
            k = _html.escape(ev.get("alert_kind") or "")
            d = _html.escape(ev.get("alert_deal_id") or "")
            t = _html.escape(ev.get("alert_trigger_key") or "")
            if k and d and t:
                ack_form = (
                    f'<form method="POST" action="/api/alerts/ack" '
                    f'style="flex-shrink:0;margin:0;" '
                    f'onsubmit="event.target.querySelector(\'button\')'
                    f'.disabled=true;">'
                    f'<input type="hidden" name="kind" value="{k}">'
                    f'<input type="hidden" name="deal_id" value="{d}">'
                    f'<input type="hidden" name="trigger_key" value="{t}">'
                    f'<input type="hidden" name="snooze_days" value="0">'
                    f'<input type="hidden" name="redirect" value="/dashboard">'
                    f'<button type="submit" title="Acknowledge alert" '
                    f'style="background:transparent;border:1px solid #d0e3f0;'
                    f'color:#1F4E78;padding:2px 10px;border-radius:4px;'
                    f'font-size:11px;cursor:pointer;font-weight:500;">'
                    f'Ack</button></form>'
                )

        rows.append(
            f'<li style="padding:6px 0;border-bottom:1px solid #f3f4f6;'
            f'display:flex;gap:10px;align-items:center;">'
            f'<span style="flex-shrink:0;font-size:14px;width:20px;">{icon}</span>'
            f'<span style="flex:1;color:#1f2937;">{label}</span>'
            f'{ack_form}'
            f'<span style="flex-shrink:0;color:#6b7280;font-size:11px;'
            f'font-family:monospace;white-space:nowrap;">{ts}</span>'
            f'</li>'
        )
    # Sort hint — the list is always newest-first, but without this
    # caption a partner may wonder whether it's oldest-first or some
    # priority ordering. 20-event cap also surfaced so they know
    # older-than-top might exist off-page.
    hint = (
        f'<p style="margin:0 0 10px;color:#6b7280;font-size:11px;">'
        f'{len(events)} event{"s" if len(events) != 1 else ""} · '
        f'newest first · past 24 hours'
        f'{" · older events in /audit" if len(events) >= 20 else ""}'
        f'</p>'
    )
    body = (
        hint
        + f'<ul style="list-style:none;padding:0;margin:0;'
        f'font-size:13px;">{"".join(rows)}</ul>'
    )
    return _wc.section_card("Since yesterday", body, pad=True)


def _sparkline_svg(scores: List[int], *,
                   width: int = 80, height: int = 20,
                   stroke: str = "#1F4E78") -> str:
    """Tiny inline SVG — one score per point, oldest-first.

    Returns empty string when there are <2 points (a single point
    isn't a trend). Scores are auto-normalized to the SVG viewport
    using the observed min/max of the series, so a deal bouncing
    between 70 and 75 uses the full chart height instead of looking
    flat against a 0-100 scale.

    Rendered as an inline SVG (no external request) so it lands
    with the page and stays cached with it.
    """
    if not scores or len(scores) < 2:
        return ""
    lo = min(scores)
    hi = max(scores)
    span = max(1, hi - lo)  # guard against flat line
    n = len(scores)
    pad_y = 2
    usable_h = height - 2 * pad_y

    points: List[str] = []
    for i, s in enumerate(scores):
        x = (i / (n - 1)) * width
        # Higher score should be higher on the chart — SVG y is
        # inverted, so normalized=0 is top, 1 is bottom; subtract
        # from 1 to flip.
        norm = (s - lo) / span
        y = pad_y + (1 - norm) * usable_h
        points.append(f"{x:.1f},{y:.1f}")
    polyline = " ".join(points)

    # Last-point marker shows where the trend ended
    last_x = (n - 1) / (n - 1) * width
    last_norm = (scores[-1] - lo) / span
    last_y = pad_y + (1 - last_norm) * usable_h

    return (
        f'<svg width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" '
        f'aria-label="Health score trend, {n} points" '
        f'style="vertical-align:middle;">'
        f'<polyline fill="none" stroke="{stroke}" stroke-width="1.5" '
        f'stroke-linejoin="round" stroke-linecap="round" '
        f'points="{polyline}"/>'
        f'<circle cx="{last_x:.1f}" cy="{last_y:.1f}" r="2" '
        f'fill="{stroke}"/>'
        f'</svg>'
    )


def _render_saved_templates_section(db_path: str) -> str:
    """Partner's own named shortcuts — one click to relaunch an
    analysis with the same params they used last time.

    Empty → render a one-line pitch ("Save analyses you run often to
    relaunch them in one click") + a "Save current" form below the
    curated analyses table. Non-empty → show up to 8 cards sorted
    pinned-first, then by most recent run.
    """
    from . import _web_components as _wc
    try:
        from ..portfolio.store import PortfolioStore
        from ..analysis.saved_analyses import list_templates, resolved_href
        store = PortfolioStore(db_path)
        templates = list_templates(store, limit=8)
    except Exception:  # noqa: BLE001
        return ""

    if not templates:
        return ""

    rows: List[str] = []
    for t in templates:
        href = resolved_href(t)
        run_count = t.get("run_count") or 0
        last_run = t.get("last_run_at") or "never run"
        desc = t.get("description") or ""
        name = t.get("name") or "unnamed"
        pinned_chip = (
            '<span style="margin-left:6px;font-size:10px;color:#1F4E78;">'
            '📌</span>'
        ) if t.get("pinned") else ""
        delete_form = (
            f'<form method="POST" action="/api/saved-analyses/'
            f'{t["id"]}/delete" style="display:inline;margin:0;" '
            f'onsubmit="return confirm(\'Delete template: '
            f'{_html.escape(name)}?\');">'
            f'<input type="hidden" name="redirect" value="/dashboard">'
            f'<button type="submit" title="Delete template" '
            f'style="background:transparent;border:0;color:#9ca3af;'
            f'cursor:pointer;font-size:14px;padding:0 4px;">×</button>'
            f'</form>'
        )
        rows.append(
            f'<li style="padding:8px 12px;border-bottom:1px solid #f3f4f6;'
            f'display:flex;align-items:center;gap:12px;">'
            f'<a href="/api/saved-analyses/{t["id"]}/run" '
            f'style="flex:1;color:#1f2937;text-decoration:none;" '
            f'title="Click to launch"'
            f' onclick="if(!event.metaKey&&!event.ctrlKey){{'
            f'fetch(this.href,{{method:\'POST\',credentials:\'same-origin\'}})'
            f'.then(()=>window.location=\'{_html.escape(href)}\');'
            f'event.preventDefault();}}">'
            f'<span style="font-weight:500;color:#1F4E78;">'
            f'{_html.escape(name)}</span>{pinned_chip}'
            f'<div style="font-size:11px;color:#6b7280;margin-top:2px;">'
            f'{_html.escape(desc) if desc else _html.escape(href)}'
            f' · ran {run_count}×</div>'
            f'</a>'
            f'{delete_form}'
            f'</li>'
        )
    body = (
        f'<ul style="list-style:none;padding:0;margin:0;">'
        f'{"".join(rows)}</ul>'
        f'<p style="margin:10px 0 0;font-size:11px;color:#6b7280;">'
        f'Click any template to launch — run count updates automatically. '
        f'<a href="/api/saved-analyses" style="color:#1F4E78;">API</a>'
        f'</p>'
    )
    return _wc.section_card(
        f"Your templates ({len(templates)})", body, pad=True,
    )


def _render_needs_attention_section(db_path: str) -> str:
    """Top-3 deals the risk scanner flagged as highest-priority.

    Complement to "Pinned deals" — Pinned shows deals the partner
    has *explicitly* starred; this card shows deals the TOOL has
    auto-flagged. A deal covenant-tripping overnight that the
    partner hasn't starred still surfaces here.

    The ranking uses the same `_priority_rank()` the risk-scan
    page uses, so the top item here is always the top row on
    /portfolio/risk-scan — consistent answers across surfaces.
    """
    from . import _web_components as _wc
    try:
        from .portfolio_risk_scan_page import (
            _gather_per_deal, _priority_rank,
        )
    except Exception:  # noqa: BLE001
        return ""

    try:
        deals = _gather_per_deal(db_path)
    except Exception:  # noqa: BLE001
        return ""

    if not deals:
        return ""  # no deals → no card (empty state covered elsewhere)

    # Filter to deals with ANY actionable signal — priority > 0
    # means at least one of the five risk factors is non-neutral.
    scored = [(d, _priority_rank(d)) for d in deals]
    scored = [(d, r) for d, r in scored if r > 0]
    if not scored:
        # Everything is healthy — render a one-line reassurance
        # instead of a card full of nothing.
        return _wc.section_card(
            "Needs attention today",
            '<p style="margin:0;color:#065f46;">'
            '✓ Everything looks healthy. No deals are flagging '
            'covenant, alert, or deadline risks right now.'
            '</p>',
        )

    scored.sort(key=lambda t: t[1], reverse=True)
    top = scored[:3]

    # One chip row per flagged deal — same visual language as the
    # risk-scan page so the partner doesn't have to translate.
    rows: List[str] = []
    for d, priority in top:
        # Build a compact "why" string — which factors are firing.
        reasons: List[str] = []
        cov = (d.get("covenant_status") or "").upper()
        if cov == "TRIPPED":
            reasons.append(
                '<span style="color:#991b1b;font-weight:600;">'
                'covenant TRIPPED</span>')
        elif cov == "TIGHT":
            reasons.append(
                '<span style="color:#92400e;">covenant TIGHT</span>')
        if (d.get("overdue_deadlines") or 0) > 0:
            reasons.append(
                f'<span style="color:#991b1b;">'
                f'{d["overdue_deadlines"]} overdue '
                f'deadline{"s" if d["overdue_deadlines"] != 1 else ""}</span>')
        if (d.get("alerts") or 0) > 0:
            reasons.append(
                f'<span style="color:#92400e;">'
                f'{d["alerts"]} open alert{"s" if d["alerts"] != 1 else ""}</span>')
        score = d.get("score")
        if isinstance(score, int) and score < 60:
            reasons.append(
                f'<span style="color:#92400e;">'
                f'health {score}</span>')
        if d.get("snap_age_days") is not None and d["snap_age_days"] > 30:
            reasons.append(
                f'<span style="color:#6b7280;">'
                f'snapshot {d["snap_age_days"]}d stale</span>')

        rows.append(
            f'<li style="padding:10px 0;border-bottom:1px solid #f3f4f6;'
            f'display:flex;align-items:center;gap:12px;">'
            f'<span style="flex-shrink:0;font-family:monospace;font-size:11px;'
            f'color:#6b7280;text-transform:uppercase;min-width:100px;">'
            f'{_html.escape(d["deal_id"])}</span>'
            f'<a href="/deal/{_html.escape(d["deal_id"])}" '
            f'style="flex:1;color:#1F4E78;font-weight:500;'
            f'text-decoration:none;">{_html.escape(d["name"])}</a>'
            f'<span style="flex-shrink:0;font-size:12px;'
            f'display:flex;flex-wrap:wrap;gap:12px;">'
            f'{" · ".join(reasons) if reasons else ""}</span>'
            f'</li>'
        )
    more_link = (
        f'<p style="margin:10px 0 0;font-size:12px;color:#6b7280;">'
        f'Showing top 3 of {len(scored)} deals with active risk flags. '
        f'See all on <a href="/portfolio/risk-scan" '
        f'style="color:#1F4E78;">Portfolio risk scan</a>.'
        f'</p>'
        if len(scored) > 3 else
        f'<p style="margin:10px 0 0;font-size:12px;color:#6b7280;">'
        f'Showing {len(scored)} deal{"s" if len(scored) != 1 else ""} '
        f'with active risk flags. See all on '
        f'<a href="/portfolio/risk-scan" '
        f'style="color:#1F4E78;">Portfolio risk scan</a>.'
        f'</p>'
    )
    body = (
        f'<ul style="list-style:none;padding:0;margin:0;">'
        f'{"".join(rows)}</ul>{more_link}'
    )
    return _wc.section_card(
        f"Needs attention today ({len(scored)})", body, pad=True,
    )


def _render_pinned_deals_section(db_path: str) -> str:
    """Morning glance at health scores for every deal the user has
    starred in the watchlist.

    Each deal renders as a compact card: score (color-coded by band),
    band label, top-contributing component (the single factor moving
    the score most). No card if the watchlist is empty — saves space
    for partners who haven't starred anything yet.

    Failures degrade silently: a deal that can't resolve (no snapshot,
    DB error during compute) is skipped rather than surfacing a
    traceback, since the section is a convenience view, not a
    critical workflow.
    """
    from . import _web_components as _wc
    try:
        from ..portfolio.store import PortfolioStore
        from ..deals.watchlist import list_starred
        from ..deals.health_score import compute_health
        store = PortfolioStore(db_path)
        starred = list_starred(store)
    except Exception:  # noqa: BLE001
        return ""  # no section at all — nothing to show

    if not starred:
        return ""

    # Colors per band — aligned with the existing severity palette.
    band_palette = {
        "excellent": ("#d1fae5", "#065f46"),
        "good":      ("#d1fae5", "#065f46"),
        "fair":      ("#fef3c7", "#92400e"),
        "poor":      ("#fee2e2", "#991b1b"),
        "critical":  ("#fee2e2", "#991b1b"),
        "unknown":   ("#f3f4f6", "#6b7280"),
    }

    try:
        from ..deals.health_score import history_series
    except Exception:  # noqa: BLE001
        history_series = None  # type: ignore[assignment]

    cards: List[str] = []
    # Cap at 12 so a partner with a big watchlist doesn't blow the
    # dashboard height — Daily workflow has the full list.
    for deal_id in starred[:12]:
        try:
            h = compute_health(store, deal_id)
        except Exception:  # noqa: BLE001
            continue
        score = h.get("score")
        band = (h.get("band") or "unknown").lower()
        components = h.get("components") or []
        bg, fg = band_palette.get(band, band_palette["unknown"])

        # Pick the single top-impact component (most negative) — that's
        # the "why" a partner wants to see at a glance.
        def _abs_impact(c: Dict[str, Any]) -> float:
            try:
                return abs(float(c.get("impact") or 0))
            except (TypeError, ValueError):
                return 0.0
        top = max(components, key=_abs_impact) if components else None
        reason = (_html.escape(str(top.get("label") or ""))
                  if top else "")

        # 90-day score trend — pulled from deal_health_history.
        # Silent no-op when the history table doesn't exist yet
        # (fresh deploy) or the deal has <2 snapshots.
        spark = ""
        if history_series is not None:
            try:
                series = history_series(store, deal_id, days=90)
                scores = [s for _, s in series if s is not None]
                if scores:
                    # Color the spark the same as the score chip —
                    # a tight visual tie between the number and the
                    # line.
                    spark_color = fg if band != "unknown" else "#6b7280"
                    spark = _sparkline_svg(scores, stroke=spark_color)
            except Exception:  # noqa: BLE001
                spark = ""

        score_str = str(score) if score is not None else "—"
        cards.append(
            f'<a href="/deal/{_html.escape(deal_id)}" '
            f'style="display:block;text-decoration:none;color:inherit;'
            f'background:#fff;border:1px solid #e5e7eb;border-radius:8px;'
            f'padding:10px 12px;min-width:160px;flex:1 1 160px;'
            f'transition:border-color 0.1s;">'
            f'<div style="display:flex;align-items:baseline;'
            f'justify-content:space-between;gap:6px;">'
            f'<span style="font-family:monospace;font-size:11px;'
            f'color:#6b7280;text-transform:uppercase;letter-spacing:0.03em;">'
            f'{_html.escape(deal_id)}</span>'
            f'<span style="padding:1px 8px;background:{bg};color:{fg};'
            f'border-radius:9999px;font-size:11px;font-weight:600;'
            f'font-variant-numeric:tabular-nums;">{score_str}</span>'
            f'</div>'
            f'<div style="display:flex;align-items:center;gap:8px;'
            f'margin-top:4px;">'
            f'<span style="flex:1;font-size:12px;color:#4b5563;'
            f'white-space:nowrap;overflow:hidden;'
            f'text-overflow:ellipsis;">{reason or "&nbsp;"}</span>'
            f'<span style="flex-shrink:0;">{spark}</span>'
            f'</div>'
            f'</a>'
        )

    if not cards:
        return ""

    body = (
        f'<div style="display:flex;flex-wrap:wrap;gap:8px;">'
        f'{"".join(cards)}</div>'
    )
    return _wc.section_card(
        f"Pinned deals ({len(cards)})", body, pad=True,
    )


def _render_workflow_shortcuts_section(db_path: str) -> str:
    """One-click hops into the partner's daily workflow surfaces.

    Each row links to a route that already exists in server.py and
    shows a live badge count where one is informative — alerts to
    triage, deadlines that have slipped, deals on your watchlist,
    saved filters waiting to be re-run. Counts come from the same
    DB the surfaces themselves read, so the dashboard never lies.
    """
    from . import _web_components as _wc
    counts = _workflow_badge_counts(db_path)

    overdue_lvl = ("alert" if (counts.get("overdue_deadlines") or 0) > 0
                   else "neutral")
    alert_lvl = ("warn" if (counts.get("alerts") or 0) > 0 else "neutral")

    items = [
        ("Portfolio risk scan",       "/portfolio/risk-scan",
         "One-screen scan — which deals need attention today, "
         "sorted highest-priority first. Start here on Monday.",
         ""),
        ("Pipeline & saved searches", "/pipeline",
         "Resume a saved filter or pin a new one for the morning sweep.",
         _badge(counts.get("saved_searches"))),
        ("Watchlist",                 "/watchlist",
         "Hospitals you've starred — see freshness + recent flag changes.",
         _badge(counts.get("watchlist"))),
        ("Active alerts",             "/alerts",
         "Fired alerts awaiting ack/snooze; returning-badges show "
         "snooze expirations.",
         _badge(counts.get("alerts"), level=alert_lvl)),
        ("My inbox",                  "/my/me",
         "Per-owner pulse: deals you own, deadlines you're on the hook for.",
         _badge(counts.get("overdue_deadlines"), level=overdue_lvl)),
        ("Team activity",             "/team",
         "Recent comments, reassignments, and IC checklist progress.",
         ""),
        ("LP quarterly update",       "/lp-update",
         "Fund-scope partner-ready HTML over the last 90 days.",
         ""),
        ("Notifications",             "/settings/integrations",
         "Email + Slack channels for alert digests and refresh status.",
         ""),
        ("Scheduled refreshes",       "/data/refresh",
         "Per-source freshness + on-demand background refresh.",
         ""),
    ]
    rows: List[List[str]] = []
    for label, href, desc, badge in items:
        rows.append([
            (f'<a href="{_html.escape(href)}" '
             f'style="color:#1F4E78;font-weight:500;">'
             f'{_html.escape(label)}</a>{badge}'),
            f'<span style="color:#6b7280;">{_html.escape(desc)}</span>',
        ])
    table = _wc.sortable_table(
        ["Open", "Why you'd come here today"], rows,
        id="dashboard-workflow",
        filterable=True, filter_placeholder="Filter workflow…",
    )
    return _wc.section_card("Daily workflow", table, pad=False)


def _render_recent_results_section(db_path: str) -> str:
    """Compose from in-process job queue (always safe) + optional run history."""
    from . import _web_components as _wc

    rows: List[List[str]] = []

    try:
        from ..infra.job_queue import get_default_registry
        reg = get_default_registry()
        jobs = reg.list_recent(n=5)
        for j in jobs:
            badge = {
                "done": '<span style="color:#10b981;">●</span> done',
                "running": '<span style="color:#f59e0b;">●</span> running',
                "queued": '<span style="color:#6b7280;">●</span> queued',
                "failed": '<span style="color:#ef4444;">●</span> failed',
            }.get(j.status, _html.escape(j.status))
            ts = _html.escape(j.created_at or "")
            job_id = _html.escape(j.job_id or "")
            kind = _html.escape(j.kind or "")
            rows.append([
                f'<code>{job_id[:8]}</code>',
                kind,
                badge,
                f'<span style="color:#6b7280;">{ts}</span>',
            ])
    except Exception:  # noqa: BLE001
        pass

    if not rows:
        body = (
            '<p style="margin:0 0 8px;"><strong>No runs yet — '
            'first time here?</strong> Try one of the curated analyses '
            'above. <a href="/diligence/thesis-pipeline?dataset=hospital_04_mixed_payer" '
            'style="color:#1F4E78;font-weight:500;">Thesis Pipeline</a> '
            'runs in ~170 ms on a fixture and walks you through 19 '
            'diligence steps end-to-end.</p>'
            '<p style="margin:0;color:#6b7280;font-size:12px;">'
            'Async jobs (data refresh, packet rebuild) appear here once '
            'submitted, with status badges that update automatically.</p>'
        )
    else:
        body = _wc.sortable_table(
            ["Job ID", "Kind", "Status", "Submitted (UTC)"],
            rows, id="dashboard-recent-runs", hide_columns_sm=[3],
        )
    return _wc.section_card("Recent runs", body, pad=(not rows))


def _render_system_status_section(db_path: str,
                                  started_at: Optional[datetime]) -> str:
    items: List[tuple[str, str, str]] = []  # (label, level, value)

    # Version
    try:
        from .. import __version__
        items.append(("Version", "ok", str(__version__)))
    except Exception:  # noqa: BLE001
        items.append(("Version", "never", "unknown"))

    # Uptime
    if started_at is not None:
        up = datetime.now(timezone.utc) - started_at
        hrs = up.total_seconds() / 3600.0
        items.append(("Uptime", "ok", f"{hrs:.1f} h"))
    else:
        items.append(("Uptime", "never", "—"))

    # DB reachable + migrations applied
    try:
        from ..infra import migrations
        from ..portfolio.store import PortfolioStore
        store = PortfolioStore(db_path)
        with store.connect() as con:
            con.execute("SELECT 1").fetchone()
        items.append(("DB", "ok", "reachable"))
        applied = migrations.list_applied(store)
        from ..infra.migrations import _MIGRATIONS
        total = len(_MIGRATIONS)
        if len(applied) >= total:
            items.append(("Migrations", "ok",
                          f"{len(applied)}/{total} applied"))
        else:
            items.append(("Migrations", "stale",
                          f"{len(applied)}/{total} applied"))
    except Exception as exc:  # noqa: BLE001
        items.append(("DB", "cold", f"error: {type(exc).__name__}"))

    # Job queue worker
    try:
        from ..infra.job_queue import get_default_registry
        reg = get_default_registry()
        if reg._worker_started.is_set():
            items.append(("Job worker", "ok", "running"))
        else:
            items.append(("Job worker", "stale", "idle (lazy-start)"))
    except Exception:  # noqa: BLE001
        items.append(("Job worker", "cold", "unavailable"))

    # PHI posture
    phi_mode = (os.environ.get("RCM_MC_PHI_MODE") or "unset").lower()
    phi_level = {"disallowed": "ok", "restricted": "stale",
                 "unset": "never"}.get(phi_mode, "never")
    items.append(("PHI mode", phi_level, phi_mode))

    from . import _web_components as _wc
    cards = []
    for label, level, value in items:
        cards.append(
            f'<div style="background:#f9fafb;border:1px solid #e5e7eb;'
            f'border-radius:6px;padding:10px 12px;min-width:140px;'
            f'flex:1 1 140px;">'
            f'<div style="font-size:11px;color:#6b7280;text-transform:uppercase;'
            f'letter-spacing:0.05em;">{_html.escape(label)}</div>'
            f'<div style="font-size:13px;color:#111;margin-top:4px;font-weight:500;">'
            f'{_dot(level)}{_html.escape(value)}</div>'
            f'</div>'
        )
    body = (
        '<div style="display:flex;flex-wrap:wrap;gap:10px;">'
        + "".join(cards) + '</div>'
    )
    return _wc.section_card("System status", body)


def _render_data_freshness_section(db_path: str) -> str:
    from . import _web_components as _wc

    try:
        from ..data.data_refresh import get_status
        from ..portfolio.store import PortfolioStore
        rows_data = get_status(PortfolioStore(db_path))
    except Exception as exc:  # noqa: BLE001
        return _wc.section_card(
            "Data freshness",
            f'<p>Status table unavailable '
            f'(<code>{_html.escape(type(exc).__name__)}</code>). '
            f'Run <code>rcm-mc data refresh</code> to populate, or open '
            f'<a href="/data/refresh" style="color:#1F4E78;">'
            f'Data refresh</a>.</p>',
        )

    if not rows_data:
        return _wc.section_card(
            "Data freshness",
            '<p>No data sources registered yet. Run a data refresh via the '
            '<code>rcm-mc data refresh</code> CLI or open '
            '<a href="/data/refresh" style="color:#1F4E78;">Data refresh</a> '
            'and click a Refresh button.</p>',
        )

    rows: List[List[str]] = []
    for r in rows_data:
        name = _html.escape(str(r.get("source_name", "—")))
        last = r.get("last_refreshed")
        level, label = _freshness_bucket(last)
        status = _html.escape(str(r.get("status", "—")))
        rows.append([
            name,
            f'{_dot(level)}{_html.escape(label)}',
            f'<span style="color:#6b7280;">{status}</span>',
        ])
    table = _wc.sortable_table(
        ["Source", "Last refreshed", "Status"], rows,
        id="dashboard-freshness",
    )
    return _wc.section_card("Data freshness", table, pad=False)


# ── Public entry point ─────────────────────────────────────────────

def render_dashboard(db_path: str, *,
                     started_at: Optional[datetime] = None) -> str:
    """Render the private-app landing page.

    Args:
        db_path: SQLite path; used for DB reachability, migrations, runs,
                 data-freshness lookups.
        started_at: Process start time (UTC) for uptime display. Falls
                    back to "—" if None.

    Returns:
        Full HTML page (passes through `chartis_shell` for consistent
        chrome + PHI banner).
    """
    from ._chartis_kit import chartis_shell
    from ._export_menu import export_menu
    from . import _web_components as _wc

    portfolio_exports = export_menu(
        "Download portfolio-scope exports",
        [
            ("Portfolio CSV",       "/api/export/portfolio.csv"),
            ("Data refresh panel",  "/data/refresh"),
            ("LP quarterly update", "/exports/lp-update?days=90"),
        ],
    )

    workflow_shortcuts = _render_workflow_shortcuts_section(db_path)

    header = _wc.page_header(
        "Dashboard",
        subtitle=('Private web app — curated analyses, recent runs, '
                  'system status, and data freshness in one view.'),
        crumbs=[("Dashboard", None)],
    )
    # Discoverability hint for the command palette — kbd tags need to
    # render as HTML, which page_header's subtitle escapes, so emit
    # this as a standalone strip below the header.
    cmdk_hint = (
        '<div class="wc-cmdk-hint-bar" style="margin:4px 0 16px;'
        'padding:8px 12px;background:#f0f6fc;border:1px solid #d0e3f0;'
        'border-radius:6px;font-size:12px;color:#1e40af;">'
        'Tip: press '
        '<kbd style="font-family:monospace;padding:1px 5px;background:#fff;'
        'color:#374151;border:1px solid #e5e7eb;border-radius:3px;'
        'font-size:11px;">⌘K</kbd> '
        '(or <kbd style="font-family:monospace;padding:1px 5px;'
        'background:#fff;color:#374151;border:1px solid #e5e7eb;'
        'border-radius:3px;font-size:11px;">Ctrl-K</kbd>) '
        'anywhere on this page to open the command palette — '
        'jump to a deal, open any page, or launch an analysis.'
        '</div>'
    )

    inner = (
        header
        + _render_headline_insight_section(db_path)
        + cmdk_hint
        + _render_since_yesterday_section(db_path)
        + _render_needs_attention_section(db_path)
        + _render_pinned_deals_section(db_path)
        + _render_saved_templates_section(db_path)
        + _render_analyses_section()
        + workflow_shortcuts
        + _render_recent_results_section(db_path)
        + _render_system_status_section(db_path, started_at)
        + _render_data_freshness_section(db_path)
        + portfolio_exports
    )
    # The Cmd-K palette is now injected globally by chartis_shell
    # via universal_palette_bundle() — every authenticated page on
    # the private web deployment has it. No dashboard-specific
    # wiring needed; removing the duplicate here keeps the DOM
    # free of two #wc-cmdk modals on the dashboard.
    body = (
        _wc.web_styles()
        + _wc.responsive_container(inner)
        + _wc.sortable_table_js()
        + _wc.spinner_js()
    )
    return chartis_shell(body, "Dashboard", active_nav="/dashboard")
