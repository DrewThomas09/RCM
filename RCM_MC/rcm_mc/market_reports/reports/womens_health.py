"""Women's Health — the OB/GYN + fertility platform.

Deals-only deep-dive (no national physician-practice facility file; geography is
omitted rather than fabricated). Women's health is an unusual specialty roll-up:
the obstetric side is Medicaid-heavy and carries the highest malpractice premiums
in medicine, while the margin sits in gynecologic ancillaries (ultrasound, lab,
ASC gyn surgery) and in cash-and-commercial fertility. The qualitative sections
are authored around the global obstetric payment, the falling US birth rate, the
malpractice-as-geography reality, fertility as the growth engine, and the
post-Dobbs / embryo-ruling regulatory tail. Consumes ``womens_health_deep_dive()``
for SOURCED corpus deal figures.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="womens_health",
    name="Women's Health",
    care_setting="Physician services",
    naics="621111",
    one_line_def=(
        "Physician practices serving women across the lifespan — obstetrics "
        "(prenatal, delivery, postpartum), gynecology (well-woman, surgery, "
        "menopause), and increasingly fertility/IVF — where the obstetric base is "
        "Medicaid-heavy and malpractice-laden, and the margin sits in gynecologic "
        "ancillaries (ultrasound, lab, ASC gyn surgery) and cash-and-commercial "
        "fertility."),
    tam_headline=TamHeadline(
        value=45.0, unit="$B", growth_pct=5.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "Modeled from the ~40,000-50,000 practicing US OB/GYNs (ACOG "
            "workforce) plus fertility, times the professional fee and the "
            "ultrasound/lab/ASC ancillary stack and IVF cycle revenue — not a "
            "single published figure. Growth is the modeled composite of a "
            "falling birth rate offset by gynecologic, menopause, and fertility "
            "demand, net of Medicaid/MPFS rate drag."),
    ),
    executive_summary=[
        "Obstetrics is not the profit center — it is the Medicaid-heavy, "
        "malpractice-heavy front door. Medicaid finances roughly 40%+ of US "
        "births at thin state-set rates, and OB carries the highest malpractice "
        "premiums in medicine. The margin sits in gynecologic ancillaries and in "
        "cash-and-commercial fertility.",
        "The US birth rate is falling. The total fertility rate is around 1.6 — "
        "below replacement and near record lows — a genuine structural headwind "
        "for delivery volume that a women's-health thesis must underwrite "
        "honestly, offset by gynecology, menopause, and fertility growth rather "
        "than assumed away.",
        "Fertility/IVF is the growth engine and the cash-pay hedge. Expanding "
        "employer benefits (Progyny, Carrot, Maven) and state IVF coverage "
        "mandates are pulling IVF from elective cash toward a covered benefit — "
        "but the 2024 Alabama embryo ruling showed the IVF regulatory tail is "
        "real and sudden.",
        "Malpractice is the geography. OB economics swing on the state tort "
        "environment (non-economic damage caps, verdict history); the same "
        "practice is a materially different business in a cap state versus a "
        "high-verdict state.",
        "The obstetric payment is a global bundle. A single maternity fee covers "
        "routine antepartum visits, delivery, and postpartum care, so utilization "
        "management within the pregnancy episode is margin, and "
        "complication/transfer unbundling is where the coding attention goes.",
        "Women's health is an active PE roll-up (Unified Women's Healthcare, "
        "Axia, Women's Care) with fertility platforms alongside. The acquirable "
        "pool is the independent OB/GYN group, richest where gynecologic "
        "ancillaries and fertility can be captured.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Access — well-woman visit, obstetric intake, or fertility consult",
            "Obstetrics — antepartum visits, ultrasound, delivery, postpartum",
            "Gynecology — well-woman, in-office procedures, surgery referral",
            "In-office ancillaries — ultrasound, lab (pap/HPV/STI), LARC",
            "Gyn surgery — minimally invasive hysterectomy/laparoscopy in the ASC",
            "Fertility — diagnostic workup, IVF cycle, embryology lab, cryostorage",
            "Charge capture, global-OB coding, and collections",
        ],
        sites_of_care=[
            "Physician office / clinic (well-woman, prenatal, gyn procedures)",
            "Hospital labor & delivery (the delivery — professional fee)",
            "Owned ambulatory surgery center (gyn surgery ancillary)",
            "In-office ultrasound + lab (the gynecologic ancillary base)",
            "Fertility center + embryology lab (IVF cycles, cryostorage)",
        ],
        money_flow=(
            "Obstetric care is usually paid as a global maternity package — a "
            "single fee (e.g. CPT 59400) covering routine antepartum visits, the "
            "delivery, and postpartum care — which unbundles only on a transfer "
            "of care or a complication. Because Medicaid finances a large share "
            "of births at thin rates, the OB line is low-margin; the money is in "
            "gynecology and its ancillaries — obstetric and gynecologic "
            "ultrasound billed as a technical component, in-house pap/HPV/STI "
            "lab, LARC placement, and minimally-invasive gyn surgery in an owned "
            "ASC — plus fertility, which is largely cash-pay and commercial and "
            "priced per IVF cycle. In the PE structure the payer (or the patient, "
            "for cash fertility) pays the physician-owned PC, which pays the MSO a "
            "management fee for the ultrasound, lab, ASC, embryology lab, and "
            "shared services. A smart platform weights toward the "
            "gynecology/fertility margin and manages the OB base for access and "
            "referral rather than profit."),
        key_players=(
            "PE-backed MSOs lead: Unified Women's Healthcare (the largest, "
            "~2,700+ providers), Axia Women's Health (Audax/Partners Group), "
            "Women's Care, and Privia Women's Health, with Ob Hospitalist Group "
            "(OBHG) staffing hospital L&D. Fertility platforms sit alongside or "
            "within: US Fertility, Ivy Fertility, Pinnacle Fertility, Inception/"
            "Prelude, Kindbody, and CCRM, with fertility-benefit managers "
            "(Progyny, Carrot, Maven) intermediating employer coverage. The "
            "acquirable pool is the independent OB/GYN group with capturable "
            "ultrasound, lab, ASC, and fertility ancillaries."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Practicing US OB/GYNs", "~40,000-50,000",
                    "INDUSTRY · ACOG / workforce estimates (directional)"),
            Segment("US annual births", "~3.6M and declining",
                    "GOV · CDC National Vital Statistics (natality)"),
            Segment("Medicaid share of US births", "~40%+",
                    "GOV · CMS / KFF maternity-financing data"),
            Segment("US total fertility rate", "~1.6 (below replacement)",
                    "GOV · CDC natality — fertility-rate series"),
            Segment("US IVF cycles / yr", "~400,000+ and rising",
                    "GOV · CDC ART / SART national summary"),
        ],
        growth_drivers=[
            "Fertility/IVF expansion — employer benefits + state coverage mandates",
            "Gynecologic ancillary capture (ultrasound, lab, ASC gyn surgery)",
            "Menopause / midlife women's-health service lines — new whitespace",
            "Delayed childbearing lifting fertility demand per birth",
            "Falling birth rate + Medicaid/MPFS rate drag — the structural headwind",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Commercial": 0.48,
            "Medicaid": 0.28,
            "Medicare / MA": 0.15,
            "Self-pay / cash (fertility, other)": 0.09,
        },
        rate_mechanics=[
            "Global obstetric package (CPT 59400/59510/59610) — a single bundled "
            "fee covering routine antepartum visits, delivery, and postpartum; it "
            "unbundles only on transfer of care or complications.",
            "Medicaid as the dominant OB payer — Medicaid finances ~40%+ of US "
            "births at state-set rates typically well below commercial, so the OB "
            "line's margin is Medicaid-mix-sensitive.",
            "MPFS professional fees for gynecologic E&M and procedures, plus "
            "in-office ancillaries — obstetric/gyn ultrasound technical "
            "component, colposcopy, LEEP, LARC/IUD placement, hysteroscopy.",
            "Gyn surgery facility fee (ASC/HOPD) — minimally invasive "
            "hysterectomy and laparoscopy migrating to the owned surgery center.",
            "Fertility/IVF — largely cash-pay and commercial, increasingly "
            "employer-sponsored (Progyny/Carrot/Maven) and mandated by state IVF "
            "laws; priced per cycle plus embryology-lab and cryostorage revenue.",
            "Pathology/lab (pap cytology, HPV, STI) and LARC buy-and-bill round "
            "out the ancillary revenue; commercial multiples apply on the "
            "gyn/fertility book.",
        ],
        reimbursement_risk=(
            "Women's-health reimbursement risk is bifurcated. On the OB side, the "
            "risk is rate and volume: Medicaid pays a large share of births at "
            "thin rates, the global maternity fee compresses per-pregnancy "
            "revenue, and the falling birth rate shrinks delivery volume — while "
            "malpractice premiums, the highest in medicine, load the OB cost side. "
            "On the gynecology/fertility side, the risk is ancillary durability "
            "and policy: ultrasound, lab, and ASC gyn surgery depend on the Stark "
            "in-office ancillary exception and site-of-service rates, and fertility "
            "— the growth engine — is exposed to a fast-moving regulatory tail "
            "(the Alabama embryo ruling briefly halted IVF in the state) even as "
            "coverage mandates expand demand. The healthiest platforms de-risk by "
            "weighting toward gynecology and fertility and managing OB for access."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("Medicaid maternity coverage + 12-month postpartum extension",
                 "Medicaid finances ~40%+ of US births; state rates and the "
                 "postpartum-coverage extension set the OB payer backbone.",
                 "https://www.medicaid.gov/medicaid/quality-of-care/improvement-initiatives/maternal-health/index.html"),
            Rule("Dobbs v. Jackson Women's Health Organization (2022)",
                 "Returned abortion regulation to the states; the resulting "
                 "patchwork reshapes service availability, liability, and "
                 "physician recruitment in restrictive states.",
                 "https://www.supremecourt.gov/opinions/21pdf/19-1392_6j37.pdf"),
            Rule("State medical-malpractice tort environment (damage caps)",
                 "OB carries the highest malpractice premiums in medicine; state "
                 "non-economic-damage caps are the single biggest geographic "
                 "economic variable.",
                 None),
            Rule("EMTALA (emergency obstetric care)",
                 "Requires stabilizing emergency care including active labor; the "
                 "post-Dobbs EMTALA tension adds OB liability complexity.",
                 "https://www.cms.gov/medicare/regulations-guidance/legislation/emergency-medical-treatment-labor-act"),
            Rule("State infertility / IVF coverage mandates + embryology-lab "
                 "oversight (CLIA)",
                 "A growing set of states mandate IVF coverage (demand tailwind), "
                 "while embryo-status rulings (Alabama, 2024) are a sudden risk.",
                 None),
            Rule("Physician self-referral law (Stark, 42 CFR 411.350+)",
                 "The in-office ancillary-services exception is what makes owned "
                 "ultrasound, lab, and the ASC legal.",
                 "https://www.cms.gov/medicare/regulations-guidance/physician-self-referral"),
        ],
        policy_watch=[
            "The falling US birth rate (total fertility ~1.6) as a structural OB "
            "volume headwind",
            "Expanding state IVF mandates + employer fertility benefits — the "
            "fertility tailwind",
            "Post-Dobbs state-law patchwork and the EMTALA-emergency-care "
            "litigation",
            "Embryo/personhood rulings threatening IVF availability (Alabama and "
            "beyond)",
            "Medicaid postpartum extension, maternal-health-equity funding, and "
            "MPFS conversion-factor cuts",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "US women's health is fragmented across many small OB/GYN groups, "
            "with consolidation led by a few national MSOs (Unified, Axia, "
            "Women's Care) and a parallel wave of fertility platforms. The "
            "acquirable pool is the independent OB/GYN group with capturable "
            "gynecologic ancillaries and, where present, a fertility book."),
        hhi_or_share=(
            "No single owner is dominant nationally, though Unified Women's "
            "Healthcare is the largest MSO by provider count. No vendored "
            "physician-practice roll captures operator concentration, so a "
            "national chain HHI is honestly omitted — the corpus deal history "
            "below is the real read."),
        consolidation=(
            "The model is an OB/GYN MSO that captures gynecologic ancillaries "
            "(ultrasound, lab, ASC gyn surgery) and bolts on fertility as the "
            "high-growth, cash-and-commercial adjacency, while managing the "
            "Medicaid-heavy, malpractice-heavy OB base for access and referral. "
            "Fertility itself has consolidated rapidly under dedicated platforms "
            "and benefit managers, sometimes inside a broader women's-health MSO."),
        pe_activity=(
            "Actively PE-backed on both sides — Unified Women's Healthcare, Axia "
            "Women's Health, and Women's Care on the OB/GYN MSO side; US "
            "Fertility, Ivy, Pinnacle, Inception, Kindbody, and CCRM on the "
            "fertility side, with Progyny/Carrot/Maven intermediating employer "
            "coverage. Diligence centers on OB payer mix and malpractice "
            "geography, ancillary durability, and the fertility regulatory tail."),
        notable_players=[
            "Unified Women's Healthcare", "Axia Women's Health", "Women's Care",
            "Privia Women's Health", "Ob Hospitalist Group (OBHG)",
            "US Fertility", "Pinnacle Fertility", "Kindbody",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Deliveries / OB physician / yr", "practice-dependent",
                "The obstetric volume base; declining births pressure it, and the "
                "global maternity fee caps per-pregnancy revenue."),
            Kpi("Medicaid share of the OB book", "the OB margin variable",
                "Medicaid finances ~40%+ of births at thin rates; a "
                "Medicaid-heavy OB book is low-margin."),
            Kpi("Malpractice premium / OB physician", "the highest in medicine",
                "A defining OB cost line that swings on the state tort "
                "environment."),
            Kpi("Ancillary revenue (% of total)", "ultrasound + lab + ASC gyn",
                "The gynecologic margin base; the higher the capture, the more "
                "platform value beyond the professional fee."),
            Kpi("IVF cycles / fertility revenue", "cash-and-commercial",
                "The growth engine and cash-pay hedge; cycle volume and payer "
                "shift (mandates/benefits) drive it."),
            Kpi("Platform EBITDA margin (post-MSO)", "12-20% (illustrative)",
                "Gyn/fertility-weighted platforms run higher; OB-heavy, "
                "Medicaid-heavy books run lower."),
        ],
        margin_profile=(
            "A women's-health platform's margin is a tale of two books. The "
            "obstetric book is low-margin and risk-heavy: Medicaid pays a large "
            "share of births at thin rates, the global maternity fee compresses "
            "per-pregnancy revenue, and OB malpractice premiums — the highest in "
            "medicine — load the cost side, all against a falling birth rate. The "
            "gynecology-and-fertility book is where the money is: in-office "
            "ultrasound and lab, minimally-invasive gyn surgery in an owned ASC, "
            "and cash-and-commercial IVF cycles carry real margin. So the "
            "operating art is mix management — weighting the platform toward "
            "gynecologic ancillaries and fertility, managing the OB base for "
            "access and referral, and choosing malpractice geography "
            "deliberately. Scale spreads the MSO back office and strengthens "
            "commercial leverage, but it does not change the underlying "
            "bifurcation."),
    ),
    risks=[
        Risk("Obstetric malpractice / birth-injury tort exposure", "High",
             "OB carries the highest malpractice premiums in medicine, with a "
             "long-tail, high-verdict liability profile that swings on state tort "
             "law."),
        Risk("Physician retention / comp-haircut backlash", "High",
             "Selling OB/GYNs and fertility physicians are the EBITDA; a botched "
             "post-close compensation redesign drives defection and volume loss."),
        Risk("Medicaid OB rate adequacy + payer mix", "Medium",
             "A Medicaid-heavy OB book at thin state-set rates is low-margin and "
             "exposed to state budget cycles."),
        Risk("Falling US birth rate (OB volume headwind)", "Medium",
             "A total fertility rate near 1.6 structurally shrinks delivery "
             "volume — an OB headwind that must be offset by gyn/fertility."),
        Risk("Fertility regulatory tail (embryo/personhood rulings)", "Medium",
             "The 2024 Alabama embryo ruling briefly halted IVF; sudden state "
             "action can disrupt the growth engine."),
        Risk("Post-Dobbs state-law patchwork + physician recruitment", "Medium",
             "Restrictive-state law reshapes service availability, liability, and "
             "the ability to recruit and retain OB/GYNs."),
        Risk("MPFS / global-OB rate erosion", "Medium",
             "A structural squeeze on the professional and maternity fees with no "
             "inflation update."),
    ],
    diligence_questions=[
        "What is the OB payer mix (Medicaid share) and the malpractice "
        "premium/geography, and how do they load the OB cost side?",
        "What share of EBITDA is gynecologic ancillary (ultrasound, lab, ASC gyn "
        "surgery) versus the OB professional fee?",
        "How large and how fast-growing is the fertility book, and what is its "
        "payer mix (cash, commercial, mandate/benefit)?",
        "How exposed is the fertility book to state embryo/IVF regulatory action "
        "(Alabama-style rulings)?",
        "What is the delivery-volume trend against the local birth rate, and how "
        "is the platform offsetting it with gyn/menopause/fertility?",
        "What is the post-close physician compensation and retention model across "
        "OB, gyn, and fertility physicians?",
        "How is the global-OB coding handled (episode utilization, "
        "complication/transfer unbundling), and what is the audit history?",
        "In which states does the platform operate, and how does the tort "
        "environment and post-Dobbs law affect recruiting and liability?",
    ],
    insider_lens=[
        "OB is the front door, not the profit center. Medicaid finances 40%+ of "
        "births at thin rates and OB carries the highest malpractice premiums in "
        "medicine — the margin sits in gynecologic ancillaries (ultrasound, lab, "
        "ASC gyn surgery) and cash-and-commercial fertility, and smart platforms "
        "weight toward those.",
        "The birth rate is falling and it matters. US total fertility is near "
        "1.6, below replacement — a genuine structural headwind for delivery "
        "volume that a women's-health thesis must underwrite honestly, not "
        "assume away, offset by gynecology, menopause, and fertility growth.",
        "Malpractice is the geography. The same OB practice is a different "
        "business in a state with non-economic damage caps than in a "
        "high-verdict state; the tort environment, not just the payer mix, sets "
        "OB economics.",
        "Fertility is the growth engine and the cash-pay hedge — but its "
        "regulatory tail is real and sudden. Employer benefits and state IVF "
        "mandates are pulling IVF toward covered demand, yet the Alabama embryo "
        "ruling showed a single state decision can halt cycles overnight.",
        "The global maternity fee bundles a whole pregnancy into one payment, so "
        "visit-cadence and ultrasound-frequency management within the episode is "
        "margin, and complication/transfer unbundling is where the coding "
        "attention (and audit risk) lands.",
        "Menopause and midlife women's health is the newest whitespace — a large, "
        "underserved, cash-and-commercial population that platforms are building "
        "dedicated service lines around, distinct from the OB and fertility "
        "books.",
    ],
    connections=default_connections(
        "womens_health",
        deals_sector="womens_health",
        extra_pages=[
            ("/industry/womens_health",
             "Industry deep-dive — women's-health deal history + OB/GYN read"),
        ],
        connectors=[
            ("npi_provider_taxonomy",
             "NPI taxonomy — OB/GYN & fertility specialty mix & enrollment"),
            ("cms_open_data_mup_physician_by_provider_service",
             "Medicare physician utilization — gynecologic service volume"),
            ("provider_data_asc_quality_facility",
             "CMS ASC quality file — gyn surgery-center footprint"),
            ("medicaid_data_enrollment_monthly",
             "Medicaid enrollment — the dominant obstetric payer read"),
            ("open_payments_general_payments_2024",
             "Open Payments — industry payments to OB/GYN physicians"),
            ("census_acs_cbsa_profile",
             "Census ACS — CBSA women-of-reproductive-age demographics"),
        ],
    ),
    sources=[
        Source("CDC — National Vital Statistics System (natality, births, "
               "fertility rate)", "GOV",
               "https://www.cdc.gov/nchs/nvss/births.htm"),
        Source("CDC — Assisted Reproductive Technology (ART) / SART national "
               "IVF summary", "GOV",
               "https://www.cdc.gov/art/"),
        Source("CMS / Medicaid — maternity financing and postpartum-coverage "
               "extension", "GOV",
               "https://www.medicaid.gov/medicaid/quality-of-care/improvement-initiatives/maternal-health/index.html"),
        Source("Dobbs v. Jackson Women's Health Organization, 597 U.S. 215 "
               "(2022)", "ACADEMIC",
               "https://www.supremecourt.gov/opinions/21pdf/19-1392_6j37.pdf"),
        Source("American College of Obstetricians and Gynecologists (ACOG) — "
               "workforce and practice data", "INDUSTRY",
               "https://www.acog.org/"),
        Source("KFF — Medicaid's role in financing births and women's-health "
               "coverage", "INDUSTRY",
               "https://www.kff.org/womens-health-policy/"),
        Source("PE Desk industry deep-dive (womens_health) + realized-deal "
               "corpus", "INTERNAL",
               "/diligence/tam-sam?template=womens_health"),
    ],
    live_figures=live_figures_from_dive("womens_health"),
    trends=(
        "Women's health became an active specialty roll-up on an unusual "
        "structure. Unlike derm or GI, the obstetric base is Medicaid-heavy and "
        "malpractice-laden — Medicaid finances 40%+ of births at thin rates, and "
        "OB carries the highest malpractice premiums in medicine — so national "
        "MSOs (Unified Women's Healthcare, Axia, Women's Care) built their "
        "economics on gynecologic ancillaries (ultrasound, lab, ASC gyn surgery) "
        "and increasingly on fertility, managing OB for access and referral. Two "
        "secular forces define the trajectory. The birth rate is falling — total "
        "fertility near 1.6, below replacement and near record lows — a real "
        "headwind for delivery volume. And fertility is the counterweight: "
        "expanding employer benefits (Progyny, Carrot, Maven) and state IVF "
        "mandates are converting elective cash-pay IVF into covered demand, "
        "pulling capital into dedicated fertility platforms. The regulatory frame "
        "shifted hard after Dobbs (2022) returned abortion law to the states, "
        "and the 2024 Alabama embryo ruling showed how suddenly a state decision "
        "can disrupt IVF. The forward thesis is mix management — weighting toward "
        "gynecology, menopause, and fertility, choosing malpractice geography, "
        "and underwriting the birth-rate and fertility-regulatory tails honestly."),
    growth_levers=[
        GrowthLever(
            "Fertility/IVF expansion (mandates + employer benefits)",
            "State IVF coverage mandates and employer fertility benefits convert "
            "elective cash-pay cycles into covered demand — the primary growth "
            "engine and cash-pay hedge.",
            "primary", "ILLUSTRATIVE"),
        GrowthLever(
            "Gynecologic ancillary capture",
            "Own the ultrasound, lab, and ASC gyn surgery the gynecologist "
            "generates — the durable, non-arbitrage margin base.",
            "+ ancillary margin", "ILLUSTRATIVE"),
        GrowthLever(
            "Menopause / midlife service line",
            "Build dedicated service lines for a large, underserved, "
            "cash-and-commercial midlife population.",
            "new whitespace", "ILLUSTRATIVE"),
        GrowthLever(
            "Consolidation multiple arbitrage",
            "Acquire independent OB/GYN groups at lower multiples and re-rate the "
            "platform on scale, ancillaries, and fertility.",
            "supporting / retention-gated", "ILLUSTRATIVE"),
        GrowthLever(
            "Falling birth rate (OB volume headwind)",
            "A total fertility rate near 1.6 structurally shrinks delivery "
            "volume — the demographic drag the gyn/fertility levers must outrun.",
            "volume headwind", "GOV"),
        GrowthLever(
            "Medicaid / MPFS rate drag",
            "Thin Medicaid OB rates and a flat-to-declining professional fee are "
            "the structural rate headwind.",
            "rate headwind", "GOV"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="The divergence of falling births and rising gyn/fertility demand",
        analysis=(
            "Women's-health volume is not one curve but two moving in opposite "
            "directions. Obstetric volume is falling: US births are around 3.6M "
            "and declining, with a total fertility rate near 1.6 — below "
            "replacement and near record lows — so delivery demand is a genuine "
            "structural headwind, not a growth story. Against that, gynecologic "
            "demand is durable and demographic (well-woman care, gyn surgery, and "
            "a large, underserved midlife/menopause population), and fertility is "
            "actively growing: delayed childbearing raises the need for assisted "
            "reproduction per birth, and expanding employer benefits and state "
            "IVF mandates convert elective cash-pay cycles (already ~400,000+ per "
            "year) into covered demand. So the honest volume analysis isolates "
            "the divergence — an OB base to be managed for access and a gyn/"
            "fertility book to be grown — rather than a single blended rate."),
        basis="GOV"),
    cost_drivers=[
        CostDriver(
            "Physician / APP / midwife compensation", "~40-50% of cost",
            "The dominant cost across OB, gyn, and fertility; the post-close comp "
            "model is the biggest margin lever and retention risk.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Professional-liability / malpractice (OB)", "outsized vs peers",
            "OB carries the highest malpractice premiums in medicine — a distinct, "
            "large cost line that swings on state tort law, unusual among "
            "specialties.", "ILLUSTRATIVE"),
        CostDriver(
            "Clinical & office staff (sonographers, MAs, nurses, embryologists)",
            "~15-20% of cost",
            "The labor running prenatal care, ultrasound, gyn procedures, and — "
            "for fertility — the embryology lab.", "ILLUSTRATIVE"),
        CostDriver(
            "Ancillary + fertility COGS (ultrasound, lab, IVF media, cryostorage)",
            "variable / service-driven",
            "The cost side of the margin-differentiating ancillaries and the "
            "capital-intensive embryology lab.", "ILLUSTRATIVE"),
        CostDriver(
            "MSO back office (billing/RCM, IT, compliance)", "~10% of cost",
            "The shared-services and compliance chassis the multi-line structure "
            "requires.", "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "No national physician-practice facility file is vendored — an OB/GYN or "
        "fertility group is a business, not a Medicare-certified facility — so "
        "state geography is omitted rather than fabricated. The most "
        "consequential geographic variables are the medical-malpractice tort "
        "environment (non-economic damage caps, which are the single biggest OB "
        "economic swing), the state Medicaid maternity rate and enrollment mix, "
        "the post-Dobbs abortion-law posture (which affects service lines, "
        "liability, and physician recruiting), and the presence of a state IVF "
        "coverage mandate or embryo-status ruling. The corporate-practice-of-"
        "medicine doctrine shapes the deal structure on top. The NPI-taxonomy, "
        "Medicare physician-utilization, ASC-quality, Medicaid-enrollment, and "
        "demographic connectors linked below map women's-health supply and "
        "demand — the honest footprint read."),
)

register(REPORT)
