"""Extended seed 94: Podiatry / foot & ankle / diabetic-limb-preservation PE deals.

This module contains a curated set of 15 healthcare private equity deal
records focused on the podiatry / foot & ankle surgery / diabetic limb
preservation subsector. The theme covers:

- Podiatry practice networks delivering routine foot care, nail
  debridement (CPT 11720 / 11721), callus / corn paring (11055-11057),
  custom orthotics (HCPCS L3020 covered commercial, non-covered
  Medicare under the 1980 routine foot care statutory exclusion
  except when tied to Class A / B / C systemic conditions under
  CMS NCD 70.2.1), and DME diabetic footwear under the Therapeutic
  Shoe Bill (A5500 / A5501)
- Foot & ankle surgery platforms delivering bunion / hallux valgus
  correction, hammertoe repair, plantar fasciotomy, Lapidus
  procedures, ankle arthroscopy, and total ankle replacement (TAR)
  across physician-owned ASCs, navigating the CMS IPO-list migration
  of foot & ankle procedures and the HOPPS / ASC site-of-service
  differential
- Diabetic limb preservation programs delivering multidisciplinary
  wound clinics, diabetic foot ulcer (DFU) debridement (CPT 11042-
  11047 for subcutaneous / muscle / bone depth), Charcot arthropathy
  reconstruction (external fixation, midfoot arthrodesis), and
  integrated vascular / podiatry "toe-and-flow" model clinics
  targeting LEA (lower extremity amputation) avoidance and the
  15-20% 1-year mortality post-major-LEA literature
- Wound care and foot-specific wound platforms deploying cellular
  and tissue-based products (CTPs / skin substitutes under CMS
  2024-2025 LCD tightening), NPWT (negative-pressure wound
  therapy), hyperbaric oxygen therapy (HBOT for Wagner 3+ DFU
  under CMS NCD 20.29), and PAD (peripheral arterial disease) /
  angiosome-directed revascularization referral coordination
- Podiatric ASC operators with multi-specialty foot & ankle
  surgical suites capturing facility-fee revenue on bunionectomy,
  Lapidus, TAR, and Charcot reconstruction, and participating in
  BPCI Advanced bundled-payment episodes on major LEA (DRG 616-
  618) and amputation of lower limb episodes under the LEA
  avoidance thesis

Podiatry / foot & ankle / diabetic-limb-preservation economics are
distinguished by a Medicare-heavy payer mix (diabetic and elderly
patients concentrate Medicare and Medicare Advantage revenue,
typically 30-48%), a commercial block (30-52%) driven by bunion
and sports-medicine foot/ankle surgery, and Medicaid (8-18%)
reflecting the dual-eligible diabetic population. The subsector
faces specific regulatory and coverage constraints: (a) the 1980
Medicare routine foot care statutory exclusion (Section 1862(a)(13)
of the Social Security Act) excluding nail trimming, callus paring,
and "hygienic care" except when the patient has a qualifying Class
A / B / C systemic condition (e.g., diabetes with loss of protective
sensation, PVD, peripheral neuropathy) under CMS NCD 70.2.1 — the
"Q-modifier" documentation regime (Q7 / Q8 / Q9 class findings) is
a recurring audit-risk and revenue-integrity vulnerability in PE-
backed podiatry platforms; (b) custom orthotic coverage divergence
— HCPCS L3020 (full-length custom-fabricated shoe insert) typically
covered by commercial PPO and workers-comp but statutorily excluded
from Medicare (except under the Therapeutic Shoe Bill for diabetics
with A5500 / A5501 / A5512 / A5513 codes) — driving PE platforms
toward commercial-heavy markets for orthotic revenue capture;
(c) diabetic foot ulcer debridement CPT 11042-11047 subject to
MAC LCDs requiring documentation of wound depth, measurements,
and medical necessity, with recurring RAC audit focus on
debridement-frequency and depth-upcoding; (d) CMS 2024-2025 LCD
tightening on cellular/tissue products (skin substitutes) reducing
DFU wound care margins on products like Apligraf, Dermagraft,
Grafix, and amniotic membrane allografts — driving platform
wound-care economics; (e) BPCI Advanced bundled-payment episodes
on major lower-extremity amputation (DRG 616-618) creating an
LEA-avoidance economic incentive when platforms capture upstream
wound care and revascularization referral coordination; and
(f) CMS NCD 20.29 HBOT coverage for Wagner 3+ DFU requiring
documented failure of standard wound care for 30+ days. Value
creation in PE-backed podiatry platforms centers on commercial-
heavy orthotic revenue capture (L3020 at $400-600/pair commercial
vs. non-covered Medicare), DME therapeutic shoe attach-rates
under A5500 series (diabetic shoes covered 1 pair/year), ASC
migration of foot & ankle surgery capturing facility-fee revenue,
multidisciplinary "toe-and-flow" diabetic limb preservation
programs capturing PAD / angiosome-directed revascularization
referral share and LEA-avoidance BPCI bundle margin, and roll-up
of independent single-shingle DPM (Doctor of Podiatric Medicine)
practices into regional MSO platforms modeled on Upperline Health
(NEA / Frazier), Foot & Ankle Specialists of the Mid-Atlantic
(Gryphon), U.S. Foot & Ankle Specialists, and HOPCo-adjacent foot
& ankle pilots. Each record captures deal economics (EV, EV/EBITDA,
margins), return profile (MOIC, IRR, hold period), payer mix,
regional footprint, sponsor, realization status, and a short deal
narrative. These records are synthesized for modeling, backtesting,
and scenario analysis use cases.
"""

