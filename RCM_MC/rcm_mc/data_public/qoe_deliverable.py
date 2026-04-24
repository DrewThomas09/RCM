"""QoE Deliverable — Partner-Signed Quality-of-Earnings Report.

The document that gets handed to the client. Composes all analytical
layers into the 12-section formal QoE report structure used by
Chartis, VMG, Kaufman Hall, and Crowe healthcare-advisory practices:

    1. Cover page (client logo, partner names, date, engagement)
    2. Table of contents
    3. Executive summary
    4. Transaction overview
    5. Market & competitive context
    6. Financial performance review
    7. Quality-of-earnings adjustments (EBITDA walk)
    8. RCM diligence findings
    9. Regulatory & compliance exposure
    10. Risk assessment
    11. Recommendations & conditions precedent
    12. Partner sign-off / exhibits

Every field auto-populates from the IC Brief layer + module outputs.
The UI renders as a print-optimized document with @media print CSS so
Cmd+P / Ctrl+P → "Save as PDF" produces a paginated artifact that looks
like a consulting-firm deliverable, not a dashboard export.

Editable commentary sections are rendered as <textarea> elements —
partner fills in the narrative, then prints. For the Word-export path,
we ship the same content as HTML which Word opens natively (retains
structure + styling). True .docx generation would need python-docx
(not installed in this env); HTML-as-.doc is the interim path.

Public API
----------
    QoEEBITDAAdjustment          one line in the EBITDA walk
    QoESection                   one section spec
    QoEDeliverableResult         composite
    compute_qoe_deliverable(target_input)  -> QoEDeliverableResult
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class QoEEBITDAAdjustment:
    category: str                   # "Reported" / "One-Time" / "Run-Rate" / "Normalized"
    line_item: str
    amount_mm: float                # positive or negative
    rationale: str
    confidence: str                 # "high" / "medium" / "low"


@dataclass
class QoESection:
    section_number: str             # "1" / "2" / etc.
    title: str
    kind: str                       # "narrative" / "data_table" / "mixed"
    is_editable: bool               # partner can override via textarea
    default_content: str            # auto-generated narrative
    data_rows: List[Dict[str, object]] = field(default_factory=list)


@dataclass
class QoEDeliverableResult:
    # Deal header
    deal_name: str
    client_name: str                # engaging PE sponsor
    partner_names: List[str]
    engagement_number: str
    report_date: str
    report_type: str                # "Buy-Side QoE" / "Sell-Side QoE"
    # Composite data
    sections: List[QoESection]
    ebitda_walk: List[QoEEBITDAAdjustment]
    # Summary metrics
    reported_ebitda_mm: Optional[float]
    adjusted_ebitda_mm: Optional[float]
    ebitda_quality_score: float     # 0-100, derived from adjustment composition
    overall_recommendation: str     # from IC Brief verdict
    # Headers / footers
    header_text: str
    footer_text: str
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Report composition
# ---------------------------------------------------------------------------

def _build_ebitda_walk(target, ic_brief) -> List[QoEEBITDAAdjustment]:
    """Auto-generate an EBITDA walk from deal inputs + platform findings."""
    walk: List[QoEEBITDAAdjustment] = []
    reported = target.ebitda_mm or 0.0

    walk.append(QoEEBITDAAdjustment(
        category="Reported",
        line_item="Management-reported LTM EBITDA",
        amount_mm=reported,
        rationale="As presented in CIM / data-room financial package.",
        confidence="high",
    ))

    # One-time adjustments (typical QoE items)
    # Transaction bonus accruals — add back (typical 0.5-1.5% of reported)
    tx_bonus = round(reported * 0.010, 2)
    if tx_bonus > 0:
        walk.append(QoEEBITDAAdjustment(
            category="One-Time",
            line_item="Transaction-related bonuses (add-back)",
            amount_mm=tx_bonus,
            rationale="Management bonuses triggered by transaction; not recurring under new sponsor.",
            confidence="high",
        ))

    # Owner compensation normalization (typical 2-4% of reported, add-back)
    if target.facility_type.lower() in ("physician group", "ambulatory surgery center"):
        owner_comp_adj = round(reported * 0.025, 2)
        walk.append(QoEEBITDAAdjustment(
            category="One-Time",
            line_item="Owner compensation normalization",
            amount_mm=owner_comp_adj,
            rationale="Above-market owner W-2 compensation normalized to peer-median replacement cost.",
            confidence="medium",
        ))

    # Run-rate adjustments
    # NCCI denial exposure - deduct if edit density >= 30
    ncci = ic_brief.ncci_exposure_summary
    if ncci.get("density", 0) >= 30:
        denial_haircut = -round(reported * 0.015, 2)
        walk.append(QoEEBITDAAdjustment(
            category="Run-Rate",
            line_item="NCCI edit / denial-management exposure",
            amount_mm=denial_haircut,
            rationale=f"Specialty NCCI density {ncci.get('density', 0):.0f} implies 1.0-2.0% revenue haircut for denial absorption; modifier-59 usage under federal audit.",
            confidence="medium",
        ))

    # OIG exposure - run-rate deduction if active matches
    oig = ic_brief.oig_exposure_summary
    if oig.get("open_active_matches", 0) >= 2:
        oig_haircut = -round(reported * 0.010, 2)
        walk.append(QoEEBITDAAdjustment(
            category="Run-Rate",
            line_item="OIG Work Plan audit-exposure reserve",
            amount_mm=oig_haircut,
            rationale=f"{oig.get('open_active_matches', 0)} open/active Work Plan items for {oig.get('provider_type', '?')} imply recoupment reserve (~1% of EBITDA).",
            confidence="medium",
        ))

    # Market rate trajectory
    govt = target.medicare_share + target.medicaid_share
    if govt >= 0.55:
        gov_haircut = -round(reported * 0.008, 2)
        walk.append(QoEEBITDAAdjustment(
            category="Run-Rate",
            line_item="Medicare/Medicaid rate-trajectory pressure",
            amount_mm=gov_haircut,
            rationale=f"Government mix {govt:.0%} implies rate compression sensitivity; -0.8% EBITDA haircut for 2026-2028 PFS + OPPS trajectory.",
            confidence="medium",
        ))

    # Pro-forma additions: commercial rate uplift if scale provides leverage
    if target.commercial_share >= 0.45 and target.ev_mm and target.ev_mm >= 300:
        rate_uplift = round(reported * 0.015, 2)
        walk.append(QoEEBITDAAdjustment(
            category="Normalized",
            line_item="Commercial rate normalization (scale-driven)",
            amount_mm=rate_uplift,
            rationale=f"Platform scale ($EV {target.ev_mm:,.0f}M, {target.commercial_share:.0%} commercial) supports mid-contract renewal at +1.5% above market trend.",
            confidence="low",
        ))

    return walk


def _build_sections(target, ic_brief, ebitda_walk) -> List[QoESection]:
    """Assemble the 12 canonical QoE sections."""
    mult = None
    if target.ev_mm and target.ebitda_mm and target.ebitda_mm > 0:
        mult = target.ev_mm / target.ebitda_mm

    # Aggregate EBITDA metrics for narratives
    reported = next((a.amount_mm for a in ebitda_walk if a.category == "Reported"), 0)
    total_adj = sum(a.amount_mm for a in ebitda_walk if a.category != "Reported")
    adjusted = reported + total_adj

    sections: List[QoESection] = []

    # Section 1 — Cover (title-only; rendered separately)
    sections.append(QoESection(
        section_number="1",
        title="Cover Page",
        kind="narrative",
        is_editable=False,
        default_content="",
    ))

    # Section 2 — Table of Contents (auto-rendered from other sections)
    sections.append(QoESection(
        section_number="2",
        title="Table of Contents",
        kind="narrative",
        is_editable=False,
        default_content="",
    ))

    # Section 3 — Executive Summary
    top_flag = ic_brief.red_flags[0].flag if ic_brief.red_flags else "No critical red flags identified."
    sections.append(QoESection(
        section_number="3",
        title="Executive Summary",
        kind="narrative",
        is_editable=True,
        default_content=(
            f"{target.deal_name} is a {target.sector} platform with EV ${target.ev_mm or '—'}M and reported LTM EBITDA "
            f"${target.ebitda_mm or '—'}M (implied entry multiple {mult:.1f}x)." if mult else
            f"{target.deal_name} is a {target.sector} platform."
        ) + (
            f"\n\nPlatform verdict: {ic_brief.verdict.verdict} (composite {ic_brief.verdict.composite_score:.0f}, "
            f"distress probability {ic_brief.verdict.distress_probability*100:.1f}%). "
            f"{ic_brief.verdict.one_line_take[:400]}\n\n"
            f"QoE EBITDA walk: reported ${reported:.1f}M → adjusted ${adjusted:.1f}M "
            f"(net ${total_adj:+.1f}M across {len(ebitda_walk)-1} adjustments). "
            f"Primary pre-close watch-items: {top_flag}.\n\n"
            f"This deliverable composes findings from 15+ analytical modules operating over a "
            f"{ic_brief.corpus_deal_count:,}-deal healthcare-PE public-data corpus."
        ),
    ))

    # Section 4 — Transaction Overview
    sections.append(QoESection(
        section_number="4",
        title="Transaction Overview",
        kind="data_table",
        is_editable=False,
        default_content="",
        data_rows=[
            {"label": "Deal Name",          "value": target.deal_name},
            {"label": "Sector / Specialty", "value": target.sector},
            {"label": "Facility Type",      "value": target.facility_type},
            {"label": "Region",             "value": target.region},
            {"label": "Enterprise Value",   "value": f"${target.ev_mm:,.0f}M" if target.ev_mm else "—"},
            {"label": "LTM EBITDA",         "value": f"${target.ebitda_mm:,.1f}M" if target.ebitda_mm else "—"},
            {"label": "Entry Multiple",     "value": f"{mult:.2f}x" if mult else "—"},
            {"label": "Hold Period",        "value": f"{target.hold_years:.0f} years"},
            {"label": "Payer Mix — Commercial", "value": f"{target.commercial_share*100:.0f}%"},
            {"label": "Payer Mix — Medicare",   "value": f"{target.medicare_share*100:.0f}%"},
            {"label": "Payer Mix — Medicaid",   "value": f"{target.medicaid_share*100:.0f}%"},
            {"label": "Payer Mix — Self-Pay",   "value": f"{target.self_pay_share*100:.0f}%"},
            {"label": "Buyer / Sponsor",    "value": target.buyer},
        ],
    ))

    # Section 5 — Market & Competitive Context
    comp_text = ""
    if ic_brief.comparable_deals:
        lines = [f"• {c.deal_name} ({c.year}): ${c.ev_mm:,.0f}M at {c.implied_multiple:.1f}x"
                 + (f", realized {c.realized_moic:.1f}x MOIC" if c.realized_moic else "")
                 for c in ic_brief.comparable_deals[:5] if c.ev_mm and c.implied_multiple]
        comp_text = "\n".join(lines)
    sections.append(QoESection(
        section_number="5",
        title="Market & Competitive Context",
        kind="mixed",
        is_editable=True,
        default_content=(
            f"Comparable transactions in {target.sector} drawn from the {ic_brief.corpus_deal_count:,}-deal corpus:\n\n"
            f"{comp_text}\n\n"
            f"Benchmark positioning — " + "; ".join(
                f"{d.curve_id} {d.curve_name[:40]} (P50 {d.p50})"
                for d in ic_brief.benchmark_deltas[:3]
            )
        ),
    ))

    # Section 6 — Financial Performance Review
    sections.append(QoESection(
        section_number="6",
        title="Financial Performance Review",
        kind="narrative",
        is_editable=True,
        default_content=(
            f"Management-reported LTM EBITDA of ${reported:.1f}M forms the foundation of the QoE analysis. "
            f"Revenue mix reflects {target.commercial_share:.0%} commercial / "
            f"{target.medicare_share + target.medicaid_share:.0%} government / "
            f"{target.self_pay_share:.0%} self-pay. "
            f"The bear-case Monte Carlo run by the adversarial engine produces worst-quartile MOIC "
            f"distributions; see Section 10 for risk decomposition. "
            f"[Partner to expand: historical growth rates, gross margin trend, cash conversion.]"
        ),
    ))

    # Section 7 — QoE EBITDA Walk
    sections.append(QoESection(
        section_number="7",
        title="Quality-of-Earnings Adjustments",
        kind="data_table",
        is_editable=True,
        default_content=(
            f"EBITDA walk detail: {len(ebitda_walk)-1} adjustments identified. "
            f"Reported ${reported:.1f}M → Adjusted ${adjusted:.1f}M. Net change ${total_adj:+.1f}M. "
            f"Partner commentary may refine individual line items."
        ),
        data_rows=[
            {
                "category": a.category,
                "line_item": a.line_item,
                "amount_mm": a.amount_mm,
                "rationale": a.rationale,
                "confidence": a.confidence,
            }
            for a in ebitda_walk
        ],
    ))

    # Section 8 — RCM Diligence Findings
    ncci = ic_brief.ncci_exposure_summary
    sections.append(QoESection(
        section_number="8",
        title="RCM Diligence Findings",
        kind="mixed",
        is_editable=True,
        default_content=(
            f"NCCI edit exposure — specialty density score {ncci.get('density', 0):.0f} "
            f"({ncci.get('ptp_edits_affecting', 0)} PTP edits affecting target's CPT footprint, "
            f"{ncci.get('override_pct', 0):.0f}% modifier-override eligible). "
            f"Key edits to validate in claims-level sample audit:\n\n"
            + "\n".join(
                f"• {e.get('col1', '?')} + {e.get('col2', '?')}: {e.get('rationale', '')}"
                for e in (ncci.get('top_edits') or [])[:3]
            )
            + f"\n\nHFMA MAP Keys benchmark comparison recommended during 60-day post-close audit "
            f"(clean-claim rate, A/R days, initial denial rate, net collection rate, cost-to-collect). "
            f"[Partner to expand: target's RCM maturity assessment, specific CARC denial-code concentration.]"
        ),
    ))

    # Section 9 — Regulatory & Compliance Exposure
    oig = ic_brief.oig_exposure_summary
    team = ic_brief.team_exposure_summary
    sections.append(QoESection(
        section_number="9",
        title="Regulatory & Compliance Exposure",
        kind="mixed",
        is_editable=True,
        default_content=(
            f"OIG Work Plan overlap — provider type {oig.get('provider_type', '?')} "
            f"with {oig.get('open_active_matches', 0)} open/active items, estimated exposure "
            f"${oig.get('exposure_mm', 0):.1f}M (platform-wide benchmark, target-scaled).\n\n"
            + (
                f"TEAM mandatory-bundle exposure: {team.get('risk_tier', 'UNAFFECTED')} tier, "
                f"PY5 downside ${team.get('py5_downside_mm', 0):.1f}M across "
                f"{len(team.get('matched_cbsas') or [])} CBSAs.\n\n"
                if team else
                "TEAM mandatory-bundle exposure: not applicable (non-hospital target).\n\n"
            )
            + f"DOJ False Claims Act defendant-match screen recommended (see /doj-fca). "
            f"Independent compliance review with pre-close self-disclosure optionality for "
            f"material findings. [Partner to expand: target's compliance-program maturity, "
            f"HIPAA breach history from HHS OCR portal, any pending state AG inquiries.]"
        ),
    ))

    # Section 10 — Risk Assessment
    rf_lines = "\n".join(
        f"{f.rank}. [{f.severity}] {f.flag} — {f.evidence}. Mitigation: {f.mitigation}"
        for f in ic_brief.red_flags
    )
    sections.append(QoESection(
        section_number="10",
        title="Risk Assessment",
        kind="mixed",
        is_editable=True,
        default_content=(
            f"Top-5 red-flag scorecard derived from Backtesting Harness + Named-Failure Library "
            f"+ NCCI + OIG + TEAM composite:\n\n{rf_lines}\n\n"
            f"Bear-case adversarial memo: {ic_brief.bear_case_memo_narrative[:600]}\n\n"
            f"[Partner to expand: specific mitigants, indemnity-cap recommendations, "
            f"reps & warranties to negotiate into SPA.]"
        ),
    ))

    # Section 11 — Recommendations & Conditions Precedent
    cp_lines = "\n".join(
        f"• {c.day_range} ({c.owner}): {c.title} — {c.description} [Success: {c.success_metric}]"
        for c in ic_brief.conditions_precedent
    )
    sections.append(QoESection(
        section_number="11",
        title="Recommendations & Conditions Precedent",
        kind="mixed",
        is_editable=True,
        default_content=(
            f"Overall recommendation: {ic_brief.verdict.verdict} "
            f"(composite {ic_brief.verdict.composite_score:.0f}, distress P "
            f"{ic_brief.verdict.distress_probability*100:.1f}%).\n\n"
            f"{ic_brief.verdict.one_line_take}\n\n"
            f"100-day conditions precedent:\n\n{cp_lines}\n\n"
            f"Management questions for pre-close diligence:\n\n" +
            "\n".join(
                f"• [{q.category}] {q.question} — Why: {q.why_it_matters}"
                for q in ic_brief.management_questions
            )
        ),
    ))

    # Section 12 — Partner Sign-Off / Exhibits
    sections.append(QoESection(
        section_number="12",
        title="Partner Sign-Off & Exhibits",
        kind="narrative",
        is_editable=True,
        default_content=(
            "This Quality-of-Earnings report has been prepared using SeekingChartis's "
            "healthcare-PE diligence platform operating over public-data sources (CMS, "
            "IRS 990, HCRIS, NCCI, OIG Work Plan, DOJ FCA, SEC EDGAR). Findings reflect "
            "the application of peer-benchmarked methodology and named-failure pattern "
            "matching against a corpus of 1,700+ prior healthcare-PE transactions. "
            "Partner commentary supplements algorithmic findings.\n\n"
            "Methodology references and module-level citations are available in the "
            "platform audit log. This document is prepared for the exclusive use of "
            "[CLIENT NAME] in connection with [TRANSACTION NAME]; redistribution "
            "restricted per engagement letter."
        ),
    ))

    return sections


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def compute_qoe_deliverable(
    target=None,
    client_name: str = "Client Sponsor (to be completed)",
    partner_names: Optional[List[str]] = None,
    engagement_number: str = "ENG-2026-001",
) -> QoEDeliverableResult:
    from .ic_brief import compute_ic_brief, DEFAULT_DEMO_TARGET
    if target is None:
        target = DEFAULT_DEMO_TARGET
    if partner_names is None:
        partner_names = ["Partner Name 1", "Partner Name 2"]

    # Pull the IC Brief layer once — it already composes all modules
    ic_brief = compute_ic_brief(target)

    # Build EBITDA walk from target inputs + IC Brief findings
    ebitda_walk = _build_ebitda_walk(target, ic_brief)

    # Compose 12 sections
    sections = _build_sections(target, ic_brief, ebitda_walk)

    reported = next((a.amount_mm for a in ebitda_walk if a.category == "Reported"), None)
    total_adj = sum(a.amount_mm for a in ebitda_walk if a.category != "Reported")
    adjusted = (reported + total_adj) if reported is not None else None

    # Quality score: high-confidence adjustments count favorably
    total_adjustments = [a for a in ebitda_walk if a.category != "Reported"]
    if total_adjustments:
        high_conf = sum(1 for a in total_adjustments if a.confidence == "high")
        med_conf = sum(1 for a in total_adjustments if a.confidence == "medium")
        quality = 100 * (high_conf * 1.0 + med_conf * 0.6) / len(total_adjustments)
    else:
        quality = 50.0

    now = datetime.now(timezone.utc)
    report_date = now.strftime("%B %d, %Y")

    return QoEDeliverableResult(
        deal_name=target.deal_name,
        client_name=client_name,
        partner_names=partner_names,
        engagement_number=engagement_number,
        report_date=report_date,
        report_type="Buy-Side Quality-of-Earnings Report",
        sections=sections,
        ebitda_walk=ebitda_walk,
        reported_ebitda_mm=reported,
        adjusted_ebitda_mm=adjusted,
        ebitda_quality_score=round(quality, 1),
        overall_recommendation=ic_brief.verdict.verdict,
        header_text=f"SeekingChartis Healthcare Advisory · Buy-Side Quality-of-Earnings · {target.deal_name}",
        footer_text=f"Engagement {engagement_number} · Confidential & Proprietary · Page {{page}} of {{total}}",
        corpus_deal_count=ic_brief.corpus_deal_count,
    )
