"""LTC Pharmacy — closed-door institutional pharmacy for long-term care.

Deals-only vertical (no public closed-door-pharmacy census), authored off the
hospice copy-template. The report is organized around the truth an operator
lives by: LTC pharmacy is a route-density logistics business wearing a pharmacy
license, squeezed from both sides — the facility negotiates the Part A drug cost
down, and Part D DIR claws back the rest — with the customer's own solvency as
the pharmacy's credit risk.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver, default_connections,
    live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="ltc_pharmacy",
    name="LTC Pharmacy",
    care_setting="Pharmacy & infusion",
    naics="446110",
    one_line_def=(
        "Closed-door institutional pharmacy serving long-term care facilities — "
        "skilled nursing, assisted living, group homes, and hospice — with "
        "unit-dose / blister-pack cycle fills, med carts and eMAR integration, "
        "emergency kits, STAT delivery, and the federally-mandated consultant-"
        "pharmacist drug-regimen review."),
    tam_headline=TamHeadline(
        value=25.0, unit="$B", growth_pct=3.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "US institutional / LTC pharmacy revenue, modeled at ~$25B off the "
            "SNF + assisted-living bed base times per-resident drug spend "
            "(there is no single CMS LTC-pharmacy line). Growth is bed-count "
            "constrained — occupancy and the resident base, not price, cap it."),
    ),
    executive_summary=[
        "It is a route-density logistics business wearing a pharmacy license. "
        "Margin is won on delivery-route density, generic dispensing rate, and "
        "cycle-fill efficiency — not on clinical differentiation.",
        "The customer is the facility, and the facility's solvency is the "
        "pharmacy's credit risk. SNF bankruptcies and slow-pay are the quiet "
        "killer; post-COVID occupancy is the volume risk on the bed base.",
        "The pharmacy is squeezed from both sides. For skilled (Part A) days "
        "the drug is bundled into the SNF's PDPM per-diem, so the facility "
        "negotiates the price down; for long-stay days the drug bills Part D, "
        "where DIR fees claw back reimbursement after the fact.",
        "The consultant-pharmacist drug-regimen review (OBRA '87) is both a "
        "regulatory moat and a cost — mandated monthly, hard to staff, and the "
        "compliance backbone that keeps the facility contract.",
        "Omnicare's decline reshaped the map; PharMerica (BrightSpring) and "
        "Guardian consolidate the regional tail, but the tail persists because "
        "local route density and facility relationships are sticky and local.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Facility contract — the pharmacy of record for a SNF / ALF / home",
            "Admission — resident medication profile + physician orders",
            "Adjudication — Part A (facility-billed) vs. Part D / Medicaid",
            "Dispensing — unit-dose / blister-pack cycle fill (short-cycle)",
            "Delivery — routed courier, STAT / emergency-kit backup",
            "eMAR / med-cart integration at the facility",
            "Consultant-pharmacist monthly drug-regimen review (mandated)",
            "Billing + collections from the facility, plan, and Medicaid",
        ],
        sites_of_care=[
            "Skilled nursing facilities (SNFs — the core customer)",
            "Assisted living + memory care communities",
            "Group homes / ICF-IID and IDD residential",
            "Hospice and correctional (secondary closed-door segments)",
        ],
        money_flow=(
            "Payment splits by the resident's coverage on a given day. On "
            "skilled (Part A) days, drugs are bundled into the SNF's PDPM "
            "per-diem — the pharmacy bills the facility, not Medicare, so the "
            "facility squeezes the drug cost as its own expense. On long-stay "
            "(custodial) days, prescriptions bill the resident's Medicare Part D "
            "plan under LTC network rules, subject to short-cycle dispensing "
            "(≤14-day fills on brand drugs to cut waste) and to DIR fees that "
            "claw back reimbursement after adjudication. Dual-eligible and "
            "Medicaid residents add a third billing path. The consultant-"
            "pharmacist drug-regimen review is typically a contracted facility "
            "fee or bundled into the arrangement. Net, the pharmacy earns a thin "
            "dispensing margin driven by its generic dispensing rate and its "
            "delivery-route density."),
        key_players=(
            "Two national scale players plus a long regional tail. PharMerica, "
            "under BrightSpring Health Services (KKR-backed, IPO'd 2024), is the "
            "leading national closed-door operator; Guardian Pharmacy Services "
            "(a franchise-style roll-up, public since 2024) is the fast-growing "
            "consolidator of the regional tail. Omnicare (CVS Health) was the "
            "historical giant and has receded. Beneath them, hundreds of "
            "regional and independent closed-door pharmacies compete on local "
            "route density and facility relationships — the acquirable pool."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Skilled nursing (SNF) resident base",
                    "~1.2M certified beds",
                    "GOV · CMS Nursing Home Care Compare bed counts"),
            Segment("Assisted living + memory care beds",
                    "~900K-1M residences (est.)",
                    "ILLUSTRATIVE · industry residence estimates"),
            Segment("Part A bundled (skilled-day) drug spend",
                    "facility-borne per-diem cost",
                    "GOV · CMS SNF PDPM structure"),
            Segment("Part D long-stay drug spend",
                    "plan-billed, DIR-exposed",
                    "GOV · CMS Part D LTC dispensing rules"),
        ],
        growth_drivers=[
            "65+ / 85+ population growth lifting the LTC resident base ~+2%/yr",
            "Post-COVID SNF occupancy recovery (a swing on the bed base)",
            "Assisted-living and memory-care bed growth (softer LTC-pharmacy fit)",
            "Drug mix / new therapies raising per-resident cost",
            "Generic dispensing-rate gains (efficiency, not revenue)",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Medicare Part D (long-stay)": 0.45,
            "Medicaid (custodial / dual-eligible)": 0.30,
            "Facility-billed Part A (bundled) + private": 0.25,
        },
        rate_mechanics=[
            "SNF Part A bundling (PDPM) — on skilled days the drug is inside the "
            "SNF per-diem; the pharmacy bills the facility, which manages it as "
            "a cost and negotiates price down.",
            "Part D LTC dispensing — long-stay scripts bill the resident's Part "
            "D plan through LTC network contracts, benchmarked to WAC/AWP/NADAC "
            "plus a dispensing fee.",
            "Short-cycle dispensing rule — ≤14-day fills for brand drugs in LTC "
            "to reduce waste, raising dispensing labor per script.",
            "DIR fees (Part D) — retroactive clawbacks that compress the "
            "already-thin LTC dispensing margin.",
            "Medicaid — custodial and dual-eligible residents add a state "
            "reimbursement path (room-and-board is Medicaid; drugs run Part D "
            "for duals).",
            "Consultant-pharmacist services — the mandated drug-regimen review "
            "is a contracted facility fee or bundled into the arrangement.",
        ],
        reimbursement_risk=(
            "The pharmacy is compressed from both directions and carries the "
            "customer's credit risk. On skilled days the facility owns the drug "
            "cost inside its PDPM per-diem and pushes price down; on long-stay "
            "days Part D DIR fees claw back the dispensing margin. Generic "
            "dispensing rate is the main lever the pharmacy actually controls. "
            "Overlaying all of it, the facility itself is the payer of first "
            "resort on Part A and private billing — so SNF financial distress "
            "and occupancy declines translate directly into bad debt and lost "
            "volume. The result is a low-margin business where operating "
            "discipline (route density, GDR, collections) separates winners "
            "from losers far more than pricing does."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("OBRA '87 consultant-pharmacist review (42 CFR 483.45)",
                 "Mandates monthly drug-regimen review, gradual dose reduction, "
                 "and antipsychotic reduction in SNFs — the compliance backbone "
                 "and a required service line.",
                 "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-C/part-483"),
            Rule("CMS short-cycle dispensing rule (Part D LTC)",
                 "Requires ≤14-day brand fills in LTC to cut waste — raises "
                 "dispensing labor per script and reshapes cycle economics.",
                 "https://www.cms.gov/medicare/payment/prescription-drug-coverage"),
            Rule("SNF PDPM (Part A bundling of drugs)",
                 "Folds skilled-day drug cost into the SNF per-diem, making the "
                 "facility the price-setter for Part A pharmacy.",
                 "https://www.cms.gov/medicare/payment/prospective-payment-systems/skilled-nursing-facility-snf"),
            Rule("Part D DIR fee reform (2024)",
                 "Moves DIR to point of sale; changes LTC pharmacy cash-flow "
                 "timing and margin visibility.",
                 "https://www.cms.gov/medicare/payment/prescription-drug-coverage"),
            Rule("State board closed-door pharmacy licensure + DEA",
                 "Closed-door licensing, controlled-substance handling, and "
                 "emergency-kit (e-kit) rules govern operations.",
                 None),
            Rule("USP <797> / <800> for LTC IV + hazardous drugs",
                 "Sterile and hazardous-drug standards for any admixture or "
                 "specialty compounding the LTC pharmacy performs.",
                 "https://www.usp.org/compounding"),
        ],
        policy_watch=[
            "SNF minimum-staffing rule effects on facility solvency + census",
            "DIR reform cash-flow effects working through LTC pharmacy",
            "Medicaid rate pressure on custodial / dual-eligible residents",
            "SNF ownership consolidation reshaping pharmacy contracting leverage",
            "Any revisit of short-cycle dispensing / LTC Part D rules",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "A two-tier structure: two national scale players (PharMerica/"
            "BrightSpring and Guardian) over a long tail of regional and "
            "independent closed-door pharmacies. The tail persists because the "
            "unit of competition is local route density and facility "
            "relationships, which don't consolidate away easily — exactly the "
            "acquirable roll-up pool."),
        hhi_or_share=(
            "Moderately concentrated at the top (PharMerica/BrightSpring and "
            "Guardian lead) with a large fragmented regional tail; no vendored "
            "closed-door-pharmacy census exists to compute a defensible "
            "national HHI, so a figure is omitted."),
        consolidation=(
            "Omnicare (CVS) and PharMerica were the historical duopoly; "
            "Omnicare's retreat left BrightSpring (KKR) and the Guardian "
            "franchise/roll-up as the consolidators of regional independents. "
            "The playbook is classic buy-and-build: tuck in local closed-door "
            "pharmacies, densify delivery routes, and lift the generic "
            "dispensing rate."),
        pe_activity=(
            "The defining PE story is BrightSpring/PharMerica under KKR (2024 "
            "IPO), with Guardian as the other public consolidator. Sponsor "
            "diligence centers on facility credit quality and concentration, "
            "route density, GDR, and DIR exposure rather than on clinical "
            "differentiation."),
        notable_players=[
            "PharMerica (BrightSpring Health Services)",
            "Guardian Pharmacy Services", "Omnicare (CVS Health)",
            "Remedi SeniorCare", "Pharmscript", "Skilled Nursing Pharmacy (regional)",
            "Regional / independent closed-door pharmacies",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Revenue / bed / month", "$300-600 (illustrative)",
                "The core throughput metric; varies with acuity, drug mix, and "
                "Part A vs. long-stay day mix."),
            Kpi("Generic dispensing rate (GDR)", "85-92%",
                "The single biggest controllable margin lever — higher GDR "
                "means more of the thin spread is captured."),
            Kpi("Beds under contract", "the volume base",
                "Contracted SNF/ALF beds drive route density; the asset is the "
                "book of facility relationships."),
            Kpi("Delivery cost / script (route density)", "logistics-driven",
                "A distribution-economics metric — dense routes spread the "
                "courier and cycle-fill cost across more scripts."),
            Kpi("Facility bad-debt / DSO", "credit-quality metric",
                "Slow-pay and SNF distress drive receivables risk — the quiet "
                "killer of LTC-pharmacy returns."),
            Kpi("LTC-pharmacy EBITDA margin (illustrative)", "6-12%",
                "A thin-margin logistics business; scale, GDR, and route "
                "density set where in the band an operator lands."),
        ],
        margin_profile=(
            "LTC pharmacy is a low-margin, high-throughput distribution business. "
            "Gross margin is a thin dispensing spread — maximized by generic "
            "dispensing rate — against a cost base dominated by pharmacist and "
            "delivery labor. Because the drug is bundled on Part A and DIR-clawed "
            "on Part D, pricing power is limited; profitability is manufactured "
            "operationally through route density, cycle-fill efficiency, and "
            "disciplined collections. Scale helps on purchasing and on spreading "
            "the consultant-pharmacist and technology base, but returns live and "
            "die on execution and on the credit quality of the facility book."),
    ),
    risks=[
        Risk("Facility credit risk + concentration", "High",
             "SNF bankruptcies and slow-pay leave the pharmacy unpaid; "
             "concentration in a distressed operator is a direct hit."),
        Risk("SNF occupancy / census decline", "Medium",
             "Post-COVID occupancy softness shrinks the bed base the pharmacy "
             "depends on for volume."),
        Risk("Part A bundling + facility price squeeze", "Medium",
             "Facilities push skilled-day drug cost down as their own PDPM "
             "expense, compressing the pharmacy."),
        Risk("Part D DIR / reimbursement compression", "High",
             "Retroactive clawbacks erode the already-thin long-stay dispensing "
             "margin."),
        Risk("Pharmacist + delivery labor / fuel", "Medium",
             "Pharmacist shortages and courier/fuel costs pressure a labor- and "
             "logistics-intensive model."),
        Risk("SNF customer consolidation", "Medium",
             "Chains that self-contract or negotiate as a bloc erode pricing "
             "and increase concentration."),
    ],
    diligence_questions=[
        "What is the facility customer concentration, and what is the credit "
        "quality / payment history of the top facility accounts?",
        "What is the generic dispensing rate, and what is the trend versus "
        "peers?",
        "What is the Part A (bundled) versus long-stay (Part D) day mix, and "
        "how price-squeezed is the Part A book?",
        "What is DSO and bad-debt experience, and how exposed is the book to "
        "any distressed SNF operators?",
        "What is route density and delivery cost per script across the "
        "service territory?",
        "What is DIR-fee exposure, and how has the 2024 reform changed realized "
        "margin and cash flow?",
        "How is the consultant-pharmacist / drug-regimen-review obligation "
        "staffed and priced, and is it compliant?",
    ],
    insider_lens=[
        "It's logistics wearing a pharmacy license. Margin is won on delivery-"
        "route density, generic dispensing rate, and cycle-fill efficiency — "
        "not on clinical services. Underwrite the operations, not the "
        "formulary.",
        "The facility is your customer and your credit risk at once. SNF "
        "bankruptcies and slow-pay quietly destroy LTC-pharmacy returns; "
        "concentration in one shaky operator can be worse than any rate cut.",
        "You're squeezed from both sides. Part A drugs are the facility's cost "
        "(bundled in PDPM) and it negotiates you down; Part D drugs are the "
        "plan's and DIR claws back the rest. GDR is about the only lever you "
        "fully control.",
        "Bed census is the whole volume story. Post-COVID occupancy softness on "
        "the SNF base is a bigger swing than any single contract — the resident "
        "count caps the market.",
        "The consultant-pharmacist review is a moat and a cost. OBRA-mandated "
        "monthly drug-regimen review is hard to staff and keeps the facility "
        "contract sticky — but it's a service you must fund whether or not it's "
        "separately paid.",
    ],
    connections=default_connections(
        "ltc_pharmacy",
        deals_sector="ltc_pharmacy",
        connectors=[
            ("provider_data_nursing_home_provider_info",
             "CMS Nursing Home Care Compare — the SNF customer base, ownership, "
             "and certified beds (concentration + credit read)"),
            ("cms_open_data_ltc_facility_characteristics",
             "CMS LTC facility characteristics — resident-base and facility "
             "profile"),
            ("cms_open_data_pbj_daily_nurse_staffing",
             "CMS PBJ daily staffing — SNF census / occupancy proxy for the "
             "bed base"),
            ("cms_open_data_mup_partd_prescriber_by_geo_drug",
             "CMS Part D prescriber-by-geography — LTC drug-volume and geographic "
             "prescribing"),
            ("npi_provider_taxonomy",
             "NPI taxonomy — closed-door / LTC pharmacy enrollment"),
            ("oig_leie_exclusions",
             "OIG LEIE — excluded individuals/entities (integrity screen)"),
        ],
    ),
    sources=[
        Source("CMS Nursing Home Care Compare — SNF provider info and certified "
               "bed counts", "GOV",
               "https://data.cms.gov/provider-data/"),
        Source("CMS SNF Prospective Payment System (PDPM) — Part A drug "
               "bundling structure", "GOV",
               "https://www.cms.gov/medicare/payment/prospective-payment-systems/skilled-nursing-facility-snf"),
        Source("Requirements for Long-Term Care Facilities — consultant "
               "pharmacist (42 CFR 483.45)", "GOV",
               "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-C/part-483"),
        Source("CMS Medicare Part D — LTC dispensing, short-cycle rule, and "
               "DIR reform", "GOV",
               "https://www.cms.gov/medicare/payment/prescription-drug-coverage"),
        Source("American Society of Consultant Pharmacists (ASCP) — LTC "
               "pharmacy practice standards", "INDUSTRY",
               "https://www.ascp.com/"),
        Source("PE Desk industry deep-dive (LTC pharmacy) + realized-deal "
               "corpus", "INTERNAL",
               "/diligence/tam-sam?template=ltc_pharmacy"),
    ],
    live_figures=live_figures_from_dive("ltc_pharmacy"),
    trends=(
        "LTC pharmacy's trajectory is bounded by two structural realities: the "
        "resident bed base and the two-sided reimbursement squeeze. The bed "
        "base — dominated by skilled nursing — was hit hard by the pandemic and "
        "has been recovering occupancy slowly, so volume growth is modest and "
        "demographic rather than pricing-driven. On reimbursement, the sector "
        "gets compressed from both sides: PDPM bundles skilled-day drugs into "
        "the SNF per-diem (the facility sets the price), while Part D DIR fees "
        "claw back the long-stay dispensing margin. The competitive map shifted "
        "when Omnicare receded, leaving BrightSpring/PharMerica (KKR, 2024 IPO) "
        "and the Guardian franchise roll-up to consolidate a large regional "
        "tail — a classic buy-and-build densifying delivery routes and lifting "
        "generic dispensing rates. Overlaying it all, SNF financial distress and "
        "the new minimum-staffing rule make the facility customer's solvency the "
        "sector's central risk, keeping quality-of-earnings focused on customer "
        "credit and route economics rather than growth."),
    growth_levers=[
        GrowthLever(
            "65+ / 85+ population growth (resident base)",
            "The aging population slowly expands the long-term-care resident "
            "base that drives script volume.",
            "+2%/yr demographic", "GOV"),
        GrowthLever(
            "SNF occupancy recovery",
            "Post-COVID occupancy rebuilding lifts the bed base the pharmacy "
            "serves — a recovery lever, not a secular one.",
            "occupancy swing", "ILLUSTRATIVE"),
        GrowthLever(
            "Roll-up route densification",
            "Consolidators tuck in regional pharmacies and densify delivery "
            "routes, converting fragmentation into operating leverage.",
            "M&A + density", "ILLUSTRATIVE"),
        GrowthLever(
            "Per-resident drug intensity",
            "New therapies and higher-acuity residents raise per-bed drug "
            "spend (partly offset by generic substitution).",
            "+1-2%/yr mix", "ILLUSTRATIVE"),
        GrowthLever(
            "Generic dispensing-rate gains",
            "Lifting GDR improves captured margin — an efficiency lever rather "
            "than a revenue lever.",
            "margin lever", "ILLUSTRATIVE"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="The long-term-care resident bed base (occupancy × beds)",
        analysis=(
            "LTC pharmacy volume is a near-direct function of occupied long-term-"
            "care beds — roughly 1.2M certified skilled-nursing beds plus a "
            "comparably-sized assisted-living base. That makes the demand driver "
            "unusually mechanical: script volume tracks the resident census, "
            "which is set by the aging 65+/85+ population on the upside and by "
            "facility occupancy on the downside. The pandemic depressed SNF "
            "occupancy sharply, and the slow recovery — not disease incidence — "
            "is the dominant swing factor on near-term volume. Because the bed "
            "base grows only slowly and occupancy is the binding constraint, LTC "
            "pharmacy is a low-single-digit organic-growth market where scale is "
            "built through consolidation of the resident base rather than "
            "through per-unit demand growth. Assisted-living growth adds beds but "
            "with a softer closed-door-pharmacy fit than skilled nursing."),
        basis="GOV"),
    cost_drivers=[
        CostDriver(
            "Drug acquisition (inventory)",
            "~80-85% of revenue",
            "The medications themselves; generic dispensing rate is the primary "
            "lever on the spread taken over this cost.", "ILLUSTRATIVE"),
        CostDriver(
            "Pharmacist + technician labor",
            "the #1 controllable cost",
            "Dispensing, cycle-fill, and the mandated consultant-pharmacist "
            "drug-regimen review — a scarce, hard-to-staff labor base.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Delivery & logistics (route density)",
            "~8-12% of cost",
            "Routed couriers, STAT and emergency-kit service — the distribution "
            "backbone where density is everything.", "ILLUSTRATIVE"),
        CostDriver(
            "Packaging & dispensing technology",
            "~4-8% of cost",
            "Unit-dose / blister-pack automation, eMAR/med-cart integration, and "
            "pharmacy systems.", "ILLUSTRATIVE"),
        CostDriver(
            "Bad debt / DIR clawback",
            "varies by book",
            "Facility slow-pay and uncollected receivables plus Part D DIR "
            "clawbacks — the margin leak on both billing sides.",
            "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "No public closed-door-pharmacy census is vendored, so LTC-pharmacy "
        "geography is not directly computable and is omitted rather than "
        "fabricated. As a proxy, the demand geography follows the skilled-"
        "nursing bed base, which IS observable — the CMS Nursing Home Care "
        "Compare file (wired in the connectors below) maps SNF beds, ownership, "
        "and concentration by state and stands in for where LTC-pharmacy demand "
        "and facility-customer credit risk actually sit."),
)

register(REPORT)
