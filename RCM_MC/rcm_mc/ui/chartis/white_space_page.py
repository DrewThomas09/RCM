"""Per-deal White Space — /deal/<id>/white-space.

Surfaces ``pe_intelligence.white_space.detect_white_space(inputs)`` —
adjacencies where the target has room to grow along three dimensions:

  - Geographic: states the target doesn't cover but that are adjacent
    to its existing footprint or match the subsector's typical
    expansion map.
  - Segment: service lines / sub-specialties the target lacks that
    are common expansion paths for its subsector.
  - Channel: delivery-channel adjacencies (e.g. HOPD → ASC, IP → OP,
    direct-contracting → employer self-funded).

Output read off the PartnerReview (enriched via
``_enrich_secondary_analytics``). When the packet lacks
existing/candidate lists, the brain returns an empty opportunities
array and a partner-voice note — we render the empty state instead of
500ing.
"""
from __future__ import annotations

import html as _html
from collections import defaultdict
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
    insufficient_data_banner,
    render_page_explainer,
    safe_dict,
    small_panel,
    verdict_badge,
)


_DIM_LABELS = {
    "geographic": ("GEOGRAPHIC", P["accent"], "states adjacent to existing footprint"),
    "segment": ("SEGMENT", P["warning"], "service lines common for this subsector"),
    "channel": ("CHANNEL", P["positive"], "delivery-channel adjacencies"),
}


def _score_color(score: float) -> str:
    if score >= 0.75:
        return P["positive"]
    if score >= 0.50:
        return P["warning"]
    if score >= 0.25:
        return P["text_dim"]
    return P["text_faint"]


def _opportunity_card(opp: Dict[str, Any]) -> str:
    name = _html.escape(str(opp.get("name", "—")))
    score = float(opp.get("score", 0.0) or 0.0)
    col = _score_color(score)
    rationale = _html.escape(str(opp.get("rationale", "") or ""))
    barriers = opp.get("barriers") or []
    if isinstance(barriers, str):
        barriers = [barriers]
    barriers_html = ""
    if barriers:
        items = "".join(
            f'<li style="padding:2px 0;color:{P["text_dim"]};font-size:11px;">'
            f'{_html.escape(str(b))}</li>'
            for b in barriers
        )
        barriers_html = (
            f'<div style="margin-top:6px;">'
            f'<span style="font-family:var(--ck-mono);font-size:9px;'
            f'letter-spacing:0.12em;color:{P["negative"]};">BARRIERS</span>'
            f'<ul style="list-style:none;padding:0;margin:4px 0 0;">{items}</ul>'
            f'</div>'
        )
    return (
        f'<div style="background:{P["panel"]};border:1px solid {P["border"]};'
        f'border-radius:3px;padding:10px 12px;margin-bottom:8px;">'
        f'<div style="display:flex;align-items:baseline;gap:10px;">'
        f'<span style="font-family:var(--ck-mono);font-size:12px;'
        f'font-weight:600;color:{P["text"]};">{name}</span>'
        f'<span style="margin-left:auto;font-family:var(--ck-mono);'
        f'font-size:11px;color:{col};font-variant-numeric:tabular-nums;">'
        f'score {score:.2f}</span>'
        f'</div>'
        + (
            f'<div style="color:{P["text_dim"]};font-size:11px;margin-top:4px;'
            f'line-height:1.5;">{rationale}</div>' if rationale else ""
        )
        + barriers_html
        + f'</div>'
    )


def _dimension_section(dim: str, opps: List[Dict[str, Any]]) -> str:
    label, col, desc = _DIM_LABELS.get(dim, (dim.upper(), P["text_dim"], ""))
    if not opps:
        inner = empty_note(f"No {label.lower()} opportunities surfaced.")
    else:
        inner = "".join(_opportunity_card(o) for o in opps)
    return (
        f'<div style="margin-bottom:14px;">'
        f'<div style="display:flex;align-items:baseline;gap:10px;margin-bottom:8px;">'
        f'<span style="font-family:var(--ck-mono);font-size:10px;'
        f'font-weight:700;letter-spacing:0.12em;color:{col};">{label}</span>'
        f'<span style="color:{P["text_faint"]};font-size:10px;">{_html.escape(desc)}</span>'
        f'<span style="margin-left:auto;font-family:var(--ck-mono);font-size:9px;'
        f'color:{P["text_faint"]};">{len(opps)} opportunit{"y" if len(opps) == 1 else "ies"}</span>'
        f'</div>'
        f'{inner}'
        f'</div>'
    )


