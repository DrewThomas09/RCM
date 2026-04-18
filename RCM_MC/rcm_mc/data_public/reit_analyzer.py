"""Healthcare REIT / Sale-Leaseback Analyzer.

Models real-estate monetization for PE healthcare platforms — a critical
value-creation lever for hospital, ASC, SNF, and MOB assets. Sale-leaseback
frees capital for bolt-ons or dividend recaps but creates long-term rent
obligation that affects covenant math and EBITDAR capacity.

Outputs:
- Real-estate portfolio roster
- Cap rate vs comparables
- Sale-leaseback transaction model
- Rent coverage (EBITDAR / rent)
- Ground-lease optionality
- Lease vs own NPV waterfall
- REIT buyer landscape
- Debt pre-payment mechanics
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


_ASSET_CAP_RATES = {
    "Acute Care Hospital":  {"cap_low": 0.062, "cap_mid": 0.068, "cap_high": 0.078},
    "ASC Facility":         {"cap_low": 0.065, "cap_mid": 0.072, "cap_high": 0.082},
    "Medical Office Building (MOB)": {"cap_low": 0.058, "cap_mid": 0.065, "cap_high": 0.072},
    "Skilled Nursing Facility":      {"cap_low": 0.085, "cap_mid": 0.095, "cap_high": 0.115},
    "Senior Living / Independent":   {"cap_low": 0.062, "cap_mid": 0.072, "cap_high": 0.085},
    "Behavioral Health Inpatient":   {"cap_low": 0.078, "cap_mid": 0.088, "cap_high": 0.098},
    "Specialty Hospital":            {"cap_low": 0.072, "cap_mid": 0.082, "cap_high": 0.095},
    "Rehab / LTACH":                 {"cap_low": 0.085, "cap_mid": 0.095, "cap_high": 0.110},
}


@dataclass
class RealEstateAsset:
    asset_id: str
    asset_type: str
    location: str
    building_sqft: int
    annual_noi_mm: float
    cap_rate_implied: float
    market_value_mm: float
    book_value_mm: float
    unrealized_gain_mm: float
    occupancy_pct: float
    lease_status: str


@dataclass
class SaleLeasebackScenario:
    scenario: str
    asset_type: str
    sale_proceeds_mm: float
    initial_rent_mm: float
    rent_escalation_pct: float
    term_years: int
    coverage_ratio: float
    npv_benefit_mm: float
    tax_gain_mm: float


@dataclass
class REITBuyer:
    buyer_name: str
    buyer_type: str
    focus_asset_type: str
    typical_cap_rate: float
    avg_deal_size_mm: float
    pipeline_capacity_mm: float
    credit_rating: str


@dataclass
class RentCoverage:
    metric: str
    pre_slb_value: float
    post_slb_value: float
    delta_pct: float
    covenant_threshold: float
    headroom_pct: float


@dataclass
class DebtUse:
    use_category: str
    allocation_pct: float
    allocation_mm: float
    rationale: str
    moic_uplift: float


@dataclass
class REITResult:
    total_assets: int
    total_book_value_mm: float
    total_market_value_mm: float
    total_unrealized_gain_mm: float
    weighted_cap_rate: float
    recommended_scenario: str
    max_proceeds_mm: float
    assets: List[RealEstateAsset]
    scenarios: List[SaleLeasebackScenario]
    reit_buyers: List[REITBuyer]
    rent_coverage: List[RentCoverage]
    proceeds_uses: List[DebtUse]
    corpus_deal_count: int


def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 90):
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


def _build_assets(platform_ebitdar_mm: float, platform_type: str) -> List[RealEstateAsset]:
    import hashlib
    if platform_type == "Hospital System":
        mix = [
            ("Acute Care Hospital", 0.45, 285_000, 0.92),
            ("Medical Office Building (MOB)", 0.20, 68_000, 0.88),
            ("ASC Facility", 0.12, 42_000, 0.85),
            ("Specialty Hospital", 0.10, 95_000, 0.82),
            ("Rehab / LTACH", 0.08, 62_000, 0.78),
            ("Medical Office Building (MOB)", 0.05, 38_000, 0.91),
        ]
    elif platform_type == "Senior Living Portfolio":
        mix = [
            ("Senior Living / Independent", 0.32, 95_000, 0.88),
            ("Skilled Nursing Facility", 0.38, 68_000, 0.80),
            ("Skilled Nursing Facility", 0.20, 62_000, 0.78),
            ("Senior Living / Independent", 0.10, 78_000, 0.85),
        ]
    elif platform_type == "Behavioral Health Platform":
        mix = [
            ("Behavioral Health Inpatient", 0.55, 52_000, 0.86),
            ("Behavioral Health Inpatient", 0.25, 45_000, 0.82),
            ("Medical Office Building (MOB)", 0.20, 28_000, 0.90),
        ]
    else:   # ASC Platform
        mix = [
            ("ASC Facility", 0.40, 35_000, 0.88),
            ("ASC Facility", 0.30, 38_000, 0.82),
            ("Medical Office Building (MOB)", 0.20, 32_000, 0.90),
            ("ASC Facility", 0.10, 42_000, 0.92),
        ]

    rows = []
    for i, (asset_type, share, base_sqft, occ) in enumerate(mix):
        h = int(hashlib.md5(f"{asset_type}{i}".encode()).hexdigest()[:6], 16)
        noi = platform_ebitdar_mm * share * (0.35 + (h % 20) / 100)  # rent portion of ebitdar
        bench = _ASSET_CAP_RATES[asset_type]
        cap = bench["cap_mid"] * (0.94 + (h % 12) / 100)
        market_val = noi / cap
        book = market_val * (0.55 + (h % 30) / 100)
        sqft = int(base_sqft * (0.85 + (h % 25) / 100))
        locations = ["Phoenix, AZ", "Dallas, TX", "Tampa, FL", "Atlanta, GA", "Chicago, IL", "Denver, CO", "Seattle, WA"]
        lease_statuses = ["owned", "owned", "ground lease", "owned", "owned"]
        rows.append(RealEstateAsset(
            asset_id=f"RE-{i + 1:03d}",
            asset_type=asset_type,
            location=locations[h % len(locations)],
            building_sqft=sqft,
            annual_noi_mm=round(noi, 2),
            cap_rate_implied=round(cap, 4),
            market_value_mm=round(market_val, 2),
            book_value_mm=round(book, 2),
            unrealized_gain_mm=round(market_val - book, 2),
            occupancy_pct=round(occ * (0.97 + (h % 6) / 100), 3),
            lease_status=lease_statuses[h % len(lease_statuses)],
        ))
    return rows


def _build_scenarios(assets: List[RealEstateAsset], platform_ebitdar: float) -> List[SaleLeasebackScenario]:
    if not assets:
        return []
    rows = []
    total_market = sum(a.market_value_mm for a in assets if a.lease_status == "owned")
    total_noi = sum(a.annual_noi_mm for a in assets if a.lease_status == "owned")

    # Scenario 1: Partial (hospital-only)
    hospitals = [a for a in assets if "Hospital" in a.asset_type and a.lease_status == "owned"]
    if hospitals:
        h_mv = sum(a.market_value_mm for a in hospitals)
        h_noi = sum(a.annual_noi_mm for a in hospitals)
        rent = h_noi * 1.10  # rent usually 8-12% higher than current NOI for sub-market comp
        coverage = platform_ebitdar / rent if rent else 0
        rows.append(SaleLeasebackScenario(
            scenario="Hospital Only Partial",
            asset_type="Hospital",
            sale_proceeds_mm=round(h_mv, 2),
            initial_rent_mm=round(rent, 2),
            rent_escalation_pct=0.0225,
            term_years=20,
            coverage_ratio=round(coverage, 2),
            npv_benefit_mm=round(h_mv - (rent * 12) * 0.68, 2),
            tax_gain_mm=round((h_mv - h_mv * 0.6) * 0.24, 2),
        ))

    # Scenario 2: MOB portfolio
    mobs = [a for a in assets if "MOB" in a.asset_type and a.lease_status == "owned"]
    if mobs:
        m_mv = sum(a.market_value_mm for a in mobs)
        m_noi = sum(a.annual_noi_mm for a in mobs)
        rent = m_noi * 1.05
        coverage = platform_ebitdar / rent if rent else 0
        rows.append(SaleLeasebackScenario(
            scenario="MOB Portfolio",
            asset_type="Medical Office Building (MOB)",
            sale_proceeds_mm=round(m_mv, 2),
            initial_rent_mm=round(rent, 2),
            rent_escalation_pct=0.025,
            term_years=15,
            coverage_ratio=round(coverage, 2),
            npv_benefit_mm=round(m_mv - (rent * 10) * 0.72, 2),
            tax_gain_mm=round((m_mv - m_mv * 0.55) * 0.24, 2),
        ))

    # Scenario 3: Full portfolio
    rent_full = total_noi * 1.08
    coverage_full = platform_ebitdar / rent_full if rent_full else 0
    rows.append(SaleLeasebackScenario(
        scenario="Full Portfolio SLB",
        asset_type="All Owned RE",
        sale_proceeds_mm=round(total_market, 2),
        initial_rent_mm=round(rent_full, 2),
        rent_escalation_pct=0.025,
        term_years=20,
        coverage_ratio=round(coverage_full, 2),
        npv_benefit_mm=round(total_market - (rent_full * 14) * 0.65, 2),
        tax_gain_mm=round((total_market - total_market * 0.58) * 0.24, 2),
    ))

    # Scenario 4: ground-lease / hybrid
    rows.append(SaleLeasebackScenario(
        scenario="Ground-Lease Only (Hybrid)",
        asset_type="Land Only",
        sale_proceeds_mm=round(total_market * 0.28, 2),
        initial_rent_mm=round(rent_full * 0.32, 2),
        rent_escalation_pct=0.02,
        term_years=99,
        coverage_ratio=round(platform_ebitdar / (rent_full * 0.32) if rent_full else 0, 2),
        npv_benefit_mm=round(total_market * 0.28 - (rent_full * 0.32 * 35) * 0.55, 2),
        tax_gain_mm=round(total_market * 0.28 * 0.15, 2),
    ))

    return rows


def _build_buyers() -> List[REITBuyer]:
    return [
        REITBuyer("Medical Properties Trust", "Public REIT", "Acute Care Hospital", 0.075, 125.0, 850.0, "BB+"),
        REITBuyer("Healthcare Trust of America / Healthpeak", "Public REIT", "MOB / Life Sciences", 0.062, 85.0, 1250.0, "BBB+"),
        REITBuyer("Welltower", "Public REIT", "Senior Living / SNF", 0.068, 95.0, 2400.0, "BBB+"),
        REITBuyer("Ventas", "Public REIT", "Senior Living / MOB", 0.065, 92.0, 1850.0, "BBB+"),
        REITBuyer("Omega Healthcare", "Public REIT", "Skilled Nursing", 0.095, 68.0, 825.0, "BBB-"),
        REITBuyer("Sabra Health Care", "Public REIT", "SNF / Behavioral", 0.092, 45.0, 485.0, "BBB-"),
        REITBuyer("CareTrust REIT", "Public REIT", "Skilled Nursing", 0.088, 35.0, 320.0, "BBB-"),
        REITBuyer("Physicians Realty Trust", "Public REIT", "MOB", 0.063, 48.0, 520.0, "BBB"),
        REITBuyer("Global Medical REIT", "Public REIT", "MOB / Specialty Med", 0.078, 25.0, 195.0, "BB+"),
        REITBuyer("Blackstone Real Estate Debt Strategies", "Private Capital", "All Healthcare RE", 0.072, 150.0, 3500.0, "N/A"),
        REITBuyer("KKR Real Estate Credit", "Private Capital", "MOB / Hospital", 0.068, 95.0, 1850.0, "N/A"),
        REITBuyer("Carlyle Real Estate", "Private Capital", "MOB / ASC", 0.070, 75.0, 1250.0, "N/A"),
    ]


def _build_rent_coverage(ebitdar: float, rent: float, pre_slb_ebitdar: float) -> List[RentCoverage]:
    cov_pre = pre_slb_ebitdar / 0.01 if ebitdar else 0
    cov_post = ebitdar / rent if rent else 0
    return [
        RentCoverage("EBITDAR / Rent Coverage", round(cov_pre, 2), round(cov_post, 2),
                     round((cov_post / cov_pre - 1) if cov_pre else 0, 4), 1.75, round((cov_post / 1.75 - 1) if cov_post else 0, 4)),
        RentCoverage("Fixed Charge Coverage", round(cov_pre * 0.85, 2), round(cov_post * 0.82, 2),
                     round(((cov_post * 0.82) / (cov_pre * 0.85) - 1) if cov_pre else 0, 4),
                     1.50, round(((cov_post * 0.82) / 1.50 - 1) if cov_post else 0, 4)),
        RentCoverage("Debt / EBITDAR", 4.5, 3.2, -0.289, 5.5, 0.719),
        RentCoverage("Interest Coverage", 5.8, 5.6, -0.034, 3.0, 0.867),
    ]


def _build_proceeds_uses(total_proceeds: float) -> List[DebtUse]:
    return [
        DebtUse("Debt Paydown (reduce leverage)", 0.42, round(total_proceeds * 0.42, 2),
                "Primary covenant protection", 0.12),
        DebtUse("M&A / Bolt-On Acquisitions", 0.28, round(total_proceeds * 0.28, 2),
                "Redeploy into platform expansion", 0.38),
        DebtUse("Dividend Recap to LPs", 0.15, round(total_proceeds * 0.15, 2),
                "Accelerated DPI", 0.22),
        DebtUse("Growth Capex (facility expansion)", 0.08, round(total_proceeds * 0.08, 2),
                "Capacity additions", 0.18),
        DebtUse("Technology / EHR Investment", 0.04, round(total_proceeds * 0.04, 2),
                "Platform integration", 0.08),
        DebtUse("Working Capital Reserve", 0.03, round(total_proceeds * 0.03, 2),
                "Operational flexibility", 0.02),
    ]


def compute_reit_analyzer(
    platform_type: str = "Hospital System",
    platform_ebitdar_mm: float = 85.0,
) -> REITResult:
    corpus = _load_corpus()

    assets = _build_assets(platform_ebitdar_mm, platform_type)
    scenarios = _build_scenarios(assets, platform_ebitdar_mm)
    buyers = _build_buyers()

    total_book = sum(a.book_value_mm for a in assets)
    total_market = sum(a.market_value_mm for a in assets)
    total_unr = sum(a.unrealized_gain_mm for a in assets)
    total_noi = sum(a.annual_noi_mm for a in assets)
    wcap = total_noi / total_market if total_market else 0

    recommended = max(scenarios, key=lambda s: s.npv_benefit_mm).scenario if scenarios else "N/A"
    max_proceeds = max(scenarios, key=lambda s: s.sale_proceeds_mm).sale_proceeds_mm if scenarios else 0

    # Rent coverage uses full portfolio scenario rent
    full_rent = next((s.initial_rent_mm for s in scenarios if s.scenario == "Full Portfolio SLB"), 0)
    rent_cov = _build_rent_coverage(platform_ebitdar_mm, full_rent, platform_ebitdar_mm)
    proceeds_uses = _build_proceeds_uses(total_market * 0.75)  # Assume 75% of portfolio monetized

    return REITResult(
        total_assets=len(assets),
        total_book_value_mm=round(total_book, 2),
        total_market_value_mm=round(total_market, 2),
        total_unrealized_gain_mm=round(total_unr, 2),
        weighted_cap_rate=round(wcap, 4),
        recommended_scenario=recommended,
        max_proceeds_mm=round(max_proceeds, 2),
        assets=assets,
        scenarios=scenarios,
        reit_buyers=buyers,
        rent_coverage=rent_cov,
        proceeds_uses=proceeds_uses,
        corpus_deal_count=len(corpus),
    )
