"""IFT clinical service levels — BLS / ALS1 / ALS2 / SCT-CCT in depth.

The research model behind ``/in-depth-ift-bls-als1-als2-cct``: how the four
ground-ambulance service levels differ in the clinical care delivered, patient
types served, staffing required, equipment needed, operating complexity,
reimbursement treatment, and relevance to interfacility transport (IFT).

Design contract (mirrors the IFT estate, esp. ``ift_demand_evidence``):

  * ZERO illustrative figures. Every fact carries a basis label restricted to
    GOV / ACADEMIC / SOURCED / DERIVED / FRAMEWORK — never ILLUSTRATIVE — and
    every fact carries one or more named sources WITH A LINK. DERIVED numbers
    state their arithmetic; FRAMEWORK entries are authored classification
    logic over cited rules (no invented quantities).
  * Frozen dataclasses, pure functions, degrade-and-never-raise.
  * Reuses (read-only) the existing IFT connector estate:
    ``ift_analytics.ambulance_part_b_utilization`` /
    ``ift_analytics.ambulance_employment`` and the shared
    ``ift_demand_evidence`` registry, so shared numbers cannot drift.

Everything here was verified against the primary source in July 2026; the
verification date matters because the fee-schedule dollars (CY2026), the CY2024
utilization file (published May 2026), and the OEWS wage vintage (May 2025)
roll annually.

Public API:
    service_levels() -> Tuple[ServiceLevel, ...]        # the top table
    classification_framework() -> Tuple[Fact, ...]      # what is classified
    fee_rows() -> Tuple[FeeRow, ...]                    # codes/RVU/$ ladder
    payment_mechanics() -> Tuple[Fact, ...]
    medicare_mix() -> Tuple[MixRow, ...]                # CY2024 by HCPCS
    mix_readings() -> Tuple[Fact, ...]                  # GADCS/MedPAC/NEMSIS
    wage_ladder() -> Tuple[WageRow, ...]                # OEWS May 2025
    workforce_facts() -> Tuple[Fact, ...]
    acuity_progression() -> Tuple[ProgressionRow, ...]
    crew_matrix() -> Tuple[CrewRow, ...]
    equipment_facts() -> Tuple[Fact, ...]
    medication_rules() -> Tuple[Fact, ...]
    necessity_and_denials() -> Tuple[Fact, ...]
    payer_differences() -> Tuple[Fact, ...]
    state_variation() -> Tuple[Fact, ...]
    edge_cases() -> Tuple[EdgeCase, ...]
    misconceptions() -> Tuple[Misconception, ...]
    conclusion_test() -> Conclusion
    connector_reads() -> Dict[str, Any]                 # live-estate hooks
    kpis() -> Dict[str, Any]
    bibliography() -> Tuple[Src, ...]
    n_by_basis() -> Dict[str, int]
    has_no_illustrative() -> bool
    summary() -> Dict[str, Any]
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# Types
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Src:
    """One linked source. ``label`` names publisher + document; ``url`` opens
    the exact document verified in July 2026."""
    label: str
    url: str


@dataclass(frozen=True)
class Fact:
    """One sourced claim. ``basis`` is restricted to the honest set (never
    ILLUSTRATIVE); ``quote`` is a short verbatim excerpt when one exists."""
    text: str
    basis: str                       # GOV | ACADEMIC | SOURCED | DERIVED | FRAMEWORK
    srcs: Tuple[Src, ...]
    quote: str = ""


@dataclass(frozen=True)
class ServiceLevel:
    """One row of the four-level comparison — the slide's top table."""
    key: str                         # BLS | ALS1 | ALS2 | SCT
    name: str
    hcpcs: Tuple[Tuple[str, str, float], ...]   # (code, descriptor, RVU)
    definition: Fact                 # 1. comprehensive definition
    clinical: Tuple[Fact, ...]       # 2. typical clinical needs
    operational: Tuple[Fact, ...]    # 3. typical operational needs
    reimbursement: Tuple[Fact, ...]  # 4. reimbursement differences
    boundary: Fact                   # what separates it from the level below
    use_cases: Tuple[Fact, ...]      # typical IFT use cases


@dataclass(frozen=True)
class FeeRow:
    hcpcs: str
    level: str
    rvu: float
    cy2026_base: float               # national unadjusted, CF $284.56 × RVU
    cy2024_services: Optional[int]   # CMS CY2024 allowed services (suppliers)
    cy2024_avg_allowed: Optional[float]
    cy2024_avg_paid: Optional[float]
    cy2024_providers: Optional[int]
    srcs: Tuple[Src, ...] = ()


@dataclass(frozen=True)
class MixRow:
    hcpcs: str
    level: str
    services: int
    share_pct: float                 # of the six ground transport codes
    avg_allowed: float
    srcs: Tuple[Src, ...] = ()


@dataclass(frozen=True)
class WageRow:
    occupation: str
    soc: str
    employment: int
    median_wage: int
    mean_wage: int
    src: Src = Src("", "")


@dataclass(frozen=True)
class ProgressionRow:
    dimension: str
    bls: str
    als1: str
    als2: str
    sct: str
    srcs: Tuple[Src, ...] = ()


@dataclass(frozen=True)
class CrewRow:
    level: str
    federal_minimum: Fact
    state_examples: Fact
    certifications: Fact


@dataclass(frozen=True)
class EdgeCase:
    scenario: str
    likely_level: str
    determinant: str                 # the key determining fact
    ambiguity: str                   # source of ambiguity / alternative
    basis: str
    srcs: Tuple[Src, ...] = ()


@dataclass(frozen=True)
class Misconception:
    myth: str
    reality: str
    srcs: Tuple[Src, ...] = ()


@dataclass(frozen=True)
class Conclusion:
    statement: str
    verdict: str                     # SUPPORTED / REFUTED / SUPPORTED WITH REFINEMENTS
    support: Tuple[Fact, ...]
    refinements: Tuple[Fact, ...]


# ─────────────────────────────────────────────────────────────────────────────
# Shared sources (each URL verified July 2026)
# ─────────────────────────────────────────────────────────────────────────────

S_414_605 = Src("42 CFR 414.605 — definitions (eCFR)",
                "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/"
                "part-414/subpart-H/section-414.605")
S_410_40 = Src("42 CFR 410.40 — ambulance coverage & medical necessity (eCFR)",
               "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/"
               "part-410/subpart-B/section-410.40")
S_410_41 = Src("42 CFR 410.41 — vehicle & crew requirements (eCFR)",
               "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/"
               "part-410/subpart-B/section-410.41")
S_414_610 = Src("42 CFR 414.610 — AFS payment basis (eCFR)",
                "https://www.ecfr.gov/current/title-42/section-414.610")
S_BPM10 = Src("Medicare Benefit Policy Manual, Ch. 10 (CMS Pub. 100-02)",
              "https://www.cms.gov/regulations-and-guidance/guidance/manuals/"
              "downloads/bp102c10.pdf")
S_CLM15 = Src("Medicare Claims Processing Manual, Ch. 15 (CMS Pub. 100-04)",
              "https://www.cms.gov/regulations-and-guidance/guidance/manuals/"
              "downloads/clm104c15.pdf")
S_AFS_PUF = Src("CMS Ambulance Fee Schedule public use files (CY2026)",
                "https://www.cms.gov/medicare/payment/fee-schedules/ambulance/"
                "ambulance-fee-schedule-public-use-files")
S_MEDPAC26 = Src("MedPAC June 2026 Report to Congress, Ch. 6 (ground ambulance)",
                 "https://www.medpac.gov/wp-content/uploads/2026/06/"
                 "Jun26_Ch6_MedPAC_Report_To_Congress_SEC.pdf")
S_MEDPAC13 = Src("MedPAC June 2013 mandated report, Ch. 7 (ambulance)",
                 "https://www.medpac.gov/wp-content/uploads/import_data/"
                 "scrape_files/docs/default-source/reports/chapter-7-mandated-"
                 "report-medicare-payment-for-ambulance-services-june-2013-"
                 "report-.pdf")
S_MEDPAC25 = Src("MedPAC March 2025 mandated-report slides (ground ambulance)",
                 "https://www.medpac.gov/wp-content/uploads/2025/03/"
                 "Ambulance-MedPAC-03.25_SEC.pdf")
S_AIF26 = Src("CMS Transmittal 13464 / CR 14269 — CY2026 AIF (Nov 2025)",
              "https://www.cms.gov/files/document/r13464cp.pdf")
S_CAA26 = Src("Consolidated Appropriations Act 2026 §6203 — add-on extension "
              "(Senate Finance section-by-section)",
              "https://www.finance.senate.gov/imo/media/doc/"
              "consolidated_appropriations_act_2026_section-by-section.pdf")
S_GAO13_6 = Src("GAO-13-6 — Ambulance Providers: Costs and Medicare Margins "
                "Varied Widely (Oct 2012)",
                "https://www.gao.gov/products/gao-13-6")
S_GADCS = Src("CMS/RAND GADCS report — Year 1 + Year 2 cohorts (Dec 2024)",
              "https://www.cms.gov/files/document/medicare-ground-ambulance-"
              "data-collection-system-gadcs-report-year-1-and-year-2-cohort-"
              "analysis.pdf")
S_OIG15 = Src("HHS OIG OEI-09-12-00351 — Inappropriate Payments and "
              "Questionable Billing for Ambulance Transports (2015)",
              "https://oig.hhs.gov/oei/reports/oei-09-12-00351.pdf")
S_MEDPOP = Src("CMS Medicare Physician & Other Practitioners — by Geography "
               "and Service (CY2024, published May 2026)",
               "https://data.cms.gov/provider-summary-by-type-of-service/"
               "medicare-physician-other-practitioners/"
               "medicare-physician-other-practitioners-by-geography-and-service")
S_SCOPE19 = Src("National EMS Scope of Practice Model 2019 (NHTSA/NASEMSO)",
                "https://www.ems.gov/assets/"
                "National_EMS_Scope_of_Practice_Model_2019.pdf")
S_EQUIP20 = Src("Recommended Essential Equipment for BLS and ALS Ground "
                "Ambulances 2020 (NAEMSP/ACS-COT/AAP/ENA/NASEMSO)",
                "https://emscimprovement.center/documents/1316/"
                "Recommended_Equipment_for_BLS__ALS_Ambulances_2020.pdf")
S_CAMTS = Src("CAMTS Accreditation Standards, 12th Edition (2022)",
              "https://cdn.prod.website-files.com/65de10e0a5df356d60f6b987/"
              "68793613ef5467e9754953c3_CAMTS%2012th%20Edition%20free%20"
              "download.pdf")
S_CAMTS_N = Src("CAMTS accredited-services list (157 as of Jan 12, 2026)",
                "https://www.camts.org/accreditedservices")
S_NJ = Src("N.J.A.C. 8:41 — NJ MICU / SCTU staffing rules",
           "https://www.nj.gov/health/ems/documents/reg-enforcement/"
           "njac841r.pdf")
S_TX = Src("25 TAC §157.11 — Texas EMS provider licensure (BLS→MICU)",
           "http://txrules.elaws.us/rule/title25_chapter157_sec.157.11")
S_PA = Src("28 Pa. Code §1027.39 — PA critical care transport service",
           "https://www.pacodeandbulletin.gov/Display/pacode?file=%2Fsecure%2F"
           "pacode%2Fdata%2F028%2Fchapter1027%2Fs1027.39.html")
