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

from .colors import STATUS
from .loading import page_progress_bar
from .nav import breadcrumb, keyboard_shortcuts

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

_BG_PRIMARY = "#0f172a"
_BG_SURFACE = "#1f2937"
_BG_ELEVATED = "#111827"
_BORDER = "#374151"
_TEXT = "#f3f4f6"
_TEXT_DIM = STATUS["neutral"]
_ACCENT = STATUS["info"]
_GREEN = STATUS["positive"]
_AMBER = STATUS["watch"]
_RED = STATUS["negative"]


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
    health_color = (
        _GREEN if (health or 0) >= 75
        else _AMBER if (health or 0) >= 60
        else _RED)

    def _kpi(label: str, value: str, color: str = _TEXT,
             sub: str = "") -> str:
        return (
            f'<div style="flex:1;min-width:180px;padding:'
            f'18px 22px;border-right:1px solid {_BORDER};">'
            f'<div style="font-size:11px;text-transform:'
            f'uppercase;letter-spacing:0.06em;color:'
            f'{_TEXT_DIM};margin-bottom:8px;">'
            f'{_esc(label)}</div>'
            f'<div style="font-size:30px;font-weight:600;'
            f'color:{color};font-variant-numeric:tabular-nums;">'
            f'{_esc(value)}</div>'
            + (f'<div style="font-size:11px;color:'
               f'{_TEXT_DIM};margin-top:6px;">{_esc(sub)}'
               f'</div>' if sub else "")
            + "</div>"
        )

    return (
        f'<section style="background:{_BG_SURFACE};border:1px '
        f'solid {_BORDER};border-radius:10px;margin-bottom:'
        f'24px;overflow:hidden;">'
        f'<div style="display:flex;flex-wrap:wrap;border-bottom:'
        f'1px solid {_BORDER};">'
        + _kpi("Active deals",
               f"{n_active}",
               sub=f"of {n_deals} total")
        + _kpi("Total NPR", _fmt_money(npr))
        + _kpi("Current EBITDA", _fmt_money(ebitda))
        + _kpi("Health score", health_text,
               color=health_color, sub="weighted by NPR")
        + '</div>'
        f'<div style="padding:18px 22px;color:{_TEXT};'
        f'font-size:14px;line-height:1.5;">'
        f'{_esc(narrative)}</div></section>'
    )


def _section_header(label: str, prose: str) -> str:
    return (
        f'<header style="margin:32px 0 12px 0;">'
        f'<h2 style="font-size:13px;text-transform:uppercase;'
        f'letter-spacing:0.10em;color:{_TEXT_DIM};margin:'
        f'0 0 6px 0;">{_esc(label)}</h2>'
        f'<p style="font-size:14px;color:{_TEXT};margin:0;'
        f'max-width:720px;line-height:1.5;">{_esc(prose)}</p>'
        f'</header>')


