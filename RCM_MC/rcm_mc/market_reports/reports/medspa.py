"""Medspa — cash-pay medical aesthetics (injectables, energy devices, body).

Deals-only pattern (no vendored facility file — AmSpa's location census is
proprietary). The defining feature of the whole subsector is that there is NO
payer: med-spa services are elective, self-pay consumer purchases, so this
dossier is authored around discretionary demand, the injectable annuity, the
Corporate-Practice-of-Medicine (CPOM) structure, and the roll-up graveyard.
Live SOURCED figures come from ``medspa_deep_dive()`` (the realized-deal corpus)
when present; geography is honestly omitted, not fabricated.
"""
from __future__ import annotations

from .. import (
    Competition, CostDriver, GrowthLever, HowItWorks, Kpi, MarketReport,
    MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment, Source,
    TamHeadline, UnitEconomics, VolumeDriver, default_connections,
    live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="medspa",
    name="Medspa",
    care_setting="Ambulatory",
    naics="812199",
    one_line_def=(
        "Elective, cash-pay medical aesthetics — neurotoxins (Botox/Dysport), "
        "dermal fillers, energy-based skin and laser treatments, and body "
        "contouring — delivered by injectors (RNs/NPs/PAs) under physician "
        "oversight in a retail-style clinic. A consumer business wearing a "
        "medical coat, with no third-party payer."),
    tam_headline=TamHeadline(
        value=17.0, unit="$B", growth_pct=12.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "Modeled US medical-aesthetics / med-spa services revenue. Industry "
            "trackers (AmSpa state-of-the-industry, aesthetics market "
            "aggregators) put it in the mid-teens $B growing low-double-digits; "
            "this is an ILLUSTRATIVE industry-anchored figure, not a filed "
            "government number — there is no CMS spend line for cash-pay "
            "cosmetics."),
    ),
    executive_summary=[
        "There is no payer. Med-spa services are elective, self-pay consumer "
        "purchases — no Medicare, no Medicaid, minimal insurance. That is the "
        "defining fact: no denials or AR, but also no price floor and 100% "
        "exposure to discretionary consumer spending. Underwrite it like a "
        "premium consumer brand, not a healthcare provider.",
        "The asset is the injectable annuity, not the lasers. Neurotoxins and "
        "fillers rebook every ~3-4 months and carry high gross margin; "
        "laser/body-contouring is episodic and price-shopped. Recurring "
        "injectable + membership revenue is the quality-of-earnings tell.",
        "Corporate Practice of Medicine (CPOM) is the structural gate. Most "
        "states bar lay/PE ownership of the medical entity, so platforms run "
        "through an MSO plus a 'friendly' physician-owned PC, and scope-of-"
        "practice rules on who may inject vary state by state — the legal "
        "structure is diligence item #1.",
        "The injectors ARE the goodwill. RN/NP injectors own the client "
        "relationship and are highly mobile; a top injector leaving can take a "
        "book of business across the street, so retention and non-competes "
        "matter more than the buildout.",
        "The roll-up graveyard is real. Thousands of single sites, near-zero "
        "entry barriers, and brand-fickle demand have repeatedly humbled PE "
        "platforms — Ideal Image filed Chapter 11 in 2024. Discretionary + "
        "provider-dependent + locally price-competitive is hard to compound.",
        "Manufacturer loyalty programs quietly run the funnel. AbbVie's Allē "
        "and Galderma's ASPIRE lock patients to brands and rebate the practice; "
        "a change in those economics moves both traffic and injectable margin.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Consumer marketing / social lead-gen → booked consultation",
            "Good-faith exam by physician/NP (state-required) + treatment plan",
            "Procedure by the injector (neurotoxin / filler / laser / body)",
            "Membership or loyalty-program enrollment (Allē / ASPIRE)",
            "Rebooking cadence — neurotoxin ~every 3-4 months",
            "Retail skincare + package attach (higher ticket, deferred revenue)",
            "Referral / review flywheel back into the marketing funnel",
        ],
        sites_of_care=[
            "Standalone med spa (the archetype)",
            "Dermatology / plastic-surgery practice ancillary program",
            "Branded national chain / franchise location",
            "Inside gyms, salons, or wellness centers (co-located)",
            "Mobile / pop-up injectables (event-driven)",
        ],
        money_flow=(
            "Cash at the point of service — card, occasionally HSA/FSA (though "
            "purely cosmetic services are generally NOT HSA/FSA-eligible), and "
            "third-party patient financing (CareCredit, Cherry, PatientFi) for "
            "bigger tickets. There is no third-party payer adjudication, so "
            "revenue is recognized at service with no AR aging and no denials. "
            "Manufacturer loyalty/rebate programs (AbbVie/Allergan's Allē, "
            "Galderma's ASPIRE, Merz) rebate the patient to drive brand choice "
            "and pass volume rebates to the practice that lower injectable "
            "COGS. Prepaid packages and monthly memberships convert episodic "
            "demand into deferred/recurring revenue — and a deferred-revenue "
            "liability the balance sheet carries."),
        key_players=(
            "Upstream, a concentrated set of drug/device makers set the demand "
            "funnel: AbbVie/Allergan Aesthetics (Botox, Juvederm, CoolSculpting), "
            "Galderma (Dysport, Restylane, Sculptra), Merz (Xeomin, Radiesse), "
            "and Revance (Daxxify). Downstream is a vast, fragmented operator "
            "base — single-physician sites, dermatology/plastic-surgery groups, "
            "and national chains (LaserAway, SkinSpirit, Milan Laser, Ever/Body, "
            "and the bankrupt Ideal Image) — most running on an MSO/friendly-PC "
            "structure to satisfy Corporate Practice of Medicine."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Neurotoxins (Botox / Dysport / Xeomin / Daxxify)",
                    "largest injectable category",
                    "INDUSTRY · aesthetics market trackers"),
            Segment("Dermal fillers (HA + biostimulators)",
                    "second injectable category",
                    "INDUSTRY · aesthetics market trackers"),
            Segment("Energy-based / laser & skin (LHR, RF, IPL, resurfacing)",
                    "large episodic category",
                    "INDUSTRY · device & procedure trackers"),
            Segment("Body contouring (cryolipolysis / muscle stim)",
                    "capex-heavy, discretionary",
                    "INDUSTRY · device & procedure trackers"),
            Segment("Memberships + retail skincare attach",
                    "the recurring / annuity layer",
                    "ILLUSTRATIVE · operator revenue mix"),
        ],
        growth_drivers=[
            "Mainstreaming of 'tweakments' — wider, younger, more male client base",
            "New molecules (longer-acting Daxxify, new biostimulator fillers)",
            "Membership / subscription conversion of episodic demand",
            "GLP-1 weight-loss as a new high-ticket cash service line",
            "RN/NP injector supply growth enabling more sites",
            "Consumer disposable income / confidence — a driver AND a risk",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Self-pay (cash / card)": 0.90,
            "Third-party patient financing": 0.08,
            "Insurance (medical-derm overlap only)": 0.02,
        },
        rate_mechanics=[
            "No fee schedule — the operator sets price: per-unit neurotoxin, "
            "per-syringe filler, per-treatment or per-package laser, and "
            "monthly memberships. Price is a marketing decision, not a payer "
            "rate.",
            "Manufacturer loyalty & rebate programs (Allē, ASPIRE, Merz) — "
            "patient rebates drive brand choice; practice volume rebates lower "
            "injectable COGS and swing gross margin.",
            "Packages & memberships — prepaid packages and subscriptions turn "
            "episodic demand into deferred/recurring revenue (and a deferred-"
            "revenue liability).",
            "Patient financing (CareCredit, Cherry, PatientFi) — extends ticket "
            "size for lasers/body contouring; the practice absorbs a merchant "
            "discount.",
            "Cosmetic services are generally NOT insurance-reimbursed and NOT "
            "HSA/FSA-eligible — there is no payer to deny, and no payer floor "
            "on price.",
        ],
        reimbursement_risk=(
            "The 'reimbursement risk' here is really demand and pricing risk. "
            "With no payer, revenue is fully exposed to consumer discretionary "
            "spending and local competition, and price is easily undercut "
            "(Groupon-ization, franchise price wars) because entry barriers are "
            "trivial. Manufacturer rebate-program changes move injectable "
            "margin directly. And because there is no insurance adjudication, "
            "revenue quality is a function of membership retention and "
            "rebooking cadence — not payer mix — so the diligence is same-store "
            "recurring revenue, not a payer contract."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("Corporate Practice of Medicine (CPOM) doctrine",
                 "State law in most states bars lay/PE ownership of the medical "
                 "practice, forcing an MSO + 'friendly' physician-owned PC "
                 "structure. A defective structure is an existential legal and "
                 "tax problem hiding under good margins.",
                 "https://www.ama-assn.org/"),
            Rule("Scope of practice & physician supervision (state boards)",
                 "Who may inject or fire a laser — and the required physician "
                 "oversight and good-faith exam — varies materially by state "
                 "medical and nursing board rules.",
                 None),
            Rule("FDA regulation of neurotoxins, fillers & energy devices",
                 "Neurotoxins/fillers are regulated drugs/biologics; lasers and "
                 "RF are 510(k)/PMA devices. Off-label promotion and counterfeit "
                 "or gray-market product are enforcement risks.",
                 "https://www.fda.gov/medical-devices"),
            Rule("FTC advertising & consumer-protection rules",
                 "Cosmetic claims, before/after imagery, and financing "
                 "disclosures are FTC-regulated — a consumer-marketing "
                 "compliance surface, not a clinical one.",
                 "https://www.ftc.gov/business-guidance/advertising-marketing"),
            Rule("State med-spa statutes (e.g., Florida 2024 law)",
                 "A growing set of states impose med-spa-specific ownership, "
                 "supervision, and adverse-event rules — the regulatory drift "
                 "is toward tighter, not looser, supervision.",
                 None),
        ],
        policy_watch=[
            "More states passing med-spa-specific supervision / ownership laws",
            "Scope-of-practice expansion (or restriction) for NP/PA injectors",
            "FDA action on counterfeit / gray-market neurotoxin & filler supply",
            "GLP-1 weight-loss lines pulling med spas into prescribing risk",
            "Consolidation of loyalty-program economics by AbbVie / Galderma",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Extremely fragmented — thousands of single-site med spas plus "
            "dermatology and plastic-surgery ancillary programs. Entry barriers "
            "are trivial (a lease, a laser, an injector), which keeps the "
            "market atomized, locally price-competitive, and hard to "
            "differentiate."),
        hhi_or_share=(
            "No national operator holds meaningful share — the top chains are "
            "low-single-digit percentages of locations. AmSpa's location census "
            "is proprietary and not vendored, so share is honestly unquantified; "
            "fragmentation is the structure."),
        consolidation=(
            "PE has chased roll-ups, but the graveyard is instructive: Ideal "
            "Image filed Chapter 11 in 2024. Scaling a discretionary, provider-"
            "dependent, brand-fickle, locally price-competitive service has "
            "repeatedly disappointed. SkinSpirit (backed), LaserAway, Milan "
            "Laser (laser hair removal, more repeatable), and dermatology-DSO "
            "formats are the live attempts."),
        pe_activity=(
            "Active but humbled. The thesis is recurring injectable + "
            "membership revenue plus MSO scale on marketing and purchasing; the "
            "reality is customer-acquisition cost, injector turnover, and same-"
            "store discretionary cyclicality. Injectable-heavy, membership-"
            "heavy, physician-anchored formats travel better than laser-package "
            "'deal' formats."),
        notable_players=[
            "LaserAway", "SkinSpirit", "Milan Laser", "Ideal Image (Ch. 11, 2024)",
            "Ever/Body", "Advanced Dermatology & Cosmetic Surgery",
            "AbbVie / Allergan Aesthetics", "Galderma", "Merz", "Revance",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Revenue / treatment room / day", "utilization-driven",
                "Throughput of the injector and the room is the operating "
                "leverage; empty chairs kill the fixed-cost base."),
            Kpi("Injectable gross margin (net of rebates)", "55-70%",
                "Neurotoxin/filler COGS net of manufacturer rebates — the "
                "highest-margin, most-repeatable revenue."),
            Kpi("Recurring (membership + injectable) mix", "the annuity",
                "Share of revenue that rebooks — the quality-of-earnings a "
                "buyer actually pays for."),
            Kpi("Rebooking cadence (neurotoxin)", "~every 3-4 months",
                "The frequency that turns a trial into a habit — the engine of "
                "recurring revenue."),
            Kpi("Customer acquisition cost & conversion", "the swing factor",
                "Discretionary demand is bought; CAC and lead-to-treatment "
                "conversion separate site-level from corporate margin."),
            Kpi("Provider productivity & retention", "$/injector/hr",
                "Injectors are mobile and own the client relationship; "
                "productivity and tenure drive both revenue and goodwill."),
        ],
        margin_profile=(
            "Mature single sites can run attractive contribution margins "
            "because injectables are high-gross-margin and largely variable-"
            "cost. But corporate EBITDA is eaten by marketing/CAC, provider "
            "comp (often a percentage of collections), and MSO overhead. The "
            "winners convert episodic laser/package buyers into a membership + "
            "injectable annuity; the losers compete on price and churn both "
            "clients and injectors. Ranges are ILLUSTRATIVE — confirm against "
            "the target's own P&L and its deferred-revenue schedule."),
    ),
    risks=[
        Risk("Discretionary-demand cyclicality", "High",
             "No payer floor — recession or a consumer-confidence dip cuts "
             "revenue directly and immediately."),
        Risk("CPOM / scope-of-practice / structure risk", "High",
             "MSO / friendly-PC structures and state supervision rules; a "
             "defective structure is an existential legal and tax problem."),
        Risk("Injector retention / key-person risk", "High",
             "Injectors own the client relationship and are mobile; a departure "
             "can move a book of business across the street."),
        Risk("Brand / manufacturer & rebate-program dependence", "Medium",
             "Loyalty economics and product supply concentrate in AbbVie and "
             "Galderma; program changes move traffic and margin."),
        Risk("Price competition / commoditization", "Medium",
             "Near-zero entry barriers, Groupon-ization, and franchise price "
             "wars compress ticket and margin."),
        Risk("GLP-1 / new service-line & adverse-event exposure", "Medium",
             "Weight-loss injectables and counterfeit product add revenue but "
             "prescribing, sourcing, and liability risk."),
    ],
    diligence_questions=[
        "What is the recurring (membership + injectable rebooking) revenue mix, "
        "and what is same-store growth ex-new-units and ex-price?",
        "How is the entity structured for CPOM (MSO / friendly-PC), and does it "
        "survive the target states' ownership and supervision rules?",
        "Who are the top injectors, what share of revenue do they control, and "
        "what are their comp, non-competes, and tenure?",
        "What is injectable gross margin after manufacturer rebates, and how "
        "exposed is it to a loyalty-program change?",
        "What is CAC and lead-to-consult-to-treatment conversion, and how much "
        "revenue is discount / Groupon-sourced?",
        "What is the deferred-revenue liability from prepaid packages and "
        "memberships, and the breakage / refund history?",
        "Is the practice offering GLP-1 / weight-loss or other new lines, and "
        "how are prescribing, sourcing, and liability handled?",
    ],
    insider_lens=[
        "There is no payer — which sounds great (no denials, no AR) but means "
        "zero price floor and total exposure to consumer discretionary spend. "
        "Underwrite it like a premium consumer/retail brand, not a healthcare "
        "provider.",
        "The asset is the injectable annuity, not the lasers. Neurotoxin and "
        "filler clients rebook every few months; laser and body-contouring is "
        "episodic and price-shopped. The membership + injectable mix is the "
        "real quality-of-revenue signal.",
        "CPOM is not a footnote. In most states a sponsor cannot own the PC; "
        "the platform runs through an MSO and a 'friendly' physician-owned PC. "
        "A sloppy structure hides an existential legal and tax problem under "
        "great-looking margins.",
        "The injectors are the goodwill. They own the client and are highly "
        "mobile; a top injector walking can take a book of business with them. "
        "Retention and enforceable non-competes matter more than the buildout.",
        "The roll-up graveyard is real. Ideal Image's 2024 bankruptcy is the "
        "cautionary tale — discretionary + provider-dependent + brand-fickle + "
        "locally price-competitive is a genuinely hard thing to scale.",
        "Manufacturer loyalty programs run the demand funnel. AbbVie's Allē "
        "and Galderma's ASPIRE lock patients to brands and rebate the practice; "
        "a change in those economics moves both traffic and gross margin.",
    ],
    connections=default_connections(
        "medspa",
        deals_sector="medspa",
        connectors=[
            ("npi_provider",
             "NPI Registry — dermatology / plastic-surgery / NP injector supply"),
            ("open_payments_general_payments_2024",
             "CMS Open Payments — aesthetics device/drug maker payments to physicians"),
            ("openfda_device_510k",
             "openFDA 510(k) — energy-based aesthetic devices (laser / RF / IPL)"),
            ("census_acs_cbsa_profile",
             "Census ACS — metro household-income density (discretionary demand)"),
            ("bls_qcew_industry_area",
             "BLS QCEW — personal-care / medical wage base"),
        ],
    ),
    sources=[
        Source("American Med Spa Association (AmSpa) — Medical Spa State of the "
               "Industry Report", "INDUSTRY", "https://americanmedspa.org/"),
        Source("U.S. FDA — regulation of neurotoxins & dermal fillers (drugs) "
               "and energy-based aesthetic devices (510(k)/PMA)", "GOV",
               "https://www.fda.gov/medical-devices"),
        Source("American Medical Association — Corporate Practice of Medicine "
               "doctrine & MSO structure guidance", "INDUSTRY",
               "https://www.ama-assn.org/"),
        Source("FTC — advertising, health-claim, and consumer-financing "
               "guidance", "GOV",
               "https://www.ftc.gov/business-guidance/advertising-marketing"),
        Source("American Society of Plastic Surgeons / Aesthetic Society — "
               "procedural statistics", "INDUSTRY",
               "https://www.plasticsurgery.org/"),
        Source("PE Desk industry deep-dive (medical-aesthetics) + realized-deal "
               "corpus", "INTERNAL", "/diligence/tam-sam?template=medspa"),
    ],
    live_figures=live_figures_from_dive("medspa"),
    trends=(
        "The med-spa boom of the late 2010s–2020s was built on the "
        "mainstreaming of 'tweakments,' a widening (younger, more male) client "
        "base, and a surge of RN/NP injectors; industry trackers put the market "
        "in the mid-teens billions growing low-double-digits. PE piled in on a "
        "recurring-injectable-plus-MSO-scale thesis and then met the reality "
        "that discretionary, provider-dependent, brand-fickle, locally price-"
        "competitive services are hard to compound — Ideal Image filed Chapter "
        "11 in 2024. The next chapter has three vectors: new molecules (longer-"
        "acting Daxxify, new biostimulator fillers) refreshing the injectable "
        "annuity; GLP-1 weight-loss drugs pulling med spas into a new and "
        "regulatorily fraught revenue line; and a slow tightening of state med-"
        "spa supervision laws (Florida's 2024 statute a template). The winners "
        "are consolidating around injectable/membership annuity and physician-"
        "anchored, structurally-clean MSO platforms; laser-package 'deal' "
        "formats remain the churniest and most cyclical."),
    growth_levers=[
        GrowthLever(
            "Injectable adoption ('tweakment' mainstreaming)",
            "Rising social acceptance broadens the client base (younger, more "
            "male) and lifts rebooking frequency — the primary engine.",
            "primary", "ILLUSTRATIVE"),
        GrowthLever(
            "New molecules (Daxxify, new fillers/biostimulators)",
            "Longer-acting toxins and new filler chemistries refresh pricing "
            "and cadence and pull switchers.",
            "+ price / cadence", "ILLUSTRATIVE"),
        GrowthLever(
            "Membership / recurring conversion",
            "Subscriptions and prepaid packages convert episodic demand into an "
            "annuity, lifting lifetime value and retention.",
            "margin / retention", "ILLUSTRATIVE"),
        GrowthLever(
            "GLP-1 weight-loss add-on",
            "Semaglutide/tirzepatide programs add a high-ticket cash line — new "
            "revenue with new prescribing and liability risk.",
            "new line", "ILLUSTRATIVE"),
        GrowthLever(
            "Consumer disposable income / confidence",
            "Discretionary spend swings the demand curve both ways — a growth "
            "lever in expansions and a direct hit in downturns.",
            "cyclical ±", "ILLUSTRATIVE"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Discretionary consumer demand for aesthetic injectables",
        analysis=(
            "Unlike every reimbursed subsector, med-spa volume is a consumer-"
            "spending decision, not a clinical-eligibility one. The dominant "
            "driver is the mainstreaming of minimally-invasive aesthetics — "
            "neurotoxins and fillers — across a widening demographic (steadily "
            "younger and increasingly male), with rebooking every 3-4 months "
            "turning trial into habit. That makes the demand curve a function "
            "of disposable income, consumer confidence, social-media-driven "
            "acceptance, and local injector supply: high-growth in expansions "
            "and directly exposed in downturns. There is no demographic or "
            "reimbursement backstop under it — which is why same-store, ex-"
            "price recurring revenue is the number that matters."),
        basis="ILLUSTRATIVE"),
    cost_drivers=[
        CostDriver(
            "Provider compensation (injectors, medical director)",
            "~30-45% of revenue",
            "The largest line, often structured as a percentage of collections; "
            "retention-sensitive and the direct lever on same-site margin.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Injectable & consumable COGS (toxin, filler, tips) net of rebates",
            "~15-25% of revenue",
            "A pass-through cost moved materially by manufacturer rebate "
            "economics — utilization and buying scale are margin.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Marketing / customer acquisition",
            "~10-20% of revenue",
            "Discretionary demand is bought; CAC is the swing factor between "
            "healthy site-level and thin corporate margin.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Occupancy & device capex/lease (lasers, RF, rooms)",
            "~10-15% of revenue",
            "Energy devices are capex; underused lasers destroy ROI while "
            "injectables carry the site.",
            "ILLUSTRATIVE"),
        CostDriver(
            "G&A / MSO overhead & compliance",
            "~5-10% of revenue",
            "Management, CPOM-structure maintenance, and merchant/financing "
            "fees.",
            "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "No CMS facility file exists — med spas are cash-pay and not enrolled "
        "as Medicare providers, and AmSpa's location census is proprietary, so "
        "geography is not fabricated here. Directionally, density tracks "
        "disposable income and metro affluence (a Sun Belt and coastal-metro "
        "skew) and state supervision law rather than demographics — a "
        "distribution closer to premium consumer retail than to a healthcare "
        "facility map. Use the ACS income-density and deal-history connectors "
        "below rather than a fabricated map."),
)

register(REPORT)
