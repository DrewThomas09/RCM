# US Healthcare Verticals & Specialty-Pharmacy / Life-Sciences Deep Dive

_PEDesk / RCM-MC sector-intelligence series. Fifteen diligence verticals profiled
with chart-ready codes, epidemiology, workforce, throughput, and 2025/2026
reimbursement detail._

## Where this fits

PEDesk started hospital-centric and has six structurally-integrated provider
verticals today (Hospital/HCRIS, SNF, Dialysis, Home Health, Hospice, IRF,
LTCH — see [PEDESK_VERTICAL_DATA_DEPTH_AUDIT.md](PEDESK_VERTICAL_DATA_DEPTH_AUDIT.md)).
This brief is the **sector-expansion reference** that sits underneath
[PEDESK_SECTOR_INTELLIGENCE_ROADMAP.md](PEDESK_SECTOR_INTELLIGENCE_ROADMAP.md) and
[MULTI_ASSET_EXPANSION.md](MULTI_ASSET_EXPANSION.md): it profiles fifteen
**candidate verticals** — ten provider/therapy/ancillary segments plus the
five-segment life-sciences "drug-dollar" layer (specialty pharmacy, PBMs,
CROs/CDMOs, GPOs/340B, home infusion).

Every vertical below carries the billing codes, epidemiology, workforce, unit
economics, and named primary datasets needed to build a screener + provider
profile + chart pack the way the six live verticals already do. Per the data
discipline elsewhere in the repo: figures from commercial market-research firms
are flagged as approximate ranges; primary CMS/HRSA/BLS/MedPAC/IQVIA/Drug
Channels sources are named per vertical so each chart can be source-traced and
auto-refreshed.

**Bottom line.** The single most consequential near-term operational change
across the provider verticals is the January 1, 2026 reclassification of non-BLA
skin substitutes/CTPs from ASP+6% biologicals to "incident-to supplies" at a
flat **$127.28/cm²** national rate (CMS projects ~$19B in 2026 PFS savings) —
while the dominant structural story in the life-sciences layer is continued
concentration: the big-three PBMs process **80%** of US prescription claims and
340B purchases hit a record **$81.4 billion** in 2024.

## TL;DR

- **Provider/therapy verticals are PFS-driven and being reshaped by three 2026
  levers:** the dual PFS conversion factors ($33.5675 APM / $33.4009 non-APM),
  the -2.5% efficiency adjustment (which spares time-based therapy codes), and
  the CTP/skin-substitute flat-rate overhaul. Wound care, podiatry, and clinical
  labs face the largest reimbursement disruptions; ground ambulance remains
  uniquely exposed as the lone surprise-billing carve-out.
- **The drug-dollar layer (specialty pharmacy, PBMs, 340B, GPOs, home infusion)
  is large, concentrated, and growing double-digit.** Specialty medicines = ~53%
  of US net drug sales ($262B of $487B in 2024); the big-three PBMs control 80%
  of claims; 340B reached $81.4B (+22.8%); the home-infusion site-of-care shift
  continues (~$39.9B US infusion market in 2025).
- **Data is chart-ready below**: every vertical includes structured codes,
  specific rates/volumes, and explicit visualization recommendations (funnels,
  waterfalls, 100% stacked bars, line/treemap).

---

## Cross-cutting 2025/2026 reimbursement anchors

- **2026 PFS conversion factors:** $33.5675 (qualifying-APM) and $33.4009
  (non-qualifying), up from the single 2025 CF of $32.3465 (+3.77% / +3.26%);
  includes a 2.5% one-year OBBBA increase plus a **-2.5% "efficiency adjustment"**
  applied to non-time-based codes (CMS-1832-F, Oct 31 2025).
- **2026 OPPS/ASC** payment rates up 2.6%; rules affect ~4,000 hospitals and
  ~6,000 ASCs (CMS-1834-FC, Nov 21 2025).
- **Skin substitutes/CTPs (non-BLA)** reclassified as "incident-to supplies"
  effective Jan 1 2026 at a single national rate — **$127.28/cm² under PFS** and
  $127.14/cm² under OPPS; discarded/wasted product not payable; CMS projects
  ~$19B PFS savings in 2026. Three FDA-based APCs created: 6000 (PMA), 6001
  (510(k)), 6002 (361 HCT/P); low-cost C-codes C5271–C5278 deleted.
- **CLFS/PAMA:** no cuts in 2026; cuts of up to 15%/yr delayed to 2027–2029; new
  data collection Jan 1–Jun 30 2025, reporting May 1–Jul 31 2026 (CAA 2026
  §6226).
- **Drug spend context:** Per IQVIA Institute, *Understanding the Use of
  Medicines in the U.S. 2025* (Apr 2025), the US market at net prices grew 11.4%
  in 2024 to **$487 billion**, with **specialty medications accounting for $262
  billion (53% of net sales)**.

---

# Group A — provider / therapy / ancillary verticals

