"""Direct-to-Employer Contract Analyzer.

Models employer direct-contract economics for PE-backed provider platforms:
centers of excellence (COEs), bundled-payment arrangements, on-site clinics,
and direct-primary-care agreements bypassing traditional payers.

Key diligence questions:
- Revenue per employee-life
- Bundle profitability vs fee-for-service
- Self-insured employer exposure (ERISA)
- Travel reimbursement accounting
- Stop-loss interaction
- Attrition risk if employer switches TPA
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class EmployerContract:
    employer: str
    industry: str
    covered_lives: int
    contract_type: str
    annual_revenue_mm: float
    utilization_rate: float
    pmpy_rev: float
    renewal_year: int
    churn_risk: str


@dataclass
class COEBundle:
    procedure: str
    bundled_price_k: float
    ffs_benchmark_k: float
    gross_margin_pct: float
    case_volume_annual: int
    annual_revenue_mm: float
    travel_reimbursement_k: float


@dataclass
class OnsiteClinic:
    location: str
    employer: str
    employee_lives: int
    annual_visits: int
    annual_fee_mm: float
    capacity_utilization_pct: float
    nps_score: int


@dataclass
class ERISAConsideration:
    topic: str
    description: str
    exposure_mm: float
    mitigation: str


@dataclass
class DPCOpportunity:
    market: str
    employer_count: int
    employee_lives: int
    rfp_pipeline_mm: float
    win_probability_pct: float
    expected_revenue_mm: float


@dataclass
class DirectEmployerResult:
    total_employers: int
    total_lives: int
    total_annual_revenue_mm: float
    blended_pmpy: float
    coe_margin_pct: float
    onsite_capacity_pct: float
    contracts: List[EmployerContract]
    coes: List[COEBundle]
    onsites: List[OnsiteClinic]
    erisa: List[ERISAConsideration]
    pipeline: List[DPCOpportunity]
    corpus_deal_count: int


def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 95):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    return deals


def _build_contracts() -> List[EmployerContract]:
    return [
        EmployerContract("Walmart Centers of Excellence", "Retail", 1650000, "COE bundle",
                         85.5, 0.008, 3250, 2027, "low"),
        EmployerContract("Amazon Internal Health (Amazon Care alt)", "Tech", 1200000, "On-site + COE",
                         62.5, 0.032, 1820, 2026, "medium"),
        EmployerContract("Boeing Touchstone Network", "Aerospace", 185000, "Direct PPO",
                         38.2, 0.24, 4200, 2028, "low"),
        EmployerContract("GM EBCH Network", "Manufacturing", 235000, "COE + DPC",
                         48.5, 0.18, 2500, 2027, "medium"),
        EmployerContract("Cleveland Clinic Employer Solutions", "Multi-employer", 420000, "Direct access",
                         92.5, 0.22, 3100, 2029, "low"),
        EmployerContract("JPMorgan Chase Premium Network", "Financial", 280000, "COE + on-site",
                         55.8, 0.15, 2880, 2026, "medium"),
        EmployerContract("Disney Cast Member Health", "Entertainment", 195000, "On-site clinic",
                         28.5, 0.045, 1850, 2025, "high"),
        EmployerContract("Lowe's Home Improvement", "Retail", 310000, "DPC + COE",
                         42.8, 0.025, 1620, 2027, "low"),
        EmployerContract("Intel Corp Platforms", "Tech", 105000, "On-site + DPC", 32.5, 0.068, 3480, 2028, "low"),
        EmployerContract("FedEx Freight Network", "Logistics", 425000, "COE bundle", 45.2, 0.012, 1340, 2026, "medium"),
    ]


def _build_coes() -> List[COEBundle]:
    return [
        COEBundle("Hip Replacement", 38.5, 54.5, 0.38, 380, 14.63, 2.5),
        COEBundle("Knee Replacement", 34.8, 48.2, 0.41, 650, 22.62, 2.8),
        COEBundle("Spinal Fusion", 78.5, 112.0, 0.32, 185, 14.52, 3.2),
        COEBundle("Cardiac Bypass (CABG)", 72.5, 98.0, 0.28, 145, 10.51, 3.5),
        COEBundle("Bariatric Surgery", 24.8, 38.5, 0.44, 520, 12.90, 2.2),
        COEBundle("Oncology Episode (Breast)", 85.0, 125.0, 0.30, 125, 10.63, 4.2),
        COEBundle("Complex GI Procedure", 42.5, 62.0, 0.35, 210, 8.93, 2.5),
        COEBundle("Fertility Cycle (IVF)", 22.5, 38.0, 0.38, 385, 8.66, 1.8),
        COEBundle("Maternity Complex", 15.8, 24.0, 0.30, 780, 12.32, 1.5),
        COEBundle("Behavioral Health 90-day", 18.5, 32.0, 0.42, 420, 7.77, 0.0),
    ]


def _build_onsites() -> List[OnsiteClinic]:
    return [
        OnsiteClinic("Bentonville HQ", "Walmart", 18000, 32000, 4.8, 0.72, 78),
        OnsiteClinic("Seattle Campus", "Amazon", 42000, 68000, 6.2, 0.85, 82),
        OnsiteClinic("Detroit Plant", "GM", 12000, 18500, 2.8, 0.78, 74),
        OnsiteClinic("JPMC Manhattan", "JPMorgan", 25000, 35000, 5.5, 0.82, 81),
        OnsiteClinic("Everett Factory", "Boeing", 18000, 28500, 4.2, 0.68, 72),
        OnsiteClinic("Burbank Studios", "Disney", 14000, 22000, 3.5, 0.65, 69),
        OnsiteClinic("Mooresville HQ", "Lowe's", 8500, 12000, 1.9, 0.55, 76),
        OnsiteClinic("Folsom Campus", "Intel", 11500, 17000, 2.6, 0.72, 80),
    ]


def _build_erisa() -> List[ERISAConsideration]:
    return [
        ERISAConsideration("Self-Insured Plan Structure",
                           "All direct contracts with self-insured employers fall under ERISA preemption, limiting state-law exposure.",
                           0.0, "Standard structure; no material exposure"),
        ERISAConsideration("State Mandate Override Risk",
                           "State attempts to impose benefit mandates on ERISA plans historically preempted, but activist states (NY, CA) testing limits.",
                           3.5, "Monitor state regulation; maintain ERISA preemption documentation"),
        ERISAConsideration("Non-Network Balance Billing",
                           "Direct contracts outside of employer's TPA network may generate balance bills; employer must contract explicit.",
                           2.8, "Ensure employer explicit in-network designation in contract"),
        ERISAConsideration("Stop-Loss Interaction",
                           "Bundled-case pricing creates stop-loss claim timing issues; reinsurance may disallow certain bundled payments.",
                           8.5, "Pre-clear bundled pricing structure with employer's stop-loss carrier"),
        ERISAConsideration("Travel Reimbursement Tax Treatment",
                           "Travel for COE may be taxable imputed income to employee unless structured as medical-expense reimbursement.",
                           1.8, "Structure as IRS §213 medical expense; consult employer's ERISA counsel"),
        ERISAConsideration("Fiduciary Exposure for Employers",
                           "DOL has signaled increased scrutiny on PBM / employer direct-contract fiduciary duty; transitive exposure to provider.",
                           0.0, "Indemnification clause in direct-contract SPA"),
    ]


def _build_pipeline() -> List[DPCOpportunity]:
    return [
        DPCOpportunity("Dallas-Fort Worth Metro", 85, 720000, 45.5, 0.35, 15.9),
        DPCOpportunity("Atlanta Metro", 68, 540000, 38.5, 0.30, 11.5),
        DPCOpportunity("Phoenix-Mesa", 58, 480000, 32.5, 0.38, 12.4),
        DPCOpportunity("Minneapolis-St. Paul", 48, 425000, 28.5, 0.42, 12.0),
        DPCOpportunity("Nashville Metro", 42, 320000, 22.5, 0.40, 9.0),
        DPCOpportunity("Charlotte Metro", 38, 295000, 19.5, 0.35, 6.8),
        DPCOpportunity("Denver Metro", 45, 385000, 26.8, 0.28, 7.5),
        DPCOpportunity("Austin Metro", 55, 420000, 32.5, 0.45, 14.6),
    ]


def compute_direct_employer() -> DirectEmployerResult:
    corpus = _load_corpus()

    contracts = _build_contracts()
    coes = _build_coes()
    onsites = _build_onsites()
    erisa = _build_erisa()
    pipeline = _build_pipeline()

    total_lives = sum(c.covered_lives for c in contracts)
    total_rev = sum(c.annual_revenue_mm for c in contracts)
    total_rev += sum(c.annual_revenue_mm for c in coes)
    total_rev += sum(c.annual_fee_mm for c in onsites)

    coe_margin = sum(c.gross_margin_pct * c.annual_revenue_mm for c in coes) / sum(c.annual_revenue_mm for c in coes) if coes else 0
    onsite_cap = sum(o.capacity_utilization_pct for o in onsites) / len(onsites) if onsites else 0

    pmpy = total_rev * 1000000 / total_lives if total_lives else 0

    return DirectEmployerResult(
        total_employers=len(contracts),
        total_lives=total_lives,
        total_annual_revenue_mm=round(total_rev, 2),
        blended_pmpy=round(pmpy, 2),
        coe_margin_pct=round(coe_margin, 4),
        onsite_capacity_pct=round(onsite_cap, 4),
        contracts=contracts,
        coes=coes,
        onsites=onsites,
        erisa=erisa,
        pipeline=pipeline,
        corpus_deal_count=len(corpus),
    )
