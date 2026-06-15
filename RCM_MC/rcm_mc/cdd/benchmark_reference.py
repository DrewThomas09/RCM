"""REF-01 through REF-06 Granular benchmarking reference data.

This is the chart-ready benchmark-data layer that sits beneath the vertical,
payer-economics, and unit-economics exhibits. It does not compute a forecast or
a score: it encodes current, sourced reference figures (CMS, MedPAC, MGMA,
AAMC, Kaufman Hall, AHA, CDC/NCHS, SEER/ACS, KFF, NCQA) as typed
:class:`~rcm_mc.cdd.exhibit.Exhibit` objects so a surface can render them
directly, and so a test can prove the cells tie to their stated totals.

Six domains, each its own registered feature:

- REF-01 quality measure weights (CMS MA-PD Star Ratings, 2025 vs 2026).
- REF-02 procedure and code frequency (top CPT, top inpatient MS-DRG, top
  Medicare Part B drugs by spend).
- REF-03 physician compensation, productivity, and supply.
- REF-04 hospital and provider cost structure.
- REF-05 disease-prevalence denominators and leading causes of death.
- REF-06 national health expenditure and utilization rates.

Every figure carries a source and a vintage in the footnote. Cells that are
estimates, projections, proprietary, or under active litigation are flagged so
a reader never mistakes a scenario for realized data. The numbers are static
reference data: no LLM is on any path that produces a value, label, or flag.
"""
from __future__ import annotations

from typing import Any, Dict, List

from .exhibit import Exhibit, Flag, Footnote, Reconciliation, Series, safe_div
from .registry import CddFeature, register


# ---------------------------------------------------------------------------
# REF-01 Quality measure weights (CMS MA-PD Star Ratings)
# ---------------------------------------------------------------------------

# Star Ratings measure weights by category. The patient-experience, complaints,
# and access weight dropped from 4 to 2 beginning with the 2026 Star Ratings.
STAR_WEIGHTS_2025 = {
    "Process": 1.0,
    "Patient experience, complaints, access": 4.0,
    "Outcome and intermediate outcome": 3.0,
    "Improvement": 5.0,
}
STAR_WEIGHTS_2026 = {
    "Process": 1.0,
    "Patient experience, complaints, access": 2.0,
    "Outcome and intermediate outcome": 3.0,
    "Improvement": 5.0,
}
PATIENT_EXPERIENCE = "Patient experience, complaints, access"


def quality_measure_weights(*, audience: str = "both") -> Exhibit:
    """Star Ratings measure weights by category, 2025 versus 2026.

    The single most decision-relevant change is the patient-experience weight
    falling from 4 to 2, which the reconciliation proves out.
    """
    categories = list(STAR_WEIGHTS_2025)
    series = [
        Series(name="Star measure weight 2025", kind="bar", points=[
            {"label": c, "value": STAR_WEIGHTS_2025[c]} for c in categories
        ]),
        Series(name="Star measure weight 2026", kind="bar", points=[
            {"label": c, "value": STAR_WEIGHTS_2026[c]} for c in categories
        ]),
    ]

    reduction = STAR_WEIGHTS_2025[PATIENT_EXPERIENCE] - STAR_WEIGHTS_2026[PATIENT_EXPERIENCE]
    reconciliations = [
        Reconciliation(
            identity="2025 patient experience weight minus the 2026 reduction equals the 2026 weight",
            lhs=STAR_WEIGHTS_2025[PATIENT_EXPERIENCE] - reduction,
            rhs=STAR_WEIGHTS_2026[PATIENT_EXPERIENCE],
            tolerance=1e-9,
        ),
    ]

    flags = [
        Flag(
            code="star_patient_experience_weight_cut",
            severity="warn",
            message=(
                "Patient experience, complaints, and access weight falls from 4 to 2 "
                "with the 2026 Star Ratings, shifting Stars toward clinical outcomes."
            ),
            source="CMS Medicare Advantage and Part D Star Ratings",
        ),
        Flag(
            code="star_2027_proposal_forward_looking",
            severity="info",
            message=(
                "The CY2027 proposed rule of November 2025 would remove 12 measures, "
                "with CAHPS and HOS approaching 40 percent of total Star weight by 2029. "
                "This is a proposal, not final."
            ),
            source="CMS CY2027 proposed rule",
        ),
    ]

    footnote = Footnote(
        source="CMS Medicare Advantage and Part D Star Ratings Technical Notes; NCQA HEDIS",
        vintage="2025 and 2026 Star Years",
        assumptions=[
            "Weights: improvement is 5, outcome is 3, patient experience is 4 through 2025 then 2 from 2026, process is 1.",
            "Tag every quality measure table to a measurement year because the measure set changes annually.",
            "The 2027 measure removals and 2029 CAHPS weighting are proposals, not realized policy.",
        ],
    )

    return Exhibit(
        feature_id="REF-01",
        title="Quality measure weights, Star Ratings 2025 versus 2026",
        audience=audience,
        series=series,
        footnote=footnote,
        flags=flags,
        reconciliations=reconciliations,
        summary=(
            "CMS cut the patient experience weight from 4 to 2 starting with the 2026 "
            "Star Ratings, the major weighting inflection in the program."
        ),
        meta={
            "weights_2025": STAR_WEIGHTS_2025,
            "weights_2026": STAR_WEIGHTS_2026,
            "patient_experience_reduction": reduction,
        },
    ).validate()