## 1. Physical, occupational & speech therapy (outpatient rehab)

**(a) Common codes.** *Timed (15-min) CPT:* 97110 therapeutic exercise (~42% of
PT billing per APTA), 97112 neuromuscular re-education, 97116 gait training,
97140 manual therapy, 97530 therapeutic activities, 97535 self-care training,
97542 wheelchair management, 97761 prosthetic training. *Untimed:*
97161/97162/97163 PT eval (low/mod/high complexity), 97164 re-eval; 97165–97168
OT eval; 97010 hot/cold packs. *SLP:* 92507 speech/language treatment, 92610
swallowing eval, 92526 dysphagia treatment. *NPPES taxonomy:* 225100000X (PT),
225X00000X (OT), 235Z00000X (SLP).

**(b) Population/epidemiology.** Demand driven by musculoskeletal disorders,
post-surgical recovery, stroke, and aging; Medicare Part B is the dominant payer
for the 65+ rehab population.

**(c) Workforce.** PTs ~253,300 jobs (BLS OOH 2024, median wage $101,020); OTs
~162,000 (median $98,340); SLPs (median $95,410).

**(d) Operations/benchmarks.** The Medicare 8-minute rule governs time-based
billing: 1 unit = 8–22 min, 2 units = 23–37, 3 = 38–52, 4 = 53–67 min — total
timed minutes summed then divided by 15 with the 8-minute remainder rule.
Commercial payers often use the AMA "Rule of Eights"/Substantial Portion Method
(each code independently ≥8 min, allowing more units). Medicare typically caps at
4 units/day.

**(e) Reimbursement.** Paid under PFS. The 2025 KX-modifier therapy threshold was
$2,330 (combined PT+SLP) and $2,330 (OT); beyond it the KX modifier attests
medical necessity. 2026 CF $33.4009. Critically, the -2.5% efficiency adjustment
**exempts time-based codes** (most therapy codes), so therapy is relatively
insulated versus procedural specialties.

**(f) Data sources.** CMS PFS; CMS Medicare Benefit Policy Manual Ch. 15; APTA;
BLS OES; MEPS.

**Charts:** bar — visit economics by CPT; 100% stacked bar — timed vs untimed
units; line — therapy cap threshold over time.

## 2. Chiropractic care

**(a) Codes.** Medicare covers ONLY three CPT codes: 98940 (CMT spinal 1–2
regions), 98941 (3–4 regions), 98942 (5 regions). 98943 (extraspinal) is NOT
Medicare-covered. The **AT modifier** is required for active/corrective
treatment; claims without it are denied as maintenance. ICD-10 primary must be
M99.0x (segmental/somatic dysfunction). Cash-pay/ancillary: 97140 manual
therapy, 97110, E/M exam codes.

**(b) Population.** Historic Medicare Part B CSM claims: ~824,249 (1998) rising
to ~1,133,872 (2003) in published claims studies, with 98941 displacing 98940 as
the most common code. A large cash-pay/wellness market exists outside Medicare.

**(c) Workforce.** ~50,000 chiropractors (BLS, median wage ~$78,410, 2024; exact
employment count requires direct BLS verification).

**(d) Operations.** Only one CMT code payable per patient per day. Acute episodes
typically a few weeks to ~3 months; chiropractic carries one of the highest
Medicare error/denial rates. 60-day re-evaluation norms.

**(e) Reimbursement.** The covered/non-covered split is the defining feature:
Medicare covers only spinal manipulation for an active subluxation; maintenance
care, DC-ordered X-rays, E/M, and therapies are non-covered, driving a
substantial cash-pay model. PFS rates apply to the three covered codes.

**(f) Data sources.** CMS LCD/Article A56273; MLN SE1601; ACA.

**Charts:** stacked bar — covered vs cash-pay revenue; bar — CMT code
distribution.

## 3. Podiatry

**(a) Codes.** Routine foot care: 11055/11056/11057 (paring corns/calluses),
11719 (trim nondystrophic nails), 11720 (debride 1–5 nails), 11721 (debride 6+
nails), G0127 (trim dystrophic nails), G0247 (LOPS diabetic foot care). **Q
modifiers mandatory:** Q7 (1 Class A finding), Q8 (2 Class B), Q9 (1 Class B + 2
Class C). T-modifiers (TA, T1–T9) for toe laterality. ICD-10: E11.621 (diabetes
w/ foot ulcer), B35.1 (onychomycosis), E08–E13, G60.x neuropathy, I80.x.
Surgical: 20610 joint injection, 28810/28820 amputations.

**(b) Population/epidemiology.** Per Armstrong/Boulton, JAMA *Diabetic Foot
Ulcers: A Review* (PMID 37395769): ~**37 million people in the United States have
diabetes**, and **approximately 1.6 million Americans are affected by a diabetic
foot ulcer each year** (18.6M worldwide). Lifetime DFU risk is **19–34%**
(Armstrong et al., ADA *Diabetes Care* 2023). Aging + diabetes are the demand
drivers; routine foot care is the highest-volume podiatry service family.

