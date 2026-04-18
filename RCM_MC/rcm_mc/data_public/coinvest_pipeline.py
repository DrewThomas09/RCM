"""Co-Investment Pipeline / LP Allocation Tracker.

Tracks active co-invest opportunities, LP allocations, fee / carry
economics, historical realizations, and LP appetite by strategy.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class CoinvestDeal:
    deal: str
    sector: str
    sponsor: str
    equity_check_m: float
    coinvest_allocation_m: float
    allocation_status: str
    management_fee_pct: float
    carry_pct: float
    hurdle_pct: float
    expected_close: str


@dataclass
class LPParticipation:
    lp_name: str
    lp_type: str
    commitment_m: float
    coinvests_active: int
    coinvests_total: int
    avg_check_m: float
    aum_b: float
    appetite: str


@dataclass
class SectorAllocation:
    sector: str
    active_opportunities: int
    total_equity_m: float
    allocated_m: float
    unallocated_m: float
    avg_fee_pct: float
    avg_carry_pct: float


@dataclass
class HistoricalRealization:
    deal: str
    sector: str
    sponsor: str
    vintage: int
    exit_year: int
    coinvest_invested_m: float
    coinvest_realized_m: float
    gross_moic: float
    net_moic: float
    gross_irr_pct: float
    dpi: float


@dataclass
class FeeStructure:
    lp_tier: str
    tiers_description: str
    mgmt_fee_discount: float
    carry_reduction: float
    hurdle_concession_pct: float
    realized_savings_m: float


@dataclass
class DealCapacity:
    deal: str
    total_equity_m: float
    sponsor_check_m: float
    anchor_coinvest_m: float
    remaining_capacity_m: float
    indicative_demand_m: float
    oversubscribed: float
    allocation_methodology: str


@dataclass
class CoinvestResult:
    active_opportunities: int
    total_equity_pipeline_m: float
    total_coinvest_available_m: float
    total_coinvest_allocated_m: float
    historical_avg_moic: float
    historical_avg_irr_pct: float
    active_lp_count: int
    deals: List[CoinvestDeal]
    lps: List[LPParticipation]
    sectors: List[SectorAllocation]
    realizations: List[HistoricalRealization]
    fees: List[FeeStructure]
    capacity: List[DealCapacity]
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


def _build_deals() -> List[CoinvestDeal]:
    return [
        CoinvestDeal("Project Azalea — GI Network SE", "Gastroenterology", "Welsh Carson", 580.0, 175.0, "in marketing",
                     0.50, 10.0, 8.0, "2026-06-30"),
        CoinvestDeal("Project Magnolia — MSK Platform", "MSK / Ortho", "KKR", 420.0, 120.0, "closed",
                     0.0, 10.0, 8.0, "2026-03-15"),
        CoinvestDeal("Project Willow — Fertility", "Fertility / IVF", "Apollo", 385.0, 110.0, "in marketing",
                     0.25, 10.0, 8.0, "2026-07-15"),
        CoinvestDeal("Project Cedar — Cardiology", "Cardiology", "Bain Capital", 445.0, 135.0, "closed",
                     0.0, 10.0, 8.0, "2026-02-28"),
        CoinvestDeal("Project Ash — Infusion", "Infusion", "TPG", 525.0, 155.0, "allocation",
                     0.50, 10.0, 8.0, "2026-05-15"),
        CoinvestDeal("Project Fir — Lab / Pathology", "Lab Services", "Carlyle", 475.0, 140.0, "closed",
                     0.0, 10.0, 8.0, "2026-03-10"),
        CoinvestDeal("Project Aspen — Eye Care", "Eye Care", "CVC Capital", 285.0, 85.0, "in marketing",
                     0.50, 10.0, 8.0, "2026-06-20"),
        CoinvestDeal("Project Maple — Urology", "Urology", "Summit Partners", 195.0, 60.0, "in marketing",
                     0.75, 10.0, 8.0, "2026-07-30"),
        CoinvestDeal("Project Sage — Home Health", "Home Health", "Advent International", 340.0, 95.0, "allocation",
                     0.25, 10.0, 8.0, "2026-05-30"),
        CoinvestDeal("Project Linden — Behavioral Health", "Behavioral Health", "Warburg Pincus", 265.0, 80.0, "in marketing",
                     0.50, 10.0, 8.0, "2026-08-15"),
        CoinvestDeal("Project Basil — Dental DSO", "Dental DSO", "L Catterton", 385.0, 115.0, "closed",
                     0.0, 10.0, 8.0, "2026-01-28"),
        CoinvestDeal("Project Thyme — Specialty Pharmacy", "Specialty Pharma", "Silver Lake", 450.0, 135.0, "allocation",
                     0.25, 10.0, 8.0, "2026-05-05"),
    ]


def _build_lps() -> List[LPParticipation]:
    return [
        LPParticipation("CalPERS", "Public Pension", 850.0, 8, 42, 68.5, 475.0, "very active"),
        LPParticipation("CalSTRS", "Public Pension", 620.0, 6, 38, 52.3, 310.0, "active"),
        LPParticipation("Texas Teachers", "Public Pension", 710.0, 7, 35, 62.8, 195.0, "active"),
        LPParticipation("NYC ERS", "Public Pension", 485.0, 5, 28, 55.2, 285.0, "active"),
        LPParticipation("HOOPP", "Canadian Pension", 420.0, 4, 22, 72.0, 125.0, "very active"),
        LPParticipation("CPPIB", "Canadian Pension", 925.0, 9, 48, 84.5, 680.0, "very active"),
        LPParticipation("Temasek Holdings", "Sovereign Wealth", 1150.0, 11, 52, 95.8, 385.0, "very active"),
        LPParticipation("GIC (Singapore)", "Sovereign Wealth", 985.0, 10, 46, 88.2, 790.0, "very active"),
        LPParticipation("ADIA (Abu Dhabi)", "Sovereign Wealth", 780.0, 8, 38, 72.5, 925.0, "active"),
        LPParticipation("NBIM (Norway)", "Sovereign Wealth", 685.0, 7, 32, 75.8, 1380.0, "active"),
        LPParticipation("Harvard Management", "Endowment", 285.0, 4, 22, 54.2, 50.0, "active"),
        LPParticipation("Yale Investments", "Endowment", 325.0, 5, 28, 58.0, 42.0, "active"),
        LPParticipation("MIT Investment Co.", "Endowment", 185.0, 3, 18, 48.8, 30.0, "selective"),
        LPParticipation("Stanford Management", "Endowment", 225.0, 4, 22, 50.5, 36.5, "active"),
        LPParticipation("Ford Foundation", "Foundation", 165.0, 3, 15, 45.0, 16.5, "selective"),
        LPParticipation("Gates Foundation Trust", "Foundation", 380.0, 5, 25, 62.5, 75.0, "active"),
        LPParticipation("Northwestern Mutual", "Insurance", 295.0, 4, 20, 52.5, 360.0, "active"),
        LPParticipation("MassMutual", "Insurance", 245.0, 3, 16, 50.0, 315.0, "selective"),
        LPParticipation("Adams Street Partners", "FoF / Secondaries", 465.0, 6, 32, 65.0, 55.0, "very active"),
        LPParticipation("HarbourVest Partners", "FoF / Secondaries", 585.0, 8, 42, 72.5, 125.0, "very active"),
        LPParticipation("Family Office — Pritzker", "Family Office", 125.0, 3, 15, 35.0, 45.0, "selective"),
        LPParticipation("Family Office — Bass", "Family Office", 95.0, 2, 12, 32.0, 15.0, "selective"),
    ]


def _build_sectors(deals: List[CoinvestDeal]) -> List[SectorAllocation]:
    buckets: dict = {}
    for d in deals:
        b = buckets.setdefault(d.sector, {"deals": 0, "equity": 0.0, "alloc": 0.0, "fee_sum": 0.0, "carry_sum": 0.0})
        b["deals"] += 1
        b["equity"] += d.equity_check_m
        b["alloc"] += d.coinvest_allocation_m
        b["fee_sum"] += d.management_fee_pct
        b["carry_sum"] += d.carry_pct
    rows = []
    for sector, d in buckets.items():
        unalloc = d["equity"] - d["alloc"]
        afee = d["fee_sum"] / d["deals"] if d["deals"] else 0
        acarry = d["carry_sum"] / d["deals"] if d["deals"] else 0
        rows.append(SectorAllocation(
            sector=sector, active_opportunities=d["deals"],
            total_equity_m=round(d["equity"], 1),
            allocated_m=round(d["alloc"], 1),
            unallocated_m=round(unalloc, 1),
            avg_fee_pct=round(afee, 2),
            avg_carry_pct=round(acarry, 2),
        ))
    return sorted(rows, key=lambda x: x.total_equity_m, reverse=True)


def _build_realizations() -> List[HistoricalRealization]:
    return [
        HistoricalRealization("Project Fern — Vision Care", "Eye Care", "KKR", 2019, 2024, 85.0, 238.0, 2.80, 2.72, 24.5, 2.72),
        HistoricalRealization("Project Pine — MSK", "MSK / Ortho", "Bain Capital", 2020, 2024, 105.0, 262.5, 2.50, 2.42, 22.8, 2.42),
        HistoricalRealization("Project Poplar — Dental DSO", "Dental DSO", "L Catterton", 2019, 2024, 95.0, 237.5, 2.50, 2.45, 20.5, 2.45),
        HistoricalRealization("Project Oak — GI Network", "Gastroenterology", "Welsh Carson", 2018, 2023, 125.0, 375.0, 3.00, 2.92, 26.5, 2.92),
        HistoricalRealization("Project Hemlock — Derma", "Dermatology", "Advent International", 2020, 2025, 75.0, 180.0, 2.40, 2.32, 21.2, 2.32),
        HistoricalRealization("Project Cedar1 — Fertility", "Fertility / IVF", "Apollo", 2021, 2025, 90.0, 225.0, 2.50, 2.40, 24.8, 2.40),
        HistoricalRealization("Project Birch — Behavioral Health", "Behavioral Health", "Summit Partners", 2020, 2024, 60.0, 126.0, 2.10, 2.02, 17.5, 2.02),
        HistoricalRealization("Project Elm — RCM SaaS", "RCM / HCIT", "Silver Lake", 2019, 2023, 70.0, 252.0, 3.60, 3.48, 32.5, 3.48),
        HistoricalRealization("Project Maple1 — Cardiology", "Cardiology", "TPG", 2020, 2024, 115.0, 276.0, 2.40, 2.32, 22.5, 2.32),
        HistoricalRealization("Project Sycamore — Urology", "Urology", "Thomas H. Lee", 2019, 2024, 65.0, 162.5, 2.50, 2.41, 20.8, 2.41),
    ]


def _build_fees() -> List[FeeStructure]:
    return [
        FeeStructure("Cornerstone / Anchor", "$100M+ commitment", 1.00, 0.20, 1.0, 125.0),
        FeeStructure("Core / Strategic", "$50-100M commitment", 0.75, 0.10, 0.5, 65.0),
        FeeStructure("Preferred / Repeat", "3+ prior deals", 0.50, 0.08, 0.0, 35.0),
        FeeStructure("Standard Co-Invest", "$10-50M commitment", 0.25, 0.0, 0.0, 10.0),
        FeeStructure("No Fee / No Carry", "Pari-passu w/ sponsor", 1.00, 1.00, 1.0, 22.5),
        FeeStructure("Deal-by-Deal (fees-only)", "Ad hoc", 0.0, 0.0, 0.0, 0.0),
    ]


def _build_capacity() -> List[DealCapacity]:
    return [
        DealCapacity("Project Azalea — GI Network SE", 580.0, 385.0, 35.0, 175.0, 420.0, 2.40, "pro-rata to cornerstones"),
        DealCapacity("Project Willow — Fertility", 385.0, 255.0, 25.0, 110.0, 225.0, 2.05, "pro-rata to cornerstones"),
        DealCapacity("Project Aspen — Eye Care", 285.0, 185.0, 20.0, 85.0, 185.0, 2.18, "tier-based allocation"),
        DealCapacity("Project Ash — Infusion", 525.0, 345.0, 40.0, 155.0, 285.0, 1.84, "pro-rata + cornerstones"),
        DealCapacity("Project Maple — Urology", 195.0, 125.0, 15.0, 60.0, 105.0, 1.75, "first-come-first-serve"),
        DealCapacity("Project Sage — Home Health", 340.0, 225.0, 25.0, 95.0, 145.0, 1.53, "tier-based allocation"),
        DealCapacity("Project Linden — Behavioral Health", 265.0, 175.0, 15.0, 80.0, 125.0, 1.56, "tier-based allocation"),
        DealCapacity("Project Thyme — Specialty Pharmacy", 450.0, 295.0, 30.0, 135.0, 235.0, 1.74, "pro-rata + cornerstones"),
    ]


def compute_coinvest_pipeline() -> CoinvestResult:
    corpus = _load_corpus()
    deals = _build_deals()
    lps = _build_lps()
    sectors = _build_sectors(deals)
    realizations = _build_realizations()
    fees = _build_fees()
    capacity = _build_capacity()

    total_equity = sum(d.equity_check_m for d in deals)
    total_allocated = sum(d.coinvest_allocation_m for d in deals if d.allocation_status in ("closed", "allocation"))
    total_available = sum(d.coinvest_allocation_m for d in deals)
    active_lps = sum(1 for lp in lps if lp.appetite in ("very active", "active"))
    avg_moic = sum(r.gross_moic for r in realizations) / len(realizations) if realizations else 0
    avg_irr = sum(r.gross_irr_pct for r in realizations) / len(realizations) if realizations else 0

    return CoinvestResult(
        active_opportunities=len(deals),
        total_equity_pipeline_m=round(total_equity, 1),
        total_coinvest_available_m=round(total_available, 1),
        total_coinvest_allocated_m=round(total_allocated, 1),
        historical_avg_moic=round(avg_moic, 2),
        historical_avg_irr_pct=round(avg_irr, 1),
        active_lp_count=active_lps,
        deals=deals,
        lps=lps,
        sectors=sectors,
        realizations=realizations,
        fees=fees,
        capacity=capacity,
        corpus_deal_count=len(corpus),
    )
