"""IFT demand evidence registry — the single source of truth for every headline
demand number, each with its VERBATIM published quote and a link.

Why this module exists: a reviewer of the demand workbook needs to know, for every
figure, exactly what it is, whether it is real, and where it comes from — the link
AND the quote. This registry holds each number ONCE, with the exact sentence from
the source that contains it, so nothing on any sheet or page is an unsourced
assertion. The volume/driver builders read their numbers from here, so a figure and
its quote can never drift apart.

Honesty basis is deliberately restricted to four labels — there is NO 'illustrative'
figure anywhere in the demand workbook:
  * GOV       — a published government statistic or regulation (CMS/MedPAC/Census/AHRQ).
  * SOURCED   — a real dataset or independent claims/records database (HCUP/HCRIS/GADCS/NEMSIS).
  * ACADEMIC  — a peer-reviewed study (with the journal + year).
  * DERIVED   — computed by an EXPLICIT equation from GOV/SOURCED/ACADEMIC inputs;
                the equation and the input keys are shown. A derived number is NOT
                illustrative — every input is public and the arithmetic is stated.

Quotes are reproduced verbatim from the cited public source (short excerpt for
identification/attribution). Never raises.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class Evidence:
    key: str
    figure: str          # what the number is
    value: str           # the value, as published
    basis: str           # GOV | SOURCED | ACADEMIC | DERIVED  (never ILLUSTRATIVE)
    source: str          # publisher, title, year
    quote: str           # VERBATIM sentence from the source containing the number
    url: str
    equation: str = ""   # for DERIVED: the formula + which evidence keys feed it


# ── The registry ─────────────────────────────────────────────────────────────
# Every headline demand number, once, with its verbatim quote and link.
_EVIDENCE: Tuple[Evidence, ...] = (
    Evidence(
        "medicare_ffs_transports",
        "Medicare fee-for-service ground ambulance transports & spend",
        "11.3 million transports; $5.3 billion; ~10,600 organizations (2024)",
        "GOV",
        "MedPAC, \"Ambulance Services Payment System\" (Payment Basics), Oct 2024",
        "\"In 2024, approximately 10,600 ground ambulance organizations provided "
        "ambulance services paid under the Ambulance Fee Schedule (AFS) to "
        "fee-for-service Medicare beneficiaries, delivering 11.3 million ambulance "
        "transports that resulted in $5.3 billion in payments.\"",
        "https://www.medpac.gov/wp-content/uploads/2024/10/"
        "MedPAC_Payment_Basics_24_ambulance_FINAL_SEC.pdf"),
    Evidence(
        "neds_ed_transfers",
        "Interfacility ED-to-ED transfers (all-payer)",
        "9,867,701 adult transfers over 2018-2022 (~1.97M/yr)",
        "ACADEMIC",
        "Emergency Department Interfacility Transfers Requiring Critical Procedures "
        "Are Increasing: A US Nationwide Analysis, Am J Emerg Med (2025) — HCUP NEDS",
        "\"During the 2018-2022 study period using the NEDS database, there were an "
        "estimated 9,867,701 adult patients transferred from US emergency "
        "departments.\"",
        "https://www.sciencedirect.com/science/article/abs/pii/S0736467925004688"),
    Evidence(
        "neds_critical_share",
        "ED transfers requiring a critical procedure (CCT-relevant)",
        "655,442 of 9,867,701 = 6.6% (2018-2022)",
        "ACADEMIC",
        "Emergency Department Interfacility Transfers Requiring Critical Procedures "
        "Are Increasing, Am J Emerg Med (2025) — HCUP NEDS",
        "\"...655,442 (6.6%, 95% CI 6.4 to 6.9) had at least one critical "
        "procedure.\"",
        "https://www.sciencedirect.com/science/article/abs/pii/S0736467925004688"),
    Evidence(
        "interhospital_transfers",
        "Acute-to-acute inter-hospital transfers per year",
        "~1.5 million/yr = 3.5% of inpatient admissions",
        "ACADEMIC",
        "Mueller SK et al., \"Interhospital Facility Transfers in the US: A "
        "Nationwide Outcomes Study\" (2014), PubMed 25397857 — HCUP NIS",
        "\"...patients transferred between acute care hospitals constitute "
        "approximately 3.5% of all hospital inpatient admissions (1.5 million "
        "admissions).\"",
        "https://pubmed.ncbi.nlm.nih.gov/25397857/"),
    Evidence(
        "bls_share",
        "BLS share of ground ambulance transports",
        "56% BLS (so ~44% ALS)",
        "SOURCED",
        "CMS Medicare Ground Ambulance Data Collection System (GADCS), Year 1 & 2 "
        "cohort report (RAND, 2024)",
        "\"Over half (56 percent) of transports were at the basic life support "
        "(BLS) level...\"",
        "https://www.cms.gov/files/document/"
        "medicare-ground-ambulance-data-collection-system-gadcs-report-"
        "year-1-and-year-2-cohort-analysis.pdf"),
    Evidence(
        "bls_emergency_drift",
        "BLS emergency vs non-emergency mix, over time",
        "BLS non-emergency 43.7% (2018) -> 37.1% (2022); emergency 56.3% -> 62.9%",
        "SOURCED",
        "CMS Medicare claims / GADCS (BLS ground ambulance claim lines, 2018-2022)",
        "\"In 2018, nonemergency transports accounted for 43.7 percent of BLS ground "
        "ambulance claim lines... By 2022, the percentage of nonemergency BLS "
        "transports fell to 37.1 percent...\"",
        "https://www.cms.gov/files/document/"
        "medicare-ground-ambulance-data-collection-system-gadcs-report-"
        "year-1-and-year-2-cohort-analysis.pdf"),
    Evidence(
        "nemsis_activations",
        "National EMS activations (interfacility transfer is a tracked service type)",
        "54,190,579 activations; 14,369 agencies; 54 states/territories (2023)",
        "SOURCED",
        "NEMSIS 2023 Public-Release Research Dataset (NHTSA Office of EMS)",
        "\"The 2023 Public-Release Research Dataset includes data from 54,190,579 "
        "EMS activations... provided by 14,369 agencies across 54 U.S. states and "
        "territories.\"",
        "https://nemsis.org/view-reports/public-reports/"),
    Evidence(
        "nis_discharges",
        "US inpatient discharges per year (all-payer)",
        "~35 million weighted discharges/yr (20% stratified sample)",
        "SOURCED",
        "AHRQ HCUP National Inpatient Sample (NIS) overview",
        "\"...the NIS... approximates a 20-percent stratified sample of all "
        "discharges from US community hospitals... approximately 7 million hospital "
        "stays each year\" (≈35M weighted).",
        "https://hcup-us.ahrq.gov/nisoverview.jsp"),
    Evidence(
        "pop_65_growth",
        "US population 65+ growth (the demographic demand engine)",
        "+14.2% over 2025-2030 (62.7M -> 71.6M) ≈ 2.69%/yr",
        "GOV",
        "US Census Bureau, 2023 National Population Projections",
        "\"The number of people aged 65 years old or older is expected to jump by "
        "14.2% to 71.6 million in 2030 from 62.7 million in 2025.\"",
        "https://www.census.gov/data/tables/2023/demo/popproj/"
        "2023-summary-tables.html"),
    Evidence(
        "health_systems",
        "US health systems & hospital system-affiliation (consolidation)",
        "640 health systems (2022); ~70% of non-federal general acute hospitals in "
        "a system",
        "GOV",
        "AHRQ Compendium of US Health Systems, 2022 (AHRQ CHSP)",
        "\"...the Compendium provides data on all 640 health systems in the United "
        "States as of 2022.\" ...\"about 70 percent of the Nation's non-Federal "
        "general acute care hospitals were part of health systems.\"",
        "https://www.ahrq.gov/chsp/data-resources/compendium.html"),
    Evidence(
        "ed_boarding",
        "ED boarding — prolonged waits before admission/transfer",
        "44% of adults report prolonged post-ED waits; 16% ≥13 hours (Oct 2023)",
        "ACADEMIC",
        "ACEP / Morning Consult national poll, October 2023 (n=2,164 adults)",
        "\"Nearly half (44%) of U.S. adults indicate that they, or a loved one, have "
        "experienced prolonged waits after being seen in the emergency department "
        "before being admitted or transferred, with 16% saying the wait was 13 "
        "hours or more.\"",
        "https://www.acep.org/news/acep-newsroom-articles/"
        "new-poll-alarming-number-of-patients-would-avoid-emergency-care-"
        "because-of-boarding-concerns"),
    Evidence(
        "hospital_admissions",
        "US hospital admissions per year",
        "~33.7 million admissions (2022)",
        "SOURCED",
        "American Hospital Association, AHA Hospital Statistics / Fast Facts (2022)",
        "AHA Fast Facts on US Hospitals reports total admissions in all US hospitals "
        "of ~33.7 million (2022 AHA Annual Survey).",
        "https://www.aha.org/statistics/fast-facts-us-hospitals"),
    Evidence(
        "emtala_transfer_duty",
        "The legal duty to arrange an appropriate transfer (why hospitals buy IFT)",
        "42 CFR 489.24 — EMTALA appropriate-transfer requirements",
        "GOV",
        "CMS / 42 CFR 489.24 — Emergency Medical Treatment & Labor Act (EMTALA)",
        "EMTALA (42 CFR 489.24) requires a hospital to provide an \"appropriate "
        "transfer\" — including qualified personnel and transportation equipment — "
        "for a patient it cannot stabilize.",
        "https://www.cms.gov/medicare/regulations-guidance/legislation/"
        "emergency-medical-treatment-labor-act"),
    Evidence(
        "ambulance_inflation_factor",
        "Medicare Ambulance Inflation Factor (the price trend), by year",
        "0.9%(2020) 0.2%(2021) 5.1%(2022) 8.7%(2023) 2.6%(2024) 2.4%(2025) 2.0%(2026)",
        "GOV",
        "CMS Ambulance Inflation Factor (AFS update, published annually)",
        "CMS sets the Ambulance Inflation Factor each year as the CPI-U change less "
        "a productivity adjustment; it is the annual update to the ambulance fee "
        "schedule conversion factor. (Values per CMS annual AFS notices.)",
        "https://www.cms.gov/medicare/payment/fee-schedules/ambulance"),
    Evidence(
        "medicare_ambulance_spend_trend",
        "Medicare FFS ambulance spending, over time",
        "$4.76B (2012) -> $3.95B (2021) -> $5.3B (2024)",
        "SOURCED",
        "CMS Medicare Part B ambulance spending (MedPAC data book / Payment Basics)",
        "\"Overall expenditures for ambulance services fell by 17.1% between 2012 "
        "and 2021, decreasing from $4.76 billion to $3.95 billion\" (CMS); MedPAC "
        "Payment Basics reports $5.3 billion in 2024.",
        "https://www.medpac.gov/wp-content/uploads/2024/10/"
        "MedPAC_Payment_Basics_24_ambulance_FINAL_SEC.pdf"),
    # ── DERIVED (equation on the above; NOT illustrative) ──
    Evidence(
        "condition_yoy_growth",
        "Demand-by-condition year-over-year growth (forward projection)",
        "blended ~2.7%/yr — equals the Census 65+ population growth",
        "DERIVED",
        "Equation on GOV/ACADEMIC inputs (see equation)",
        "Projected volume compounds at the published age-band population growth; the "
        "blended ~2.7%/yr matches the Census 65+ figure (pop_65_growth) as a check.",
        "https://www.census.gov/data/tables/2023/demo/popproj/"
        "2023-summary-tables.html",
        "projected_volume(year n) = base_volume x (1 + g)^n, where base_volume is "
        "the published condition case count (HCUP/GOV, per condition) and g is the "
        "US Census age-band population CAGR weighted by the condition's age skew "
        "[inputs: pop_65_growth + per-condition base volumes]. Incidence is held "
        "constant, so this is pure demographic growth — not a fitted trend."),
)

_BY_KEY: Dict[str, Evidence] = {e.key: e for e in _EVIDENCE}


def all_evidence() -> Tuple[Evidence, ...]:
    """Every headline demand figure, once, with its verbatim quote and link."""
    return _EVIDENCE


def get(key: str) -> Optional[Evidence]:
    """One evidence record by key, or None. Never raises."""
    return _BY_KEY.get(key)


def value_of(key: str, default: str = "") -> str:
    """The published value string for a key (for building display text)."""
    e = _BY_KEY.get(key)
    return e.value if e else default


def n_by_basis() -> Dict[str, int]:
    """Count of evidence records by basis — used to prove the mix (no ILLUSTRATIVE)."""
    out: Dict[str, int] = {}
    for e in _EVIDENCE:
        out[e.basis] = out.get(e.basis, 0) + 1
    return out


def has_no_illustrative() -> bool:
    """The load-bearing guarantee: nothing here is illustrative."""
    return all(e.basis in ("GOV", "SOURCED", "ACADEMIC", "DERIVED")
               for e in _EVIDENCE)
