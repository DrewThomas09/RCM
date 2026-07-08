"""Home Health — Medicare-certified skilled home health.

Rich-data flagship: consumes ``home_health_deep_dive()`` (CMS Home Health Care
Agencies, ~12.4K agencies) for SOURCED live figures. The qualitative sections
are authored around the PDGM payment rewrite, the MA rate story, and the
strategic-buyer crowding that reshaped the sector.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, HowItWorks, Kpi, MarketReport, MarketSize,
    Regulatory, Reimbursement, Risk, Rule, Segment, Source, TamHeadline,
    UnitEconomics, default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="home_health",
    name="Home Health",
    care_setting="Post-acute",
    naics="621610",
    one_line_def=(
        "Intermittent skilled nursing and therapy delivered in the patient's "
        "home under a physician-certified plan of care — Medicare-certified "
        "home health, paid in 30-day case-mix periods under PDGM."),
    tam_headline=TamHeadline(
        value=17.5, unit="$B", growth_pct=4.0, basis_label="GOV",
        basis_note=(
            "Medicare home health spend ~$16-18B (MedPAC); growth is the "
            "modeled composite of the TAM/SAM drivers (aging +3.0%, site-of-"
            "care shift +4.0%, PDGM/MA pressure offsets)."),
    ),
    executive_summary=[
        "PDGM (2020) rewrote the payment model: 30-day periods replaced 60-day "
        "episodes, therapy volume no longer pays, and rates now hinge on "
        "clinical grouping, admission source, timing, functional level, and "
        "comorbidity. Agencies that didn't retool their staffing got crushed.",
        "It's a referral business. Hospital-discharge (post-acute) is ~60% of "
        "volume; the discharge relationship and hospital JV/alignment are the "
        "moat, and referral concentration is a core diligence risk.",
        "Demographics and the site-of-care shift are the tailwind, but CMS "
        "behavioral-adjustment clawbacks and Medicare Advantage's below-FFS "
        "rates are the structural offsets — model the blended rate DOWN.",
        "MA is the quiet margin killer: as MA penetration rises past 50% of "
        "volume in many agencies, the blended rate falls even when FFS holds. "
        "A growing agency can be shrinking economically.",
        "Fragmented (~11-12K certified agencies) and PE-active — but the "
        "strategics (UnitedHealth/Optum, Humana/CenterWell) now outbid "
        "sponsors, valuing home health as a member-cost asset, not standalone "
        "EBITDA. PE's lane narrowed to sub-scale regional roll-ups.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Referral — hospital discharge (post-acute) or community/physician",
            "Physician face-to-face encounter + homebound/skilled eligibility",
            "OASIS assessment → clinical grouping and case-mix",
            "Plan of care + physician certification",
            "Skilled visits over 30-day periods (SN, PT, OT, ST, aide, MSW)",
            "Notice of Admission (NOA) filed to open the period",
            "PDGM period billing → recertification or discharge",
            "OASIS-based quality reporting + HHVBP scoring",
        ],
        sites_of_care=[
            "Patient home (the entire delivery model)",
            "Assisted living / senior housing residents",
            "Hospital-at-home partner (an emerging adjacency)",
        ],
        money_flow=(
            "Medicare pays a 30-day period rate — a national standardized "
            "amount around $2,000 — adjusted by the PDGM case-mix weight and "
            "the area wage index. The agency files a No-Pay Notice of Admission "
            "to open the period; periods with visits below the clinical-group "
            "LUPA threshold drop to low per-visit rates instead of the full "
            "period payment. The cost base is clinician labor and the number "
            "of visits delivered per period, so margin is the spread between "
            "the case-mix-driven period payment and the visits actually "
            "required to deliver care — with LUPA management and recert "
            "discipline deciding whether that spread is captured."),
        key_players=(
            "The top of the market consolidated into payers and strategics: "
            "UnitedHealth/Optum (LHC Group + Amedisys), Humana's CenterWell "
            "Home Health, and Enhabit (spun from Encompass). Below them sit "
            "large nonprofits and independents — BAYADA, VNS Health, Interim "
            "HealthCare franchises — and a very long tail of proprietary "
            "agencies that is where platform tuck-in M&A actually happens."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Post-acute (hospital-discharge) episodes",
                    "~62% of volume",
                    "ILLUSTRATIVE · TAM/SAM segment mix (MedPAC-anchored)"),
            Segment("Community-admitted episodes",
                    "~38% of volume",
                    "ILLUSTRATIVE · TAM/SAM segment mix"),
            Segment("Annual Medicare HH users",
                    "~3.3M beneficiaries",
                    "GOV · MedPAC home health chapter"),
            Segment("30-day periods per user / year",
                    "~2.9",
                    "GOV · MedPAC PDGM utilization"),
        ],
        growth_drivers=[
            "Aging population (65+ growth) ~3.0%/yr — the demand floor",
            "Site-of-care shift to home ~4.0%/yr — payers/patients prefer home",
            "PDGM behavioral-adjustment clawbacks −1.5%/yr — a rate headwind",
            "Clinical labor supply constraint −1.0%/yr caps realized volume",
            "MA penetration −0.5%/yr drag on the blended rate",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Medicare FFS": 0.38,
            "Medicare Advantage": 0.40,
            "Medicaid (waiver)": 0.13,
            "Commercial / other": 0.09,
        },
        rate_mechanics=[
            "PDGM 30-day period — case-mix from admission source (community vs "
            "institutional) × timing (early/late) × 12 clinical groups × "
            "functional level × comorbidity adjustment.",
            "LUPA — periods below a clinical-group visit threshold pay low "
            "per-visit rates instead of the full period; LUPA management is a "
            "margin and compliance tightrope.",
            "Behavioral adjustment — CMS asserts PDGM overpaid and recoups via "
            "permanent + temporary rate cuts every rule cycle.",
            "Notice of Admission (NOA) — replaced the RAP in 2022; late filing "
            "forfeits payment for the delay period.",
            "HHVBP — Home Health Value-Based Purchasing is now nationwide, "
            "putting up to ±5% of payment at risk on quality.",
            "MA negotiated rates — per-visit or per-episode, typically 80-90% "
            "of FFS; the mix shift compresses the blended rate.",
        ],
        reimbursement_risk=(
            "The rate is structurally under pressure from two directions. CMS's "
            "permanent and temporary behavioral adjustments claw back what it "
            "calls PDGM overpayment, cutting FFS rates every cycle. "
            "Simultaneously, Medicare Advantage — now the majority of volume "
            "at many agencies — pays 80-90% of FFS and adds prior-auth and "
            "any-willing-provider friction, so the blended rate falls even "
            "when the FFS rate holds. On top of that, HHVBP puts 5% at risk on "
            "quality and the Review Choice Demonstration adds pre-claim review "
            "burden in fraud-hotspot states."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("Home Health PPS / PDGM (annual Final Rule)",
                 "Defines the 30-day period, case-mix, LUPA thresholds, and "
                 "the behavioral-adjustment clawback — the sector's price.",
                 "https://www.cms.gov/medicare/payment/prospective-payment-systems/home-health-pps"),
            Rule("Conditions of Participation (42 CFR 484)",
                 "Certification, plan-of-care, and OASIS requirements that "
                 "gate Medicare participation and drive survey risk.",
                 "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-484"),
            Rule("Home Health Value-Based Purchasing (HHVBP)",
                 "Now nationwide; ±5% payment adjustment on quality cohort "
                 "performance — a real EBITDA swing.",
                 "https://www.cms.gov/priorities/innovation/innovation-models/expanded-home-health-value-based-purchasing-model"),
            Rule("Review Choice Demonstration (RCD)",
                 "Pre-claim review in select states (fraud control) — a heavy "
                 "administrative burden and a target-geography risk.",
                 "https://www.cms.gov/data-research/monitoring-programs/medicare-fee-service-compliance-programs/review-choice-demonstration"),
            Rule("Face-to-face encounter requirement",
                 "The physician encounter and documentation that support "
                 "eligibility — a common audit-denial pressure point.",
                 None),
        ],
        policy_watch=[
            "Magnitude of the annual behavioral-adjustment clawback",
            "MA prior-authorization and any-willing-provider rulemaking",
            "Review Choice Demonstration expansion to new states",
            "Hospital-at-home waiver permanence (a home-based adjacency)",
            "OASIS-E and quality-measure changes feeding HHVBP",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "About 11-12K Medicare-certified agencies, the majority for-profit "
            "and sub-scale. Historically low barriers to entry (outside "
            "fraud-moratorium markets) produced a deeply fragmented long tail — "
            "the proprietary agencies are the M&A pool, and our facility file "
            "measures how large that pool is state by state."),
        hhi_or_share=(
            "No national duopoly. The proprietary (for-profit) share — the "
            "platform-tuck-in pool — is measured directly from our agency file "
            "below."),
        consolidation=(
            "The top consolidated into payers and strategics: UnitedHealth "
            "absorbed LHC Group and Amedisys; Humana's CenterWell verticalized "
            "home health into a member-cost engine; Enhabit and BAYADA scaled "
            "independently. Below them, PE and regional platforms still roll up "
            "the proprietary tail — but the marquee assets now trade to "
            "payers, not sponsors."),
        pe_activity=(
            "Intense at the regional level, but the thesis changed: strategics "
            "value home health as a member-retention and total-cost-of-care "
            "asset and will pay above standalone-EBITDA multiples, crowding PE "
            "into sub-scale roll-ups below their radar. Quality-of-earnings now "
            "centers on the MA mix trajectory and the durability of referral "
            "relationships."),
        notable_players=[
            "UnitedHealth / Optum (LHC Group + Amedisys)",
            "CenterWell Home Health (Humana)", "Enhabit", "BAYADA",
            "VNS Health", "Aveanna Healthcare", "Interim HealthCare",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Revenue / 30-day period (FFS)", "~$2,000",
                "The national standardized amount before case-mix and wage "
                "index; MA periods pay meaningfully less."),
            Kpi("LUPA rate (% of periods)", "8-12%",
                "Periods below the visit threshold drop to per-visit pay — the "
                "margin leak agencies manage against."),
            Kpi("Visits / 30-day period", "8-14",
                "The cost driver; the spread vs the period payment is the "
                "margin."),
            Kpi("Clinician productivity", "5-6 visits / day",
                "Nurse and therapist utilization; the labor constraint on "
                "volume and margin."),
            Kpi("MA share of volume", "40-60% and rising",
                "The single biggest driver of the blended-rate trajectory."),
            Kpi("Agency EBITDA margin", "8-15%",
                "Labor-dominated; scale helps back-office and payer "
                "contracting."),
        ],
        margin_profile=(
            "Home health is a labor business — clinician wages and the number "
            "of visits per period dominate the cost base. Margin is made by "
            "matching visit intensity to the case-mix-driven period payment, "
            "avoiding LUPA leakage, and negotiating MA rates that don't gut "
            "the blend. Scale earns its keep in back-office leverage, payer "
            "contracting, and HHVBP performance rather than in clinical unit "
            "cost, which is largely market-wage-bound."),
    ),
    risks=[
        Risk("PDGM behavioral-adjustment clawbacks", "High",
             "CMS recoups asserted overpayment via permanent + temporary rate "
             "cuts every rule cycle — a persistent FFS-rate headwind."),
        Risk("Medicare Advantage mix and rate erosion", "High",
             "MA pays 80-90% of FFS and keeps taking share; the blended rate "
             "falls structurally as penetration rises."),
        Risk("Clinician labor shortage and turnover", "High",
             "Nurse/therapist scarcity caps volume and inflates cost per "
             "visit; turnover disrupts referral service levels."),
        Risk("Referral concentration on one or two hospital systems", "Medium",
             "The moat is also the single point of failure if a system "
             "in-sources or switches partners."),
        Risk("Strategic buyers crowding out the PE thesis", "Medium",
             "Payers value home health differently and outbid sponsors for the "
             "scaled assets."),
        Risk("Review Choice Demonstration / audit burden", "Medium",
             "Pre-claim review and face-to-face documentation drive denials "
             "and administrative cost in target geographies."),
    ],
    diligence_questions=[
        "What is the MA-vs-FFS mix by market, and what is its trajectory over "
        "the last three years?",
        "What is the LUPA rate, and how is it managed operationally?",
        "What is the recertification rate and the visits-per-period trend "
        "since PDGM?",
        "How concentrated are referrals — what share comes from the top one "
        "or two hospital systems, and are they contractual?",
        "Which states expose the agency to the Review Choice Demonstration, "
        "and what is the pre-claim approval rate?",
        "What is clinician turnover, and how does open-position coverage "
        "affect the ability to accept referrals?",
        "How accurate is OASIS coding (upcoding exposure), and what is the "
        "NOA timely-filing performance?",
        "What is the HHVBP cohort performance and the resulting payment "
        "adjustment?",
    ],
    insider_lens=[
        "Therapy no longer pays. Pre-PDGM the game was therapy-visit volume; "
        "PDGM killed that overnight and rewarded clinical grouping and "
        "admission source. Confirm the target actually re-engineered staffing "
        "— many didn't.",
        "The clawback is structural, not a one-off. CMS treats PDGM as an "
        "overpayment it is entitled to recoup, cycle after cycle. Underwrite "
        "the rate flat-to-down, never up.",
        "MA is the silent shrinker. Volume and revenue can rise while economic "
        "profit falls as MA displaces FFS at 80-90% of the rate — read the "
        "mix, not the top line.",
        "You will lose the scaled assets to the strategics. UnitedHealth and "
        "Humana buy home health to lower member medical cost, so they clear "
        "at multiples PE can't. The edge is regional roll-up below their "
        "screen.",
        "LUPA and recert discipline is where the money is actually made — it's "
        "an operations story, not a growth story, and it doesn't show up in a "
        "revenue chart.",
    ],
    connections=default_connections(
        "home_health",
        deals_sector="home_health",
        extra_pages=[
            ("/home-health",
             "Home Health vertical — CMS Care Compare + star ratings"),
        ],
        connectors=[
            ("provider_data_catalog",
             "CMS Provider Data Catalog — Home Health Care Agencies"),
            ("cms_open_data_catalog",
             "CMS Open Data — home health utilization & spending"),
            ("census_acs_cbsa_profile",
             "Census ACS — senior (65+) density for demand mapping"),
            ("npi_provider", "NPI Registry — home health agencies & clinicians"),
        ],
    ),
    sources=[
        Source("MedPAC — Report to Congress, home health care services "
               "chapter", "GOV", "https://www.medpac.gov/"),
        Source("CMS Home Health Prospective Payment System / PDGM — annual "
               "Final Rule", "GOV",
               "https://www.cms.gov/medicare/payment/prospective-payment-systems/home-health-pps"),
        Source("Conditions of Participation for Home Health Agencies "
               "(42 CFR 484)", "GOV",
               "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-484"),
        Source("Expanded Home Health Value-Based Purchasing Model — CMS "
               "Innovation Center", "GOV",
               "https://www.cms.gov/priorities/innovation/innovation-models/expanded-home-health-value-based-purchasing-model"),
        Source("Health Affairs — analyses of PDGM's effect on home health "
               "utilization and access", "ACADEMIC",
               "https://www.healthaffairs.org/"),
        Source("PE Desk industry deep-dive (CMS Home Health Care Agencies) + "
               "realized-deal corpus", "INTERNAL",
               "/diligence/tam-sam?template=home_health"),
    ],
    live_figures=live_figures_from_dive("home_health"),
)

register(REPORT)
