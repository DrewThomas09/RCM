"""Palliative — specialized care for serious illness (not end-of-life only).

Deals-only deep-dive (the CAPC registry covers hospital programs, not community
providers). Authored around the structural fact that distinguishes palliative
from hospice: there is no dedicated Medicare palliative benefit and no
6-month-prognosis limit, so fee-for-service professional billing does not cover
the interdisciplinary team — the economics only work at risk (MA, ACO, serious-
illness population contracts) or as a top-of-funnel feeder into hospice.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks,
    Kpi, MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule,
    Segment, Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="palliative",
    name="Palliative",
    care_setting="Post-acute",
    naics="621999",
    one_line_def=(
        "Specialized interdisciplinary care for people living with serious "
        "illness — symptom management, care coordination, and goals-of-care "
        "support delivered ALONGSIDE curative treatment (no 6-month-prognosis "
        "limit, unlike hospice) across hospital consult teams, clinics, and "
        "home-based programs."),
    tam_headline=TamHeadline(
        value=12.0, unit="$B", growth_pct=9.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "Modeled US palliative-care spend across hospital consult "
            "programs, clinic, and community/home-based delivery — there is no "
            "dedicated Medicare benefit to anchor a filed figure, so this is a "
            "composite of professional billing plus the value-based / at-risk "
            "contracting that actually funds the team. Growth is the modeled "
            "composite of the serious-illness population and MA/ACO adoption of "
            "at-risk palliative."),
    ),
    executive_summary=[
        "Palliative is NOT hospice. There is no 6-month-prognosis requirement "
        "and no election to forgo curative care — palliative runs concurrently "
        "with treatment for anyone with serious illness. And there is no "
        "dedicated Medicare palliative benefit.",
        "Because there is no benefit, palliative is billed piecemeal under the "
        "physician fee schedule (E/M, advance-care-planning, chronic-care-"
        "management codes), which does NOT pay for the interdisciplinary team "
        "(social work, chaplaincy). Pure fee-for-service palliative loses "
        "money.",
        "The economics only work at risk. The value of palliative is total-"
        "cost-of-care reduction — fewer ICU days, fewer readmissions — so it "
        "pays when you own or share those savings: MA at-risk contracts, ACOs, "
        "and serious-illness population management (PMPM + shared savings).",
        "The buyers are payers, not classic PE. Elevance bought Aspire Health, "
        "Humana bought Prospero, Optum owns Landmark — vertical integration by "
        "payers who capture the savings, because that is where the value "
        "lands.",
        "For hospices, community palliative is a top-of-funnel feeder that "
        "drives earlier, longer hospice enrollment — its strategic value "
        "(better hospice length of stay) often exceeds its standalone P&L.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Identification of the seriously-ill patient (hospital, health "
            "plan, ACO, or referral)",
            "Interdisciplinary assessment — physician/NP, nurse, social worker, "
            "chaplain",
            "Symptom management + goals-of-care and advance-care-planning "
            "conversations",
            "Care coordination across specialists, primary care, and the "
            "family",
            "Delivery — hospital consult, outpatient clinic, or home-based "
            "visits + 24/7 support",
            "Billing — professional fees under the fee schedule, OR a PMPM / "
            "at-risk contract",
            "For hospice-owned programs: transition to the hospice benefit at "
            "the right time",
        ],
        sites_of_care=[
            "Hospital inpatient consult team (where most palliative still "
            "happens)",
            "Outpatient / clinic-based palliative program",
            "Home-based / community palliative (the growth frontier)",
            "Long-term care and assisted-living facilities",
        ],
        money_flow=(
            "Unlike hospice's per-diem benefit, palliative has no dedicated "
            "payment vehicle, so revenue is stitched together. On fee-for-"
            "service, physicians and NPs bill the Medicare Physician Fee "
            "Schedule — office/home E/M visits, advance-care-planning codes "
            "(99497/99498), chronic-care and complex-care management — but "
            "those fees do not cover the social workers and chaplains the model "
            "requires, so a professional-fee-only program runs at a loss and is "
            "subsidized by the hospital. The economics invert under risk: a "
            "Medicare Advantage plan, an ACO, or a serious-illness contract "
            "pays a per-member fee and/or shares the savings that palliative "
            "generates by cutting avoidable hospital and ICU days. In that "
            "model the team is funded by the total-cost-of-care reduction it "
            "produces — which is why the value accrues to whoever holds the "
            "risk."),
        key_players=(
            "The marquee community-palliative platforms were absorbed by "
            "payers: Aspire Health (Elevance/Anthem), Prospero (Humana), and "
            "Landmark Health (Optum) — high-need, home-based medical groups for "
            "which palliative is core. Contessa (Amedisys) runs palliative-at-"
            "home; ConcertoCare, Vynca, and Empatia pursue serious-illness "
            "management. Most inpatient palliative sits inside hospitals and "
            "academic medical centers, and most hospices (VITAS, Gentiva, "
            "Amedisys) run community palliative as an upstream feeder into the "
            "hospice benefit."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Hospital-based palliative consult programs",
                    "the largest share of delivery",
                    "ACADEMIC · CAPC hospital palliative-program prevalence"),
            Segment("Community / home-based palliative",
                    "the growth frontier (payer-funded)",
                    "ILLUSTRATIVE · modeled at-risk community-palliative share"),
            Segment("Serious-illness population (the addressable base)",
                    "millions of multi-chronic, high-cost patients",
                    "ILLUSTRATIVE · modeled from CMS high-need/multi-chronic "
                    "counts"),
            Segment("MA + ACO at-risk palliative contracts",
                    "where community economics actually work",
                    "ILLUSTRATIVE · modeled at-risk contracting adoption"),
        ],
        growth_drivers=[
            "Growth in the seriously-ill / multi-chronic population ~4%/yr",
            "MA penetration — plans wanting to manage their highest-cost "
            "members",
            "Shift of palliative from the hospital to the home",
            "CMMI serious-illness models (e.g. GUIDE for dementia) funding the "
            "team",
            "Hospice integration — palliative as an upstream feeder improving "
            "length of stay",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Medicare FFS (physician fee schedule, professional)": 0.45,
            "Medicare Advantage / at-risk (PMPM + shared savings)": 0.35,
            "Commercial / ACO / other": 0.20,
        },
        rate_mechanics=[
            "Physician Fee Schedule (MPFS) — E/M office/home visits plus "
            "advance-care-planning (99497/99498), chronic-care and complex-"
            "care management; the FFS backbone that under-funds the team.",
            "No dedicated Medicare palliative benefit — the defining structural "
            "gap versus hospice's per-diem benefit.",
            "Value-based / at-risk — MA and ACO contracts pay a PMPM and/or "
            "share the total-cost-of-care savings palliative produces; the "
            "model that actually pays for the interdisciplinary team.",
            "CMMI serious-illness models — e.g. GUIDE (dementia, launched "
            "2024) pays a care-management PMPM that funds palliative-style "
            "support; the former Medicare Care Choices Model tested concurrent "
            "hospice+curative care.",
            "Hospital subsidy — inpatient consult programs are commonly funded "
            "by the hospital because they reduce length of stay and cost, not "
            "because the professional fees cover them.",
            "MA supplemental benefits — some plans buy in-home palliative "
            "support as a supplemental/again-VBID-style benefit.",
        ],
        reimbursement_risk=(
            "The core risk is structural: with no dedicated benefit, a "
            "professional-fee-only palliative program cannot cover its own "
            "interdisciplinary team and depends on hospital subsidy or an at-"
            "risk contract to survive. That makes revenue durability a function "
            "of contract structure — a program leaning on FFS is exposed to the "
            "annual MPFS conversion-factor cuts and simply cannot scale the "
            "team, while an at-risk program depends on accurately pricing and "
            "managing a high-cost, high-variance seriously-ill population. There "
            "is also no standardized quality or payment framework (unlike "
            "hospice's HQRP and per-diem), so contracting is bespoke and "
            "renewal risk is real. The upside case — owning the savings — is "
            "also the risk case: mis-managing the population turns a shared-"
            "savings contract into a loss."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("No Medicare palliative Conditions of Participation / benefit",
                 "Community palliative is not a Medicare-certified benefit with "
                 "its own CoPs or per-diem — the single most important "
                 "structural fact about the sector's economics.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
            Rule("Advance Care Planning + CCM/PCM billing codes",
                 "The fee-schedule codes (99497/99498, chronic- and principal-"
                 "care management) that palliative programs rely on — subject "
                 "to MPFS updates and documentation rules.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
            Rule("GUIDE Model — Guiding an Improved Dementia Experience (2024)",
                 "A CMMI model paying a care-management PMPM for dementia — a "
                 "concrete, palliative-adjacent payment pathway that funds team-"
                 "based serious-illness care.",
                 "https://www.cms.gov/priorities/innovation/innovation-models/guide"),
            Rule("Medicare Advantage / VBID + supplemental-benefit authority",
                 "The rules that let MA plans buy and delegate at-risk / in-"
                 "home palliative — the channel where community economics "
                 "work.",
                 None),
            Rule("Hospice regulation (42 CFR 418) where palliative is hospice-"
                 "delivered",
                 "When a hospice runs community palliative as a feeder, the "
                 "hospice CoPs, eligibility, and anti-kickback rules govern the "
                 "referral relationship.",
                 "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-418"),
        ],
        policy_watch=[
            "Any move toward a dedicated community-palliative benefit or "
            "demonstration",
            "GUIDE model rollout and serious-illness payment pathways",
            "MPFS conversion-factor cuts (the FFS backbone's exposure)",
            "MA supplemental-benefit and at-risk-palliative contracting scope",
            "Concurrent-care / hospice-adjacency policy after the Care Choices "
            "Model",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Fragmented and nascent as a standalone business. Most palliative "
            "capacity sits inside hospitals (consult teams) and hospices "
            "(feeder programs) rather than in independent companies, and the "
            "specialized community platforms are few. There is no vendored "
            "national community-palliative registry, so a computed geographic "
            "share is honestly omitted — the CAPC data covers hospital programs, "
            "not community providers."),
        hhi_or_share=(
            "No independent operator holds meaningful national share; the "
            "largest community platforms were acquired by payers, and the rest "
            "of delivery is dispersed across hospitals and hospices. "
            "Concentration is low and sits with the integrated payers."),
        consolidation=(
            "Consolidation has run through payer vertical integration rather "
            "than PE roll-up: Elevance/Anthem acquired Aspire Health, Humana "
            "acquired Prospero, and Optum owns Landmark Health — high-need "
            "home-based groups for which palliative is central. Amedisys folded "
            "in Contessa's palliative-at-home. Hospices continue to build "
            "community palliative organically as an upstream funnel."),
        pe_activity=(
            "Less classic-PE than most post-acute verticals precisely because "
            "the value accrues to the risk-holder: payers are the natural "
            "owners, so they have been the acquirers. PE and growth capital "
            "show up in serious-illness / high-need home-based medical groups "
            "(the palliative-adjacent VBC plays) rather than in standalone "
            "palliative billing businesses, whose FFS economics do not stand "
            "alone."),
        notable_players=[
            "Aspire Health (Elevance)", "Prospero (Humana)",
            "Landmark Health (Optum)", "Contessa (Amedisys)",
            "ConcertoCare", "Vynca", "Empatia",
            "Hospital-based academic palliative programs",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("PMPM (at-risk / serious-illness contract)", "contract-specific",
                "The revenue unit where community palliative works; sized to "
                "the population's cost and the savings opportunity."),
            Kpi("Hospital-admission / ICU-day reduction", "the value metric",
                "The savings palliative produces — what an at-risk or shared-"
                "savings contract monetizes."),
            Kpi("Panel size per physician / NP", "the scale lever",
                "NP-led models scale a scarce palliative workforce; panel size "
                "drives the professional-fee and management economics."),
            Kpi("Hospice conversion rate (for hospice-owned programs)",
                "the feeder value",
                "How effectively community palliative funnels patients into "
                "the hospice benefit at the right time."),
            Kpi("FFS professional-fee cost coverage", "typically < 100%",
                "The tell that a program cannot survive on FFS alone — the "
                "team costs more than the fees pay."),
            Kpi("Program contribution margin", "negative on FFS · positive at "
                "risk",
                "The whole thesis in one line: FFS loses money, at-risk (well "
                "managed) makes it."),
        ],
        margin_profile=(
            "Palliative margin is a story of two models. The professional-fee "
            "model is structurally negative: the fee schedule pays for "
            "physician/NP visits but not for the social workers, chaplains, and "
            "24/7 coordination the model requires, so a standalone FFS program "
            "runs at a loss and survives on hospital subsidy or as a hospice "
            "feeder. The at-risk model inverts that: paid a PMPM and/or a share "
            "of the total-cost-of-care savings it generates, a well-managed "
            "program on a seriously-ill population can earn a healthy margin — "
            "but only if it prices the population correctly and actually "
            "reduces avoidable hospital and ICU use. Scale helps by spreading a "
            "scarce specialist workforce (via NP-led panels) and by "
            "diversifying population risk across contracts."),
    ),
    risks=[
        Risk("No dedicated benefit / FFS under-funds the team", "High",
             "Professional fees do not cover the interdisciplinary team, so "
             "standalone FFS palliative cannot scale or sustain itself."),
        Risk("Contract / at-risk dependence and renewal", "High",
             "The viable model depends on bespoke MA/ACO at-risk contracts; "
             "loss or repricing of a key contract is an outsized revenue "
             "event."),
        Risk("Population risk mispricing", "High",
             "At risk on a high-cost, high-variance seriously-ill population, a "
             "mispriced or under-managed panel turns shared savings into "
             "loss."),
        Risk("MPFS conversion-factor cuts", "Medium",
             "The FFS backbone is exposed to annual physician-fee-schedule "
             "reductions, worsening the coverage gap."),
        Risk("Palliative-physician workforce shortage", "Medium",
             "A severe specialist shortage caps growth; NP-led models mitigate "
             "but do not eliminate it."),
        Risk("Referral / anti-kickback exposure (hospice-linked programs)",
             "Medium",
             "Where palliative feeds an owned hospice, the referral "
             "relationship draws Stark/AKS scrutiny."),
    ],
    diligence_questions=[
        "What share of revenue is FFS professional billing versus at-risk / "
        "PMPM, and what is the contribution margin of each?",
        "What is the total-cost-of-care impact — documented admission / ICU / "
        "readmission reduction — that anchors the at-risk contracts?",
        "How concentrated is revenue by contract and by payer, and what is the "
        "renewal / repricing risk?",
        "For hospice-owned programs, what is the palliative-to-hospice "
        "conversion rate and the effect on hospice length of stay?",
        "How is the population risk priced, and what is the historical "
        "medical-cost performance against target?",
        "What is the clinical staffing model (physician vs NP-led) and the "
        "panel size per clinician?",
        "What is the exposure to MPFS cuts and to any single CMMI model (e.g. "
        "GUIDE) for revenue?",
        "How are referral relationships with owned hospice / home health "
        "structured against Stark and Anti-Kickback?",
    ],
    insider_lens=[
        "Palliative is the concurrent-care cousin of hospice — no prognosis "
        "clock, care alongside treatment — but the fee schedule pays for a "
        "doctor's visit, not for the team, so pure-FFS palliative is a "
        "money-loser dressed up as a service line.",
        "Follow the savings to find the owner. Palliative's value is fewer ICU "
        "days and readmissions, which a PAYER captures — which is exactly why "
        "Elevance, Humana, and Optum bought the platforms and PE largely did "
        "not.",
        "For a hospice, community palliative is a length-of-stay machine. It "
        "gets patients into hospice earlier and for longer — the strategic "
        "value shows up in the hospice P&L, not the palliative one, so never "
        "value the two in isolation.",
        "The thesis and the risk are the same sentence: 'the right care avoids "
        "the wrong costs.' You only monetize it if you own or share the "
        "savings, and you only earn it if you actually manage the population.",
        "The workforce is the quiet ceiling. Palliative physicians are scarce; "
        "the operators who scale do it with NP-led panels and disciplined "
        "identification of the right seriously-ill patients — not by hiring "
        "specialists they cannot find.",
    ],
    connections=default_connections(
        "palliative",
        deals_sector="palliative",
        extra_pages=[
            ("/market/hospice",
             "Adjacency — the Hospice report (palliative's downstream benefit "
             "and feeder relationship)"),
            ("/diligence/tam-sam?template=palliative",
             "Size it — palliative TAM/SAM build (serious-illness population "
             "chain)"),
        ],
        connectors=[
            ("provider_data_hospice_general",
             "CMS Hospice General Information — the downstream benefit and "
             "feeder relationship"),
            ("cms_open_data_acos",
             "CMS ACO data — the shared-savings vehicle palliative reduces "
             "cost for"),
            ("npi_provider_taxonomy",
             "NPI taxonomy — hospice & palliative medicine clinicians (the "
             "scarce workforce)"),
            ("cdc_data_nchs_leading_causes",
             "CDC NCHS leading causes of death — the serious-illness demand "
             "base"),
            ("census_acs_cbsa_profile",
             "Census ACS — senior (65+) density for program planning"),
        ],
    ),
    sources=[
        Source("Center to Advance Palliative Care (CAPC) — hospital and "
               "community palliative-care prevalence and standards",
               "INDUSTRY", "https://www.capc.org/"),
        Source("CMS — Medicare Physician Fee Schedule (E/M, advance care "
               "planning, chronic care management)", "GOV",
               "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
        Source("CMS Innovation Center — GUIDE Model (dementia care "
               "management)", "GOV",
               "https://www.cms.gov/priorities/innovation/innovation-models/guide"),
        Source("National Academies / JAMA / JPSM — research on palliative "
               "care and total-cost-of-care impact", "ACADEMIC",
               "https://jamanetwork.com/"),
        Source("American Academy of Hospice and Palliative Medicine (AAHPM) — "
               "workforce and practice data", "INDUSTRY",
               "https://aahpm.org/"),
        Source("PE Desk industry deep-dive (deals-only) + realized-deal "
               "corpus for palliative (hospice adjacency)", "INTERNAL",
               "/diligence/tam-sam?template=palliative"),
    ],
    live_figures=live_figures_from_dive("palliative"),
    trends=(
        "Palliative care has been on a two-track trajectory. Inside hospitals "
        "it became standard of care — the great majority of larger hospitals "
        "now run consult teams (documented by CAPC) — but that growth was "
        "funded by hospital subsidy, not by any dedicated benefit. Outside the "
        "hospital, the story is the search for a payment model: because "
        "fee-for-service cannot cover the interdisciplinary team, community "
        "palliative only scaled where a payer would fund it. That pulled the "
        "sector into value-based care, and the marquee platforms were absorbed "
        "by payers — Elevance/Aspire, Humana/Prospero, Optum/Landmark — who "
        "capture the total-cost-of-care savings palliative produces. CMMI's "
        "serious-illness experiments (Medicare Care Choices, and now GUIDE for "
        "dementia) kept probing a dedicated pathway. Meanwhile hospices built "
        "community palliative as an upstream feeder to lengthen and deepen "
        "hospice enrollment. The direction of travel is clear — more serious-"
        "illness patients, more at-risk contracting, more care at home — but "
        "the constraint is equally clear: without a benefit, palliative "
        "monetizes only through risk, and only for those who can manage the "
        "population."),
    growth_levers=[
        GrowthLever(
            "MA / ACO at-risk contracting",
            "Plans and ACOs pay a PMPM and share savings for managing their "
            "highest-cost members — the model that funds the team.",
            "primary", "ILLUSTRATIVE"),
        GrowthLever(
            "Serious-illness population growth",
            "The multi-chronic, high-need population expands structurally, "
            "enlarging the addressable base for palliative management.",
            "+4%/yr population", "ILLUSTRATIVE"),
        GrowthLever(
            "Shift from hospital to home",
            "Community and home-based palliative grows as payers move serious-"
            "illness management out of the hospital.",
            "site-shift", "ILLUSTRATIVE"),
        GrowthLever(
            "CMMI serious-illness models (GUIDE, etc.)",
            "Dedicated care-management PMPMs create concrete payment pathways "
            "for team-based serious-illness care.",
            "policy tailwind", "GOV"),
        GrowthLever(
            "Hospice-integration / feeder value",
            "Palliative lengthens and deepens downstream hospice enrollment, "
            "adding value that shows up in the hospice P&L.",
            "strategic", "ILLUSTRATIVE"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Seriously-ill / multi-chronic population × at-risk payer "
               "adoption",
        analysis=(
            "The demand base is the population living with serious, "
            "life-limiting illness — advanced heart failure, COPD, cancer, "
            "dementia, and multi-morbidity — a group that is both large and "
            "growing as the population ages and as more conditions become "
            "chronic-but-survivable. What converts that latent demand into "
            "palliative volume is not the patients' willingness (it is high) "
            "but the payment: because there is no benefit, realized volume "
            "tracks the adoption of at-risk contracting by Medicare Advantage "
            "plans, ACOs, and CMMI models that will fund the interdisciplinary "
            "team. So the honest read is a large, rising demand base whose "
            "realized volume is gated by payer willingness to pay for "
            "total-cost-of-care management — the population sets the ceiling, "
            "at-risk adoption sets the pace."),
        basis="ILLUSTRATIVE"),
    cost_drivers=[
        CostDriver(
            "Interdisciplinary clinical labor (MD/NP, RN, MSW, chaplain)",
            "the dominant cost",
            "The team the fee schedule will not pay for — the reason FFS "
            "palliative loses money and at-risk is required.", "ILLUSTRATIVE"),
        CostDriver(
            "Home visits / travel (community programs)",
            "material for home-based models",
            "Windshield time and per-visit logistics for a dispersed, "
            "homebound seriously-ill population.", "ILLUSTRATIVE"),
        CostDriver(
            "24/7 coordination & after-hours coverage",
            "a fixed support cost",
            "Round-the-clock availability to prevent avoidable ER/hospital use "
            "— the cost that produces the savings.", "ILLUSTRATIVE"),
        CostDriver(
            "Care-management technology & analytics",
            "growing with at-risk models",
            "Population identification, risk stratification, and outcomes "
            "measurement needed to price and manage at-risk contracts.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Physician recruitment (scarce specialty)",
            "a scarcity premium",
            "The severe palliative-physician shortage raises acquisition cost "
            "and pushes models toward NP-led staffing.", "ILLUSTRATIVE"),
    ],
    # Deals-only vertical: no provider_backed CMS roll, so cms_trend and a
    # computed state_breakdown are intentionally omitted — the renderer shows an
    # honest "unavailable offline" note and the qualitative sections carry the
    # weight. The live figures above are the corpus palliative/hospice-adjacency
    # deals, computed at render.
)

register(REPORT)
