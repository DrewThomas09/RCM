"""Physician Groups — the MSO/PPM physician-practice roll-up.

Deals-only deep-dive (no national physician-practice facility file; geography is
omitted rather than fabricated). The whole PE model is the friendly-PA / MSO
structure the corporate-practice-of-medicine doctrine forces, so the qualitative
sections are authored around the Medicare Physician Fee Schedule squeeze, the
comp-haircut value lever, ancillary capture, and the 1990s PPM cautionary tale.
Consumes ``physician_group_deep_dive()`` for SOURCED corpus deal figures.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="physician_group",
    name="Physician Groups",
    care_setting="Physician services",
    naics="6211",
    one_line_def=(
        "Multi-physician medical groups — independent practices and specialty "
        "platforms consolidated under a management services organization (MSO) "
        "that owns the non-clinical assets while a physician-owned professional "
        "corporation holds the clinical practice — reimbursed primarily through "
        "the Medicare Physician Fee Schedule and commercial multiples of it."),
    tam_headline=TamHeadline(
        value=978.0, unit="$B", growth_pct=5.5, basis_label="GOV",
        basis_note=(
            "US 'Physician and clinical services' spending was ~$978.0B in 2023 "
            "(CMS National Health Expenditure Accounts); the PE-addressable "
            "independent-group slice is a fraction of that total. Growth is the "
            "modeled composite of demographic volume, a flat MPFS professional "
            "fee, ancillary capture, and value-based upside."),
    ),
    executive_summary=[
        "The asset is the MSO, not the practice. Corporate practice of medicine "
        "(CPOM) bars lay/corporate ownership of a medical practice in roughly "
        "half the states, so PE buys through a friendly-PA structure — a "
        "management company owns everything non-clinical and takes a management "
        "fee; a physician-owned PC holds the licenses. Get the structure or the "
        "fee wrong and it is an existential legal and reimbursement risk.",
        "Value is created three ways: multiple arbitrage (buy small practices at "
        "4-6x, sell the platform at 10-14x), ancillary capture (imaging, labs, "
        "an ASC, infusion, pathology — margin the physician generated but did "
        "not own), and payer leverage (a bigger group negotiates better "
        "commercial rates). Same-store organic growth is usually the weakest "
        "lever.",
        "Revenue is the Medicare Physician Fee Schedule (MPFS) and commercial "
        "multiples of it. The conversion factor has been flat-to-declining in "
        "nominal terms for a decade while costs rise — a structural squeeze on "
        "the professional fee, with no market-basket inflation update, that "
        "pushes every platform toward ancillaries and value-based upside.",
        "Physician retention is the whole game. In a physician-practice "
        "management (PPM) deal the selling physicians ARE the EBITDA; rollover "
        "equity, employment agreements, non-competes, and the post-close "
        "compensation redesign (the 'comp haircut') decide whether volume and "
        "quality survive the transaction.",
        "The first PPM wave (1990s — PhyCor, MedPartners) collapsed under "
        "over-leverage, over-diversification, and physician misalignment. "
        "Today's wave is specialty-focused (derm, GI, ortho, cardiology, "
        "ophthalmology, urology) rather than multispecialty — a real "
        "improvement, but the same governance and alignment fault lines recur.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Patient access / referral (PCP or self-referral) → appointment",
            "Office visit / E&M encounter (history, exam, medical decision)",
            "Ancillaries ordered/performed in-house (imaging, lab, procedures)",
            "Charge capture + coding (E&M level, CPT, modifiers)",
            "Claim to payer (MPFS or commercial); patient cost-share",
            "Denials management, appeals, and collections (the RCM function)",
            "Value-based settlement (shared savings / capitation) where present",
        ],
        sites_of_care=[
            "Physician office / clinic (the core encounter)",
            "Owned ancillary sites (imaging suite, in-office lab, ASC, infusion)",
            "Hospital (inpatient rounding, surgery — the professional fee)",
            "Telehealth / virtual visits",
            "MSO shared-services center (billing, HR, IT, contracting)",
        ],
        money_flow=(
            "The group earns a professional fee for each encounter — an E&M or "
            "procedure code paid off the Medicare Physician Fee Schedule (RVUs "
            "× the Geographic Practice Cost Indices × the annual conversion "
            "factor) or a commercial multiple of it. Ancillaries the group owns "
            "— imaging, in-office lab, pathology, infusion, an ASC facility fee "
            "— are billed separately and usually carry higher margin than the "
            "visit itself; capturing that margin the physician already generated "
            "is the core PE value lever. In the PE structure the payer pays the "
            "physician-owned professional corporation, the PC pays the MSO a "
            "management fee for all non-clinical services, and the MSO is where "
            "the sponsor's economics sit. Increasingly a slice of revenue is "
            "value-based — shared savings, chronic-care-management (CCM/TCM) "
            "fees, or partial capitation — layered on the fee-for-service "
            "chassis."),
        key_players=(
            "Below the health systems, the payer-owned groups define the top of "
            "the market — Optum (UnitedHealth) is now the largest employer of "
            "US physicians. Among PE-backed specialty platforms: dermatology "
            "roll-ups under multiple sponsors, GI (GI Alliance, Gastro Health, "
            "One GI), orthopedics/MSK, cardiology (Cardiovascular Associates of "
            "America, US Heart & Vascular), ophthalmology (EyeCare Partners), "
            "urology (US Urology Partners, Solaris), ENT (SENTA), women's "
            "health, and primary care (agilon, Privia, apree). MSO enablers "
            "(Privia Health, Aledade) provide the platform without owning the "
            "practice. The acquirable pool is the independent single- and "
            "multi-specialty group long tail, richest in ancillary-heavy "
            "specialties."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Physician & clinical services (NHE 2023)", "~$978.00B",
                    "GOV · CMS National Health Expenditure Accounts"),
            Segment("Medicare Part B physician services spending",
                    "~$90B+ / yr", "GOV · MedPAC physician-services chapter"),
            Segment("Largest US physician employer (Optum)",
                    "~90,000 employed/affiliated MDs",
                    "INDUSTRY · UnitedHealth disclosures (directional)"),
            Segment("Independent-physician share of the workforce",
                    "below half and falling",
                    "INDUSTRY · AMA Physician Practice Benchmark (directional)"),
            Segment("PE-backed physician-platform add-ons",
                    "hundreds per year at cycle peak",
                    "ILLUSTRATIVE · industry deal tracking, directional"),
        ],
        growth_drivers=[
            "Demographic demand + aging lift encounter volume ~1.5-2.0%/yr",
            "MPFS conversion factor flat-to-declining — a structural rate drag",
            "Ancillary capture (imaging, labs, ASC, infusion) — the margin lever",
            "Consolidation multiple arbitrage — buy small, sell the platform",
            "Value-based upside (shared savings, capitation) layered on FFS",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Commercial": 0.50,
            "Medicare / MA": 0.35,
            "Medicaid": 0.10,
            "Self-pay / other": 0.05,
        },
        rate_mechanics=[
            "Medicare Physician Fee Schedule (MPFS) — payment = RVUs (work + "
            "practice-expense + malpractice) × Geographic Practice Cost Indices "
            "× the annual conversion factor; the CF (~$32-33) is the political "
            "battleground and roughly flat/declining for a decade.",
            "Budget neutrality — MPFS is statutorily budget-neutral, so an RVU "
            "increase for one service forces offsetting cuts elsewhere (the "
            "fight over the G2211 E&M add-on is the archetype).",
            "Site-of-service differential — the same code pays more in the "
            "non-facility (office) setting, where the practice bears the "
            "practice-expense overhead, than when performed in a facility.",
            "Commercial multiple of Medicare — contracts as a percent of "
            "Medicare or a fee schedule; scale drives negotiating leverage.",
            "Incident-to and shared-visit billing — NP/PA services billed under "
            "the physician at 100% vs 85% — a margin and compliance lever.",
            "Ancillary / technical-component billing — imaging TC, in-office "
            "lab, pathology, and infusion buy-and-bill billed separately from "
            "the professional fee.",
            "Value-based overlays — MSSP/ACO shared savings, MIPS/APM "
            "adjustments, CCM/TCM care-management codes, and partial capitation.",
        ],
        reimbursement_risk=(
            "The structural risk is the MPFS conversion factor, which has been "
            "flat-to-declining in nominal terms while the Medicare Economic "
            "Index (practice cost) rises — a slow annual squeeze on the "
            "professional fee with no inflation-update mechanism, unlike the "
            "hospital and SNF market-basket updates. Budget neutrality means "
            "every RVU win is somebody's cut. Commercial rate durability is the "
            "swing factor: the whole consolidation thesis assumes a bigger group "
            "extracts better commercial rates, which invites payer pushback, "
            "narrow networks, and antitrust scrutiny of physician-market "
            "concentration. Layer on the site-of-service / site-neutral debate, "
            "MPFS misvaluation fights, and documentation/coding audits (E&M "
            "levels, incident-to, modifier 25), and the professional-fee line is "
            "under persistent pressure — which is exactly why platforms lean on "
            "ancillaries and value-based upside."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("Corporate Practice of Medicine (CPOM) doctrine (state law)",
                 "Bars lay/corporate ownership of a medical practice in ~half "
                 "the states; forces the friendly-PA/MSO structure the entire PE "
                 "model rides on.",
                 None),
            Rule("Medicare Physician Fee Schedule (annual Final Rule)",
                 "Sets the RVUs, the conversion factor, and budget neutrality — "
                 "the price of the professional fee.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
            Rule("Physician self-referral law (Stark, 42 CFR 411.350+)",
                 "Governs referrals to owned ancillaries (imaging, lab, PT, "
                 "ASC); the in-office ancillary-services exception is what makes "
                 "ancillary capture legal.",
                 "https://www.cms.gov/medicare/regulations-guidance/physician-self-referral"),
            Rule("Anti-Kickback Statute (42 USC 1320a-7b)",
                 "Governs compensation, MSO management fees, and referral "
                 "relationships; fair-market-value and commercial-reasonableness "
                 "are diligence gates.",
                 "https://oig.hhs.gov/compliance/safe-harbor-regulations/"),
            Rule("MACRA / Quality Payment Program (MIPS & Advanced APMs)",
                 "Ties a slice of MPFS payment to quality/cost performance and "
                 "pushes groups toward value-based models.",
                 "https://qpp.cms.gov/"),
            Rule("FTC/DOJ + state review of physician-practice consolidation",
                 "Scrutiny of roll-up-driven commercial-rate concentration, "
                 "including serial sub-HSR-threshold acquisitions and state "
                 "PE-in-healthcare transaction-review laws.",
                 "https://www.ftc.gov/"),
        ],
        policy_watch=[
            "Annual MPFS conversion-factor cuts and the perennial 'doc fix' "
            "congressional patches",
            "MACRA APM incentive expiration and MIPS reform",
            "FTC scrutiny of PE physician roll-ups + state PE-transaction-review "
            "laws (CA, MA, OR, and others)",
            "Site-neutral / site-of-service payment moving office ancillaries "
            "toward equalized rates",
            "Corporate-practice-of-medicine enforcement and MSO-structure "
            "challenges",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "US physician supply is still highly fragmented — a large share of "
            "physicians practice in small independent groups — but the "
            "independent share has fallen below half as hospitals, payers "
            "(Optum), and PE platforms employ or affiliate more physicians. The "
            "acquirable pool is the independent single- and multi-specialty "
            "group long tail, richest in ancillary-heavy specialties."),
        hhi_or_share=(
            "No single owner is dominant nationally, but Optum (UnitedHealth) is "
            "now the largest employer of US physicians (~90,000 employed/"
            "affiliated), and hospital employment plus PE platforms have pushed "
            "the independent-physician share under 50%. No vendored "
            "physician-practice roll captures operator concentration, so a chain "
            "HHI is honestly omitted."),
        consolidation=(
            "Two structural buyers — health systems (vertical, outpatient "
            "capture) and payers (Optum's value-based play) — compete with PE "
            "specialty platforms. PE's model is specialty-specific buy-and-"
            "build: acquire an anchor group, tuck in independents at lower "
            "multiples, centralize the MSO back office, add ancillaries, and "
            "re-rate the platform. Dermatology and GI led; ortho, cardiology, "
            "urology, ophthalmology, ENT, women's health, and primary care "
            "followed."),
        pe_activity=(
            "One of the most PE-active healthcare categories of the last "
            "decade, now maturing — many first-generation platforms are on their "
            "second or third sponsor (secondary buyouts), and exits increasingly "
            "go platform-to-platform or to strategics/payers. Scrutiny has risen "
            "with scale: FTC challenges, state transaction-review laws, and "
            "press attention on comp haircuts and quality make governance and "
            "physician alignment the underwriting centerpiece."),
        notable_players=[
            "Optum Health (UnitedHealth)", "agilon health", "Privia Health",
            "Aledade", "GI Alliance", "EyeCare Partners",
            "US Urology Partners", "US Orthopaedic Partners",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Physician compensation (% of net revenue)", "40-55%+",
                "The dominant cost line — 'margin' is what is left after the "
                "physicians are paid, so the post-close comp model is the deal."),
            Kpi("Ancillary revenue (% of total)", "15-40%",
                "Imaging/lab/ASC/infusion — the higher the share, the more "
                "platform value beyond the professional fee."),
            Kpi("Provider productivity (wRVUs / physician / yr)",
                "specialty-dependent",
                "The throughput metric, benchmarked against MGMA — the volume "
                "engine behind the professional fee."),
            Kpi("Net collections rate", "95-98% of contractual",
                "RCM quality; every point of leakage is pure margin loss."),
            Kpi("Commercial vs Medicare mix", "higher commercial = higher yield",
                "Commercial pays a multiple of Medicare, so payer mix drives "
                "realized revenue per RVU."),
            Kpi("Platform EBITDA margin (post-MSO)", "12-20% (illustrative)",
                "After physician compensation; ancillary-rich specialties run "
                "higher, thin-ancillary primary care lower."),
        ],
        margin_profile=(
            "A physician group's economics are dominated by provider "
            "compensation — often 40-55%+ of net revenue — so 'margin' is really "
            "what is left after the physicians are paid. That is why the "
            "post-close compensation redesign (moving selling physicians from an "
            "eat-what-you-kill draw onto a market salary plus productivity, with "
            "the spread accruing to the platform) is the single biggest EBITDA "
            "lever and the single biggest retention risk. Above that base, "
            "ancillary services (imaging, lab, pathology, infusion, an ASC "
            "facility fee) carry higher incremental margin and are why "
            "ancillary-rich specialties command premium multiples. Scale spreads "
            "the MSO back office (billing, contracting, IT, compliance) but does "
            "not change the fundamental fact that the doctors generate — and "
            "largely consume — the revenue."),
    ),
    risks=[
        Risk("MPFS conversion-factor erosion + budget neutrality", "High",
             "Structural, with no inflation update; the professional fee is "
             "squeezed every year, and RVU wins are offset by cuts elsewhere."),
        Risk("Physician retention / comp-haircut backlash", "High",
             "Selling physicians are the EBITDA; a botched post-close comp "
             "redesign drives defection, volume loss, and quality erosion."),
        Risk("Corporate-practice / MSO-structure & regulatory challenge",
             "High",
             "A misstructured friendly-PA or a non-FMV management fee is an "
             "existential legal/reimbursement risk; state PE-transaction review "
             "is rising."),
        Risk("Commercial-rate / payer pushback + antitrust", "Medium",
             "The consolidation-leverage thesis invites narrow networks, rate "
             "cuts, and FTC/state scrutiny of physician-market concentration."),
        Risk("Ancillary / site-of-service repricing (Stark, site-neutral)",
             "Medium",
             "The ancillary margin lever depends on the in-office ancillary "
             "exception and the office-rate premium — both under policy review."),
        Risk("Multiple compression on exit", "Medium",
             "Entry multiples rose across the cycle; a maturing market and "
             "higher rates pressure the arbitrage the thesis is priced on."),
        Risk("Coding / audit exposure (E&M, incident-to, modifier 25)",
             "Medium",
             "Documentation and NPP-billing compliance drive recoupment risk "
             "under payer and CMS audit."),
    ],
    diligence_questions=[
        "Is the friendly-PA/MSO structure sound in every state of operation, "
        "and is the management fee at fair market value and commercially "
        "reasonable?",
        "What is the post-close physician compensation model, and how much "
        "projected EBITDA depends on the comp haircut versus organic growth?",
        "How concentrated are revenue and referrals in the top physicians, and "
        "what are their ages, rollover equity, employment terms, and "
        "non-competes?",
        "What share of EBITDA is ancillary (imaging/lab/ASC/infusion), and how "
        "exposed is it to Stark and site-of-service repricing?",
        "What is the payer mix and commercial-rate position, and how durable "
        "are the top commercial contracts?",
        "What is the same-store organic growth excluding acquisitions and the "
        "comp restructuring?",
        "What is the coding/documentation compliance posture (E&M levels, "
        "incident-to, modifier 25) and the audit history?",
        "How much of the value plan is multiple arbitrage versus real "
        "operational improvement, and what does the exit universe look like?",
    ],
    insider_lens=[
        "The comp haircut IS the deal. Most platform EBITDA is manufactured by "
        "moving selling physicians off their historical take-home onto a market "
        "salary; the spread is the sponsor's margin — and the moment doctors "
        "feel it, retention and volume are at risk. Underwrite the physicians' "
        "post-close motivation, not just the pro forma.",
        "You are buying an MSO, not a practice. Because of corporate practice of "
        "medicine, the sponsor never owns the medical practice — it owns a "
        "management company that contracts with a physician-owned PC. If that "
        "structure or the management fee is off, the whole thing is legally and "
        "reimbursement-wise fragile.",
        "Ancillaries are where the real money hides. The visit is a thin "
        "professional fee; the imaging, lab, pathology, infusion, and ASC the "
        "physician orders are the margin. A platform's quality is largely 'how "
        "much ancillary can we legally capture that the doctor was already "
        "generating.'",
        "The 1990s PPM wave died for reasons that still apply. PhyCor and "
        "MedPartners over-levered, over-diversified into multispecialty, and "
        "misaligned physicians. Today's specialty-focused version is a real "
        "improvement, but governance, alignment, and integration discipline are "
        "the same fault lines.",
        "The MPFS has no inflation update. Unlike hospitals and SNFs, physicians "
        "get no market-basket increase — the conversion factor is set by "
        "Congress and has drifted down in real terms for years. Every platform's "
        "base professional fee is on a slow downward escalator, which is why "
        "value-based upside and ancillaries are not optional.",
    ],
    connections=default_connections(
        "physician_group",
        deals_sector="physician_group",
        extra_pages=[
            ("/industry/physician_group",
             "Industry deep-dive — physician-group deal history + structure"),
        ],
        connectors=[
            ("npi_provider_taxonomy",
             "NPI taxonomy — physician specialty mix & practice enrollment"),
            ("cms_open_data_mup_physician_by_provider_service",
             "Medicare physician utilization & allowed charges by service "
             "(fee-schedule read)"),
            ("cms_open_data_mup_physician_by_geo_service",
             "Medicare physician service variation by geography"),
            ("open_payments_general_payments_2024",
             "Open Payments — industry payments to physicians (relationship "
             "screen)"),
            ("census_acs_cbsa_profile",
             "Census ACS — CBSA demographics for demand mapping"),
        ],
    ),
    sources=[
        Source("CMS — National Health Expenditure Accounts (physician & "
               "clinical services)", "GOV",
               "https://www.cms.gov/data-research/statistics-trends-and-reports/national-health-expenditure-data"),
        Source("CMS — Medicare Physician Fee Schedule annual Final Rule (RVUs, "
               "conversion factor, budget neutrality)", "GOV",
               "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
        Source("MedPAC — Report to Congress, physician and other health "
               "professional services chapter", "GOV",
               "https://www.medpac.gov/"),
        Source("Physician self-referral law (Stark, 42 CFR 411.350+)", "GOV",
               "https://www.cms.gov/medicare/regulations-guidance/physician-self-referral"),
        Source("FTC — policy and enforcement on physician-practice "
               "consolidation and serial acquisitions", "GOV",
               "https://www.ftc.gov/"),
        Source("AMA — Physician Practice Benchmark Survey (employment vs "
               "ownership trends)", "INDUSTRY",
               "https://www.ama-assn.org/"),
        Source("PE Desk industry deep-dive (physician_group) + realized-deal "
               "corpus", "INTERNAL",
               "/diligence/tam-sam?template=physician_group"),
    ],
    live_figures=live_figures_from_dive("physician_group"),
    trends=(
        "Physician-practice consolidation was one of the defining PE healthcare "
        "trades of the last decade, and it ran in two acts. The first PPM wave "
        "of the 1990s — PhyCor, MedPartners, and multispecialty roll-ups — "
        "collapsed under over-leverage, over-diversification, and misaligned "
        "physicians. The current wave learned the lesson and went "
        "specialty-specific: dermatology and gastroenterology led, then "
        "orthopedics, cardiology, urology, ophthalmology, ENT, women's health, "
        "and primary care, each betting on ancillary-rich economics and tighter "
        "structure. Meanwhile two other buyers reshaped the landscape — health "
        "systems employing physicians for outpatient capture, and payers (Optum "
        "became the largest US physician employer) buying groups to power "
        "value-based care — pushing the independent-physician share below half. "
        "The forward tension is policy and maturity: the MPFS conversion factor "
        "keeps drifting down in real terms with no inflation update, the FTC and "
        "a growing list of states are scrutinizing roll-ups and serial "
        "acquisitions, and many first-generation platforms are now trading "
        "sponsor-to-sponsor, putting governance, physician alignment, and "
        "durable ancillary economics — not multiple arbitrage — at the center "
        "of the thesis."),
    growth_levers=[
        GrowthLever(
            "Multiple arbitrage (buy small, sell the platform)",
            "Acquire independent practices at 4-6x and re-rate the aggregated "
            "platform at 10-14x on scale, ancillaries, and payer leverage.",
            "primary", "ILLUSTRATIVE"),
        GrowthLever(
            "Comp-haircut EBITDA capture",
            "Move selling physicians from historical take-home onto a market "
            "salary plus productivity; the spread accrues to the MSO.",
            "large / retention-gated", "ILLUSTRATIVE"),
        GrowthLever(
            "Ancillary capture (imaging, lab, ASC, infusion)",
            "Own the higher-margin services the physician already orders — the "
            "durable, non-arbitrage margin lever.",
            "+ ancillary margin", "ILLUSTRATIVE"),
        GrowthLever(
            "Payer-rate leverage from scale",
            "A larger group negotiates better commercial rates — the "
            "consolidation-leverage thesis (and the antitrust risk).",
            "+ commercial yield", "ILLUSTRATIVE"),
        GrowthLever(
            "Demographic encounter volume",
            "Aging and prevalence lift underlying visit and procedure volume.",
            "+1.5-2.0%/yr volume", "GOV"),
        GrowthLever(
            "MPFS conversion-factor drag",
            "A flat-to-declining professional fee with no inflation update is a "
            "structural headwind that ancillaries must outrun.",
            "rate headwind", "GOV"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Demographic demand × the independent-to-consolidated shift",
        analysis=(
            "The underlying demand driver is demographic — an aging, "
            "higher-prevalence population lifts office-visit and procedure "
            "volume at a low-single-digit annual rate, and that base demand is "
            "non-discretionary for chronic and procedural care. But for a "
            "physician-platform thesis the more important 'volume' driver is "
            "structural: the migration of physicians from independent practice "
            "into consolidated platforms (PE, hospital, or payer). That shift is "
            "what creates the acquirable pipeline and the scale on which "
            "ancillary capture and payer leverage operate. The critical honesty "
            "check is that a platform's headline growth is mostly acquired "
            "volume and comp restructuring, not organic same-store growth — so "
            "isolating true organic growth is the first diligence move."),
        basis="GOV"),
    cost_drivers=[
        CostDriver(
            "Physician & advanced-practice compensation", "~40-55% of cost",
            "The dominant cost by far; the post-close comp model is both the "
            "biggest margin lever and the biggest retention risk.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Clinical & office support staff (MAs, nurses, front office)",
            "~15-20% of cost",
            "The labor that runs the clinic and the ancillaries; a fixed cost "
            "scale spreads.", "ILLUSTRATIVE"),
        CostDriver(
            "Ancillary cost of goods (imaging, lab, infusion drugs, supplies)",
            "variable / specialty-driven",
            "The cost side of the margin-differentiating ancillaries — "
            "buy-and-bill drugs and imaging capital scale with the service mix.",
            "ILLUSTRATIVE"),
        CostDriver(
            "MSO back office (billing/RCM, IT, contracting, compliance)",
            "~10-15% of cost",
            "The shared-services chassis the platform centralizes; the "
            "scale-economies line, plus the compliance/legal apparatus the "
            "structure requires.", "ILLUSTRATIVE"),
        CostDriver(
            "Facility, occupancy & malpractice", "~8-12% of cost",
            "Clinic real estate, equipment, and professional-liability "
            "coverage.", "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "No national physician-practice facility file is vendored — a medical "
        "group is a business, not a Medicare-certified facility — so state "
        "geography is omitted rather than fabricated. The single most "
        "consequential geographic variable is the corporate-practice-of-"
        "medicine doctrine: strong-CPOM states (California, Texas, New York, and "
        "others) force the friendly-PA/MSO structure and shape how a deal can be "
        "papered, while lax-CPOM states allow more direct employment. A second "
        "variable is the growing list of states (California, Massachusetts, "
        "Oregon, and more) enacting PE-in-healthcare transaction-review laws. "
        "The NPI, Medicare physician-utilization, and demographic connectors "
        "linked below map physician supply and service volume against demand — "
        "the honest footprint read."),
)

register(REPORT)
