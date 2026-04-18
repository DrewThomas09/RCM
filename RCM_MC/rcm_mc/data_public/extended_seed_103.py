"""Extended seed 103: Skilled nursing / long-term care / post-acute PE deals.

This module contains a curated set of 15 healthcare private equity
deal records focused on the skilled nursing facility (SNF), post-
acute rehabilitation, long-term care (LTC), memory care, and
assisted living (AL) subsector. The theme covers:

- Skilled nursing facility (SNF) platforms delivering Medicare-
  certified Part A post-acute short-stay skilled nursing and
  rehabilitation services (typical 20-30 day short-stay SNF
  episode following a qualifying 3-midnight acute-hospital
  inpatient stay) alongside Medicaid-reimbursed long-stay
  custodial care for chronically ill and frail elderly residents,
  with average daily census (ADC), revenue per patient day (RPPD),
  and skilled mix (percentage of census on Medicare Part A or
  managed-care skilled rates) as the load-bearing operating
  metrics
- Post-acute rehabilitation platforms delivering inpatient
  rehabilitation facility (IRF), long-term-acute-care hospital
  (LTACH), and high-acuity post-acute rehab services for stroke,
  orthopedic-joint-replacement, traumatic-brain-injury, spinal-
  cord-injury, and medically complex patient populations, with
  Medicare IRF-PPS (inpatient rehab prospective payment system) /
  LTACH-PPS case-mix-weighted reimbursement, CMS 60% rule
  compliance (≥60% of IRF admissions in one of 13 CMS-specified
  diagnostic categories), and IRF patient-assessment-instrument
  (IRF-PAI) functional-assessment scoring driving case-mix
  reimbursement
- Long-term care (LTC) platforms delivering custodial nursing-
  home care for chronically ill elderly residents on a heavily
  Medicaid-reimbursed per-diem payment model (50-65% Medicaid,
  state-by-state variation in per-diem rates with meaningful
  state-level Medicaid rate-parity legislative dynamics),
  typically lower-acuity long-stay census relative to SNF with
  lower skilled mix and RPPD but higher occupancy-stability
- Memory care platforms delivering specialized Alzheimer's-
  disease, vascular-dementia, Lewy-body-dementia, and
  frontotemporal-dementia resident care in secured memory-care
  units or freestanding memory-care communities with enhanced
  staffing ratios (typical 1:5-1:7 caregiver-to-resident ratio
  versus 1:10-1:15 in standard assisted living), wander-
  management protocols, and specialized dementia-care-trained
  clinical staff, with premium private-pay rates ($7,500-
  $11,000/month) relative to standard assisted living
- Assisted living (AL) platforms delivering private-pay
  residential assisted-living services for semi-independent
  elderly residents requiring activities-of-daily-living (ADL)
  assistance but not skilled nursing care, with private-pay
  monthly rates ($4,500-$7,500/month) as the dominant revenue
  model, operating under state AL licensure regulations rather
  than federal Medicare/Medicaid certification, and exposed to
  residential-real-estate cycle dynamics and single-family-home-
  price-driven demand cyclicality

Skilled nursing and post-acute economics are distinguished by (a)
the fundamental Medicare Part A versus Medicaid per-diem rate
differential driving SNF operator economics — Medicare Part A
short-stay skilled rates average $560-$750/day under the Patient-
Driven Payment Model (PDPM) implemented October 2019 versus
state Medicaid LTC per-diem rates averaging $220-$340/day (with
material state-by-state variation), making skilled mix (% of
census on Medicare Part A or managed-care skilled rates) the
single most important operational KPI in PE-backed SNF
operations, (b) the October 2019 CMS implementation of the
Patient-Driven Payment Model (PDPM) replacing the prior RUG-IV
(Resource Utilization Groups) therapy-minutes-driven SNF
reimbursement system — PDPM reimburses based on patient clinical
characteristics across five case-mix-adjusted payment components
(PT, OT, SLP, nursing, non-therapy ancillary) rather than therapy
minutes delivered, fundamentally restructuring SNF therapy
staffing and incentivizing clinical-acuity documentation over
therapy-minute volume, with material operational impact on SNF
therapy-company contracts and MDS (Minimum Data Set) assessment
workflows, (c) the corresponding January 2020 CMS implementation
of the Patient-Driven Groupings Model (PDGM) for home health
agencies operating in adjacent post-acute referral pathways,
replacing the prior 60-day episode payment system with 30-day
payment periods and case-mix-adjusted HIPPS code reimbursement,
(d) the Medicare 3-midnight rule requiring a qualifying ≥3-
consecutive-midnight inpatient acute-hospital stay to qualify
for subsequent Medicare Part A SNF coverage (with Medicare
Advantage plan 3-midnight-waiver programs and the CMS MA Star
Ratings 3-midnight-waiver bonus dynamics creating referral-
pathway shifts toward MA-covered SNF admissions), (e) the SNF
Value-Based Purchasing (SNF VBP) program implemented October
2018 applying a 2% Medicare Part A payment withhold with up to
~60% value-based redistribution based on the 30-day all-cause
readmission measure (SNFRM), with expansion to additional
quality measures (falls with major injury, pressure ulcers,
functional improvement) under the SNF QRP (Quality Reporting
Program) creating readmission-reduction operating pressure, (f)
the CMS 5-star Nursing Home Compare rating system weighting
health-inspection surveys, staffing levels (nursing hours per
resident day, RN hours per resident day), and quality measures
(antipsychotic use, pressure ulcers, falls, rehospitalization,
functional improvement) driving facility-level census referrals
from hospitals, MA plans, and family decision-makers with
material occupancy and skilled-mix impact, (g) state Medicaid
LTC per-diem rate-parity legislative dynamics with meaningful
state-by-state per-diem rate variation ($180-$340/day state-
Medicaid rate range) and ongoing state-legislative battles over
Medicaid LTC rate adequacy, Medicaid expansion rate-pass-through
requirements, and state provider-tax / IGT (intergovernmental
transfer) SNF-funding mechanisms, (h) Medicare RAC (Recovery
Audit Contractor) audit exposure on SNF Medicare Part A claims
— RAC audits review SNF PDPM case-mix coding, MDS assessment
accuracy, 3-midnight-rule compliance, therapy delivery
documentation, and medical-necessity-of-skilled-level-of-care
determinations with material recoupment exposure on audited
SNF claims, and (i) the healthcare-REIT landlord dynamic
dominating SNF / LTC / post-acute capital structure — Sabra
Health Care REIT (SBRA), Welltower (WELL), Ventas (VTR), CareTrust
REIT (CTRE), Omega Healthcare Investors (OHI), LTC Properties
(LTC), Diversified Healthcare Trust (DHC), and National Health
Investors (NHI) own the majority of SNF / LTC / AL real estate
and lease to operator companies under long-dated master lease
structures with EBITDAR (EBITDA before rent) as the operator-
level return metric, fixed-rent obligations, coverage-ratio
covenants (typically 1.1x-1.3x EBITDAR/rent), and periodic rent-
escalation / lease-renegotiation dynamics creating operator-REIT
partnership interdependence and PE-sponsor-operator-REIT capital
stack complexity. Value creation in PE-backed SNF / LTC / post-
acute platforms centers on skilled-mix optimization (shifting
census toward higher-reimbursement Medicare Part A / managed-
care skilled census), PDPM case-mix documentation and MDS
assessment workflow optimization, CMS 5-star rating improvement
(driving hospital / MA-plan / family referral-share gains),
30-day readmission reduction under SNF VBP, regional
consolidation and operating leverage across contiguous state /
MSA geographies, REIT-landlord master-lease renegotiation and
EBITDAR-coverage-ratio management, therapy-company contract
restructuring post-PDPM, and state-Medicaid rate-parity
legislative advocacy. Each record captures deal economics (EV,
EV/EBITDA, margins), return profile (MOIC, IRR, hold period),
payer mix, regional footprint, sponsor, realization status, and
a short deal narrative. These records are synthesized for
modeling, backtesting, and scenario analysis use cases.
"""

