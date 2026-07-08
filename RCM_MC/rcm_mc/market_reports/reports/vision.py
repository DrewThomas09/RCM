"""Vision — the optometry + optical-retail eye-care roll-up.

Deals-only deep-dive (no national OD-practice facility file; geography is
omitted rather than fabricated). "Vision" is the optometrist-led, retail-heavy
eye-care vertical — the routine eye exam plus the optical dispensary (frames,
lenses, contact lenses) — as distinct from ``ophthalmology`` (surgical MD eye
care: cataract, retina, glaucoma surgery). The economics are a retail business
wearing a clinic: the exam is a near-loss-leader that drives traffic, and the
money is optical capture, managed-vision-plan volume, and — increasingly —
medical optometry billed to health insurance. The qualitative sections are
authored around the capture-rate model, the VSP/EyeMed managed-vision duopoly,
the online-contacts disruption, and the optometric scope-of-practice expansion.
Consumes ``vision_deep_dive()`` for SOURCED corpus deal figures.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="vision",
    name="Vision",
    care_setting="Physician services",
    naics="621320",
    one_line_def=(
        "Optometrist-led primary eye care — the routine refractive exam plus "
        "the optical dispensary that sells frames, spectacle lenses, and "
        "contact lenses — where the professional exam fee is a traffic driver "
        "and the economics live in optical retail capture, managed-vision-plan "
        "volume, and a growing medical-optometry line billed to health "
        "insurance (distinct from surgical ophthalmology)."),
    tam_headline=TamHeadline(
        value=45.0, unit="$B", growth_pct=4.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "Modeled from the ~45,000 practicing US optometrists (BLS OES / "
            "AOA workforce) times the exam professional fee plus the optical "
            "dispensary capture (frames + lenses + contact lenses) and the "
            "medical-optometry line — an eye-care-services-plus-optical base, "
            "not a single published figure. Growth is the modeled composite of "
            "aging/myopia demand, medical-optometry mix shift, and optical "
            "average-order-value, net of online-contacts substitution and "
            "managed-vision fee pressure."),
    ),
    executive_summary=[
        "The exam is the traffic; the money is the optical. A routine eye exam "
        "reimburses modestly, but it writes a prescription that converts into a "
        "frame + lens + contact-lens sale at strong retail margin — 'capture "
        "rate' (share of exams that buy optical in-store) and average order "
        "value are the two numbers that set a vision platform's value.",
        "Managed vision is a discount club, not medical insurance. VSP and "
        "EyeMed together control the great majority of the vision-plan market; "
        "a member's plan pays a thin exam fee and a materials allowance, so "
        "panel access drives traffic but compresses per-unit economics — the "
        "plan mix is a first-order diligence item.",
        "Medical optometry is the upgrade thesis. Optometrists increasingly "
        "diagnose and manage ocular disease (dry eye, glaucoma monitoring, "
        "diabetic retinopathy screening) billed to Medicare and commercial "
        "medical benefits at real professional fees — a higher-value, "
        "recurring line that de-risks the retail cyclicality.",
        "Online and DTC are the structural headwind. 1-800 Contacts, Warby "
        "Parker, and Hubble unbundled the prescription from the dispensary; the "
        "Fairness to Contact Lens Consumers Act and the FTC prescription-release "
        "rule force the practice to hand the Rx to the patient, who can then buy "
        "materials anywhere.",
        "Scope-of-practice is a state-by-state tailwind. Optometry's expanding "
        "authority (therapeutic drugs, and in a growing set of states laser and "
        "injection privileges) enlarges the billable medical scope — the "
        "ongoing 'scope wars' with organized ophthalmology are a real, "
        "state-legislative value driver.",
        "It is a national retail roll-up already well underway (MyEyeDr, "
        "EyeCare Partners, Acuity Eyecare); the acquirable pool is the "
        "independent OD practice with an owned dispensary, richest where "
        "medical-optometry capture and managed-plan panels can be layered on.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Patient books a routine or medical eye exam (self-pay, vision "
            "plan, or medical benefit)",
            "Comprehensive exam + refraction by the optometrist (OD)",
            "Prescription written (spectacle Rx and/or contact-lens Rx) and "
            "released to the patient",
            "Optical dispensary: frame selection, lens options (progressive, "
            "AR, photochromic), measurements",
            "Lab fabrication (in-house or wholesale surfacing lab) + dispensing",
            "Contact-lens fitting, trial, and annual supply sale",
            "Medical-eye-care management (dry eye, glaucoma, diabetic screen) "
            "billed to the medical benefit + recall",
        ],
        sites_of_care=[
            "Independent OD office with an attached optical dispensary",
            "Retail-host sublease (LensCrafters, Walmart, Costco, Target "
            "Optical — OD leases space next to the optical)",
            "Regional optical-retail chain locations (branded platforms)",
            "Online / omnichannel (Rx renewal, contact-lens resupply, DTC "
            "eyewear) — the substitute channel",
        ],
        money_flow=(
            "A vision practice earns three distinct streams off one patient. "
            "The exam is paid a modest professional fee — often through a "
            "managed vision plan (VSP, EyeMed, Davis) that also grants a "
            "materials allowance, or self-pay, or (for a medical complaint) the "
            "patient's medical insurance under the Physician Fee Schedule. The "
            "optical dispensary then sells frames, spectacle lenses, and "
            "contact lenses at retail — the true profit engine, gated by how "
            "many exam patients buy in-store (capture rate) and at what average "
            "order value. And a growing medical-optometry line bills Medicare "
            "and commercial medical benefits for diagnosing and managing ocular "
            "disease. In the PE structure the platform MSO owns the optical, "
            "the labs, buying scale on frames/lenses, and the managed-vision "
            "contracts, while the OD retains the clinical professional entity. "
            "The single question that sets a vision platform's value is the mix "
            "of high-margin optical capture and recurring medical-optometry "
            "revenue against the thin, plan-compressed exam fee."),
        key_players=(
            "PE-backed national platforms lead the roll-up: MyEyeDr (Goldman "
            "Sachs), EyeCare Partners (Partners Group), and Acuity Eyecare "
            "Group scaled the OD-plus-optical model; National Vision Holdings "
            "(America's Best, Eyeglass World) and Warby Parker are public "
            "retail comparables; Walmart, Costco, and Target Optical anchor the "
            "host-retail channel; and Luxottica/EssilorLuxottica (LensCrafters, "
            "Pearle, plus lens and frame manufacturing and the EyeMed plan) is "
            "the vertically-integrated giant that sits across supply, retail, "
            "and payer. The acquirable pool is the independent OD practice with "
            "an owned dispensary and a managed-plan panel."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Practicing US optometrists (ODs)", "~45,000",
                    "GOV · BLS OES optometrist employment (directional)"),
            Segment("US vision-care + optical retail (exams + eyewear + "
                    "contacts)", "~$45-60B",
                    "ILLUSTRATIVE · modeled services-plus-optical base, "
                    "directional"),
            Segment("Managed-vision covered lives (VSP + EyeMed + others)",
                    "majority of insured Americans carry a vision plan",
                    "INDUSTRY · vision-plan enrollment estimates (directional)"),
            Segment("Optical materials share of a practice's revenue",
                    "~50-65% (frames + lenses + contacts)",
                    "ILLUSTRATIVE · practice economics, directional"),
            Segment("US adults with myopia (refractive demand base)",
                    "~40%+ of the population and rising",
                    "ACADEMIC · myopia-prevalence epidemiology (directional)"),
        ],
        growth_drivers=[
            "Aging + presbyopia — the 45+ population needs progressive lenses "
            "and drives higher-value optical",
            "Myopia prevalence rising (screen time / near-work) — larger "
            "refractive base and myopia-management upsell",
            "Medical-optometry mix shift — disease management billed to the "
            "medical benefit at real fees",
            "Optical average-order-value — premium progressives, AR/blue-light, "
            "and specialty contact lenses",
            "Online / DTC substitution and managed-vision fee pressure — the "
            "structural offsets",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Managed vision plan (VSP / EyeMed / Davis)": 0.40,
            "Self-pay / cash (optical + exams)": 0.30,
            "Medical (Medicare / commercial medical benefit)": 0.22,
            "Medicaid": 0.08,
        },
        rate_mechanics=[
            "Managed vision plans (VSP, EyeMed, Davis Vision) — a discount / "
            "materials-allowance model, NOT medical insurance: the plan pays a "
            "thin exam fee plus a frame/lens/contact allowance, and reimburses "
            "materials near wholesale-plus, so plan mix compresses per-unit "
            "economics even as it drives traffic.",
            "Optical retail — frames, spectacle lenses, and contact lenses sold "
            "largely cash / allowance at retail margin; the true profit engine, "
            "outside the medical fee schedule entirely.",
            "Medical eye care — the Medicare Physician Fee Schedule (RVUs × "
            "GPCI × conversion factor) and commercial equivalents for E&M and "
            "ophthalmic-diagnostic CPTs (visual fields, OCT, fundus imaging) "
            "when the visit is for a medical complaint or disease management.",
            "Refraction (CPT 92015) is typically NON-covered by Medicare — a "
            "routine-vision service the patient pays out of pocket even inside "
            "a medical visit.",
            "Contact-lens fitting fees and annual-supply sales — a recurring, "
            "largely cash line separate from the spectacle Rx.",
            "The Fairness to Contact Lens Consumers Act (FCLCA) + FTC "
            "prescription-release rule require the practice to hand the Rx to "
            "the patient, enabling third-party (online) materials purchase.",
        ],
        reimbursement_risk=(
            "Vision's reimbursement risk is bifurcated. On the routine side, "
            "the managed-vision duopoly (VSP, EyeMed) sets thin exam fees and "
            "materials allowances, and online/DTC channels strip the materials "
            "margin the moment the Rx is released — so the retail engine faces "
            "structural fee and channel pressure. On the medical side, the "
            "professional fee for medical-optometry visits and ophthalmic "
            "diagnostics rides the same MPFS conversion-factor drift as every "
            "specialty, and refraction stays non-covered. The healthiest "
            "platforms hedge by growing the medical-optometry line (real, "
            "recurring, insurance-paid) and defending optical capture and "
            "average order value against the online channel — because no single "
            "managed-vision contract or DTC entrant should be existential."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("Fairness to Contact Lens Consumers Act (FCLCA) + FTC "
                 "Contact Lens Rule",
                 "Requires automatic release and verification of the "
                 "contact-lens prescription — the rule that lets patients buy "
                 "contacts online and unbundles materials from the exam.",
                 "https://www.ftc.gov/legal-library/browse/rules/contact-lens-rule"),
            Rule("FTC Eyeglass Rule (prescription release)",
                 "Requires the prescriber to give the patient the spectacle Rx "
                 "at no extra charge — the same unbundling force on eyewear.",
                 "https://www.ftc.gov/legal-library/browse/rules/eyeglass-rule"),
            Rule("State optometric scope-of-practice statutes",
                 "State boards define what optometrists may diagnose, "
                 "prescribe, and perform (therapeutics, and in a growing set of "
                 "states laser/injection privileges) — the billable-scope and "
                 "the 'scope wars' battleground with organized ophthalmology.",
                 None),
            Rule("Corporate practice of medicine / optometry doctrine",
                 "Strong-CPOM states force the friendly-professional-entity + "
                 "MSO structure and constrain how a retailer or investor may "
                 "own the clinical practice.",
                 None),
            Rule("Medicare Physician Fee Schedule (annual Final Rule)",
                 "Sets RVUs and the conversion factor for the medical-eye-care "
                 "E&M and ophthalmic-diagnostic (OCT, visual field) codes — the "
                 "medical-optometry revenue base.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
            Rule("Anti-Kickback Statute (retail-host & referral arrangements)",
                 "Governs OD-to-optical and OD-to-ophthalmology referral and "
                 "sublease arrangements (co-located surgical/retail relations "
                 "must be fair-market-value).",
                 "https://oig.hhs.gov/compliance/advisory-opinions/"),
        ],
        policy_watch=[
            "State scope-of-practice expansion (laser/injection authority) — "
            "the ongoing optometry-vs-ophthalmology legislative fights",
            "FTC enforcement / rulemaking on contact-lens prescription release "
            "and online-verification robocalls",
            "Managed-vision plan consolidation and provider-fee schedules "
            "(VSP/EyeMed panel economics)",
            "State PE-in-healthcare transaction-review laws reaching optometry "
            "roll-ups",
            "Annual MPFS conversion-factor cuts hitting the medical-optometry "
            "line",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "US optometry is still highly fragmented across independent single- "
            "and few-doctor practices with attached dispensaries, but it is one "
            "of the more consolidated ambulatory retail-clinical verticals: a "
            "handful of PE-backed national platforms and public retail chains "
            "now operate thousands of locations. The acquirable pool is the "
            "independent OD practice with an owned optical and a managed-plan "
            "panel."),
        hhi_or_share=(
            "No single owner is dominant nationally; concentration is regional "
            "and channel-specific (host-retail vs independent-brand). No "
            "vendored OD-practice roll captures operator concentration, so a "
            "national chain HHI is honestly omitted — the corpus deal history "
            "below is the real read. Note the managed-vision layer IS "
            "concentrated: VSP and EyeMed dominate the plan side."),
        consolidation=(
            "A mature retail-clinical roll-up. The model is buy-and-build: "
            "acquire independent OD practices, centralize optical buying "
            "(frames, lenses, labs), consolidate managed-vision contracting, "
            "layer in medical-optometry billing and equipment, and re-rate on "
            "scale. MyEyeDr, EyeCare Partners, and Acuity built national "
            "footprints this way; several first-generation platforms are on "
            "their second sponsor and carry meaningful leverage."),
        pe_activity=(
            "One of the more PE-active ambulatory verticals of the last decade "
            "— MyEyeDr (Goldman Sachs), EyeCare Partners (Partners Group), and "
            "Acuity Eyecare (among others) scaled aggressively. Diligence now "
            "centers on optical capture and average-order-value durability "
            "against online/DTC, managed-vision fee pressure, medical-optometry "
            "penetration, and OD recruitment/retention in a supply-tight "
            "market rather than pure location count."),
        notable_players=[
            "MyEyeDr (Goldman Sachs)", "EyeCare Partners (Partners Group)",
            "Acuity Eyecare Group", "National Vision Holdings (America's Best)",
            "Warby Parker", "EssilorLuxottica (LensCrafters / Pearle / EyeMed)",
            "VSP Vision (Marchon / managed-vision leader)",
            "Walmart / Costco / Target Optical (host-retail channel)",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Optical capture rate", "~50-70% of exams",
                "Share of exam patients who buy eyewear in-store; the single "
                "biggest driver of practice profit versus a bare exam."),
            Kpi("Average optical order value", "$200-450+ per pair",
                "Premium progressives, AR/blue-light, and specialty lenses lift "
                "the ticket; the materials margin is the engine."),
            Kpi("Materials (optical) share of revenue", "~50-65%",
                "Frames + lenses + contacts; the higher the optical mix, the "
                "more retail margin beyond the exam fee."),
            Kpi("Medical-optometry share of revenue", "practice-dependent",
                "Disease management billed to the medical benefit — the "
                "recurring, insurance-paid line that de-risks retail "
                "cyclicality."),
            Kpi("Exams / OD / day", "~12-20",
                "Exam throughput sets the top of the funnel; APP/technician "
                "leverage and pre-testing free the OD for medical work."),
            Kpi("Platform EBITDA margin (post-MSO)", "12-20% (illustrative)",
                "Retail-clinical hybrid; optical margin and buying scale push "
                "the top end, managed-vision mix pulls the bottom."),
        ],
        margin_profile=(
            "Vision economics are a retail P&L with a clinical front door. The "
            "exam fee — often plan-compressed — barely covers the OD's chair "
            "time; the profit is the optical dispensary, where frame, lens, and "
            "contact-lens materials carry retail gross margin and platform-scale "
            "buying (and owned surfacing labs) widen it further. Capture rate "
            "and average order value are therefore the master variables. The "
            "medical-optometry line adds a higher-quality, insurance-paid, "
            "recurring stream that smooths the retail cyclicality and is the "
            "premium a well-run platform earns. Scale spreads the MSO back "
            "office, concentrates managed-vision and frame-vendor negotiating "
            "leverage, and standardizes the optical merchandising — but the "
            "underlying quality of a vision platform is optical capture plus "
            "medical-optometry penetration against a rising online-materials "
            "leak."),
    ),
    risks=[
        Risk("Online / DTC materials substitution", "High",
             "1-800 Contacts, Warby Parker, and resupply apps strip optical "
             "margin once the mandated prescription release lets patients buy "
             "materials anywhere."),
        Risk("Managed-vision fee compression (VSP / EyeMed)", "High",
             "A concentrated plan layer sets thin exam fees and materials "
             "allowances; adverse contract terms hit both traffic and per-unit "
             "economics."),
        Risk("OD recruitment / retention in a supply-tight market", "Medium",
             "The selling and staff optometrists are the capacity; comp "
             "redesign missteps and a tight labor market cap chair time and "
             "volume."),
        Risk("Scope-of-practice stagnation (state legislature risk)", "Medium",
             "The medical-optometry upgrade thesis depends on state scope "
             "expansion that organized ophthalmology actively contests."),
        Risk("Consumer-discretionary cyclicality of optical", "Medium",
             "Eyewear is a partly-deferrable retail purchase; recessions push "
             "out replacement cycles and down-trade the ticket."),
        Risk("MPFS conversion-factor erosion (medical line)", "Medium",
             "A structural, no-inflation-update squeeze on the medical-optometry "
             "professional fee and ophthalmic-diagnostic codes."),
        Risk("Multiple compression on exit", "Medium",
             "Entry multiples rose across the cycle in a maturing, "
             "leverage-heavy roll-up."),
    ],
    diligence_questions=[
        "What is the optical capture rate and the average order value, by "
        "location, and how have both trended against online substitution?",
        "What is the revenue mix across managed-vision exam fees, cash optical, "
        "and medical-optometry — and how fast is the medical line growing?",
        "What are the VSP/EyeMed/Davis contract terms and panel dependence, "
        "and what share of traffic rides each plan?",
        "What is the online/DTC materials leakage (Rx released but bought "
        "elsewhere), and how is the platform defending the resupply annuity?",
        "What is the OD staffing model, comp structure, and recruitment "
        "pipeline in a supply-tight labor market?",
        "How exposed is the growth plan to state scope-of-practice expansion "
        "that has not yet passed?",
        "What is the optical buying scale (frame/lens vendor terms, owned lab), "
        "and how much margin is synergy versus organic?",
        "What is the host-retail vs independent-brand mix, and how durable are "
        "the sublease/host relationships?",
    ],
    insider_lens=[
        "The exam is the loss-leader; the optical is the business. An eye exam "
        "reimburses modestly, but it writes a prescription that becomes a "
        "frame-plus-lens-plus-contacts sale at retail margin. Capture rate and "
        "average order value — not exam volume — are what a vision platform is "
        "actually worth.",
        "Managed vision is a discount club, not health insurance. VSP and "
        "EyeMed pay a thin exam fee and a materials allowance; the panel brings "
        "the patient in the door but reprices the materials the practice would "
        "rather sell at full retail. Read the plan mix before you believe the "
        "revenue line.",
        "The prescription belongs to the patient — by law. The FTC eyeglass and "
        "contact-lens rules force the practice to release the Rx, which is "
        "exactly what lets 1-800 Contacts and Warby Parker capture the "
        "materials sale. The online leak is structural, not a market-share blip.",
        "Medical optometry is the quality upgrade. The differentiated practices "
        "bill Medicare and commercial medical benefits for dry eye, glaucoma "
        "monitoring, and diabetic-retinopathy screening — real recurring fees "
        "that turn a cyclical retail P&L into a healthcare annuity. Penetration "
        "of this line is the tell of a good platform.",
        "Scope-of-practice is legislated margin. Every state that grants "
        "optometrists broader therapeutic, laser, or injection authority "
        "enlarges the billable medical scope — and organized ophthalmology "
        "fights each bill. The growth plan quietly depends on statehouse "
        "outcomes.",
        "Don't confuse Vision with Ophthalmology. This is optometry and optical "
        "retail — refraction, eyewear, and disease monitoring. The surgical "
        "eye care (cataract, retina, LASIK, MIGS) and its ASC facility fees "
        "live in the ophthalmology roll-up; a platform that blends the two is "
        "underwriting two different businesses.",
    ],
    connections=default_connections(
        "vision",
        deals_sector="vision",
        extra_pages=[
            ("/industry/vision",
             "Industry deep-dive — vision deal history + optical-capture read"),
        ],
        connectors=[
            ("npi_provider_taxonomy",
             "NPI taxonomy — optometrist (OD) supply & practice enrollment"),
            ("npi_provider",
             "NPI registry — OD/optical practice locations for footprint "
             "mapping"),
            ("cms_open_data_mup_physician_by_provider_service",
             "Medicare physician utilization — medical-optometry E&M & "
             "ophthalmic-diagnostic volume"),
            ("open_payments_general_payments_2024",
             "Open Payments — device/contact-lens maker payments to eye-care "
             "providers"),
            ("census_acs_cbsa_profile",
             "Census ACS — CBSA age & income demographics for optical demand "
             "mapping"),
        ],
    ),
    sources=[
        Source("US Bureau of Labor Statistics — Occupational Employment & Wage "
               "Statistics, Optometrists (29-1041)", "GOV",
               "https://www.bls.gov/oes/current/oes291041.htm"),
        Source("FTC — Contact Lens Rule / Fairness to Contact Lens Consumers "
               "Act and the Eyeglass Rule", "GOV",
               "https://www.ftc.gov/legal-library/browse/rules/contact-lens-rule"),
        Source("CMS — Medicare Physician Fee Schedule annual Final Rule (medical "
               "eye-care E&M and ophthalmic-diagnostic codes)", "GOV",
               "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
        Source("American Optometric Association — optometry workforce and "
               "scope-of-practice data", "INDUSTRY",
               "https://www.aoa.org/"),
        Source("Peer-reviewed epidemiology — global myopia prevalence and "
               "projections (e.g. Holden et al., Ophthalmology)", "ACADEMIC",
               "https://www.aaojournal.org/"),
        Source("PE Desk industry deep-dive (vision) + realized-deal corpus",
               "INTERNAL",
               "/diligence/tam-sam?template=vision"),
    ],
    live_figures=live_figures_from_dive("vision"),
    trends=(
        "Vision was rolled up as a retail-clinical hybrid, not a classic "
        "physician specialty: platforms like MyEyeDr, EyeCare Partners, and "
        "Acuity acquired independent OD practices and monetized the optical "
        "dispensary — frames, lenses, and contact lenses — with the exam as the "
        "traffic driver. Three forces now shape the trajectory. First, the "
        "materials channel is leaking online: the FTC's mandated prescription "
        "release let 1-800 Contacts, Warby Parker, and resupply apps unbundle "
        "the eyewear and contact-lens sale from the exam, structurally "
        "pressuring the retail engine. Second, the managed-vision duopoly (VSP, "
        "EyeMed) keeps exam fees and materials allowances thin. Third, and "
        "offsetting, medical optometry is expanding: broader state scope-of- "
        "practice authority and an aging, myopic, screen-heavy population push "
        "optometrists into disease management billed to the medical benefit at "
        "real, recurring fees. Quality-of-earnings work now centers on optical "
        "capture and average-order-value durability, medical-optometry "
        "penetration, and OD retention in a supply-tight labor market — not "
        "location count."),
    growth_levers=[
        GrowthLever(
            "Medical-optometry mix shift",
            "Move revenue from thin managed-vision exam fees toward "
            "insurance-paid disease management (dry eye, glaucoma, diabetic "
            "screening) at real MPFS/commercial fees.",
            "+ recurring medical revenue", "ILLUSTRATIVE"),
        GrowthLever(
            "Optical capture + average-order-value",
            "Lift the share of exams that buy in-store and the ticket (premium "
            "progressives, AR/blue-light, specialty contacts) — the retail "
            "margin engine.",
            "primary margin lever", "ILLUSTRATIVE"),
        GrowthLever(
            "Aging + myopia demand",
            "Presbyopia in the 45+ population and rising myopia prevalence "
            "enlarge the refractive base and the myopia-management upsell.",
            "+ steady volume", "ACADEMIC"),
        GrowthLever(
            "Optical buying scale + owned labs",
            "Platform-scale frame/lens vendor terms and owned surfacing labs "
            "widen the materials margin on every pair.",
            "+ synergy margin", "ILLUSTRATIVE"),
        GrowthLever(
            "State scope-of-practice expansion",
            "Each state that grants broader therapeutic/laser/injection "
            "authority enlarges the billable medical scope.",
            "+ state-gated scope", "ILLUSTRATIVE"),
        GrowthLever(
            "Online/DTC substitution + managed-vision fee pressure",
            "Mandated Rx release leaks materials to online channels and the "
            "VSP/EyeMed duopoly compresses fees — the structural headwind.",
            "channel + rate headwind", "ILLUSTRATIVE"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Refractive + eye-disease demand (aging × myopia × screening)",
        analysis=(
            "The demand base is refractive error and, increasingly, ocular "
            "disease. Presbyopia arrives for essentially everyone in the 45+ "
            "window, driving progressive-lens demand and higher-value optical; "
            "myopia prevalence has risen toward ~40%+ of the population on "
            "near-work and screen time, enlarging the refractive base and "
            "opening a myopia-management line for children. Overlaid on this is "
            "the medical demand: diabetes and an aging population expand "
            "diabetic-retinopathy screening, glaucoma monitoring, and dry-eye "
            "management — the insurance-paid work that separates a differentiated "
            "practice from a pure optical shop. The genuine offset is channel, "
            "not demand: mandated prescription release lets patients satisfy the "
            "materials purchase online, so the practice must convert the exam "
            "into an in-store optical sale and grow the medical line to hold "
            "value per patient."),
        basis="ACADEMIC"),
    cost_drivers=[
        CostDriver(
            "Optical cost of goods (frames, lenses, contacts)",
            "~30-40% of cost",
            "The materials the dispensary sells; platform buying scale and "
            "owned surfacing labs are the primary lever on this line.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Optometrist + staff compensation", "~30-40% of cost",
            "OD chair time plus opticians, technicians, and front desk; the "
            "post-close comp model is the biggest retention risk.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Occupancy / retail real estate", "~10-15% of cost",
            "Optical retail is a location business — visible, trafficked space "
            "(or host-retail sublease) carries real rent.", "ILLUSTRATIVE"),
        CostDriver(
            "MSO back office (billing/RCM, managed-vision, IT)",
            "~8-12% of cost",
            "Shared services, managed-vision contracting/eligibility, and the "
            "medical-optometry billing apparatus.", "ILLUSTRATIVE"),
        CostDriver(
            "Diagnostic equipment + marketing", "~5-10% of cost",
            "OCT, fundus cameras, and visual-field units for medical optometry, "
            "plus the local marketing that drives exam traffic.",
            "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "No national OD-practice facility file is vendored — an optometry "
        "practice is a retail-clinical business, not a Medicare-certified "
        "facility — so state geography is omitted rather than fabricated. The "
        "most consequential geographic variables are state optometric "
        "scope-of-practice statutes (which states permit therapeutic, laser, "
        "and injection authority — the billable medical scope), the "
        "corporate-practice-of-medicine/optometry doctrine (strong-CPOM states "
        "force the friendly-entity/MSO structure), and the growing set of "
        "states enacting PE-in-healthcare transaction-review laws. The NPI "
        "taxonomy, Medicare physician-utilization, and demographic connectors "
        "linked below map optometrist supply and medical-eye-care volume "
        "against age and income — the honest footprint read."),
)

register(REPORT)
