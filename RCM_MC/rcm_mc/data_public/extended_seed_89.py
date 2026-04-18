"""Extended seed 89: Revenue cycle management, healthcare BPO, and medical
coding PE deals.

This module contains a curated set of 15 healthcare private equity deal
records focused on the revenue cycle management (RCM) / healthcare BPO /
medical coding subsector. The theme covers:

- End-to-end RCM platforms delivering patient access, coding, charge
  capture, claim scrubbing, submission, denial management, and
  collections across hospital and physician clients
- Medical coding services operators delivering inpatient (MS-DRG /
  APR-DRG), outpatient (APC), and professional-fee (E/M, CPT) coding
  under AAPC / AHIMA certified coder workforces, increasingly augmented
  by computer-assisted coding (CAC) engines embedded in the EHR
- Healthcare BPO platforms delivering offshore / nearshore labor
  arbitrage for insurance verification, eligibility, authorization,
  payment posting, and patient statement processing
- Denials management specialists attacking CARC/RARC-tagged claim
  denials, executing root-cause analysis against the top CARC families
  (CO-16 documentation, CO-50 medical necessity, CO-97 bundling,
  CO-197 precertification), and driving first-pass and overturn rates
- Prior authorization / utilization management platforms automating
  payer-specific PA workflows under CMS Interoperability and Prior
  Authorization Final Rule (CMS-0057-F) timelines and electronic PA
  (ePA) adoption across commercial, Medicare Advantage, and Medicaid

RCM / BPO economics are distinguished by a commercial-heavy payer
mix in the services layer (commercial claims carry higher per-claim
fees than Medicare FFS), sensitivity to No Surprises Act IDR volumes,
CMS price-transparency-driven patient-responsibility collections,
offshore cost-arbitrage labor pools in India and the Philippines, the
shift from clearinghouse fees to value-based contingency and per-claim
economics, AI/ML claim-scrub automation reducing initial denial rate,
EHR-integrated computer-assisted coding lifting coder productivity,
and specialty-specific coding depth (cardiology, orthopedics, oncology,
radiology) commanding pricing premiums. Value creation in PE-backed
RCM platforms centers on labor-arbitrage mix shift toward offshore
delivery, AI claim-scrub bolt-ons, EHR certification expansion (Epic,
Cerner, Meditech), specialty-vertical tuck-ins, and denial write-off
recovery under a contingency-fee model.

Each record captures deal economics (EV, EV/EBITDA, margins), return
profile (MOIC, IRR, hold period), payer mix, regional footprint, sponsor,
realization status, and a short deal narrative. These records are
synthesized for modeling, backtesting, and scenario analysis use cases.
"""

