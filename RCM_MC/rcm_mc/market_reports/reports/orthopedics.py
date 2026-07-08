"""Orthopedics — the musculoskeletal (MSK) surgery + ancillary platform.

Deals-only deep-dive (no national physician-practice facility file; geography is
omitted rather than fabricated). Orthopedics carries the deepest ancillary stack
in medicine — an owned surgery center, in-office imaging, physical therapy, DME/
bracing, injections/orthobiologics, and pain — so the surgeon's professional fee
is a fraction of the economic footprint. The qualitative sections are authored
around the total-joint migration to the ASC, implant COGS, bundled-episode risk,
and the harder-to-haircut economics of high-earning surgeons. Consumes
``orthopedics_deep_dive()`` for SOURCED corpus deal figures.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="orthopedics",
    name="Orthopedics",
    care_setting="Physician services",
    naics="621111",
    one_line_def=(
        "Physician practices treating the musculoskeletal system — joint "
        "replacement, spine, sports medicine, trauma, and hand/foot — where the "
        "economics live in the deepest ancillary stack in medicine (an owned "
        "surgery center, in-office imaging, physical therapy, DME/bracing, and "
        "injections) and increasingly in owning the full episode of care under "
        "bundled and value-based MSK contracts."),
    tam_headline=TamHeadline(
        value=55.0, unit="$B", growth_pct=6.5, basis_label="ILLUSTRATIVE",
        basis_note=(
            "Modeled from the ~19,000-20,000 practicing US orthopedic surgeons "
            "(AAOS census) times the surgical professional fee plus the ASC/"
            "facility fee, implants, and the PT/imaging/DME ancillary stack — "
            "not a single published figure. Growth is the modeled composite of "
            "aging-driven joint-replacement volume, ASC migration, and ancillary "
            "capture, net of bundle/rate compression."),
    ),
    executive_summary=[
        "Orthopedics has the deepest ancillary stack in medicine: an owned "
        "surgery center, in-office MRI/X-ray, physical therapy, DME and bracing, "
        "injections and orthobiologics, and pain management. The surgeon's "
        "professional fee is a fraction of the economic footprint the surgeon "
        "generates — ancillary capture is the thesis.",
        "The defining opportunity is the total-joint migration to the ASC. CMS "
        "removed total knee replacement from the inpatient-only list in 2018 and "
        "total hip in 2020, then added them to the ASC-covered list — so a joint "
        "done in a surgeon-owned surgery center captures a facility fee that used "
        "to go to the hospital.",
        "The implant is the swing variable. In joint replacement the device can "
        "be 30-50% of the facility payment, so implant-cost management (and the "
        "device supply chain) makes or breaks ASC joint economics — a level of "
        "COGS exposure other specialties do not carry.",
        "Surgeons are the hardest specialists to comp-haircut. They earn the "
        "most and have the most outside options (hospital employment, their own "
        "ASC), so the value plan leans more on facility and ancillary capture and "
        "value-based MSK than on the compensation spread that powers derm/GI "
        "deals.",
        "Bundled and episodic payment is both a threat and the differentiated "
        "play. CJR, BPCI Advanced, and the mandatory TEAM model (2026) compress "
        "episode payments — but a platform that owns the full episode (HOPCo-"
        "style value-based MSK) can turn that risk into margin.",
        "The ortho roll-up is the current frontier — later than derm and GI and "
        "accelerating (United Musculoskeletal Partners, OrthoAlliance, US "
        "Orthopaedic Partners, HOPCo). The acquirable pool is the independent "
        "single-specialty group and the large regional supergroup.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Referral / self-referral for injury, pain, or joint degeneration",
            "Office E&M visit + in-office imaging (X-ray, MRI)",
            "Conservative care — injections, orthobiologics, physical therapy",
            "Surgical decision — joint replacement, spine, arthroscopy, trauma",
            "Surgery in the owned ASC (or HOPD/inpatient for higher acuity)",
            "Implant / device supply + post-op DME and bracing",
            "Post-acute rehab (owned PT) + episode / bundle reconciliation",
        ],
        sites_of_care=[
            "Physician office / clinic (E&M, injections, in-office imaging)",
            "Owned ambulatory surgery center (ASC) — the facility-fee engine",
            "Owned physical-therapy clinics (the post-acute ancillary)",
            "Hospital (inpatient joints/spine, trauma — the professional fee)",
            "In-office imaging suite (MRI, X-ray) and DME/bracing dispensary",
        ],
        money_flow=(
            "An orthopedic surgeon earns a professional fee off the Medicare "
            "Physician Fee Schedule — with a 90-day global surgical period that "
            "bundles pre- and post-op visits into the surgical fee — or a "
            "commercial multiple of it. Around that thin fee sits the deepest "
            "ancillary stack in medicine: the surgery-center facility fee "
            "(Medicare ASC/OPPS), the implant/device the case consumes, "
            "in-office MRI and X-ray technical components, owned physical "
            "therapy, DME and custom bracing, and injections/orthobiologics. In "
            "joint replacement the implant is a large share of the facility "
            "payment, so device cost directly sets case margin. Increasingly a "
            "slice of revenue is episodic — CJR/BPCI/TEAM bundle payments for a "
            "joint-replacement episode — where the platform takes risk on the "
            "full cost of care and keeps the savings. In the PE structure the "
            "payer pays the physician-owned PC, which pays the MSO a management "
            "fee for the ASC, PT, imaging, and shared services."),
        key_players=(
            "The current PE frontier: United Musculoskeletal Partners (Welsh "
            "Carson; anchored by Resurgens), OrthoAlliance (Revelstoke), US "
            "Orthopaedic Partners, and HOPCo (Healthcare Outcomes Performance "
            "Company — value-based MSK management). Large independent "
            "supergroups — Rothman Orthopaedics, OrthoCarolina, Illinois Bone & "
            "Joint, OrthoVirginia, EmergeOrtho — are the anchors and prime "
            "targets. Device makers (Stryker, Zimmer Biomet, DePuy Synthes, "
            "Smith+Nephew) sit upstream and set the implant COGS the ASC economics "
            "turn on. The acquirable pool is the independent single-specialty "
            "group with an owned ASC and PT."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Practicing US orthopedic surgeons", "~19,000-20,000",
                    "INDUSTRY · AAOS orthopaedic census (directional)"),
            Segment("US total knee + hip replacements", "~1.8M+ procedures / yr",
                    "ACADEMIC · AAOS / registry & JBJS projection estimates"),
            Segment("Ancillary share of a mature ortho platform's revenue",
                    "~40-55% (ASC + PT + imaging + DME)",
                    "ILLUSTRATIVE · platform economics, directional"),
            Segment("Implant/device share of a joint-replacement case",
                    "~30-50% of the facility payment",
                    "ILLUSTRATIVE · device-cost economics, directional"),
            Segment("Musculoskeletal conditions (US prevalence)",
                    "the largest chronic-condition cost category",
                    "GOV · AHRQ/BMUS musculoskeletal burden (directional)"),
        ],
        growth_drivers=[
            "Aging + obesity-driven osteoarthritis → joint-replacement demand",
            "Total-joint ASC migration (inpatient-only-list removals) — capture",
            "Ancillary stack (PT, imaging, DME, orthobiologics) — the margin lever",
            "Value-based MSK / bundled-episode ownership — the differentiated play",
            "Bundle + MPFS rate compression — a structural rate drag",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Commercial": 0.48,
            "Medicare / MA": 0.35,
            "Workers' comp": 0.08,
            "Medicaid": 0.05,
            "Self-pay / other": 0.04,
        },
        rate_mechanics=[
            "MPFS professional fee with a 90-day global surgical period — the "
            "surgical fee bundles the operation plus pre- and post-op visits; "
            "RVUs × GPCI × the annual conversion factor, or a commercial multiple.",
            "Medicare ASC / hospital-outpatient (OPPS) facility fee — the anchor "
            "ancillary; the inpatient-only-list removals (TKA 2018, THA 2020) and "
            "ASC-covered-procedure additions migrated total joints to the ASC.",
            "Implant / device cost — a large share of the joint-replacement "
            "facility payment; device pricing and the supply chain set ASC case "
            "margin (and raise physician-owned-distributorship AKS questions).",
            "Bundled-episode payment — CJR (mandatory in selected markets), BPCI "
            "Advanced, and the mandatory TEAM model (2026) pay a fixed episode "
            "price for joint replacement; the platform keeps savings and bears "
            "overruns.",
            "Physical-therapy fee schedule — per-visit/per-15-minute-unit under "
            "MPFS therapy, with the multiple-procedure payment reduction and the "
            "KX-modifier threshold (the former therapy cap).",
            "In-office imaging technical component, DME/bracing (L-code "
            "orthotics), and workers'-comp fee schedules (state-set, often "
            "higher) round out the ancillary revenue.",
        ],
        reimbursement_risk=(
            "The professional fee faces the same MPFS conversion-factor drift as "
            "every specialty, compounded by CMS proposals to revalue or unbundle "
            "the 10/90-day global surgical periods. The ancillary base carries "
            "ortho-specific risk: episode bundles (CJR/BPCI/TEAM) compress the "
            "joint-replacement payment and put the implant COGS squarely in the "
            "platform's risk; site-of-service and site-neutral policy move cases "
            "and rates between inpatient, HOPD, and ASC; and imaging and PT "
            "self-referral draw Stark scrutiny (studies have found self-referral "
            "raises utilization). The offsetting strength is that owning the full "
            "episode lets a disciplined platform turn bundle risk into margin — "
            "which is why value-based MSK is the differentiated thesis rather "
            "than a threat."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("Medicare Inpatient-Only list & ASC-Covered-Procedures list",
                 "The site-of-service rules that moved total joints out of the "
                 "hospital and into the surgeon-owned ASC — the facility-fee "
                 "capture opportunity.",
                 "https://www.cms.gov/medicare/payment/prospective-payment-systems/ambulatory-surgical-center-asc"),
            Rule("Bundled-episode models — CJR / BPCI Advanced / TEAM (2026)",
                 "Fixed-price joint-replacement episodes; the mandatory TEAM "
                 "model extends episodic risk to more markets in 2026.",
                 "https://www.cms.gov/priorities/innovation/innovation-models/cjr"),
            Rule("Medicare Physician Fee Schedule + global-period revaluation",
                 "Sets the surgical professional fee; CMS has probed unbundling "
                 "the 10/90-day globals, a direct hit to surgical fee structure.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
            Rule("Physician self-referral law (Stark, 42 CFR 411.350+)",
                 "The in-office ancillary-services exception is what makes owned "
                 "imaging, PT, and the ASC legal; imaging/PT self-referral draws "
                 "utilization scrutiny.",
                 "https://www.cms.gov/medicare/regulations-guidance/physician-self-referral"),
            Rule("OIG Special Fraud Alert — physician-owned distributorships "
                 "(PODs)",
                 "Flags surgeon-owned implant distributorships as a suspect "
                 "Anti-Kickback arrangement — a device-supply-chain diligence gate.",
                 "https://oig.hhs.gov/documents/special-fraud-alerts/"),
            Rule("Corporate Practice of Medicine (CPOM) doctrine (state law)",
                 "Bars lay/corporate ownership of the practice in ~half the "
                 "states; forces the friendly-PA/MSO structure the PE model rides.",
                 None),
        ],
        policy_watch=[
            "Mandatory TEAM episode model (2026) extending bundle risk to more "
            "hospitals and markets",
            "Continued inpatient-only-list / ASC-covered-list expansion migrating "
            "cases (and facility fees)",
            "Site-neutral payment convergence across inpatient / HOPD / ASC",
            "MPFS global-surgical-period revaluation or unbundling",
            "Implant PODs and device-cost transparency enforcement",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "US orthopedics is highly fragmented across independent "
            "single-specialty groups and a layer of large regional supergroups "
            "(Rothman, OrthoCarolina, Illinois Bone & Joint). Consolidation is "
            "younger than in dermatology or GI but accelerating. The acquirable "
            "pool is the independent group or supergroup with an owned ASC and "
            "physical-therapy footprint."),
        hhi_or_share=(
            "No single owner is dominant nationally; concentration is regional. "
            "No vendored physician-practice roll captures operator concentration, "
            "so a national chain HHI is honestly omitted — the corpus deal "
            "history below is the real read. Upstream, the joint-implant market "
            "is itself concentrated among four device makers, which shapes the "
            "COGS side of ASC economics."),
        consolidation=(
            "Orthopedics is the current specialty-roll-up frontier. The model is "
            "specialty-specific buy-and-build: acquire an anchor supergroup with "
            "an ASC and PT, tuck in independents, centralize the MSO, migrate "
            "cases into the owned surgery center, and layer value-based MSK "
            "episode contracts. The harder-to-haircut surgeon economics push the "
            "thesis toward facility/ancillary capture and episode ownership more "
            "than the compensation spread that powers derm/GI."),
        pe_activity=(
            "Increasingly PE-active — United Musculoskeletal Partners (Welsh "
            "Carson), OrthoAlliance (Revelstoke), US Orthopaedic Partners, and "
            "HOPCo built platforms across the last several years, with HOPCo "
            "distinguishing on value-based MSK management. Diligence centers on "
            "ASC case-migration runway, implant-cost management, bundle exposure, "
            "and — above all — surgeon retention and alignment."),
        notable_players=[
            "United Musculoskeletal Partners (Resurgens)", "OrthoAlliance",
            "US Orthopaedic Partners", "HOPCo (value-based MSK)",
            "Rothman Orthopaedics", "OrthoCarolina", "Illinois Bone & Joint",
            "EmergeOrtho",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Surgical cases / surgeon / yr", "specialty-mix dependent",
                "The volume engine behind the professional fee and the facility "
                "fee; joint, spine, and sports-med mix drives yield."),
            Kpi("ASC case-migration rate", "share of eligible cases in the ASC",
                "How much surgical volume is captured in the owned surgery center "
                "versus the hospital — the facility-fee lever."),
            Kpi("Implant cost / case (device COGS)", "~30-50% of facility fee",
                "The joint-replacement margin swing; device pricing and supply "
                "chain make or break ASC joint economics."),
            Kpi("PT visits / surgical episode", "episode-dependent",
                "The post-acute ancillary; owned physical therapy captures the "
                "rehab margin and supports value-based episode performance."),
            Kpi("Ancillary revenue (% of total)", "40-55%",
                "ASC facility + PT + imaging + DME — the highest ancillary share "
                "of any specialty."),
            Kpi("Platform EBITDA margin (post-MSO)", "15-22% (illustrative)",
                "Facility- and ancillary-rich ortho runs at the higher end of "
                "physician-services margins."),
        ],
        margin_profile=(
            "Orthopedic economics are dominated by surgeon compensation, but the "
            "differentiator is the breadth of the ancillary stack: an owned "
            "surgery center, physical therapy, in-office imaging, DME/bracing, "
            "and injections all earn margin off the same patient the professional "
            "fee barely covers. The ASC is a high-fixed-cost chassis whose "
            "facility-fee margin steps up with case migration — except in joint "
            "replacement, where the implant COGS (30-50% of the facility payment) "
            "can compress the case, making device management the single biggest "
            "operating variable. Because surgeons earn the most and are the "
            "hardest to comp-haircut, the platform's margin comes from capturing "
            "facility and ancillary revenue and from performing under bundled "
            "episodes — not from the compensation spread that powers lower-acuity "
            "specialty roll-ups."),
    ),
    risks=[
        Risk("Implant / device COGS inflation compressing ASC joint economics",
             "High",
             "The implant is 30-50% of the joint-replacement facility payment; "
             "device pricing directly determines whether ASC joints are "
             "profitable."),
        Risk("Physician retention (high-earner surgeons, weaker haircut lever)",
             "High",
             "Surgeons are the EBITDA and the hardest to comp-haircut, with "
             "hospital and independent-ASC alternatives; misalignment drives "
             "defection."),
        Risk("Bundled / episodic payment compression (CJR / BPCI / TEAM)",
             "Medium",
             "Fixed-price joint-replacement episodes squeeze the payment and put "
             "implant and post-acute cost in the platform's risk."),
        Risk("Site-of-service / inpatient-only-list & site-neutral shifts",
             "Medium",
             "Policy moves cases and rates across inpatient, HOPD, and ASC — the "
             "facility-fee capture thesis is exposed both ways."),
        Risk("Stark / AKS on imaging & PT self-referral and implant PODs",
             "Medium",
             "The ancillary engine depends on the in-office ancillary exception; "
             "PODs are an OIG-flagged device-supply arrangement."),
        Risk("MPFS conversion-factor + global-period revaluation", "Medium",
             "A structural squeeze on the surgical professional fee with no "
             "inflation update, plus proposed global-period unbundling."),
        Risk("Multiple compression on exit", "Medium",
             "A maturing ortho roll-up and higher rates pressure the arbitrage "
             "the thesis is priced on."),
    ],
    diligence_questions=[
        "What share of surgical volume already runs through the owned ASC, and "
        "how much eligible case-migration runway remains?",
        "What is the implant/device cost per case and the supply-chain / GPO "
        "arrangement — and is there any physician-owned-distributorship exposure?",
        "What share of EBITDA is ancillary (ASC facility, PT, imaging, DME), and "
        "how exposed is it to Stark and site-neutral repricing?",
        "What is the bundled-episode exposure (CJR/BPCI/TEAM), and how has the "
        "platform performed against episode targets?",
        "What is the post-close surgeon compensation and alignment model, and "
        "how retention-durable are the top revenue-generating surgeons?",
        "What is the case mix (joints, spine, sports, trauma) and the payer mix, "
        "including the workers'-comp share and its rate position?",
        "What is the value-based MSK / risk-contract book, and is the platform "
        "an episode price-taker or a capable risk-bearer?",
        "How much of the value plan is ASC/ancillary capture versus multiple "
        "arbitrage, and what does the exit universe look like?",
    ],
    insider_lens=[
        "Ortho has the deepest ancillary stack in medicine. The surgery-center "
        "facility fee, in-office MRI, physical therapy, DME/bracing, injections, "
        "and pain all earn off the same patient — the surgeon's professional fee "
        "is a fraction of the economic footprint the surgeon generates.",
        "The total-joint migration to the ASC is the defining play. CMS took "
        "knees and hips off the inpatient-only list, so a joint done in a "
        "surgeon-owned center captures a facility fee that used to be the "
        "hospital's — but the implant COGS is the swing variable that decides "
        "whether that capture is profitable.",
        "Surgeons are the hardest to comp-haircut. They earn the most and can "
        "walk to a hospital or their own ASC, so the derm/GI compensation-spread "
        "playbook works less well; the value has to come from facility, "
        "ancillary, and episode economics.",
        "Value-based MSK is the differentiated thesis. A musculoskeletal episode "
        "is expensive and variable, so a platform that owns the full episode "
        "(HOPCo-style) can turn bundle risk into margin — the opposite of a "
        "price-taker bleeding on CJR.",
        "The implant is where the money leaks. In joint replacement the device "
        "is 30-50% of the facility payment, so a target's GPO contract and "
        "device-standardization discipline are first-order — and any "
        "physician-owned distributorship is an OIG red flag, not a footnote.",
        "Workers' comp is a quiet high-rate payer. A book heavy in comp and "
        "sports-medicine trauma yields differently than a Medicare joint book — "
        "the payer mix, not just the case mix, sets the realized revenue.",
    ],
    connections=default_connections(
        "orthopedics",
        deals_sector="orthopedics",
        extra_pages=[
            ("/industry/orthopedics",
             "Industry deep-dive — orthopedics deal history + MSK ancillary read"),
        ],
        connectors=[
            ("npi_provider_taxonomy",
             "NPI taxonomy — orthopedic-surgery specialty mix & enrollment"),
            ("cms_open_data_mup_physician_by_provider_service",
             "Medicare physician utilization — surgical volume & allowed charges"),
            ("provider_data_asc_quality_facility",
             "CMS ASC quality file — orthopedic surgery-center footprint"),
            ("cms_open_data_mup_outpatient_by_provider_service",
             "Medicare outpatient (HOPD) service volume — site-of-service read"),
            ("open_payments_general_payments_2024",
             "Open Payments — device-maker payments to orthopedic surgeons"),
            ("census_acs_cbsa_profile",
             "Census ACS — CBSA age demographics for joint-replacement demand"),
        ],
    ),
    sources=[
        Source("CMS — OPPS / Ambulatory Surgical Center Payment System Final "
               "Rule (inpatient-only & ASC-covered lists)", "GOV",
               "https://www.cms.gov/medicare/payment/prospective-payment-systems/ambulatory-surgical-center-asc"),
        Source("CMS Innovation Center — CJR / BPCI Advanced / TEAM bundled "
               "joint-replacement episode models", "GOV",
               "https://www.cms.gov/priorities/innovation/innovation-models/cjr"),
        Source("CMS — Medicare Physician Fee Schedule annual Final Rule (RVUs, "
               "conversion factor, global periods)", "GOV",
               "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
        Source("American Academy of Orthopaedic Surgeons — orthopaedic census "
               "and joint-replacement volume projections (JBJS)", "ACADEMIC",
               "https://www.aaos.org/quality/research-resources/census/"),
        Source("OIG — Special Fraud Alert on physician-owned distributorships "
               "(implant PODs)", "GOV",
               "https://oig.hhs.gov/documents/special-fraud-alerts/"),
        Source("Physician self-referral law (Stark, 42 CFR 411.350+)", "GOV",
               "https://www.cms.gov/medicare/regulations-guidance/physician-self-referral"),
        Source("PE Desk industry deep-dive (orthopedics) + realized-deal "
               "corpus", "INTERNAL",
               "/diligence/tam-sam?template=orthopedics"),
    ],
    live_figures=live_figures_from_dive("orthopedics"),
    trends=(
        "Orthopedics is the current specialty-roll-up frontier — later than "
        "dermatology and gastroenterology and now accelerating, because it "
        "carries the deepest ancillary stack in medicine. The economic story of "
        "the last decade is site-of-service: CMS removed total knee replacement "
        "from the inpatient-only list in 2018 and total hip in 2020 and added "
        "them to the ASC-covered list, migrating high-value joints from the "
        "hospital to the surgeon-owned surgery center and putting a facility fee "
        "— previously the hospital's — into the platform's hands. The swing "
        "variable is the implant: at 30-50% of the joint-replacement facility "
        "payment, device cost decides whether ASC joints are profitable. In "
        "parallel, bundled and episodic payment (CJR, BPCI Advanced, and the "
        "mandatory 2026 TEAM model) is compressing episode prices and rewarding "
        "platforms that can own the full episode — the value-based MSK thesis "
        "HOPCo built. Because surgeons are high earners who are hard to "
        "comp-haircut, the forward thesis is about ASC case migration, implant "
        "and post-acute cost discipline, and episode ownership, not the "
        "compensation spread that powered earlier specialty deals."),
    growth_levers=[
        GrowthLever(
            "Total-joint ASC migration (facility-fee capture)",
            "Inpatient-only-list removals moved knees and hips to the "
            "surgeon-owned surgery center, capturing a facility fee that used to "
            "go to the hospital.",
            "primary / + facility fee", "GOV"),
        GrowthLever(
            "Ancillary stack (PT, imaging, DME, orthobiologics)",
            "Own the physical therapy, imaging, and bracing the surgeon already "
            "generates — the durable, non-arbitrage margin lever.",
            "+ ancillary margin", "ILLUSTRATIVE"),
        GrowthLever(
            "Value-based MSK / bundled-episode ownership",
            "Take episode risk and keep the savings by managing the full "
            "musculoskeletal episode — the differentiated play.",
            "risk-based upside", "ILLUSTRATIVE"),
        GrowthLever(
            "Demographic joint-replacement volume",
            "Aging and obesity-driven osteoarthritis lift total-joint demand at "
            "a durable rate.",
            "+ structural volume", "ACADEMIC"),
        GrowthLever(
            "Consolidation multiple arbitrage",
            "Acquire independent groups and supergroups at lower multiples and "
            "re-rate the platform on scale, ASC, and ancillaries.",
            "supporting", "ILLUSTRATIVE"),
        GrowthLever(
            "Bundle + MPFS rate compression",
            "Episode-payment squeeze and a flat-to-declining professional fee "
            "are the structural headwind.",
            "rate headwind", "GOV"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Osteoarthritis-driven joint-replacement demand (aging × obesity)",
        analysis=(
            "The dominant demand driver is degenerative joint disease — "
            "osteoarthritis of the knee and hip — driven by an aging population "
            "and rising obesity. Total knee and hip replacements already run at "
            "roughly 1.8M+ procedures per year, and peer-reviewed projections "
            "(AAOS/JBJS) have long pointed to strong secular growth in primary "
            "and revision arthroplasty as the population ages. That demand is "
            "largely non-discretionary once a joint fails, and it is precisely "
            "the high-value volume the ASC-migration thesis is built to capture. "
            "Sports-medicine, spine, trauma/fracture (osteoporosis-driven), and "
            "hand volume layer on top. The credible offsets are slow: better "
            "conservative care, orthobiologics, and weight-loss drugs (GLP-1s) "
            "may defer some replacements at the margin, but none materially bend "
            "the arthroplasty curve within a typical hold."),
        basis="ACADEMIC"),
    cost_drivers=[
        CostDriver(
            "Physician / surgeon & advanced-practice compensation",
            "~40-50% of cost",
            "The dominant cost; high-earning surgeons are hard to comp-haircut, "
            "so retention economics differ from lower-acuity specialties.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Implant / device COGS (joint & spine hardware)",
            "~30-50% of a joint-replacement facility case",
            "The single biggest ASC-joint margin swing; GPO contracting and "
            "device standardization are core operating levers.", "ILLUSTRATIVE"),
        CostDriver(
            "ASC + PT clinical staff", "~15-20% of cost",
            "The labor running the surgery center and the physical-therapy "
            "clinics — a fixed cost scale spreads.", "ILLUSTRATIVE"),
        CostDriver(
            "Imaging & facility capital / occupancy", "~8-12% of cost",
            "In-office MRI/X-ray equipment and the ASC/clinic real estate — the "
            "capital chassis behind the facility and imaging fees.",
            "ILLUSTRATIVE"),
        CostDriver(
            "MSO back office (billing/RCM, IT, compliance)", "~10% of cost",
            "The shared-services and compliance apparatus the ancillary- and "
            "bundle-heavy structure requires.", "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "No national physician-practice facility file is vendored — an "
        "orthopedic group is a business, not a Medicare-certified facility — so "
        "state geography is omitted rather than fabricated. The most "
        "consequential geographic variables are the corporate-practice-of-"
        "medicine doctrine, state ASC licensure and certificate-of-need regimes "
        "(which gate where a surgeon-owned surgery center can open and are the "
        "single biggest constraint on the ASC-migration thesis), whether a "
        "market falls inside a mandatory bundled-episode footprint (CJR/TEAM), "
        "and the state workers'-compensation fee schedule. The NPI-taxonomy, "
        "Medicare physician- and outpatient-utilization, ASC-quality, and "
        "demographic connectors linked below map orthopedic supply, surgical "
        "volume, and joint-replacement demand — the honest footprint read."),
)

register(REPORT)
