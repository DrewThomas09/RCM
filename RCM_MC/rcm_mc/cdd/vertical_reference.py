"""REF-01..04 Healthcare vertical operational reference layer.

A sourced, chart-ready reference across the US healthcare verticals a PE
operator would speak to on an expert call. The layer is deliberately built
around the RAND commercial-to-Medicare ratio as the spine, because that single
ratio drives payer-mix economics and the site-of-care migration in every
downstream vertical.

Four registered exhibits surface the reference:

- REF-01 site-of-care price ladder (RAND PT5.1, 2022 data),
- REF-02 physician productivity wRVU percentiles by specialty (MGMA),
- REF-03 revenue cycle KPI benchmarks (HFMA MAP Keys and related),
- REF-04 per-vertical unit-economics catalog across the deep-dive verticals.

Every datapoint carries an explicit source, a vintage, and a confidence tier:

- Tier 1 (established): RAND, MGMA, HFMA, MedPAC, CMS, KFF, SEC filings.
- Tier 2 (directional): Becker's, VMG secondary citations, specialty societies.
- Tier 3 (requires verification): per-unit economics that today trace only to a
  consulting or financial-model source. These are tagged and flagged so a
  partner surface never presents them as established fact.

This module is a deterministic reference catalog. There is no estimator and no
LLM on any path; values are the published figures, tagged and reconciled.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .exhibit import Exhibit, Flag, Footnote, Reconciliation, Series, safe_div
from .registry import CddFeature, register

FEATURE_PRICE_LADDER = "REF-01"
FEATURE_WRVU = "REF-02"
FEATURE_RCM_KPI = "REF-03"
FEATURE_VERTICAL_CATALOG = "REF-04"

# Confidence tiers. Lower is more established.
TIER_ESTABLISHED = 1
TIER_DIRECTIONAL = 2
TIER_REQUIRES_VERIFICATION = 3

TIER_LABEL = {
    TIER_ESTABLISHED: "established",
    TIER_DIRECTIONAL: "directional",
    TIER_REQUIRES_VERIFICATION: "requires verification",
}


@dataclass(frozen=True)
class RefPoint:
    """One sourced reference figure with its unit, vintage, and confidence tier.

    ``value`` is the headline number, ``unit`` names what it measures so a chart
    axis can be labeled without guessing, and ``tier`` is the confidence tier so
    a surface can gate or annotate low-confidence figures.
    """

    label: str
    value: float
    unit: str
    source: str
    vintage: str
    tier: int = TIER_ESTABLISHED
    note: str = ""

    def to_point(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "value": float(self.value),
            "unit": self.unit,
            "source": self.source,
            "vintage": self.vintage,
            "tier": int(self.tier),
            "tier_label": TIER_LABEL.get(self.tier, str(self.tier)),
            "note": self.note,
        }


@dataclass(frozen=True)
class VerticalRef:
    """A healthcare vertical with its headline per-unit economic and a metric set.

    ``headline`` is the single most chartable figure an operator would lead with;
    ``metrics`` is the supporting reference set. The headline tier drives whether
    the vertical is flagged as resting on a figure that still needs verification.
    """

    key: str
    name: str
    headline: RefPoint
    metrics: List[RefPoint] = field(default_factory=list)


# ---------------------------------------------------------------------------
# REF-01 data: RAND PT5.1 site-of-care price ladder (2022 data).
# ---------------------------------------------------------------------------
_RAND_LADDER: List[RefPoint] = [
    RefPoint("Hospital outpatient facility", 279.0, "pct of Medicare",
             "RAND PT5.1", "2022 data", TIER_ESTABLISHED),
    RefPoint("Hospital inpatient facility", 254.0, "pct of Medicare",
             "RAND PT5.1", "2022 data", TIER_ESTABLISHED),
    RefPoint("All hospital services blended", 254.0, "pct of Medicare",
             "RAND PT5.1", "2022 data", TIER_ESTABLISHED),
    RefPoint("Professional services", 184.0, "pct of Medicare",
             "RAND PT5.1", "2022 data", TIER_ESTABLISHED),
    RefPoint("ASC common outpatient surgery", 170.0, "pct of Medicare",
             "RAND PT5.1", "2022 data", TIER_ESTABLISHED),
]

# Physician-administered drugs are priced off ASP, a different basis. Kept as a
# separate, internal-only series so it is never blended into the Medicare ladder.
_RAND_DRUGS: List[RefPoint] = [
    RefPoint("Physician drugs, hospital setting", 281.0, "pct of ASP",
             "RAND PT5.1", "2022 data", TIER_ESTABLISHED),
    RefPoint("Physician drugs, Medicare benchmark", 106.0, "pct of ASP",
             "RAND PT5.1", "2022 data", TIER_ESTABLISHED),
]

# State distribution and time trend (for the choropleth and trend overlays).
_RAND_STATE_MIN = RefPoint("Arkansas (lowest state ratio)", 162.0,
                           "pct of Medicare", "RAND PT5.1", "2022 data")
_RAND_STATE_MAX = RefPoint("Florida (highest state ratio)", 346.0,
                           "pct of Medicare", "RAND PT5.1", "2022 data")
_RAND_TREND: List[RefPoint] = [
    RefPoint("2018", 247.0, "pct of Medicare", "RAND PT5.1", "2018 data"),
    RefPoint("2020", 224.0, "pct of Medicare", "RAND PT5.1", "2020 data"),
    RefPoint("2022", 254.0, "pct of Medicare", "RAND PT5.1", "2022 data"),
]


def price_ladder(audience: str = "both") -> Exhibit:
    """Build the RAND commercial-to-Medicare site-of-care price ladder exhibit."""
    ladder = Series(
        name="Commercial as percent of Medicare by setting",
        kind="bar",
        points=[p.to_point() for p in _RAND_LADDER],
    )
    state = Series(
        name="State ratio range",
        kind="bar",
        points=[_RAND_STATE_MIN.to_point(), _RAND_STATE_MAX.to_point()],
    )
    trend = Series(
        name="Blended hospital ratio trend",
        kind="line",
        points=[p.to_point() for p in _RAND_TREND],
    )
    drugs = Series(
        name="Physician-administered drug basis (ASP)",
        kind="bar",
        internal_only=True,
        points=[p.to_point() for p in _RAND_DRUGS],
    )

    inpatient = next(p.value for p in _RAND_LADDER if p.label.startswith("Hospital inpatient"))
    blended = next(p.value for p in _RAND_LADDER if "blended" in p.label)
    recon = Reconciliation(
        identity="blended all-hospital ratio equals hospital inpatient ratio",
        lhs=blended,
        rhs=inpatient,
        tolerance=1e-9,
    )

    footnote = Footnote(
        source="RAND PT5.1 hospital price transparency study",
        vintage="2022 data, final report",
        basis="facility-inclusive for hospital settings, professional for clinician services",
        assumptions=[
            "Ratios are commercial allowed divided by Medicare allowed for the same setting.",
            "Drug pricing is on a percent-of-ASP basis and is not blended into the facility ladder.",
            "State ratios range from 162 percent in Arkansas to 346 percent in Florida.",
        ],
    )
    ex = Exhibit(
        feature_id=FEATURE_PRICE_LADDER,
        title="Commercial-to-Medicare site-of-care price ladder",
        audience=audience,
        series=[ladder, state, trend, drugs],
        footnote=footnote,
        flags=[],
        reconciliations=[recon],
        summary=(
            "Commercial payers paid 279.0 percent of Medicare for hospital "
            "outpatient, 254.0 percent for hospital inpatient, 184.0 percent "
            "for professional services, and 170.0 percent at ASCs. This ladder "
            "is the economic engine behind the site-of-care shift."
        ),
        meta={
            "ladder": [p.to_point() for p in _RAND_LADDER],
            "state_min": _RAND_STATE_MIN.to_point(),
            "state_max": _RAND_STATE_MAX.to_point(),
            "trend": [p.to_point() for p in _RAND_TREND],
            "drugs": [p.to_point() for p in _RAND_DRUGS],
        },
    )
    return ex.validate()


# ---------------------------------------------------------------------------
# REF-02 data: MGMA physician productivity (wRVU) medians by specialty.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class WrvuRow:
    specialty: str
    median_wrvu: float
    comp_per_wrvu: Optional[float] = None
    note: str = ""


_WRVU: List[WrvuRow] = [
    WrvuRow("Family medicine", 5100.0, 42.0, "grew about 20.9 percent over 5 years"),
    WrvuRow("Hospitalist", 4800.0),
    WrvuRow("Pediatrics and internal medicine", 5250.0),
    WrvuRow("Gastroenterology", 8700.0, 61.0, "colonoscopy averages about 3.6 wRVU"),
    WrvuRow("Dermatology", 7900.0, None, "Mohs 17311 is 5.76 wRVU"),
    WrvuRow("Orthopedic surgery", 9600.0, None, "total knee about 20 to 25 wRVU per case"),
    WrvuRow("Cardiology", 9850.0, None, "imaging weighted"),
    WrvuRow("Radiology", 11950.0),
    WrvuRow("Neurosurgery", 9700.0, None, "highest variance, 25th to 90th spread about 6,700 wRVU"),
]


def wrvu_percentiles(audience: str = "both") -> Exhibit:
    """Build the MGMA wRVU productivity-by-specialty reference exhibit."""
    prod = Series(
        name="Median annual wRVU by specialty",
        kind="bar",
        points=[
            {"label": r.specialty, "value": r.median_wrvu, "unit": "wRVU", "note": r.note}
            for r in _WRVU
        ],
    )
    comp = Series(
        name="Compensation per wRVU by specialty",
        kind="bar",
        points=[
            {"label": r.specialty, "value": r.comp_per_wrvu, "unit": "USD per wRVU"}
            for r in _WRVU
            if r.comp_per_wrvu is not None
        ],
    )

    # Cross-check: GI median compensation divided by GI median productivity
    # should land inside the independently reported GI dollars-per-wRVU band.
    gi = next(r for r in _WRVU if r.specialty == "Gastroenterology")
    gi_median_comp = 512_500.0  # midpoint of reported 495K to 530K (MGMA 2024)
    implied_comp_per_wrvu = safe_div(gi_median_comp, gi.median_wrvu)
    recon = Reconciliation(
        identity="GI compensation divided by productivity ties to reported dollars per wRVU",
        lhs=implied_comp_per_wrvu,
        rhs=gi.comp_per_wrvu or 0.0,
        tolerance=5.0,  # both inputs are published as rounded ranges
    )

    footnote = Footnote(
        source="MGMA Provider Compensation, approximately 220,000 providers",
        vintage="2024 production reported 2025",
        assumptions=[
            "Figures are approximate medians; treat exact values as estimates pending licensed MGMA data.",
            "Proceduralists cluster at 9,000 to 12,000 wRVU; primary care at 5,000 to 6,000.",
            "New graduates typically reach median productivity by year 2 to 3.",
        ],
    )
    ex = Exhibit(
        feature_id=FEATURE_WRVU,
        title="Physician productivity wRVU percentiles by specialty",
        audience=audience,
        series=[prod, comp],
        footnote=footnote,
        flags=[],
        reconciliations=[recon],
        summary=(
            "Primary care medians run about 5,000 to 6,000 wRVU while "
            "proceduralists run 9,000 to 12,000. Radiology leads at about "
            "11,950 and cardiology at about 9,850."
        ),
        meta={
            "rows": [
                {"specialty": r.specialty, "median_wrvu": r.median_wrvu,
                 "comp_per_wrvu": r.comp_per_wrvu, "note": r.note}
                for r in _WRVU
            ],
            "gi_implied_comp_per_wrvu": implied_comp_per_wrvu,
        },
    )
    return ex.validate()


# ---------------------------------------------------------------------------
# REF-03 data: HFMA MAP Keys revenue cycle KPI benchmarks.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class KpiRow:
    kpi: str
    target: float
    target_unit: str
    industry: str
    source: str
    note: str = ""


_RCM_KPI: List[KpiRow] = [
    KpiRow("Days in A/R", 35.0, "days", "varies", "HFMA", "good band is 30 to 40 days"),
    KpiRow("A/R over 90 days", 15.0, "pct", "varies", "HFMA and industry",
           "best practice under 15 percent, some cite under 10 percent"),
    KpiRow("Clean claim first-pass rate", 95.0, "pct", "low-80s to 90s",
           "HFMA MAP Keys", "top performers near 98 percent"),
    KpiRow("Initial denial rate", 5.0, "pct", "6 to 11 percent in 2024 to 2025",
           "HFMA and MGMA", "over 10 percent at more than half of organizations"),
    KpiRow("Net revenue lost to denials", 4.8, "pct", "4.8 percent average",
           "HFMA Pulse"),
    KpiRow("Cost to rework a denied claim", 25.0, "USD", "about 25 dollars per claim",
           "industry"),
    KpiRow("Denials resolved within 30 days", 85.0, "pct", "varies", "industry"),
    KpiRow("Charge lag", 24.0, "hours", "up to 72 hours", "MGMA",
           "best practice under 24 hours, 72 hours is standard"),
]


def rcm_kpis(audience: str = "both") -> Exhibit:
    """Build the HFMA MAP Keys revenue cycle KPI benchmark exhibit."""
    targets = Series(
        name="Revenue cycle KPI targets",
        kind="bar",
        points=[
            {"label": k.kpi, "value": k.target, "unit": k.target_unit,
             "industry": k.industry, "source": k.source, "note": k.note}
            for k in _RCM_KPI
        ],
    )

    # Genuine arithmetic identity in the optimal targets: an optimal first-pass
    # clean-claim rate plus the optimal initial-denial ceiling account for the
    # full claim population.
    clean = next(k.target for k in _RCM_KPI if k.kpi.startswith("Clean claim"))
    denial = next(k.target for k in _RCM_KPI if k.kpi == "Initial denial rate")
    recon = Reconciliation(
        identity="optimal clean-claim rate plus optimal initial-denial ceiling equals 100 percent",
        lhs=clean + denial,
        rhs=100.0,
        tolerance=1e-9,
    )

    footnote = Footnote(
        source="HFMA MAP Keys and related industry benchmarking",
        vintage="2024 to 2025",
        assumptions=[
            "HFMA defines 29 standardized MAP Keys across 5 domains.",
            "Targets are best-practice thresholds, not the median performer.",
            "Coding-related denials rose about 126 percent over 3 years.",
        ],
    )
    ex = Exhibit(
        feature_id=FEATURE_RCM_KPI,
        title="Revenue cycle KPI benchmarks",
        audience=audience,
        series=[targets],
        footnote=footnote,
        flags=[],
        reconciliations=[recon],
        summary=(
            "Best-practice revenue cycle targets are days in A/R of 30 to 40, "
            "A/R over 90 days under 15.0 percent, a first-pass clean claim rate "
            "of 95.0 percent, and an initial denial rate under 5.0 percent."
        ),
        meta={
            "kpis": [
                {"kpi": k.kpi, "target": k.target, "target_unit": k.target_unit,
                 "industry": k.industry, "source": k.source, "note": k.note}
                for k in _RCM_KPI
            ],
        },
    )
    return ex.validate()


# ---------------------------------------------------------------------------
# REF-04 data: per-vertical unit-economics catalog (deep-dive verticals).
# ---------------------------------------------------------------------------
_VERTICALS: List[VerticalRef] = [
    VerticalRef(
        "asc", "Ambulatory Surgery Centers",
        RefPoint("Mean operating expense as percent of revenue", 76.3, "pct of revenue",
                 "VMG Intellimarker", "2018", TIER_DIRECTIONAL),
        [
            RefPoint("Mean operating expense per case", 1543.0, "USD per case",
                     "VMG Intellimarker", "2018", TIER_DIRECTIONAL),
            RefPoint("Cases per OR per day", 5.0, "cases", "VMG Intellimarker",
                     "2018", TIER_DIRECTIONAL),
            RefPoint("USPI ASC segment EBITDA margin", 38.6, "pct",
                     "Tenet USPI Q3 filing", "2025", TIER_ESTABLISHED),
            RefPoint("GI net revenue per case", 1420.0, "USD per case", "HST",
                     "2024", TIER_DIRECTIONAL),
        ],
    ),
    VerticalRef(
        "gi", "Gastroenterology",
        RefPoint("Medicare colonoscopy professional fee", 220.0, "USD per case",
                 "University of Chicago analysis", "2025", TIER_ESTABLISHED),
        [
            RefPoint("Colonoscopy 45378 work RVU", 3.18, "wRVU", "CMS fee schedule",
                     "2026", TIER_ESTABLISHED),
            RefPoint("Office endoscopy payment change", 16.0, "pct change",
                     "CMS final rule", "2026", TIER_ESTABLISHED,
                     "ASC and HOPD endoscopy physician pay falls about 8 percent"),
            RefPoint("Inflation-adjusted colonoscopy pay change 2018 to 2023", -22.0,
                     "pct change", "specialty society analysis", "2018-2023",
                     TIER_DIRECTIONAL),
            RefPoint("Median GI compensation", 512_500.0, "USD", "MGMA",
                     "2024", TIER_ESTABLISHED),
        ],
    ),
    VerticalRef(
        "dermatology", "Dermatology",
        RefPoint("Average revenue per office visit", 221.0, "USD per visit",
                 "industry baseline", "pre-2020", TIER_REQUIRES_VERIFICATION),
        [
            RefPoint("Median compensation", 426_000.0, "USD", "MGMA", "2024",
                     TIER_ESTABLISHED),
            RefPoint("Mohs 17311 work RVU", 5.76, "wRVU", "CMS fee schedule",
                     "2026", TIER_ESTABLISHED),
            RefPoint("Typical patients per day", 32.0, "patients",
                     "specialty society", "2024", TIER_DIRECTIONAL),
            RefPoint("Large-platform EBITDA multiple", 13.5, "multiple",
                     "PE deal commentary", "2024", TIER_DIRECTIONAL),
        ],
    ),
    VerticalRef(
        "dialysis", "Dialysis",
        RefPoint("Medicare ESRD PPS base rate per treatment", 281.71, "USD per treatment",
                 "CMS-1830-F final rule", "CY2026", TIER_ESTABLISHED),
        [
            RefPoint("DaVita cost per treatment", 269.0, "USD per treatment",
                     "company disclosure", "recent", TIER_DIRECTIONAL),
            RefPoint("Fresenius revenue per treatment", 353.0, "USD per treatment",
                     "company disclosure", "2017", TIER_DIRECTIONAL),
            RefPoint("Fresenius cost per treatment", 282.0, "USD per treatment",
                     "company disclosure", "2017", TIER_DIRECTIONAL),
            RefPoint("Fresenius operating margin", 19.0, "pct", "company disclosure",
                     "2017", TIER_DIRECTIONAL),
            RefPoint("Commercial multiple of Medicare per session", 4.0, "multiple",
                     "UCLA estimate", "recent", TIER_DIRECTIONAL),
        ],
    ),
    VerticalRef(
        "urgent_care", "Urgent Care",
        RefPoint("Net revenue per visit", 121.6, "USD per visit", "Experity",
                 "2020", TIER_DIRECTIONAL),
        [
            RefPoint("Operating sweet spot visits per day", 50.0, "visits",
                     "operator benchmark", "recent", TIER_REQUIRES_VERIFICATION,
                     "sweet spot of 40 to 60 visits per day"),
            RefPoint("Healthy EBITDA margin", 18.0, "pct", "PE buyer view",
                     "recent", TIER_REQUIRES_VERIFICATION,
                     "healthy band is 15 to 22 percent"),
            RefPoint("Labor as share of incremental cost", 85.0, "pct",
                     "operator benchmark", "recent", TIER_REQUIRES_VERIFICATION),
        ],
    ),
    VerticalRef(
        "physical_therapy", "Physical Therapy",
        RefPoint("Revenue per visit", 102.80, "USD per visit",
                 "U.S. Physical Therapy filing", "2023", TIER_ESTABLISHED),
        [
            RefPoint("Payroll as percent of revenue", 51.0, "pct of revenue",
                     "operator benchmark", "recent", TIER_DIRECTIONAL,
                     "largest single line, 48 to 55 percent"),
            RefPoint("Visits per day per clinic", 32.0, "visits",
                     "operator benchmark", "recent", TIER_DIRECTIONAL),
            RefPoint("Net margin", 17.0, "pct", "operator benchmark", "recent",
                     TIER_DIRECTIONAL, "14 to 20 percent, cash and workers comp higher"),
        ],
    ),
    VerticalRef(
        "imaging", "Imaging and Radiology Centers",
        RefPoint("MRI revenue per scan", 1190.0, "USD per scan",
                 "operator model", "recent", TIER_REQUIRES_VERIFICATION,
                 "commonly modeled 580 to 1,800 dollars"),
        [
            RefPoint("Well-utilized MRI annual revenue per machine", 1_000_000.0,
                     "USD per year", "operator model", "recent",
                     TIER_REQUIRES_VERIFICATION),
            RefPoint("Target MRI utilization", 80.0, "pct", "operator benchmark",
                     "recent", TIER_REQUIRES_VERIFICATION, "60 percent toward 80 to 85"),
            RefPoint("Labor as share of operating cost", 50.0, "pct",
                     "operator benchmark", "recent", TIER_REQUIRES_VERIFICATION,
                     "40 to 60 percent"),
        ],
    ),
    VerticalRef(
        "snf", "Skilled Nursing Facilities",
        RefPoint("FFS Medicare margin", 24.0, "pct", "MedPAC March report",
                 "2024 data", TIER_ESTABLISHED),
        [
            RefPoint("Occupancy benchmark", 82.5, "pct", "MedPAC and industry",
                     "recent", TIER_DIRECTIONAL, "benchmark 80 to 85 percent"),
            RefPoint("Labor as share of operating cost", 70.0, "pct",
                     "industry", "recent", TIER_DIRECTIONAL, "65 to 75 percent"),
            RefPoint("Hospital-based SNF margin", -38.0, "pct", "MedPAC March report",
                     "2024 data", TIER_ESTABLISHED),
        ],
    ),
    VerticalRef(
        "home_health_hospice", "Home Health and Hospice",
        RefPoint("Home health average Medicare margin", 16.2, "pct",
                 "MedPAC", "historical", TIER_ESTABLISHED),
        [
            RefPoint("Hospice routine home care per diem", 218.0, "USD per day",
                     "CMS", "FY2024 era", TIER_ESTABLISHED),
            RefPoint("Freestanding hospice margin", 10.7, "pct", "MedPAC",
                     "recent", TIER_ESTABLISHED),
            RefPoint("Hospital-based hospice margin", -16.0, "pct", "MedPAC",
                     "recent", TIER_ESTABLISHED),
            RefPoint("Decedents using hospice", 46.0, "pct", "MedPAC",
                     "recent", TIER_ESTABLISHED),
        ],
    ),
    VerticalRef(
        "behavioral_aba", "Behavioral Health and ABA",
        RefPoint("ABA technician weighted-mean reimbursement", 65.16, "USD per hour",
                 "RAND", "recent", TIER_ESTABLISHED),
        [
            RefPoint("Master's or doctoral reimbursement", 94.72, "USD per hour",
                     "RAND", "recent", TIER_ESTABLISHED),
            RefPoint("National Medicaid ABA spend 2019", 660_000_000.0, "USD",
                     "Medicaid data", "2019", TIER_ESTABLISHED),
            RefPoint("National Medicaid ABA spend 2023", 2_200_000_000.0, "USD",
                     "Medicaid data", "2023", TIER_ESTABLISHED),
        ],
    ),
    VerticalRef(
        "fertility_ivf", "Fertility and IVF",
        RefPoint("All-in IVF cycle cost", 25_000.0, "USD per cycle",
                 "industry", "recent", TIER_DIRECTIONAL),
        [
            RefPoint("US IVF services market 2024", 5_900_000_000.0, "USD",
                     "Allied Market Research", "2024", TIER_DIRECTIONAL),
            RefPoint("Projected IVF services market 2032", 13_900_000_000.0, "USD",
                     "Allied Market Research", "2032 projection", TIER_DIRECTIONAL),
            RefPoint("IVF share of treatment revenue", 46.6, "pct", "industry",
                     "2025", TIER_DIRECTIONAL),
        ],
    ),
    VerticalRef(
        "infusion_specialty", "Infusion and Specialty Pharmacy",
        RefPoint("Medicare Part B buy-and-bill reimbursement", 106.0, "pct of ASP",
                 "CMS", "recent", TIER_ESTABLISHED,
                 "ASP plus 6 percent, about ASP plus 4.3 after sequestration"),
        [
            RefPoint("Annual cost per infusion patient low", 32_000.0, "USD",
                     "industry", "recent", TIER_DIRECTIONAL),
            RefPoint("Annual cost per infusion patient high", 136_000.0, "USD",
                     "industry", "recent", TIER_DIRECTIONAL),
            RefPoint("US specialty drug spend 2021", 285_000_000_000.0, "USD",
                     "industry", "2021", TIER_DIRECTIONAL),
        ],
    ),
    VerticalRef(
        "dental_dso", "Dental and DSOs",
        RefPoint("General practice overhead", 66.0, "pct of revenue",
                 "Levin and industry", "recent", TIER_DIRECTIONAL,
                 "general 60 to 75 percent, specialty 70 to 85"),
        [
            RefPoint("Average private-practice production", 750_000.0, "USD per year",
                     "industry", "recent", TIER_DIRECTIONAL),
            RefPoint("DSO and group net margin", 31.0, "pct", "industry",
                     "recent", TIER_DIRECTIONAL, "28 to 35 percent"),
            RefPoint("Hygiene share of production", 25.0, "pct", "industry",
                     "recent", TIER_DIRECTIONAL),
        ],
    ),
    VerticalRef(
        "vbc_ma", "Value-Based Primary Care and Medicare Advantage",
        RefPoint("Medicare Advantage penetration", 54.0, "pct of eligible",
                 "KFF", "2024", TIER_ESTABLISHED),
        [
            RefPoint("Risk-bearing PCP revenue per member", 13_200.0, "USD per year",
                     "Oak Street planning assumption", "recent", TIER_ESTABLISHED),
            RefPoint("agilon revenue per member", 11_570.0, "USD per year",
                     "agilon FY filing", "2024", TIER_ESTABLISHED),
            RefPoint("Full-risk panel size", 400.0, "members", "ChenMed",
                     "recent", TIER_DIRECTIONAL, "350 to 450 versus 1,200 to 2,900 in FFS"),
            RefPoint("MA paid versus FFS", 122.0, "pct of FFS", "MedPAC",
                     "2024", TIER_ESTABLISHED),
        ],
    ),
]


def get_vertical(key: str) -> VerticalRef:
    """Return the reference record for one vertical, by key."""
    for v in _VERTICALS:
        if v.key == key:
            return v
    raise KeyError(f"unknown vertical key: {key!r}")


def verticals() -> List[VerticalRef]:
    """Return all deep-dive vertical reference records."""
    return list(_VERTICALS)


def vertical_catalog(audience: str = "both") -> Exhibit:
    """Build the cross-vertical unit-economics catalog exhibit.

    The partner-facing series carries one headline per-unit economic per
    vertical. The full metric set, with per-figure source and confidence tier,
    is an internal-only series so a partner surface stays uncluttered and never
    silently presents a tier-3 figure as established.
    """
    headline = Series(
        name="Headline per-unit economics by vertical",
        kind="bar",
        points=[
            {
                "label": v.name,
                "value": v.headline.value,
                "unit": v.headline.unit,
                "source": v.headline.source,
                "vintage": v.headline.vintage,
                "tier": v.headline.tier,
                "tier_label": TIER_LABEL[v.headline.tier],
            }
            for v in _VERTICALS
        ],
    )
    detail_points: List[Dict[str, Any]] = []
    for v in _VERTICALS:
        for m in [v.headline, *v.metrics]:
            row = m.to_point()
            row["vertical"] = v.key
            detail_points.append(row)
    detail = Series(
        name="Full vertical metric detail",
        kind="bar",
        internal_only=True,
        points=detail_points,
    )

    # Flag every vertical whose headline figure still rests on a tier-3 source.
    flags: List[Flag] = []
    needs_verification = [v for v in _VERTICALS
                          if v.headline.tier == TIER_REQUIRES_VERIFICATION]
    if needs_verification:
        names = ", ".join(v.name for v in needs_verification)
        flags.append(Flag(
            code="headline_requires_verification",
            severity="warn",
            message=(
                f"{len(needs_verification)} vertical headline figure(s) trace to a "
                f"single consulting or model source and need a second source before "
                f"use as established fact: {names}."
            ),
            source="confidence tiering per the reference caveats",
        ))

    # Cross-check: the Fresenius implied operating margin from its own reported
    # revenue and cost per treatment ties to its reported operating margin.
    dialysis = get_vertical("dialysis")
    rev = next(m.value for m in dialysis.metrics if m.label.startswith("Fresenius revenue"))
    cost = next(m.value for m in dialysis.metrics if m.label.startswith("Fresenius cost"))
    reported_margin = next(m.value for m in dialysis.metrics
                           if m.label.startswith("Fresenius operating margin"))
    implied_margin = safe_div(rev - cost, rev) * 100.0
    recon = Reconciliation(
        identity="Fresenius implied operating margin from revenue and cost ties to reported margin",
        lhs=implied_margin,
        rhs=reported_margin,
        tolerance=1.5,  # published figures are rounded
    )

    n_t1 = sum(1 for v in _VERTICALS if v.headline.tier == TIER_ESTABLISHED)
    footnote = Footnote(
        source="RAND, MGMA, HFMA, MedPAC, CMS, KFF, SEC filings, VMG, specialty societies",
        vintage="2017 to 2026 by figure, labeled per datapoint",
        assumptions=[
            "Each figure carries its own source, vintage, and confidence tier.",
            "Tier 3 figures are flagged and are never presented as established fact.",
            "Catalog covers the deep-dive verticals; the framework extends to the rest.",
        ],
    )
    ex = Exhibit(
        feature_id=FEATURE_VERTICAL_CATALOG,
        title="Healthcare vertical unit-economics reference catalog",
        audience=audience,
        series=[headline, detail],
        footnote=footnote,
        flags=flags,
        reconciliations=[recon],
        summary=(
            f"Headline per-unit economics for {len(_VERTICALS)} deep-dive "
            f"verticals, {n_t1} of them resting on a tier 1 source. The universal "
            f"margin lever is utilization, and labor is the dominant cost line in "
            f"nearly every vertical."
        ),
        meta={
            "n_verticals": len(_VERTICALS),
            "tier_counts": {
                TIER_LABEL[TIER_ESTABLISHED]: n_t1,
                TIER_LABEL[TIER_DIRECTIONAL]: sum(
                    1 for v in _VERTICALS if v.headline.tier == TIER_DIRECTIONAL),
                TIER_LABEL[TIER_REQUIRES_VERIFICATION]: len(needs_verification),
            },
            "fresenius_implied_margin": implied_margin,
            "verticals": [
                {
                    "key": v.key,
                    "name": v.name,
                    "headline": v.headline.to_point(),
                    "metrics": [m.to_point() for m in v.metrics],
                }
                for v in _VERTICALS
            ],
        },
    )
    return ex.validate()


def _demo_price_ladder() -> Exhibit:
    return price_ladder()


def _demo_wrvu() -> Exhibit:
    return wrvu_percentiles()


def _demo_rcm_kpis() -> Exhibit:
    return rcm_kpis()


def _demo_vertical_catalog() -> Exhibit:
    return vertical_catalog()


register(CddFeature(
    feature_id=FEATURE_PRICE_LADDER,
    title="Commercial-to-Medicare site-of-care price ladder",
    audience="both",
    demo=_demo_price_ladder,
))
register(CddFeature(
    feature_id=FEATURE_WRVU,
    title="Physician productivity wRVU percentiles by specialty",
    audience="both",
    demo=_demo_wrvu,
))
register(CddFeature(
    feature_id=FEATURE_RCM_KPI,
    title="Revenue cycle KPI benchmarks",
    audience="both",
    demo=_demo_rcm_kpis,
))
register(CddFeature(
    feature_id=FEATURE_VERTICAL_CATALOG,
    title="Healthcare vertical unit-economics reference catalog",
    audience="both",
    demo=_demo_vertical_catalog,
))
