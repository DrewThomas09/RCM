"""Dashboard v2: the morning view (Prompt 31).

Partners open the platform and need "what needs my attention today?"
in 5 seconds. Four summary cards at the top, a "Needs Attention"
action list, a deal-card grid, and quick-action buttons.

Replaces the legacy dashboard at ``/`` when called from the route
dispatcher.
"""
from __future__ import annotations

import html
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _esc(s: Any) -> str:
    return html.escape("" if s is None else str(s))


def _fmt_money(v: float) -> str:
    if abs(v) >= 1e9:
        return f"${v / 1e9:,.2f}B"
    if abs(v) >= 1e6:
        return f"${v / 1e6:,.1f}M"
    if abs(v) >= 1e3:
        return f"${v / 1e3:,.0f}K"
    return f"${v:,.0f}"


# ── Data assembly ──────────────────────────────────────────────────

def _load_deal_cards(store: Any) -> List[Dict[str, Any]]:
    """One card per deal with packet-derived summary numbers."""
    cards: List[Dict[str, Any]] = []
    try:
        from ..analysis.analysis_store import list_packets, load_packet_by_id
    except Exception:  # noqa: BLE001
        return cards
    rows = list_packets(store)
    seen: set = set()
    for r in rows:
        did = r.get("deal_id") or ""
        if did in seen:
            continue
        seen.add(did)
        pkt = load_packet_by_id(store, r["id"])
        if pkt is None:
            continue
        ebitda = float(pkt.ebitda_bridge.total_ebitda_impact or 0) if pkt.ebitda_bridge else 0
        grade = getattr(pkt.completeness, "grade", "?") or "?"
        top_risk = ""
        risk_sev = ""
        if pkt.risk_flags:
            rf = pkt.risk_flags[0]
            top_risk = rf.title or ""
            risk_sev = rf.severity.value if hasattr(rf.severity, "value") else str(rf.severity)
        cards.append({
            "deal_id": did,
            "name": pkt.deal_name or did,
            "ebitda_opportunity": ebitda,
            "grade": grade,
            "top_risk": top_risk,
            "risk_severity": risk_sev,
            "updated": r.get("created_at") or "",
        })
    return cards