EXTENDED_SEED_DEALS_103 = [
    {
        "company_name": "Aspen Skilled Nursing Partners",
        "sector": "Skilled Nursing Facility",
        "buyer": "Formation Capital",
        "year": 2017,
        "region": "Mountain",
        "ev_mm": 425.0,
        "ev_ebitda": 13.0,
        "ebitda_mm": 69.55,
        "ebitda_margin": 0.17,
        "revenue_mm": 409.12,
        "hold_years": 5.5,
        "moic": 2.3,
        "irr": 0.1608,
        "status": "Realized",
        "payer_mix": {"commercial": 0.08, "medicaid": 0.48, "medicare": 0.32, "self_pay": 0.12},
        "comm_pct": 0.08,
        "deal_narrative": (
            "Mountain-region skilled nursing facility (SNF) "
            "platform operating 32 Medicare/Medicaid-certified "
            "SNF facilities with 3,850 licensed beds across "
            "Colorado, Utah, Idaho, Wyoming, and Montana under a "
            "Sabra Health Care REIT master-lease structure. "
            "Platform delivered Medicare Part A short-stay post-"
            "acute skilled rehabilitation (20-30 day episode "
            "following qualifying 3-midnight acute-hospital "
            "inpatient stay) alongside Medicaid-reimbursed long-"
            "stay custodial LTC census. Hold navigated the "
            "October 2019 CMS implementation of the Patient-"
            "Driven Payment Model (PDPM) replacing RUG-IV "
            "therapy-minutes-driven SNF reimbursement — "
            "restructured contract-therapy company relationships, "
            "invested in MDS (Minimum Data Set) assessment "
            "workflows and PDPM case-mix-adjusted clinical "
            "documentation, and shifted therapy staffing from "
            "therapy-minute volume toward clinical-acuity "
            "capture. Improved platform CMS 5-star Nursing Home "
            "Compare average rating from 2.8 to 3.6 stars "
            "driving hospital / MA-plan referral-share gains and "
            "skilled mix expansion from 19% to 26%. Navigated "
            "Sabra master-lease EBITDAR coverage-ratio covenant "
            "(1.15x minimum) and negotiated rent-escalation "
            "deferrals through COVID-era occupancy disruption. "
            "Exited to a strategic SNF operator at 2.3x MOIC."
        ),
    },
    {
        "company_name": "Birchwood Post-Acute Rehab Holdings",
        "sector": "Post-Acute Rehab",
        "buyer": "Vistria Group",
        "year": 2018,
        "region": "Southeast",
        "ev_mm": 685.0,
        "ev_ebitda": 15.5,
        "ebitda_mm": 116.45,
        "ebitda_margin": 0.19,
        "revenue_mm": 612.89,
        "hold_years": 6.0,
        "moic": 2.9,
        "irr": 0.1969,
        "status": "Realized",
        "payer_mix": {"commercial": 0.12, "medicaid": 0.40, "medicare": 0.36, "self_pay": 0.12},
        "comm_pct": 0.12,
        "deal_narrative": (
            "Southeast post-acute rehabilitation platform "
            "operating 14 Medicare-certified inpatient "
            "rehabilitation facilities (IRFs) and 38 SNF "
            "post-acute rehab units across Florida, Georgia, "
            "the Carolinas, Alabama, and Tennessee delivering "
            "high-acuity post-acute rehab services for stroke, "
            "orthopedic-joint-replacement, traumatic-brain-"
            "injury, spinal-cord-injury, and medically complex "
            "patient populations under the Medicare IRF-PPS "
            "(inpatient rehab prospective payment system) case-"
            "mix-weighted reimbursement framework. Platform "
            "navigated CMS 60% rule compliance (requiring ≥60% "
            "of IRF admissions in one of 13 CMS-specified "
            "diagnostic categories — stroke, SCI, TBI, hip "
            "fracture, major multiple trauma, etc.) through "
            "disciplined IRF-PAI (patient-assessment-instrument) "
            "functional-assessment scoring and case-mix "
            "documentation. Managed the October 2019 PDPM "
            "transition on the SNF-based post-acute rehab units, "
            "optimized 30-day readmission performance under the "
            "SNF VBP program (SNFRM measure) capturing value-"
            "based payment incentive, and built referral-pathway "
            "relationships with 48 acute-hospital systems across "
            "the Southeast footprint. Long 6-year hold added "
            "18 tuck-in IRF and post-acute SNF acquisitions, "
            "navigated Ventas master-lease structure on 22 of "
            "52 facilities, and exited to a strategic post-"
            "acute consolidator at 2.9x MOIC."
        ),
    },
    {
        "company_name": "Cypress Long-Term Care Group",
        "sector": "Long-Term Care",
        "buyer": "Carlyle Group",
        "year": 2016,
        "region": "Midwest",
        "ev_mm": 545.0,
        "ev_ebitda": 12.5,
        "ebitda_mm": 81.75,
        "ebitda_margin": 0.15,
        "revenue_mm": 545.00,
        "hold_years": 6.5,
        "moic": 2.0,
        "irr": 0.1106,
        "status": "Realized",
        "payer_mix": {"commercial": 0.06, "medicaid": 0.54, "medicare": 0.26, "self_pay": 0.14},
        "comm_pct": 0.06,
        "deal_narrative": (
            "Midwest long-term care (LTC) platform operating 48 "
            "Medicaid-dominant nursing-home facilities with "
            "5,420 licensed beds across Ohio, Indiana, Michigan, "
            "Illinois, Iowa, and Missouri under a Welltower "
            "master-lease structure covering 34 of 48 "
            "facilities. Platform census heavily weighted to "
            "Medicaid long-stay custodial LTC residents (56% "
            "Medicaid payer mix) reflecting the traditional LTC "
            "nursing-home economic model with chronically ill "
            "elderly residents on extended state-Medicaid per-"
            "diem reimbursement ($225-$285/day state-Medicaid "
            "per-diem across the six-state footprint). Low "
            "15% EBITDA margin reflects Medicaid-heavy payer "
            "mix and the inherent margin compression of long-"
            "stay LTC versus Medicare Part A skilled rehab "
            "census. Hold navigated (a) the October 2019 PDPM "
            "transition on the 22% Medicare Part A skilled-mix "
            "census, (b) CMS 5-star rating improvement from a "
            "platform average of 2.4 stars to 3.2 stars through "
            "staffing-level investments and quality-measure "
            "remediation, (c) state-level Medicaid rate-parity "
            "legislative battles in Ohio, Indiana, and Illinois "
            "on Medicaid LTC per-diem rate adequacy, (d) COVID-"
            "era occupancy disruption compressing ADC from 86% "
            "to 71% and subsequent 2022-2024 recovery to 82%, "
            "and (e) Welltower master-lease rent-deferral and "
            "EBITDAR-coverage-ratio renegotiation through the "
            "COVID occupancy trough. Exited to a strategic LTC "
            "operator at 2.0x MOIC."
        ),
    },
    {
        "company_name": "Dogwood Memory Care Communities",
        "sector": "Memory Care",
        "buyer": "Harrison Street Real Estate Capital",
        "year": 2018,
        "region": "Southeast",
        "ev_mm": 285.0,
        "ev_ebitda": 14.5,
        "ebitda_mm": 45.60,
        "ebitda_margin": 0.18,
        "revenue_mm": 253.33,
        "hold_years": 5.5,
        "moic": 2.4,
        "irr": 0.1708,
        "status": "Realized",
        "payer_mix": {"commercial": 0.08, "medicaid": 0.42, "medicare": 0.28, "self_pay": 0.22},
        "comm_pct": 0.08,
        "deal_narrative": (
            "Southeast specialty memory care platform operating "
            "22 freestanding memory-care communities with 1,840 "
            "licensed secured memory-care units across Florida, "
            "Georgia, the Carolinas, and Alabama delivering "
            "specialized Alzheimer's-disease, vascular-dementia, "
            "Lewy-body-dementia, and frontotemporal-dementia "
            "resident care in secured memory-care communities "
            "with enhanced 1:6 caregiver-to-resident staffing "
            "ratios (versus 1:10-1:15 in standard AL), wander-"
            "management protocols, and specialized dementia-"
            "care-trained clinical staff. Revenue model captures "
            "premium private-pay rates of $8,200-$9,800/month "
            "per resident for specialized memory care, "
            "supplemented by state-level Medicaid HCBS (home-"
            "and-community-based-services) waiver payments and "
            "Medicare Advantage institutional special-needs-plan "
            "(I-SNP) managed-care payments on the dual-eligible "
            "portion of the memory-care census. Hold scaled "
            "community footprint from 14 to 22 communities "
            "through 6 ground-up developments and 2 tuck-in "
            "acquisitions, navigated the Ventas and Welltower "
            "master-lease structures covering 15 of 22 "
            "communities, and captured secular memory-care "
            "demand growth from the aging-of-boomers / "
            "Alzheimer's-prevalence demographic tailwind. "
            "Exited to a senior-housing REIT / strategic memory-"
            "care consolidator at 2.4x MOIC."
        ),
    },
    {
        "company_name": "Elm Assisted Living Partners",
        "sector": "Assisted Living",
        "buyer": "Fortress Investment Group",
        "year": 2019,
        "region": "West",
        "ev_mm": 365.0,
        "ev_ebitda": 13.5,
        "ebitda_mm": 54.75,
        "ebitda_margin": 0.15,
        "revenue_mm": 365.00,
        "hold_years": 5.0,
        "moic": 1.7,
        "irr": 0.1146,
        "status": "Realized",
        "payer_mix": {"commercial": 0.10, "medicaid": 0.38, "medicare": 0.26, "self_pay": 0.26},
        "comm_pct": 0.10,
        "deal_narrative": (
            "West Coast assisted living (AL) platform operating "
            "34 AL communities with 3,280 licensed AL units "
            "across California, Oregon, Washington, Arizona, "
            "and Nevada delivering private-pay residential AL "
            "services for semi-independent elderly residents "
            "requiring activities-of-daily-living (ADL) "
            "assistance but not skilled nursing care. Revenue "
            "model captures private-pay monthly rates of "
            "$5,800-$7,200/month per resident reflecting West "
            "Coast senior-housing price levels, supplemented by "
            "meaningful state-Medicaid HCBS-waiver census on "
            "the lower-income AL-qualified resident population. "
            "Platform operated under state AL licensure "
            "regulations rather than federal Medicare/Medicaid "
            "SNF certification, exposing operator economics to "
            "residential-real-estate cycle dynamics and single-"
            "family-home-price-driven demand cyclicality — "
            "prospective AL residents typically fund AL "
            "residency by selling their single-family home, "
            "making AL occupancy and rate-increase absorption "
            "correlated to regional single-family-home-price "
            "trends. Modest 1.7x MOIC reflects (a) COVID-era "
            "2020-2021 occupancy disruption compressing platform "
            "ADC from 89% to 74% with extended 2022-2024 "
            "recovery, (b) senior-housing construction "
            "oversupply in select California MSAs compressing "
            "rate growth, and (c) staffing wage inflation in "
            "West Coast senior-housing labor markets compressing "
            "margins from 18% to 15%. Exited to a senior-"
            "housing REIT at 1.7x MOIC."
        ),
    },
    {
        "company_name": "Fir SNF Consolidation Platform",
        "sector": "Skilled Nursing Facility",
        "buyer": "TPG Capital",
        "year": 2015,
        "region": "National",
        "ev_mm": 825.0,
        "ev_ebitda": 14.0,
        "ebitda_mm": 148.50,
        "ebitda_margin": 0.18,
        "revenue_mm": 825.00,
        "hold_years": 6.5,
        "moic": 3.2,
        "irr": 0.1969,
        "status": "Realized",
        "payer_mix": {"commercial": 0.10, "medicaid": 0.44, "medicare": 0.34, "self_pay": 0.12},
        "comm_pct": 0.10,
        "deal_narrative": (
            "National skilled nursing facility (SNF) "
            "consolidation platform operating 118 Medicare/"
            "Medicaid-certified SNF facilities with 14,200 "
            "licensed beds across 18 states under a blended "
            "Ventas / Omega Healthcare Investors / CareTrust "
            "REIT master-lease structure. Platform operated the "
            "full SNF economic model with 34% Medicare Part A "
            "short-stay skilled-mix census (Medicare Part A "
            "PDPM per-diem ~$620/day) supporting the majority "
            "of EBITDA contribution, supplemented by 44% "
            "Medicaid long-stay custodial LTC census (blended "
            "state-Medicaid per-diem ~$265/day across the 18-"
            "state footprint). Long 6.5-year hold executed the "
            "PE-backed SNF consolidation playbook — added 42 "
            "tuck-in SNF facility acquisitions across "
            "contiguous MSAs capturing regional operating "
            "density, navigated the October 2019 PDPM "
            "transition restructuring contract-therapy "
            "relationships and MDS workflows, improved "
            "platform CMS 5-star Nursing Home Compare average "
            "rating from 2.9 to 3.7 stars, reduced 30-day "
            "all-cause readmission rate from 22.8% to 18.1% "
            "capturing SNF VBP value-based payment incentive, "
            "expanded skilled mix from 28% to 34%, and "
            "navigated Medicare RAC (Recovery Audit Contractor) "
            "audit exposure on Medicare Part A PDPM case-mix "
            "coding through disciplined MDS documentation "
            "workflows. Exited to a strategic national SNF "
            "operator at 3.2x MOIC — the top-performing SNF "
            "exit in the 2015-2022 PE-backed SNF cycle."
        ),
    },
    {
        "company_name": "Gingko LTACH Specialty Hospitals",
        "sector": "Post-Acute Rehab",
        "buyer": "Kohlberg & Company",
        "year": 2017,
        "region": "Mid-Atlantic",
        "ev_mm": 445.0,
        "ev_ebitda": 15.0,
        "ebitda_mm": 71.20,
        "ebitda_margin": 0.16,
        "revenue_mm": 445.00,
        "hold_years": 6.0,
        "moic": 2.5,
        "irr": 0.1671,
        "status": "Realized",
        "payer_mix": {"commercial": 0.14, "medicaid": 0.38, "medicare": 0.36, "self_pay": 0.12},
        "comm_pct": 0.14,
        "deal_narrative": (
            "Mid-Atlantic long-term-acute-care hospital (LTACH) "
            "and post-acute rehab platform operating 8 "
            "Medicare-certified LTACH specialty hospitals and 6 "
            "inpatient rehabilitation facilities (IRFs) across "
            "Pennsylvania, New Jersey, Maryland, Virginia, and "
            "Delaware delivering high-acuity medically complex "
            "post-acute hospital-level care for ventilator-"
            "weaning, wound-care, post-ICU medically complex, "
            "and septic-recovery patient populations under the "
            "Medicare LTACH-PPS case-mix-weighted reimbursement "
            "framework. Platform navigated CMS LTACH patient-"
            "criteria requirements (≥25-day average length of "
            "stay, LTACH-qualifying acute-hospital ICU / "
            "ventilator / respiratory-failure transfer source) "
            "and the site-neutral payment framework applying "
            "IPPS (inpatient prospective payment system) rates "
            "to LTACH admissions failing the LTACH patient-"
            "criteria threshold — a material Medicare "
            "reimbursement compression for out-of-criteria "
            "LTACH admissions requiring disciplined admission-"
            "screening workflows. Long 6-year hold navigated "
            "the LTACH site-neutral rate phase-in, built ICU / "
            "respiratory-failure referral-pathway relationships "
            "with 22 Mid-Atlantic acute-hospital systems, "
            "optimized Medicare IRF-PAI case-mix documentation "
            "on the IRF service line, and exited to a "
            "strategic specialty-hospital operator at 2.5x MOIC."
        ),
    },
    {
        "company_name": "Hickory Medicaid Nursing Homes",
        "sector": "Long-Term Care",
        "buyer": "GI Partners",
        "year": 2016,
        "region": "South",
        "ev_mm": 385.0,
        "ev_ebitda": 11.5,
        "ebitda_mm": 50.05,
        "ebitda_margin": 0.13,
        "revenue_mm": 385.00,
        "hold_years": 6.0,
        "moic": 1.6,
        "irr": 0.0815,
        "status": "Realized",
        "payer_mix": {"commercial": 0.06, "medicaid": 0.56, "medicare": 0.26, "self_pay": 0.12},
        "comm_pct": 0.06,
        "deal_narrative": (
            "South Central Medicaid-dominant nursing home "
            "platform operating 42 LTC facilities with 4,680 "
            "licensed beds across Texas, Louisiana, Arkansas, "
            "Oklahoma, and Mississippi under an Omega "
            "Healthcare Investors master-lease structure "
            "covering 38 of 42 facilities. Platform census "
            "heavily weighted to Medicaid long-stay custodial "
            "LTC residents (58% Medicaid payer mix — the "
            "highest Medicaid concentration in the PE-backed "
            "SNF/LTC subsector) reflecting the low-income "
            "South Central elderly population and state "
            "Medicaid LTC per-diem rate environments "
            "($195-$245/day state-Medicaid per-diem across the "
            "five-state footprint — the lowest in the U.S. "
            "Medicaid LTC rate spectrum). Low 13% EBITDA "
            "margin reflects the Medicaid-dominant payer mix "
            "and the inherent margin compression of low-rate "
            "Southern Medicaid LTC per-diem economics. Hold "
            "navigated (a) the October 2019 PDPM transition on "
            "the 22% Medicare Part A skilled-mix census, (b) "
            "Texas, Louisiana, and Mississippi state-Medicaid "
            "LTC rate-parity legislative battles with mixed "
            "rate-adjustment outcomes, (c) COVID-era occupancy "
            "disruption compressing ADC from 84% to 68%, (d) "
            "Medicare RAC audit recoupment exposure on 2,400 "
            "audited SNF Medicare Part A claims resulting in "
            "$3.8M aggregate recoupment, and (e) Omega Health "
            "Investors master-lease EBITDAR coverage-ratio "
            "covenant pressure through the COVID trough. "
            "Modest 1.6x MOIC reflects Medicaid-dominant "
            "margin compression and COVID occupancy disruption. "
            "Exited to a strategic LTC operator."
        ),
    },
    {
        "company_name": "Ironwood Rehab & Wellness",
        "sector": "Post-Acute Rehab",
        "buyer": "Revelstoke Capital Partners",
        "year": 2020,
        "region": "Southwest",
        "ev_mm": 185.0,
        "ev_ebitda": 13.5,
        "ebitda_mm": 33.30,
        "ebitda_margin": 0.18,
        "revenue_mm": 185.00,
        "hold_years": 4.0,
        "moic": 1.7,
        "irr": 0.1410,
        "status": "Active",
        "payer_mix": {"commercial": 0.14, "medicaid": 0.40, "medicare": 0.34, "self_pay": 0.12},
        "comm_pct": 0.14,
        "deal_narrative": (
            "Southwest post-acute rehabilitation platform "
            "operating 6 Medicare-certified inpatient "
            "rehabilitation facilities (IRFs) and 18 SNF post-"
            "acute rehab units across Texas, New Mexico, and "
            "Arizona delivering post-acute rehab services for "
            "orthopedic-joint-replacement, stroke, and "
            "medically complex patient populations under the "
            "Medicare IRF-PPS case-mix-weighted reimbursement "
            "framework. Platform navigating CMS 60% rule "
            "compliance, IRF-PAI functional-assessment case-"
            "mix documentation, and the SNF VBP 30-day "
            "readmission measure on the SNF-based post-acute "
            "rehab units. Mid-hold executing (a) Medicare "
            "Advantage 3-midnight-waiver referral-pathway "
            "capture from MA plan post-acute direct-referral "
            "programs bypassing the traditional 3-midnight "
            "acute-hospital qualifying stay requirement, (b) "
            "PDPM case-mix optimization on SNF-rehab census "
            "with refined clinical-acuity documentation "
            "capture, (c) readmission-reduction initiatives "
            "targeting sub-18% 30-day all-cause readmission "
            "rate capturing SNF VBP incentive, (d) CareTrust "
            "REIT master-lease EBITDAR-coverage management on "
            "14 of 24 facilities, and (e) 4 targeted tuck-in "
            "IRF acquisitions. Targeting sale to a strategic "
            "post-acute consolidator at a low-teens multiple "
            "at a mid-hold 1.7x MOIC trajectory."
        ),
    },
    {
        "company_name": "Juniper Senior Living Communities",
        "sector": "Assisted Living",
        "buyer": "Kayne Anderson Real Estate",
        "year": 2017,
        "region": "National",
        "ev_mm": 625.0,
        "ev_ebitda": 14.5,
        "ebitda_mm": 93.75,
        "ebitda_margin": 0.15,
        "revenue_mm": 625.00,
        "hold_years": 6.5,
        "moic": 1.8,
        "irr": 0.0946,
        "status": "Realized",
        "payer_mix": {"commercial": 0.12, "medicaid": 0.38, "medicare": 0.26, "self_pay": 0.24},
        "comm_pct": 0.12,
        "deal_narrative": (
            "National assisted living and independent-living "
            "senior-housing platform operating 68 AL / IL / "
            "memory-care communities with 6,820 licensed units "
            "across 22 states under a Welltower / Ventas / "
            "Diversified Healthcare Trust master-lease "
            "structure. Platform delivered the full senior-"
            "housing continuum from independent-living "
            "apartments ($3,800-$5,200/month private-pay) "
            "through AL ($5,200-$7,500/month) and secured "
            "memory-care ($8,000-$10,500/month). Revenue mix "
            "dominated by 58% private-pay, supplemented by "
            "state-Medicaid HCBS-waiver census on the lower-"
            "income AL-qualified resident population. Long "
            "6.5-year hold navigated severe COVID-era 2020-2021 "
            "occupancy disruption — senior-housing occupancy "
            "declined from 90% to 72% as family decision-"
            "makers deferred senior-housing placement decisions "
            "and senior-housing COVID mortality disrupted the "
            "resident census — with extended 2022-2024 "
            "occupancy recovery to 84%. Executed Welltower / "
            "Ventas / DHC master-lease rent-deferral / "
            "EBITDAR-coverage-ratio renegotiation across the "
            "COVID occupancy trough, added 12 senior-housing "
            "tuck-in acquisitions in the post-COVID distressed-"
            "asset environment, and captured the post-2022 "
            "senior-housing demographic demand-recovery cycle. "
            "Modest 1.8x MOIC reflects severe COVID-era "
            "occupancy disruption and extended recovery "
            "timeline. Exited to a senior-housing REIT."
        ),
    },
    {
        "company_name": "Kauri SNF Regional Operator",
        "sector": "Skilled Nursing Facility",
        "buyer": "Apollo Global Management",
        "year": 2019,
        "region": "Northeast",
        "ev_mm": 495.0,
        "ev_ebitda": 13.0,
        "ebitda_mm": 76.23,
        "ebitda_margin": 0.14,
        "revenue_mm": 544.50,
        "hold_years": 5.0,
        "moic": 1.8,
        "irr": 0.1247,
        "status": "Active",
        "payer_mix": {"commercial": 0.10, "medicaid": 0.50, "medicare": 0.28, "self_pay": 0.12},
        "comm_pct": 0.10,
        "deal_narrative": (
            "Northeast regional SNF operator running 38 "
            "Medicare/Medicaid-certified SNF facilities with "
            "4,450 licensed beds across New York, New Jersey, "
            "Connecticut, Massachusetts, and Rhode Island "
            "under a Sabra Health Care REIT / Omega Healthcare "
            "Investors master-lease structure. Platform "
            "delivered Medicare Part A short-stay post-acute "
            "skilled rehabilitation and Medicaid-reimbursed "
            "long-stay custodial LTC census with 50% Medicaid "
            "payer mix reflecting Northeast high-acuity "
            "state-Medicaid LTC population and $305-$345/day "
            "Northeast state-Medicaid per-diem rates. Mid-hold "
            "navigating (a) the October 2019 PDPM transition "
            "effects on contract-therapy relationships and MDS "
            "assessment workflows, (b) severe COVID-era "
            "Northeast occupancy disruption (Northeast SNFs "
            "disproportionately impacted by early 2020 COVID "
            "outbreaks) compressing ADC from 88% to 65% with "
            "2022-2024 recovery to 80%, (c) Medicare RAC audit "
            "exposure on Medicare Part A PDPM case-mix coding "
            "with $6.2M aggregate audit recoupment across "
            "hold, (d) CMS 5-star rating improvement from 2.6 "
            "to 3.3 platform-average driving referral-share "
            "gains, and (e) New York and New Jersey state-"
            "Medicaid LTC rate-parity legislative advocacy "
            "achieving modest per-diem rate increases in 2022 "
            "and 2024. Targeting sale to a strategic SNF "
            "operator at a mid-teens multiple."
        ),
    },
    {
        "company_name": "Larch Memory Care Holdings",
        "sector": "Memory Care",
        "buyer": "Bridgewood Advisors",
        "year": 2020,
        "region": "Midwest",
        "ev_mm": 95.0,
        "ev_ebitda": 12.5,
        "ebitda_mm": 14.25,
        "ebitda_margin": 0.15,
        "revenue_mm": 95.00,
        "hold_years": 3.5,
        "moic": 1.4,
        "irr": 0.1000,
        "status": "Active",
        "payer_mix": {"commercial": 0.08, "medicaid": 0.44, "medicare": 0.28, "self_pay": 0.20},
        "comm_pct": 0.08,
        "deal_narrative": (
            "Midwest memory care platform operating 9 "
            "freestanding secured memory-care communities with "
            "720 licensed memory-care units across Ohio, "
            "Indiana, Michigan, and Wisconsin delivering "
            "specialized Alzheimer's-disease and vascular-"
            "dementia resident care with 1:5 caregiver-to-"
            "resident staffing ratios, wander-management "
            "protocols, and dementia-care-trained clinical "
            "staff. Revenue model captures Midwest private-"
            "pay memory-care rates of $6,800-$8,200/month "
            "(below coastal memory-care price levels "
            "reflecting Midwest senior-housing pricing), "
            "supplemented by state-Medicaid HCBS-waiver "
            "dementia-care census and MA I-SNP managed-care "
            "payments on the dual-eligible memory-care "
            "population. Acquired in mid-2020 at the onset of "
            "the COVID-era senior-housing distressed-asset "
            "cycle at attractive 12.5x EBITDA entry multiple. "
            "Early hold navigating (a) extended COVID-era "
            "memory-care occupancy disruption with memory-"
            "care-specific COVID mortality and family-"
            "placement-deferral dynamics compressing ADC from "
            "88% to 69%, (b) LTC Properties master-lease "
            "EBITDAR-coverage management through the "
            "occupancy trough, (c) 2022-2024 occupancy "
            "recovery to 81%, (d) Midwest senior-housing "
            "staffing wage inflation compressing margins, and "
            "(e) 2 targeted tuck-in memory-care community "
            "acquisitions. Mid-hold 1.4x MOIC trajectory "
            "reflects COVID-era operating headwinds; sponsor "
            "pursuing additional tuck-ins and continued "
            "occupancy recovery to reach target exit multiple."
        ),
    },
    {
        "company_name": "Maple SNF & Rehab Alliance",
        "sector": "Skilled Nursing Facility",
        "buyer": "Centerbridge Partners",
        "year": 2018,
        "region": "Pacific",
        "ev_mm": 565.0,
        "ev_ebitda": 14.0,
        "ebitda_mm": 96.05,
        "ebitda_margin": 0.17,
        "revenue_mm": 565.00,
        "hold_years": 6.0,
        "moic": 2.6,
        "irr": 0.1744,
        "status": "Realized",
        "payer_mix": {"commercial": 0.12, "medicaid": 0.42, "medicare": 0.34, "self_pay": 0.12},
        "comm_pct": 0.12,
        "deal_narrative": (
            "Pacific SNF and post-acute rehab platform "
            "operating 48 Medicare/Medicaid-certified SNF "
            "facilities with 5,680 licensed beds across "
            "California, Oregon, Washington, and Nevada under "
            "a Ventas / CareTrust REIT master-lease structure. "
            "Platform delivered integrated SNF short-stay "
            "skilled rehab, long-stay Medicaid LTC, and SNF-"
            "based post-acute orthopedic-rehab service lines "
            "with 34% Medicare Part A skilled mix supporting "
            "the core EBITDA contribution. Long 6-year hold "
            "navigated (a) the October 2019 PDPM transition — "
            "restructured contract-therapy relationships from "
            "prior RUG-IV therapy-minutes model to PDPM "
            "clinical-acuity model capturing $1.8M annualized "
            "therapy-cost savings and $3.2M annualized case-"
            "mix-capture revenue uplift, (b) the corresponding "
            "January 2020 PDGM home-health transition on "
            "adjacent post-acute referral pathways, (c) "
            "California-specific state-Medicaid LTC rate-"
            "parity legislative dynamics and the California "
            "Department of Public Health SNF-staffing "
            "regulatory environment, (d) CMS 5-star rating "
            "improvement from 2.9 to 3.8 platform-average, (e) "
            "30-day readmission reduction from 21.4% to 17.6% "
            "capturing SNF VBP value-based payment incentive, "
            "(f) Ventas master-lease rent-deferral through "
            "COVID occupancy trough, and (g) 12 targeted "
            "tuck-in SNF facility acquisitions. Exited to a "
            "strategic West Coast SNF operator at 2.6x MOIC."
        ),
    },
    {
        "company_name": "Nettle Long-Term Care Services",
        "sector": "Long-Term Care",
        "buyer": "Trive Capital",
        "year": 2021,
        "region": "Southeast",
        "ev_mm": 245.0,
        "ev_ebitda": 12.0,
        "ebitda_mm": 34.30,
        "ebitda_margin": 0.14,
        "revenue_mm": 245.00,
        "hold_years": 3.0,
        "moic": 1.5,
        "irr": 0.1447,
        "status": "Active",
        "payer_mix": {"commercial": 0.06, "medicaid": 0.54, "medicare": 0.26, "self_pay": 0.14},
        "comm_pct": 0.06,
        "deal_narrative": (
            "Southeast long-term care (LTC) platform operating "
            "24 Medicaid-dominant nursing home facilities with "
            "2,620 licensed beds across Florida, Georgia, "
            "Alabama, and South Carolina under a Diversified "
            "Healthcare Trust / National Health Investors "
            "master-lease structure. Platform census heavily "
            "weighted to Medicaid long-stay custodial LTC "
            "residents (54% Medicaid) with $220-$265/day "
            "state-Medicaid per-diem rates across the four-"
            "state Southeast footprint. Acquired in late 2021 "
            "at the tail of the COVID-era senior-housing "
            "distressed-asset cycle at attractive 12.0x EBITDA "
            "entry multiple. Early hold navigating (a) post-"
            "COVID occupancy recovery from 72% entry ADC "
            "toward 82% target, (b) the ongoing PDPM-era "
            "Medicare Part A case-mix-capture workflow "
            "optimization on the 26% skilled-mix census, (c) "
            "CMS 5-star rating improvement programs on the "
            "initial 2.4-star platform-average rating, (d) "
            "Florida and Georgia state-Medicaid LTC rate-"
            "parity legislative advocacy, (e) DHC / NHI "
            "master-lease EBITDAR-coverage-ratio management "
            "through the early-hold occupancy-recovery "
            "trajectory, and (f) Medicare RAC audit exposure "
            "with disciplined MDS assessment documentation "
            "workflow. Mid-hold 1.5x MOIC trajectory; sponsor "
            "targeting sale to a strategic LTC operator at "
            "a low-teens multiple on continued occupancy "
            "recovery and skilled-mix expansion."
        ),
    },
    {
        "company_name": "Olive Post-Acute Network",
        "sector": "Post-Acute Rehab",
        "buyer": "Webster Equity Partners",
        "year": 2016,
        "region": "National",
        "ev_mm": 785.0,
        "ev_ebitda": 16.0,
        "ebitda_mm": 141.30,
        "ebitda_margin": 0.20,
        "revenue_mm": 706.50,
        "hold_years": 6.5,
        "moic": 3.5,
        "irr": 0.2063,
        "status": "Realized",
        "payer_mix": {"commercial": 0.15, "medicaid": 0.38, "medicare": 0.35, "self_pay": 0.12},
        "comm_pct": 0.15,
        "deal_narrative": (
            "National post-acute rehabilitation platform "
            "operating 18 Medicare-certified inpatient "
            "rehabilitation facilities (IRFs), 12 LTACH "
            "specialty hospitals, and 62 SNF post-acute rehab "
            "units across 16 states delivering the full post-"
            "acute rehab continuum from highest-acuity LTACH "
            "medically complex care through IRF case-mix-"
            "weighted rehab to SNF post-acute skilled rehab "
            "under a blended Ventas / Welltower / Omega "
            "Healthcare Investors master-lease structure. "
            "Platform captured the Medicare Advantage "
            "3-midnight-waiver post-acute direct-referral "
            "pathway — MA plan 3-midnight-waiver programs "
            "bypass the traditional Medicare fee-for-service "
            "3-midnight acute-hospital qualifying stay "
            "requirement and direct MA members to PE-backed "
            "post-acute preferred-network facilities — driving "
            "MA-plan referral-share expansion from 12% to 28% "
            "of post-acute admissions across hold. Long 6.5-"
            "year hold executed (a) Medicare IRF-PPS case-mix "
            "documentation optimization capturing IRF-PAI "
            "functional-assessment-driven CMG (case-mix-group) "
            "reimbursement uplift, (b) the October 2019 PDPM "
            "transition on SNF-rehab service lines, (c) 30-day "
            "readmission-reduction SNF VBP program capture, "
            "(d) CMS 5-star rating improvement, (e) 18 tuck-"
            "in IRF / LTACH / SNF-rehab acquisitions, and (f) "
            "MA-plan preferred-network contract scaling. "
            "Exited to a strategic post-acute consolidator at "
            "3.5x MOIC — the top-performing post-acute rehab "
            "exit in the 2016-2022 PE-backed post-acute cycle."
        ),
    },
]
