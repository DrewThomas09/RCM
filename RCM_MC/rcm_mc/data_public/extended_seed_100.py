"""Extended seed 100: Urology / men's-health PE deals.

This module contains a curated set of 15 healthcare private equity
deal records focused on the urology and men's-health subsector. The
theme covers:

- Urology practice platforms delivering comprehensive urologic care
  (BPH evaluation and treatment, stone disease management, prostate
  cancer screening / biopsy / radical prostatectomy, bladder cancer,
  pediatric urology, female urology / urogynecology, male fertility)
  under large-group independent-urology practice models with
  ancillary service lines in in-office imaging (CT / MRI / ultrasound),
  ambulatory surgery centers (ASCs), radiation oncology (IMRT for
  prostate cancer), pathology labs, and dispensing pharmacy
- Men's health platforms offering testosterone replacement therapy
  (TRT) cash-pay programs, erectile dysfunction (ED) management,
  peptide therapy, hair-loss treatment, and sexual-health services
  via brick-and-mortar clinic networks, direct-to-consumer (D2C)
  telehealth brands (Hims & Hers Health, Ro/Roman, Mosh, BlueChew,
  Numan), and hybrid brick-and-click delivery models
- BPH (benign prostatic hyperplasia) treatment centers performing
  minimally invasive surgical therapies (MISTs) — UroLift
  (Teleflex prostatic urethral lift), Rezum (Boston Scientific
  water-vapor thermal therapy), Aquablation (PROCEPT BioRobotics
  robotic waterjet ablation), GreenLight laser photoselective
  vaporization of the prostate (PVP), holmium laser enucleation of
  the prostate (HoLEP), and traditional transurethral resection of
  the prostate (TURP) — typically as office-based procedures or
  ASC-based outpatient surgery with favorable Medicare Part B and
  commercial-payer reimbursement
- Kidney stone centers delivering comprehensive stone-disease
  management including extracorporeal shock wave lithotripsy
  (ESWL), ureteroscopy with laser lithotripsy (URS/LL),
  percutaneous nephrolithotomy (PCNL), medical expulsive therapy,
  and stone-prevention metabolic evaluation / 24-hour urine
  collection / dietary counseling programs
- Prostate cancer care platforms offering integrated diagnosis-to-
  treatment pathways — PSA screening, multiparametric MRI (mpMRI),
  fusion-guided prostate biopsy, Gleason grading pathology,
  genomic risk stratification (Decipher, Oncotype DX Prostate,
  Prolaris), active surveillance protocols, da Vinci robotic-
  assisted radical prostatectomy (RARP), IMRT / SBRT radiation,
  brachytherapy, focal therapy (HIFU, cryotherapy), and advanced
  prostate cancer management (androgen deprivation therapy,
  novel hormonals like Xtandi / Zytiga / Nubeqa / Erleada,
  PSMA-PET imaging, and Lu-177 PSMA-617 Pluvicto radioligand
  therapy)

Urology and men's-health economics are distinguished by an
elevated self-pay / cash-pay revenue stream (5-15% self-pay
reflecting TRT cash-pay programs, men's health D2C subscription
revenue, and ED / sexual-health concierge pricing) layered on a
commercial-heavy base (38-55% commercial) and a material Medicare
segment (32-48% Medicare reflecting the aging-male urology /
prostate-cancer / BPH patient demographic where the median urology
patient is 65+ and Medicare fee-for-service and Medicare Advantage
dominate the BPH / prostate-cancer / overactive-bladder case mix).
The subsector faces specific regulatory and reimbursement dynamics:
(a) the 2024-2026 CMS Medicare Physician Fee Schedule (MPFS)
revaluation of urology CPT codes with favorable office-based BPH
MIST (UroLift CPT 52441 / 52442, Rezum CPT 53854) reimbursement
driving office-based procedure migration, (b) Medicare site-of-
service payment differentials between office / ASC / HOPD venues
creating ASC-migration economics on BPH and stone procedures where
the ASC rate captures 60-75% of the HOPD rate versus the office-
based rate capturing 40-55% of the HOPD rate, (c) da Vinci
robotic-assisted surgery utilization economics with Intuitive
Surgical's Xi / SP platform capital costs ($1.5-$2.5M per unit)
and per-case instrument costs ($1,500-$2,500) offset by
favorable radical prostatectomy (RARP) reimbursement versus open
radical prostatectomy, (d) LUGPA (Large Urology Group Practice
Association) consolidation dynamics with 75+ large-group
independent urology practices (US Urology Partners, Solaris
Health, Urology America, United Urology Group, Chesapeake
Urology) backed by PE sponsors including Audax, Lee Equity,
NMS Capital, and Silver Oak Services Partners, (e) TRT cash-pay
economics with testosterone replacement therapy priced at
$150-$400/month cash-pay subscription (injectable testosterone
cypionate / enanthate, testosterone pellets, topical
testosterone, and hCG / anastrozole ancillary therapy) and
FDA-indicated testosterone prescribing requiring documented
hypogonadism (two morning total testosterone measurements <300
ng/dL and clinical symptoms) with commercial-payer coverage
variably restrictive driving cash-pay migration, (f) men's
health D2C brands (Hims & Hers Health, Ro/Roman, Numan, Mosh,
BlueChew) scaling TRT / ED / hair-loss / mental-health
subscription revenue at $20-$100/month ARPU with asynchronous
telehealth consultation / compounded-pharmacy dispensing and
aggressive digital-direct-response customer-acquisition
spending — creating competitive pressure on brick-and-mortar
men's-health clinics, (g) prostate cancer genomics and PSMA-PET
imaging adoption materially reshaping diagnosis and risk
stratification with Decipher / Oncotype DX Prostate / Prolaris
genomic classifiers guiding treatment intensification decisions
and PSMA-PET imaging (Gallium-68 PSMA-11 / F-18 piflufolastat /
F-18 flotufolastat) replacing conventional bone scan / CT in
staging and biochemical-recurrence evaluation, and (h) Lu-177
PSMA-617 Pluvicto radioligand therapy approved for mCRPC
(metastatic castration-resistant prostate cancer) creating new
radiopharmacy / theranostics revenue streams for integrated
urology / prostate-cancer platforms. Value creation in PE-
backed urology and men's-health platforms centers on LUGPA
consolidation and scale-driven payer contracting, ASC
migration of BPH and stone procedures from HOPD venues,
UroLift / Rezum / Aquablation adoption in office-based BPH
management capturing favorable MIST reimbursement, da Vinci
RARP utilization optimization and robotic-surgery volume
scaling, prostate-cancer integrated-care pathway development
with in-house mpMRI / fusion biopsy / genomics / radiation
oncology, TRT cash-pay program scaling with concierge /
membership pricing models, and men's-health D2C platform
customer-acquisition / retention economics. Each record
captures deal economics (EV, EV/EBITDA, margins), return
profile (MOIC, IRR, hold period), payer mix, regional
footprint, sponsor, realization status, and a short deal
narrative. These records are synthesized for modeling,
backtesting, and scenario analysis use cases.
"""

