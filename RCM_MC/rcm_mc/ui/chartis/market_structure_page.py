"""Per-deal Market Structure — /deal/<id>/market-structure.

Renders the output of ``pe_intelligence.market_structure`` for the
deal's local competitive landscape. Shares are pulled off the packet
profile under ``market_shares`` (a ``{player: share}`` dict).

The panel answers three questions every healthcare-PE partner asks
on the first read:

  - How concentrated is this market? (HHI, CR3, CR5, top-share)
  - Is this a consolidation play? (consolidation_play_score + thesis hint)
  - What's the competitive dynamic — concentrated / fragmented /
    consolidating / bimodal? (fragmentation_verdict)

When the packet lacks market shares the page renders a guided
empty state rather than a 500 — most packets today don't carry them.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

from .._chartis_kit import (
    P,
    chartis_shell,
    ck_kpi_block,
    ck_section_header,
)
from ._helpers import (
    deal_header_nav,
    empty_note,
    fmt_pct,
    insufficient_data_banner,
    render_page_explainer,
    safe_dict,
    small_panel,
    verdict_badge,
)
from ._sanity import render_number


_VERDICT_META = {
    "fragmented":    (P["warning"],  "lots of small players — consolidation opportunity"),
    "consolidating": (P["accent"],   "mid-concentration — the window is closing"),
    "concentrated":  (P["positive"], "oligopoly — pricing power, fewer bolt-ons"),
    "monopolistic":  (P["negative"], "one-player market — regulator risk"),
    "unknown":       (P["text_faint"], "insufficient shares to classify"),
}


def _hhi_bar(hhi: float) -> str:
    """Visual HHI scale: 0 (perfect competition) → 10,000 (monopoly).

    DOJ-style thresholds: <1,500 unconcentrated, 1,500-2,500 moderate,
    >2,500 highly concentrated. Position a marker on a horizontal bar.
    """
    pct = max(0.0, min(1.0, hhi / 10000.0))
    return (
        f'<div style="margin:10px 0;">'
        f'<div style="display:flex;justify-content:space-between;'
        f'font-family:var(--ck-mono);font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:0.10em;margin-bottom:4px;">'
        f'<span>PERFECT COMPETITION</span>'
        f'<span>1,500 · MODERATE</span>'
        f'<span>2,500 · HIGH</span>'
        f'<span>MONOPOLY (10,000)</span>'
        f'</div>'
        f'<div style="position:relative;height:12px;border-radius:2px;'
        f'background:linear-gradient(to right,{P["positive"]},{P["warning"]},{P["negative"]});'
        f'border:1px solid {P["border"]};">'
        f'<div style="position:absolute;top:-4px;left:calc({pct*100:.1f}% - 2px);'
        f'width:4px;height:20px;background:{P["text"]};"></div>'
        f'</div>'
        f'<div style="text-align:center;font-family:var(--ck-mono);font-size:11px;'
        f'color:{P["text"]};margin-top:4px;font-variant-numeric:tabular-nums;">'
        f'HHI {render_number(hhi, "hhi")}</div>'
        f'</div>'
    )


def _shares_table(shares: Dict[str, float], *, target_name: Optional[str]) -> str:
    if not shares:
        return empty_note("No market shares on packet.")
    items = sorted(shares.items(), key=lambda kv: kv[1], reverse=True)
    rows = []
    for i, (name, share) in enumerate(items, start=1):
        is_target = (target_name and name.lower() == str(target_name).lower())
        col = P["accent"] if is_target else P["text"]
        tag = (
            f'<span style="font-family:var(--ck-mono);font-size:9px;'
            f'letter-spacing:0.12em;color:{P["accent"]};margin-left:8px;">'
            f'TARGET</span>' if is_target else ""
        )
        bar_w = max(1, int(float(share) * 100))
        rows.append(
            f'<tr>'
            f'<td style="color:{P["text_faint"]};font-family:var(--ck-mono);'
            f'font-size:10px;text-align:right;width:30px;">{i}</td>'
            f'<td style="color:{col};font-family:var(--ck-mono);font-size:11px;">'
            f'{_html.escape(str(name))}{tag}</td>'
            f'<td style="font-family:var(--ck-mono);font-size:11px;'
            f'color:{col};font-variant-numeric:tabular-nums;text-align:right;'
            f'width:80px;">{render_number(share, "market_share")}</td>'
            f'<td style="width:180px;">'
            f'<span style="display:block;height:6px;background:{P["border_dim"]};'
            f'border-radius:1px;overflow:hidden;">'
            f'<span style="display:block;height:100%;width:{bar_w}%;background:{col};">'
            f'</span></span></td>'
            f'</tr>'
        )
    return (
        f'<div class="ck-table-wrap"><table class="ck-table">'
        f'<thead><tr><th class="num">Rank</th><th>Player</th>'
        f'<th class="num">Share</th><th></th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>'
    )


def _thesis_hint_badge(hint: str) -> str:
    labels = {
        "buy_and_build": ("BUY &amp; BUILD", P["positive"]),
        "platform_entry": ("PLATFORM ENTRY", P["accent"]),
        "market_leader": ("MARKET LEADER", P["accent"]),
        "roll_up": ("ROLL-UP", P["positive"]),
        "competitive_response": ("COMPETITIVE RESPONSE", P["warning"]),
        "antitrust_watch": ("ANTITRUST WATCH", P["negative"]),
        "": ("—", P["text_faint"]),
    }
    text, col = labels.get(hint, (hint.upper().replace("_", " "), P["text_dim"]))
    return verdict_badge(text, color=col)


def _target_name_from_packet(packet: Any, profile: Dict[str, Any]) -> Optional[str]:
    if profile.get("name"):
        return str(profile.get("name"))
    if isinstance(packet, dict):
        return packet.get("deal_name")
    return getattr(packet, "deal_name", None)


def render_market_structure(
    review: Any,
    deal_id: str,
    *,
    deal_name: str = "",
    packet: Any = None,
    profile: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    missing_fields: Optional[List[str]] = None,
    current_user: Optional[str] = None,
) -> str:
    label = deal_name or deal_id
    header = deal_header_nav(deal_id, active="market-structure")

    if error:
        body = header + insufficient_data_banner(
            deal_id,
            title="Market structure",
            error=error,
            missing_fields=missing_fields,
        )
        return chartis_shell(
            body,
            title=f"Market Structure · {label}",
            active_nav="/pe-intelligence",
        breadcrumbs=[
            ("Home", "/app"),
            ("Market", "/market-intel"),
            ("Structure", None),
        ],
            subtitle=f"Market structure unavailable for {label}",
        )

    ms = safe_dict(getattr(review, "market_structure", None))
    if not ms or "hhi" not in ms:
        note = ms.get("note") or ms.get("error") or (
            "No market-share data on packet. Add a ``market_shares`` dict "
            "under profile to enable HHI / CR3 / CR5 scoring."
        )
        body = header + small_panel(
            "Market Structure — not scored",
            empty_note(note) + (
                f'<div style="margin-top:10px;font-size:11px;color:{P["text_dim"]};">'
                f'Structure: <code style="color:{P["accent"]};'
                f'font-family:var(--ck-mono);">profile.market_shares = '
                f'{{"TargetCo": 0.35, "CompA": 0.25, "CompB": 0.15, ...}}</code>'
                f'</div>'
            ),
            code="N/A",
        )
        return chartis_shell(
            body,
            title=f"Market Structure · {label}",
            active_nav="/pe-intelligence",
        breadcrumbs=[
            ("Home", "/app"),
            ("Market", "/market-intel"),
            ("Structure", None),
        ],
            subtitle=f"{label} · add market_shares to score",
        )

    hhi = float(ms.get("hhi", 0.0) or 0.0)
    cr3 = float(ms.get("cr3", 0.0) or 0.0)
    cr5 = float(ms.get("cr5", 0.0) or 0.0)
    top_share = float(ms.get("top_share", 0.0) or 0.0)
    n_players = int(ms.get("n_players", 0) or 0)
    verdict = str(ms.get("fragmentation_verdict", "unknown") or "unknown")
    cons_score = float(ms.get("consolidation_play_score", 0.0) or 0.0)
    thesis_hint = str(ms.get("partner_thesis_hint", "") or "")
    note = str(ms.get("partner_note", "") or "")
    shares = ms.get("shares_used") or {}

    col, verdict_desc = _VERDICT_META.get(verdict, (P["text_dim"], ""))

    kpis = (
        ck_kpi_block("HHI", render_number(hhi, "hhi"), "0–10,000 (monopoly)")
        + ck_kpi_block("CR3", render_number(cr3, "cr3"), "top-3 combined share")
        + ck_kpi_block("CR5", render_number(cr5, "cr5"), "top-5 combined share")
        + ck_kpi_block("Top Share",
                        render_number(top_share, "market_share"),
                        f"out of {n_players} players")
        + ck_kpi_block("Consolidation", fmt_pct(cons_score), "play-score 0-1")
    )
    kpi_strip = f'<div class="ck-kpi-grid">{kpis}</div>'

    verdict_panel = (
        f'<div style="display:flex;gap:12px;align-items:center;margin-bottom:12px;">'
        f'<span style="font-family:var(--ck-mono);font-size:9px;'
        f'color:{P["text_faint"]};letter-spacing:0.15em;">FRAGMENTATION</span>'
        f'{verdict_badge(verdict.upper(), color=col)}'
        f'<span style="color:{P["text_dim"]};font-size:11px;">'
        f'{_html.escape(verdict_desc)}</span>'
        f'</div>'
        + (
            f'<p style="color:{P["text"]};font-size:12px;line-height:1.6;'
            f'margin-bottom:10px;">{_html.escape(note)}</p>' if note else ""
        )
        + _hhi_bar(hhi)
        + f'<div style="display:flex;gap:14px;align-items:center;'
        f'margin-top:10px;padding-top:10px;border-top:1px solid {P["border_dim"]};">'
        f'<span style="font-family:var(--ck-mono);font-size:9px;'
        f'letter-spacing:0.12em;color:{P["text_faint"]};">THESIS HINT</span>'
        f'{_thesis_hint_badge(thesis_hint)}'
        f'</div>'
    )

    target_name = _target_name_from_packet(packet, profile or {})
    shares_panel = _shares_table(shares, target_name=target_name)

    explainer = render_page_explainer(
        what=(
            "Standard market-concentration metrics for the target's "
            "local market: HHI (Herfindahl–Hirschman Index — sum of "
            "squared shares), CR3 and CR5 (combined share of top-3 "
            "and top-5 players), plus a consolidation-play score."
        ),
        scale=(
            "HHI under 1,500 = unconcentrated; 1,500–2,500 = "
            "moderately concentrated; over 2,500 = highly "
            "concentrated. Thresholds are from the DOJ/FTC Horizontal "
            "Merger Guidelines."
        ),
        use=(
            "Use HHI + CR5 to judge pricing power and consolidation "
            "opportunity. Deals in unconcentrated markets have more "
            "buy-and-build runway; concentrated markets command "
            "higher multiples but carry antitrust scrutiny."
        ),
        source=(
            "pe_intelligence/market_structure.py HHI_UNCONCENTRATED "
            "and HHI_HIGHLY_CONCENTRATED constants (DOJ/FTC Horizontal "
            "Merger Guidelines)."
        ),
        page_key="deal-market-structure",
    )

    body = (
        explainer
        + header
        + kpi_strip
        + ck_section_header(
            "COMPETITIVE STRUCTURE",
            f"{n_players} players · top-share {top_share*100:.1f}%",
        )
        + small_panel("Verdict + thesis", verdict_panel, code="STR")
        + small_panel(f"Shares used ({n_players} players)", shares_panel, code="SHR")
    )

    return chartis_shell(
        body,
        title=f"Market Structure · {label}",
        active_nav="/pe-intelligence",
        breadcrumbs=[
            ("Home", "/app"),
            ("Market", "/market-intel"),
            ("Structure", None),
        ],
        subtitle=f"{label} · HHI {hhi:,.0f} · {verdict}",
    )
