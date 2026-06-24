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