S_MD = Src("COMAR 30.09.14.04 — Maryland SCT staffing",
           "http://mdrules.elaws.us/comar/30.09.14.04")
S_PACEP = Src("PACEP Interfacility Transport Resource Document (June 2018)",
              "https://www.ptsf.org/wp-content/uploads/2020/10/"
              "PACEP-Interfacility_Transport_Resource_Document_June_2018.pdf")
S_EMTALA = Src("42 CFR 489.24(e) — EMTALA transfer requirements (eCFR)",
               "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-G/"
               "part-489/subpart-B/section-489.24")
S_OEWS_EMT = Src("BLS OEWS May 2025 — EMTs (SOC 29-2042)",
                 "https://www.bls.gov/oes/current/oes292042.htm")
S_OEWS_MEDIC = Src("BLS OEWS May 2025 — Paramedics (SOC 29-2043)",
                   "https://www.bls.gov/oes/current/oes292043.htm")
S_OEWS_RN = Src("BLS OEWS May 2025 — Registered Nurses (SOC 29-1141)",
                "https://www.bls.gov/oes/current/oes291141.htm")
S_OEWS_RT = Src("BLS OEWS May 2025 — Respiratory Therapists (SOC 29-1126)",
                "https://www.bls.gov/oes/current/oes291126.htm")
S_OOH = Src("BLS Occupational Outlook Handbook — EMTs and Paramedics",
            "https://www.bls.gov/ooh/healthcare/emts-and-paramedics.htm")
S_NEMSIS24 = Src("NEMSIS National EMS Data Report 2024",
                 "https://nemsis.org/wp-content/uploads/2025/08/"
                 "NEMSIS-End-of-Year-Report-2024.pdf")
S_NREMT = Src("NREMT national certification dashboard",
              "https://www.nremt.org/maps")
S_AAA_TURN = Src("AAA/Newton 360 EMS turnover research (2024 study)",
                 "https://ambulance.org/sp_product/2024-turnover/")
S_AAA_1PG = Src("AAA EMS-shortage one-pager (2025) — turnover 20-30%",
                "https://ambulance.org/wp-content/uploads/2025/12/"
                "10-30-2025-EMS-Shortage-NDAA-One-Pager.pdf")
S_HCCI = Src("HCCI — commercial ground-ambulance prices ~2x Medicare (2022)",
             "https://healthcostinstitute.org/hcci-originals-dropdown/"
             "all-hcci-reports/commercial-prices-for-ground-ambulance-are-"
             "double-medicare-rates")
S_HA22 = Src("Health Affairs 2022 — ground-ambulance surprise billing",
             "https://www.healthaffairs.org/doi/10.1377/hlthaff.2022.00738")
S_GAPB = Src("GAPB Advisory Committee report (Mar 2024, CMS)",
             "https://www.cms.gov/files/document/report-advisory-committee-"
             "ground-ambulance-and-patient-billing.pdf")
S_ALABDALI = Src("Alabdali et al., Air Med J 2017 — paramedic critical-care "
                 "IFT adverse events (systematic review)",
                 "https://pubmed.ncbi.nlm.nih.gov/28499680/")
S_JEYARAJU = Src("Jeyaraju et al., Air Med J 2021 — interhospital-transport "
                 "adverse events meta-analysis",
                 "https://pubmed.ncbi.nlm.nih.gov/34535244/")
S_NIDDK = Src("NIDDK/USRDS — US kidney disease statistics",
              "https://www.niddk.nih.gov/health-information/health-statistics/"
              "kidney-disease")
S_HERNANDEZ = Src("Hernandez-Boussard et al., J Patient Saf 2017 — "
                  "interhospital transfers (2009 NIS)",
                  "https://pubmed.ncbi.nlm.nih.gov/25397857/")
S_MUELLER = Src("Mueller et al., J Hosp Med 2017 — Medicare interhospital "
                "transfers",
                "https://pubmed.ncbi.nlm.nih.gov/28574533/")
S_HCUP205 = Src("HCUP Statistical Brief #205 — discharge disposition (2013)",
                "https://www.ncbi.nlm.nih.gov/books/NBK373736/figure/"
                "sb205.f1/")
S_NEO = Src("Pediatric Emergency Care — national neonatal/pediatric "
            "transport-team survey",
            "https://pubmed.ncbi.nlm.nih.gov/30399063/")
S_ACEP = Src("ACEP policy — Appropriate Interfacility Patient Transfer "
             "(rev. 2022)",
             "https://www.acep.org/patient-care/policy-statements/"
             "appropriate-interfacility-patient-transfer/")
S_ENA = Src("ENA position — Interfacility Transfer of Emergency Care Patients",
            "https://d1w2w5dpazlk1u.cloudfront.net/pdf/"
            "9c1382ca-d14d-47d2-8c3a-5ab575223922.pdf")
S_BCEN = Src("BCEN — CTRN/CFRN transport nursing certifications",
             "https://bcen.org/ctrn/")
S_IBSC = Src("IBSC — FP-C / CCP-C critical-care paramedic certifications",
             "https://www.ibscertifications.org/")
S_GVS = Src("CAAS Ground Vehicle Standard v4.0 (effective July 1, 2025)",
            "https://www.groundvehiclestandard.org/")
S_NFPA = Src("NFPA 1917 — Standard for Automotive Ambulances",
             "https://www.nfpa.org/codes-and-standards/nfpa-1917-standard-"
             "development/1917")
S_RSNAT = Src("CMS — prior authorization for Repetitive, Scheduled "
              "Non-Emergent Ambulance Transport (RSNAT)",
              "https://www.cms.gov/data-research/monitoring-programs/"
              "medicare-fee-service-compliance-programs/prior-authorization-"
              "and-pre-claim-review-initiatives/prior-authorization-repetitive-"
              "scheduled-non-emergent-ambulance-transport")
S_STATPEARLS = Src("StatPearls — Aeromedical Transport (2017 ADAMS figures)",
                   "https://www.ncbi.nlm.nih.gov/books/NBK518986/")
S_R236BP = Src("CMS Transmittal R236BP — BPM ch. 10 §30.1.1 level-of-service "
               "definitions (2017)",
               "https://www.cms.gov/Regulations-and-Guidance/Guidance/"
               "Transmittals/2017Downloads/R236BP.pdf")
S_MLN_RSNAT = Src("CMS MLN6805343 — RSNAT prior-authorization fact sheet "
                  "(Jan 2026)",
                  "https://www.cms.gov/files/document/mln6805343-repetitive-"
                  "scheduled-non-emergent-ambulance-transport-prior-"
                  "authorization-model.pdf")
S_AB02131 = Src("CMS Program Memorandum AB-02-131 — treat-no-transport not "
                "covered (2002)",
                "https://www.cms.gov/Regulations-and-Guidance/Guidance/"
                "Transmittals/downloads/AB02131.pdf")


# ─────────────────────────────────────────────────────────────────────────────
# 1 — Classification framework (what exactly is being classified)
# ─────────────────────────────────────────────────────────────────────────────

