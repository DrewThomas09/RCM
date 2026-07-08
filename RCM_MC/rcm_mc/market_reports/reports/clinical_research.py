"""Research Sites — clinical-trial sites & integrated site organizations.

Deals-only deep-dive (no public site-level census is vendored — ClinicalTrials.
gov site-level data is not in our files — so geography is omitted rather than
fabricated). The critical framing, authored throughout: a research site is paid
by trial sponsors and CROs, NOT by health insurance. Revenue is per-patient
grants, startup/milestone fees, and pass-through costs; the value driver is
enrollment against a fixed clinical-staff base; the sector is consolidating from
a cottage industry of single sites and academic centers into PE-backed
integrated-site organizations. A distinct billing-compliance overlay exists —
Medicare Clinical Trial Policy (NCD 310.1) lets sites bill routine trial costs,
but only with a correct coverage analysis (a False Claims Act line). Consumes
``clinical_research_deep_dive()`` for SOURCED corpus deal figures.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="clinical_research",
    name="Research Sites",
    care_setting="Dx & labs",
    naics="541715",
    one_line_def=(
        "Clinical-trial research sites and integrated site organizations "
        "(ISOs/SMOs/site networks) that recruit and enroll patients and conduct "
        "sponsor- and CRO-funded interventional and observational studies — "
        "earning per-patient grants, startup and milestone fees, and pass-through "
        "costs, not health-insurance reimbursement. Increasingly consolidated "
        "dedicated-site platforms sit between pharma/biotech sponsors (and their "
        "CROs) and trial participants."),
    tam_headline=TamHeadline(
        value=60.0, unit="$B", growth_pct=7.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "There is no single published figure for US clinical-trials spend. "
            "~$60B is the modeled anchor for US clinical-development/trial spend "
            "that flows to trials; the global clinical-trials/CRO market is "
            "~$70-80B+ (industry-directional), with the US the largest share. "
            "Research sites capture the portion paid as per-patient grants, "
            "startup, and pass-throughs. Growth is modeled "
            "clinical-development-spend growth net of R&D-funding cyclicality."),
    ),
    executive_summary=[
        "Research sites earn from sponsors and CROs, not from insurance. Revenue "
        "is per-patient grants, screening/startup fees, milestone payments, and "
        "pass-through costs from interventional and observational trials — so the "
        "'payer' is pharma/biotech (directly or via a CRO), and the business "
        "cycles with clinical-development spend, not healthcare utilization.",
        "The value driver is enrollment. A site is paid largely per "
        "enrolled/completed patient, so patient access, the recruitment engine, "
        "the database/registry, and speed-to-first-patient are the assets — empty "
        "or slow-enrolling sites destroy trial economics and lose future "
        "studies.",
        "The sector is consolidating from cottage industry to platform. "
        "Historically a fragmented world of single physician-office sites and "
        "academic medical centers; PE has built dedicated integrated-site "
        "organizations (Velocity, CenExel, Headlands, Flourish, Care Access) that "
        "offer sponsors scale, standardization, and multi-site delivery — the "
        "core roll-up thesis.",
        "Concentration risk cuts two ways: revenue depends on a pipeline of "
        "awarded studies from a limited set of sponsors/CROs and on "
        "therapeutic-area mix; a network's backlog, sponsor diversity, and "
        "re-award rate are the earnings-quality crux, and study timing makes "
        "revenue lumpy.",
        "There is a real billing-compliance overlay. Medicare (and commercial) "
        "can be billed for the routine costs of qualifying trials under the "
        "Medicare Clinical Trial Policy (NCD 310.1) — but only with a correct "
        "coverage analysis separating routine care from sponsor-paid research "
        "costs. Double-billing research costs to Medicare is a False Claims Act "
        "exposure.",
        "Structural tailwinds — decentralized/hybrid trials, diversity-in-"
        "enrollment mandates, real-world evidence, and a heavy "
        "oncology/rare-disease/GLP-1 pipeline — favor scaled, patient-access-rich "
        "site platforms, but pricing power sits with sponsors and CROs and site "
        "margins depend on enrollment delivery against fixed clinical staff.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Sponsor (pharma/biotech) designs a protocol; a CRO is often engaged "
            "to run the trial",
            "Site selection / feasibility — the CRO/sponsor awards the study to "
            "qualified sites (investigators, patient access, past performance)",
            "Site startup — IRB/ethics approval, budget & CTA contract "
            "negotiation, regulatory documents, site initiation visit",
            "Patient identification & recruitment (database/registry, referral, "
            "advertising, EHR screening)",
            "Screening, informed consent, and enrollment against "
            "inclusion/exclusion criteria",
            "Visit conduct — dosing, procedures, assessments, EDC data entry, "
            "source documentation",
            "Monitoring & data queries (CRA visits), safety reporting, protocol "
            "compliance",
            "Payments — startup/milestone fees + per-patient grants + "
            "pass-throughs; study close-out",
            "(Parallel) coverage analysis + billing routine costs to "
            "Medicare/commercial under NCD 310.1",
        ],
        sites_of_care=[
            "Dedicated research site / integrated-site-organization location "
            "(the roll-up asset)",
            "Physician-office / specialty-practice embedded research site",
            "Academic medical center / health-system research office",
            "Decentralized / virtual & mobile trial delivery (home health, "
            "telehealth, local labs)",
            "Phase I clinical-pharmacology unit (early-phase, healthy-volunteer "
            "inpatient)",
        ],
        money_flow=(
            "A research site is paid by the trial sponsor — directly or through "
            "the CRO managing the study — under a clinical trial agreement, not "
            "by any health plan. Payment has several components: startup and "
            "site-initiation fees, per-visit and per-procedure grants, "
            "per-patient enrollment/completion payments (the bulk of the "
            "economics), holdbacks released at milestones, and pass-through "
            "reimbursement of costs (advertising, imaging, central lab). Because "
            "the largest component is per-enrolled/completed patient, a site's "
            "revenue is enrollment times grant per patient across its active "
            "study portfolio, and empty or slow sites earn little while still "
            "carrying fixed coordinator and investigator cost. Separately, the "
            "routine clinical costs of a qualifying trial (the care the patient "
            "would have received anyway) can be billed to Medicare or commercial "
            "insurance under the Medicare Clinical Trial Policy (NCD 310.1) — but "
            "only after a Medicare Coverage Analysis correctly separates billable "
            "routine costs from sponsor-paid research costs; getting that wrong is "
            "a False Claims Act risk. The engine is a backlog of awarded studies "
            "converting to enrolled patients against a fixed clinical-staff "
            "base."),
        key_players=(
            "The site side has consolidated into PE-backed integrated-site "
            "organizations — Velocity Clinical Research, CenExel, Headlands "
            "Research, Flourish Research, and Care Access — alongside academic "
            "medical centers, health-system research institutes, and a long tail "
            "of independent physician-office sites. Adjacent and upstream sit the "
            "CROs that place and run trials — IQVIA, ICON, Fortrea, Parexel, "
            "Thermo Fisher/PPD, Medpace — and the sponsors (large pharma and "
            "biotech) that fund them. Site-enablement, patient-recruitment, "
            "eClinical/EDC, and decentralized-trial technology vendors surround "
            "the economics. The acquirable PE pool is the dedicated-site and "
            "specialty-practice-site tail."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("US clinical-development / trials spend (funds sites)",
                    "~$60B (directional)",
                    "ILLUSTRATIVE · modeled US trial-spend anchor"),
            Segment("Global clinical-trials / CRO market",
                    "~$70-80B+ (directional)",
                    "INDUSTRY · industry directional"),
            Segment("Research-site-level revenue (grants + pass-throughs)",
                    "a slice of total trial spend",
                    "ILLUSTRATIVE · modeled site-capture share"),
            Segment("Oncology + rare-disease + cardiometabolic (GLP-1) trials",
                    "pipeline-heavy, high-value",
                    "INDUSTRY · pipeline directional"),
            Segment("Decentralized / hybrid trial delivery",
                    "fastest-growing model",
                    "INDUSTRY · industry directional"),
        ],
        growth_drivers=[
            "Robust biopharma R&D pipeline (oncology, rare disease, "
            "GLP-1/cardiometabolic, neuro)",
            "Site consolidation into scaled platforms sponsors prefer for "
            "multi-site delivery",
            "Decentralized/hybrid trials + real-world evidence widening "
            "participation",
            "Diversity-in-enrollment mandates favoring community/patient-access "
            "sites",
            "Growing trial complexity and the volume of studies",
            "Sponsor/CRO pricing power, study-timing lumpiness, and enrollment "
            "risk as the drag",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Pharma / biotech sponsor grants (direct + via CRO)": 0.80,
            "Routine-care billing to Medicare / commercial (NCD 310.1)": 0.10,
            "Government / academic / foundation grants + other": 0.10,
        },
        rate_mechanics=[
            "Per-patient grants + per-visit/per-procedure payments — the bulk of "
            "site revenue, set in the trial-budget negotiation against the "
            "protocol schedule of assessments.",
            "Startup, site-initiation, and milestone fees + holdbacks — "
            "front-loaded fees and milestone-released holdbacks; working-capital "
            "sensitive.",
            "Pass-through costs — advertising/recruitment, imaging, central lab, "
            "and other reimbursed costs (little margin; grosses up revenue).",
            "Medicare Clinical Trial Policy (NCD 310.1) — routine costs of a "
            "qualifying clinical trial are billable to Medicare/commercial; "
            "requires a Medicare Coverage Analysis and correct research-vs-routine "
            "billing separation.",
            "Budget & CTA negotiation leverage — sponsors/CROs set price; a "
            "site's re-award record and enrollment performance are its only real "
            "leverage.",
            "Payment timing — sponsors/CROs often pay on a lag (net 30-90+, "
            "milestone-gated), so revenue recognition and cash timing diverge.",
        ],
        reimbursement_risk=(
            "The core 'reimbursement' risk is not payer denial but sponsor/CRO "
            "dependence and enrollment delivery: revenue is a function of awarded "
            "studies converting to enrolled patients, so a thin backlog, sponsor "
            "concentration, a paused or failed program, or under-enrollment "
            "against a fixed clinical-staff base compresses margin fast. Study "
            "timing makes revenue lumpy and hard to forecast, and payment lags "
            "and milestone holdbacks stretch working capital. The distinct "
            "compliance risk is billing: improperly billing sponsor-paid research "
            "costs to Medicare — or failing a Medicare Coverage Analysis under "
            "NCD 310.1 — is a False Claims Act exposure. And because sponsors and "
            "CROs hold the pricing power, site margins are ultimately capped by "
            "enrollment productivity, not by rate."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("FDA IND regulations + Good Clinical Practice "
                 "(21 CFR 312/50/56/54; ICH E6)",
                 "The framework governing investigational trials, informed "
                 "consent, IRB oversight, and investigator financial disclosure "
                 "— the operating license for conducting studies.",
                 "https://www.ecfr.gov/current/title-21/chapter-I/subchapter-D/part-312"),
            Rule("Common Rule — human-subjects protection (45 CFR 46)",
                 "The ethics-review and human-subjects regime (IRB approval, "
                 "informed consent) every research site operates under.",
                 "https://www.hhs.gov/ohrp/regulations-and-policy/regulations/45-cfr-46/index.html"),
            Rule("Medicare Clinical Trial Policy (NCD 310.1) + coverage analysis",
                 "Governs which routine trial costs Medicare covers; a correct "
                 "Medicare Coverage Analysis and billing separation is a False "
                 "Claims Act compliance line.",
                 "https://www.cms.gov/medicare-coverage-database/view/ncd.aspx?ncdid=1"),
            Rule("HIPAA + 21 CFR Part 11 (electronic records/signatures)",
                 "Patient-data privacy and data-integrity requirements for EDC "
                 "and electronic source — audit and inspection exposure.",
                 "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/part-11-electronic-records-electronic-signatures-scope-and-application"),
            Rule("FDA diversity action plans + decentralized-trial guidance",
                 "Enrollment-diversity requirements and DCT conduct guidance that "
                 "increasingly shape site selection and study design.",
                 "https://www.fda.gov/regulatory-information/search-fda-guidance-documents"),
            Rule("ClinicalTrials.gov registration & results reporting "
                 "(FDAAA 801)",
                 "Mandatory trial registration and results posting — a "
                 "transparency and compliance obligation tied to federal funding "
                 "and FDA action.",
                 "https://clinicaltrials.gov/"),
        ],
        policy_watch=[
            "FDA diversity action plan requirements and enforcement",
            "Decentralized/hybrid trial guidance and reimbursement for remote "
            "conduct",
            "ICH E6(R3) GCP modernization implementation",
            "Medicare Coverage Analysis / NCD 310.1 billing-compliance "
            "enforcement (FCA)",
            "Data-privacy + AI-in-trials and real-world-evidence policy",
            "Biopharma R&D funding cycle + IRA effect on small-molecule "
            "pipeline",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Historically extremely fragmented — tens of thousands of "
            "investigators at physician offices, academic medical centers, and "
            "independent sites, most conducting a handful of studies. That tail "
            "is now being rolled up by PE-backed integrated-site organizations "
            "that give sponsors scale, standardization, and multi-site delivery. "
            "No public site-level census is vendored (ClinicalTrials.gov "
            "site-level data is not in our files), so a site-count HHI is "
            "honestly omitted; the acquirable pool is the independent-site and "
            "specialty-practice tail plus regional networks."),
        hhi_or_share=(
            "Still fragmented at the site level despite consolidation — the "
            "largest integrated-site organizations hold a small share of total "
            "sites, and academic medical centers remain a large, separate "
            "channel. Concentration is higher among CROs (a handful of large "
            "global CROs place most industry-sponsored trials) than among "
            "sites."),
        consolidation=(
            "The defining trend. PE has assembled dedicated-site platforms "
            "(Velocity, CenExel, Headlands, Flourish, Care Access) by acquiring "
            "high-performing independent sites and specialty practices with "
            "strong patient access and enrollment track records, then "
            "standardizing operations and cross-selling to sponsors. Sponsors and "
            "CROs increasingly favor these networks for reliability and speed. "
            "Consolidation is mid-innings, with plenty of independent-site "
            "whitespace remaining."),
        pe_activity=(
            "One of the more active healthcare-services roll-up themes of the "
            "last several years — site networks are attractive for their "
            "recurring sponsor relationships, asset-light model, and enrollment "
            "moats, though earnings are lumpy and sponsor-dependent. "
            "Quality-of-earnings centers on backlog and re-award rate, "
            "sponsor/CRO and therapeutic-area diversity, enrollment performance "
            "and patient-database depth, study-timing revenue recognition, and "
            "NCD 310.1 billing compliance."),
        notable_players=[
            "Velocity Clinical Research", "CenExel", "Headlands Research",
            "Flourish Research", "Care Access",
            "Academic medical centers / health-system research offices",
            "CRO channel (IQVIA, ICON, Fortrea)",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Enrolled patients / study & enrollment rate", "the value driver",
                "Per-patient grants dominate revenue; recruitment speed and "
                "patient access are the moat."),
            Kpi("Revenue / site / year", "site-scale + study-mix dependent",
                "A function of active studies times grant per patient — lumpy "
                "with study timing."),
            Kpi("Backlog / awarded-but-unstarted studies",
                "forward-revenue signal",
                "The pipeline of contracted studies — the best earnings-quality "
                "indicator."),
            Kpi("Startup cycle time (award → first patient)", "weeks matter",
                "Speed to first-patient-in wins re-awards and drives revenue "
                "conversion."),
            Kpi("Coordinator productivity (studies/patients per CRC)",
                "the fixed-cost lever",
                "Clinical-research-coordinator staffing against active-study load "
                "drives margin."),
            Kpi("Site EBITDA margin", "variable; enrollment-dependent",
                "Strong for well-enrolling scaled sites; thin or negative for "
                "slow or sub-scale sites carrying fixed staff."),
        ],
        margin_profile=(
            "Site economics are an enrollment-versus-fixed-cost story. Revenue is "
            "dominated by per-patient grants across the active study portfolio, "
            "while the cost base — investigators, clinical-research coordinators, "
            "regulatory/quality staff, and facility — is largely fixed in the "
            "near term, so margin swings on how fully the site's studies enroll "
            "and on coordinator productivity (studies and patients managed per "
            "CRC). A scaled, patient-access-rich site with a full study slate and "
            "fast startup earns attractive, asset-light margins; a slow-enrolling "
            "or sub-scale site burns fixed staff cost against thin grant revenue. "
            "Pass-through costs gross up revenue with little margin, so reported "
            "revenue overstates the true earning base. Because sponsors and CROs "
            "set pricing, the site's levers are enrollment delivery, startup "
            "speed, and study-slate density — not rate — and lumpy study timing "
            "makes any single period a poor read on run-rate."),
    ),
    risks=[
        Risk("Enrollment underperformance vs fixed staff", "High",
             "Per-patient revenue against fixed coordinator/investigator cost; "
             "slow enrollment compresses margin and loses re-awards."),
        Risk("Sponsor/CRO concentration & backlog risk", "High",
             "Revenue depends on a pipeline of awarded studies from limited "
             "sponsors; a paused program or lost re-award hits hard, and revenue "
             "is lumpy."),
        Risk("NCD 310.1 / billing-compliance (Medicare Coverage Analysis)",
             "Medium",
             "Improperly billing research costs to Medicare is a False Claims Act "
             "exposure requiring rigorous coverage analysis."),
        Risk("Biopharma R&D funding cycle", "Medium",
             "Site demand cycles with clinical-development spend; a funding "
             "pullback or IRA-driven pipeline shift reduces studies."),
        Risk("GCP / FDA inspection & data integrity", "Medium",
             "A Form 483, warning letter, or data-integrity finding can bar an "
             "investigator and end sponsor relationships."),
        Risk("Integration & standardization execution", "Medium",
             "Roll-ups depend on standardizing acquired sites and retaining "
             "investigators/patient access without eroding performance."),
    ],
    diligence_questions=[
        "What is the backlog of awarded studies and the historical re-award rate "
        "by sponsor/CRO?",
        "What is sponsor, CRO, and therapeutic-area concentration, and how lumpy "
        "is revenue by study timing?",
        "What is enrollment performance vs. target across active studies, and "
        "what is patient database/registry depth per site?",
        "What share of revenue is pass-through vs. grant (the true earning "
        "base), and what is coordinator productivity per CRC?",
        "What is startup cycle time (award to first-patient-in) versus sponsor "
        "benchmarks?",
        "What is the Medicare Coverage Analysis / NCD 310.1 billing process and "
        "any FCA or audit exposure?",
        "What is the GCP/FDA inspection history — any 483s, warning letters, or "
        "investigator disqualifications?",
        "For a roll-up, how standardized are acquired sites, and what is "
        "investigator/coordinator retention post-acquisition?",
    ],
    insider_lens=[
        "Sites don't have patients, they have access to patients. The moat is a "
        "recruitment engine and a database/registry that fills studies fast — "
        "enrollment speed, not square footage or equipment, decides which sites "
        "win the next award. An empty site is worthless to a sponsor no matter "
        "how nice the facility.",
        "Revenue is lumpy and pass-through-inflated. A big chunk of reported "
        "revenue is pass-through cost (advertising, imaging, labs) with no "
        "margin, and study timing makes any quarter a poor read — underwrite "
        "grant revenue and backlog, not headline revenue.",
        "Backlog and re-award rate are the earnings-quality tell. This is a "
        "repeat-business relationship game: sponsors and CROs send their next "
        "study to sites that enrolled fast and clean last time. A thin backlog "
        "or a falling re-award rate is the leading indicator, long before "
        "revenue rolls over.",
        "There's a quiet compliance landmine in the billing. Under NCD 310.1 a "
        "site can bill Medicare for routine trial costs — but only with a "
        "coverage analysis that cleanly separates routine care from sponsor-paid "
        "research. Billing research costs to Medicare is a False Claims Act case; "
        "a sloppy coverage-analysis process is a real liability.",
        "Pricing power sits with sponsors and CROs, so the site's only margin "
        "lever is productivity — how many studies and patients each coordinator "
        "can carry, and how fast startup runs. Roll-ups create value by "
        "standardizing that, not by raising rates.",
        "The roll-up thesis is real but delivery-fragile: buying high-performing "
        "independent sites works only if you keep the investigators and patient "
        "access that made them perform. Over-standardize or lose the local PI, "
        "and the enrollment engine you paid for walks out the door.",
    ],
    connections=default_connections(
        "clinical_research",
        deals_sector="clinical_research",
        extra_pages=[
            ("/industry/clinical_research",
             "Industry deep-dive — research-site deal history + structure"),
        ],
        connectors=[
            ("clinicaltrials_gov",
             "ClinicalTrials.gov — registered trials & site activity "
             "(demand/backlog signal)"),
            ("open_payments",
             "CMS Open Payments — research payments from sponsors to "
             "investigators (site-activity & integrity signal)"),
            ("npi_provider_taxonomy",
             "NPI taxonomy — investigator/physician enrollment for site "
             "mapping"),
            ("census_acs_cbsa_profile",
             "Census ACS — CBSA demographics for recruitment-catchment & "
             "diversity mapping"),
            ("oig_leie_exclusions",
             "OIG LEIE — excluded investigators/entities (integrity screen)"),
        ],
    ),
    sources=[
        Source("FDA — investigational new drug (IND) regulations & Good Clinical "
               "Practice (21 CFR 312/50/56/54; ICH E6)", "GOV",
               "https://www.ecfr.gov/current/title-21/chapter-I/subchapter-D/part-312"),
        Source("HHS — Common Rule (45 CFR 46) human-subjects protection", "GOV",
               "https://www.hhs.gov/ohrp/regulations-and-policy/regulations/45-cfr-46/index.html"),
        Source("CMS — Medicare Clinical Trial Policy (NCD 310.1) & routine-costs "
               "coverage", "GOV",
               "https://www.cms.gov/medicare-coverage-database/view/ncd.aspx?ncdid=1"),
        Source("ClinicalTrials.gov / FDAAA 801 — trial registration & results "
               "reporting", "GOV", "https://clinicaltrials.gov/"),
        Source("Association of Clinical Research Organizations (ACRO) — industry "
               "clinical-development data", "INDUSTRY",
               "https://www.acrohealth.org/"),
        Source("Tufts Center for the Study of Drug Development — clinical-trial "
               "performance research", "ACADEMIC", "https://csdd.tufts.edu/"),
        Source("PE Desk industry deep-dive (clinical research) + realized-deal "
               "corpus", "INTERNAL",
               "/diligence/tam-sam?template=clinical_research"),
    ],
    live_figures=live_figures_from_dive("clinical_research"),
    trends=(
        "Clinical research has shifted from a fragmented cottage industry of "
        "individual investigators and academic centers toward a consolidated, "
        "platform-delivered model. PE-backed integrated-site organizations "
        "(Velocity, CenExel, Headlands, Flourish, Care Access) assembled "
        "high-performing independent sites and specialty practices to offer "
        "sponsors and CROs scale, standardization, and reliable multi-site "
        "delivery — a response to sponsors' chronic frustration with slow and "
        "non-enrolling sites. In parallel, trial conduct modernized: "
        "decentralized and hybrid designs, telehealth and mobile visits, "
        "EHR-based recruitment, real-world evidence, and FDA diversity action "
        "plans widened where and how patients participate. The biopharma "
        "pipeline stayed rich — oncology, rare disease, neuro, and a "
        "cardiometabolic/GLP-1 wave — sustaining study volume even as trial "
        "complexity rose and the Inflation Reduction Act raised questions about "
        "small-molecule development economics. Through all of it, the "
        "fundamental structure held: sponsors and CROs hold the pricing power, "
        "revenue is lumpy and enrollment-driven, and the sites that win are those "
        "with genuine patient access and fast, clean startup. The forward story "
        "is continued consolidation and decentralized-trial adoption favoring "
        "scaled, patient-access-rich platforms, against sponsor pricing power, "
        "R&D-funding cyclicality, and a real billing-compliance overlay."),
    growth_levers=[
        GrowthLever(
            "Biopharma R&D pipeline volume",
            "Study count across oncology, rare disease, neuro, and "
            "cardiometabolic/GLP-1 sustains site demand — the upstream engine.",
            "primary", "ILLUSTRATIVE"),
        GrowthLever(
            "Site consolidation into preferred networks",
            "Sponsors route more studies to scaled, standardized platforms, "
            "lifting studies per site.",
            "+ share of studies", "ILLUSTRATIVE"),
        GrowthLever(
            "Decentralized/hybrid & diversity-driven access",
            "DCT models and diversity mandates widen participation and favor "
            "community/patient-access sites.",
            "+ participation", "ILLUSTRATIVE"),
        GrowthLever(
            "Enrollment & startup productivity",
            "Faster startup and higher coordinator productivity convert backlog "
            "to revenue and win re-awards.",
            "+ conversion", "ILLUSTRATIVE"),
        GrowthLever(
            "Sponsor pricing power + R&D cyclicality drag",
            "Sponsors/CROs cap rate and clinical-development-spend cycles create "
            "revenue lumpiness.",
            "rate & cycle risk", "ILLUSTRATIVE"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Awarded studies converting to enrolled patients",
        analysis=(
            "Demand for a research site is the flow of studies sponsors and CROs "
            "award it, and value is realized only when those studies convert to "
            "enrolled, completed patients — so the driver is a two-step: winning "
            "studies (a function of past enrollment performance, investigator "
            "quality, therapeutic-area fit, and increasingly network scale) and "
            "then enrolling them fast against inclusion/exclusion criteria. The "
            "upstream engine is biopharma clinical-development spend and pipeline "
            "breadth (oncology, rare disease, neuro, and the cardiometabolic/"
            "GLP-1 wave), which sets how many studies exist to award; "
            "decentralized and diversity-driven models widen the accessible "
            "patient pool. But because per-patient grants dominate site revenue "
            "and study timing is lumpy, the binding operational variable is "
            "enrollment conversion — a site with a rich patient database and fast "
            "startup turns backlog into revenue, while a slow or non-enrolling "
            "site loses both current economics and future awards."),
        basis="ILLUSTRATIVE"),
    cost_drivers=[
        CostDriver(
            "Clinical-research coordinators & investigators (labor)",
            "~40-55% of cost",
            "CRCs, sub-investigators, and PI time — the fixed clinical base that "
            "enrollment must cover.", "ILLUSTRATIVE"),
        CostDriver(
            "Patient recruitment & retention", "~10-20% of cost",
            "Advertising, community outreach, referral, and database maintenance "
            "to fill studies (some pass-through).", "ILLUSTRATIVE"),
        CostDriver(
            "Regulatory, quality & data management", "~10-15% of cost",
            "IRB/regulatory coordination, GCP/quality, and source/EDC data entry "
            "and query resolution.", "ILLUSTRATIVE"),
        CostDriver(
            "Facility, equipment & procedures", "~10-15% of cost",
            "Clinic space, study procedures/imaging, and drug-storage/pharmacy "
            "where required (some pass-through).", "ILLUSTRATIVE"),
        CostDriver(
            "Corporate/network overhead & integration", "~10-15% of cost",
            "Platform G&A, business development to sponsors/CROs, and "
            "acquired-site integration.", "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "No public site-level census is vendored (ClinicalTrials.gov site-level "
        "data is not in our files), so state geography is omitted rather than "
        "fabricated. Qualitatively, research activity concentrates around "
        "academic medical centers, large metros, and therapeutic-area referral "
        "hubs, though decentralized models and diversity-in-enrollment mandates "
        "are pushing studies into community and underserved settings. The "
        "ClinicalTrials.gov, Open Payments (research payments), and NPI-taxonomy "
        "connectors linked below give a real read on where trials and "
        "investigators actually sit."),
)

register(REPORT)
