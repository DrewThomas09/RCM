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
        # Save-as-template form: pre-fills the name + route from
        # this row so the partner just clicks ★ to bookmark the
        # current parametrization. Wraps to /api/saved-analyses
        # POST → 303-redirect back to /dashboard.
        save_form = (
            f'<form method="POST" action="/api/saved-analyses" '
            f'style="display:inline;margin:0;" '
            f'onsubmit="var n=prompt(\'Save this analysis as template '
            f'— give it a name:\', \'{_html.escape(a["name"])}\');'
            f'if(!n){{return false;}}'
            f'this.querySelector(\'input[name=name]\').value=n;return true;">'
            f'<input type="hidden" name="name" value="">'
            f'<input type="hidden" name="route" '
            f'value="{_html.escape(a["route"])}">'
            f'<input type="hidden" name="description" '
            f'value="{_html.escape(a["desc"][:200])}">'
            f'<input type="hidden" name="redirect" value="/dashboard">'
            f'<button type="submit" '
            f'title="Save as template for one-click relaunch" '
            f'style="background:transparent;border:0;color:#9ca3af;'
            f'cursor:pointer;font-size:14px;padding:0;'
            f'transition:color 0.1s;" '
            f'onmouseover="this.style.color=\'#1F4E78\';" '
            f'onmouseout="this.style.color=\'#9ca3af\';">★</button>'
            f'</form>'
        )
        rows.append([
            (f'<a href="{_html.escape(a["route"])}" '
             f'style="color:#1F4E78;font-weight:500;">'
             f'{_html.escape(a["name"])}</a>'
             f'&nbsp;{save_form}'),
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
    return _wc.section_card(
        "What you can run", table, pad=False,
        actions_html=(
            '<span style="font-size:11px;color:#6b7280;'
            'font-weight:normal;">click ★ to save as template</span>'
        ),
    )


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


def _all_insights(
    db_path: str,
    *, deals: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Compute ALL candidate insights (not just the top-1).

    Used by the dashboard headline card (which picks #1) AND by
    the /insights full-page view (which renders the complete
    ranked list). Insights are returned sorted highest-score first;
    consumers can slice as needed.

    Each insight is a dict with:
      - ``kind`` (slug for templating)
      - ``headline`` (one-line attention-grabber, ≤ 100 chars)
      - ``body`` (one-line "so what", ≤ 200 chars)
      - ``href`` (drill-down URL)
      - ``tone`` ("alert" | "warn" | "positive" | "neutral")
      - ``score`` (priority for ranking — higher = more urgent)
    """
    if deals is None:
        try:
            from .portfolio_risk_scan_page import _gather_per_deal
            deals = _gather_per_deal(db_path)
        except Exception:  # noqa: BLE001
            return []
    if not deals:
        return []

    insights: List[Dict[str, Any]] = []
    insights.extend(_chain_concentration_insights(deals))
    insights.extend(_covenant_insights(deals))
    insights.extend(_health_distribution_insights(deals))
    insights.extend(_freshness_insights(deals))
    insights.extend(_attention_pileup_insights(deals))
    insights.extend(_geo_concentration_insights(deals))
    insights.extend(_sponsor_concentration_insights(db_path, deals))
    insights.extend(_low_quality_insights(deals))
    insights.extend(_hrrp_penalty_insights(deals))
    insights.extend(_quiet_morning_insights(deals))

    insights.sort(key=lambda i: i.get("score", 0), reverse=True)
    return insights


# ── Individual insight detectors ──────────────────────────────────
#
# Each returns 0+ insight dicts. Composing them in `_all_insights`
# lets us add new signals without touching the picking logic.

def _chain_concentration_insights(
    deals: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Multiple deals in the same CMS POS chain → correlated
    covenant + sponsor + regulatory exposure."""
    chain_counts: Dict[str, List[Dict[str, Any]]] = {}
    for d in deals:
        c = (d.get("chain") or "").strip()
        if c:
            chain_counts.setdefault(c, []).append(d)
    out: List[Dict[str, Any]] = []
    for chain, members in chain_counts.items():
        if len(members) >= 2:
            names = ", ".join(m["name"] for m in members[:3])
            if len(members) > 3:
                names += f", +{len(members) - 3} more"
            out.append({
                "kind": "chain_concentration",
                "headline": f"You have {len(members)} deals in the {chain} chain",
                "body": (f"Same corporate parent → correlated covenant, "
                         f"sponsor, and regulatory exposure. "
                         f"Deals: {names}."),
                "href": "/portfolio/risk-scan",
                "tone": "warn",
                "score": 40 + 10 * len(members),
            })
    return out


def _covenant_insights(
    deals: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """TRIPPED is the scariest signal; TIGHT pile-up is a quieter
    warning that 3+ deals are within 1 turn of breach."""
    out: List[Dict[str, Any]] = []
    tripped = [d for d in deals
               if (d.get("covenant_status") or "").upper() == "TRIPPED"]
    if tripped:
        t = tripped[0]
        rest = (
            f"{len(tripped)-1} other deal{'s' if len(tripped) > 2 else ''} also tripped."
            if len(tripped) > 1 else ""
        )
        out.append({
            "kind": "covenant_tripped",
            "headline": f"Covenant TRIPPED on {t['name']}",
            "body": (f"Deal {t['deal_id']} is over its leverage cap — "
                     f"action today. {rest}".strip()),
            "href": f"/deal/{t['deal_id']}",
            "tone": "alert",
            "score": 100,
        })
    tight = [d for d in deals
             if (d.get("covenant_status") or "").upper() == "TIGHT"]
    if len(tight) >= 3:
        names = ", ".join(d["name"] for d in tight[:3])
        out.append({
            "kind": "covenant_tight_pileup",
            "headline": f"{len(tight)} deals within 1 turn of covenant breach",
            "body": (f"Cluster of TIGHT-covenant deals: {names}. "
                     f"Run covenant-stress on each before any "
                     f"adverse-case shock lands."),
            "href": "/diligence/covenant-stress",
            "tone": "warn",
            "score": 50 + 5 * len(tight),
        })
    return out


def _health_distribution_insights(
    deals: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Worst-of-portfolio + median-shift signals."""
    out: List[Dict[str, Any]] = []
    scored = [d for d in deals if isinstance(d.get("score"), int)]
    if not scored:
        return out

    # Single worst deal — even if covenant is fine, a 25 health is
    # an "investigate today" signal.
    worst = min(scored, key=lambda d: d["score"])
    if worst["score"] < 40:
        out.append({
            "kind": "single_worst_deal",
            "headline": (f"{worst['name']} health score is "
                         f"{worst['score']} ({worst.get('band') or 'poor'})"),
            "body": (f"{worst['deal_id']} is the weakest deal in the "
                     f"portfolio — drill into the deal page to see "
                     f"which components are dragging the score."),
            "href": f"/deal/{worst['deal_id']}",
            "tone": "warn",
            "score": 35 + max(0, 40 - worst["score"]),
        })

    # Median check — if median < 60, the whole portfolio is shaky.
    sorted_scores = sorted(d["score"] for d in scored)
    median = sorted_scores[len(sorted_scores) // 2]
    if median < 60 and len(scored) >= 5:
        out.append({
            "kind": "median_health_low",
            "headline": (f"Median health score across {len(scored)} "
                         f"deals is {median}"),
            "body": ("Half the portfolio is below a 60 — the issue "
                     "isn't a single bad deal. Look for systemic "
                     "drivers (sector, payer mix, vintage)."),
            "href": "/portfolio/risk-scan",
            "tone": "warn",
            "score": 28 + (60 - median),
        })
    return out


def _freshness_insights(
    deals: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Stale snapshots → tool is rendering old numbers."""
    stale = [d for d in deals
             if d.get("snap_age_days") is not None
             and d["snap_age_days"] > 30]
    if len(stale) >= 3:
        worst = max(stale, key=lambda x: x.get("snap_age_days") or 0)
        return [{
            "kind": "stale_portfolio",
            "headline": (f"{len(stale)} deals haven't refreshed "
                         f"in over 30 days"),
            "body": (f"Oldest: {worst['name']} "
                     f"({worst['snap_age_days']}d stale). "
                     f"Current numbers may be outdated."),
            "href": "/data/refresh",
            "tone": "warn",
            "score": 25 + len(stale) * 3,
        }]
    return []


def _attention_pileup_insights(
    deals: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """When a meaningful share of the portfolio needs attention."""
    flagged = [d for d in deals
               if (d.get("alerts") or 0) > 0
               or (d.get("overdue_deadlines") or 0) > 0
               or (d.get("covenant_status") or "").upper() == "TRIPPED"]
    if len(flagged) >= 3 and len(deals) >= 5:
        pct = int(100 * len(flagged) / len(deals))
        return [{
            "kind": "attention_pileup",
            "headline": (f"{len(flagged)} of {len(deals)} deals "
                         f"({pct}%) need attention"),
            "body": (f"Worst deal: {flagged[0]['name']}. "
                     f"See the portfolio risk scan for the full triage."),
            "href": "/portfolio/risk-scan",
            "tone": "alert" if pct > 30 else "warn",
            "score": 30 + pct,
        }]
    return []


def _geo_concentration_insights(
    deals: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Single-state exposure ≥ 50% → state-policy / Medicaid-rate
    risk concentrated in one regulator's hands. Reads the state
    field from the CMS POS join (already in `deals` dicts via
    chain lookup; falls back to deal name parsing if absent)."""
    # State field isn't propagated through _gather_per_deal yet,
    # so we infer from the chain's POS row when available. This
    # is an approximation that improves once the per-deal POS row
    # is threaded through (separate refactor).
    out: List[Dict[str, Any]] = []
    # Skip for tiny portfolios — concentration math isn't meaningful.
    if len(deals) < 5:
        return out
    # We don't have state yet on the deal dicts; placeholder until
    # _gather_per_deal threads facility.state through.
    # Don't emit anything here for now — better to ship empty than
    # fake.
    return out


def _sponsor_concentration_insights(
    db_path: str,
    deals: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Multiple deals from the same sponsor → reputation risk +
    correlated diligence assumptions. Sponsor field comes from the
    deals table profile_json; uses a best-effort lookup."""
    import json as _json
    out: List[Dict[str, Any]] = []
    try:
        from ..portfolio.store import PortfolioStore
        store = PortfolioStore(db_path)
        sponsor_counts: Dict[str, List[str]] = {}
        with store.connect() as con:
            rows = con.execute(
                "SELECT deal_id, profile_json FROM deals "
                "WHERE archived_at IS NULL"
            ).fetchall()
        for r in rows:
            try:
                profile = _json.loads(r["profile_json"] or "{}")
            except (TypeError, _json.JSONDecodeError):
                continue
            sponsor = (profile.get("sponsor") or "").strip()
            if sponsor:
                sponsor_counts.setdefault(sponsor, []).append(r["deal_id"])
        for sponsor, dids in sponsor_counts.items():
            if len(dids) >= 3:
                out.append({
                    "kind": "sponsor_concentration",
                    "headline": (f"{len(dids)} deals from sponsor "
                                 f"{sponsor}"),
                    "body": ("Diligence on these deals is correlated — "
                             "if the sponsor's playbook fails on one, "
                             "expect it to fail on the others."),
                    "href": "/sponsor-league",
                    "tone": "warn",
                    "score": 30 + 5 * len(dids),
                })
    except Exception:  # noqa: BLE001 — best effort
        pass
    return out


def _low_quality_insights(
    deals: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """CMS Hospital General 5-star rating ≤2 → labor + revenue-cycle
    issues that flow straight into the EBITDA bridge. Cluster of
    these is a real PE concern."""
    low_rated = [d for d in deals
                 if isinstance(d.get("quality_rating"), int)
                 and d["quality_rating"] <= 2]
    if len(low_rated) >= 2:
        names = ", ".join(d["name"] for d in low_rated[:3])
        if len(low_rated) > 3:
            names += f", +{len(low_rated) - 3} more"
        return [{
            "kind": "low_quality_cluster",
            "headline": (f"{len(low_rated)} hospitals at CMS quality "
                         f"≤2 stars"),
            "body": (f"Low CMS rating means readmission penalties + "
                     f"labor friction + patient-experience drag. "
                     f"Deals: {names}."),
            "href": "/portfolio/risk-scan",
            "tone": "warn",
            "score": 35 + 8 * len(low_rated),
        }]
    return []


def _hrrp_penalty_insights(
    deals: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Hospitals carrying HRRP readmission penalties >2% have
    direct Medicare-revenue exposure: a 2% penalty on Medicare ≈
    60-80bps EBITDA hit on a typical hospital. Cluster of these
    is a real bridge-math concern."""
    high = [d for d in deals
            if isinstance(d.get("hrrp_pct"), (int, float))
            and d["hrrp_pct"] >= 2.0]
    if len(high) >= 2:
        names = ", ".join(d["name"] for d in high[:3])
        if len(high) > 3:
            names += f", +{len(high) - 3} more"
        worst_pct = max(d["hrrp_pct"] for d in high)
        return [{
            "kind": "hrrp_penalty_cluster",
            "headline": (f"{len(high)} hospitals carrying HRRP "
                         f"penalties ≥2%"),
            "body": (f"Worst: {worst_pct:.1f}% Medicare reduction. "
                     f"Each 1% HRRP penalty is ~30-40bps EBITDA "
                     f"on Medicare-heavy facilities. Deals: "
                     f"{names}."),
            "href": "/portfolio/risk-scan",
            "tone": "warn",
            "score": 32 + 8 * len(high),
        }]
    return []


def _quiet_morning_insights(
    deals: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """All-green reassurance — when nothing is firing, say so."""
    no_flags = [d for d in deals
                if (d.get("alerts") or 0) == 0
                and (d.get("overdue_deadlines") or 0) == 0
                and (d.get("covenant_status") or "").upper()
                    not in ("TRIPPED", "TIGHT")]
    if len(deals) >= 3 and len(no_flags) == len(deals):
        return [{
            "kind": "all_green",
            "headline": f"All {len(deals)} deals are healthy this morning",
            "body": ("No covenant breaks, no overdue deadlines, no open "
                     "alerts. Great week to focus on the pipeline."),
            "href": "/pipeline",
            "tone": "positive",
            "score": 15,
        }]
    return []


def _compute_sharpest_insight(
    db_path: str,
    *, deals: Optional[List[Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    """Top-ranked candidate — used by the dashboard headline card.
    See ``_all_insights`` for the full ranked list."""
    rows = _all_insights(db_path, deals=deals)
    return rows[0] if rows else None


def _portfolio_pulse_inputs(
    db_path: str,
    *, deals: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Crunch the numbers behind the Portfolio Pulse hero.

    Pulled out of the renderer so tests can assert on the maths
    without parsing HTML.

    Returns a dict with:
      n_deals, total_ev_mm, avg_health, band_counts (great/good/fair/poor),
      portfolio_moic_median + p25 + p75 (from corpus benchmarks),
      hrrp_exposure_mm (annualized $ EBITDA at risk from HRRP penalties),
      headline_synthesis (string — the surprise insight).
    """
    out: Dict[str, Any] = {
        "n_deals": 0,
        "total_ev_mm": 0.0,
        "avg_health": None,
        "band_counts": {"great": 0, "good": 0, "fair": 0, "poor": 0},
        "deal_tiles": [],          # [{deal_id, name, score, band}]
        "portfolio_moic_median": None,
        "portfolio_moic_p25": None,
        "portfolio_moic_p75": None,
        "hrrp_exposure_mm": 0.0,
        "n_hrrp_exposed": 0,
        "headline_synthesis": "",
    }

    rows: List[Dict[str, Any]] = list(deals or [])
    if not rows:
        return out

    out["n_deals"] = len(rows)

    # ── Per-deal profile lookup for EV ──────────────────────────
    profiles: Dict[str, Dict[str, Any]] = {}
    try:
        from ..portfolio.store import PortfolioStore
        import json as _json
        store = PortfolioStore(db_path)
        deal_ids = [d.get("deal_id") for d in rows if d.get("deal_id")]
        if deal_ids:
            with store.connect() as con:
                placeholders = ",".join("?" * len(deal_ids))
                for r in con.execute(
                    f"SELECT deal_id, profile_json FROM deals "
                    f"WHERE deal_id IN ({placeholders})",
                    deal_ids,
                ).fetchall():
                    try:
                        profiles[r["deal_id"]] = _json.loads(
                            r["profile_json"] or "{}")
                    except (TypeError, _json.JSONDecodeError):
                        profiles[r["deal_id"]] = {}
    except Exception:  # noqa: BLE001
        pass

    # HCRIS revenue → EV proxy fallback. Loaded once, used per deal.
    hcris_lookup = None
    try:
        from ..data.hcris import _get_latest_per_ccn
        hcris_lookup = _get_latest_per_ccn()
    except Exception:  # noqa: BLE001
        pass

    # ── Aggregate stats ─────────────────────────────────────────
    score_sum = 0
    score_n = 0
    deal_tiles: List[Dict[str, Any]] = []
    for d in rows:
        deal_id = d.get("deal_id") or ""
        score = d.get("score")
        band = d.get("band") or "unknown"
        if isinstance(score, (int, float)):
            score_sum += int(score)
            score_n += 1
        if band in out["band_counts"]:
            out["band_counts"][band] += 1
        deal_tiles.append({
            "deal_id": deal_id,
            "name": d.get("name") or deal_id,
            "score": score,
            "band": band,
        })

        # Total EV: explicit profile.ev_mm wins; HCRIS proxy second
        prof = profiles.get(deal_id, {})
        ev = prof.get("ev_mm")
        if ev is None and hcris_lookup is not None:
            try:
                if not hcris_lookup.empty:
                    h = hcris_lookup[hcris_lookup["ccn"] == deal_id]
                    if not h.empty:
                        rev = h.iloc[0].get("net_patient_revenue")
                        if rev and rev > 0:
                            ev = float(rev) / 1_000_000.0
            except Exception:  # noqa: BLE001
                pass
        if ev:
            try:
                out["total_ev_mm"] += float(ev)
            except (TypeError, ValueError):
                pass

        # HRRP exposure: penalty% × Medicare-IPPS-equivalent. We
        # use a lightweight proxy: 1% HRRP penalty ≈ 30bps of EBITDA
        # for a typical Medicare-heavy hospital. Anchor a $200M EV
        # deal to ~$20M EBITDA at 10% margin × 30bps × pct.
        # Resulting $ figure is in $M of *annualized* EBITDA at risk.
        hrrp = d.get("hrrp_pct")
        if hrrp and hrrp > 0:
            out["n_hrrp_exposed"] += 1
            ev_for_calc = ev or 200.0  # default proxy if unknown
            ebitda_proxy = ev_for_calc * 0.10
            out["hrrp_exposure_mm"] += (
                ebitda_proxy * 0.0030 * hrrp)

    if score_n > 0:
        out["avg_health"] = round(score_sum / score_n, 1)
    out["deal_tiles"] = deal_tiles

    # ── Portfolio-level predicted MOIC (corpus benchmark) ───────
    # Run benchmark_deal once per deal and aggregate the medians.
    # Bounded — only deals with enough profile signal participate.
    try:
        from ..diligence.comparable_outcomes import benchmark_deal
        from ..data_public.deals_corpus import DealsCorpus
        corpus = DealsCorpus(db_path)
        try:
            corpus.seed(skip_if_populated=True)
        except Exception:  # noqa: BLE001
            pass

        medians: List[float] = []
        for d in rows:
            deal_id = d.get("deal_id") or ""
            prof = profiles.get(deal_id, {})
            target = {
                "sector": d.get("sector") or prof.get("sector")
                          or "hospital",
                "ev_mm": prof.get("ev_mm"),
                "year": prof.get("entry_year") or prof.get("year"),
                "buyer": prof.get("sponsor") or prof.get("buyer") or "",
                "payer_mix": prof.get("payer_mix"),
            }
            try:
                res = benchmark_deal(corpus, target, top_n=10)
            except Exception:  # noqa: BLE001
                continue
            outcome = res.get("outcome_distribution", {})
            moic = outcome.get("moic", {})
            med = moic.get("median")
            if med is not None and outcome.get("n_comparables", 0) >= 3:
                medians.append(float(med))

        if medians:
            sorted_m = sorted(medians)
            n = len(sorted_m)
            out["portfolio_moic_median"] = round(
                sorted_m[n // 2], 2)
            # 25th/75th of the per-deal medians = portfolio dispersion
            out["portfolio_moic_p25"] = round(
                sorted_m[max(0, int(n * 0.25))], 2)
            out["portfolio_moic_p75"] = round(
                sorted_m[min(n - 1, int(n * 0.75))], 2)
    except Exception:  # noqa: BLE001
        pass

    # ── Surprise synthesis: pick the most striking aggregate ────
    # Priority order: HRRP $ exposure → covenant-tripped count →
    # health-band cluster → readiness affirmation.
    syn = ""
    if out["n_hrrp_exposed"] >= 2:
        syn = (
            f"{out['n_hrrp_exposed']} portfolio hospitals carry CMS "
            f"readmission penalties — combined ~"
            f"${out['hrrp_exposure_mm']:.1f}M EBITDA at risk this fiscal "
            f"year. Discount the bid book accordingly."
        )
    else:
        tripped = sum(1 for d in rows
                      if (d.get("covenant_status") or "").upper()
                      == "TRIPPED")
        if tripped >= 1:
            syn = (
                f"{tripped} deal{'s' if tripped != 1 else ''} have "
                f"TRIPPED covenants in the latest snapshot. Lender "
                f"calls land first — review the watchlist before the "
                f"morning standup."
            )
        elif (out["band_counts"]["poor"] + out["band_counts"]["fair"]
              >= max(2, len(rows) // 3)):
            n_below = (out["band_counts"]["poor"]
                       + out["band_counts"]["fair"])
            syn = (
                f"{n_below} of {len(rows)} deals scored fair-or-poor "
                f"on health. The portfolio's middle is widening — "
                f"prioritize ops time on the bottom-quartile names."
            )
        elif out["portfolio_moic_median"] is not None:
            syn = (
                f"Predicted exit MOIC across the portfolio: "
                f"{out['portfolio_moic_median']:.2f}x median, with "
                f"the comparable corpus suggesting {out['n_deals']} "
                f"deals are tracking inside the historical band."
            )
        else:
            syn = (
                f"Portfolio of {out['n_deals']} deals — "
                f"{out['band_counts']['great']} great, "
                f"{out['band_counts']['good']} good. Quiet morning. "
                f"Use it to chase the long-tail diligence asks."
            )
    out["headline_synthesis"] = syn

    return out


def _band_color(band: str) -> str:
    """Map health bands to the visual palette for the mosaic."""
    return {
        "great": "#10b981",
        "good":  "#3b82f6",
        "fair":  "#f59e0b",
        "poor":  "#ef4444",
    }.get(band or "unknown", "#9ca3af")


def _format_money_compact(mm: float) -> str:
    """`$1,840M` → `$1.84B`; `$320M` → `$320M`. Compact for the hero."""
    if mm is None:
        return "—"
    try:
        v = float(mm)
    except (TypeError, ValueError):
        return "—"
    if v >= 1000:
        return f"${v/1000:.2f}B"
    if v >= 1:
        return f"${v:.0f}M"
    return f"${v*1000:.0f}K"


def _render_portfolio_pulse_hero(
    db_path: str,
    *, deals: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """The wow-moment hero card. Sits at the very top of the
    dashboard and synthesizes:

      • Total deals + total EV (sum across portfolio profiles)
      • Average health + a per-deal mosaic (one colored tile per deal)
      • The most striking aggregate signal (HRRP $ exposure, covenant
        cluster, health-band cluster, or predicted MOIC)
      • Predicted portfolio-level exit MOIC distribution

    Designed so a partner who has never opened the tool sees a
    single screen that explains: how big the book is, how it's
    doing, and what to worry about — without clicking anywhere.
    """
    pulse = _portfolio_pulse_inputs(db_path, deals=deals)
    if pulse["n_deals"] == 0:
        return ""

    n = pulse["n_deals"]
    total_ev = _format_money_compact(pulse["total_ev_mm"])
    avg_health = (f"{int(round(pulse['avg_health']))}"
                  if pulse["avg_health"] is not None else "—")
    bands = pulse["band_counts"]

    # ── Mosaic: one colored square per deal ─────────────────────
    # Sorted high-to-low so the mosaic reads as a gradient — visual
    # cue for portfolio shape at a glance.
    tiles = sorted(
        pulse["deal_tiles"],
        key=lambda t: (t.get("score") or -1),
        reverse=True,
    )
    tile_html: List[str] = []
    for t in tiles[:80]:  # cap at 80 to keep DOM bounded
        c = _band_color(t.get("band") or "")
        deal_id = _html.escape(t.get("deal_id") or "")
        name = _html.escape(t.get("name") or "")
        score = t.get("score")
        score_str = f"{score}" if isinstance(score, (int, float)) else "—"
        tile_html.append(
            f'<a href="/deal/{deal_id}" '
            f'title="{name} — health {score_str}" '
            f'style="display:inline-block;width:18px;height:18px;'
            f'background:{c};border-radius:3px;'
            f'transition:transform 0.1s, box-shadow 0.1s;" '
            f'onmouseover="this.style.transform=\'scale(1.4)\';'
            f'this.style.boxShadow=\'0 4px 12px rgba(0,0,0,0.25)\';" '
            f'onmouseout="this.style.transform=\'\';'
            f'this.style.boxShadow=\'\';"></a>'
        )
    mosaic = (
        '<div style="display:flex;flex-wrap:wrap;gap:4px;'
        'margin-top:2px;line-height:0;">'
        + "".join(tile_html)
        + '</div>'
    )

    # ── MOIC strip ──────────────────────────────────────────────
    moic_med = pulse["portfolio_moic_median"]
    moic_p25 = pulse["portfolio_moic_p25"]
    moic_p75 = pulse["portfolio_moic_p75"]
    moic_strip = ""
    if moic_med is not None:
        bar = _moic_range_bar(moic_p25, moic_med, moic_p75,
                              width=300, height=22)
        moic_strip = (
            '<div style="display:flex;align-items:center;gap:14px;'
            'margin-top:14px;padding-top:12px;'
            'border-top:1px solid rgba(255,255,255,0.18);">'
            '<div style="font-size:10px;font-weight:600;'
            'text-transform:uppercase;letter-spacing:0.08em;'
            'color:#cbd5f5;flex-shrink:0;">'
            'Predicted exit MOIC<br/>(corpus)</div>'
            f'<div style="font-size:28px;font-weight:700;'
            f'color:#fff;font-variant-numeric:tabular-nums;'
            f'flex-shrink:0;">{moic_med:.2f}x</div>'
            f'<div style="background:#fff;padding:6px 10px;'
            f'border-radius:6px;flex-shrink:0;">{bar}</div>'
            f'<div style="font-size:11px;color:#cbd5f5;'
            f'font-variant-numeric:tabular-nums;">'
            f'p25 {moic_p25:.2f}x · p75 {moic_p75:.2f}x'
            f'</div></div>'
        )

    # ── Band-mosaic legend ──────────────────────────────────────
    legend_chip = (
        lambda c, label, n: (
            f'<span style="display:inline-flex;align-items:center;'
            f'gap:4px;font-size:11px;color:#cbd5f5;'
            f'font-variant-numeric:tabular-nums;">'
            f'<span style="display:inline-block;width:10px;'
            f'height:10px;background:{c};border-radius:2px;"></span>'
            f'{label} <strong style="color:#fff;">{n}</strong></span>'
        )
    )
    legend = (
        '<div style="display:flex;gap:14px;margin-top:8px;'
        'flex-wrap:wrap;">'
        + legend_chip("#10b981", "great", bands["great"])
        + legend_chip("#3b82f6", "good", bands["good"])
        + legend_chip("#f59e0b", "fair", bands["fair"])
        + legend_chip("#ef4444", "poor", bands["poor"])
        + '</div>'
    )

    # ── Stat tiles ──────────────────────────────────────────────
    def _stat(big: str, small: str) -> str:
        return (
            '<div style="flex:1;min-width:120px;">'
            f'<div style="font-size:32px;font-weight:700;color:#fff;'
            f'line-height:1;font-variant-numeric:tabular-nums;'
            f'letter-spacing:-0.02em;">{big}</div>'
            f'<div style="font-size:10px;font-weight:600;'
            f'text-transform:uppercase;letter-spacing:0.1em;'
            f'color:#cbd5f5;margin-top:6px;">{small}</div>'
            '</div>'
        )

    stats = (
        '<div style="display:flex;gap:24px;flex-wrap:wrap;'
        'margin-bottom:16px;">'
        + _stat(f"{n}", "deals")
        + _stat(total_ev, "total EV")
        + _stat(avg_health, "portfolio health")
        + '</div>'
    )

    # ── The synthesis line — the surprise the partner didn't ask for
    syn_text = _html.escape(pulse["headline_synthesis"])
    synthesis = (
        '<div style="background:rgba(255,255,255,0.08);'
        'border-left:3px solid #fbbf24;padding:12px 16px;'
        'border-radius:6px;margin:18px 0 0;">'
        '<div style="font-size:10px;font-weight:600;'
        'text-transform:uppercase;letter-spacing:0.1em;'
        'color:#fbbf24;margin-bottom:4px;">'
        'The synthesis you\'d miss</div>'
        f'<div style="font-size:14px;color:#fff;line-height:1.5;">'
        f'{syn_text}</div>'
        '</div>'
    )

    # ── Live indicator + label row ──────────────────────────────
    label_row = (
        '<div style="display:flex;align-items:center;'
        'justify-content:space-between;margin-bottom:14px;">'
        '<div style="font-size:11px;font-weight:700;'
        'text-transform:uppercase;letter-spacing:0.18em;color:#fff;">'
        'Portfolio pulse</div>'
        '<span style="display:inline-flex;align-items:center;gap:6px;'
        'font-size:10px;color:#86efac;font-weight:600;'
        'text-transform:uppercase;letter-spacing:0.12em;">'
        '<span class="wc-pulse-dot" style="display:inline-block;'
        'width:8px;height:8px;background:#22c55e;border-radius:50%;'
        'box-shadow:0 0 6px #22c55e;"></span> live</span>'
        '</div>'
    )

    pulse_anim = (
        '<style>'
        '@keyframes wc-pulse {'
        ' 0%,100% { opacity:1; transform:scale(1); }'
        ' 50% { opacity:0.55; transform:scale(0.85); } }'
        '.wc-pulse-dot { animation: wc-pulse 1.6s ease-in-out infinite; }'
        '</style>'
    )

    return (
        pulse_anim
        + '<section style="background:linear-gradient(135deg,'
        '#0f172a 0%,#1F4E78 100%);color:#fff;padding:22px 26px;'
        'border-radius:12px;margin:6px 0 18px;'
        'box-shadow:0 8px 24px rgba(15,23,42,0.18);">'
        + label_row
        + stats
        + '<div style="font-size:10px;font-weight:600;'
        'text-transform:uppercase;letter-spacing:0.08em;'
        'color:#cbd5f5;margin:8px 0 4px;">'
        'Deals (sorted by health, hover for name)</div>'
        + mosaic
        + legend
        + moic_strip
        + synthesis
        + '</section>'
    )


def _render_headline_insight_section(
    db_path: str,
    *, deals: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """One-glance insight card — the "wow" that justifies the morning
    visit. Rendered immediately after the header, before every other
    section, so it's the first thing a partner sees."""
    from . import _web_components as _wc
    all_ins = _all_insights(db_path, deals=deals)
    ins = all_ins[0] if all_ins else None
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

    # "See all N" link only appears when there are more than the
    # top-1 — otherwise we're nudging the partner at empty.
    extras = len(all_ins) - 1
    see_all = ""
    if extras > 0:
        see_all = (
            f'<div style="margin-top:8px;font-size:11px;color:{fg};'
            f'opacity:0.7;">'
            f'+ {extras} more signal{"s" if extras != 1 else ""} · '
            f'<a href="/insights" style="color:{fg};font-weight:500;">'
            f'see all →</a>'
            f'</div>'
        )
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
        f'{see_all}'
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

        # Inline ack + snooze controls for alert rows. Two
        # one-click options without leaving the dashboard:
        #   - Ack       (snooze_days=0, "I'm handling it")
        #   - Snooze 7d (snooze_days=7, "remind me in a week")
        # CSRF auto-injected by the shell's form-patching JS.
        # Both forms redirect back to /dashboard so the user's
        # scroll position + other events are preserved.
        ack_form = ""
        if ev.get("kind") == "alert":
            k = _html.escape(ev.get("alert_kind") or "")
            d = _html.escape(ev.get("alert_deal_id") or "")
            t = _html.escape(ev.get("alert_trigger_key") or "")
            if k and d and t:
                btn_style = (
                    "background:transparent;border:1px solid #d0e3f0;"
                    "color:#1F4E78;padding:2px 8px;border-radius:4px;"
                    "font-size:11px;cursor:pointer;font-weight:500;"
                )
                hidden = (
                    f'<input type="hidden" name="kind" value="{k}">'
                    f'<input type="hidden" name="deal_id" value="{d}">'
                    f'<input type="hidden" name="trigger_key" value="{t}">'
                    f'<input type="hidden" name="redirect" value="/dashboard">'
                )
                ack_form = (
                    f'<span style="flex-shrink:0;display:flex;gap:4px;">'
                    # Ack now (snooze_days=0)
                    f'<form method="POST" action="/api/alerts/ack" '
                    f'style="margin:0;" '
                    f'onsubmit="event.target.querySelector(\'button\')'
                    f'.disabled=true;">'
                    f'{hidden}'
                    f'<input type="hidden" name="snooze_days" value="0">'
                    f'<button type="submit" title="Acknowledge — handled" '
                    f'style="{btn_style}">Ack</button></form>'
                    # Snooze 7d (snooze_days=7) — partner says "I see
                    # this, but don't bother me about it for a week"
                    f'<form method="POST" action="/api/alerts/ack" '
                    f'style="margin:0;" '
                    f'onsubmit="event.target.querySelector(\'button\')'
                    f'.disabled=true;">'
                    f'{hidden}'
                    f'<input type="hidden" name="snooze_days" value="7">'
                    f'<button type="submit" '
                    f'title="Snooze for 7 days — remind me later" '
                    f'style="{btn_style}background:#fafbfc;">'
                    f'Snooze 7d</button></form>'
                    f'</span>'
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
        # Clone button — copy this template's route + params under a
        # new name so a partner can tweak (e.g. swap the CCN) without
        # rebuilding from scratch. Major time-saver for repeated
        # diligence on similar deals.
        clone_form = (
            f'<form method="POST" action="/api/saved-analyses/'
            f'{t["id"]}/clone" style="display:inline;margin:0;">'
            f'<input type="hidden" name="redirect" value="/dashboard">'
            f'<button type="submit" '
            f'title="Clone — duplicate this template under a new name '
            f'so you can tweak it (e.g. swap the CCN)" '
            f'style="background:transparent;border:0;color:#9ca3af;'
            f'cursor:pointer;font-size:14px;padding:0 6px;'
            f'transition:color 0.1s;" '
            f'onmouseover="this.style.color=\'#1F4E78\';" '
            f'onmouseout="this.style.color=\'#9ca3af\';">⎘</button>'
            f'</form>'
        )
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
            f'{clone_form}{delete_form}'
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


def _render_needs_attention_section(
    db_path: str,
    *, deals: Optional[List[Dict[str, Any]]] = None,
) -> str:
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
        from .portfolio_risk_scan_page import _priority_rank
    except Exception:  # noqa: BLE001
        return ""

    if deals is None:
        try:
            from .portfolio_risk_scan_page import _gather_per_deal
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


def _render_exposure_section(
    db_path: str,
    *, deals: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Sector + chain concentration at a glance.

    A partner with 12 deals should be able to read their portfolio
    composition without opening every deal. This card shows two
    breakdowns — sector and chain — as inline horizontal bars
    sorted by exposure.

    Skipped entirely on portfolios <= 1 deal (concentration math
    is meaningless on a single deal).
    """
    from . import _web_components as _wc
    if deals is None:
        try:
            from .portfolio_risk_scan_page import _gather_per_deal
            deals = _gather_per_deal(db_path)
        except Exception:  # noqa: BLE001
            return ""
    if not deals or len(deals) <= 1:
        return ""

    sector_counts: Dict[str, int] = {}
    chain_counts: Dict[str, int] = {}
    for d in deals:
        s = (d.get("sector") or "").strip() or "—"
        sector_counts[s] = sector_counts.get(s, 0) + 1
        c = (d.get("chain") or "").strip()
        if c:
            chain_counts[c] = chain_counts.get(c, 0) + 1

    total = len(deals)

    def _bar_chart(items: Dict[str, int], *, top_n: int = 6,
                   color: str = "#1F4E78") -> str:
        if not items:
            return (
                '<p style="margin:0;color:#9ca3af;font-size:12px;'
                'font-style:italic;">No data yet.</p>'
            )
        # Sort descending, cap at top_n, lump the rest into "Other"
        ranked = sorted(items.items(), key=lambda t: t[1], reverse=True)
        head = ranked[:top_n]
        tail = ranked[top_n:]
        if tail:
            head.append((f"Other ({len(tail)})", sum(v for _, v in tail)))

        rows: List[str] = []
        for label, count in head:
            pct = (count / total) * 100
            bar_w = int(round(pct))
            rows.append(
                f'<div style="display:grid;grid-template-columns:'
                f'140px 1fr 70px;align-items:center;gap:10px;'
                f'padding:4px 0;font-size:12px;">'
                f'<span style="color:#374151;white-space:nowrap;'
                f'overflow:hidden;text-overflow:ellipsis;" '
                f'title="{_html.escape(label)}">'
                f'{_html.escape(label)}</span>'
                f'<div style="background:#f3f4f6;border-radius:3px;'
                f'height:14px;overflow:hidden;">'
                f'<div style="background:{color};height:100%;'
                f'width:{bar_w}%;transition:width 0.2s;"></div></div>'
                f'<span style="color:#6b7280;font-variant-numeric:'
                f'tabular-nums;text-align:right;">'
                f'{count} · {pct:.0f}%</span></div>'
            )
        return "".join(rows)

    sector_block = (
        '<div style="font-size:11px;font-weight:600;color:#374151;'
        'text-transform:uppercase;letter-spacing:0.05em;margin-bottom:6px;">'
        'By sector</div>'
        + _bar_chart(sector_counts, color="#1F4E78")
    )
    chain_block = (
        '<div style="font-size:11px;font-weight:600;color:#374151;'
        'text-transform:uppercase;letter-spacing:0.05em;'
        'margin:14px 0 6px;">By chain '
        '<span style="font-weight:normal;color:#9ca3af;">'
        '— deals where CMS POS knows the parent</span></div>'
        + (_bar_chart(chain_counts, color="#92400e") if chain_counts
           else '<p style="margin:0;color:#9ca3af;font-size:12px;'
                'font-style:italic;">No chain-affiliated deals — '
                'either all independent or POS data not loaded.</p>')
    )
    body = sector_block + chain_block
    return _wc.section_card(
        f"Portfolio composition ({total} active deals)", body, pad=True,
    )


def _moic_range_bar(p25: Optional[float],
                    median: Optional[float],
                    p75: Optional[float],
                    *, scale_max: float = 6.0,
                    width: int = 200, height: int = 18) -> str:
    """Inline SVG horizontal range bar showing p25 - median - p75
    of predicted realized MOIC.

    Visual: a thin gray track from 0 to scale_max, an indigo whisker
    spanning p25-p75, a navy dot at the median, optional dashed line
    at 1.0x (cost of capital) and 2.5x (the partner's "good deal" bar).
    """
    if median is None:
        return ""
    p25 = p25 if p25 is not None else median
    p75 = p75 if p75 is not None else median

    def _x(v: float) -> float:
        return min(width, max(0, (v / scale_max) * width))

    cost_x = _x(1.0)
    bar_x = _x(2.5)
    p25_x = _x(p25)
    p75_x = _x(p75)
    med_x = _x(median)

    return (
        f'<svg width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" '
        f'aria-label="MOIC range chart" '
        f'style="vertical-align:middle;">'
        # Background track
        f'<rect x="0" y="{height/2 - 2}" width="{width}" height="4" '
        f'fill="#f3f4f6"/>'
        # 1.0x cost-of-capital reference line
        f'<line x1="{cost_x}" y1="2" x2="{cost_x}" y2="{height-2}" '
        f'stroke="#d1d5db" stroke-width="1" stroke-dasharray="2,2"/>'
        # 2.5x "good deal" reference line
        f'<line x1="{bar_x}" y1="2" x2="{bar_x}" y2="{height-2}" '
        f'stroke="#10b981" stroke-width="1" stroke-dasharray="2,2"/>'
        # p25-p75 whisker
        f'<rect x="{p25_x}" y="{height/2 - 4}" '
        f'width="{max(2, p75_x - p25_x)}" height="8" '
        f'fill="#1F4E78" opacity="0.35" rx="2"/>'
        # Median dot
        f'<circle cx="{med_x}" cy="{height/2}" r="4" '
        f'fill="#1F4E78" stroke="#fff" stroke-width="1.5"/>'
        f'</svg>'
    )


def _render_predicted_outcomes_section(
    db_path: str,
    *, deals_scan: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """For each pinned deal, predict an exit MOIC distribution by
    running it through the comparable-outcomes engine against the
    corpus of 600+ realized PE deals.

    The wow moment: a partner pinned DEAL_042 to track. Without
    asking for any analysis, the dashboard volunteers "your similar
    deals returned 2.3x median, 3.1x p75 at exit. Yours is on track."

    Compute is bounded — only runs for the partner's watchlisted
    deals (max 8) so the dashboard doesn't pay for 100 corpus
    scans on every render.
    """
    from . import _web_components as _wc
    try:
        from ..portfolio.store import PortfolioStore
        from ..deals.watchlist import list_starred
        from ..data_public.deals_corpus import DealsCorpus
        from ..diligence.comparable_outcomes import benchmark_deal
        store = PortfolioStore(db_path)
        starred = list_starred(store)
    except Exception:  # noqa: BLE001
        return ""

    if not starred:
        return ""

    # Cap at 8 — bounded compute, room for partners with deep watchlists
    starred = starred[:8]

    # Best-effort corpus seed so the prediction has data to chew on
    try:
        corpus = DealsCorpus(db_path)
        try:
            corpus.seed(skip_if_populated=True)
        except Exception:  # noqa: BLE001
            pass
    except Exception:  # noqa: BLE001
        return ""

    # Build a {deal_id → scan_row} map for sector + size lookup
    scan_by_id: Dict[str, Dict[str, Any]] = {}
    if deals_scan:
        scan_by_id = {d.get("deal_id", ""): d for d in deals_scan
                      if d.get("deal_id")}

    rows: List[str] = []
    any_prediction = False
    # Pull EV / payer-mix / sponsor from the deal's profile_json
    # in one query so each prediction can be deal-specific instead
    # of every starred deal getting the same hardcoded target.
    profiles_by_id: Dict[str, Dict[str, Any]] = {}
    try:
        import json as _json
        with store.connect() as con:
            for r in con.execute(
                "SELECT deal_id, profile_json FROM deals "
                "WHERE deal_id IN ({})".format(
                    ",".join("?" * len(starred))),
                starred,
            ).fetchall():
                try:
                    profiles_by_id[r["deal_id"]] = _json.loads(
                        r["profile_json"] or "{}")
                except (TypeError, _json.JSONDecodeError):
                    profiles_by_id[r["deal_id"]] = {}
    except Exception:  # noqa: BLE001
        pass

    # Cache HCRIS revenue → rough EV proxy (10x revenue is a typical
    # hospital multiple) when the profile doesn't carry an explicit EV.
    hcris_lookup = None
    try:
        from ..data.hcris import _get_latest_per_ccn
        hcris_lookup = _get_latest_per_ccn()
    except Exception:  # noqa: BLE001
        pass

    for deal_id in starred:
        scan_row = scan_by_id.get(deal_id, {})
        profile = profiles_by_id.get(deal_id, {})

        # Sector: prefer the scan row (already normalized), fall
        # back to profile, finally default to hospital.
        sector = (scan_row.get("sector")
                  or profile.get("sector")
                  or "hospital")

        # EV: explicit profile wins; HCRIS-derived proxy second;
        # None last (corpus matcher uses 0.5 neutral on None).
        ev_mm: Optional[float] = profile.get("ev_mm")
        if ev_mm is None and hcris_lookup is not None:
            try:
                if not hcris_lookup.empty:
                    h = hcris_lookup[hcris_lookup["ccn"] == deal_id]
                    if not h.empty:
                        rev = h.iloc[0].get("net_patient_revenue")
                        # Hospital EV / revenue typically 0.5-1.5x;
                        # use 1.0 as a middling proxy.
                        if rev and rev > 0:
                            ev_mm = float(rev) / 1_000_000.0
            except Exception:  # noqa: BLE001
                pass

        # Year: sponsor expects the analysis-year (default to current
        # so recency match favors recent comparables).
        year = profile.get("entry_year") or profile.get("year") or 2024

        # Buyer: helps the same-sponsor weight when the partner
        # tracks a sponsor's playbook
        buyer = (profile.get("sponsor") or profile.get("buyer") or "")

        # Payer mix: directly from profile if the deal was
        # registered with one, otherwise falls through to neutral.
        payer_mix = profile.get("payer_mix")

        target = {
            "sector": sector,
            "ev_mm": ev_mm,
            "year": year,
            "buyer": buyer,
            "payer_mix": payer_mix,
        }
        try:
            result = benchmark_deal(corpus, target, top_n=10)
        except Exception:  # noqa: BLE001
            continue
        outcome = result.get("outcome_distribution", {})
        moic = outcome.get("moic", {})
        median = moic.get("median")
        p25 = moic.get("p25")
        p75 = moic.get("p75")
        win_rate = outcome.get("win_rate_2_5x")
        n_comps = outcome.get("n_comparables", 0)

        if median is None or n_comps < 3:
            continue
        any_prediction = True

        bar = _moic_range_bar(p25, median, p75)
        win_pct = f"{int(win_rate * 100)}%" if win_rate else "—"
        name = scan_row.get("name") or deal_id

        # "See why" deep-link — preserves the EXACT target profile
        # used for the prediction so the comparable-outcomes page
        # shows the same comparable set. Partner clicks the median,
        # gets the full ranked match list with reasons.
        import urllib.parse as _urlparse
        comp_qs = _urlparse.urlencode(
            {k: v for k, v in {
                "sector": target.get("sector"),
                "ev_mm": target.get("ev_mm"),
                "year": target.get("year"),
                "buyer": target.get("buyer"),
            }.items() if v not in (None, "")},
        )
        comp_href = f"/diligence/comparable-outcomes?{comp_qs}"

        rows.append(
            f'<li style="padding:10px 0;border-bottom:1px solid #f3f4f6;'
            f'display:flex;align-items:center;gap:14px;">'
            f'<a href="/deal/{_html.escape(deal_id)}" '
            f'style="color:#1f2937;text-decoration:none;'
            f'min-width:160px;flex-shrink:0;">'
            f'<div style="font-weight:500;color:#1F4E78;font-size:13px;">'
            f'{_html.escape(name)}</div>'
            f'<div style="font-family:monospace;font-size:10px;'
            f'color:#6b7280;text-transform:uppercase;margin-top:2px;">'
            f'{_html.escape(deal_id)}</div></a>'
            f'<div style="flex-shrink:0;">{bar}</div>'
            f'<div style="flex:1;font-size:12px;color:#374151;'
            f'font-variant-numeric:tabular-nums;white-space:nowrap;">'
            f'<a href="{_html.escape(comp_href)}" '
            f'title="See the comparable deals that drove this prediction" '
            f'style="text-decoration:none;color:inherit;">'
            f'<span style="font-weight:600;color:#1F4E78;'
            f'font-size:14px;border-bottom:1px dotted #1F4E78;">'
            f'{median:.2f}x</span>'
            f'<span style="color:#6b7280;"> median · '
            f'p25 {p25:.2f}x · p75 {p75:.2f}x · '
            f'{win_pct} clear 2.5x</span>'
            f'</a></div>'
            f'</li>'
        )

    if not any_prediction:
        return ""

    legend = (
        '<div style="display:flex;align-items:center;gap:14px;'
        'font-size:11px;color:#6b7280;margin-bottom:10px;'
        'flex-wrap:wrap;">'
        '<span style="display:inline-flex;align-items:center;gap:5px;">'
        '<svg width="20" height="10" viewBox="0 0 20 10">'
        '<rect x="0" y="3" width="20" height="4" fill="#f3f4f6"/>'
        '<line x1="3" y1="0" x2="3" y2="10" stroke="#d1d5db" '
        'stroke-width="1" stroke-dasharray="2,2"/>'
        '<line x1="9" y1="0" x2="9" y2="10" stroke="#10b981" '
        'stroke-width="1" stroke-dasharray="2,2"/>'
        '</svg>scale 0–6×</span>'
        '<span style="display:inline-flex;align-items:center;gap:4px;">'
        '<span style="display:inline-block;width:14px;height:6px;'
        'background:#1F4E78;opacity:0.35;border-radius:2px;"></span>'
        'p25–p75 range</span>'
        '<span style="display:inline-flex;align-items:center;gap:4px;">'
        '<span style="display:inline-block;width:8px;height:8px;'
        'background:#1F4E78;border-radius:50%;border:1.5px solid #fff;'
        'box-shadow:0 0 0 1px #1F4E78;"></span>'
        'median predicted MOIC</span>'
        '<span style="color:#10b981;">— —</span>'
        '<span>2.5× "good deal" bar</span>'
        '</div>'
    )

    body = (
        '<p style="margin:0 0 10px;font-size:12px;color:#6b7280;">'
        'Predicted exit MOIC for each watchlisted deal, computed '
        'live by matching against the realized PE deals in the '
        'corpus.</p>'
        + legend
        + f'<ul style="list-style:none;padding:0;margin:0;">'
        f'{"".join(rows)}</ul>'
    )
    return _wc.section_card(
        f"Predicted exit outcomes ({len(rows)})", body, pad=True,
    )


def _render_quiet_too_long_section(db_path: str) -> str:
    """Surface deals that haven't been touched in too long — the
    inverse of "Needs attention". A deal you watchlisted 6 months
    ago but never opened might be the one needing your fresh eyes
    more than the one pinging you daily.

    Source: ``audit_events`` table — the same audit log that
    powers Since-yesterday. Looks for the most recent view event
    targeting each watchlisted deal; ranks by oldest-first.
    """
    from . import _web_components as _wc
    try:
        from ..portfolio.store import PortfolioStore
        from ..deals.watchlist import list_starred
        store = PortfolioStore(db_path)
        starred = list_starred(store)
    except Exception:  # noqa: BLE001
        return ""

    if not starred:
        return ""

    # Pull last-view timestamps for each starred deal in one pass.
    # The audit table doesn't always exist on a fresh install, so
    # this whole branch is best-effort.
    last_view_by_deal: Dict[str, Optional[str]] = {d: None for d in starred}
    try:
        import sqlite3 as _sql
        with _sql.connect(db_path) as con:
            con.row_factory = _sql.Row
            # Check the table exists first (lazy-created elsewhere)
            tbl = con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name='audit_events'",
            ).fetchone()
            if tbl is None:
                return ""
            placeholders = ",".join("?" * len(starred))
            for row in con.execute(
                f"SELECT target, MAX(at) AS last_at FROM audit_events "
                f"WHERE target IN ({placeholders}) "
                f"GROUP BY target",
                starred,
            ).fetchall():
                last_view_by_deal[row["target"]] = row["last_at"]
    except Exception:  # noqa: BLE001
        return ""

    # Rank quiet-first: never-viewed comes first, then oldest, then
    # newest. Cap at 4 — this is a complement to Pinned, not a
    # replacement.
    from datetime import datetime as _dt, timezone as _tz
    now = _dt.now(_tz.utc)

    def _days_since(iso: Optional[str]) -> Optional[int]:
        if not iso:
            return None
        try:
            ts = _dt.fromisoformat(str(iso).replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=_tz.utc)
            return (now - ts).days
        except (TypeError, ValueError):
            return None

    enriched: List[Dict[str, Any]] = []
    for did in starred:
        last = last_view_by_deal.get(did)
        days = _days_since(last)
        # Only surface deals that are actually "quiet" (unseen >14d,
        # or never viewed). A deal viewed yesterday isn't quiet.
        if days is not None and days < 14:
            continue
        enriched.append({
            "deal_id": did,
            "last_view_iso": last,
            "days_quiet": days,  # None = never viewed
        })

    if not enriched:
        return ""

    # Never-viewed first (sentinel: -1 sorts before all positive
    # day counts when reversed); then by days_quiet descending
    enriched.sort(
        key=lambda d: (-1 if d["days_quiet"] is None else d["days_quiet"]),
        reverse=True,
    )
    rows: List[str] = []
    for d in enriched[:4]:
        days = d["days_quiet"]
        if days is None:
            quiet_label = "never viewed"
            tone = "#fee2e2"
            fg = "#991b1b"
        elif days >= 60:
            quiet_label = f"{days}d quiet"
            tone, fg = "#fee2e2", "#991b1b"
        elif days >= 30:
            quiet_label = f"{days}d quiet"
            tone, fg = "#fef3c7", "#92400e"
        else:
            quiet_label = f"{days}d quiet"
            tone, fg = "#e0e7ff", "#3730a3"
        rows.append(
            f'<li style="padding:8px 0;border-bottom:1px solid #f3f4f6;'
            f'display:flex;align-items:center;gap:14px;">'
            f'<a href="/deal/{_html.escape(d["deal_id"])}" '
            f'style="flex:1;color:#1F4E78;font-weight:500;'
            f'text-decoration:none;font-family:monospace;font-size:12px;'
            f'text-transform:uppercase;letter-spacing:0.03em;">'
            f'{_html.escape(d["deal_id"])}</a>'
            f'<span style="display:inline-block;padding:1px 8px;'
            f'background:{tone};color:{fg};border-radius:9999px;'
            f'font-size:11px;font-weight:600;">'
            f'{quiet_label}</span>'
            f'</li>'
        )
    body = (
        '<p style="margin:0 0 8px;font-size:12px;color:#6b7280;">'
        'Watchlisted deals you haven\'t opened in a while. The '
        'one nobody is yelling at might need your fresh eyes more '
        'than the one pinging you daily.</p>'
        + f'<ul style="list-style:none;padding:0;margin:0;">'
        f'{"".join(rows)}</ul>'
    )
    return _wc.section_card(
        f"Quiet too long ({len(enriched)})", body, pad=True,
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

    # Compute the per-deal scan ONCE per dashboard render and thread
    # it through every section that needs it. Without this, three
    # separate sections (headline-insight, needs-attention, exposure)
    # each call _gather_per_deal independently, multiplying
    # compute_health and POS lookups by 3× on every page load.
    deals_scan: Optional[List[Dict[str, Any]]] = None
    try:
        from .portfolio_risk_scan_page import _gather_per_deal
        deals_scan = _gather_per_deal(db_path)
    except Exception:  # noqa: BLE001
        deals_scan = None

    inner = (
        header
        + _render_portfolio_pulse_hero(db_path, deals=deals_scan)
        + _render_headline_insight_section(db_path, deals=deals_scan)
        + cmdk_hint
        + _render_since_yesterday_section(db_path)
        + _render_needs_attention_section(db_path, deals=deals_scan)
        + _render_exposure_section(db_path, deals=deals_scan)
        + _render_pinned_deals_section(db_path)
        + _render_quiet_too_long_section(db_path)
        + _render_predicted_outcomes_section(db_path, deals_scan=deals_scan)
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