EXTENDED_SEED_DEALS_100 = [
    {
        "company_name": "Sagebrush Urology Partners",
        "sector": "Urology Practice",
        "buyer": "Audax Private Equity",
        "year": 2018,
        "region": "Southeast",
        "ev_mm": 485.0,
        "ev_ebitda": 13.5,
        "ebitda_mm": 101.85,
        "ebitda_margin": 0.21,
        "revenue_mm": 485.00,
        "hold_years": 5.5,
        "moic": 2.9,
        "irr": 0.2148,
        "status": "Realized",
        "payer_mix": {"commercial": 0.45, "medicaid": 0.08, "medicare": 0.40, "self_pay": 0.07},
        "comm_pct": 0.45,
        "deal_narrative": (
            "Southeast LUGPA-scale urology practice platform "
            "operating 42 clinic sites across Florida, Georgia, "
            "and the Carolinas with integrated ancillaries "
            "including 4 urology-focused ambulatory surgery "
            "centers (ASCs), in-office CT / MRI / ultrasound "
            "imaging, a CLIA-certified pathology lab, and "
            "dispensing pharmacy. Clinical footprint spans BPH "
            "management (UroLift prostatic urethral lift, Rezum "
            "water-vapor thermal therapy, GreenLight laser PVP, "
            "TURP), prostate cancer care (mpMRI fusion-guided "
            "biopsy, da Vinci robotic-assisted radical "
            "prostatectomy at 380 RARP cases annually), stone "
            "disease (ESWL, ureteroscopy with laser lithotripsy, "
            "PCNL), and female / pediatric urology. Long hold "
            "executed the LUGPA consolidation playbook — adding "
            "14 tuck-in urology-practice acquisitions, migrating "
            "BPH MIST volume from HOPD to office-based venues "
            "capturing favorable CMS Medicare Physician Fee "
            "Schedule (MPFS) office-based reimbursement on CPT "
            "52441 / 52442 (UroLift) and CPT 53854 (Rezum), and "
            "exited to a strategic physician-services platform at "
            "2.9x MOIC."
        ),
    },
    {
        "company_name": "Ironwood Men's Health Clinics",
        "sector": "Men's Health Platform",
        "buyer": "Shore Capital Partners",
        "year": 2019,
        "region": "National",
        "ev_mm": 215.0,
        "ev_ebitda": 11.5,
        "ebitda_mm": 54.95,
        "ebitda_margin": 0.25,
        "revenue_mm": 215.00,
        "hold_years": 5.0,
        "moic": 2.6,
        "irr": 0.2113,
        "status": "Realized",
        "payer_mix": {"commercial": 0.42, "medicaid": 0.04, "medicare": 0.40, "self_pay": 0.14},
        "comm_pct": 0.42,
        "deal_narrative": (
            "National men's-health clinic platform operating 58 "
            "brick-and-mortar locations across Texas, Florida, "
            "Arizona, Colorado, and California delivering "
            "testosterone replacement therapy (TRT) cash-pay "
            "programs, erectile dysfunction (ED) management, "
            "peptide therapy, hair-loss treatment, and concierge "
            "sexual-health services. TRT service mix captures "
            "injectable testosterone cypionate / enanthate "
            "programs (~65% of TRT patients), testosterone "
            "pellet insertion (~20%), topical testosterone "
            "gels (~10%), and hCG / anastrozole ancillary "
            "therapy with average cash-pay subscription pricing "
            "of $225-$350/month. Long hold scaled TRT active-"
            "patient panel from 38,000 to 142,000, built "
            "compliant FDA-indicated hypogonadism prescribing "
            "protocols (dual morning total testosterone <300 "
            "ng/dL documentation), navigated competitive "
            "pressure from D2C telehealth entrants (Hims, Ro, "
            "BlueChew), and exited to a strategic health-and-"
            "wellness consolidator at 2.6x MOIC."
        ),
    },
    {
        "company_name": "Cholla BPH Treatment Centers",
        "sector": "BPH Treatment Center",
        "buyer": "NMS Capital",
        "year": 2020,
        "region": "Southwest",
        "ev_mm": 165.0,
        "ev_ebitda": 12.5,
        "ebitda_mm": 37.95,
        "ebitda_margin": 0.23,
        "revenue_mm": 165.00,
        "hold_years": 4.5,
        "moic": 2.2,
        "irr": 0.1956,
        "status": "Active",
        "payer_mix": {"commercial": 0.41, "medicaid": 0.05, "medicare": 0.46, "self_pay": 0.08},
        "comm_pct": 0.41,
        "deal_narrative": (
            "Southwest BPH-focused treatment center platform "
            "operating 22 office-based procedure suites across "
            "Arizona, Nevada, New Mexico, and West Texas "
            "delivering minimally invasive surgical therapies "
            "(MISTs) for benign prostatic hyperplasia — UroLift "
            "(Teleflex prostatic urethral lift), Rezum (Boston "
            "Scientific water-vapor thermal therapy), and "
            "selective GreenLight laser photoselective "
            "vaporization of the prostate (PVP) in partnered ASC "
            "venues. Case mix weighted 58% UroLift / 28% Rezum / "
            "14% GreenLight or TURP across 4,800 annual BPH "
            "procedures with a Medicare-heavy payer mix "
            "reflecting the 65+ BPH patient demographic. Mid-"
            "hold scaling case volume via referral-physician "
            "network expansion, capturing CMS MPFS office-based "
            "reimbursement on CPT 52441/52442 (UroLift) and CPT "
            "53854 (Rezum) at favorable non-facility payment "
            "rates, navigating post-2024 MPFS revaluation "
            "dynamics, and targeting sale to a strategic urology "
            "services platform at a mid-teens multiple."
        ),
    },
    {
        "company_name": "Tamarack Urology America",
        "sector": "Urology Practice",
        "buyer": "Lee Equity Partners",
        "year": 2017,
        "region": "National",
        "ev_mm": 715.0,
        "ev_ebitda": 14.5,
        "ebitda_mm": 157.30,
        "ebitda_margin": 0.22,
        "revenue_mm": 715.00,
        "hold_years": 6.5,
        "moic": 3.4,
        "irr": 0.2012,
        "status": "Realized",
        "payer_mix": {"commercial": 0.44, "medicaid": 0.08, "medicare": 0.42, "self_pay": 0.06},
        "comm_pct": 0.44,
        "deal_narrative": (
            "National LUGPA-scale urology practice platform with "
            "88 clinic sites across 14 states and integrated "
            "ancillaries including 8 urology ASCs, 6 IMRT-"
            "capable radiation oncology centers for prostate "
            "cancer treatment, in-office mpMRI / fusion biopsy "
            "suites, pathology lab with Gleason grading and "
            "genomic classifier (Decipher, Oncotype DX Prostate, "
            "Prolaris) order infrastructure, and dispensing "
            "pharmacy. Da Vinci robotic program executes 950+ "
            "RARP (robotic-assisted radical prostatectomy) cases "
            "annually across the platform on Intuitive Xi / SP "
            "systems. Long 6.5-year hold consolidated 28 tuck-in "
            "urology-practice acquisitions, scaled office-based "
            "UroLift / Rezum BPH MIST volume to 8,200 annual "
            "cases, built integrated prostate-cancer pathway "
            "capability with mpMRI fusion biopsy and genomic "
            "risk stratification, captured peak 2023-2024 "
            "LUGPA-platform M&A valuations, and exited to a "
            "strategic diversified physician-services platform "
            "at 3.4x MOIC."
        ),
    },
    {
        "company_name": "Yucca Stone Center Network",
        "sector": "Stone Center",
        "buyer": "Silver Oak Services Partners",
        "year": 2019,
        "region": "West",
        "ev_mm": 125.0,
        "ev_ebitda": 11.0,
        "ebitda_mm": 25.00,
        "ebitda_margin": 0.20,
        "revenue_mm": 125.00,
        "hold_years": 5.0,
        "moic": 2.1,
        "irr": 0.1636,
        "status": "Realized",
        "payer_mix": {"commercial": 0.48, "medicaid": 0.10, "medicare": 0.35, "self_pay": 0.07},
        "comm_pct": 0.48,
        "deal_narrative": (
            "West Coast kidney stone center network operating 14 "
            "stone-disease-focused clinic locations and 3 "
            "dedicated stone ASCs across California, Oregon, "
            "Washington, and Nevada delivering comprehensive "
            "stone-disease management — extracorporeal shock "
            "wave lithotripsy (ESWL), ureteroscopy with holmium "
            "laser lithotripsy (URS/LL), percutaneous "
            "nephrolithotomy (PCNL), medical expulsive therapy, "
            "and integrated stone-prevention metabolic "
            "evaluation with 24-hour urine collection, dietary "
            "counseling, and pharmacologic thiazide / "
            "potassium-citrate / allopurinol management. Long "
            "hold scaled annual stone-procedure volume from "
            "6,400 to 11,800 cases (66% URS/LL, 22% ESWL, 12% "
            "PCNL), migrated procedure mix from HOPD to ASC "
            "venues capturing ASC site-of-service reimbursement "
            "advantages, built referral-physician networks with "
            "ED and primary-care stone-patient pipelines, and "
            "exited to a strategic urology consolidator at 2.1x "
            "MOIC."
        ),
    },
    {
        "company_name": "Manzanita Prostate Cancer Care",
        "sector": "Prostate Cancer Care",
        "buyer": "Linden Capital Partners",
        "year": 2018,
        "region": "Midwest",
        "ev_mm": 385.0,
        "ev_ebitda": 15.5,
        "ebitda_mm": 84.70,
        "ebitda_margin": 0.22,
        "revenue_mm": 385.00,
        "hold_years": 6.0,
        "moic": 3.2,
        "irr": 0.2155,
        "status": "Realized",
        "payer_mix": {"commercial": 0.40, "medicaid": 0.05, "medicare": 0.48, "self_pay": 0.07},
        "comm_pct": 0.40,
        "deal_narrative": (
            "Midwest integrated prostate cancer care platform "
            "operating 18 urologic oncology clinic sites, 4 "
            "IMRT / SBRT radiation oncology centers, 3 "
            "brachytherapy suites, and 2 PSMA-PET imaging "
            "centers across Ohio, Indiana, Michigan, Illinois, "
            "and Wisconsin with integrated diagnosis-to-"
            "treatment pathway capability. Service model "
            "captures the full prostate-cancer patient journey "
            "from PSA screening through multiparametric MRI "
            "(mpMRI) and fusion-guided biopsy, Gleason grading "
            "pathology, Decipher / Oncotype DX Prostate / "
            "Prolaris genomic risk stratification, active "
            "surveillance protocols, da Vinci robotic-assisted "
            "radical prostatectomy (RARP at 520 annual cases), "
            "IMRT / SBRT external-beam radiation, LDR and HDR "
            "brachytherapy, focal therapy (HIFU and cryotherapy), "
            "and advanced prostate-cancer management including "
            "novel hormonals (Xtandi, Zytiga, Nubeqa, Erleada) "
            "and Lu-177 PSMA-617 Pluvicto radioligand therapy. "
            "Long hold captured favorable prostate-cancer genomics "
            "and PSMA-PET adoption tailwinds, exited to a "
            "strategic oncology-services platform at 3.2x MOIC."
        ),
    },
    {
        "company_name": "Mesquite Urology Group",
        "sector": "Urology Practice",
        "buyer": "Warburg Pincus",
        "year": 2016,
        "region": "Southwest",
        "ev_mm": 585.0,
        "ev_ebitda": 13.0,
        "ebitda_mm": 134.55,
        "ebitda_margin": 0.23,
        "revenue_mm": 585.00,
        "hold_years": 6.5,
        "moic": 3.6,
        "irr": 0.2201,
        "status": "Realized",
        "payer_mix": {"commercial": 0.42, "medicaid": 0.09, "medicare": 0.43, "self_pay": 0.06},
        "comm_pct": 0.42,
        "deal_narrative": (
            "Texas-and-Southwest LUGPA-scale urology practice "
            "platform with 68 clinic sites across Texas, "
            "Oklahoma, Arkansas, and Louisiana and integrated "
            "ancillaries including 6 urology ASCs, 4 IMRT "
            "radiation oncology centers, in-office imaging, and "
            "pathology lab. Da Vinci robotic-surgery program "
            "executes 620 RARP cases annually with optimized Xi-"
            "platform utilization economics. Long 6.5-year hold "
            "executed aggressive LUGPA consolidation — adding 22 "
            "tuck-in acquisitions across the Texas / Oklahoma "
            "urology-practice landscape, building ASC footprint "
            "from 2 to 6 centers capturing ASC site-of-service "
            "migration on BPH / stone procedures, scaling office-"
            "based UroLift / Rezum BPH MIST volume, developing "
            "in-house mpMRI fusion biopsy capability, and "
            "exiting to a strategic diversified physician-"
            "services platform at 3.6x MOIC on the platform-"
            "scale thesis — a top-quartile outcome in the LUGPA "
            "cycle."
        ),
    },
    {
        "company_name": "Sumac Digital Men's Health",
        "sector": "Men's Health Platform",
        "buyer": "TPG Growth",
        "year": 2021,
        "region": "National",
        "ev_mm": 345.0,
        "ev_ebitda": 17.5,
        "ebitda_mm": 62.10,
        "ebitda_margin": 0.18,
        "revenue_mm": 345.00,
        "hold_years": 3.0,
        "moic": 1.4,
        "irr": 0.1187,
        "status": "Active",
        "payer_mix": {"commercial": 0.38, "medicaid": 0.03, "medicare": 0.34, "self_pay": 0.25},
        "comm_pct": 0.38,
        "deal_narrative": (
            "National hybrid brick-and-click men's-health platform "
            "operating 32 brick-and-mortar concierge clinic "
            "locations and a D2C telehealth subscription business "
            "delivering testosterone replacement therapy (TRT), "
            "erectile dysfunction (ED) management, peptide "
            "therapy, hair-loss treatment (finasteride / "
            "minoxidil), and mental-health medication management "
            "across asynchronous telehealth and in-person "
            "clinical-service delivery. Cash-pay-heavy revenue mix "
            "reflects TRT / ED / hair-loss subscription economics "
            "at $45-$225/month ARPU across 185,000 active "
            "subscribers competing against D2C incumbents (Hims & "
            "Hers Health, Ro/Roman, Mosh, BlueChew, Numan). Early "
            "hold acquired at peak 2021 D2C-healthcare growth-"
            "equity multiples navigating post-2022 digital-health "
            "customer-acquisition-cost compression, CMS / state-"
            "pharmacy-board scrutiny of compounded-GLP-1 and "
            "compounded-testosterone D2C prescribing, and FDA-"
            "indicated hypogonadism-documentation compliance "
            "requirements. Sponsor targeting sale at a compressed "
            "post-peak-multiple exit."
        ),
    },
    {
        "company_name": "Palmetto Urology Consolidated",
        "sector": "Urology Practice",
        "buyer": "Silver Oak Services Partners",
        "year": 2019,
        "region": "Southeast",
        "ev_mm": 265.0,
        "ev_ebitda": 12.5,
        "ebitda_mm": 58.30,
        "ebitda_margin": 0.22,
        "revenue_mm": 265.00,
        "hold_years": 4.5,
        "moic": 2.3,
        "irr": 0.2021,
        "status": "Active",
        "payer_mix": {"commercial": 0.43, "medicaid": 0.08, "medicare": 0.43, "self_pay": 0.06},
        "comm_pct": 0.43,
        "deal_narrative": (
            "Southeast regional urology practice consolidation "
            "platform with 26 clinic sites across South Carolina, "
            "North Carolina, and Georgia and integrated "
            "ancillaries including 2 urology ASCs, in-office "
            "imaging, and dispensing pharmacy. Clinical case mix "
            "weighted toward BPH management (32% of revenue via "
            "UroLift / Rezum / GreenLight PVP / TURP office-based "
            "and ASC-based procedures), prostate cancer care "
            "(26% via mpMRI fusion biopsy and da Vinci RARP at "
            "180 annual cases), stone disease (18% via ESWL / "
            "URS/LL / PCNL), female / overactive bladder (12%), "
            "and general urology (12%). Mid-hold executing "
            "LUGPA-model tuck-in consolidation, scaling office-"
            "based BPH MIST volume from 1,200 to 2,400 annual "
            "cases, optimizing ASC site-of-service migration on "
            "stone and BPH procedures, and targeting sale to a "
            "strategic diversified physician-services platform at "
            "a mid-teens multiple."
        ),
    },
    {
        "company_name": "Juniper Men's Wellness Network",
        "sector": "Men's Health Platform",
        "buyer": "Great Hill Partners",
        "year": 2018,
        "region": "Southeast",
        "ev_mm": 145.0,
        "ev_ebitda": 10.5,
        "ebitda_mm": 40.60,
        "ebitda_margin": 0.28,
        "revenue_mm": 145.00,
        "hold_years": 5.5,
        "moic": 2.8,
        "irr": 0.2049,
        "status": "Realized",
        "payer_mix": {"commercial": 0.40, "medicaid": 0.04, "medicare": 0.41, "self_pay": 0.15},
        "comm_pct": 0.40,
        "deal_narrative": (
            "Southeast men's-health clinic network operating 38 "
            "brick-and-mortar concierge locations across Florida, "
            "Georgia, Alabama, and Tennessee with a heavily cash-"
            "pay-oriented TRT / ED / hair-loss / peptide-therapy "
            "service model. TRT program mix weighted toward "
            "testosterone pellet insertion (~45% of TRT patients) "
            "and injectable testosterone cypionate (~40%) with "
            "average membership pricing of $250-$400/month cash-"
            "pay. Service menu expansion includes peptide therapy "
            "(BPC-157, CJC-1295, ipamorelin, sermorelin), "
            "shockwave therapy for ED, low-intensity extracorporeal "
            "shockwave therapy (Li-ESWT) for erectile function, "
            "and weight-loss / metabolic-health programs including "
            "compounded semaglutide / tirzepatide. Long hold "
            "scaled active-member panel from 18,000 to 62,000, "
            "navigated competitive pressure from D2C telehealth "
            "entrants (Hims, Ro, BlueChew), built scalable "
            "compliant FDA-indicated hypogonadism prescribing "
            "protocols, and exited to a strategic health-and-"
            "wellness consolidator at 2.8x MOIC."
        ),
    },
    {
        "company_name": "Agave BPH Centers of Excellence",
        "sector": "BPH Treatment Center",
        "buyer": "Gryphon Investors",
        "year": 2020,
        "region": "West",
        "ev_mm": 235.0,
        "ev_ebitda": 13.0,
        "ebitda_mm": 51.70,
        "ebitda_margin": 0.22,
        "revenue_mm": 235.00,
        "hold_years": 4.0,
        "moic": 2.0,
        "irr": 0.1892,
        "status": "Active",
        "payer_mix": {"commercial": 0.42, "medicaid": 0.06, "medicare": 0.45, "self_pay": 0.07},
        "comm_pct": 0.42,
        "deal_narrative": (
            "West Coast BPH-focused treatment center platform "
            "operating 28 office-based procedure suites and 4 "
            "partnered ASCs across California, Oregon, Washington, "
            "and Nevada delivering the full minimally invasive "
            "BPH treatment spectrum — UroLift (Teleflex prostatic "
            "urethral lift) in office, Rezum (Boston Scientific "
            "water-vapor thermal therapy) in office, Aquablation "
            "(PROCEPT BioRobotics AquaBeam robotic waterjet "
            "ablation) in ASC, GreenLight laser photoselective "
            "vaporization of the prostate (PVP) in ASC, holmium "
            "laser enucleation of the prostate (HoLEP), and "
            "traditional transurethral resection of the prostate "
            "(TURP). Case mix across 7,200 annual BPH procedures "
            "weighted 48% UroLift / 22% Rezum / 12% Aquablation / "
            "10% GreenLight / 8% TURP/HoLEP. Mid-hold scaling "
            "Aquablation program as a differentiated offering "
            "against competing UroLift / Rezum MIST pure-plays, "
            "capturing favorable office-based and ASC-based CMS "
            "reimbursement, and targeting sale to a strategic "
            "urology-services platform."
        ),
    },
    {
        "company_name": "Cottonwood Solaris Health Urology",
        "sector": "Urology Practice",
        "buyer": "Lee Equity Partners",
        "year": 2020,
        "region": "Mid-Atlantic",
        "ev_mm": 545.0,
        "ev_ebitda": 13.5,
        "ebitda_mm": 114.45,
        "ebitda_margin": 0.21,
        "revenue_mm": 545.00,
        "hold_years": 4.5,
        "moic": 2.1,
        "irr": 0.1794,
        "status": "Active",
        "payer_mix": {"commercial": 0.46, "medicaid": 0.08, "medicare": 0.40, "self_pay": 0.06},
        "comm_pct": 0.46,
        "deal_narrative": (
            "Mid-Atlantic LUGPA-scale urology practice platform "
            "with 72 clinic sites across Maryland, Virginia, "
            "Delaware, New Jersey, and Pennsylvania and integrated "
            "ancillaries including 5 urology ASCs, 3 IMRT / SBRT "
            "radiation oncology centers, in-office mpMRI / fusion "
            "biopsy suites, pathology lab with Gleason grading, "
            "and dispensing pharmacy. Da Vinci robotic-surgery "
            "program executes 480 RARP cases annually across Xi "
            "and SP platforms. Mid-hold executing LUGPA "
            "consolidation playbook — pursuing 12 identified "
            "tuck-in urology-practice targets, scaling office-"
            "based UroLift / Rezum BPH MIST volume, optimizing "
            "da Vinci RARP case-mix and robotic-platform "
            "utilization economics, developing integrated "
            "prostate-cancer pathway capability with mpMRI "
            "fusion biopsy and Decipher / Oncotype DX Prostate / "
            "Prolaris genomic risk stratification, and targeting "
            "sale to a strategic diversified physician-services "
            "platform at a mid-teens multiple."
        ),
    },
    {
        "company_name": "Prickly Pear Prostate Care",
        "sector": "Prostate Cancer Care",
        "buyer": "Water Street Healthcare Partners",
        "year": 2017,
        "region": "National",
        "ev_mm": 425.0,
        "ev_ebitda": 16.5,
        "ebitda_mm": 80.75,
        "ebitda_margin": 0.19,
        "revenue_mm": 425.00,
        "hold_years": 6.5,
        "moic": 3.8,
        "irr": 0.2218,
        "status": "Realized",
        "payer_mix": {"commercial": 0.39, "medicaid": 0.06, "medicare": 0.48, "self_pay": 0.07},
        "comm_pct": 0.39,
        "deal_narrative": (
            "National integrated prostate cancer care platform "
            "with 24 urologic oncology clinic sites, 8 IMRT / "
            "SBRT radiation oncology centers, 5 brachytherapy "
            "suites, and 4 PSMA-PET imaging / radiopharmacy "
            "facilities across the Northeast, Mid-Atlantic, "
            "Southeast, and Midwest. Integrated diagnosis-to-"
            "treatment pathway captures the full prostate-cancer "
            "patient journey — PSA screening, multiparametric "
            "MRI (mpMRI), fusion-guided prostate biopsy, Gleason "
            "grading pathology, Decipher / Oncotype DX Prostate / "
            "Prolaris genomic risk stratification, active "
            "surveillance protocols, da Vinci robotic-assisted "
            "radical prostatectomy (RARP at 820 annual cases), "
            "IMRT / SBRT external-beam radiation, LDR and HDR "
            "brachytherapy, focal therapy (HIFU, cryotherapy), "
            "advanced prostate-cancer management with novel "
            "hormonals (Xtandi, Zytiga, Nubeqa, Erleada), PSMA-"
            "PET imaging, and Lu-177 PSMA-617 Pluvicto "
            "radioligand therapy. Long 6.5-year hold captured "
            "peak prostate-cancer genomics / PSMA-PET / Pluvicto "
            "adoption cycle, scaled theranostics revenue stream, "
            "and exited to a strategic oncology-services "
            "platform at 3.8x MOIC — the top-performing exit in "
            "the subsector cycle."
        ),
    },
    {
        "company_name": "Sandstone Stone Disease Partners",
        "sector": "Stone Center",
        "buyer": "BPOC (Beecken Petty O'Keefe)",
        "year": 2021,
        "region": "Midwest",
        "ev_mm": 85.0,
        "ev_ebitda": 10.5,
        "ebitda_mm": 15.30,
        "ebitda_margin": 0.18,
        "revenue_mm": 85.00,
        "hold_years": 3.5,
        "moic": 1.5,
        "irr": 0.1215,
        "status": "Active",
        "payer_mix": {"commercial": 0.50, "medicaid": 0.11, "medicare": 0.33, "self_pay": 0.06},
        "comm_pct": 0.50,
        "deal_narrative": (
            "Midwest kidney stone center platform operating 9 "
            "stone-disease-focused clinic locations and 2 "
            "dedicated stone ASCs across Missouri, Kansas, Iowa, "
            "and Nebraska delivering ESWL, ureteroscopy with "
            "holmium laser lithotripsy (URS/LL), percutaneous "
            "nephrolithotomy (PCNL), and stone-prevention "
            "metabolic evaluation programs. Service model "
            "captures a commercial-heavy payer mix reflecting "
            "the broader stone-disease age-distribution (onset "
            "typically 30-50 years old with commercial-insurance "
            "coverage dominant versus the older BPH / prostate-"
            "cancer demographic where Medicare dominates). Early "
            "hold acquired at peak 2021 healthcare-services "
            "multiples navigating post-2022 rate-environment "
            "multiple compression, CMS site-of-service ASC-rate "
            "dynamics on stone procedures, and referral-physician "
            "network-building in a fragmented regional "
            "competitive landscape. Sponsor pursuing ASC-"
            "migration of stone-procedure volume and referral-"
            "network expansion to reach target exit multiple."
        ),
    },
    {
        "company_name": "Ponderosa Integrated Urology Platform",
        "sector": "Urology Practice",
        "buyer": "KKR",
        "year": 2016,
        "region": "National",
        "ev_mm": 825.0,
        "ev_ebitda": 14.0,
        "ebitda_mm": 189.75,
        "ebitda_margin": 0.23,
        "revenue_mm": 825.00,
        "hold_years": 6.5,
        "moic": 3.5,
        "irr": 0.2118,
        "status": "Realized",
        "payer_mix": {"commercial": 0.43, "medicaid": 0.09, "medicare": 0.42, "self_pay": 0.06},
        "comm_pct": 0.43,
        "deal_narrative": (
            "National LUGPA-scale integrated urology platform "
            "combining urology practice, BPH treatment, stone "
            "disease, prostate cancer care, and men's-health "
            "service lines across 112 clinic sites, 12 urology "
            "ASCs, 7 IMRT / SBRT radiation oncology centers, 4 "
            "PSMA-PET imaging facilities, in-office mpMRI / "
            "fusion biopsy suites, pathology lab, dispensing "
            "pharmacy, and TRT cash-pay men's-health program "
            "nationally. Da Vinci robotic-surgery program "
            "executes 1,450 RARP cases annually across Xi and SP "
            "platforms — the largest independent RARP program in "
            "the PE-backed urology landscape. Long 6.5-year hold "
            "executed aggressive LUGPA consolidation with 42 "
            "tuck-in acquisitions across the national urology-"
            "practice landscape, scaled office-based UroLift / "
            "Rezum / Aquablation BPH MIST volume, built "
            "integrated prostate-cancer pathway capability with "
            "PSMA-PET and Lu-177 Pluvicto radioligand therapy, "
            "scaled TRT cash-pay men's-health subscription "
            "revenue, and exited to a strategic diversified "
            "physician-services platform at 3.5x MOIC on the "
            "integrated-scale thesis."
        ),
    },
]
