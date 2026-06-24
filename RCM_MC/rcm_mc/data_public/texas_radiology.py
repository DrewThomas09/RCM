"""Texas radiology deep-dive — the outsourced / hybrid on-site + tele market.

Narrows the national radiology atlas to Texas and the specific business profile
of a **Lubbock, TX-headquartered, hybrid on-site + teleradiology platform** that
serves rural Texas hospitals and partners across 15+ states with AI-supported
diagnostic and interventional reads. (Subject company profile is drawn from
public sources — coaxionradiology.com / ZoomInfo — and framed as Texas market
intelligence; nothing here is deal-, transaction-, or engagement-specific.)

DATA REUSE — this module deliberately cross-uses the Texas-infusion evidence
base rather than re-deriving it:
  * ``rcm_mc.data.county_demographics._county()`` — the committed 254-county
    Texas ACS aggregate (population, 65+ share, rural share, uninsured rate,
    median income) already vendored for the infusion geography model. Imaging
    demand is the SAME senior/population apportionment the infusion model uses
    (0.60·senior-share + 0.40·population-share), because radiology demand, like
    infusion demand, is driven by an aging, geographically-dispersed population.
  * The Texas payer-mix shape (commercial-heavy, ~Medicare third, ~20% uninsured
    drag) mirrors ``texas_infusion._payer_mix`` — the same Texas payer reality.

The Texas twist radiology adds on top of that shared base is the **rural
coverage gap**: Texas has the most rural hospitals and the most rural-hospital
closures of any state, its radiologists concentrate in the five big metros, and
its sparse West-Texas counties (the Lubbock catchment) cannot staff an on-site
radiologist — which is exactly the demand an on-site + tele hybrid serves.

CMS layer (kept deliberately tight): Novitas Solutions is the Texas Part-B MAC
(Jurisdiction JH); the live Novitas MRA LCD (L34865) is the Texas-binding local
policy; and the Texas PFS GPCI localities show why the same read pays a metro
premium and a rural discount within one state.

Falls back to a curated metro/rural county subset if the vendored ACS aggregate
is absent, so the page always renders.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Dataclasses
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class TXCounty:
    county: str
    fips: str
    population: int
    pct_65_plus: float
    pct_rural: float
    uninsured_rate: float
    median_income: int
    imaging_demand_share: float   # share of TX imaging demand (0.6 senior + 0.4 pop)
    coverage_gap_score: float     # 0-100; high = rural+aging, on-site+tele opportunity
    tier: str                     # metro / suburban / rural-gap


@dataclass
class TXMarketStat:
    metric: str
    value: str
    detail: str
    source: str


@dataclass
class TXCMSConnection:
    label: str
    kind: str                     # MAC / LCD / GPCI / code
    identifier: str
    detail: str
    url: str


@dataclass
class TXGPCILocality:
    locality: str
    work_gpci: float
    pe_gpci: float                # practice-expense GPCI — the metro/rural swing
    mp_gpci: float
    read_economics: str


@dataclass
class TXOutsourcedProfile:
    attribute: str
    value: str
    dimension3_read: str


@dataclass
class TXPayerShare:
    payer: str
    share_pct: float
    note: str


@dataclass
class OperatingState:
    """A state in the platform's operating footprint (from the public coverage
    map): which MAC prices it, Medicaid-expansion status, payer skew, and the
    competitive/teleradiology dynamic there."""
    state: str
    postal: str
    region: str
    mac: str
    medicaid_expansion: str       # "expanded (year)" / "non-expansion"
    payer_skew: str
    competitive_note: str


@dataclass
class RegionPayerMix:
    """Payer mix for an operating region — the 'payer mix by these groups' cut."""
    region: str
    states: str
    commercial_pct: float
    medicare_pct: float
    medicaid_pct: float
    uninsured_pct: float
    dynamics: str


@dataclass
class TeleradiologyTrend:
    trend: str
    detail: str
    hybrid_implication: str       # what it means for an on-site+tele hybrid


@dataclass
class AIWorkflowReality:
    """Market-intelligence read on where AI actually helps the radiology
    workflow — public industry knowledge (Viz/Aidoc/Rad AI/Harrison.ai/
    PowerScribe), not any confidential source."""
    theme: str
    reality: str
    evidence: str


@dataclass
class ServiceLine:
    line: str
    description: str
    competitive_edge: str


@dataclass
class TexasRadiologyResult:
    counties_modeled: int
    tx_population: int
    tx_senior_population: int
    tx_rural_population: int
    tx_uninsured_rate: float
    data_mode: str                # "ACS aggregate (reused)" | "curated fallback"
    metro_counties: List[TXCounty]
    rural_gap_counties: List[TXCounty]
    lubbock: Optional[TXCounty]
    market_stats: List[TXMarketStat]
    cms_connections: List[TXCMSConnection]
    gpci_localities: List[TXGPCILocality]
    outsourced_profile: List[TXOutsourcedProfile]
    payer_shares: List[TXPayerShare]
    operating_states: List[OperatingState]
    region_payer_mix: List[RegionPayerMix]
    teleradiology_trends: List[TeleradiologyTrend]
    ai_workflow: List[AIWorkflowReality]
    service_lines: List[ServiceLine]
    operating_state_count: int
    mac_count: int


# ─────────────────────────────────────────────────────────────────────────────
# Reuse the infusion county base
# ─────────────────────────────────────────────────────────────────────────────
# Curated fallback: the largest TX metro counties + representative West-Texas
# rural-gap counties (the Lubbock catchment). Real ACS magnitudes; used only
# when the vendored 254-county aggregate isn't present.
_FALLBACK_COUNTIES: List[Dict[str, Any]] = [
    # name, fips, population, pct_65, pct_rural, uninsured, median_income
    {"n": "Harris County", "f": "48201", "p": 4780913, "s": 0.117, "r": 0.011, "u": 0.205, "i": 66000},
    {"n": "Dallas County", "f": "48113", "p": 2600840, "s": 0.118, "r": 0.006, "u": 0.214, "i": 64000},
    {"n": "Tarrant County", "f": "48439", "p": 2154595, "s": 0.123, "r": 0.012, "u": 0.166, "i": 70000},
    {"n": "Bexar County", "f": "48029", "p": 2059530, "s": 0.128, "r": 0.047, "u": 0.170, "i": 60000},
    {"n": "Travis County", "f": "48453", "p": 1326436, "s": 0.110, "r": 0.051, "u": 0.135, "i": 86000},
    {"n": "Collin County", "f": "48085", "p": 1158696, "s": 0.117, "r": 0.061, "u": 0.110, "i": 105000},
    {"n": "El Paso County", "f": "48141", "p": 865657, "s": 0.130, "r": 0.020, "u": 0.220, "i": 51000},
    {"n": "Hidalgo County", "f": "48215", "p": 880356, "s": 0.108, "r": 0.130, "u": 0.290, "i": 42000},
    {"n": "Lubbock County", "f": "48303", "p": 318862, "s": 0.130, "r": 0.060, "u": 0.165, "i": 56000},
    {"n": "Hale County", "f": "48189", "p": 32522, "s": 0.165, "r": 0.300, "u": 0.215, "i": 47000},
    {"n": "Terry County", "f": "48445", "p": 11831, "s": 0.170, "r": 0.420, "u": 0.230, "i": 45000},
    {"n": "Garza County", "f": "48169", "p": 5816, "s": 0.150, "r": 0.520, "u": 0.215, "i": 52000},
    {"n": "Cochran County", "f": "48079", "p": 2750, "s": 0.190, "r": 0.700, "u": 0.240, "i": 43000},
    {"n": "Dickens County", "f": "48125", "p": 1770, "s": 0.230, "r": 0.760, "u": 0.220, "i": 41000},
]

_BIG_METRO_FIPS = {"48201", "48113", "48439", "48029", "48453", "48085",
                   "48141", "48215", "48121", "48157", "48491"}  # incl Denton/Fort Bend/Williamson


def _load_tx_counties() -> tuple[List[Dict[str, Any]], str]:
    """Reuse the committed 254-county ACS aggregate from the infusion model.
    Returns (rows, mode). Falls back to the curated subset if absent."""
    try:
        from ..data.county_demographics import _county
        df = _county()
        if df is not None and len(df):
            tx = df[df["state"] == "TX"]
            rows: List[Dict[str, Any]] = []
            for r in tx.itertuples(index=False):
                rows.append({
                    "n": str(getattr(r, "county_name", "")),
                    "f": str(getattr(r, "county_fips", "")),
                    "p": int(float(getattr(r, "population", 0) or 0)),
                    "s": float(getattr(r, "pct_age_65_plus", 0) or 0),
                    "r": float(getattr(r, "pct_rural", 0) or 0),
                    "u": float(getattr(r, "uninsured_rate", 0) or 0),
                    "i": int(float(getattr(r, "median_household_income", 0) or 0)),
                })
            if rows:
                return rows, "ACS aggregate (reused from infusion model)"
    except Exception:
        pass
    return _FALLBACK_COUNTIES, "curated fallback"


def _tier(fips: str, pct_rural: float, population: int) -> str:
    if fips in _BIG_METRO_FIPS or population >= 500_000:
        return "metro"
    if pct_rural >= 0.25 or population < 50_000:
        return "rural-gap"
    return "suburban"


def compute_texas_radiology() -> TexasRadiologyResult:
    rows, mode = _load_tx_counties()

    tx_pop = sum(r["p"] for r in rows) or 1
    tx_senior = sum(r["p"] * r["s"] for r in rows)
    tx_rural = sum(r["p"] * r["r"] for r in rows)
    tx_senior_total = tx_senior or 1.0
    # Uninsured rate weighted by population.
    tx_uninsured = sum(r["p"] * r["u"] for r in rows) / tx_pop

    counties: List[TXCounty] = []
    for r in rows:
        pop = r["p"]; s65 = r["s"]; rural = max(0.0, min(1.0, r["r"]))
        seniors = pop * s65
        # Same 60/40 senior/population apportionment the infusion model uses —
        # radiology demand, like infusion, skews to the aging population.
        demand_share = 0.60 * (seniors / tx_senior_total) + 0.40 * (pop / tx_pop)
        # Coverage-gap score: rural × aging-lift × not-a-major-metro. High score
        # = the county a sparse-market on-site+tele hybrid actually serves.
        metro = r["f"] in _BIG_METRO_FIPS or pop >= 500_000
        aging_lift = min(2.0, s65 / 0.12)        # vs ~12% TX baseline
        gap = rural * aging_lift * (0.15 if metro else 1.0)
        gap_score = round(min(100.0, gap * 100.0), 1)
        counties.append(TXCounty(
            county=r["n"].replace(" County", ""),
            fips=r["f"], population=pop, pct_65_plus=s65, pct_rural=rural,
            uninsured_rate=r["u"], median_income=r["i"],
            imaging_demand_share=round(demand_share * 100.0, 2),
            coverage_gap_score=gap_score,
            tier=_tier(r["f"], rural, pop),
        ))

    metro_counties = sorted(counties, key=lambda c: c.imaging_demand_share, reverse=True)[:10]
    # Rank rural-gap by gap, then by population — a high-gap county with a real
    # population is more likely to have a critical-access hospital to cover than
    # an empty one, so it's the more actionable coverage target.
    rural_gap_counties = sorted(
        [c for c in counties if c.tier == "rural-gap"],
        key=lambda c: (c.coverage_gap_score, c.population), reverse=True)[:12]
    lubbock = next((c for c in counties if c.fips == "48303"), None)

    return TexasRadiologyResult(
        counties_modeled=len(counties),
        tx_population=int(tx_pop),
        tx_senior_population=int(tx_senior),
        tx_rural_population=int(tx_rural),
        tx_uninsured_rate=round(tx_uninsured, 3),
        data_mode=mode,
        metro_counties=metro_counties,
        rural_gap_counties=rural_gap_counties,
        lubbock=lubbock,
        market_stats=_build_market_stats(),
        cms_connections=_build_cms_connections(),
        gpci_localities=_build_gpci(),
        outsourced_profile=_build_outsourced_profile(),
        payer_shares=_build_payer_shares(),
        operating_states=(op_states := _build_operating_states()),
        region_payer_mix=_build_region_payer_mix(),
        teleradiology_trends=_build_teleradiology_trends(),
        ai_workflow=_build_ai_workflow(),
        service_lines=_build_service_lines(),
        operating_state_count=len(op_states),
        mac_count=len({s.mac.split(" (")[0] for s in op_states}),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Texas market context (sourced estimates)
# ─────────────────────────────────────────────────────────────────────────────
def _build_market_stats() -> List[TXMarketStat]:
    return [
        TXMarketStat("Texas acute-care hospitals", "~430+",
                     "Among the most of any state; large rural footprint",
                     "AHA / THA (approx)"),
        TXMarketStat("Texas rural hospitals", "~160",
                     "Most rural hospitals of any state — the tele/on-site demand base",
                     "TX Organization of Rural & Community Hospitals (approx)"),
        TXMarketStat("TX rural hospital closures (since 2010)", "~25+",
                     "Most rural closures of any state; survivors run lean on coverage",
                     "Cecil G. Sheps Center (approx)"),
        TXMarketStat("Texas radiologists (approx)", "~3,000",
                     "Concentrated in Houston/Dallas/Austin/San Antonio/Fort Worth metros",
                     "ACR / NPPES (approx)"),
        TXMarketStat("Freestanding imaging centers (TX)", "~720",
                     "2nd-largest state imaging-center base after California",
                     "IBISWorld / NPPES (approx)"),
        TXMarketStat("Texas Part-B MAC", "Novitas (JH)",
                     "Prices every Texas Part-B imaging claim; issues TX-binding LCDs",
                     "CMS — live"),
        TXMarketStat("PFS GPCI localities in Texas", "8",
                     "Austin, Beaumont, Brazoria, Dallas, Fort Worth, Galveston, Houston, Rest of Texas",
                     "CMS PFS GPCI"),
    ]


# CMS connections kept deliberately tight (Texas-binding only).
def _build_cms_connections() -> List[TXCMSConnection]:
    return [
        TXCMSConnection(
            "Texas Part-B MAC", "MAC", "Novitas Solutions, Inc. (JH)",
            "Processes all TX Part-B imaging claims and authors the local coverage that binds Texas; "
            "JH also covers AR, CO, LA, MS, NM, OK.",
            "https://www.cms.gov/medicare-coverage-database"),
        TXCMSConnection(
            "MR Angiography (Texas LCD)", "LCD", "L34865 (Novitas)",
            "Magnetic Resonance Angiography — the live Novitas local coverage determination binding Texas "
            "(effective 2020-07-01). Sets the TX coverage conditions for MRA.",
            "https://www.cms.gov/medicare-coverage-database/view/lcd.aspx?lcdid=34865"),
        TXCMSConnection(
            "GPCI localization", "GPCI", "8 TX localities",
            "The same CPT pays a metro premium (higher practice-expense GPCI) and a 'Rest of Texas' discount — "
            "a structural reason rural reads are economically thinner.",
            "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
    ]


# Approximate TX GPCI values (~CY2025). Exact values are published per locality;
# these are directional — the point is the metro vs Rest-of-Texas PE swing.
def _build_gpci() -> List[TXGPCILocality]:
    return [
        TXGPCILocality("Houston", 1.014, 0.995, 1.169, "Metro PE premium; highest TX read economics."),
        TXGPCILocality("Dallas", 1.009, 1.001, 1.045, "Metro PE premium."),
        TXGPCILocality("Austin", 1.004, 1.004, 0.900, "Metro; lower malpractice GPCI."),
        TXGPCILocality("Fort Worth", 1.000, 0.953, 1.045, "Metro."),
        TXGPCILocality("Galveston", 1.000, 0.945, 1.169, "Coastal metro."),
        TXGPCILocality("Beaumont", 0.987, 0.901, 1.169, "Smaller metro."),
        TXGPCILocality("Brazoria", 1.000, 0.949, 1.169, "Houston-adjacent."),
        TXGPCILocality("Rest of Texas", 0.991, 0.876, 0.950, "Rural discount — the thinnest read economics; the hybrid's market."),
    ]


# Public profile of the subject Texas-HQ outsourced radiology platform, framed
# against Dimension-3 mechanics. Public-source facts only (company website /
# ZoomInfo); no transaction, engagement, or non-public detail.
def _build_outsourced_profile() -> List[TXOutsourcedProfile]:
    return [
        TXOutsourcedProfile("Headquarters", "Lubbock, Texas (West Texas hub)",
                            "A regional metro hub surrounded by sparse rural counties — the natural base for a hub-and-spoke on-site+tele model."),
        TXOutsourcedProfile("Model", "Hybrid 24/7 on-site + teleradiology",
                            "Covers both on-premise procedures/supervision AND remote reads — the single-vendor hybrid archetype that can displace a local group AND a tele-only vendor."),
        TXOutsourcedProfile("Footprint", "Hospitals, imaging centers & clinics across 15+ US states",
                            "Tele backbone scales the Lubbock reading capacity nationally; geography of the read is irrelevant to the ordering physician."),
        TXOutsourcedProfile("Clinical scope", "Diagnostic + interventional radiology",
                            "IR requires on-site presence — the part tele-only competitors structurally can't serve."),
        TXOutsourcedProfile("Technology", "AI-supported reads",
                            "AI as productivity/triage enabler against the radiologist-supply gap — accretive, not (yet) substitutive."),
        TXOutsourcedProfile("Served market", "Rural & community hospitals",
                            "Maps onto Texas's ~160 rural hospitals that cannot staff an on-site radiologist — the high-coverage-gap counties below."),
    ]


# Texas payer mix — reuses the infusion model's TX payer shape (commercial-heavy,
# Medicare ~third, ~20% uninsured drag), the same Texas payer reality.
def _build_payer_shares() -> List[TXPayerShare]:
    return [
        TXPayerShare("Commercial / employer", 45.0, "Best-paying book; concentrated in the metros."),
        TXPayerShare("Medicare (FFS + MA)", 33.0, "Aging West-Texas counties skew Medicare; the imaging-demand driver."),
        TXPayerShare("Medicaid (TX)", 13.0, "Non-expansion state — thin Medicaid; rural safety-net load."),
        TXPayerShare("Self-pay / uninsured", 9.0, "TX has ~the highest uninsured rate in the US (~18-20%) — a real rural-read payer drag."),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Operating footprint — the states the public coverage map shows, by region.
# A 15+ state on-site+tele platform spans all 7 Medicare MACs, so it credentials
# and complies across seven different local-coverage (LCD) regimes at once.
# ─────────────────────────────────────────────────────────────────────────────
def _build_operating_states() -> List[OperatingState]:
    return [
        OperatingState("Texas", "TX", "Texas", "Novitas (JH)", "non-expansion",
                       "Commercial-metro / high-uninsured",
                       "Home market; metros have local groups, rural West/South TX is tele-served."),
        OperatingState("Oklahoma", "OK", "Southern Plains", "Novitas (JH)", "expanded (2021)",
                       "Rural / Medicare-aging",
                       "Heavy map cluster; rural CAHs that can't staff on-site — core tele demand."),
        OperatingState("Kansas", "KS", "Southern Plains", "WPS (J5)", "non-expansion",
                       "Rural / Medicare-aging / high-uninsured",
                       "Heavy cluster; frontier counties, no local radiologist depth."),
        OperatingState("Nebraska", "NE", "Southern Plains", "WPS (J5)", "expanded (2020)",
                       "Rural / commercial-ag",
                       "Sparse rural hospitals; tele-dependent."),
        OperatingState("New Mexico", "NM", "Southern Plains", "Novitas (JH)", "expanded (2014)",
                       "Rural / Medicaid-heavy / high-uninsured",
                       "Frontier; severe radiologist scarcity."),
        OperatingState("Minnesota", "MN", "Upper Midwest", "NGS (J6)", "expanded (2014)",
                       "Commercial-strong / low-uninsured",
                       "Heavy cluster (Sioux Falls catchment); strong commercial, dense CAH network."),
        OperatingState("South Dakota", "SD", "Upper Midwest", "Noridian (JF)", "expanded (2023)",
                       "Rural / commercial / low-uninsured",
                       "Heavy cluster; large rural geography, regional-hub reading."),
        OperatingState("North Dakota", "ND", "Upper Midwest", "Noridian (JF)", "expanded (2014)",
                       "Rural / commercial / low-uninsured",
                       "Frontier; tele backbone over sparse population."),
        OperatingState("Wisconsin", "WI", "Upper Midwest", "NGS (J6)", "non-expansion (≤100% FPL)",
                       "Commercial / low-uninsured",
                       "Edge of the Upper-Midwest cluster."),
        OperatingState("Alabama", "AL", "Southeast", "Palmetto (JJ)", "non-expansion",
                       "Rural / high-uninsured / Medicaid-gap",
                       "Heavy cluster; most rural-hospital distress — strong tele demand."),
        OperatingState("Georgia", "GA", "Southeast", "Palmetto (JJ)", "non-expansion",
                       "Mixed metro/rural / high-uninsured",
                       "Heavy cluster; Atlanta metro + a deep rural tail."),
        OperatingState("Tennessee", "TN", "Southeast", "Palmetto (JJ)", "non-expansion",
                       "Rural / high-uninsured",
                       "Rural-hospital closures elevate tele reliance."),
        OperatingState("North Carolina", "NC", "Southeast", "Palmetto (JM)", "expanded (2023)",
                       "Mixed / improving coverage",
                       "Cluster; recent Medicaid expansion lifts the payer floor."),
        OperatingState("Kentucky", "KY", "Southeast", "CGS (J15)", "expanded (2014)",
                       "Rural / Medicaid-heavy",
                       "Appalachian rural reads; CGS issues the breast/cardiac-CT LCDs."),
        OperatingState("Mississippi", "MS", "Southeast", "Novitas (JH)", "non-expansion",
                       "Rural / highest-uninsured / Medicaid-gap",
                       "Poorest payer mix; deepest rural-coverage need."),
        OperatingState("Florida", "FL", "Florida", "First Coast (JN)", "non-expansion",
                       "Senior-heavy / high-uninsured",
                       "North-FL edge of the map; oldest-skew = high imaging demand."),
    ]


# Payer mix by operating region (illustrative, ACS-anchored shares that sum to
# 100). The regional spread is the point: Upper-Midwest is commercial-rich and
# low-uninsured; the Southeast and Texas carry the Medicaid-gap + uninsured drag.
def _build_region_payer_mix() -> List[RegionPayerMix]:
    return [
        RegionPayerMix("Texas", "TX", 45.0, 33.0, 13.0, 9.0,
                       "Commercial-strong metros vs a high-uninsured (~18-20%) non-expansion rural tail."),
        RegionPayerMix("Southern Plains", "OK · KS · NE · NM", 42.0, 36.0, 13.0, 9.0,
                       "Aging, rural, Medicare-heavy; mixed expansion (NE/NM/OK yes, KS no)."),
        RegionPayerMix("Upper Midwest / Dakotas", "MN · SD · ND · WI", 50.0, 33.0, 11.0, 6.0,
                       "Best payer mix in the footprint — commercial-rich, low-uninsured, dense CAH network; all expanded."),
        RegionPayerMix("Southeast", "AL · GA · TN · NC · KY · MS", 43.0, 33.0, 14.0, 10.0,
                       "Highest uninsured + Medicaid-gap (most non-expansion); the deepest rural-hospital distress."),
        RegionPayerMix("Florida", "FL (north)", 40.0, 38.0, 13.0, 9.0,
                       "Senior-heavy (highest Medicare share) non-expansion; oldest-skew lifts imaging demand."),
    ]


# Teleradiology trends — general market + the structural nighthawk weakness that
# an integrated on-site+tele hybrid (with the hospital's systems & priors) beats.
def _build_teleradiology_trends() -> List[TeleradiologyTrend]:
    return [
        TeleradiologyTrend(
            "Shortage-driven demand",
            "Hospitals lack the bandwidth to staff their own radiology groups, so they reach out to tele providers — the radiologist shortage IS the demand engine.",
            "Tailwind for any outsourced platform; the bigger the shortage, the more reads route out."),
        TeleradiologyTrend(
            "The nighthawk priors / context gap",
            "An off-hours nighthawk reader often lacks access to the patient's prior exams & context. The classic case: a 12-hour follow-up head CT comes back as just 'head bleed' — no quantification, no better/worse-than-before — so the day team must RE-READ it.",
            "The structural weakness of pure-tele — and exactly where an on-site+tele hybrid WIRED INTO the hospital's systems & priors wins on quality and avoids the reread."),
        TeleradiologyTrend(
            "Prelim → final shift",
            "Nighthawk reads are moving from preliminary to final reads as tele matures and SLAs tighten.",
            "Raises the bar on reader quality + system integration; favors integrated platforms."),
        TeleradiologyTrend(
            "Subspecialty routing",
            "Tele lets a rural hospital reach neuro/MSK/breast/peds subspecialists it could never staff locally.",
            "A core hybrid value prop — subspecialty depth the local group can't match."),
        TeleradiologyTrend(
            "AI on the reporting side",
            "Auto-impression / report-drafting AI (Rad AI, Nuance PowerScribe) is cutting read time per patient — the real, proven AI ROI, easing the shortage.",
            "Lifts reads/radiologist for the platform; a productivity lever, not a substitute."),
        TeleradiologyTrend(
            "PACS / cloud fragmentation",
            "Radiology runs on archaic, on-prem, non-connected systems — there is no cloud radiology platform at scale, and no common US patient identifier to string priors together.",
            "The binding workflow barrier; whoever solves cross-site priors & cloud reads captures durable advantage."),
        TeleradiologyTrend(
            "Consolidation",
            "A dominant national consolidator (owns the largest teleradiology arm) anchors the market; the US teleradiology market is ~$0.85B (2022) → ~$2.1B (2030), ~12% CAGR.",
            "Scale compresses per-read cost; the local-group share-donor keeps shrinking."),
    ]


# AI workflow reality — public industry knowledge on where AI actually helps the
# radiology workflow (the detection-vs-reporting split, the widget/noise problem,
# the cloud/priors barrier, the enterprise pivot, foundation-model FDA gaps).
def _build_ai_workflow() -> List[AIWorkflowReality]:
    return [
        AIWorkflowReality(
            "Two AI worlds: the image vs the report",
            "AI splits into (1) detection/triage on the image and (2) automating everything that wraps the read — patient context + the report. The value is migrating to (2).",
            "Detection started the market (Viz stroke, Aidoc ICH); reporting (Rad AI, PowerScribe) is where time is actually saved."),
        AIWorkflowReality(
            "Detection ROI has underwhelmed",
            "A suspected-stroke patient is already labeled 'stroke?' — so a triage flag doesn't make the radiologist read faster. Disease-detection/triage time-savings have been hard to prove.",
            "Why pure-detection algorithm shops struggled to justify their value to the radiologist."),
        AIWorkflowReality(
            "Reporting ROI is real",
            "Auto-impression / report drafting saves significant time on EVERY patient — the radiologist's mind is doing 'summarize this' on every read, and AI does part of it.",
            "The proven productivity win; directly eases the radiologist shortage & volume load."),
        AIWorkflowReality(
            "The widget / noise problem",
            "Because radiology systems are archaic & non-connected, AI bolts on as a desktop widget. Stacking algorithms (one vendor reached ~17 clearances) adds irrelevant findings — an old vertebral fracture on a stroke case — i.e. noise, not value.",
            "More algorithms ≠ more value without workflow integration; alert fatigue is real."),
        AIWorkflowReality(
            "The priors / cloud barrier",
            "No cloud radiology platform at scale and no common US patient identifier means you can't string a patient's imaging history together — radiology still hands out CDs ('the blockbuster era'). Tying priors together is what the radiologist actually needs.",
            "The real blocker is infrastructure (cloud migration), not model capability."),
        AIWorkflowReality(
            "The enterprise pivot",
            "AI vendors moved from selling the radiologist ('save time/quality' — unproven) to the C-suite (CIO/CDO): 'help you treat & capture more patients = more revenue'. The radiology-only TAM didn't support venture valuations.",
            "Enterprise buyers see less of the radiology-workflow barriers; deals get bigger but ROI gets fuzzier."),
        AIWorkflowReality(
            "Foundation models — promise vs productization",
            "Excitement around every-disease foundation models, but the FDA pathway for approving hundreds of algorithms at once is unclear (a notable 2024-25 setback), and the models sit on top of the same un-integrated systems.",
            "Capability isn't the gate — regulatory clarity + cloud/workflow integration is."),
        AIWorkflowReality(
            "Radiologists are not replaced — the role evolves",
            "AI will 100% remain human-in-the-loop for nearly everything; 'not reading every case' begins narrowly (e.g., chest X-ray). The radiologist stays central for context and what-happens-next.",
            "The scarcity thesis holds; AI re-prices the bottleneck (productivity) rather than removing it."),
    ]


# The four service lines (from the public site), mapped to competitive edge.
def _build_service_lines() -> List[ServiceLine]:
    return [
        ServiceLine("On-site services",
                    "Contracted radiologists read on premise — faster results, procedure coverage, supervision.",
                    "The part pure-tele can't do; satisfies on-premise-required reads + IR + fluoro supervision."),
        ServiceLine("Teleradiology",
                    "Contracted radiologists deliver expert reads & consults remotely, 24/7/365.",
                    "Scales reading capacity nationally; the labor-arbitrage + after-hours layer."),
        ServiceLine("Diagnostic radiology",
                    "Advanced imaging across all subspecialties for precise diagnosis & treatment planning.",
                    "Subspecialty depth a rural local group can't staff — the switching trigger answered."),
        ServiceLine("Interventional radiology",
                    "Minimally invasive, image-guided procedures — precise treatment, faster recovery.",
                    "Requires on-site presence; the highest-acuity line tele-only competitors structurally can't serve."),
    ]

