"""Markdown IC binder renderer.

Walks a SynthesisResult section-by-section and emits a markdown
document suitable for paste into Notion / Confluence / a Word doc
/ an email body.

Each section is rendered defensively — if the source attribute
is None (packet didn't run), the section is omitted from the
body and listed under "Data gaps" instead.
"""
from __future__ import annotations

from typing import Any, List


def _format_money(mm: float) -> str:
    if mm is None:
        return "—"
    if abs(mm) >= 1000:
        return f"${mm/1000:.2f}B"
    if abs(mm) >= 1:
        return f"${mm:.1f}M"
    return f"${mm*1000:.0f}K"


def _section_header(title: str) -> str:
    return f"\n## {title}\n"


def _payer_negotiation_section(rows: list) -> str:
    if not rows:
        return ""
    out: List[str] = [_section_header(
        "Payer Negotiation — modeled rates")]
    out.append("| NPI | Code | Rates seen | p25 | p75 | Modeled |")
    out.append("|---|---|---:|---:|---:|---:|")
    for r in rows[:15]:
        out.append(
            f"| {r['npi']} | {r['code']} | {r['rate_count']} | "
            f"${r.get('p25', 0):.0f} | ${r.get('p75', 0):.0f} | "
            f"${r.get('modeled_rate', 0):.0f} |")
    return "\n".join(out)


def _cohort_ltv_section(ltv: Any) -> str:
    if ltv is None:
        return ""
    out: List[str] = [_section_header(
        "Cohort LTV — Bridge v3")]
    out.append(
        f"- Starting lives: **{ltv.starting_lives:,}**, "
        f"horizon: {ltv.horizon_years} years")
    out.append(
        f"- Nominal LTV: **{_format_money(ltv.nominal_ltv)}** "
        f"({_format_money(ltv.nominal_ltv_per_life/1e6 if ltv.nominal_ltv_per_life else 0)} per life)")
    out.append(
        f"- Discounted LTV: **{_format_money(ltv.discounted_ltv)}**")
    if ltv.risk_score_by_year:
        out.append(
            f"- Risk score trajectory: "
            f"{', '.join(f'{r:.2f}' for r in ltv.risk_score_by_year)}")
    return "\n".join(out)


def _referral_section(payload: Any) -> str:
    if payload is None:
        return ""
    leakage = payload.get("leakage", {})
    risk = payload.get("key_person_risk", {})
    out: List[str] = [_section_header(
        "Referral Network — leakage + key-person risk")]
    rate = leakage.get("leakage_rate", 0)
    out.append(
        f"- Leakage rate: **{rate*100:.1f}%** "
        f"(${leakage.get('external_referral_volume', 0):.0f} "
        f"external vs ${leakage.get('internal_referral_volume', 0):.0f} "
        f"internal volume)")
    crit = risk.get("critical_count", 0)
    out.append(
        f"- Key-person risk: **{crit}** external referrer(s) "
        f"above the {risk.get('critical_threshold_pct', 0.2)*100:.0f}% "
        f"threshold")
    if risk.get("referrers"):
        top = risk["referrers"][0]
        out.append(
            f"- Top referrer NPI {top['npi']} drives "
            f"{top['share_of_inbound']*100:.0f}% of platform inbound")
    return "\n".join(out)


def _regulatory_section(payload: Any) -> str:
    if payload is None:
        return ""
    exposure = payload.get("exposure")
    if not exposure:
        return ""
    out: List[str] = [_section_header(
        "Regulatory Risk — topic exposure")]
    out.append(
        f"- Total EBITDA at risk: "
        f"**{_format_money(exposure.total_at_risk_mm)}**")
    if exposure.topic_exposures:
        out.append("")
        out.append("| Topic | $ at risk | Docs | Avg relevance |")
        out.append("|---|---:|---:|---:|")
        for t in exposure.topic_exposures[:5]:
            out.append(
                f"| {t.label} | "
                f"{_format_money(t.ebitda_at_risk_mm)} | "
                f"{t.n_documents} | {t.relevance:.2f} |")
    return "\n".join(out)


