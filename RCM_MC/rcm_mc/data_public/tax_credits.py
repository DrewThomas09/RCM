"""Tax Credits / Incentives Tracker.

Tracks federal + state tax credits, incentives, and deferrals across
portfolio: R&D credit, ITC, Opportunity Zones, WOTC, state incentives,
conservation easements, transfer pricing benefit.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class TaxCredit:
    deal: str
    credit_type: str
    credit_name: str
    tax_year: int
    gross_credit_m: float
    carryforward_m: float
    utilized_m: float
    remaining_m: float
    expiration_year: int
    counsel: str


@dataclass
class StateIncentive:
    deal: str
    state: str
    program: str
    incentive_type: str
    award_m: float
    period_years: int
    annual_value_m: float
    obligations: str
    status: str


@dataclass
class OpportunityZone:
    project: str
    deal: str
    qoz_tract: str
    invested_m: float
    investment_date: str
    hold_period_remaining_years: float
    deferred_gain_m: float
    projected_exit_value_m: float
    step_up_basis_pct: float


@dataclass
class WOTCProgram:
    deal: str
    annual_headcount_hired: int
    eligible_hires: int
    eligible_rate_pct: float
    annual_credit_m: float
    credits_since_inception_m: float


@dataclass
class TransferPricingBenefit:
    deal: str
    structure: str
    annual_tax_benefit_m: float
    risk_level: str
    documentation_status: str
    counsel: str


@dataclass
class CreditPipeline:
    opportunity: str
    deal: str
    credit_type: str
    estimated_annual_benefit_m: float
    implementation_cost_m: float
    probability_pct: float
    timeline_months: int


@dataclass
class TaxCreditResult:
    total_credits_gross_m: float
    total_credits_utilized_m: float
    total_credits_remaining_m: float
    total_state_incentives_annual_m: float
    total_annual_benefit_m: float
    total_deals: int
    credits: List[TaxCredit]
    state_incentives: List[StateIncentive]
    opportunity_zones: List[OpportunityZone]
    wotc: List[WOTCProgram]
    transfer_pricing: List[TransferPricingBenefit]
    pipeline: List[CreditPipeline]
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


def _build_credits() -> List[TaxCredit]:
    return [
        TaxCredit("Project Oak — RCM SaaS", "Federal", "R&D Tax Credit (IRC §41)", 2024, 8.5, 3.2, 2.5, 9.2, 2044, "KPMG"),
        TaxCredit("Project Oak — RCM SaaS", "Federal", "R&D Tax Credit (IRC §41)", 2025, 9.8, 0.0, 0.0, 9.8, 2045, "KPMG"),
        TaxCredit("Project Oak — RCM SaaS", "State (CA, NY, MA)", "State R&D Credits", 2024, 2.8, 1.2, 0.5, 3.5, 2044, "KPMG"),
        TaxCredit("Project Cypress — GI Network", "Federal", "Federal Work Opportunity Tax Credit", 2024, 0.85, 0.0, 0.85, 0.0, 2024, "Deloitte"),
        TaxCredit("Project Cypress — GI Network", "Federal", "R&D Tax Credit (IRC §41)", 2024, 1.5, 0.5, 0.8, 1.2, 2044, "Deloitte"),
        TaxCredit("Project Cypress — GI Network", "Texas + Georgia", "State Job Creation Credits", 2024, 1.2, 0.3, 0.8, 0.7, 2028, "Local counsel"),
        TaxCredit("Project Magnolia — MSK Platform", "Federal", "R&D Tax Credit (IRC §41)", 2024, 0.85, 0.2, 0.5, 0.55, 2044, "PwC"),
        TaxCredit("Project Redwood — Behavioral", "Federal", "Federal WOTC", 2024, 1.1, 0.0, 1.1, 0.0, 2024, "Deloitte"),
        TaxCredit("Project Redwood — Behavioral", "State (multi-state)", "State Behavioral Health Access Credit", 2024, 2.5, 0.8, 1.2, 2.1, 2030, "Local counsel"),
        TaxCredit("Project Sage — Home Health", "Federal", "Federal WOTC", 2024, 2.8, 0.0, 2.8, 0.0, 2024, "Deloitte"),
        TaxCredit("Project Sage — Home Health", "State (NC + FL)", "State Home Care Incentive Credits", 2024, 0.95, 0.3, 0.4, 0.85, 2029, "Local counsel"),
        TaxCredit("Project Willow — Fertility", "Federal", "R&D Tax Credit (IRC §41)", 2024, 1.8, 0.5, 0.8, 1.5, 2044, "KPMG"),
        TaxCredit("Project Laurel — Derma", "Federal", "Section 179D (energy efficient)", 2024, 0.35, 0.0, 0.35, 0.0, 2024, "KPMG"),
        TaxCredit("Project Fir — Lab / Pathology", "Federal", "R&D Tax Credit (IRC §41)", 2024, 2.5, 0.8, 1.2, 2.1, 2044, "PwC"),
        TaxCredit("Project Cedar — Cardiology", "Federal", "R&D Tax Credit (IRC §41)", 2024, 0.55, 0.0, 0.45, 0.10, 2044, "EY"),
        TaxCredit("Project Basil — Dental DSO", "Federal", "Federal WOTC", 2024, 1.5, 0.0, 1.5, 0.0, 2024, "Deloitte"),
        TaxCredit("Project Thyme — Specialty Pharm", "Federal", "R&D Tax Credit (IRC §41)", 2024, 3.2, 1.1, 1.5, 2.8, 2044, "PwC"),
        TaxCredit("Project Thyme — Specialty Pharm", "Federal", "Section 45Q (carbon sequestration)", 2024, 0.25, 0.0, 0.25, 0.0, 2044, "EY"),
    ]


def _build_state_incentives() -> List[StateIncentive]:
    return [
        StateIncentive("Project Cypress — GI Network", "Georgia", "Georgia Quality Jobs Tax Credit", "Payroll credit", 4.5, 5, 0.90,
                       "Maintain 250+ jobs + minimum wage level", "active"),
        StateIncentive("Project Cypress — GI Network", "Texas", "Texas Enterprise Fund", "Job creation grant", 2.2, 3, 0.73,
                       "Create 125 net new jobs + capital investment", "active"),
        StateIncentive("Project Magnolia — MSK", "Arizona", "Arizona Quality Jobs Credit", "Payroll credit", 1.8, 5, 0.36,
                       "Hire 85 new Arizona employees", "active"),
        StateIncentive("Project Cedar — Cardiology", "Arizona", "Arizona Angel Investment Credit", "Investment credit", 0.85, 3, 0.28,
                       "Minority-owned capital partner participation", "active"),
        StateIncentive("Project Laurel — Derma", "North Carolina", "NC Job Development Investment Grant", "Payroll refund", 2.5, 5, 0.50,
                       "Maintain 180 jobs + $12M capital investment", "active"),
        StateIncentive("Project Willow — Fertility", "Colorado", "Colorado Strategic Fund", "Performance grant", 1.2, 3, 0.40,
                       "Open Denver IVF center + hire 45 FTEs", "pending"),
        StateIncentive("Project Ash — Infusion", "Massachusetts", "MA Life Sciences Tax Incentive", "Jobs credit + ITC", 3.5, 5, 0.70,
                       "Create 85 qualified research positions", "active"),
        StateIncentive("Project Oak — RCM SaaS", "California", "CA R&D Tax Credit + Partial Sales Tax Exemption", "R&D + sales tax", 1.8, 3, 0.60,
                       "R&D spend within CA + qualified property purchases", "active"),
        StateIncentive("Project Spruce — Radiology", "Colorado", "CO Job Creation Performance Incentive Fund", "Payroll credit", 1.5, 3, 0.50,
                       "Create 60 new Colorado positions", "active"),
        StateIncentive("Project Basil — Dental DSO", "Indiana", "Indiana EDGE Credit", "Payroll refund", 2.2, 5, 0.44,
                       "Create 220 new Indiana jobs", "active"),
        StateIncentive("Project Thyme — Specialty Pharm", "New Jersey", "NJ NewJersey ERG / Emerge Program", "Income tax credit", 4.5, 7, 0.64,
                       "Maintain 185 jobs in Newark tract + capital commit", "active"),
        StateIncentive("Project Fir — Lab / Pathology", "Illinois", "IL EDGE Credit", "Income tax credit", 2.8, 5, 0.56,
                       "Maintain 150 jobs + $25M investment", "active"),
    ]


def _build_opportunity_zones() -> List[OpportunityZone]:
    return [
        OpportunityZone("Atlanta ASC — Cypress", "Project Cypress — GI Network", "GA-121-05-3800", 8.5, "2022-08-15",
                        5.5, 4.2, 22.5, 1.15),
        OpportunityZone("Nashville ASC — Cypress", "Project Cypress — GI Network", "TN-047-01-5400", 7.5, "2022-11-22",
                        5.8, 3.8, 18.5, 1.15),
        OpportunityZone("Austin MSK Clinic — Magnolia", "Project Magnolia — MSK Platform", "TX-453-01-2100", 4.5, "2023-02-10",
                        6.2, 2.2, 12.5, 1.00),
        OpportunityZone("Austin MSK Clinic 2 — Magnolia", "Project Magnolia — MSK Platform", "TX-453-01-2105", 4.5, "2023-05-18",
                        6.5, 2.2, 12.5, 1.00),
        OpportunityZone("Raleigh Derma — Laurel", "Project Laurel — Derma", "NC-183-05-1400", 1.8, "2022-09-25",
                        5.7, 0.9, 4.2, 1.15),
        OpportunityZone("Charleston Derma — Laurel", "Project Laurel — Derma", "SC-019-01-2700", 1.8, "2023-08-15",
                        6.9, 0.9, 4.2, 1.15),
        OpportunityZone("Chicago IVF — Willow", "Project Willow — Fertility", "IL-031-11-0420", 8.5, "2023-06-01",
                        6.7, 4.2, 18.5, 1.15),
        OpportunityZone("Denver IVF — Willow", "Project Willow — Fertility", "CO-031-03-2800", 8.5, "2024-03-15",
                        7.5, 4.2, 18.5, 1.15),
        OpportunityZone("Newark Specialty Pharm — Thyme", "Project Thyme — Specialty Pharm", "NJ-013-08-0700", 12.0, "2023-10-15",
                        7.1, 5.8, 28.5, 1.15),
    ]


def _build_wotc() -> List[WOTCProgram]:
    return [
        WOTCProgram("Project Cypress — GI Network", 285, 48, 0.168, 0.85, 3.8),
        WOTCProgram("Project Redwood — Behavioral", 485, 125, 0.258, 1.1, 4.2),
        WOTCProgram("Project Sage — Home Health", 850, 265, 0.312, 2.8, 11.5),
        WOTCProgram("Project Magnolia — MSK", 185, 28, 0.151, 0.55, 2.2),
        WOTCProgram("Project Laurel — Derma", 125, 22, 0.176, 0.45, 1.8),
        WOTCProgram("Project Basil — Dental DSO", 385, 85, 0.221, 1.5, 6.5),
        WOTCProgram("Project Fir — Lab / Pathology", 225, 48, 0.213, 0.85, 3.5),
        WOTCProgram("Project Linden — Behavioral", 285, 82, 0.288, 0.95, 3.8),
    ]


def _build_transfer_pricing() -> List[TransferPricingBenefit]:
    return [
        TransferPricingBenefit("Project Oak — RCM SaaS", "IP licensing (US → Ireland/Cayman)", 4.5, "medium",
                               "IRS APA pending", "Baker McKenzie"),
        TransferPricingBenefit("Project Thyme — Specialty Pharm", "Specialty pharma supply chain (contract manufacturing)", 3.8, "low",
                               "Contemporaneous documentation", "PwC"),
        TransferPricingBenefit("Project Fir — Lab / Pathology", "Lab services centralization (US → international)", 2.2, "medium",
                               "Contemporaneous documentation", "EY"),
        TransferPricingBenefit("Project Willow — Fertility", "Technology IP (ML + embryo lab)", 1.5, "low",
                               "Contemporaneous documentation", "KPMG"),
        TransferPricingBenefit("Project Spruce — Radiology", "Teleradiology cross-border pricing", 2.5, "medium",
                               "Contemporaneous documentation", "KPMG"),
    ]


def _build_pipeline() -> List[CreditPipeline]:
    return [
        CreditPipeline("R&D Study Retroactive (4 yrs lookback)", "Project Cedar — Cardiology", "Federal R&D",
                       2.8, 0.5, 85, 6),
        CreditPipeline("R&D Study Retroactive (4 yrs lookback)", "Project Magnolia — MSK Platform", "Federal R&D",
                       2.5, 0.45, 80, 6),
        CreditPipeline("State R&D Credit Expansion (CA)", "Project Oak — RCM SaaS", "State R&D",
                       1.8, 0.2, 90, 3),
        CreditPipeline("Section 179D Energy Efficient Buildings (retroactive)", "Multi-deal (8 real estate)", "Federal 179D",
                       2.2, 0.3, 75, 9),
        CreditPipeline("Section 45L New Energy Efficient Home Credit", "Project Magnolia — MSK (de novo)", "Federal 45L",
                       0.35, 0.08, 65, 6),
        CreditPipeline("Conservation Easement (clinical campus)", "Project Cypress — GI Network", "Federal Conservation",
                       2.5, 0.4, 50, 12),
        CreditPipeline("QOZ Designation (Charleston site)", "Project Laurel — Derma", "Federal QOZ",
                       0.85, 0.05, 95, 3),
        CreditPipeline("Cost Segregation Study (post-renovation)", "Project Cedar — Cardiology", "Federal Depreciation",
                       1.2, 0.15, 90, 4),
        CreditPipeline("ERC Retroactive Claim (2020-2021 PHE)", "Multi-deal (behavioral + home health)", "Federal ERC",
                       3.8, 0.6, 60, 9),
        CreditPipeline("Section 48 Investment Tax Credit (solar)", "Project Sage — Home Health HQ", "Federal ITC",
                       0.55, 0.15, 85, 12),
    ]


def compute_tax_credits() -> TaxCreditResult:
    corpus = _load_corpus()
    credits = _build_credits()
    state_incentives = _build_state_incentives()
    opportunity_zones = _build_opportunity_zones()
    wotc = _build_wotc()
    transfer_pricing = _build_transfer_pricing()
    pipeline = _build_pipeline()

    total_gross = sum(c.gross_credit_m for c in credits)
    total_util = sum(c.utilized_m for c in credits)
    total_rem = sum(c.remaining_m for c in credits)
    state_annual = sum(s.annual_value_m for s in state_incentives)
    wotc_annual = sum(w.annual_credit_m for w in wotc)
    tp_annual = sum(t.annual_tax_benefit_m for t in transfer_pricing)
    total_annual = state_annual + wotc_annual + tp_annual + total_gross / 5.0

    deals_set = {c.deal for c in credits} | {s.deal for s in state_incentives} | {w.deal for w in wotc}

    return TaxCreditResult(
        total_credits_gross_m=round(total_gross, 1),
        total_credits_utilized_m=round(total_util, 1),
        total_credits_remaining_m=round(total_rem, 1),
        total_state_incentives_annual_m=round(state_annual, 1),
        total_annual_benefit_m=round(total_annual, 1),
        total_deals=len(deals_set),
        credits=credits,
        state_incentives=state_incentives,
        opportunity_zones=opportunity_zones,
        wotc=wotc,
        transfer_pricing=transfer_pricing,
        pipeline=pipeline,
        corpus_deal_count=len(corpus),
    )
