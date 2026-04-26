"""Per-deal Deal Archetype + Regime — /deal/<id>/archetype.

Renders two orthogonal classifications:

  - ``pe_intelligence.deal_archetype.classify_archetypes(ctx)`` —
    sponsor-structure archetype (platform-rollup / take-private /
    carve-out / turnaround / buy-and-build / continuation /
    GP-led secondary / PIPE / operating-lift / growth equity) plus
    per-archetype lever stack, named risks, and IC questions.
  - ``pe_intelligence.regime_classifier.classify_regime(inputs)`` —
    time-series regime (durable_growth / emerging_volatile /
    steady / stagnant / declining_risk) with confidence + signals +
    playbook + key risk.

Both are run fresh here rather than read from the PartnerReview,
because the review only carries the regime dict — the richer
archetype output (playbook, risks, questions) isn't on the review.
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
    bullet_list,
    deal_header_nav,
    empty_note,
    flat_get,
    fmt_pct,
    insufficient_data_banner,
    kv_list,
    render_page_explainer,
    safe_dict,
    small_panel,
    verdict_badge,
)
from ._sanity import render_number


_REGIME_COLORS = {
    "durable_growth": P["positive"],
    "emerging_volatile": P["warning"],
    "steady": P["accent"],
    "stagnant": P["text_dim"],
    "declining_risk": P["negative"],
}

_CONFIDENCE_BANDS = [
    (0.75, P["positive"], "HIGH"),
    (0.5, P["warning"], "MEDIUM"),
    (0.0, P["text_faint"], "LOW"),
]


def _confidence_band(score: float) -> tuple[str, str]:
    for thresh, col, label in _CONFIDENCE_BANDS:
        if score >= thresh:
            return col, label
    return P["text_faint"], "UNKNOWN"


def _build_archetype_context(profile: Dict[str, Any], packet: Any) -> Any:
    """Assemble an ArchetypeContext from the packet + deal profile.

    Most ArchetypeContext fields are deal-structure metadata that isn't
    on the packet (is_carveout, seller_is_strategic, etc.). We pull what
    we can from the profile and let the rest default to None — the
    classifier is defensive and scores what it can.
    """
    from rcm_mc.pe_intelligence.deal_archetype import ArchetypeContext

    hospital_type = profile.get("hospital_type") or profile.get("facility_type")

    # Pull the quantitative fields the classifier uses off whatever
    # is closest: the packet's observed metrics first, then the profile.
    def _pfield(name: str) -> Any:
        return profile.get(name)

    def _obsfield(name: str) -> Optional[float]:
        if packet is None:
            return None
        obs = getattr(packet, "observed_metrics", None)
        if obs is None and isinstance(packet, dict):
            obs = packet.get("observed_metrics")
        if obs is None:
            return None
        if isinstance(obs, dict):
            v = obs.get(name)
        else:
            v = getattr(obs, name, None)
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, dict):
            try:
                return float(v.get("value"))
            except (TypeError, ValueError):
                return None
        try:
            return float(getattr(v, "value", None))
        except (TypeError, ValueError):
            return None

    margin = _obsfield("ebitda_margin") or _pfield("ebitda_margin")
    try:
        margin = float(margin) if margin is not None else None
    except (TypeError, ValueError):
        margin = None
    # Heuristic: values >1 are percents — normalize.
    if margin is not None and margin > 1.5:
        margin = margin / 100.0

    return ArchetypeContext(
        hospital_type=str(hospital_type) if hospital_type else None,
        platform_or_addon=_pfield("platform_or_addon"),
        number_of_addons_planned=_pfield("number_of_addons_planned"),
        is_public_target=_pfield("is_public_target"),
        is_carveout=_pfield("is_carveout"),
        seller_is_strategic=_pfield("seller_is_strategic"),
        seller_is_sponsor=_pfield("seller_is_sponsor"),
        is_continuation_vehicle=_pfield("is_continuation_vehicle"),
        is_minority=_pfield("is_minority"),
        ownership_pct=_pfield("ownership_pct"),
        current_ebitda_margin=margin,
        peer_median_margin=_pfield("peer_median_margin"),
        debt_to_ebitda=_obsfield("net_debt_to_ebitda") or _pfield("debt_to_ebitda"),
        is_distressed=_pfield("is_distressed"),
        revenue_growth_pct=_obsfield("revenue_growth_pct"),
        ebitda_growth_pct=_obsfield("ebitda_growth_pct"),
        has_rcm_thesis=_pfield("has_rcm_thesis"),
        has_rollup_thesis=_pfield("has_rollup_thesis"),
        has_turnaround_thesis=_pfield("has_turnaround_thesis"),
        plans_go_private=_pfield("plans_go_private"),
    )


def _archetype_card(hit: Any, *, primary: bool = False) -> str:
    title = _html.escape(str(getattr(hit, "archetype", "—")))
    confidence = float(getattr(hit, "confidence", 0.0) or 0.0)
    conf_col, conf_label = _confidence_band(confidence)
    signals = list(getattr(hit, "signals", None) or [])
    playbook = list(getattr(hit, "playbook", None) or [])
    risks = list(getattr(hit, "risks", None) or [])
    questions = list(getattr(hit, "questions", None) or [])

    primary_tag = ""
    border_col = P["border"]
    if primary:
        primary_tag = (
            f'<span style="font-family:var(--ck-mono);font-size:9px;'
            f'font-weight:700;letter-spacing:0.12em;color:{P["accent"]};'
            f'margin-left:10px;">PRIMARY</span>'
        )
        border_col = P["accent"]

    return (
        f'<div style="background:{P["panel"]};border:1px solid {border_col};'
        f'border-radius:3px;padding:14px 16px;margin-bottom:12px;">'
        f'<div style="display:flex;align-items:baseline;gap:10px;'
        f'margin-bottom:8px;">'
        f'<span style="font-family:var(--ck-mono);font-size:13px;'
        f'font-weight:700;letter-spacing:0.06em;color:{P["text"]};'
        f'text-transform:uppercase;">{title}</span>'
        f'{primary_tag}'
        f'<span style="margin-left:auto;font-family:var(--ck-mono);'
        f'font-size:10px;color:{P["text_faint"]};">CONFIDENCE</span>'
        f'{verdict_badge(f"{confidence:.2f} · {conf_label}", color=conf_col)}'
        f'</div>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;">'
        f'<div>'
        f'<div style="font-family:var(--ck-mono);font-size:9px;'
        f'letter-spacing:0.12em;color:{P["text_faint"]};margin-bottom:4px;">'
        f'SIGNALS</div>'
        f'{bullet_list(signals, color=P["text_dim"])}'
        f'</div>'
        f'<div>'
        f'<div style="font-family:var(--ck-mono);font-size:9px;'
        f'letter-spacing:0.12em;color:{P["text_faint"]};margin-bottom:4px;">'
        f'PLAYBOOK</div>'
        f'{bullet_list(playbook, color=P["text"])}'
        f'</div>'
        f'</div>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;'
        f'margin-top:10px;">'
        f'<div>'
        f'<div style="font-family:var(--ck-mono);font-size:9px;'
        f'letter-spacing:0.12em;color:{P["negative"]};margin-bottom:4px;">'
        f'NAMED RISKS</div>'
        f'{bullet_list(risks, color=P["text_dim"])}'
        f'</div>'
        f'<div>'
        f'<div style="font-family:var(--ck-mono);font-size:9px;'
        f'letter-spacing:0.12em;color:{P["warning"]};margin-bottom:4px;">'
        f'IC QUESTIONS</div>'
        f'{bullet_list(questions, color=P["text"])}'
        f'</div>'
        f'</div>'
        f'</div>'
    )


def _regime_panel(review: Any) -> str:
    regime_dict = safe_dict(getattr(review, "regime", None))
    if not regime_dict or regime_dict.get("error"):
        err = regime_dict.get("error") if isinstance(regime_dict, dict) else None
        return empty_note(err or "Regime classification unavailable.")
    regime = str(regime_dict.get("regime", "—"))
    col = _REGIME_COLORS.get(regime, P["text_dim"])
    confidence = regime_dict.get("confidence", 0.0)
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.0
    conf_col, conf_label = _confidence_band(confidence)
    note = str(regime_dict.get("partner_note", "") or "")
    playbook = str(regime_dict.get("playbook", "") or "")
    key_risk = str(regime_dict.get("key_risk", "") or "")
    signals = list(regime_dict.get("signals", None) or [])

    return (
        f'<div style="display:flex;gap:14px;align-items:center;margin-bottom:10px;">'
        f'<div style="font-family:var(--ck-mono);font-size:22px;font-weight:700;'
        f'letter-spacing:0.04em;color:{col};text-transform:uppercase;">'
        f'{_html.escape(regime)}</div>'
        f'{verdict_badge(f"{confidence:.2f} · {conf_label}", color=conf_col)}'
        f'</div>'
        + (
            f'<p style="color:{P["text"]};font-size:12px;line-height:1.55;'
            f'margin-bottom:8px;">{_html.escape(note)}</p>'
            if note else ""
        )
        + f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px;'
        f'margin-top:10px;">'
        f'<div>'
        f'<div style="font-family:var(--ck-mono);font-size:9px;'
        f'letter-spacing:0.12em;color:{P["text_faint"]};margin-bottom:4px;">'
        f'SIGNALS</div>'
        f'{bullet_list(signals, color=P["text_dim"])}'
        f'</div>'
        f'<div>'
        f'<div style="font-family:var(--ck-mono);font-size:9px;'
        f'letter-spacing:0.12em;color:{P["positive"]};margin-bottom:4px;">'
        f'PLAYBOOK</div>'
        f'<p style="color:{P["text"]};font-size:11px;line-height:1.55;">'
        f'{_html.escape(playbook) or "—"}</p>'
        f'</div>'
        f'<div>'
        f'<div style="font-family:var(--ck-mono);font-size:9px;'
        f'letter-spacing:0.12em;color:{P["negative"]};margin-bottom:4px;">'
        f'KEY RISK</div>'
        f'<p style="color:{P["text"]};font-size:11px;line-height:1.55;">'
        f'{_html.escape(key_risk) or "—"}</p>'
        f'</div>'
        f'</div>'
    )


def render_archetype(
    review: Any,
    deal_id: str,
    *,
    deal_name: str = "",
    archetype_hits: Optional[List[Any]] = None,
    primary: Optional[str] = None,
    archetype_context: Any = None,
    error: Optional[str] = None,
    missing_fields: Optional[List[str]] = None,
    current_user: Optional[str] = None,
) -> str:
    label = deal_name or deal_id
    header = deal_header_nav(deal_id, active="archetype")

    if error:
        body = header + insufficient_data_banner(
            deal_id,
            title="Archetype scan",
            error=error,
            missing_fields=missing_fields,
        )
        return chartis_shell(
            body,
            title=f"Archetype · {label}",
            active_nav="/pe-intelligence",
        breadcrumbs=[
            ("Home", "/app"),
            ("Deals", "/deals"),
            ("Archetype", None),
        ],
            subtitle=f"Archetype unavailable for {label}",
        )

    hits = list(archetype_hits or [])
    n_archetypes = len(hits)
    primary_name = primary or (hits[0].archetype if hits else "—")

    regime_dict = safe_dict(getattr(review, "regime", None))
    regime_label = str(regime_dict.get("regime", "—")) if regime_dict else "—"

    kpis = (
        ck_kpi_block("Primary Archetype", _html.escape(primary_name), "highest confidence")
        + ck_kpi_block("Total Matches", str(n_archetypes), "over 25% confidence")
        + ck_kpi_block("Regime", _html.escape(regime_label), "time-series read")
        + ck_kpi_block(
            "Regime Confidence",
            f'{float(regime_dict.get("confidence", 0.0) or 0.0):.2f}',
            "0-1 score",
        )
    )
    kpi_strip = f'<div class="ck-kpi-grid">{kpis}</div>'

    # Archetype section
    archetype_header = ck_section_header(
        "SPONSOR-STRUCTURE ARCHETYPES",
        "playbook + named risks + IC questions per shape",
        count=n_archetypes,
    )
    if hits:
        archetype_cards = "".join(
            _archetype_card(h, primary=(i == 0)) for i, h in enumerate(hits)
        )
    else:
        archetype_cards = small_panel(
            "No archetype matched",
            empty_note(
                "The classifier did not find any archetype scoring above the "
                "0.25 confidence threshold. Most likely cause: the deal "
                "profile is missing structural metadata (platform_or_addon, "
                "is_carveout, has_rollup_thesis, etc.). Open the analysis "
                "workbench and fill those fields."
            ),
            code="NIL",
        )

    # Context-used panel so partners can see what was fed in
    ctx = archetype_context
    ctx_fields = []
    if ctx is not None:
        ctx_fields = [
            ("hospital_type", str(ctx.hospital_type or "—")),
            ("platform_or_addon", str(ctx.platform_or_addon or "—")),
            ("addons_planned", str(ctx.number_of_addons_planned or "—")),
            ("current_margin", render_number(ctx.current_ebitda_margin, "ebitda_margin")),
            ("debt_to_ebitda", render_number(ctx.debt_to_ebitda, "leverage_multiple")),
            ("revenue_growth", fmt_pct(ctx.revenue_growth_pct)),
            ("ebitda_growth", fmt_pct(ctx.ebitda_growth_pct)),
            ("has_rollup_thesis", str(ctx.has_rollup_thesis)),
            ("has_rcm_thesis", str(ctx.has_rcm_thesis)),
            ("has_turnaround_thesis", str(ctx.has_turnaround_thesis)),
            ("is_carveout", str(ctx.is_carveout)),
            ("seller_is_strategic", str(ctx.seller_is_strategic)),
            ("is_distressed", str(ctx.is_distressed)),
        ]
    ctx_panel = small_panel(
        "Classifier inputs",
        kv_list(ctx_fields),
        code="CTX",
    )

    # Regime section
    regime_section = ck_section_header(
        "REGIME CLASSIFICATION",
        "time-series read of the target",
    )
    regime_body = small_panel("Regime verdict", _regime_panel(review), code="REG")

    explainer = render_page_explainer(
        what=(
            "Two orthogonal classifications for this deal: the "
            "sponsor-structure archetype(s) it matches, and the "
            "performance regime it sits in based on historical "
            "trends."
        ),
        scale=(
            "10 archetypes: platform_rollup, take_private, carve_out, "
            "turnaround, buy_and_build, continuation, gp_led_secondary, "
            "pipe, operating_lift, growth_equity. 5 regimes: "
            "durable_growth, emerging_volatile, steady, stagnant, "
            "declining_risk. Confidence score on both: HIGH ≥ 0.75, "
            "MEDIUM ≥ 0.50, LOW below."
        ),
        use=(
            "Each matched archetype carries its own playbook, named "
            "risks, and IC-question list — use those as the diligence "
            "scaffold. The regime classifier tells you which playbook "
            "tone fits (e.g. steady → operating levers carry the "
            "return, not multiple expansion)."
        ),
        source=(
            "pe_intelligence/deal_archetype.py::classify_archetypes; "
            "regime_classifier.py (five regime definitions + playbook)."
        ),
        page_key="deal-archetype",
    )

    body = (
        explainer
        + header
        + kpi_strip
        + archetype_header
        + archetype_cards
        + ctx_panel
        + regime_section
        + regime_body
    )

    return chartis_shell(
        body,
        title=f"Archetype · {label}",
        active_nav="/pe-intelligence",
        breadcrumbs=[
            ("Home", "/app"),
            ("Deals", "/deals"),
            ("Archetype", None),
        ],
        subtitle=f"{label} · archetype match + regime classification",
    )