def _qoe_section(qoe: Any) -> str:
    if qoe is None:
        return ""
    out: List[str] = [_section_header(
        "QoE Auto-Flagger — EBITDA adjustments")]
    bridge = getattr(qoe, "ebitda_bridge", None)
    if bridge:
        out.append(
            f"- Reported EBITDA: "
            f"**{_format_money(bridge.reported_ebitda_mm)}** → "
            f"adjusted: "
            f"**{_format_money(bridge.adjusted_ebitda_mm)}** "
            f"(confidence-weighted: "
            f"{_format_money(bridge.confidence_weighted_adjusted_ebitda_mm)})")
    flags = getattr(qoe, "flags", []) or []
    if flags:
        out.append(f"- {len(flags)} flag(s) raised:")
        for f in flags[:6]:
            out.append(
                f"  - **{f.category}** — {f.title}: "
                f"{_format_money(f.proposed_adjustment_mm)} "
                f"(confidence {f.confidence:.0%})")
    nwc = getattr(qoe, "nwc_normalization", None)
    if nwc and nwc.proposed_peg_mm:
        out.append(
            f"- NWC peg: TTM avg "
            f"{_format_money(nwc.ttm_average_mm)}; "
            f"proposed "
            f"**{_format_money(nwc.proposed_peg_mm)}** "
            f"({'excluded ' + nwc.excluded_period if nwc.excluded_period else 'no period excluded'})")
    return "\n".join(out)


def _buyandbuild_section(bb: Any) -> str:
    if bb is None:
        return ""
    out: List[str] = [_section_header(
        "Buy-and-Build — optimal sequence")]
    out.append(
        f"- Sequence ({len(bb.sequence)} add-ons): "
        f"{', '.join(bb.sequence) if bb.sequence else '—'}")
    out.append(
        f"- Cumulative value: "
        f"**{_format_money(bb.cumulative_value_mm)}** "
        f"on **{_format_money(bb.cumulative_capital_mm)}** capital")
    out.append(
        f"- Cumulative regulatory blocking probability: "
        f"{bb.cumulative_block_prob*100:.1f}%")
    out.append(
        f"- Synergy share captured: "
        f"{bb.synergy_share*100:.1f}% of platform EBITDA")
    return "\n".join(out)


def _exit_readiness_section(er: Any) -> str:
    if er is None:
        return ""
    out: List[str] = [_section_header(
        "Exit Readiness — 7-archetype valuation")]
    out.append(
        f"- Recommended archetype: "
        f"**{er.recommended_archetype.value}** "
        f"(EV {_format_money(er.recommended_ev_mm)})")
    if er.valuations:
        out.append("")
        out.append("| Archetype | EV | Multiple | Confidence |")
        out.append("|---|---:|---:|---:|")
        for v in er.valuations:
            out.append(
                f"| {v.archetype.value} | "
                f"{_format_money(v.enterprise_value_mm)} | "
                f"{v.implied_multiple:.2f}x | "
                f"{v.confidence:.0%} |")
    if er.readiness_gaps:
        out.append("")
        out.append("**Readiness gaps:**")
        for g in er.readiness_gaps[:5]:
            out.append(
                f"- [{g.severity.upper()}] {g.title} — "
                f"{g.months_to_remediate}mo to fix")
    return "\n".join(out)


def _vbc_track_section(track: Any) -> str:
    if track is None:
        return ""
    out: List[str] = [_section_header(
        "VBC Contract — optimal Track choice")]
    rec = track.get("recommended")
    out.append(f"- Recommended Track: **{rec}**")
    reasoning = track.get("reasoning", "")
    if reasoning:
        out.append(f"- {reasoning}")
    return "\n".join(out)


def _esg_section(esg: Any, disclosure_md: str) -> str:
    if esg is None:
        return ""
    out: List[str] = [_section_header(
        "ESG — EDCI scorecard")]
    out.append(f"- Maturity band: **{esg.maturity_band}**")
    out.append(f"- Metrics reported: {esg.metric_count}")
    if disclosure_md:
        out.append("")
        out.append(disclosure_md)
    return "\n".join(out)


def _comparables_section(comps: Any) -> str:
    if comps is None:
        return ""
    out: List[str] = [_section_header(
        "Comparables Engine — matched comps")]
    out.append(f"- Method: **{comps.method}**, "
               f"matches: {comps.n_matches}")
    edist = comps.entry_multiple_distribution
    if edist.get("p50") is not None:
        out.append(
            f"- Entry multiple distribution: "
            f"p25 {edist.get('p25', 0):.1f}x, "
            f"p50 {edist['p50']:.1f}x, "
            f"p75 {edist.get('p75', 0):.1f}x")
    me = comps.margin_expansion_distribution
    if me.get("p50") is not None:
        out.append(
            f"- Median margin expansion among comps: "
            f"{me['p50']*100:+.1f} pp")
    return "\n".join(out)


