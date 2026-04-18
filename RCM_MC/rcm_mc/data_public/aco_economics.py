"""ACO Economics Analyzer.

Models Medicare Shared Savings Program (MSSP) and ACO REACH economics:
- Benchmark establishment and regional adjustments
- Risk corridor selection (Track A/B/E, ACO REACH)
- Quality score multiplier (MIPS components)
- Shared savings / loss splits
- MA contract math (capitation PMPM)
- Full-risk transition modeling
- Infrastructure investment ROI
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ACOTrack:
    track: str
    beneficiaries: int
    benchmark_pmpm: float
    risk_level: str
    upside_cap_pct: float
    downside_cap_pct: float
    quality_weight: float
    min_savings_rate: float


@dataclass
class BenchmarkMath:
    component: str
    value_pmpm: float
    basis: str


@dataclass
class SavingsOutcome:
    scenario: str
    actual_pmpm: float
    savings_pct: float
    gross_savings_mm: float
    quality_multiplier: float
    net_shared_savings_mm: float
    aco_share_pct: float
    payout_to_aco_mm: float


@dataclass
class QualityComponent:
    component: str
    weight: float
    current_score: float
    target: float
    contribution_to_quality: float


@dataclass
class InfrastructureInvestment:
    investment: str
    year_1_cost_mm: float
    ongoing_cost_mm: float
    enables_savings_mm: float
    payback_months: int


@dataclass
class FullRiskTransition:
    stage: str
    risk_exposure_pct: float
    required_infra_mm: float
    reinsurance_cost_mm: float
    expected_shared_savings_mm: float
    expected_capitation_margin_mm: float


@dataclass
class ACOEconomicsResult:
    total_beneficiaries: int
    blended_benchmark_pmpm: float
    quality_score: float
    expected_shared_savings_mm: float
    total_annual_value_mm: float
    tracks: List[ACOTrack]
    benchmark: List[BenchmarkMath]
    savings_scenarios: List[SavingsOutcome]
    quality_components: List[QualityComponent]
    infrastructure: List[InfrastructureInvestment]
    full_risk: List[FullRiskTransition]
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 80):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    try:
        from rcm_mc.data_public.deals_corpus import _SEED_DEALS, EXTENDED_SEED_DEALS
        deals = _SEED_DEALS + EXTENDED_SEED_DEALS + deals
    except Exception:
        pass
    return deals


def _build_tracks(total_beneficiaries: int, benchmark_pmpm: float) -> List[ACOTrack]:
    return [
        ACOTrack(
            track="MSSP Track A (Upside-Only)",
            beneficiaries=int(total_beneficiaries * 0.40),
            benchmark_pmpm=benchmark_pmpm,
            risk_level="upside-only",
            upside_cap_pct=0.10,
            downside_cap_pct=0.0,
            quality_weight=0.50,
            min_savings_rate=0.02,
        ),
        ACOTrack(
            track="MSSP Track E (Two-sided)",
            beneficiaries=int(total_beneficiaries * 0.30),
            benchmark_pmpm=benchmark_pmpm,
            risk_level="two-sided",
            upside_cap_pct=0.15,
            downside_cap_pct=0.05,
            quality_weight=0.60,
            min_savings_rate=0.02,
        ),
        ACOTrack(
            track="ACO REACH (Direct Contracting)",
            beneficiaries=int(total_beneficiaries * 0.15),
            benchmark_pmpm=benchmark_pmpm * 1.02,
            risk_level="global / full-risk",
            upside_cap_pct=1.00,
            downside_cap_pct=1.00,
            quality_weight=0.40,
            min_savings_rate=0.0,
        ),
        ACOTrack(
            track="MA Full-Risk Capitation",
            beneficiaries=int(total_beneficiaries * 0.15),
            benchmark_pmpm=benchmark_pmpm * 1.08,
            risk_level="full-risk",
            upside_cap_pct=1.00,
            downside_cap_pct=1.00,
            quality_weight=0.20,
            min_savings_rate=0.0,
        ),
    ]


def _build_benchmark(base_pmpm: float) -> List[BenchmarkMath]:
    return [
        BenchmarkMath("Regional Baseline PMPM", round(base_pmpm * 0.94, 0),
                      "BY1-3 Medicare FFS weighted average"),
        BenchmarkMath("Regional Trend Adjustment", round(base_pmpm * 0.035, 0),
                      "+3.5% annual growth factor"),
        BenchmarkMath("ACO-specific Trend", round(base_pmpm * 0.01, 0),
                      "+1.0% ACO-specific adjustment"),
        BenchmarkMath("Complete-ACO Benchmark", round(base_pmpm * 1.00, 0),
                      "Final benchmark for shared savings math"),
        BenchmarkMath("National MA Benchmark (ref)", round(base_pmpm * 1.12, 0),
                      "For comparison vs MA contracts"),
    ]


def _build_savings(benchmark_pmpm: float, beneficiaries: int, quality: float) -> List[SavingsOutcome]:
    # Expected PMPM scenarios
    ben_cost_annual_mm = benchmark_pmpm * beneficiaries * 12 / 1_000_000
    scenarios_def = [
        ("Strong Performance (-6% vs benchmark)", benchmark_pmpm * 0.94, 0.06, 0.90, 0.55),
        ("Good Performance (-4% vs benchmark)", benchmark_pmpm * 0.96, 0.04, 0.85, 0.50),
        ("Target (-2.5% vs benchmark)", benchmark_pmpm * 0.975, 0.025, 0.85, 0.50),
        ("Marginal (-1% vs benchmark)", benchmark_pmpm * 0.99, 0.01, 0.80, 0.30),
        ("Above Benchmark (+2%)", benchmark_pmpm * 1.02, -0.02, 0.85, 0.0),
    ]
    rows = []
    for label, actual, pct, mult, aco_share in scenarios_def:
        gross_savings = ben_cost_annual_mm * pct
        net_savings = max(0, gross_savings) * mult   # quality-adjusted
        aco_payout = net_savings * aco_share
        rows.append(SavingsOutcome(
            scenario=label,
            actual_pmpm=round(actual, 0),
            savings_pct=round(pct, 4),
            gross_savings_mm=round(gross_savings, 2),
            quality_multiplier=round(mult, 2),
            net_shared_savings_mm=round(net_savings, 2),
            aco_share_pct=round(aco_share, 2),
            payout_to_aco_mm=round(aco_payout, 2),
        ))
    return rows


def _build_quality() -> List[QualityComponent]:
    return [
        QualityComponent("Patient Experience of Care", 0.25, 4.2, 4.5, 1.05),
        QualityComponent("Preventive Health", 0.25, 82, 90, 0.91),
        QualityComponent("At-Risk Population (Diabetes, HTN)", 0.25, 72, 80, 0.90),
        QualityComponent("Medication Reconciliation", 0.10, 88, 95, 0.93),
        QualityComponent("Falls Screening & Intervention", 0.05, 78, 85, 0.92),
        QualityComponent("Tobacco Cessation", 0.05, 72, 82, 0.88),
        QualityComponent("Depression Screening", 0.05, 85, 90, 0.94),
    ]


def _build_infrastructure(total_annual_value: float) -> List[InfrastructureInvestment]:
    return [
        InfrastructureInvestment(
            investment="Population Health Platform (tech)",
            year_1_cost_mm=0.85,
            ongoing_cost_mm=0.45,
            enables_savings_mm=total_annual_value * 0.25,
            payback_months=14,
        ),
        InfrastructureInvestment(
            investment="Care Coordination Team (RN/SW)",
            year_1_cost_mm=1.2,
            ongoing_cost_mm=1.2,
            enables_savings_mm=total_annual_value * 0.30,
            payback_months=18,
        ),
        InfrastructureInvestment(
            investment="Risk Adjustment / Coding Accuracy",
            year_1_cost_mm=0.35,
            ongoing_cost_mm=0.28,
            enables_savings_mm=total_annual_value * 0.10,
            payback_months=8,
        ),
        InfrastructureInvestment(
            investment="High-Risk Patient Outreach / Home Visits",
            year_1_cost_mm=0.95,
            ongoing_cost_mm=0.85,
            enables_savings_mm=total_annual_value * 0.20,
            payback_months=22,
        ),
        InfrastructureInvestment(
            investment="Remote Patient Monitoring (RPM)",
            year_1_cost_mm=0.48,
            ongoing_cost_mm=0.32,
            enables_savings_mm=total_annual_value * 0.12,
            payback_months=15,
        ),
        InfrastructureInvestment(
            investment="Pharmacy Integration / Med Therapy Mgmt",
            year_1_cost_mm=0.28,
            ongoing_cost_mm=0.22,
            enables_savings_mm=total_annual_value * 0.08,
            payback_months=12,
        ),
    ]


def _build_full_risk(benchmark_pmpm: float, total_beneficiaries: int) -> List[FullRiskTransition]:
    total_premium = benchmark_pmpm * total_beneficiaries * 12 / 1_000_000
    return [
        FullRiskTransition(
            stage="Current — MSSP Upside/Two-sided",
            risk_exposure_pct=0.25,
            required_infra_mm=2.4,
            reinsurance_cost_mm=0.45,
            expected_shared_savings_mm=total_premium * 0.025,
            expected_capitation_margin_mm=0,
        ),
        FullRiskTransition(
            stage="Year 1 — Add ACO REACH Track",
            risk_exposure_pct=0.45,
            required_infra_mm=3.8,
            reinsurance_cost_mm=0.95,
            expected_shared_savings_mm=total_premium * 0.038,
            expected_capitation_margin_mm=total_premium * 0.012,
        ),
        FullRiskTransition(
            stage="Year 2 — MA Partial Risk (30%)",
            risk_exposure_pct=0.65,
            required_infra_mm=5.2,
            reinsurance_cost_mm=1.85,
            expected_shared_savings_mm=total_premium * 0.045,
            expected_capitation_margin_mm=total_premium * 0.032,
        ),
        FullRiskTransition(
            stage="Year 3-4 — MA Full Risk",
            risk_exposure_pct=1.00,
            required_infra_mm=7.5,
            reinsurance_cost_mm=3.5,
            expected_shared_savings_mm=total_premium * 0.055,
            expected_capitation_margin_mm=total_premium * 0.055,
        ),
    ]


def _quality_score(components: List[QualityComponent]) -> float:
    if not components:
        return 0
    return round(sum(c.contribution_to_quality * c.weight for c in components), 3)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_aco_economics(
    total_beneficiaries: int = 25000,
    regional_benchmark_pmpm: float = 950.0,
) -> ACOEconomicsResult:
    corpus = _load_corpus()

    tracks = _build_tracks(total_beneficiaries, regional_benchmark_pmpm)
    benchmark = _build_benchmark(regional_benchmark_pmpm)
    quality_comps = _build_quality()
    quality = _quality_score(quality_comps)

    savings = _build_savings(regional_benchmark_pmpm, total_beneficiaries, quality)

    # Expected: use target scenario
    target = next((s for s in savings if "Target" in s.scenario), savings[2] if len(savings) > 2 else savings[0])
    expected_savings = target.payout_to_aco_mm

    total_premium = regional_benchmark_pmpm * total_beneficiaries * 12 / 1_000_000
    total_value = expected_savings + total_premium * 0.02    # PMPM admin + MA mix

    infra = _build_infrastructure(total_value)
    full_risk = _build_full_risk(regional_benchmark_pmpm, total_beneficiaries)

    return ACOEconomicsResult(
        total_beneficiaries=total_beneficiaries,
        blended_benchmark_pmpm=round(regional_benchmark_pmpm, 0),
        quality_score=quality,
        expected_shared_savings_mm=round(expected_savings, 2),
        total_annual_value_mm=round(total_value, 2),
        tracks=tracks,
        benchmark=benchmark,
        savings_scenarios=savings,
        quality_components=quality_comps,
        infrastructure=infra,
        full_risk=full_risk,
        corpus_deal_count=len(corpus),
    )