**(c) Workforce.** ~9,700 podiatrists (DPMs) employed (BLS 2024), median wage
$152,800.

**(d) Operations.** Routine foot care capped at ~once/60 days (≤6×/yr).
Q-modifier plus a qualifying systemic ICD-10 is mandatory or the claim
auto-denies. RVUs: 11720 non-facility total ~0.98; 11721 ~1.32.

**(e) Reimbursement.** PFS. The routine-vs-medically-necessary foot-care
distinction is the operational crux: routine care is excluded unless a qualifying
systemic condition (diabetes with neuropathy/PVD) is documented with class
findings.

**(f) Data sources.** CMS LCD Articles A57759/A56232; CDC Diabetes; APMA; ADA
*Diabetes Care*.

**Charts:** funnel — diabetes→neuropathy→DFU→amputation; bar — RVU/payment by
code.

## 4. Plastic surgery & medical aesthetics / med-spa

**(a) Codes.** *Cosmetic (cash):* botulinum toxin J0585 (onabotulinumtoxinA, per
unit) and fillers; CPT 15780s dermabrasion, 15834+ body contouring/lipectomy,
17106–17108 vascular laser. *Reconstructive (insured):* 19357 breast
reconstruction, 15734 muscle flap, 14000-series adjacent tissue transfer.

**(b) Population/market.** US aesthetic injectable market ~$4.1B in 2024 (CAGR
11.2% to 2030; Grand View Research). Global medical aesthetics ~$17.3–20.1B in
2024. Botulinum toxin = ~45.9% of US injectables; ~4.7M botox procedures in 2023
(+6% YoY); dermal fillers ~3.44M procedures. Med spas = ~47.3% of
injectable-delivery setting in 2024; an average med spa generates >$1.9M annually
(AmSpa 2022). ~90% of clientele are women; a fast-growing "prejuvenation"
under-30 segment.

**(c) Providers/facilities.** Thousands of med spas plus dermatology and
plastic-surgery practices; care increasingly delivered by mid-level injectors.
>200 medical aesthetics product companies; AbbVie/Allergan dominant
(Botox/Juvederm — ~$5.2B 2023 aesthetics revenue).

**(d) Operations.** Cash-pay, retail-style economics; botox typically
$400–500/session, bundled with skincare/wellness. Body contouring, laser
hair/tattoo removal as ancillary lines.

**(e) Reimbursement.** Reconstructive procedures are insured under PFS/OPPS;
cosmetic procedures are fully cash-pay with no third-party reimbursement — the
reconstructive-vs-cosmetic split is the defining payer dynamic.

**(f) Data sources.** ASPS procedural statistics; ISAPS Global Survey; AmSpa;
Grand View Research (market-size figures approximate).

**Charts:** stacked bar — procedure mix; line — injectable market growth; bar —
cash-pay per-procedure economics.

## 5. Sleep medicine

**(a) Codes.** *In-lab PSG:* 95810 (PSG ≥6yr, ≥4 parameters), 95811 (PSG w/ CPAP
titration), 95808 (1–3 params); split-night studies. *HSAT:* 95800, 95801,
95806; G0398/G0399/G0400 (Medicare HSAT types). *CPAP/DME:* E0601 (CPAP),
E0470/E0471 (BiPAP), A7030 (mask), A7038 (filters). ICD-10: G47.33 (OSA), G47.30
(sleep apnea unspecified), G47.00 (insomnia).

**(b) Epidemiology.** Per Benjafield et al. (cited in *Respiratory Medicine*
2025), over **54 million (33.2%) US adults aged 30–69 were previously estimated
to have OSA**; a 2024 estimate puts US adult OSA (age 20+) at **83.7 million
adults, a 32.4% overall prevalence** (ScienceDirect S0954611125004111).
Historically underdiagnosed (~4% of men, 2% of women diagnosed per Young et al.;
up to ~10% in 65+). Globally ~936M adults age 30–69 have mild+ OSA (AHI≥5;
Benjafield 2019). AHI severity: 5–14 mild, 15–29 moderate, ≥30 severe.

**(c) Facilities.** Thousands of AASM-accredited sleep centers; growing HSAT-at-
home delivery with DME tie-in to CPAP suppliers.

**(d) Operations / funnel.** Diagnosis-to-treatment funnel: screening (STOP-BANG)
→ HSAT or in-lab PSG → diagnosis → CPAP titration → DME setup → adherence
monitoring. AASM recommends HSAT for uncomplicated moderate-severe OSA; a
negative/inconclusive HSAT should be followed by in-lab PSG. PSG (type 1) records
≥7 channels; HSAT types 2–4 use fewer sensors. Strong payer push toward
lower-cost HSAT.

**(e) Reimbursement.** PSG/HSAT professional + technical components paid under
PFS; CPAP DME under the DMEPOS fee schedule with adherence requirements
(compliance documented within the first 90 days).

