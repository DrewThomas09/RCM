"""The healthcare-subsector registry — the ~55-subsector map.

Single source of truth for which subsectors the workbench knows how to
diligence, organised into the six :class:`~rcm_mc.taxonomy.models.Grouping`
buckets. Each entry carries its business model, KPI pack, reimbursement
codes/mechanics, public data sources, 2025-26 thesis/risks, and the standard
CDD exhibits — sourced from the platform's subsector research, not invented.

Adding a subsector is a data edit here plus a count bump in
``tests/test_taxonomy.py``; no other module needs to change. Lookups
(:func:`by_id`, :func:`by_grouping`, :func:`search`, …) are defined at the
bottom and re-exported from :mod:`rcm_mc.taxonomy`.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from .models import Grouping, KPI, Subsector

# Short alias keeps the dense KPI lists readable without a custom format.
K = KPI
G = Grouping


_SUBSECTORS: Tuple[Subsector, ...] = (
    # ── GROUPING 1 — PROVIDER SERVICES / PPM ──────────────────────────────
    Subsector(
        id="dermatology",
        name="Dermatology",
        grouping=G.PROVIDER_SERVICES,
        business_model="High-volume office procedural + cosmetic cash-pay + "
                       "pathology/Mohs ancillary, under an MSO/PC structure.",
        kpis=(
            K("Visits per provider per day", "count"),
            K("Mohs cases", "count"),
            K("Pathology in-sourcing %", "pct"),
            K("Cosmetic (cash) mix", "pct"),
            K("PA/NP leverage ratio", "ratio"),
        ),
        reimbursement_codes=("E/M 99202-99215", "biopsy 11102-11104",
                             "Mohs 17311-17315", "path 88305"),
        reimbursement_mechanics="FFS office E/M + procedure fees; cosmetic is "
                                "cash-pay; pathology/Mohs in-sourced as ancillary.",
        data_sources=("CMS Physician & Other Practitioners", "NPPES",
                      "Open Payments", "DocGraph referral data", "MGMA benchmarks"),
        thesis="Aging demographics + skin-cancer prevalence + cosmetic cash pay; "
               "~30+ PE platforms by 2020.",
        risks="PA/NP supervision scrutiny, E/M downcoding, biopsy "
              "overutilization scrutiny.",
        exhibits=("Provider productivity vs MGMA", "Ancillary penetration bridge",
                  "Cosmetic vs medical mix", "Mohs referral map"),
        vertical="MSO",
    ),
    Subsector(
        id="ophthalmology",
        name="Ophthalmology / Optometry",
        grouping=G.PROVIDER_SERVICES,
        business_model="Cataract/retina surgical + optical retail + ASC JV.",
        kpis=(
            K("Surgical volume (cataracts/yr)", "count"),
            K("Premium IOL mix (cash upgrade)", "pct"),
            K("Anti-VEGF injections", "count"),
            K("Optical capture rate", "pct"),
        ),
        reimbursement_codes=("66984/66982 cataract", "67028 intravitreal injection",
                             "J-codes Eylea/Lucentis (drug pass-through)"),
        reimbursement_mechanics="Surgical professional + ASC facility fee; "
                                "high-cost retina drugs reimbursed ASP+6% (buy-and-bill).",
        data_sources=("CMS Physician & Other Practitioners", "NPPES",
                      "Open Payments", "MGMA benchmarks"),
        thesis="Aging, retina drug volume; recent Cencora/Retina Consultants, "
               "McKesson/Prism Vision.",
        risks="Drug-cost reimbursement (ASP+6%), MA scrutiny.",
        exhibits=("Surgical case-mix", "IOL upgrade penetration",
                  "Drug margin (buy-and-bill) analysis"),
        vertical="MSO",
    ),
    Subsector(
        id="gastroenterology",
        name="Gastroenterology",
        grouping=G.PROVIDER_SERVICES,
        business_model="Endoscopy + ASC + pathology + anesthesia + infusion "
                       "(biologics) ancillary roll-up.",
        kpis=(
            K("Procedures per MD", "count"),
            K("ASC site-of-service capture", "pct"),
            K("Pathology/anesthesia in-sourcing", "pct"),
            K("Screening vs diagnostic mix", "pct"),
        ),
        reimbursement_codes=("45378-45385 colonoscopy", "43235-43239 EGD"),
        reimbursement_mechanics="Professional + ASC facility fee; ancillary "
                                "pathology/anesthesia/infusion margin.",
        data_sources=("CMS Physician & Other Practitioners", "NPPES",
                      "DocGraph referral data", "HCRIS (ASC)"),
        thesis="Screening age lowered to 45, ASC migration, ancillary roll-up "
               "(GI Alliance scale).",
        risks="Payer screening reimbursement, anesthesia OON.",
        exhibits=("ASC migration capture", "Ancillary EBITDA bridge",
                  "Screening-eligible population sizing"),
        vertical="MSO",
    ),
    Subsector(
        id="orthopedics",
        name="Orthopedics / MSK",
        grouping=G.PROVIDER_SERVICES,
        business_model="Surgical + ASC migration (total joints) + PT + imaging "
                       "+ DME ancillary.",
        kpis=(
            K("Surgical case volume", "count"),
            K("ASC-eligible case migration %", "pct"),
            K("Implant cost per case", "dollars"),
            K("PT visits per referral", "ratio"),
            K("Ancillary capture", "pct"),
        ),
        reimbursement_codes=("27447 TKA", "27130 THA", "29826/29827 arthroscopy"),
        reimbursement_mechanics="Professional + site-of-service facility fee "
                                "(HOPD vs ASC); implant cost pass-through.",
        data_sources=("CMS Physician & Other Practitioners", "OPPS/ASC FS",
                      "NPPES", "DocGraph referral data"),
        thesis="Site-of-service shift to ASC (spine ~20-25% of ortho procedures "
               "but >50% of profit), aging, ancillary.",
        risks="Implant cost, CON for ASC.",
        exhibits=("Site-of-service differential ($)", "Implant cost benchmarking",
                  "Ancillary ladder"),
        vertical="MSO",
    ),
    Subsector(
        id="cardiology",
        name="Cardiology",
        grouping=G.PROVIDER_SERVICES,
        business_model="Office E/M + cath lab/imaging + ASC (office-based labs) "
                       "+ VBC.",
        kpis=(
            K("Imaging volume (echo, nuclear)", "count"),
            K("Cath/PCI volume", "count"),
            K("OBL migration", "pct"),
        ),
        reimbursement_codes=("93306 echo", "93000 EKG", "92928 PCI"),
        reimbursement_mechanics="FFS office + imaging technical/professional; "
                                "OBL site-of-service economics; VBC capitation adjacency.",
        data_sources=("CMS Physician & Other Practitioners", "NPPES",
                      "DocGraph referral data"),
        thesis="OBL site-of-service shift, VBC cardiology (cardiometabolic "
               "risk), aging.",
        risks="Imaging self-referral (Stark), reimbursement cuts.",
        exhibits=("Imaging volume vs benchmark", "OBL economics",
                  "Referral inflow map"),
        vertical="MSO",
    ),
    Subsector(
        id="urology",
        name="Urology",
        grouping=G.PROVIDER_SERVICES,
        business_model="Office + surgical + ASC + pathology + radiation "
                       "(LDR/IMRT) + infusion.",
        kpis=(
            K("Surgical volume", "count"),
            K("In-office procedures", "count"),
            K("Advanced prostate-cancer drug/infusion", "count"),
            K("Pathology capture", "pct"),
        ),
        reimbursement_codes=("E/M 99202-99215", "prostate path 88305",
                             "IMRT 77385-77386"),
        reimbursement_mechanics="Professional + ancillary path/radiation/infusion; "
                                "buy-and-bill drug margin (340B-sensitive).",
        data_sources=("CMS Physician & Other Practitioners", "NPPES",
                      "Open Payments"),
        thesis="Aging male demographics, ancillary (UroGPO scale, Solaris).",
        risks="340B, drug reimbursement.",
        exhibits=("Ancillary penetration", "Prostate-cancer pathway economics"),
        vertical="MSO",
    ),
    Subsector(
        id="ent_allergy",
        name="ENT / Allergy",
        grouping=G.PROVIDER_SERVICES,
        business_model="Office + surgical (sinus, tubes) + audiology + allergy "
                       "immunotherapy.",
        kpis=(
            K("Surgical volume", "count"),
            K("Balloon sinuplasty", "count"),
            K("Audiology/hearing-aid attach", "pct"),
            K("Allergy shots", "count"),
        ),
        reimbursement_codes=("31231 nasal endoscopy", "69436 tubes",
                             "95115-95117 allergy immunotherapy"),
        reimbursement_mechanics="Professional + surgical fee; audiology/hearing "
                                "aid retail; allergy serum billing.",
        data_sources=("CMS Physician & Other Practitioners", "NPPES",
                      "MGMA benchmarks"),
        thesis="Aging, hearing-aid tailwind/risk, ancillary.",
        risks="Hearing-aid commoditization (OTC).",
        exhibits=("Audiology attach rate", "Surgical mix"),
        vertical="MSO",
    ),
    Subsector(
        id="dental_dso",
        name="Dental / DSOs",
        grouping=G.PROVIDER_SERVICES,
        business_model="MSO/DSO charges affiliated PCs a management fee "
                       "(typically 5-15% of collections); recurring hygiene + "
                       "private-pay mix + procurement scale.",
        kpis=(
            K("Same-store growth", "pct"),
            K("Hygiene reappointment rate", "pct", "~98% target, often <85%"),
            K("Case acceptance rate", "pct"),
            K("Production per operatory", "dollars"),
            K("Chair/operatory utilization", "pct"),
            K("New-patient flow", "count"),
            K("Overhead ratio", "pct", "50-40-30 rule: solo <=50%, group 40%, "
                                       "mature DSO 30% of collections"),
            K("AR aging", "days"),
            K("No-show rate", "pct"),
        ),
        reimbursement_codes=("ADA CDT codes",),
        reimbursement_mechanics="Private-pay + dental insurance; DSO management "
                                "fee on PC collections.",
        data_sources=("Target P&L/PMS", "NPPES", "MGMA/DSO benchmarks"),
        thesis="Fragmentation, private-pay stability, recession resistance; "
               ">50 PE-backed dental platforms; specialty DSOs (endo, perio, "
               "OMS, ortho, pedo).",
        risks="Billing-system fragmentation/bad debt on integration, associate "
              "dependence, MA dental benefit cuts (2027), CPOM.",
        exhibits=("Same-store waterfall", "Overhead bridge to 30%",
                  "Location density map", "Hygiene reactivation analysis",
                  "Integration billing-system risk"),
        nucc_verticals=("dental",),
        central=True,
        deep_dive="Same-store growth; overhead ratio toward 30%; hygiene "
                  "reappointment and case acceptance; associate/provider "
                  "dependence; billing-system integration risk and bad-debt; "
                  "payer mix (private-pay stability); MA dental cut exposure (2027).",
    ),
    Subsector(
        id="anesthesiology",
        name="Anesthesiology",
        grouping=G.PROVIDER_SERVICES,
        business_model="Hospital/ASC coverage; professional fees + stipends.",
        kpis=(
            K("ASA units per case", "ratio"),
            K("Sites covered", "count"),
            K("Subsidy/stipend reliance", "pct"),
            K("Payer mix", "pct"),
            K("OON exposure (NSA)", "pct"),
        ),
        reimbursement_codes=("ASA base units + time",),
        reimbursement_mechanics="ASA base units + time units x conversion "
                                "factor; hospital/ASC stipends close the gap.",
        data_sources=("CMS Physician & Other Practitioners", "NPPES"),
        thesis="Surgical volume growth, ASC coverage.",
        risks="No Surprises Act (OON balance-billing curtailed), CRNA labor "
              "cost, payer rate cuts.",
        exhibits=("OON exposure pre/post-NSA", "Subsidy dependency",
                  "Site coverage map"),
    ),
    Subsector(
        id="radiology_group",
        name="Radiology (groups)",
        grouping=G.PROVIDER_SERVICES,
        business_model="Teleradiology + imaging center + hospital contracts.",
        kpis=(
            K("Reads/RVU per radiologist", "ratio"),
            K("Modality mix (CT/MRI high value)", "pct"),
            K("Subspecialty mix", "pct"),
            K("Turnaround time", "minutes"),
            K("Contract concentration", "pct"),
        ),
        reimbursement_codes=("70000-series CPT (prof vs technical component)",),
        reimbursement_mechanics="Professional component on reads; technical "
                                "component if facility-owned.",
        data_sources=("CMS Physician & Other Practitioners", "NPPES"),
        thesis="AI-augmented read volume, teleradiology scale.",
        risks="Reimbursement cuts, AI disruption.",
        exhibits=("Read productivity", "Modality mix",
                  "Hospital contract concentration"),
    ),
    Subsector(
        id="primary_care",
        name="Primary Care",
        grouping=G.PROVIDER_SERVICES,
        business_model="FFS + increasingly capitated/VBC (see VBC enablers).",
        kpis=(
            K("Panel size", "count"),
            K("Visits per day", "count"),
            K("Attribution", "count"),
            K("RAF", "ratio"),
            K("PMPM", "dollars"),
        ),
        reimbursement_codes=("E/M 99202-99215", "G2211 complexity add-on"),
        reimbursement_mechanics="FFS office E/M transitioning to capitation/"
                                "PMPM under VBC.",
        data_sources=("CMS Physician & Other Practitioners", "NPPES",
                      "MA enrollment files"),
        thesis="VBC enablement.",
        risks="FFS margin compression.",
        exhibits=("FFS-to-VBC transition model",),
        nucc_verticals=("physician_primary_care",),
    ),
    Subsector(
        id="womens_health",
        name="Women's Health / OB-GYN",
        grouping=G.PROVIDER_SERVICES,
        business_model="Office + deliveries + ancillary (ultrasound, lab, "
                       "in-office procedures) + fertility adjacency.",
        kpis=(
            K("Deliveries per year", "count"),
            K("Well-woman visits", "count"),
            K("Ancillary capture", "pct"),
            K("Payer mix (Medicaid births)", "pct"),
        ),
        reimbursement_codes=("59400 global OB", "76805 OB ultrasound"),
        reimbursement_mechanics="Global OB package + FFS office/ancillary; "
                                "Medicaid-heavy delivery payer mix.",
        data_sources=("CMS Physician & Other Practitioners", "NPPES",
                      "T-MSIS (Medicaid)"),
        thesis="Fragmentation, ancillary.",
        risks="Malpractice cost, Medicaid OB rates.",
        exhibits=("Ancillary capture", "Payer-mix waterfall (Medicaid exposure)"),
    ),
    Subsector(
        id="fertility_ivf",
        name="Fertility / IVF",
        grouping=G.PROVIDER_SERVICES,
        business_model="Largely cash-pay + growing employer benefit coverage; "
                       "cycle-based.",
        kpis=(
            K("IVF cycles per year", "count"),
            K("Cycles per physician", "ratio"),
            K("Success rates (SART/CDC)", "pct"),
            K("Cash vs covered mix", "pct"),
            K("Conversion (consult to cycle)", "pct"),
        ),
        reimbursement_codes=("58970-58976 ART procedures", "89250-89342 lab"),
        reimbursement_mechanics="Cash-pay per cycle + employer benefit "
                                "(Progyny/Carrot) coverage.",
        data_sources=("CDC ART data", "SART", "NPPES"),
        thesis="Delayed childbearing, employer coverage expansion, fragmentation.",
        risks="Success-rate transparency, cyclical discretionary spend.",
        exhibits=("Cycle volume sizing", "Success-rate benchmarking (CDC ART)",
                  "Payer/employer coverage mix"),
    ),
    Subsector(
        id="pain_management",
        name="Pain Management",
        grouping=G.PROVIDER_SERVICES,
        business_model="Injections + procedures + ancillary (UDT labs, DME, PT).",
        kpis=(
            K("Procedures per MD", "count"),
            K("Injection mix", "pct"),
            K("UDT lab capture", "pct"),
            K("Opioid vs interventional mix", "pct"),
        ),
        reimbursement_codes=("64483-64484 ESI", "62321"),
        reimbursement_mechanics="Professional + facility for interventional; "
                                "UDT lab and DME ancillary.",
        data_sources=("CMS Physician & Other Practitioners", "NPPES"),
        thesis="Aging, interventional shift.",
        risks="Opioid/UDT compliance scrutiny, reimbursement.",
        exhibits=("Procedure mix", "Lab capture compliance flags"),
    ),
    Subsector(
        id="plastic_surgery",
        name="Plastic Surgery / Medical Aesthetics",
        grouping=G.PROVIDER_SERVICES,
        business_model="Cash-pay cosmetic + reconstructive.",
        kpis=(
            K("Revenue per provider", "dollars"),
            K("Injectable (Botox/filler) recurring revenue", "dollars"),
            K("Device utilization", "pct"),
            K("Consult conversion", "pct"),
        ),
        reimbursement_codes=("Cash-pay cosmetic", "reconstructive CPT (insured)"),
        reimbursement_mechanics="Mostly cash-pay cosmetic; reconstructive billed "
                                "to insurance.",
        data_sources=("Target P&L", "NPPES"),
        thesis="Cash-pay growth, recurring injectables.",
        risks="Discretionary/cyclical, med-spa competition.",
        exhibits=("Recurring vs one-time revenue", "Injectable cohort retention"),
    ),
    Subsector(
        id="veterinary",
        name="Veterinary",
        grouping=G.PROVIDER_SERVICES,
        business_model="Cash/pet-insurance; GP + specialty/ER hospitals.",
        kpis=(
            K("Revenue per DVM", "dollars"),
            K("Active patients", "count"),
            K("Visits per DVM", "ratio"),
            K("Ancillary (pharmacy, labs, imaging)", "pct"),
            K("Same-store growth", "pct"),
        ),
        reimbursement_codes=("Cash-pay / pet insurance (no CMS codes)",),
        reimbursement_mechanics="Cash-pay + pet insurance reimbursement; "
                                "pharmacy/lab/imaging ancillary.",
        data_sources=("Target P&L", "Industry density data"),
        thesis="Humanization of pets, fragmentation, recurring.",
        risks="DVM labor shortage, valuation reset.",
        exhibits=("Same-store growth", "DVM productivity", "Density map"),
    ),

    # ── GROUPING 2 — FACILITY-BASED CARE ──────────────────────────────────
    Subsector(
        id="asc",
        name="Ambulatory Surgery Centers (ASCs)",
        grouping=G.FACILITY_BASED,
        business_model="Facility fee (separate from professional fee) + "
                       "physician syndication ownership.",
        kpis=(
            K("Cases per year", "count"),
            K("Case-mix by CPT", ""),
            K("Revenue per case", "dollars"),
            K("Payer mix", "pct"),
            K("OON exposure", "pct"),
            K("Physician syndication ownership %", "pct"),
            K("EBITDA margin", "pct"),
            K("Site-of-service differential vs HOPD", "pct"),
            K("OR utilization", "pct"),
        ),
        reimbursement_codes=("ASC Fee Schedule (% of OPPS; ~56% of HOPD)",
                             "ASC Covered Procedures List"),
        reimbursement_mechanics="ASC FS as a % of OPPS (historically ~56% of "
                                "HOPD); CY2025 base ~$54.895; ASCQR "
                                "non-compliance = 2% payment reduction.",
        data_sources=("HCRIS", "POS file", "ASCQR (data.cms.gov)",
                      "CMS OPPS/ASC rule", "ASC-12 measure"),
        thesis="Surgical migration from HOPD, ASC CPL expansion (spine, cardio, "
               "total joints); MedPAC counts 6,394 Medicare-certified ASCs in "
               "2024; market ~$45-50B, ~95% for-profit.",
        risks="Low rural penetration, payer rate pressure, physician recruitment.",
        exhibits=("Case volume by CPT", "Site-of-service differential ($/case)",
                  "Syndication ownership map", "ASC-eligible migration sizing",
                  "OR utilization"),
        nucc_verticals=("asc",),
        vertical="ASC",
        central=True,
        deep_dive="Case volume by CPT and case-mix migration potential; OON "
                  "exposure (NSA risk); physician syndication ownership and "
                  "alignment; site-of-service differential capture; ASC CPL "
                  "expansion upside.",
    ),
    Subsector(
        id="hospitals",
        name="Hospitals / Health Systems",
        grouping=G.FACILITY_BASED,
        business_model="DRG inpatient (IPPS) + OPPS outpatient + DSH/340B.",
        kpis=(
            K("Occupancy", "pct"),
            K("ALOS", "days"),
            K("Case-mix index (CMI)", "ratio"),
            K("Payer mix", "pct"),
            K("Operating margin", "pct"),
            K("Cost per adjusted discharge", "dollars"),
            K("HHI/market share", "ratio"),
        ),
        reimbursement_codes=("MS-DRG (IPPS)", "APC (OPPS)"),
        reimbursement_mechanics="DRG per-discharge inpatient + OPPS outpatient; "
                                "DSH/340B supplements.",
        data_sources=("HCRIS", "RAND Hospital Data", "AHA survey", "Care Compare",
                      "Price transparency MRFs"),
        thesis="Scale, outpatient shift.",
        risks="Labor cost, site-neutral, antitrust (per KFF, 1-2 systems "
              "controlled the entire inpatient market in ~half of MSAs in 2024).",
        exhibits=("HHI/antitrust screen", "Service-line contribution",
                  "Payer-rate vs Medicare (price transparency)"),
        vertical="HOSPITAL",
    ),
    Subsector(
        id="inpatient_psych",
        name="Inpatient Psych / Residential (Behavioral Health)",
        grouping=G.FACILITY_BASED,
        business_model="Per-diem / DRG inpatient psychiatric / residential.",
        kpis=(
            K("Occupancy", "pct"),
            K("ALOS", "days"),
            K("Per-diem rate", "dollars"),
            K("Payer mix", "pct"),
        ),
        reimbursement_codes=("IPF PPS per-diem",),
        reimbursement_mechanics="Per-diem / DRG; platform 9-15x EBITDA "
                                "depending on subsegment/scale.",
        data_sources=("HCRIS", "Care Compare", "T-MSIS (Medicaid)"),
        thesis="Unmet behavioral demand, parity enforcement.",
        risks="Occupancy, labor, payer rate.",
        exhibits=("Occupancy/ALOS trend", "Payer-mix waterfall"),
        nucc_verticals=("behavioral",),
        vertical="BEHAVIORAL_HEALTH",
    ),
    Subsector(
        id="sud_treatment",
        name="SUD / Addiction Treatment (Behavioral Health)",
        grouping=G.FACILITY_BASED,
        business_model="Per-diem + UDT lab; OON vs in-network economics.",
        kpis=(
            K("Census", "count"),
            K("Length of stay", "days"),
            K("OON vs in-network", "pct",
              "OON SUD bolt-ons 4-6x; in-network >6x"),
            K("Referral source", ""),
            K("Readmission", "pct"),
        ),
        reimbursement_codes=("H0010-H0020 SUD", "UDT 80305-80377"),
        reimbursement_mechanics="Per-diem + UDT lab billing; OON balance-billing "
                                "historically inflated economics.",
        data_sources=("T-MSIS", "Care Compare", "State Medicaid rate schedules"),
        thesis="Unmet demand, parity.",
        risks="OON reimbursement crackdown, patient-brokering compliance.",
        exhibits=("Census/LOS trend", "OON vs in-network mix",
                  "Referral-source concentration"),
        nucc_verticals=("behavioral",),
        vertical="BEHAVIORAL_HEALTH",
        central=True,
        deep_dive="Payer-rate-by-state, clinician productivity/utilization and "
                  "retention, OON vs in-network (SUD), authorization "
                  "utilization, billing-intensity/fraud audit risk, accreditation.",
    ),
    Subsector(
        id="aba_therapy",
        name="Autism / ABA Therapy (Behavioral Health)",
        grouping=G.FACILITY_BASED,
        business_model="Hourly behavioral codes, heavily Medicaid + commercial "
                       "mandate.",
        kpis=(
            K("Billable hours per clinician (BCBA/RBT)", "ratio"),
            K("Authorization utilization", "pct"),
            K("Payer rates by state", "dollars"),
            K("Clinician retention", "pct"),
            K("Waitlist", "count"),
        ),
        reimbursement_codes=("97151-97158 adaptive behavior",),
        reimbursement_mechanics="Hourly behavioral codes; Medicaid + commercial "
                                "mandate; valuations ~6-8x.",
        data_sources=("T-MSIS", "State Medicaid rate schedules", "NPPES"),
        thesis="Unmet demand, mandates; Medicaid ABA spend surged from $660M "
               "(2019) to $2.2B (2023).",
        risks="State Medicaid rate cuts (NE, IN), outcomes scrutiny, "
              "billing-intensity/fraud audits.",
        exhibits=("Payer-rate-by-state heatmap",
                  "Clinician productivity/utilization", "Authorization-trend",
                  "Geographic rate arbitrage"),
        nucc_verticals=("behavioral",),
        vertical="BEHAVIORAL_HEALTH",
        central=True,
        deep_dive="Payer-rate-by-state (ABA Medicaid volatility), clinician "
                  "productivity/utilization and retention, authorization "
                  "utilization, billing-intensity/fraud audit risk, accreditation.",
    ),
    Subsector(
        id="idd_services",
        name="IDD Services (Behavioral Health)",
        grouping=G.FACILITY_BASED,
        business_model="Medicaid waiver (1915(c)/(i)) services.",
        kpis=(
            K("DCW retention", "pct"),
            K("Waiver rate adequacy", ""),
            K("Multi-state diversification", ""),
            K("Occupancy", "pct"),
        ),
        reimbursement_codes=("1915(c)/(i) waiver service codes",),
        reimbursement_mechanics="Medicaid HCBS waiver per-service / per-diem rates.",
        data_sources=("T-MSIS", "State Medicaid waiver schedules"),
        thesis="Unmet demand, deinstitutionalization.",
        risks="DCW retention, waiver rate adequacy.",
        exhibits=("DCW retention trend", "Waiver rate adequacy by state"),
        nucc_verticals=("behavioral",),
        vertical="BEHAVIORAL_HEALTH",
    ),
    Subsector(
        id="snf",
        name="Skilled Nursing (SNF)",
        grouping=G.FACILITY_BASED,
        business_model="PDPM per-diem (case-mix) post-acute.",
        kpis=(
            K("Occupancy", "pct"),
            K("Skilled mix %", "pct"),
            K("Medicare/MA mix", "pct"),
            K("ALOS", "days"),
            K("PDPM case-mix", "ratio"),
            K("Agency labor %", "pct"),
            K("Star rating", "ratio"),
        ),
        reimbursement_codes=("PDPM per-diem (case-mix)",),
        reimbursement_mechanics="PDPM case-mix-adjusted per-diem.",
        data_sources=("HCRIS SNF cost reports", "Care Compare (5-star)",
                      "PBJ staffing", "MDS"),
        thesis="Aging demand.",
        risks="Labor/agency cost, MA rate pressure, staffing mandates.",
        exhibits=("PDPM case-mix bridge", "Skilled-mix trend",
                  "Star-rating impact", "Agency-labor exposure"),
        nucc_verticals=("snf",),
    ),
    Subsector(
        id="home_health",
        name="Home Health",
        grouping=G.FACILITY_BASED,
        business_model="PDGM 30-day episodes (432 case-mix groups).",
        kpis=(
            K("Recertification rate", "pct"),
            K("Visits per episode", "ratio"),
            K("LUPA rate", "pct"),
            K("Case-mix weight", "ratio"),
            K("Admission source mix", "pct", "institutional pays more"),
            K("Referral trends", ""),
            K("Star ratings", "ratio"),
            K("Revenue per episode", "dollars"),
        ),
        reimbursement_codes=("PDGM 30-day episode (admission source, timing, "
                             "clinical group, functional level, comorbidity)",),
        reimbursement_mechanics="PDGM 30-day episode payment across 432 case-mix "
                                "groups; LUPA threshold below visit floor.",
        data_sources=("HCRIS HHA", "OASIS", "Home Health Care Compare", "HHVBP"),
        thesis="Aging-in-place, hospital-at-home.",
        risks="PDGM rate cuts, LUPA exposure, CMS enrollment freeze.",
        exhibits=("PDGM case-mix bridge", "LUPA analysis", "Recert-rate trend",
                  "Star-rating impact on referrals"),
        nucc_verticals=("home_health",),
        central=True,
        deep_dive="PDGM case-mix and admission-source mix, LUPA exposure, "
                  "recertification rate, star ratings (referral driver), "
                  "referral-source concentration.",
    ),
    Subsector(
        id="hospice",
        name="Hospice",
        grouping=G.FACILITY_BASED,
        business_model="Per-diem (4 levels: routine, continuous, inpatient, "
                       "respite); cap-limited.",
        kpis=(
            K("Average daily census (ADC)", "count"),
            K("Length of stay", "days"),
            K("Live discharge rate", "pct"),
            K("Cap exposure (aggregate cap)", "dollars"),
            K("Diagnosis mix", ""),
            K("Referral source", ""),
        ),
        reimbursement_codes=("Hospice per-diem (4 levels)", "aggregate cap"),
        reimbursement_mechanics="Per-diem across 4 levels; aggregate annual cap "
                                "with recoupment.",
        data_sources=("HCRIS Hospice", "Care Compare", "DocGraph referral data"),
        thesis="Aging demand.",
        risks="Cap recoupment, live-discharge/eligibility audits, MA carve-in "
              "pilot.",
        exhibits=("ADC trend", "LOS distribution", "Cap-utilization analysis"),
        nucc_verticals=("hospice",),
        central=True,
        deep_dive="Hospice cap exposure and live-discharge rate, ADC/LOS trend, "
                  "referral-source concentration.",
    ),
    Subsector(
        id="irf_ltch",
        name="IRF / LTACH",
        grouping=G.FACILITY_BASED,
        business_model="Per-discharge (CMG / MS-LTC-DRG).",
        kpis=(
            K("Compliance with 60% rule (IRF)", "pct"),
            K("CMI", "ratio"),
            K("ALOS", "days"),
            K("Occupancy", "pct"),
        ),
        reimbursement_codes=("IRF CMG", "LTCH MS-LTC-DRG"),
        reimbursement_mechanics="Per-discharge case-mix payment; IRF 60%-rule "
                                "compliance gates the PPS.",
        data_sources=("HCRIS", "Care Compare"),
        thesis="Post-acute demand.",
        risks="60%-rule compliance, site-neutral payment.",
        exhibits=("60%-rule compliance", "CMI/ALOS trend"),
    ),
    Subsector(
        id="urgent_care",
        name="Urgent Care",
        grouping=G.FACILITY_BASED,
        business_model="Episodic FFS + occupational health/employer + ancillary "
                       "(X-ray, labs).",
        kpis=(
            K("Visits per day", "count", "breakeven ~25-32/day; ~32 pre-COVID avg"),
            K("Average revenue per visit", "dollars", "$123 historic; "
                                                       "$250-450 typical range"),
            K("Provider utilization", "pct", "flag <60%"),
            K("Payer mix", "pct"),
            K("E/M level distribution", ""),
            K("Ancillary capture", "pct", "15-25% often uncaptured"),
            K("First-pass resolution", "pct"),
            K("Days in AR", "days", "<45"),
        ),
        reimbursement_codes=("E/M 99202-99215", "S9088 urgent-care facility"),
        reimbursement_mechanics="Episodic FFS + occ-health/employer contracts; "
                                "valuation 3-7x single, 6-11x regional, "
                                "10-15x+ scaled.",
        data_sources=("POS file", "Definitive", "UCA benchmarking"),
        thesis="Convenience, occ-health diversification.",
        risks="Visit cyclicality, OON/narrow networks, labor.",
        exhibits=("Visits/day cohort", "ARPV by payer", "De novo ramp",
                  "Density/cannibalization map"),
        nucc_verticals=("urgent_care",),
    ),
    Subsector(
        id="dialysis",
        name="Dialysis / Nephrology",
        grouping=G.FACILITY_BASED,
        business_model="Bundled ESRD PPS per-treatment + commercial "
                       "pass-through; physician JV model.",
        kpis=(
            K("Treatments per station per week", "ratio"),
            K("Station count", "count"),
            K("Patient census", "count"),
            K("Commercial vs Medicare mix", "pct",
              "Medicare ~75% of patients but commercial drives profit"),
            K("Mortality/hospitalization", "pct"),
            K("JV ownership", "pct"),
        ),
        reimbursement_codes=("90960-90962 MCP", "bundled ESRD PPS"),
        reimbursement_mechanics="Bundled ESRD PPS per-treatment + commercial "
                                "pass-through margin.",
        data_sources=("HCRIS", "Care Compare (Dialysis)", "POS file"),
        thesis="ESRD prevalence (diabetes/HTN), VBC kidney care (CKCC); DaVita+"
               "Fresenius share rose 59.1% to 77.1% (2005-2019).",
        risks="Commercial-rate caps (CA/OR legislation), MA penetration, "
              "transplant/home-dialysis shift.",
        exhibits=("Treatments/station utilization",
                  "Commercial-mix margin sensitivity", "JV ownership map"),
        nucc_verticals=("dialysis",),
    ),
    Subsector(
        id="infusion_centers",
        name="Infusion Centers",
        grouping=G.FACILITY_BASED,
        business_model="Buy-and-bill drug margin + nursing/chair fee; ASP+6% "
                       "(or commercial).",
        kpis=(
            K("Chairs", "count"),
            K("Chair utilization", "pct"),
            K("Drug mix/margin", "pct"),
            K("Payer mix", "pct"),
            K("Referral source", ""),
        ),
        reimbursement_codes=("96365-96379 infusion administration",
                             "J-code drugs (ASP+6%)"),
        reimbursement_mechanics="Buy-and-bill drug margin (ASP+6% or commercial) "
                                "+ nursing/chair administration fee.",
        data_sources=("NPPES (infusion taxonomies)", "DocGraph referral data"),
        thesis="Site-of-care shift from HOPD (cost savings), biologics pipeline.",
        risks="Drug reimbursement (ASP, 340B), white bagging.",
        exhibits=("Chair utilization", "Drug-margin bridge",
                  "Site-of-care savings"),
        nucc_verticals=("infusion",),
    ),
    Subsector(
        id="imaging_centers",
        name="Imaging / Radiology Centers",
        grouping=G.FACILITY_BASED,
        business_model="Technical fee (+ professional).",
        kpis=(
            K("Scans per day by modality", "count"),
            K("Modality mix (MRI/CT high value)", "pct"),
            K("Equipment utilization", "pct"),
            K("Payer mix", "pct"),
            K("Referral concentration", "pct"),
        ),
        reimbursement_codes=("70000-series CPT (technical component)",),
        reimbursement_mechanics="Technical component (+ professional if "
                                "in-housed); outpatient site-of-service.",
        data_sources=("POS file", "CMS Physician & Other Practitioners",
                      "DocGraph referral data"),
        thesis="Outpatient migration, fragmentation.",
        risks="Reimbursement cuts, CON.",
        exhibits=("Modality utilization", "Referral inflow map", "De novo siting"),
    ),
    Subsector(
        id="freestanding_er",
        name="Freestanding ERs",
        grouping=G.FACILITY_BASED,
        business_model="High facility fee.",
        kpis=(
            K("Visits per day", "count"),
            K("Acuity / E/M level", ""),
            K("Payer mix", "pct"),
            K("OON exposure", "pct"),
        ),
        reimbursement_codes=("99281-99285 ED E/M", "facility fee"),
        reimbursement_mechanics="High facility fee per visit; OON-sensitive.",
        data_sources=("POS file", "Definitive"),
        thesis="Convenience.",
        risks="No Surprises Act, payer/regulatory backlash, sustainability.",
        exhibits=("Visits/day", "Acuity mix", "OON exposure"),
    ),

    # ── GROUPING 3 — HEALTHCARE IT / TECH-ENABLED SERVICES ────────────────
    Subsector(
        id="rcm",
        name="Revenue Cycle Management (RCM)",
        grouping=G.HEALTHCARE_IT,
        business_model="% of collections or per-transaction or SaaS.",
        kpis=(
            K("Net collection rate", "pct"),
            K("Clean-claim / first-pass rate", "pct"),
            K("Denial rate", "pct"),
            K("Days in AR", "days"),
            K("Client retention", "pct"),
            K("Revenue per FTE", "dollars"),
            K("Automation rate", "pct"),
            K("Net Revenue Retention (NRR)", "pct", "best-in-class 120-130%"),
            K("Rule of 40/60", ""),
        ),
        reimbursement_codes=("N/A (services/SaaS)",),
        reimbursement_mechanics="% of collections, per-transaction, or SaaS "
                                "subscription.",
        data_sources=("Target billing/CRM",),
        thesis="Billing complexity, AI automation (Rule of 60 assets like AGS "
               "Health, Smarter Technologies).",
        risks="AI-native disruption, client concentration.",
        exhibits=("Client cohort retention", "NRR", "Automation/margin bridge",
                  "ARR bridge"),
        central=True,
        deep_dive="NRR/GRR and cohort durability, Rule of 40/60, gross margin "
                  "and automation trajectory, client concentration, services vs "
                  "recurring mix, AI-disruption exposure.",
    ),
    Subsector(
        id="ehr_pm",
        name="EHR / Practice-Management Software",
        grouping=G.HEALTHCARE_IT,
        business_model="SaaS / per-provider.",
        kpis=(
            K("NRR", "pct"),
            K("Logo retention", "pct"),
            K("ARPU", "dollars"),
            K("Specialty penetration", "pct"),
        ),
        reimbursement_codes=("N/A (SaaS)",),
        reimbursement_mechanics="Per-provider SaaS subscription.",
        data_sources=("Target billing/CRM",),
        thesis="Specialty-specific EHR, AI documentation (e.g. ModMed deal).",
        risks="Incumbent switching costs, AI disruption.",
        exhibits=("ARR bridge", "Logo vs revenue retention",
                  "Specialty penetration"),
    ),
    Subsector(
        id="healthcare_payments",
        name="Healthcare Payments",
        grouping=G.HEALTHCARE_IT,
        business_model="Per-transaction / take-rate.",
        kpis=(
            K("Payment volume", "dollars"),
            K("Take rate", "pct"),
            K("Attach to EHR/RCM", "pct"),
        ),
        reimbursement_codes=("N/A (payments)",),
        reimbursement_mechanics="Take-rate on payment volume; attach to EHR/RCM.",
        data_sources=("Target billing/CRM",),
        thesis="Patient financial responsibility growth, digital payments.",
        risks="Interchange, disintermediation.",
        exhibits=("Volume x take-rate bridge", "Attach-rate cohort"),
    ),
    Subsector(
        id="clinical_decision_support",
        name="Clinical Decision Support / Population Health / Care Coordination",
        grouping=G.HEALTHCARE_IT,
        business_model="SaaS / PMPM.",
        kpis=(
            K("Covered lives", "count"),
            K("PMPM", "dollars"),
            K("Engagement", "pct"),
            K("Outcomes", ""),
        ),
        reimbursement_codes=("N/A (SaaS/PMPM)",),
        reimbursement_mechanics="SaaS or PMPM on covered lives.",
        data_sources=("Target billing/CRM",),
        thesis="VBC enablement, care-gap closure.",
        risks="Outcomes proof, procurement cycles.",
        exhibits=("Covered-lives cohort", "PMPM economics", "Engagement funnel"),
    ),
    Subsector(
        id="telehealth",
        name="Telehealth / Virtual Care",
        grouping=G.HEALTHCARE_IT,
        business_model="Visit fee or PMPM / subscription.",
        kpis=(
            K("Visits", "count"),
            K("Utilization", "pct"),
            K("Provider supply", "count"),
            K("Retention", "pct"),
            K("Take rate", "pct"),
        ),
        reimbursement_codes=("E/M telehealth modifiers (95/GT)",),
        reimbursement_mechanics="Visit FFS or PMPM/subscription; "
                                "telehealth-flexibility-dependent.",
        data_sources=("Target billing/CRM",),
        thesis="Access, convenience, hybrid care.",
        risks="Reimbursement-flexibility expiry, utilization normalization.",
        exhibits=("Visit volume", "Utilization cohort", "Retention curve"),
    ),
    Subsector(
        id="rpm",
        name="Remote Patient Monitoring (RPM)",
        grouping=G.HEALTHCARE_IT,
        business_model="Device + monitoring fee.",
        kpis=(
            K("Enrolled patients", "count"),
            K("Adherence", "pct", "16-day threshold"),
            K("Reimbursement per patient", "dollars"),
        ),
        reimbursement_codes=("99453-99458 RPM",),
        reimbursement_mechanics="Device setup + monthly monitoring CPT; 16-day "
                                "adherence threshold gates billing.",
        data_sources=("Target billing/CRM", "CMS Physician & Other Practitioners"),
        thesis="Chronic-care management, aging-in-place.",
        risks="Reimbursement scrutiny, adherence drop-off.",
        exhibits=("Enrollment cohort", "Adherence funnel",
                  "Reimbursement-per-patient"),
    ),
    Subsector(
        id="ai_clinical_documentation",
        name="AI / Clinical Documentation (Ambient Scribe)",
        grouping=G.HEALTHCARE_IT,
        business_model="Per-provider SaaS.",
        kpis=(
            K("Provider adoption", "pct"),
            K("Note-time reduction", "pct"),
            K("Retention", "pct"),
        ),
        reimbursement_codes=("N/A (SaaS)",),
        reimbursement_mechanics="Per-provider SaaS subscription.",
        data_sources=("Target billing/CRM",),
        thesis="Clinician burnout, generative AI (value driver and disruption "
               "risk per Bain).",
        risks="Commoditization, accuracy/liability, incumbent bundling.",
        exhibits=("Adoption cohort", "Note-time-reduction proof",
                  "Retention curve"),
    ),
    Subsector(
        id="healthcare_data_analytics",
        name="Healthcare Data / Analytics",
        grouping=G.HEALTHCARE_IT,
        business_model="Subscription / data license.",
        kpis=(
            K("Data assets", ""),
            K("Recurring %", "pct"),
            K("NRR", "pct"),
        ),
        reimbursement_codes=("N/A (data license)",),
        reimbursement_mechanics="Subscription / data-license recurring revenue.",
        data_sources=("Target billing/CRM",),
        thesis="Data network effects, all-payer claims demand.",
        risks="Data-rights durability, privacy regulation.",
        exhibits=("Recurring-mix", "NRR", "Data-asset moat"),
    ),
    Subsector(
        id="patient_engagement",
        name="Patient Engagement / Credentialing / Prior Authorization",
        grouping=G.HEALTHCARE_IT,
        business_model="SaaS / per-transaction.",
        kpis=(
            K("NRR", "pct"),
            K("Transactions", "count"),
            K("Automation rate", "pct"),
        ),
        reimbursement_codes=("N/A (SaaS/per-transaction)",),
        reimbursement_mechanics="SaaS or per-transaction; prior-auth automation "
                                "a key 2025-26 theme.",
        data_sources=("Target billing/CRM",),
        thesis="Prior-auth automation (payers committed to cuts), credentialing "
               "complexity.",
        risks="Payer-rule change, point-solution fatigue.",
        exhibits=("ARR bridge", "Automation rate", "Transaction-volume cohort"),
    ),

    # ── GROUPING 4 — PAYER / RISK-BEARING ─────────────────────────────────
    Subsector(
        id="medicare_advantage",
        name="Medicare Advantage Plans",
        grouping=G.PAYER_RISK,
        business_model="Capitated PMPM from CMS via bid-to-benchmark.",
        kpis=(
            K("MLR", "pct", "federal minimum 85%"),
            K("Admin loss ratio", "pct"),
            K("PMPM", "dollars"),
            K("RAF / risk score trends", "ratio"),
            K("Member growth", "pct"),
            K("Disenrollment/churn", "pct"),
            K("Star rating", "ratio"),
            K("Days in AR", "days"),
        ),
        reimbursement_codes=("County benchmarks (115/107.5/100/95% of FFS)",
                             "QBP 5% bonus at 4+ stars",
                             "rebate 50/65/70% by star tier"),
        reimbursement_mechanics="Bid-to-benchmark: rebate = star-tied % of "
                                "(benchmark - bid); QBP 5% (10% double-bonus) at "
                                "4+ stars; federal min MLR 85%.",
        data_sources=("MA enrollment files", "MA encounter data (EDPS)",
                      "Star ratings"),
        thesis="Aging, MA penetration.",
        risks="V28 RAF recalibration (lowers scores/revenue), star-rating "
              "declines (~62% of membership in 4+ star plans in 2025 vs ~79% "
              "prior year), rate/audit pressure.",
        exhibits=("Bid-benchmark-rebate waterfall", "Star-rating revenue bridge",
                  "MLR trend", "RAF/V28 impact model"),
    ),
    Subsector(
        id="medicaid_mco",
        name="Managed Care / Medicaid MCOs",
        grouping=G.PAYER_RISK,
        business_model="Capitated managed care.",
        kpis=(
            K("MLR", "pct"),
            K("PMPM", "dollars"),
            K("Membership", "count"),
            K("State contract concentration", "pct"),
        ),
        reimbursement_codes=("State capitation rates",),
        reimbursement_mechanics="State-set capitation PMPM; actuarially sound "
                                "rate cells.",
        data_sources=("T-MSIS",),
        thesis="Medicaid managed-care penetration.",
        risks="State rate adequacy, redeterminations, contract concentration.",
        exhibits=("MLR trend", "Membership by state",
                  "Contract concentration"),
    ),
    Subsector(
        id="vbc_enablers",
        name="Value-Based Care Enablers / Risk-Bearing Primary Care / MSOs",
        grouping=G.PAYER_RISK,
        business_model="Capitation / shared savings; senior-focused "
                       "(e.g. P3, CenterWell model).",
        kpis=(
            K("Attributed lives", "count"),
            K("PMPM", "dollars"),
            K("Medical margin", "dollars", "capitation - medical cost"),
            K("MLR", "pct"),
            K("RAF / coding accuracy", "ratio"),
            K("Shared savings", "dollars"),
            K("Star/HEDIS", ""),
            K("Total cost of care vs benchmark", "pct"),
            K("Panel growth", "pct"),
            K("Clinic density", ""),
        ),
        reimbursement_codes=("Capitation PMPM", "shared-savings benchmark"),
        reimbursement_mechanics="Capitation / shared savings; medical margin = "
                                "capitation minus medical cost.",
        data_sources=("Target capitation/claims", "CMS-HCC V28 model",
                      "MA enrollment files"),
        thesis="VBC tailwind, payer/distributor exits.",
        risks="V28, MLR management, downside risk, attribution.",
        exhibits=("Medical-margin bridge", "RAF trend", "PMPM cohort economics",
                  "MLR by market", "Attribution waterfall"),
        central=True,
        deep_dive="Medical margin and MLR by market, PMPM unit economics, RAF "
                  "trend and V28 exposure, attribution accuracy, panel growth, "
                  "clinic density (fixed-cost leverage), downside-risk corridors.",
    ),
    Subsector(
        id="acos",
        name="ACOs",
        grouping=G.PAYER_RISK,
        business_model="MSSP shared savings.",
        kpis=(
            K("Attributed beneficiaries", "count"),
            K("Benchmark vs spend", "dollars"),
            K("Quality score", ""),
            K("Savings rate", "pct"),
        ),
        reimbursement_codes=("MSSP benchmark / shared-savings",),
        reimbursement_mechanics="MSSP benchmark vs spend; one- or two-sided risk "
                                "(67% of 2023 ACOs in two-sided models).",
        data_sources=("CMS MSSP data", "Target claims"),
        thesis="MSSP record $2.1B net savings in 2023.",
        risks="Benchmark ratchet, downside-risk exposure.",
        exhibits=("Benchmark vs spend", "Quality score", "Savings-rate trend"),
    ),
    Subsector(
        id="tpa",
        name="TPAs",
        grouping=G.PAYER_RISK,
        business_model="Admin fee per-employee-per-month (PEPM).",
        kpis=(
            K("Lives administered", "count"),
            K("PEPM", "dollars"),
            K("Retention", "pct"),
        ),
        reimbursement_codes=("PEPM admin fee",),
        reimbursement_mechanics="PEPM administrative fee on self-insured lives.",
        data_sources=("Target billing/CRM",),
        thesis="Self-insured employer growth, ERISA transparency.",
        risks="Fee compression, fiduciary-disclosure regulation.",
        exhibits=("Lives x PEPM bridge", "Retention cohort"),
    ),
    Subsector(
        id="pbm",
        name="PBMs",
        grouping=G.PAYER_RISK,
        business_model="Spread pricing + rebate retention + admin/dispensing "
                       "fees + owned mail/specialty pharmacy margin.",
        kpis=(
            K("Generic dispensing rate", "pct"),
            K("Rebate retention %", "pct"),
            K("Script volume", "count"),
            K("Mail-order/specialty penetration", "pct"),
            K("PMPM admin fee", "dollars"),
            K("AWP discount guarantees", "pct"),
        ),
        reimbursement_codes=("AWP-based pricing", "rebate / admin fee"),
        reimbursement_mechanics="Spread pricing + rebate retention + admin/"
                                "dispensing fees + owned pharmacy margin; top-3 "
                                "manage 79% of claims.",
        data_sources=("Target billing/CRM", "Part D Prescriber PUF"),
        thesis="Scale, specialty.",
        risks="CAA 2026 (delinks Part D comp from list price, 100% rebate "
              "pass-through to ERISA plans, spread-pricing ban in Part D from "
              "2028, any-willing-pharmacy by 2029), FTC settlements, DOL ERISA "
              "rule, state patchwork (>1,250 bills in 2025).",
        exhibits=("Revenue-stream decomposition", "Rebate-retention model",
                  "Regulatory-scenario impact"),
    ),
    Subsector(
        id="dental_vision_benefits",
        name="Dental / Vision Benefits",
        grouping=G.PAYER_RISK,
        business_model="Premium / PEPM.",
        kpis=(
            K("Membership", "count"),
            K("Loss ratio", "pct"),
            K("Retention", "pct"),
        ),
        reimbursement_codes=("Premium / PEPM",),
        reimbursement_mechanics="Premium or PEPM with a managed loss ratio.",
        data_sources=("Target billing/CRM",),
        thesis="Voluntary-benefit attach, MA supplemental.",
        risks="MA dental benefit cuts, loss-ratio pressure.",
        exhibits=("Membership trend", "Loss-ratio", "Retention cohort"),
    ),

    # ── GROUPING 5 — PHARMA SERVICES / LIFE SCIENCES TOOLS ────────────────
    Subsector(
        id="cro",
        name="CROs",
        grouping=G.PHARMA_SERVICES,
        business_model="Fee-for-service / milestone on clinical trials.",
        kpis=(
            K("Backlog", "dollars"),
            K("Book-to-bill", "ratio", "net >1.0 growing; premium >1.2x"),
            K("Backlog burn/conversion rate", "pct"),
            K("Cancellation rate", "pct", "4-6% of quarterly backlog"),
            K("Backlog quality (concentration, contingent trials)", ""),
            K("Gross margin", "pct", "35-45%"),
            K("Pass-through revenue", "dollars", "inflates revenue multiple"),
        ),
        reimbursement_codes=("N/A (FFS/milestone)",),
        reimbursement_mechanics="FFS / milestone on trial execution; "
                                "pass-through revenue inflates the multiple.",
        data_sources=("Target backlog", "ClinicalTrials.gov v2"),
        thesis="Biopharma R&D outsourcing (>70% of new products use contract "
               "mfg); IQVIA FY2025 R&D ~$8.9B, backlog $32.7B.",
        risks="Biotech funding, cancellations, BIOSECURE Act reshoring.",
        exhibits=("Backlog rollforward", "Book-to-bill trend",
                  "Customer concentration", "Therapeutic-mix vs strategy"),
    ),
    Subsector(
        id="cdmo",
        name="CDMOs",
        grouping=G.PHARMA_SERVICES,
        business_model="Development + GMP manufacturing.",
        kpis=(
            K("Capacity utilization", "pct", "key margin driver"),
            K("Modality mix", ""),
            K("Commercial vs clinical program mix", "pct"),
            K("Top-program concentration", "pct",
              "Phase III failure = 15-25% revenue loss"),
            K("Regulatory record (FDA warning letters)", ""),
            K("On-time / batch success rate", "pct"),
        ),
        reimbursement_codes=("N/A (manufacturing contracts)",),
        reimbursement_mechanics="Development fees + GMP manufacturing; capacity "
                                "utilization is the key margin driver.",
        data_sources=("Target program data", "FDA inspection records"),
        thesis="Biologics/ADC/gene therapy, BIOSECURE reshoring premium; market "
               "$331B (2025) -> $528B (2030, ~9.8% CAGR).",
        risks="Program concentration, capex intensity, capacity gluts.",
        exhibits=("Capacity utilization",
                  "Program-by-program clinical-status risk", "Modality mix"),
    ),
    Subsector(
        id="specialty_pharmacy",
        name="Specialty Pharmacy / Pharmacy Services",
        grouping=G.PHARMA_SERVICES,
        business_model="Dispensing margin + fees + 340B.",
        kpis=(
            K("Script volume", "count"),
            K("Specialty mix", "pct"),
            K("Payer/PBM contracts", ""),
            K("Adherence", "pct"),
            K("Limited-distribution-drug access", ""),
        ),
        reimbursement_codes=("NDC dispensing + DIR fees", "340B"),
        reimbursement_mechanics="Dispensing margin + service fees + 340B; "
                                "DIR-fee and PBM-steering sensitive.",
        data_sources=("Target billing/CRM", "Part D Prescriber PUF"),
        thesis="Precision/specialty drug volume, limited-distribution access.",
        risks="DIR fees, reimbursement, PBM steering.",
        exhibits=("Script-volume sizing", "Specialty-mix", "Adherence cohort"),
    ),
    Subsector(
        id="clinical_trial_sites",
        name="Clinical Trial Sites / SMOs",
        grouping=G.PHARMA_SERVICES,
        business_model="Per-patient / per-visit + startup fees.",
        kpis=(
            K("Active trials", "count"),
            K("Patient enrollment/retention", "pct"),
            K("Sponsor concentration", "pct"),
            K("Site utilization", "pct"),
        ),
        reimbursement_codes=("Per-patient / per-visit + startup fees",),
        reimbursement_mechanics="Per-patient / per-visit + startup fees from "
                                "sponsors/CROs.",
        data_sources=("ClinicalTrials.gov v2", "Target trial roster"),
        thesis="Site consolidation (Headlands, CenExel).",
        risks="Sponsor concentration, enrollment risk.",
        exhibits=("Trial backlog", "Enrollment funnel", "Sponsor concentration"),
    ),
    Subsector(
        id="pharmacovigilance",
        name="Pharmacovigilance / Regulatory / Commercialization / Med Comms",
        grouping=G.PHARMA_SERVICES,
        business_model="Project / retainer fees.",
        kpis=(
            K("Revenue retention", "pct"),
            K("Client concentration", "pct"),
            K("Headcount utilization", "pct"),
        ),
        reimbursement_codes=("N/A (project/retainer)",),
        reimbursement_mechanics="Project or retainer fees; people-utilization "
                                "driven.",
        data_sources=("Target billing/CRM",),
        thesis="Outsourced regulatory/safety/commercialization demand.",
        risks="Client concentration, utilization swings.",
        exhibits=("Revenue retention", "Client concentration",
                  "Utilization trend"),
    ),
    Subsector(
        id="lab_diagnostics",
        name="Lab Services / Diagnostics / Pathology / Genetic Testing",
        grouping=G.PHARMA_SERVICES,
        business_model="Per-test reimbursement.",
        kpis=(
            K("Test volume", "count"),
            K("Revenue per test", "dollars"),
            K("Payer mix", "pct"),
            K("Reimbursement (CLFS/PFS, PAMA cuts)", ""),
            K("Test menu / esoteric mix", "pct"),
            K("No-pay/denial rate", "pct"),
        ),
        reimbursement_codes=("CPT lab/path 80000-89000", "molecular/genetic"),
        reimbursement_mechanics="Per-test reimbursement under CLFS/PFS; "
                                "PAMA-driven rate cuts.",
        data_sources=("CMS Physician & Other Practitioners", "CLFS", "NPPES"),
        thesis="Precision medicine, genetic-testing volume.",
        risks="PAMA reimbursement cuts, payer coverage, reimbursement per test.",
        exhibits=("Test-volume sizing", "Reimbursement-per-test trend",
                  "Payer mix"),
    ),

    # ── GROUPING 6 — CONSUMER / OTHER ─────────────────────────────────────
    Subsector(
        id="medical_aesthetics",
        name="Medical Aesthetics / Medspas",
        grouping=G.CONSUMER_OTHER,
        business_model="Cash-pay; injectables recurring + device/laser.",
        kpis=(
            K("Revenue per location", "dollars"),
            K("Recurring injectable %", "pct"),
            K("Membership", "count"),
            K("Consult conversion", "pct"),
            K("Provider productivity", "ratio"),
        ),
        reimbursement_codes=("Cash-pay (no CMS codes)",),
        reimbursement_mechanics="Cash-pay; recurring injectable revenue + device "
                                "utilization.",
        data_sources=("Target P&L",),
        thesis="Cash-pay growth, recurring.",
        risks="Discretionary/cyclical, supervision/CPOM.",
        exhibits=("Recurring revenue cohort", "Membership retention",
                  "Density map"),
    ),
    Subsector(
        id="hearing_aids",
        name="Hearing Aids / Audiology",
        grouping=G.CONSUMER_OTHER,
        business_model="Device sale + fitting/service.",
        kpis=(
            K("Units per location", "count"),
            K("ASP", "dollars"),
            K("Attach (service plans)", "pct"),
            K("Referral", ""),
        ),
        reimbursement_codes=("Device retail + V-codes",),
        reimbursement_mechanics="Device sale ASP + fitting/service; mostly "
                                "cash/retail.",
        data_sources=("Target P&L", "NPPES"),
        thesis="Aging demand.",
        risks="OTC hearing-aid disruption, commoditization.",
        exhibits=("Units/location", "ASP trend", "Service-attach"),
    ),
    Subsector(
        id="dme",
        name="DME / Home Medical Equipment",
        grouping=G.CONSUMER_OTHER,
        business_model="Product reimbursement (competitive bidding).",
        kpis=(
            K("Revenue per category", "dollars"),
            K("Payer mix", "pct"),
            K("Rental vs sale", "pct"),
            K("Denial rate", "pct"),
            K("Resupply recurring", "pct"),
        ),
        reimbursement_codes=("HCPCS E-codes (competitive bidding)",),
        reimbursement_mechanics="Product reimbursement under competitive "
                                "bidding; rental vs sale; resupply recurring.",
        data_sources=("CMS competitive-bidding rates", "Target billing"),
        thesis="Aging-in-place, resupply recurring revenue.",
        risks="Competitive-bidding reimbursement, audit.",
        exhibits=("Revenue by category", "Rental vs sale", "Resupply cohort"),
    ),
    Subsector(
        id="healthcare_staffing",
        name="Healthcare Staffing (nurse/locum/allied)",
        grouping=G.CONSUMER_OTHER,
        business_model="Bill-rate spread over pay-rate.",
        kpis=(
            K("Bill-pay spread/margin", "pct"),
            K("Fill rate", "pct"),
            K("Headcount on assignment", "count"),
            K("Contract vs perm mix", "pct"),
            K("Client concentration", "pct"),
        ),
        reimbursement_codes=("N/A (bill-rate spread)",),
        reimbursement_mechanics="Bill-rate spread over pay-rate; gross margin "
                                "is the spread.",
        data_sources=("Target billing/CRM", "BLS OES wages"),
        thesis="Labor shortage (normalizing post-COVID).",
        risks="Bill-rate normalization, gross-margin compression.",
        exhibits=("Spread trend", "Volume x rate bridge", "Client concentration"),
    ),
    Subsector(
        id="medical_education",
        name="Medical Education / Training",
        grouping=G.CONSUMER_OTHER,
        business_model="Tuition / subscription.",
        kpis=(
            K("Enrollment", "count"),
            K("Completion", "pct"),
            K("Recurring", "pct"),
        ),
        reimbursement_codes=("Tuition / subscription",),
        reimbursement_mechanics="Tuition or subscription recurring revenue.",
        data_sources=("Target P&L",),
        thesis="Workforce-shortage-driven training demand.",
        risks="Enrollment cyclicality, accreditation.",
        exhibits=("Enrollment trend", "Completion rate", "Recurring-mix"),
    ),
    Subsector(
        id="healthcare_real_estate",
        name="Healthcare Real Estate (MOBs)",
        grouping=G.CONSUMER_OTHER,
        business_model="Rental income.",
        kpis=(
            K("Occupancy", "pct"),
            K("Lease term (WALT)", "years"),
            K("Tenant credit (health-system anchor)", ""),
            K("Cap rate", "pct"),
            K("Rent per sf", "dollars"),
        ),
        reimbursement_codes=("Lease rental income (no CMS codes)",),
        reimbursement_mechanics="Rental income; cap-rate-driven valuation; "
                                "tenant credit quality.",
        data_sources=("Target rent roll", "Comparable cap-rate data"),
        thesis="Outpatient shift, demographic demand.",
        risks="Interest rates, tenant credit.",
        exhibits=("Occupancy/WALT", "Tenant-credit", "Cap-rate benchmarking"),
    ),
)


# ── Indexes (built once at import) ────────────────────────────────────────
_BY_ID: Dict[str, Subsector] = {s.id: s for s in _SUBSECTORS}


def _validate() -> None:
    """Fail loudly at import if the registry is internally inconsistent.

    A duplicate id would silently shadow an entry in ``_BY_ID`` and make
    ``by_id`` return the wrong subsector; catching it here (rather than in a
    test that might not run) keeps the single-source-of-truth invariant honest.
    """
    if len(_BY_ID) != len(_SUBSECTORS):
        seen, dupes = set(), set()
        for s in _SUBSECTORS:
            (dupes if s.id in seen else seen).add(s.id)
        raise ValueError(f"duplicate subsector id(s): {sorted(dupes)}")


_validate()


# ── Public lookups ────────────────────────────────────────────────────────
def all_subsectors() -> List[Subsector]:
    """Every subsector, in registry (grouping) order."""
    return list(_SUBSECTORS)


def by_id(subsector_id: str) -> Subsector | None:
    """One subsector by slug, or ``None`` when unknown (callers treat an
    unknown id as out-of-scope, not an error — mirrors ``nucc_taxonomy.by_code``)."""
    return _BY_ID.get(str(subsector_id).strip().lower())


def by_grouping(grouping: Grouping | str) -> List[Subsector]:
    """All subsectors in one grouping, registry order. Accepts the enum or its
    string value/name so ``by_grouping("Facility-Based Care")`` and
    ``by_grouping(Grouping.FACILITY_BASED)`` both work."""
    g = _coerce_grouping(grouping)
    return [s for s in _SUBSECTORS if s.grouping is g]


def groupings() -> List[Grouping]:
    """The six groupings in canonical order."""
    return list(Grouping)


def grouping_counts() -> Dict[Grouping, int]:
    """Subsector count per grouping — powers the taxonomy overview header."""
    out: Dict[Grouping, int] = {g: 0 for g in Grouping}
    for s in _SUBSECTORS:
        out[s.grouping] += 1
    return out


def search(query: str) -> List[Subsector]:
    """Subsectors whose id/name/business-model/thesis/risks contain ``query``
    (case-insensitive). Empty/blank query returns nothing rather than the whole
    universe, so a stray ``search("")`` in a UI doesn't dump 55 rows."""
    return [s for s in _SUBSECTORS if s.matches(query)]


