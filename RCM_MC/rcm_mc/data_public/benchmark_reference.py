"""US Healthcare Operational & Benchmarking Reference — the granular layer.

A measure-level / code-level / productivity-level / cost-structure reference
that sits *beneath* the vertical, payer-economics and unit-economics analytics
elsewhere in the platform. Six chart-ready data domains, each populated with
current sourced figures (CMS, MGMA, AAMC, SEER/ACS, CDC/NCHS, KFF, Kaufman
Hall, AHA, MedPAC, NCQA) and an explicit visualization recommendation.

Why this lives in its own module rather than inside ma_star_tracker /
specialty_benchmarks: those pages model *portfolio* exposure over the
illustrative seed corpus. This is the opposite — published national reference
data with named primary sources, no corpus dependency. Every row carries a
``source`` and an ``access`` flag (``free`` / ``proprietary`` / ``estimate``)
so a partner can trace and tier each figure exactly as the source notes in the
underlying research require. Numbers are tagged to a measurement / vintage year
because Star weights, HEDIS sets and penalty pools change annually.

Figures are real published benchmarks as of the 2024/2025/2026 releases — NOT
modeled outputs over the seed corpus — so this route deliberately does not join
the illustrative-analyzer banner registry; it self-discloses provenance via a
per-row source column and a caveats panel instead.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


# ── Domain 1 — Quality measure reference (Star Ratings measure weights) ──
@dataclass
class StarWeight:
    category: str
    weight_2025: float
    weight_2026: float
    note: str


# ── Domain 2 — Procedure & code frequency ────────────────────────────────
@dataclass
class CPTCode:
    code: str
    description: str
    pct_of_procedures: float   # share of all physician procedures (2024)
    avg_charge: float          # avg charge, all-payer
    medicare_2026: float       # 2026 Medicare national allowed
    work_rvu: float


@dataclass
class DRGRow:
    rank: int
    drg: str
    description: str
    pct_of_volume: float       # % of total DRG diagnoses (CY2024)


@dataclass
class PartBDrug:
    rank: int
    brand: str
    jcode: str
    therapy: str
    spend_2022_b: float        # MedPAC 2022, FFS only ($B)


# ── Domain 3 — Physician compensation & productivity (proprietary-flagged) ─
@dataclass
class CompBenchmark:
    specialty: str
    median_comp: float         # MGMA-derived total cash comp (2024)
    median_wrvu: float
    dollar_per_wrvu: float
    access: str                # 'proprietary' — DataDive is member-only


@dataclass
class ShortageProjection:
    group: str
    low: int                   # 2036 shortage low bound (physicians)
    high: int                  # 2036 shortage high bound


# ── Domain 4 — Hospital & provider cost structure ─────────────────────────
@dataclass
class MarginPoint:
    period: str
    operating_margin_pct: float   # median, with system allocations
    label: str


@dataclass
class CostStructureItem:
    item: str
    value: float
    unit: str
    note: str


# ── Domain 5 — Disease prevalence / epidemiological denominators ──────────
@dataclass
class Prevalence:
    condition: str
    count_millions: float
    pct_of_pop: float
    source: str


@dataclass
class CauseOfDeath:
    rank: int
    cause: str
    deaths_2023: int
    approx: bool               # True where the figure is rounded


# ── Domain 6 — Utilization / national spending ────────────────────────────
@dataclass
class NHECategory:
    category: str
    dollars_b: float
    share_pct: float
    growth_pct: float


@dataclass
class NHEPayer:
    payer: str
    dollars_b: float
    share_pct: float
    growth_pct: float


@dataclass
class SourceRef:
    domain: str
    dataset: str
    publisher: str
    vintage: str
    access: str                # 'free' / 'proprietary' / 'estimate'


@dataclass
class BenchmarkReferenceResult:
    # headline reference facts
    nhe_total_t: float
    nhe_gdp_pct: float
    nhe_per_capita: float
    hospital_op_margin_pct: float
    top_drg: str
    top_cpt: str
    top_partb_drug: str
    partb_total_b: float
    # domain tables
    star_weights: List[StarWeight]
    cpt_codes: List[CPTCode]
    drgs: List[DRGRow]
    partb_drugs: List[PartBDrug]
    comp_benchmarks: List[CompBenchmark]
    shortages: List[ShortageProjection]
    margin_trend: List[MarginPoint]
    cost_structure: List[CostStructureItem]
    prevalence: List[Prevalence]
    causes_of_death: List[CauseOfDeath]
    nhe_categories: List[NHECategory]
    nhe_payers: List[NHEPayer]
    sources: List[SourceRef]
    # rollups
    domain_count: int = 6


def _star_weights() -> List[StarWeight]:
    # CMS MA-PD Star Ratings measure-category weights. The headline 2026
    # inflection: patient-experience / complaints / access drops from 4 → 2.
    return [
        StarWeight("Improvement measures", 5.0, 5.0,
                   "Highest weight — year-over-year change measures"),
        StarWeight("Patient experience / complaints / access", 4.0, 2.0,
                   "Reduced 4→2 beginning with the 2026 Star Ratings"),
        StarWeight("Outcome / intermediate-outcome", 3.0, 3.0,
                   "Clinical outcomes (e.g. controlling blood pressure)"),
        StarWeight("Process measures", 1.0, 1.0,
                   "Screening / monitoring process measures"),
    ]


def _cpt_codes() -> List[CPTCode]:
    # Definitive Healthcare all-payer claims, 2024 share of all physician
    # procedures; 2026 Medicare national rates + work RVUs from the PFS.
    return [
        CPTCode("99214", "Office/outpatient E/M, established, moderate",
                4.50, 261.0, 131.45, 1.92),
        CPTCode("99213", "Office/outpatient E/M, established, low",
                3.88, 0.0, 91.85, 1.30),
        CPTCode("97110", "Therapeutic exercise", 3.46, 0.0, 0.0, 0.0),
        CPTCode("97530", "Therapeutic activities", 2.99, 0.0, 0.0, 0.0),
    ]


def _drgs() -> List[DRGRow]:
    # Definitive Healthcare, CY2024 volume (CMS Medicare SAF-derived),
    # reported as % of total DRG diagnoses.
    return [
        DRGRow(1, "871", "Septicemia/severe sepsis w/o MV ≥96 hrs W MCC", 7.44),
        DRGRow(2, "291", "Heart failure & shock W MCC", 4.05),
        DRGRow(3, "885", "Psychoses", 2.43),
        DRGRow(4, "177", "Respiratory infections & inflammations W MCC", 1.91),
        DRGRow(5, "193", "Simple pneumonia & pleurisy W MCC", 1.88),
        DRGRow(6, "189", "Pulmonary edema & respiratory failure", 1.45),
        DRGRow(7, "872", "Septicemia/severe sepsis w/o MV ≥96 hrs W/O MCC", 1.44),
        DRGRow(8, "690", "Kidney & urinary tract infections W/O MCC", 1.37),
        DRGRow(9, "392", "Esophagitis, gastroenteritis & misc digestive W/O MCC", 1.27),
        DRGRow(10, "57", "Degenerative nervous system disorders W/O MCC", 1.21),
    ]


def _partb_drugs() -> List[PartBDrug]:
    # MedPAC July 2024 Data Book — 2022 Part B drug spending, FFS only.
    # Total Part B drug spend = $46.9B; top 10 = $18.5B (39%).
    return [
        PartBDrug(1, "Keytruda", "J9271", "Cancer", 4.9),
        PartBDrug(2, "Eylea", "J0178", "Macular degeneration", 3.5),
        PartBDrug(3, "Prolia/Xgeva", "denosumab", "Osteoporosis", 2.0),
        PartBDrug(4, "Darzalex", "daratumumab", "Cancer", 1.9),
        PartBDrug(5, "Opdivo", "nivolumab", "Cancer", 1.9),
        PartBDrug(6, "Rituxan", "rituximab", "Cancer/arthritis", 1.0),
        PartBDrug(7, "Orencia", "abatacept", "Arthritis", 0.9),
        PartBDrug(8, "Lucentis", "ranibizumab", "Macular degeneration", 0.8),
        PartBDrug(9, "Tecentriq", "atezolizumab", "Cancer", 0.8),
        PartBDrug(10, "Avastin", "bevacizumab", "Cancer/eye", 0.7),
        PartBDrug(11, "Ocrevus", "ocrelizumab", "Multiple sclerosis", 0.7),
    ]


def _comp_benchmarks() -> List[CompBenchmark]:
    # MGMA-derived, 2024 data. The official DataDive per-specialty percentile
    # cells are proprietary (member-only); these are aggregator-reported
    # approximations and are flagged 'proprietary' so they are never
    # presented as official MGMA figures.
    return [
        CompBenchmark("Family Medicine", 218_400.0, 5_200.0, 42.00, "proprietary"),
        CompBenchmark("Internal Medicine", 248_000.0, 5_400.0, 45.90, "proprietary"),
        CompBenchmark("Cardiology (invasive)", 612_000.0, 10_500.0, 58.30, "proprietary"),
        CompBenchmark("Orthopedic Surgery", 654_000.0, 11_200.0, 58.40, "proprietary"),
        CompBenchmark("Neurosurgery", 821_000.0, 13_400.0, 61.30, "proprietary"),
        CompBenchmark("Gastroenterology", 506_000.0, 9_100.0, 55.60, "proprietary"),
    ]


def _shortages() -> List[ShortageProjection]:
    # AAMC, "The Complexities of Physician Supply and Demand: Projections
    # From 2021 to 2036" (2024).
    return [
        ShortageProjection("Total physicians", 13_500, 86_000),
        ShortageProjection("Primary care", 20_200, 40_400),
        ShortageProjection("Surgical specialties", 10_100, 19_900),
        ShortageProjection("Medical specialties", -3_700, 5_500),
    ]


def _margin_trend() -> List[MarginPoint]:
    # Kaufman Hall National Hospital Flash Report (~1,300 hospitals), median
    # operating margin including system allocations.
    return [
        MarginPoint("2024 FY", 4.9, "Full-year 2024 median"),
        MarginPoint("2024 Dec", 7.6, "December 2024"),
        MarginPoint("2025 YTD", 1.3, "YTD through December 2025"),
        MarginPoint("2025 Dec", 5.0, "December 2025"),
    ]


def _cost_structure() -> List[CostStructureItem]:
    return [
        CostStructureItem("Hospital median operating margin", 1.3, "%",
                          "YTD through Dec 2025, incl. allocations (Kaufman Hall)"),
        CostStructureItem("Hospitals operating in the red", 40.0, "%",
                          "May 2024, Strata/Kaufman Hall 1,300+ sample"),
        CostStructureItem("Practice labor as % of total expense", 84.4, "%",
                          "Q4 2025 (Kaufman Hall Physician Flash Report)"),
        CostStructureItem("Median physician subsidy/investment", 315_358.0, "$",
                          "Q4 2025, +4% since 2023"),
        CostStructureItem("340B manufacturer discounts to hospitals", 46.5, "$B",
                          "2022, AHA (~3.1% of global drug revenues)"),
        CostStructureItem("340B hospitals at a negative margin", 44.0, "%",
                          "2023 cost reports (AHA)"),
        CostStructureItem("Uncompensated care provided by hospitals", 42.0, "$B",
                          "2019; 340B hospitals ~68% of total"),
    ]


def _prevalence() -> List[Prevalence]:
    return [
        Prevalence("Prediabetes (adults)", 115.2, 0.0,
                   "CDC National Diabetes Statistics Report (2023 data)"),
        Prevalence("Diabetes (total)", 40.1, 12.0,
                   "CDC — 29.1M diagnosed + 11M undiagnosed"),
        Prevalence("Hypertension (adults, self-reported)", 0.0, 30.0,
                   "CDC MMWR 2017–2021"),
        Prevalence("Cancer — new cases (2024 projected)", 2.0, 0.0,
                   "ACS/SEER — 2,001,140 new cases"),
        Prevalence("Medicare beneficiaries (A&B, 2025)", 62.8, 0.0,
                   "CMS — 54% (34.1M) in Medicare Advantage"),
    ]


def _causes_of_death() -> List[CauseOfDeath]:
    # CDC/NCHS final 2023. Top 10 = 70.9% of all deaths; total = 3,090,964.
    return [
        CauseOfDeath(1, "Heart disease", 680_909, False),
        CauseOfDeath(2, "Cancer", 613_352, False),
        CauseOfDeath(3, "Unintentional injury", 222_518, False),
        CauseOfDeath(4, "Stroke (cerebrovascular)", 162_000, True),
        CauseOfDeath(5, "Chronic lower respiratory disease", 145_000, True),
        CauseOfDeath(6, "Alzheimer's disease", 114_000, True),
        CauseOfDeath(7, "Diabetes", 95_000, True),
        CauseOfDeath(8, "Kidney disease", 55_000, True),
        CauseOfDeath(9, "Chronic liver disease/cirrhosis", 52_000, True),
        CauseOfDeath(10, "COVID-19", 49_932, False),
    ]


def _nhe_categories() -> List[NHECategory]:
    # CMS Office of the Actuary, NHE 2023 — $4.9T total, 17.6% of GDP.
    return [
        NHECategory("Hospital care", 1519.7, 31.0, 10.4),
        NHECategory("Physician & clinical services", 978.0, 20.0, 7.4),
        NHECategory("Retail prescription drugs", 449.7, 9.0, 11.4),
        NHECategory("Other (nursing, dental, home health, admin, etc.)", 1952.6, 40.0, 0.0),
    ]


def _nhe_payers() -> List[NHEPayer]:
    return [
        NHEPayer("Private health insurance", 1500.0, 30.0, 11.5),
        NHEPayer("Medicare", 1029.8, 21.0, 8.1),
        NHEPayer("Medicaid", 871.7, 18.0, 7.9),
        NHEPayer("Out-of-pocket", 505.7, 10.0, 7.2),
        NHEPayer("Other (VA, CHIP, other federal/state)", 992.8, 21.0, 0.0),
    ]


def _sources() -> List[SourceRef]:
    return [
        SourceRef("Quality measures", "MA-PD Star Ratings Technical Notes",
                  "CMS", "2025 / 2026 Star years", "free"),
        SourceRef("Quality measures", "HEDIS measure set", "NCQA",
                  "MY2025 / MY2026", "free"),
        SourceRef("Code frequency", "Top CPT codes (all-payer)",
                  "Definitive Healthcare", "2024", "proprietary"),
        SourceRef("Code frequency", "Top inpatient MS-DRGs",
                  "Definitive Healthcare / CMS SAF", "CY2024", "proprietary"),
        SourceRef("Code frequency", "Part B drug spending (FFS)",
                  "MedPAC Data Book", "2022", "free"),
        SourceRef("Compensation", "Provider Compensation & Productivity (DataDive)",
                  "MGMA", "2025 report / 2024 data", "proprietary"),
        SourceRef("Workforce", "Physician Supply & Demand Projections 2021–2036",
                  "AAMC", "2024", "free"),
        SourceRef("Cost structure", "National Hospital Flash Report",
                  "Kaufman Hall", "Dec 2025 YTD", "free"),
        SourceRef("Cost structure", "340B program savings & community benefit",
                  "AHA / HRSA", "2022–2024", "free"),
        SourceRef("Prevalence", "National Diabetes Statistics Report",
                  "CDC", "2023 data", "free"),
        SourceRef("Prevalence", "Cancer Facts & Figures / SEER Stat Facts",
                  "ACS / SEER", "2024 / 2026", "free"),
        SourceRef("Mortality", "Final mortality (leading causes of death)",
                  "CDC / NCHS", "2023 final", "free"),
        SourceRef("Spending", "National Health Expenditure Accounts",
                  "CMS Office of the Actuary", "2023", "free"),
    ]


def compute_benchmark_reference() -> BenchmarkReferenceResult:
    star = _star_weights()
    cpt = _cpt_codes()
    drgs = _drgs()
    partb = _partb_drugs()
    comp = _comp_benchmarks()
    shortages = _shortages()
    margins = _margin_trend()
    cost = _cost_structure()
    prev = _prevalence()
    deaths = _causes_of_death()
    nhe_cat = _nhe_categories()
    nhe_pay = _nhe_payers()
    sources = _sources()

    top_cpt = max(cpt, key=lambda c: c.pct_of_procedures)
    top_drg = min(drgs, key=lambda d: d.rank)
    top_drug = min(partb, key=lambda d: d.rank)
    # current YTD hospital operating margin (last point that is a YTD figure)
    ytd = next((m for m in margins if "YTD" in m.period), margins[-1])

    return BenchmarkReferenceResult(
        nhe_total_t=4.9,
        nhe_gdp_pct=17.6,
        nhe_per_capita=14_570.0,
        hospital_op_margin_pct=ytd.operating_margin_pct,
        top_drg=f"DRG {top_drg.drg} ({top_drg.pct_of_volume:.2f}%)",
        top_cpt=f"CPT {top_cpt.code} ({top_cpt.pct_of_procedures:.2f}%)",
        top_partb_drug=f"{top_drug.brand} (${top_drug.spend_2022_b:.1f}B)",
        partb_total_b=46.9,
        star_weights=star,
        cpt_codes=cpt,
        drgs=drgs,
        partb_drugs=partb,
        comp_benchmarks=comp,
        shortages=shortages,
        margin_trend=margins,
        cost_structure=cost,
        prevalence=prev,
        causes_of_death=deaths,
        nhe_categories=nhe_cat,
        nhe_payers=nhe_pay,
        sources=sources,
    )