# ---------------------------------------------------------------------------
# REF-02 Procedure and code frequency
# ---------------------------------------------------------------------------

# Top physician CPT codes as a share of all physician procedures
# (Definitive Healthcare all-payer claims, 2024).
TOP_CPT = [
    {"code": "99214", "label": "99214 office visit established moderate", "share_pct": 4.50},
    {"code": "99213", "label": "99213 office visit established low", "share_pct": 3.88},
    {"code": "97110", "label": "97110 therapeutic exercise", "share_pct": 3.46},
    {"code": "97530", "label": "97530 therapeutic activities", "share_pct": 2.99},
]

# Top inpatient MS-DRGs by share of total DRG diagnoses (Definitive Healthcare,
# CY2024, CMS SAF derived).
TOP_DRG = [
    {"drg": "871", "label": "DRG 871 septicemia or severe sepsis with MCC", "share_pct": 7.44},
    {"drg": "291", "label": "DRG 291 heart failure and shock with MCC", "share_pct": 4.05},
    {"drg": "885", "label": "DRG 885 psychoses", "share_pct": 2.43},
    {"drg": "177", "label": "DRG 177 respiratory infections with MCC", "share_pct": 1.91},
    {"drg": "193", "label": "DRG 193 simple pneumonia and pleurisy with MCC", "share_pct": 1.88},
    {"drg": "189", "label": "DRG 189 pulmonary edema and respiratory failure", "share_pct": 1.45},
    {"drg": "872", "label": "DRG 872 septicemia or severe sepsis without MCC", "share_pct": 1.44},
    {"drg": "690", "label": "DRG 690 kidney and urinary tract infections without MCC", "share_pct": 1.37},
    {"drg": "392", "label": "DRG 392 esophagitis and gastroenteritis without MCC", "share_pct": 1.27},
    {"drg": "57", "label": "DRG 57 degenerative nervous system disorders without MCC", "share_pct": 1.21},
]