**(f) Data sources.** AASM; USPSTF evidence review (NBK588761); CMS NCD
(CAG-00405N); CDC.

**Charts:** 100% stacked bar — in-lab PSG vs HSAT volume; funnel —
diagnosis→treatment→adherence; bar — OSA severity distribution.

## 6. Wound care

**(a) Codes.** *Debridement:* 11042–11047 (by depth/area), 97597/97598
(selective debridement). *Skin substitute application:* 15271–15278 (by wound
size/location); low-cost C-codes C5271–C5278 deleted for 2026. *HBOT:* 99183
(physician supervision, per session), G0277 (hyperbaric O2, 30-min interval). CTP
product HCPCS Q-codes. ICD-10: E11.621 DFU, L97.x (non-pressure chronic ulcer),
I83.0x (varicose veins w/ ulcer), L89.x (pressure ulcer by stage/site).

**(b) Epidemiology.** Per Nussbaum et al., *Value in Health* (2018), a Medicare
5% 2014 dataset found **nearly 15% of Medicare beneficiaries (8.2 million) had at
least one type of wound or infection**, at a conservative estimated annual cost
of **$28.1–$31.7 billion** (PMID 29304937). DFUs ~1.6M/yr; venous leg ulcers and
pressure injuries are large additional cohorts. >50% of DFUs become infected;
~20% lead to amputation; 5-yr mortality after DFU ~2.5×. CKD/ESKD strongly
elevate risk.

**(c) Facilities.** Hospital outpatient wound centers, podiatry/physician
offices, mobile clinics, and increasingly ASCs.

**(d) Operations.** Standard of care: debridement, offloading, moist wound
therapy, infection control; SOC-alone DFU closure rates 20–38%. HBOT for select
DFU/osteomyelitis/radiation injury. Wound-center economics were historically
dependent on CTP product margin.

**(e) Reimbursement — the CTP controversy.** Effective Jan 1 2026, non-BLA skin
substitutes were reclassified from ASP+6% biologicals to "incident-to supplies"
at a single flat national rate. Per the National Law Review on the CMS CY2026
final rule (Nov 5 2025), CMS "shifts skin substitute payments to a
**$127.28/cm² flat rate in 2026**" (PFS; OPPS $127.14/cm²) across office, HOPD,
and ASC — ending product-based pricing. Discarded/wasted product is NOT payable.
CMS projects ~$19B in 2026 savings. The change was spurred in part by the **DOJ
2025 National Health Care Fraud Takedown** (June 30 2025), which charged seven
defendants "in connection with approximately $1.1 billion in fraudulent claims to
Medicare and other health care benefit programs for amniotic wound allografts"
(part of a broader $14.6B takedown). BLA-licensed (§351) products remain on
ASP+6%. For 2027+, CMS plans three differentiated FDA-pathway payment categories
(PMA, 510(k), 361 HCT/P).

**(f) Data sources.** CMS PFS/OPPS final rules; Alliance of Wound Care
Stakeholders; MedPAC; ADA; Nussbaum et al. (Value in Health).

**Charts:** waterfall — CTP reimbursement before/after 2026; funnel —
wound→infection→amputation; line — CTP Medicare spend growth.

## 7. Allergy & immunology

**(a) Codes.** *Testing:* 95004 (percutaneous/scratch, per test), 95017/95018
(venom/drug), 95024/95027 (intradermal), 86003/86008 (specific IgE).
*Immunotherapy:* 95165 (prep/supervision of antigen vials, per dose; commonly
capped ~120–150 doses/yr, ≤84 units/day per some policies), 95115 (single
injection), 95117 (2+ injections), 95120/95125 (complete service). *Biologics
(J-codes):* J2357 omalizumab (Xolair), J2182 mepolizumab (Nucala), J0517
benralizumab (Fasenra), J2786 reslizumab, plus dupilumab. ICD-10: J30.x allergic
rhinitis, J45.x asthma, L20.x atopic dermatitis, T78.40 allergy unspecified.

**(b) Epidemiology.** Allergic rhinitis affects ~400M people worldwide and is
highly prevalent in the US; AR markedly increases asthma risk (OR ~7.8 in one
cohort, Polosa et al.). AIT is the only disease-modifying therapy for allergic
respiratory disease. Severe eosinophilic/allergic asthma is the biologics target
population.

**(c) Workforce.** Allergists/immunologists (ACAAI/AAAAI societies); in-office
model dominant.

**(d) Operations.** In-office economics center on 95165 antigen preparation (the
practice owns extract prep) plus injection visits (95115/95117). Payer
documentation burden on these three codes is a key friction point
(ACAAI/AAAAI/JCAAI joint guidance, 2024). Biologics shift some severe-asthma
patients to buy-and-bill or specialty pharmacy.

**(e) Reimbursement.** PFS for testing and immunotherapy; biologics under Part B
ASP+6% (buy-and-bill) or the pharmacy benefit. AIT vial prep is a recurring
revenue stream.