def _opportunities_section(
    opps: List[Dict[str, Any]],
) -> str:
    if not opps:
        return (
            _section_header(
                "Top opportunities",
                "No realized EBITDA uplift opportunities yet — "
                "build analysis packets to populate this list.")
            + f'<div style="background:{_BG_ELEVATED};border:'
            f'1px solid {_BORDER};border-radius:8px;padding:'
            f'24px;color:{_TEXT_DIM};text-align:center;'
            f'font-size:13px;">No opportunities to rank.</div>'
        )

    total_uplift = sum(o["uplift"] for o in opps)
    rows = []
    for i, opp in enumerate(opps, 1):
        deal_link = (
            f'<a href="/deal/{_esc(opp["deal_id"])}" '
            f'style="color:{_ACCENT};text-decoration:none;'
            f'font-weight:500;">{_esc(opp["deal_id"])}</a>')
        rows.append(
            f'<tr style="border-bottom:1px solid {_BORDER};">'
            f'<td style="padding:12px 16px;color:{_TEXT_DIM};'
            f'font-variant-numeric:tabular-nums;width:30px;">'
            f'{i}.</td>'
            f'<td style="padding:12px 16px;">{deal_link}</td>'
            f'<td style="padding:12px 16px;text-align:right;'
            f'color:{_GREEN};font-weight:500;'
            f'font-variant-numeric:tabular-nums;">'
            f'+{_fmt_money(opp["uplift"])}</td>'
            f'<td style="padding:12px 16px;text-align:right;'
            f'color:{_TEXT_DIM};font-variant-numeric:'
            f'tabular-nums;">'
            f'{_fmt_pct(opp["uplift_pct"])}</td>'
            f'<td style="padding:12px 16px;text-align:right;'
            f'color:{_TEXT_DIM};font-variant-numeric:'
            f'tabular-nums;font-size:12px;">'
            f'{_fmt_money(opp["current_ebitda"])} → '
            f'{_fmt_money(opp["target_ebitda"])}</td>'
            f'</tr>')
    prose = (
        f"Ranked by realistic EBITDA uplift across the active "
        f"portfolio. The top {len(opps)} represent "
        f"{_fmt_money(total_uplift)} in additional EBITDA if "
        f"value-creation plans land — start with the biggest "
        f"and work down.")
    return (
        _section_header("Top opportunities", prose)
        + f'<div style="background:{_BG_SURFACE};border:'
        f'1px solid {_BORDER};border-radius:8px;overflow:'
        f'hidden;">'
        + '<table style="width:100%;border-collapse:collapse;">'
        + '<thead><tr style="background:'
        + _BG_ELEVATED + ';">'
        + ('<th style="padding:10px 16px;text-align:left;'
           f'font-size:11px;text-transform:uppercase;'
           f'letter-spacing:0.05em;color:{_TEXT_DIM};">#</th>'
           '<th style="padding:10px 16px;text-align:left;'
           f'font-size:11px;text-transform:uppercase;'
           f'letter-spacing:0.05em;color:{_TEXT_DIM};">Deal</th>'
           '<th style="padding:10px 16px;text-align:right;'
           f'font-size:11px;text-transform:uppercase;'
           f'letter-spacing:0.05em;color:{_TEXT_DIM};">'
           'EBITDA Uplift</th>'
           '<th style="padding:10px 16px;text-align:right;'
           f'font-size:11px;text-transform:uppercase;'
           f'letter-spacing:0.05em;color:{_TEXT_DIM};">'
           'vs. Current</th>'
           '<th style="padding:10px 16px;text-align:right;'
           f'font-size:11px;text-transform:uppercase;'
           f'letter-spacing:0.05em;color:{_TEXT_DIM};">'
           'Bridge</th>')
        + '</tr></thead>'
        + f'<tbody>{"".join(rows)}</tbody></table></div>'
    )


def _alerts_section(
    alerts: List[Dict[str, Any]],
) -> str:
    if not alerts:
        return (
            _section_header(
                "Key alerts",
                "Nothing demanding your decision today — the "
                "portfolio is quiet.")
            + f'<div style="background:{_BG_ELEVATED};border:'
            f'1px solid {_BORDER};border-radius:8px;padding:'
            f'24px;color:{_GREEN};text-align:center;font-size:'
            f'14px;">All clear.</div>'
        )
    n_critical = sum(1 for a in alerts
                     if str(a.get("severity")
                            ).lower()
                     in ("critical", "high"))
    sev_color = {
        "critical": _RED, "high": _RED,
        "medium": _AMBER, "warning": _AMBER,
        "low": _TEXT_DIM, "info": _TEXT_DIM,
    }
    rows = []
    for a in alerts:
        sev = str(a.get("severity") or "info").lower()
        color = sev_color.get(sev, _TEXT_DIM)
        rows.append(
            f'<div style="padding:14px 18px;border-bottom:'
            f'1px solid {_BORDER};display:flex;align-items:'
            f'center;gap:14px;">'
            f'<span style="display:inline-block;width:8px;'
            f'height:8px;border-radius:50%;background:'
            f'{color};flex-shrink:0;"></span>'
            f'<div style="flex:1;">'
            f'<div style="color:{_TEXT};font-size:13px;">'
            f'{_esc(a.get("message", ""))}</div>'
            f'<div style="color:{_TEXT_DIM};font-size:11px;'
            f'margin-top:3px;">'
            f'{_esc(a.get("kind", ""))} · '
            f'<a href="/deal/{_esc(a.get("deal_id", ""))}"'
            f' style="color:{_ACCENT};">{_esc(a.get("deal_id", ""))}</a>'
            f'</div></div>'
            f'<span style="font-size:11px;color:{color};'
            f'text-transform:uppercase;letter-spacing:0.05em;'
            f'font-weight:600;">{_esc(sev)}</span></div>'
        )
    prose = (
        f"{len(alerts)} active alert"
        f"{'s' if len(alerts) != 1 else ''}"
        + (f", {n_critical} requiring partner attention"
           if n_critical else "")
        + ". Triage starts with red dots; amber items can wait "
          "until the weekly review.")
    return (
        _section_header("Key alerts", prose)
        + f'<div style="background:{_BG_SURFACE};border:'
        f'1px solid {_BORDER};border-radius:8px;overflow:'
        f'hidden;">{"".join(rows)}</div>'
    )