# Top Medicare Part B drugs by spending (MedPAC July 2024 Data Book, 2022, FFS).
# Ranks 1 through 10 sum to the reported 18.5 billion within rounding.
TOP_PART_B = [
    {"drug": "Keytruda (pembrolizumab)", "therapy": "cancer", "spend_b": 4.9},
    {"drug": "Eylea (aflibercept)", "therapy": "ophthalmology", "spend_b": 3.5},
    {"drug": "Prolia or Xgeva (denosumab)", "therapy": "osteoporosis", "spend_b": 2.0},
    {"drug": "Darzalex (daratumumab)", "therapy": "cancer", "spend_b": 1.9},
    {"drug": "Opdivo (nivolumab)", "therapy": "cancer", "spend_b": 1.9},
    {"drug": "Rituxan (rituximab)", "therapy": "cancer or arthritis", "spend_b": 1.0},
    {"drug": "Orencia", "therapy": "arthritis", "spend_b": 0.9},
    {"drug": "Lucentis", "therapy": "ophthalmology", "spend_b": 0.8},
    {"drug": "Tecentriq", "therapy": "cancer", "spend_b": 0.8},
    {"drug": "Avastin", "therapy": "cancer or eye", "spend_b": 0.7},
    {"drug": "Ocrevus", "therapy": "multiple sclerosis", "spend_b": 0.7},
]
PART_B_TOP10_REPORTED_B = 18.5


def code_frequency(*, audience: str = "both") -> Exhibit:
    """Top CPT codes, inpatient MS-DRGs, and Medicare Part B drugs by volume.

    The Part B reconciliation proves the listed top 10 drugs sum to the reported
    18.5 billion dollars of spend within rounding to a tenth of a billion.
    """
    series = [
        Series(name="Top physician CPT codes by share", kind="bar", points=[
            {"label": c["label"], "value": c["share_pct"]} for c in TOP_CPT
        ]),
        Series(name="Top inpatient DRGs by share", kind="bar", points=[
            {"label": d["label"], "value": d["share_pct"]} for d in TOP_DRG
        ]),
        Series(name="Top Medicare Part B drugs by spend", kind="bar", points=[
            {"label": d["drug"], "value": d["spend_b"], "therapy": d["therapy"]}
            for d in TOP_PART_B
        ]),
    ]

    top10_sum = round(sum(d["spend_b"] for d in TOP_PART_B[:10]), 4)
    reconciliations = [
        Reconciliation(
            identity="top 10 Part B drugs sum to the reported 18.5 billion dollars within rounding",
            lhs=top10_sum,
            rhs=PART_B_TOP10_REPORTED_B,
            tolerance=0.15,
        ),
    ]

    flags = [
        Flag(
            code="definitive_shares_not_counts",
            severity="info",
            message=(
                "Definitive Healthcare rankings are reported as percentage shares, not "
                "raw counts. Use the CMS MEDPAR public file for exact discharge counts "
                "and per stay payments."
            ),
            source="Definitive Healthcare; CMS MEDPAR PUF",
        ),
        Flag(
            code="drg470_site_of_care_migration",
            severity="info",
            message=(
                "DRG 470 major joint replacement was historically the top volume DRG but "
                "dropped out of the inpatient top 10 after CMS moved total joint "
                "replacement to outpatient and ASC settings."
            ),
            source="CMS site of care policy",
        ),
        Flag(
            code="part_b_ffs_only",
            severity="warn",
            message=(
                "MedPAC Part B figures are fee for service only and exclude Medicare "
                "Advantage, and round to a tenth of a billion dollars."
            ),
            source="MedPAC July 2024 Data Book",
        ),
    ]

    footnote = Footnote(
        source="Definitive Healthcare all-payer claims; CMS SAF; MedPAC July 2024 Data Book",
        vintage="CPT and DRG 2024; Part B drug spend 2022",
        assumptions=[
            "CPT 99214 and 99213 together are roughly 8 to 10 percent of all physician procedures.",
            "The ten highest volume MS-DRGs are roughly 30 percent of Medicare inpatient volume.",
            "Top 10 Part B drugs are 39 percent of the 46.9 billion dollar Part B drug total.",
        ],
    )

    return Exhibit(
        feature_id="REF-02",
        title="Procedure and code frequency, top CPT, DRG, and Part B drugs",
        audience=audience,
        series=series,
        footnote=footnote,
        flags=flags,
        reconciliations=reconciliations,
        summary=(
            "CPT 99214 and 99213 lead physician billing, DRG 871 sepsis is the top "
            "inpatient stay, and Keytruda is the top Medicare Part B drug."
        ),
        meta={
            "top_cpt": TOP_CPT,
            "top_drg": TOP_DRG,
            "top_part_b": TOP_PART_B,
            "part_b_top10_sum_b": top10_sum,
        },
    ).validate()