**(f) Data sources.** CMS PFS; AAAAI; ACAAI; JACI/JCAAI.

**Charts:** bar — testing vs IT vs biologics revenue; funnel — testing→IT
initiation→maintenance.

## 8. Clinical laboratories & anatomic pathology

**(a) Codes.** *Chemistry/hematology:* 80053 (CMP), 80048 (BMP), 85025 (CBC w/
diff), 80061 (lipid panel), 83036 (HbA1c). *Molecular:* 81479 (unlisted
molecular), PLA (0xxxU) codes, 81455 (solid tumor panel). *Pathology:* 88305
(level IV surgical path — the workhorse), 88307/88309, 88112/88142 (cytology),
88341/88342 (IHC). Pathology splits into professional (-26) and technical (-TC)
components.

**(b) Population.** ~13.3–14B clinical lab tests performed annually in the US;
~70% of medical decisions rely on laboratory testing (CDC/Lewin Group basis;
figure ranges 70–80% by source).

**(c) Facilities/workforce.** ~320,000 CLIA-certified lab entities (CMS) — most
are Certificate-of-Waiver; ~33,000 active CoA+CoC labs. Clinical lab
technologists/technicians ~351,200 jobs (BLS 2024, median $61,890). Reference-lab
market concentrated (Labcorp, Quest).

**(d) Operations.** High-volume, low-margin routine testing; molecular/genetic
and esoteric testing carry higher value. The professional/technical split is
central to pathology economics.

**(e) Reimbursement — PAMA/CLFS.** Most CDLTs paid on CLFS at the
weighted-median of private-payor rates. The first PAMA round (2016 data, <1% of
labs reporting) cut ~$3.8B over 2018–2020 (10% caps). CAA 2026 §6226: NO 2026
cuts; up-to-15%/yr cuts delayed to 2027–2029; data now from Jan–Jun 2025,
reported May–Jul 2026. ~820 tests face cuts absent reform (the RESULTS Act,
introduced Sept 2025, would freeze rates at 2025 levels through 2028 and cap cuts
at 5%/yr from 2029). Pathology professional component on PFS; technical on OPPS.

**(f) Data sources.** CMS CLFS; ACLA; NILA; CDC CLIA.

**Charts:** bar — test volume by category; line — CLFS rate cuts timeline;
stacked bar — pathology professional vs technical.

## 9. Emergency medical services / ambulance

**(a) Codes.** *Ground:* A0425 (mileage), A0426 (ALS non-emergency), A0427 (ALS
emergency), A0428 (BLS), A0429 (BLS emergency), A0433 (ALS2), A0434 (specialty
care transport). *Air:* A0430/A0431 (fixed-wing/rotary), A0435/A0436 (air
mileage). Origin/destination modifiers (R, H, S, etc.).

**(b) Population.** ~3M privately-insured emergency ground ambulance transports/
yr, plus a high Medicare/Medicaid mix.

**(c) Providers.** ~13,000 ambulance providers nationwide (American Ambulance
Association); ~4 in 5 carry <1,000 Medicare-billable trips/yr — highly
fragmented, many volunteer/municipal. Mix of municipal, fire-based, hospital,
private, and PE-backed operators.

**(d) Operations / access.** Rural ambulances travel farther with fewer trips →
cost-spreading difficulty. "Treat-no-transport" calls often go unreimbursed
(Maine first to pay, 2025; New Hampshire followed). Response-time standards are
set locally.

**(e) Reimbursement — surprise-billing carve-out.** Ground ambulances were
EXCLUDED from the No Surprises Act (air ambulances were included). An estimated
28–50% of emergency ground rides produce out-of-network/surprise bills; median
surprise bill ~$450; ~79% of rides could yield OON bills. The GAPB Advisory
Committee issued 2024 recommendations; 22 states now have some protection (5
enacted in 2025); self-funded ERISA plans (~99.5M people) remain outside state
authority. Paid under the Medicare Ambulance Fee Schedule (PFS final rule updates
the ambulance fee-schedule regulations for 2026).

**(f) Data sources.** CMS Ambulance Fee Schedule; GAPB report; Commonwealth
Fund; American Ambulance Association; Health Affairs.

**Charts:** bar — code/level reimbursement; map/bar — state surprise-bill
protections; bar — OON rate by state.

## 10. IRF, LTACH & PACE

**(a) Codes/systems.** *IRF:* paid per-discharge under IRF-PPS using CMGs from
the IRF-PAI (required for all payers since Oct 1 2024); the **60% Rule** requires
≥60% of patients in 13 qualifying conditions (42 CFR 412.29). *LTACH:* LTCH-PPS
(MS-LTC-DRGs), with site-neutral payment for non-qualifying cases. *PACE:* fully
capitated PMPM (Medicare Parts A/B/D + Medicaid). Facility revenue codes / bill
types apply.

