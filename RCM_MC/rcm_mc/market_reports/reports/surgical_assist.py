"""Surgical Assist — first-assisting labor for the operating room.

Deals-only pattern (no public surgical-assist roster exists). The defining fact
is that this is a *labor-arbitrage + billing* business, not a facility one: an
independent surgical-assist company contracts first assistants to surgeons/ASCs
and bills payers for the assistant-at-surgery fee. Medicare reimburses the
assistant at a fixed 16% of the surgeon's fee and recognizes only physicians and
NPP assistants (PA/NP/CNS with -AS) — not RNFAs or certified surgical assistants
— so the historical margin came from OUT-OF-NETWORK commercial balance billing,
which the No Surprises Act (2022) largely closed. Live SOURCED figures come from
``surgical_assist_deep_dive()`` (deals-only; the corpus is thin here).
"""
from __future__ import annotations

from .. import (
    Competition, CostDriver, GrowthLever, HowItWorks, Kpi, MarketReport,
    MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment, Source,
    TamHeadline, UnitEconomics, VolumeDriver, default_connections,
    live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="surgical_assist",
    name="Surgical Assist",
    care_setting="Ambulatory",
    naics="621111",
    one_line_def=(
        "First-assisting labor for the operating room — a physician assistant, "
        "nurse practitioner, RN first assistant (RNFA), or certified surgical "
        "assistant who assists the primary surgeon during a procedure, supplied "
        "either by the facility/surgeon (employed) or by an independent surgical-"
        "assist company that contracts the assistant and bills payers the "
        "assistant-at-surgery fee."),
    tam_headline=TamHeadline(
        value=4.0, unit="$B", growth_pct=3.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "Modeled US surgical-first-assist professional-fee/labor spend — "
            "derived from surgical case volume × the assist-eligible share of "
            "procedures × the blended assistant-at-surgery fee. No published "
            "market figure exists for this micro-niche; the magnitude is a "
            "TAM/SAM-style build, not a filed number. Growth tracks surgical "
            "volume and the ASC migration, net of the post-No-Surprises-Act "
            "reimbursement reset. ILLUSTRATIVE."),
    ),
    executive_summary=[
        "This is a labor-arbitrage and billing business, not a facility one. "
        "The 'asset' is a bench of credentialed first assistants and a billing "
        "engine that collects the assistant-at-surgery fee — there is no real "
        "estate, no census, and almost no capital.",
        "Medicare hard-caps the economics: the assistant-at-surgery is paid a "
        "flat 16% of the surgeon's fee-schedule amount, and an NPP assistant "
        "(PA/NP/CNS, billed -AS) is paid 85% of that. RNFAs and certified "
        "surgical assistants are NOT separately reimbursed by Medicare at all — "
        "so who holds the credential determines whether a claim can even be "
        "billed to Medicare.",
        "Not every procedure is assist-eligible. Each CPT carries a Medicare "
        "assistant-at-surgery indicator (0 = documentation-gated, 1 = never "
        "paid, 2 = allowed), so the billable universe is a specific slice of the "
        "OR schedule — ortho, spine, cardiac, bariatric, complex general/robotic.",
        "The historical PE playbook was out-of-network commercial balance "
        "billing: bill the plan an aggressive OON charge for the assistant, "
        "collect a multiple of the Medicare rate. The No Surprises Act (2022) "
        "swept surgical assistants at in-network facilities into patient "
        "protections and IDR arbitration — repricing the whole model.",
        "Demand is a derivative of surgical case volume and case mix, amplified "
        "by the outpatient migration to ASCs; supply is a scope-of-practice and "
        "credentialing patchwork (only some states license surgical assistants), "
        "and collections — not clinical work — is where deals are won or lost.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Surgeon / ASC / hospital requests a first assistant for a case",
            "Assist company credentials & schedules a qualified assistant",
            "Assistant is present and assists during the procedure",
            "Operative note documents the assistant and medical necessity",
            "Claim coded with the assist modifier (-80/-81/-82 or -AS)",
            "Payer adjudicates against the CPT's assistant-at-surgery indicator",
            "Collection / appeal / IDR arbitration on out-of-network balances",
        ],
        sites_of_care=[
            "Hospital operating rooms (inpatient & HOPD)",
            "Ambulatory surgery centers (ASCs) — the growth site",
            "Office-based surgical suites",
            "Cardiac / spine / orthopedic specialty ORs",
        ],
        money_flow=(
            "The primary surgeon bills the procedure; the first assistant bills "
            "a separate assistant-at-surgery line for the SAME CPT with an "
            "assist modifier. Medicare pays a physician assistant-at-surgery 16% "
            "of the surgical fee-schedule amount (modifiers -80/-81/-82); an NPP "
            "assistant (PA/NP/CNS) bills -AS and is paid 85% of that 16%. "
            "Medicare does not separately reimburse RNFAs or certified surgical "
            "assistants, so on Medicare work those assistants must be employed/"
            "absorbed by the facility. Commercial plans historically paid "
            "surgical assistants out-of-network at a large multiple of the "
            "Medicare rate — the source of the roll-up margin — until the No "
            "Surprises Act held patients harmless and pushed the plan-vs-provider "
            "dispute into independent dispute resolution (IDR). The economics are "
            "therefore a spread between the assistant's day-rate/salary (the "
            "COGS) and what the biller actually collects per case."),
        key_players=(
            "The segment is sub-scale and overwhelmingly private. Three archetypes: "
            "independent regional first-assist staffing-and-billing companies "
            "(the PE-relevant model); hospital and ASC in-house RNFA/PA-C "
            "programs (assist absorbed into facility labor, billed only where "
            "allowed); and independent certified-surgical-assistant (CSA/SA) "
            "contractor networks in the states that license them. Surgical assist "
            "also rides inside broader perioperative and anesthesia-management "
            "platforms as a bolt-on line. Device-company clinical reps assist at "
            "the table in some specialties but are not billed."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Assist-eligible surgical volume (ortho/spine/cardiac/"
                    "bariatric/complex general)",
                    "the billable slice of the OR schedule",
                    "GOV · CPT assistant-at-surgery indicators (MPFS)"),
            Segment("ASC-site cases (outpatient migration)",
                    "the fastest-growing setting",
                    "ILLUSTRATIVE · surgical site-of-care shift"),
            Segment("NPP-delivered assists (PA/NP, billable -AS)",
                    "the Medicare-reimbursable delivery model",
                    "GOV · Medicare -AS payment policy"),
            Segment("RNFA / CSA-delivered assists (facility-absorbed on Medicare)",
                    "non-Medicare-billable labor",
                    "GOV · Medicare non-recognition of RNFA/CSA"),
            Segment("Commercial out-of-network assist balances",
                    "collapsed post-No Surprises Act",
                    "GOV · No Surprises Act / IDR"),
        ],
        growth_drivers=[
            "Total surgical case volume (population + procedure incidence)",
            "Outpatient migration of surgery to ASCs (more assist demand sites)",
            "Ortho/spine/cardiac case growth (assist-heavy specialties)",
            "Robotic-surgery adoption (changes, not eliminates, bedside assist)",
            "Reimbursement reset (No Surprises Act) — a structural drag on rate",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Commercial (post-NSA, in/out-of-network)": 0.55,
            "Medicare (assistant-at-surgery 16% / -AS)": 0.30,
            "Medicaid / other": 0.15,
        },
        rate_mechanics=[
            "Assistant-at-surgery fee — Medicare pays a physician assistant 16% "
            "of the surgical fee-schedule amount (modifiers -80 assistant "
            "surgeon, -81 minimum assistant, -82 when a qualified resident is "
            "unavailable).",
            "NPP -AS modifier — a PA/NP/CNS assistant is paid 85% of the 16%, "
            "i.e. ~13.6% of the surgeon's allowed amount; this is the Medicare-"
            "reimbursable independent delivery model.",
            "RNFA / certified surgical assistant — not separately recognized by "
            "Medicare; on Medicare cases the assist must be absorbed by the "
            "facility. Some commercial plans and some state Medicaid programs do "
            "recognize them (state-by-state).",
            "CPT assistant-at-surgery indicator — each procedure code carries a "
            "flag (0 = paid only with documented medical necessity, 1 = never "
            "paid an assistant, 2 = allowed) that defines the billable universe.",
            "Out-of-network commercial billing — historically an aggressive OON "
            "charge collected at a multiple of Medicare; now constrained by the "
            "No Surprises Act patient protections and IDR arbitration.",
        ],
        reimbursement_risk=(
            "The risk is concentrated and structural. First, the No Surprises "
            "Act closed the out-of-network balance-billing arbitrage that made "
            "independent surgical assist a roll-up: the patient is held harmless "
            "and the collectible amount is now what the plan pays or an IDR "
            "arbitrator awards, so historical collections do not carry forward. "
            "Second, credential mix caps Medicare billability — RNFA/CSA work is "
            "not separately payable, so a company staffed with non-NPP assistants "
            "has a smaller reimbursable universe than its case count implies. "
            "Third, payer medical-necessity edits and the CPT assist indicators "
            "deny a meaningful share of claims. Underwrite collected revenue per "
            "case, not billed charges, and stress it to the post-NSA IDR reality."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("No Surprises Act (out-of-network balance-billing ban + IDR)",
                 "The defining rule for this niche — surgical assistants at in-"
                 "network facilities are swept into patient protections, and the "
                 "old OON balance-billing margin is replaced by plan payment and "
                 "IDR arbitration.",
                 "https://www.cms.gov/nosurprises"),
            Rule("Medicare assistant-at-surgery payment policy (16% / -AS)",
                 "Sets the 16% physician rate, the 85%-of-16% NPP rate, and the "
                 "modifiers — the reimbursement backbone and the Medicare "
                 "billability boundary.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
            Rule("CPT assistant-at-surgery indicators (MPFS RVU file)",
                 "The per-procedure flag (0/1/2) that decides whether an "
                 "assistant can be billed at all — it defines the eligible case "
                 "universe.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/physician/pfs-relative-value-files"),
            Rule("State scope-of-practice & surgical-assistant licensure",
                 "Only some states license/certify surgical assistants (SA/CSA) "
                 "or define RNFA practice; scope and who may bill varies by "
                 "state, shaping the labor model market-by-market.",
                 None),
            Rule("Facility credentialing & Conditions of Participation",
                 "Hospitals/ASCs credential and privilege first assistants; the "
                 "operative note must document the assistant and medical "
                 "necessity or the claim is deniable.",
                 None),
        ],
        policy_watch=[
            "No Surprises Act IDR process litigation and rulemaking (award "
            "benchmarks, batching, fees)",
            "Any change to the 16% assistant-at-surgery percentage or -AS policy",
            "State licensure expansion for surgical assistants (billability)",
            "MPFS annual updates to assist indicators on high-volume CPTs",
            "Robotic-surgery guidelines that reshape bedside-assist requirements",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Extremely fragmented and sub-scale. Independent surgical-assist "
            "companies are mostly small, private, and regional, competing on "
            "surgeon relationships, credentialed-assistant availability, and "
            "billing/collections capability. There is no dominant national brand "
            "and no public roster of operators."),
        hhi_or_share=(
            "No public census of surgical-assist companies is vendored, so share "
            "is honestly unquantified. The structure is a long private tail plus "
            "assist lines embedded in larger perioperative/anesthesia platforms; "
            "the deal history and the surgical-volume base below are the anchors, "
            "not a facility map."),
        consolidation=(
            "Consolidation logic is billing scale and payer leverage: a larger "
            "biller negotiates and arbitrates better and spreads credentialing "
            "overhead. But the No Surprises Act removed the OON-arbitrage engine "
            "that drove the prior wave of roll-ups (the same engine that priced "
            "physician staffing and air medical), so post-NSA consolidation is "
            "about operating efficiency and surgeon capture, not rate arbitrage."),
        pe_activity=(
            "Sponsor interest cooled sharply after the No Surprises Act repriced "
            "out-of-network surgical-assist economics. What interest remains "
            "treats surgical assist as a bolt-on to perioperative, anesthesia, or "
            "ASC platforms rather than a standalone thesis, and underwrites "
            "collected revenue per case under IDR — not the legacy billed-charge "
            "model."),
        notable_players=[
            "Independent regional first-assist staffing/billing companies "
            "(private, sub-scale)",
            "Hospital & ASC in-house RNFA / PA-C programs",
            "Certified surgical assistant (CSA/SA) contractor networks",
            "Perioperative & anesthesia-management platforms (assist as a bolt-on)",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Collected revenue per case", "post-NSA reset",
                "The only number that matters — billed charges overstate it; "
                "collections under plan payment + IDR are the real yield."),
            Kpi("Assistant day-rate / salary (the COGS)", "labor-driven",
                "The assistant's compensation is essentially cost of goods; the "
                "business is the spread over it."),
            Kpi("Cases per assistant per day", "throughput",
                "Utilization of a fixed labor cost — turnover and OR scheduling "
                "drive it."),
            Kpi("Credential mix (NPP vs RNFA/CSA)", "billability lever",
                "NPP (-AS) work is Medicare-billable; RNFA/CSA is not — mix "
                "changes the reimbursable universe."),
            Kpi("Payer mix & OON share", "rate exposure",
                "Commercial vs Medicare and in- vs out-of-network drive rate and "
                "post-NSA collectibility."),
            Kpi("Denial / medical-necessity edit rate", "leakage",
                "Assist-indicator and documentation edits deny a real share of "
                "claims — the RCM competence test."),
        ],
        margin_profile=(
            "Margin is the spread between the assistant's compensation (the COGS) "
            "and collected revenue per case, minus billing/credentialing "
            "overhead. Because Medicare caps the assist at 16% and the No "
            "Surprises Act capped the commercial upside, the model lives on "
            "throughput (cases per assistant), credential mix (billable NPP "
            "work), and collections competence (winning IDR and clearing "
            "assist-indicator/necessity edits). It is a people-and-billing "
            "business with little operating leverage beyond scheduling density; "
            "ranges are ILLUSTRATIVE — confirm against the target's collected-"
            "per-case actuals, not its charges."),
    ),
    risks=[
        Risk("No Surprises Act reimbursement reset", "High",
             "The OON balance-billing margin that built independent surgical "
             "assist is gone; collections now hinge on plan payment and IDR "
             "awards, and history doesn't carry forward."),
        Risk("Credential-mix billability", "High",
             "RNFA/CSA assists are not separately Medicare-reimbursable; a bench "
             "weighted to non-NPP assistants has a smaller billable universe "
             "than case count implies."),
        Risk("Payer denials & assist-indicator edits", "Medium",
             "Necessity documentation and per-CPT assist indicators deny a "
             "meaningful share of claims; RCM quality is the differentiator."),
        Risk("Surgeon-relationship concentration & transfer", "Medium",
             "Volume follows individual surgeons/ASCs; relationships are personal "
             "and may not transfer with the deal."),
        Risk("Labor supply & scope-of-practice patchwork", "Medium",
             "Qualified first assistants are scarce, and who may practice/bill "
             "varies state by state, constraining growth."),
        Risk("Surgical-volume cyclicality & site shift", "Low",
             "Elective volume dips (e.g., COVID) and the ASC migration reshape "
             "where and how much assist demand exists."),
    ],
    diligence_questions=[
        "What is collected revenue per case (not billed charges), and how has it "
        "moved since the No Surprises Act took effect?",
        "What is the credential mix of the bench (NPP vs RNFA/CSA), and what "
        "share of volume is Medicare-billable versus facility-absorbed?",
        "What is the payer mix and out-of-network share, and what has IDR "
        "experience been (win rate, award levels, cycle time)?",
        "How concentrated is volume among the top surgeons/ASCs, and do those "
        "relationships transfer with the transaction?",
        "What is the denial / assist-indicator edit rate, and how strong is the "
        "documentation and appeals process?",
        "Across which states does the company operate, and how do licensure and "
        "billability differ across them?",
        "What is assistant utilization (cases/day) and turnover, and how "
        "dependent is the model on a few key assistants?",
    ],
    insider_lens=[
        "Charges are fiction; collections are the business. Independent surgical "
        "assist historically billed enormous out-of-network charges and "
        "collected a fraction — the No Surprises Act made even that fraction "
        "contingent on IDR. Underwrite collected-per-case, and assume the "
        "legacy billed-charge history does not repeat.",
        "The credential on the badge decides the claim. Medicare pays a "
        "physician or NPP assistant but not an RNFA or certified surgical "
        "assistant — so two companies with identical case volume can have very "
        "different billable revenue depending on who is at the table.",
        "The No Surprises Act did to surgical assist what it did to ER staffing "
        "and air medical: it removed the balance-billing arbitrage that was the "
        "entire margin. Treat this niche the way you'd treat any post-NSA OON "
        "model — the old comps are a trap.",
        "It's a staffing-and-billing company wearing surgical scrubs. There's no "
        "facility, no census, almost no capital — the value is a bench of "
        "credentialed assistants, surgeon relationships, and a collections "
        "engine. If any one of those is thin, the platform is thin.",
        "Robotics doesn't kill the assist, it moves it. Robotic cases still need "
        "a bedside assistant for port placement, retraction, and instrument "
        "exchange — the role changes, the billable line often persists. But some "
        "payers and indicators treat robotic assists differently, so read the "
        "case mix code by code.",
    ],
    connections=default_connections(
        "surgical_assist",
        deals_sector="surgical_assist",
        connectors=[
            ("cms_open_data_mup_physician_by_provider_service",
             "CMS Physician & Other Practitioners — assist-modifier (-80/-AS) "
             "line utilization & payment"),
            ("npi_provider",
             "NPI Registry — PA/NP/RNFA/surgical-assistant enumeration & taxonomy"),
            ("cms_open_data_mup_outpatient_by_provider_service",
             "CMS Outpatient — assist-eligible procedure volume by facility"),
            ("open_payments_general_payments_2024",
             "CMS Open Payments — device/industry ties in assist-heavy specialties"),
            ("oig_leie_exclusions",
             "OIG LEIE — exclusion screen for contracted clinical staff"),
        ],
    ),
    sources=[
        Source("CMS Medicare Physician Fee Schedule — assistant-at-surgery "
               "payment policy, modifiers, and RVU assist indicators", "GOV",
               "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
        Source("No Surprises Act — out-of-network balance-billing protections & "
               "independent dispute resolution", "GOV",
               "https://www.cms.gov/nosurprises"),
        Source("Medicare Claims Processing Manual — assistant-at-surgery (Ch. "
               "12) modifiers -80/-81/-82/-AS", "GOV",
               "https://www.cms.gov/regulations-and-guidance/guidance/manuals/internet-only-manuals-ioms"),
        Source("Association of Surgical Assistants / AORN RNFA practice "
               "standards & state scope references", "INDUSTRY",
               "https://www.aorn.org/"),
        Source("PE Desk industry deep-dive (surgical assist) + realized-deal "
               "corpus", "INTERNAL",
               "/diligence/tam-sam?template=surgical_assist"),
    ],
    live_figures=live_figures_from_dive("surgical_assist"),
    trends=(
        "Surgical assist spent the 2010s as a quiet out-of-network billing play: "
        "independent companies staffed first assistants to surgeons and ASCs and "
        "collected commercial OON balances at a large multiple of the Medicare "
        "16% rate — a model structurally identical to the physician-staffing and "
        "air-medical roll-ups of the same era. The No Surprises Act (effective "
        "2022) ended that: surgical assistants at in-network facilities were "
        "swept into patient protections, and the collectible amount became plan "
        "payment or an IDR arbitrator's award. The trajectory since is a "
        "repricing — collected revenue per case reset downward, sponsor interest "
        "cooled, and the surviving logic is bolt-on scale inside perioperative, "
        "anesthesia, or ASC platforms. Underneath, real demand keeps rising with "
        "surgical volume and the outpatient migration to ASCs, and robotics "
        "reshapes (without eliminating) the bedside-assist role. The through-line "
        "for diligence is that the business is now a labor-and-collections spread "
        "under IDR, credential-mix-limited on Medicare — not a billed-charge "
        "arbitrage."),
    growth_levers=[
        GrowthLever(
            "Surgical case volume",
            "First-assist demand is a direct derivative of the number of "
            "assist-eligible procedures performed.",
            "primary", "ILLUSTRATIVE"),
        GrowthLever(
            "ASC / outpatient migration",
            "As surgery shifts to ambulatory settings, assist demand spreads to "
            "more, smaller sites — a distribution tailwind.",
            "site shift", "ILLUSTRATIVE"),
        GrowthLever(
            "Assist-heavy specialty growth (ortho/spine/cardiac/bariatric)",
            "These specialties both grow with demographics and carry high "
            "assist-eligibility, lifting billable case mix.",
            "mix", "GOV"),
        GrowthLever(
            "Credential-mix optimization (toward billable NPP work)",
            "Shifting delivery toward PA/NP assistants (-AS) expands the "
            "Medicare-reimbursable universe versus RNFA/CSA labor.",
            "billability", "GOV"),
        GrowthLever(
            "No Surprises Act reimbursement reset",
            "The OON balance-billing margin that once drove the sector is gone; "
            "IDR awards set a lower, structural ceiling.",
            "−rate (structural)", "GOV"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Assist-eligible surgical case volume (procedures × assist "
               "indicator × site mix)",
        analysis=(
            "Surgical-assist demand is not a demographic count of patients — it "
            "is a count of procedures that (a) are performed and (b) carry an "
            "assistant-at-surgery indicator that permits billing. That makes the "
            "true demand meter the surgical schedule of assist-heavy specialties "
            "(orthopedics, spine, cardiac, bariatric, and complex general and "
            "robotic cases), filtered by each CPT's Medicare assist indicator. "
            "Two secular shifts move it: the outpatient migration of surgery to "
            "ASCs spreads assist demand across more sites, and robotic adoption "
            "reshapes the bedside-assist role rather than removing it. CMS "
            "physician- and outpatient-service files (assist-modifier lines and "
            "procedure volumes) are the honest way to size the billable base — "
            "case count alone overstates it, because a large share of the OR "
            "schedule is not assist-eligible."),
        basis="GOV"),
    cost_drivers=[
        CostDriver(
            "First-assistant compensation (day-rate / salary)",
            "#1 — the COGS",
            "The assistant's pay is essentially cost of goods sold; the entire "
            "model is the spread of collections over it.", "ILLUSTRATIVE"),
        CostDriver(
            "Billing, coding & IDR/collections",
            "~10-20% of cost",
            "Post-No-Surprises-Act, winning IDR and clearing assist-indicator/"
            "necessity edits is the core competency — a real cost center, not "
            "back-office.", "ILLUSTRATIVE"),
        CostDriver(
            "Credentialing, licensing & malpractice",
            "~8-12% of cost",
            "Facility privileging, state licensure upkeep, and professional "
            "liability for clinicians at the table.", "ILLUSTRATIVE"),
        CostDriver(
            "Scheduling & clinical operations",
            "~8-12% of cost",
            "Matching credentialed assistants to OR schedules across sites — the "
            "utilization engine that spreads fixed labor.", "ILLUSTRATIVE"),
        CostDriver(
            "Sales / surgeon relationship management & G&A",
            "~8-12% of cost",
            "Surgeon and ASC capture is a B2B relationship sale; retention is "
            "personal and drives the book.", "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "No public surgical-assist company roster is vendored, so geography is "
        "not fabricated here. The honest geographic read is two-layered: demand "
        "follows surgical-volume density (population, ASC penetration, and the "
        "concentration of assist-heavy specialties), while billability follows "
        "each state's surgical-assistant licensure and Medicaid recognition — so "
        "who may practice and bill differs market by market. Use the CMS "
        "physician/outpatient assist-line connectors and the deal history below "
        "rather than a facility map."),
)

register(REPORT)
