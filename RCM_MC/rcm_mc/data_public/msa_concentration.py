"""ILLUSTRATIVE — MSA-level concentration analyzer over a curated synthetic panel.

Do not quote these outputs in IC documents: the MSA rows, operator
profiles, FTC-action likelihoods, and value-at-risk figures below carry
real operator names with CURATED numbers — they illustrate the regime-
classification methodology (fragmented vs concentrated via HHI/CR3/CR5)
and are not filed or computed market data. For concentration computed
from an actual CMS pull use
:mod:`rcm_mc.data_public.market_concentration` (note that module's HHI
is on the 0-1 fractional scale, while this panel uses the 0-10,000
merger-guideline convention).
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import List


@dataclass
class MSAConcentration:
    msa: str
    specialty: str
    providers: int
    hhi: int
    cr3_pct: float
    cr5_pct: float
    market_structure: str
    rollup_opportunity: str
    top_operator: str


@dataclass
class RegimeClassification:
    regime: str
    description: str
    hhi_range: str
    cr3_range: str
    typical_moic: float
    typical_hold_years: float
    msa_count_in_sample: int


@dataclass
class WhitespaceScore:
    msa: str
    state: str
    population_000: int
    total_providers: int
    top_operator_share_pct: float
    top3_combined_pct: float
    whitespace_score: int
    rollup_priority: str


@dataclass
class StressScenario:
    scenario: str
    hhi_delta: int
    cr3_delta_pp: float
    likely_ftc_action: str
    estimated_value_at_risk_mm: float


@dataclass
class OperatorProfile:
    operator: str
    markets_active: int
    total_practices: int
    total_providers: int
    median_hhi_contribution: int
    growth_strategy: str


@dataclass
class MSAResult:
    total_msas_analyzed: int
    fragmented_count: int
    moderately_concentrated_count: int
    highly_concentrated_count: int
    avg_hhi: int
    avg_cr3_pct: float
    msa_details: List[MSAConcentration]
    regimes: List[RegimeClassification]
    whitespace: List[WhitespaceScore]
    stress_scenarios: List[StressScenario]
    top_operators: List[OperatorProfile]
    corpus_deal_count: int
    # Machine-readable honesty flag: the MSA panel pairs real operator
    # names with curated numbers, so any consumer beyond the labelled
    # UI page (exports, assistant context, future APIs) inherits the
    # caveat instead of unlabelled numbers.
    is_illustrative: bool = True
    # Median HHI beside the mean: the panel's HHI distribution is
    # right-skewed (a 4,250 fertility market against a 380 home-health
    # market), so the mean overstates the typical market's
    # concentration — median is the robust central read. Additive
    # field; ``avg_hhi`` stays for back-compat.
    median_hhi: int = 0


def _load_corpus() -> List[dict]:
    """Delegate to the canonical registry-driven loader.

    Five sibling market models each hand-rolled an ``importlib`` loop
    over divergent ``range()``s, so the same corpus read as five
    different "Corpus Deals" counts depending on the page and silently
    drifted stale as seed files were added. The registry enumerates
    every seed group, so all five now agree and track new seeds.
    """
    from rcm_mc.data_public.corpus_loader import load_corpus_deals
    return load_corpus_deals("all")


def _build_msas() -> List[MSAConcentration]:
    items = [
        ("Houston-The Woodlands-Sugar Land, TX", "Gastroenterology", 428, 1850, 0.42, 0.58, "moderately concentrated", "consolidation underway", "GI Alliance (PE)"),
        ("Dallas-Fort Worth-Arlington, TX", "Gastroenterology", 385, 1520, 0.38, 0.52, "moderately concentrated", "opportunistic", "US Digestive Partners"),
        ("New York-Newark-Jersey City, NY", "Dermatology", 1250, 420, 0.12, 0.18, "fragmented", "platform opportunity", "Schweiger Dermatology"),
        ("Los Angeles-Long Beach-Anaheim, CA", "Dermatology", 985, 485, 0.14, 0.22, "fragmented", "platform opportunity", "ADCS / SkinWorks"),
        ("Phoenix-Mesa-Chandler, AZ", "Cardiology", 325, 2450, 0.48, 0.62, "moderately concentrated", "limited", "Banner / HonorHealth"),
        ("Miami-Fort Lauderdale-Pompano Beach, FL", "Home Health", 2850, 380, 0.15, 0.22, "fragmented", "fraud-adjacent; proceed caution", "BrightStar / multiple"),
        ("Atlanta-Sandy Springs-Alpharetta, GA", "Urgent Care", 385, 1850, 0.28, 0.42, "moderately concentrated", "strategic M&A", "Piedmont / WellStar"),
        ("Chicago-Naperville-Elgin, IL", "Orthopedics", 285, 1650, 0.32, 0.48, "moderately concentrated", "consolidation underway", "Illinois Bone & Joint (PE)"),
        ("Philadelphia-Camden-Wilmington, PA", "Anesthesiology", 228, 2850, 0.52, 0.68, "highly concentrated", "regulatory attention", "USAP / NAPA"),
        ("Boston-Cambridge-Newton, MA", "Ophthalmology", 185, 1420, 0.35, 0.48, "moderately concentrated", "limited", "Eye Health Network (PE)"),
        ("San Francisco-Oakland-Berkeley, CA", "Fertility / IVF", 42, 4250, 0.72, 0.88, "highly concentrated", "regulatory attention", "Kindbody / RMA"),
        ("Seattle-Tacoma-Bellevue, WA", "Urgent Care", 165, 1250, 0.28, 0.42, "moderately concentrated", "strategic", "Swedish / Providence"),
        ("Denver-Aurora-Lakewood, CO", "ASC / Orthopedics", 128, 1850, 0.38, 0.52, "moderately concentrated", "active roll-up", "Panorama Ortho (KKR)"),
        ("Nashville-Davidson, TN", "Behavioral Health", 165, 1420, 0.32, 0.48, "moderately concentrated", "strategic", "Acadia Healthcare"),
        ("Austin-Round Rock-Georgetown, TX", "Anesthesiology", 85, 3250, 0.58, 0.72, "highly concentrated", "FTC Second Request risk", "USAP"),
        ("Tampa-St. Petersburg-Clearwater, FL", "Home Health", 1850, 480, 0.18, 0.28, "fragmented", "active consolidation", "LHC Group / Amedisys"),
        ("Orlando-Kissimmee-Sanford, FL", "Urgent Care", 285, 1620, 0.32, 0.48, "moderately concentrated", "strategic", "AdventHealth / Orlando Health"),
        ("Minneapolis-St. Paul-Bloomington, MN", "Primary Care", 485, 1250, 0.28, 0.42, "moderately concentrated", "limited", "Optum / HealthPartners"),
        ("Detroit-Warren-Dearborn, MI", "Cardiology", 225, 2250, 0.48, 0.62, "moderately concentrated", "limited", "Henry Ford / Beaumont"),
        ("San Diego-Chula Vista-Carlsbad, CA", "Behavioral Health", 225, 1120, 0.24, 0.38, "moderately concentrated", "active", "Scripps / Sharp"),
    ]
    rows = []
    for msa, spec, prov, hhi, cr3, cr5, struct, opp, op in items:
        rows.append(MSAConcentration(
            msa=msa, specialty=spec, providers=prov,
            hhi=hhi, cr3_pct=cr3, cr5_pct=cr5,
            market_structure=struct, rollup_opportunity=opp,
            top_operator=op,
        ))
    return rows


def _build_regimes() -> List[RegimeClassification]:
    return [
        RegimeClassification("Fragmented", "Many small practices; no dominant operator",
                             "<1500 HHI", "<25% CR3", 2.85, 4.8, 8),
        RegimeClassification("Moderately Concentrated", "3-5 leading operators; active roll-up",
                             "1500-2500 HHI", "25-50% CR3", 2.62, 4.5, 18),
        RegimeClassification("Highly Concentrated", "Dominant operator; antitrust scrutiny",
                             ">2500 HHI", ">50% CR3", 2.25, 5.2, 6),
        RegimeClassification("Near-Monopoly", "Single dominant; regulatory intervention likely",
                             ">5000 HHI", ">75% CR1", 1.85, 6.8, 2),
    ]


def _build_whitespace() -> List[WhitespaceScore]:
    return [
        WhitespaceScore("Raleigh-Cary, NC", "NC", 1585, 385, 0.12, 0.22, 92, "priority expansion"),
        WhitespaceScore("Charlotte-Concord-Gastonia, NC", "NC", 2770, 685, 0.15, 0.25, 88, "priority expansion"),
        WhitespaceScore("Jacksonville, FL", "FL", 1650, 285, 0.18, 0.30, 85, "priority expansion"),
        WhitespaceScore("Columbus, OH", "OH", 2150, 485, 0.20, 0.32, 82, "active target"),
        WhitespaceScore("Indianapolis-Carmel-Anderson, IN", "IN", 2100, 325, 0.22, 0.35, 78, "active target"),
        WhitespaceScore("Richmond, VA", "VA", 1320, 185, 0.25, 0.38, 75, "active target"),
        WhitespaceScore("Albuquerque, NM", "NM", 925, 125, 0.28, 0.42, 72, "fill-in"),
        WhitespaceScore("Boise City, ID", "ID", 825, 95, 0.32, 0.48, 68, "fill-in"),
        WhitespaceScore("Omaha-Council Bluffs, NE-IA", "NE-IA", 985, 165, 0.28, 0.42, 72, "fill-in"),
        WhitespaceScore("Tucson, AZ", "AZ", 1050, 148, 0.32, 0.48, 68, "fill-in"),
        WhitespaceScore("Des Moines-West Des Moines, IA", "IA", 710, 85, 0.35, 0.52, 62, "selective"),
        WhitespaceScore("Knoxville, TN", "TN", 925, 125, 0.32, 0.45, 68, "fill-in"),
    ]


def _build_stress() -> List[StressScenario]:
    return [
        StressScenario("Base case (consolidate 1 top-5 operator)", 250, 0.08, "unlikely challenge", 0.0),
        StressScenario("Consolidate top 2 operators", 680, 0.18, "possible 2R", 125.0),
        StressScenario("Platform + 3 practices same MSA", 420, 0.12, "likely review", 45.0),
        StressScenario("Cross-MSA consolidation (geographic diversification)", 120, 0.04, "clears", 0.0),
        StressScenario("Acquire market leader (all 5 markets)", 1250, 0.28, "likely challenge", 285.0),
        StressScenario("Vertical integration (payer acquisition)", 350, 0.10, "FTC vertical scrutiny", 85.0),
    ]


def _build_operators() -> List[OperatorProfile]:
    return [
        OperatorProfile("USAP (US Anesthesia Partners)", 28, 385, 4250, 2850, "concentrated; FTC scrutiny"),
        OperatorProfile("GI Alliance", 22, 125, 685, 1850, "active roll-up (PE)"),
        OperatorProfile("ADCS / Schweiger / Forefront Derm", 42, 425, 1850, 625, "active roll-up (multi-PE)"),
        OperatorProfile("DaVita Kidney Care", 48, 2850, 8500, 2250, "consolidated; mature"),
        OperatorProfile("Fresenius Medical Care", 38, 2650, 7850, 1950, "consolidated; mature"),
        OperatorProfile("Optum Health Services", 45, 1850, 52000, 1450, "vertical payer"),
        OperatorProfile("Acadia Healthcare", 32, 250, 4850, 1250, "behavioral health leader"),
        OperatorProfile("LHC Group (UnitedHealth)", 42, 1250, 14500, 485, "home health leader"),
        OperatorProfile("Panorama Orthopedics (KKR)", 6, 58, 485, 2850, "regional ortho roll-up"),
        OperatorProfile("US Digestive Partners", 15, 85, 425, 1620, "GI roll-up (PE)"),
        OperatorProfile("Kindbody / RMA", 12, 42, 185, 3850, "fertility consolidator"),
        OperatorProfile("Illinois Bone & Joint Institute", 3, 28, 175, 1650, "regional ortho"),
    ]


def compute_msa_concentration() -> MSAResult:
    corpus = _load_corpus()

    msas = _build_msas()
    regimes = _build_regimes()
    whitespace = _build_whitespace()
    stress = _build_stress()
    operators = _build_operators()

    fragmented = sum(1 for m in msas if m.market_structure == "fragmented")
    moderate = sum(1 for m in msas if m.market_structure == "moderately concentrated")
    high = sum(1 for m in msas if m.market_structure == "highly concentrated")

    avg_hhi = int(sum(m.hhi for m in msas) / len(msas)) if msas else 0
    median_hhi = int(statistics.median(m.hhi for m in msas)) if msas else 0
    avg_cr3 = sum(m.cr3_pct for m in msas) / len(msas) if msas else 0

    return MSAResult(
        total_msas_analyzed=len(msas),
        fragmented_count=fragmented,
        moderately_concentrated_count=moderate,
        highly_concentrated_count=high,
        avg_hhi=avg_hhi,
        median_hhi=median_hhi,
        avg_cr3_pct=round(avg_cr3, 4),
        msa_details=msas,
        regimes=regimes,
        whitespace=whitespace,
        stress_scenarios=stress,
        top_operators=operators,
        corpus_deal_count=len(corpus),
    )
