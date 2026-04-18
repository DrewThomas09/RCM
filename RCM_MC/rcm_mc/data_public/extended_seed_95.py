"""Extended seed 95: Medical dermatology / aesthetic / skin-cancer PE deals.

This module contains a curated set of 15 healthcare private equity deal
records focused on the medical dermatology / aesthetic / skin-cancer
subsector. The theme covers:

- Medical dermatology practice platforms delivering general
  medical-dermatology office visits (acne, psoriasis, atopic
  dermatitis, rosacea), biologic-injectable programs for
  psoriasis / AD (Dupixent, Skyrizi, Cosentyx, Tremfya under
  commercial specialty benefits and Medicare Part B buy-and-bill),
  cryotherapy / actinic keratosis destruction (CPT 17000 / 17003 /
  17004), and roll-up of independent single-shingle dermatology
  practices modeled on the Advanced Dermatology & Cosmetic Surgery
  (ADCS / Harvest Partners), U.S. Dermatology Partners (ABRY),
  Forefront Dermatology (OMERS), Epiphany Dermatology (WCAS),
  Pinnacle Dermatology, and Schweiger Dermatology (LLR / Assured)
  PE-backed aggregation thesis
- Mohs micrographic surgery / skin cancer platforms delivering
  Mohs surgery (CPT 17311 first stage of head / neck / genitalia /
  hands / feet; 17312 additional stages same site; 17313 first
  stage trunk / extremities; 17314 additional stages trunk; 17315
  each additional block beyond 5 in a stage), the complex excision
  / closure / flap / graft reconstruction downstream revenue
  (CPT 14000 series adjacent-tissue transfer, 15100 series STSG,
  15200 series FTSG), and the surgical dermatology workflow
  capturing both the Mohs professional fee and the closure
  reconstruction under -59 / XS modifier same-day billing
- Aesthetic / medi-spa platforms delivering injectable neuromodulators
  (Botox / botulinum toxin Type A, Dysport, Xeomin, Daxxify at
  $10-15/unit cash-pay), injectable HA fillers (Juvederm, Restylane,
  RHA collection at $550-850/syringe cash-pay), laser hair removal
  (cash-pay packages $200-400/treatment, 6-treatment typical
  protocol), laser resurfacing (CO2, Fraxel, IPL / BBL), body
  contouring (CoolSculpting cryolipolysis, Emsculpt), and
  skincare / medical-grade topical retail on the PE-backed
  aesthetic roll-up thesis modeled on Ideal Image, LaserAway,
  Skin Laundry, SkinSpirit, and Ever/Body
- Pediatric dermatology subspecialty platforms delivering atopic
  dermatitis / eczema management (Dupixent, crisaborole), hemangioma
  management (propranolol), molluscum / wart destruction, port-
  wine stain / vascular laser (PDL), and genetic skin disorders
  (ichthyosis, epidermolysis bullosa) at academic-center-affiliated
  PE-backed subspecialty networks
- Dermatopathology labs delivering histopathology readouts on
  shave / punch biopsy specimens (CPT 88305 Level IV surgical
  pathology), melanoma / melanocytic lesion diagnosis (including
  the MelanomaDx / DecisionDx-Melanoma molecular ancillary testing
  landscape), IHC staining (88342 / 88341 / 88344), and
  consolidation of the dermpath subsector at the intersection of
  dermatology MSOs and pathology lab roll-ups (Aurora Diagnostics /
  Sonic Healthcare, PathGroup, Miraca / Inform Diagnostics)

Medical dermatology / aesthetic / skin-cancer economics are
distinguished by a commercial-heavy payer mix (50-70% commercial
on medical-dermatology office visits, Mohs surgery, and medical-
necessity surgical destructions), a Medicare block (18-32%)
concentrated in Mohs / actinic keratosis / skin cancer on the
elderly sun-damaged cohort, and a material self-pay (8-20%)
segment concentrated in aesthetic / medi-spa cash-pay service
lines (Botox, fillers, laser hair removal, body contouring,
skincare retail). The subsector faces specific regulatory and
coverage dynamics: (a) Mohs micrographic surgery CPT 17311-17315
requires the same physician to serve as both surgeon and
pathologist — a unique code-set economic structure creating
pricing power for dual-boarded Mohs surgeons (ACMS fellowship-
trained); (b) CMS scrutiny of Mohs utilization via the MAC LCDs
requiring documentation of anatomic site, tumor size, and AUC
(Appropriate Use Criteria published by AAD / ACMS / ASDS /
ASMS in 2012) driving audit-risk management on non-head/neck /
low-risk tumors; (c) commercial-covered biologic-injectable
programs for psoriasis / AD (Dupixent at ~$60K/year WAC)
operating under specialty pharmacy carve-outs and white-bagging
dynamics reducing in-office buy-and-bill margin; (d) skin
substitute / CTP (cellular / tissue-based product) application
in derm surgical practices under 2024-2025 CMS LCD tightening
compressing wound-closure product margin; (e) aesthetic / medi-
spa cash-pay pricing power on Botox ($10-15/unit retail), HA
fillers ($550-850/syringe retail), and laser hair removal
($200-400/treatment retail) with 50-70% gross margin on
consumables after room / labor / provider cost; (f) medical-
spa corporate-practice-of-medicine (CPOM) compliance
variability state-by-state requiring MSO / PC split structures
and MD-supervision requirements on laser / injection service
lines; and (g) PE-backed dermatology aggregation facing
post-2022 multiple compression as the 2015-2022 derm MSO
roll-up wave matured and exit multiples normalized from
18-20x peak to 12-15x. Value creation in PE-backed derm /
aesthetic / skin-cancer platforms centers on Mohs surgery
scale and surgeon-pathologist economics, biologic-injectable
buy-and-bill margin capture where not white-bagged, aesthetic
cash-pay service-line lift and medical-grade skincare retail,
dermpath insourcing / vertical integration capturing the 88305
professional component, and consolidation of independent single-
shingle derm practices into regional MSO platforms. Each record
captures deal economics (EV, EV/EBITDA, margins), return profile
(MOIC, IRR, hold period), payer mix, regional footprint, sponsor,
realization status, and a short deal narrative. These records
are synthesized for modeling, backtesting, and scenario analysis
use cases.
"""

