"""PACE — Program of All-Inclusive Care for the Elderly.

Deals-only deep-dive (the National PACE Association program roster is not
vendored). Authored around the structural fact that a PACE organization is a
fully-capitated risk-bearer wearing a provider's clothes: it takes dual Medicare
+ Medicaid capitation for the frailest, nursing-home-eligible seniors and is at
risk for ALL of their care. The economics turn on the Medicaid rate negotiation,
census ramp, nursing-home diversion, and regulatory-sanction risk.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks,
    Kpi, MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule,
    Segment, Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="pace",
    name="PACE",
    care_setting="Post-acute",
    naics="621498",
    one_line_def=(
        "A fully-capitated, provider-sponsored integrated-care model for "
        "nursing-home-eligible seniors (55+) who live in the community — the "
        "PACE organization takes full risk for ALL Medicare + Medicaid "
        "services and delivers them through an interdisciplinary team anchored "
        "at a PACE adult-day center."),
    tam_headline=TamHeadline(
        value=8.0, unit="$B", growth_pct=12.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "Modeled combined Medicare+Medicaid PACE capitation revenue — "
            "roughly 75-80K enrollees at a blended dual PMPM near $7,500-9,000 "
            "(the frailest, most expensive duals). Growth is the modeled "
            "composite of enrollment expansion (new states/slots + census "
            "fill) far above demographic growth, off a <1% penetration base. "
            "Anchored to NPA enrollment counts and CMS PACE rates, not a single "
            "filed dollar total."),
    ),
    executive_summary=[
        "PACE is an insurance company wearing a provider's clothes. The "
        "organization receives dual capitation — a Medicare Part C/D payment "
        "plus a Medicaid payment — and is fully at risk for every dollar of "
        "the enrollee's care: primary, specialty, hospital, drugs, long-term "
        "services, the day center, transportation, and meals.",
        "The Medicaid rate negotiation with the state IS the deal. Medicaid "
        "capitation is typically set below what the state would have paid for "
        "nursing-home care (the value proposition), so the entire model rests "
        "on an actuarial/political negotiation, not a market price.",
        "Census ramp is brutal. A new center bleeds cash for years until it "
        "fills, because the interdisciplinary team, center, and transportation "
        "are fixed costs spread over too few participants. Enterprise value is "
        "about mature-census centers, not the count of centers.",
        "Nursing-home placement is the tail risk. The organization pays for a "
        "permanent nursing-home stay out of its own capitation, so keeping "
        "frail seniors safely in the community IS the margin — clinical "
        "management is the P&L.",
        "Tiny today, structurally under-penetrated. ~150-180 organizations and "
        "~75-80K enrollees nationally against millions of nursing-home-eligible "
        "duals; growth is expansion-limited (state approvals, slots, ramp), not "
        "demand-limited — which is exactly why for-profit and PE capital "
        "arrived.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Eligibility — age 55+, state-certified nursing-home level of care, "
            "living in a PACE service area, able to live safely in the "
            "community",
            "Enrollment — voluntary; the participant leaves fee-for-service and "
            "gets all care through PACE",
            "Interdisciplinary team (IDT) assessment + individualized care plan",
            "Care delivery — PACE day center (medical clinic, therapy, adult "
            "day health), plus home care and contracted specialty/hospital",
            "Transportation to/from the center and appointments (a core, "
            "capitated service)",
            "Total-cost-of-care management — the IDT coordinates every "
            "service to keep the participant out of the hospital and nursing "
            "home",
            "Dual capitation reconciliation + CMS/state audit and reporting",
        ],
        sites_of_care=[
            "PACE center — the hub (clinic + adult day health + therapy + "
            "socialization)",
            "Participant's home (home care, personal care, home visits)",
            "Contracted hospital / specialist / SNF (paid out of capitation)",
            "Permanent nursing facility (a cost the PACE org bears if placement "
            "is needed)",
        ],
        money_flow=(
            "A PACE organization is paid two capitated streams and bears full "
            "risk against both. Medicare pays a Part C rate — a risk-adjusted "
            "county benchmark plus a PACE-specific frailty adjuster (because "
            "PACE enrollees are frailer than typical Medicare Advantage) — plus "
            "Part D for drugs. Medicaid pays a separately negotiated monthly "
            "capitation, usually pegged below the cost the state would "
            "otherwise incur for institutional nursing-home care. There is no "
            "fee-for-service: the organization is simultaneously the payer and "
            "the provider, so every avoided hospital day or nursing-home "
            "placement is retained margin, and every unmanaged complication is "
            "an absorbed cost. The whole enterprise is total-cost-of-care "
            "management on a fixed dual PMPM for the frailest 5% of seniors."),
        key_players=(
            "Historically nonprofit and community-rooted — On Lok in San "
            "Francisco originated the model. The last decade brought scaled "
            "for-profit and venture/PE-backed operators: InnovAge (the largest, "
            "publicly traded, for-profit), WelbeHealth, ConcertoCare, "
            "CareConnectMD, and a wave of new entrants, alongside a long tail "
            "of single-market nonprofits and health-system programs. The "
            "National PACE Association (NPA) is the trade body and the sector's "
            "advocacy engine for state expansion."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("PACE enrollees (national)", "~75-80K participants",
                    "INDUSTRY · National PACE Association enrollment"),
            Segment("PACE organizations / centers", "~150-180 orgs, ~270-300 "
                    "centers",
                    "INDUSTRY · National PACE Association program counts"),
            Segment("Dual-eligible enrollees (Medicare + Medicaid)",
                    "the overwhelming majority of PACE",
                    "GOV · CMS PACE program characteristics"),
            Segment("Nursing-home-eligible duals (the addressable pool)",
                    "millions — <1% PACE-penetrated",
                    "ILLUSTRATIVE · modeled from CMS dual + LTC-eligible "
                    "counts"),
        ],
        growth_drivers=[
            "State expansion — new PACE states and added slots (the binding "
            "growth gate)",
            "Census fill at existing centers — the highest-return growth "
            "(marginal enrollee on fixed cost)",
            "For-profit + PE entry — capital to open and scale new centers",
            "Rural and de-novo center expansion — reaching un-served service "
            "areas",
            "Very low penetration of nursing-home-eligible duals — long "
            "structural runway",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Medicaid capitation": 0.55,
            "Medicare (Part C + D) capitation": 0.44,
            "Private pay (non-Medicaid-eligible participants)": 0.01,
        },
        rate_mechanics=[
            "Dual capitation — a Medicare Part C payment plus a Medicaid "
            "payment; the organization is fully at risk for all covered "
            "services, with no fee-for-service.",
            "Medicare frailty adjuster — a PACE-specific factor layered on the "
            "CMS-HCC risk score to reflect that PACE enrollees are frailer than "
            "typical MA members.",
            "Medicaid rate — a state-negotiated monthly capitation, generally "
            "set below the state's institutional (nursing-home) cost; the "
            "single most important economic variable.",
            "Part D — prescription-drug capitation folded into the model.",
            "Risk adjustment / encounter data — accurate coding drives the "
            "Medicare payment, as in MA, but on a frailer population.",
            "Private-pay PACE — participants who are Medicare-only (not "
            "Medicaid-eligible) may pay the Medicaid-equivalent premium out of "
            "pocket; a small minority.",
        ],
        reimbursement_risk=(
            "The primary risk is the adequacy of the Medicaid rate. Because it "
            "is negotiated with the state and pegged to institutional cost, a "
            "rate set too low leaves the organization absorbing care costs it "
            "cannot recover — and PACE cannot simply drop the benefit. The "
            "secondary risk is actuarial: the organization is fully at risk for "
            "the frailest seniors, so an under-managed population (excess "
            "hospital days, avoidable nursing-home placements) turns capitation "
            "into loss. Medicare risk-coding accuracy and the frailty adjuster "
            "add MA-style rate exposure. And unlike a health plan, PACE has "
            "little reinsurance cushion at the single-center level, so an "
            "immature census amplifies every actuarial miss."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("PACE Program Regulations (42 CFR Part 460)",
                 "The federal rulebook — IDT requirements, enrollment, service "
                 "delivery, and the CMS+state dual-oversight regime that "
                 "governs every organization.",
                 "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-E/part-460"),
            Rule("2019 PACE Final Rule (modernization)",
                 "Updated the model — e.g. allowing community-based (non-center-"
                 "employed) physicians and other flexibilities — easing "
                 "expansion.",
                 "https://www.cms.gov/newsroom/fact-sheets/programs-all-inclusive-care-elderly-pace-final-rule"),
            Rule("State PACE election + program agreement",
                 "A state must elect PACE as a Medicaid option and approve each "
                 "organization and its slots; state approval is the true entry "
                 "barrier (a CON-like, 12-18+ month process).",
                 None),
            Rule("For-profit PACE authority (BBA 1997 pilot, made permanent)",
                 "Federal law permits for-profit PACE organizations — the legal "
                 "basis for the recent for-profit / PE entry into a historically "
                 "nonprofit field.",
                 None),
            Rule("CMS enrollment sanctions / audit authority",
                 "CMS can freeze new enrollment at a non-compliant "
                 "organization (as it did with InnovAge centers in 2021) — an "
                 "existential, growth-stopping enforcement lever.",
                 "https://www.cms.gov/medicare-medicaid-coordination/pace"),
        ],
        policy_watch=[
            "State PACE expansion decisions and slot allocations (the growth "
            "gate)",
            "CMS PACE rate methodology, the frailty adjuster, and risk-"
            "adjustment changes",
            "PACE-audit findings and enrollment-sanction actions (compliance "
            "risk)",
            "Rural PACE and PACE-innovation / pilot authorities",
            "Any expansion of PACE eligibility below age 55 or beyond "
            "nursing-home-level-of-care",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Structurally fragmented by design — PACE is delivered center-by-"
            "center in defined service areas, so even the largest operators run "
            "a modest number of markets. Historically a landscape of single-"
            "market nonprofits; the entry of scaled for-profit operators is "
            "only beginning to concentrate it. There is no vendored program "
            "roster, so a computed geographic share is honestly omitted."),
        hhi_or_share=(
            "InnovAge is the largest single operator but still a minority of "
            "national enrollment; the field remains a patchwork of local "
            "nonprofits and a handful of scaling for-profits. Concentration is "
            "low and rising, not high."),
        consolidation=(
            "Early-stage consolidation. Capital has flowed to build and scale "
            "new centers (InnovAge's IPO, WelbeHealth's venture rounds, "
            "ConcertoCare and others), and health systems and Medicaid MCOs "
            "have partnered on or sponsored programs. But the slow state-"
            "approval process and multi-year census ramp cap how fast anyone "
            "can roll up — this is a build-and-fill story more than a buy-and-"
            "build one."),
        pe_activity=(
            "Active and thesis-driven: PACE offers full-risk economics on the "
            "highest-cost seniors with enormous under-penetration, which is "
            "catnip for value-based-care capital. But the InnovAge enrollment "
            "sanction was a live reminder that compliance and census maturity, "
            "not TAM, gate returns — diligence now centers on center-level "
            "census ramps, medical-management track record, and regulatory "
            "standing."),
        notable_players=[
            "InnovAge", "WelbeHealth", "ConcertoCare", "CareConnectMD",
            "On Lok (the originator)", "Trinity Health PACE",
            "AltaMed Senior BuenaCare", "National PACE Association (trade body)",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Blended dual capitation (PMPM)", "~$7,500-9,000",
                "Medicare + Medicaid combined; high because the population is "
                "the frailest, most expensive seniors."),
            Kpi("Census per center", "target a few hundred participants",
                "Fixed IDT + center + transportation cost demands scale; a "
                "half-empty center loses money."),
            Kpi("Time to center breakeven", "~2-4 years",
                "The ramp to fill census is the defining cash-flow reality of a "
                "de-novo center."),
            Kpi("Hospital / SNF utilization", "the managed-cost variable",
                "Avoided admissions and avoided permanent nursing-home "
                "placement are retained margin."),
            Kpi("Permanent nursing-home placement rate", "low is the goal",
                "The organization pays for placement out of capitation — "
                "community tenure IS the P&L."),
            Kpi("Mature-center operating margin", "thin and variable",
                "Positive at mature census with good medical management; "
                "fragile at low census or after an actuarial miss."),
        ],
        margin_profile=(
            "PACE margin is total-cost-of-care management against a fixed dual "
            "capitation, on a small, frail, high-variance population. Two "
            "things dominate: census maturity (fixed center + IDT + "
            "transportation cost spread over enough participants) and clinical "
            "management (keeping participants out of the hospital and out of "
            "permanent nursing-home placement). A mature, well-run center earns "
            "a modest operating margin; an immature or poorly managed one loses "
            "money quickly because there is no fee-for-service floor and little "
            "single-center reinsurance. Scale helps administratively and "
            "spreads actuarial variance across centers, but each center must "
            "still fill and manage its own risk."),
    ),
    risks=[
        Risk("Medicaid rate adequacy", "High",
             "A state capitation set too low, pegged to institutional cost, "
             "leaves unrecoverable care cost — and PACE cannot drop the "
             "benefit."),
        Risk("Census ramp / immature centers", "High",
             "Fixed IDT and center cost over too few participants means new "
             "centers bleed cash for years before breakeven."),
        Risk("Regulatory sanction / enrollment freeze", "High",
             "CMS can halt new enrollment at a non-compliant organization "
             "(InnovAge, 2021) — a growth-stopping, existential event."),
        Risk("Actuarial / total-cost-of-care risk", "High",
             "Full risk on the frailest seniors with little reinsurance "
             "cushion; an under-managed population turns capitation into "
             "loss."),
        Risk("Nursing-home placement leakage", "Medium",
             "Every permanent placement is a cost the org bears; failure to "
             "keep participants safely in the community erodes margin."),
        Risk("State-approval / expansion dependence", "Medium",
             "Growth depends on slow state elections and slot allocations, so "
             "the pipeline is exogenous and lumpy."),
    ],
    diligence_questions=[
        "What is the census maturity by center, and where is each center on "
        "its ramp to breakeven?",
        "What is the Medicaid rate in each state, how was it negotiated, and "
        "what is the reset / trend outlook?",
        "What is hospital and SNF utilization versus benchmark, and what is "
        "the permanent nursing-home placement rate?",
        "What is the organization's CMS/state audit history and current "
        "compliance standing (any sanctions or corrective-action plans)?",
        "How accurate and defensible is Medicare risk coding, and what is the "
        "frailty-adjusted rate trajectory?",
        "What is the de-novo pipeline — approved slots, expected ramp curves, "
        "and the cash needed to fund it?",
        "What is the disenrollment / voluntary-disenrollment rate and its "
        "drivers?",
        "How concentrated is the enterprise by state and by center, and what "
        "is the reinsurance / stop-loss posture?",
    ],
    insider_lens=[
        "PACE is a health plan for the frailest 5% that happens to also be the "
        "provider. Read it like a full-risk MA plan, not like a clinic — the "
        "numbers that matter are utilization, medical management, and "
        "risk-adjusted revenue, not visit volume.",
        "The Medicaid rate is negotiated, not priced. It is pegged to what the "
        "state would have paid for a nursing-home bed, so the whole model lives "
        "or dies on an actuarial/political negotiation you must diligence "
        "state by state.",
        "Count mature census, not centers. A shiny new center is a multi-year "
        "cash drain; enterprise value sits in the filled, seasoned centers. A "
        "roll-up of immature centers is a roll-up of losses.",
        "Every nursing-home placement is a self-inflicted cost. The margin is "
        "literally the seniors you keep safely at home — clinical management is "
        "not overhead here, it is the product.",
        "Regulatory standing is existential. A CMS enrollment freeze (see "
        "InnovAge) does not dent growth — it stops it. Compliance is a first-"
        "order underwriting item, not a checklist.",
        "Under-penetration is real but not free. <1% of eligible duals are in "
        "PACE, but every incremental participant requires a slot, an approval, "
        "and a ramp — the runway is long and gated, not a switch you flip.",
    ],
    connections=default_connections(
        "pace",
        deals_sector="pace",
        extra_pages=[
            ("/diligence/tam-sam?template=pace",
             "Size it — PACE TAM/SAM build (dual-eligible × capitation chain)"),
        ],
        connectors=[
            ("cms_open_data_medicare_monthly_enrollment",
             "CMS Medicare monthly enrollment — the dual-eligible base"),
            ("medicaid_data_managed_care_by_state_2024",
             "Medicaid managed care by state — the LTSS payer landscape"),
            ("cms_open_data_ma_geo_variation",
             "CMS MA geographic variation — county benchmark rates (PACE-"
             "adjacent risk economics)"),
            ("provider_data_nursing_home_provider_info",
             "CMS Nursing Home Care Compare — the institutional alternative "
             "PACE diverts from"),
            ("census_acs_cbsa_profile",
             "Census ACS — senior (65+) density for service-area planning"),
        ],
    ),
    sources=[
        Source("CMS — Programs of All-Inclusive Care for the Elderly (PACE) "
               "program overview and rates", "GOV",
               "https://www.cms.gov/medicare-medicaid-coordination/pace"),
        Source("PACE Program Regulations, 42 CFR Part 460", "GOV",
               "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-E/part-460"),
        Source("National PACE Association — enrollment, program counts, and "
               "policy", "INDUSTRY", "https://www.npaonline.org/"),
        Source("MedPAC / MACPAC — dual-eligible and integrated-care policy "
               "analysis", "GOV", "https://www.macpac.gov/"),
        Source("Health Affairs / JAGS — research on PACE outcomes and "
               "nursing-home diversion", "ACADEMIC",
               "https://www.healthaffairs.org/"),
        Source("PE Desk industry deep-dive (deals-only) + realized-deal "
               "corpus for PACE", "INTERNAL",
               "/diligence/tam-sam?template=pace"),
    ],
    live_figures=live_figures_from_dive("pace"),
    trends=(
        "PACE spent its first three decades as a small, beloved, nonprofit "
        "model — On Lok's community program scaled to ~150-180 organizations "
        "and ~75-80K enrollees, but still under 1% of the nursing-home-eligible "
        "dual population. The last several years changed the capital structure: "
        "the permanent for-profit authority, the 2019 modernization rule, and a "
        "value-based-care investment wave brought scaled operators (InnovAge's "
        "IPO, WelbeHealth, ConcertoCare, CareConnectMD) and a build-and-fill "
        "growth agenda. The reality check came fast — InnovAge's 2021 CMS "
        "enrollment sanction reminded the sector that compliance and census "
        "maturity, not TAM, gate returns. The trajectory now is expansion under "
        "discipline: states adding PACE and slots, operators racing to fill "
        "centers to breakeven, and diligence centered on Medicaid rate "
        "adequacy, medical management, and regulatory standing. The demographic "
        "and fiscal logic — full-risk community care that diverts costly "
        "nursing-home days — is durable; the constraint is how fast approvals, "
        "capital, and census can actually ramp."),
    growth_levers=[
        GrowthLever(
            "State expansion (new states + slots)",
            "Growth is gated by states electing PACE and allocating slots; each "
            "expansion opens addressable service areas.",
            "primary gate", "ILLUSTRATIVE"),
        GrowthLever(
            "Census fill at existing centers",
            "The highest-return growth — a marginal enrollee on an already-"
            "fixed center/IDT/transportation base is nearly pure contribution.",
            "highest-return", "ILLUSTRATIVE"),
        GrowthLever(
            "For-profit + PE / venture capital entry",
            "Permanent for-profit authority plus value-based-care capital funds "
            "de-novo centers and scale the historically nonprofit field.",
            "capital-driven", "ILLUSTRATIVE"),
        GrowthLever(
            "Under-penetration of eligible duals",
            "With <1% of the millions of nursing-home-eligible duals enrolled, "
            "the structural runway is enormous — if approvals and ramp allow.",
            "long runway", "ILLUSTRATIVE"),
        GrowthLever(
            "Regulatory / compliance drag",
            "Enrollment sanctions and slow state approvals remove growth; "
            "compliance stumbles stop the engine cold.",
            "−growth risk", "GOV"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Nursing-home-eligible dual-eligible seniors × PACE penetration "
               "(expansion-gated)",
        analysis=(
            "The demand pool is the population that is simultaneously 55+, "
            "certified for nursing-home level of care, dual-eligible, and able "
            "to live safely in the community — millions of people, of whom "
            "under 1% are enrolled in PACE today. So unlike most post-acute "
            "sectors, PACE volume is not demand-constrained; it is expansion-"
            "constrained. The realizable growth is a product of three gated "
            "steps: a state electing PACE and allocating slots, an operator "
            "opening a center in a service area, and that center filling its "
            "census over a multi-year ramp. Demographics (the aging duals "
            "population) quietly enlarge the pool, but the binding variables "
            "are state policy and census ramp — which is why the sector grows "
            "in lumpy, approval-driven steps rather than smoothly with "
            "demand."),
        basis="GOV"),
    cost_drivers=[
        CostDriver(
            "Contracted medical & hospital care",
            "the largest managed cost",
            "Specialty, inpatient, and acute care purchased out of capitation "
            "— the line the IDT exists to manage down.", "ILLUSTRATIVE"),
        CostDriver(
            "PACE center + interdisciplinary team (IDT)",
            "the fixed cost base",
            "Physicians, nurses, therapists, social workers, aides, and the "
            "center itself — fixed, so census maturity decides whether it is "
            "affordable.", "ILLUSTRATIVE"),
        CostDriver(
            "Long-term care / nursing-home placement",
            "the tail-risk cost",
            "Permanent institutional placement is paid from capitation — every "
            "avoided placement is retained margin.", "ILLUSTRATIVE"),
        CostDriver(
            "Transportation",
            "a distinctive, material cost",
            "Getting frail participants to and from the center and appointments "
            "is a core capitated service and a real logistics expense.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Prescription drugs (Part D)",
            "meaningful for a polychronic population",
            "The frail, multi-morbid PACE population carries high pharmacy "
            "cost, folded into the capitation.", "ILLUSTRATIVE"),
    ],
    # Deals-only vertical: no provider_backed CMS roll, so cms_trend and a
    # computed state_breakdown are intentionally omitted — the renderer shows an
    # honest "unavailable offline" note and the qualitative sections carry the
    # weight.
)

register(REPORT)