EXTENDED_SEED_DEALS_89 = [
    {
        "company_name": "Crestline RCM Partners",
        "sector": "RCM / Billing",
        "buyer": "Warburg Pincus",
        "year": 2019,
        "region": "National",
        "ev_mm": 565.0,
        "ev_ebitda": 14.5,
        "ebitda_mm": 38.97,
        "ebitda_margin": 0.22,
        "revenue_mm": 177.11,
        "hold_years": 5.0,
        "moic": 2.9,
        "irr": 0.2370,
        "status": "Realized",
        "payer_mix": {"commercial": 0.68, "medicare": 0.18, "medicaid": 0.09, "self_pay": 0.05},
        "comm_pct": 0.68,
        "deal_narrative": (
            "National end-to-end RCM platform serving mid-market hospital and "
            "physician clients across patient access, coding, claim scrubbing, "
            "submission, and denials. Long hold executed a denial write-off "
            "recovery playbook under a contingency-fee model, deployed an AI/ML "
            "claim-scrub engine that lifted first-pass clean claim rate from "
            "88% to 94%, shifted 40% of back-office FTEs to offshore delivery, "
            "and exited to a strategic healthcare IT acquirer at a 2.9x MOIC."
        ),
    },
    {
        "company_name": "Beacon Medical Coding",
        "sector": "Medical Coding",
        "buyer": "New Mountain Capital",
        "year": 2020,
        "region": "National",
        "ev_mm": 385.0,
        "ev_ebitda": 13.5,
        "ebitda_mm": 28.52,
        "ebitda_margin": 0.23,
        "revenue_mm": 124.00,
        "hold_years": 4.5,
        "moic": 2.5,
        "irr": 0.2207,
        "status": "Active",
        "payer_mix": {"commercial": 0.66, "medicare": 0.19, "medicaid": 0.10, "self_pay": 0.05},
        "comm_pct": 0.66,
        "deal_narrative": (
            "National medical coding services operator delivering inpatient "
            "MS-DRG, outpatient APC, and professional-fee E/M coding under a "
            "1,800-coder AAPC/AHIMA-certified workforce. Value creation deploys "
            "EHR-integrated computer-assisted coding (CAC) across Epic and "
            "Cerner clients lifting coder throughput 35%, expands specialty-"
            "specific coding depth in cardiology and orthopedics at premium "
            "rates, and builds an India-based offshore coder bench for "
            "overnight turnaround on inpatient discharges."
        ),
    },
    {
        "company_name": "Sentinel Healthcare BPO",
        "sector": "Healthcare BPO",
        "buyer": "TPG",
        "year": 2018,
        "region": "National",
        "ev_mm": 720.0,
        "ev_ebitda": 13.0,
        "ebitda_mm": 55.38,
        "ebitda_margin": 0.20,
        "revenue_mm": 276.92,
        "hold_years": 6.0,
        "moic": 3.4,
        "irr": 0.2266,
        "status": "Realized",
        "payer_mix": {"commercial": 0.64, "medicare": 0.20, "medicaid": 0.11, "self_pay": 0.05},
        "comm_pct": 0.64,
        "deal_narrative": (
            "National healthcare BPO platform delivering eligibility, insurance "
            "verification, prior authorization, payment posting, and patient "
            "statement services. Long hold scaled the India and Philippines "
            "offshore delivery centers from 1,200 to 4,500 FTEs, captured "
            "cost-arbitrage savings of 55-65% per seat vs domestic, deployed "
            "AI/ML claim-scrub automation across payment posting, and exited "
            "to a strategic IT services acquirer at a 3.4x MOIC on scale."
        ),
    },
    {
        "company_name": "Ridgewater Denials Management",
        "sector": "Denials Management",
        "buyer": "Welsh Carson",
        "year": 2021,
        "region": "National",
        "ev_mm": 295.0,
        "ev_ebitda": 14.0,
        "ebitda_mm": 21.07,
        "ebitda_margin": 0.24,
        "revenue_mm": 87.80,
        "hold_years": 4.0,
        "moic": 2.2,
        "irr": 0.2204,
        "status": "Active",
        "payer_mix": {"commercial": 0.72, "medicare": 0.15, "medicaid": 0.08, "self_pay": 0.05},
        "comm_pct": 0.72,
        "deal_narrative": (
            "National denials management specialist attacking CARC/RARC-tagged "
            "claim denials under a contingency-fee model across hospital "
            "clients. Value creation drives root-cause analysis against the "
            "top CARC families (CO-16 documentation, CO-50 medical necessity, "
            "CO-97 bundling, CO-197 precertification), deploys AI/ML denial "
            "prediction models at the claim-scrub stage to reduce initial "
            "denial rate, and lifts overturn rates on appealed write-offs."
        ),
    },
    {
        "company_name": "Meridian Prior Auth",
        "sector": "Prior Authorization",
        "buyer": "Thoma Bravo",
        "year": 2022,
        "region": "National",
        "ev_mm": 245.0,
        "ev_ebitda": 15.5,
        "ebitda_mm": 15.81,
        "ebitda_margin": 0.21,
        "revenue_mm": 75.27,
        "hold_years": 3.5,
        "moic": 1.7,
        "irr": 0.1608,
        "status": "Active",
        "payer_mix": {"commercial": 0.74, "medicare": 0.14, "medicaid": 0.07, "self_pay": 0.05},
        "comm_pct": 0.74,
        "deal_narrative": (
            "National prior authorization platform automating payer-specific PA "
            "workflows across commercial, MA, and Medicaid lines. Value creation "
            "capitalizes on the CMS Interoperability and Prior Authorization "
            "Final Rule (CMS-0057-F) mandating electronic PA API adoption and "
            "72-hour urgent / 7-day standard decision timelines, deploys an AI/"
            "ML clinical-criteria matching engine for automated PA submission, "
            "and integrates with Epic and Cerner EHRs for seamless provider UX."
        ),
    },
    {
        "company_name": "Harborlight RCM Services",
        "sector": "RCM / Billing",
        "buyer": "Bain Capital",
        "year": 2017,
        "region": "Northeast",
        "ev_mm": 435.0,
        "ev_ebitda": 12.5,
        "ebitda_mm": 34.80,
        "ebitda_margin": 0.22,
        "revenue_mm": 158.18,
        "hold_years": 6.5,
        "moic": 3.2,
        "irr": 0.1939,
        "status": "Realized",
        "payer_mix": {"commercial": 0.65, "medicare": 0.21, "medicaid": 0.09, "self_pay": 0.05},
        "comm_pct": 0.65,
        "deal_narrative": (
            "Northeast RCM services platform anchored in AMC and IDN clients "
            "across New York, Boston, and Philadelphia delivering end-to-end "
            "RCM, charge capture, and denials. Long hold executed a labor-"
            "arbitrage mix shift moving 45% of back-office FTEs offshore to "
            "India, layered an AI/ML claim-scrub bolt-on reducing initial "
            "denial rate from 12% to 7%, and exited to a national strategic "
            "RCM consolidator at a 3.2x MOIC following EBITDA scale."
        ),
    },
    {
        "company_name": "Summit Coding Partners",
        "sector": "Medical Coding",
        "buyer": "Audax",
        "year": 2023,
        "region": "Southeast",
        "ev_mm": 135.0,
        "ev_ebitda": 11.5,
        "ebitda_mm": 11.74,
        "ebitda_margin": 0.18,
        "revenue_mm": 65.22,
        "hold_years": 2.5,
        "moic": 1.4,
        "irr": 0.1472,
        "status": "Held",
        "payer_mix": {"commercial": 0.63, "medicare": 0.22, "medicaid": 0.10, "self_pay": 0.05},
        "comm_pct": 0.63,
        "deal_narrative": (
            "Southeast medical coding platform serving community hospitals and "
            "physician groups across Florida, Georgia, and the Carolinas with "
            "AHIMA-certified inpatient and outpatient coding. Early hold "
            "deploys EHR-integrated computer-assisted coding across Meditech "
            "and Cerner clients, scales a Philippines-based offshore coder "
            "bench for E/M professional-fee coding cost arbitrage, and pursues "
            "specialty-specific tuck-ins in oncology and radiology coding."
        ),
    },
    {
        "company_name": "Everline Healthcare BPO",
        "sector": "Healthcare BPO",
        "buyer": "KKR",
        "year": 2020,
        "region": "National",
        "ev_mm": 625.0,
        "ev_ebitda": 14.0,
        "ebitda_mm": 44.64,
        "ebitda_margin": 0.21,
        "revenue_mm": 212.57,
        "hold_years": 4.5,
        "moic": 2.4,
        "irr": 0.2054,
        "status": "Active",
        "payer_mix": {"commercial": 0.67, "medicare": 0.18, "medicaid": 0.10, "self_pay": 0.05},
        "comm_pct": 0.67,
        "deal_narrative": (
            "National healthcare BPO platform delivering eligibility, patient "
            "access, and back-office revenue cycle services across hospital "
            "and physician clients. Value creation scales India and Philippines "
            "offshore delivery to 6,200 FTEs at 60% cost arbitrage vs domestic, "
            "deploys AI/ML claim-scrub automation and intelligent document "
            "processing for explanation-of-benefits posting, and layers a No "
            "Surprises Act IDR submission desk capturing commercial volumes."
        ),
    },
    {
        "company_name": "Cardinal Denials Recovery",
        "sector": "Denials Management",
        "buyer": "TA Associates",
        "year": 2019,
        "region": "National",
        "ev_mm": 185.0,
        "ev_ebitda": 12.0,
        "ebitda_mm": 15.42,
        "ebitda_margin": 0.25,
        "revenue_mm": 61.67,
        "hold_years": 5.5,
        "moic": 2.7,
        "irr": 0.2010,
        "status": "Realized",
        "payer_mix": {"commercial": 0.70, "medicare": 0.16, "medicaid": 0.09, "self_pay": 0.05},
        "comm_pct": 0.70,
        "deal_narrative": (
            "National denials management recovery specialist working aged "
            "hospital AR write-offs under a contingency-fee model. Long hold "
            "executed root-cause analysis against CO-16 documentation and "
            "CO-50 medical necessity denials, deployed AI/ML pattern "
            "recognition to prioritize the highest-yield appeal candidates, "
            "lifted overturn rate from 32% to 48% on denied claims, and "
            "exited to a strategic RCM platform at a 2.7x MOIC."
        ),
    },
    {
        "company_name": "Lakemont Prior Authorization",
        "sector": "Prior Authorization",
        "buyer": "Silver Lake",
        "year": 2023,
        "region": "National",
        "ev_mm": 165.0,
        "ev_ebitda": 16.0,
        "ebitda_mm": 10.31,
        "ebitda_margin": 0.19,
        "revenue_mm": 54.28,
        "hold_years": 3.0,
        "moic": 1.5,
        "irr": 0.1447,
        "status": "Held",
        "payer_mix": {"commercial": 0.73, "medicare": 0.15, "medicaid": 0.07, "self_pay": 0.05},
        "comm_pct": 0.73,
        "deal_narrative": (
            "National prior authorization automation platform serving physician "
            "groups and specialty practices. Early hold executes on the CMS-"
            "0057-F electronic PA API rule driving payer ePA adoption by "
            "January 2027, deploys an AI/ML clinical-criteria matching engine "
            "that auto-drafts PA submissions from the EHR progress note, and "
            "scales specialty-specific PA workflows in oncology and radiology "
            "where high-cost PA denial rates drive provider pain."
        ),
    },
    {
        "company_name": "Evergreen RCM Solutions",
        "sector": "RCM / Billing",
        "buyer": "Vista Equity",
        "year": 2022,
        "region": "National",
        "ev_mm": 510.0,
        "ev_ebitda": 17.5,
        "ebitda_mm": 29.14,
        "ebitda_margin": 0.22,
        "revenue_mm": 132.47,
        "hold_years": 3.5,
        "moic": 1.8,
        "irr": 0.1793,
        "status": "Active",
        "payer_mix": {"commercial": 0.69, "medicare": 0.17, "medicaid": 0.09, "self_pay": 0.05},
        "comm_pct": 0.69,
        "deal_narrative": (
            "National RCM software-enabled services platform delivering a "
            "cloud-native RCM workflow engine plus managed services across "
            "physician practice clients. Value creation embeds AI/ML claim-"
            "scrub automation pre-submission lifting clean claim rate, scales "
            "an Epic-certified EHR-integrated CAC coding overlay, builds out "
            "an India-based offshore delivery center for payment posting, and "
            "pursues specialty-vertical tuck-ins in cardiology and orthopedics."
        ),
    },
    {
        "company_name": "Pinehurst Medical Coding",
        "sector": "Medical Coding",
        "buyer": "Frazier Healthcare",
        "year": 2018,
        "region": "National",
        "ev_mm": 215.0,
        "ev_ebitda": 12.0,
        "ebitda_mm": 17.92,
        "ebitda_margin": 0.23,
        "revenue_mm": 77.90,
        "hold_years": 6.0,
        "moic": 3.1,
        "irr": 0.2098,
        "status": "Realized",
        "payer_mix": {"commercial": 0.64, "medicare": 0.22, "medicaid": 0.09, "self_pay": 0.05},
        "comm_pct": 0.64,
        "deal_narrative": (
            "National medical coding services operator specializing in "
            "inpatient MS-DRG and outpatient APC coding for community hospital "
            "clients. Long hold scaled a 2,400-coder AAPC/AHIMA-certified "
            "workforce, deployed computer-assisted coding integrated with Epic "
            "and Meditech EHRs lifting productivity 40%, built specialty "
            "coding depth in cardiology interventional procedures, and exited "
            "to a strategic RCM consolidator at a 3.1x MOIC on scale."
        ),
    },
    {
        "company_name": "Westmark Healthcare BPO",
        "sector": "Healthcare BPO",
        "buyer": "Cressey & Company",
        "year": 2021,
        "region": "National",
        "ev_mm": 325.0,
        "ev_ebitda": 13.5,
        "ebitda_mm": 24.07,
        "ebitda_margin": 0.21,
        "revenue_mm": 114.63,
        "hold_years": 4.0,
        "moic": 2.1,
        "irr": 0.2037,
        "status": "Active",
        "payer_mix": {"commercial": 0.65, "medicare": 0.19, "medicaid": 0.11, "self_pay": 0.05},
        "comm_pct": 0.65,
        "deal_narrative": (
            "National healthcare BPO platform delivering patient statement, "
            "self-pay collections, and customer service across hospital and "
            "physician clients. Value creation scales Philippines-based "
            "offshore delivery to 3,800 FTEs at 58% cost arbitrage, deploys "
            "AI/ML propensity-to-pay scoring for patient self-pay segmentation "
            "under CMS price-transparency-driven patient responsibility growth, "
            "and layers a No Surprises Act IDR submission workflow desk."
        ),
    },
    {
        "company_name": "Glenmore Denials Solutions",
        "sector": "Denials Management",
        "buyer": "Shore Capital",
        "year": 2016,
        "region": "Midwest",
        "ev_mm": 85.0,
        "ev_ebitda": 10.5,
        "ebitda_mm": 8.10,
        "ebitda_margin": 0.17,
        "revenue_mm": 47.61,
        "hold_years": 6.5,
        "moic": 3.6,
        "irr": 0.2124,
        "status": "Realized",
        "payer_mix": {"commercial": 0.69, "medicare": 0.17, "medicaid": 0.09, "self_pay": 0.05},
        "comm_pct": 0.69,
        "deal_narrative": (
            "Midwest denials management specialist across Ohio, Illinois, and "
            "Michigan hospital clients working aged write-offs under a "
            "contingency-fee model. Long hold executed a platform playbook "
            "targeting CO-97 bundling and CO-197 precertification denials, "
            "deployed an AI/ML appeal-prioritization engine, scaled an India "
            "back-office for appeal letter drafting, and exited to a national "
            "RCM platform at a 3.6x MOIC driven by multiple expansion."
        ),
    },
    {
        "company_name": "Coastline Prior Auth Services",
        "sector": "Prior Authorization",
        "buyer": "Nordic Capital",
        "year": 2020,
        "region": "National",
        "ev_mm": 205.0,
        "ev_ebitda": 13.5,
        "ebitda_mm": 15.19,
        "ebitda_margin": 0.20,
        "revenue_mm": 75.93,
        "hold_years": 5.0,
        "moic": 2.3,
        "irr": 0.1812,
        "status": "Active",
        "payer_mix": {"commercial": 0.70, "medicare": 0.16, "medicaid": 0.09, "self_pay": 0.05},
        "comm_pct": 0.70,
        "deal_narrative": (
            "National prior authorization services platform managing PA "
            "workflows for specialty practices and ambulatory surgery centers. "
            "Value creation scales a hybrid domestic clinician plus offshore "
            "administrative workforce, deploys an AI/ML clinical-criteria "
            "matching engine against payer medical policies, captures the CMS-"
            "0057-F ePA adoption tailwind requiring 72-hour urgent PA "
            "decisions, and layers specialty coding depth in oncology PA."
        ),
    },
]
