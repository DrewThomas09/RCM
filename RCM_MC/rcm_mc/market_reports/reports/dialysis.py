"""Dialysis — in-center + home renal replacement therapy for ESRD.

Rich-data flagship: consumes ``dialysis_deep_dive()`` (CMS Dialysis Facility
Compare, ~7.5K facilities) for SOURCED live figures, and authors the
qualitative sections from the operating knowledge of a regulated duopoly whose
whole economic model turns on the ~10% of commercial patients.
"""
from __future__ import annotations

from .. import (
    CmsTrend, Competition, Connection, CostDriver, GrowthLever, HowItWorks,
    Kpi, MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule,
    Segment, Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="dialysis",
    name="Dialysis",
    care_setting="Ambulatory",
    naics="621492",
    one_line_def=(
        "Chronic renal replacement therapy for end-stage renal disease (ESRD) "
        "patients — thrice-weekly in-center hemodialysis plus home HD and "
        "peritoneal dialysis — reimbursed through a bundled Medicare per-"
        "treatment rate."),
    tam_headline=TamHeadline(
        value=24.0, unit="$B", growth_pct=2.5, basis_label="GOV",
        basis_note=(
            "US in-center dialysis-services revenue ~$24B (USRDS/CMS ESRD "
            "program); growth is the modeled composite of the TAM/SAM drivers "
            "(incidence +1.8%, rate +2.2%, home-shift −1.5%)."),
    ),
    executive_summary=[
        "A regulated duopoly: DaVita and Fresenius run roughly 70-75% of US "
        "dialysis stations. There is no platform to build at the top — the "
        "acquirable market is the independent and nephrologist-JV long tail.",
        "The whole economic model is the commercial cliff. ~10% of patients "
        "carry commercial insurance and the majority of clinic EBITDA; when "
        "they age into Medicare at month 30-33 the rate collapses from "
        "$1,000+ to the ~$280 bundle. Value = commercial census × time-to-"
        "Medicare.",
        "Demand is demographic and non-discretionary (diabetes/hypertension → "
        "ESRD) and grows ~2%/yr, but CMS is actively pulling patients out of "
        "the in-center chair via the ESRD Treatment Choices model and the "
        "home-dialysis push.",
        "The 2021 Medicare Advantage carve-in (21st Century Cures) let ESRD "
        "patients enroll in MA — reshaping the payer mix and shrinking the "
        "commercial pool that funds the margin.",
        "Regulatory tail risk is concentrated and specific: charitable "
        "premium-assistance (American Kidney Fund) plumbing, the Marietta v. "
        "DaVita ruling, state anti-steering laws, and the DaVita DOJ history.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "CKD progression → nephrologist referral at ESRD (eGFR <15)",
            "Vascular access placed (AV fistula preferred; graft or catheter)",
            "Dialysis prescription + modality choice (in-center HD / home)",
            "Treatment delivery — ~3×/week, ~4 hours in-center",
            "Anemia, mineral-bone and lab management (monthly panels)",
            "Billing — Medicare ESRD PPS bundle or commercial multiple",
            "Quality reporting — ESRD QIP + ETC model attribution",
        ],
        sites_of_care=[
            "In-center hemodialysis clinic (the volume + revenue base)",
            "Home hemodialysis (CMS-favored, growing off a small base)",
            "Home peritoneal dialysis (nocturnal / CAPD)",
            "Acute inpatient dialysis (hospital-contracted)",
            "SNF-based dialysis (Dialyze Direct-style, a growth pocket)",
        ],
        money_flow=(
            "Medicare pays a bundled per-treatment PPS rate (base ~$275-280 "
            "in CY2024) that folds in the dialysis session plus formerly "
            "separately-billed drugs (ESAs, IV iron) and labs. Commercial "
            "payers pay a large multiple of Medicare — often 3-6× — so the "
            "clinic P&L is a fixed-cost chassis (chairs, techs, a nephrologist "
            "medical director) against which every commercial patient is "
            "nearly pure contribution margin. Nephrologists bill their monthly "
            "capitation (MCP) separately. The single lever that moves clinic "
            "value is the commercial mix and how long those patients stay "
            "commercial before the 30-month Medicare-secondary window ends."),
        key_players=(
            "Two national chains dominate: DaVita and Fresenius Medical Care. "
            "The next tier is US Renal Care, Innovative Renal Care (formerly "
            "American Renal), Satellite Healthcare, and the home/SNF-focused "
            "Dialyze Direct. Growth at the chains comes from de novo clinics "
            "and joint ventures with nephrology groups (the referral source), "
            "not from buying independents. Value-based nephrology risk-bearers "
            "— Interwell Health, Strive, Somatus — sit upstream, taking risk "
            "on the CKD-to-ESRD transition itself."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Commercial-insured patients (~10% of patients)",
                    "majority of clinic EBITDA",
                    "GOV · USRDS modality/coverage mix"),
            Segment("Medicare / Medicare Advantage patients",
                    "~74% of patients",
                    "ILLUSTRATIVE · TAM/SAM patient split (USRDS-anchored)"),
            Segment("Medicaid / other patients",
                    "~16% of patients",
                    "ILLUSTRATIVE · TAM/SAM patient split"),
            Segment("Home modality share of dialysis",
                    "~14% and rising (CMS target)",
                    "GOV · USRDS modality mix"),
        ],
        growth_drivers=[
            "ESRD incidence growth ~1.8%/yr — diabetes and hypertension driven",
            "Annual PPS + commercial rate updates ~2.2%/yr",
            "Home-modality shift −1.5%/yr — CMS ETC pulls volume from the chair",
            "MA carve-in erodes the commercial pool that funds margin",
            "Longer run: GLP-1 / SGLT2 adoption may slow CKD progression",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Medicare / MA": 0.74,
            "Commercial": 0.10,
            "Medicaid / other": 0.16,
        },
        rate_mechanics=[
            "ESRD Prospective Payment System (PPS) — a bundled per-treatment "
            "rate (SSA §1881); the base rate + case-mix + wage index set FFS.",
            "TDAPA / TPNIES — transitional add-on payments for new drugs and "
            "equipment before they fold into the bundle.",
            "ESRD Quality Incentive Program (QIP) — pay-for-performance; up to "
            "a 2% payment reduction for poor quality scores.",
            "ESRD Treatment Choices (ETC) Model — mandatory in selected "
            "regions; bonuses/penalties to push home dialysis and transplant.",
            "Commercial multiple of Medicare — the EBITDA engine; the 30-month "
            "Medicare Secondary Payer window is when the clinic earns it.",
            "MA carve-in (2021) — ESRD patients may now enroll in Medicare "
            "Advantage; MA network/rate leverage reshapes the payer mix.",
        ],
        reimbursement_risk=(
            "The commercial cliff is the whole risk: patients roll to Medicare "
            "as primary at month 30-33, and Medicare's ~$280 bundle is a "
            "fraction of the commercial rate, so a clinic's economics decay "
            "with its commercial book's age. Two structural threats compound "
            "it — the MA carve-in shrinks the commercial pool, and the "
            "Marietta Memorial Hospital v. DaVita ruling (SCOTUS, 2022) let "
            "group health plans set uniformly low dialysis benefits, pressuring "
            "the American Kidney Fund premium-assistance plumbing that "
            "underwrites many commercial premiums. State anti-steering laws "
            "(e.g. California AB-290) attack the same mechanism from the other "
            "direction."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("ESRD Prospective Payment System (PPS)",
                 "Sets the bundled per-treatment rate that governs ~90% of the "
                 "patient base — the single most important price in the sector.",
                 "https://www.cms.gov/medicare/payment/prospective-payment-systems/end-stage-renal-disease-esrd"),
            Rule("ESRD Treatment Choices (ETC) Model",
                 "Mandatory home-dialysis/transplant incentive model — CMS is "
                 "paying to empty the in-center chair a platform is priced on.",
                 "https://www.cms.gov/priorities/innovation/innovation-models/esrd-treatment-choices-model"),
            Rule("Conditions for Coverage (42 CFR 494)",
                 "Survey-and-certification regime; water treatment and "
                 "infection-control deficiencies can shut a clinic.",
                 "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-G/part-494"),
            Rule("Marietta Memorial Hospital v. DaVita (SCOTUS, 2022)",
                 "Held that a plan may set low, uniform dialysis benefits — a "
                 "direct threat to the commercial-rate and AKF premium model.",
                 "https://www.supremecourt.gov/opinions/21pdf/20-1641_1b8e.pdf"),
            Rule("21st Century Cures Act — ESRD MA enrollment (2021)",
                 "Opened Medicare Advantage to ESRD patients, moving the payer "
                 "mix and the negotiating leverage over rates.",
                 None),
        ],
        policy_watch=[
            "MA carve-in rate trajectory and network adequacy rulings",
            "ETC model expansion / permanence and home-dialysis targets",
            "Potential PPS bundle revisions (oral-only ESRD drugs into bundle)",
            "GLP-1 / SGLT2 slowing CKD progression — a long-run demand headwind",
            "Kidney transplant supply growth reducing the dialysis pool",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Roughly 7,500 US dialysis facilities, but concentration is the "
            "story: two national chains hold ~70-75% of stations. The "
            "remainder is regional chains, nephrologist-owned joint ventures, "
            "and true independents — the only acquirable pool, and it is thin "
            "and referral-dependent."),
        hhi_or_share=(
            "Top-2 chain share ≈ 70-75% (DaVita + Fresenius). The live chain "
            "concentration is measured directly from our facility file below."),
        consolidation=(
            "In-center is a mature, buy-and-build-exhausted market. The majors "
            "grow by de novo and nephrology JV rather than platform M&A, and "
            "antitrust limits big-2 tuck-ins. Independents get absorbed by US "
            "Renal Care and regional players. The live PE thesis has migrated "
            "off in-center chairs toward home dialysis, SNF-based dialysis, "
            "and value-based nephrology risk models."),
        pe_activity=(
            "US Renal Care (Bain and co-investors) and Innovative Renal Care "
            "(American Renal) are the marquee sponsor-backed platforms; "
            "Dialyze Direct scaled SNF-based home dialysis; Interwell/Strive/"
            "Somatus attracted growth capital for value-based nephrology. New "
            "in-center roll-ups are rare — the whitespace is upstream (CKD "
            "risk) and adjacent (home, access centers)."),
        notable_players=[
            "DaVita", "Fresenius Medical Care", "US Renal Care",
            "Innovative Renal Care (American Renal)", "Satellite Healthcare",
            "Dialyze Direct", "Interwell Health", "Somatus",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Blended revenue / treatment", "$300-360",
                "Weighted by payer mix; commercial patients pull the blend up "
                "far above the ~$280 Medicare bundle."),
            Kpi("Commercial patient mix", "8-12% of patients",
                "The single biggest determinant of clinic value — the margin "
                "concentrates in this thin slice."),
            Kpi("Treatments / station / week", "~15-18",
                "3 shifts × ~6 days is full utilization; empty chairs kill the "
                "fixed-cost model."),
            Kpi("Clinic EBITDA margin (mature)", "15-22%",
                "High operating leverage — margin is almost entirely a "
                "function of utilization and commercial mix."),
            Kpi("Missed-treatment rate", "3-8%",
                "Missed treatments are lost, non-recoverable revenue on a "
                "fixed-cost base."),
        ],
        margin_profile=(
            "A dialysis clinic is a high-fixed-cost chassis: the chairs, "
            "technicians, nurses, and a nephrologist medical director are "
            "largely fixed, so contribution margin steps up sharply with each "
            "additional treatment and, above all, with each commercial "
            "patient. A mature, well-utilized clinic with a healthy commercial "
            "mix runs mid-to-high-teens EBITDA margin; a Medicare-heavy or "
            "under-filled clinic can be near breakeven on the same cost base."),
    ),
    risks=[
        Risk("Commercial-mix erosion (aging into Medicare + MA carve-in)",
             "High",
             "Directly compresses the margin engine as the commercial book "
             "ages and MA absorbs former commercial lives."),
        Risk("American Kidney Fund / premium-assistance litigation", "High",
             "Marietta ruling + state anti-steering laws threaten the "
             "plumbing that funds commercial premiums for many patients."),
        Risk("CMS home-dialysis shift (ETC) cannibalizing in-center chairs",
             "Medium",
             "The payer is paying to move volume out of the asset base a "
             "buy-and-build thesis is priced on."),
        Risk("Clinical labor shortage (dialysis techs, nurses)", "Medium",
             "Wage inflation and staffing caps limit chair utilization and "
             "de novo growth."),
        Risk("Regulatory / DOJ history and survey exposure", "Medium",
             "Conditions-for-Coverage deficiencies and the sector's DOJ track "
             "record raise compliance diligence stakes."),
        Risk("GLP-1 / SGLT2 slowing CKD-to-ESRD progression", "Low",
             "A genuine long-run demand headwind, but slow to bite within a "
             "typical hold."),
    ],
    diligence_questions=[
        "What is the commercial payer mix by clinic, and what is the age "
        "distribution of the commercial book (months to Medicare-primary)?",
        "How concentrated are missed/no-show treatments, and what is the "
        "trend?",
        "How are medical-director and JV agreements structured against Stark "
        "and Anti-Kickback (fair-market-value, commercial reasonableness)?",
        "What share of commercial premiums rely on American Kidney Fund "
        "charitable assistance, and what is the exposure post-Marietta?",
        "What is the MA-vs-FFS trajectory, and how do MA network rates compare "
        "to the historical commercial book?",
        "What is home-program penetration versus the clinic's ETC targets and "
        "penalties?",
        "What is the survey/deficiency history (water treatment, infection "
        "control) and any open CMS corrective actions?",
    ],
    insider_lens=[
        "Ten percent of patients, most of the EBITDA. A clinic's value is its "
        "commercial census and how long those lives stay commercial before "
        "aging into the Medicare bundle at month 33 — everything else is "
        "supporting cast.",
        "The duopoly does not buy independents to grow; it de novos and JVs "
        "with nephrologists. So an independent's real value is its referral "
        "relationships — which do not always transfer with the real estate.",
        "The American Kidney Fund quietly underwrites a slice of commercial "
        "premiums; Marietta and state anti-steering laws are pulling on that "
        "thread, and the whole commercial-rate thesis is downstream of it.",
        "Buy-and-build in in-center is essentially over. The live PE thesis "
        "moved upstream to value-based nephrology (owning the CKD-to-ESRD "
        "transition) and sideways to home and SNF dialysis.",
        "CMS wants patients out of the chair — home plus transplant. A "
        "platform priced on in-center chair growth is betting against the "
        "payer's own incentive design (the mandatory ETC model).",
    ],
    connections=default_connections(
        "dialysis",
        deals_sector="dialysis",
        extra_pages=[
            ("/dialysis", "Dialysis vertical — CMS Care Compare facility view"),
        ],
        connectors=[
            ("provider_data_catalog",
             "CMS Provider Data Catalog — Dialysis Facility Compare"),
            ("cms_open_data_catalog", "CMS Open Data — ESRD program datasets"),
            ("npi_provider", "NPI Registry — nephrology providers & facilities"),
            ("icd10_cm", "ICD-10-CM — N18 CKD / ESRD diagnosis codes"),
        ],
    ),
    sources=[
        Source("USRDS Annual Data Report — ESRD incidence, prevalence, and "
               "modality mix", "GOV",
               "https://usrds-adr.niddk.nih.gov/"),
        Source("CMS ESRD Prospective Payment System — annual Final Rule "
               "(bundle base rate, QIP, wage index)", "GOV",
               "https://www.cms.gov/medicare/payment/prospective-payment-systems/end-stage-renal-disease-esrd"),
        Source("MedPAC — Report to Congress, outpatient dialysis services "
               "chapter", "GOV", "https://www.medpac.gov/"),
        Source("Marietta Memorial Hospital Employee Health Benefit Plan v. "
               "DaVita Inc., 596 U.S. 880 (2022)", "ACADEMIC",
               "https://www.supremecourt.gov/opinions/21pdf/20-1641_1b8e.pdf"),
        Source("ESRD Treatment Choices (ETC) Model — CMS Innovation Center",
               "GOV",
               "https://www.cms.gov/priorities/innovation/innovation-models/esrd-treatment-choices-model"),
        Source("PE Desk industry deep-dive (CMS Dialysis Facility Compare) + "
               "realized-deal corpus", "INTERNAL",
               "/diligence/tam-sam?template=dialysis"),
    ],
    live_figures=live_figures_from_dive("dialysis"),
    trends=(
        "The in-center trajectory bends around three policy events. The 2011 "
        "ESRD PPS bundle folded the once-lucrative separately-billable drugs "
        "(ESAs, IV iron) into a single per-treatment rate and reset the whole "
        "P&L around efficiency and utilization. The 2021 Medicare Advantage "
        "carve-in (21st Century Cures) let ESRD patients enroll in MA, which "
        "has been steadily eroding the ~10% commercial pool that carries clinic "
        "margin. And the mandatory ESRD Treatment Choices (ETC) model is CMS "
        "paying to move volume out of the in-center chair toward home dialysis "
        "and transplant. Underneath, in-center is a mature, consolidation-"
        "exhausted duopoly; the live capital has migrated upstream to value-"
        "based nephrology (owning the CKD-to-ESRD transition) and sideways to "
        "home and SNF-based dialysis. The demand base keeps growing ~2%/yr, but "
        "every structural policy vector points volume and margin the other way."),
    growth_levers=[
        GrowthLever(
            "ESRD prevalence (diabetes / hypertension / aging)",
            "The prevalent dialysis-dependent population expands structurally "
            "as diabetes, hypertension, and aging drive incident ESRD — non-"
            "discretionary demand.",
            "+1.8%/yr incidence", "GOV"),
        GrowthLever(
            "PPS + commercial rate updates",
            "The bundle base rate and commercial multiples step up with the "
            "annual ESRD PPS Final Rule and payer negotiations.",
            "+2.2%/yr rate", "ILLUSTRATIVE"),
        GrowthLever(
            "Home-modality shift (ETC model)",
            "CMS pays to move patients from the in-center chair to home HD/PD — "
            "grows the home segment while shrinking the in-center asset base a "
            "buy-and-build thesis is priced on.",
            "−1.5%/yr in-center", "GOV"),
        GrowthLever(
            "MA carve-in (2021 Cures Act)",
            "ESRD patients may now enroll in Medicare Advantage, reshaping the "
            "payer mix and shrinking the commercial pool that funds margin.",
            "mix shift · margin drag", "GOV"),
        GrowthLever(
            "Home & SNF-based whitespace",
            "Dialyze Direct-style SNF dialysis and value-based nephrology risk "
            "models are the live growth pockets versus a mature in-center core.",
            "platform-dependent", "ILLUSTRATIVE"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="ESRD prevalence (via diabetes, hypertension, and aging)",
        analysis=(
            "The single dominant demand driver is the prevalent ESRD "
            "population, not a discretionary utilization choice: once a patient "
            "reaches end-stage renal disease they need thrice-weekly renal "
            "replacement to live. USRDS counts well over 800,000 prevalent ESRD "
            "patients with roughly 70% on dialysis (the rest transplanted), and "
            "incidence grows ~1.8%/yr — diabetes alone accounts for ~45-47% of "
            "incident cases, with hypertension the next largest. That makes the "
            "demand curve demographic and highly predictable. The two credible "
            "long-run offsets are both slow: GLP-1 / SGLT2 adoption may blunt "
            "CKD-to-ESRD progression, and kidney-transplant supply growth pulls "
            "a small share out of the dialysis pool — neither bites materially "
            "within a typical hold."),
        basis="GOV"),
    cost_drivers=[
        CostDriver(
            "Clinical labor (RNs, patient-care techs, dietitians)",
            "~40-50% of cost",
            "The dominant, largely fixed cost — techs and nurses run the "
            "chairs. Wage inflation and staffing caps directly limit chair "
            "utilization and de novo growth.", "ILLUSTRATIVE"),
        CostDriver(
            "In-bundle drugs (ESAs, IV iron, calcimimetics)",
            "~20-25% of cost",
            "Anemia and mineral-bone agents plus oral calcimimetics are folded "
            "into the PPS bundle — a cost the clinic absorbs rather than bills "
            "separately, so drug-management efficiency is pure margin.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Facility & machines (rent, RO water, dialysis machines)",
            "~10-15% of cost",
            "The fixed chassis — real estate, reverse-osmosis water treatment, "
            "and the dialysis machines. De novo capex and water-system "
            "compliance gate expansion.", "ILLUSTRATIVE"),
        CostDriver(
            "Consumable supplies (dialyzers, tubing, saline)",
            "~10-15% of cost",
            "Per-treatment consumables — the main variable cost, scaling "
            "directly with treatment volume.", "ILLUSTRATIVE"),
        CostDriver(
            "Medical direction & G&A",
            "~5-10% of cost",
            "Nephrologist medical-director fees (Stark / Anti-Kickback-"
            "sensitive) plus corporate overhead.", "ILLUSTRATIVE"),
    ],
    cms_trend=CmsTrend(
        takeaway=(
            "The policy inflection is the 2011 ESRD PPS bundle, which folded "
            "the separately-billable drugs into one per-treatment rate and "
            "reset clinic economics around efficiency. Our facility roll shows "
            "the in-center build wave cresting in the mid-2010s and "
            "decelerating after — the fingerprint of a mature, consolidation-"
            "exhausted market where CMS is now actively pushing volume home via "
            "the ETC model rather than into new chairs."),
        chart_kind="bars"),
    state_breakdown=(
        "The South and Sun Belt anchor the chair base (Texas, California, "
        "Florida, Georgia lead), for-profit ownership is near-universal "
        "(~90%), and the chain layer is a genuine duopoly — DaVita and "
        "Fresenius together hold roughly three-quarters of facilities, the "
        "highest chain concentration in post-acute. The acquirable pool is the "
        "thin independent and nephrologist-JV tail, concentrated in a handful "
        "of large states."),
)

register(REPORT)
