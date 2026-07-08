"""Ambulatory Surgery Centers (ASC) — physician-owned outpatient surgery.

Deals-only deep-dive (no vendored all-payer ASC facility file; the CMS ASC
Quality file is a connector, not a state roll for analytics). The whole thesis
is site-of-service migration out of the hospital outpatient department (HOPD)
into the lower-cost, frequently physician-owned ASC — so the qualitative
sections are authored around the ASC payment system's discount to HOPD, the
physician-investment safe harbor, and case-/payer-mix economics. Consumes
``asc_deep_dive()`` for SOURCED corpus deal figures.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="asc",
    name="Ambulatory Surgery (ASC)",
    care_setting="Ambulatory",
    naics="621493",
    one_line_def=(
        "Licensed freestanding facilities where surgical and procedural cases "
        "are done same-day without an overnight stay — a lower-cost site of "
        "service than the hospital outpatient department (HOPD), paid a "
        "packaged facility fee under the Medicare ASC payment system and "
        "usually physician-owned or physician/hospital joint-ventured."),
    tam_headline=TamHeadline(
        value=40.0, unit="$B", growth_pct=6.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "All-payer US ASC facility-services revenue is commercial-heavy and "
            "not a single published figure; ~$40B is the modeled composite. "
            "Medicare alone paid ASCs ~$5.6B in 2022 across ~6,300 certified "
            "centers (MedPAC) — see segments. Growth is the modeled composite "
            "of case-migration, rate updates, and higher-acuity mix."),
    ),
    executive_summary=[
        "The thesis is site-of-service migration: the same case costs 40-60% "
        "less in an ASC than in the HOPD, so CMS, commercial payers, and "
        "surgeons all want it there. The ASC payment rate is a deliberate "
        "discount to HOPD, and CMS keeps adding codes (total knee 2020, total "
        "hip 2021, cardiac) to the ASC Covered Procedures List.",
        "Physician ownership IS the model. Most ASCs are physician-owned or "
        "three-way JVs (physicians + a health system + a manager). The surgeon "
        "is both the referral source and the owner — powerful alignment that "
        "puts the whole structure under Stark/AKS and the ASC safe harbor.",
        "Value = case mix × payer mix × volume per OR. A high-throughput GI or "
        "cataract center and a total-joint ortho center are utterly different "
        "assets — implant cost, acuity, and commercial rates drive the spread, "
        "and empty OR block time is unrecoverable.",
        "Fragmentation is extreme below three national managers — USPI "
        "(Tenet), SCA (Optum/UnitedHealth), and AmSurg. ~6,300 Medicare-"
        "certified ASCs; the acquirable pool is thousands of independent "
        "single- and multi-specialty centers.",
        "The regulatory frame is specific: Certificate-of-Need laws gate new "
        "centers in roughly half the states, the ASC Covered Procedures List "
        "expands the addressable case set each year, and the site-neutral "
        "(HOPD vs ASC vs office) debate could widen or compress the arbitrage.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Surgeon office diagnosis → decision to operate (elective case)",
            "Case scheduled into an ASC OR/procedure-room block",
            "Pre-op clearance + anesthesia assessment",
            "Procedure performed (surgeon + anesthesia + OR team)",
            "Post-anesthesia recovery (PACU) → same-day discharge",
            "Facility claim (ASC payment system) submitted by the center",
            "Separate professional (surgeon MPFS) + anesthesia claims; "
            "implants/devices billed per the packaging rules",
            "ASC Quality Reporting (ASCQR) submission gates the annual update",
        ],
        sites_of_care=[
            "Single-specialty ASC (GI endoscopy, ophthalmology, pain, ortho)",
            "Multispecialty ASC (the platform asset — mixed OR block)",
            "Hospital-JV ASC (system + physicians + manager)",
            "Office-based lab / procedure suite (a competing, lower-acuity site)",
            "Hospital outpatient department (HOPD) — the site cases migrate FROM",
        ],
        money_flow=(
            "The ASC bills a packaged FACILITY fee under the Medicare ASC "
            "payment system — an APC-based relative weight scaled by the ASC "
            "conversion factor, set as a discount to the HOPD/OPPS rate for the "
            "same code (the ASC typically pays roughly half to two-thirds of "
            "HOPD). The surgeon bills a separate professional fee on the "
            "Medicare Physician Fee Schedule, and anesthesia bills separately "
            "(ASA base + time units). Commercial payers pay a case rate or "
            "percent-of-charges that is a large multiple of Medicare — that is "
            "where the margin lives. Device-intensive procedures carry separate "
            "device payment so implant-heavy cases aren't underwater. The "
            "economic engine is filling OR blocks with well-reimbursed "
            "commercial cases against a largely fixed OR cost base."),
        key_players=(
            "Three national managers dominate the managed segment: United "
            "Surgical Partners International (USPI, Tenet) — the largest "
            "platform, Surgical Care Affiliates (SCA, now Optum/UnitedHealth), "
            "and AmSurg (GI-heavy, part of the former Envision). Regional and "
            "specialty managers include Regent Surgical Health, Nueterra "
            "Capital, Compass Surgical Partners, and Physicians Endoscopy. But "
            "the majority of centers are independent physician-owned or "
            "hospital-JV. Device/implant vendors (Stryker, Zimmer Biomet) and "
            "anesthesia groups sit adjacent to the model."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Medicare ASC facility payments (2022)", "~$5.60B",
                    "GOV · MedPAC ASC services chapter"),
            Segment("Medicare-certified ASCs", "~6,300 centers",
                    "GOV · MedPAC / CMS certification counts"),
            Segment("Commercial / all-payer share of ASC revenue",
                    "the majority — the margin engine",
                    "ILLUSTRATIVE · modeled payer mix (commercial-heavy)"),
            Segment("GI/endoscopy + ophthalmology (cataract)",
                    "the two highest-volume single specialties",
                    "ILLUSTRATIVE · industry case-mix, directional"),
            Segment("Total-joint / ortho / spine",
                    "the fastest-growing, highest-acuity migration",
                    "ILLUSTRATIVE · ASC-CPL additions (GOV) + industry mix"),
        ],
        growth_drivers=[
            "Site-of-service migration HOPD→ASC — the primary lever",
            "ASC Covered Procedures List expansion (total joints, cardiac)",
            "Aging population lifts elective volume (cataract, ortho, GI)",
            "Commercial payer steerage to the low-cost ASC site",
            "CON constraints and site-neutral policy as the offsets",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Commercial": 0.48,
            "Medicare / MA": 0.37,
            "Medicaid / self-pay / other": 0.15,
        },
        rate_mechanics=[
            "Medicare ASC Payment System — a packaged facility rate per primary "
            "procedure (APC relative weight × ASC conversion factor), set as a "
            "deliberate discount to the HOPD/OPPS rate for the same code.",
            "ASC Covered Procedures List (CPL) — CMS defines which procedures "
            "Medicare pays in an ASC; annual additions (total knee 2020, total "
            "hip 2021, many cardiac codes) expand the addressable case set.",
            "Multiple-procedure discounting — secondary procedures on the same "
            "date pay at ~50% of their rate.",
            "Device-intensive procedures — separate/offset device payment so "
            "implant-heavy ortho and cardiac cases are not underwater.",
            "Commercial case rates / percent-of-charge — the margin engine; "
            "in-network negotiation, site-of-service steerage, and (post-NSA) "
            "curtailed out-of-network billing.",
            "ASC Quality Reporting (ASCQR) — pay-for-reporting; failure to "
            "report cuts the annual payment update.",
            "Anesthesia and surgeon professional fees bill separately — they "
            "are NOT inside the packaged facility rate.",
        ],
        reimbursement_risk=(
            "The core risk is the HOPD-to-ASC rate differential and how CMS "
            "updates it: the ASC update factor has swung between the hospital "
            "market basket and the lower CPI-U, and any drift toward site-"
            "neutral payment — equalizing HOPD, ASC, and office rates — could "
            "compress the facility-fee premium the whole migration thesis is "
            "priced on. Commercial rate durability is the bigger swing: payers "
            "steer volume to ASCs but also cut rates, impose prior "
            "authorization, and (under the No Surprises Act) have curtailed the "
            "out-of-network billing some centers relied on. Finally, implant "
            "and device cost inflation on fixed case rates squeezes ortho and "
            "spine centers, where the device can approach half the case's net "
            "revenue."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("Medicare ASC Conditions for Coverage (42 CFR 416)",
                 "The licensure/survey-and-certification regime; infection-"
                 "control and governance deficiencies can decertify a center.",
                 "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-416"),
            Rule("Hospital OPPS / ASC Payment System (annual Final Rule)",
                 "Sets ASC rates, the conversion factor, and the ASC Covered "
                 "Procedures List — the prices and the addressable case set.",
                 "https://www.cms.gov/medicare/payment/prospective-payment-systems/ambulatory-surgical-center-asc"),
            Rule("Anti-Kickback safe harbor for ASC investments "
                 "(42 CFR 1001.952(r))",
                 "The physician-investment safe harbor (one-third practice-"
                 "income and one-third procedures tests) is what keeps the "
                 "own-and-refer alignment legal — the model rides on it.",
                 "https://oig.hhs.gov/compliance/safe-harbor-regulations/"),
            Rule("Physician self-referral law (Stark, 42 CFR 411.350+)",
                 "Governs surgeon referrals to entities they own; ASC "
                 "ownership and ancillary arrangements must fit an exception.",
                 "https://www.cms.gov/medicare/regulations-guidance/physician-self-referral"),
            Rule("Certificate of Need (CON) laws (state)",
                 "~35 states regulate new ASC/OR capacity — a binding de novo "
                 "constraint and a moat for incumbents in CON states.",
                 None),
            Rule("No Surprises Act (out-of-network protections)",
                 "Limits balance billing and OON payment at ASCs, compressing "
                 "the out-of-network strategy some centers used.",
                 "https://www.cms.gov/nosurprises"),
        ],
        policy_watch=[
            "Site-neutral payment reform (HOPD vs ASC vs office) — the central "
            "swing factor for the arbitrage",
            "Annual ASC Covered Procedures List additions (more cardiac, ortho)",
            "CON repeal / relaxation momentum in several states",
            "ASC update factor — market-basket vs CPI-U alignment",
            "Enforcement on physician-ownership safe-harbor compliance",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Roughly 6,300 Medicare-certified ASCs, overwhelmingly independent "
            "physician-owned or hospital-JV; three national managers run a "
            "minority — but rapidly growing — share. Below the top three the "
            "market is extremely fragmented, and that independent single- and "
            "multi-specialty long tail is the acquirable pool."),
        hhi_or_share=(
            "No dominant national owner. USPI (Tenet), SCA (Optum), and AmSurg "
            "lead the managed segment, but most centers are independent. The "
            "CMS ASC file carries no operator/chain field, so a chain HHI is "
            "honestly omitted — fragmentation is the structure."),
        consolidation=(
            "Rapid roll-up over the last decade: Tenet built USPI into the "
            "largest platform, UnitedHealth's Optum acquired SCA and folded the "
            "ASC into vertically-integrated care, and the hospital-JV model "
            "(system + physicians + manager) proliferated as systems chase "
            "outpatient migration. Multispecialty and total-joint-capable "
            "centers command premium multiples."),
        pe_activity=(
            "Highly active, but the marquee acquirers are strategics "
            "(Tenet/USPI, Optum/SCA). PE plays it mostly through specialty "
            "physician platforms — GI, orthopedics, ophthalmology, pain — that "
            "own or JV ASCs as the ancillary profit center. Inside a physician-"
            "platform deal the ASC is often the crown jewel: the facility fee "
            "is margin captured on top of the professional fee the surgeon "
            "earns anyway."),
        notable_players=[
            "USPI (Tenet)", "Surgical Care Affiliates (Optum)",
            "AmSurg", "Regent Surgical Health", "Nueterra Capital",
            "Compass Surgical Partners", "Physicians Endoscopy",
            "Health-system ASC joint ventures",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Cases / OR / day", "6-12",
                "GI and cataract run high-throughput; ortho/spine far fewer. "
                "OR utilization is the whole fixed-cost story."),
            Kpi("Net revenue / case (blended)", "$1,500-4,000+",
                "Wildly specialty-dependent — endoscopy low, total joint high; "
                "the blend follows case and payer mix."),
            Kpi("Commercial case mix", "40-60% of cases",
                "The single biggest value driver — commercial pays a multiple "
                "of the Medicare facility rate."),
            Kpi("Implant/supply cost (% of net revenue)", "15-40%",
                "Low for GI, very high for ortho/spine, where the device can "
                "approach half the case's net revenue."),
            Kpi("OR / block utilization", ">70% target",
                "Empty block time is unrecoverable fixed cost — the core "
                "efficiency lever."),
            Kpi("ASC EBITDA margin (mature)", "25-35%+",
                "High operating leverage on the OR chassis when well-utilized "
                "and commercial-rich."),
        ],
        margin_profile=(
            "An ASC is a high-fixed-cost OR chassis — the ORs, sterile-"
            "processing, nursing/tech staff, and the anesthesia arrangement are "
            "largely fixed, so contribution margin steps up sharply with each "
            "additional case and, above all, with each commercial case. A "
            "mature, well-utilized multispecialty center with a healthy "
            "commercial book and controlled implant cost runs high-20s to "
            "mid-30s EBITDA margin; a Medicare-heavy or under-booked center on "
            "the same cost base is far thinner. Implant-intensive specialties "
            "(ortho, spine) carry device cost that can swamp the facility fee "
            "if case rates aren't negotiated to cover it."),
    ),
    risks=[
        Risk("Site-neutral payment reform", "High",
             "Equalizing HOPD/ASC/office rates would reprice the migration "
             "thesis and compress the facility-fee premium."),
        Risk("Commercial rate compression + payer site-of-service policy",
             "High",
             "Payers steer volume but also cut rates and impose prior auth; "
             "the No Surprises Act curtailed the out-of-network strategy."),
        Risk("Physician-ownership Stark/AKS safe-harbor exposure", "High",
             "The ownership model depends on safe-harbor compliance; a "
             "misstructured JV is an existential legal risk, not a discount."),
        Risk("Implant / device cost inflation on fixed case rates", "Medium",
             "Squeezes ortho and spine margins where the device is a large "
             "share of net revenue."),
        Risk("Surgeon concentration / retirement / defection", "Medium",
             "A few surgeons often drive most volume and are both the referral "
             "source and the owner — losing one hits volume and equity."),
        Risk("Anesthesia and clinical-labor supply/cost", "Medium",
             "CRNA/anesthesiologist coverage and OR nurse staffing gate how "
             "many blocks can actually run."),
        Risk("CON / de novo capacity constraints", "Low",
             "A growth ceiling in CON states — but also a moat that protects "
             "incumbent centers."),
    ],
    diligence_questions=[
        "What is the case mix by specialty and CPT, and how concentrated is "
        "volume in the top 3-5 surgeons (key-man risk)?",
        "What is the payer mix by case, and how do commercial contract rates "
        "compare to Medicare — how durable are those contracts?",
        "How is the ownership/JV structured against the ASC safe harbor "
        "(one-third income / one-third procedures), and is every investor "
        "compliant?",
        "What is OR/block utilization and its trend — how much unbooked "
        "capacity exists, and could added surgeons fill it?",
        "For implant-heavy specialties, what is device cost as a % of net "
        "revenue, and how are case rates structured to cover implants?",
        "Which ASC-CPL additions (total joints, cardiac) is the center "
        "adding, and what capex/credentialing does that require?",
        "Is the center in a CON state, and what is the local HOPD and office "
        "competitive landscape?",
        "What is the anesthesia arrangement (employed, exclusive contract, "
        "company model) and its economics and compliance posture?",
    ],
    insider_lens=[
        "The facility fee is the prize. In a physician-platform deal the ASC "
        "is usually the highest-margin asset — the surgeon earns a "
        "professional fee either way, but owning the facility captures the "
        "packaged facility payment on top. That is why platforms fight to move "
        "cases into an owned center.",
        "Two or three surgeons usually ARE the center. ASC value concentrates "
        "in a handful of high-volume owners — underwrite their age, retirement "
        "horizon, non-competes, and satisfaction before you trust the P&L.",
        "Ortho and spine look lucrative but the implant eats the case. A "
        "total-joint ASC lives or dies on device pricing and case-rate "
        "structure — a big facility fee with a $6-8k implant can be thinner "
        "than a boring, supply-light GI center.",
        "The whole ownership model is a regulatory construct. The physician-"
        "investment safe harbor (one-third practice income, one-third "
        "procedures) is what keeps own-and-refer legal — a JV that drifts out "
        "of compliance is a landmine, not a bargain.",
        "Site-of-service cuts both ways. CMS and payers moving cases out of "
        "the HOPD is the tailwind; CMS moving toward site-neutral — paying the "
        "ASC like an office, or the HOPD like an ASC — is the tail risk that "
        "reprices everything.",
    ],
    connections=default_connections(
        "asc",
        deals_sector="asc",
        extra_pages=[
            ("/industry/asc",
             "Industry deep-dive — ASC deal history + structure"),
        ],
        connectors=[
            ("provider_data_asc_quality_facility",
             "CMS ASC Quality Reporting (ASCQR) — certified centers by facility"),
            ("provider_data_oas_cahps_asc_facility",
             "OAS CAHPS — ASC patient-experience by facility"),
            ("open_payments_ownership_payments_2024",
             "Open Payments — physician ownership & investment interests "
             "(JV/safe-harbor screen)"),
            ("cms_open_data_mup_outpatient_by_provider_service",
             "Medicare outpatient utilization by procedure — HOPD/ASC "
             "migration read"),
            ("npi_provider_taxonomy",
             "NPI taxonomy — surgeon specialty & ASC enrollment"),
        ],
    ),
    sources=[
        Source("MedPAC — Report to Congress, ambulatory surgical center "
               "services chapter", "GOV", "https://www.medpac.gov/"),
        Source("CMS — Hospital OPPS / ASC Payment System annual Final Rule "
               "(rates + Covered Procedures List)", "GOV",
               "https://www.cms.gov/medicare/payment/prospective-payment-systems/ambulatory-surgical-center-asc"),
        Source("Medicare ASC Conditions for Coverage (42 CFR 416)", "GOV",
               "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-416"),
        Source("OIG — Anti-Kickback safe harbor for ASC investments "
               "(42 CFR 1001.952(r))", "GOV",
               "https://oig.hhs.gov/compliance/safe-harbor-regulations/"),
        Source("Ambulatory Surgery Center Association (ASCA) — industry data "
               "and outcomes", "INDUSTRY", "https://www.ascassociation.org/"),
        Source("No Surprises Act — CMS out-of-network billing protections",
               "GOV", "https://www.cms.gov/nosurprises"),
        Source("PE Desk industry deep-dive (ASC) + realized-deal corpus",
               "INTERNAL", "/diligence/tam-sam?template=asc"),
    ],
    live_figures=live_figures_from_dive("asc"),
    trends=(
        "The ASC story of the last decade is site-of-service migration, and it "
        "accelerated on three fronts. CMS added blockbuster codes to the ASC "
        "Covered Procedures List — total knee in 2020, total hip in 2021, and "
        "dozens of cardiac codes — pulling higher-acuity work into the "
        "ambulatory setting. Commercial payers built site-of-service steerage "
        "policies that push elective cases out of the more expensive HOPD. And "
        "the strategics consolidated: Tenet scaled USPI into the largest "
        "platform while UnitedHealth's Optum absorbed SCA, folding the ASC into "
        "vertically-integrated care. The COVID elective-surgery shutdown was a "
        "sharp but temporary shock; volume rebounded and reinforced the "
        "ambulatory shift. The forward tension is policy — CMS's on-again/off-"
        "again alignment of the ASC update factor with the hospital market "
        "basket, and the broader site-neutral debate, will decide whether the "
        "HOPD-to-ASC arbitrage widens or compresses. Underneath, the "
        "addressable case set keeps expanding into ortho, spine, and cardiac "
        "work — lifting both revenue per case and the implant cost that "
        "travels with it."),
    growth_levers=[
        GrowthLever(
            "Site-of-service migration (HOPD → ASC)",
            "The same case is 40-60% cheaper in an ASC, so CMS pays a discount "
            "to HOPD and payers steer volume — the primary engine of ASC "
            "growth.",
            "primary", "ILLUSTRATIVE"),
        GrowthLever(
            "ASC Covered Procedures List expansion",
            "CMS keeps adding codes Medicare will pay in an ASC (total joints, "
            "cardiac), widening the addressable case set each year.",
            "+ case set", "GOV"),
        GrowthLever(
            "Aging-driven elective volume",
            "Cataracts, joint replacement, GI screening, and pain procedures "
            "rise with the 65+ population.",
            "+~2%/yr volume", "ILLUSTRATIVE"),
        GrowthLever(
            "Annual ASC rate update",
            "The packaged facility rate steps up with the annual Final Rule "
            "and the conversion factor.",
            "+ low-single %/yr", "ILLUSTRATIVE"),
        GrowthLever(
            "Site-neutral / rate-alignment drag",
            "CMS moving the ASC update to CPI-U, or equalizing site-of-service "
            "payment, would compress the facility-fee premium.",
            "policy risk", "GOV"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Elective surgical volume × the HOPD→ASC migration rate",
        analysis=(
            "The dominant demand driver is the pool of elective, ambulatory-"
            "appropriate surgical cases and how fast they migrate from the "
            "hospital outpatient department into the ASC. Two forces compound: "
            "an aging population lifts the underlying rate of cataracts, joint "
            "replacements, GI screening/endoscopy, and pain procedures; and a "
            "deliberate site-of-service shift — engineered by CMS (expanding "
            "the ASC Covered Procedures List and paying the ASC a discount to "
            "the HOPD) and by commercial payers (steerage and prior auth "
            "favoring the low-cost site) — moves a rising share of those cases "
            "into ASCs. The addressable set keeps widening as higher-acuity "
            "total-joint, spine, and cardiac cases become ambulatory-safe. The "
            "offset is capacity and policy: CON laws cap new ORs in many "
            "states, and any move toward site-neutral payment blunts the "
            "financial incentive that powers the migration."),
        basis="GOV"),
    cost_drivers=[
        CostDriver(
            "Clinical labor (OR/PACU nurses, surgical techs, sterile "
            "processing)", "~25-35% of cost",
            "The largest fixed operating cost; staffing determines how many "
            "ORs can run and gates de novo growth.", "ILLUSTRATIVE"),
        CostDriver(
            "Implants, devices & medical supplies", "~15-40% of cost",
            "Hugely specialty-dependent — ortho/spine implants can approach "
            "half of case net revenue; GI/ophthalmology are supply-light.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Anesthesia arrangement", "variable / carve-out",
            "CRNA/anesthesiologist coverage is often a separate company or "
            "exclusive contract; its economics and any subsidy affect "
            "throughput.", "ILLUSTRATIVE"),
        CostDriver(
            "Facility & equipment (OR build-out, sterilization, real estate)",
            "~10-15% of cost",
            "The fixed chassis — de novo and expansion capex plus CON gate "
            "capacity.", "ILLUSTRATIVE"),
        CostDriver(
            "G&A, billing & compliance (safe-harbor, ASCQR, accreditation)",
            "~8-12% of cost",
            "Corporate overhead plus the ownership-compliance and quality-"
            "reporting apparatus the model requires.", "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "No national all-payer ASC facility file is vendored, so state "
        "geography is omitted rather than fabricated. Qualitatively, ASC "
        "density tracks two things. First, Certificate-of-Need regimes: CON "
        "states (New York and much of the Southeast/Mid-Atlantic) cap new "
        "centers and concentrate ownership, while non-CON states — Texas, "
        "California, Arizona, Colorado — saw far denser de novo build-out. "
        "Second, surgeon supply and commercial-payer density. The CMS ASC "
        "Quality (ASCQR) connector linked below carries certified centers by "
        "state for a real footprint read."),
)

register(REPORT)
