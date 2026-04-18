"""Secondaries / GP-Led Market Tracker.

Tracks GP-led secondary market activity: continuation vehicles (CVs),
strip sales, single-asset CVs, tender offers, and LP-led portfolio sales.
Secondaries have grown from ~$40B (2019) to ~$140B+ (2024) — essential
market for extended-hold exits and DPI acceleration.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class SecondariesTransaction:
    transaction: str
    structure: str
    gp_sponsor: str
    asset: str
    vintage: int
    close_year: int
    transaction_size_mm: float
    nav_premium_discount_pct: float


@dataclass
class BuyerLandscape:
    buyer: str
    buyer_type: str
    aum_b: float
    typical_check_mm: float
    focus: str
    recent_close: str


@dataclass
class CVEconomics:
    component: str
    mechanics: str
    typical_value: str
    key_consideration: str


@dataclass
class LPALPConflict:
    conflict_area: str
    description: str
    mitigation: str
    lpac_vote_needed: bool


@dataclass
class GPLedDeal:
    deal_name: str
    deal_type: str
    sector: str
    nav_mm: float
    holder_offered_options: str
    close_date: str
    lead_buyers: str


@dataclass
class MarketTrend:
    metric: str
    y2020: float
    y2022: float
    y2024: float
    trend: str


@dataclass
class SecondariesResult:
    total_gp_led_volume_2024_b: float
    single_asset_cv_share_pct: float
    typical_nav_premium_discount_pct: float
    transactions: List[SecondariesTransaction]
    buyers: List[BuyerLandscape]
    cv_economics: List[CVEconomics]
    conflicts: List[LPALPConflict]
    deals: List[GPLedDeal]
    trends: List[MarketTrend]
    corpus_deal_count: int


def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 115):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    return deals


def _build_transactions() -> List[SecondariesTransaction]:
    return [
        SecondariesTransaction("Project Atlas CV", "Single-Asset CV", "Welsh Carson (Fund XI)",
                               "U.S. Renal Care", 2013, 2024, 3250.0, -0.02),
        SecondariesTransaction("Project Beacon CV", "Multi-Asset CV", "KKR (Americas Fund X)",
                               "3-asset portfolio (healthcare + services)", 2013, 2024, 4850.0, -0.05),
        SecondariesTransaction("Project Cadence Strip", "Strip Sale", "TA Associates (Fund XIII)",
                               "Consolidated Pathology Consultants", 2014, 2024, 685.0, 0.02),
        SecondariesTransaction("Project Delta CV", "Single-Asset CV", "New Mountain (Fund V)",
                               "Benefytt Technologies", 2014, 2023, 1850.0, -0.08),
        SecondariesTransaction("Project Enterprise Tender", "LP Tender Offer", "Bain Capital (Fund XII)",
                               "Pro-rata strip (multiple healthcare assets)", 2015, 2024, 2850.0, -0.04),
        SecondariesTransaction("Project Fulcrum CV", "Single-Asset CV", "Frazier Healthcare (Fund VIII)",
                               "Millennium Specialty Pharmacy", 2015, 2024, 485.0, -0.06),
        SecondariesTransaction("Project Gemini CV", "Single-Asset CV", "Ampersand (Fund V)",
                               "PHC Group (life sciences)", 2016, 2024, 1225.0, 0.01),
        SecondariesTransaction("Project Horizon CV", "Multi-Asset CV", "Silver Lake (Healthcare Fund II)",
                               "3 HCIT assets", 2016, 2024, 3850.0, -0.03),
        SecondariesTransaction("Project Ibex CV", "Single-Asset CV", "Clayton Dubilier & Rice",
                               "Cynergy Healthcare", 2018, 2025, 1650.0, -0.07),
        SecondariesTransaction("Project Juniper LP Sale", "LP Portfolio Sale", "Multiple GP",
                               "15 healthcare fund interests", 2017, 2024, 925.0, -0.12),
    ]


def _build_buyers() -> List[BuyerLandscape]:
    return [
        BuyerLandscape("Ardian Secondaries", "Primary Secondary Investor", 138, 485.0, "GP-led, single-asset CV", "2024-Q4"),
        BuyerLandscape("Blackstone Strategic Partners", "Primary Secondary Investor", 78, 525.0, "multi-asset CV, large GP-led", "2025-Q1"),
        BuyerLandscape("Lexington Partners", "Primary Secondary Investor", 54, 385.0, "GP-led and LP-led tenders", "2025-Q1"),
        BuyerLandscape("Goldman Sachs AIMS", "Primary Secondary Investor", 35, 285.0, "healthcare focus", "2024-Q4"),
        BuyerLandscape("HarbourVest Partners", "Primary Secondary Investor", 49, 325.0, "diversified mandate", "2025-Q1"),
        BuyerLandscape("Coller Capital", "Primary Secondary Investor", 25, 215.0, "large tender offers", "2024-Q4"),
        BuyerLandscape("Pantheon", "Primary Secondary Investor", 22, 185.0, "LP-led fund commitments", "2025-Q1"),
        BuyerLandscape("Committed Advisors", "Primary Secondary Investor", 8, 95.0, "niche / specialist", "2024-Q4"),
        BuyerLandscape("Hollyport Capital", "Primary Secondary Investor", 6, 85.0, "boutique", "2024-Q4"),
        BuyerLandscape("Yale / Columbia Endowment", "Secondary LP Buyer", 45, 125.0, "high-quality GP only", "2024-Q3"),
        BuyerLandscape("CalPERS Direct Secondary", "Public Pension", 485, 185.0, "large CVs", "2024-Q2"),
        BuyerLandscape("Manulife Investment Mgmt", "Insurance LP / Secondary", 85, 145.0, "insurance-led CV", "2024-Q4"),
    ]


def _build_cv_economics() -> List[CVEconomics]:
    return [
        CVEconomics("NAV Pricing", "Independent 3rd-party fairness opinion; reference price vs agreed deal price",
                    "0-5% discount to NAV typical", "Fairness opinion from JP Morgan or Lazard standard"),
        CVEconomics("LP Options", "Roll / Sell / Receive Cash choice presented to existing fund LPs",
                    "35-55% of LPs typically roll", "60+ day election period; unanimous consent not required"),
        CVEconomics("GP Rollover", "Proportional GP interest rolls into CV alongside LPs who choose roll",
                    "Typically 100% of GP interest rolls", "Signals alignment"),
        CVEconomics("Fund Fees (Reset)", "New carry clock, typically 20% over 8% preferred return",
                    "Management fee 1.5-2.0% of NAV", "Lower fee structure than primary funds"),
        CVEconomics("Carry Waterfall", "Standard American waterfall with new 8% preferred return",
                    "Catch-up typically 50% or 100% of distributions after preferred return",
                    "Crystallize old GP carry at CV close; start new clock"),
        CVEconomics("Adviser Waiver / Carry Waiver", "GP may waive management fee on rollover portion",
                    "0-100% waiver typical; full waiver for key assets",
                    "LPA amendment may be required"),
        CVEconomics("New Equity Commitment", "GP commits 1-3% of new CV as new equity (fresh commitment)",
                    "$15-50M GP commitment typical", "Additional alignment signal"),
        CVEconomics("LPAC Consent", "Limited Partner Advisory Committee must approve structural terms",
                    "Unanimous or majority vote typical", "90-120 day diligence typical"),
    ]


def _build_conflicts() -> List[LPALPConflict]:
    return [
        LPALPConflict("Pricing Fairness", "Risk that NAV pricing favors GP or rolling LPs",
                      "Independent 3rd-party fairness opinion required", True),
        LPALPConflict("LP Liquidity Options", "Some LPs may not fully understand roll/sell tradeoff",
                      "Multiple 60-day election windows; LP advisor support", False),
        LPALPConflict("Future Carry", "New CV crystallizes old carry; reset clock benefits GP",
                      "Transparent LPA amendment; LPAC review", True),
        LPALPConflict("Asset Concentration", "Single-asset CV concentrates risk for buyers",
                      "Standard in single-asset CV structure; disclosed", False),
        LPALPConflict("GP Conflict (Auctioned Sale Alternative)", "GP chose CV over auction",
                      "GP must justify CV > auction price decision; LPAC review", True),
        LPALPConflict("Fee Stripping", "Management fee on rolled assets continues",
                      "Fee waiver on rolled portion common remedy", True),
    ]


def _build_deals() -> List[GPLedDeal]:
    return [
        GPLedDeal("Welsh Carson / U.S. Renal Care", "Single-Asset CV", "Dialysis", 3850.0,
                  "Roll / Sell / Strip to New Vehicle", "2024-11-15", "Ardian, Lexington"),
        GPLedDeal("KKR / Healthcare Services Portfolio", "Multi-Asset CV", "Mixed Healthcare", 4850.0,
                  "Pro-rata Roll / Sell / Mixed", "2024-09-30", "Blackstone Strategic, HarbourVest"),
        GPLedDeal("TA Associates / Pathology Assets", "Strip Sale", "Diagnostics", 685.0,
                  "Sell Strip to New Fund", "2024-08-22", "Goldman AIMS, Pantheon"),
        GPLedDeal("New Mountain / Benefytt Technologies", "Single-Asset CV", "Health Benefits", 1850.0,
                  "Roll / Sell", "2023-12-15", "Ardian, Coller"),
        GPLedDeal("Bain Capital / Healthcare Tender", "LP Tender Offer", "Cross-sector", 2850.0,
                  "Tender Pro-rata", "2024-06-30", "Lexington, Blackstone"),
        GPLedDeal("Frazier Healthcare / Millennium Specialty Pharmacy", "Single-Asset CV", "Specialty Pharmacy", 485.0,
                  "Roll / Sell", "2024-10-08", "Committed Advisors, Hollyport"),
        GPLedDeal("Clayton Dubilier & Rice / Cynergy Healthcare", "Single-Asset CV", "Healthcare Services", 1650.0,
                  "Roll / Sell", "2025-02-22", "Ardian, Goldman AIMS"),
        GPLedDeal("Silver Lake / HCIT Portfolio", "Multi-Asset CV", "HCIT / SaaS", 3850.0,
                  "Pro-rata Roll / Sell", "2024-04-18", "Blackstone, Lexington"),
        GPLedDeal("Vista Equity / Healthcare Software", "Single-Asset CV", "HCIT / EHR", 2250.0,
                  "Roll / Sell", "2024-07-15", "HarbourVest, Ardian"),
        GPLedDeal("Ampersand / PHC Group (Life Sciences)", "Single-Asset CV", "Life Sciences", 1225.0,
                  "Roll / Sell", "2024-03-22", "Coller, Hollyport"),
    ]


def _build_trends() -> List[MarketTrend]:
    return [
        MarketTrend("Total GP-Led Volume ($B)", 48.0, 68.0, 98.0, "expanding"),
        MarketTrend("Total Secondaries Volume ($B)", 95.0, 110.0, 140.0, "expanding"),
        MarketTrend("Single-Asset CVs (% of GP-Led)", 0.22, 0.38, 0.52, "dominant"),
        MarketTrend("Average NAV Discount (GP-Led)", -0.02, -0.08, -0.04, "improved"),
        MarketTrend("Average LP Roll Rate", 0.28, 0.35, 0.42, "rising"),
        MarketTrend("Active Buyers Count", 22, 35, 48, "expanding"),
        MarketTrend("Healthcare GP-Led Share (%)", 0.22, 0.25, 0.28, "rising"),
        MarketTrend("Fairness Opinion Frequency (%)", 0.78, 0.92, 0.98, "now standard"),
    ]


def compute_secondaries_tracker() -> SecondariesResult:
    corpus = _load_corpus()

    transactions = _build_transactions()
    buyers = _build_buyers()
    cv_econ = _build_cv_economics()
    conflicts = _build_conflicts()
    deals = _build_deals()
    trends = _build_trends()

    total_vol_2024 = 98.0  # billion
    single_asset_share = 0.52
    typical_premium = sum(t.nav_premium_discount_pct for t in transactions) / len(transactions) if transactions else 0

    return SecondariesResult(
        total_gp_led_volume_2024_b=total_vol_2024,
        single_asset_cv_share_pct=single_asset_share,
        typical_nav_premium_discount_pct=round(typical_premium, 4),
        transactions=transactions,
        buyers=buyers,
        cv_economics=cv_econ,
        conflicts=conflicts,
        deals=deals,
        trends=trends,
        corpus_deal_count=len(corpus),
    )