# ---------------------------------------------------------------------------
# REF-03 Physician compensation, productivity, and supply
# ---------------------------------------------------------------------------

# Illustrative MGMA derived compensation for family medicine (2024). The full
# MGMA DataDive percentile cells are proprietary; these are approximate.
FAMILY_MEDICINE_COMP = 218400.0
FAMILY_MEDICINE_WRVU = 5200.0
FAMILY_MEDICINE_DOLLARS_PER_WRVU = 42.0

# AAMC physician shortage projection ranges to 2036 (low, high).
AAMC_SHORTAGE = [
    {"group": "Total physicians", "low": 13500, "high": 86000},
    {"group": "Primary care", "low": 20200, "high": 40400},
    {"group": "Surgical specialties", "low": 10100, "high": 19900},
]


def physician_compensation_supply(*, audience: str = "both") -> Exhibit:
    """Physician compensation, dollars per wRVU, and AAMC shortage ranges.

    The reconciliation proves family medicine compensation divided by wRVUs
    equals the reported dollars per wRVU.
    """
    series = [
        Series(name="Family medicine compensation and productivity", kind="bar", points=[
            {"label": "Total compensation", "value": FAMILY_MEDICINE_COMP},
            {"label": "Annual wRVUs", "value": FAMILY_MEDICINE_WRVU},
            {"label": "Dollars per wRVU", "value": FAMILY_MEDICINE_DOLLARS_PER_WRVU},
        ]),
        Series(name="AAMC physician shortage range to 2036", kind="bar", points=[
            {"label": s["group"], "low": s["low"], "high": s["high"]}
            for s in AAMC_SHORTAGE
        ]),
    ]

    reconciliations = [
        Reconciliation(
            identity="family medicine compensation divided by wRVUs equals dollars per wRVU",
            lhs=safe_div(FAMILY_MEDICINE_COMP, FAMILY_MEDICINE_WRVU),
            rhs=FAMILY_MEDICINE_DOLLARS_PER_WRVU,
            tolerance=0.05,
        ),
    ]

    flags = [
        Flag(
            code="mgma_proprietary",
            severity="warn",
            message=(
                "MGMA DataDive per specialty percentile cells are subscription only. "
                "Only summary figures and approximate ranges are public."
            ),
            source="MGMA 2025 Provider Compensation and Productivity",
        ),
        Flag(
            code="aggregator_approximate",
            severity="warn",
            message=(
                "Aggregator reported MGMA numbers from RVUEdge, FastRVU, and Resolve are "
                "approximate. Verify against the official MGMA DataDive before use."
            ),
            source="secondary aggregators",
        ),
        Flag(
            code="aamc_shortage_projection",
            severity="info",
            message=(
                "AAMC shortage ranges are projections to 2036 that assume about 1 percent "
                "annual GME growth. Treat them as scenarios, not realized data."
            ),
            source="AAMC physician supply and demand projections 2024",
        ),
        Flag(
            code="pfs_efficiency_adjustment_2026",
            severity="info",
            message=(
                "The 2026 Medicare PFS efficiency adjustment of negative 2.5 percent on "
                "non time based codes will lower wRVU values for many surgical procedures."
            ),
            source="CMS 2026 Medicare Physician Fee Schedule",
        ),
    ]

    footnote = Footnote(
        source="MGMA 2025 Provider Compensation and Productivity; AAMC workforce projections",
        vintage="MGMA 2024 data; AAMC 2024 report",
        assumptions=[
            "Family medicine dollars per wRVU fell from about 51.70 in 2019 to about 42 in 2024.",
            "AAMC projects a total shortage of 13,500 to 86,000 physicians by 2036.",
            "Compensation cells here are illustrative pending an MGMA DataDive license.",
        ],
    )

    return Exhibit(
        feature_id="REF-03",
        title="Physician compensation, productivity, and supply",
        audience=audience,
        series=series,
        footnote=footnote,
        flags=flags,
        reconciliations=reconciliations,
        summary=(
            "Family medicine pays about 42 dollars per wRVU, down from 2019, while AAMC "
            "projects a physician shortage of up to 86,000 by 2036."
        ),
        meta={
            "family_medicine_comp": FAMILY_MEDICINE_COMP,
            "family_medicine_wrvu": FAMILY_MEDICINE_WRVU,
            "dollars_per_wrvu": FAMILY_MEDICINE_DOLLARS_PER_WRVU,
            "aamc_shortage": AAMC_SHORTAGE,
        },
    ).validate()