**(b) Population.** IRF top condition is stroke (~21.8% of 2024 cases), followed
by hip fracture, brain injury, and neurological conditions. PACE serves frail
dual-eligibles age 55+ certified nursing-home-eligible; ~56,000 participants
(2024), 80,815 enrolled Jan 1 2025; ~90% dually eligible.

**(c) Facilities.** IRFs ~1,180 (freestanding + hospital units); ~68% aggregate
occupancy. PACE: **178 programs by Dec 31 2024** (25 new in 2024), ~198 by
end-2025 (20 new); 47 for-profit organizations as of Jan 2025. PACE enrollment
nearly tripled 2011–2023 but remains <0.5% of eligible older adults.

**(d) Operations.** IRF requires patients tolerate 3 hrs of intensive therapy/
day. IRF FFS Medicare margin ~13.7% (2022), projected ~14% (2024); median
discharge-to-community 67.5%; potentially-preventable readmissions ~9.2%. PACE
average length of enrollment 2–3 yrs (death is the main disenrollment cause);
2025 median program census growth 11.7%.

**(e) Reimbursement.** IRF FFS Medicare spending ~$11.0B. FY2026 LTACH PPS +2.7%
(3.4% market basket -0.7% productivity). IRF FY2026 updated via market basket
-productivity. PACE Medicare capitation averages ~20% more per beneficiary than
comparable MA plans; ~90% of PACE enrollees are full-dual; a CA full-dual PMPM
lower-bound of ~$8,279 (San Francisco, 2022) has been cited.

**(f) Data sources.** CMS IRF-PPS/LTCH-PPS final rules; MedPAC Ch. 8/9; National
PACE Association; NORC; MACPAC; Urban Institute.

**Charts:** line — PACE enrollment growth; bar — IRF case-mix by condition; bar —
post-acute Medicare margins.

---

# Group B — specialty pharmacy & life-sciences services

## 11. Specialty pharmacy

**(a) Codes/identifiers.** NDC-driven dispensing; J-codes for provider-
administered specialty (buy-and-bill vs pharmacy benefit). NCPDP standards for
pharmacy claims. Accreditation by URAC and ACHC.

**(b) Population/categories.** Specialty spans oncology, autoimmune/immunology,
rare/orphan disease, HIV, MS, hepatitis, and increasingly GLP-1s. The Medicare
Part D specialty-tier threshold is $670/month (set 2017). Per IQVIA (Apr 2025),
specialty medications accounted for **$262 billion, 53% of US net drug sales in
2024**. The median annual cost of 2023-launched drugs exceeded $150,000, with
oncology and rare-disease drugs both approaching ~$300,000/patient (IQVIA 2024).
GLP-1s: per IQVIA, "nearly 700,000 GLP-1 agonist new prescriptions for diabetes
and obesity were filled in February 2024, up 181% compared with two years prior."

**(c) Companies.** US specialty dispensing revenue ~$243B (2023) and ~$265B
(2024) per Drug Channels Institute (DCI). ~1,749–1,900 accredited specialty
pharmacy locations (~3% of all US pharmacies). The big-three PBM-affiliated
specialty pharmacies — Accredo (Evernorth/Cigna), CVS Specialty, and Optum
Specialty — together represent ~two-thirds of specialty Rx revenue.

**(d) Operations.** Limited distribution drugs (LDDs): manufacturer restricts
distribution to a narrow network of pharmacies (REMS, cold-chain handling, orphan
populations) — an industry definition, not a statutory one. Hub services, prior
authorization, patient assistance, and adherence programs are core. High
per-script value with thin dispensing margins offset by data/services revenue.

**(e) Reimbursement.** A mix of pharmacy benefit (PBM-adjudicated) and medical
benefit (ASP+6% buy-and-bill). Payer/PBM steering to vertically-owned specialty
pharmacies and gross-to-net erosion are dominant dynamics.

**(f) Data sources.** Drug Channels Institute; IQVIA *Use of Medicines*; CMS.

**Charts:** line — specialty drug spend trend; treemap — specialty pharmacy
market share; waterfall — gross-to-net.

## 12. Pharmacy benefit managers (PBMs)

**(a) Mechanics.** Formulary management, rebate negotiation, spread pricing,
retail network contracting, claims adjudication, and mail/specialty dispensing.

**(b/c) Concentration.** Per DCI's 2026 Economic Report: "For 2025, 80% of all
equivalent prescription claims were processed by three companies: the CVS
Caremark business of CVS Health, the Express Scripts business of Cigna, and the
Optum Rx business of UnitedHealth Group" — and 2024 was also ~80% (one point
higher than 2023). 2024 shares (DCI/Becker's): **Express Scripts 30%** (up from
23% in 2023, driven by the ~20M-member Centene contract), **CVS Caremark 27%**
(down from 34%), **Optum Rx 23%**. 2025: Express Scripts 31%, CVS Caremark 26%,
Optum Rx 23%. Five of the six largest PBMs are owned by insurers. AMA
rebate-negotiation market shares (2023): OptumRx 22.2%, CVS 18.9%, Express
Scripts 15.5%, Prime 10.6%; local PBM markets are highly concentrated (avg HHI
~2300). Per DCI, "For 2025, [Optum Rx] managed $188 billion in drug spend, of
which $87 billion (46%) was classified by Optum Rx as specialty
pharmaceuticals."

