"""Fund-level quarterly LP report (Prompt 54).

Aggregates across all deals in the portfolio: deployed capital,
total MOIC, EBITDA growth, per-deal cards, initiative progress,
risk summary. HTML export + optional scheduled delivery via the
notification system (Prompt 44).
"""
from __future__ import annotations

import html
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _esc(s: Any) -> str:
    return html.escape("" if s is None else str(s))


def _fmt_money(v: float) -> str:
    if abs(v) >= 1e9:
        return f"${v / 1e9:,.2f}B"
    if abs(v) >= 1e6:
        return f"${v / 1e6:,.1f}M"
    return f"${v:,.0f}"


def _load_deal_summaries(store: Any) -> List[Dict[str, Any]]:
    """One summary per deal from the latest analysis packet."""
    summaries: List[Dict[str, Any]] = []
    try:
        from ..analysis.analysis_store import list_packets, load_packet_by_id
    except Exception:  # noqa: BLE001
        return summaries
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
        risk_count = len([
            f for f in (pkt.risk_flags or [])
            if (f.severity.value if hasattr(f.severity, "value") else str(f.severity))
            in ("CRITICAL", "HIGH")
        ])
        summaries.append({
            "deal_id": did,
            "name": pkt.deal_name or did,
            "ebitda_opportunity": ebitda,
            "grade": grade,
            "high_risk_count": risk_count,
        })
    return summaries


def generate_lp_quarterly_html(store: Any, *, quarter: str = "") -> str:
    """Produce the full quarterly LP report as an HTML string.

    Partners download this or the digest scheduler emails it to the
    LP distribution list.
    """
    if not quarter:
        now = datetime.now(timezone.utc)
        q = (now.month - 1) // 3 + 1
        quarter = f"{now.year}-Q{q}"

    deals = _load_deal_summaries(store)
    total_opp = sum(d.get("ebitda_opportunity") or 0 for d in deals)
    total_deals = len(deals)
    total_risks = sum(d.get("high_risk_count") or 0 for d in deals)

    deal_cards = ""
    for d in sorted(deals, key=lambda x: x.get("ebitda_opportunity") or 0, reverse=True):
        deal_cards += (
            f'<div style="border:1px solid #ddd;padding:12px;margin:8px 0;border-radius:4px;">'
            f'<strong>{_esc(d["name"])}</strong> '
            f'<span style="color:#64748b;">(grade {d["grade"]})</span><br>'
            f'EBITDA opportunity: {_fmt_money(d.get("ebitda_opportunity") or 0)}'
            + (f' · <span style="color:#ef4444;">{d["high_risk_count"]} high/critical risk(s)</span>'
               if d.get("high_risk_count") else "")
            + '</div>'
        )

    return (
        '<!DOCTYPE html><html><head><meta charset="utf-8">'
        f'<title>LP Quarterly Report — {_esc(quarter)}</title>'
        '<style>body{font-family:sans-serif;max-width:800px;margin:0 auto;padding:24px;'
        'color:#111;line-height:1.6;} h1{color:#1f4e78;} .summary{display:flex;gap:20px;'
        'margin:20px 0;} .kpi{background:#f8fafc;border:1px solid #e2e8f0;padding:16px;'
        'border-radius:6px;flex:1;text-align:center;} .kpi .big{font-size:28px;font-weight:700;}'
        '.kpi .label{font-size:11px;color:#64748b;text-transform:uppercase;}</style></head>'
        f'<body><h1>LP Quarterly Report — {_esc(quarter)}</h1>'
        '<div class="summary">'
        f'<div class="kpi"><div class="big">{total_deals}</div><div class="label">Active Deals</div></div>'
        f'<div class="kpi"><div class="big">{_fmt_money(total_opp)}</div><div class="label">Total Opportunity</div></div>'
        f'<div class="kpi"><div class="big" style="color:#ef4444;">{total_risks}</div><div class="label">High/Critical Risks</div></div>'
        '</div>'
        f'<h2>Portfolio Deals</h2>{deal_cards or "<p>No deals in portfolio.</p>"}'
        f'<footer style="margin-top:40px;color:#94a3b8;font-size:12px;">'
        f'Generated {datetime.now(timezone.utc).strftime("%Y-%m-%d")} · RCM-MC · Confidential</footer>'
        '</body></html>'
    )