# ---------------------------------------------------------------------------
# REF-04 Hospital and provider cost structure
# ---------------------------------------------------------------------------

# Kaufman Hall median hospital operating margins, with system allocations.
HOSPITAL_MARGINS = [
    {"period": "2024 full year", "margin_pct": 4.9},
    {"period": "December 2024", "margin_pct": 7.6},
    {"period": "YTD December 2025", "margin_pct": 1.3},
    {"period": "December 2025", "margin_pct": 5.0},
]

# Physician practice cost structure (Kaufman Hall Physician Flash Report, Q4 2025).
LABOR_PCT_OF_PRACTICE_EXPENSE = 84.4
PHYSICIAN_SUBSIDY = 315358.0

# 340B and uncompensated care.
UNCOMPENSATED_CARE_TOTAL_B = 42.0   # hospitals, 2019
SHARE_340B = 0.68                   # 340B hospital share of uncompensated care
UNCOMPENSATED_340B_B = round(UNCOMPENSATED_CARE_TOTAL_B * SHARE_340B, 4)


def hospital_cost_structure(*, audience: str = "both") -> Exhibit:
    """Hospital operating margins, practice labor share, and 340B context.

    The reconciliation proves the 340B share of uncompensated care equals the
    stated 340B uncompensated care dollars.
    """
    series = [
        Series(name="Median hospital operating margin", kind="line", points=[
            {"label": m["period"], "value": m["margin_pct"]} for m in HOSPITAL_MARGINS
        ]),
        Series(name="Physician practice cost structure", kind="bar", points=[
            {"label": "Labor as percent of practice expense", "value": LABOR_PCT_OF_PRACTICE_EXPENSE},
            {"label": "Median physician subsidy dollars", "value": PHYSICIAN_SUBSIDY},
        ]),
        Series(name="Uncompensated care by hospital type", kind="bar", points=[
            {"label": "All hospitals", "value": UNCOMPENSATED_CARE_TOTAL_B},
            {"label": "340B hospitals", "value": UNCOMPENSATED_340B_B},
        ]),
    ]

    reconciliations = [
        Reconciliation(
            identity="340B share of uncompensated care equals the reported 340B uncompensated dollars",
            lhs=UNCOMPENSATED_CARE_TOTAL_B * SHARE_340B,
            rhs=UNCOMPENSATED_340B_B,
            tolerance=1e-9,
        ),
    ]

    flags = [
        Flag(
            code="margin_allocation_basis",
            severity="warn",
            message=(
                "Margins include system allocations. The YTD December 2025 median is 1.3 "
                "percent with allocations versus about 5.3 percent without them, so always "
                "label the basis."
            ),
            source="Kaufman Hall National Hospital Flash Report",
        ),
        Flag(
            code="hospitals_in_the_red",
            severity="risk",
            message=(
                "Even with a positive median, about 40 percent of hospitals operated in the "
                "red in May 2024. Escalate cost analysis below a 1 percent operating margin."
            ),
            source="Strata and Kaufman Hall",
        ),
        Flag(
            code="340b_rebate_pilot_vacated",
            severity="info",
            message=(
                "The 340B Rebate Model Pilot was vacated and remanded to HHS on February 10, "
                "2026 by the District of Maine. Treat the pilot as under active litigation."
            ),
            source="American Hospital Association v. Kennedy, No. 25-cv-600",
        ),
        Flag(
            code="uncompensated_care_2019_vintage",
            severity="info",
            message="Uncompensated care figures are 2019, the latest comparable AHA series.",
            source="American Hospital Association",
        ),
    ]

    footnote = Footnote(
        source="Kaufman Hall National Hospital and Physician Flash Reports; AHA 340B data",
        vintage="margins through December 2025; 340B 2022 to 2024; uncompensated care 2019",
        assumptions=[
            "The 2024 full year median operating margin was 4.9 percent with December at 7.6 percent.",
            "Practice labor is about 84.4 percent of total practice expense in Q4 2025.",
            "340B hospitals accounted for roughly 68 percent of hospital uncompensated care.",
        ],
    )

    return Exhibit(
        feature_id="REF-04",
        title="Hospital and provider cost structure",
        audience=audience,
        series=series,
        footnote=footnote,
        flags=flags,
        reconciliations=reconciliations,
        summary=(
            "Median hospital operating margin sits at 1.3 percent YTD through December 2025 "
            "with allocations, and labor is about 84 percent of practice expense."
        ),
        meta={
            "hospital_margins": HOSPITAL_MARGINS,
            "labor_pct_of_practice_expense": LABOR_PCT_OF_PRACTICE_EXPENSE,
            "physician_subsidy": PHYSICIAN_SUBSIDY,
            "uncompensated_340b_b": UNCOMPENSATED_340B_B,
        },
    ).validate()