**(d) Operations/economics.** Rebate retention, spread pricing (charging plans
more than pharmacies are reimbursed), and DIR fees. CVS Caremark's total PBM
30-day-equivalent claims fell -18.2% (2.3B→1.9B) in 2024 on the Centene loss.

**(e) Regulatory pressure.** FTC antitrust action on insulin rebates (2024–25);
transparency legislation; vertical-integration scrutiny. CalPERS shifted to CVS
Caremark for 2026.

**(f) Data sources.** Drug Channels Institute; AMA Policy Research Perspectives;
FTC; JAMA.

**Charts:** stacked bar / treemap — PBM market share; line — share shift
2023→2025.

## 13. CROs & CDMOs

**(a) Structure.** CROs provide outsourced clinical trial services (Phase I–IV,
biostatistics, data management, pharmacovigilance, regulatory). CDMOs provide
contract development plus manufacturing (API, drug product, biologics).

**(b) Market.** Global CRO services market ~$80–86B in 2024 (estimates: Fortune
$86.3B; MarketsandMarkets $79.1–84.6B; Mordor $85.9B for 2025); ~8–9.6% CAGR.
5,318 clinical trials started in 2024; oncology/immunology/neurology/CV = 71%.
Emerging biopharma = 63% of trial starts (up from 56% in 2019). R&D funding hit a
10-yr high of $102B in 2024 (up from $71B in 2023). >50% of sponsor clinical
budgets are now outsourced. CDMO: the CMO segment is largest; phase costs ~$4M
(I), $13M (II), $20M (III); only ~12% of trialed drugs gain FDA approval.

**(c) Companies.** IQVIA (largest), Labcorp, Thermo Fisher/PPD, ICON, Syneos,
Parexel, Charles River, Medpace; CDMOs Lonza, Catalent, Samsung Biologics,
Thermo Fisher. IQVIA FY2024 revenue $15.4B; R&DS backlog ~$31.1B.

**(d) Operations.** Book-to-bill ~1.2–1.3× (IQVIA). Decentralized/hybrid trials
cut per-patient costs ~15–25%; Phase III per-patient cost ~$60,000 (North
America). North America ~38.9–50% of CRO revenue.

**(e) Pricing.** Fee-for-service / functional service provider (FSP) /
milestone-based; not government-reimbursed.

**(f) Data sources.** IQVIA *Global Trends in R&D*; Contract Pharma; SEC filings;
ClinicalTrials.gov (market-size figures approximate).

**Charts:** line — CRO market growth; bar — trial starts by therapeutic area; bar
— phase costs.

## 14. GPOs & the 340B program

**(a) Mechanics.** GPOs aggregate purchasing and are funded by vendor
administrative fees (≤3% under the 1987 Anti-Kickback safe harbor, codified by
OIG in 1991; actual weighted-avg fees ~1.22–2.25% per GAO). 340B requires
manufacturers to sell outpatient drugs to covered entities at a statutory
discount (up to 100% off list).

**(b) Ecosystem.** GPOs: Vizient, Premier, and HealthTrust control ~75% of GPO
spend; ~90% of hospital medical-equipment procurement runs through GPOs; ~97% of
hospitals use ≥1 GPO. 340B covered entities: DSH hospitals, FQHCs,
children's/critical-access hospitals, Ryan White clinics; >2,600 hospitals
enrolled (2023).

**(c) Scale.** 340B purchases hit **$81.4B in 2024 (+22.8%** over $66.3B in
2023); CAGR 23.5% (2015–2024). Hospitals = 87% of purchases; DSH ~78%. WAC list
value $147.8B (2024); the list-to-340B gap (≈entity benefit) was $66.4B. 340B is
now ~19% of the total brand gross-to-net bubble ($356B in 2024). Top-10 drugs ≈
one-third of purchases. The specialty channel = 40% of units but 61.5% ($50.1B)
of spend.

**(d) Economics/controversy.** Minnesota transparency reports: $1.34B net 340B
revenue (2024) vs $630M (2023, dispensed-only — the jump reflects adding
clinician-administered drugs). An NPC study tied 340B growth to ~$23B/yr in
higher employer premiums. Manufacturers have imposed contract-pharmacy
restrictions; IRA pressure is expected to slow growth beginning 2026.

**(e) Policy.** CMS declined to finalize the 2026 OPPS 340B "offset" remedy but
will survey hospital acquisition costs → likely lower future 340B reimbursement.
The 2026 PFS finalized 340B data-collection changes.

**(f) Data sources.** HRSA OPA; Drug Channels Institute; GAO; Minnesota DOH;
MedPAC; CBO; NPC.

