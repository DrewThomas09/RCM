"""Plasma — FDA-licensed source-plasma collection.

Deals-only deep-dive (no public FDA source-plasma center roster is vendored, so
geography is omitted rather than fabricated). The critical framing, authored
throughout: this is NOT a Medicare-reimbursed healthcare provider — it is an
industrial biologics raw-material supply business. Centers pay donors to undergo
plasmapheresis and sell the collected source plasma by the liter to
fractionators (CSL, Grifols, Takeda, Octapharma) under long-term supply
agreements. Demand is set by the downstream immunoglobulin (IG) market, and the
US is the source of most of the world's plasma because it permits donor
compensation and high-frequency donation. The "payer mix" below is the
downstream plasma-derived-therapeutics end-market that ultimately funds the
price per liter — the collector itself has no insurance reimbursement.
Consumes ``plasma_deep_dive()`` for SOURCED corpus deal figures.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="plasma",
    name="Plasma",
    care_setting="Dx & labs",
    naics="621991",
    one_line_def=(
        "A network of FDA-licensed source-plasma collection centers that pay "
        "donors to undergo plasmapheresis and sell the collected source plasma "
        "by the liter, under long-term supply agreements, to fractionators who "
        "manufacture plasma-derived medicinal products (immunoglobulin, albumin, "
        "clotting factors, alpha-1). It is a biologics raw-material supply "
        "business, not a Medicare-reimbursed provider — the donor is compensated "
        "and the plasma is sold, not billed to a health plan."),
    tam_headline=TamHeadline(
        value=30.0, unit="$B", growth_pct=8.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "There is no single published US figure for source-plasma "
            "collection. ~$30B is the modeled anchor for the plasma-derived "
            "medicinal products (PDMP) end-market that funds the whole chain "
            "(industry/PPTA-directional, global PDMP is ~$30-40B+ and IG-led). "
            "The US collects the majority of the world's source plasma. Growth "
            "is IG-demand-led, driven by expanding neurology indications and "
            "immune-deficiency treatment."),
    ),
    executive_summary=[
        "Plasma collection is a biologics raw-material business, not a "
        "healthcare provider: FDA-licensed centers pay donors for source plasma "
        "and sell it by the liter to fractionators under long-term supply "
        "agreements. There is no insurance reimbursement at the center — the "
        "customer is the fractionator and demand is set by the downstream "
        "immunoglobulin (IG) market.",
        "The whole industry runs on IG demand. Immunoglobulin (IVIG/SCIG) for "
        "immune deficiencies and expanding neurology indications (CIDP, "
        "multifocal motor neuropathy) is the demand and margin engine; albumin, "
        "clotting factors, and alpha-1 are byproducts of the same liter. The "
        "business is supply-constrained, not demand-constrained, in most years.",
        "The US is the 'OPEC of plasma' — it collects most of the world's source "
        "plasma (roughly 60-70%) because it permits donor compensation and "
        "twice-weekly donation that most other countries restrict. That "
        "regulatory arbitrage is the reason the US collection footprint exists at "
        "this scale — and the biggest tail risk if paid-donation policy changes.",
        "The market is a vertically-integrated oligopoly: CSL, Grifols, Takeda, "
        "and Octapharma own most collection and virtually all fractionation. "
        "Independent collectors exist to sell into that oligopoly. Consolidation "
        "is near-complete at the top; PE plays independent collector networks and "
        "adjacencies, not fractionation.",
        "Unit economics turn on liters per center, donor yield, and cost per "
        "liter (donor compensation + labor + testing) against a contracted price "
        "per liter. A center is a fixed-cost box that only makes money once its "
        "donor base fills — center maturation (12-24+ months), donor retention, "
        "and FDA/cGMP compliance are the operational crux.",
        "The risks are FDA/cGMP inspection (a warning letter or import alert can "
        "halt a center or block export), donor-supply and compensation dynamics, "
        "and ethics/policy scrutiny of paid and cross-border donation — plus IG "
        "demand cyclicality and fractionator concentration.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Site selection near a dense, eligible donor pool (campuses, urban "
            "areas, border towns)",
            "Donor recruitment + eligibility screening (health history, viral "
            "markers, protein/hematocrit)",
            "Plasmapheresis collection — whole blood drawn, plasma separated, "
            "cells returned (~35-60+ minutes)",
            "Donor compensation (debit-card payment, with first-time and "
            "frequency incentives)",
            "Sample testing (NAT/serology) + qualification; a two-donation "
            "'applicant' hold for new donors",
            "Freezing + storage of source-plasma units; cold-chain logistics",
            "Sale/transfer to a fractionator under a long-term supply agreement "
            "(price per liter)",
            "Fractionation into IG, albumin, factor, and alpha-1; product sold "
            "into the clinical channel",
        ],
        sites_of_care=[
            "FDA-licensed source-plasma collection center (the unit asset)",
            "Fractionation plant (owned by the integrated majors; "
            "capital-intensive)",
            "Cold-chain storage & logistics network",
            "Downstream infusion / specialty-pharmacy channel where IG is "
            "administered (adjacent)",
        ],
        money_flow=(
            "The collection center's revenue is the sale of source plasma to a "
            "fractionator, priced per liter under a long-term supply agreement "
            "(the integrated majors 'sell' internally to their own "
            "fractionation). The center's costs are donor compensation (paid per "
            "donation via debit card, with frequency and first-time incentives), "
            "phlebotomy and screening labor, testing, and facility. There is no "
            "health-insurance reimbursement at the center — the donor is "
            "compensated, not billed. Downstream, the fractionator manufactures "
            "plasma-derived medicinal products (IG, albumin, factor, alpha-1) and "
            "sells them into the clinical channel, where IG is reimbursed under "
            "Medicare Part B (buy-and-bill, ASP-plus-add-on mechanics), Part D, "
            "and commercial plans — and that downstream reimbursement is what "
            "ultimately funds the price per liter the collector earns. The "
            "economics are liters collected times price per liter, less donor pay "
            "and center opex; a center is a high-fixed-cost box whose "
            "profitability turns on filling its donor base."),
        key_players=(
            "A vertically-integrated global oligopoly dominates both collection "
            "and fractionation: CSL Behring (CSL Plasma — the largest network), "
            "Grifols (Biomat USA / Talecris), Takeda (BioLife Plasma Services, "
            "from Baxalta/Shire), and Octapharma Plasma. Smaller and independent "
            "players include ADMA Biologics, Kedrion/BPL, and Emergent, plus a "
            "tail of independent collectors that supply the majors. The "
            "end-market is the same integrated names selling IG, albumin, and "
            "factor. PE and independents play collector networks and adjacencies "
            "rather than fractionation, which is capital- and scale-prohibitive."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Plasma-derived medicinal products (PDMP) end-market, global",
                    "~$30-40B+ (directional)",
                    "INDUSTRY · PPTA / market-research directional"),
            Segment("Immunoglobulin (IG) — the demand & margin driver",
                    "the majority of PDMP value",
                    "INDUSTRY · industry directional"),
            Segment("US source-plasma collection (raw material)",
                    "US collects most of world plasma (~60-70%)",
                    "INDUSTRY · PPTA directional"),
            Segment("Albumin, clotting factors, alpha-1",
                    "byproducts of the same fractionated liter",
                    "INDUSTRY · industry directional"),
            Segment("US collection centers",
                    "~1,000+ FDA-licensed centers (directional)",
                    "INDUSTRY · PPTA / FDA-registration directional"),
        ],
        growth_drivers=[
            "Immunoglobulin (IG) demand — neurology indications (CIDP, MMN) + "
            "immune deficiency widen the treated population",
            "Aging + better diagnosis of immune/neurologic conditions",
            "Global reliance on US donor compensation (the collection arbitrage)",
            "New center openings + donor-base maturation lifting collection "
            "volume",
            "Subcutaneous IG (SCIG) home administration expanding the treated "
            "pool",
            "Donor supply, compensation cost, and FDA/cGMP constraints as the "
            "drag",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "End-market: Medicare Part B / Part D (IG etc.)": 0.45,
            "End-market: Commercial": 0.40,
            "End-market: Medicaid / 340B / other": 0.15,
        },
        rate_mechanics=[
            "No center-level insurance reimbursement — the collector is paid per "
            "liter by the fractionator under a long-term supply agreement; the "
            "donor is compensated (debit card), not billed. The payer mix above "
            "is the DOWNSTREAM IG end-market that funds that price per liter.",
            "Donor compensation — the primary 'rate' the collector controls; "
            "frequency and first-time incentives set against local competition "
            "for donors.",
            "Downstream IG reimbursement — Medicare Part B buy-and-bill (ASP-plus "
            "mechanics, subject to sequestration) plus a separate IVIG "
            "administration/demonstration payment; Part D for self-administered "
            "SCIG; commercial and Medicaid apply their own coverage.",
            "FDA licensure & cGMP — a center must be FDA-licensed and each "
            "fractionation product BLA-approved; compliance status gates the "
            "ability to collect and to export.",
            "Product pricing (ASP) — IG average sales price sets downstream "
            "revenue and, through supply contracts, flows back into the "
            "collector's realized price per liter.",
            "Export/import controls — plasma and products cross borders; FDA and "
            "foreign regulators (EMA) gate market access.",
        ],
        reimbursement_risk=(
            "The collector has no insurance reimbursement risk in the usual "
            "sense — its revenue is a contracted price per liter — but that price "
            "is ultimately a derivative of downstream IG reimbursement and "
            "demand, so IG ASP erosion, Part B payment changes (sequestration, "
            "add-on pressure, the Inflation Reduction Act), or a demand shock "
            "flow back into the price per liter and center economics. The "
            "nearer-term risks are operational and regulatory: donor supply and "
            "rising donor-compensation cost compress cost per liter; an FDA cGMP "
            "warning letter, Form 483, import alert, or license action can halt a "
            "center or block export; and paid-donation ethics/policy scrutiny — "
            "and any restriction on donation frequency, donor compensation, or "
            "cross-border collection — would strike at the US collection model "
            "directly."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("FDA licensure & cGMP for blood/plasma establishments "
                 "(21 CFR 606/610/640)",
                 "Every center must be FDA-licensed and follow current good "
                 "manufacturing practice; inspection findings (483s, warning "
                 "letters, import alerts) gate operations and export.",
                 "https://www.fda.gov/vaccines-blood-biologics/blood-blood-products"),
            Rule("FDA source-plasma donor eligibility & frequency "
                 "(21 CFR 630/640)",
                 "Governs donation frequency (up to twice in a 7-day period), "
                 "donor screening, weight-tiered collection volume, and "
                 "applicant qualification — the rules that set donor throughput.",
                 "https://www.ecfr.gov/current/title-21/chapter-I/subchapter-F/part-640"),
            Rule("PPTA IQPP / QSEAL voluntary standards",
                 "Industry self-regulation layered on FDA — qualified-donor and "
                 "inventory-hold standards, national donor deferral, and viral "
                 "marker requirements that define the compliant operating model.",
                 "https://www.pptaglobal.org/"),
            Rule("Medicare Part B immune globulin (IVIG) payment + IVIG "
                 "demonstration",
                 "The downstream reimbursement that funds the whole chain — "
                 "buy-and-bill ASP mechanics for IG plus a separate home-IVIG "
                 "administration benefit.",
                 "https://www.cms.gov/medicare/payment/fee-for-service-providers"),
            Rule("Paid / cross-border donation policy (FDA + CBP)",
                 "Limits and scrutiny on donor compensation and cross-border "
                 "(border-town) collection — a direct check on the US "
                 "collection model and its border-town center economics.",
                 None),
        ],
        policy_watch=[
            "FDA inspection/enforcement trends (483s, warning letters, import "
            "alerts) on collection & fractionation",
            "Donor-compensation ethics and any frequency/eligibility rule "
            "changes",
            "Cross-border (border-town) donor-collection policy and CBP/visa "
            "restrictions",
            "Medicare Part B IG payment (add-on, sequestration, IRA effects) "
            "feeding the end-market",
            "IG demand/indication expansion (neurology) vs. periodic shortage "
            "cycles",
            "Pathogen-safety and testing-standard changes raising cost per liter",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Highly concentrated and vertically integrated. Four names — CSL, "
            "Grifols, Takeda, and Octapharma — own most US collection capacity "
            "and essentially all fractionation; the acquirable independent-"
            "collector pool is a thin tail that mostly exists to supply the "
            "majors. No public FDA-center roster is vendored, so a center-count "
            "HHI is honestly omitted — but this is one of the most concentrated "
            "healthcare-adjacent supply verticals."),
        hhi_or_share=(
            "Collection and fractionation are both oligopolistic — the top four "
            "control the large majority of US collection and virtually all "
            "fractionation capacity, and independent collectors are price-takers "
            "into that structure. Concentration sits near the top of the "
            "healthcare-adjacent spectrum."),
        consolidation=(
            "Essentially complete at the top through decades of M&A — "
            "Grifols/Talecris, Shire-Baxalta/Takeda, CSL's organic build, and "
            "Octapharma's expansion — leaving a fully integrated "
            "collect-to-product oligopoly. Remaining deal activity is "
            "independent-collector networks, new-center build-outs, and "
            "adjacencies (ADMA's specialty IG, Kedrion/BPL). Fractionation's "
            "capital intensity and scale economics are a near-insurmountable "
            "barrier to new entry."),
        pe_activity=(
            "PE participates on the edges — independent collector platforms, "
            "center build-and-fill roll-ups, and downstream infusion/"
            "specialty-pharmacy adjacencies — rather than in fractionation, "
            "which is capital- and scale-prohibitive. Quality-of-earnings "
            "centers on liters per center and donor-base maturation, donor "
            "retention and compensation cost, FDA/cGMP compliance history, the "
            "durability and pricing of fractionator supply agreements, and IG "
            "demand exposure."),
        notable_players=[
            "CSL Plasma (CSL Behring)", "Grifols (Biomat / Talecris)",
            "Takeda (BioLife Plasma)", "Octapharma Plasma", "ADMA Biologics",
            "Kedrion / BPL", "Emergent BioSolutions",
            "Independent collector networks",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Liters collected / center / year", "center-scale dependent",
                "The top-line volume driver; a center fills over 12-24+ months "
                "to its steady state."),
            Kpi("Yield per donation", "~0.6-0.9+ L (donor-weight tiered)",
                "Plasma volume per visit is FDA weight-tiered; frequency (up to "
                "2x per 7 days) drives throughput."),
            Kpi("Cost per liter (donor pay + labor + testing)",
                "the controllable cost",
                "Donor compensation is the largest and most competitive line; "
                "local donor competition sets it."),
            Kpi("Price per liter (supply contract)",
                "contracted, IG-demand-linked",
                "The realized price the fractionator pays; the spread over cost "
                "per liter is the margin."),
            Kpi("Center maturation time", "12-24+ months to fill",
                "A new center burns cash until its donor base fills; the "
                "build-and-fill curve is the value-creation lever."),
            Kpi("Donor retention / lapse rate", "high churn at the margin",
                "Retention drives yield and lowers per-liter recruitment cost."),
        ],
        margin_profile=(
            "A collection center is a fixed-cost box: the economics are liters "
            "collected times price per liter, less donor compensation, "
            "phlebotomy/screening labor, and testing. The single largest and "
            "most competitive cost is donor pay, which local competition among "
            "nearby centers bids up; the largest value lever is filling a new "
            "center's donor base, since a mature high-volume center spreads fixed "
            "labor and facility cost across far more liters. The integrated "
            "majors capture the full collect-to-product margin — the real value "
            "sits in the IG product, not the raw liter — while independent "
            "collectors earn the narrower per-liter spread and live or die on "
            "liters per center and cost per liter. FDA/cGMP compliance is an "
            "existential cost: a stop-collection or import alert zeroes a "
            "center's output."),
    ),
    risks=[
        Risk("FDA / cGMP compliance action", "High",
             "A Form 483, warning letter, import alert, or license action can "
             "halt a center or block export — the existential operational "
             "risk."),
        Risk("Donor supply & compensation cost", "High",
             "Donor availability and rising pay (bid up by nearby centers) drive "
             "cost per liter and center fill — the core margin variable."),
        Risk("IG end-market demand / pricing", "Medium",
             "Collection is derivative of IG demand and ASP; a demand shock or "
             "Part B/IRA payment change flows back into the price per liter."),
        Risk("Fractionator concentration / contract dependence", "Medium",
             "Independent collectors sell into an oligopsony; supply-contract "
             "durability and pricing power are limited."),
        Risk("Paid-donation ethics & policy", "Medium",
             "Restrictions on donor compensation, donation frequency, or "
             "cross-border collection would strike the US model directly."),
        Risk("Center maturation / build risk", "Medium",
             "New centers burn cash for 12-24+ months; a slow fill or "
             "oversupplied local donor market impairs returns."),
    ],
    diligence_questions=[
        "What is liters per center and where is each center on its maturation "
        "curve — how much EBITDA is from mature vs still-filling centers?",
        "What is cost per liter (donor pay, labor, testing) by center, and how "
        "competitive is the local donor market?",
        "What are the fractionator supply agreements — price per liter, term, "
        "volume commitments, exclusivity, and renewal risk?",
        "What is the FDA/cGMP inspection history — any 483s, warning letters, "
        "import alerts, or stop-collections?",
        "What is donor retention/lapse and recruitment cost, and how sensitive "
        "is yield to compensation changes?",
        "How exposed is the price per liter to downstream IG demand and "
        "Part B/ASP/IRA payment changes?",
        "What is the center pipeline (new builds), the capital plan, and the "
        "local competitive density for donors?",
        "For border-town centers, what is exposure to cross-border "
        "donor-collection policy and CBP/visa restrictions?",
    ],
    insider_lens=[
        "This isn't a healthcare provider — it's an industrial biologics supply "
        "business. There's no claim to a health plan; the donor is paid and the "
        "plasma is sold by the liter. Diligence is a manufacturing-and-"
        "supply-chain exercise, not a reimbursement one — until you trace the "
        "price per liter back to IG demand.",
        "The US is the 'OPEC of plasma.' Most of the world's source plasma is "
        "collected here because the US allows donor compensation and twice-weekly "
        "donation that most countries ban. The entire US center footprint is a "
        "regulatory-arbitrage asset — and a policy change to paid donation is the "
        "tail risk that outweighs everything on the P&L.",
        "The whole chain is really an IG business. Albumin, factor, and alpha-1 "
        "come off the same liter, but immunoglobulin demand — driven increasingly "
        "by neurology (CIDP, MMN) — sets collection volume and price. The "
        "industry is supply-constrained most years: it can sell every liter it "
        "can collect.",
        "A center is a build-and-fill curve. It burns cash for 12-24+ months "
        "until its donor base fills, then throws off cash as fixed labor and "
        "facility spread over more liters. Buying a network is buying its "
        "maturation stage — the mix of mature vs filling centers is the real "
        "earnings-quality question.",
        "Donor pay is the battleground. Where centers cluster — near a campus or "
        "a border crossing — they bid up donor compensation against each other; "
        "cost per liter is a local-competition story, not a national one.",
        "The FDA is the off-switch. A warning letter or import alert can stop a "
        "center from collecting or block its plasma from export overnight — cGMP "
        "compliance history is not a footnote, it's the first page of diligence.",
    ],
    connections=default_connections(
        "plasma",
        deals_sector="plasma",
        extra_pages=[
            ("/industry/plasma",
             "Industry deep-dive — plasma collection deal history + structure"),
        ],
        connectors=[
            ("census_acs_cbsa_profile",
             "Census ACS — CBSA demographics for donor-catchment siting "
             "(income, age, campus/border density)"),
            ("bls_qcew_area_industry",
             "BLS QCEW — local wage & employment base for phlebotomy/screening "
             "labor cost"),
            ("cms_open_data_part_b_spending_by_drug",
             "CMS Part B spending by drug — downstream IG (IVIG) spend & ASP, the "
             "end-market that funds price per liter"),
            ("fda_ndc_directory",
             "FDA NDC directory — plasma-derived product (IG/albumin/factor) "
             "end-market mapping"),
            ("open_payments",
             "CMS Open Payments — manufacturer payments to IG-prescribing "
             "physicians (downstream demand channel)"),
        ],
    ),
    sources=[
        Source("FDA — blood & plasma establishment licensure and cGMP "
               "(21 CFR 606/610/630/640)", "GOV",
               "https://www.fda.gov/vaccines-blood-biologics/blood-blood-products"),
        Source("PPTA (Plasma Protein Therapeutics Association) — industry "
               "standards (IQPP/QSEAL) & data", "INDUSTRY",
               "https://www.pptaglobal.org/"),
        Source("CMS — Medicare Part B immune globulin (IVIG) payment & IVIG "
               "demonstration", "GOV",
               "https://www.cms.gov/medicare/payment/fee-for-service-providers"),
        Source("Marketing Research Bureau — plasma-derived products market data "
               "(directional)", "INDUSTRY", "https://marketingresearchbureau.com/"),
        Source("Transfusion / peer-reviewed literature on paid plasma donation "
               "and supply", "ACADEMIC",
               "https://onlinelibrary.wiley.com/journal/15372995"),
        Source("PE Desk industry deep-dive (plasma) + realized-deal corpus",
               "INTERNAL", "/diligence/tam-sam?template=plasma"),
    ],
    live_figures=live_figures_from_dive("plasma"),
    trends=(
        "Plasma collection scaled dramatically over the last decade on the back "
        "of immunoglobulin demand — IG for immune deficiencies and, increasingly, "
        "neurologic indications (CIDP, multifocal motor neuropathy) — with the US "
        "cementing its role as the source of most of the world's plasma because "
        "it permits donor compensation and high-frequency donation. The "
        "integrated majors (CSL, Grifols, Takeda, Octapharma) raced to open "
        "centers; COVID-19 then cratered donations (lockdowns, stimulus that "
        "reduced donor economics, and border closures that hit Mexican-national "
        "donors), creating a supply crunch and IG tightness that took years to "
        "normalize and pulled donor compensation up. As collection recovered, the "
        "industry returned to its structural state: supply-constrained, "
        "IG-demand-led, and highly concentrated. The forward trajectory is "
        "durable IG demand (aging, expanding neurology use, SCIG home therapy) "
        "pulling collection, against rising donor-compensation cost, FDA/cGMP "
        "scrutiny, periodic shortage cycles, ethics/policy debate over paid and "
        "cross-border donation, and downstream Part B/IRA payment pressure that "
        "feeds back into the price per liter."),
    growth_levers=[
        GrowthLever(
            "Immunoglobulin (IG) demand growth",
            "Neurology indications plus immune deficiency widen the IG-treated "
            "population — the primary demand engine pulling collection volume.",
            "primary", "ILLUSTRATIVE"),
        GrowthLever(
            "New center build-and-fill",
            "Opening centers and maturing their donor bases adds collection "
            "capacity and volume.",
            "+ capacity", "ILLUSTRATIVE"),
        GrowthLever(
            "SCIG home administration",
            "Subcutaneous IG expands and normalizes the treated pool and its "
            "steady demand.",
            "+ treated pool", "ILLUSTRATIVE"),
        GrowthLever(
            "Donor yield & retention",
            "Donation frequency (up to 2x per 7 days), retention, and yield per "
            "donation lift liters per center.",
            "+ liters/center", "ILLUSTRATIVE"),
        GrowthLever(
            "Donor-compensation cost + cGMP + supply-cyclicality drag",
            "Rising donor pay and compliance cost, plus periodic shortage "
            "cycles, subtract from per-liter margin.",
            "cost & supply risk", "ILLUSTRATIVE"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Immunoglobulin (IG) demand — the pull on every collected liter",
        analysis=(
            "The dominant demand driver is downstream immunoglobulin "
            "consumption, not anything at the collection center. IG (IVIG and "
            "subcutaneous SCIG) treats primary and secondary immune deficiencies "
            "and a widening set of neurologic and autoimmune indications — CIDP, "
            "multifocal motor neuropathy, and others — and that treated "
            "population grows with aging, better diagnosis, and expanding label "
            "use; SCIG home therapy further normalizes and grows demand. Because "
            "albumin, clotting factor, and alpha-1 are byproducts of the same "
            "fractionated liter, IG demand effectively sets how much plasma the "
            "industry needs, and the industry is supply-constrained in most "
            "years — it can sell essentially every liter it collects. That makes "
            "collection volume (liters per center times center count times donor "
            "frequency), not end-demand, the binding operational variable, and "
            "donor supply plus FDA/cGMP capacity the true constraint on growth."),
        basis="ILLUSTRATIVE"),
    cost_drivers=[
        CostDriver(
            "Donor compensation", "#1 — largest variable cost",
            "Paid per donation and bid up by local center competition — the "
            "primary controllable cost per liter.", "ILLUSTRATIVE"),
        CostDriver(
            "Center labor (phlebotomy, screening, QA)", "~25-35% of center cost",
            "Staffing the plasmapheresis floor and donor screening — largely "
            "fixed, spread by higher volume.", "ILLUSTRATIVE"),
        CostDriver(
            "Testing, consumables & cold chain", "~10-20% of cost",
            "NAT/serology testing, apheresis kits, freezing, and cold-chain "
            "logistics per unit.", "ILLUSTRATIVE"),
        CostDriver(
            "Facility & occupancy", "fixed per center",
            "The leased box — profitability turns on filling it (liters over "
            "fixed cost).", "ILLUSTRATIVE"),
        CostDriver(
            "FDA/cGMP compliance & QA overhead", "cost of the license to operate",
            "Quality systems, inspection readiness, and the existential cost of "
            "a compliance failure.", "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "No public FDA source-plasma center roster is vendored, so state "
        "geography is omitted rather than fabricated. Qualitatively, centers "
        "cluster where eligible, motivated donors are dense — around "
        "universities, lower-income urban areas, and (historically) US-Mexico "
        "border crossings, where cross-border donors were significant until "
        "CBP/visa restrictions tightened. The Census ACS and BLS QCEW connectors "
        "linked below give a real donor-catchment and local-labor read for "
        "siting; the FDA establishment registry (not vendored offline) is the "
        "authoritative center list."),
)

register(REPORT)
