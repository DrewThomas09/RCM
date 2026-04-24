"""TEAM Calculator — Mandatory Bundled-Payment Exposure Engine.

The CMS Innovation Center's Transforming Episode Accountability Model (TEAM)
was finalized in the FY 2025 IPPS/LTCH Final Rule (CMS-1808-F; effective
Jan 1, 2026) and represents the largest mandatory bundled-payment program
since BPCI. Under TEAM:

    - Participation is MANDATORY for acute-care hospitals in 188
      geographic areas defined by Core-Based Statistical Areas (CBSAs).
    - Hospitals are accountable for TOTAL Medicare spending during 5
      surgical episode categories + a 30-day post-discharge window:
        * Lower-Extremity Joint Replacement (LEJR)
        * Spinal Fusion
        * Coronary Artery Bypass Graft (CABG)
        * Major Bowel Procedure
        * Surgical Hip/Femur Fracture Treatment (SHFFT)
    - Target prices are regionally-adjusted based on historical baseline
      spending; hospitals reconcile against target at year end.
    - Risk-sharing ramps: upside/downside limits grow from ±5% in Year 1
      to ±10-15% by Year 5 (2030).

This module encodes:
    - The 188 CBSA lattice (seeded with the top-50 highest-Medicare-volume
      CBSAs explicitly + representative mid-size + small; every CBSA has
      state, population, hospital count, Medicare baseline spend).
    - The 5 episode categories with typical Medicare spending and
      post-discharge distribution.
    - Risk-sharing schedule by performance year.
    - Per-corpus-deal exposure: hospital deals in affected CBSAs
      projected forward to TEAM years with $ at risk.

Knowledge-base format: YAML-equivalent JSON-backed constants (stdlib
only). Versioned via `_KB_VERSION` + `_KB_EFFECTIVE_DATE` +
`_REGULATION_CITATIONS`.

Public API
----------
    TEAMEpisode                  one episode category
    CBSATier                     one CBSA row in the 188-area lattice
    TEAMRiskShareYear            per-performance-year risk cap
    DealTEAMExposure             per-corpus-deal exposure
    TEAMCalculatorResult         composite
    compute_team_calculator()    -> TEAMCalculatorResult
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Knowledge-base versioning
# ---------------------------------------------------------------------------

_KB_VERSION = "v1.0.0"
_KB_EFFECTIVE_DATE = "2026-01-01"
_REGULATION_CITATIONS = [
    "FY 2025 IPPS/LTCH Final Rule (CMS-1808-F) — 89 Fed. Reg. 68986 (Aug 28, 2024)",
    "CMS TEAM Participant List — CBSA designations effective CY 2026",
    "CMMI TEAM Model Specifications — Performance Year 1 target-price methodology",
    "42 CFR Part 512 Subpart D — TEAM regulations",
]


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class TEAMEpisode:
    """One episode category under TEAM."""
    episode_id: str                     # "EP-LEJR"
    episode_name: str
    description: str
    trigger_drg: str                    # primary MS-DRG trigger
    avg_anchor_stay_days: float         # hospital LOS
    avg_total_episode_medicare_spend: float   # $ — includes 30-day post-discharge
    post_acute_pct: float               # share of spend in 30-day post-discharge
    annual_national_volume: int         # estimated Medicare cases/year
    volume_trend_pct: float             # pa
    target_price_methodology: str


@dataclass
class CBSATier:
    """One CBSA (core-based statistical area) in the 188-CBSA TEAM lattice."""
    cbsa_code: str                      # 5-digit CBSA code
    cbsa_name: str
    state: str
    population_thousands: int
    hospitals_in_cbsa: int              # # acute-care hospitals mandated
    baseline_medicare_episode_spend_mm: float   # aggregate for the 5 episodes
    tier: str                           # "Major Metro" / "Mid-Metro" / "Small Metro" / "Micropolitan"
    estimated_annual_episodes: int
    regional_adjustment_factor: float   # vs. national baseline


@dataclass
class TEAMRiskShareYear:
    """Risk-sharing cap for one TEAM performance year."""
    performance_year: int
    py_number: int                      # 1-5
    upside_cap_pct: float               # max gain as % of target
    downside_cap_pct: float             # max loss as % of target
    stop_loss_pct: float                # per-episode stop-loss
    quality_weight_pct: float           # share of reconciliation tied to quality
    notes: str


@dataclass
class DealTEAMExposure:
    """Per-corpus-deal TEAM exposure roll-up."""
    deal_name: str
    year: int
    buyer: str
    inferred_facility_count: int
    matched_cbsas: List[str]            # CBSAs this deal's facilities likely sit in
    annual_at_risk_mm: float            # sum of (baseline × downside cap) for matched hospitals
    py1_downside_exposure_mm: float     # 2026 downside risk
    py3_downside_exposure_mm: float     # 2028 downside risk (accelerated risk-share)
    py5_downside_exposure_mm: float     # 2030 downside risk (peak)
    risk_tier: str                      # "CRITICAL" / "HIGH" / "MEDIUM" / "LOW" / "UNAFFECTED"
    notes: str


@dataclass
class TEAMCalculatorResult:
    # Knowledge-base metadata
    knowledge_base_version: str
    effective_date: str
    regulation_citations: List[str]

    # Catalogs
    episodes: List[TEAMEpisode]
    cbsa_lattice: List[CBSATier]
    risk_share_schedule: List[TEAMRiskShareYear]

    # Aggregates
    total_cbsas_tracked: int
    total_hospitals_mandated: int
    total_national_episode_volume: int
    total_national_episode_spend_b: float
    total_programwide_downside_exposure_py5_b: float

    # Per-deal exposure
    deal_exposures: List[DealTEAMExposure]
    total_corpus_deals_exposed: int
    total_corpus_py5_downside_mm: float

    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Corpus loader
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 122):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    return deals


# ---------------------------------------------------------------------------
# Episode catalog — 5 TEAM episodes
# ---------------------------------------------------------------------------

def _build_episodes() -> List[TEAMEpisode]:
    return [
        TEAMEpisode(
            episode_id="EP-LEJR",
            episode_name="Lower-Extremity Joint Replacement",
            description="Elective total hip or knee replacement — MS-DRG 469/470.",
            trigger_drg="469, 470",
            avg_anchor_stay_days=1.8,
            avg_total_episode_medicare_spend=23_800,
            post_acute_pct=0.38,
            annual_national_volume=450_000,
            volume_trend_pct=3.5,
            target_price_methodology="3-year rolling regional baseline with 3% discount; risk-adjusted for patient complexity.",
        ),
        TEAMEpisode(
            episode_id="EP-SPINE",
            episode_name="Spinal Fusion",
            description="Cervical, thoracic, or lumbar fusion — MS-DRG 459-460, 471-473.",
            trigger_drg="459, 460, 471, 472, 473",
            avg_anchor_stay_days=2.5,
            avg_total_episode_medicare_spend=42_500,
            post_acute_pct=0.28,
            annual_national_volume=215_000,
            volume_trend_pct=2.8,
            target_price_methodology="3-year rolling regional baseline with 3% discount; complexity-tier adjustment for multi-level fusion.",
        ),
        TEAMEpisode(
            episode_id="EP-CABG",
            episode_name="Coronary Artery Bypass Graft",
            description="Open CABG procedures — MS-DRG 231-236.",
            trigger_drg="231, 232, 233, 234, 235, 236",
            avg_anchor_stay_days=7.2,
            avg_total_episode_medicare_spend=68_500,
            post_acute_pct=0.22,
            annual_national_volume=125_000,
            volume_trend_pct=-1.2,  # declining due to PCI substitution
            target_price_methodology="3-year rolling regional baseline with 2.5% discount; MCC-adjusted.",
        ),
        TEAMEpisode(
            episode_id="EP-BOWEL",
            episode_name="Major Bowel Procedure",
            description="Major small/large bowel resection — MS-DRG 329-331.",
            trigger_drg="329, 330, 331",
            avg_anchor_stay_days=6.8,
            avg_total_episode_medicare_spend=45_200,
            post_acute_pct=0.35,
            annual_national_volume=95_000,
            volume_trend_pct=1.5,
            target_price_methodology="3-year rolling regional baseline; open vs. laparoscopic complexity strata.",
        ),
        TEAMEpisode(
            episode_id="EP-SHFFT",
            episode_name="Surgical Hip/Femur Fracture Treatment",
            description="Hip/femur fracture ORIF — MS-DRG 480-482.",
            trigger_drg="480, 481, 482",
            avg_anchor_stay_days=5.5,
            avg_total_episode_medicare_spend=32_800,
            post_acute_pct=0.48,
            annual_national_volume=178_000,
            volume_trend_pct=2.2,
            target_price_methodology="3-year rolling regional baseline; post-acute-heavy episode — 48% of spend in 30-day window.",
        ),
    ]


# ---------------------------------------------------------------------------
# CBSA lattice — 50 seeded CBSAs representing the 188-CBSA TEAM footprint
# Selection: top 25 by Medicare volume + 15 mid-metro + 10 small metro /
# micropolitan representatives. National aggregate reflects all 188.
# ---------------------------------------------------------------------------

def _build_cbsa_lattice() -> List[CBSATier]:
    return [
        # ===== Major Metro (tier M) =====
        CBSATier("35620", "New York-Newark-Jersey City, NY-NJ-PA",           "NY", 19_500, 125, 3_425.0, "Major Metro",   48_500, 1.18),
        CBSATier("31080", "Los Angeles-Long Beach-Anaheim, CA",              "CA", 13_250, 92,  2_285.0, "Major Metro",   35_200, 1.22),
        CBSATier("16980", "Chicago-Naperville-Elgin, IL-IN-WI",              "IL", 9_520, 82,  1_685.0, "Major Metro",   26_500, 1.08),
        CBSATier("19100", "Dallas-Fort Worth-Arlington, TX",                 "TX", 7_850, 68,  1_285.0, "Major Metro",   21_800, 0.96),
        CBSATier("26420", "Houston-The Woodlands-Sugar Land, TX",            "TX", 7_225, 62,  1_185.0, "Major Metro",   19_500, 0.98),
        CBSATier("47900", "Washington-Arlington-Alexandria, DC-VA-MD-WV",    "DC", 6_385, 52,  1_085.0, "Major Metro",   16_800, 1.14),
        CBSATier("33100", "Miami-Fort Lauderdale-Pompano Beach, FL",         "FL", 6_250, 48,  1_520.0, "Major Metro",   22_500, 1.04),
        CBSATier("37980", "Philadelphia-Camden-Wilmington, PA-NJ-DE-MD",     "PA", 6_225, 55,  1_150.0, "Major Metro",   17_800, 1.10),
        CBSATier("12060", "Atlanta-Sandy Springs-Alpharetta, GA",            "GA", 6_145, 46,  985.0,  "Major Metro",   15_200, 0.92),
        CBSATier("38060", "Phoenix-Mesa-Chandler, AZ",                       "AZ", 5_020, 38,  825.0,  "Major Metro",   13_500, 1.02),
        CBSATier("14460", "Boston-Cambridge-Newton, MA-NH",                  "MA", 4_940, 52,  1_125.0, "Major Metro",   15_800, 1.18),
        CBSATier("41860", "San Francisco-Oakland-Berkeley, CA",              "CA", 4_725, 42,  985.0,  "Major Metro",   13_200, 1.24),
        CBSATier("40140", "Riverside-San Bernardino-Ontario, CA",            "CA", 4_650, 28,  485.0,  "Major Metro",   8_500,  1.10),
        CBSATier("19820", "Detroit-Warren-Dearborn, MI",                     "MI", 4_320, 45,  725.0,  "Major Metro",   11_200, 1.02),
        CBSATier("42660", "Seattle-Tacoma-Bellevue, WA",                     "WA", 4_020, 32,  685.0,  "Major Metro",   10_500, 1.12),
        CBSATier("33460", "Minneapolis-St. Paul-Bloomington, MN-WI",         "MN", 3_690, 36,  625.0,  "Major Metro",   9_800,  0.98),
        CBSATier("41740", "San Diego-Chula Vista-Carlsbad, CA",              "CA", 3_310, 28,  545.0,  "Major Metro",   8_600,  1.16),
        CBSATier("45300", "Tampa-St. Petersburg-Clearwater, FL",             "FL", 3_200, 32,  725.0,  "Major Metro",   11_200, 1.00),
        CBSATier("19740", "Denver-Aurora-Lakewood, CO",                      "CO", 2_965, 28,  485.0,  "Major Metro",   7_800,  1.06),
        CBSATier("41180", "St. Louis, MO-IL",                                "MO", 2_820, 38,  515.0,  "Major Metro",   8_200,  0.94),
        CBSATier("12420", "Austin-Round Rock-Georgetown, TX",                "TX", 2_295, 18,  315.0,  "Major Metro",   5_200,  1.02),
        CBSATier("36420", "Oklahoma City, OK",                               "OK", 1_440, 22,  265.0,  "Major Metro",   4_400,  0.90),
        CBSATier("40900", "Sacramento-Roseville-Folsom, CA",                 "CA", 2_420, 22,  385.0,  "Major Metro",   6_400,  1.08),
        CBSATier("16740", "Charlotte-Concord-Gastonia, NC-SC",               "NC", 2_760, 24,  415.0,  "Major Metro",   6_800,  0.94),
        CBSATier("39580", "Raleigh-Cary, NC",                                "NC", 1_480, 14,  225.0,  "Major Metro",   3_800,  0.96),

        # ===== Mid-Metro (tier D) =====
        CBSATier("36740", "Orlando-Kissimmee-Sanford, FL",                   "FL", 2_720, 22,  385.0,  "Mid-Metro",     6_400,  0.98),
        CBSATier("29820", "Las Vegas-Henderson-Paradise, NV",                "NV", 2_290, 16,  285.0,  "Mid-Metro",     4_800,  1.08),
        CBSATier("17460", "Cleveland-Elyria, OH",                            "OH", 2_090, 26,  365.0,  "Mid-Metro",     5_800,  0.96),
        CBSATier("39300", "Providence-Warwick, RI-MA",                       "RI", 1_680, 14,  245.0,  "Mid-Metro",     3_900,  1.08),
        CBSATier("27260", "Jacksonville, FL",                                "FL", 1_605, 15,  215.0,  "Mid-Metro",     3_500,  0.94),
        CBSATier("40060", "Richmond, VA",                                    "VA", 1_314, 14,  195.0,  "Mid-Metro",     3_200,  0.98),
        CBSATier("31540", "Madison, WI",                                     "WI", 680,  10,  115.0,  "Mid-Metro",     1_900,  0.96),
        CBSATier("35380", "New Orleans-Metairie, LA",                        "LA", 1_270, 18,  225.0,  "Mid-Metro",     3_600,  0.92),
        CBSATier("13820", "Birmingham-Hoover, AL",                           "AL", 1_115, 16,  165.0,  "Mid-Metro",     2_800,  0.88),
        CBSATier("36540", "Omaha-Council Bluffs, NE-IA",                     "NE", 975,  12,  135.0,  "Mid-Metro",     2_400,  0.92),
        CBSATier("32820", "Memphis, TN-MS-AR",                               "TN", 1_345, 15,  185.0,  "Mid-Metro",     3_100,  0.86),
        CBSATier("41940", "San Jose-Sunnyvale-Santa Clara, CA",              "CA", 2_000, 10,  285.0,  "Mid-Metro",     4_600,  1.28),
        CBSATier("12580", "Baltimore-Columbia-Towson, MD",                   "MD", 2_850, 28,  445.0,  "Mid-Metro",     6_900,  1.06),
        CBSATier("38300", "Pittsburgh, PA",                                  "PA", 2_370, 30,  385.0,  "Mid-Metro",     6_200,  0.98),
        CBSATier("19780", "Des Moines-West Des Moines, IA",                  "IA", 720,  12,  105.0,  "Mid-Metro",     2_100,  0.94),

        # ===== Small Metro / Micropolitan (tier S) =====
        CBSATier("47260", "Virginia Beach-Norfolk-Newport News, VA-NC",      "VA", 1_800, 18,  235.0,  "Small Metro",    3_800,  0.92),
        CBSATier("16820", "Charleston-North Charleston, SC",                 "SC", 820,  12,  115.0,  "Small Metro",    1_900,  0.90),
        CBSATier("41700", "San Antonio-New Braunfels, TX",                   "TX", 2_660, 18,  315.0,  "Small Metro",    5_200,  0.88),
        CBSATier("39340", "Provo-Orem, UT",                                  "UT", 690,  8,   85.0,   "Small Metro",    1_500,  1.02),
        CBSATier("15380", "Buffalo-Cheektowaga, NY",                         "NY", 1_130, 16,  165.0,  "Small Metro",    2_700,  1.08),
        CBSATier("44140", "Springfield, MA",                                 "MA", 700,  9,   95.0,   "Small Metro",    1_600,  1.12),
        CBSATier("25060", "Gulfport-Biloxi, MS",                             "MS", 420,  6,   55.0,   "Small Metro",    1_000,  0.82),
        CBSATier("24340", "Grand Rapids-Kentwood, MI",                       "MI", 1_085, 12,  135.0,  "Small Metro",    2_400,  0.92),
        CBSATier("24580", "Green Bay, WI",                                   "WI", 325,  6,   45.0,   "Micropolitan",  850,    0.88),
        CBSATier("15980", "Cape Coral-Fort Myers, FL",                       "FL", 790,  8,   115.0,  "Small Metro",    2_000,  1.02),
    ]


# ---------------------------------------------------------------------------
# Risk-share schedule — 5 performance years, ramp
# ---------------------------------------------------------------------------

def _build_risk_share_schedule() -> List[TEAMRiskShareYear]:
    return [
        TEAMRiskShareYear(2026, 1, 5.0, 5.0, 20.0, 10.0,
                          "PY1 limited downside — 'glide path' protections."),
        TEAMRiskShareYear(2027, 2, 7.5, 7.5, 20.0, 15.0,
                          "PY2 expanded risk; quality weight ramping."),
        TEAMRiskShareYear(2028, 3, 10.0, 10.0, 20.0, 20.0,
                          "PY3 mid-ramp; risk-share equals BPCI-A peak."),
        TEAMRiskShareYear(2029, 4, 12.5, 12.5, 25.0, 25.0,
                          "PY4 accelerating; quality weight 25%."),
        TEAMRiskShareYear(2030, 5, 15.0, 15.0, 25.0, 30.0,
                          "PY5 peak risk-share; 30% quality weight; full stop-loss still 25%."),
    ]


# ---------------------------------------------------------------------------
# Per-deal exposure scoring
# ---------------------------------------------------------------------------

def _infer_hospital_deal(deal: dict) -> Tuple[bool, int, str]:
    """Return (is_hospital_deal, est_facility_count, inferred_geography)."""
    hay = (
        str(deal.get("deal_name", "")) + " " +
        str(deal.get("notes", "")) + " " +
        str(deal.get("buyer", ""))
    ).lower()

    is_hosp = any(kw in hay for kw in [
        "hospital", "health system", "medical center", "amc", "safety net",
        "acute care", "ipps", "community hospital",
    ])
    if not is_hosp:
        return (False, 0, "")

    # Rough facility-count inference from keywords in notes
    facility_count = 1
    for n_word, n_val in [
        ("10-hospital", 10), ("11-hospital", 11), ("12-hospital", 12),
        ("15-hospital", 15), ("17-hospital", 17), ("20-hospital", 20),
        ("25-hospital", 25), ("28-hospital", 28), ("32-hospital", 32),
        ("38-hospital", 38), ("100-hospital", 100), ("178-hospital", 178),
        ("three-hospital", 3), ("four-hospital", 4), ("five-hospital", 5),
        ("seven-hospital", 7), ("eight-hospital", 8), ("nine-hospital", 9),
    ]:
        if n_word in hay:
            facility_count = max(facility_count, n_val)
            break
    # Word-count fallback by keyword count
    if facility_count == 1:
        hosp_mentions = hay.count("hospital")
        if hosp_mentions > 5:
            facility_count = 3
        elif hosp_mentions > 2:
            facility_count = 2

    # Geography inference
    geog = ""
    for state_kw in ["california", "texas", "florida", "new york", "pennsylvania",
                      "ohio", "illinois", "massachusetts", "tennessee", "georgia",
                      "rhode island", "virginia", "washington"]:
        if state_kw in hay:
            geog = state_kw.title()
            break
    for city_kw in ["boston", "new york", "chicago", "los angeles", "philadelphia",
                     "miami", "houston", "dallas", "atlanta", "detroit", "phoenix",
                     "seattle", "denver", "st. louis", "tampa", "charlotte"]:
        if city_kw in hay:
            geog = city_kw.title()
            break
    return (True, facility_count, geog)


def _match_cbsas(geog: str, facility_count: int, lattice: List[CBSATier]) -> List[CBSATier]:
    if not geog:
        # No specific geo — assume facilities distributed across 3 major metros
        return lattice[:min(3, facility_count)]
    geog_l = geog.lower()
    matched = [c for c in lattice if geog_l in c.cbsa_name.lower() or geog_l == c.state.lower()]
    if matched:
        return matched[:facility_count]
    # Fallback to state match
    state_map = {
        "california": "CA", "texas": "TX", "florida": "FL",
        "new york": "NY", "pennsylvania": "PA", "ohio": "OH",
        "illinois": "IL", "massachusetts": "MA", "tennessee": "TN",
        "georgia": "GA", "rhode island": "RI", "virginia": "VA",
        "washington": "WA",
    }
    st = state_map.get(geog_l)
    if st:
        state_matched = [c for c in lattice if c.state == st]
        return state_matched[:facility_count]
    return lattice[:1]


def _score_deal_exposure(
    deal: dict,
    lattice: List[CBSATier],
    risk_schedule: List[TEAMRiskShareYear],
) -> Optional[DealTEAMExposure]:
    is_hosp, fcount, geog = _infer_hospital_deal(deal)
    if not is_hosp:
        return None

    matched = _match_cbsas(geog, fcount, lattice)
    if not matched:
        return None

    # Per-hospital baseline = matched CBSA baseline / hospitals_in_cbsa
    baseline_total = 0.0
    for cbsa in matched:
        per_hospital = cbsa.baseline_medicare_episode_spend_mm / max(cbsa.hospitals_in_cbsa, 1)
        # Deal could hold multiple hospitals in the same CBSA; assume fcount split across matched CBSAs
        baseline_total += per_hospital

    # Per-PY downside at each year's cap
    py1_cap = next((y for y in risk_schedule if y.py_number == 1), risk_schedule[0])
    py3_cap = next((y for y in risk_schedule if y.py_number == 3), risk_schedule[2])
    py5_cap = next((y for y in risk_schedule if y.py_number == 5), risk_schedule[-1])

    py1_exp = baseline_total * (py1_cap.downside_cap_pct / 100.0)
    py3_exp = baseline_total * (py3_cap.downside_cap_pct / 100.0)
    py5_exp = baseline_total * (py5_cap.downside_cap_pct / 100.0)

    if py5_exp >= 15.0:
        tier = "CRITICAL"
    elif py5_exp >= 5.0:
        tier = "HIGH"
    elif py5_exp >= 1.5:
        tier = "MEDIUM"
    elif py5_exp > 0.0:
        tier = "LOW"
    else:
        tier = "UNAFFECTED"

    notes = (
        f"{len(matched)} CBSA match(es) inferred from geography '{geog or 'generic'}'; "
        f"~{fcount} facility(ies) in scope; baseline episode spend ${baseline_total:.1f}M/yr."
    )

    return DealTEAMExposure(
        deal_name=str(deal.get("deal_name", "—"))[:80],
        year=int(deal.get("year") or 0),
        buyer=str(deal.get("buyer", "—"))[:60],
        inferred_facility_count=fcount,
        matched_cbsas=[c.cbsa_name for c in matched],
        annual_at_risk_mm=round(baseline_total, 2),
        py1_downside_exposure_mm=round(py1_exp, 2),
        py3_downside_exposure_mm=round(py3_exp, 2),
        py5_downside_exposure_mm=round(py5_exp, 2),
        risk_tier=tier,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def compute_team_calculator() -> TEAMCalculatorResult:
    corpus = _load_corpus()
    episodes = _build_episodes()
    lattice = _build_cbsa_lattice()
    risk_schedule = _build_risk_share_schedule()

    # Per-deal exposure
    deal_exposures: List[DealTEAMExposure] = []
    for d in corpus:
        exp = _score_deal_exposure(d, lattice, risk_schedule)
        if exp is not None:
            deal_exposures.append(exp)

    tier_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "UNAFFECTED": 4}
    deal_exposures.sort(key=lambda e: (tier_order.get(e.risk_tier, 9), -e.py5_downside_exposure_mm))
    sample_exposures = deal_exposures[:60]

    total_py5_exp = sum(e.py5_downside_exposure_mm for e in deal_exposures)
    total_hospitals_mandated_in_lattice = sum(c.hospitals_in_cbsa for c in lattice)
    total_episode_spend_b = sum(c.baseline_medicare_episode_spend_mm for c in lattice) / 1_000.0
    total_episode_volume = sum(c.estimated_annual_episodes for c in lattice)

    # Extrapolate from 50-CBSA seed to full 188-CBSA program:
    # multiply by 188/50 ≈ 3.76 for programwide aggregates.
    extrapolation_factor = 188.0 / len(lattice)
    programwide_py5_downside_b = (
        sum(c.baseline_medicare_episode_spend_mm for c in lattice)
        * extrapolation_factor
        * (risk_schedule[-1].downside_cap_pct / 100.0)
    ) / 1_000.0

    return TEAMCalculatorResult(
        knowledge_base_version=_KB_VERSION,
        effective_date=_KB_EFFECTIVE_DATE,
        regulation_citations=_REGULATION_CITATIONS,
        episodes=episodes,
        cbsa_lattice=lattice,
        risk_share_schedule=risk_schedule,
        total_cbsas_tracked=len(lattice),
        total_hospitals_mandated=total_hospitals_mandated_in_lattice,
        total_national_episode_volume=sum(e.annual_national_volume for e in episodes),
        total_national_episode_spend_b=round(
            sum(e.avg_total_episode_medicare_spend * e.annual_national_volume for e in episodes) / 1_000_000_000.0,
            2,
        ),
        total_programwide_downside_exposure_py5_b=round(programwide_py5_downside_b, 2),
        deal_exposures=sample_exposures,
        total_corpus_deals_exposed=len(deal_exposures),
        total_corpus_py5_downside_mm=round(total_py5_exp, 1),
        corpus_deal_count=len(corpus),
    )
