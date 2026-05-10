"""Dashboard v3 — story-driven morning view.

Replaces the wall-of-widgets v2 layout with a narrative read:

  1. **Portfolio health at a glance** — hero strip with the
     headline numbers + a one-sentence read on overall posture.
  2. **Top opportunities** — ranked deals with biggest realistic
     EBITDA uplift potential, prose-introduced.
  3. **Key alerts** — what needs the partner's decision today,
     not 'every covenant trigger ever'.
  4. **Recent activity** — what changed since the last open
     (new packets, completed runs, regime changes).

Each section opens with a sentence framing the numbers — partner
reads top-to-bottom and gets the story, not a dashboard quiz.

Public API::

    render_dashboard_v3(store) -> str
"""
from __future__ import annotations

import html as _html
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from ._chartis_kit import (
    ck_kpi_block, ck_panel, ck_section_intro, ck_signal_badge,
)

# Editorial port (2026-04-27): dropped imports for .colors / .loading /
# .nav / .responsive / .theme — chartis_shell() now provides all the
# editorial chrome + responsive layout + theme cascade. The .global_search
# render_search_bar dropped too — chartis_shell's editorial topbar
# already includes the editorial server-rendered search input.

logger = logging.getLogger(__name__)


def _esc(s: Any) -> str:
    return _html.escape("" if s is None else str(s))


def _fmt_money(v: Optional[float]) -> str:
    if v is None:
        return "—"
    if abs(v) >= 1e9:
        return f"${v / 1e9:,.2f}B"
    if abs(v) >= 1e6:
        return f"${v / 1e6:,.1f}M"
    if abs(v) >= 1e3:
        return f"${v / 1e3:,.0f}K"
    return f"${v:,.0f}"


def _fmt_pct(v: Optional[float], digits: int = 1) -> str:
    if v is None:
        return "—"
    return f"{v * 100:+.{digits}f}%"