def _top_opportunities_strip(opportunities: List[Dict[str, Any]]) -> str:
    top = sorted(
        opportunities,
        key=lambda o: float(o.get("score", 0.0) or 0.0),
        reverse=True,
    )[:3]
    if not top:
        return empty_note("No ranked opportunities.")
    cards = []
    for i, o in enumerate(top, start=1):
        score = float(o.get("score", 0.0) or 0.0)
        col = _score_color(score)
        cards.append(
            f'<div style="flex:1;min-width:200px;background:{P["panel"]};'
            f'border:1px solid {col};border-left-width:4px;border-radius:3px;'
            f'padding:10px 14px;">'
            f'<div style="display:flex;align-items:baseline;gap:8px;">'
            f'<span style="font-family:var(--ck-mono);font-size:16px;'
            f'font-weight:700;color:{col};">#{i}</span>'
            f'<span style="font-family:var(--ck-mono);font-size:9px;'
            f'letter-spacing:0.12em;color:{P["text_faint"]};">'
            f'{_html.escape(str(o.get("dimension", "—")).upper())}</span>'
            f'</div>'
            f'<div style="color:{P["text"]};font-size:13px;font-weight:600;'
            f'margin-top:4px;">{_html.escape(str(o.get("name", "—")))}</div>'
            f'<div style="color:{P["text_dim"]};font-size:10.5px;margin-top:2px;'
            f'font-family:var(--ck-mono);font-variant-numeric:tabular-nums;">'
            f'score {score:.2f}</div>'
            f'</div>'
        )
    return f'<div style="display:flex;gap:10px;flex-wrap:wrap;">{"".join(cards)}</div>'


