"""Extended seed 93: MSK / chiropractic / pain management / spine PE deals.

This module contains a curated set of 15 healthcare private equity deal
records focused on the musculoskeletal (MSK) / chiropractic / pain
management / spine subsector. The theme covers:

- Chiropractic network operators delivering spinal manipulation
  therapy (CPT 98940 / 98941 / 98942), therapeutic exercise (97110),
  manual therapy (97140), and DME bracing to workers-compensation,
  commercial, and cash-pay patient populations, navigating payer
  visit-limit and MUE (Medically Unlikely Edit) caps on chiropractic
  CMT codes
- Pain management physician platforms delivering interventional
  procedures including epidural steroid injections (ESIs), facet
  joint injections, medial branch blocks, radiofrequency ablation
  (RFA), spinal cord stimulator (SCS) implants, percutaneous
  cryoneurolysis, and integrated opioid-tapering behavioral health
  under SUPPORT Act alignment and CDC opioid prescribing guideline
  constraints
- Spine care centers delivering minimally invasive spine surgery
  (MISS), ASC-based lumbar decompression, cervical fusion,
  percutaneous image-guided injections on CPT 62321 / 62322 / 62323
  (interstitial catheter PCI epidural injections under CMS 2017
  bundled imaging policy), and BPCI Advanced bundled-payment
  participation for DRG 459 / 460 spinal fusion episodes
- MSK platforms integrating orthopedics, physical therapy,
  chiropractic, and pain management under a single MSO, capturing
  the ortho DRG consolidation thesis where CMS finalized the 2024
  reduction in spinal fusion DRGs and hospital outpatient spine
  migration under the CMS Inpatient-Only (IPO) list removal of
  lumbar fusion (2021) subsequently partially reversed
- Interventional pain ASC operators delivering floor-based fluoro /
  C-arm procedures under the CMS ASC fee schedule, capturing the
  HOPPS / ASC site-of-service differential on high-volume
  interventional codes (62321-62323, 64483/64484 transforaminal
  ESI, 64635 RFA) as payers steer workers-comp and commercial
  volume away from HOPPS

MSK / pain / spine economics are distinguished by a workers-
compensation-heavy payer mix layered on top of commercial
preferred-provider networks, with workers-comp fee schedules
typically 110-130% of Medicare on interventional procedures and
providing fast-pay cash flow benefits that PE sponsors target as
a margin lever. Commercial payers in the 42-62% range reflect
employer-direct-contracting opportunities especially in MSK
bundled-episode arrangements (e.g., Vori Health, Hinge Health
competitors). Medicare (18-32%) concentrates on RFA, SCS implant,
and vertebral augmentation. The subsector faces regulatory
headwinds from: (a) the SUPPORT for Patients and Communities Act
of 2018 and CDC 2016 / 2022 opioid prescribing guidelines
constraining chronic opioid management revenue and driving
platform pivots to interventional and non-opioid alternatives;
(b) MUE limits on chiropractic CMT CPT 98940-98942 capping per-
visit billing and commercial payer visit-cap policies (12-24
visits/year typical); (c) CMS 2017 bundled imaging policy folding
fluoroscopic guidance into CPT 62321 / 62322 / 62323 (formerly
62310-62319) reducing per-procedure revenue; (d) commercial payer
prior-auth expansion on ESIs, RFA, and SCS implants; and (e) CMS
BPCI Advanced bundled-payment pressure on DRG 459 / 460 spinal
fusion episodes and the 2024 DRG consolidation reducing spine
inpatient margins. Value creation in PE-backed MSK platforms
centers on workers-comp payer mix optimization, interventional
procedure volume growth offsetting chiropractic visit caps,
ASC migration capturing facility-fee revenue on MISS and
interventional pain, opioid-tapering program deployment under
SUPPORT Act funding streams, and roll-up of independent single-
shingle pain and chiro practices into regional MSO platforms
modeled on National Spine & Pain Centers (SCP / KKR),
HOPCo (Sterling Partners), U.S. Physical Therapy, and Select
Medical's concentra-adjacent MSK pilots. Each record captures
deal economics (EV, EV/EBITDA, margins), return profile (MOIC,
IRR, hold period), payer mix, regional footprint, sponsor,
realization status, and a short deal narrative. These records
are synthesized for modeling, backtesting, and scenario analysis
use cases.
"""

