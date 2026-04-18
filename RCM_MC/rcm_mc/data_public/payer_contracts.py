"""Payer Contract Renewal / Rate Escalator Tracker.

Tracks commercial + government payer contracts: renewal timing, rate
escalators, CPI adjustments, medical loss ratio, network adequacy,
portfolio-wide negotiation calendar.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class PayerContract:
    deal: str
    payer: str
    contract_type: str
    annual_revenue_m: float
    effective_date: str
    expires: str
    rate_escalator_pct: float
    cpi_floor: bool
    cpi_cap_pct: float
    renegotiation_stage: str
    lives_covered_k: int


@dataclass
class RateChangeHistory:
    payer: str
    sector: str
    py_2022_pct: float
    py_2023_pct: float
    py_2024_pct: float
    py_2025_pct: float
    py_2026_requested_pct: float
    trend: str


@dataclass
class PayerConcentration:
    payer: str
    contracts: int
    annual_revenue_m: float
    pct_of_portfolio_rev: float
    sectors_covered: str
    relationship_tenure_avg_years: float
    network_status: str


@dataclass
class NegotiationPipeline:
    deal: str
    payer: str
    target_close: str
    current_ask_pct: float
    payer_counter_pct: float
    gap_pct: float
    risk_level: str
    revenue_at_stake_m: float


@dataclass
class NetworkAdequacy:
    payer: str
    market: str
    provider_count: int
    time_distance_compliance_pct: float
    waived_members: int
    network_gaps: str


@dataclass
class ContractOptimization:
    initiative: str
    deals: int
    typical_rate_lift_pct: float
    implementation_months: int
    annualized_value_m: float
    prerequisite: str


@dataclass
class PayerContractResult:
    total_contracts: int
    total_annual_revenue_m: float
    contracts_in_negotiation: int
    weighted_avg_escalator_pct: float
    contracts_expiring_12mo: int
    revenue_at_renegotiation_m: float
    contracts: List[PayerContract]
    history: List[RateChangeHistory]
    concentration: List[PayerConcentration]
    negotiations: List[NegotiationPipeline]
    network: List[NetworkAdequacy]
    optimization: List[ContractOptimization]
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


def _build_contracts() -> List[PayerContract]:
    return [
        PayerContract("Project Cypress — GI Network", "UnitedHealthcare", "Commercial + MA", 125.0,
                      "2023-01-01", "2026-12-31", 0.025, True, 0.045, "in negotiation", 485),
        PayerContract("Project Cypress — GI Network", "BCBS (multiple)", "Commercial", 85.0,
                      "2022-07-01", "2026-06-30", 0.028, True, 0.045, "pre-negotiation", 385),
        PayerContract("Project Cypress — GI Network", "Aetna / CVS", "Commercial + MA", 58.0,
                      "2023-04-01", "2027-03-31", 0.028, True, 0.045, "active", 285),
        PayerContract("Project Magnolia — MSK", "UnitedHealthcare", "Commercial", 85.0,
                      "2023-06-01", "2027-05-31", 0.022, True, 0.045, "active", 325),
        PayerContract("Project Magnolia — MSK", "Cigna", "Commercial", 62.0,
                      "2022-10-01", "2026-09-30", 0.025, True, 0.045, "pre-negotiation", 285),
        PayerContract("Project Cedar — Cardiology", "UnitedHealthcare", "Commercial + MA", 148.0,
                      "2022-04-01", "2026-03-31", 0.032, True, 0.045, "in negotiation", 485),
        PayerContract("Project Cedar — Cardiology", "Humana (MA)", "MA (capitated)", 95.0,
                      "2023-07-01", "2027-06-30", 0.040, False, 0.00, "active", 285),
        PayerContract("Project Redwood — Behavioral", "Optum Behavioral (UHG)", "Commercial + MA", 68.0,
                      "2023-03-01", "2027-02-28", 0.035, True, 0.055, "active", 285),
        PayerContract("Project Redwood — Behavioral", "State Medicaid", "Medicaid FFS", 45.0,
                      "2022-01-01", "2026-12-31", 0.00, False, 0.00, "state-directed", 385),
        PayerContract("Project Laurel — Derma", "BCBS (multiple)", "Commercial", 58.0,
                      "2022-11-01", "2026-10-31", 0.022, True, 0.045, "pre-negotiation", 485),
        PayerContract("Project Willow — Fertility", "Employer Direct (42 employers)", "Commercial (capitated)", 45.0,
                      "2023-06-01", "2026-05-31", 0.030, False, 0.00, "pre-negotiation", 65),
        PayerContract("Project Spruce — Radiology", "UnitedHealthcare", "Commercial + MA", 68.0,
                      "2023-01-01", "2026-12-31", 0.022, True, 0.045, "in negotiation", 485),
        PayerContract("Project Aspen — Eye Care", "VSP / Vision", "Commercial (vision only)", 42.0,
                      "2023-10-01", "2027-09-30", 0.028, True, 0.045, "active", 245),
        PayerContract("Project Maple — Urology", "Humana", "Commercial + MA", 28.5,
                      "2022-08-01", "2026-07-31", 0.025, True, 0.045, "pre-negotiation", 145),
        PayerContract("Project Ash — Infusion", "Accredo (Cigna) + Optum Specialty", "Specialty Pharma", 85.0,
                      "2023-09-01", "2027-08-31", 0.035, True, 0.055, "active", 35),
        PayerContract("Project Fir — Lab / Pathology", "LabCorp / Quest aggregator", "Commercial", 48.0,
                      "2022-12-01", "2026-11-30", 0.025, True, 0.045, "pre-negotiation", 285),
        PayerContract("Project Sage — Home Health", "State Medicaid (multi-state)", "Medicaid", 85.0,
                      "2022-07-01", "2026-06-30", 0.015, False, 0.00, "state-directed", 225),
        PayerContract("Project Sage — Home Health", "MA (various)", "Medicare Advantage (capitated)", 62.0,
                      "2023-05-01", "2027-04-30", 0.035, False, 0.00, "active", 125),
        PayerContract("Project Linden — Behavioral", "Optum Behavioral", "Commercial + MA", 38.0,
                      "2022-11-01", "2026-10-31", 0.032, True, 0.055, "pre-negotiation", 185),
        PayerContract("Project Basil — Dental DSO", "Delta Dental", "Dental commercial", 52.0,
                      "2023-06-01", "2027-05-31", 0.025, True, 0.045, "active", 485),
    ]


def _build_history() -> List[RateChangeHistory]:
    return [
        RateChangeHistory("UnitedHealthcare", "Multi-specialty MD", 0.025, 0.023, 0.022, 0.025, 0.028, "accelerating"),
        RateChangeHistory("UnitedHealthcare", "Radiology/Imaging", 0.022, 0.020, 0.018, 0.022, 0.025, "accelerating"),
        RateChangeHistory("UnitedHealthcare", "GI", 0.028, 0.025, 0.025, 0.028, 0.032, "accelerating"),
        RateChangeHistory("Anthem/Elevance (BCBS)", "Multi-specialty MD", 0.028, 0.025, 0.024, 0.026, 0.030, "accelerating"),
        RateChangeHistory("Cigna", "Multi-specialty MD", 0.025, 0.022, 0.022, 0.024, 0.028, "stable"),
        RateChangeHistory("Aetna / CVS Health", "Multi-specialty MD", 0.028, 0.025, 0.024, 0.028, 0.030, "stable"),
        RateChangeHistory("Humana (MA)", "VBC / Capitated", 0.040, 0.045, 0.050, 0.048, 0.045, "moderating"),
        RateChangeHistory("Optum Behavioral (UHG)", "Behavioral Health", 0.035, 0.038, 0.038, 0.038, 0.042, "accelerating"),
        RateChangeHistory("Centene", "Medicaid managed care", 0.018, 0.020, 0.020, 0.022, 0.020, "stable"),
        RateChangeHistory("State Medicaid (avg)", "Medicaid FFS", 0.010, 0.015, 0.020, 0.020, 0.015, "cooling"),
        RateChangeHistory("Kaiser Permanente", "Multi-specialty MD", 0.020, 0.018, 0.020, 0.025, 0.025, "stable"),
        RateChangeHistory("Commercial Employer Direct", "VBC / Direct", 0.030, 0.035, 0.030, 0.032, 0.035, "stable"),
    ]


def _build_concentration() -> List[PayerConcentration]:
    return [
        PayerConcentration("UnitedHealthcare (incl Optum)", 22, 425.0, 0.258, "GI, MSK, Cardio, Radiology, Behavioral, Lab, Infusion", 6.5, "in-network (all)"),
        PayerConcentration("Anthem / Elevance BCBS", 18, 285.0, 0.173, "Derma, GI, MSK, Cardio, Behavioral, Lab, Urology, OB/GYN", 7.2, "in-network (all)"),
        PayerConcentration("Cigna", 14, 185.0, 0.112, "MSK, Derma, Infusion, Lab, Cardio", 5.8, "in-network (all)"),
        PayerConcentration("Aetna / CVS Health", 16, 195.0, 0.118, "GI, MSK, Cardio, Derma, Dental, Eye", 6.2, "in-network (all)"),
        PayerConcentration("Humana", 12, 145.0, 0.088, "Cardio, Home Health, MSK, Urology", 5.5, "in-network (all MA focused)"),
        PayerConcentration("Centene Corp", 10, 95.0, 0.058, "Behavioral, Home Health, Dental (Medicaid)", 4.8, "in-network (Medicaid)"),
        PayerConcentration("Kaiser Permanente", 6, 58.0, 0.035, "Radiology, Pathology (carve-out agreements)", 4.5, "carve-out / in-network"),
        PayerConcentration("State Medicaid (aggregated)", 12, 148.0, 0.090, "Behavioral, Home Health, FQHC, Dental, Lab", 5.2, "participating"),
        PayerConcentration("Molina Healthcare", 6, 42.0, 0.025, "Medicaid programs", 3.8, "in-network (Medicaid)"),
        PayerConcentration("VSP / Vision Service Plan", 4, 48.0, 0.029, "Eye Care (vision-only)", 5.2, "in-network"),
        PayerConcentration("Delta Dental", 5, 65.0, 0.040, "Dental (commercial)", 6.0, "in-network"),
        PayerConcentration("Accredo (Cigna) + Optum Specialty", 4, 85.0, 0.052, "Specialty pharma distribution", 4.8, "participating"),
        PayerConcentration("Commercial Employer Direct", 8, 72.0, 0.044, "Fertility, Musculoskeletal, PBM-adjacent", 3.5, "direct"),
    ]


def _build_negotiations() -> List[NegotiationPipeline]:
    return [
        NegotiationPipeline("Project Cypress — GI Network", "UnitedHealthcare", "2026-12-31", 0.055, 0.025, 0.030, "medium", 125.0),
        NegotiationPipeline("Project Cedar — Cardiology", "UnitedHealthcare", "2026-03-31", 0.050, 0.025, 0.025, "medium", 148.0),
        NegotiationPipeline("Project Spruce — Radiology", "UnitedHealthcare", "2026-12-31", 0.045, 0.022, 0.023, "medium", 68.0),
        NegotiationPipeline("Project Cypress — GI Network", "BCBS (multiple)", "2026-06-30", 0.055, 0.028, 0.027, "medium", 85.0),
        NegotiationPipeline("Project Magnolia — MSK", "Cigna", "2026-09-30", 0.045, 0.025, 0.020, "low", 62.0),
        NegotiationPipeline("Project Laurel — Derma", "BCBS", "2026-10-31", 0.045, 0.022, 0.023, "low", 58.0),
        NegotiationPipeline("Project Maple — Urology", "Humana", "2026-07-31", 0.040, 0.025, 0.015, "low", 28.5),
        NegotiationPipeline("Project Willow — Fertility", "Employer Direct", "2026-05-31", 0.045, 0.030, 0.015, "low", 45.0),
        NegotiationPipeline("Project Fir — Lab / Pathology", "LabCorp aggregator", "2026-11-30", 0.045, 0.025, 0.020, "low", 48.0),
        NegotiationPipeline("Project Linden — Behavioral", "Optum Behavioral", "2026-10-31", 0.055, 0.032, 0.023, "medium", 38.0),
    ]


def _build_network() -> List[NetworkAdequacy]:
    return [
        NetworkAdequacy("UnitedHealthcare", "Atlanta, GA", 285, 0.98, 0, "no gaps"),
        NetworkAdequacy("UnitedHealthcare", "Dallas-Fort Worth", 325, 0.95, 180, "ortho sports medicine gap"),
        NetworkAdequacy("UnitedHealthcare", "Phoenix, AZ", 215, 0.92, 425, "cardiology interventional gap"),
        NetworkAdequacy("Cigna", "Miami, FL", 185, 0.94, 285, "fertility specialty gap"),
        NetworkAdequacy("Aetna", "Chicago, IL", 245, 0.96, 125, "no material gaps"),
        NetworkAdequacy("BCBS TX", "San Antonio, TX", 125, 0.88, 585, "behavioral health gap"),
        NetworkAdequacy("Humana", "Jacksonville, FL", 65, 0.85, 485, "cardiology rural gap"),
        NetworkAdequacy("Anthem CO", "Denver, CO", 152, 0.96, 85, "no material gaps"),
        NetworkAdequacy("Kaiser (NoCal)", "SF Bay Area", 0, 1.00, 0, "carve-out arrangement only"),
        NetworkAdequacy("Centene (Medicaid)", "North Carolina", 235, 0.92, 325, "dental + behavioral gaps"),
    ]


def _build_optimization() -> List[ContractOptimization]:
    return [
        ContractOptimization("Multi-state consolidation (UHG)", 4, 1.5, 6, 3.5, "all subsidiaries share pricing"),
        ContractOptimization("Value-based contract add-on (quality + shared savings)", 8, 2.8, 12, 12.5, "HEDIS + cost KPIs"),
        ContractOptimization("Clinical integration (e.g., CIN participation)", 6, 3.5, 18, 15.8, "clinical integration + anti-trust safeguards"),
        ContractOptimization("Site-neutral / ASC conversion pricing", 3, 4.2, 12, 8.5, "ASC licensure + payer contracting"),
        ContractOptimization("Bundled payment / episode pricing", 4, 2.2, 12, 4.8, "episode definition + risk model"),
        ContractOptimization("Rate floor + minimum increase clause", 10, 1.2, 6, 3.8, "next renewal cycle"),
        ContractOptimization("Payer-direct / employer-direct contracting", 3, 5.5, 18, 8.5, "direct marketing + value prop"),
        ContractOptimization("Reference-pricing adjustment", 6, 1.8, 12, 5.2, "QPA / NSA context"),
        ContractOptimization("Risk-based contract participation (2-sided)", 4, 4.5, 24, 9.5, "population health infrastructure"),
        ContractOptimization("Part B ASP+ reimbursement optimization", 5, 2.5, 12, 6.5, "Part B drug mix + buy-and-bill"),
    ]


def compute_payer_contracts() -> PayerContractResult:
    corpus = _load_corpus()
    contracts = _build_contracts()
    history = _build_history()
    concentration = _build_concentration()
    negotiations = _build_negotiations()
    network = _build_network()
    optimization = _build_optimization()

    total_rev = sum(c.annual_revenue_m for c in contracts)
    in_neg = sum(1 for c in contracts if c.renegotiation_stage == "in negotiation")
    wtd_esc = sum(c.rate_escalator_pct * c.annual_revenue_m for c in contracts) / total_rev if total_rev > 0 else 0
    exp_12mo = sum(1 for c in contracts if c.expires <= "2026-12-31")
    rev_reneg = sum(n.revenue_at_stake_m for n in negotiations)

    return PayerContractResult(
        total_contracts=len(contracts),
        total_annual_revenue_m=round(total_rev, 1),
        contracts_in_negotiation=in_neg,
        weighted_avg_escalator_pct=round(wtd_esc, 4),
        contracts_expiring_12mo=exp_12mo,
        revenue_at_renegotiation_m=round(rev_reneg, 1),
        contracts=contracts,
        history=history,
        concentration=concentration,
        negotiations=negotiations,
        network=network,
        optimization=optimization,
        corpus_deal_count=len(corpus),
    )