def classification_framework() -> Tuple[Fact, ...]:
    """§1 of the question architecture: the thing being classified is the
    LEVEL OF SERVICE FURNISHED (and, for coverage, required) — not the
    diagnosis, not the destination, not the crew that happened to show up."""
    return (
        Fact("Medicare classifies the SERVICE FURNISHED, not the patient: the "
             "seven ground levels (BLS, BLS-emergency, ALS1, ALS1-emergency, "
             "ALS2, SCT, paramedic intercept) are defined in regulation by "
             "what is done and who must do it — an assessment, a count of "
             "medication administrations, named procedures, or care beyond "
             "paramedic scope.", "GOV", (S_414_605,)),
        Fact("Coverage is a separate test from level: 42 CFR 410.40 pays for "
             "ambulance transport only when other means of transportation are "
             "contraindicated by the beneficiary's condition — medical "
             "necessity is judged on the condition at the time of transport, "
             "whatever level is billed.", "GOV", (S_410_40, S_BPM10)),
        Fact("Clinical level and billed level can legitimately diverge: an "
             "ALS assessment performed as part of an emergency response "
             "justifies the ALS1-emergency base rate even when the patient "
             "turns out to need no ALS intervention; conversely, dispatching "
             "a paramedic crew to a non-emergency trip does not by itself "
             "make the trip billable as ALS — 'payment is based on the "
             "level of service provided, not on the vehicle used,' and "
             "even where local government mandates ALS responses, Medicare "
             "pays only for the level furnished and medically necessary.",
             "GOV", (S_414_605, S_BPM10, S_CLM15, S_R236BP),
             quote="Payment is based on the level of service provided, not "
                   "on the vehicle used."),
        Fact("Emergency status is a dispatch-time fact, not a clinical "
             "one: an emergency response means 'responding immediately at "
             "the BLS or ALS1 level of service to a 911 call or the "
             "equivalent,' judged against the local dispatch protocol — "
             "where dispatch was inconsistent with protocol, the patient's "
             "condition at the scene determines the payable level.",
             "GOV", (S_414_605, S_R236BP),
             quote="Emergency response means responding immediately at the "
                   "BLS or ALS1 level of service to a 911 call or the "
                   "equivalent in areas without a 911 call system."),
        Fact("The billed level is also not the paid level: claims are "
             "downcoded or denied on medical-necessity review — HHS OIG found "
             "$24M paid in one half-year for transports not meeting program "
             "requirements and flagged transport-level/destination mismatches "
             "($7.1M) as a marker of questionable billing.",
             "GOV", (S_OIG15,)),
        Fact("The four-level ladder is therefore a COMBINATION continuum — a "
             "reimbursement-code ladder (HCPCS/RVUs), a clinical-intervention "
             "ladder (what must happen in transit), and a licensing/"
             "scope-of-practice ladder (who may do it) stacked on top of each "
             "other. They correlate but are set by different authorities: CMS "
             "fixes the payment definitions; states fix scope of practice and "
             "vehicle/service licensure.", "FRAMEWORK",
             (S_414_605, S_SCOPE19)),
        Fact("Final authority differs by question: the sending physician/"
             "practitioner orders and certifies the transport (physician "
             "certification statement for non-emergency transports); the "
             "ambulance supplier determines what service it can legally "
             "furnish under state scope rules; the payer determines what it "
             "will pay for — retrospectively for most claims, prospectively "
             "for repetitive non-emergency transports under RSNAT prior "
             "authorization.", "GOV", (S_410_40, S_RSNAT)),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2 — The four service levels (the top table)
# ─────────────────────────────────────────────────────────────────────────────

def service_levels() -> Tuple[ServiceLevel, ...]:
    bls = ServiceLevel(
        key="BLS", name="Basic Life Support",
        hcpcs=(("A0428", "BLS, non-emergency", 1.00),
               ("A0429", "BLS, emergency", 1.60)),
        definition=Fact(
            "Transport plus medically necessary supplies and services at the "
            "EMT-Basic level of care: the vehicle must be staffed by at least "
            "two people, at least one of whom is state-certified as an EMT "
            "and legally authorized to operate all lifesaving equipment on "
            "board. BLS is care WITHIN the EMT scope — assessment, oxygen, "
            "suction, CPR/AED, basic airway adjuncts, hemorrhage control, "
            "glucose monitoring, and a short list of assisted/administered "
            "medications (oral glucose, aspirin, epinephrine auto-injector, "
            "naloxone). It does not include IV therapy or cardiac "
            "monitoring.", "GOV", (S_414_605, S_410_41, S_SCOPE19),
            quote="Basic life support (BLS) means transportation by ground "
                  "ambulance vehicle and medically necessary supplies and "
                  "services, plus the provision of BLS ambulance services. "
                  "The ambulance must be staffed by at least two people... "
                  "at least one of the staff members must be certified, at "
                  "a minimum, as an emergency medical technician-basic "
                  "(EMT-Basic)..."),
        clinical=(
            Fact("Typical patient: medically stable, but ambulance transport "
                 "is required because other means are contraindicated — "
                 "bed-confined, fall/aspiration risk, needs supervision or "
                 "oxygen en route, or must remain on a stretcher.",
                 "GOV", (S_410_40,)),
            Fact("Permitted in-transit care (2019 national scope model): "
                 "vital signs, pulse oximetry, oxygen therapy, BVM "
                 "ventilation, CPAP, suction, AED defibrillation, CPR, "
                 "12-lead ECG acquisition/transmission (not interpretation), "
                 "blood-glucose monitoring, hemorrhage control; EMT "
                 "medications limited to oral glucose, aspirin, epinephrine "
                 "auto-injector, naloxone, inhaled bronchodilators, and "
                 "assisting the patient's own prescribed drugs.",
                 "GOV", (S_SCOPE19,)),
            Fact("Not permitted at BLS under the national model: initiating "
                 "or maintaining IV lines or IV medications, cardiac "
                 "monitoring, advanced airways. Pennsylvania's interfacility "
                 "guidance is explicit: 'EMTs do not provide intravenous or "
                 "intraosseous therapy. BLS transports are indicated for "
                 "stable patients who do not require medications or cardiac "
                 "monitoring.'", "GOV", (S_SCOPE19, S_PACEP),
                 quote="EMTs do not provide intravenous or intraosseous "
                       "therapy. BLS transports are indicated for stable "
                       "patients who do not require medications or cardiac "
                       "monitoring."),
        ),
        operational=(
            Fact("Crew floor is the federal minimum: two crew, ≥1 EMT-Basic "
                 "(42 CFR 410.41); EMTs are the deepest labor pool — 399,868 "
                 "nationally certified EMTs (66.9% of all NREMT-certified "
                 "clinicians) vs 149,643 paramedics.",
                 "GOV", (S_410_41, S_NREMT)),
            Fact("Cheapest labor per unit-hour: EMT median wage $44,470 "
                 "(May 2025 OEWS) vs $60,600 for paramedics and $97,550 for "
                 "RNs — the arithmetic behind BLS being the scalable, "
                 "price-competitive service line.", "GOV",
                 (S_OEWS_EMT, S_OEWS_MEDIC, S_OEWS_RN)),
            Fact("Equipment floor is the BLS ambulance list (AED, airway "
                 "adjuncts, suction, oxygen, BVM, tourniquets, glucometer, "
                 "pulse oximeter) — no monitor/defibrillator, no infusion "
                 "pumps, no ventilator.", "GOV", (S_EQUIP20,)),
            Fact("Highest-volume, most schedulable book: discharge legs "
                 "(hospital→SNF/IRF/home) and recurring dialysis dominate "
                 "non-emergency BLS; Medicare's repetitive non-emergent "
                 "transports are subject to nationwide RSNAT prior "
                 "authorization.", "GOV", (S_MEDPAC13, S_RSNAT)),
        ),
        reimbursement=(
            Fact("HCPCS A0428 (non-emergency, RVU 1.00 — the fee-schedule "
                 "anchor) and A0429 (emergency, RVU 1.60). CY2026 national "
                 "unadjusted base: $284.56 and $455.30 + $9.15/mile.",
                 "GOV", (S_414_610, S_AFS_PUF, S_MEDPAC26)),
            Fact("CY2024 Medicare supplier claims: 2,956,154 A0428 services "
                 "(avg allowed $260.65) and 2,608,184 A0429 (avg allowed "
                 "$446.94) — BLS = 57.7% of the six ground transport codes.",
                 "GOV", (S_MEDPOP,)),
            Fact("Highest denial/downcode exposure of the ladder: OIG found "
                 "questionable billing concentrated in non-emergency BLS "
                 "(especially dialysis); MedPAC recommended targeted "
                 "medical-necessity edits for BLS non-emergency.",
                 "GOV", (S_OIG15, S_MEDPAC13)),
            Fact("Dialysis carve-down: non-emergency BLS transports to/from "
                 "dialysis (A0428 with a G or J modifier) are paid at a 23% "
                 "REDUCTION since Oct 1, 2018 (42 CFR 414.610(c)(8)) — "
                 "Congress's response to the dialysis-transport growth OIG "
                 "and MedPAC documented.", "GOV",
                 (S_414_610, S_CLM15, S_MEDPAC13)),
        ),
        boundary=Fact(
            "Boundary vs non-ambulance transport (wheelchair van/stretcher "
            "car/NEMT): Medicare pays for an AMBULANCE only when other means "
            "of transport are contraindicated by the patient's condition; "
            "bed confinement (unable to get up without assistance, unable "
            "to ambulate, unable to sit in a chair or wheelchair) is a "
            "factor but 'is not the sole criterion' — the manual is "
            "blunter: by itself it is 'neither sufficient nor is it "
            "necessary.'",
            "GOV", (S_410_40, S_BPM10),
            quote="Bed-confinement, by itself, is neither sufficient nor is "
                  "it necessary to determine the coverage for Medicare "
                  "ambulance benefits."),
        use_cases=(
            Fact("Hospital→SNF / IRF / LTCH / home discharge legs; "
                 "SNF→hospital returns; recurring dialysis (2.3M Medicare "
                 "dialysis transports in 2011 — 15% of all transports, 97% "
                 "of them BLS non-emergency); behavioral-health transfers; "
                 "bed-confined outpatient appointments; stable oxygen-"
                 "dependent moves; isolation and bariatric moves with the "
                 "right equipment.", "GOV",
                 (S_MEDPAC13, S_NIDDK, S_410_40)),
        ),
    )

    als1 = ServiceLevel(
        key="ALS1", name="Advanced Life Support, Level 1",
        hcpcs=(("A0426", "ALS1, non-emergency", 1.20),
               ("A0427", "ALS1, emergency", 1.90)),
        definition=Fact(
            "Transport plus the provision of an ALS ASSESSMENT or at least "
            "one ALS INTERVENTION. An ALS assessment is an assessment "
            "performed by an ALS crew as part of an emergency response that "
            "was necessary because the patient's reported condition at "
            "dispatch required ALS-level evaluation — and it qualifies even "
            "if the assessment finds no ALS intervention is needed. An ALS "
            "intervention is a procedure that state law requires to be "
            "furnished by ALS personnel (e.g., IV therapy, medicated "
            "infusions, cardiac monitoring, most parenteral medications); "
            "'ALS personnel' means a clinician trained to at least the "
            "EMT-Intermediate or paramedic level.",
            "GOV", (S_414_605, S_R236BP),
            quote="Advanced life support (ALS) assessment is an assessment "
                  "performed by an ALS crew as part of an emergency response "
                  "that was necessary because the patient's reported "
                  "condition at the time of dispatch was such that only an "
                  "ALS crew was qualified to perform the assessment. An ALS "
                  "assessment does not necessarily result in a determination "
                  "that the patient requires an ALS level of service."),
        clinical=(
            Fact("Typical patient: stable-but-at-risk — needs continuous "
                 "cardiac monitoring, an IV medication, advanced-airway "
                 "readiness, seizure watch, or paramedic-level serial "
                 "reassessment during the move.", "FRAMEWORK",
                 (S_414_605, S_PACEP)),
            Fact("The paramedic scope adds (over EMT): IV/IO access, "
                 "medicated infusion maintenance, 12-lead interpretation, "
                 "manual defibrillation/cardioversion, transcutaneous "
                 "pacing, endotracheal intubation, needle chest "
                 "decompression, chest-tube and central-line monitoring, "
                 "blood-product infusion maintenance.", "GOV", (S_SCOPE19,)),
            Fact("One qualifying element is enough: a single medically "
                 "necessary ALS intervention (one IV medication, cardiac "
                 "monitoring required by the patient's condition) makes the "
                 "trip ALS1; it stays ALS1 until the ALS2 triggers (≥3 IV "
                 "med administrations or a listed procedure) are met.",
                 "GOV", (S_414_605,)),
        ),
        operational=(
            Fact("Crew: the ALS vehicle must be staffed by ≥2 people, at "
                 "least one certified as a paramedic or an EMT authorized by "
                 "the state to perform the ALS services (42 CFR 410.41); the "
                 "typical configuration is one paramedic + one EMT.",
                 "GOV", (S_410_41,)),
            Fact("Paramedics are the binding constraint: 100,610 employed "
                 "(May 2025 OEWS) vs 180,510 EMTs; annual EMT/paramedic "
                 "turnover runs 20-30% (AAA/Newton 360), so ALS capacity is "
                 "recruiting-limited, not vehicle-limited.", "GOV",
                 (S_OEWS_MEDIC, S_OEWS_EMT, S_AAA_1PG)),
            Fact("Equipment step-up over BLS: monitor/defibrillator with "
                 "3-lead monitoring, 12-lead acquisition and pacing, "
                 "laryngoscopy, supraglottic airways, waveform capnography, "
                 "chest-decompression needles, IV/IO supplies, crystalloids "
                 "+ pressure infusion, and a stocked medication kit.",
                 "GOV", (S_EQUIP20,)),
        ),
        reimbursement=(
            Fact("HCPCS A0426 (non-emergency, RVU 1.20) and A0427 "
                 "(emergency, RVU 1.90). CY2026 national unadjusted base: "
                 "$341.47 and $540.66.", "GOV",
                 (S_414_610, S_AFS_PUF, S_MEDPAC26)),
            Fact("CY2024 Medicare supplier claims: A0427 is the single "
                 "biggest transport code — 3,697,421 services (avg allowed "
                 "$522.51); non-emergency A0426 is small (218,943, avg "
                 "$327.72) — scheduled interfacility ALS is a thin book "
                 "next to emergency ALS.", "GOV", (S_MEDPOP,)),
            Fact("The emergency/non-emergency split matters more to revenue "
                 "than the BLS/ALS split: A0427 pays 1.9x the BLS anchor vs "
                 "1.2x for A0426 — response mode, not just acuity, drives "
                 "the RVU.", "GOV", (S_414_610,)),
        ),
        boundary=Fact(
            "Boundary vs BLS: something during (or justifying) the response "
            "must exceed EMT scope — an ALS assessment necessary at dispatch "
            "or ≥1 ALS intervention. A paramedic merely being on board a "
            "non-emergency trip does not lift a BLS-level patient to ALS "
            "billing; on an appropriately dispatched EMERGENCY, a completed "
            "ALS assessment covers the trip at the ALS-emergency level even "
            "if no ALS intervention follows.", "GOV",
            (S_414_605, S_R236BP),
            quote="...if the ALS crew completes an ALS Assessment, the "
                  "services provided by the ambulance transportation service "
                  "provider or supplier shall be covered at the ALS "
                  "emergency level, regardless of whether the patient "
                  "required ALS intervention services during the "
                  "transport..."),
        use_cases=(
            Fact("Community hospital → tertiary-center transfers with "
                 "cardiac monitoring; ED → specialty hospital moves; "
                 "patients on one IV medication (e.g., antibiotics); "
                 "post-stabilization returns still needing paramedic "
                 "monitoring; seizure- or arrhythmia-watch transfers; "
                 "higher-oxygen-support moves short of ventilation.",
                 "FRAMEWORK", (S_414_605, S_PACEP)),
        ),
    )

    als2 = ServiceLevel(
        key="ALS2", name="Advanced Life Support, Level 2",
        hcpcs=(("A0433", "ALS2", 2.75),),
        definition=Fact(
            "Transport plus EITHER (a) at least three separate "
            "administrations of one or more medications by IV push/bolus or "
            "continuous infusion — crystalloid, hypotonic, isotonic and "
            "hypertonic solutions (dextrose, normal saline, Ringer's "
            "lactate) explicitly do not count — OR (b) at least one of "
            "EIGHT named procedures: manual defibrillation/cardioversion, "
            "endotracheal intubation, central venous line, cardiac pacing, "
            "chest decompression, surgical airway, intraosseous line, or — "
            "added effective CY2025 (89 FR 98559) — prehospital blood "
            "transfusion (whole blood, PRBCs, plasma, or PRBCs+plasma).",
            "GOV", (S_414_605, S_BPM10),
            quote="...the administration of at least three medications by "
                  "intravenous push/bolus or by continuous infusion, "
                  "excluding crystalloid, hypotonic, isotonic, and "
                  "hypertonic solutions (Dextrose, Normal Saline, Ringer's "
                  "Lactate); or... the provision of at least one of the "
                  "following ALS procedures: (1) Manual defibrillation/"
                  "cardioversion. (2) Endotracheal intubation. (3) Central "
                  "venous line. (4) Cardiac pacing. (5) Chest "
                  "decompression. (6) Surgical airway. (7) Intraosseous "
                  "line. (8) Prehospital blood transfusion..."),
        clinical=(
            Fact("Typical patient: actively unstable or resuscitated-and-"
                 "fragile — active arrhythmia needing pacing/cardioversion, "
                 "airway secured by intubation, multiple pressor/sedation/"
                 "antiarrhythmic pushes en route. ALS2 is defined by "
                 "DISCRETE interventions, not by continuous specialty "
                 "management.", "FRAMEWORK", (S_414_605,)),
            Fact("Repeat doses count — gaming does not: the manual counts "
                 "'three separate administrations of one or more "
                 "medications' (so repeat doses of the same drug qualify), "
                 "but 'it is not appropriate to administer a medication in "
                 "divided doses in order to meet the ALS2 level of "
                 "payment'; crystalloid volume never qualifies no matter "
                 "the rate.", "GOV", (S_414_605, S_BPM10),
                 quote="It is not appropriate to administer a medication in "
                       "divided doses in order to meet the ALS2 level of "
                       "payment."),
        ),
        operational=(
            Fact("Same federal crew floor as ALS1 (paramedic-staffed ALS "
                 "vehicle) — ALS2 is a payment tier, not a separate federal "
                 "licensure tier; several states do license higher tiers "
                 "(e.g., Texas MICU) that map onto this acuity.",
                 "GOV", (S_410_41, S_TX)),
            Fact("Operationally rare: 85,087 Medicare ALS2 claims in CY2024 "
                 "— 0.9% of ground transports — versus 3.7M ALS1-emergency; "
                 "too thin to schedule dedicated ALS2 units, so it is "
                 "served by the ALS fleet.", "GOV", (S_MEDPOP,)),
        ),
        reimbursement=(
            Fact("HCPCS A0433, RVU 2.75 — one code, no emergency/"
                 "non-emergency split: the claims manual states ALS2 (like "
                 "SCT) 'assume[s] an emergency condition.' CY2026 national "
                 "unadjusted base $782.54; CY2024 average allowed $753.58.",
                 "GOV", (S_414_610, S_MEDPOP, S_CLM15),
                 quote="NOTE: PI, ALS2, SCT, FW, and RW assume an emergency "
                       "condition and do not require an emergency "
                       "designator."),
            Fact("2.3x the ALS1 non-emergency rate for the same crew and "
                 "vehicle — the margin is in the qualifying documentation "
                 "(med administrations logged, procedure recorded), which "
                 "is also the audit exposure.", "DERIVED",
                 (S_414_610, S_OIG15)),
        ),
        boundary=Fact(
            "Boundary vs ALS1: a counting rule, not a judgment call — the "
            "third qualifying medication administration or the first listed "
            "procedure flips the code. Boundary vs SCT: everything in ALS2 "
            "is still within paramedic scope; the moment required care "
            "exceeds paramedic scope, the trip is SCT.", "GOV",
            (S_414_605,)),
        use_cases=(
            Fact("ED → trauma/cardiac-center transfers mid-resuscitation; "
                 "intubated-but-paramedic-manageable patients; active "
                 "arrhythmia requiring pacing or cardioversion en route; "
                 "transfers on multiple pushed medications. In practice "
                 "mostly emergency-origin; a scheduled ALS2 is unusual.",
                 "FRAMEWORK", (S_414_605, S_MEDPOP)),
        ),
    )

    sct = ServiceLevel(
        key="SCT", name="Specialty Care Transport (operating term: CCT)",
        hcpcs=(("A0434", "SCT", 3.25),),
        definition=Fact(
            "INTERFACILITY transport of a critically injured or ill "
            "beneficiary at a level of service beyond the scope of the "
            "EMT-Paramedic — necessary when the patient's condition requires "
            "ongoing care that must be furnished by one or more health "
            "professionals in an appropriate specialty area: nursing, "
            "emergency medicine, respiratory care, cardiovascular care, or "
            "a paramedic with additional training. 'Critical care "
            "transport' and 'mobile ICU' are the industry/state operating "
            "terms for the same tier; SCT is the Medicare payment term.",
            "GOV", (S_414_605,),
            quote="Specialty care transport (SCT) means interfacility "
                  "transportation of a critically injured or ill beneficiary "
                  "by a ground ambulance vehicle... at a level of service "
                  "beyond the scope of the EMT-Paramedic. SCT is necessary "
                  "when a beneficiary's condition requires ongoing care that "
                  "must be furnished by one or more health professionals in "
                  "an appropriate specialty area..."),
        clinical=(
            Fact("Typical patient: dependent on continuously managed "
                 "life-sustaining therapy — ventilator with active "
                 "management, multiple/titratable vasoactive infusions, "
                 "sedation/paralytics, invasive monitoring, balloon pump or "
                 "VAD support, neonatal isolette. The defining feature is "
                 "CONTINUOUS management beyond paramedic scope, not any one "
                 "procedure.", "FRAMEWORK", (S_414_605, S_CAMTS)),
            Fact("Adverse-event risk is materially higher: pooled medical "
                 "adverse-event rate of 11% (95% CI 7.5-16%) across 14,969 "
                 "critically ill interhospital transports; paramedic-crewed "
                 "critical-care IFT studies report 5.1-18%.", "ACADEMIC",
                 (S_JEYARAJU, S_ALABDALI)),
        ),
        operational=(
            Fact("Crew is the product: CAMTS critical-care standard requires "
                 "≥2 medical personnel plus a vehicle operator, with a "
                 "primary care provider (physician, APN, RN, PA, or "
                 "paramedic) holding ≥3 years / 4,000 hours of ICU/ED "
                 "critical-care experience; transport-specific certifications "
                 "(CTRN/CFRN for nurses, FP-C/CCP-C for paramedics) are "
                 "required after two years.", "GOV",
                 (S_CAMTS, S_BCEN, S_IBSC)),
            Fact("Scarcest labor on the ladder: RN median wage $97,550 — "
                 "2.2x an EMT — and specialty teams (e.g., neonatal: most "
                 "commonly RN + respiratory therapist) must be credentialed, "
                 "simulated, and kept current, so SCT capacity concentrates "
                 "in a few programs (157 CAMTS-accredited services "
                 "nationally as of Jan 2026).", "GOV",
                 (S_OEWS_RN, S_NEO, S_CAMTS_N)),
            Fact("Equipment step-up: transport ventilator, multi-channel "
                 "infusion pumps, invasive-pressure monitoring, device power "
                 "and oxygen redundancy — plus state licensure of the CCT "
                 "service itself in several states.", "FRAMEWORK",
                 (S_CAMTS, S_PA, S_NJ)),
        ),
        reimbursement=(
            Fact("HCPCS A0434, RVU 3.25 — the top of the ground ladder; "
                 "CY2026 national unadjusted base $924.82; CY2024 average "
                 "allowed $918.36. SCT is interfacility BY DEFINITION — a "
                 "scene response cannot be SCT.", "GOV",
                 (S_414_610, S_MEDPOP, S_414_605)),
            Fact("Lowest volume: 71,279 Medicare claims in CY2024 (0.7% of "
                 "ground transports, 1,181 billing suppliers vs 9,430 for "
                 "BLS-emergency) — strategically important, definitionally "
                 "IFT, but a thin book. OIG flagged $4.3M of SCT billed "
                 "between non-hospital origins/destinations as improper.",
                 "GOV", (S_MEDPOP, S_OIG15)),
            Fact("'Interfacility' is strictly defined for SCT payment: "
                 "BOTH origin and destination must be a Medicare-"
                 "participating hospital or SNF (or a provider-based "
                 "hospital facility) — a scene, home, or clinic endpoint "
                 "disqualifies the SCT code.", "GOV", (S_R236BP,),
                 quote="For purposes of SCT payment, an interfacility "
                       "transportation is one in which the origin and "
                       "destination are one of the following: a hospital or "
                       "skilled nursing facility that participates in the "
                       "Medicare program or a hospital-based facility that "
                       "meets Medicare's requirements for provider-based "
                       "status."),
        ),
        boundary=Fact(
            "Boundary vs ALS2: not a count of interventions but WHO the "
            "care requires — the moment required ongoing care exceeds "
            "EMT-Paramedic scope (titratable vasoactives, complex vent "
            "management, blood products in many states), the trip is SCT. "
            "Because paramedic scope varies by state, the ALS2/SCT line "
            "moves at state borders: New Jersey requires an RN on every "
            "SCT unit ('under no circumstances' may a paramedic "
            "substitute), while Pennsylvania and Maryland allow specially "
            "trained critical-care paramedics. CMS is explicit about the "
            "state-relativity — and 'additional training' means the "
            "specific training a state requires for specialty-care "
            "qualification.", "GOV",
            (S_414_605, S_R236BP, S_NJ, S_PA, S_MD),
            quote="...if EMT-Paramedics - without specialty care "
                  "certification or qualification - are permitted to "
                  "furnish a given service in a state, then that service "
                  "does not qualify for SCT."),
        use_cases=(
            Fact("ICU→ICU transfers; community hospital → academic/"
                 "quaternary center; ventilated patients; multi-drip "
                 "cardiogenic-shock transfers to advanced cardiac centers; "
                 "IABP/Impella/LVAD moves; NICU/PICU team transports; "
                 "high-risk OB; burn-center transfers; ECMO-center "
                 "transfers.", "FRAMEWORK", (S_414_605, S_CAMTS, S_NEO)),
        ),
    )
    return (bls, als1, als2, sct)


# ─────────────────────────────────────────────────────────────────────────────
# 3 — Fee schedule + CY2024 utilization ladder
# ─────────────────────────────────────────────────────────────────────────────

_CY2026_CF = 284.56          # GOV — CMS CY2026 AFS PUF / MedPAC June 2026
_CY2026_MILEAGE = 9.15       # GOV — per statute mile, national unadjusted

_FEE_SRCS = (S_AFS_PUF, S_MEDPAC26, S_414_610, S_MEDPOP)

# (hcpcs, level, rvu, cy2024_services, cy2024_avg_allowed, cy2024_avg_paid,
#  cy2024_providers) — CY2024 figures are Medicare FFS supplier (carrier)
# claims from the CMS Medicare Physician & Other Practitioners file.
_FEE_TABLE: Tuple[Tuple[str, str, float, Optional[int], Optional[float],
                        Optional[float], Optional[int]], ...] = (
    ("A0428", "BLS non-emergency", 1.00, 2_956_154, 260.65, 206.38, 4_223),
    ("A0429", "BLS emergency", 1.60, 2_608_184, 446.94, 351.82, 9_430),
    ("A0426", "ALS1 non-emergency", 1.20, 218_943, 327.72, 259.34, 2_559),
    ("A0427", "ALS1 emergency", 1.90, 3_697_421, 522.51, 412.46, 8_360),
    ("A0433", "ALS2", 2.75, 85_087, 753.58, 594.95, 5_585),
    ("A0434", "Specialty Care Transport", 3.25, 71_279, 918.36, 729.40,
     1_181),
)


def fee_rows() -> Tuple[FeeRow, ...]:
    """The code/RVU/dollar ladder. CY2026 base = RVU x CF $284.56 (DERIVED
    arithmetic over two GOV constants; the PUF publishes locality-adjusted
    amounts). CY2024 utilization columns are GOV published figures."""
    out: List[FeeRow] = []
    for code, level, rvu, svcs, allowed, paid, provs in _FEE_TABLE:
        out.append(FeeRow(
            hcpcs=code, level=level, rvu=rvu,
            cy2026_base=round(rvu * _CY2026_CF, 2),
            cy2024_services=svcs, cy2024_avg_allowed=allowed,
            cy2024_avg_paid=paid, cy2024_providers=provs,
            srcs=_FEE_SRCS))
    return tuple(out)


def medicare_mix() -> Tuple[MixRow, ...]:
    """CY2024 Medicare FFS supplier-billed ground service mix by HCPCS —
    shares are DERIVED (each code / the six-code total of 9,637,068)."""
    total = sum(r[3] for r in _FEE_TABLE if r[3])
    out: List[MixRow] = []
    for code, level, _rvu, svcs, allowed, _paid, _provs in _FEE_TABLE:
        if not svcs:
            continue
        out.append(MixRow(
            hcpcs=code, level=level, services=svcs,
            share_pct=round(100.0 * svcs / total, 1),
            avg_allowed=allowed or 0.0, srcs=(S_MEDPOP,)))
    return tuple(out)


def payment_mechanics() -> Tuple[Fact, ...]:
    return (
        Fact("Payment = RVU x conversion factor, geographically adjusted: "
             "the practice-expense GPCI applies to 70% of the base rate "
             "(paid = RVU x CF x (0.7 x PE GPCI + 0.3)), with mileage paid "
             "separately per loaded statute mile.", "GOV",
             (S_414_610, S_MEDPAC26)),
        Fact("CY2026 ground conversion factor: $284.56; ground mileage "
             "$9.15/mile national (urban $9.33, rural $9.42; rural miles "
             "1-17 pay 1.5x = $14.13). CY2025 was $278.98 / $8.97.",
             "GOV", (S_MEDPAC26, S_AFS_PUF, S_MEDPAC25)),
        Fact("Annual update = Ambulance Inflation Factor (CPI-U minus "
             "productivity): CY2026 AIF is 2.0% (CPI-U 2.7% - TFP 0.7%); "
             "CY2025 was 2.4%.", "GOV", (S_AIF26,),
             quote="The TFP for CY 2026 is 0.7 percent and the CPI-U for "
                   "2026 is 2.7... Therefore, the AIF for CY 2026 is 2.0 "
                   "percent."),
        Fact("Temporary add-ons — +2% urban, +3% rural, and a 22.6% "
             "super-rural base-rate bonus — were extended by §6203 of the "
             "Consolidated Appropriations Act, 2026 through December 31, "
             "2027 (CBO scored the extension at ~$197M). MedPAC notes the "
             "2%/3% add-ons 'did not have an underlying empirical basis.'",
             "GOV", (S_CAA26, S_MEDPAC26)),
        Fact("Scale economics: GADCS (the mandatory federal cost survey) "
             "found mean cost per transport of $2,673 (median $1,340), "
             "labor = 69.4% of costs, and volume the strongest driver of "
             "unit cost; GAO found 2010 cost per transport ranged $224-"
             "$2,204 (median $429) and the median Medicare margin was "
             "about +2% WITH the add-ons, -1% without.", "GOV",
             (S_GADCS, S_GAO13_6)),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4 — Mix readings (GADCS / MedPAC / NEMSIS) + wages/workforce
# ─────────────────────────────────────────────────────────────────────────────

def mix_readings() -> Tuple[Fact, ...]:
    return (
        Fact("All-payer service mix (GADCS, 3,694 reporting organizations): "
             "56% of US ground transports are BLS, 42% ALS1, and ALS2 + SCT "
             "combined are 3%; 72% of responses are emergencies.",
             "GOV", (S_GADCS,),
             quote="Over half—56 percent—of transports were at the basic "
                   "life support (BLS) level... ALS1 services accounted for "
                   "an additional 42 percent... ALS2 and SCT combined "
                   "accounted for 3 percent."),
        Fact("Medicare FFS 2024: ~10,600 ground organizations delivered "
             "11.3M transports for $5.3B in AFS payments.", "GOV",
             (S_MEDPAC26,)),
        Fact("CY2024 Medicare supplier-billed mix across the six ground "
             "codes (9.64M services): ALS1-emergency 38.4%, BLS "
             "non-emergency 30.7%, BLS-emergency 27.1%, ALS1 non-emergency "
             "2.3%, ALS2 0.9%, SCT 0.7%.", "DERIVED", (S_MEDPOP,)),
        Fact("The IFT lens (NEMSIS 2024, 60,298,684 EMS activations): "
             "hospital-to-hospital transfers are 5,510,664 activations "
             "(9.1%); ALL facility-to-facility categories combined are "
             "7,512,656 (12.5%) — the interfacility book inside US EMS.",
             "SOURCED", (S_NEMSIS24,)),
        Fact("Historical Medicare mix for the same ladder (2011 claims, "
             "MedPAC): BLS 60.9% (42.0% non-emergency), ALS 38.4%, ALS2 "
             "0.9%, SCT 0.8% — and SCT was the fastest-growing type "
             "(+35.5% per FFS beneficiary 2007-2011).", "GOV",
             (S_MEDPAC13,)),
        Fact("Demand context: US hospitals discharge 33M+ inpatients a "
             "year; 22.3% go to post-acute care (the BLS discharge book), "
             "~1.4M/yr (~4%) transfer acute-to-acute (the ALS/SCT book), "
             "and ~550k dialysis patients generate the recurring "
             "BLS book.", "ACADEMIC",
             (S_HCUP205, S_HERNANDEZ, S_NIDDK)),
    )


_WAGES: Tuple[WageRow, ...] = (
    WageRow("EMT", "29-2042", 180_510, 44_470, 46_830, S_OEWS_EMT),
    WageRow("Paramedic", "29-2043", 100_610, 60_600, 63_360, S_OEWS_MEDIC),
    WageRow("Respiratory therapist", "29-1126", 139_790, 82_280, 87_300,
            S_OEWS_RT),
    WageRow("Registered nurse", "29-1141", 3_379_720, 97_550, 101_420,
            S_OEWS_RN),
)


def wage_ladder() -> Tuple[WageRow, ...]:
    """OEWS May 2025 national employment + wages for the four crew
    credentials that define the service ladder."""
    return _WAGES


def workforce_facts() -> Tuple[Fact, ...]:
    return (
        Fact("Certified pipeline: 597,491 nationally certified EMS "
             "clinicians (NREMT, July 2026) — EMT 399,868 (66.9%), "
             "paramedic 149,643 (25.0%), AEMT 30,698, EMR 17,282. The "
             "paramedic pool is roughly ONE-THIRD the EMT pool.",
             "SOURCED", (S_NREMT,)),
        Fact("Turnover 20-30% annually for EMTs and paramedics (AAA/"
             "Newton 360, ~20,000 employees across 258 organizations); "
             "over a third of new hires leave within the first year.",
             "SOURCED", (S_AAA_1PG, S_AAA_TURN)),
        Fact("Occupational outlook: EMT/paramedic employment projected "
             "+5% 2024-2034 with ~19,000 openings a year — growth plus "
             "churn keeps the ALS labor market structurally tight.",
             "GOV", (S_OOH,)),
        Fact("Wage ladder (May 2025 medians): EMT $44,470 → paramedic "
             "$60,600 (+36%) → respiratory therapist $82,280 → RN $97,550 "
             "(2.2x EMT). Each service-level step up substitutes scarcer, "
             "costlier labor — the core reason level mix drives unit "
             "economics.", "GOV",
             (S_OEWS_EMT, S_OEWS_MEDIC, S_OEWS_RT, S_OEWS_RN)),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 5 — Acuity progression (§6): what actually increases across the ladder
# ─────────────────────────────────────────────────────────────────────────────

def acuity_progression() -> Tuple[ProgressionRow, ...]:
    srcs = (S_414_605, S_SCOPE19, S_EQUIP20, S_CAMTS)
    return (
        ProgressionRow(
            "Patient stability",
            "Stable; transport contraindicates other means",
            "Stable-but-at-risk; deterioration plausible",
            "Actively unstable or freshly resuscitated",
            "Critically ill; dependent on life-sustaining therapy",
            srcs),
        ProgressionRow(
            "Monitoring intensity",
            "Periodic vitals, pulse oximetry",
            "Continuous cardiac monitoring, capnography as needed",
            "Continuous monitoring + procedure response",
            "Ventilator, invasive pressures, multi-device monitoring",
            srcs),
        ProgressionRow(
            "Intervention intensity",
            "Supportive care within EMT scope",
            "ALS assessment or ≥1 ALS intervention",
            "≥3 IV med administrations or a listed procedure",
            "Continuous management/titration beyond paramedic scope",
            (S_414_605,)),
        ProgressionRow(
            "Decision-making",
            "Protocol-based EMT care",
            "Paramedic assessment and protocols",
            "Paramedic procedural decisions (pacing, intubation)",
            "Specialty clinician judgment (RN/RT/MD or CC-paramedic)",
            (S_SCOPE19, S_CAMTS)),
        ProgressionRow(
            "Crew minimum (typical)",
            "2 crew, ≥1 EMT (federal floor)",
            "≥1 paramedic + EMT",
            "Paramedic crew (state tiers vary, e.g. TX MICU)",
            "≥2 medical personnel incl. specialty provider (CAMTS); "
            "RN mandatory in some states (NJ)",
            (S_410_41, S_TX, S_CAMTS, S_NJ)),
        ProgressionRow(
            "Payment (RVU / CY2026 base)",
            "1.00 / $284.56 (1.60 / $455.30 emergency)",
            "1.20 / $341.47 (1.90 / $540.66 emergency)",
            "2.75 / $782.54",
            "3.25 / $924.82",
            (S_414_610, S_AFS_PUF, S_MEDPAC26)),
        ProgressionRow(
            "Share of transports (CY2024 Medicare / GADCS all-payer)",
            "57.7% / 56%",
            "40.7% / 42%",
            "0.9% / combined",
            "0.7% / 3% combined with ALS2",
            (S_MEDPOP, S_GADCS)),
    )


def progression_findings() -> Tuple[Fact, ...]:
    """Is the ladder linear? Mostly — with two documented wrinkles."""
    return (
        Fact("The ladder is NOT purely linear at the top: ALS2 and SCT "
             "overlap. ALS2 is triggered by discrete interventions still "
             "within paramedic scope; SCT by required care beyond paramedic "
             "scope. An intubated patient on two pushed medications can be "
             "ALS2 in a strong-paramedic state and SCT in a state (like NJ) "
             "that reserves that care to an RN crew.", "FRAMEWORK",
             (S_414_605, S_NJ, S_PA)),
        Fact("The emergency/non-emergency axis crosscuts acuity: BLS-"
             "emergency (RVU 1.60) outpays ALS1 non-emergency (1.20) — "
             "response mode is a second dimension, not a rung on the "
             "acuity ladder.", "GOV", (S_414_610,)),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 6 — Crew, equipment, medications
# ─────────────────────────────────────────────────────────────────────────────

def crew_matrix() -> Tuple[CrewRow, ...]:
    return (
        CrewRow(
            "BLS",
            Fact("Two crew members; at least one EMT-Basic certified by the "
                 "state and legally authorized to operate all lifesaving "
                 "equipment on board.", "GOV", (S_410_41,)),
            Fact("Texas licenses BLS vehicles at two ECAs minimum "
                 "(25 TAC §157.11(h)) — states may staff above the federal "
                 "floor.", "GOV", (S_TX,)),
            Fact("EMT certification (NREMT or state); no transport-"
                 "specialty credential expected.", "GOV",
                 (S_SCOPE19, S_NREMT)),
        ),
        CrewRow(
            "ALS1 / ALS2",
            Fact("Two crew; at least one paramedic or state-authorized "
                 "ALS-level EMT (42 CFR 410.41(b)(2)).", "GOV", (S_410_41,)),
            Fact("Texas MICU = one EMT + one paramedic minimum; Pennsylvania "
                 "ALS squads run paramedic + EMSVO; New Jersey MICUs "
                 "require TWO paramedics (or RN combinations).", "GOV",
                 (S_TX, S_PA, S_NJ)),
            Fact("Paramedic license; ACLS-level competencies; state "
                 "medical-director oversight.", "GOV", (S_SCOPE19,)),
        ),
        CrewRow(
            "SCT / CCT",
            Fact("Medicare requires the CARE be furnishable only by a "
                 "specialty professional (nurse, emergency medicine, "
                 "respiratory, cardiovascular, or paramedic with additional "
                 "training) — it does not name a fixed crew; states and "
                 "accreditors do.", "GOV", (S_414_605,)),
            Fact("NJ SCTU: RN mandatory ('under no circumstances' may a "
                 "paramedic substitute) + two EMTs; PA CCT: two providers "
                 "above AEMT, ≥1 CCT-trained paramedic/PHRN/physician; MD "
                 "SCT: SCT-trained paramedic OR specialty RN + oriented "
                 "second provider; NJ neonatal SCT adds a neonatal RN or "
                 "physician.", "GOV", (S_NJ, S_PA, S_MD)),
            Fact("CAMTS: primary care provider with ≥3 yrs/4,000 hrs "
                 "ICU/ED experience; CTRN/CFRN (BCEN) for nurses and "
                 "FP-C/CCP-C (IBSC) for paramedics required after two "
                 "years; RRT with ACCS/NPS for respiratory therapists.",
                 "GOV", (S_CAMTS, S_BCEN, S_IBSC)),
        ),
    )


def equipment_facts() -> Tuple[Fact, ...]:
    return (
        Fact("BLS ambulance essential equipment (2020 joint national list): "
             "AED with adult+pediatric pads, oral/nasal airways, suction, "
             "oxygen delivery, BVM, noninvasive positive-pressure device, "
             "tourniquets/wound packing/chest seals, glucometer, pulse "
             "oximeter, BP cuffs.", "GOV", (S_EQUIP20,)),
        Fact("ALS adds (same list): monitor/defibrillator capable of manual "
             "defibrillation, ≥3-lead rhythm monitoring, 12-lead "
             "acquisition and transcutaneous pacing; direct/video "
             "laryngoscopy neonate-to-adult; Magill forceps; supraglottic "
             "airways; continuous waveform capnography; chest-decompression "
             "needles; IV/IO supplies; isotonic crystalloids with pressure "
             "infusion.", "GOV", (S_EQUIP20,),
             quote="A device capable of performing automatic and/or manual "
                   "defibrillation, cardiac rhythm monitoring (in at least "
                   "three leads), 12 lead ECG acquisition, and "
                   "transcutaneous pacing."),
        Fact("SCT/CCT equipment is set by the accreditor + state CCT rules "
             "rather than one federal list: transport ventilator, "
             "multi-channel infusion pumps, invasive-pressure monitoring, "
             "point-of-care labs, isolette/balloon-pump/ECMO mounting as "
             "the mission requires, with power and oxygen redundancy "
             "(CAMTS 12th Ed. standards).", "GOV", (S_CAMTS,)),
        Fact("Vehicle standards: the federal KKK-A-1822 purchase spec (the "
             "'Star of Life' spec) is no longer maintained by GSA; NFPA "
             "1917 and the CAAS Ground Vehicle Standard (v4.0 effective "
             "July 1, 2025) are the successor build standards. The chassis "
             "does not define the service level — staffing and licensure "
             "do; the same box can be relicensed across levels in most "
             "states (Texas explicitly licenses one vehicle at multiple "
             "capability levels).", "GOV", (S_GVS, S_NFPA, S_TX)),
    )


def medication_rules() -> Tuple[Fact, ...]:
    return (
        Fact("EMT (BLS) medication authority is enumerated and tiny: oral "
             "glucose, aspirin, epinephrine auto-injector, naloxone, "
             "inhaled bronchodilators, oxygen, plus assisting the "
             "patient's own prescribed drugs — no IV therapy of any kind "
             "under the national model.", "GOV", (S_SCOPE19,)),
        Fact("AEMT may INITIATE peripheral IV/IO and maintain "
             "NON-medicated fluids; only the paramedic may maintain "
             "MEDICATED infusions, blood products, or access central "
             "lines/ports — this is the clinical hinge between BLS and "
             "ALS interfacility work.", "GOV", (S_SCOPE19,)),
        Fact("For ALS2 counting: three separate ADMINISTRATIONS (IV "
             "push/bolus or continuous infusion) of one or more "
             "medications qualify — repeat doses of the same drug count, "
             "divided doses given to reach the count do not, routes other "
             "than IV do not, and crystalloid/hypotonic/isotonic/"
             "hypertonic solutions (dextrose, saline, Ringer's lactate) "
             "are excluded by regulation. Since CY2025, prehospital blood "
             "transfusion (whole blood, PRBCs, plasma) is itself an ALS2 "
             "qualifying procedure.", "GOV", (S_414_605, S_BPM10)),
        Fact("Titration is the SCT tell: a fixed-rate, paramedic-"
             "maintainable infusion can ride at ALS1; care requiring "
             "ongoing specialty titration (vasoactives, sedation for a "
             "ventilated patient) exceeds paramedic scope in many states "
             "— Pennsylvania requires a pre-hospital RN for certain "
             "medications, and its guidance routes vasoactive-infusion "
             "transfers to RN-staffed CCT.", "GOV", (S_PACEP, S_PA),
             quote="The State of Pennsylvania requires the presence of a "
                   "PHRN for certain medications... The CCT staffed with an "
                   "on board PHRN is best suited to interfacility transfers "
                   "involving critically ill patients requiring vasoactive "
                   "medications."),
        Fact("Formulary and acceptance limits are provider-level policy on "
             "top of state scope: what a transport service will accept "
             "(running heparin, blood, PCA pumps) is set by its medical "
             "director within — never beyond — state scope rules.",
             "FRAMEWORK", (S_SCOPE19, S_PACEP)),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 7 — Necessity, denials, payer differences, state variation
# ─────────────────────────────────────────────────────────────────────────────

def necessity_and_denials() -> Tuple[Fact, ...]:
    return (
        Fact("Medical necessity gate (42 CFR 410.40): ambulance transport "
             "is covered only when other transportation is contraindicated "
             "by the beneficiary's condition; for non-emergency transports "
             "the beneficiary must be bed-confined OR require medically "
             "necessary ambulance-level services — bed confinement alone "
             "is 'not the sole criterion.'", "GOV", (S_410_40,)),
        Fact("Non-emergency, scheduled, repetitive transports require a "
             "physician certification statement (PCS) obtained BEFORE the "
             "service, dated no earlier than 60 days prior — and a signed "
             "PCS 'does not alone demonstrate' necessity; unscheduled "
             "non-emergency transports of facility inpatients allow a PCS "
             "within 48 hours after transport.", "GOV", (S_410_40,),
             quote="While a signed physician certification statement (PCS), "
                   "does not alone demonstrate that transportation by "
                   "ground ambulance was medically necessary, the PCS and "
                   "additional documentation from the beneficiary's medical "
                   "record may be used to support a claim..."),
        Fact("Repetitive non-emergent transports (≥3 round trips in 10 "
             "days, or ≥1 round trip weekly for 3 weeks) are under "
             "NATIONWIDE Medicare prior authorization (RSNAT, fully "
             "national since Aug 1, 2022), covering exactly A0426 and "
             "A0428; skipping prior authorization routes the claims to "
             "prepayment medical review.", "GOV",
             (S_RSNAT, S_MLN_RSNAT)),
        Fact("Coverage is origin/destination-gated and distance-capped: "
             "Medicare covers transport to the NEAREST appropriate "
             "facility (hospital/CAH/REH/SNF), facility→home, SNF→needed "
             "services, and home↔dialysis; excess miles beyond the "
             "closest appropriate facility are non-covered (billed A0888), "
             "payment is lesser-of charge vs fee schedule, and "
             "treat-without-transport is not a covered benefit at all.",
             "GOV", (S_410_40, S_CLM15, S_AB02131),
             quote="The Medicare ambulance benefit is a transportation "
                   "benefit. If no transport of a Medicare beneficiary "
                   "occurs, then there is no Medicare-covered service."),
        Fact("Documentation must support the LEVEL, not just the trip: OIG "
             "found $7.1M paid where destination modifiers were "
             "inconsistent with the level billed, $4.3M of SCT billed "
             "between non-hospital origins/destinations, and 1-in-5 "
             "suppliers with questionable billing patterns; $207M of "
             "questionable payments concentrated in four metros in one "
             "half-year.", "GOV", (S_OIG15,)),
        Fact("EMTALA binds the SENDING hospital: transfers must be "
             "'effected through qualified personnel and transportation "
             "equipment... including the use of necessary and medically "
             "appropriate life support measures' — the hospital, not the "
             "ambulance company, owns the level-of-care decision and the "
             "liability for under-leveling.", "GOV", (S_EMTALA, S_ACEP),
             quote="The transfer is effected through qualified personnel "
                   "and transportation equipment, as required, including "
                   "the use of necessary and medically appropriate life "
                   "support measures during the transfer."),
    )


def payer_differences() -> Tuple[Fact, ...]:
    return (
        Fact("Medicare pays the AFS ladder described here; Medicare "
             "Advantage adds another 17% of transport revenue on top of "
             "FFS Medicare's 25% (GADCS payer mix).", "GOV", (S_GADCS,)),
        Fact("Commercial prices run ~2x Medicare: 2022 median commercial "
             "base rate $718 vs Medicare $365, mileage $17 vs $8 (HCCI); "
             "the ratio widened ~9% from 2016 to 2022.", "SOURCED",
             (S_HCCI,)),
        Fact("Ground ambulance is NOT covered by the No Surprises Act: "
             "28% of commercially insured emergency ground transports "
             "produced a potential surprise bill (2014-17); the federal "
             "GAPB advisory committee (Mar 2024) unanimously recommended "
             "prohibiting balance billing with a reasonable-payment "
             "guarantee and a patient cost-share cap (lesser of $100 or "
             "10%).", "ACADEMIC", (S_HA22, S_GAPB)),
        Fact("Level recognition varies by payer: Medicare's seven ground "
             "levels are the common vocabulary, but Medicaid programs and "
             "commercial contracts set their own rates and prior-auth "
             "rules — the classification standard travels better than the "
             "payment attached to it.", "FRAMEWORK", (S_414_605, S_HCCI)),
    )


def state_variation() -> Tuple[Fact, ...]:
    return (
        Fact("The scope model is guidance, not law: 'Each State has the "
             "authority and responsibility to regulate EMS within its "
             "borders and to determine the scope of practice of "
             "State-licensed EMS personnel.'", "GOV", (S_SCOPE19,),
             quote="Each State has the authority and responsibility to "
                   "regulate EMS within its borders and to determine the "
                   "scope of practice of State-licensed EMS personnel."),
        Fact("New Jersey: SCT units MUST carry an RN with critical-care "
             "experience and CCRN/CEN certification — a paramedic may "
             "never substitute; MICUs need two paramedics (or RN "
             "combinations); neonatal SCT adds a neonatal RN or physician "
             "(N.J.A.C. 8:41).", "GOV", (S_NJ,)),
        Fact("Pennsylvania: a licensed critical-care-transport ambulance "
             "service staffs an EMSVO plus two providers above AEMT, at "
             "least one a CCT-trained paramedic, PHRN, PHPE, or physician "
             "— i.e., a critical-care PARAMEDIC pathway exists (28 Pa. "
             "Code §1027.39).", "GOV", (S_PA,)),
        Fact("Texas: licenses the VEHICLE tier (BLS, BLS-with-ALS, ALS, "
             "MICU...) with staffing minima per tier — MICU = EMT + "
             "paramedic (25 TAC §157.11).", "GOV", (S_TX,)),
        Fact("Maryland: commercial SCT requires an SCT-trained paramedic "
             "or specialty RN, plus an oriented second clinician; care "
             "beyond the SCT paramedic's scope requires an RN or "
             "physician aboard (COMAR 30.09.14.04).", "GOV", (S_MD,)),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 8 — Edge cases (§17)
# ─────────────────────────────────────────────────────────────────────────────

def edge_cases() -> Tuple[EdgeCase, ...]:
    return (
        EdgeCase("Stable patient on home-flow oxygen",
                 "BLS",
                 "Oxygen therapy is an EMT skill; oxygen alone never makes "
                 "a trip ALS.",
                 "Coverage still requires that other transport be "
                 "contraindicated — oxygen use by itself doesn't prove "
                 "medical necessity.",
                 "GOV", (S_SCOPE19, S_410_40)),
        EdgeCase("Saline lock in place, nothing running",
                 "BLS (state-dependent)",
                 "No infusion to maintain; under the national model EMTs "
                 "don't manage IVs, but a capped lock needs no management.",
                 "Some states/services route any vascular access to ALS by "
                 "protocol.",
                 "FRAMEWORK", (S_SCOPE19, S_PACEP)),
        EdgeCase("IV antibiotic running during transport",
                 "ALS1",
                 "A medicated infusion must be maintained by a paramedic "
                 "(national model); one medication = ALS1, not ALS2.",
                 "An AEMT may maintain only NON-medicated fluids; state "
                 "scope varies.",
                 "GOV", (S_SCOPE19, S_414_605)),
        EdgeCase("Fixed-rate heparin infusion",
                 "ALS1 → SCT (state-dependent)",
                 "Paramedic-maintainable at fixed rate in many states; PA "
                 "requires a PHRN for certain medications.",
                 "One continuous infusion is a single administration — not "
                 "ALS2 by itself; the RN requirement flips it to SCT where "
                 "it applies.",
                 "GOV", (S_PACEP, S_414_605)),
        EdgeCase("Titratable vasopressor (e.g., norepinephrine)",
                 "SCT",
                 "Ongoing titration of vasoactives is the canonical "
                 "beyond-paramedic-scope therapy; PA guidance routes these "
                 "to RN-staffed CCT.",
                 "A few strong-paramedic states train CCP-C paramedics to "
                 "run pressors — then it can bill SCT with a 'paramedic "
                 "with additional training.'",
                 "GOV", (S_414_605, S_PACEP)),
        EdgeCase("Ventilated patient, stable settings",
                 "SCT (most states); ALS2 possible",
                 "Ventilator management is beyond the 2019 paramedic model "
                 "baseline; SCT covers 'respiratory care' specialty. An "
                 "intubation performed en route is itself an ALS2 trigger.",
                 "States with critical-care paramedic tiers (PA, MD) allow "
                 "paramedic vent transports — the ALS2/SCT line moves at "
                 "the border.",
                 "GOV", (S_414_605, S_PA, S_MD)),
        EdgeCase("Tracheostomy, not ventilator-dependent",
                 "BLS",
                 "Airway suctioning is an EMT skill; no in-transit "
                 "intervention beyond EMT scope is required.",
                 "Fresh/complicated trachs or frequent deep suctioning "
                 "push services to send ALS.",
                 "FRAMEWORK", (S_SCOPE19,)),
        EdgeCase("Chest tube in place",
                 "ALS1 (monitoring) / SCT (active management)",
                 "'Chest tube monitoring/management' is a paramedic skill "
                 "in the 2019 model.",
                 "Suction/drainage systems needing titration or a fresh "
                 "unstable tube escalate to SCT.",
                 "GOV", (S_SCOPE19, S_414_605)),
        EdgeCase("Central line present, no meds running",
                 "ALS1 (monitoring); placement is an ALS2 trigger",
                 "Central-line MONITORING is a paramedic skill; central "
                 "venous line PLACEMENT is one of the eight ALS2 "
                 "procedures.",
                 "BLS crews cannot monitor central access under the "
                 "national model.",
                 "GOV", (S_SCOPE19, S_414_605)),
        EdgeCase("Wound vac / feeding tube / Foley",
                 "BLS",
                 "Self-contained devices requiring no in-transit clinical "
                 "management within or beyond EMT scope.",
                 "Necessity documentation still must show why an ambulance "
                 "(vs stretcher van) is required.",
                 "FRAMEWORK", (S_410_40,)),
        EdgeCase("Dementia / altered mental status, medically stable",
                 "BLS",
                 "Supervision and safety needs support ambulance necessity "
                 "without requiring ALS-level care.",
                 "New or undiagnosed AMS at dispatch can require an ALS "
                 "assessment — which alone justifies ALS1-emergency.",
                 "GOV", (S_410_40, S_414_605)),
        EdgeCase("Behavioral-health patient in restraints",
                 "BLS (typical) / ALS if chemically sedated",
                 "Physical restraint monitoring is within EMT scope; "
                 "chemical sedation en route requires a paramedic.",
                 "State protocols differ on restraint monitoring "
                 "requirements.",
                 "FRAMEWORK", (S_SCOPE19,)),
        EdgeCase("Bariatric patient, stable",
                 "BLS + bariatric equipment",
                 "Acuity, not size, sets the level; bariatric stretcher/"
                 "winch changes the vehicle kit, not the code.",
                 "Some payers/contracts carry bariatric surcharges — a "
                 "contract term, not a Medicare level.",
                 "FRAMEWORK", (S_414_605, S_EQUIP20)),
        EdgeCase("Patient receiving blood products en route",
                 "ALS2 (since CY2025); SCT where state scope requires RN",
                 "Prehospital blood transfusion (whole blood, PRBCs, "
                 "plasma) was added as ALS2 qualifying procedure #8 "
                 "effective CY2025 (89 FR 98559); the 2019 model lets "
                 "paramedics MAINTAIN blood-product infusions.",
                 "Many states still restrict transfusion management to RN "
                 "crews — there the same patient rides SCT.",
                 "GOV", (S_414_605, S_SCOPE19)),
        EdgeCase("Temporary transvenous pacemaker",
                 "SCT",
                 "The model gives paramedics transvenous-pacing MONITORING "
                 "only; a patient dependent on a temporary wire needs "
                 "specialty management. Active cardiac pacing en route is "
                 "an ALS2 procedure.",
                 "State CC-paramedic tiers may carry it; crew composition "
                 "varies by program.",
                 "GOV", (S_SCOPE19, S_414_605)),
        EdgeCase("LVAD / IABP / Impella / ECMO patient",
                 "SCT (CCT team)",
                 "Device-specific expertise (cardiovascular specialty care) "
                 "is definitionally beyond paramedic scope; CAMTS requires "
                 "critical-care-experienced specialty crews.",
                 "Hospital may send its own perfusionist/device specialist "
                 "aboard the ambulance — the crew composition then blends "
                 "hospital + supplier staff.",
                 "GOV", (S_414_605, S_CAMTS)),
        EdgeCase("Hospital sends its own RN because of hospital policy",
                 "Level set by care REQUIRED, not staff aboard",
                 "SCT requires that the patient's condition NEED specialty "
                 "care; an RN riding along for policy comfort does not "
                 "create SCT billing.",
                 "OIG flagged SCT claims where level and trip did not "
                 "match; relatedly, Medicare pays nothing for moving staff "
                 "without the beneficiary aboard (e.g., repositioning a "
                 "specialty team between hospitals).",
                 "GOV", (S_414_605, S_OIG15, S_BPM10)),
        EdgeCase("Patient improves before pickup",
                 "Re-level at pickup",
                 "Medical necessity is judged on the condition at the time "
                 "of transport, not at booking.",
                 "PCS paperwork obtained in advance can lag the clinical "
                 "picture — a downgrade discipline is a compliance control.",
                 "GOV", (S_410_40, S_BPM10)),
        EdgeCase("Patient deteriorates after dispatch (BLS → ALS)",
                 "Upgrade en route / intercept",
                 "An ALS intervention performed because the condition "
                 "changed makes the trip ALS1 (or ALS2 if triggers met); "
                 "rural systems use the paramedic-intercept benefit.",
                 "The reverse (ALS dispatched, BLS delivered) bills BLS "
                 "unless an emergency-response ALS assessment applies.",
                 "GOV", (S_414_605, S_BPM10)),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 9 — Misconceptions (§18)
# ─────────────────────────────────────────────────────────────────────────────

def misconceptions() -> Tuple[Misconception, ...]:
    return (
        Misconception(
            "BLS means no medical care.",
            "BLS is defined medical care: EMT assessment, oxygen, airway "
            "adjuncts, suction, CPR/AED, glucose monitoring, and several "
            "medications — furnished by a certified clinician crew.",
            (S_SCOPE19, S_410_41)),
        Misconception(
            "Oxygen automatically makes a trip ALS.",
            "Oxygen therapy is squarely within EMT scope; it neither "
            "requires nor justifies ALS billing.",
            (S_SCOPE19,)),
        Misconception(
            "A paramedic on board permits ALS billing.",
            "For non-emergency trips the service furnished must include an "
            "ALS intervention; crew capability alone is not a billable "
            "level. (Emergency responses differ: a necessary ALS "
            "assessment qualifies even without an intervention.)",
            (S_414_605, S_BPM10)),
        Misconception(
            "Every hospital-to-hospital transfer is ALS.",
            "Level follows required in-transit care: 30.7% of CY2024 "
            "Medicare ground transports were BLS NON-emergency — much of "
            "it interfacility discharge traffic.",
            (S_MEDPOP, S_414_605)),
        Misconception(
            "Every ICU transfer / every ventilated patient is CCT.",
            "SCT requires care beyond paramedic scope; states with "
            "critical-care paramedic tiers move some ventilated transfers "
            "into paramedic hands, and a stabilized ICU patient may need "
            "only ALS1 monitoring.",
            (S_414_605, S_PA, S_MD)),
        Misconception(
            "ALS2 is just 'sicker ALS1.'",
            "ALS2 is a counting rule: ≥3 IV medication administrations "
            "(crystalloids excluded) or one of eight named procedures — "
            "objective triggers, not a severity impression.",
            (S_414_605,)),
        Misconception(
            "CCT is ALS with a nurse.",
            "The defining test is required specialty-level care; the crew "
            "may be RN, RT, physician, or a critical-care paramedic — and "
            "which of those is REQUIRED varies by state law (NJ mandates "
            "the RN; PA/MD allow CCT paramedics).",
            (S_414_605, S_NJ, S_PA, S_MD)),
        Misconception(
            "Requested level = delivered level = billed level = paid "
            "level.",
            "Each link can break: trips are re-leveled at pickup, "
            "assessments can justify ALS without intervention, claims are "
            "downcoded or denied on review, and prior authorization gates "
            "repetitive non-emergent trips.",
            (S_BPM10, S_OIG15, S_RSNAT)),
        Misconception(
            "Medicare definitions apply identically to every payer.",
            "Commercial prices run ~2x Medicare and contracts set their "
            "own terms; Medicaid NEMT is a separate benefit; ground "
            "ambulance sits outside the No Surprises Act.",
            (S_HCCI, S_HA22, S_GAPB)),
        Misconception(
            "Bed confinement by itself qualifies the transport.",
            "Regulation makes bed confinement a factor — not the sole "
            "criterion; the covered test is that other means of transport "
            "are contraindicated by the condition.",
            (S_410_40,)),
        Misconception(
            "Critical care transport is a high-volume line.",
            "SCT was 71,279 Medicare claims in CY2024 — 0.7% of ground "
            "transports (ALS2+SCT are 3% of all-payer transports in "
            "GADCS). It is strategically important, not volumetrically.",
            (S_MEDPOP, S_GADCS)),
        Misconception(
            "Higher acuity always means a different vehicle.",
            "Federal rules regulate staffing and equipment, not the box; "
            "the same ambulance is commonly licensed/flexed across levels "
            "(Texas licenses multi-level capability explicitly). CCT adds "
            "equipment, power, and mounting — usually not a new chassis "
            "class.",
            (S_410_41, S_TX, S_CAMTS)),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 10 — The conclusion under test (§20)
# ─────────────────────────────────────────────────────────────────────────────

_CONCLUSION_STATEMENT = (
    "Clinical service levels are differentiated less by where the patient is "
    "going and more by the intensity, continuity, and specialization of care "
    "required during transport. As acuity rises, the operating model shifts "
    "from basic supportive transport to advanced intervention and ultimately "
    "to continuous management of complex life-sustaining therapies.")


def conclusion_test() -> Conclusion:
    return Conclusion(
        statement=_CONCLUSION_STATEMENT,
        verdict="SUPPORTED — with three refinements",
        support=(
            Fact("The regulatory definitions are written in care terms, "
                 "not destination terms: ALS1 turns on an assessment or "
                 "intervention; ALS2 on medication-administration counts "
                 "and named procedures; SCT on ongoing care beyond "
                 "paramedic scope — intensity, continuity, and "
                 "specialization, exactly as the statement claims.",
                 "GOV", (S_414_605,)),
            Fact("The operating model shifts with the level exactly as "
                 "claimed: the crew ladder (EMT → paramedic → specialty "
                 "clinician) tracks a wage ladder ($44,470 → $60,600 → "
                 "$97,550 median) and a scarcity ladder (399,868 EMTs → "
                 "149,643 paramedics → credentialed CC-transport "
                 "specialists at 157 accredited programs).", "GOV",
                 (S_OEWS_EMT, S_OEWS_MEDIC, S_OEWS_RN, S_NREMT,
                  S_CAMTS_N)),
            Fact("Payment follows the same care gradient: RVUs 1.00 → "
                 "1.20 → 2.75 → 3.25 price the in-transit care package, "
                 "not the mileage or destination (mileage is a separate "
                 "code).", "GOV", (S_414_610,)),
        ),
        refinements=(
            Fact("Refinement 1 — destination is not irrelevant: SCT is "
                 "definitionally INTERFACILITY (a scene call cannot be "
                 "SCT), coverage rules enumerate covered origins/"
                 "destinations, and OIG polices level-vs-destination "
                 "consistency.", "GOV", (S_414_605, S_410_40, S_OIG15)),
            Fact("Refinement 2 — response mode is a second axis: "
                 "emergency vs non-emergency splits BLS and ALS1 (RVU "
                 "1.60/1.90 vs 1.00/1.20) independent of in-transit care "
                 "intensity.", "GOV", (S_414_610,)),
            Fact("Refinement 3 — the top of the ladder is state-"
                 "relative: 'beyond the scope of the EMT-Paramedic' moves "
                 "with state scope rules, so the ALS2/SCT boundary (and "
                 "who must crew it) changes at state lines — NJ mandates "
                 "RNs where PA credentials critical-care paramedics.",
                 "GOV", (S_414_605, S_NJ, S_PA)),
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 11 — Connector hooks (reuse the live estate read-only) + KPIs
# ─────────────────────────────────────────────────────────────────────────────

def connector_reads() -> Dict[str, Any]:
    """Live-estate probes reused from the IFT connector layer (read-only).
    Degrades to {available: False} blocks offline; never raises."""
    out: Dict[str, Any] = {}
    try:
        from . import ift_analytics as A
        pb = A.ambulance_part_b_utilization()
        out["part_b"] = {
            "available": bool(getattr(pb, "available", False)),
            "dataset_id": getattr(pb, "dataset_id", ""),
            "rows": list(getattr(pb, "rows", []) or []),
            "source_label": getattr(pb, "source_label", ""),
            "fallback_citation": getattr(pb, "fallback_citation", ""),
        }
        emp = A.ambulance_employment()
        out["qcew"] = {
            "available": bool(getattr(emp, "available", False)),
            "dataset_id": getattr(emp, "dataset_id", ""),
            "rows": list(getattr(emp, "rows", []) or []),
            "source_label": getattr(emp, "source_label", ""),
            "fallback_citation": getattr(emp, "fallback_citation", ""),
        }
    except Exception:  # noqa: BLE001 — estate optional by design
        out.setdefault("part_b", {"available": False})
        out.setdefault("qcew", {"available": False})
    try:
        from . import ift_demand_evidence as E
        ev = E.get("medicare_ffs_transports")
        if ev is not None:
            out["shared_medicare_volume"] = {
                "value": ev.value, "source": ev.source, "url": ev.url,
            }
    except Exception:  # noqa: BLE001
        pass
    return out


def kpis() -> Dict[str, Any]:
    mix = medicare_mix()
    total = sum(m.services for m in mix)
    return {
        "rvu_span": "1.00 → 3.25",
        "cy2026_base_span": "$284.56 → $924.82",
        "cy2026_cf": _CY2026_CF,
        "cy2026_mileage": _CY2026_MILEAGE,
        "medicare_transports_2024": "11.3M",
        "medicare_spend_2024": "$5.3B",
        "cy2024_supplier_transports": total,
        "gadcs_mix": "56% BLS · 42% ALS1 · 3% ALS2+SCT",
        "ift_share_nemsis": "12.5% of 60.3M activations",
        "sct_share": "0.7%",
    }


# ─────────────────────────────────────────────────────────────────────────────
# 12 — Bibliography + honesty guards
# ─────────────────────────────────────────────────────────────────────────────

def _iter_facts() -> List[Fact]:
    out: List[Fact] = []
    out.extend(classification_framework())
    for lv in service_levels():
        out.append(lv.definition)
        out.extend(lv.clinical)
        out.extend(lv.operational)
        out.extend(lv.reimbursement)
        out.append(lv.boundary)
        out.extend(lv.use_cases)
    out.extend(payment_mechanics())
    out.extend(mix_readings())
    out.extend(workforce_facts())
    out.extend(progression_findings())
    for cr in crew_matrix():
        out.extend((cr.federal_minimum, cr.state_examples,
                    cr.certifications))
    out.extend(equipment_facts())
    out.extend(medication_rules())
    out.extend(necessity_and_denials())
    out.extend(payer_differences())
    out.extend(state_variation())
    c = conclusion_test()
    out.extend(c.support)
    out.extend(c.refinements)
    return out


def bibliography() -> Tuple[Src, ...]:
    """Every unique source used anywhere on the page, deduped by URL."""
    seen: Dict[str, Src] = {}
    for f in _iter_facts():
        for s in f.srcs:
            seen.setdefault(s.url, s)
    for ec in edge_cases():
        for s in ec.srcs:
            seen.setdefault(s.url, s)
    for m in misconceptions():
        for s in m.srcs:
            seen.setdefault(s.url, s)
    for r in fee_rows():
        for s in r.srcs:
            seen.setdefault(s.url, s)
    for w in wage_ladder():
        if w.src.url:
            seen.setdefault(w.src.url, w.src)
    for p in acuity_progression():
        for s in p.srcs:
            seen.setdefault(s.url, s)
    return tuple(sorted(seen.values(), key=lambda s: s.label.lower()))


def n_by_basis() -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for f in _iter_facts():
        counts[f.basis] = counts.get(f.basis, 0) + 1
    for ec in edge_cases():
        counts[ec.basis] = counts.get(ec.basis, 0) + 1
    return counts


def has_no_illustrative() -> bool:
    """The page-level honesty guard: no fact anywhere carries an
    ILLUSTRATIVE basis (mirrors ift_demand_evidence.has_no_illustrative)."""
    return "ILLUSTRATIVE" not in n_by_basis()


def summary() -> Dict[str, Any]:
    return {
        "levels": [lv.key for lv in service_levels()],
        "n_facts": len(_iter_facts()),
        "n_edge_cases": len(edge_cases()),
        "n_misconceptions": len(misconceptions()),
        "n_sources": len(bibliography()),
        "n_by_basis": n_by_basis(),
        "no_illustrative": has_no_illustrative(),
        "verdict": conclusion_test().verdict,
        "kpis": kpis(),
    }