def _activity_section(
    activity: List[Dict[str, Any]],
) -> str:
    if not activity:
        return (
            _section_header(
                "Recent activity",
                "No changes in the last week — the portfolio "
                "data is steady.")
            + f'<div style="background:{_BG_ELEVATED};border:'
            f'1px solid {_BORDER};border-radius:8px;padding:'
            f'24px;color:{_TEXT_DIM};text-align:center;'
            f'font-size:13px;">No recent activity.</div>'
        )
    rows = []
    for a in activity:
        deal_id = a.get("deal_id", "")
        rows.append(
            f'<div style="padding:12px 18px;border-bottom:'
            f'1px solid {_BORDER};display:flex;align-items:'
            f'baseline;gap:14px;">'
            f'<a href="/deal/{_esc(deal_id)}" '
            f'style="color:{_ACCENT};text-decoration:none;'
            f'font-weight:500;font-size:13px;">{_esc(deal_id)}'
            f'</a>'
            f'<div style="flex:1;color:{_TEXT};font-size:13px;">'
            f'{_esc(a.get("label", ""))}</div></div>')
    prose = (
        f"{len(activity)} item"
        f"{'s' if len(activity) != 1 else ''} from the last "
        f"week. Clicking through shows what changed and "
        f"who owns it.")
    return (
        _section_header("Recent activity", prose)
        + f'<div style="background:{_BG_SURFACE};border:'
        f'1px solid {_BORDER};border-radius:8px;overflow:'
        f'hidden;">{"".join(rows)}</div>'
    )


# ── Main render ─────────────────────────────────────────────

def render_dashboard_v3(store: Any) -> str:
    """Render the story-driven dashboard."""
    summary = _load_portfolio_summary(store)
    opportunities = _load_top_opportunities(store)
    alerts = _load_alerts(store)
    activity = _load_recent_activity(store)

    return (
        f'<!doctype html><html><head>'
        f'<meta charset="utf-8">'
        f'<title>Portfolio · Morning view</title>'
        f'<style>body{{margin:0;font-family:system-ui,'
        f'-apple-system,sans-serif;background:{_BG_PRIMARY};'
        f'color:{_TEXT};}}</style></head><body>'
        + page_progress_bar()
        + f'<div style="max-width:1100px;margin:0 auto;'
        f'padding:32px 24px;">'
        + breadcrumb([("Dashboard", None)])
        + f'<div style="display:flex;justify-content:'
        f'space-between;align-items:baseline;'
        f'margin-bottom:8px;">'
        f'<h1 style="font-size:22px;color:{_TEXT};margin:0;">'
        f'Morning view</h1>'
        f'<div style="display:flex;gap:14px;font-size:12px;">'
        f'<a href="/data/catalog" style="color:{_ACCENT};">'
        f'Data →</a>'
        f'<a href="/models/quality" style="color:{_ACCENT};">'
        f'Models →</a>'
        f'<a href="/?v2=1" style="color:{_TEXT_DIM};">'
        f'Legacy v2</a>'
        f'</div></div>'
        f'<p style="color:{_TEXT_DIM};font-size:13px;'
        f'margin:0 0 24px 0;">Today\'s read on the '
        f'portfolio — what\'s working, what needs your '
        f'attention, what changed.</p>'
        + _hero_strip(summary)
        + _opportunities_section(opportunities)
        + _alerts_section(alerts)
        + _activity_section(activity)
        + '</div>'
        + keyboard_shortcuts()
        + '</body></html>'
    )
