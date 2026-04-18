"""Partner Economics / Physician Buy-in Calculator.

Models physician partner economics in PE healthcare platforms:
- Buy-in price (equity to purchase)
- Distributions vs salary
- Tax leakage
- Exit proceeds sharing
- Rollover equity modeling
- New partner recruitment economics
- Comparison: W-2 employee vs partner
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class PartnerTier:
    tier: str
    target_partners: int
    base_salary_k: float
    quarterly_distributions_mm: float
    equity_pct: float
    buy_in_value_mm: float
    annual_total_comp_k: float


@dataclass
class PartnerCashFlow:
    year: int
    salary_k: float
    distributions_mm: float
    total_cash_pretax_mm: float
    federal_tax_mm: float
    state_tax_mm: float
    se_tax_mm: float
    total_tax_mm: float
    after_tax_take_home_mm: float


@dataclass
class BuyInStructure:
    structure: str
    buy_in_amount_mm: float
    financing_source: str
    annual_cost_mm: float          # interest / amortization if financed
    years_to_recoup: float
    risk: str


@dataclass
class EmployeeVsPartner:
    metric: str
    employee_value: str
    partner_value: str
    delta: str
    favorable: str                 # "partner", "employee", "even"


@dataclass
class ExitProceeds:
    role: str
    equity_pct: float
    gross_proceeds_mm: float
    carry_paid_mm: float
    tax_on_proceeds_mm: float
    net_proceeds_mm: float
    moic_on_buy_in: float


@dataclass
class RecruitmentModel:
    scenario: str
    years_to_partner: int
    all_in_comp_y1_k: float
    all_in_comp_partnership_k: float
    total_5yr_value_mm: float
    retention_impact: str


@dataclass
class PartnerEconomicsResult:
    practice_revenue_mm: float
    practice_ebitda_mm: float
    total_partners: int
    avg_partner_comp_k: float
    tiers: List[PartnerTier]
    cash_flow: List[PartnerCashFlow]
    buy_in_structures: List[BuyInStructure]
    emp_vs_partner: List[EmployeeVsPartner]
    exit_proceeds: List[ExitProceeds]
    recruitment: List[RecruitmentModel]
    annual_gp_cost_mm: float
    physician_equity_pool_pct: float
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 78):
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


def _build_tiers(practice_ebitda: float, total_partners: int, phys_equity_pool: float) -> List[PartnerTier]:
    # Split partners by seniority
    senior = int(total_partners * 0.20)
    mid = int(total_partners * 0.35)
    junior = total_partners - senior - mid

    # Senior partners get larger share
    senior_pool = phys_equity_pool * 0.45
    mid_pool = phys_equity_pool * 0.35
    junior_pool = phys_equity_pool * 0.20

    sr_distributions = practice_ebitda * 0.55 * senior_pool / senior / 4 if senior else 0
    md_distributions = practice_ebitda * 0.55 * mid_pool / mid / 4 if mid else 0
    jr_distributions = practice_ebitda * 0.55 * junior_pool / junior / 4 if junior else 0

    sr_salary = 320
    md_salary = 280
    jr_salary = 240

    tiers = [
        PartnerTier(
            tier="Senior / Founding Partner",
            target_partners=senior,
            base_salary_k=sr_salary,
            quarterly_distributions_mm=round(sr_distributions, 3),
            equity_pct=round(senior_pool / senior if senior else 0, 4),
            buy_in_value_mm=round(practice_ebitda * 12 * (senior_pool / senior if senior else 0), 2),
            annual_total_comp_k=round(sr_salary + sr_distributions * 4 * 1000, 0),
        ),
        PartnerTier(
            tier="Mid-Level Partner",
            target_partners=mid,
            base_salary_k=md_salary,
            quarterly_distributions_mm=round(md_distributions, 3),
            equity_pct=round(mid_pool / mid if mid else 0, 4),
            buy_in_value_mm=round(practice_ebitda * 12 * (mid_pool / mid if mid else 0), 2),
            annual_total_comp_k=round(md_salary + md_distributions * 4 * 1000, 0),
        ),
        PartnerTier(
            tier="Junior / Recent Partner",
            target_partners=junior,
            base_salary_k=jr_salary,
            quarterly_distributions_mm=round(jr_distributions, 3),
            equity_pct=round(junior_pool / junior if junior else 0, 4),
            buy_in_value_mm=round(practice_ebitda * 12 * (junior_pool / junior if junior else 0), 2),
            annual_total_comp_k=round(jr_salary + jr_distributions * 4 * 1000, 0),
        ),
    ]
    return tiers


def _build_cash_flow(base_salary_k: float, annual_dist_mm: float, years: int) -> List[PartnerCashFlow]:
    rows = []
    for yr in range(1, years + 1):
        # Assume 4% annual inflation / growth
        salary = base_salary_k * ((1.04) ** (yr - 1))
        dist = annual_dist_mm * ((1.06) ** (yr - 1))
        total_pretax = salary / 1000 + dist
        # Taxes: 37% federal + 9% state + SE on K-1 income
        fed_tax = total_pretax * 0.37
        state_tax = total_pretax * 0.09
        se_tax = dist * 0.029    # Medicare surtax on K-1 guaranteed payments
        total_tax = fed_tax + state_tax + se_tax
        after_tax = total_pretax - total_tax
        rows.append(PartnerCashFlow(
            year=yr,
            salary_k=round(salary, 0),
            distributions_mm=round(dist, 3),
            total_cash_pretax_mm=round(total_pretax, 3),
            federal_tax_mm=round(fed_tax, 3),
            state_tax_mm=round(state_tax, 3),
            se_tax_mm=round(se_tax, 3),
            total_tax_mm=round(total_tax, 3),
            after_tax_take_home_mm=round(after_tax, 3),
        ))
    return rows


def _build_buy_in_structures(buy_in_amount: float) -> List[BuyInStructure]:
    return [
        BuyInStructure(
            structure="Full Cash Buy-in",
            buy_in_amount_mm=round(buy_in_amount, 2),
            financing_source="Personal savings",
            annual_cost_mm=0,
            years_to_recoup=0,
            risk="low",
        ),
        BuyInStructure(
            structure="Bank Loan (Personal)",
            buy_in_amount_mm=round(buy_in_amount, 2),
            financing_source="Commercial bank term loan (7%, 7-yr)",
            annual_cost_mm=round(buy_in_amount * 0.18, 3),   # amortization
            years_to_recoup=7,
            risk="medium",
        ),
        BuyInStructure(
            structure="Seller Note (Practice-financed)",
            buy_in_amount_mm=round(buy_in_amount, 2),
            financing_source="Practice seller note (6% interest, 5-yr)",
            annual_cost_mm=round(buy_in_amount * 0.22, 3),
            years_to_recoup=5,
            risk="medium",
        ),
        BuyInStructure(
            structure="Sweat Equity (phased vesting)",
            buy_in_amount_mm=round(buy_in_amount * 0.50, 2),   # 50% discount
            financing_source="Reduced distribution split + vesting",
            annual_cost_mm=round(buy_in_amount * 0.10, 3),
            years_to_recoup=4,
            risk="low",
        ),
        BuyInStructure(
            structure="PE-backed Rollover",
            buy_in_amount_mm=round(buy_in_amount, 2),
            financing_source="Rollover from sale of prior equity",
            annual_cost_mm=0,
            years_to_recoup=0,
            risk="low",
        ),
    ]


def _build_emp_vs_partner(partner_total_comp: float) -> List[EmployeeVsPartner]:
    return [
        EmployeeVsPartner(
            "Annual Cash Comp (Year 1)",
            "$350K W-2", f"${partner_total_comp:,.0f} mixed",
            f"${partner_total_comp - 350:,.0f} in favor of partner",
            "partner",
        ),
        EmployeeVsPartner(
            "Exit Equity Participation",
            "Stock options ($200K-500K)", "Full equity share (~3-8%)",
            "~3-10x more value at exit", "partner",
        ),
        EmployeeVsPartner(
            "Buy-in Capital Required",
            "$0 — 0.25% option pool", "$800K - $2.5M cash / financed",
            "Significant capital requirement", "employee",
        ),
        EmployeeVsPartner(
            "Tax Treatment",
            "W-2 — standard withholding", "K-1 / pass-through — SE tax + state",
            "~3-4% higher effective rate", "employee",
        ),
        EmployeeVsPartner(
            "Benefits (Health / Retirement)",
            "Full employer-sponsored", "Self-funded within partnership",
            "Partner pays through practice", "employee",
        ),
        EmployeeVsPartner(
            "Profitability / Governance Voice",
            "None — employment contract", "Vote + distribution rights",
            "Material governance", "partner",
        ),
        EmployeeVsPartner(
            "Downside Risk",
            "Salary floor", "Distributions can drop / zero",
            "More variable", "employee",
        ),
        EmployeeVsPartner(
            "Termination Exposure",
            "Severance package", "Buy-out at book or formula",
            "Partner needs liquidity event", "even",
        ),
    ]


def _build_exit_proceeds(equity_mm: float, ebitda_mm: float, hold_years: int) -> List[ExitProceeds]:
    exit_mult_entry = 12
    exit_ebitda = ebitda_mm * ((1.06) ** hold_years)
    exit_ev = exit_ebitda * exit_mult_entry
    # Physician equity pool
    phys_pool_pct = 0.20

    rows = []
    for role, pct_within in [("Senior Partner", 0.045), ("Mid-level Partner", 0.025), ("Junior Partner", 0.010)]:
        gross = exit_ev * phys_pool_pct * pct_within
        carry = gross * 0.20   # GP carry
        # Tax: 20% LTCG + 3.8% NIIT
        tax = (gross - carry) * 0.238
        net = gross - carry - tax
        buy_in = ebitda_mm * exit_mult_entry * phys_pool_pct * pct_within
        moic = net / buy_in if buy_in else 0
        rows.append(ExitProceeds(
            role=role,
            equity_pct=round(pct_within, 4),
            gross_proceeds_mm=round(gross, 2),
            carry_paid_mm=round(carry, 2),
            tax_on_proceeds_mm=round(tax, 2),
            net_proceeds_mm=round(net, 2),
            moic_on_buy_in=round(moic, 2),
        ))
    return rows


def _build_recruitment() -> List[RecruitmentModel]:
    return [
        RecruitmentModel(
            scenario="Direct-to-Partner (experienced)",
            years_to_partner=0,
            all_in_comp_y1_k=520,
            all_in_comp_partnership_k=620,
            total_5yr_value_mm=3.4,
            retention_impact="high — immediate equity",
        ),
        RecruitmentModel(
            scenario="2-Year Partnership Track (mid-career)",
            years_to_partner=2,
            all_in_comp_y1_k=390,
            all_in_comp_partnership_k=540,
            total_5yr_value_mm=2.8,
            retention_impact="high — defined path",
        ),
        RecruitmentModel(
            scenario="3-Year Associate Track (early career)",
            years_to_partner=3,
            all_in_comp_y1_k=320,
            all_in_comp_partnership_k=475,
            total_5yr_value_mm=2.4,
            retention_impact="medium — longer runway",
        ),
        RecruitmentModel(
            scenario="Employee-Only (no partnership)",
            years_to_partner=99,
            all_in_comp_y1_k=360,
            all_in_comp_partnership_k=410,
            total_5yr_value_mm=1.9,
            retention_impact="low — high churn risk",
        ),
        RecruitmentModel(
            scenario="Locum / Contract",
            years_to_partner=99,
            all_in_comp_y1_k=580,
            all_in_comp_partnership_k=580,
            total_5yr_value_mm=2.9,
            retention_impact="very low — gap coverage",
        ),
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_partner_economics(
    practice_revenue_mm: float = 100.0,
    practice_ebitda_mm: float = 18.0,
    total_partners: int = 20,
    hold_years: int = 5,
    physician_equity_pool: float = 0.20,
) -> PartnerEconomicsResult:
    corpus = _load_corpus()

    tiers = _build_tiers(practice_ebitda_mm, total_partners, physician_equity_pool)
    # Use mid-tier for cash flow illustration
    mid_tier = tiers[1] if len(tiers) > 1 else tiers[0]
    annual_dist = mid_tier.quarterly_distributions_mm * 4
    cash_flow = _build_cash_flow(mid_tier.base_salary_k, annual_dist, hold_years)

    # Buy-in example
    buy_in_amount = mid_tier.buy_in_value_mm
    buy_in_structures = _build_buy_in_structures(buy_in_amount)
    emp_vs_partner = _build_emp_vs_partner(mid_tier.annual_total_comp_k)
    exit_proceeds = _build_exit_proceeds(practice_revenue_mm * 0.45, practice_ebitda_mm, hold_years)
    recruitment = _build_recruitment()

    # Annual GP cost: difference vs W-2 equivalent
    annual_gp_cost = sum(t.annual_total_comp_k / 1000 * t.target_partners for t in tiers)
    avg_comp = sum(t.annual_total_comp_k * t.target_partners for t in tiers) / sum(t.target_partners for t in tiers) if sum(t.target_partners for t in tiers) else 0

    return PartnerEconomicsResult(
        practice_revenue_mm=round(practice_revenue_mm, 2),
        practice_ebitda_mm=round(practice_ebitda_mm, 2),
        total_partners=total_partners,
        avg_partner_comp_k=round(avg_comp, 0),
        tiers=tiers,
        cash_flow=cash_flow,
        buy_in_structures=buy_in_structures,
        emp_vs_partner=emp_vs_partner,
        exit_proceeds=exit_proceeds,
        recruitment=recruitment,
        annual_gp_cost_mm=round(annual_gp_cost, 2),
        physician_equity_pool_pct=round(physician_equity_pool, 3),
        corpus_deal_count=len(corpus),
    )
