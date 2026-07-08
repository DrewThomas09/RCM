"""Vascular Access — dialysis-access & central-venous-access interventions in OBLs.

Deals-only pattern (OBL/access-center rosters aren't public; the adjacent
dialysis facility map stands in for the referral pool). Authored around the two
things that define the niche: a captive, recurring procedural annuity on the
ESRD dialysis population (fistulas and grafts re-stenose and must be kept
patent), and the site-of-service arbitrage of doing those cases in a physician
office-based lab (OBL) or ASC instead of the hospital — an economic engine that
is also a Stark/AKS and site-neutral-payment risk. Live SOURCED figures come
from ``vascular_access_deep_dive()``.
"""
from __future__ import annotations

from .. import (
    Competition, CostDriver, GrowthLever, HowItWorks, Kpi, MarketReport,
    MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment, Source,
    TamHeadline, UnitEconomics, VolumeDriver, default_connections,
    live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="vascular_access",
    name="Vascular Access",
    care_setting="Ambulatory",
    naics="621111",
    one_line_def=(
        "Placement and maintenance of vascular access — creation and upkeep of "
        "dialysis AV fistulas/grafts (angioplasty, thrombectomy, declots) and "
        "central venous access (PICC lines, ports, tunneled catheters) — "
        "delivered increasingly in office-based labs (OBLs) and ambulatory "
        "access centers rather than the hospital OR."),
    tam_headline=TamHeadline(
        value=4.5, unit="$B", growth_pct=4.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "Modeled US vascular-access services market — dialysis-access "
            "maintenance for the ESRD population plus central-venous-access "
            "placement. Anchored on the ~550K in-center dialysis patients "
            "(USRDS), each requiring recurring access surveillance and "
            "intervention, plus CVC/PICC/port volumes. The value driver is the "
            "site-of-service shift to lower-cost OBL/ASC settings, not raw "
            "volume growth. ILLUSTRATIVE."),
    ),
    executive_summary=[
        "The business is a captive, recurring annuity on the dialysis "
        "population: an ESRD patient's fistula or graft is their lifeline and "
        "needs periodic angioplasty/thrombectomy to stay patent, so a dialysis-"
        "access practice earns predictable, repeat procedural revenue tied to "
        "the local dialysis census.",
        "The whole margin story is site-of-service arbitrage. Moving these "
        "procedures out of the hospital outpatient department into physician "
        "office-based labs (OBLs) and ASCs captures the technical/facility "
        "payment at the practice, at lower cost — the reason OBLs proliferated.",
        "Ownership economics collide with Stark/Anti-Kickback: nephrologists "
        "who own an access center and refer their own dialysis patients into it "
        "are the textbook self-referral fact pattern — structure and referral "
        "compliance are diligence item #1.",
        "Reimbursement is CPT/MPFS-driven and has already been cut once: the "
        "2017 bundling of dialysis-circuit codes (36901-36909) compressed per-"
        "procedure revenue, and site-neutral payment pressure is the standing "
        "threat.",
        "It's fragmented — nephrologist-owned centers and IR/cardiology OBLs — "
        "with one scaled strategic (Fresenius's Azura Vascular Care); the "
        "acquirable pool is the independent physician-owned access center.",
        "Adjacent OBL procedures (peripheral-artery-disease atherectomy/"
        "angioplasty) rode the same economics but drew OIG/overutilization "
        "scrutiny — a cautionary read-across for the whole OBL roll-up thesis.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Dialysis unit / nephrologist detects access dysfunction (low flows, clotting)",
            "Referral to the access center + fistulogram / imaging",
            "Intervention (angioplasty, thrombectomy, stent, declot) or new-access creation",
            "Central venous access placement where indicated (PICC / port / tunneled)",
            "Same-day discharge back to dialysis",
            "Billing under MPFS/OPPS by site of service",
            "Surveillance & repeat as the circuit re-stenoses — the annuity",
        ],
        sites_of_care=[
            "Office-based lab (OBL) / freestanding vascular access center",
            "Ambulatory surgery center (ASC)",
            "Hospital outpatient department (HOPD)",
            "Bedside / mobile PICC teams (hospitals and SNFs)",
        ],
        money_flow=(
            "The procedures are billed under the Medicare Physician Fee "
            "Schedule and its commercial equivalents, with the economics "
            "decided by where the case is done. In a hospital outpatient "
            "department, the hospital captures a facility fee under OPPS and the "
            "physician bills only the professional component; in a physician-"
            "owned office-based lab, the practice bills the global service — "
            "professional plus the practice-expense (technical) component — "
            "keeping the facility economics in-house at lower cost. That OBL "
            "'global' capture is the arbitrage that built the segment. Dialysis-"
            "circuit interventions (CPT 36901-36909, restructured and bundled "
            "in 2017) are the recurring core; CVC/PICC/port placements add "
            "episodic volume; an ASC setting pays an ASC facility fee instead. "
            "Payment is per procedure, so throughput and case mix drive "
            "revenue."),
        key_players=(
            "A fragmented field of nephrologist-owned access centers and "
            "interventional radiology/cardiology office-based labs, with "
            "Fresenius's Azura Vascular Care (built on American Access Care and "
            "other roll-ups) the scaled national strategic. Interventional "
            "nephrologists, interventional radiologists, and vascular surgeons "
            "are the operating physicians; the referral source is the local "
            "dialysis population (often the same nephrology groups); and device "
            "makers (BD/Bard, Boston Scientific, Medtronic) sit upstream."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Dialysis-access maintenance (angioplasty/thrombectomy/declot)",
                    "the recurring core, tied to ESRD census",
                    "GOV · USRDS ESRD population"),
            Segment("New AV access creation (fistula / graft)",
                    "lower-frequency, higher-acuity",
                    "INDUSTRY · vascular procedure mix"),
            Segment("Central venous access (PICC / port / tunneled catheter)",
                    "episodic; hospital & SNF bedside",
                    "ILLUSTRATIVE · CVC placement volumes"),
            Segment("Site-of-service mix (OBL/ASC vs HOPD)",
                    "the shift OBLs are built on",
                    "GOV · CMS OPPS / MPFS site differential"),
            Segment("Adjacent PAD interventions in the same OBL",
                    "same economics, more scrutiny",
                    "INDUSTRY · OBL procedure mix"),
        ],
        growth_drivers=[
            "ESRD prevalence growth — the recurring referral pool",
            "Continued site shift HOPD → OBL/ASC (the arbitrage)",
            "Aging / oncology / infusion / TPN driving CVC demand",
            "Interventional-nephrology adoption expanding access-center supply",
            "Offset: reimbursement cuts (2017 bundling) and site-neutral pressure",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Medicare / MA": 0.75,
            "Commercial": 0.12,
            "Medicaid / other": 0.13,
        },
        rate_mechanics=[
            "Medicare Physician Fee Schedule — the dialysis-circuit and access "
            "codes (36901-36909; PICC/port codes) pay a professional component "
            "plus, in a non-facility office setting, the practice-expense "
            "(technical) component — the OBL 'global' capture.",
            "Site-of-service differential (OPPS vs MPFS vs ASC) — the same "
            "procedure pays differently in an HOPD (hospital facility fee), an "
            "OBL (physician global), or an ASC (ASC facility fee); the OBL "
            "arbitrage is the engine and the site-neutral target.",
            "2017 dialysis-circuit CPT bundling — the 36901-36909 restructuring "
            "bundled previously separately-billed components and cut per-"
            "procedure revenue; a reminder CMS can reprice the core.",
            "ESRD referral linkage — volume is downstream of the dialysis "
            "census; the nephrologist's referral is the demand valve (and the "
            "AKS pressure point).",
            "Prior authorization & overutilization review — payers scrutinize "
            "repeat-angioplasty frequency and (in adjacent PAD) atherectomy "
            "utilization.",
        ],
        reimbursement_risk=(
            "Two specific threats. First, site-neutral payment: the entire OBL "
            "model depends on the office (or ASC) capturing facility-type "
            "economics; any move to equalize payment across sites removes the "
            "arbitrage. Second, CMS repricing of the core codes — the 2017 "
            "dialysis-circuit bundling already cut per-procedure revenue, and "
            "repeat-intervention frequency is an overutilization-audit target. "
            "Layer on the Stark/AKS exposure of nephrologist self-referral, and "
            "the durable value sits with clean-structured, high-throughput "
            "centers whose volume survives a rate cut — not with a practice "
            "priced on today's per-procedure economics."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("Stark Law (self-referral) & Anti-Kickback Statute",
                 "Nephrologist ownership of an access center receiving their own "
                 "dialysis referrals is the central compliance question — the "
                 "economics and the legal risk are the same relationship.",
                 "https://oig.hhs.gov/"),
            Rule("Medicare site-of-service / OPPS vs MPFS payment policy",
                 "Sets the OBL/ASC vs HOPD payment differential the model is "
                 "built on; site-neutral proposals are the standing threat.",
                 "https://www.cms.gov/medicare/payment/prospective-payment-systems"),
            Rule("ASC Conditions for Coverage / state OBL accreditation",
                 "Where the setting is an ASC or accredited OBL, CoP/"
                 "accreditation and state office-based-surgery rules apply.",
                 "https://www.cms.gov/"),
            Rule("OIG overutilization scrutiny (repeat angioplasty; PAD atherectomy)",
                 "Enforcement attention on intervention frequency and medically-"
                 "unnecessary procedures — the adjacent PAD/atherectomy episode "
                 "is the precedent.",
                 "https://oig.hhs.gov/"),
            Rule("Radiation safety & FDA device regulation",
                 "Fluoroscopy/imaging and the balloons/stents/thrombectomy "
                 "devices are FDA-regulated; state radiation-safety rules apply.",
                 "https://www.fda.gov/medical-devices"),
        ],
        policy_watch=[
            "Site-neutral payment expansion equalizing OBL/HOPD rates",
            "Further CMS repricing of dialysis-circuit / interventional codes",
            "OIG/DOJ actions on OBL overutilization (the PAD atherectomy precedent)",
            "Interventional-nephrology scope and OBL accreditation standards",
            "ESRD value-based models (ETC) changing access-management incentives",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Highly fragmented — independent nephrologist-owned access centers "
            "and IR/cardiology OBLs dominate, with procedures having migrated "
            "out of hospital ORs. Barriers are a lab, imaging, and a "
            "proceduralist, so local independents are the norm."),
        hhi_or_share=(
            "One scaled national strategic — Fresenius's Azura Vascular Care — "
            "sits atop a long independent tail; beyond it, share is diffuse. "
            "OBL rosters aren't public and no facility census is vendored, so "
            "precise share is honestly unquantified — the dialysis facility map "
            "(the referral pool) and the deal history below are the real "
            "anchors."),
        consolidation=(
            "Fresenius rolled up access centers (American Access Care and "
            "others) into Azura, integrating access with its dialysis "
            "footprint; IR and cardiology OBL platforms consolidate regionally. "
            "The thesis is capturing the dialysis-access annuity and the site-"
            "of-service spread; the caution is the adjacent PAD/atherectomy "
            "roll-ups that drew overutilization scrutiny."),
        pe_activity=(
            "Sponsor activity tracks the broader OBL/ASC arbitrage — backing "
            "interventional OBL and access-center platforms — but the vascular-"
            "access niche is small and referral-dependent, and the PAD-"
            "atherectomy episode made underwriters wary of volume built on "
            "aggressive intervention frequency. The cleaner theses are "
            "dialysis-linked access management and CVC/PICC service lines with "
            "defensible medical necessity."),
        notable_players=[
            "Azura Vascular Care (Fresenius)", "American Access Care (now Azura)",
            "Independent interventional-nephrology access centers",
            "IR / cardiology OBL platforms", "Hospital-based access services",
            "BD / Bard", "Boston Scientific", "Medtronic",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Procedures per room per day", "throughput",
                "The fixed-cost OBL leverage — utilization of the imaging suite "
                "and proceduralist."),
            Kpi("Case mix (recurring maintenance vs one-time CVC/new access)",
                "annuity vs episodic",
                "Recurring dialysis-access maintenance is the predictable "
                "annuity; CVC/new access is episodic."),
            Kpi("Referral capture from local dialysis census", "demand base",
                "The captive demand pool — and the AKS-sensitive referral "
                "valve."),
            Kpi("Revenue per procedure", "site-of-service dependent",
                "The arbitrage the model is priced on — OBL global vs HOPD "
                "professional-only."),
            Kpi("Supply cost per case (balloons, stents, contrast)", "the variable line",
                "The main variable cost; vendor contracting is margin."),
            Kpi("Repeat-intervention interval", "clinical & audit-relevant",
                "Too-frequent re-intervention flatters revenue and invites "
                "overutilization scrutiny."),
        ],
        margin_profile=(
            "An office-based access lab is a high-fixed-cost room (imaging "
            "suite, staff, proceduralist) whose margin turns on throughput and "
            "on capturing the technical/facility economics the hospital would "
            "otherwise keep. Recurring dialysis-access maintenance fills the "
            "schedule predictably; device/supply cost is the main variable "
            "line. Margins are attractive while the site-of-service spread "
            "holds and volume is defensible, but they compress with any rate "
            "cut (as in 2017) or site-neutral change — so the margin is as much "
            "a policy position as an operating one. Ranges are ILLUSTRATIVE — "
            "confirm against the target's own financials."),
    ),
    risks=[
        Risk("Site-neutral payment / OBL arbitrage removal", "High",
             "The model's core economics depend on the site-of-service "
             "differential; equalizing it removes the spread."),
        Risk("Stark / AKS self-referral exposure", "High",
             "Nephrologist ownership referring own dialysis patients is the "
             "classic self-referral fact pattern."),
        Risk("CMS code repricing (post-2017 precedent)", "High",
             "The core dialysis-circuit codes have been cut before and can be "
             "cut again."),
        Risk("OIG overutilization scrutiny (repeat angioplasty / PAD)", "Medium",
             "Intervention-frequency audits and the atherectomy precedent."),
        Risk("Referral concentration / dialysis-linkage", "Medium",
             "Volume depends on a captive dialysis census and specific "
             "referrers that may not transfer."),
        Risk("Small, niche, key-proceduralist dependence", "Medium",
             "A thin market in which a few interventionalists can be most of a "
             "center's volume."),
    ],
    diligence_questions=[
        "What share of volume is recurring dialysis-access maintenance vs "
        "episodic CVC/new-access, and how tied is it to the local dialysis "
        "census?",
        "How is ownership/referral structured against Stark/AKS — do referring "
        "nephrologists have equity, and does the arrangement fit a safe harbor?",
        "What is the site-of-service mix (OBL/ASC/HOPD), and how exposed is "
        "revenue to a site-neutral payment change?",
        "What is the repeat-intervention frequency versus benchmarks, and is "
        "there any overutilization / audit exposure?",
        "How concentrated is referral in a few dialysis units or nephrology "
        "groups, and do those relationships transfer?",
        "What was the revenue impact of the 2017 dialysis-circuit bundling, and "
        "how would a further code cut flow through?",
        "What is device/supply cost per case and the contract pricing with "
        "balloon/stent vendors?",
    ],
    insider_lens=[
        "The dialysis chair is the demand engine. A fistula or graft is an ESRD "
        "patient's lifeline; it re-stenoses and clots on a schedule, so access "
        "maintenance is a recurring, captive, high-visibility annuity tied "
        "directly to the local dialysis census — underwrite the census, not the "
        "procedure count.",
        "The whole model is a site-of-service trade. Doing the case in a "
        "physician-owned OBL instead of the hospital captures the facility "
        "economics at lower cost. That spread built the segment — and it's "
        "exactly what site-neutral payment policy exists to erase, so the "
        "margin is partly a bet on CMS not acting.",
        "The referral loop is the compliance loop. The nephrologist who sends "
        "the patient often owns the center — the textbook Stark/AKS self-"
        "referral pattern. The economics and the legal risk are the same "
        "relationship; the structure IS the diligence.",
        "CMS has already shown it will reprice the core. The 2017 bundling of "
        "the dialysis-circuit codes cut per-procedure revenue overnight; anyone "
        "paying for today's per-case economics is exposed to the next "
        "revision.",
        "The PAD-atherectomy episode is the cautionary read-across. The same "
        "OBL arbitrage drove aggressive peripheral-artery intervention volumes "
        "that drew OIG/DOJ overutilization scrutiny — a warning that volume "
        "built on intervention frequency is fragile and reputationally risky.",
        "It's a small, thin, proceduralist-dependent niche. A handful of "
        "interventionalists can be most of a center's volume; the scaled "
        "strategic (Azura) is dialysis-integrated. Independent platforms live "
        "and die on referral relationships and clean structure, not scale.",
    ],
    connections=default_connections(
        "vascular_access",
        deals_sector="vascular_access",
        extra_pages=[
            ("/dialysis",
             "Dialysis vertical — the referral pool (CMS Care Compare facilities)"),
        ],
        connectors=[
            ("cms_open_data_dialysis_facilities",
             "CMS ESRD / Dialysis Facilities — the local dialysis census (referral pool)"),
            ("cms_open_data_mup_physician_by_provider_service",
             "CMS Physician & Other Practitioners — access-procedure volumes (36901-36909, PICC/port)"),
            ("npi_provider",
             "NPI Registry — interventional nephrology / IR / vascular surgery"),
            ("openfda_device_510k",
             "openFDA 510(k) — angioplasty balloons, stents, thrombectomy devices"),
            ("cms_open_data_market_saturation_cbsa",
             "CMS Market Saturation — utilization / provider density by CBSA"),
        ],
    ),
    sources=[
        Source("USRDS Annual Data Report — ESRD population, vascular-access "
               "modality, and interventions", "GOV",
               "https://usrds-adr.niddk.nih.gov/"),
        Source("CMS Medicare Physician Fee Schedule & OPPS — site-of-service "
               "payment and the dialysis-circuit codes", "GOV",
               "https://www.cms.gov/medicare/payment/fee-schedules"),
        Source("HHS OIG — overutilization & self-referral enforcement "
               "(office-based labs / atherectomy)", "GOV", "https://oig.hhs.gov/"),
        Source("KDOQI (National Kidney Foundation) — clinical practice "
               "guidelines for vascular access", "ACADEMIC",
               "https://www.kidney.org/"),
        Source("MedPAC — Report to Congress, site-neutral payment and "
               "ambulatory payment-differential analysis", "GOV",
               "https://www.medpac.gov/"),
        Source("PE Desk industry deep-dive (vascular access) + realized-deal "
               "corpus", "INTERNAL",
               "/diligence/tam-sam?template=vascular_access"),
    ],
    live_figures=live_figures_from_dive("vascular_access"),
    trends=(
        "Vascular access has ridden the ambulatory migration that reshaped "
        "procedural medicine: dialysis-access interventions and central-venous "
        "placements moved out of the hospital OR into physician office-based "
        "labs and ASCs, where the practice captures the facility economics at "
        "lower cost. That site-of-service arbitrage, layered on a captive and "
        "growing ESRD referral population, built a recurring procedural annuity "
        "— and drew both roll-up capital (Fresenius's Azura consolidating "
        "access centers) and regulatory attention. CMS repriced the core once "
        "already, bundling the dialysis-circuit codes in 2017, and site-neutral "
        "payment remains the standing threat to the whole OBL premise. The "
        "adjacent PAD/atherectomy boom — same economics, more aggressive "
        "intervention frequency — drew OIG/DOJ overutilization scrutiny and "
        "stands as the cautionary tale. The durable theses are dialysis-"
        "integrated access management and defensible CVC/PICC service lines "
        "with clean Stark/AKS structure; the fragile ones are priced on today's "
        "per-procedure rates and intervention frequency."),
    growth_levers=[
        GrowthLever(
            "ESRD prevalence (the referral pool)",
            "A growing in-center dialysis population expands recurring access-"
            "maintenance demand — non-discretionary and predictable.",
            "+1.8%/yr referral pool", "GOV"),
        GrowthLever(
            "Site-of-service shift HOPD → OBL/ASC",
            "Moving cases to the practice-owned setting captures facility "
            "economics — the segment's margin engine.",
            "arbitrage", "GOV"),
        GrowthLever(
            "CVC/PICC demand (oncology, infusion, TPN, aging)",
            "Episodic central-venous-access volume beyond the dialysis core.",
            "adjacent", "ILLUSTRATIVE"),
        GrowthLever(
            "Interventional-nephrology adoption",
            "More nephrologists building and using access centers expands "
            "supply and captures more of the referral loop.",
            "capacity", "ILLUSTRATIVE"),
        GrowthLever(
            "Reimbursement drag (2017 bundling, site-neutral)",
            "Code repricing and site-neutral pressure remove per-procedure and "
            "site value.",
            "− rate", "GOV"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="ESRD dialysis prevalence (the captive access-maintenance population)",
        analysis=(
            "The dominant demand driver is the in-center dialysis population — "
            "USRDS counts well over 500,000 patients on maintenance dialysis, "
            "each dependent on a functioning AV fistula/graft or catheter that "
            "re-stenoses and thromboses over time and requires recurring "
            "angioplasty, thrombectomy, or declot to stay usable. That makes "
            "access-maintenance volume a predictable, non-discretionary "
            "derivative of the local dialysis census, growing with ESRD "
            "prevalence (~1.8%/yr, diabetes/hypertension-driven) rather than a "
            "utilization choice. Central-venous access (PICCs, ports, tunneled "
            "catheters for oncology, infusion, and TPN) adds episodic volume "
            "tied to aging and cancer care. The demand is durable; the risk is "
            "on price (repricing / site-neutral) and on utilization scrutiny, "
            "not on whether the patients exist."),
        basis="GOV"),
    cost_drivers=[
        CostDriver(
            "Device & disposable COGS (balloons, stents, thrombectomy, contrast)",
            "~25-35% of cost",
            "The main variable cost, scaling per case; vendor contracting is "
            "margin.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Clinical & procedural labor (proceduralist, RN/tech, imaging staff)",
            "~30-40% of cost",
            "The fixed staffing of the lab; throughput sets the operating "
            "leverage.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Imaging suite & facility (fluoroscopy, real estate, radiation compliance)",
            "~12-18% of cost",
            "The fixed OBL chassis and its capex.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Billing / prior-auth / compliance (RCM + Stark/AKS structuring)",
            "~8-12% of cost",
            "Coding accuracy, prior authorization, and maintaining a defensible "
            "referral/ownership structure.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Medical direction & G&A",
            "~5-10% of cost",
            "Physician leadership and corporate overhead.",
            "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "No OBL / access-center roster is public and no facility census is "
        "vendored, so geography is not fabricated here. The honest proxy is the "
        "dialysis footprint itself: access-maintenance demand tracks the local "
        "in-center dialysis census (Sun Belt and Southeast-heavy, as the "
        "dialysis map shows), and site economics track state office-based-"
        "surgery and ASC rules. Use the CMS dialysis-facility and procedure-"
        "volume connectors below rather than a fabricated vascular-access map."),
)

register(REPORT)