def _irr_section(attr: Any, lp_md: str) -> str:
    if attr is None:
        return ""
    out: List[str] = [_section_header(
        "IRR Attribution — ILPA 2.0")]
    out.append(
        f"- Gross IRR: **{attr.irr*100:.1f}%** · "
        f"MOIC **{attr.moic:.2f}x**")
    out.append(
        f"- Total value created: "
        f"**{_format_money(attr.components.total_value_created_mm)}**")
    if lp_md:
        out.append("")
        out.append(lp_md)
    return "\n".join(out)


def _joint_tail_section(payload: Any) -> str:
    if payload is None:
        return ""
    out: List[str] = [_section_header(
        "MC v3 — Joint-tail healthcare shock")]
    cms = payload.get("cms_rate_shock")
    com = payload.get("commercial_rate_shock")
    lab = payload.get("labor_inflation_shock")
    if cms is None or com is None or lab is None:
        return ""
    import numpy as np
    p5_cms = float(np.percentile(cms, 5))
    p5_com = float(np.percentile(com, 5))
    p95_lab = float(np.percentile(lab, 95))
    out.append(
        f"- 5th-percentile CMS rate shock: **{p5_cms*100:+.1f}%**")
    out.append(
        f"- 5th-percentile commercial rate shock: "
        f"**{p5_com*100:+.1f}%**")
    out.append(
        f"- 95th-percentile labor inflation shock: "
        f"**{p95_lab*100:+.1f}%**")
    out.append(
        "- Joint Clayton-coupled — bear case is the simultaneous "
        "hit of all three.")
    return "\n".join(out)


def _themes_section(themes: Any, heatmap: Any,
                    universe: Any) -> str:
    if themes is None:
        return ""
    out: List[str] = [_section_header(
        "Sector Themes — emerging-theme positioning")]
    if heatmap:
        out.append("**Theme density by period:**")
        for theme_id, periods in heatmap.items():
            top_period = max(periods.items(),
                             key=lambda kv: kv[1],
                             default=(None, 0))
            if top_period[0]:
                out.append(
                    f"- {theme_id}: peak {top_period[0]} "
                    f"@ {top_period[1]:.2f}")
    if universe:
        out.append("")
        out.append(
            f"**Thesis-aligned universe** (top {len(universe)} "
            f"deals):")
        for entry in universe[:5]:
            out.append(
                f"- {entry.doc_id} — composite "
                f"{entry.composite_score:.2f}")
    return "\n".join(out)


def render_markdown_binder(synthesis_result: Any) -> str:
    """Top-level entry. Returns a single markdown string ready to
    paste into a partner's IC pre-read."""
    deal_name = synthesis_result.deal_name or "Untitled Deal"
    sections_run = synthesis_result.sections_run or []
    missing = synthesis_result.missing_inputs or []

    body: List[str] = []
    body.append(f"# IC Binder — {deal_name}")
    body.append("")
    body.append(
        f"**Sections complete:** {len(sections_run)} of 13. "
        f"**Open data gaps:** {len(missing)}.")

    body.append(_payer_negotiation_section(
        synthesis_result.payer_negotiation))
    body.append(_cohort_ltv_section(synthesis_result.cohort_ltv))
    body.append(_referral_section(
        synthesis_result.referral_leakage))
    body.append(_regulatory_section(
        synthesis_result.regulatory_exposure))
    body.append(_qoe_section(synthesis_result.qoe_result))
    body.append(_buyandbuild_section(
        synthesis_result.buyandbuild_optimal))
    body.append(_exit_readiness_section(
        synthesis_result.exit_readiness))
    body.append(_vbc_track_section(
        synthesis_result.vbc_track_choice))
    body.append(_esg_section(
        synthesis_result.esg_scorecard,
        getattr(synthesis_result, "esg_disclosure_md", "")))
    body.append(_comparables_section(
        synthesis_result.comparables))
    body.append(_irr_section(
        synthesis_result.irr_attribution,
        getattr(synthesis_result, "irr_attribution_lp_md", "")))
    body.append(_joint_tail_section(
        synthesis_result.joint_tail_shock))
    body.append(_themes_section(
        synthesis_result.sector_themes,
        synthesis_result.theme_heatmap,
        synthesis_result.target_universe))

    if missing:
        body.append("\n## Data Gaps")
        for m in missing:
            body.append(f"- {m}")

    return "\n".join(filter(None, body)) + "\n"
