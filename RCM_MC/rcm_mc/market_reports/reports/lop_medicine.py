"""LOP Medicine — Letter-of-Protection / personal-injury lien-based care.

Deals-only deep-dive with NO payer dataset at all: care delivered to
personal-injury plaintiffs on a lien/Letter-of-Protection basis, billed at
chargemaster and collected out of the eventual litigation settlement. The
qualitative sections are authored around billed-vs-collected economics, the
attorney referral channel, the medical-lien finance layer, and the tort-reform
backlash (Howell, FL HB 837) that reprices the book. Geography and payer data
are honestly omitted — this is specialty finance wearing a clinical coat — so
``cms_trend`` and ``state_breakdown`` are unset and the renderer shows the note.
"""
from __future__ import annotations

from .. import (
    Competition, CostDriver, GrowthLever, HowItWorks, Kpi, MarketReport,
    MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment, Source,
    TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="lop_medicine",
    name="LOP Medicine",
    care_setting="Other services",
    naics="621111",
    one_line_def=(
        "Medical care delivered to personal-injury plaintiffs on a lien / "
        "Letter-of-Protection basis — the provider (pain, orthopedics, imaging, "
        "chiropractic, ambulatory surgery) treats now at billed charges and is "
        "paid later out of the litigation settlement, with the receivable often "
        "sold to a medical-lien funder at a discount. Specialty finance wearing "
        "a clinical coat."),
    tam_headline=TamHeadline(
        value=4.0, unit="$B", growth_pct=6.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "LOP medicine sits outside the insurance system, so there is no CMS "
            "or payer figure — nothing is filed as a claim. The ~$3-5B US "
            "medical-lien figure is modeled from personal-injury claim volume "
            "and the medical-lien / litigation-finance market; it is a "
            "billed-charge notion, and the collectible value is materially "
            "lower after settlement reductions. Growth tracks PI claim volume "
            "and litigation-finance capital inflow."),
    ),
    executive_summary=[
        "LOP medicine sits entirely outside the payer system. There is no "
        "Medicare, no commercial claim — the provider bills chargemaster (full "
        "billed charges, not contracted rates) and collects from the "
        "personal-injury settlement, secured by the attorney's Letter of "
        "Protection. Billed-versus-collected is the only number that matters.",
        "The asset is a channel, not a clinic. Cases come from the "
        "personal-injury attorney referral network; referral concentration — a "
        "few law firms — is the entire moat and the entire risk. No public "
        "dataset captures it, so diligence is relationship archaeology.",
        "Cash is a long-tail receivable. A lien is collected only when the case "
        "settles — 12 to 36+ months out — at a negotiated haircut to billed "
        "charges (the settlement 'reduction'). The business underwrites "
        "collectibility, timing, and the reduction rate, not clinical outcomes.",
        "Lien funders sit in the middle. Litigation-finance and medical-lien "
        "buyers purchase the receivable from the provider at a discount, giving "
        "the clinic cash now and taking collection risk — a parallel capital "
        "market with its own regulatory heat (usury, champerty, disclosure).",
        "The whole model rides on billed-charge economics and the tort "
        "environment. Chargemaster inflation, 'reasonable value of services' "
        "evidentiary fights (Howell v. Hamilton Meats and its progeny), "
        "no-fault/PIP rules, and tort reform admitting paid-not-billed amounts "
        "(Florida HB 837) reprice the entire book.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Accident (MVA, slip-and-fall) → plaintiff retains a PI attorney",
            "Attorney refers the client to an LOP provider",
            "Provider treats at billed charges (eval, imaging, injections, "
            "surgery, PT) and secures a signed Letter of Protection",
            "Charges accrue as a lien against the case",
            "(Optional) provider sells the receivable to a medical-lien funder "
            "for cash now at a discount",
            "Case settles or is tried → lien negotiated down (the 'reduction')",
            "Lien paid from settlement proceeds → net collection",
        ],
        sites_of_care=[
            "Pain-management clinic (injections, blocks)",
            "Orthopedic / spine practice + ambulatory surgery center",
            "Imaging center (MRI is the high-ticket lien)",
            "Chiropractic office + physical therapy",
        ],
        money_flow=(
            "There is no third-party payer. The provider renders care at full "
            "billed charges and holds a lien on the plaintiff's recovery, "
            "evidenced by the Letter of Protection the attorney signs. Nothing "
            "is collected until the case resolves — often one to three years "
            "later — and then the amount is negotiated down from billed charges "
            "as part of the settlement (the 'reduction'). Many providers "
            "monetize immediately by selling the receivable to a medical-lien "
            "funder for cash today at a discount; the funder collects on the "
            "back end. The economics are a spread between billed charges, the "
            "reduction, the time-to-cash, and the funding discount — a "
            "receivable, not a fee."),
        key_players=(
            "Personal-injury-focused physician practices and MSOs (pain, "
            "orthopedics, spine, chiropractic), imaging chains that court the PI "
            "bar, and the medical-lien-finance layer — specialty funders and "
            "litigation-finance firms that buy medical receivables. Roll-ups "
            "combine a clinical footprint with a captive funding book. The "
            "referral source — the plaintiff law firm — is the true gatekeeper "
            "of volume."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Medical liens outstanding (billed-charge basis)",
                    "the gross book",
                    "ILLUSTRATIVE · modeled from PI claim volume"),
            Segment("Net collected (post-reduction)",
                    "materially below billed",
                    "ILLUSTRATIVE · reduction-rate estimate"),
            Segment("Lien-funding / litigation-finance advances",
                    "the parallel capital market",
                    "ILLUSTRATIVE · industry estimates"),
            Segment("High-ticket liens (spine surgery, MRI)",
                    "the value concentration",
                    "ILLUSTRATIVE · case-mix estimate"),
        ],
        growth_drivers=[
            "Motor-vehicle-accident / personal-injury claim volume",
            "Attorney referral-network expansion",
            "Chargemaster / billed-charge inflation (offset by reductions)",
            "Litigation-finance capital inflow professionalizing the funding "
            "layer",
            "Migration of spine/orthopedic surgery to the ASC lien setting",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Personal-injury settlement lien (billed-charge, back-end)": 0.80,
            "Auto MedPay / PIP (no-fault states)": 0.12,
            "Cash / other": 0.08,
        },
        rate_mechanics=[
            "Billed charges (chargemaster), not contracted rates — the lien "
            "attaches to full billed charges; there is no fee-schedule discount "
            "because there is no payer contract.",
            "Letter of Protection — the attorney's written promise to pay the "
            "provider from settlement proceeds; it is a security instrument, "
            "not a guarantee of payment.",
            "Settlement reduction — at resolution the lien is negotiated down; "
            "the reduction rate (collected ÷ billed) is the true yield.",
            "Lien-funding discount — a funder buys the receivable for cash now "
            "at a haircut, transferring timing and collection risk off the "
            "clinic's balance sheet.",
            "No-fault / PIP / MedPay overlay — in no-fault states, first-party "
            "auto coverage pays a slice before the lien, changing the math.",
            "'Reasonable value of services' evidentiary rules — what a jury may "
            "hear (billed vs. paid) drives the recoverable value under Howell "
            "and its successors.",
        ],
        reimbursement_risk=(
            "Everything is collection risk and timing risk. A lien is only "
            "worth the settlement it is paid from — a weak liability case, an "
            "uninsured or underinsured defendant, or a low policy limit can "
            "leave the provider collecting cents on the billed dollar or "
            "nothing. Time-to-cash of one to three years ties up working "
            "capital; the reduction negotiation compresses yield; and the legal "
            "environment is actively hostile. 'Reasonable value of services' "
            "litigation (billed vs. paid), mandatory disclosure of "
            "provider-attorney LOP relationships, and phantom-damages reform "
            "(Florida's HB 837) can all impair the book at once. "
            "Chargemaster-based billing is the reform target."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("'Reasonable value' / collateral-source doctrine "
                 "(Howell v. Hamilton Meats, Cal. 2011, and state analogues)",
                 "Governs whether a jury sees billed or paid amounts and thus "
                 "defines the recoverable value a lien can capture — the single "
                 "most important legal input to LOP economics.",
                 "https://law.justia.com/cases/california/supreme-court/2011/s179115.html"),
            Rule("Letter-of-Protection & paid-amount disclosure "
                 "(Florida HB 837, 2023; spreading templates)",
                 "Forces disclosure of LOP/provider-attorney financial "
                 "relationships and lets defense introduce paid (not billed) "
                 "amounts — curbing phantom damages and cutting recoverable "
                 "value.",
                 "https://www.flsenate.gov/Session/Bill/2023/837"),
            Rule("Champerty / maintenance & usury doctrines",
                 "Old doctrines revived against litigation funding and "
                 "medical-lien finance; some states cap or void certain funding "
                 "arrangements, threatening the enforceability of the funder's "
                 "position.",
                 None),
            Rule("State fee-splitting & corporate-practice-of-medicine limits",
                 "Because LOP is cash, federal AKS/Stark generally do not "
                 "apply — but state fee-splitting and CPOM rules police "
                 "physician-attorney referral compensation and MSO structures.",
                 None),
            Rule("Third-party litigation-finance disclosure "
                 "(state rules + proposed federal mandates)",
                 "Growing requirements to disclose litigation funding in "
                 "litigation — transparency that pressures the medical-lien "
                 "finance layer.",
                 None),
        ],
        policy_watch=[
            "State tort-reform waves (Florida HB 837 and copycats) mandating "
            "LOP and paid-amount disclosure",
            "Litigation-finance transparency legislation (state + federal)",
            "Champerty / usury rulings on medical-lien enforceability",
            "No-fault / PIP reform in first-party states",
            "'Reasonable value of services' evidentiary developments post-Howell",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Highly fragmented and opaque — thousands of PI-oriented clinics and "
            "imaging/surgery sites tied to local plaintiff bars, plus a "
            "specialty-finance layer. There is no roster and no registry; "
            "concentration is by attorney relationship, not geography, so a "
            "market-share HHI is not measurable and is honestly omitted."),
        hhi_or_share=(
            "No public roster exists; concentration is by attorney referral "
            "relationship rather than measurable geographic share — omitted "
            "rather than fabricated."),
        consolidation=(
            "Emerging roll-ups pair a multi-site clinical footprint (pain, "
            "orthopedics, imaging, ASC) with a captive lien-funding book to "
            "internalize the finance spread. Litigation-finance capital has "
            "professionalized the funding side, standardizing receivable "
            "purchase and collection."),
        pe_activity=(
            "PE interest is rising but idiosyncratic. The thesis is the finance "
            "spread — buy receivables cheap, collect at scale — plus a clinical "
            "roll-up, offset by legal/collection risk and reputational and "
            "regulatory overhang. Quality-of-earnings is dominated by "
            "receivable valuation and reduction-rate durability, not visit "
            "growth."),
        notable_players=[
            "Multi-site PI pain / orthopedic / spine groups",
            "PI-focused imaging chains", "Ambulatory surgery centers on liens",
            "Medical-lien funders / litigation-finance firms",
            "Plaintiff personal-injury law-firm networks (the referral source)",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Reduction rate (net collected ÷ billed charges)", "40-70%",
                "The true yield on a lien; the number the whole P&L should be "
                "restated on."),
            Kpi("Days-to-cash (time to settlement)", "12-36+ months",
                "The working-capital and IRR driver; a growth clinic can "
                "starve for cash."),
            Kpi("Collection rate (% of liens ultimately paid)", "case-dependent",
                "Driven by liability strength and policy limits, not clinical "
                "quality."),
            Kpi("Funding discount (if selling receivables)", "haircut to billed",
                "Converts a back-end, uncertain yield into front-end cash — at "
                "a price."),
            Kpi("Referral concentration (top-firm share)", "often high",
                "The moat and the single-point-of-failure; an undocumented "
                "relationship that walks out with a rainmaker."),
            Kpi("Case mix (surgery/imaging vs. conservative care)", "value-skewed",
                "High-ticket liens (spine surgery, MRI) carry the value and the "
                "scrutiny."),
        ],
        margin_profile=(
            "Reported margins on billed charges look enormous and are illusory. "
            "The real margin is net collected minus cost of care minus the "
            "time-value drag of a one-to-three-year receivable minus bad debt "
            "on cases that lose or under-settle. A clinic that books revenue at "
            "billed charges without reserving for reductions and non-collection "
            "is overstating economics by a wide margin. Restate on collected, "
            "not billed. Ranges are ILLUSTRATIVE."),
    ),
    risks=[
        Risk("Collection / policy-limit risk", "High",
             "A lien is only worth the settlement; weak cases or low policy "
             "limits gut recovery regardless of care quality."),
        Risk("Legal / regulatory reform", "High",
             "LOP disclosure, paid-vs-billed rules, and phantom-damages reform "
             "(Florida HB 837) directly cut recoverable value."),
        Risk("Working-capital / timing", "High",
             "One-to-three-year cash conversion; rapid growth consumes cash "
             "faster than settlements return it."),
        Risk("Referral concentration", "High",
             "Dependence on a few law firms; a lost relationship is a demand "
             "cliff with no dataset to warn you."),
        Risk("Champerty / usury attack on funding", "Medium",
             "The finance layer's enforceability varies by state and can be "
             "voided."),
        Risk("Reputational / fraud narrative", "Medium",
             "'Lawsuit mill' perception and occasional kickback/fraud "
             "prosecutions overhang the model."),
    ],
    diligence_questions=[
        "What is the reduction rate (collected ÷ billed), and what is its "
        "trend?",
        "What is the collection rate by case type, and what is the "
        "policy-limit exposure of the outstanding book?",
        "What is the days-to-cash distribution and the receivable aging?",
        "What is the referral concentration by law firm, and how durable are "
        "the top relationships?",
        "How is revenue booked — at billed charges or reserved to collected — "
        "and what reserve methodology is used?",
        "What funding arrangements exist, at what discount, and who bears "
        "collection risk?",
        "What is the state tort-reform exposure (Florida-style disclosure and "
        "paid-amount rules) across the book?",
        "Are the liens and funding arrangements enforceable under state "
        "champerty/usury and fee-splitting/CPOM law?",
    ],
    insider_lens=[
        "The P&L is fiction until you apply the reduction. Revenue booked at "
        "billed charges is a chargemaster number nobody pays; the only real "
        "figure is net collected after settlement reductions, and it can be "
        "half of billed or less. Reprice the whole thing on collected, not "
        "billed.",
        "It is specialty finance, not healthcare. You are underwriting the "
        "plaintiff's case — liability, damages, and policy limits — as much as "
        "the clinical care. A great surgeon attached to weak cases collects "
        "poorly.",
        "Referral concentration is the asset and the cliff. Volume comes from a "
        "handful of PI law firms; that relationship is the moat, is "
        "undocumented, and walks out the door with a rainmaker. There is no "
        "dataset for it — only the referral ledger.",
        "Regulation is turning against the model. Florida's 2023 HB 837 forced "
        "LOP and paid-amount disclosure and curbed phantom damages; that "
        "template is spreading. A book underwritten on pre-reform reduction "
        "rates can reprice overnight.",
        "The funding spread is where the money and the legal risk both hide. "
        "Buying liens cheap and collecting at scale is lucrative — until a "
        "court voids the arrangement on champerty or usury grounds, or a "
        "disclosure rule lets defense counsel parade the finance relationship "
        "in front of a jury.",
    ],
    connections=default_connections(
        "lop_medicine",
        deals_sector="lop_medicine",
        connectors=[
            ("npi_provider_taxonomy",
             "NPI taxonomy — PI-heavy specialties (pain, ortho, chiro, imaging)"),
            ("oig_leie_exclusions",
             "OIG LEIE — excluded providers (integrity screen on PI clinics)"),
            ("census_acs_cbsa_profile",
             "Census ACS — metro population (accident/litigation demand proxy)"),
        ],
    ),
    sources=[
        Source("Howell v. Hamilton Meats & Provisions, Inc., 52 Cal.4th 541 "
               "(2011) — reasonable value of medical services", "GOV",
               "https://law.justia.com/cases/california/supreme-court/2011/s179115.html"),
        Source("Florida CS/CS/HB 837 (2023) — civil-remedies / tort reform "
               "(LOP + paid-amount disclosure)", "GOV",
               "https://www.flsenate.gov/Session/Bill/2023/837"),
        Source("RAND Institute for Civil Justice — auto-injury and medical-cost "
               "research", "ACADEMIC", "https://www.rand.org/well-being/justice-policy.html"),
        Source("International Legal Finance Association / litigation-finance "
               "disclosure debate", "INDUSTRY", "https://www.ilfa.com/"),
        Source("PE Desk industry deep-dive (deals-only, channel-relationship "
               "business) + realized-deal corpus", "INTERNAL",
               "/diligence/tam-sam?template=lop_medicine"),
    ],
    live_figures=live_figures_from_dive("lop_medicine"),
    trends=(
        "LOP medicine has moved from a cottage arrangement between individual "
        "doctors and plaintiff lawyers toward an institutionalized, "
        "finance-backed model — and straight into a regulatory headwind. On the "
        "capital side, litigation finance professionalized the funding layer: "
        "specialty funders now buy medical receivables at scale, letting clinics "
        "convert a one-to-three-year lien into cash today and letting sponsors "
        "roll up a clinical footprint with a captive funding book. On the legal "
        "side, the tort environment turned hostile. Howell v. Hamilton Meats "
        "reframed 'reasonable value' around paid rather than billed amounts in "
        "California, and Florida's 2023 HB 837 forced disclosure of "
        "provider-attorney LOP relationships and admitted paid-not-billed "
        "evidence — a template other states are copying. The net trajectory is "
        "a bigger, more capitalized market whose recoverable value per lien is "
        "being compressed by reform, so the durable question is reduction-rate "
        "resilience, not case volume."),
    growth_levers=[
        GrowthLever(
            "Personal-injury / MVA claim volume",
            "The demand base — every retained accident claim is a potential "
            "referral into LOP care.",
            "demand base", "ILLUSTRATIVE"),
        GrowthLever(
            "Attorney referral-network expansion",
            "Adding plaintiff-firm relationships is the primary volume lever — "
            "and the only real moat.",
            "primary channel", "ILLUSTRATIVE"),
        GrowthLever(
            "Chargemaster / billed-charge inflation",
            "Raises the gross lien book — but is directly offset by the "
            "reduction and by paid-vs-billed reform.",
            "nominal (reform-offset)", "ILLUSTRATIVE"),
        GrowthLever(
            "Captive lien-funding spread",
            "Internalizing the receivable purchase captures the funder's "
            "discount and accelerates cash.",
            "finance monetization", "ILLUSTRATIVE"),
        GrowthLever(
            "High-ticket case mix (spine / ASC / imaging)",
            "Shifting toward surgical and imaging liens raises value per case — "
            "and scrutiny.",
            "value per case", "ILLUSTRATIVE"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Personal-injury claim volume routed through the attorney "
               "referral channel",
        analysis=(
            "The dominant demand driver is the number of personal-injury claims "
            "steered into LOP care by plaintiff attorneys — not organic patient "
            "demand. A clinic's volume is a function of how many, and which, PI "
            "law firms refer to it; the attorney chooses the provider because "
            "the LOP secures the bill against a recovery the attorney controls. "
            "That makes referral-network breadth and depth the true volume "
            "engine, upstream of any clinical reputation. Case type amplifies "
            "value: a spine surgery or an MRI lien is worth many times a course "
            "of chiropractic care, so mix shift toward high-ticket procedures "
            "grows the book faster than visit count. No public dataset captures "
            "referral flow, so this driver is inferred from the deal's own "
            "referral ledger — and it is the first thing to diligence."),
        basis="ILLUSTRATIVE"),
    cost_drivers=[
        CostDriver(
            "Cost of capital / receivable carry (time-to-cash)", "#1 economic drag",
            "A one-to-three-year receivable is the dominant economic cost — the "
            "time-value and financing drag, not the clinical cost, defines the "
            "return.", "ILLUSTRATIVE"),
        CostDriver(
            "Bad debt / non-collection reserve", "reduction + loss",
            "Cases that lose, under-settle, or hit a low policy limit — the "
            "reserve that separates billed from collected.", "ILLUSTRATIVE"),
        CostDriver(
            "Clinical labor & physician compensation", "core delivery cost",
            "The actual cost of care (visits, imaging, surgery) — real, but "
            "second-order to the finance economics.", "ILLUSTRATIVE"),
        CostDriver(
            "Billing, collections & lien negotiation", "settlement legal cost",
            "Negotiating each lien down at settlement and litigating disputed "
            "reductions — a labor-intensive back office.", "ILLUSTRATIVE"),
        CostDriver(
            "Referral development & marketing", "channel cost",
            "Cultivating the plaintiff-firm relationships that supply volume — "
            "the spend that protects the moat.", "ILLUSTRATIVE"),
    ],
)

register(REPORT)
