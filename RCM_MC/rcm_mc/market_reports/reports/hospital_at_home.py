"""Hospital-at-Home (HaH) — acute, inpatient-level care delivered in the home.

Deals-only pattern (no vendored facility file — the honest geography layer is
the sector's deal history, so state breakdown and a CMS certification trend are
omitted rather than fabricated). The qualitative sections are authored around
the one fact that governs the whole model: HaH exists at Medicare scale only
because of a temporary CMS waiver, so the sector is a regulatory bet wrapped in
a logistics business.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver, default_connections,
    live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="hospital_at_home",
    name="Hospital-at-Home",
    care_setting="Post-acute",
    naics="621610",
    one_line_def=(
        "Acute, inpatient-level care delivered in the patient's home as a "
        "substitute for a hospital admission — daily physician oversight "
        "(largely virtual), in-person nursing visits, IV medications, mobile "
        "diagnostics, and continuous remote monitoring — reimbursed at Medicare "
        "scale only through the temporary CMS Acute Hospital Care at Home "
        "(AHCaH) waiver."),
    tam_headline=TamHeadline(
        value=25.0, unit="$B", growth_pct=None, basis_label="ILLUSTRATIVE",
        basis_note=(
            "There is no published HaH market size. The realized AHCaH program "
            "is still small — a few hundred approved hospitals and tens of "
            "thousands of Medicare episodes — and entirely waiver-dependent. The "
            "~$25B is a modeled near/medium-term substitution estimate against a "
            "much larger (>$100B) long-run pool of inpatient care that could "
            "shift home; treat it as directional, not filed, and gated on waiver "
            "permanence."),
    ),
    executive_summary=[
        "The whole model is a regulatory bet. HaH is reimbursed at Medicare "
        "scale only under the CMS Acute Hospital Care at Home (AHCaH) waiver, "
        "launched in November 2020 and since extended only on short, rolling "
        "bases — there is no permanent Medicare fee-for-service payment pathway. "
        "Reauthorization risk is the first thing to underwrite, before any "
        "clinical or unit-economics question.",
        "The real customer is often the hospital, not the patient. The core "
        "value is freeing a scarce inpatient bed and moving a DRG's worth of "
        "care to a lower-cost home setting — so many of these businesses are B2B "
        "enablement (tech + services + staffing) sold to health systems, not "
        "direct providers holding the DRG and the risk.",
        "The escalation ('rescue') rate is the safety-and-economics linchpin. "
        "Too many patients bounced back to the brick-and-mortar hospital erases "
        "both the cost savings and the safety case that the reauthorization "
        "depends on.",
        "It is a logistics business wearing clinical clothes. Density and "
        "drive-time decide unit economics — nursing visits, mobile diagnostics, "
        "DME, and infusion have to reach the home fast and cheaply, so a strong "
        "clinical model still fails in a low-density market.",
        "Consolidation is strategic-led, not a facility roll-up. Payers, "
        "retailers, and distributors have moved (Optum via Contessa and "
        "DispatchHealth; Best Buy Health via Current Health; Cardinal-backed "
        "Medically Home) — the assets are capabilities and command centers, and "
        "MA/commercial adoption is the path to a model that outlives the waiver.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Eligible-patient identification in the ED or on the inpatient unit",
            "Clinical + social eligibility screen and patient consent",
            "Admission to HaH (billed as an inpatient stay under the waiver)",
            "Home setup — biometrics, connectivity, DME, first medications",
            "Daily physician rounds (virtual) + in-person nursing visits",
            "24/7 command-center monitoring with a defined escalation pathway",
            "Rescue back to brick-and-mortar if the patient destabilizes",
            "Discharge home or to a lower level of care; outcomes reporting",
        ],
        sites_of_care=[
            "The patient's home (the site of care)",
            "A central command / virtual-care center (the clinical hub)",
            "The host hospital (referral source + escalation destination)",
            "Mobile ancillary network — phlebotomy, imaging, infusion, DME",
        ],
        money_flow=(
            "Under the AHCaH waiver, a Medicare-certified hospital admits the "
            "patient to hospital-at-home and bills Medicare the full inpatient "
            "DRG, exactly as if the patient occupied a physical bed — there is "
            "no separate HaH fee schedule. The economics are the spread between "
            "that DRG (or a negotiated MA/commercial case rate) and the variable "
            "cost of delivering the episode at home: nursing visits, physician "
            "telehealth, DME, home infusion, mobile diagnostics, logistics, and "
            "an allocated share of the 24/7 command center. Because the fixed "
            "command-center and technology costs are spread across census, "
            "contribution improves sharply with scale and with geographic "
            "density (shorter drive-times). Absent the waiver, that Medicare "
            "billing pathway disappears, which is why MA and commercial "
            "contracts — and any future dedicated CMS payment model — are the "
            "revenue that would survive a lapse."),
        key_players=(
            "The field is enablement-led. Tech-and-services companies stand up "
            "the model for health systems: Medically Home (backed by Mayo "
            "Clinic, Kaiser, and Cardinal Health), Contessa Health (built inside "
            "Amedisys, now within Optum), DispatchHealth (Optum), Current Health "
            "(Best Buy Health), Inbound Health, and monitoring platforms such as "
            "Biofourmis. Alongside them, large systems run their own programs — "
            "Mass General Brigham, Cleveland Clinic, Atrium Health, Presbyterian/"
            "Adventist, and Kaiser among the most cited. The strategic buyers are "
            "payers, retailers, and distributors verticalizing into the home, "
            "not classic facility roll-up sponsors."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Approved AHCaH hospitals",
                    "~370+ hospitals / ~140 systems, ~38 states",
                    "GOV · CMS Acute Hospital Care at Home program data"),
            Segment("Realized Medicare HaH episodes to date",
                    "tens of thousands of episodes",
                    "GOV · CMS / JAMA AHCaH utilization reporting"),
            Segment("Medicare inpatient (IPPS) substitution pool",
                    "~$150B+ inpatient spend",
                    "GOV · MedPAC / CMS inpatient hospital spending"),
            Segment("Clinically eligible medical admissions (modeled)",
                    "~20-30% of medical admissions",
                    "ILLUSTRATIVE · clinical-eligibility modeling"),
            Segment("Long-run addressable home-shiftable inpatient care",
                    ">$100B (directional)",
                    "ILLUSTRATIVE · substitution-potential estimate"),
        ],
        growth_drivers=[
            "Inpatient bed scarcity + capacity pressure — the system pull",
            "Aging + chronic-disease admissions (CHF, COPD, pneumonia, "
            "cellulitis, infections) — the clinical demand base",
            "RPM, telehealth, and mobile-diagnostics maturation — the enablers",
            "MA / commercial adoption — the payment model that outlives the "
            "waiver",
            "Waiver reauthorization — the binary gate on the entire FFS market",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Medicare FFS (AHCaH waiver)": 0.45,
            "Medicare Advantage": 0.25,
            "Commercial": 0.20,
            "Medicaid / other": 0.10,
        },
        rate_mechanics=[
            "AHCaH waiver inpatient billing — the hospital bills the full "
            "inpatient DRG for the home episode; there is no separate HaH fee "
            "schedule, and this pathway exists only while the waiver is in force.",
            "Medicare Advantage / commercial arrangements — negotiated case "
            "rates, per-diems, or DRG-equivalents, sometimes with shared "
            "savings; these are the revenue that would survive a waiver lapse.",
            "Conditions-of-Participation waivers — the 24-hour on-premises "
            "nursing and other hospital CoPs are waived to permit home delivery.",
            "Physician oversight + telehealth flexibilities — daily physician "
            "evaluation delivered largely virtually under the PHE-era rules.",
            "Bundled home ancillaries — nursing visits, DME, infusion, and "
            "mobile diagnostics are absorbed into the episode rather than billed "
            "separately.",
            "No permanent Medicare FFS pathway absent the waiver — the single "
            "most important reimbursement fact in the sector.",
        ],
        reimbursement_risk=(
            "The dominant reimbursement risk is existential and binary: the "
            "AHCaH waiver is temporary and has been extended only on short, "
            "rolling bases, so a lapse would remove the Medicare inpatient-"
            "billing pathway that carries the current market. Even with the "
            "waiver, the model depends on a favorable CMS/ASPE evaluation of "
            "whether HaH truly saves money and matches inpatient outcomes — the "
            "reauthorization and any future dedicated payment model both ride on "
            "that verdict. The mitigant is payer diversification: MA and "
            "commercial contracts (and a possible CMMI model) are the revenue "
            "that would outlive a waiver lapse, so a book concentrated in FFS-"
            "waiver dollars is a book with a cliff."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("CMS Acute Hospital Care at Home (AHCaH) waiver",
                 "The individual waiver (launched Nov 2020 under Hospitals "
                 "Without Walls) that lets certified hospitals deliver and bill "
                 "inpatient-level care at home — the legal basis for the entire "
                 "Medicare-scale market.",
                 "https://qualitynet.cms.gov/acute-hospital-care-at-home"),
            Rule("Congressional extensions of AHCaH (CAA 2023 + subsequent CRs)",
                 "The waiver has been extended only on short, rolling bases; its "
                 "long-run permanence requires ongoing Congressional "
                 "reauthorization — the binary policy risk.",
                 "https://www.congress.gov/"),
            Rule("Hospital Conditions of Participation waivers (42 CFR 482)",
                 "The specific CoPs (e.g. 24-hour on-premises nursing) waived to "
                 "permit home-based inpatient care — reinstated automatically if "
                 "the waiver lapses.",
                 "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-G/part-482"),
            Rule("CMS/ASPE HaH evaluation & data reporting requirement",
                 "The waiver mandates outcome and cost reporting; the study "
                 "verdict on savings and safety drives reauthorization and any "
                 "future payment model.",
                 "https://aspe.hhs.gov/"),
            Rule("State hospital licensure & scope rules",
                 "States must also permit home-based hospital care; licensure "
                 "and nurse/telehealth scope vary and gate market entry.",
                 None),
        ],
        policy_watch=[
            "AHCaH waiver reauthorization / permanence — the existential gate",
            "CMS/ASPE outcome-and-cost evaluation results",
            "A possible dedicated CMMI hospital-at-home payment model",
            "MA and commercial payment-model maturation",
            "State-by-state licensure and telehealth-scope expansion",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Early-stage and enablement-led rather than facility-based. The "
            "market splits between health-system-run programs and the tech-and-"
            "services enablers that stand them up; there is no national provider "
            "footprint to count, which is why geography here is a deal-history "
            "read rather than a facility map."),
        hhi_or_share=(
            "No meaningful facility-concentration measure exists — the sector is "
            "a set of programs and platforms, not a certified-facility universe. "
            "Concentration is emerging at the enabler layer as payers and "
            "retailers consolidate capabilities."),
        consolidation=(
            "Consolidation is active but strategic-led: Optum absorbed Contessa "
            "(via the Amedisys acquisition) and DispatchHealth; Best Buy Health "
            "acquired Current Health; Cardinal Health backs Medically Home. The "
            "logic is payers, retailers, and distributors verticalizing into the "
            "home to own the acute-substitution capability, not sponsors rolling "
            "up sites."),
        pe_activity=(
            "Sponsor exposure is mostly growth equity into the enablers "
            "(Medically Home, Inbound Health, Biofourmis) and adjacency plays in "
            "home infusion, mobile diagnostics, and RPM. Classic buy-and-build "
            "is hard because there is little to roll up and because the "
            "underlying revenue is waiver-contingent — the value is a defensible "
            "operating platform and payer contracts, not a site count."),
        notable_players=[
            "Medically Home", "Contessa Health (Optum)", "DispatchHealth (Optum)",
            "Current Health (Best Buy Health)", "Inbound Health", "Biofourmis",
            "Mass General Brigham (system program)", "Cleveland Clinic (system "
            "program)",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Eligible-patient capture rate", "program-specific",
                "The share of clinically eligible admissions actually diverted "
                "home — the top of the funnel and the scale determinant."),
            Kpi("Escalation / rescue rate to hospital", "target low single "
                "digits to ~10%",
                "The safety-and-economics linchpin — high rescue rates erase the "
                "savings and undercut the reauthorization case."),
            Kpi("Cost per episode vs inpatient benchmark", "target below IPPS",
                "The value proposition — home delivery must undercut the "
                "inpatient cost the DRG is priced on."),
            Kpi("Average daily census / capacity utilization", "scale-driven",
                "The fixed command-center and tech cost is only spread when "
                "census is high enough."),
            Kpi("Readmission & mortality (outcomes parity)", "≈ inpatient",
                "The evidence the CMS evaluation weighs — outcomes must match "
                "brick-and-mortar to justify the model."),
            Kpi("Drive-time / visit density", "market-specific",
                "The logistics variable — low density lengthens nurse drive-time "
                "and breaks the unit economics."),
        ],
        margin_profile=(
            "HaH unit economics are still emerging and illustrative. The margin "
            "is the spread between the inpatient DRG (or negotiated case rate) "
            "and the variable cost of delivering the episode at home — nursing "
            "labor, physician telehealth, DME, infusion, mobile diagnostics, "
            "logistics, and an allocated share of the 24/7 command center. "
            "Because the command center and technology are largely fixed, "
            "contribution scales steeply with census and with geographic density "
            "(shorter drive-times), and it is highly sensitive to nursing wages "
            "and rescue rates. A dense, high-census program with a low rescue "
            "rate can be solidly contribution-positive; a thin, low-density "
            "program with frequent escalations loses the savings that justify "
            "the model — and every scenario sits on top of the waiver."),
    ),
    risks=[
        Risk("AHCaH waiver lapse / no permanent FFS pathway", "High",
             "The Medicare-scale market exists only under a temporary waiver; a "
             "lapse removes the inpatient-billing pathway that carries revenue."),
        Risk("Scale & density economics", "High",
             "Fixed command-center cost and drive-time logistics mean sub-scale "
             "or low-density programs cannot reach positive contribution."),
        Risk("Clinical safety / escalation-rate exposure", "Medium",
             "High rescue rates undercut both the savings and the safety "
             "evidence the reauthorization depends on."),
        Risk("Nursing labor + logistics cost", "Medium",
             "Home-visit nursing supply and rapid-response logistics are scarce "
             "and expensive, especially outside dense metros."),
        Risk("Unproven long-run evidence base", "Medium",
             "The CMS/ASPE verdict on savings and outcomes is still being "
             "written and drives both reauthorization and any payment model."),
        Risk("In-house system programs & payer verticalization", "Medium",
             "Systems building their own programs and payers acquiring enablers "
             "compress the independent enablement opportunity."),
    ],
    diligence_questions=[
        "What share of revenue depends on the AHCaH waiver, and what is the "
        "concrete plan (and contracted MA/commercial book) if it lapses?",
        "What is the escalation/rescue rate and the safety/outcomes data versus "
        "the inpatient benchmark?",
        "What is the cost per episode versus the inpatient benchmark, and how "
        "does it scale with census and market density?",
        "Is this a direct-provider model (holding the DRG and clinical risk) or "
        "a B2B enablement model, and how is risk shared with the health system?",
        "How mature and durable are the MA/commercial contracts that would "
        "survive a waiver lapse?",
        "What is the eligible-patient capture rate and the depth of referral "
        "integration with host-hospital EHRs and ED workflows?",
        "What is the nursing-labor and mobile-ancillary logistics model, and "
        "the drive-time economics by market?",
        "What is the regulatory and licensure status in each operating state?",
    ],
    insider_lens=[
        "Underwrite the waiver first. HaH exists at Medicare scale only because "
        "of a temporary CMS waiver that Congress has extended in short bursts — "
        "a book that is mostly FFS-waiver dollars has a cliff, and the "
        "reauthorization is the first-order variable, ahead of any clinical "
        "story.",
        "Know who holds the DRG. Many 'hospital-at-home companies' are actually "
        "B2B enablers selling technology, staffing, and command-center services "
        "to systems that hold the billing and the risk — the revenue quality, "
        "margins, and defensibility are completely different for an enabler "
        "than for a risk-bearing provider.",
        "The rescue rate is the whole safety-and-savings case. Every patient "
        "escalated back to a physical bed both costs money and weakens the "
        "evidence CMS is weighing — a low, well-managed escalation rate is the "
        "operating metric that matters most.",
        "It's logistics as much as medicine. Nurse drive-time and mobile-"
        "ancillary density decide whether an episode is profitable; a clinically "
        "excellent program in a low-density market simply does not pencil.",
        "MA and commercial are the escape hatch. The only revenue that outlives "
        "a waiver lapse is negotiated payer contracts and any future CMS payment "
        "model — the depth of that non-waiver book is the real measure of "
        "durability.",
    ],
    connections=default_connections(
        "hospital_at_home",
        deals_sector="hospital_at_home",
        extra_pages=[
            ("/diligence/tam-sam?template=hospital_at_home",
             "Hospital-at-Home sizing + deal history (deals-only deep-dive)"),
        ],
        connectors=[
            ("healthdata_gov_hospital_capacity_facility",
             "HealthData.gov — hospital capacity (the bed-freeing rationale)"),
            ("cms_open_data_medicare_telehealth_trends",
             "CMS Medicare telehealth trends — the enabling-tech backdrop"),
            ("provider_data_hospital_general",
             "CMS Hospital General Info — host hospitals / customers"),
            ("provider_data_home_health_agencies",
             "CMS Home Health Agencies — overlapping home-delivery infrastructure"),
            ("census_acs_cbsa_profile",
             "Census ACS — CBSA density for drive-time / logistics economics"),
        ],
    ),
    sources=[
        Source("CMS — Acute Hospital Care at Home (AHCaH) program & approved-"
               "facility data", "GOV",
               "https://qualitynet.cms.gov/acute-hospital-care-at-home"),
        Source("Consolidated Appropriations Act, 2023 + subsequent continuing "
               "resolutions — AHCaH waiver extensions", "GOV",
               "https://www.congress.gov/"),
        Source("ASPE / CMS — hospital-at-home evaluation and report to Congress "
               "(outcomes & cost)", "GOV", "https://aspe.hhs.gov/"),
        Source("JAMA / Health Affairs — hospital-at-home outcomes, escalation, "
               "and cost-of-care studies", "ACADEMIC",
               "https://jamanetwork.com/"),
        Source("Medically Home / Contessa / DispatchHealth public materials — "
               "the enablement operating model", "INDUSTRY",
               "https://www.medicallyhome.com/"),
        Source("PE Desk industry deep-dive (deals-only) + realized-deal corpus",
               "INTERNAL", "/diligence/tam-sam?template=hospital_at_home"),
    ],
    live_figures=live_figures_from_dive("hospital_at_home"),
    trends=(
        "Hospital-at-home went from a fringe academic model to a national "
        "policy experiment almost overnight when CMS launched the Acute Hospital "
        "Care at Home waiver in November 2020, giving hospitals a way to bill "
        "inpatient DRGs for home-based acute care during a capacity crisis. In "
        "the years since, a few hundred hospitals across dozens of systems have "
        "stood up programs, an ecosystem of enablers (Medically Home, Contessa, "
        "DispatchHealth, Current Health, Inbound Health, Biofourmis) matured, and "
        "strategic buyers — payers, retailers, distributors — moved to own the "
        "capability. But the whole edifice still rests on a temporary waiver that "
        "Congress has extended only in short bursts, and on an unfinished CMS/"
        "ASPE evidence base about whether HaH truly saves money and matches "
        "outcomes. The trajectory therefore forks sharply: with permanence and a "
        "durable payment model (MA, commercial, or a dedicated CMMI model), a "
        "large slice of inpatient care could shift home over a decade; without "
        "it, the Medicare-scale market contracts to whatever payers will fund "
        "voluntarily. This is a genuine structural opportunity priced against a "
        "genuine binary policy risk."),
    growth_levers=[
        GrowthLever(
            "Inpatient capacity pressure (the system pull)",
            "Chronic bed scarcity and throughput pressure give hospitals a "
            "standing incentive to move eligible admissions home and free beds.",
            "primary system pull", "ILLUSTRATIVE"),
        GrowthLever(
            "Aging + chronic-disease admissions",
            "The clinical demand base — CHF, COPD, pneumonia, cellulitis, and "
            "infection admissions rise with the aging, chronically-ill "
            "population.",
            "+demographic demand", "GOV"),
        GrowthLever(
            "Enabling-technology maturation (RPM, telehealth, mobile Dx)",
            "Better remote monitoring, virtual physician rounding, and mobile "
            "diagnostics widen the set of conditions safely treatable at home.",
            "capability expansion", "ILLUSTRATIVE"),
        GrowthLever(
            "MA / commercial payment adoption",
            "Negotiated payer contracts (and a possible CMMI model) are the "
            "revenue that outlives the waiver and the path to a durable market.",
            "durability lever", "ILLUSTRATIVE"),
        GrowthLever(
            "Waiver reauthorization",
            "The binary gate — permanence unlocks the FFS market; a lapse "
            "removes the Medicare inpatient-billing pathway entirely.",
            "binary gate", "GOV"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Diversion of clinically eligible acute admissions from the "
               "hospital bed",
        analysis=(
            "HaH volume is not a new demand pool — it is a diversion of "
            "admissions that would otherwise fill a hospital bed. The dominant "
            "driver is therefore the intersection of two things: the clinical "
            "eligibility of an admission (a meaningful but bounded share of "
            "medical admissions — CHF, COPD, pneumonia, cellulitis, selected "
            "infections — that can be safely managed at home) and the health "
            "system's incentive to divert them, which is strongest when beds are "
            "scarce. That makes the near-term growth curve a function of program "
            "adoption and capture rate rather than underlying disease incidence. "
            "The long-run ceiling is large — a double-digit percentage of "
            "inpatient care is plausibly home-shiftable — but the realized "
            "volume is gated by the waiver, by payer willingness to fund the "
            "non-waiver book, and by the logistics of reaching enough eligible "
            "patients densely enough to be economic."),
        basis="ILLUSTRATIVE"),
    cost_drivers=[
        CostDriver(
            "In-home clinical labor (nursing visits, paramedicine)",
            "~35-45% of cost",
            "The largest variable cost — home-visit nursing and community "
            "paramedicine; supply and wages, and drive-time, drive the whole "
            "episode economics.", "ILLUSTRATIVE"),
        CostDriver(
            "Command center & virtual physician rounding",
            "~15-20% of cost",
            "The 24/7 monitoring hub and daily virtual physician evaluation — "
            "largely fixed, so it only pencils at scale/census.", "ILLUSTRATIVE"),
        CostDriver(
            "Logistics & mobile ancillaries (Dx, imaging, infusion, DME)",
            "~15-20% of cost",
            "Getting labs, imaging, infusion, and equipment to the home quickly "
            "— a dispatch-and-density problem that punishes low-density markets.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Technology platform & remote monitoring",
            "~10-15% of cost",
            "Biometric kits, connectivity, and the software layer integrating "
            "with the host EHR — a fixed-plus-per-episode cost.", "ILLUSTRATIVE"),
        CostDriver(
            "Pharmacy & medical supplies",
            "~8-12% of cost",
            "IV and oral medications and consumables delivered to the home over "
            "the episode.", "ILLUSTRATIVE"),
    ],
    state_breakdown=None,
)

register(REPORT)
