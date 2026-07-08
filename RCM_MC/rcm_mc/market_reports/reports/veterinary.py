"""Veterinary — companion-animal veterinary services (GP, specialty, ER).

Deals-only market-report module (no public veterinary facility census — AVMA
data is member-gated — so no computed state_breakdown or supply trend). The
defining feature that shapes every section: veterinary is a CASH-PAY consumer-
health category with no dominant third-party payer, no Medicare, and no
Stark/Anti-Kickback overlay. That is the source of its pricing power and the
reason it became one of the hottest PE roll-ups of the last decade — now cooling
on the vet-labor shortage and the first FTC antitrust scrutiny of the sector.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver, default_connections,
    live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="veterinary",
    name="Veterinary",
    care_setting="Other services",
    naics="541940",
    one_line_def=(
        "Companion-animal veterinary care — general practice, specialty, and "
        "emergency hospitals — a cash-pay consumer-health service with no "
        "dominant third-party payer, real pricing power, and a binding "
        "constraint on the supply of veterinarians rather than on demand."),
    tam_headline=TamHeadline(
        value=40.0, unit="$B", growth_pct=7.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "APPA/AVMA companion-animal veterinary-care spend (~$38-40B), part "
            "of ~$150B total US pet spending. INDUSTRY-survey basis, not a "
            "government figure. Growth is the modeled mid-to-high-single-digit "
            "consumer-health trend (price + pet-humanization), normalizing off "
            "the COVID pet-adoption pull-forward."),
    ),
    executive_summary=[
        "Cash-pay is the moat. Clients pay out of pocket at the point of care — "
        "there is no Medicare, no dominant insurer, no Stark/Anti-Kickback "
        "overlay — so the sector has genuine pricing power and none of the "
        "reimbursement risk that defines human healthcare. That is why multiples "
        "ran to the high teens and beyond.",
        "The binding constraint is the supply of veterinarians, not demand. You "
        "buy a clinic for its doctors, and they can walk — so retention, "
        "non-competes, and associate compensation (ProSal, production-based) are "
        "the entire integration risk, and the DVM shortage caps how fast anyone "
        "can grow.",
        "It is one of the most PE-penetrated fragmented roll-ups in healthcare: "
        "corporate ownership is roughly a quarter to a third of clinics and much "
        "higher in specialty/ER. Mars Veterinary Health is the strategic giant; "
        "a dozen sponsor-backed platforms compete for the independent-clinic tail.",
        "The FTC now reviews veterinary roll-ups. The JAB/NVA-SAGE divestiture "
        "consent order was the wake-up call — local-market overlap in specialty "
        "and ER is a real gating item, not a formality, and it reprices the "
        "serial-acquisition thesis.",
        "The COVID pet boom pulled demand forward; visit volume softened in "
        "2023-24 even as price held. Same-store growth is now a price story more "
        "than a volume story, and pet-insurance penetration — still low but "
        "rising — is the variable that could reshape the cash-pay dynamic over a hold.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Client acquisition (new pet, relocation, referral, reputation)",
            "Wellness / preventive visit (vaccines, exams, dental, parasiticides)",
            "Diagnostics (in-house + reference lab, imaging) and pharmacy",
            "Sick / urgent visit → GP treatment or referral to specialty/ER",
            "Specialty & surgery (ortho, oncology, cardiology, internal medicine)",
            "Point-of-care payment — cash, card, or third-party financing",
            "Retention loop — wellness plans, reminders, and client lifetime value",
        ],
        sites_of_care=[
            "General-practice companion-animal clinics (the volume base)",
            "Specialty / referral hospitals (higher acuity and margin)",
            "24/7 emergency and critical-care hospitals (ER)",
            "Mobile / house-call and telehealth (emerging, VCPR-gated)",
            "Corporate-affiliated networks under an MSO where state law requires",
        ],
        money_flow=(
            "The client pays at the point of care — cash, card, or third-party "
            "financing (CareCredit, Scratchpay) — and the practice is paid in "
            "full at the visit. There is no institutional payer: where pet "
            "insurance exists it reimburses the OWNER after the fact, not the "
            "practice, so the practice's cash flow and pricing are insulated "
            "from any payer network. Revenue is a bundle of professional "
            "services (exams, surgery), diagnostics, and product/pharmacy margin. "
            "Because pricing is set by the practice rather than a fee schedule, "
            "the business has real price-taking power — the defining economic "
            "difference from every human-healthcare vertical, and the reason it "
            "trades at consumer-health rather than provider multiples."),
        key_players=(
            "Mars Veterinary Health is the strategic anchor — Banfield, VCA, "
            "BluePearl, and (globally) AniCura and Linnaeus. The sponsor-backed "
            "platforms include National Veterinary Associates (JAB), Southern "
            "Veterinary Partners (Shore Capital / Silver Lake), PetVet Care "
            "Centers (KKR), Thrive Pet Healthcare, Mission Veterinary Partners, "
            "VetCor, Blue River PetCare, and Encore Vet Group. IDEXX and Zoetis "
            "supply the diagnostics/pharma rails. The acquirable pool is the "
            "large independent-clinic long tail — the same fragmentation the "
            "platforms are consolidating."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("US companion-animal veterinary-care spend",
                    "~$38-40B",
                    "INDUSTRY · APPA / AVMA pet-industry spending"),
            Segment("Total US pet-industry spending (context)",
                    "~$150B (vet care is a subset)",
                    "INDUSTRY · APPA State of the Industry"),
            Segment("Corporate-owned clinic share",
                    "~25-35% of clinics; higher in specialty/ER",
                    "INDUSTRY · consolidation estimates"),
            Segment("General practice vs specialty/ER",
                    "GP is the volume; specialty/ER the margin + consolidation",
                    "INDUSTRY · practice-type split"),
        ],
        growth_drivers=[
            "Pet humanization — higher spend per pet on medical care ~4-6%/yr",
            "Services price inflation — real pricing power, ~5-8%/yr on price",
            "Specialty & advanced-care adoption (oncology, ortho, cardiology)",
            "Pet-insurance penetration rising off a low base (demand unlock)",
            "Vet-labor supply — a NEGATIVE constraint capping volume growth",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Client out-of-pocket (cash / card / financing)": 0.94,
            "Pet insurance (reimburses the owner, not the practice)": 0.06,
        },
        rate_mechanics=[
            "Cash-pay at point of care — the practice sets prices; there is no "
            "government fee schedule and no payer network, hence real pricing power.",
            "Pet insurance reimburses the OWNER after payment (indemnity), so the "
            "practice is paid in full at the visit regardless of coverage.",
            "Third-party patient financing (CareCredit, Scratchpay) converts "
            "large bills into installments, supporting higher-ticket care.",
            "Product & pharmacy margin — parasiticides, food, and dispensed drugs "
            "add a retail margin layer distinct from professional services.",
            "Wellness / subscription plans — bundled preventive care for a "
            "monthly fee, smoothing revenue and improving retention.",
            "No Medicare / Medicaid and no Stark/Anti-Kickback regime — the "
            "compliance surface is state practice acts and consumer law, not "
            "federal healthcare-program rules.",
        ],
        reimbursement_risk=(
            "There is almost no classic reimbursement risk — that is the point of "
            "the sector. The practice is paid in full at the visit, so bad debt "
            "is minimal and there is no denial, downcoding, or payer-mix decay. "
            "The real 'reimbursement' variables are consumer, not institutional: "
            "how much price elasticity exists as fees rise (pet care is "
            "discretionary at the margin, and clients defer or decline care they "
            "cannot afford), how far third-party financing can stretch a big "
            "bill, and whether rising pet-insurance penetration eventually "
            "introduces payer-like pressure on pricing and utilization the way it "
            "did in human care. For now, elasticity and demand normalization — "
            "not a payer — are the top-line risks."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("State veterinary practice acts + corporate-practice rules",
                 "Some states restrict clinic ownership to licensed "
                 "veterinarians, forcing MSO/management structures (as in human "
                 "physician practice management) — a real deal-structuring item.",
                 None),
            Rule("Veterinarian-Client-Patient Relationship (VCPR) + telemedicine",
                 "State VCPR requirements govern whether care and prescribing can "
                 "occur remotely — the gating rule for veterinary telehealth.",
                 None),
            Rule("DEA controlled-substance registration",
                 "Practices dispensing/administering controlled drugs must hold "
                 "DEA registration and meet handling and recordkeeping rules.",
                 "https://www.deadiversion.usdoj.gov/"),
            Rule("FTC antitrust review of veterinary consolidation",
                 "The FTC has ordered divestitures in veterinary deals (the "
                 "JAB/NVA-SAGE consent order) — local specialty/ER overlap is a "
                 "genuine gating item for roll-ups.",
                 "https://www.ftc.gov/"),
            Rule("FDA Center for Veterinary Medicine + state pharmacy/board rules",
                 "Animal-drug approval, compounding, and dispensing are governed "
                 "by FDA CVM and state veterinary/pharmacy boards.",
                 "https://www.fda.gov/animal-veterinary"),
        ],
        policy_watch=[
            "FTC posture on serial veterinary acquisitions and local overlap",
            "State corporate-practice-of-veterinary-medicine enforcement",
            "Telehealth / VCPR liberalization (state-by-state)",
            "Pet-insurance regulation and NAIC model-act adoption",
            "Veterinary workforce / new-vet-school capacity policy",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Historically a classic fragmented cottage industry — tens of "
            "thousands of independent, often single-doctor clinics — now roughly "
            "a quarter to a third consolidated, with specialty and emergency "
            "hospitals far more consolidated than general practice. No public "
            "facility census is vendored (AVMA data is member-gated), so "
            "geography is honestly omitted; the corpus trade history stands in "
            "its place below."),
        hhi_or_share=(
            "Nationally unconcentrated, but LOCAL specialty/ER markets can be "
            "tight — which is exactly where the FTC has focused. Mars is the "
            "largest owner but holds a modest share of a still-fragmented base."),
        consolidation=(
            "One of the defining healthcare roll-ups of the last decade: Mars "
            "assembled Banfield, VCA, and BluePearl, and a dozen sponsor-backed "
            "platforms (NVA/JAB, Southern Veterinary Partners, PetVet/KKR, "
            "Thrive, Mission, VetCor) raced to acquire independents. Entry "
            "multiples peaked very high in 2021 on the cash-pay, recession-"
            "resilient thesis, then cooled as rate normalized, labor tightened, "
            "and the FTC engaged."),
        pe_activity=(
            "Veterinary is a marquee PE category precisely for its cash-pay, "
            "recession-resilient, fragmented profile with a humanization "
            "tailwind. The thesis is buy-and-build: acquire independents at "
            "single-digit multiples, professionalize procurement/RCM/marketing, "
            "and re-rate at platform scale. The headwinds that repriced it are "
            "the vet-labor shortage (the growth constraint), demand "
            "normalization after the COVID boom, higher rates, and the FTC's "
            "arrival — the divestiture consent order signaled that local "
            "specialty/ER overlap will be scrutinized."),
        notable_players=[
            "Mars Veterinary Health (Banfield / VCA / BluePearl)",
            "National Veterinary Associates (JAB)",
            "Southern Veterinary Partners", "PetVet Care Centers (KKR)",
            "Thrive Pet Healthcare", "Mission Veterinary Partners",
            "VetCor", "IDEXX / Zoetis (diagnostics & pharma rails)",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Revenue per DVM", "the core productivity metric",
                "Output per veterinarian is the binding lever — doctors are the "
                "scarce input, so revenue scales with DVM capacity and productivity."),
            Kpi("Same-store growth (price × volume)", "mid-to-high single digit",
                "Now more price than volume post-COVID; the durability of price "
                "increases is the key underwriting question."),
            Kpi("Average client transaction (ACT)", "rising",
                "Ticket per visit; lifted by diagnostics attach, dentals, and "
                "specialty referral, and by price."),
            Kpi("Associate (DVM) compensation — ProSal", "~20-25% of production",
                "Production-based pay aligns doctors to output but is the largest "
                "controllable cost and the retention lever."),
            Kpi("Staff turnover (DVM + technician)", "the integration risk",
                "Doctor and tech attrition is the single biggest post-close risk "
                "in a labor-constrained roll-up."),
            Kpi("Clinic EBITDA margin", "~15-22% (GP); higher at scale/specialty",
                "Healthy for a services business; procurement and G&A leverage "
                "improve it at platform scale."),
        ],
        margin_profile=(
            "A veterinary clinic is a doctor-driven services business with a "
            "retail overlay: professional-services and surgical revenue plus "
            "diagnostics and product/pharmacy margin, against labor as the "
            "dominant cost. Because it is cash-pay, there is no reimbursement "
            "leakage — the practice collects what it charges — so margin is a "
            "function of doctor productivity (revenue per DVM), the diagnostics "
            "and specialty attach rate, and procurement/G&A leverage at scale. "
            "The constraint is not the top line but the input: a shortage of "
            "veterinarians caps volume and inflates associate compensation, so "
            "the margin story is ultimately a labor-availability and retention story."),
    ),
    risks=[
        Risk("Veterinarian labor shortage (the growth ceiling)", "High",
             "Too few DVMs caps volume growth and inflates compensation; you "
             "acquire doctors who can leave, making retention the core risk."),
        Risk("Demand normalization after the COVID pet-adoption boom", "Medium",
             "Visit volume softened in 2023-24; same-store growth now leans on "
             "price, whose durability is the underwriting question."),
        Risk("FTC antitrust scrutiny of roll-ups", "Medium",
             "Local specialty/ER overlap can force divestitures or block deals — "
             "the JAB/NVA-SAGE order set the precedent."),
        Risk("Price elasticity / discretionary deferral", "Medium",
             "Pet care is discretionary at the margin; as fees rise, clients "
             "defer or decline care, capping the price lever."),
        Risk("Multiple compression from 2021 peaks", "Medium",
             "Entry multiples ran to the high teens; a lower-growth, "
             "higher-rate environment reprices both entry and exit."),
        Risk("Pet-insurance-driven payer dynamics (long-run)", "Low",
             "If insurance penetration rises materially, payer-like pricing and "
             "utilization pressure could erode the cash-pay moat over time."),
    ],
    diligence_questions=[
        "What is revenue per DVM, and what is the DVM/technician staffing and "
        "vacancy position versus the growth plan?",
        "What is DVM and technician turnover, and how are non-competes and "
        "retention/earnout structures written?",
        "What is same-store growth decomposed into price versus volume, and how "
        "durable are the price increases?",
        "What is the mix of GP versus specialty/ER, and where is margin and "
        "consolidation risk concentrated?",
        "What is the local-market overlap in specialty/ER that could draw FTC "
        "review on the buy-and-build plan?",
        "How are clinics structured against state corporate-practice-of-veterinary "
        "-medicine rules (MSO where required)?",
        "What is the diagnostics and pharmacy attach rate, and the procurement "
        "leverage available at scale?",
        "What is the entry multiple versus the platform's realized organic and "
        "acquired growth — and the exit-multiple assumption?",
    ],
    insider_lens=[
        "Cash-pay is the whole thesis. No Medicare, no payer network, no "
        "Stark/AKS — the practice collects what it charges, which is why "
        "veterinary trades at consumer-health multiples, not provider ones. "
        "Protect that moat in the underwriting; it is the source of the returns.",
        "You are buying doctors, not clinics — and they can walk. The vet "
        "shortage makes DVM retention the entire integration risk; a clinic "
        "whose lead doctors leave post-close is worth a fraction of the model. "
        "Non-competes, ProSal alignment, and culture are the real diligence.",
        "Growth is capped by labor, not demand. Demand is abundant; the "
        "constraint is the supply of veterinarians and technicians. A roll-up's "
        "de novo and same-store ambitions live or die on hiring, not on the "
        "addressable market.",
        "The FTC has arrived. The SAGE/JAB divestiture ended the assumption that "
        "veterinary roll-ups fly under the antitrust radar — local specialty/ER "
        "overlap is now a gating item, and serial acquirers must map it deal by deal.",
        "Watch pet insurance carefully. It is low today, but if penetration "
        "climbs the way it has abroad, indemnity could tip toward "
        "network/managed dynamics — and the cash-pay pricing power that justifies "
        "today's multiples would face its first real payer.",
    ],
    connections=default_connections(
        "veterinary",
        deals_sector="veterinary",
        extra_pages=[
            ("/diligence/tam-sam?template=veterinary",
             "Veterinary deep-dive — sizing build + realized-deal history"),
        ],
        connectors=[
            ("census_acs_cbsa_profile",
             "Census ACS — household income & pet-owning demographics by CBSA"),
            ("bls_qcew_industry_area",
             "BLS QCEW — veterinary-services (NAICS 541940) wages & establishments"),
            ("npi_provider",
             "NPI Registry — cross-reference for co-located human/animal facilities"),
            ("cms_open_data_catalog",
             "CMS Open Data — adjacency reference (no federal vet payer exists)"),
        ],
    ),
    sources=[
        Source("American Pet Products Association (APPA) — State of the Industry "
               "/ pet-spending survey", "INDUSTRY", "https://www.americanpetproducts.org/"),
        Source("American Veterinary Medical Association (AVMA) — economic reports "
               "and workforce studies", "INDUSTRY", "https://www.avma.org/"),
        Source("FTC — In re JAB Consumer Partners / NVA-SAGE consent order "
               "(veterinary divestiture)", "GOV", "https://www.ftc.gov/"),
        Source("US BLS — Occupational Outlook / QCEW, veterinarians & veterinary "
               "services (NAICS 541940)", "GOV", "https://www.bls.gov/"),
        Source("Journal of the American Veterinary Medical Association (JAVMA) — "
               "workforce and consolidation research", "ACADEMIC",
               "https://avmajournals.avma.org/"),
        Source("PE Desk industry deep-dive (veterinary sizing) + realized-deal "
               "corpus", "INTERNAL", "/diligence/tam-sam?template=veterinary"),
    ],
    live_figures=live_figures_from_dive("veterinary"),
    trends=(
        "Veterinary spent the last decade as one of healthcare's favorite "
        "roll-ups, and the trajectory now bends around three forces. First, the "
        "cash-pay, recession-resilient, humanization-driven thesis pushed entry "
        "multiples to the high teens by 2021 as Mars and a dozen sponsor-backed "
        "platforms consolidated a fragmented base — most aggressively in "
        "specialty and emergency care. Second, the COVID pet-adoption boom "
        "pulled demand forward, and as it normalized in 2023-24 visit volume "
        "softened even as price held, shifting same-store growth from a volume "
        "story to a price story and testing elasticity. Third, two constraints "
        "hardened the outlook: the structural shortage of veterinarians became "
        "the binding limit on growth (and the core integration risk, since a "
        "clinic is really its doctors), and the FTC entered the sector, ordering "
        "divestitures and signaling that local specialty/ER overlap will be "
        "scrutinized. The forward question is whether the cash-pay pricing power "
        "that justifies the multiples endures as demand normalizes, labor stays "
        "tight, and pet-insurance penetration slowly rises toward payer-like dynamics."),
    growth_levers=[
        GrowthLever(
            "Pet humanization (spend per pet)",
            "Owners treat pets as family and buy more, and more advanced, medical "
            "care per animal — the durable secular tailwind.",
            "+4-6%/yr spend per pet", "ILLUSTRATIVE"),
        GrowthLever(
            "Services price inflation (pricing power)",
            "Cash-pay with no fee schedule lets practices raise prices; the "
            "primary same-store lever post-COVID, bounded by elasticity.",
            "+5-8%/yr on price", "ILLUSTRATIVE"),
        GrowthLever(
            "Specialty & advanced-care adoption",
            "Oncology, orthopedics, cardiology, and ER expand the reachable "
            "ticket per pet and carry higher margin than GP.",
            "mix up-shift", "ILLUSTRATIVE"),
        GrowthLever(
            "Pet-insurance penetration",
            "Rising (still low) insurance uptake unlocks larger spend by reducing "
            "the owner's out-of-pocket shock — a demand unlock, with long-run "
            "payer risk attached.",
            "demand unlock", "ILLUSTRATIVE"),
        GrowthLever(
            "Veterinarian labor supply (a negative constraint)",
            "The DVM/technician shortage caps volume growth and inflates "
            "compensation — the ceiling on how fast the sector can scale.",
            "growth ceiling", "ILLUSTRATIVE"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Pet population × humanized spend per pet, gated by DVM supply",
        analysis=(
            "Demand is the product of the pet population and how much owners "
            "spend on medical care per animal. The pet base stepped up during "
            "the COVID adoption boom and the humanization trend keeps lifting "
            "spend per pet — more preventive care, more diagnostics, more "
            "willingness to pursue specialty and emergency treatment that owners "
            "once declined. That makes underlying demand strong and only "
            "moderately cyclical. But the driver that actually governs realized "
            "volume is supply-side: there are not enough veterinarians and "
            "technicians to serve the demand, so appointment capacity — not "
            "client interest — sets the ceiling. This is the inversion that makes "
            "veterinary unusual: demand is abundant and the constraint is labor, "
            "so the operative question for growth is hiring and retention, and "
            "the post-COVID volume softening is a normalization off a "
            "pulled-forward peak, not a demand collapse."),
        basis="ILLUSTRATIVE"),
    cost_drivers=[
        CostDriver(
            "Veterinarian & staff labor (incl. ProSal)",
            "~45-55% of cost",
            "Doctors and technicians are the dominant cost and the scarce input; "
            "production-based DVM pay plus support staff — the binding constraint "
            "on both margin and growth.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Drugs, supplies & diagnostics (COGS)",
            "~20-25% of cost",
            "Pharmacy, parasiticides, consumables, and reference-lab spend; "
            "procurement leverage at platform scale is a core synergy.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Occupancy & equipment",
            "~8-12% of cost",
            "Clinic real estate, imaging, surgical, and dental equipment; de "
            "novo build-out capex where the platform grows organically.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Marketing & client acquisition",
            "~4-8% of cost",
            "New-client growth and retention programs; lower than most consumer "
            "verticals given local reputation and referral dynamics.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Corporate G&A / platform overhead",
            "~6-10% of cost",
            "Management-company overhead, RCM-equivalent billing, and integration "
            "cost — the layer scale is meant to leverage down.",
            "ILLUSTRATIVE"),
    ],
    state_breakdown=None,
    cms_trend=None,
)

register(REPORT)
