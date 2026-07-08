"""DME — durable medical equipment, prosthetics, orthotics & supplies (DMEPOS).

Deals-only vertical (CMS DMEPOS supplier files aren't vendored as a facility
roll), authored off the hospice copy-template. The report is organized around
the two truths that decide a DME deal: the setup is the cost but the recurring
resupply annuity is the business, and documentation IS the revenue — DME is the
most audit- and denial-intensive corner of healthcare billing, with competitive
bidding hanging over the fee schedule.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver, default_connections,
    live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="dme",
    name="DME",
    care_setting="Pharmacy & infusion",
    naics="423450",
    one_line_def=(
        "Durable medical equipment, prosthetics, orthotics, and supplies "
        "(DMEPOS) furnished to patients at home — home respiratory (oxygen, "
        "CPAP/BiPAP and resupply, ventilators), mobility and complex rehab, "
        "diabetic supplies and CGMs, enteral nutrition, wound, and ostomy/"
        "urological — billed largely through the Medicare Part B DMEPOS fee "
        "schedule."),
    tam_headline=TamHeadline(
        value=60.0, unit="$B", growth_pct=6.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "US all-payer home medical equipment / DMEPOS market, modeled at "
            "~$60B; Medicare DMEPOS spend (~$8-9B, CMS) is the filed sub-"
            "segment. Growth is the modeled composite of aging, chronic-disease "
            "prevalence, and CGM/respiratory expansion, net of fee-schedule "
            "pressure."),
    ),
    executive_summary=[
        "The setup is the cost; the resupply is the business. New patient "
        "setups are documentation-heavy and low-margin; the recurring CPAP, "
        "diabetic, and ostomy resupply annuity is where the money and the "
        "multiple are. Underwrite resupply pull-through, not new starts.",
        "Documentation IS the revenue. DME is the most audit- and "
        "documentation-intensive billing in healthcare — a missing face-to-face "
        "note or written order (WOPD) means the claim is denied and clawed "
        "back. Cost-to-collect and denial rate separate winners from losers.",
        "Competitive bidding is the sword of Damocles. The program's dormancy "
        "props up current rates; a restart can reset the whole fee schedule — a "
        "structural policy overhang that caps the multiple.",
        "DME telehealth / brace fraud enforcement poisoned the well. Clean "
        "referral sourcing and marketing compliance are first-order diligence, "
        "not footnotes, after the orthotic-brace and telehealth takedowns.",
        "Complex rehab (power wheelchairs) is a different, better animal — high "
        "service, ATP-credentialed, carved out of competitive bidding — versus "
        "commodity respiratory. It is the more defensible niche in a fragmented, "
        "PE-rolled-up market.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Referral — hospital discharge, sleep lab, physician, health system",
            "Qualification — face-to-face, written order (WOPD), medical-need "
            "documentation",
            "Benefit + prior authorization (PMDs, certain items)",
            "Setup / fitting — deliver, fit, and educate the patient",
            "Billing — rental vs. purchase; capped-rental schedules",
            "Compliance monitoring (e.g., CPAP adherence data)",
            "Resupply cadence — the recurring consumables annuity",
            "Audit defense — ADR / CERT / UPIC documentation response",
        ],
        sites_of_care=[
            "Patient home (the delivery + service model)",
            "Retail / storefront HME locations (mobility, fitting)",
            "Hospital-discharge and health-system partnerships (referral)",
            "Mail-order (diabetic supplies, CPAP resupply)",
        ],
        money_flow=(
            "Most revenue runs through the Medicare Part B DMEPOS fee schedule "
            "(with commercial and Medicaid alongside). Items are paid as capped "
            "rentals (oxygen is a 36-month rental cap then continued furnishing; "
            "CPAP is a 13-month rent-to-own), inexpensive-or-routinely-purchased, "
            "or resupply consumables (CPAP masks and tubing, diabetic supplies, "
            "ostomy/urological — the recurring annuity). Payment on any claim is "
            "contingent on documentation: a face-to-face encounter, a written "
            "order prior to delivery, and proof of continued medical need — and "
            "on compliance for some items (CPAP adherence data). The historical "
            "Competitive Bidding Program set rates by bid area; it has been "
            "dormant since 2018, so current rates rest on an adjusted fee "
            "schedule that a future bidding round could reset."),
        key_players=(
            "Home respiratory is led by Lincare (Linde), AdaptHealth (public), "
            "Apria (Owens & Minor), and Rotech. Diabetic and mail-order supply "
            "runs through Byram Healthcare (Owens & Minor), CCS Medical, and "
            "Aeroflow. Complex rehab technology (power wheelchairs) is its own "
            "high-service niche led by Numotion and National Seating & Mobility "
            "(NSM). Device makers ResMed and Philips sit upstream. Beneath the "
            "consolidators is a long fragmented tail of regional HME suppliers — "
            "the acquirable pool."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Home respiratory (oxygen, CPAP/BiPAP, vents)",
                    "the largest DME block",
                    "ILLUSTRATIVE · product-mix model"),
            Segment("Resupply consumables (CPAP, diabetic, ostomy)",
                    "the recurring annuity",
                    "ILLUSTRATIVE · resupply-economics model"),
            Segment("Mobility + complex rehab (CRT / power wheelchairs)",
                    "high-service, bidding-carved-out niche",
                    "ILLUSTRATIVE · product-mix model"),
            Segment("Medicare DMEPOS spend (the filed sub-segment)",
                    "~$8-9B",
                    "GOV · CMS Medicare DMEPOS expenditures"),
            Segment("Diabetic supplies + CGMs",
                    "fast-growing (CGM channel shift)",
                    "ILLUSTRATIVE · CGM adoption model"),
        ],
        growth_drivers=[
            "Aging population + chronic-disease prevalence ~+3-4%/yr",
            "CGM adoption (Dexcom / Libre) expanding diabetic DME ~double digit",
            "Sleep-apnea diagnosis + CPAP resupply pull-through",
            "Site-of-care shift toward home-based care lifting home equipment",
            "Competitive-bidding overhang / fee-schedule pressure (a drag)",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Medicare Part B / MA (DMEPOS)": 0.45,
            "Commercial": 0.35,
            "Medicaid / other": 0.20,
        },
        rate_mechanics=[
            "DMEPOS fee schedule (Part B) — the base rates for equipment, "
            "supplies, prosthetics, and orthotics.",
            "Competitive Bidding Program — historically set rates in bid areas; "
            "dormant since 2018, so an adjusted fee schedule applies (a restart "
            "is the overhang).",
            "Capped rental / rent-to-own — oxygen 36-month cap then continued "
            "furnishing; CPAP 13-month rent-to-own; other capped-rental items.",
            "Resupply cadence + documentation — consumables (CPAP masks, "
            "diabetic, ostomy) pay recurring, contingent on proof of continued "
            "use and orders.",
            "CPAP compliance requirement — coverage continuation requires "
            "demonstrated adherence data.",
            "Prior authorization — required for power mobility devices (PMDs) "
            "and certain high-cost items.",
        ],
        reimbursement_risk=(
            "Two forces dominate. First, documentation-driven denials and "
            "audits: DME is the most heavily audited billing in Medicare (CERT, "
            "ADR, UPIC/RAC), and a missing face-to-face, WOPD, or continued-need "
            "record turns paid revenue into a clawback — cost-to-collect and "
            "denial rate are first-order to margin. Second, competitive bidding: "
            "the program's dormancy is holding rates up, and a future round "
            "could reset the fee schedule downward across core categories. "
            "Layered on top are item-specific cuts (oxygen, CPAP), the CGM "
            "channel shift between pharmacy and DME, and a fraud-enforcement "
            "history (orthotic braces, telehealth) that makes referral and "
            "marketing compliance a live risk."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("DMEPOS Competitive Bidding Program",
                 "Historically set DME rates in bid areas; its dormancy props "
                 "up current pricing and a restart is the sector's largest "
                 "structural overhang.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/dmepos-competitive-bidding"),
            Rule("Medicare DMEPOS fee schedule + capped rental",
                 "The core price list and the oxygen-36-month / CPAP-13-month "
                 "rental structures that shape revenue recognition.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/dmepos-fee-schedule"),
            Rule("Documentation regime — face-to-face, WOPD, continued need",
                 "The written-order-prior-to-delivery and medical-necessity "
                 "rules whose gaps drive CERT/ADR/UPIC denials and recoupment.",
                 "https://www.cms.gov/medicare-coverage-database/"),
            Rule("Medicare supplier enrollment (855S) + accreditation + bond",
                 "DMEPOS suppliers must enroll, accredit, and post a surety "
                 "bond — the barriers that thinned the supplier base after "
                 "bidding.",
                 "https://www.cms.gov/medicare/enrollment-renewal/providers-suppliers/chain-ownership-system-pecos"),
            Rule("Prior authorization for PMDs + certain items",
                 "Power mobility devices and selected high-cost items require "
                 "prior auth — a cash-flow and denial-timing factor.",
                 "https://www.cms.gov/research-statistics-data-and-systems/monitoring-programs/medicare-ffs-compliance-programs/prior-authorization-and-pre-claim-review-initiatives"),
            Rule("OIG / DOJ DME fraud enforcement (braces, telehealth)",
                 "The orthotic-brace and telehealth takedowns make referral "
                 "sourcing and marketing compliance a first-order diligence "
                 "item.",
                 "https://oig.hhs.gov/reports-and-publications/all-reports-and-publications/"),
        ],
        policy_watch=[
            "Any restart / redesign of the DMEPOS Competitive Bidding Program",
            "CGM coverage policy + pharmacy-vs-DME channel placement",
            "Item-specific rate cuts (oxygen, CPAP, urological)",
            "Prior-authorization expansion to more DME categories",
            "Continued DME telehealth / marketing fraud enforcement",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Highly fragmented despite consolidation — thousands of DMEPOS "
            "suppliers thinned by competitive bidding, accreditation, and bond "
            "requirements, but still a long regional tail beneath the national "
            "consolidators. That tail, plus recurring resupply revenue, is the "
            "PE roll-up pool."),
        hhi_or_share=(
            "No single dominant national supplier; Lincare, AdaptHealth, Apria, "
            "and Rotech lead home respiratory while complex rehab is a Numotion/"
            "NSM near-duopoly. CMS DMEPOS supplier files aren't vendored as a "
            "facility roll, so a national HHI is omitted rather than "
            "fabricated."),
        consolidation=(
            "Aggressively rolled up over the last decade. AdaptHealth "
            "assembled respiratory, CPAP, and diabetes assets; Rotech and Apria "
            "scaled respiratory; Byram/CCS consolidated diabetic supply; and "
            "complex rehab concentrated into Numotion (AEA) and NSM. The thesis "
            "is fragmentation plus a recurring resupply annuity, discounted for "
            "bidding and audit risk."),
        pe_activity=(
            "One of the most PE-active supply verticals: respiratory and "
            "diabetic-resupply roll-ups and complex-rehab platforms (Numotion, "
            "NSM). Sponsor diligence centers on resupply pull-through, denial/"
            "audit exposure, referral-source compliance, and competitive-bidding "
            "sensitivity."),
        notable_players=[
            "Lincare (Linde)", "AdaptHealth", "Apria (Owens & Minor)",
            "Rotech Healthcare", "Byram Healthcare (Owens & Minor)",
            "CCS Medical", "Numotion", "National Seating & Mobility (NSM)",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Active patient census", "the annuity base",
                "The installed base driving recurring resupply — the primary "
                "value driver over one-time setups."),
            Kpi("Resupply pull-through / adherence", "the crown-jewel metric",
                "How reliably CPAP/diabetic/ostomy patients reorder — the "
                "recurring revenue that carries the multiple."),
            Kpi("Denial / audit rate + cost-to-collect", "billing-quality metric",
                "DME's documentation intensity means denials and rework can "
                "swamp margin; clean billing is the operating edge."),
            Kpi("Rental vs. purchase mix + DSO", "cash-flow metric",
                "Capped-rental schedules spread revenue and stretch DSO; the "
                "mix shapes working capital."),
            Kpi("Revenue / setup", "referral-economics metric",
                "New starts are documentation-heavy and low-margin; they matter "
                "as feeders into the resupply annuity."),
            Kpi("DME EBITDA margin (illustrative)", "10-20%",
                "Thin gross plus heavy billing/logistics ops; resupply mix, "
                "denial discipline, and bidding exposure set the band."),
        ],
        margin_profile=(
            "DME margin is built on recurring resupply, not on equipment sales. "
            "Gross margins are thin and the cost base is dominated by billing "
            "operations, logistics/delivery, and denial rework; a new setup is "
            "often near break-even and earns its return only through the "
            "downstream resupply annuity. The operators that win run clean "
            "documentation (low denial and audit-recoupment rates), high "
            "resupply pull-through, and dense delivery logistics. Complex rehab "
            "is structurally higher-margin — high service, ATP-credentialed, and "
            "carved out of competitive bidding — while commodity respiratory is "
            "the most bidding- and rate-exposed."),
    ),
    risks=[
        Risk("Competitive-bidding restart / rate reset", "High",
             "A new bidding round could reset the fee schedule downward across "
             "core categories — the central structural overhang."),
        Risk("Documentation denials + audit recoupment", "High",
             "CERT/ADR/UPIC/RAC audits turn paid claims into clawbacks when "
             "face-to-face, WOPD, or continued-need records are missing."),
        Risk("Item-specific rate cuts (oxygen, CPAP)", "Medium",
             "Category rate reductions compress the highest-volume respiratory "
             "lines."),
        Risk("Referral compliance + AKS / fraud enforcement", "Medium",
             "The brace and telehealth takedowns make marketing and referral "
             "sourcing a live compliance risk."),
        Risk("Supply / device disruption", "Medium",
             "The Philips CPAP recall showed how a device event can freeze "
             "setups and resupply across the sector."),
        Risk("CGM channel shift (pharmacy vs. DME)", "Medium",
             "Movement of continuous glucose monitors between the pharmacy and "
             "DME benefits reshapes diabetic economics."),
    ],
    diligence_questions=[
        "What share of revenue is recurring resupply versus one-time setups, "
        "and what is resupply pull-through / adherence?",
        "What are the denial rate, audit-recoupment history (CERT/ADR/UPIC), "
        "and cost-to-collect?",
        "What is the product mix, and how exposed is it to a competitive-bidding "
        "restart by category?",
        "How is referral sourcing structured (hospital, sleep lab, physician), "
        "and does marketing pass Anti-Kickback scrutiny?",
        "What is the rental-vs-purchase mix and DSO, and how much revenue sits "
        "in capped-rental schedules?",
        "What is the CGM / diabetic exposure, and how is the pharmacy-vs-DME "
        "channel shift affecting it?",
        "For complex rehab, what is ATP staffing and the CRT carve-out share of "
        "the book?",
    ],
    insider_lens=[
        "The setup loses money; the resupply makes it. New starts are "
        "documentation-heavy and near break-even — the CPAP/diabetic/ostomy "
        "resupply annuity is the business. A book heavy on new starts and light "
        "on resupply is worth far less than the revenue suggests.",
        "Documentation is literally the revenue. DME is the most audited billing "
        "in Medicare; a missing face-to-face note or WOPD converts a paid claim "
        "into a clawback. Denial rate and cost-to-collect are the real operating "
        "metrics.",
        "Competitive bidding is a dormant volcano. Current rates rest on the "
        "program being paused since 2018; a restart can reset the whole fee "
        "schedule and re-underwrite the sector overnight — it caps the multiple "
        "even while quiet.",
        "The fraud history is a live liability, not old news. Brace and "
        "telehealth DME takedowns mean clean referral sourcing and marketing "
        "compliance are underwriting inputs — a dirty lead channel is a "
        "deal-killer.",
        "Complex rehab is the good neighborhood. Power-wheelchair CRT is high-"
        "service, ATP-credentialed, and carved out of competitive bidding — a "
        "structurally better-margin, more-defensible niche than commodity "
        "respiratory.",
    ],
    connections=default_connections(
        "dme",
        deals_sector="dme",
        connectors=[
            ("cms_open_data_mup_dme_by_supplier_service",
             "CMS Medicare DME by supplier & service — supplier volume, "
             "allowed charges, and product-line mix"),
            ("provider_data_medical_equipment_suppliers",
             "CMS Medical Equipment Suppliers — the enrolled DMEPOS supplier "
             "footprint"),
            ("npi_provider_taxonomy",
             "NPI taxonomy — DMEPOS supplier enrollment and product-category "
             "specialties"),
            ("oig_leie_exclusions",
             "OIG LEIE — excluded individuals/entities (given the DME fraud "
             "history, a first-order integrity screen)"),
            ("census_acs_cbsa_profile",
             "Census ACS — 65+ and chronic-condition catchment for territory "
             "mapping"),
            ("openfda_device_recall",
             "openFDA device recalls — respiratory/CPAP device-event exposure "
             "(the Philips-recall class of risk)"),
        ],
    ),
    sources=[
        Source("CMS Medicare DMEPOS fee schedule + Competitive Bidding "
               "Program", "GOV",
               "https://www.cms.gov/medicare/payment/fee-schedules/dmepos-fee-schedule"),
        Source("CMS Medicare DMEPOS expenditure and utilization data", "GOV",
               "https://www.cms.gov/data-research/statistics-trends-and-reports"),
        Source("HHS OIG — DMEPOS program-integrity and fraud-enforcement "
               "reports (braces, telehealth)", "GOV",
               "https://oig.hhs.gov/reports-and-publications/all-reports-and-publications/"),
        Source("CMS DME MAC Local Coverage Determinations + documentation "
               "requirements", "GOV",
               "https://www.cms.gov/medicare-coverage-database/"),
        Source("AAHomecare — home medical equipment industry data and policy",
               "INDUSTRY", "https://www.aahomecare.org/"),
        Source("PE Desk industry deep-dive (DME) + realized-deal corpus",
               "INTERNAL", "/diligence/tam-sam?template=dme"),
    ],
    live_figures=live_figures_from_dive("dme"),
    trends=(
        "DME has been reshaped by consolidation on one side and a fee-schedule "
        "overhang on the other. Competitive bidding thinned the supplier base "
        "through the 2010s, and accreditation and surety-bond requirements "
        "raised the barrier further — clearing the field for national "
        "consolidators (AdaptHealth, Lincare, Apria, Rotech) to roll up "
        "respiratory and diabetic supply and for complex rehab to concentrate "
        "into Numotion and NSM. The durable value migrated to the recurring "
        "resupply annuity — CPAP consumables, diabetic supplies, ostomy — while "
        "one-time setups became low-margin feeders. Three currents now define "
        "the trajectory: the dormant Competitive Bidding Program, whose pause "
        "holds rates up but whose restart could reset the fee schedule; a "
        "relentless documentation-and-audit regime that makes billing quality "
        "the operating edge; and secular demand tailwinds from aging, sleep-"
        "apnea diagnosis, and the CGM boom in diabetes. Overlaying it, the DME "
        "fraud takedowns (orthotic braces, telehealth) moved referral and "
        "marketing compliance to the center of diligence."),
    growth_levers=[
        GrowthLever(
            "Aging + chronic-disease prevalence",
            "An older population with more COPD, sleep apnea, diabetes, and "
            "mobility need expands the installed equipment base.",
            "+3-4%/yr demographic", "ILLUSTRATIVE"),
        GrowthLever(
            "CGM adoption (diabetic DME)",
            "Continuous glucose monitors are a fast-growing, high-volume "
            "diabetic category expanding the DME book.",
            "double-digit", "ILLUSTRATIVE"),
        GrowthLever(
            "CPAP resupply pull-through",
            "Sleep-apnea diagnosis feeds an installed CPAP base whose mask/"
            "tubing resupply is the recurring annuity.",
            "annuity growth", "ILLUSTRATIVE"),
        GrowthLever(
            "Site-of-care shift to the home",
            "Home-based care models lift demand for home respiratory, mobility, "
            "and monitoring equipment.",
            "channel shift", "ILLUSTRATIVE"),
        GrowthLever(
            "Competitive-bidding / fee-schedule pressure",
            "The bidding overhang and item-specific rate cuts are a persistent "
            "drag on per-unit reimbursement.",
            "rate drag", "GOV"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="The aging chronic-disease population feeding the resupply base",
        analysis=(
            "DME demand is driven by the growth of the chronic-disease "
            "population that needs home equipment — and, crucially, by how much "
            "of that need converts into a recurring resupply base rather than a "
            "one-time sale. Aging lifts COPD and oxygen, sleep-apnea diagnosis "
            "lifts CPAP, and the diabetes epidemic — turbocharged by continuous "
            "glucose monitors — lifts diabetic supply, each creating an "
            "installed base that reorders consumables on a cadence. The dominant "
            "value driver is therefore the durable resupply annuity, not the "
            "flow of new setups: a supplier's growth is the product of new-start "
            "capture and resupply pull-through/adherence. The main offset is not "
            "demand but reimbursement — the competitive-bidding overhang and "
            "item-specific rate cuts compress per-unit revenue even as unit "
            "volume climbs."),
        basis="ILLUSTRATIVE"),
    cost_drivers=[
        CostDriver(
            "Equipment + consumable cost of goods",
            "~40-50% of revenue",
            "The devices and resupply consumables themselves; commodity "
            "respiratory carries thinner margins than complex rehab.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Billing, intake & audit-defense operations",
            "the #1 controllable cost",
            "Documentation collection, benefit/prior-auth, denial rework, and "
            "ADR/audit response — DME's defining cost intensity.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Delivery, logistics & fitting labor",
            "~10-15% of cost",
            "Home delivery, setup/fitting (respiratory therapists, ATPs for "
            "CRT), and resupply fulfillment logistics.", "ILLUSTRATIVE"),
        CostDriver(
            "Field / clinical labor",
            "~8-12% of cost",
            "Respiratory therapists, mobility/ATP specialists, and patient "
            "education staff.", "ILLUSTRATIVE"),
        CostDriver(
            "Bad debt / recoupment reserve",
            "varies by book",
            "Uncollected patient responsibility plus reserves against audit "
            "recoupment — a real margin leak in a denial-heavy business.",
            "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "CMS publishes DMEPOS supplier and utilization data, but not as a clean "
        "vendored facility roll here, so a computed state map is omitted rather "
        "than fabricated. Two connectors below stand in: the Medicare DME "
        "by-supplier-service dataset and the Medical Equipment Suppliers file "
        "map supplier volume and enrolled footprint, and the demand geography "
        "tracks the 65+ and chronic-disease population (via Census ACS) more "
        "than any certified-site census. Use those to triangulate supplier "
        "concentration and catchment by market."),
)

register(REPORT)