def render_white_space(
    review: Any,
    deal_id: str,
    *,
    deal_name: str = "",
    error: Optional[str] = None,
    missing_fields: Optional[List[str]] = None,
    current_user: Optional[str] = None,
) -> str:
    label = deal_name or deal_id
    header = deal_header_nav(deal_id, active="white-space")

    if error:
        body = header + insufficient_data_banner(
            deal_id,
            title="White space",
            error=error,
            missing_fields=missing_fields,
        )
        return chartis_shell(
            body,
            title=f"White Space · {label}",
            active_nav="/pe-intelligence",
            subtitle=f"White-space scan unavailable for {label}",
        )

    ws = safe_dict(getattr(review, "white_space", None))
    if not ws or ws.get("error"):
        err = ws.get("error") if isinstance(ws, dict) else None
        body = header + small_panel(
            "White Space — not scored",
            empty_note(err or "White-space scan failed."),
            code="N/A",
        )
        return chartis_shell(
            body,
            title=f"White Space · {label}",
            active_nav="/pe-intelligence",
            subtitle=f"{label} · white-space scan unavailable",
        )

    opportunities = list(ws.get("opportunities", None) or [])
    top_dim = ws.get("top_dimension")
    note = str(ws.get("partner_note", "") or "")

    # Group by dimension for per-section display
    by_dim: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for o in opportunities:
        dim = str(o.get("dimension", "unknown") or "unknown")
        by_dim[dim].append(o)

    kpis = (
        ck_kpi_block("Opportunities", str(len(opportunities)), "across 3 dimensions")
        + ck_kpi_block("Top Dimension",
                        _html.escape(str(top_dim or "—")).upper(), "highest score")
        + ck_kpi_block("Geographic", str(len(by_dim.get("geographic", []))),
                        "states / regions")
        + ck_kpi_block("Segment", str(len(by_dim.get("segment", []))),
                        "service lines")
        + ck_kpi_block("Channel", str(len(by_dim.get("channel", []))),
                        "delivery channels")
    )
    kpi_strip = f'<div class="ck-kpi-grid">{kpis}</div>'

    if not opportunities:
        guidance = (
            f'<div style="color:{P["text_dim"]};font-size:11.5px;line-height:1.55;">'
            f'{_html.escape(note or "No white-space opportunities surfaced.")}'
            f'</div>'
            f'<div style="color:{P["text_faint"]};font-size:10.5px;margin-top:8px;'
            f'line-height:1.55;">'
            f'To surface more opportunities, add '
            f'<code style="color:{P["accent"]};font-family:var(--ck-mono);">'
            f'existing_states / existing_segments / existing_channels</code> and '
            f'<code style="color:{P["accent"]};font-family:var(--ck-mono);">'
            f'candidate_states / candidate_segments / candidate_channels</code> '
            f'lists under the deal profile.</div>'
        )
        body = header + kpi_strip + small_panel(
            "White Space — empty scan",
            guidance,
            code="NIL",
        )
        return chartis_shell(
            body,
            title=f"White Space · {label}",
            active_nav="/pe-intelligence",
            subtitle=f"{label} · no opportunities surfaced",
        )

    dim_sections = (
        _dimension_section("geographic", by_dim.get("geographic", []))
        + _dimension_section("segment", by_dim.get("segment", []))
        + _dimension_section("channel", by_dim.get("channel", []))
    )

    top_dim_col = _DIM_LABELS.get(str(top_dim or ""), (P["text_dim"],))[0] if top_dim else P["text_dim"]
    note_panel = (
        f'<div style="display:flex;gap:12px;align-items:baseline;'
        f'margin-bottom:10px;">'
        f'<span style="font-family:var(--ck-mono);font-size:9px;'
        f'color:{P["text_faint"]};letter-spacing:0.15em;">TOP DIMENSION</span>'
        f'{verdict_badge(str(top_dim or "—").upper(), color=P["accent"])}'
        f'</div>'
        + (
            f'<p style="color:{P["text"]};font-size:12px;line-height:1.55;'
            f'margin-bottom:10px;">{_html.escape(note)}</p>' if note else ""
        )
    )

    explainer = render_page_explainer(
        what=(
            "Adjacency opportunities for this target across three "
            "dimensions: geographic (states or regions the target "
            "does not cover), segment (service lines adjacent to the "
            "target's core), and channel (commercial direct, Medicare "
            "Advantage, ACO risk contracts, etc.)."
        ),
        scale=(
            "Each opportunity is scored 0–1 by blending addressable "
            "size, competitive intensity, and proximity-to-core. "
            "Scores above 0.75 are strong fit; 0.50–0.75 are fair; "
            "below 0.50 are low-conviction."
        ),
        use=(
            "Use this to size the post-close value-creation plan "
            "beyond the entry thesis. A 0.8 segment score is a case "
            "for bolt-on planning; a 0.3 score says the adjacency is "
            "in the brochure but not worth capital."
        ),
        source=(
            "pe_intelligence/white_space.py::detect_white_space "
            "(three-dimension scoring blending addressable size × "
            "competitive intensity × proximity-to-core)."
        ),
        page_key="deal-white-space",
    )

    body = (
        explainer
        + header
        + kpi_strip
        + ck_section_header(
            "TOP 3 OPPORTUNITIES",
            "ranked across all dimensions",
        )
        + small_panel("Ranked top-3", _top_opportunities_strip(opportunities), code="TOP")
        + ck_section_header(
            "BY DIMENSION",
            "geographic / segment / channel breakouts",
        )
        + small_panel("Brain verdict", note_panel, code="VRD")
        + dim_sections
    )

    return chartis_shell(
        body,
        title=f"White Space · {label}",
        active_nav="/pe-intelligence",
        subtitle=f"{label} · {len(opportunities)} opportunities · top: {top_dim or '—'}",
    )
