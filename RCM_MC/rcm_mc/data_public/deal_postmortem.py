"""Deal Post-Mortem / Realized Performance Review.

Structured retrospective on a completed PE deal: actual MOIC/IRR vs
underwritten plan, lever-by-lever attribution of returns, lessons learned,
and what to change for the next comparable deal.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class PlanVsActual:
    metric: str
    underwritten: float
    realized: float
    variance_pct: float
    commentary: str


@dataclass
class LeverAttribution:
    lever: str
    planned_mm: float
    realized_mm: float
    capture_rate_pct: float
    what_went_right: str
    what_went_wrong: str


@dataclass
class MilestoneRecord:
    milestone: str
    planned_date: str
    actual_date: str
    slipped_days: int
    impact: str


@dataclass
class LessonLearned:
    category: str
    lesson: str
    change_for_next: str
    priority: str


@dataclass
class ValueBridge:
    component: str
    underwritten_mm: float
    realized_mm: float
    delta_mm: float
    delta_pct: float


@dataclass
class CounterfactualScenario:
    scenario: str
    change_from_actual: str
    estimated_moic_delta: float
    feasibility: str


@dataclass
class PostMortemResult:
    deal_name: str
    entry_year: int
    exit_year: int
    hold_years: float
    underwritten_moic: float
    realized_moic: float
    underwritten_irr: float
    realized_irr: float
    overall_grade: str
    plan_vs_actual: List[PlanVsActual]
    attribution: List[LeverAttribution]
    milestones: List[MilestoneRecord]
    lessons: List[LessonLearned]
    value_bridge: List[ValueBridge]
    counterfactuals: List[CounterfactualScenario]
    corpus_deal_count: int


def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 114):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    return deals


def _build_plan_vs_actual() -> List[PlanVsActual]:
    return [
        PlanVsActual("Entry EBITDA ($M)", 18.5, 18.5, 0.0, "on plan"),
        PlanVsActual("Exit EBITDA ($M)", 48.5, 42.2, -0.13, "bolt-on integration slower than planned"),
        PlanVsActual("EBITDA Growth CAGR", 0.21, 0.18, -0.14, "organic growth below target; M&A on track"),
        PlanVsActual("Entry Multiple (x)", 13.0, 13.0, 0.0, "on plan"),
        PlanVsActual("Exit Multiple (x)", 14.5, 13.2, -0.09, "exit market weaker than underwritten"),
        PlanVsActual("Revenue Growth Rate", 0.18, 0.16, -0.11, "volume below plan; rate on track"),
        PlanVsActual("Commercial Mix %", 0.42, 0.40, -0.05, "BCBS share below target"),
        PlanVsActual("Gross Margin %", 0.485, 0.465, -0.04, "locum costs higher than modeled"),
        PlanVsActual("EBITDA Margin %", 0.225, 0.215, -0.04, "integration drag"),
        PlanVsActual("Hold Period (years)", 5.0, 5.5, 0.10, "extended for better exit timing"),
        PlanVsActual("MOIC", 2.85, 2.42, -0.15, "multiple compression + slower growth"),
        PlanVsActual("IRR", 0.232, 0.180, -0.22, "compounded underperformance"),
    ]


def _build_attribution() -> List[LeverAttribution]:
    return [
        LeverAttribution("Organic Revenue Growth", 12.5, 8.5, 0.68,
                         "Launched 3 new specialties successfully", "Volume below plan due to referral dependency"),
        LeverAttribution("Margin Expansion", 6.2, 4.8, 0.77,
                         "RCM consolidation saved $3.5M", "Labor inflation ate $2.2M vs plan"),
        LeverAttribution("Bolt-On M&A", 8.5, 5.8, 0.68,
                         "Closed 8 of 12 targeted add-ons", "4 targets backed out during diligence"),
        LeverAttribution("Payer Rate Uplift", 2.8, 1.2, 0.43,
                         "BCBS renewal at +3% (plan +5%)", "UHC renegotiation yielded 0% rate lift"),
        LeverAttribution("Multiple Arbitrage", 15.5, 6.2, 0.40,
                         "Buyer universe validated", "Exit multiple compressed to 13.2x vs 14.5x plan"),
        LeverAttribution("Debt Paydown", 4.5, 4.2, 0.93,
                         "Cash sweep delivered as planned", "Rate environment rose post-entry"),
        LeverAttribution("Operating Leverage", 3.8, 2.8, 0.74,
                         "Back-office consolidation as planned", "Corporate G&A grew with headcount"),
        LeverAttribution("Synergy Realization", 2.5, 1.6, 0.64,
                         "Supply chain unified", "IT integration slipped 6 months"),
    ]


def _build_milestones() -> List[MilestoneRecord]:
    return [
        MilestoneRecord("Close", "2020-10-15", "2020-10-15", 0, "on time"),
        MilestoneRecord("Management transition complete", "2020-12-31", "2021-02-15", 46, "minor delay"),
        MilestoneRecord("EHR unified", "2021-06-30", "2022-01-15", 199, "material delay — 6.5 months late"),
        MilestoneRecord("First bolt-on close", "2021-09-30", "2021-10-22", 22, "on track"),
        MilestoneRecord("$25M run-rate EBITDA", "2022-06-30", "2022-09-15", 77, "minor delay"),
        MilestoneRecord("Payer renegotiation complete", "2022-12-31", "2023-03-30", 89, "minor delay"),
        MilestoneRecord("$40M run-rate EBITDA", "2023-12-31", "2024-06-30", 182, "material delay"),
        MilestoneRecord("Exit process launch", "2025-01-15", "2025-09-15", 243, "market timing deferred"),
        MilestoneRecord("Signing LOI", "2025-04-30", "2025-12-15", 229, "buyer selection slower than plan"),
        MilestoneRecord("Close (exit)", "2025-07-15", "2026-03-30", 258, "closing delays"),
    ]


def _build_lessons() -> List[LessonLearned]:
    return [
        LessonLearned("M&A Execution", "Bolt-on conversion rate (target → close) was 67% vs 85% model",
                      "Reduce target list size; require earlier diligence gates", "high"),
        LessonLearned("Technology", "EHR unification routinely slips 6+ months post-close",
                      "Extend PMI timeline budget + $2M contingency", "high"),
        LessonLearned("Labor Market", "Locum MD costs rose 40% in COVID era",
                      "Lock contract rates pre-close; include labor escalator in underwriting", "critical"),
        LessonLearned("Payer Negotiation", "Large payer renewals historically deliver 30-50% of plan",
                      "Underwrite payer uplift at 60% of negotiated target", "high"),
        LessonLearned("Exit Multiples", "Multiple compression happens faster than expansion",
                      "Model -1.5x exit multiple stress case", "high"),
        LessonLearned("Management Team", "CFO transition extended by 6 months — execution hit",
                      "Complete CFO hire pre-close or in first 30 days", "medium"),
        LessonLearned("Integration Investment", "Integration spend exceeded budget by 22%",
                      "Add 20% contingency to integration budget", "high"),
        LessonLearned("Cash Sweep", "Covenant-compliant debt paydown was easier than expected",
                      "Can underwrite more aggressive leverage on future comparable deals", "medium"),
    ]


def _build_value_bridge() -> List[ValueBridge]:
    return [
        ValueBridge("Entry EBITDA × Entry Multiple (Base)", 240.5, 240.5, 0.0, 0.0),
        ValueBridge("Organic Revenue Growth", 112.0, 82.5, -29.5, -0.264),
        ValueBridge("Bolt-On EBITDA (Acquired)", 185.0, 128.5, -56.5, -0.305),
        ValueBridge("Margin Expansion", 68.5, 52.8, -15.7, -0.229),
        ValueBridge("Multiple Arbitrage (13x → 14.5x plan)", 52.5, 0.0, -52.5, -1.0),
        ValueBridge("Multiple Compression (Actual 13x → 13.2x)", 0.0, 22.8, 22.8, float('inf')),
        ValueBridge("Debt Paydown / FCF Conversion", 48.5, 45.2, -3.3, -0.068),
        ValueBridge("Total Proceeds to Equity", 707.0, 572.3, -134.7, -0.191),
    ]


def _build_counterfactuals() -> List[CounterfactualScenario]:
    return [
        CounterfactualScenario("Full Bolt-On Execution", "All 12 targets closed on time", 0.42, "medium"),
        CounterfactualScenario("EHR Migration On Time", "Save 6 months of productivity drag", 0.18, "high"),
        CounterfactualScenario("Payer Rate Uplift at Plan", "BCBS +5%, UHC +3%", 0.25, "medium"),
        CounterfactualScenario("Exit at 14.5x (on plan)", "Held 6 more months into 2026 upcycle", 0.32, "speculative"),
        CounterfactualScenario("No Labor Inflation", "Wage stability 2021-2023", 0.28, "counterfactual"),
        CounterfactualScenario("All combined", "All levers at plan", 0.78, "hypothetical ceiling"),
    ]


def compute_deal_postmortem() -> PostMortemResult:
    corpus = _load_corpus()

    plan_vs_actual = _build_plan_vs_actual()
    attribution = _build_attribution()
    milestones = _build_milestones()
    lessons = _build_lessons()
    bridge = _build_value_bridge()
    counterfactuals = _build_counterfactuals()

    underwritten_moic = 2.85
    realized_moic = 2.42
    underwritten_irr = 0.232
    realized_irr = 0.180

    moic_delta = (realized_moic - underwritten_moic) / underwritten_moic
    if moic_delta >= 0.05:
        grade = "outperformed (A)"
    elif moic_delta >= -0.10:
        grade = "on plan (B)"
    elif moic_delta >= -0.25:
        grade = "underperformed (C)"
    else:
        grade = "material miss (D)"

    return PostMortemResult(
        deal_name="Project Azalea — GI Network SE (realized 2020-2026)",
        entry_year=2020,
        exit_year=2026,
        hold_years=5.5,
        underwritten_moic=underwritten_moic,
        realized_moic=realized_moic,
        underwritten_irr=underwritten_irr,
        realized_irr=realized_irr,
        overall_grade=grade,
        plan_vs_actual=plan_vs_actual,
        attribution=attribution,
        milestones=milestones,
        lessons=lessons,
        value_bridge=bridge,
        counterfactuals=counterfactuals,
        corpus_deal_count=len(corpus),
    )