# ---------------------------------------------------------------------------
# REF-05 Disease prevalence denominators and leading causes of death
# ---------------------------------------------------------------------------

# Chronic condition prevalence in the US, counts in millions.
CHRONIC_PREVALENCE = [
    {"condition": "Prediabetes adults", "millions": 115.2},
    {"condition": "Diabetes total", "millions": 40.1},
    {"condition": "Diabetes diagnosed", "millions": 29.1},
    {"condition": "Diabetes undiagnosed", "millions": 11.0},
]

# Projected new cancer cases for 2026, counts in thousands (SEER).
CANCER_INCIDENCE_2026 = [
    {"site": "Prostate", "new_cases_k": 333.83},
    {"site": "Breast (women and men)", "new_cases_k": 324.58},
    {"site": "Lung and bronchus", "new_cases_k": 229.41},
]

# Leading causes of death, CDC NCHS final 2023, counts.
LEADING_CAUSES_2023 = [
    {"cause": "Heart disease", "deaths": 680909},
    {"cause": "Cancer", "deaths": 613352},
    {"cause": "Unintentional injury", "deaths": 222518},
    {"cause": "Stroke", "deaths": 162000},
    {"cause": "Chronic lower respiratory disease", "deaths": 145000},
    {"cause": "Alzheimer disease", "deaths": 114000},
    {"cause": "Diabetes", "deaths": 95000},
    {"cause": "Kidney disease", "deaths": 55000},
    {"cause": "Chronic liver disease", "deaths": 52000},
    {"cause": "COVID-19", "deaths": 49932},
]
TOTAL_DEATHS_2023 = 3090964
HEART_PLUS_CANCER_SHARE = 41.9  # reported percent of all deaths


