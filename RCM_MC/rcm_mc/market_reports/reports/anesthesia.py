"""Anesthesia — the case-coverage staffing model repriced by the No Surprises Act.

Deals-only deep-dive (no national physician-practice facility file; ASA workforce
data is aggregate-only, so geography is omitted rather than fabricated). Anesthesia
is the specialty most reshaped by the No Surprises Act: PE-backed platforms built
value on out-of-network balance-billing leverage that the NSA eliminated in 2022,
turning the business into a labor-intensive, subsidy-dependent case-coverage model.
The qualitative sections are authored around the base-plus-time unit payment math,
the care-team (MD medically directing CRNAs) staffing structure, the hospital
stipend/subsidy dynamic, and the FTC antitrust scrutiny of anesthesia roll-ups.
Consumes ``anesthesia_deep_dive()`` for SOURCED corpus deal figures.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="anesthesia",
    name="Anesthesia",
    care_setting="Physician services",
    naics="621111",
    one_line_def=(
        "Physician and CRNA anesthesia services covering surgical and procedural "
        "cases across hospital ORs, ambulatory surgery centers, obstetrics, GI "
        "endoscopy, and non-OR sites — paid on a base-plus-time unit schedule, "
        "staffed through a care-team model, and, since the No Surprises Act, "
        "increasingly dependent on hospital subsidies rather than out-of-network "
        "billing leverage."),
    tam_headline=TamHeadline(
        value=28.0, unit="$B", growth_pct=3.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "Modeled from the ~42,000-45,000 practicing US anesthesiologists and "
            "~55,000-60,000 CRNAs (ASA / AANA workforce, directional) times the "
            "professional and facility-subsidy revenue per anesthetizing location "
            "— not a single published figure. Growth is the modeled composite of "
            "surgical/procedural case-volume growth and ASC migration, net of the "
            "No Surprises Act out-of-network repricing and MPFS anesthesia "
            "conversion-factor drag."),
    ),
    executive_summary=[
        "The No Surprises Act repriced the whole model. PE platforms built value "
        "on out-of-network balance-billing leverage; the NSA (effective 2022) "
        "banned surprise billing and routed disputes to an arbitration (IDR) "
        "process benchmarked to the qualifying payment amount — collapsing the "
        "OON premium that funded many roll-ups.",
        "Anesthesia is a coverage business, not a volume business. A group "
        "commits to staff every anesthetizing location a facility runs, 24/7, "
        "including money-losing obstetric and trauma coverage — so the economics "
        "are labor cost against a payer mix the group does not control.",
        "The result is subsidy dependence. When commercial rates plus a "
        "Medicare/Medicaid-heavy payer mix do not cover the cost of coverage, "
        "the group requires a stipend/subsidy from the hospital — and post-NSA "
        "those subsidy demands have surged, making the hospital contract the "
        "central asset and risk.",
        "Payment is base units + time units. Medicare pays (ASA base units + "
        "15-minute time units + modifiers) × a low anesthesia conversion factor "
        "(~$20/unit, far below the main MPFS CF); commercial pays a multiple. "
        "Value is the commercial rate × case volume × the subsidy, minus a "
        "clinician labor line that is nearly the entire cost.",
        "The care-team model is the labor lever. An anesthesiologist medically "
        "directing up to four CRNAs (or supervising more) sets the cost per "
        "location; CRNA scope-of-practice and state supervision opt-outs are "
        "first-order economic variables, not clinical footnotes.",
        "Antitrust caught up to the roll-up. The FTC's 2023 case against US "
        "Anesthesia Partners and Welsh Carson put physician-staffing "
        "consolidation on notice, and Envision's 2023 bankruptcy is the "
        "cautionary tale for leverage plus NSA exposure.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Facility (hospital / ASC) contracts a group to cover all "
            "anesthetizing locations",
            "Pre-anesthesia evaluation + risk stratification (ASA physical "
            "status)",
            "Case coverage — general, regional, MAC, or obstetric anesthesia by "
            "the care team",
            "Intraoperative management + post-anesthesia recovery (PACU) "
            "oversight",
            "Charge capture — base units + time units + modifiers, coded to the "
            "case",
            "Billing at the commercial multiple / Medicare CF, plus any hospital "
            "stipend true-up",
            "Chronic pain / interventional line where the group runs it (overlaps "
            "pain management)",
        ],
        sites_of_care=[
            "Hospital operating rooms (the coverage core, including trauma/OB)",
            "Ambulatory surgery centers (the growth site — ASC case migration)",
            "Obstetric suites (labor epidurals — 24/7, low-margin coverage)",
            "Non-OR anesthesia (NORA) — GI endoscopy, cath lab, radiology, EP",
            "Office-based anesthesia (dental, plastics, GI)",
            "Chronic-pain / interventional suites (where the group runs pain)",
        ],
        money_flow=(
            "Anesthesia is paid on a unit schedule unlike any other specialty: "
            "Medicare pays (ASA base units for the procedure + time units of "
            "15 minutes each + any modifying units) multiplied by a dedicated "
            "anesthesia conversion factor that is far lower than the main "
            "physician-fee-schedule conversion factor (roughly $20 per unit). "
            "Commercial payers pay a multiple of that. The care-team model sets "
            "the cost: an anesthesiologist can medically direct up to four "
            "concurrent CRNAs (billed with the QK/QX medical-direction modifiers) "
            "or supervise more, and a CRNA practicing without medical direction "
            "bills with the QZ modifier. Because a group contracts to cover every "
            "anesthetizing location a facility runs — including unprofitable "
            "obstetric and trauma coverage — the revenue is a payer mix the group "
            "does not control against a clinician labor cost that is nearly the "
            "entire expense. When that gap is negative, the hospital pays a "
            "stipend/subsidy to keep the coverage. In the PE structure the "
            "management company centralizes billing and staffing across many "
            "contracts, so platform value is the portfolio of commercial rates, "
            "subsidies, and labor cost — not a single P&L."),
        key_players=(
            "Large PE-backed and physician-owned groups dominate the scaled tier: "
            "North American Partners in Anesthesia (NAPA), US Anesthesia Partners "
            "(Welsh Carson), NorthStar Anesthesia, Somnia, and the anesthesia "
            "lines inside multispecialty staffers TeamHealth and the "
            "now-restructured Envision. On the labor side, CRNAs (represented by "
            "the AANA) and anesthesiologist assistants are the care-team staff "
            "whose scope-of-practice rules move the cost curve. Hospitals and ASC "
            "chains are the counterparties whose subsidies increasingly determine "
            "group profitability. Independent single-hospital and regional groups "
            "are the acquirable pool."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Practicing US anesthesiologists", "~42,000-45,000",
                    "INDUSTRY · ASA workforce (directional)"),
            Segment("Practicing US CRNAs", "~55,000-60,000",
                    "INDUSTRY · AANA workforce (directional)"),
            Segment("Medicare anesthesia conversion factor", "~$20 / unit",
                    "GOV · CMS Anesthesia Conversion Factor (annual PFS Final "
                    "Rule)"),
            Segment("States with CRNA supervision opt-out", "~20+ states",
                    "GOV · CMS Part A Conditions of Participation opt-out list"),
            Segment("Share of revenue from hospital subsidy (post-NSA)",
                    "rising / group-dependent",
                    "ILLUSTRATIVE · post-No-Surprises-Act stipend dynamics, "
                    "directional"),
        ],
        growth_drivers=[
            "Surgical + procedural case-volume growth ~2-3%/yr (aging demand)",
            "ASC and non-OR anesthesia (NORA) case migration expanding sites",
            "Hospital subsidy/stipend growth backfilling the NSA repricing",
            "CRNA-leverage labor substitution lowering cost per location",
            "No Surprises Act out-of-network repricing — the offsetting headwind",
            "MPFS anesthesia conversion-factor drift — a flat-to-declining rate",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Commercial": 0.46,
            "Medicare / MA": 0.34,
            "Medicaid": 0.14,
            "Self-pay / other": 0.06,
        },
        rate_mechanics=[
            "Base-plus-time units — (ASA base units by procedure + 15-minute time "
            "units + modifying units) × the anesthesia conversion factor; the "
            "Medicare CF (~$20/unit) is far below the main MPFS conversion factor.",
            "Care-team modifiers — AA (personally performed), QK/QX (medical "
            "direction of 2-4 concurrent CRNAs), AD (supervision of >4), and QZ "
            "(CRNA without medical direction) set both payment and the labor cost "
            "structure.",
            "No Surprises Act — bans balance-billing for OON emergency and "
            "facility-based anesthesia; disputes go to Independent Dispute "
            "Resolution benchmarked to the Qualifying Payment Amount (QPA), "
            "collapsing the OON leverage that funded many platforms.",
            "Hospital stipend / subsidy — a negotiated true-up when commercial "
            "rates and the payer mix do not cover the cost of contracted "
            "coverage; increasingly the swing variable in group profitability.",
            "CRNA supervision opt-out — states may opt out of the Medicare "
            "physician-supervision requirement for CRNAs, changing the legal "
            "staffing ratio and the cost per anesthetizing location.",
            "Commercial multiple of Medicare — the rate engine; post-NSA it is "
            "negotiated in-network under IDR/QPA pressure rather than won through "
            "out-of-network billing.",
        ],
        reimbursement_risk=(
            "The No Surprises Act is the defining reimbursement risk: it removed "
            "the out-of-network balance-billing leverage that anesthesia (with "
            "radiology and emergency medicine) relied on, and the IDR process is "
            "benchmarked to a Qualifying Payment Amount that the payer largely "
            "sets — repeated litigation (the Texas Medical Association cases) has "
            "reshaped the QPA methodology but not restored the old economics. The "
            "second risk is the subsidy: post-NSA, groups increasingly depend on "
            "hospital stipends to cover money-losing obstetric and trauma "
            "coverage, so a subsidy that is under-negotiated, expiring, or at a "
            "financially stressed hospital is an existential exposure. Layered on "
            "top are the low, flat-to-declining anesthesia conversion factor and "
            "the labor market for anesthesiologists and CRNAs, whose wage "
            "inflation and locum premiums directly compress a business that is "
            "almost entirely clinician labor cost."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("No Surprises Act (2022) + IDR / QPA",
                 "Banned surprise out-of-network billing for facility-based "
                 "anesthesia and routed disputes to arbitration benchmarked to "
                 "the Qualifying Payment Amount — the single event that repriced "
                 "the PE anesthesia thesis.",
                 "https://www.cms.gov/nosurprises"),
            Rule("Medicare anesthesia payment + conversion factor (annual PFS "
                 "Final Rule)",
                 "Sets the base/time unit values and the dedicated anesthesia "
                 "conversion factor — the low unit price that anchors the fee "
                 "schedule.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
            Rule("Medical-direction rules (TEFRA 7 conditions, 42 CFR 415.110)",
                 "Governs when an anesthesiologist may bill for medically "
                 "directing concurrent CRNAs — the legal basis of the care-team "
                 "cost structure.",
                 "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-415"),
            Rule("CRNA supervision opt-out (Medicare CoP)",
                 "States may opt out of the physician-supervision requirement for "
                 "CRNAs, changing the staffing ratio and cost per anesthetizing "
                 "location — a scope-of-practice economic lever.",
                 "https://www.cms.gov/medicare/regulations-guidance/manuals"),
            Rule("FTC v. US Anesthesia Partners / Welsh Carson (2023)",
                 "The marquee antitrust challenge to physician-staffing roll-ups; "
                 "put anesthesia consolidation and serial-acquisition strategy on "
                 "notice even though the sponsor was largely dismissed.",
                 "https://www.ftc.gov/legal-library/browse/cases-proceedings/us-anesthesia-partners"),
            Rule("Anti-Kickback Statute + corporate practice of medicine",
                 "Governs the MSO / friendly-PC structure, exclusive facility "
                 "contracts, and any subsidy arrangement's fair-market-value "
                 "posture.",
                 "https://oig.hhs.gov/compliance/advisory-opinions/"),
        ],
        policy_watch=[
            "No Surprises Act IDR/QPA litigation and rule revisions (Texas "
            "Medical Association line of cases) and IDR backlog",
            "FTC / DOJ antitrust posture on physician-staffing and serial "
            "roll-ups",
            "CRNA scope-of-practice and additional state supervision opt-outs",
            "Hospital financial stress and subsidy sustainability",
            "Annual MPFS / anesthesia conversion-factor cuts and the 'doc fix'",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "US anesthesia spans a large tail of independent single-hospital and "
            "regional physician groups, a set of scaled PE-backed and "
            "physician-owned national platforms, and hospital-employed "
            "departments. Consolidation ran hard through the 2010s on "
            "out-of-network billing leverage; the No Surprises Act reset the "
            "logic, and the acquirable pool is now the independent group whose "
            "value is a defensible in-network commercial book and a workable "
            "hospital subsidy — not billing arbitrage."),
        hhi_or_share=(
            "No single owner is dominant nationally; concentration is local and "
            "contract-specific, which is exactly what the FTC's US Anesthesia "
            "Partners case probed. No vendored physician-staffing roll captures "
            "operator concentration, so a national chain HHI is honestly omitted "
            "— the corpus deal history below is the real read."),
        consolidation=(
            "The 2010s roll-up (NAPA, US Anesthesia Partners, Envision, "
            "TeamHealth) was built substantially on out-of-network balance-billing "
            "leverage and scale over payers. The No Surprises Act removed the OON "
            "lever, Envision filed for bankruptcy in 2023 under leverage plus NSA "
            "exposure, and the FTC challenged the US Anesthesia Partners strategy "
            "— so the consolidation thesis shifted from billing arbitrage toward "
            "operational efficiency, CRNA-leverage labor management, and defensible "
            "hospital subsidies."),
        pe_activity=(
            "Anesthesia was one of the most PE-active staffing verticals of the "
            "2010s and is now one of the most scrutinized. Diligence centers on "
            "NSA/QPA exposure, the durability and fair-market-value posture of "
            "hospital subsidies, CRNA-leverage staffing economics, and antitrust "
            "and physician-retention risk rather than the out-of-network billing "
            "that once drove returns."),
        notable_players=[
            "North American Partners in Anesthesia (NAPA)",
            "US Anesthesia Partners (Welsh Carson)", "NorthStar Anesthesia",
            "Somnia Anesthesia", "TeamHealth (anesthesia line)",
            "Envision Healthcare (restructured — cautionary tale)",
            "AANA (CRNA workforce / scope-of-practice)",
            "American Society of Anesthesiologists (ASA)",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Subsidy / stipend per anesthetizing location", "group-dependent",
                "The swing variable post-NSA; the gap between the cost of "
                "coverage and what the payer mix yields, backfilled by the "
                "hospital."),
            Kpi("Care-team ratio (MD : CRNA)", "up to 1:4 medical direction",
                "Sets the labor cost per location; higher CRNA leverage lowers "
                "cost where scope-of-practice and facilities allow."),
            Kpi("ASA units per case (base + time)", "procedure + duration",
                "The billing unit; case mix and case length drive units, but the "
                "conversion factor is low, so commercial rate and volume matter "
                "more."),
            Kpi("Commercial % of payer mix", "~40-50%",
                "The rate engine; post-NSA it is negotiated in-network rather than "
                "won out-of-network, so the commercial book's durability is the "
                "value."),
            Kpi("Anesthetizing-location utilization", "cases per site per day",
                "A coverage commitment is a fixed cost; idle or low-volume "
                "locations bleed the group unless subsidized."),
            Kpi("Platform EBITDA margin (post-MSO)", "8-15% (illustrative)",
                "Lower than ancillary-rich specialties — anesthesia is almost "
                "entirely clinician labor cost, with subsidy determining the "
                "swing."),
        ],
        margin_profile=(
            "Anesthesia economics are unusual: there is almost no ancillary stack "
            "and almost no capital base — the business is clinician labor "
            "committed to cover a facility's anesthetizing locations. Contribution "
            "is the commercial rate times case volume, plus any hospital subsidy, "
            "minus a labor cost (anesthesiologists, CRNAs, and locums) that is "
            "nearly the entire expense. The care-team ratio is the main lever: "
            "more CRNA leverage lowers cost per location where scope-of-practice "
            "and facility policy permit. Because the group cannot control the "
            "payer mix on a coverage contract, obstetric and trauma coverage "
            "often run at a loss and the hospital subsidy makes the contract "
            "whole. Post-No-Surprises-Act, with the out-of-network premium gone, "
            "margin is thin and subsidy-dependent — the quality of a platform is "
            "the durability of its commercial rates and its subsidies, not a "
            "product mix."),
    ),
    risks=[
        Risk("No Surprises Act / QPA out-of-network repricing", "High",
             "The NSA removed the balance-billing leverage the roll-up thesis was "
             "priced on; IDR/QPA outcomes cap the in-network alternative."),
        Risk("Hospital subsidy dependence / renegotiation", "High",
             "Post-NSA profitability rests on stipends; an expiring, "
             "under-negotiated, or financially stressed-hospital subsidy is an "
             "existential exposure."),
        Risk("Clinician labor cost + locum premium", "High",
             "The business is almost entirely anesthesiologist and CRNA labor; "
             "wage inflation and locum reliance directly compress a thin margin."),
        Risk("Antitrust scrutiny of physician-staffing roll-ups", "Medium",
             "The FTC's US Anesthesia Partners case put serial acquisition and "
             "local concentration on notice."),
        Risk("Physician / CRNA retention and coverage gaps", "Medium",
             "Losing anesthetists breaks coverage commitments and forces "
             "expensive locum backfill or contract loss."),
        Risk("MPFS anesthesia conversion-factor erosion", "Medium",
             "A structurally low, flat-to-declining unit price with no inflation "
             "update squeezes the Medicare/Medicaid slice."),
    ],
    diligence_questions=[
        "What is the NSA/QPA exposure by contract — how much historical revenue "
        "came from out-of-network billing, and what are the IDR outcomes and "
        "backlog?",
        "What is the hospital subsidy by facility — size, term, renewal date, "
        "fair-market-value support, and the counterparty's financial health?",
        "What is the care-team ratio and CRNA-leverage mix by site, and how much "
        "does it depend on state scope-of-practice / supervision opt-out?",
        "What is the commercial-rate position and contract durability post-NSA, "
        "and how concentrated is the top-payer exposure?",
        "What is the locum reliance and clinician-vacancy rate, and what is the "
        "premium-labor cost trend?",
        "What is the antitrust posture given local concentration and the group's "
        "acquisition history?",
        "What is the case-mix and anesthetizing-location utilization, and how "
        "many locations run below break-even without subsidy?",
        "What is the physician-retention and compensation structure post-close, "
        "and how exposed is coverage to key-anesthetist departure?",
    ],
    insider_lens=[
        "The No Surprises Act broke the old thesis. A generation of anesthesia "
        "roll-ups monetized out-of-network balance billing; the NSA banned it and "
        "benchmarked disputes to a payer-set QPA. Any platform still priced on "
        "OON leverage is priced on a business that no longer exists.",
        "Anesthesia is a coverage commitment, not a fee-for-service practice. The "
        "group agrees to staff every location a facility runs, 24/7, including "
        "money-losing OB and trauma — so it owns a labor cost against a payer mix "
        "it cannot choose. The subsidy is what closes the gap.",
        "The hospital stipend is the real asset now. Post-NSA, group profit lives "
        "in the subsidy — its size, its term, and the hospital's ability to pay. "
        "Underwrite the subsidy book like a contract portfolio, because that is "
        "what it is.",
        "The care-team ratio is the cost curve. Medical direction of up to four "
        "CRNAs, or supervision of more, sets cost per location — so CRNA "
        "scope-of-practice and each state's Medicare supervision opt-out are "
        "economic variables, not clinical trivia.",
        "The conversion factor is a trap for the unwary. Anesthesia's Medicare "
        "unit price is far below the main fee schedule, so Medicare/Medicaid "
        "coverage is often below cost — the commercial book and the subsidy carry "
        "the whole business.",
        "Envision and the FTC are the two warnings. Envision's bankruptcy showed "
        "what leverage plus NSA exposure does; the FTC's US Anesthesia Partners "
        "case showed that local roll-up concentration is now an antitrust target. "
        "Both reprice the diligence, not just the model.",
    ],
    connections=default_connections(
        "anesthesia",
        deals_sector="anesthesia",
        extra_pages=[
            ("/industry/anesthesia",
             "Industry deep-dive — anesthesia deal history + NSA/subsidy read"),
        ],
        connectors=[
            ("npi_provider_taxonomy",
             "NPI taxonomy — anesthesiology, CRNA & anesthesiologist-assistant "
             "specialty mix and enrollment"),
            ("cms_open_data_mup_physician_by_provider_service",
             "Medicare physician utilization — anesthesia units, allowed charges "
             "& care-team modifier mix"),
            ("provider_data_asc_quality_facility",
             "CMS ASC quality file — ambulatory surgery-center footprint (the "
             "coverage sites)"),
            ("provider_data_hospital_general",
             "CMS Hospital General Information — hospital OR counterparties for "
             "coverage contracts & subsidies"),
            ("open_payments_general_payments_2024",
             "Open Payments — industry payments to anesthesiologists "
             "(relationship screen)"),
            ("bls_qcew_area_industry",
             "BLS QCEW — physician-office wage/employment base for anesthesia "
             "labor-cost mapping"),
        ],
    ),
    sources=[
        Source("American Society of Anesthesiologists (ASA) — workforce, "
               "Relative Value Guide, and payment advocacy", "INDUSTRY",
               "https://www.asahq.org/"),
        Source("American Association of Nurse Anesthesiology (AANA) — CRNA "
               "workforce and scope-of-practice", "INDUSTRY",
               "https://www.aana.com/"),
        Source("CMS — No Surprises Act / Independent Dispute Resolution", "GOV",
               "https://www.cms.gov/nosurprises"),
        Source("CMS — Medicare Physician Fee Schedule annual Final Rule "
               "(anesthesia conversion factor, base/time units)", "GOV",
               "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
        Source("FTC — In the Matter of U.S. Anesthesia Partners / Welsh Carson "
               "(2023 complaint)", "GOV",
               "https://www.ftc.gov/legal-library/browse/cases-proceedings/us-anesthesia-partners"),
        Source("Medical-direction rules — TEFRA seven conditions (42 CFR "
               "415.110)", "GOV",
               "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-415"),
        Source("PE Desk industry deep-dive (anesthesia) + realized-deal corpus",
               "INTERNAL",
               "/diligence/tam-sam?template=anesthesia"),
    ],
    live_figures=live_figures_from_dive("anesthesia"),
    trends=(
        "Anesthesia is the specialty most reshaped by a single policy event. "
        "Through the 2010s, PE-backed platforms (NAPA, US Anesthesia Partners, "
        "Envision, TeamHealth) consolidated groups substantially on out-of-network "
        "balance-billing leverage and scale over payers. The No Surprises Act, "
        "effective 2022, banned surprise billing for facility-based anesthesia and "
        "routed disputes to an Independent Dispute Resolution process benchmarked "
        "to a payer-influenced Qualifying Payment Amount — collapsing the OON "
        "premium that funded the roll-up. The consequences cascaded: Envision "
        "filed for bankruptcy in 2023 under leverage plus NSA exposure, and the "
        "FTC sued US Anesthesia Partners and Welsh Carson, putting serial "
        "acquisition and local concentration on notice. The business that remains "
        "is a coverage commitment — staff every anesthetizing location a facility "
        "runs, including money-losing obstetric and trauma coverage — whose "
        "profitability increasingly depends on hospital subsidies rather than "
        "billing arbitrage. Underneath, case volume grows with aging surgical "
        "demand and migrates toward the ASC and non-OR sites, and CRNA-leverage "
        "labor management is the main cost lever, but the anesthesia conversion "
        "factor stays structurally low. Quality-of-earnings work now centers on "
        "NSA/QPA exposure, subsidy durability, and labor cost."),
    growth_levers=[
        GrowthLever(
            "Surgical + procedural case-volume growth",
            "Aging demand and rising procedure rates expand the number of cases "
            "requiring anesthesia coverage.",
            "+2-3%/yr cases", "ILLUSTRATIVE"),
        GrowthLever(
            "ASC + non-OR anesthesia (NORA) migration",
            "Cases moving to ambulatory surgery centers, GI endoscopy, cath labs, "
            "and imaging expand the number of anesthetizing locations to staff.",
            "+ sites of care", "ILLUSTRATIVE"),
        GrowthLever(
            "Hospital subsidy / stipend growth",
            "Post-NSA, hospitals backfill the gap between coverage cost and payer "
            "yield with stipends — a growing revenue line and the swing variable.",
            "+ subsidy revenue", "ILLUSTRATIVE"),
        GrowthLever(
            "CRNA-leverage labor substitution",
            "Higher CRNA-to-MD ratios and scope-of-practice opt-outs lower cost "
            "per anesthetizing location where facilities permit.",
            "cost lever", "ILLUSTRATIVE"),
        GrowthLever(
            "No Surprises Act out-of-network repricing",
            "The NSA removed the balance-billing leverage the roll-up thesis was "
            "priced on, capping the in-network alternative via IDR/QPA.",
            "primary headwind", "GOV"),
        GrowthLever(
            "MPFS anesthesia conversion-factor drag",
            "A structurally low, flat-to-declining unit price with no inflation "
            "update squeezes the government-payer slice.",
            "rate headwind", "GOV"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Surgical & procedural case volume (aging demand × ASC/NORA "
               "migration)",
        analysis=(
            "Anesthesia demand is derived, not primary: it tracks the number of "
            "surgical and procedural cases that require anesthesia coverage, which "
            "grows with an aging population's rising rate of operations, endoscopy, "
            "and interventional procedures. The important structural shift is site "
            "migration — cases moving from the hospital OR into ambulatory surgery "
            "centers and into non-OR anesthesia settings (GI endoscopy, cath and "
            "EP labs, interventional radiology) — which multiplies the number of "
            "anesthetizing locations a group must staff and changes the payer and "
            "acuity mix. Critically, more volume is not automatically more profit: "
            "because the business is a coverage commitment paid on a low unit "
            "schedule against a payer mix the group does not control, incremental "
            "cases only add margin where the commercial rate and any subsidy cover "
            "the clinician labor to staff the location. The demand curve is "
            "reliable; the economics turn on rate and subsidy, not case count."),
        basis="ILLUSTRATIVE"),
    cost_drivers=[
        CostDriver(
            "Anesthesiologist compensation", "~35-45% of cost",
            "The senior clinical labor; medical-direction ratios and physician "
            "comp set the largest cost line.", "ILLUSTRATIVE"),
        CostDriver(
            "CRNA + anesthesiologist-assistant compensation", "~25-35% of cost",
            "The care-team staff; CRNA leverage lowers cost per location, but "
            "CRNA wage inflation is a direct margin pressure.", "ILLUSTRATIVE"),
        CostDriver(
            "Locum / premium labor", "cyclical / can spike",
            "Backfilling coverage gaps with locums carries a steep premium and is "
            "the fastest way a coverage contract goes underwater.", "ILLUSTRATIVE"),
        CostDriver(
            "Billing / RCM + MSO overhead", "~8-12% of cost",
            "Unit-based anesthesia billing and the shared-services and "
            "compliance apparatus across many contracts.", "ILLUSTRATIVE"),
        CostDriver(
            "Malpractice + benefits", "~5-10% of cost",
            "Professional liability and clinician benefits on a labor-heavy cost "
            "base.", "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "No national physician-staffing facility file is vendored — an anesthesia "
        "group is a coverage contract, not a Medicare-certified facility — and ASA "
        "workforce data is aggregate-only, so state geography is omitted rather "
        "than fabricated. The most consequential geographic variables are the "
        "state CRNA supervision opt-out (which changes the legal care-team ratio "
        "and the cost per anesthetizing location), the corporate-practice-of- "
        "medicine doctrine (strong-CPOM states force the friendly-PC/MSO "
        "structure), and the growing list of states enacting PE-in-healthcare "
        "transaction-review laws. The NPI-taxonomy, Medicare physician-utilization, "
        "ASC-quality, hospital, and labor-cost connectors linked below map "
        "anesthesia supply, care-team modifier mix, and the surgical facilities "
        "that generate coverage contracts — the honest footprint read."),
)

register(REPORT)
