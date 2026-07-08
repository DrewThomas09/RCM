"""Fertility / IVF — assisted reproductive technology (ART) practices.

Deals-only deep-dive (fertility patients are of reproductive age, outside
Medicare, so no CMS facility roll exists; CDC/SART clinic-level data is the
census). The whole model is a cash-pay / employer-benefit lab business, so the
qualitative sections are authored around the embryology lab as the crown jewel,
the REI/embryologist supply ceiling, cryostorage as a recurring annuity, the
benefit-manager payer layer, and the post-Dobbs embryo-personhood tail risk.
Consumes ``fertility_deep_dive()`` for SOURCED corpus deal figures.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="fertility_ivf",
    name="Fertility / IVF",
    care_setting="Physician services",
    naics="621111",
    one_line_def=(
        "Assisted-reproductive-technology (ART) practices — reproductive "
        "endocrinology (REI) physicians plus an embryology lab — delivering "
        "IVF, egg freezing, IUI, and third-party reproduction; a largely "
        "cash-pay and employer-benefit market with essentially no Medicare "
        "exposure."),
    tam_headline=TamHeadline(
        value=7.0, unit="$B", growth_pct=9.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "No single published US fertility-services revenue figure exists; "
            "~$7B is the modeled composite from ~410,000 ART cycles/yr "
            "(CDC/SART) at a ~$15-25K all-in cycle price plus medications, "
            "genetics, and recurring cryostorage. Growth is the modeled "
            "composite of delayed childbearing, employer-benefit expansion, and "
            "state mandates."),
    ),
    executive_summary=[
        "Cash is king — literally. Fertility is one of the few large healthcare "
        "verticals where the patient (or her employer benefit) pays, not "
        "Medicare. A typical IVF cycle runs ~$15-25K, largely out of pocket, so "
        "demand, pricing, and collections behave more like premium consumer "
        "services than reimbursed medicine.",
        "The employer-benefit wave is the growth engine. Progyny, Carrot, and "
        "Maven plus direct employer mandates turned fertility into a covered "
        "benefit at large employers, converting cash-pay volume into contracted "
        "commercial volume and expanding the pool well beyond the affluent "
        "self-pay core.",
        "The bottleneck is people, not patients. There are only ~1,250 "
        "board-certified reproductive endocrinologists in the US and a chronic "
        "embryologist shortage; a clinic's cycle capacity — and thus its value "
        "— is gated by scarce clinical labor, so lab throughput and recruiting "
        "dominate diligence.",
        "It is a lab business wearing a physician-practice coat. The embryology "
        "lab is the crown jewel and the key risk: KPIs (fertilization, "
        "blastocyst, live-birth rates), accreditation (CAP/CLIA), and "
        "catastrophic tank-failure/liability exposure sit in the lab, and "
        "SART/CDC outcome reporting makes quality unusually transparent.",
        "PE and strategics rolled up the fragmented clinic base hard (US "
        "Fertility, Inception/Prelude, Ivy, Pinnacle, Kindbody), betting on "
        "demographic tailwinds — delayed childbearing, rising infertility "
        "prevalence, LGBTQ+ and single-parent family building — against "
        "outcome-transparency pricing pressure and post-Dobbs legal risk.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Referral or self-presentation → new-patient consult with an REI",
            "Diagnostic workup (ovarian reserve/AMH, semen analysis, imaging)",
            "Treatment plan + benefit verification / financial counseling",
            "Ovarian stimulation cycle (monitoring, gonadotropin meds)",
            "Egg retrieval (procedure) → fertilization + embryology-lab culture",
            "Embryo genetic testing (PGT-A/PGT-M) at a reference genetics lab",
            "Embryo transfer → pregnancy test → OB handoff",
            "Cryopreservation/storage of remaining embryos/eggs; SART/CDC "
            "outcome reporting",
        ],
        sites_of_care=[
            "Fertility clinic / REI practice (monitoring + procedures)",
            "Embryology & andrology laboratory (the crown jewel)",
            "Cryostorage facility (long-term egg/embryo storage — recurring)",
            "Procedure/ASC suite (retrievals under sedation)",
            "Reference genetics lab (PGT — usually outsourced)",
        ],
        money_flow=(
            "Fertility revenue is overwhelmingly cash-pay or employer-benefit — "
            "Medicare is essentially absent because the patients are of "
            "reproductive age. A stimulated IVF cycle bundles physician "
            "monitoring, the retrieval procedure, anesthesia, and embryology-lab "
            "work into a global fee, typically ~$15-25K, with fertility "
            "medications (gonadotropins) another several thousand dollars often "
            "billed through a specialty pharmacy, and PGT genetic testing billed "
            "separately by the genetics lab. Increasingly the 'payer' is an "
            "employer fertility benefit administered by a carve-out manager "
            "(Progyny, Carrot, Maven, WINFertility) that contracts rates and "
            "manages utilization — converting self-pay into contracted "
            "commercial volume. Cryostorage generates a recurring, annuity-like "
            "annual fee. Because so much is paid up front and out of pocket, the "
            "P&L looks like premium consumer services: pricing power, financing "
            "partners, and multi-cycle/refund packages matter as much as coding."),
        key_players=(
            "The consolidated platforms dominate the branded segment — US "
            "Fertility (with Shady Grove Fertility), Inception/Prelude "
            "Fertility, Ivy Fertility, Pinnacle Fertility, Kindbody, Boston IVF, "
            "and CCRM Fertility. The benefit-management layer — Progyny, Carrot, "
            "Maven, and WINFertility — increasingly controls covered-life "
            "access. Adjacent: specialty pharmacies for fertility meds, genetics "
            "labs (Natera, CooperSurgical) for PGT, and cryostorage technology "
            "(TMRW Life Sciences). A large independent single-clinic long tail "
            "remains — the acquirable pool."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("ART cycles performed (CDC/SART, latest)",
                    "~410,000 cycles / yr",
                    "GOV · CDC ART National Summary / SART registry"),
            Segment("US ART programs / fertility clinics", "~450 clinics",
                    "GOV · CDC/SART reporting programs"),
            Segment("Board-certified reproductive endocrinologists",
                    "~1,250 REIs",
                    "INDUSTRY · ABOG/SART workforce (directional)"),
            Segment("Average IVF cycle price (cash, ex-meds)",
                    "~$15,000-25,000",
                    "ILLUSTRATIVE · industry pricing, directional"),
            Segment("Employer fertility-benefit covered lives",
                    "tens of millions and rising",
                    "INDUSTRY · benefit-manager disclosures (directional)"),
        ],
        growth_drivers=[
            "Delayed childbearing — rising maternal age lifts infertility",
            "Employer fertility benefits — converting cash-pay to covered volume",
            "State insurance mandates (~21 states) — expanding coverage",
            "Family-building expansion — LGBTQ+, single parents, egg freezing",
            "Fertility preservation (elective egg freezing) — a growing segment",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Self-pay / cash": 0.45,
            "Commercial / employer benefit": 0.50,
            "Medicaid / other": 0.05,
        },
        rate_mechanics=[
            "Global cycle fee — a bundled cash or contracted price covering "
            "monitoring, retrieval, anesthesia, and embryology-lab work; "
            "medications and PGT are usually excluded.",
            "Employer-benefit contracting — carve-out managers (Progyny/Carrot/"
            "Maven) negotiate per-cycle or 'smart-cycle' rates and manage "
            "utilization; being in-network is access to covered lives.",
            "Self-pay pricing & financing — multi-cycle packages, refund/"
            "'shared-risk' guarantees, and lending partners shape realized "
            "price and consult-to-cycle conversion.",
            "Specialty-pharmacy medication billing — gonadotropins/injectables "
            "billed through specialty pharmacy, a separate several-thousand-"
            "dollar line.",
            "PGT / genetics — embryo genetic testing billed by the reference "
            "genetics lab, sometimes with a clinic markup.",
            "Cryostorage subscription — recurring annual storage fees on eggs/"
            "embryos — durable, high-margin recurring revenue.",
            "State-mandate coverage — where a state infertility mandate applies, "
            "commercial plans must cover defined services, shifting cash to "
            "insured.",
        ],
        reimbursement_risk=(
            "Because the market is cash- and employer-benefit-driven, the "
            "'reimbursement' risks are unusual. First, benefit-manager "
            "concentration: as Progyny, Carrot, and Maven aggregate covered "
            "lives, they gain leverage over clinic rates and utilization — good "
            "for volume, pressuring price. Second, macro/consumer sensitivity: a "
            "large elective, out-of-pocket ticket is exposed to consumer "
            "confidence, credit availability, and employer benefit budgets in a "
            "way reimbursed medicine is not. Third, coverage-mandate and "
            "regulatory shifts swing demand sharply — new state mandates or "
            "federal IVF-coverage action expand the pool, while post-Dobbs legal "
            "uncertainty around embryo personhood (the 2024 Alabama ruling that "
            "briefly halted IVF statewide) is a genuine tail risk to the "
            "freeze-and-discard model. Outcome transparency (SART/CDC live-birth "
            "reporting) also disciplines pricing — patients shop on success "
            "rates."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("Fertility Clinic Success Rate and Certification Act of 1992 "
                 "(CDC ART reporting)",
                 "Mandatory clinic-level success-rate reporting makes outcomes "
                 "publicly comparable and disciplines the market.",
                 "https://www.cdc.gov/art/"),
            Rule("CLIA + CAP/ASRM embryology-lab accreditation",
                 "The embryology/andrology lab must be accredited; lab quality "
                 "and accreditation gate operation and outcomes.",
                 "https://www.cms.gov/medicare/quality/clinical-laboratory-improvement-amendments"),
            Rule("FDA human cells & tissues rules (21 CFR 1271)",
                 "Donor eligibility, screening, and handling of reproductive "
                 "tissue (donor eggs/sperm/embryos).",
                 "https://www.ecfr.gov/current/title-21/chapter-I/subchapter-L/part-1271"),
            Rule("State infertility insurance mandates (~21 states)",
                 "Where enacted (IL, MA, NJ, NY, CT, and others), commercial "
                 "plans must cover defined infertility services — a demand "
                 "switch.",
                 None),
            Rule("Embryo-personhood law (LePage v. Center for Reproductive "
                 "Medicine, Ala. 2024)",
                 "The legal status of cryopreserved embryos is an existential "
                 "model risk in some post-Dobbs states.",
                 None),
            Rule("ASRM / SART practice guidelines",
                 "Professional standards (embryo-transfer limits, PGT, donor "
                 "practices) that shape clinical protocols and liability.",
                 "https://www.asrm.org/"),
        ],
        policy_watch=[
            "Federal IVF-coverage proposals and the politics of ART access",
            "Embryo-personhood litigation/legislation spreading beyond Alabama",
            "Benefit-manager consolidation and its rate/utilization leverage",
            "New and expanding state insurance mandates",
            "FDA and professional scrutiny of 'IVF add-on' efficacy",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Historically a cottage industry of independent single- and "
            "few-physician REI practices attached to a lab; a long independent "
            "tail remains, but branded multi-site platforms now hold a "
            "meaningful and growing share of US cycle volume. No CMS facility "
            "file exists (fertility is outside Medicare); CDC/SART clinic-level "
            "data is the closest census."),
        hhi_or_share=(
            "No single dominant national owner, but a handful of PE-/strategic-"
            "backed platforms (US Fertility, Inception/Prelude, Ivy, Pinnacle, "
            "Kindbody) plus the benefit managers concentrate an increasing share "
            "of branded volume and covered lives. Clinic-level share is not "
            "captured in a vendored file, so a chain HHI is honestly omitted."),
        consolidation=(
            "Aggressive roll-up over the last decade — sponsors and strategics "
            "assembled multi-clinic platforms around anchor practices (Shady "
            "Grove, CCRM, Boston IVF), centralizing lab operations, marketing, "
            "and benefit-manager contracting. Multiple sponsors have backed "
            "platforms, and several have already traded to secondary buyers."),
        pe_activity=(
            "One of the most sought-after physician-services theses of the "
            "cycle — demographic tailwinds, cash-pay pricing power, and "
            "recurring storage revenue drew heavy PE interest and premium "
            "multiples. The forward debate is durability: benefit-manager "
            "leverage, REI/embryologist scarcity capping growth, and post-Dobbs "
            "legal risk temper the story."),
        notable_players=[
            "US Fertility (Shady Grove)", "Inception / Prelude Fertility",
            "Ivy Fertility", "Pinnacle Fertility", "Kindbody",
            "CCRM Fertility", "Boston IVF", "Progyny / Carrot / Maven (benefit)",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Cycles per REI per year", "150-250+",
                "Throughput per scarce physician — the core capacity metric "
                "behind the practice's revenue."),
            Kpi("Live-birth rate per transfer", "SART/CDC-reported",
                "The outcome KPI that drives referrals and pricing; publicly "
                "reported, so quality is transparent."),
            Kpi("Revenue per IVF cycle (all-in)", "~$15,000-25,000+",
                "Cash or contracted, with or without medications; the ticket "
                "size that makes fertility a consumer-like purchase."),
            Kpi("Embryology-lab utilization", "cycles / embryologist / lab",
                "The true capacity constraint — the lab, not the waiting room, "
                "sets the ceiling."),
            Kpi("Cryostorage accounts (recurring)", "count × annual fee",
                "Durable, high-margin recurring revenue accumulating with every "
                "retrieval."),
            Kpi("Consult-to-cycle conversion", "funnel-dependent",
                "The funnel economics of an elective, often-financed purchase — "
                "marketing and financing drive it."),
            Kpi("Clinic EBITDA margin (mature)", "25-35%+ (illustrative)",
                "High-margin when the lab is well-utilized and the book skews "
                "cash-pay premium."),
        ],
        margin_profile=(
            "A mature fertility clinic is a high-margin business — a "
            "well-utilized embryology lab and a productive REI throw off strong "
            "contribution once fixed lab and physician costs are covered, and "
            "cryostorage adds recurring, near-annuity revenue. But the economics "
            "are gated by scarce clinical labor (REIs and embryologists) rather "
            "than by demand, so growth is a recruiting-and-lab-capacity problem, "
            "and a single lab incident — a cryo-tank failure — is both a "
            "clinical catastrophe and a liability event. Margins are richest for "
            "cash-pay premium volume and compress somewhat as employer-benefit "
            "contracting (with negotiated rates) grows as a share of the book."),
    ),
    risks=[
        Risk("Post-Dobbs embryo-personhood legal risk", "High",
             "A ruling like Alabama's can halt IVF or impose crippling "
             "liability and handling constraints on cryopreserved embryos."),
        Risk("REI / embryologist labor scarcity", "High",
             "A hard capacity ceiling — ~1,250 REIs nationally and a chronic "
             "embryologist shortage cap cycle growth regardless of demand."),
        Risk("Embryology-lab quality / catastrophic incident", "High",
             "Tank failure, mislabeling, or accreditation loss is clinical, "
             "reputational, and legal ruin in a single event."),
        Risk("Benefit-manager rate & utilization leverage", "Medium",
             "Progyny/Carrot/Maven concentration pressures per-cycle price as "
             "covered volume grows as a share of the book."),
        Risk("Consumer / macro sensitivity of an elective cash purchase",
             "Medium",
             "A $15-25K out-of-pocket ticket is exposed to consumer "
             "confidence, credit, and employer benefit budgets."),
        Risk("Outcome-transparency pricing pressure", "Medium",
             "Public SART/CDC success rates let patients shop, disciplining "
             "price and rewarding scale and quality."),
        Risk("Multiple compression on a maturing, heavily-bid thesis",
             "Medium",
             "Premium entry multiples across the cycle are exposed to a cooling "
             "market and higher rates."),
    ],
    diligence_questions=[
        "What is the legal exposure to embryo-personhood law in each state of "
        "operation, and what contingency exists post-Alabama?",
        "What is the REI and embryologist staffing, tenure, and recruiting "
        "pipeline — how gated is capacity by clinical labor?",
        "What are the clinic's SART/CDC-reported outcomes (live-birth rates) "
        "versus benchmarks, and how do they trend?",
        "What is the payer mix between cash-pay and employer benefit, and how "
        "exposed is realized price to benefit-manager contracting?",
        "What is embryology-lab utilization, accreditation status, incident "
        "history, and cryostorage tank-integrity and insurance posture?",
        "How large and durable is the recurring cryostorage book, and how is it "
        "priced and collected?",
        "What is consult-to-cycle conversion, and how dependent is volume on "
        "financing/refund programs?",
        "How concentrated is volume in the top physicians, and what are their "
        "retention terms?",
    ],
    insider_lens=[
        "It is a lab business, not a doctor business. The embryology lab — its "
        "throughput, its success rates, and its catastrophic-failure exposure — "
        "is the real asset and the real risk. A cryo-tank failure is the "
        "sector's nightmare: clinical tragedy, litigation, and reputational "
        "collapse in one event.",
        "The bottleneck is people, not patients. Demand is effectively "
        "unlimited relative to supply; the binding constraint is ~1,250 REIs and "
        "a chronic embryologist shortage. Value creation is recruiting and lab "
        "capacity — a platform that cannot staff cannot grow no matter the "
        "demographics.",
        "Cryostorage is the quiet annuity. Every retrieval leaves frozen "
        "eggs/embryos that generate recurring annual storage fees — a "
        "high-margin, sticky, subscription-like book the market underappreciates "
        "relative to cycle revenue.",
        "Post-Dobbs turned a stable model into a policy bet. The Alabama "
        "embryo-personhood ruling briefly halted IVF statewide and exposed that "
        "the entire freeze-and-discard workflow rests on legal assumptions that "
        "are now contested — an existential, state-by-state tail risk.",
        "The benefit managers are becoming the payer. As Progyny, Carrot, and "
        "Maven aggregate employer covered lives, they move from demand-"
        "generators to rate-setters — being in their networks is access, but "
        "their leverage over price is the emerging margin risk.",
    ],
    connections=default_connections(
        "fertility_ivf",
        deals_sector="fertility",
        extra_pages=[
            ("/industry/fertility_ivf",
             "Industry deep-dive — fertility deal history + structure"),
        ],
        connectors=[
            ("npi_provider_taxonomy",
             "NPI taxonomy — reproductive-endocrinology (REI) supply & clinics"),
            ("census_acs_cbsa_profile",
             "Census ACS — metro income & age profile (delayed-childbearing "
             "demand)"),
            ("bls_qcew_area_industry",
             "BLS QCEW — large-employer density (fertility-benefit covered-life "
             "concentration)"),
            ("open_payments_general_payments_2024",
             "Open Payments — fertility-pharma payments to REIs (relationship "
             "screen)"),
        ],
    ),
    sources=[
        Source("CDC — Assisted Reproductive Technology (ART) National Summary "
               "Report", "GOV", "https://www.cdc.gov/art/"),
        Source("SART — Society for Assisted Reproductive Technology clinic "
               "outcomes registry", "INDUSTRY", "https://www.sart.org/"),
        Source("ASRM — American Society for Reproductive Medicine practice "
               "guidelines", "INDUSTRY", "https://www.asrm.org/"),
        Source("Fertility Clinic Success Rate and Certification Act of 1992 "
               "(CDC reporting mandate)", "GOV", "https://www.cdc.gov/art/"),
        Source("LePage v. Center for Reproductive Medicine, No. SC-2022-0515 "
               "(Ala. 2024) — embryo personhood", "ACADEMIC",
               "https://law.justia.com/cases/alabama/supreme-court/2024/sc-2022-0515.html"),
        Source("FDA — Human Cells, Tissues, and Cellular/Tissue-Based Products "
               "(21 CFR 1271)", "GOV",
               "https://www.ecfr.gov/current/title-21/chapter-I/subchapter-L/part-1271"),
        Source("PE Desk industry deep-dive (fertility) + realized-deal corpus",
               "INTERNAL", "/diligence/tam-sam?template=fertility_ivf"),
    ],
    live_figures=live_figures_from_dive("fertility_ivf"),
    trends=(
        "The fertility market re-rated over the last decade on three shifts. "
        "First, demand normalized and broadened: delayed childbearing pushed "
        "age-related infertility up, and IVF moved from a stigmatized last "
        "resort toward a mainstream, marketed service — extended by elective "
        "egg freezing and by LGBTQ+ and single-parent family building. Second, "
        "the payer changed: employer fertility benefits, administered by "
        "carve-out managers (Progyny's 2019 IPO was the signal), converted a "
        "cash-pay luxury into a covered benefit at large employers, and ~21 "
        "states enacted insurance mandates. Third, capital consolidated a "
        "cottage industry: PE and strategics assembled multi-clinic platforms "
        "(US Fertility/Shady Grove, Inception/Prelude, Ivy, Pinnacle, Kindbody) "
        "around anchor practices and centralized labs and contracting. The "
        "forward tension is legal and structural: the 2024 Alabama "
        "embryo-personhood ruling exposed a post-Dobbs tail risk to the "
        "freeze-and-discard model, benefit managers are accumulating rate-"
        "setting leverage, and REI/embryologist scarcity caps how fast supply "
        "can meet the demographic tailwind."),
    growth_levers=[
        GrowthLever(
            "Employer fertility benefits",
            "Carve-out managers (Progyny/Carrot/Maven) add covered lives, "
            "converting cash-pay into contracted commercial volume.",
            "primary", "ILLUSTRATIVE"),
        GrowthLever(
            "Delayed childbearing / infertility prevalence",
            "Rising maternal age lifts age-related infertility and the "
            "underlying cycle demand base.",
            "+ mid-single %/yr volume", "GOV"),
        GrowthLever(
            "Egg freezing / fertility preservation",
            "A newer elective segment that expands the addressable population "
            "beyond classic infertility.",
            "+ segment", "ILLUSTRATIVE"),
        GrowthLever(
            "State insurance mandates",
            "~21 states requiring infertility coverage switch latent demand "
            "into paid cycles where enacted.",
            "+ where enacted", "GOV"),
        GrowthLever(
            "Cryostorage recurring revenue",
            "Accumulating frozen-tissue accounts compound annual storage fees — "
            "a durable, sticky revenue line.",
            "recurring", "ILLUSTRATIVE"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Delayed childbearing × infertility prevalence × coverage "
               "expansion",
        analysis=(
            "The dominant demand driver is the rising age of first childbirth: "
            "as women delay childbearing, age-related infertility prevalence "
            "rises, and IVF is the effective treatment. The CDC records roughly "
            "1-in-8 couples experiencing infertility and ART cycles growing "
            "steadily toward ~410,000 a year. Two multipliers compound the "
            "demographic base: coverage expansion (employer benefits via "
            "Progyny/Carrot/Maven plus ~21 state mandates) converts latent "
            "demand into paid cycles, and family-building expansion (LGBTQ+ "
            "couples, single parents by choice, and elective egg freezing) "
            "widens the eligible population beyond classic infertility. The "
            "binding offset is supply, not demand — REI and embryologist "
            "scarcity caps how many cycles the system can actually perform."),
        basis="GOV"),
    cost_drivers=[
        CostDriver(
            "Clinical & lab labor (REIs, embryologists, nurses)",
            "~35-45% of cost",
            "The scarce, expensive core — the binding capacity constraint; "
            "embryologists in particular are hard to hire and retain.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Fertility medications / specialty pharmacy",
            "variable / often pass-through",
            "Gonadotropins are a large ticket; usually billed through specialty "
            "pharmacy but bundled into some multi-cycle programs.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Lab consumables, media & cryo (incubators, LN2, tanks)",
            "~10-15% of cost",
            "Embryology culture media, andrology supplies, and the "
            "cryopreservation apparatus — the lab's cost of goods.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Marketing & patient acquisition", "~8-15% of cost",
            "A consumer-marketed elective — digital and brand spend drive the "
            "consult funnel in a way reimbursed medicine does not.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Facility, G&A & compliance (accreditation, SART, malpractice)",
            "~10-15% of cost",
            "Including elevated professional-liability insurance and the "
            "reporting/accreditation apparatus.", "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "No Medicare facility file exists for fertility — the patients are of "
        "reproductive age, outside Medicare — so state geography is omitted "
        "rather than fabricated. Qualitatively, clinic density tracks three "
        "things: affluent metros with high concentrations of delayed-"
        "childbearing professionals (the cash-pay core), states with infertility "
        "insurance mandates (Massachusetts, Illinois, New Jersey, New York, "
        "Connecticut) where covered demand is structurally higher, and "
        "large-employer density where fertility benefits concentrate covered "
        "lives. The CDC ART Report and SART registry provide clinic-level counts "
        "and outcomes by state — the honest footprint read — and the NPI, "
        "demographic, and employer connectors linked below map REI supply "
        "against metro demand."),
)

register(REPORT)