def _days_since(iso: Optional[str]) -> Optional[int]:
    if not iso:
        return None
    try:
        ts = datetime.fromisoformat(
            iso.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return (datetime.now(timezone.utc) - ts).days


# ── Data assembly ────────────────────────────────────────────

def _load_portfolio_summary(
    store: Any,
) -> Dict[str, Any]:
    """Headline numbers for the hero strip."""
    summary = {
        "n_deals": 0, "n_active": 0, "n_archived": 0,
        "total_npr": 0.0, "total_ebitda": 0.0,
        "weighted_health": None,
        "best_regime": "—", "best_deal": "—",
        "worst_regime": "—", "worst_deal": "—",
    }
    try:
        deals = store.list_deals(include_archived=True)
        summary["n_deals"] = len(deals)
        if "archived" in deals.columns:
            summary["n_active"] = int(
                (~deals["archived"].astype(bool)).sum())
            summary["n_archived"] = (
                summary["n_deals"] - summary["n_active"])
        else:
            summary["n_active"] = summary["n_deals"]
    except Exception as exc:  # noqa: BLE001
        logger.debug(
            "list_deals failed: %s", exc)
    try:
        from ..analysis.analysis_store import (
            list_packets, load_packet_by_id,
        )
        rows = list_packets(store) or []
        seen = set()
        npr = 0.0
        ebitda = 0.0
        health_w = 0.0
        health_total = 0.0
        for r in rows:
            did = r.get("deal_id")
            if did in seen:
                continue
            seen.add(did)
            pkt = load_packet_by_id(store, r["id"])
            if pkt is None:
                continue
            try:
                this_npr = float(getattr(
                    pkt.financials, "net_revenue",
                    0) or 0)
                this_ebitda = float(getattr(
                    pkt.financials, "current_ebitda",
                    0) or 0)
                npr += this_npr
                ebitda += this_ebitda
                hs = getattr(
                    pkt, "health_score", None)
                if hs is not None:
                    health_w += this_npr * float(hs)
                    health_total += this_npr
            except Exception:  # noqa: BLE001
                continue
        summary["total_npr"] = npr
        summary["total_ebitda"] = ebitda
        if health_total > 0:
            summary["weighted_health"] = (
                health_w / health_total)
    except Exception as exc:  # noqa: BLE001
        logger.debug(
            "packet rollup failed: %s", exc)
    return summary


def _load_top_opportunities(
    store: Any, *, limit: int = 5,
) -> List[Dict[str, Any]]:
    """Deals ranked by realistic EBITDA uplift potential."""
    out: List[Dict[str, Any]] = []
    try:
        from ..analysis.analysis_store import (
            list_packets, load_packet_by_id,
        )
        rows = list_packets(store) or []
        seen = set()
        for r in rows:
            did = r.get("deal_id")
            if did in seen:
                continue
            seen.add(did)
            pkt = load_packet_by_id(store, r["id"])
            if pkt is None:
                continue
            try:
                bridge = getattr(
                    pkt, "ebitda_bridge", None)
                if bridge is None:
                    continue
                uplift = float(getattr(
                    bridge, "total_ebitda_impact", 0)
                    or 0)
                if uplift <= 0:
                    continue
                out.append({
                    "deal_id": did,
                    "uplift": uplift,
                    "current_ebitda": float(getattr(
                        bridge, "current_ebitda", 0)
                        or 0),
                    "target_ebitda": float(getattr(
                        bridge, "target_ebitda", 0)
                        or 0),
                    "uplift_pct": float(getattr(
                        bridge, "ebitda_delta_pct", 0)
                        or 0),
                })
            except Exception:  # noqa: BLE001
                continue
    except Exception as exc:  # noqa: BLE001
        logger.debug(
            "opportunities scan failed: %s", exc)
    out.sort(key=lambda x: -x["uplift"])
    return out[:limit]


def _load_alerts(
    store: Any, *, limit: int = 8,
) -> List[Dict[str, Any]]:
    """Active alerts that need the partner's decision."""
    try:
        from ..alerts.alerts import evaluate_active
        alerts = evaluate_active(store) or []
    except Exception as exc:  # noqa: BLE001
        logger.debug(
            "alerts eval failed: %s", exc)
        return []
    out = []
    for a in alerts[:limit]:
        out.append({
            "deal_id": getattr(a, "deal_id", "—"),
            "kind": getattr(a, "kind", "—"),
            "severity": getattr(a, "severity", "info"),
            "message": getattr(a, "message", ""),
        })
    return out


def _load_recent_activity(
    store: Any, *, limit: int = 8, lookback_days: int = 7,
) -> List[Dict[str, Any]]:
    """Recent packet builds, runs, snapshots — what's changed
    since the partner last opened the platform."""
    out: List[Dict[str, Any]] = []
    try:
        from ..analysis.analysis_store import list_packets
        rows = list_packets(store) or []
        for r in rows[:30]:
            did = r.get("deal_id") or "—"
            ts = r.get("created_at") or r.get(
                "timestamp")
            days = _days_since(ts)
            if days is None or days > lookback_days:
                continue
            out.append({
                "deal_id": did,
                "kind": "packet_built",
                "label": (f"Analysis packet built "
                          f"({days}d ago)"
                          if days > 0 else
                          "Analysis packet built (today)"),
                "days": days,
            })
    except Exception:  # noqa: BLE001
        pass
    out.sort(key=lambda x: x["days"])
    return out[:limit]


# ── Section renderers ───────────────────────────────────────

# Editorial port (2026-04-27): dark-shell palette → editorial palette
# Same mapping as deal_profile_v2.py port (b283a04).
_BG_PRIMARY = "#FFFFFF"   # was #0f172a → paper-pure
_BG_SURFACE = "#FFFFFF"   # was #1f2937 → paper-pure
_BG_ELEVATED = "#FAF7F0"  # was #111827 → paper
_BORDER = "#D6CFC0"       # was #374151 → editorial border
_TEXT = "#0F1C2E"         # was #f3f4f6 → ink (dark on light)
_TEXT_DIM = "#5C6878"     # was STATUS["neutral"] → muted
_ACCENT = "#155752"       # was STATUS["info"] → teal-deep
_GREEN = "#3F7D4D"        # editorial green
_AMBER = "#B7791F"        # editorial amber
_RED = "#A53A2D"          # editorial red


def _hero_strip(summary: Dict[str, Any]) -> str:
    """Top-of-page hero with the headline numbers + one-sentence read."""
    n_deals = summary["n_deals"]
    n_active = summary["n_active"]
    npr = summary["total_npr"]
    ebitda = summary["total_ebitda"]
    health = summary["weighted_health"]

    # One-sentence narrative read
    if n_deals == 0:
        narrative = (
            "No deals in the portfolio yet — start by "
            "uploading a deal or building an analysis packet.")
    elif health is None:
        narrative = (
            f"{n_active} active deal"
            f"{'s' if n_active != 1 else ''} representing "
            f"{_fmt_money(npr)} NPR. Health scores not yet "
            f"computed — build packets to populate.")
    elif health >= 75:
        narrative = (
            f"{n_active} active deals at {health:.0f}/100 "
            f"weighted health — the portfolio is in good "
            f"shape; focus on growth plays.")
    elif health >= 60:
        narrative = (
            f"{n_active} active deals at {health:.0f}/100 "
            f"weighted health — mid-tier; one or two "
            f"underperformers are pulling the average down.")
    else:
        narrative = (
            f"{n_active} active deals at {health:.0f}/100 "
            f"weighted health — material drag, "
            f"restructuring conversations needed.")

    health_text = (f"{health:.0f}" if health is not None
                   else "—")
    health_tone = (
        "positive" if (health or 0) >= 75
        else "warning" if (health or 0) >= 60
        else "negative")
    health_badge = ck_signal_badge(health_text, tone=health_tone)

    intro = ck_section_intro(
        eyebrow="MORNING VIEW",
        headline="Where the portfolio stands today.",
        italic_word="today",
        body=narrative,
    )
    kpis = (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block(
            "Active deals", f"{n_active}",
            sub=f"of {n_deals} total",
        )
        + ck_kpi_block("Total NPR", _fmt_money(npr))
        + ck_kpi_block("Current EBITDA", _fmt_money(ebitda))
        + ck_kpi_block(
            "Health score", health_badge,
            sub="weighted by NPR",
        )
        + '</div>'
    )
    return f'{intro}{kpis}'


def _section_header(label: str, prose: str) -> str:
    """No-op kept for back-compat; sections now ride ck_panel."""
    return ""


def _opportunities_section(
    opps: List[Dict[str, Any]],
) -> str:
    if not opps:
        return ck_panel(
            '<p class="ck-section-body">'
            'No realized EBITDA uplift opportunities yet — '
            'build analysis packets to populate this list.</p>',
            title="Top opportunities",
        )

    total_uplift = sum(o["uplift"] for o in opps)
    rows = []
    for i, opp in enumerate(opps, 1):
        deal_link = (
            f'<a href="/deal/{_esc(opp["deal_id"])}" class="ck-link"><strong>{_esc(opp["deal_id"])}</strong></a>')
        rows.append(
            f'<tr>'
            f'<td class="num">{i}.</td>'
            f'<td>{deal_link}</td>'
            f'<td class="num cad-pos"><strong>+{_fmt_money(opp["uplift"])}</strong></td>'
            f'<td class="num">{_fmt_pct(opp["uplift_pct"])}</td>'
            f'<td class="num">{_fmt_money(opp["current_ebitda"])} → {_fmt_money(opp["target_ebitda"])}</td>'
            f'</tr>')
    prose = (
        f"Ranked by realistic EBITDA uplift across the active "
        f"portfolio. The top {len(opps)} represent "
        f"{_fmt_money(total_uplift)} in additional EBITDA if "
        f"value-creation plans land — start with the biggest "
        f"and work down.")
    return ck_panel(
        f'<p class="ck-section-body">{prose}</p>'
        '<table class="cad-table">'
        '<thead><tr>'
        '<th>#</th><th>Deal</th>'
        '<th class="num">EBITDA Uplift</th>'
        '<th class="num">vs. Current</th>'
        '<th class="num">Bridge</th>'
        '</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table>',
        title="Top opportunities",
    )


def _alerts_section(
    alerts: List[Dict[str, Any]],
) -> str:
    if not alerts:
        return ck_panel(
            '<p class="ck-section-body cad-pos">All clear.</p>',
            title="Key alerts",
        )
    n_critical = sum(1 for a in alerts
                     if str(a.get("severity")
                            ).lower()
                     in ("critical", "high"))
    sev_tone_map = {
        "critical": "negative", "high": "negative",
        "medium": "warning", "warning": "warning",
        "low": "neutral", "info": "neutral",
    }
    rows = []
    for a in alerts:
        sev = str(a.get("severity") or "info").lower()
        badge = ck_signal_badge(sev, tone=sev_tone_map.get(sev, "neutral"))
        rows.append(
            '<div class="dv-alert-row">'
            '<div class="dv-alert-body">'
            f'<div class="dv-alert-msg">{_esc(a.get("message", ""))}</div>'
            '<div class="ck-eyebrow">'
            f'{_esc(a.get("kind", ""))} · '
            f'<a href="/deal/{_esc(a.get("deal_id", ""))}" class="ck-link">{_esc(a.get("deal_id", ""))}</a>'
            '</div></div>'
            f'<span>{badge}</span></div>'
        )
    prose = (
        f"{len(alerts)} active alert"
        f"{'s' if len(alerts) != 1 else ''}"
        + (f", {n_critical} requiring partner attention"
           if n_critical else "")
        + ". Triage starts with red badges; amber items can wait "
          "until the weekly review.")
    return ck_panel(
        f'<p class="ck-section-body">{prose}</p>'
        f'{"".join(rows)}',
        title="Key alerts",
    )


def _activity_section(
    activity: List[Dict[str, Any]],
) -> str:
    if not activity:
        return ck_panel(
            '<p class="ck-section-body">'
            'No changes in the last week — the portfolio data is steady.</p>',
            title="Recent activity",
        )
    rows = []
    for a in activity:
        deal_id = a.get("deal_id", "")
        rows.append(
            '<div class="dv-activity-row">'
            f'<a href="/deal/{_esc(deal_id)}" class="ck-link"><strong>{_esc(deal_id)}</strong></a>'
            f'<div class="dv-activity-label">{_esc(a.get("label", ""))}</div></div>')
    prose = (
        f"{len(activity)} item"
        f"{'s' if len(activity) != 1 else ''} from the last "
        f"week. Clicking through shows what changed and "
        f"who owns it.")
    return ck_panel(
        f'<p class="ck-section-body">{prose}</p>'
        f'{"".join(rows)}',
        title="Recent activity",
    )


# ── Main render ─────────────────────────────────────────────

def render_dashboard_v3(store: Any) -> str:
    """Render the story-driven dashboard.

    Editorial port (2026-04-27): drop the page's own <!doctype>,
    theme_init_script, theme_stylesheet, theme_toggle, and the
    page-progress-bar / keyboard-shortcuts JS. chartis_shell()
    provides the editorial parchment + topbar + breadcrumbs +
    PHI banner + sidebar + responsive layout. Per-section helpers
    (_hero_strip / _opportunities_section / _alerts_section /
    _activity_section) keep their existing markup; the page's
    inline-styled action links convert to editorial-typed anchors.
    """
    summary = _load_portfolio_summary(store)
    opportunities = _load_top_opportunities(store)
    alerts = _load_alerts(store)
    activity = _load_recent_activity(store)

    dv_styles = """
<style>
.dv-container{max-width:1100px;margin:0 auto;padding:1.5rem 1rem;}
.dv-toplinks{display:flex;gap:14px;font-size:12px;align-items:center;
justify-content:flex-end;margin-bottom:1.5rem;}
.dv-alert-row{display:flex;align-items:center;gap:14px;
padding:14px 0;border-bottom:1px solid var(--cad-border);}
.dv-alert-body{flex:1;}
.dv-alert-msg{font-size:13px;}
.dv-activity-row{display:flex;align-items:baseline;gap:14px;
padding:12px 0;border-bottom:1px solid var(--cad-border);}
.dv-activity-label{flex:1;font-size:13px;}
</style>
"""
    page_body = (
        dv_styles
        + '<div class="dv-container">'
        + '<div class="dv-toplinks">'
        + '<a href="/data/catalog?ui=v3" class="ck-link">Data →</a>'
        + '<a href="/models/quality?ui=v3" class="ck-link">Models →</a>'
        + '</div>'
        + _hero_strip(summary)
        + _opportunities_section(opportunities)
        + _alerts_section(alerts)
        + _activity_section(activity)
        + '</div>'
    )

    from ._chartis_kit import chartis_shell
    return chartis_shell(
        page_body,
        title="Portfolio · Morning view",
        active_nav="PORTFOLIO",
        breadcrumbs=[
            ("Home", "/app"),
            ("Dashboard", None),
        ],
    )