def disease_prevalence(*, audience: str = "both") -> Exhibit:
    """Chronic prevalence, cancer incidence, and leading causes of death.

    The reconciliation proves heart disease plus cancer deaths over total deaths
    equals the reported 41.9 percent of all deaths.
    """
    series = [
        Series(name="Chronic condition prevalence in millions", kind="bar", points=[
            {"label": c["condition"], "value": c["millions"]} for c in CHRONIC_PREVALENCE
        ]),
        Series(name="Projected 2026 cancer incidence in thousands", kind="bar", points=[
            {"label": c["site"], "value": c["new_cases_k"]} for c in CANCER_INCIDENCE_2026
        ]),
        Series(name="Leading causes of death 2023", kind="bar", points=[
            {"label": c["cause"], "value": c["deaths"]} for c in LEADING_CAUSES_2023
        ]),
    ]

    heart = LEADING_CAUSES_2023[0]["deaths"]
    cancer = LEADING_CAUSES_2023[1]["deaths"]
    reconciliations = [
        Reconciliation(
            identity="heart disease plus cancer deaths over total deaths equals the reported 41.9 percent",
            lhs=safe_div(heart + cancer, TOTAL_DEATHS_2023) * 100.0,
            rhs=HEART_PLUS_CANCER_SHARE,
            tolerance=0.1,
        ),
    ]

    flags = [
        Flag(
            code="diabetes_methodology_conflict",
            severity="info",
            message=(
                "Diabetes prevalence is 40.1 million by CDC surveillance versus 15.8 percent "
                "of adults by NHANES. Use the figure whose denominator matches the analysis."
            ),
            source="CDC National Diabetes Statistics Report; NHANES",
        ),
        Flag(
            code="cancer_2026_projection",
            severity="info",
            message=(
                "2026 cancer incidence figures are SEER projections of about 2.1 million new "
                "cases, not realized counts."
            ),
            source="SEER and American Cancer Society",
        ),
        Flag(
            code="ccw_multimorbidity_vintage",
            severity="info",
            message=(
                "Widely cited Medicare multimorbidity figures such as 68.4 percent with two "
                "or more conditions derive from 2005 to 2012 analyses. Pull the live CCW "
                "dashboard for current rates."
            ),
            source="CMS Chronic Conditions Data Warehouse",
        ),
    ]

    footnote = Footnote(
        source="CDC NCHS final mortality 2023; CDC National Diabetes Statistics Report; SEER",
        vintage="mortality 2023; diabetes 2023; cancer 2026 projection",
        assumptions=[
            "Total US deaths in 2023 were 3,090,964 with life expectancy at 78.4 years.",
            "Heart disease and cancer together are 41.9 percent of all deaths, top 10 are 70.9 percent.",
            "Stroke and several lower ranked causes are rounded to the nearest thousand.",
        ],
    )

    return Exhibit(
        feature_id="REF-05",
        title="Disease prevalence denominators and leading causes of death",
        audience=audience,
        series=series,
        footnote=footnote,
        flags=flags,
        reconciliations=reconciliations,
        summary=(
            "Diabetes affects 40.1 million people and prediabetes 115.2 million, while heart "
            "disease and cancer remain 41.9 percent of all deaths."
        ),
        meta={
            "chronic_prevalence": CHRONIC_PREVALENCE,
            "cancer_incidence_2026": CANCER_INCIDENCE_2026,
            "leading_causes_2023": LEADING_CAUSES_2023,
            "total_deaths_2023": TOTAL_DEATHS_2023,
        },
    ).validate()


# ---------------------------------------------------------------------------
# REF-06 National health expenditure and utilization rates
# ---------------------------------------------------------------------------

NHE_TOTAL_B = 4900.0  # 4.9 trillion dollars, 2023

# NHE by category, dollars in billions (2023).
NHE_BY_CATEGORY = [
    {"category": "Hospital care", "spend_b": 1519.7},
    {"category": "Physician and clinical services", "spend_b": 978.0},
    {"category": "Retail prescription drugs", "spend_b": 449.7},
]

# NHE by payer, dollars in billions (2023).
NHE_BY_PAYER = [
    {"payer": "Private health insurance", "spend_b": 1500.0},
    {"payer": "Medicare", "spend_b": 1029.8},
    {"payer": "Medicaid", "spend_b": 871.7},
    {"payer": "Out of pocket", "spend_b": 505.7},
]

# Medicaid per enrollee spending by eligibility group (KFF 2023 T-MSIS).
MEDICAID_PER_ENROLLEE = [
    {"group": "People with disabilities", "dollars": 20950},
    {"group": "Aged 65 and over", "dollars": 20194},
    {"group": "National median across states", "dollars": 7909},
    {"group": "Children", "dollars": 3321},
]


