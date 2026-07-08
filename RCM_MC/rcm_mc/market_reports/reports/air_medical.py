"""Air Medical — helicopter (rotor) and fixed-wing air ambulance transport.

Deals-only market-report module (no vendored air-base facility file, so no
computed state_breakdown or supply trend). The qualitative sections are authored
around the single event that broke the sector's economics: the No Surprises Act
(2022) ended the out-of-network balance-billing / arbitrage model that the whole
PE thesis was priced on — and Air Methods, the largest independent operator,
filed Chapter 11 in 2023. Read the corpus trade history as a broken playbook.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver, default_connections,
    live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="air_medical",
    name="Air Medical",
    care_setting="Other services",
    naics="621910",
    one_line_def=(
        "Air ambulance — helicopter (rotor-wing) scene response and "
        "hospital-to-hospital transfer plus fixed-wing long-distance medical "
        "transport — a very-high-fixed-cost service whose economics were reset "
        "when the No Surprises Act ended out-of-network balance billing."),
    tam_headline=TamHeadline(
        value=6.0, unit="$B", growth_pct=3.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "Modeled total US air-ambulance revenue (~550K+ transports/yr). No "
            "clean all-payer figure exists, and the revenue base was repriced "
            "downward by the No Surprises Act; the GOV anchors are Medicare "
            "air-ambulance fee-schedule spend and GAO air-ambulance charge "
            "studies. Growth is modeled and structurally constrained."),
    ),
    executive_summary=[
        "The entire pre-2022 PE thesis was balance-billing arbitrage: fly the "
        "patient out-of-network, bill $30-50K, and settle high. The No Surprises "
        "Act ended it — disputes now run through federal Independent Dispute "
        "Resolution (IDR) anchored to a qualifying payment amount. The old "
        "revenue engine is gone.",
        "Air Methods — the largest independent operator, PE-owned — filed "
        "Chapter 11 in 2023 under the combined weight of the NSA repricing and "
        "its debt load. That bankruptcy is the sector's defining event and the "
        "clearest warning against re-underwriting the old model.",
        "This is a fixed-cost business with an uncomfortable demand base: "
        "aircraft, pilots, clinical crews, and 24/7 bases cost the same whether "
        "they fly or not, and there is structural helicopter OVERCAPACITY — too "
        "many bases chasing too few appropriate flights.",
        "Membership/subscription programs (a quasi-insurance hedge against "
        "balance bills) and the medical necessity of each flight are both under "
        "scrutiny — state insurance regulators on the former, payers and "
        "auditors on the latter (was air transport justified over ground?).",
        "Post-NSA value is about in-network contracting, IDR win rates, base "
        "rationalization, and hospital-based partnerships — not the OON premium. "
        "Nonprofit hospital-affiliated programs enter this era with structurally "
        "better payer relationships than the independent for-profit fleets.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Activation — 911 scene call or hospital interfacility transfer request",
            "Medical-necessity / mode decision (air vs ground; autolaunch protocols)",
            "Dispatch of rotor-wing (scene/short) or fixed-wing (long-distance)",
            "Clinical transport by flight crew (nurse/paramedic; sometimes physician)",
            "Delivery to a higher level of care (trauma/PCI/stroke/NICU center)",
            "Billing — Medicare AFS air rate, then commercial IDR/negotiation",
            "IDR arbitration or in-network settlement; membership offset if enrolled",
        ],
        sites_of_care=[
            "Rotor-wing scene response (trauma / rural emergency)",
            "Rotor-wing interfacility transfer (to trauma/cardiac/stroke centers)",
            "Fixed-wing long-distance transport (cross-region, repatriation)",
            "Neonatal / pediatric specialty transport (highest-acuity teams)",
            "Hospital-based air programs (nonprofit/affiliated, better payer mix)",
        ],
        money_flow=(
            "Medicare pays air ambulance under the Ambulance Fee Schedule at "
            "fixed rotary-wing and fixed-wing base rates plus statutory mileage — "
            "far below billed charges. The economic model historically depended "
            "on commercial payers: providers stayed out-of-network, billed very "
            "high charges, and balance-billed the patient for the difference. The "
            "No Surprises Act (2022) ended that — air ambulance IS covered — so "
            "out-of-network commercial disputes now go to federal Independent "
            "Dispute Resolution, where an arbiter picks an amount benchmarked to "
            "the qualifying payment amount. Membership/subscription programs "
            "collect a small annual fee to waive the patient's residual, a hedge "
            "rather than a profit center. The result: revenue per transport "
            "compressed sharply, and the high fixed cost per base did not."),
        key_players=(
            "Global Medical Response (KKR) is the scaled consolidator, spanning "
            "Air Evac Lifeteam, Med-Trans, REACH, and Guardian plus the AirMedCare "
            "Network membership program. Air Methods — long the largest "
            "independent, previously PE-owned — restructured through Chapter 11 in "
            "2023. PHI Air Medical is another national operator. The rest is "
            "hospital-based and nonprofit-affiliated programs (often the "
            "best-positioned post-NSA) and regional fleets. The acquirable pool "
            "is the independent for-profit fleets — the same assets whose model "
            "the NSA broke."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("US air-medical transports per year",
                    "~550K+ transports",
                    "INDUSTRY · air-medical association / GAO estimates"),
            Segment("Rotor-wing vs fixed-wing",
                    "rotor dominates scene/interfacility; fixed-wing long-haul",
                    "INDUSTRY · fleet composition"),
            Segment("Total US air-ambulance revenue (post-NSA)",
                    "~$6B (modeled, repriced down)",
                    "ILLUSTRATIVE · all-payer build post-No-Surprises-Act"),
            Segment("Independent for-profit vs hospital-based programs",
                    "consolidated among a few; nonprofit tail",
                    "INDUSTRY · operator structure"),
        ],
        growth_drivers=[
            "Trauma-system and time-critical-care demand (aging + rural access)",
            "Medicare AFS air-rate updates (modest; well below charges)",
            "In-network contracting replacing the lost OON premium",
            "Membership-program enrollment (a hedge, not a growth engine)",
            "Base rationalization — a NEGATIVE lever removing overcapacity",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Commercial": 0.40,
            "Medicare / MA": 0.35,
            "Medicaid": 0.15,
            "Self-pay / uninsured": 0.10,
        },
        rate_mechanics=[
            "Medicare Ambulance Fee Schedule (air) — fixed rotary-wing and "
            "fixed-wing base rates plus statutory mileage; far below billed charges.",
            "No Surprises Act — air ambulance IS covered; OON commercial disputes "
            "resolve through federal Independent Dispute Resolution (IDR).",
            "Qualifying payment amount (QPA) — the median-contracted benchmark "
            "that anchors IDR outcomes and the effective commercial rate.",
            "In-network contracting — the post-NSA lever: negotiated rates "
            "replace the vanished out-of-network balance-billing premium.",
            "Membership / subscription programs — annual fee waiving the patient "
            "residual; a hedge under state insurance-regulator scrutiny.",
            "Medical-necessity / mode-appropriateness review — payers and "
            "auditors contest whether air transport was justified over ground.",
        ],
        reimbursement_risk=(
            "The No Surprises Act is the whole risk story: by ending "
            "out-of-network balance billing and routing disputes to IDR, it "
            "removed the premium the sector's economics were built on. Revenue "
            "per transport now turns on IDR win rates, the qualifying payment "
            "amount, batching rules, and the pace of the IDR process — all still "
            "contested and litigated. Below that, Medicare and Medicaid pay a "
            "fraction of charges, self-pay collections are weak, and payers "
            "increasingly challenge the medical necessity of air transport. "
            "Membership programs face state insurance regulation. With revenue "
            "compressed and fixed cost per base unchanged, under-utilized bases "
            "are structurally unprofitable — the dynamic that pushed Air Methods "
            "into Chapter 11."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("No Surprises Act — air-ambulance coverage + IDR",
                 "Ended OON balance billing for air ambulance and created the "
                 "federal arbitration process that now sets the commercial rate.",
                 "https://www.cms.gov/nosurprises"),
            Rule("Airline Deregulation Act (ADA) preemption",
                 "Air ambulances are 'air carriers' — the ADA has preempted "
                 "state rate regulation, which is why a FEDERAL fix (the NSA) was "
                 "required to address balance billing.",
                 None),
            Rule("Medicare Ambulance Fee Schedule (air rates)",
                 "Sets the fixed rotary/fixed-wing base rates and mileage — the "
                 "government price, far below billed charges.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/ambulance"),
            Rule("FAA Part 135 air-carrier certification + HAA safety rules",
                 "Operating certificate, pilot/crew, and helicopter-air-ambulance "
                 "safety requirements; the NTSB-driven safety regime is a real "
                 "cost and operating constraint.",
                 "https://www.faa.gov/"),
            Rule("State insurance regulation of membership programs",
                 "Subscription/membership plans draw scrutiny over whether they "
                 "constitute unlicensed insurance products.",
                 None),
        ],
        policy_watch=[
            "IDR process reforms, QPA methodology, and ongoing NSA litigation",
            "GAO / federal reporting on air-ambulance charges and IDR outcomes",
            "Base overcapacity and any move toward utilization/CON-style limits",
            "State oversight of air-medical membership/subscription programs",
            "FAA/NTSB helicopter-air-ambulance safety rulemaking",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Consolidated at the top and fragmented at the base level: a few "
            "national operators run large fleets of individually-sited bases, "
            "alongside hospital-based and nonprofit-affiliated programs. The real "
            "structural problem is not fragmentation but OVERCAPACITY — years of "
            "base expansion under the old balance-billing economics left more "
            "helicopters than appropriate flight volume supports. No air-base "
            "facility file is vendored, so geography is honestly omitted."),
        hhi_or_share=(
            "Concentrated among Global Medical Response, Air Methods, and PHI at "
            "the operator level, but competition is local and volume-constrained: "
            "the binding issue is too many bases per flight, not market share."),
        consolidation=(
            "The 2010s roll-up — driven by the balance-billing model — built "
            "large national fleets (GMR assembling Air Evac, REACH, Med-Trans, "
            "Guardian; Air Methods scaling independently). The No Surprises Act "
            "reversed the logic: with the OON premium gone, over-based fleets "
            "became a liability, and Air Methods restructured through Chapter 11 "
            "in 2023. The forward motion is base rationalization and in-network "
            "contracting, not expansion."),
        pe_activity=(
            "Air medical was a favored PE roll-up precisely because of the "
            "balance-billing arbitrage — high OON charges on a captive, "
            "unconscious patient with no ability to shop. The No Surprises Act "
            "destroyed that thesis, and Air Methods' bankruptcy is the object "
            "lesson. Any live sponsor interest now underwrites in-network rates, "
            "IDR recovery, and base-level utilization — a fundamentally lower-"
            "return, operationally harder business than the one that traded in 2016-19."),
        notable_players=[
            "Global Medical Response (Air Evac / REACH / Med-Trans / Guardian, KKR)",
            "Air Methods", "PHI Air Medical",
            "Hospital-based / nonprofit-affiliated programs",
            "AirMedCare Network (membership)",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Transports per base per month", "the survival metric",
                "Fixed cost per base is enormous; utilization is the single "
                "determinant of base-level profitability, and overcapacity keeps "
                "it low."),
            Kpi("Revenue per transport (post-NSA)", "compressed sharply",
                "IDR/QPA-anchored commercial rates replaced the old OON premium, "
                "cutting realized revenue per flight."),
            Kpi("IDR win rate / recovery", "the new revenue lever",
                "Share of disputes won and amount recovered at arbitration now "
                "drives commercial realization."),
            Kpi("Fixed cost per base", "very high",
                "Aircraft lease/ownership, pilots, clinical crew, maintenance, "
                "hangar, and 24/7 readiness — largely fixed regardless of volume."),
            Kpi("Payer mix (self-pay/Medicaid share)", "realization drag",
                "Low-yield government and self-pay share compounds the post-NSA "
                "commercial compression."),
            Kpi("Membership penetration", "hedge coverage",
                "Subscription enrollment offsets patient residuals but is a "
                "defensive metric, not a profit engine."),
        ],
        margin_profile=(
            "Air medical is the extreme of the fixed-cost model: a single "
            "helicopter base — aircraft, two pilots, a clinical crew, "
            "maintenance, and 24/7 readiness — costs roughly the same whether it "
            "flies once a day or five times, so profitability is almost entirely "
            "a function of transports per base. The old model made the fixed cost "
            "work by pricing each flight at a large out-of-network balance bill; "
            "the No Surprises Act removed that, compressing revenue per transport "
            "while base costs stood still. With structural overcapacity holding "
            "utilization down, many bases now sit below breakeven — the exact "
            "arithmetic behind Air Methods' Chapter 11."),
    ),
    risks=[
        Risk("No Surprises Act repricing of commercial revenue", "High",
             "IDR/QPA replaced the OON balance-billing premium the model was "
             "built on, structurally cutting revenue per transport."),
        Risk("Fixed-cost / overcapacity at the base level", "High",
             "Too many bases chasing too few appropriate flights leaves "
             "under-utilized bases below breakeven — the Air Methods failure mode."),
        Risk("IDR process, QPA, and NSA litigation uncertainty", "High",
             "Revenue now depends on unsettled arbitration rules, benchmarks, "
             "and batching that remain in active litigation."),
        Risk("Medical-necessity / mode-appropriateness denials", "Medium",
             "Payers increasingly contest whether air transport was justified "
             "over ground, threatening volume and payment."),
        Risk("Safety / operational (helicopter crash exposure)", "Medium",
             "Helicopter air ambulance has a serious NTSB safety history; "
             "incidents carry human, regulatory, and insurance cost."),
        Risk("Membership-program insurance-regulation risk", "Low",
             "State regulators may treat subscription plans as unlicensed "
             "insurance, constraining a common patient-billing offset."),
    ],
    diligence_questions=[
        "What is revenue per transport pre- and post-NSA, and what is the IDR "
        "win rate and average recovery?",
        "What is the distribution of transports per base per month, and how many "
        "bases sit below breakeven?",
        "What share of commercial volume is in-network versus routed to IDR, and "
        "what is the contracting trajectory?",
        "What is the fixed cost per base (aircraft, crew, maintenance, "
        "readiness), and what is the base-rationalization plan?",
        "What is the payer mix and self-pay collection rate on transports?",
        "What is the medical-necessity denial rate and the mode-appropriateness "
        "audit exposure?",
        "What is the membership-program revenue, enrollment, and state-regulatory "
        "exposure?",
        "What is the safety record, insurance cost, and FAA Part 135 compliance "
        "posture?",
    ],
    insider_lens=[
        "The whole old thesis was balance-billing an unconscious patient who "
        "could not shop. The No Surprises Act ended it, and Air Methods' Chapter "
        "11 is the proof — do not re-underwrite the pre-2022 economics, because "
        "they no longer exist.",
        "It is a fixed-cost business masquerading as a per-flight one. The base "
        "costs the same empty or full, so transports per base is the only number "
        "that matters — and years of expansion under the old model left the "
        "field structurally over-based.",
        "Revenue is now an arbitration outcome, not a charge. IDR win rate, the "
        "qualifying payment amount, and batching rules set commercial "
        "realization — and they are still being litigated, so the revenue line "
        "is genuinely uncertain.",
        "Hospital-based and nonprofit-affiliated programs quietly won the new "
        "era: they carry better payer relationships and referral integration and "
        "were never as dependent on the OON premium as the independent for-profit fleets.",
        "Membership programs look like revenue but are really a defensive hedge "
        "against balance bills — and state insurance regulators are increasingly "
        "asking whether they are unlicensed insurance. Do not model them as a "
        "growth engine.",
    ],
    connections=default_connections(
        "air_medical",
        deals_sector="air_medical",
        extra_pages=[
            ("/diligence/tam-sam?template=air_medical",
             "Air Medical deep-dive — sizing build + trade history (broken playbook)"),
        ],
        connectors=[
            ("cms_open_data_catalog",
             "CMS Open Data — ambulance fee schedule (air base rates & mileage)"),
            ("npi_provider",
             "NPI Registry — air-ambulance suppliers (taxonomy 3416L0300X)"),
            ("oig_leie",
             "OIG LEIE — excluded entities (medical-necessity/fraud screen)"),
            ("census_acs_cbsa_profile",
             "Census ACS — rural population for catchment / access mapping"),
        ],
    ),
    sources=[
        Source("GAO — Air Ambulance: charges, balance billing, and market "
               "reports", "GOV", "https://www.gao.gov/"),
        Source("CMS No Surprises Act — air-ambulance IDR rules and reporting",
               "GOV", "https://www.cms.gov/nosurprises"),
        Source("CMS Ambulance Fee Schedule (air rates)", "GOV",
               "https://www.cms.gov/medicare/payment/fee-schedules/ambulance"),
        Source("NTSB / FAA — helicopter air-ambulance safety findings and Part "
               "135 rules", "GOV", "https://www.ntsb.gov/"),
        Source("Health Affairs / academic research on air-ambulance charges and "
               "the No Surprises Act", "ACADEMIC", "https://www.healthaffairs.org/"),
        Source("PE Desk industry deep-dive (air-medical sizing) + realized-deal "
               "corpus", "INTERNAL", "/diligence/tam-sam?template=air_medical"),
    ],
    live_figures=live_figures_from_dive("air_medical"),
    trends=(
        "Air medical is the clearest example in healthcare of a policy change "
        "resetting an entire business model. Through the 2010s the sector "
        "expanded aggressively — new helicopter bases, private-equity roll-ups — "
        "on the strength of out-of-network balance billing: fly a captive "
        "patient, charge $30-50K, and collect a large residual from the "
        "individual. That growth left structural overcapacity, more bases than "
        "appropriate flight volume could support. The No Surprises Act, "
        "effective 2022, ended the balance bill and moved out-of-network "
        "commercial disputes into federal Independent Dispute Resolution "
        "anchored to a qualifying payment amount — compressing revenue per "
        "transport while the high fixed cost per base did not move. The result "
        "was Air Methods' 2023 Chapter 11, the sector's defining event. The "
        "forward story is not growth but rationalization: closing under-utilized "
        "bases, contracting in-network, improving IDR recovery, and leaning on "
        "hospital-based partnerships. The corpus trade history from the OON era "
        "should be read as a broken playbook, not a comp set."),
    growth_levers=[
        GrowthLever(
            "Time-critical-care and trauma-system demand",
            "Aging, rural hospital closures, and regionalized trauma/stroke/cardiac "
            "care sustain the need for rapid interfacility and scene transport.",
            "+2-3%/yr underlying demand", "GOV"),
        GrowthLever(
            "In-network contracting (post-NSA)",
            "Negotiated commercial rates and improved IDR recovery are the only "
            "way to rebuild realization after the OON premium vanished.",
            "recovery, not expansion", "ILLUSTRATIVE"),
        GrowthLever(
            "Medicare AFS air-rate updates",
            "The government base rates step up modestly, but sit far below "
            "billed charges and cannot carry a base alone.",
            "modest, sub-cost", "GOV"),
        GrowthLever(
            "Base rationalization (a negative lever)",
            "Closing under-utilized bases raises fleet-level utilization and cuts "
            "fixed cost — a contraction that improves economics.",
            "capacity reduction", "ILLUSTRATIVE"),
        GrowthLever(
            "Membership-program enrollment",
            "Subscription growth offsets patient residuals and stabilizes "
            "collections — a hedge rather than a true growth engine.",
            "defensive hedge", "ILLUSTRATIVE"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Time-critical interfacility + scene transport (regionalized acute care)",
        analysis=(
            "Underlying demand is driven by the regionalization of "
            "time-critical care and by rural access gaps: as stroke, STEMI, "
            "trauma, and high-risk obstetric/neonatal care concentrate in "
            "designated centers, and as rural hospitals close or narrow their "
            "services, the need to move critically ill patients quickly over "
            "distance persists. Aging amplifies it. But the demand relevant to "
            "value is APPROPRIATE flight volume — transports where air is "
            "genuinely justified over ground — and that pool is smaller than the "
            "installed base of helicopters was built to serve. Payers and "
            "auditors increasingly police mode-appropriateness, which caps "
            "billable volume further. So the driver is real but bounded: demand "
            "supports a rationalized fleet at high utilization, not the "
            "over-based footprint the balance-billing era created."),
        basis="GOV"),
    cost_drivers=[
        CostDriver(
            "Aircraft (lease/ownership) & maintenance",
            "~30-40% of cost",
            "Rotor/fixed-wing acquisition or lease plus mandated maintenance — "
            "the fixed core that must be covered regardless of flight volume.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Flight & clinical crew (pilots, nurses, paramedics)",
            "~30-35% of cost",
            "24/7 pilot and clinical staffing per base; a fixed readiness cost "
            "and a binding labor constraint (pilot shortage).",
            "ILLUSTRATIVE"),
        CostDriver(
            "Base operations & readiness (hangar, fuel, dispatch)",
            "~12-18% of cost",
            "Hangar, fuel, communications, and 24/7 deployment infrastructure "
            "per sited base.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Insurance & safety/compliance (FAA Part 135)",
            "~6-10% of cost",
            "Aviation liability, safety programs, and Part 135 compliance on a "
            "high-consequence risk profile.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Billing, IDR & collections",
            "~5-8% of cost",
            "Arbitration/IDR administration plus complex payer billing and "
            "self-pay collections in the post-NSA regime.",
            "ILLUSTRATIVE"),
    ],
    state_breakdown=None,
    cms_trend=None,
)

register(REPORT)
