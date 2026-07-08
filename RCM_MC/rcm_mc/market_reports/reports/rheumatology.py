"""Rheumatology — the cognitive specialty that lives on the infusion suite.

Deals-only deep-dive (no national physician-practice facility file; geography is
omitted rather than fabricated). Rheumatology is the archetypal "cognitive"
specialty — complex autoimmune diagnosis and long visits, poorly paid on E&M
RVUs — that survives economically on the buy-and-bill infusion suite. In-office
Part B biologics (infliximab, rituximab, abatacept, tocilizumab, belimumab,
IVIG) administered at ASP-plus are the margin engine that subsidizes the thin
cognitive fee. That makes two forces existential: the payer "white bagging" war
to strip the buy-and-bill spread, and a severe, worsening rheumatologist
workforce shortage. Uniquely, the specialty consolidated more through group
purchasing organizations (GPOs) for the drugs than through classic facility
roll-ups. The qualitative sections are authored around the buy-and-bill
economics, white/brown bagging, biosimilars, and the GPO/MSO structure.
Consumes ``rheumatology_deep_dive()`` for SOURCED corpus deal figures where
present.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="rheumatology",
    name="Rheumatology",
    care_setting="Physician services",
    naics="621111",
    one_line_def=(
        "Physician practices diagnosing and managing systemic autoimmune and "
        "inflammatory disease — rheumatoid arthritis, lupus, psoriatic "
        "arthritis, axial spondyloarthritis, gout, and vasculitis — where the "
        "cognitive visit is poorly paid but the owned in-office infusion suite "
        "(buy-and-bill biologics at ASP-plus) is the margin engine, and the "
        "sector consolidated as much through drug-purchasing GPOs as through "
        "classic practice roll-ups."),
    tam_headline=TamHeadline(
        value=13.0, unit="$B", growth_pct=6.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "Modeled from the ~5,000-6,000 practicing US adult rheumatologists "
            "(ACR workforce study) times the cognitive professional fee plus "
            "the infusion-administration and ancillary (DXA, ultrasound, lab) "
            "stack — the SERVICES-and-administration base, not the far larger "
            "buy-and-bill drug throughput that flows through practice revenue at "
            "thin margin, and not a single published figure. Growth is the "
            "modeled composite of autoimmune-disease prevalence, aging, and new "
            "biologics, net of white-bagging spread loss and biosimilar "
            "erosion."),
    ),
    executive_summary=[
        "The visit is a loss leader; the infusion suite is the business. "
        "Rheumatology is a cognitive specialty — complex diagnosis, long "
        "visits — that Medicare's RVU system underpays, so the economics rest "
        "on the owned in-office infusion suite, where buy-and-bill biologics "
        "(infliximab, rituximab, abatacept, tocilizumab, belimumab, IVIG) are "
        "administered at ASP-plus.",
        "White bagging is the existential threat. Payers increasingly force the "
        "drug to be sourced from their own specialty pharmacy and shipped to "
        "the practice ('white bagging') or the patient ('brown bagging'), "
        "stripping the buy-and-bill ASP-plus spread that the whole model "
        "depends on — the single most important reimbursement fight in the "
        "sector.",
        "Rheumatology consolidated through drugs, not facilities. Because the "
        "value concentrates in buy-and-bill economics, the sector aggregated "
        "heavily via group purchasing organizations and MSOs (Bendcare, United "
        "Rheumatology, American Rheumatology Network) — a different shape from "
        "the GI/dermatology ASC roll-ups; the acquisition thesis is often "
        "drug-purchasing scale, not real estate.",
        "Workforce scarcity is severe and worsening. The ACR projects a large "
        "and growing rheumatologist shortfall with acute maldistribution; wait "
        "times run months and many regions are effectively deserts, so access "
        "and scarce-clinician retention — extended by APPs and telehealth — are "
        "the core constraint and the moat.",
        "Biosimilars cut both ways. Infliximab and, since 2023, adalimumab "
        "(Humira) biosimilars compress spreads, but adalimumab is largely a "
        "pharmacy self-injectable; the buy-and-bill exposure is to infusible "
        "biosimilar ASP resets — underwrite the spread by drug, not in the "
        "aggregate.",
        "Demand is a rising autoimmune burden meeting a shrinking supply. RA, "
        "lupus, and the spondyloarthropathies grow with an aging, more-obese "
        "population and better diagnosis; the acquirable pool is the "
        "independent single- or multi-specialty rheumatology group with an "
        "owned infusion suite and DXA/ultrasound/lab ancillaries.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Referral for joint pain, positive serology, or suspected "
            "autoimmune disease",
            "Cognitive E&M visit + diagnostic workup (rheumatology serology "
            "panel, imaging, in-office ultrasound)",
            "Diagnosis + treat-to-target plan (DMARDs → biologic/targeted "
            "therapy escalation)",
            "Benefits investigation + payer authorization / step therapy / "
            "site-of-care determination",
            "In-office infusion of a Part B biologic (buy-and-bill) OR "
            "specialty-pharmacy self-injectable (Part D)",
            "Ongoing disease monitoring, DXA bone-density scans, and joint "
            "injections",
            "Charge capture across the cognitive fee, infusion administration, "
            "drug, and ancillary lines",
        ],
        sites_of_care=[
            "Physician office / clinic (the cognitive visit, ultrasound, joint "
            "injections, DXA)",
            "Owned in-office infusion suite — the buy-and-bill margin engine",
            "Specialty pharmacy (self-injectable biologics; white/brown-bag "
            "site-of-care)",
            "Hospital outpatient infusion (payer site-of-care steerage — the "
            "competing venue)",
            "In-house / reference lab (autoimmune serology and monitoring)",
        ],
        money_flow=(
            "A rheumatologist earns a professional fee off the Medicare "
            "Physician Fee Schedule for the cognitive E&M visit — but "
            "rheumatology is one of the specialties that E&M valuation "
            "underpays relative to the time and complexity of autoimmune "
            "management, so the visit alone does not sustain the practice. The "
            "economics come from the owned infusion suite: for a Part B "
            "biologic, the practice buys the drug, bills Medicare or the "
            "commercial payer at Average Sales Price plus a margin (ASP+6% in "
            "Medicare), and separately bills infusion-administration codes — "
            "'buy-and-bill.' Self-injectable biologics instead run through the "
            "patient's Part D / specialty-pharmacy benefit, where the practice "
            "coordinates but captures no drug margin. Ancillary DXA scans, "
            "musculoskeletal ultrasound, joint injections, and lab add smaller "
            "streams. In the aggregated model the GPO negotiates drug "
            "acquisition and the MSO runs contracting, billing, and the benefit "
            "investigation. The single question that sets a rheumatology "
            "platform's value is how durable the buy-and-bill spread is against "
            "white bagging and biosimilar erosion — because the cognitive fee "
            "will not carry it."),
        key_players=(
            "The consolidators are as much drug-purchasing organizations as "
            "practice owners: Bendcare (GPO + MSO), United Rheumatology (GPO), "
            "American Rheumatology Network / ARN (Cardinal Health), and "
            "IntegraConnect (data/RCM) aggregate buy-and-bill economics across "
            "independent practices, while PE-backed groups such as Articularis "
            "Healthcare and American Arthritis & Rheumatology Associates build "
            "regional single-specialty platforms. The biologic and biosimilar "
            "manufacturers sit upstream and drive the buy-and-bill and pharmacy "
            "economics. The acquirable pool is the independent rheumatology "
            "group with an owned infusion suite and DXA/ultrasound/lab "
            "ancillaries."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Practicing US adult rheumatologists", "~5,000-6,000",
                    "INDUSTRY · ACR Workforce Study projections (directional)"),
            Segment("US adults with rheumatoid arthritis", "~1.3-1.5M",
                    "GOV · CDC / epidemiologic RA prevalence (directional)"),
            Segment("US adults with doctor-diagnosed arthritis (broad base)",
                    "~53M+",
                    "GOV · CDC arthritis surveillance (directional)"),
            Segment("Infusion/drug margin share of practice profit",
                    "the majority of profit (illustrative)",
                    "ILLUSTRATIVE · practice economics, directional"),
            Segment("US autoimmune biologic/targeted-therapy drug spend",
                    "tens of $B (gross, flows through practice revenue)",
                    "INDUSTRY · specialty-drug spend estimates (directional)"),
        ],
        growth_drivers=[
            "Rising autoimmune-disease prevalence + better/earlier diagnosis "
            "~3-4%/yr",
            "Aging + obesity expanding the inflammatory-arthritis and gout base",
            "New biologics and targeted therapies (JAK inhibitors, IL-pathway "
            "agents) expanding treatable indications",
            "Ancillary capture (DXA, musculoskeletal ultrasound, lab, joint "
            "injections)",
            "White-bagging spread loss + biosimilar erosion + MPFS/E&M drag — "
            "the structural offsets",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Medicare / MA": 0.45,
            "Commercial": 0.40,
            "Medicaid": 0.10,
            "Self-pay / other": 0.05,
        },
        rate_mechanics=[
            "MPFS cognitive professional fee for the E&M visit — RVUs × GPCI × "
            "the conversion factor; the base that autoimmune complexity "
            "outstrips, which is why the drug margin subsidizes it.",
            "Buy-and-bill Part B biologics (infliximab/Remicade, rituximab, "
            "abatacept/Orencia IV, tocilizumab/Actemra IV, belimumab/Benlysta "
            "IV, IVIG) at Average Sales Price + 6% (Medicare) — the margin "
            "engine.",
            "Infusion-administration codes (96365-96368, hydration/injection) "
            "billed separately for chair time and nursing.",
            "Self-injectable biologics (adalimumab/Humira, etanercept/Enbrel, "
            "and oral JAK inhibitors) run through Part D / specialty pharmacy — "
            "the practice coordinates but earns no buy-and-bill margin.",
            "White bagging / brown bagging — payer-mandated specialty-pharmacy "
            "sourcing of the drug that removes the buy-and-bill spread; a "
            "growing number of states have enacted white-bagging restrictions.",
            "Ancillary DXA bone-densitometry, musculoskeletal ultrasound, and "
            "in-office lab (serology/monitoring) — smaller technical/professional "
            "fees, DXA repeatedly cut in prior fee-schedule cycles.",
        ],
        reimbursement_risk=(
            "Rheumatology's reimbursement risk is unusually concentrated on the "
            "drug line. White bagging is the acute threat: when a payer forces "
            "the biologic to come from its own specialty pharmacy, the practice "
            "loses the buy-and-bill ASP-plus spread that funds the enterprise, "
            "and only the thin infusion-administration and cognitive fees "
            "remain — which is why state white-bagging bans are a live "
            "battleground. Biosimilars compress the spread on infusible drugs, "
            "though the largest biosimilar shift (adalimumab) is mostly a "
            "pharmacy event. Any change to the ASP+6 methodology (or sequester "
            "on it) directly hits margin. And the cognitive E&M base rides the "
            "same MPFS conversion-factor drift as every specialty while being "
            "structurally undervalued. The healthiest platforms diversify — "
            "multiple infusible drugs, DXA/ultrasound/lab ancillaries, and "
            "payer contracts that preserve in-office sourcing — so no single "
            "white-bagging mandate is fatal."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("Average Sales Price (ASP+6%) buy-and-bill methodology",
                 "Sets Part B reimbursement for in-office infusible biologics — "
                 "the margin engine of the specialty; ASP resets and the "
                 "Medicare sequester move the spread.",
                 "https://www.cms.gov/medicare/payment/part-b-drugs"),
            Rule("Payer white-bagging / brown-bagging policies + state bans",
                 "Payer mandates to source the drug from their specialty "
                 "pharmacy strip the buy-and-bill spread; a growing set of "
                 "states restrict white bagging — the sector's defining "
                 "reimbursement fight.",
                 None),
            Rule("Biosimilar approval + interchangeability (BPCIA)",
                 "Governs infliximab/rituximab/adalimumab biosimilar entry and "
                 "substitution that reshapes buy-and-bill and pharmacy "
                 "economics.",
                 "https://www.fda.gov/drugs/therapeutic-biologics-applications-bla/biosimilars"),
            Rule("Medicare Physician Fee Schedule (annual Final Rule) + E&M "
                 "valuation",
                 "Sets the cognitive-visit fee that autoimmune complexity "
                 "outstrips — the structural under-valuation the drug margin "
                 "offsets.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
            Rule("Payer step-therapy / prior-authorization and 'fail-first' "
                 "rules",
                 "Gate access to biologics and dictate which drug (and site of "
                 "care) is used — a direct control on the practice's drug mix "
                 "and margin.",
                 None),
            Rule("340B drug-pricing program (competing site economics)",
                 "340B hospital outpatient infusion buys biologics at a deep "
                 "discount, giving hospital-owned sites a structural cost edge "
                 "and fueling payer site-of-care steerage.",
                 "https://www.hrsa.gov/opa"),
        ],
        policy_watch=[
            "White-bagging / brown-bagging mandates vs state bans — the core "
            "buy-and-bill battleground",
            "Infusible biosimilar ASP resets and the Medicare sequester on the "
            "ASP add-on",
            "Payer site-of-care steerage (office vs 340B hospital outpatient) "
            "for biologic infusion",
            "E&M / cognitive-care valuation reform vs annual MPFS "
            "conversion-factor cuts",
            "State PE-in-healthcare transaction-review laws reaching "
            "rheumatology GPO/MSO structures",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "US rheumatology is highly fragmented across small independent "
            "practices, and it consolidated in an unusual shape: the aggregation "
            "happened largely through group purchasing organizations and MSOs "
            "that pool buy-and-bill drug economics, not through capital-heavy "
            "facility roll-ups. The acquirable pool is the independent "
            "rheumatology group with an owned infusion suite and ancillaries."),
        hhi_or_share=(
            "No single owner is dominant nationally; the concentration that "
            "matters is on the drug-purchasing side, where a few GPOs aggregate "
            "a meaningful share of buy-and-bill volume. No vendored "
            "physician-practice roll captures operator concentration, so a "
            "national chain HHI is honestly omitted — the corpus deal history "
            "below is the real read."),
        consolidation=(
            "Rheumatology's consolidation is drug-economics-led. GPOs (Bendcare, "
            "United Rheumatology, American Rheumatology Network) and MSOs give "
            "independent practices the buy-and-bill purchasing scale, contracting "
            "leverage, and benefit-investigation infrastructure that the "
            "infusion model requires. PE-backed single-specialty groups have "
            "layered classic buy-and-build on top in some regions, but the "
            "sector is earlier and more fragmented than GI or dermatology."),
        pe_activity=(
            "A younger PE story than the ancillary-ASC specialties, gated by the "
            "white-bagging threat to the core economics and by workforce "
            "scarcity. Diligence centers on buy-and-bill spread durability "
            "(white bagging, biosimilars, ASP), payer site-of-care exposure, "
            "and the ability to recruit and retain a scarce clinician against a "
            "structural shortage."),
        notable_players=[
            "Bendcare (GPO + MSO)", "United Rheumatology (GPO)",
            "American Rheumatology Network / ARN (Cardinal Health)",
            "IntegraConnect (data / RCM)", "Articularis Healthcare",
            "American Arthritis & Rheumatology Associates",
            "Biologic & biosimilar manufacturers (upstream drug economics)",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Buy-and-bill infusion margin (% of practice profit)",
                "the majority (illustrative)",
                "The ASP-plus spread on in-office biologics is what funds a "
                "specialty the cognitive fee cannot."),
            Kpi("Infusion chair utilization", "chairs × turns per day",
                "The infusion suite is a fixed-cost chassis; empty chairs and "
                "authorization delays kill the drug-margin economics."),
            Kpi("White-bag penetration (% of drug forced to SP)",
                "payer-mix-dependent",
                "The share of biologic volume a payer has pulled to its "
                "specialty pharmacy — direct erosion of buy-and-bill margin."),
            Kpi("Biologic/targeted-therapy patients per rheumatologist",
                "cohort-dependent",
                "The treated autoimmune cohort drives infusion and coordination "
                "volume; growth is diagnosis- and access-limited."),
            Kpi("Ancillary revenue (DXA / ultrasound / lab / injections)",
                "modest but real",
                "Bone density, MSK ultrasound, serology, and joint injections "
                "add diversified margin beyond the drug line."),
            Kpi("Platform EBITDA margin (post-MSO)", "12-20% (illustrative)",
                "Drug-margin-dependent; white bagging and biosimilar exposure "
                "swing it more than in facility-based specialties."),
        ],
        margin_profile=(
            "Rheumatology's margin structure is inverted from a procedural "
            "specialty: the cognitive work — the diagnostic reasoning that is "
            "the specialty's actual value — is the least-well-paid line, and the "
            "buy-and-bill infusion suite is what makes the practice viable. The "
            "profit therefore concentrates in the ASP-plus spread on a handful "
            "of infusible biologics plus the separately-billed infusion "
            "administration, supplemented by DXA, ultrasound, lab, and joint "
            "injections. Because that profit sits on the drug line, it is more "
            "exposed than most specialties to a single policy variable — white "
            "bagging — and to biosimilar ASP dynamics. Scale helps chiefly "
            "through drug-purchasing (GPO) leverage, benefit-investigation "
            "infrastructure, and payer contracting that preserves in-office "
            "sourcing; the underlying quality of a rheumatology platform is the "
            "durability of its buy-and-bill spread and its ability to keep a "
            "scarce clinician in the chair."),
    ),
    risks=[
        Risk("White bagging / brown bagging (buy-and-bill spread loss)", "High",
             "Payer-mandated specialty-pharmacy sourcing strips the ASP-plus "
             "margin that funds the specialty — the single biggest economic "
             "threat."),
        Risk("Rheumatologist recruitment / retention in a structural shortage",
             "High",
             "A worsening ACR-projected shortfall makes scarce-clinician "
             "retention the core capacity constraint and integration risk."),
        Risk("Biosimilar / ASP erosion of infusible-drug spread", "Medium",
             "Infliximab and other infusible biosimilars compress the "
             "buy-and-bill spread; ASP resets move margin drug-by-drug."),
        Risk("Payer site-of-care steerage to 340B hospital outpatient",
             "Medium",
             "Deep 340B drug discounts let hospital sites underprice office "
             "infusion, and payers steer volume there."),
        Risk("Prior-authorization / step-therapy friction", "Medium",
             "Authorization delays and fail-first rules throttle biologic "
             "starts and idle infusion capacity."),
        Risk("MPFS / cognitive-E&M under-valuation", "Medium",
             "The structurally-underpaid cognitive base leaves the practice "
             "dependent on the drug margin it may lose."),
    ],
    diligence_questions=[
        "What share of practice profit is buy-and-bill infusion margin, and how "
        "concentrated is it across drugs?",
        "What is white-bag / brown-bag penetration by payer today, and what is "
        "the trajectory and the state-law posture in the footprint?",
        "What is the infusible-drug mix, and what is the biosimilar / ASP-reset "
        "exposure to the spread over the hold?",
        "What is the GPO / drug-purchasing arrangement, and how much of the "
        "acquisition thesis is purchasing scale versus organic growth?",
        "What is the rheumatologist and APP staffing, age profile, and "
        "recruitment pipeline against a structural shortage?",
        "What is the infusion-chair utilization and the prior-authorization "
        "cycle time that gates it?",
        "How exposed is the practice to payer site-of-care steerage toward "
        "340B hospital outpatient infusion?",
        "What is the ancillary contribution (DXA, ultrasound, lab, injections), "
        "and how diversified is profit away from the single drug line?",
    ],
    insider_lens=[
        "The diagnosis is the value; the drug is the money. Rheumatology is a "
        "cognitive specialty whose actual product — untangling complex "
        "autoimmune disease — is the worst-paid thing it does, so the practice "
        "survives on the buy-and-bill infusion suite. That inversion is the "
        "whole thesis and the whole fragility.",
        "White bagging is the number that can break the model. If a payer "
        "forces the biologic to ship from its own specialty pharmacy, the "
        "ASP-plus spread that funds the practice vanishes and only the thin "
        "administration and cognitive fees remain — track white-bag penetration "
        "by payer, and the state-law bans that push back, before believing the "
        "margin.",
        "Rheumatology rolled up through drugs, not real estate. Unlike GI or "
        "derm, the aggregation happened via GPOs (Bendcare, United "
        "Rheumatology, ARN) that pool buy-and-bill purchasing — the deal is "
        "often a drug-economics play wearing a practice-management label, which "
        "changes what you are actually buying.",
        "Biosimilars are a drug-by-drug story, not a headline. Adalimumab's "
        "biosimilar wave is mostly a pharmacy event that barely touches "
        "buy-and-bill; the real infusion exposure is to infliximab and other "
        "infusible biosimilar ASP resets — underwrite the spread per molecule.",
        "Scarcity is the moat and the ceiling. The ACR projects a deepening "
        "rheumatologist shortage with months-long waits and true care deserts, "
        "so access is genuinely valuable — but the same scarcity caps organic "
        "growth and makes retaining every clinician (and leveraging APPs and "
        "telehealth) the entire operating game.",
        "340B is the silent competitor. Hospital outpatient sites buy the same "
        "biologics at 340B discounts and can underprice the independent "
        "infusion suite, which is exactly why payers steer site-of-care there — "
        "the office model competes against a structurally cheaper drug cost.",
    ],
    connections=default_connections(
        "rheumatology",
        deals_sector="rheumatology",
        extra_pages=[
            ("/industry/rheumatology",
             "Industry deep-dive — rheumatology deal history + buy-and-bill "
             "read"),
        ],
        connectors=[
            ("npi_provider_taxonomy",
             "NPI taxonomy — rheumatology specialty mix & practice enrollment"),
            ("cms_open_data_part_b_spending_by_drug",
             "Medicare Part B drug spending — buy-and-bill biologic (infliximab, "
             "rituximab) read"),
            ("cms_open_data_mup_physician_by_provider_service",
             "Medicare physician utilization — infusion-administration & E&M "
             "volume"),
            ("cms_open_data_part_d_spending_by_drug",
             "Medicare Part D drug spending — self-injectable/oral biologic "
             "(adalimumab, JAK) read"),
            ("open_payments_general_payments_2024",
             "Open Payments — biologic-maker payments to rheumatologists "
             "(relationship screen)"),
            ("cdc_data_chronic_disease_indicators",
             "CDC chronic-disease indicators — arthritis prevalence for demand "
             "mapping"),
        ],
    ),
    sources=[
        Source("American College of Rheumatology — Workforce Study of "
               "Rheumatology Specialists (supply/demand projections)",
               "INDUSTRY", "https://rheumatology.org/workforce-shortage"),
        Source("CMS — Average Sales Price (ASP) methodology and Part B drug "
               "payment files (buy-and-bill)", "GOV",
               "https://www.cms.gov/medicare/payment/part-b-drugs"),
        Source("CMS — Medicare Physician Fee Schedule annual Final Rule (E&M, "
               "infusion administration, DXA)", "GOV",
               "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
        Source("US FDA — Biosimilar approvals and interchangeability (BPCIA)",
               "GOV",
               "https://www.fda.gov/drugs/therapeutic-biologics-applications-bla/biosimilars"),
        Source("CDC — arthritis and rheumatoid-arthritis prevalence "
               "surveillance", "GOV",
               "https://www.cdc.gov/arthritis/data-statistics/"),
        Source("PE Desk industry deep-dive (rheumatology) + realized-deal "
               "corpus", "INTERNAL",
               "/diligence/tam-sam?template=rheumatology"),
    ],
    live_figures=live_figures_from_dive("rheumatology"),
    trends=(
        "Rheumatology's story is defined by an inversion: it is a cognitive "
        "specialty that the RVU system underpays for its actual work — "
        "diagnosing complex autoimmune disease — so its economics rest on the "
        "buy-and-bill infusion suite. That shaped an unusual consolidation: the "
        "sector aggregated less through capital-heavy facility roll-ups and more "
        "through group purchasing organizations (Bendcare, United Rheumatology, "
        "ARN) that pool drug-buying scale. Two forces now dominate the "
        "trajectory. First, payers are attacking the buy-and-bill spread "
        "directly through white bagging and brown bagging — mandating that the "
        "drug come from their own specialty pharmacy — and site-of-care "
        "steerage toward 340B hospital outpatient infusion; a growing set of "
        "state white-bagging bans is the counter. Second, the workforce is "
        "shrinking against rising demand: the ACR projects a deepening "
        "shortfall with months-long waits and care deserts, so access is scarce "
        "and clinician retention is paramount. Biosimilars compress infusible "
        "spreads while the largest (adalimumab) plays out mostly in pharmacy. "
        "Quality-of-earnings work now centers on buy-and-bill spread durability "
        "and scarce-clinician retention, not visit count."),
    growth_levers=[
        GrowthLever(
            "Buy-and-bill infusion capture",
            "Own the in-office infusion suite and the ASP-plus spread on "
            "infusible biologics — the specialty's margin engine.",
            "primary / white-bag-gated", "ILLUSTRATIVE"),
        GrowthLever(
            "GPO / drug-purchasing scale",
            "Aggregate buy-and-bill purchasing and contracting leverage across "
            "practices to widen the acquisition cost advantage.",
            "+ purchasing margin", "ILLUSTRATIVE"),
        GrowthLever(
            "Rising autoimmune prevalence + new biologics",
            "Growing, better-diagnosed autoimmune disease and an expanding "
            "biologic/targeted-therapy armamentarium enlarge the treated "
            "cohort.",
            "+ steady volume", "GOV"),
        GrowthLever(
            "Ancillary capture (DXA / ultrasound / lab / injections)",
            "Bone density, MSK ultrasound, serology, and joint injections "
            "diversify margin beyond the drug line.",
            "+ ancillary margin", "ILLUSTRATIVE"),
        GrowthLever(
            "APP + telehealth leverage of scarce clinicians",
            "Advanced-practice providers and telerheumatology extend a scarce "
            "workforce over more patients.",
            "+ access / capacity", "ILLUSTRATIVE"),
        GrowthLever(
            "White bagging + biosimilar ASP erosion + E&M drag",
            "Payer specialty-pharmacy mandates, infusible biosimilar resets, "
            "and cognitive-fee under-valuation are the structural headwind.",
            "rate + policy headwind", "ILLUSTRATIVE"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Autoimmune-disease burden vs a shrinking rheumatology supply",
        analysis=(
            "The demand base is systemic autoimmune and inflammatory disease — "
            "rheumatoid arthritis (~1.3-1.5M US adults), lupus, psoriatic "
            "arthritis, axial spondyloarthritis, gout, and vasculitis — growing "
            "with an aging, more-obese population and earlier, better diagnosis, "
            "and with an expanding menu of biologics and targeted synthetic "
            "DMARDs (including JAK inhibitors) that pull more patients into "
            "treatment. The defining feature is that this rising demand meets a "
            "shrinking supply: the ACR projects a large and worsening "
            "rheumatologist shortfall with severe geographic maldistribution, so "
            "realized volume is gated less by disease prevalence than by access "
            "to a scarce clinician — which is why APP leverage and telehealth "
            "matter so much. The genuine offsets are economic, not demographic: "
            "white bagging and biosimilar erosion threaten the margin on the "
            "treated cohort rather than the size of the cohort itself."),
        basis="GOV"),
    cost_drivers=[
        CostDriver(
            "Buy-and-bill drug COGS (infusible biologics)",
            "large gross / thin net",
            "Drug acquisition dominates gross cost; the practice's economics "
            "are the thin ASP-plus spread over this, squeezed by white bagging "
            "and biosimilars.", "ILLUSTRATIVE"),
        CostDriver(
            "Physician & advanced-practice compensation", "~30-40% of cost",
            "The scarce clinician is both the biggest fixed cost and the "
            "capacity constraint; retention is the core operating risk.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Infusion-suite nursing + benefit investigation", "~12-18% of cost",
            "Infusion RNs and the prior-authorization / benefit-investigation "
            "staff that keep the chairs full — a labor-heavy chassis.",
            "ILLUSTRATIVE"),
        CostDriver(
            "MSO / GPO back office (billing/RCM, contracting)",
            "~10-15% of cost",
            "The shared-services, drug-purchasing, and payer-contracting "
            "apparatus the buy-and-bill model requires.", "ILLUSTRATIVE"),
        CostDriver(
            "Ancillary equipment + facility/occupancy", "~6-10% of cost",
            "DXA, ultrasound, and lab equipment plus the clinic real estate and "
            "the infusion-suite build-out.", "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "No national physician-practice facility file is vendored — a "
        "rheumatology group is a business, not a Medicare-certified facility — "
        "so state geography is omitted rather than fabricated. The most "
        "consequential geographic variables are state white-bagging / "
        "brown-bagging laws (which states restrict payer specialty-pharmacy "
        "mandates and thereby protect the buy-and-bill spread), the acute "
        "geographic maldistribution of the scarce rheumatology workforce (large "
        "swaths of the country are effective care deserts), the "
        "corporate-practice-of-medicine doctrine, and the growing set of states "
        "enacting PE-in-healthcare transaction-review laws. The NPI-taxonomy, "
        "Part B and Part D drug-spending, physician-utilization, and "
        "chronic-disease connectors linked below map rheumatology supply and "
        "buy-and-bill volume against arthritis prevalence — the honest "
        "footprint read."),
)

register(REPORT)
