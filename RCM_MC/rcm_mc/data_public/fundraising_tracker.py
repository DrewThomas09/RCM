"""Fundraising / LP Pipeline Tracker.

Tracks active fundraising efforts: GP targets, LP pipeline (by stage),
close schedule, fund structure decisions, placement agents.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class FundTarget:
    fund_name: str
    target_size_b: float
    hard_cap_b: float
    strategy: str
    launch_date: str
    first_close: str
    final_close_target: str
    committed_m: float
    hard_circled_m: float
    status: str


@dataclass
class LPPipelineEntry:
    lp_name: str
    lp_type: str
    prior_relationship: bool
    target_commitment_m: float
    likelihood_pct: float
    stage: str
    last_activity: str
    owner: str
    notes: str


@dataclass
class StageRollup:
    stage: str
    lps: int
    target_commitment_m: float
    weighted_commitment_m: float
    avg_likelihood_pct: float


@dataclass
class FundTermsMatrix:
    term: str
    main_fund: str
    benchmark_market: str
    negotiation_status: str
    lp_pressure_direction: str


@dataclass
class PlacementAgent:
    agent: str
    fund: str
    retainer_m: float
    success_fee_bps: int
    regions: str
    deals_sourced: int
    committed_m: float


@dataclass
class CloseSchedule:
    fund: str
    close: str
    target_date: str
    target_commitment_m: float
    committed_m: float
    on_track: bool
    risk_factors: str


@dataclass
class FundraisingResult:
    active_funds: int
    total_target_b: float
    total_committed_b: float
    total_hard_circled_b: float
    pct_fundraised: float
    lps_in_pipeline: int
    targets: List[FundTarget]
    pipeline: List[LPPipelineEntry]
    stages: List[StageRollup]
    terms: List[FundTermsMatrix]
    agents: List[PlacementAgent]
    schedule: List[CloseSchedule]
    corpus_deal_count: int


def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 122):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    return deals


def _build_targets() -> List[FundTarget]:
    return [
        FundTarget("Seeking Chartis Healthcare Fund VI", 6.0, 7.5, "Healthcare Buyout",
                   "2025-11-15", "2026-03-31", "2026-12-31", 4250.0, 5100.0, "active fundraising"),
        FundTarget("Seeking Chartis Growth Equity III", 1.5, 2.0, "Healthcare Growth",
                   "2026-01-15", "2026-05-31", "2026-12-31", 650.0, 825.0, "early fundraising"),
        FundTarget("Seeking Chartis Continuation Vehicle (MSK)", 0.85, 1.0, "Single-asset CV",
                   "2026-02-22", "2026-05-31", "2026-08-31", 485.0, 620.0, "in pricing"),
        FundTarget("Seeking Chartis Opportunistic Credit Fund", 2.2, 2.5, "Healthcare Credit",
                   "2026-02-28", "2026-08-31", "2026-12-31", 320.0, 485.0, "early fundraising"),
    ]


def _build_pipeline() -> List[LPPipelineEntry]:
    return [
        LPPipelineEntry("CalPERS", "Public Pension", True, 350.0, 95.0, "hard circled", "2026-03-25",
                        "Sr. Partner", "Confirmed $350M across Fund VI + CV. Docs at counsel."),
        LPPipelineEntry("CalSTRS", "Public Pension", True, 250.0, 90.0, "due diligence complete", "2026-03-20",
                        "Sr. Partner", "Board approval May 2026."),
        LPPipelineEntry("Texas Teachers", "Public Pension", True, 300.0, 92.0, "hard circled", "2026-03-28",
                        "Sr. Partner", "Fund VI + Growth III. Docs finalized."),
        LPPipelineEntry("NYC ERS", "Public Pension", True, 185.0, 85.0, "due diligence complete", "2026-03-18",
                        "Mgr Director", "Board approval April 2026."),
        LPPipelineEntry("CPPIB", "Canadian Pension", True, 450.0, 95.0, "hard circled", "2026-03-22",
                        "Sr. Partner", "Fund VI + CV + Growth III. Side letter in final review."),
        LPPipelineEntry("HOOPP", "Canadian Pension", True, 185.0, 88.0, "due diligence complete", "2026-03-15",
                        "Mgr Director", "Approved pending committee. $185M commitment."),
        LPPipelineEntry("Temasek Holdings", "Sovereign Wealth", True, 485.0, 90.0, "hard circled", "2026-03-10",
                        "Sr. Partner", "Fund VI anchor. Cornerstone terms finalized."),
        LPPipelineEntry("GIC (Singapore)", "Sovereign Wealth", True, 385.0, 90.0, "hard circled", "2026-03-25",
                        "Sr. Partner", "Fund VI + Credit Fund. Docs final."),
        LPPipelineEntry("ADIA (Abu Dhabi)", "Sovereign Wealth", False, 250.0, 70.0, "due diligence active", "2026-03-15",
                        "Mgr Director", "First time. DD meeting next week."),
        LPPipelineEntry("NBIM (Norway)", "Sovereign Wealth", True, 285.0, 85.0, "due diligence complete", "2026-03-12",
                        "Mgr Director", "Approved subject to LPAC formation."),
        LPPipelineEntry("Harvard Management", "Endowment", True, 125.0, 88.0, "hard circled", "2026-03-05",
                        "Mgr Director", "Fund VI + Growth III. Docs signed."),
        LPPipelineEntry("Yale Investments", "Endowment", True, 165.0, 90.0, "hard circled", "2026-03-08",
                        "Mgr Director", "Top-up from Fund V. Docs signed."),
        LPPipelineEntry("Stanford Management", "Endowment", True, 115.0, 85.0, "due diligence complete", "2026-03-18",
                        "Director", "Board approval April 2026."),
        LPPipelineEntry("MIT Investment Co.", "Endowment", False, 75.0, 55.0, "introduction", "2026-03-02",
                        "Director", "Placement agent introduction. Kickoff call April 2026."),
        LPPipelineEntry("Ford Foundation", "Foundation", True, 85.0, 82.0, "due diligence complete", "2026-03-15",
                        "Director", "Previous commitment in Fund V. Board April 2026."),
        LPPipelineEntry("Gates Foundation Trust", "Foundation", True, 145.0, 88.0, "due diligence complete", "2026-03-22",
                        "Mgr Director", "Strategic for global health mandate. Docs soon."),
        LPPipelineEntry("Northwestern Mutual", "Insurance", True, 185.0, 85.0, "due diligence complete", "2026-03-18",
                        "Director", "Board committee May 2026."),
        LPPipelineEntry("MassMutual", "Insurance", False, 95.0, 65.0, "due diligence active", "2026-03-10",
                        "Director", "First commitment. DD ongoing."),
        LPPipelineEntry("Adams Street Partners", "FoF / Secondaries", True, 165.0, 85.0, "due diligence complete", "2026-03-20",
                        "Mgr Director", "Committed pending ILPA template review."),
        LPPipelineEntry("HarbourVest Partners", "FoF / Secondaries", True, 225.0, 90.0, "hard circled", "2026-03-25",
                        "Sr. Partner", "Cornerstone LP. Docs final."),
        LPPipelineEntry("Pantheon Ventures", "FoF / Secondaries", True, 145.0, 85.0, "due diligence active", "2026-03-18",
                        "Director", "DD wrapping up. Commit April 2026."),
        LPPipelineEntry("StepStone Group", "FoF / Secondaries", True, 125.0, 82.0, "due diligence active", "2026-03-20",
                        "Director", "DD ongoing. Expected commit Q2 2026."),
        LPPipelineEntry("Family Office — Pritzker", "Family Office", True, 65.0, 85.0, "hard circled", "2026-03-12",
                        "Director", "Top-up from prior fund. Docs finalized."),
        LPPipelineEntry("Family Office — Bass", "Family Office", False, 45.0, 50.0, "introduction", "2026-02-28",
                        "Director", "Placement agent introduction. Preliminary interest."),
        LPPipelineEntry("Family Office — Arnault", "Family Office", False, 55.0, 45.0, "introduction", "2026-03-05",
                        "Director", "New relationship. Cultivation mode."),
        LPPipelineEntry("KIC (Korea)", "Sovereign Wealth", False, 185.0, 60.0, "due diligence active", "2026-03-15",
                        "Mgr Director", "First time. Placement agent intro."),
        LPPipelineEntry("OMERS Private Equity", "Canadian Pension", False, 145.0, 55.0, "initial evaluation", "2026-03-10",
                        "Mgr Director", "Preliminary screens ongoing."),
        LPPipelineEntry("Ontario Teachers' Pension", "Canadian Pension", True, 185.0, 80.0, "due diligence active", "2026-03-20",
                        "Mgr Director", "Returning LP. DD wrapping up."),
        LPPipelineEntry("Qatar Investment Authority", "Sovereign Wealth", False, 285.0, 50.0, "introduction", "2026-03-08",
                        "Sr. Partner", "New relationship. Cultivation kickoff."),
        LPPipelineEntry("Boston Consulting Group Retirement", "Corporate Pension", False, 35.0, 40.0, "introduction", "2026-02-25",
                        "Director", "Placement agent intro."),
    ]


def _build_stages(pipeline: List[LPPipelineEntry]) -> List[StageRollup]:
    buckets: dict = {}
    for lp in pipeline:
        b = buckets.setdefault(lp.stage, {"lps": 0, "target": 0.0, "weighted": 0.0, "lik_sum": 0.0})
        b["lps"] += 1
        b["target"] += lp.target_commitment_m
        b["weighted"] += lp.target_commitment_m * lp.likelihood_pct / 100.0
        b["lik_sum"] += lp.likelihood_pct
    rows = []
    order = ["hard circled", "due diligence complete", "due diligence active", "initial evaluation", "introduction"]
    for stage in order:
        if stage in buckets:
            d = buckets[stage]
            avg_lik = d["lik_sum"] / d["lps"] if d["lps"] else 0
            rows.append(StageRollup(
                stage=stage, lps=d["lps"],
                target_commitment_m=round(d["target"], 1),
                weighted_commitment_m=round(d["weighted"], 1),
                avg_likelihood_pct=round(avg_lik, 1),
            ))
    return rows


def _build_terms() -> List[FundTermsMatrix]:
    return [
        FundTermsMatrix("Management Fee", "1.75% on commitment (3-yr step-down to 1.25%)", "1.75-2.00% with step-down",
                        "agreed (cornerstone tier)", "flat"),
        FundTermsMatrix("Carried Interest", "20% over 8% hurdle (ILPA catch-up)", "20% w/ 7-8% hurdle",
                        "agreed", "flat"),
        FundTermsMatrix("Hurdle Rate", "8% preferred return (compounded)", "7-8%", "agreed", "slight up"),
        FundTermsMatrix("GP Catch-Up", "100% (tiered)", "100% standard", "agreed", "flat"),
        FundTermsMatrix("Deal-by-Deal vs. Whole-Fund", "Whole-fund (European waterfall)", "Whole-fund preferred",
                        "agreed (LP strong preference)", "LP favoring"),
        FundTermsMatrix("Clawback", "100% + interest", "100% + interest standard", "agreed", "flat"),
        FundTermsMatrix("Investment Period", "5 years", "5-6 years", "agreed", "flat"),
        FundTermsMatrix("Fund Term", "10 years + 2x 1-year extensions", "10yr + 2x1 standard", "agreed", "flat"),
        FundTermsMatrix("LPAC Composition", "9 LP seats (weighted by commitment)", "7-11 LP seats", "negotiated", "LP favoring"),
        FundTermsMatrix("GP Commitment", "2.5% of fund size", "1-3% standard", "agreed", "LP favoring"),
        FundTermsMatrix("Side Letter — MFN", "Full MFN for cornerstones + $500M+", "MFN for large LPs", "agreed", "LP favoring"),
        FundTermsMatrix("Key Person Clause", "3 named partners (2-year window)", "2-3 named partners", "agreed", "flat"),
        FundTermsMatrix("ESG / DEI Reporting", "ILPA + PRI quarterly", "ILPA standard + custom", "negotiated", "LP favoring"),
        FundTermsMatrix("Co-Investment Priority", "Tiered by commitment size", "tier-based standard", "agreed", "flat"),
    ]


def _build_agents() -> List[PlacementAgent]:
    return [
        PlacementAgent("Park Hill Group (PJT)", "Fund VI", 3.5, 200, "N. America + Europe", 32, 1850.0),
        PlacementAgent("Credit Suisse Private Fund Group (UBS)", "Fund VI", 2.5, 150, "Asia + Middle East", 18, 850.0),
        PlacementAgent("Jefferies Private Capital Advisory", "Growth III", 1.5, 200, "N. America + Europe", 14, 485.0),
        PlacementAgent("Evercore Private Funds Group", "Credit Fund", 1.8, 175, "N. America + Europe", 12, 320.0),
        PlacementAgent("Campbell Lutyens", "Continuation Vehicle (MSK)", 1.2, 150, "Global", 8, 485.0),
        PlacementAgent("Eaton Partners (Stifel)", "Fund VI (secondary)", 0.8, 150, "Middle Market", 6, 185.0),
    ]


def _build_schedule() -> List[CloseSchedule]:
    return [
        CloseSchedule("Fund VI", "First Close", "2026-03-31", 3500.0, 3850.0, True, "on track; exceeded target"),
        CloseSchedule("Fund VI", "Second Close", "2026-06-30", 5000.0, 0.0, True, "pipeline of $1.5B in DD-complete stage"),
        CloseSchedule("Fund VI", "Final Close", "2026-12-31", 6000.0, 0.0, True, "$1.2B in early DD for top-up"),
        CloseSchedule("Growth III", "First Close", "2026-05-31", 850.0, 650.0, True, "cornerstones committed; building momentum"),
        CloseSchedule("Growth III", "Final Close", "2026-12-31", 1500.0, 0.0, True, "strong pipeline; on track"),
        CloseSchedule("Continuation Vehicle (MSK)", "Final Close", "2026-08-31", 850.0, 485.0, True, "pricing in progress"),
        CloseSchedule("Credit Fund", "First Close", "2026-08-31", 1000.0, 320.0, False, "slower pace than target; cornerstones needed"),
        CloseSchedule("Credit Fund", "Final Close", "2026-12-31", 2200.0, 0.0, False, "depends on first close acceleration"),
    ]


def compute_fundraising_tracker() -> FundraisingResult:
    corpus = _load_corpus()
    targets = _build_targets()
    pipeline = _build_pipeline()
    stages = _build_stages(pipeline)
    terms = _build_terms()
    agents = _build_agents()
    schedule = _build_schedule()

    total_target = sum(t.target_size_b for t in targets)
    total_committed = sum(t.committed_m for t in targets) / 1000.0
    total_hard = sum(t.hard_circled_m for t in targets) / 1000.0
    pct_raised = total_hard / total_target if total_target > 0 else 0

    return FundraisingResult(
        active_funds=len(targets),
        total_target_b=round(total_target, 2),
        total_committed_b=round(total_committed, 2),
        total_hard_circled_b=round(total_hard, 2),
        pct_fundraised=round(pct_raised, 4),
        lps_in_pipeline=len(pipeline),
        targets=targets,
        pipeline=pipeline,
        stages=stages,
        terms=terms,
        agents=agents,
        schedule=schedule,
        corpus_deal_count=len(corpus),
    )