**Charts:** line — 340B purchase growth; bar — purchases by entity type;
waterfall — list-to-340B gap.

## 15. Infusion pharmacy / home infusion

**(a) Codes.** Per-diem S-codes (HIPAA-standard since 2002): S9325–S9379 by
therapy (e.g., S9494 antibiotics, S9347 TPN). Medicare home-infusion:
G0068–G0070 (professional services per visit-day), J-codes for drugs, B4xxx for
parenteral nutrition. Therapy categories: anti-infectives, parenteral nutrition,
immune globulin, specialty infusion, enteral.

**(b) Population.** ~3.2M patients/yr receive home infusion (NHIA), up from
829,000 (2010). 74.3% of home-infusion patients are age 50+. Acute
(anti-infectives ~half of home volume) plus chronic (IG, biologics, TPN).

**(c) Companies.** >800 independent operators (fragmented; PE consolidation).
Option Care Health is the largest (~$5.65B FY2025 revenue, 8.3% EBITDA margin).

**(d) Operations / site-of-care shift.** US infusion market ~$39.9B in 2025
(IQVIA), up from $32.8B in 2024; ~11% CAGR 2020–2025 (acute ~12%, chronic ~9%).
Non-federal hospitals are losing share to clinics and home (IQVIA channel data).
Home cost ~$122–225/day vs inpatient $586–798/day. Home-care = ~62.5% of infusion
revenue (2024). 137 novel infused drugs approved since 2016; ~400 in development.

**(e) Reimbursement — per-diem.** Commercial plans treat home infusion as a
MEDICAL benefit: a per-diem for clinical services/supplies/equipment plus
separate drug and nursing payments (NHIA per-diem definition; valid for therapies
≤72 hr). The Medicare home-infusion benefit is narrow/fragmented (G0068–G0070
payable only on infusion days), limiting provider participation. H.R. 4993 (Joe
Fiandra Access to Home Infusion Act, 2026) would expand pump-required drug
coverage. The 2025 home health update was +2.7%.

**(f) Data sources.** NHIA *Infusion Industry Trends* (2026); IQVIA; Mordor
Intelligence; CMS home-infusion benefit (market-size figures approximate).

**Charts:** bar — home vs inpatient per-diem cost; line — infusion market growth;
100% stacked bar — site-of-care shift.

---

## Recommendations (build order)

1. **Ingest the 2026 reimbursement shocks first.** The CTP/skin-substitute
   reclassification to $127.28/cm², the PAMA delay to 2027, and the dual PFS
   conversion factors are the largest near-term operational disruptions, hitting
   wound care, podiatry, and labs hardest. Model wound-center and podiatry
   revenue under the flat CTP rate (and the loss of wastage billing) before any
   other refresh.
2. **Build the "drug-dollar" layer (specialty pharmacy, PBMs, 340B, GPOs, home
   infusion) as one connected module** — these share the gross-to-net/rebate
   datasets (DCI, IQVIA, HRSA) and are the highest-dollar, fastest-growing
   segments. Prioritize the 340B line ($81.4B, +22.8%) and the PBM
   80%-concentration series as flagship visualizations.
3. **Anchor every vertical to a named primary dataset** (CMS final rules, MedPAC
   Ch. 8/9, HRSA OPA, BLS OES, NHIA, AASM, IQVIA, Drug Channels) so each chart
   can be auto-refreshed and source-traced.
4. **Watch these thresholds that would change the analysis:** PAMA cuts resuming
   Jan 1 2027 (~820 tests, up to -15%/yr); CTP 2027 differentiated APC rates; any
   federal ground-ambulance NSA fix; IRA-driven 340B slowdown beginning 2026;
   passage of H.R. 4993 (home infusion) and the RESULTS Act (lab payment).

## Caveats

- Market-size figures from commercial research firms (Grand View, Mordor, Fortune
  Business Insights, MarketsandMarkets) vary widely by definition and scope and
  should be treated as approximate ranges, not precise points.
- Chiropractor and several workforce employment counts cite BLS OOH/OEWS but the
  chiropractor headcount specifically requires direct BLS verification.
- GPO and PBM market shares differ by metric (staffed beds vs purchase volume vs
  claims processed vs rebate-negotiation lives); the report notes which metric
  each figure reflects.
- PACE per-member capitation rates and IRF/LTACH margins are MedPAC and state
  estimates, not audited universal figures.
- "~70% of medical decisions rely on labs" is a widely cited but imprecise figure
  (range 70–80%) tracing to a CDC/Lewin Group basis.
- Specialty pharmacy revenue, accreditation counts, and pharmacy rankings are
  Drug Channels Institute estimates; the 340B net-revenue extrapolations beyond
  Minnesota are modeled, not directly reported nationally.
- The 2024-vs-2025 IQVIA net-drug-spend figures differ slightly between editions
  ($487B net 2024 vs earlier $494.9B spending figures) due to net-vs-list and
  edition timing; the net figure is used as primary.