def _needs_attention(cards: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Top-5 action items sorted by urgency."""
    items: List[Dict[str, str]] = []
    for c in cards:
        if c.get("risk_severity") in ("CRITICAL", "HIGH"):
            items.append({
                "text": f"{c['name']}: {c['top_risk']}",
                "link": f"/analysis/{c['deal_id']}",
                "urgency": "0" if c["risk_severity"] == "CRITICAL" else "1",
            })
        if c.get("grade") in ("D",):
            items.append({
                "text": f"{c['name']}: low completeness (grade D) — upload more data",
                "link": f"/analysis/{c['deal_id']}",
                "urgency": "3",
            })
    items.sort(key=lambda i: i.get("urgency") or "9")
    return items[:5]


# ── Renderer ───────────────────────────────────────────────────────

_DASHBOARD_CSS = """
body.dashboard-v2 { margin:0; padding:0; background:#0a0e17; color:#e2e8f0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, sans-serif;
  font-size: 14px; line-height: 1.5; }
.dash-wrap { max-width:1100px; margin:0 auto; padding:24px 20px; }
.dash-strip { display:grid; grid-template-columns:repeat(4, 1fr); gap:12px;
  margin-bottom:20px; }
.dash-card { background:#111827; border:1px solid #1e293b;
  padding:14px 16px; border-radius:4px; }
.dash-card .big { font-size:28px; font-weight:700;
  font-family:"JetBrains Mono",monospace; font-variant-numeric:tabular-nums; }
.dash-card .label { font-size:11px; color:#94a3b8;
  text-transform:uppercase; letter-spacing:.06em; margin-top:4px; }
.dash-attention { background:#111827; border:1px solid #1e293b;
  padding:16px; border-radius:4px; margin-bottom:20px; }
.dash-attention-title { font-weight:600; margin-bottom:10px; }
.dash-attention-item { padding:6px 0; border-bottom:1px solid #1e293b;
  display:flex; align-items:center; gap:10px; font-size:13px; }
.dash-attention-item a { color:#3b82f6; text-decoration:none; }
.dash-deals { display:grid; grid-template-columns:repeat(auto-fill, minmax(280px, 1fr));
  gap:12px; }
.deal-card { background:#111827; border:1px solid #1e293b;
  padding:14px 16px; border-radius:4px; transition:border-color 0.15s; }
.deal-card:hover { border-color:#3b82f6; }
.deal-card-name { font-weight:600; font-size:14px; margin-bottom:6px; }
.deal-card-meta { font-size:12px; color:#94a3b8; }
.deal-card-grade { display:inline-block; padding:1px 6px; border-radius:2px;
  font-weight:600; font-size:11px; }
.grade-A { background:#10b981; color:#fff; }
.grade-B { background:#3b82f6; color:#fff; }
.grade-C { background:#f59e0b; color:#fff; }
.grade-D { background:#ef4444; color:#fff; }
.dash-actions { display:flex; gap:8px; margin-bottom:20px; }
.dash-actions a { background:#1f4e78; color:#fff; padding:8px 16px;
  border-radius:3px; text-decoration:none; font-weight:600; font-size:13px; }
.dash-actions a:hover { background:#2563eb; }
.dash-empty { text-align:center; padding:40px; color:#94a3b8; }
.dash-empty a { color:#3b82f6; }
"""


def render_dashboard_v2(store: Any) -> str:
    """Full ``<!doctype html>`` dashboard page."""
    cards = _load_deal_cards(store)
    total_deals = len(cards)
    total_opp = sum(c.get("ebitda_opportunity") or 0 for c in cards)
    critical_count = sum(
        1 for c in cards if c.get("risk_severity") == "CRITICAL"
    )
    attention = _needs_attention(cards)

    # Summary strip.
    strip = f"""
    <div class="dash-strip">
      <div class="dash-card"><div class="big">{total_deals}</div>
        <div class="label">Active Deals</div></div>
      <div class="dash-card"><div class="big">{_fmt_money(total_opp)}</div>
        <div class="label">Total EBITDA Opportunity</div></div>
      <div class="dash-card"><div class="big" style="color:#ef4444;">{critical_count}</div>
        <div class="label">Critical Risks</div></div>
      <div class="dash-card"><div class="big">{len(attention)}</div>
        <div class="label">Needs Attention</div></div>
    </div>
    """

    # Attention items.
    attention_html = ""
    if attention:
        items_html = "".join(
            f'<div class="dash-attention-item">'
            f'<span>{_esc(a["text"])}</span>'
            f'<a href="{_esc(a["link"])}">Go →</a></div>'
            for a in attention
        )
        attention_html = f"""
        <div class="dash-attention">
          <div class="dash-attention-title">Needs Attention</div>
          {items_html}
        </div>
        """

    # Quick actions.
    actions = """
    <div class="dash-actions">
      <a href="/new-deal">+ New Deal</a>
      <a href="/portfolio/heatmap">Heatmap</a>
      <a href="/portfolio/monte-carlo">Portfolio MC</a>
      <a href="/screen">Screen Deals</a>
    </div>
    """

    # Deal grid.
    if cards:
        deal_cards_html = "".join(
            f'<a href="/analysis/{_esc(c["deal_id"])}" class="deal-card"'
            f' style="text-decoration:none;color:inherit;">'
            f'<div class="deal-card-name">{_esc(c["name"])}'
            f' <span class="deal-card-grade grade-{c["grade"]}">{c["grade"]}</span></div>'
            f'<div class="deal-card-meta">'
            f'EBITDA: {_fmt_money(c.get("ebitda_opportunity") or 0)}'
            + (f' · <span style="color:#ef4444;">{_esc(c["top_risk"][:40])}</span>'
               if c.get("top_risk") else "")
            + '</div></a>'
            for c in sorted(
                cards,
                key=lambda c: c.get("ebitda_opportunity") or 0,
                reverse=True,
            )
        )
        grid = f'<div class="dash-deals">{deal_cards_html}</div>'
    else:
        grid = (
            '<div class="dash-empty">'
            'No deals yet. <a href="/new-deal">Create your first deal →</a>'
            '</div>'
        )

    from ._chartis_kit import chartis_shell
    body = (
        '<div class="dash-wrap">'
        + actions + strip + attention_html + grid
        + '</div>'
    )
    return chartis_shell(
        body,
        "Portfolio Dashboard",
        extra_css=_DASHBOARD_CSS,
    )