def central_subsectors() -> List[Subsector]:
    """The Part D 'most-central' archetypes flagged for deep-dive packs."""
    return [s for s in _SUBSECTORS if s.central]


def by_vertical(vertical: str) -> List[Subsector]:
    """Subsectors that crosswalk to a first-class ``verticals.Vertical`` value
    (HOSPITAL/ASC/MSO/BEHAVIORAL_HEALTH). Case-insensitive."""
    v = str(vertical).strip().upper()
    return [s for s in _SUBSECTORS if s.vertical.upper() == v]


def by_nucc_vertical(nucc_vertical: str) -> List[Subsector]:
    """Subsectors crosswalked to an NPPES PE-vertical tag from
    ``data_public.nucc_taxonomy`` (e.g. ``"home_health"``), so a subsector can
    be turned into a live provider-supply count. Case-insensitive."""
    v = str(nucc_vertical).strip().lower()
    return [s for s in _SUBSECTORS if v in tuple(x.lower() for x in s.nucc_verticals)]


def _coerce_grouping(grouping: Grouping | str) -> Grouping:
    """Accept a Grouping, its ``.value`` label, or its ``.name`` — raising a
    clear error rather than returning an empty list on a typo."""
    if isinstance(grouping, Grouping):
        return grouping
    raw = str(grouping).strip()
    for g in Grouping:
        if raw == g.value or raw.upper() == g.name:
            return g
    raise ValueError(f"unknown grouping: {grouping!r}")


__all__ = [
    "all_subsectors", "by_id", "by_grouping", "groupings", "grouping_counts",
    "search", "central_subsectors", "by_vertical", "by_nucc_vertical",
]
