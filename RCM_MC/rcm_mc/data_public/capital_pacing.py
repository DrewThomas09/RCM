"""Capital Call Pacing Model.

Fund-level cashflow engine for PE healthcare funds. Models:
- Contribution schedule (capital calls)
- Distribution schedule (exits + recaps)
- J-curve trajectory (IRR over time)
- NAV evolution
- DPI / TVPI / RVPI evolution
- Vintage year comparison
- LP dry powder utilization
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class YearCashflow:
    year: int
    quarter: int
    capital_called_mm: float
    cumulative_called_mm: float
    deployed_mm: float
    cumulative_deployed_mm: float
    distributions_mm: float
    cumulative_distributions_mm: float
    unrealized_nav_mm: float
    total_value_mm: float
    dpi: float
    rvpi: float
    tvpi: float
    interim_irr: float


@dataclass
class DealInvestment:
    deal_id: str
    sector: str
    investment_year: int
    initial_check_mm: float
    follow_on_mm: float
    total_invested_mm: float
    current_fair_value_mm: float
    projected_moic: float
    projected_exit_year: int
    status: str


@dataclass
class VintageComparison:
    vintage_year: int
    fund_size_mm: float
    current_tvpi: float
    current_dpi: float
    projected_net_moic: float
    projected_net_irr: float
    years_since_vintage: int


@dataclass
class CommitmentUtilization:
    category: str
    committed_mm: float
    deployed_mm: float
    utilization_pct: float
    remaining_mm: float
    status: str


@dataclass
class CapitalPacingResult:
    fund_size_mm: float
    vintage_year: int
    current_year: int
    fund_age_years: float
    total_called_mm: float
    total_deployed_mm: float
    total_distributions_mm: float
    current_nav_mm: float
    current_tvpi: float
    current_dpi: float
    current_rvpi: float
    current_net_irr: float
    cashflows: List[YearCashflow]
    investments: List[DealInvestment]
    vintage_peers: List[VintageComparison]
    commitments: List[CommitmentUtilization]
    corpus_deal_count: int


def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 91):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    try:
        from rcm_mc.data_public.deals_corpus import _SEED_DEALS
        deals = _SEED_DEALS + deals
    except Exception:
        pass
    return deals


def _build_cashflows(fund_size: float, vintage_year: int,
                     current_year: int) -> List[YearCashflow]:
    import hashlib
    fund_life = 10
    # Typical PE pacing: 70% deployed in first 5 years, distributions begin year 4
    call_pattern = [0.08, 0.18, 0.22, 0.18, 0.14, 0.09, 0.06, 0.03, 0.02, 0.00]
    dist_pattern = [0.00, 0.00, 0.00, 0.02, 0.08, 0.18, 0.24, 0.28, 0.20, 0.18]

    rows = []
    cum_called = 0
    cum_deployed = 0
    cum_dist = 0
    nav = 0
    for i in range(fund_life):
        year = vintage_year + i
        if year > current_year + 3:  # only show 3 years of projection
            break
        h = int(hashlib.md5(f"{year}".encode()).hexdigest()[:6], 16)
        called = fund_size * call_pattern[i]
        deployed = called * 0.92  # 8% reserve for fees / expenses
        dist = fund_size * dist_pattern[i] * (1.0 if year <= current_year else 0.85)  # project conservatively
        cum_called += called
        cum_deployed += deployed
        cum_dist += dist
        # NAV: deployed accumulating at ~12% IRR, minus distributions
        nav = cum_deployed * ((1 + 0.12) ** (i * 0.4)) - cum_dist
        nav = max(0, nav)
        total = cum_dist + nav
        dpi = cum_dist / cum_called if cum_called else 0
        rvpi = nav / cum_called if cum_called else 0
        tvpi = total / cum_called if cum_called else 0
        irr = (tvpi ** (1 / max(i + 1, 1))) - 1 if tvpi > 0 else 0
        # Early J-curve: IRR negative first 2 years
        if i < 2: irr = -0.08 - i * 0.04
        elif i == 2: irr = 0.03
        rows.append(YearCashflow(
            year=year,
            quarter=4,
            capital_called_mm=round(called, 2),
            cumulative_called_mm=round(cum_called, 2),
            deployed_mm=round(deployed, 2),
            cumulative_deployed_mm=round(cum_deployed, 2),
            distributions_mm=round(dist, 2),
            cumulative_distributions_mm=round(cum_dist, 2),
            unrealized_nav_mm=round(nav, 2),
            total_value_mm=round(total, 2),
            dpi=round(dpi, 3),
            rvpi=round(rvpi, 3),
            tvpi=round(tvpi, 3),
            interim_irr=round(irr, 4),
        ))
    return rows


def _build_investments(fund_size: float, vintage_year: int,
                       current_year: int) -> List[DealInvestment]:
    import hashlib
    sectors = [
        "Primary Care Platform", "ASC Network", "Behavioral Health",
        "Dental DSO", "Dermatology Group", "Orthopedic Rehab",
        "Home Health", "Ophthalmology", "Women's Health / OB", "Pediatric Therapy",
        "Cardiology", "Specialty Pharmacy", "Medical Devices",
    ]
    rows = []
    total_allocated = 0
    for i, sector in enumerate(sectors):
        h = int(hashlib.md5(f"{sector}{i}".encode()).hexdigest()[:6], 16)
        check_year = vintage_year + 1 + (i % 4)
        if check_year > current_year: break
        initial = fund_size * 0.07 * (0.5 + (h % 25) / 100)
        followon = initial * (0.2 + (h % 20) / 100)
        total = initial + followon
        if total_allocated + total > fund_size * 0.85:
            break
        total_allocated += total
        years_held = current_year - check_year
        projected_moic = 1.8 + (h % 120) / 100
        current_fv = total * (0.7 + years_held * 0.3 * (projected_moic - 1) / 4)
        statuses = ["Active", "Active", "Exited", "Active", "Held"]
        status = statuses[h % len(statuses)] if check_year < current_year - 3 else "Active"
        exit_year = check_year + int(4 + (h % 3))
        rows.append(DealInvestment(
            deal_id=f"INV-{i + 1:03d}",
            sector=sector,
            investment_year=check_year,
            initial_check_mm=round(initial, 2),
            follow_on_mm=round(followon, 2),
            total_invested_mm=round(total, 2),
            current_fair_value_mm=round(current_fv, 2),
            projected_moic=round(projected_moic, 2),
            projected_exit_year=exit_year,
            status=status,
        ))
    return rows


def _build_vintage_peers(fund_vintage: int, current_year: int,
                         current_tvpi: float) -> List[VintageComparison]:
    import hashlib
    peers = [
        ("2016 Healthcare Fund III", 2016, 850),
        ("2017 Healthcare Fund IV", 2017, 1200),
        ("2018 Buyout Fund V", 2018, 1850),
        ("2019 Healthcare Fund VI", 2019, 2400),
        ("2020 Healthcare Fund VII", 2020, 1650),
        ("2021 Healthcare Fund VIII", 2021, 2850),
        ("2022 Healthcare Fund IX", 2022, 1950),
    ]
    rows = []
    for label, vint, size in peers:
        age = current_year - vint
        h = int(hashlib.md5(label.encode()).hexdigest()[:6], 16)
        # Mature funds have higher DPI, higher TVPI
        tvpi = 1.1 + age * 0.15 + (h % 40) / 100
        dpi = max(0, tvpi - 1 + age * 0.08 - 0.4)
        proj_moic = tvpi * 1.05
        proj_irr = (proj_moic ** (1 / 6)) - 1
        rows.append(VintageComparison(
            vintage_year=vint,
            fund_size_mm=float(size),
            current_tvpi=round(tvpi, 2),
            current_dpi=round(dpi, 2),
            projected_net_moic=round(proj_moic, 2),
            projected_net_irr=round(proj_irr, 4),
            years_since_vintage=age,
        ))
    return rows


def _build_commitments(fund_size: float, current_deployed: float) -> List[CommitmentUtilization]:
    rows = []
    buckets = [
        ("Platform Investments (70% target)", fund_size * 0.70, current_deployed * 0.72, "pacing with plan"),
        ("Add-On / Bolt-On Reserve (20%)", fund_size * 0.20, current_deployed * 0.18, "appropriate reserve"),
        ("Management Fee Reserve (4%)", fund_size * 0.04, current_deployed * 0.035, "on budget"),
        ("Fund Expense Reserve (2%)", fund_size * 0.02, current_deployed * 0.018, "on budget"),
        ("Dry Powder / New Investments (4%)", fund_size * 0.04, current_deployed * 0.032, "appropriate for vintage"),
    ]
    for label, cmt, depl, status in buckets:
        util = depl / cmt if cmt else 0
        rows.append(CommitmentUtilization(
            category=label,
            committed_mm=round(cmt, 2),
            deployed_mm=round(depl, 2),
            utilization_pct=round(util, 4),
            remaining_mm=round(cmt - depl, 2),
            status=status,
        ))
    return rows


def compute_capital_pacing(
    fund_size_mm: float = 1500.0,
    vintage_year: int = 2021,
    current_year: int = 2026,
) -> CapitalPacingResult:
    corpus = _load_corpus()

    cashflows = _build_cashflows(fund_size_mm, vintage_year, current_year)
    investments = _build_investments(fund_size_mm, vintage_year, current_year)
    vintage_peers = _build_vintage_peers(vintage_year, current_year, 0)

    current_cf = cashflows[-1] if cashflows else None
    total_called = current_cf.cumulative_called_mm if current_cf else 0
    total_deployed = current_cf.cumulative_deployed_mm if current_cf else 0
    total_dist = current_cf.cumulative_distributions_mm if current_cf else 0
    current_nav = current_cf.unrealized_nav_mm if current_cf else 0
    current_tvpi = current_cf.tvpi if current_cf else 0
    current_dpi = current_cf.dpi if current_cf else 0
    current_rvpi = current_cf.rvpi if current_cf else 0
    current_irr = current_cf.interim_irr if current_cf else 0

    commitments = _build_commitments(fund_size_mm, total_deployed)

    fund_age = current_year - vintage_year

    return CapitalPacingResult(
        fund_size_mm=round(fund_size_mm, 2),
        vintage_year=vintage_year,
        current_year=current_year,
        fund_age_years=fund_age,
        total_called_mm=round(total_called, 2),
        total_deployed_mm=round(total_deployed, 2),
        total_distributions_mm=round(total_dist, 2),
        current_nav_mm=round(current_nav, 2),
        current_tvpi=round(current_tvpi, 3),
        current_dpi=round(current_dpi, 3),
        current_rvpi=round(current_rvpi, 3),
        current_net_irr=round(current_irr, 4),
        cashflows=cashflows,
        investments=investments,
        vintage_peers=vintage_peers,
        commitments=commitments,
        corpus_deal_count=len(corpus),
    )