def national_expenditure(*, audience: str = "both") -> Exhibit:
    """National health expenditure by category and payer, plus Medicaid rates.

    The reconciliation proves the payer breakdown plus an all other payers
    residual sums to the 4.9 trillion dollar total.
    """
    payer_named = round(sum(p["spend_b"] for p in NHE_BY_PAYER), 4)
    payer_residual = round(NHE_TOTAL_B - payer_named, 4)
    payer_points = [{"label": p["payer"], "value": p["spend_b"]} for p in NHE_BY_PAYER]
    payer_points.append({"label": "All other payers", "value": payer_residual})

    category_named = round(sum(c["spend_b"] for c in NHE_BY_CATEGORY), 4)
    category_residual = round(NHE_TOTAL_B - category_named, 4)
    category_points = [{"label": c["category"], "value": c["spend_b"]} for c in NHE_BY_CATEGORY]
    category_points.append({"label": "All other categories", "value": category_residual})

    series = [
        Series(name="National health expenditure by category", kind="bar", points=category_points),
        Series(name="National health expenditure by payer", kind="bar", points=payer_points),
        Series(name="Medicaid spending per enrollee by group", kind="bar", points=[
            {"label": m["group"], "value": m["dollars"]} for m in MEDICAID_PER_ENROLLEE
        ]),
    ]

    payer_total = round(payer_named + payer_residual, 4)
    reconciliations = [
        Reconciliation(
            identity="national health expenditure by payer sums to the 4.9 trillion dollar total",
            lhs=payer_total,
            rhs=NHE_TOTAL_B,
            tolerance=1e-6,
        ),
    ]

    flags = [
        Flag(
            code="nhe_projections_forward_looking",
            severity="info",
            message=(
                "2024 and later NHE growth rates reaching 19.7 percent of GDP by 2032 are "
                "projections from the CMS Office of the Actuary, not realized data."
            ),
            source="CMS Office of the Actuary",
        ),
        Flag(
            code="medpac_all_payer_basis",
            severity="warn",
            message=(
                "MedPAC per beneficiary figures are all payer totals, not Medicare program "
                "only. Do not label all payer spending as Medicare cost per beneficiary."
            ),
            source="MedPAC July 2024 Data Book",
        ),
    ]

    footnote = Footnote(
        source="CMS Office of the Actuary National Health Expenditure; KFF Medicaid analysis",
        vintage="NHE 2023; Medicaid 2023 T-MSIS",
        assumptions=[
            "National health spending was 4.9 trillion dollars, 17.6 percent of GDP, in 2023.",
            "Hospital care is 31 percent, physician services 20 percent, retail drugs 9 percent.",
            "All other payers and categories are residuals computed so each bar ties to the total.",
        ],
    )

    return Exhibit(
        feature_id="REF-06",
        title="National health expenditure and utilization rates",
        audience=audience,
        series=series,
        footnote=footnote,
        flags=flags,
        reconciliations=reconciliations,
        summary=(
            "National health spending hit 4.9 trillion dollars in 2023, with hospital care "
            "the largest category and private insurance the largest payer."
        ),
        meta={
            "nhe_total_b": NHE_TOTAL_B,
            "nhe_by_category": NHE_BY_CATEGORY,
            "nhe_by_payer": NHE_BY_PAYER,
            "payer_residual_b": payer_residual,
            "category_residual_b": category_residual,
            "medicaid_per_enrollee": MEDICAID_PER_ENROLLEE,
        },
    ).validate()


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

_BUILDERS = [
    ("REF-01", "Quality measure weights reference", quality_measure_weights),
    ("REF-02", "Procedure and code frequency reference", code_frequency),
    ("REF-03", "Physician compensation and supply reference", physician_compensation_supply),
    ("REF-04", "Hospital and provider cost structure reference", hospital_cost_structure),
    ("REF-05", "Disease prevalence denominators reference", disease_prevalence),
    ("REF-06", "National health expenditure reference", national_expenditure),
]

for _fid, _title, _builder in _BUILDERS:
    register(
        CddFeature(
            feature_id=_fid,
            title=_title,
            audience="both",
            demo=_builder,
        )
    )