EXTENDED_SEED_DEALS_95 = [
    {
        "company_name": "Aspen Dermatology Partners",
        "sector": "Medical Dermatology",
        "buyer": "Harvest Partners",
        "year": 2018,
        "region": "Southeast",
        "ev_mm": 425.0,
        "ev_ebitda": 13.5,
        "ebitda_mm": 89.25,
        "ebitda_margin": 0.21,
        "revenue_mm": 425.00,
        "hold_years": 5.5,
        "moic": 2.9,
        "irr": 0.2127,
        "status": "Realized",
        "payer_mix": {"commercial": 0.62, "medicare": 0.24, "medicaid": 0.04, "self_pay": 0.10},
        "comm_pct": 0.62,
        "deal_narrative": (
            "Southeast medical dermatology MSO with 78 dermatologists "
            "across 58 clinics delivering general medical dermatology "
            "office visits (acne, psoriasis, atopic dermatitis, rosacea), "
            "biologic-injectable programs (Dupixent, Skyrizi, Cosentyx "
            "under commercial specialty benefits and Medicare Part B "
            "buy-and-bill), cryotherapy / actinic keratosis destruction "
            "(CPT 17000 / 17003 / 17004), and an integrated Mohs "
            "micrographic surgery service line (CPT 17311-17315). Long "
            "hold rolled up 34 single-shingle derm practices on the "
            "ADCS / U.S. Dermatology Partners aggregation playbook, "
            "insourced dermpath (88305 Level IV) capturing professional-"
            "component margin, and exited to a strategic derm MSO at "
            "2.9x MOIC before the 2022 multiple compression."
        ),
    },
    {
        "company_name": "Sequoia Mohs Surgery Institute",
        "sector": "Mohs / Skin Cancer",
        "buyer": "Welsh Carson Anderson & Stowe",
        "year": 2019,
        "region": "West",
        "ev_mm": 285.0,
        "ev_ebitda": 14.0,
        "ebitda_mm": 65.55,
        "ebitda_margin": 0.23,
        "revenue_mm": 285.00,
        "hold_years": 5.0,
        "moic": 2.7,
        "irr": 0.2196,
        "status": "Realized",
        "payer_mix": {"commercial": 0.54, "medicare": 0.32, "medicaid": 0.06, "self_pay": 0.08},
        "comm_pct": 0.54,
        "deal_narrative": (
            "West Coast Mohs micrographic surgery platform with 42 ACMS "
            "fellowship-trained Mohs surgeons across 28 clinics serving "
            "the sun-damaged California / Arizona / Nevada elderly cohort. "
            "Delivers Mohs surgery across the full CPT 17311-17315 code "
            "set (17311 first stage head / neck / genitalia / hands / "
            "feet; 17312 additional stages same site; 17313 first stage "
            "trunk / extremities; 17314 additional stages trunk; 17315 "
            "each additional block beyond 5) capturing the dual surgeon-"
            "pathologist economics, with downstream complex closure / "
            "adjacent-tissue-transfer (CPT 14000 series) and flap / graft "
            "(15100 / 15200 series) reconstruction revenue billed same-"
            "day under -59 / XS modifier. Long hold navigated MAC LCD "
            "documentation on AAD / ACMS / ASDS AUC (Appropriate Use "
            "Criteria 2012) for non-head/neck Mohs indications and "
            "exited to a strategic derm platform at 2.7x MOIC."
        ),
    },
    {
        "company_name": "Luminary Aesthetics Group",
        "sector": "Aesthetic / Medi-Spa",
        "buyer": "L Catterton",
        "year": 2020,
        "region": "National",
        "ev_mm": 685.0,
        "ev_ebitda": 16.0,
        "ebitda_mm": 191.80,
        "ebitda_margin": 0.28,
        "revenue_mm": 685.00,
        "hold_years": 4.5,
        "moic": 3.2,
        "irr": 0.2913,
        "status": "Active",
        "payer_mix": {"commercial": 0.50, "medicare": 0.18, "medicaid": 0.02, "self_pay": 0.30},
        "comm_pct": 0.50,
        "deal_narrative": (
            "National aesthetic / medi-spa platform with 88 locations "
            "modeled on the Ideal Image / LaserAway / SkinSpirit cash-pay "
            "aesthetic roll-up playbook. Service mix delivers injectable "
            "neuromodulators (Botox / botulinum toxin Type A, Dysport, "
            "Xeomin, Daxxify at $10-15/unit retail cash-pay with 50-60% "
            "gross margin on consumable after provider / room cost), "
            "injectable HA fillers (Juvederm, Restylane, RHA collection "
            "at $550-850/syringe retail), laser hair removal (cash-pay "
            "$200-400/treatment, 6-treatment packaged protocol), laser "
            "resurfacing (CO2, Fraxel, IPL / BBL), body contouring "
            "(CoolSculpting cryolipolysis, Emsculpt), and medical-grade "
            "skincare retail (ZO, SkinMedica, SkinCeuticals). Mid-hold "
            "navigates state-by-state CPOM / MSO structuring on laser / "
            "injection supervision, grows loyalty membership program, "
            "and sponsor targeting 3.5-3.8x exit on cash-pay EBITDA scale."
        ),
    },
    {
        "company_name": "Cedarview Dermatology Network",
        "sector": "Medical Dermatology",
        "buyer": "ABRY Partners",
        "year": 2017,
        "region": "Mid-Atlantic",
        "ev_mm": 545.0,
        "ev_ebitda": 13.0,
        "ebitda_mm": 119.90,
        "ebitda_margin": 0.22,
        "revenue_mm": 545.00,
        "hold_years": 6.0,
        "moic": 3.4,
        "irr": 0.2254,
        "status": "Realized",
        "payer_mix": {"commercial": 0.60, "medicare": 0.26, "medicaid": 0.06, "self_pay": 0.08},
        "comm_pct": 0.60,
        "deal_narrative": (
            "Mid-Atlantic medical dermatology MSO with 92 dermatologists "
            "and 24 PA / NP extenders across 68 clinics delivering general "
            "medical dermatology, biologic-injectable programs (Dupixent "
            "at ~$60K/year WAC navigating specialty-pharmacy white-bagging "
            "and reduced in-office buy-and-bill margin), cryotherapy / AK "
            "destruction (CPT 17000 / 17003 / 17004), and integrated Mohs. "
            "Long 6-year hold rolled up 42 single-shingle practices on the "
            "U.S. Dermatology Partners / Epiphany Dermatology / Forefront "
            "Dermatology aggregation thesis, built a dermpath in-house lab "
            "capturing 88305 professional-component margin, grew aesthetic "
            "attach-rate in a subset of clinics, and exited to a strategic "
            "derm consolidator at 3.4x MOIC."
        ),
    },
    {
        "company_name": "Summit Mohs & Skin Cancer Center",
        "sector": "Mohs / Skin Cancer",
        "buyer": "Audax Private Equity",
        "year": 2020,
        "region": "Southwest",
        "ev_mm": 165.0,
        "ev_ebitda": 12.5,
        "ebitda_mm": 36.30,
        "ebitda_margin": 0.22,
        "revenue_mm": 165.00,
        "hold_years": 4.5,
        "moic": 2.3,
        "irr": 0.2046,
        "status": "Active",
        "payer_mix": {"commercial": 0.52, "medicare": 0.32, "medicaid": 0.08, "self_pay": 0.08},
        "comm_pct": 0.52,
        "deal_narrative": (
            "Southwest Mohs micrographic surgery platform with 22 ACMS "
            "fellowship-trained Mohs surgeons across 14 clinics serving "
            "the Texas / Arizona / New Mexico sun-damaged cohort. Core "
            "service is Mohs surgery (CPT 17311-17315) with downstream "
            "complex closure / flap / FTSG reconstruction captured same-"
            "day under -59 / XS modifier. Mid-hold navigates MAC LCD "
            "scrutiny on AAD / ACMS / ASDS / ASMS AUC documentation "
            "(2012 Appropriate Use Criteria) for non-head/neck low-risk "
            "tumor indications, grows surgical-dermatology throughput, "
            "layers in dermpath co-located service (88305, IHC 88342 / "
            "88341 / 88344), and is preparing for a sale to a regional "
            "derm MSO at mid-teens multiple."
        ),
    },
    {
        "company_name": "Harborview Aesthetic Partners",
        "sector": "Aesthetic / Medi-Spa",
        "buyer": "TSG Consumer Partners",
        "year": 2021,
        "region": "Northeast",
        "ev_mm": 285.0,
        "ev_ebitda": 15.5,
        "ebitda_mm": 79.80,
        "ebitda_margin": 0.28,
        "revenue_mm": 285.00,
        "hold_years": 3.5,
        "moic": 1.8,
        "irr": 0.1795,
        "status": "Active",
        "payer_mix": {"commercial": 0.52, "medicare": 0.16, "medicaid": 0.02, "self_pay": 0.30},
        "comm_pct": 0.52,
        "deal_narrative": (
            "Northeast aesthetic / medi-spa platform with 32 locations "
            "acquired at peak 2021 aesthetic multiples on the Ever/Body / "
            "SkinSpirit urban medi-spa playbook. Service mix centered on "
            "Botox ($10-15/unit retail), HA fillers (Juvederm / Restylane / "
            "RHA at $550-850/syringe), laser hair removal (cash-pay "
            "$200-400/treatment, 6-treatment packaged), laser resurfacing "
            "(Fraxel, IPL / BBL, CO2), CoolSculpting, Emsculpt, and "
            "medical-grade skincare retail. Mid-hold faces post-2022 "
            "aesthetic spending softness on middle-income consumer "
            "pullback, CPOM compliance work on MD-supervision of laser "
            "service lines, and competitive pressure from national "
            "aesthetic chains. Sponsor targeting a 2.2-2.5x realization "
            "at compressed exit multiple."
        ),
    },
    {
        "company_name": "Pineforest Pediatric Dermatology",
        "sector": "Pediatric Dermatology",
        "buyer": "Linden Capital Partners",
        "year": 2019,
        "region": "Midwest",
        "ev_mm": 85.0,
        "ev_ebitda": 11.0,
        "ebitda_mm": 17.85,
        "ebitda_margin": 0.21,
        "revenue_mm": 85.00,
        "hold_years": 5.0,
        "moic": 2.2,
        "irr": 0.1720,
        "status": "Realized",
        "payer_mix": {"commercial": 0.68, "medicare": 0.04, "medicaid": 0.20, "self_pay": 0.08},
        "comm_pct": 0.68,
        "deal_narrative": (
            "Midwest pediatric dermatology subspecialty platform with 14 "
            "fellowship-trained pediatric dermatologists across 12 "
            "academic-affiliated clinics delivering atopic dermatitis / "
            "eczema management (Dupixent pediatric, crisaborole / Eucrisa, "
            "ruxolitinib / Opzelura topical JAK inhibitor), infantile "
            "hemangioma management (oral propranolol per 2008 Leaute-"
            "Labreze protocol), molluscum contagiosum / wart destruction "
            "(CPT 17110 / 17111), port-wine stain and capillary "
            "malformation pulsed-dye-laser (PDL) treatment, and genetic "
            "skin disorders (ichthyosis, epidermolysis bullosa). Long "
            "hold captured biologic AD growth driven by pediatric "
            "Dupixent FDA age-expansion (to 6 months in 2022), grew "
            "multistate referral footprint, and exited to an academic "
            "pediatric multi-specialty platform at 2.2x MOIC."
        ),
    },
    {
        "company_name": "Elmwood Dermatopathology Labs",
        "sector": "Dermatopathology",
        "buyer": "Sterling Partners",
        "year": 2018,
        "region": "National",
        "ev_mm": 215.0,
        "ev_ebitda": 12.0,
        "ebitda_mm": 53.75,
        "ebitda_margin": 0.25,
        "revenue_mm": 215.00,
        "hold_years": 5.5,
        "moic": 2.6,
        "irr": 0.1912,
        "status": "Realized",
        "payer_mix": {"commercial": 0.58, "medicare": 0.30, "medicaid": 0.06, "self_pay": 0.06},
        "comm_pct": 0.58,
        "deal_narrative": (
            "National dermatopathology lab platform with 28 dermpath-"
            "boarded pathologists delivering histopathology readouts on "
            "shave / punch biopsy specimens (CPT 88305 Level IV surgical "
            "pathology), melanoma / melanocytic lesion diagnosis "
            "(including DecisionDx-Melanoma / MelanomaDx molecular "
            "ancillary-testing workflow), immunohistochemistry staining "
            "(88342 first stain, 88341 additional, 88344 multiplex), and "
            "direct immunofluorescence on bullous / connective tissue "
            "disease biopsies. Long hold consolidated the fragmented "
            "dermpath lab subsector at the intersection of dermatology "
            "MSOs (U.S. Dermatology Partners, ADCS, Forefront) and "
            "pathology lab roll-ups (Aurora Diagnostics / Sonic, Inform / "
            "Miraca, PathGroup), tightened 88305 utilization and medical-"
            "necessity documentation, and exited to a strategic pathology "
            "consolidator at 2.6x MOIC."
        ),
    },
    {
        "company_name": "Coastline Derm & Aesthetics",
        "sector": "Medical Dermatology",
        "buyer": "OMERS Private Equity",
        "year": 2022,
        "region": "Southeast",
        "ev_mm": 365.0,
        "ev_ebitda": 16.5,
        "ebitda_mm": 69.35,
        "ebitda_margin": 0.19,
        "revenue_mm": 365.00,
        "hold_years": 3.0,
        "moic": 1.5,
        "irr": 0.1447,
        "status": "Active",
        "payer_mix": {"commercial": 0.58, "medicare": 0.22, "medicaid": 0.06, "self_pay": 0.14},
        "comm_pct": 0.58,
        "deal_narrative": (
            "Southeast combined medical dermatology and aesthetic platform "
            "with 48 dermatologists across 38 clinics acquired at peak "
            "2022 derm MSO multiples. Medical derm service lines deliver "
            "office visits, biologic injectables (Dupixent / Skyrizi / "
            "Cosentyx / Tremfya), cryotherapy AK destruction (CPT 17000 / "
            "17003 / 17004), and integrated Mohs. Aesthetic service lines "
            "deliver Botox, HA fillers, laser hair removal, and CoolSculpting. "
            "Early hold absorbing post-2022 multiple compression (from 18-"
            "20x peak down to 12-15x), white-bagging specialty-pharmacy "
            "erosion of in-office biologic buy-and-bill margin on Dupixent, "
            "and softer aesthetic cash-pay volume on middle-income consumer "
            "pullback. Sponsor navigating value-creation reset with de novo "
            "clinic openings and aesthetic service-line lift."
        ),
    },
    {
        "company_name": "Glacier Mohs Surgery Associates",
        "sector": "Mohs / Skin Cancer",
        "buyer": "Gryphon Investors",
        "year": 2017,
        "region": "West",
        "ev_mm": 145.0,
        "ev_ebitda": 11.5,
        "ebitda_mm": 31.90,
        "ebitda_margin": 0.22,
        "revenue_mm": 145.00,
        "hold_years": 6.5,
        "moic": 3.8,
        "irr": 0.2238,
        "status": "Realized",
        "payer_mix": {"commercial": 0.50, "medicare": 0.32, "medicaid": 0.08, "self_pay": 0.10},
        "comm_pct": 0.50,
        "deal_narrative": (
            "West Coast Mohs micrographic surgery platform acquired pre-"
            "roll-up at trough multiple with 16 ACMS fellowship-trained "
            "Mohs surgeons across 11 clinics. Long 6.5-year hold "
            "capitalized on scale in Mohs professional-fee economics "
            "(CPT 17311-17315 dual surgeon-pathologist structure), grew "
            "to 34 surgeons and 22 clinics, built integrated complex "
            "closure / adjacent-tissue-transfer / flap / STSG / FTSG "
            "reconstruction service line capturing downstream 14000 / "
            "15100 / 15200 series same-day billing under -59 / XS "
            "modifier, insourced dermpath 88305 readouts, and exited to "
            "a strategic derm MSO at 3.8x MOIC on the long-duration Mohs "
            "scarcity-value thesis before the 2022 aesthetic / derm "
            "multiple compression."
        ),
    },
    {
        "company_name": "Brightstar Medi-Spa Holdings",
        "sector": "Aesthetic / Medi-Spa",
        "buyer": "KKR",
        "year": 2019,
        "region": "National",
        "ev_mm": 545.0,
        "ev_ebitda": 14.5,
        "ebitda_mm": 152.60,
        "ebitda_margin": 0.28,
        "revenue_mm": 545.00,
        "hold_years": 5.0,
        "moic": 2.8,
        "irr": 0.2287,
        "status": "Realized",
        "payer_mix": {"commercial": 0.50, "medicare": 0.20, "medicaid": 0.02, "self_pay": 0.28},
        "comm_pct": 0.50,
        "deal_narrative": (
            "National aesthetic / medi-spa platform with 72 locations "
            "modeled on the LaserAway / Ideal Image national cash-pay "
            "aesthetic chain playbook. Core revenue from laser hair "
            "removal (cash-pay $200-400/treatment, 6-treatment packaged "
            "protocol with 60-70% gross margin post-laser-time and "
            "room / labor cost), Botox and HA fillers, CoolSculpting "
            "cryolipolysis, and Emsculpt body-contouring. Long hold "
            "standardized multi-state CPOM / MSO structure on MD-"
            "supervision of laser service lines, built a loyalty "
            "membership program driving repeat cash-pay visit frequency, "
            "grew average-revenue-per-member, and exited to a consumer-"
            "focused PE platform at 2.8x MOIC on aesthetic consumer-"
            "brand scale."
        ),
    },
    {
        "company_name": "Westbrook Dermatology MSO",
        "sector": "Medical Dermatology",
        "buyer": "WCAS (Welsh Carson)",
        "year": 2016,
        "region": "National",
        "ev_mm": 775.0,
        "ev_ebitda": 12.5,
        "ebitda_mm": 193.75,
        "ebitda_margin": 0.25,
        "revenue_mm": 775.00,
        "hold_years": 6.5,
        "moic": 3.5,
        "irr": 0.2086,
        "status": "Realized",
        "payer_mix": {"commercial": 0.58, "medicare": 0.28, "medicaid": 0.06, "self_pay": 0.08},
        "comm_pct": 0.58,
        "deal_narrative": (
            "National medical dermatology MSO acquired early in the 2015-"
            "2022 derm PE aggregation wave, scaled to 158 dermatologists "
            "and 48 PA / NP extenders across 112 clinics on the Epiphany "
            "Dermatology / U.S. Dermatology Partners / Forefront "
            "Dermatology playbook. Long 6.5-year hold rolled up 78 "
            "single-shingle derm practices, insourced dermpath lab "
            "capturing 88305 professional-component margin at scale, "
            "built integrated Mohs service line (CPT 17311-17315) across "
            "42 clinics, grew biologic-injectable volume (Dupixent / "
            "Skyrizi / Cosentyx / Tremfya) despite white-bagging "
            "specialty-pharmacy erosion, layered in aesthetic attach-"
            "rate at 28 premium-market clinics, and exited to a strategic "
            "derm consolidator at 3.5x MOIC before the 2022 multiple "
            "compression."
        ),
    },
    {
        "company_name": "Rosewood Pediatric Skin Center",
        "sector": "Pediatric Dermatology",
        "buyer": "Shore Capital Partners",
        "year": 2021,
        "region": "Northeast",
        "ev_mm": 55.0,
        "ev_ebitda": 10.5,
        "ebitda_mm": 10.45,
        "ebitda_margin": 0.19,
        "revenue_mm": 55.00,
        "hold_years": 3.5,
        "moic": 1.6,
        "irr": 0.1418,
        "status": "Active",
        "payer_mix": {"commercial": 0.66, "medicare": 0.04, "medicaid": 0.22, "self_pay": 0.08},
        "comm_pct": 0.66,
        "deal_narrative": (
            "Northeast pediatric dermatology subspecialty network with 8 "
            "fellowship-trained pediatric dermatologists across 6 academic-"
            "affiliated clinics delivering atopic dermatitis / eczema "
            "management (Dupixent FDA-approved to age 6 months post-2022, "
            "crisaborole, ruxolitinib / Opzelura topical JAK), infantile "
            "hemangioma management (oral propranolol), molluscum / wart "
            "destruction (CPT 17110 / 17111), port-wine stain pulsed-dye-"
            "laser treatment, and genetic skin disorder longitudinal care "
            "(ichthyosis, epidermolysis bullosa on Filsuvez / Vyjuvek "
            "2023-2024 FDA-approved EB therapies). Mid-hold grows "
            "subspecialty referral share from pediatric primary care, "
            "navigates state Medicaid pediatric biologic PA workflow, "
            "and sponsor targeting tuck-in add-ons ahead of sale to a "
            "regional pediatric multi-specialty platform."
        ),
    },
    {
        "company_name": "Ironridge Dermpath Diagnostics",
        "sector": "Dermatopathology",
        "buyer": "Riverside Company",
        "year": 2020,
        "region": "Mid-Atlantic",
        "ev_mm": 125.0,
        "ev_ebitda": 11.5,
        "ebitda_mm": 32.50,
        "ebitda_margin": 0.26,
        "revenue_mm": 125.00,
        "hold_years": 4.5,
        "moic": 2.1,
        "irr": 0.1794,
        "status": "Active",
        "payer_mix": {"commercial": 0.56, "medicare": 0.30, "medicaid": 0.08, "self_pay": 0.06},
        "comm_pct": 0.56,
        "deal_narrative": (
            "Mid-Atlantic dermatopathology lab with 14 dermpath-boarded "
            "pathologists delivering histopathology readouts on shave / "
            "punch biopsy specimens (CPT 88305 Level IV surgical "
            "pathology, the bread-and-butter derm biopsy code), "
            "melanocytic lesion diagnosis (including DecisionDx-Melanoma "
            "molecular prognostic ancillary-testing workflow for "
            "ambiguous melanocytic lesions), IHC staining (88342 / 88341 / "
            "88344), and direct immunofluorescence. Mid-hold grows lab "
            "partnership footprint with regional derm MSOs on the dermpath "
            "insourcing / vertical-integration trend, manages 88305 "
            "utilization audits and medical-necessity documentation, "
            "competes against national consolidators (Aurora / Sonic, "
            "Inform / Miraca, PathGroup), and is preparing for a sale "
            "to a derm-MSO vertical-integration buyer."
        ),
    },
    {
        "company_name": "Starling Aesthetic Collective",
        "sector": "Aesthetic / Medi-Spa",
        "buyer": "Leonard Green & Partners",
        "year": 2023,
        "region": "West",
        "ev_mm": 385.0,
        "ev_ebitda": 17.5,
        "ebitda_mm": 69.30,
        "ebitda_margin": 0.18,
        "revenue_mm": 385.00,
        "hold_years": 2.5,
        "moic": 1.4,
        "irr": 0.1500,
        "status": "Active",
        "payer_mix": {"commercial": 0.50, "medicare": 0.18, "medicaid": 0.02, "self_pay": 0.30},
        "comm_pct": 0.50,
        "deal_narrative": (
            "West Coast premium aesthetic / medi-spa collective with 28 "
            "urban-upscale locations acquired at peak 2023 aesthetic "
            "multiples on the SkinSpirit / Ever/Body premium-brand "
            "playbook. Service mix concentrated on Botox ($10-15/unit "
            "retail cash-pay), HA fillers (Juvederm / Restylane / RHA "
            "at $550-850/syringe), Daxxify long-acting neuromodulator, "
            "laser hair removal, Fraxel / IPL / BBL resurfacing, Sofwave "
            "/ Ultherapy ultrasound tightening, and medical-grade "
            "skincare retail (ZO, SkinMedica, SkinCeuticals). Early hold "
            "navigates soft 2024 discretionary-aesthetic-spend environment "
            "on middle-income consumer pullback, state-by-state CPOM / "
            "MSO compliance on laser and injection MD-supervision "
            "requirements, competitive pressure from GLP-1 weight-loss "
            "adjacent aesthetic services, and sponsor pursuing value "
            "creation via membership-model expansion and medical-grade "
            "skincare retail attach-rate lift."
        ),
    },
]