EXTENDED_SEED_DEALS_94 = [
    {
        "company_name": "Cardinal Podiatry Partners",
        "sector": "Podiatry Practice",
        "buyer": "Shore Capital Partners",
        "year": 2019,
        "region": "Southeast",
        "ev_mm": 185.0,
        "ev_ebitda": 12.0,
        "ebitda_mm": 37.00,
        "ebitda_margin": 0.20,
        "revenue_mm": 185.00,
        "hold_years": 5.0,
        "moic": 2.7,
        "irr": 0.2181,
        "status": "Realized",
        "payer_mix": {"commercial": 0.42, "medicare": 0.40, "medicaid": 0.10, "self_pay": 0.08},
        "comm_pct": 0.42,
        "deal_narrative": (
            "Southeast podiatry practice platform with 68 DPM providers "
            "across 42 clinics delivering routine foot care (nail "
            "debridement CPT 11720 / 11721, callus / corn paring 11055-"
            "11057 under the CMS NCD 70.2.1 Class A / B / C systemic-"
            "finding framework using Q7 / Q8 / Q9 modifiers to overcome "
            "the 1980 Medicare routine foot care statutory exclusion), "
            "custom orthotics (HCPCS L3020 covered commercial / workers-"
            "comp, non-covered standalone Medicare except via the "
            "Therapeutic Shoe Bill A5500 / A5501 series), and diabetic "
            "DME. Long hold rolled up 31 single-shingle DPM practices, "
            "tightened Q-modifier documentation in response to a CERT "
            "audit cycle, grew orthotic attach-rates in commercial markets, "
            "and exited to a strategic podiatry MSO at 2.7x MOIC."
        ),
    },
    {
        "company_name": "Ironwood Foot & Ankle Surgery",
        "sector": "Foot & Ankle Surgery",
        "buyer": "Gryphon Investors",
        "year": 2018,
        "region": "Mid-Atlantic",
        "ev_mm": 325.0,
        "ev_ebitda": 13.5,
        "ebitda_mm": 71.50,
        "ebitda_margin": 0.22,
        "revenue_mm": 325.00,
        "hold_years": 5.5,
        "moic": 3.1,
        "irr": 0.2254,
        "status": "Realized",
        "payer_mix": {"commercial": 0.50, "medicare": 0.34, "medicaid": 0.10, "self_pay": 0.06},
        "comm_pct": 0.50,
        "deal_narrative": (
            "Mid-Atlantic foot & ankle surgical platform with 54 foot & "
            "ankle surgeons (DPM and orthopedic F&A fellowship-trained) "
            "delivering bunion / hallux valgus correction, Lapidus "
            "procedures, hammertoe repair, plantar fasciotomy, ankle "
            "arthroscopy, and total ankle replacement (TAR) across 6 "
            "owned ASCs. Long hold captured CMS ASC-list expansion of "
            "foot & ankle procedures, migrated bunion / Lapidus / TAR "
            "volume from HOPD to physician-owned ASC capturing facility-"
            "fee differential, layered in Charcot arthropathy midfoot "
            "arthrodesis and external fixation reconstruction on diabetic "
            "limb preservation referrals, and exited to a strategic ortho "
            "platform at 3.1x MOIC on ASC scarcity value."
        ),
    },
    {
        "company_name": "Meridian Limb Preservation Alliance",
        "sector": "Diabetic Limb Preservation",
        "buyer": "Welsh Carson Anderson & Stowe",
        "year": 2020,
        "region": "National",
        "ev_mm": 585.0,
        "ev_ebitda": 15.0,
        "ebitda_mm": 128.70,
        "ebitda_margin": 0.22,
        "revenue_mm": 585.00,
        "hold_years": 4.5,
        "moic": 2.4,
        "irr": 0.2113,
        "status": "Active",
        "payer_mix": {"commercial": 0.32, "medicare": 0.46, "medicaid": 0.16, "self_pay": 0.06},
        "comm_pct": 0.32,
        "deal_narrative": (
            "National diabetic limb preservation platform operating 48 "
            "'toe-and-flow' multidisciplinary clinics integrating "
            "podiatry, vascular surgery, endocrinology, and wound care "
            "under the LEA (lower extremity amputation) avoidance thesis "
            "(15-20% 1-year post-major-LEA mortality literature driving "
            "payer and employer demand). Mid-hold captures diabetic foot "
            "ulcer (DFU) debridement volume on CPT 11042-11047 (subcutaneous "
            "through bone depth), Charcot arthropathy reconstruction, PAD / "
            "angiosome-directed revascularization referral coordination with "
            "vascular partners, and participates in BPCI Advanced bundled-"
            "payment on major LEA DRG 616-618 to capture LEA-avoidance "
            "upside margin. Sponsor targeting 2.8-3.2x exit on LEA-reduction "
            "outcome data."
        ),
    },
    {
        "company_name": "Cypress Wound & Foot Center",
        "sector": "Wound Care / Foot",
        "buyer": "Audax Private Equity",
        "year": 2019,
        "region": "Southeast",
        "ev_mm": 245.0,
        "ev_ebitda": 13.0,
        "ebitda_mm": 56.35,
        "ebitda_margin": 0.23,
        "revenue_mm": 245.00,
        "hold_years": 5.0,
        "moic": 2.6,
        "irr": 0.2108,
        "status": "Realized",
        "payer_mix": {"commercial": 0.36, "medicare": 0.44, "medicaid": 0.14, "self_pay": 0.06},
        "comm_pct": 0.36,
        "deal_narrative": (
            "Southeast foot-specific wound care platform with 34 outpatient "
            "wound clinics delivering diabetic foot ulcer debridement (CPT "
            "11042-11047 navigating MAC LCD requirements on depth "
            "documentation and recurring RAC audit focus on debridement-"
            "frequency), NPWT, hyperbaric oxygen therapy (HBOT for Wagner "
            "3+ DFU under CMS NCD 20.29 requiring 30+ days failed standard "
            "care), and cellular / tissue-based product (CTP / skin "
            "substitute) application. Long hold absorbed the CMS 2024-2025 "
            "LCD tightening on skin substitutes (Apligraf, Dermagraft, "
            "Grafix, amniotic allografts) compressing CTP margins, pivoted "
            "toward NPWT and podiatric surgical revenue mix, and exited to "
            "a strategic wound care platform at 2.6x MOIC."
        ),
    },
    {
        "company_name": "Summit Podiatric Surgery Centers",
        "sector": "Podiatric ASC",
        "buyer": "Linden Capital Partners",
        "year": 2020,
        "region": "West",
        "ev_mm": 205.0,
        "ev_ebitda": 13.5,
        "ebitda_mm": 49.20,
        "ebitda_margin": 0.24,
        "revenue_mm": 205.00,
        "hold_years": 4.5,
        "moic": 2.3,
        "irr": 0.2044,
        "status": "Active",
        "payer_mix": {"commercial": 0.46, "medicare": 0.36, "medicaid": 0.12, "self_pay": 0.06},
        "comm_pct": 0.46,
        "deal_narrative": (
            "West Coast podiatric ASC operator with 8 multi-specialty foot "
            "& ankle surgical centers credentialed for bunion / hallux "
            "valgus correction, Lapidus arthrodesis, hammertoe repair, "
            "plantar fasciotomy, ankle arthroscopy, total ankle "
            "replacement (TAR), and Charcot midfoot reconstruction. Mid-"
            "hold captures the HOPPS / ASC site-of-service differential "
            "on high-volume foot & ankle CPT codes following CMS ASC-list "
            "expansion, manages commercial payer prior-auth tightening on "
            "TAR and Lapidus, and participates in BPCI Advanced bundled-"
            "payment episodes on major LEA DRG 616-618 capturing upstream "
            "surgical volume for limb-salvage referrals."
        ),
    },
    {
        "company_name": "Harborlight Podiatry Group",
        "sector": "Podiatry Practice",
        "buyer": "NexPhase Capital",
        "year": 2021,
        "region": "Northeast",
        "ev_mm": 115.0,
        "ev_ebitda": 11.5,
        "ebitda_mm": 19.55,
        "ebitda_margin": 0.17,
        "revenue_mm": 115.00,
        "hold_years": 3.5,
        "moic": 1.5,
        "irr": 0.1217,
        "status": "Active",
        "payer_mix": {"commercial": 0.38, "medicare": 0.42, "medicaid": 0.14, "self_pay": 0.06},
        "comm_pct": 0.38,
        "deal_narrative": (
            "Northeast podiatry practice network with 28 clinics facing "
            "a CERT / UPIC audit cycle on routine foot care Q7 / Q8 / Q9 "
            "modifier documentation (Class A / B / C systemic findings "
            "under CMS NCD 70.2.1) that triggered recoupments and "
            "tightened billing controls. Mid-hold navigates the 1980 "
            "routine foot care statutory exclusion, rebuilds compliance "
            "infrastructure around diabetic loss-of-protective-sensation "
            "documentation, layers in custom orthotic revenue (HCPCS "
            "L3020 commercial-covered) and Therapeutic Shoe Bill DME "
            "(A5500 / A5501), and is evaluating a tuck-in sale to a "
            "larger podiatry MSO at compressed multiple."
        ),
    },
    {
        "company_name": "Pineridge Foot & Ankle Institute",
        "sector": "Foot & Ankle Surgery",
        "buyer": "Apollo Global Management",
        "year": 2018,
        "region": "National",
        "ev_mm": 685.0,
        "ev_ebitda": 14.5,
        "ebitda_mm": 164.40,
        "ebitda_margin": 0.26,
        "revenue_mm": 632.31,
        "hold_years": 5.5,
        "moic": 3.2,
        "irr": 0.2289,
        "status": "Realized",
        "payer_mix": {"commercial": 0.52, "medicare": 0.32, "medicaid": 0.10, "self_pay": 0.06},
        "comm_pct": 0.52,
        "deal_narrative": (
            "National foot & ankle surgery platform with 88 F&A surgeons "
            "(mixed DPM and orthopedic fellowship-trained), 12 owned "
            "physician ASCs, and integrated wound care service lines. "
            "Long hold captured CMS ASC-list expansion of foot & ankle "
            "CPT codes migrating bunion / Lapidus / TAR / ankle "
            "arthroscopy from HOPD to ASC capturing facility-fee "
            "revenue, deployed Charcot arthropathy reconstruction service "
            "line (external fixation, midfoot arthrodesis) anchoring "
            "diabetic limb preservation referrals, participated in BPCI "
            "Advanced on major LEA DRG 616-618, and exited to a "
            "strategic ortho consolidator at 3.2x MOIC."
        ),
    },
    {
        "company_name": "Bluestone Diabetic Foot Center",
        "sector": "Diabetic Limb Preservation",
        "buyer": "Kohlberg & Company",
        "year": 2016,
        "region": "Midwest",
        "ev_mm": 155.0,
        "ev_ebitda": 10.5,
        "ebitda_mm": 30.95,
        "ebitda_margin": 0.20,
        "revenue_mm": 154.75,
        "hold_years": 6.5,
        "moic": 3.7,
        "irr": 0.2213,
        "status": "Realized",
        "payer_mix": {"commercial": 0.30, "medicare": 0.48, "medicaid": 0.16, "self_pay": 0.06},
        "comm_pct": 0.30,
        "deal_narrative": (
            "Midwest diabetic foot center acquired pre-BPCI Advanced with "
            "22 multidisciplinary limb preservation clinics anchored by "
            "podiatry, vascular surgery, and wound care. Long 6.5-year "
            "hold built out the 'toe-and-flow' co-located clinic model, "
            "secured PAD / angiosome-directed revascularization referral "
            "partnerships with regional vascular groups, captured DFU "
            "debridement volume (CPT 11042-11047), navigated the CMS "
            "2024-2025 LCD tightening on skin substitutes late in hold, "
            "participated in BPCI Advanced major LEA DRG 616-618 bundles "
            "generating LEA-avoidance bundle margin, and exited to a "
            "strategic limb preservation consolidator at 3.7x MOIC on "
            "outcome-based LEA-reduction data."
        ),
    },
    {
        "company_name": "Bayshore Podiatric Associates",
        "sector": "Podiatry Practice",
        "buyer": "Riverside Company",
        "year": 2022,
        "region": "Southwest",
        "ev_mm": 135.0,
        "ev_ebitda": 13.5,
        "ebitda_mm": 22.95,
        "ebitda_margin": 0.17,
        "revenue_mm": 135.00,
        "hold_years": 3.0,
        "moic": 1.4,
        "irr": 0.1187,
        "status": "Active",
        "payer_mix": {"commercial": 0.40, "medicare": 0.40, "medicaid": 0.14, "self_pay": 0.06},
        "comm_pct": 0.40,
        "deal_narrative": (
            "Southwest podiatry practice network with 48 clinics acquired "
            "post-COVID at the top of the foot-&-ankle MSO multiple cycle. "
            "Early hold navigates the 1980 Medicare routine foot care "
            "statutory exclusion, Q-modifier documentation rigor on "
            "diabetic LOPS (loss of protective sensation) Class findings, "
            "and commercial payer tightening on custom orthotic L3020 "
            "pre-auth. Value creation hinges on Therapeutic Shoe Bill "
            "attach-rate lift (A5500 / A5501 diabetic shoes covered 1 "
            "pair/year on qualifying diabetic patients), DFU wound care "
            "service line buildout, and a tuck-in wound care pilot "
            "ahead of a sale to a regional podiatry or wound care "
            "consolidator at compressed multiple."
        ),
    },
    {
        "company_name": "Foxgrove Wound & Podiatry",
        "sector": "Wound Care / Foot",
        "buyer": "FFL Partners",
        "year": 2020,
        "region": "Mid-Atlantic",
        "ev_mm": 285.0,
        "ev_ebitda": 14.0,
        "ebitda_mm": 68.40,
        "ebitda_margin": 0.24,
        "revenue_mm": 285.00,
        "hold_years": 4.5,
        "moic": 2.2,
        "irr": 0.1917,
        "status": "Active",
        "payer_mix": {"commercial": 0.34, "medicare": 0.46, "medicaid": 0.14, "self_pay": 0.06},
        "comm_pct": 0.34,
        "deal_narrative": (
            "Mid-Atlantic integrated wound care and podiatry platform "
            "with 28 outpatient wound centers co-located with podiatric "
            "surgery suites delivering DFU debridement (CPT 11042-11047), "
            "NPWT, HBOT (CMS NCD 20.29 Wagner 3+ DFU coverage requiring "
            "30-day failed standard care documentation), and cellular / "
            "tissue-based skin substitute application. Mid-hold absorbs "
            "the CMS 2024-2025 LCD tightening on CTP / skin substitutes "
            "compressing product revenue, pivots toward integrated "
            "podiatric surgical service lines (Charcot reconstruction, "
            "bunion, TAR), participates in BPCI Advanced major LEA DRG "
            "616-618 bundles, and prepares for an exit to a strategic "
            "limb preservation platform."
        ),
    },
    {
        "company_name": "Crestline Foot & Ankle MSO",
        "sector": "Foot & Ankle Surgery",
        "buyer": "KKR",
        "year": 2019,
        "region": "National",
        "ev_mm": 445.0,
        "ev_ebitda": 14.0,
        "ebitda_mm": 102.35,
        "ebitda_margin": 0.23,
        "revenue_mm": 445.00,
        "hold_years": 5.0,
        "moic": 2.5,
        "irr": 0.2011,
        "status": "Realized",
        "payer_mix": {"commercial": 0.48, "medicare": 0.34, "medicaid": 0.12, "self_pay": 0.06},
        "comm_pct": 0.48,
        "deal_narrative": (
            "National foot & ankle MSO modeled on Upperline Health / Foot "
            "& Ankle Specialists of the Mid-Atlantic with 75 F&A surgeons "
            "(DPM and orthopedic F&A), 95 affiliated DPM practices, 8 "
            "owned ASCs, and integrated wound care. Long hold captured "
            "ASC migration of bunion / Lapidus / hammertoe / TAR / "
            "Charcot reconstruction, grew commercial-heavy custom orthotic "
            "(L3020) revenue via workers-comp and PPO channels, layered in "
            "the Therapeutic Shoe Bill (A5500 series) DME attach-rate "
            "program on the Medicare diabetic cohort, participated in "
            "BPCI Advanced on major LEA DRG 616-618, and exited to a "
            "strategic ortho / F&A consolidator at 2.5x MOIC."
        ),
    },
    {
        "company_name": "Trillium Podiatric Surgery",
        "sector": "Podiatric ASC",
        "buyer": "Sterling Partners",
        "year": 2021,
        "region": "Southeast",
        "ev_mm": 165.0,
        "ev_ebitda": 15.0,
        "ebitda_mm": 36.30,
        "ebitda_margin": 0.22,
        "revenue_mm": 165.00,
        "hold_years": 3.5,
        "moic": 1.7,
        "irr": 0.1594,
        "status": "Active",
        "payer_mix": {"commercial": 0.44, "medicare": 0.38, "medicaid": 0.12, "self_pay": 0.06},
        "comm_pct": 0.44,
        "deal_narrative": (
            "Southeast podiatric ASC network with 5 multi-specialty foot "
            "& ankle surgical centers delivering bunion / hallux valgus "
            "correction, Lapidus arthrodesis, hammertoe repair, ankle "
            "arthroscopy, total ankle replacement (TAR), and Charcot "
            "arthropathy midfoot reconstruction with external fixation. "
            "Mid-hold navigates the CMS ASC-list expansion on F&A CPT "
            "codes, manages commercial payer prior-auth on TAR and "
            "Lapidus (typical 14-21 day auth turnaround), and captures "
            "limb preservation referral share on diabetic Charcot cases. "
            "Sponsor targeting a 2.4-2.6x exit to a regional F&A or "
            "ortho platform."
        ),
    },
    {
        "company_name": "Northpoint Diabetic Foot Institute",
        "sector": "Diabetic Limb Preservation",
        "buyer": "Webster Equity Partners",
        "year": 2018,
        "region": "Northeast",
        "ev_mm": 225.0,
        "ev_ebitda": 12.5,
        "ebitda_mm": 51.75,
        "ebitda_margin": 0.23,
        "revenue_mm": 225.00,
        "hold_years": 5.5,
        "moic": 2.9,
        "irr": 0.2134,
        "status": "Realized",
        "payer_mix": {"commercial": 0.30, "medicare": 0.48, "medicaid": 0.16, "self_pay": 0.06},
        "comm_pct": 0.30,
        "deal_narrative": (
            "Northeast diabetic foot institute with 18 multidisciplinary "
            "limb preservation clinics integrating DPM, vascular surgery, "
            "endocrinology, and wound care under a 'toe-and-flow' model. "
            "Long hold captured Charcot arthropathy reconstruction volume "
            "(external fixation, midfoot arthrodesis), PAD / angiosome-"
            "directed revascularization referral coordination, DFU "
            "debridement (CPT 11042-11047), HBOT (CMS NCD 20.29 Wagner "
            "3+ DFU), and participated in BPCI Advanced major LEA DRG "
            "616-618 bundled-payment episodes generating LEA-avoidance "
            "bundle margin on measured reduction in major amputations "
            "per 1,000 diabetic lives. Exited to a strategic limb "
            "preservation consolidator at 2.9x MOIC."
        ),
    },
    {
        "company_name": "Evergreen Foot Care Network",
        "sector": "Podiatry Practice",
        "buyer": "Thomas H. Lee Partners",
        "year": 2023,
        "region": "National",
        "ev_mm": 225.0,
        "ev_ebitda": 17.5,
        "ebitda_mm": 36.00,
        "ebitda_margin": 0.16,
        "revenue_mm": 225.00,
        "hold_years": 2.5,
        "moic": 1.5,
        "irr": 0.1774,
        "status": "Active",
        "payer_mix": {"commercial": 0.40, "medicare": 0.38, "medicaid": 0.14, "self_pay": 0.08},
        "comm_pct": 0.40,
        "deal_narrative": (
            "National podiatry practice network acquired at peak 2023 "
            "podiatry MSO multiples with 58 clinics and 95 DPMs. Early "
            "hold faces CERT / UPIC audit pressure on routine foot care "
            "Q7 / Q8 / Q9 modifier documentation (Class A / B / C "
            "systemic findings under CMS NCD 70.2.1 overcoming the 1980 "
            "routine foot care statutory exclusion), commercial payer "
            "tightening on custom orthotic L3020 pre-authorization, and "
            "CMS 2024-2025 LCD revisions on diabetic foot wound care. "
            "Value creation hinges on Therapeutic Shoe Bill A5500 / "
            "A5501 DME attach-rate lift, integrated wound care service "
            "line expansion, and a selective podiatric surgery ASC "
            "pilot targeting bunion and hammertoe migration from HOPD."
        ),
    },
    {
        "company_name": "Kingswood Podiatric ASC Partners",
        "sector": "Podiatric ASC",
        "buyer": "Leonard Green & Partners",
        "year": 2022,
        "region": "National",
        "ev_mm": 485.0,
        "ev_ebitda": 17.0,
        "ebitda_mm": 106.70,
        "ebitda_margin": 0.22,
        "revenue_mm": 485.00,
        "hold_years": 3.0,
        "moic": 1.8,
        "irr": 0.2164,
        "status": "Active",
        "payer_mix": {"commercial": 0.48, "medicare": 0.36, "medicaid": 0.10, "self_pay": 0.06},
        "comm_pct": 0.48,
        "deal_narrative": (
            "National podiatric ASC platform with 26 physician-owned foot "
            "& ankle surgical centers delivering bunion / hallux valgus "
            "correction, Lapidus arthrodesis, hammertoe repair, plantar "
            "fasciotomy, ankle arthroscopy, total ankle replacement (TAR), "
            "and Charcot arthropathy midfoot reconstruction. Early hold "
            "captures the HOPPS / ASC site-of-service differential on "
            "CMS-ASC-list-expanded F&A CPT codes, navigates commercial "
            "payer prior-auth tightening on TAR and Lapidus (particularly "
            "UnitedHealthcare 2023 policy updates), integrates wound care "
            "and limb preservation referral pathways on diabetic Charcot "
            "cases, and participates in BPCI Advanced bundled-payment "
            "episodes on major LEA DRG 616-618 capturing upstream "
            "surgical volume for limb-salvage referral share."
        ),
    },
]