EXTENDED_SEED_DEALS_93 = [
    {
        "company_name": "Meridian Chiropractic Network",
        "sector": "Chiropractic Network",
        "buyer": "Shore Capital Partners",
        "year": 2019,
        "region": "Midwest",
        "ev_mm": 185.0,
        "ev_ebitda": 12.0,
        "ebitda_mm": 37.00,
        "ebitda_margin": 0.22,
        "revenue_mm": 168.18,
        "hold_years": 5.0,
        "moic": 2.6,
        "irr": 0.2108,
        "status": "Realized",
        "payer_mix": {"commercial": 0.52, "medicare": 0.22, "medicaid": 0.06, "self_pay": 0.20},
        "comm_pct": 0.52,
        "deal_narrative": (
            "Midwest chiropractic network with 72 clinics delivering "
            "spinal manipulation therapy (CPT 98940 / 98941 / 98942), "
            "therapeutic exercise (97110), and manual therapy (97140) to "
            "a payer mix skewing toward workers-compensation (embedded in "
            "the self-pay / cash bucket at ~14% of revenue on state WC "
            "fee schedules), commercial PPO, and cash-pay maintenance "
            "patients. Long hold navigated MUE limits capping per-visit "
            "CMT code billing, commercial payer visit-cap policies "
            "(typical 12-24 visits/year), rolled up 38 independent single-"
            "shingle DC practices, deployed a workers-comp case-management "
            "intake team to accelerate state WC board authorization, and "
            "exited to a strategic MSK platform at 2.6x MOIC."
        ),
    },
    {
        "company_name": "Ridgeline Pain Physicians",
        "sector": "Pain Management",
        "buyer": "Webster Equity Partners",
        "year": 2018,
        "region": "Southeast",
        "ev_mm": 345.0,
        "ev_ebitda": 13.5,
        "ebitda_mm": 72.45,
        "ebitda_margin": 0.24,
        "revenue_mm": 301.88,
        "hold_years": 5.5,
        "moic": 3.0,
        "irr": 0.2184,
        "status": "Realized",
        "payer_mix": {"commercial": 0.50, "medicare": 0.28, "medicaid": 0.08, "self_pay": 0.14},
        "comm_pct": 0.50,
        "deal_narrative": (
            "Southeast pain management platform with 45 interventional "
            "pain physicians delivering epidural steroid injections (CPT "
            "62321 / 62322 / 62323 for cervical / thoracic / lumbar "
            "interstitial catheter PCI epidural injections under the CMS "
            "2017 bundled-imaging revision), facet and medial branch "
            "blocks, radiofrequency ablation (RFA, CPT 64635 / 64636), "
            "and spinal cord stimulator trials / implants. Long hold "
            "pivoted from opioid-heavy chronic pain management to "
            "interventional and integrated behavioral health opioid-"
            "tapering programs aligned with the SUPPORT Act of 2018 and "
            "CDC 2016 / 2022 prescribing guidelines, captured workers-"
            "comp fee schedule premium (~110-130% of Medicare), and "
            "exited to a national pain consolidator at 3.0x MOIC."
        ),
    },
    {
        "company_name": "Coastal Spine Care Institute",
        "sector": "Spine Care",
        "buyer": "Audax Private Equity",
        "year": 2017,
        "region": "West",
        "ev_mm": 625.0,
        "ev_ebitda": 14.0,
        "ebitda_mm": 162.50,
        "ebitda_margin": 0.26,
        "revenue_mm": 625.00,
        "hold_years": 6.0,
        "moic": 3.4,
        "irr": 0.2264,
        "status": "Realized",
        "payer_mix": {"commercial": 0.55, "medicare": 0.24, "medicaid": 0.07, "self_pay": 0.14},
        "comm_pct": 0.55,
        "deal_narrative": (
            "West Coast comprehensive spine care institute combining "
            "neurosurgical and orthopedic spine surgeons, interventional "
            "pain physicians, and MISS (minimally invasive spine surgery) "
            "capability across four owned ASCs and two HOPD partnerships. "
            "Long hold captured the CMS 2021 Inpatient-Only (IPO) list "
            "removal of lumbar fusion (partially reversed in 2022) "
            "migrating appropriate spine cases to ASC / HOPD, participated "
            "in BPCI Advanced bundled-payment on DRG 459 / 460 spinal "
            "fusion episodes, absorbed the 2024 CMS ortho DRG consolidation "
            "reducing inpatient spine margins, and exited to a strategic "
            "neurosurgical platform at 3.4x MOIC on ASC scarcity value."
        ),
    },
    {
        "company_name": "Alpine MSK Partners",
        "sector": "MSK Platform",
        "buyer": "Welsh Carson Anderson & Stowe",
        "year": 2020,
        "region": "National",
        "ev_mm": 825.0,
        "ev_ebitda": 15.5,
        "ebitda_mm": 181.50,
        "ebitda_margin": 0.22,
        "revenue_mm": 825.00,
        "hold_years": 4.5,
        "moic": 2.3,
        "irr": 0.2044,
        "status": "Active",
        "payer_mix": {"commercial": 0.58, "medicare": 0.22, "medicaid": 0.06, "self_pay": 0.14},
        "comm_pct": 0.58,
        "deal_narrative": (
            "National MSK aggregation platform integrating orthopedics, "
            "physical therapy, chiropractic, and interventional pain under "
            "a unified MSO across 9 states. Mid-hold strategy leverages "
            "the ortho DRG consolidation tailwind (CMS 2024 reduced spinal "
            "fusion DRGs pressuring hospital spine economics and driving "
            "physician-owned ASC migration), expands workers-compensation "
            "direct-to-employer contracting (workers-comp fee schedules "
            "~110-130% of Medicare), deploys a SUPPORT Act-aligned "
            "opioid-tapering program across pain clinics, and participates "
            "in BPCI Advanced bundled-payment episodes on MSK DRGs to "
            "capture downside-protected episode margin."
        ),
    },
    {
        "company_name": "Summit Interventional Pain ASC",
        "sector": "Interventional Pain",
        "buyer": "Linden Capital Partners",
        "year": 2019,
        "region": "Southeast",
        "ev_mm": 215.0,
        "ev_ebitda": 13.0,
        "ebitda_mm": 53.75,
        "ebitda_margin": 0.25,
        "revenue_mm": 215.00,
        "hold_years": 5.0,
        "moic": 2.7,
        "irr": 0.2196,
        "status": "Realized",
        "payer_mix": {"commercial": 0.54, "medicare": 0.26, "medicaid": 0.06, "self_pay": 0.14},
        "comm_pct": 0.54,
        "deal_narrative": (
            "Southeast interventional pain ASC operator with 9 "
            "freestanding C-arm fluoro centers delivering high-volume "
            "PCI epidural injections (CPT 62321 / 62322 / 62323 under "
            "the CMS 2017 bundled-imaging policy folding fluoroscopy "
            "into the base code), transforaminal ESIs (64483 / 64484), "
            "RFA (64635 / 64636), and SCS trials. Long hold captured "
            "the HOPPS / ASC site-of-service differential as commercial "
            "and workers-comp payers steered volume to freestanding "
            "ASC, absorbed CMS annual APC / ASC rate recalibrations, "
            "managed commercial payer prior-auth expansion on ESIs, "
            "and exited to a strategic pain platform at 2.7x MOIC."
        ),
    },
    {
        "company_name": "Harborpoint Chiropractic Group",
        "sector": "Chiropractic Network",
        "buyer": "NexPhase Capital",
        "year": 2021,
        "region": "Northeast",
        "ev_mm": 95.0,
        "ev_ebitda": 11.0,
        "ebitda_mm": 17.10,
        "ebitda_margin": 0.18,
        "revenue_mm": 95.00,
        "hold_years": 3.5,
        "moic": 1.6,
        "irr": 0.1418,
        "status": "Active",
        "payer_mix": {"commercial": 0.48, "medicare": 0.20, "medicaid": 0.10, "self_pay": 0.22},
        "comm_pct": 0.48,
        "deal_narrative": (
            "Northeast chiropractic group with 38 clinics facing "
            "commercial payer visit-cap tightening (several regional BCBS "
            "plans tightened CMT annual visit limits to 15-18/year) and "
            "MUE limits on 98940-98942 CMT code billing. Mid-hold pivot "
            "layers in ancillary therapeutic exercise (97110), manual "
            "therapy (97140), DME spinal bracing revenue, and integrated "
            "PT-chiro co-located clinics to diversify beyond CMT caps. "
            "Workers-comp (~16% of revenue within the self-pay bucket) "
            "provides fee schedule premium cash flow; sponsor is evaluating "
            "a sale to a strategic MSK platform versus a tuck-in acquirer."
        ),
    },
    {
        "company_name": "Pinecrest Spine Institute",
        "sector": "Spine Care",
        "buyer": "Apollo Global Management",
        "year": 2018,
        "region": "National",
        "ev_mm": 745.0,
        "ev_ebitda": 14.5,
        "ebitda_mm": 178.80,
        "ebitda_margin": 0.27,
        "revenue_mm": 662.22,
        "hold_years": 5.5,
        "moic": 2.9,
        "irr": 0.2134,
        "status": "Realized",
        "payer_mix": {"commercial": 0.56, "medicare": 0.24, "medicaid": 0.06, "self_pay": 0.14},
        "comm_pct": 0.56,
        "deal_narrative": (
            "National spine care platform with 72 spine surgeons (mixed "
            "ortho and neurosurgery), 14 ASCs credentialed for MISS lumbar "
            "decompression and cervical disc arthroplasty, and integrated "
            "interventional pain service lines. Long hold captured BPCI "
            "Advanced bundled-payment episode margin on DRG 459 / 460 "
            "spine fusion, migrated appropriate cases to ASC under the "
            "CMS 2021 IPO list revision (lumbar fusion removal), absorbed "
            "the subsequent partial reversal, managed workers-comp case "
            "mix at ~18% of revenue on premium WC fee schedules, and "
            "exited to a strategic neurosurgery-focused consolidator at "
            "2.9x MOIC."
        ),
    },
    {
        "company_name": "Laurelwood Pain & Spine",
        "sector": "Pain Management",
        "buyer": "Kohlberg & Company",
        "year": 2016,
        "region": "Mid-Atlantic",
        "ev_mm": 285.0,
        "ev_ebitda": 11.5,
        "ebitda_mm": 65.55,
        "ebitda_margin": 0.23,
        "revenue_mm": 285.00,
        "hold_years": 6.5,
        "moic": 3.8,
        "irr": 0.2243,
        "status": "Realized",
        "payer_mix": {"commercial": 0.46, "medicare": 0.30, "medicaid": 0.08, "self_pay": 0.16},
        "comm_pct": 0.46,
        "deal_narrative": (
            "Mid-Atlantic pain management platform acquired pre-SUPPORT "
            "Act with meaningful chronic opioid management revenue. Long "
            "6.5-year hold executed a structural pivot from opioid-heavy "
            "chronic pain to interventional procedures (CPT 62321-62323 "
            "PCI epidural injections, 64483/64484 transforaminal ESI, "
            "64635 RFA) under SUPPORT Act 2018 alignment and CDC 2016 / "
            "2022 opioid prescribing guideline constraints, deployed "
            "integrated behavioral-health opioid-tapering programs, added "
            "SCS implant volume on Medicare fee schedule premium, and "
            "exited to a strategic pain consolidator at 3.8x MOIC on the "
            "completed regulatory transition."
        ),
    },
    {
        "company_name": "Bayridge Chiropractic Partners",
        "sector": "Chiropractic Network",
        "buyer": "Riverside Company",
        "year": 2022,
        "region": "West",
        "ev_mm": 135.0,
        "ev_ebitda": 13.5,
        "ebitda_mm": 22.95,
        "ebitda_margin": 0.17,
        "revenue_mm": 135.00,
        "hold_years": 3.0,
        "moic": 1.5,
        "irr": 0.1447,
        "status": "Active",
        "payer_mix": {"commercial": 0.50, "medicare": 0.20, "medicaid": 0.08, "self_pay": 0.22},
        "comm_pct": 0.50,
        "deal_narrative": (
            "West Coast chiropractic network with 55 clinics acquired "
            "post-COVID at the top of the MSK multiple cycle. Early hold "
            "navigates commercial payer MUE enforcement on CMT CPT "
            "98940-98942, visit-cap tightening, and state workers-comp "
            "fee schedule resets. Workers-comp revenue (~15% within the "
            "self-pay cash bucket) remains a margin anchor on premium WC "
            "fee schedules. Value creation hinges on deploying a PT co-"
            "location model, DME spinal bracing attach-rate lift, and "
            "participating in employer-direct MSK bundled-episode pilots "
            "ahead of a sale to a strategic MSK or ortho aggregator."
        ),
    },
    {
        "company_name": "Foxhollow Interventional Pain",
        "sector": "Interventional Pain",
        "buyer": "FFL Partners",
        "year": 2020,
        "region": "Southwest",
        "ev_mm": 265.0,
        "ev_ebitda": 14.0,
        "ebitda_mm": 66.25,
        "ebitda_margin": 0.25,
        "revenue_mm": 265.00,
        "hold_years": 4.5,
        "moic": 2.2,
        "irr": 0.1917,
        "status": "Active",
        "payer_mix": {"commercial": 0.52, "medicare": 0.28, "medicaid": 0.06, "self_pay": 0.14},
        "comm_pct": 0.52,
        "deal_narrative": (
            "Southwest interventional pain ASC platform with 7 C-arm-"
            "equipped centers delivering PCI epidural injections (CPT "
            "62321-62323 under CMS 2017 bundled-imaging), transforaminal "
            "ESIs, facet and medial branch blocks, RFA (CPT 64635 / 64636), "
            "and ambulatory SCS trials. Mid-hold captures workers-comp "
            "fee schedule premium (~110-130% of Medicare), navigates "
            "commercial payer prior-auth expansion on ESIs and RFA "
            "(particularly UnitedHealthcare and Anthem 2023 policy "
            "tightening), integrates a SUPPORT Act opioid-tapering "
            "behavioral-health referral network, and prepares for an exit "
            "to a national pain platform."
        ),
    },
    {
        "company_name": "Crestwood MSK Holdings",
        "sector": "MSK Platform",
        "buyer": "KKR",
        "year": 2019,
        "region": "National",
        "ev_mm": 555.0,
        "ev_ebitda": 14.5,
        "ebitda_mm": 122.10,
        "ebitda_margin": 0.22,
        "revenue_mm": 555.00,
        "hold_years": 5.0,
        "moic": 2.5,
        "irr": 0.2011,
        "status": "Realized",
        "payer_mix": {"commercial": 0.56, "medicare": 0.22, "medicaid": 0.06, "self_pay": 0.16},
        "comm_pct": 0.56,
        "deal_narrative": (
            "National MSK platform modeled on National Spine & Pain "
            "Centers with 110 pain physicians, 22 chiropractors, 48 PT "
            "clinics, and 6 owned ASCs for interventional pain and MISS. "
            "Long hold layered workers-compensation direct-contracting "
            "(~18% of revenue blended into commercial and self-pay buckets "
            "on WC fee schedule premium), captured ortho DRG consolidation "
            "migration of BPCI Advanced spine bundles to ASC, deployed "
            "SUPPORT Act opioid-tapering behavioral health across the "
            "pain footprint, and exited to a strategic MSK consolidator "
            "at 2.5x MOIC."
        ),
    },
    {
        "company_name": "Trillium Spine Surgery Centers",
        "sector": "Spine Care",
        "buyer": "Gryphon Investors",
        "year": 2021,
        "region": "Southeast",
        "ev_mm": 425.0,
        "ev_ebitda": 15.0,
        "ebitda_mm": 97.75,
        "ebitda_margin": 0.23,
        "revenue_mm": 425.00,
        "hold_years": 3.5,
        "moic": 1.7,
        "irr": 0.1594,
        "status": "Active",
        "payer_mix": {"commercial": 0.58, "medicare": 0.22, "medicaid": 0.06, "self_pay": 0.14},
        "comm_pct": 0.58,
        "deal_narrative": (
            "Southeast spine surgery ASC network with 8 centers "
            "credentialed for MISS lumbar decompression, ACDF, and "
            "cervical disc arthroplasty, anchored by physician-owner "
            "neurosurgeons and ortho spine surgeons. Mid-hold navigates "
            "the post-2022 CMS partial reversal of lumbar fusion IPO "
            "removal (restricting ASC-eligibility on certain lumbar "
            "fusion CPT codes), participates in BPCI Advanced on "
            "remaining eligible DRG 459 / 460 episodes, absorbs the "
            "2024 ortho DRG consolidation, and captures workers-comp "
            "surgical case mix at ~16% on premium WC fee schedules. "
            "Sponsor targeting an exit at 2.3-2.5x MOIC on ASC scarcity."
        ),
    },
    {
        "company_name": "Northgate Pain & Rehabilitation",
        "sector": "Pain Management",
        "buyer": "Sterling Partners",
        "year": 2018,
        "region": "Midwest",
        "ev_mm": 175.0,
        "ev_ebitda": 12.5,
        "ebitda_mm": 40.25,
        "ebitda_margin": 0.23,
        "revenue_mm": 175.00,
        "hold_years": 5.5,
        "moic": 2.8,
        "irr": 0.2091,
        "status": "Realized",
        "payer_mix": {"commercial": 0.44, "medicare": 0.32, "medicaid": 0.08, "self_pay": 0.16},
        "comm_pct": 0.44,
        "deal_narrative": (
            "Midwest pain management and rehabilitation platform "
            "delivering a balanced mix of interventional procedures (PCI "
            "epidural injections CPT 62321-62323, RFA 64635, SCS), "
            "multidisciplinary chronic pain management, and integrated "
            "SUPPORT Act-aligned opioid-tapering behavioral health "
            "programs in partnership with regional MAT (medication-"
            "assisted treatment) providers. Long hold managed workers-"
            "comp case mix (~16% of revenue), navigated CDC 2016 / 2022 "
            "opioid prescribing guideline transitions, and exited to a "
            "strategic MSK platform at 2.8x MOIC."
        ),
    },
    {
        "company_name": "Evergreen Chiropractic & Wellness",
        "sector": "Chiropractic Network",
        "buyer": "Thomas H. Lee Partners",
        "year": 2023,
        "region": "National",
        "ev_mm": 205.0,
        "ev_ebitda": 16.0,
        "ebitda_mm": 32.80,
        "ebitda_margin": 0.16,
        "revenue_mm": 205.00,
        "hold_years": 2.5,
        "moic": 1.4,
        "irr": 0.1479,
        "status": "Active",
        "payer_mix": {"commercial": 0.42, "medicare": 0.18, "medicaid": 0.10, "self_pay": 0.30},
        "comm_pct": 0.42,
        "deal_narrative": (
            "National chiropractic network acquired at peak 2023 MSK "
            "multiples with a heavy cash-pay and workers-compensation "
            "mix (workers-comp embedded within the elevated self-pay "
            "bucket at ~20% of revenue). Early hold faces commercial "
            "payer MUE enforcement on CMT CPT 98940-98942, visit-cap "
            "tightening, and the DOL 2024 workers-comp fee schedule "
            "updates in key states. Value creation leans on cash-pay "
            "maintenance program marketing, DME spinal bracing attach-"
            "rates, and a PT co-location pilot. Sponsor monitoring "
            "direct-to-employer MSK bundled-episode pilots as a potential "
            "revenue expansion lever."
        ),
    },
    {
        "company_name": "Kingsbridge Interventional Spine",
        "sector": "Interventional Pain",
        "buyer": "Leonard Green & Partners",
        "year": 2022,
        "region": "National",
        "ev_mm": 495.0,
        "ev_ebitda": 17.5,
        "ebitda_mm": 108.90,
        "ebitda_margin": 0.22,
        "revenue_mm": 495.00,
        "hold_years": 3.0,
        "moic": 1.8,
        "irr": 0.2164,
        "status": "Active",
        "payer_mix": {"commercial": 0.60, "medicare": 0.22, "medicaid": 0.06, "self_pay": 0.12},
        "comm_pct": 0.60,
        "deal_narrative": (
            "National interventional spine and pain platform with 38 "
            "physician-owned ASCs delivering high-acuity PCI epidural "
            "injections (CPT 62321 / 62322 / 62323 under CMS 2017 "
            "bundled-imaging), RFA (CPT 64635 / 64636), SCS implants, "
            "vertebral augmentation (kyphoplasty 22513 / 22514), and "
            "MISS lumbar decompression. Early hold captures HOPPS / ASC "
            "site-of-service differential as commercial and workers-comp "
            "payers steer interventional volume to freestanding ASC, "
            "navigates commercial payer prior-auth tightening on ESIs "
            "and RFA, deploys SUPPORT Act-aligned opioid-tapering "
            "behavioral health referrals, and participates in BPCI "
            "Advanced bundled-payment episodes on eligible spine cases."
        ),
    },
]
