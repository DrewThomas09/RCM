"""Hospice — the Medicare hospice benefit.

Flagship + the recommended copy-template for the fan-out (per-diem payment,
aggregate cap, deals-heavy deep-dive). Consumes ``hospice_deep_dive()`` (CMS
Hospice General Information, ~6.9K providers) for SOURCED live figures. The
qualitative sections are authored around the aggregate cap, length-of-stay
economics, and the program-integrity crackdown that reset valuations.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, HowItWorks, Kpi, MarketReport, MarketSize,
    Regulatory, Reimbursement, Risk, Rule, Segment, Source, TamHeadline,
    UnitEconomics, default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="hospice",
    name="Hospice",
    care_setting="Post-acute",
    naics="621610",
    one_line_def=(
        "Interdisciplinary palliative care for terminally-ill patients "
        "(prognosis ≤6 months) who elect to forgo curative treatment — the "
        "Medicare hospice benefit, paid a per-diem by level of care and "
        "governed by an annual aggregate cap."),
    tam_headline=TamHeadline(
        value=25.0, unit="$B", growth_pct=5.0, basis_label="GOV",
        basis_note=(
            "Medicare hospice spend ~$25B (MedPAC); growth is the modeled "
            "composite of the TAM/SAM drivers (mortality +2.0%, penetration "
            "+1.5%, rate +2.5%, integrity −1.5%)."),
    ),
    executive_summary=[
        "Paid four per-diem rates, but the economics ARE routine home care "
        "(RHC ~97% of days). The provider is paid whether or not it visits "
        "that day, so the quiet middle of a long stay is high-margin.",
        "The aggregate cap is the single most important number. Each agency "
        "faces a per-beneficiary annual cap (~$34,465 in FY2025); long-stay, "
        "high-margin patients push it toward cap liability and repayment — a "
        "great P&L can hide a cap time bomb.",
        "For-profit is ~70%+ and rising — the most PE-penetrated post-acute "
        "vertical. That penetration drew OIG/CMS scrutiny, new-provider "
        "moratoria, and a Special Focus Program that reset the risk profile.",
        "Demand is the boomer mortality curve plus rising penetration of "
        "decedents; dementia and other non-cancer diagnoses lengthen stays — "
        "good for revenue, worse for cap and audit exposure.",
        "The economic shape is front- and back-loaded: admission and the last "
        "days of life are visit-heavy (costly); the long middle carries the "
        "margin — which is exactly what the integrity apparatus targets.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Terminal prognosis ≤6 months + hospice election (forgo curative)",
            "Certification of terminal illness (two physicians, initial)",
            "Interdisciplinary plan of care (MD, RN, aide, MSW, chaplain)",
            "Per-diem care at the appropriate level (RHC / CHC / GIP / IRC)",
            "Face-to-face recertification (NP/MD) at the third benefit period",
            "Service Intensity Add-on for RN/MSW visits in the last 7 days",
            "Bereavement services + cost report and cap reconciliation",
        ],
        sites_of_care=[
            "Patient home (routine home care — the bulk of days)",
            "Nursing facility (room-and-board is a pass-through; scrutiny)",
            "Assisted living residents",
            "Inpatient hospice unit / contracted hospital bed (GIP)",
        ],
        money_flow=(
            "Medicare pays a per-diem for each day a patient is enrolled, "
            "regardless of whether a visit occurred that day. Routine Home "
            "Care is two-tier — a higher rate for days 1-60 (~$218/day in "
            "FY2024) stepping down thereafter (~$172/day) — with a Service "
            "Intensity Add-on for skilled visits in the final week of life. "
            "General Inpatient, Continuous Home Care, and Inpatient Respite "
            "pay higher per-diems for their intensity. Because payment is per "
            "enrolled day and cost concentrates at admission and death, the "
            "long quiet middle of a stay is high-margin — until the aggregate "
            "cap claws back payment above the per-beneficiary limit."),
        key_players=(
            "A very long for-profit tail under a handful of scaled operators: "
            "VITAS (Chemed), Gentiva (the former Kindred at Home hospice, now "
            "Clayton, Dubilier & Rice), Optum/Enclara, AccentCare, Amedisys "
            "(with Contessa), Addus, and Agape Care. Nonprofit and "
            "hospital-affiliated programs hold the rest — but the acquirable "
            "pool is overwhelmingly the independent for-profit long tail."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Routine Home Care (RHC) days",
                    "~97% of days — the economics",
                    "GOV · MedPAC / CMS level-of-care mix"),
            Segment("General Inpatient (GIP) days",
                    "~1.5% of days — highest rate, heaviest audit",
                    "GOV · MedPAC / CMS level-of-care mix"),
            Segment("Continuous Home Care days", "~1% of days",
                    "GOV · CMS level-of-care mix"),
            Segment("Inpatient Respite days", "~0.5% of days",
                    "GOV · CMS level-of-care mix"),
            Segment("Annual Medicare hospice users", "~1.7M patients",
                    "GOV · MedPAC hospice chapter"),
        ],
        growth_drivers=[
            "Deaths / demographic growth ~2.0%/yr — the boomer mortality curve",
            "Penetration of Medicare decedents ~1.5%/yr — still rising",
            "Annual hospice payment update ~2.5%/yr",
            "Length-of-stay mix +1.0%/yr — dementia/non-cancer extends stays",
            "Program-integrity scrutiny −1.5%/yr — OIG/CMS + the CA glut",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Medicare": 0.88,
            "Medicaid": 0.07,
            "Commercial / MA / other": 0.05,
        },
        rate_mechanics=[
            "Four per-diems — Routine Home Care (two-tier by day), Continuous "
            "Home Care (hourly), General Inpatient, and Inpatient Respite.",
            "Service Intensity Add-on (SIA) — extra payment for RN and MSW "
            "visits in the last 7 days of life.",
            "Aggregate cap — a per-beneficiary annual limit (~$34,465 FY2025); "
            "payment above the cap is repaid to Medicare.",
            "Annual hospice payment update + wage index adjust the per-diems.",
            "Face-to-face recertification requirement gates continued payment "
            "at and beyond the third benefit period.",
            "The MA hospice carve-in (VBID demonstration) tested paying "
            "hospice through MA plans; the demo ended CY2024 and reverted to "
            "traditional Medicare.",
        ],
        reimbursement_risk=(
            "Two risks dominate. First, the aggregate cap: a census skewed "
            "toward long-stay, high-margin patients pushes an agency toward "
            "cap liability, and the repayment can erase a year's profit — the "
            "diligence must reconcile revenue to the cap CBSA by CBSA. Second, "
            "eligibility and level-of-care audits: UPIC/TPE reviews test "
            "whether long-stay patients were truly terminal and whether "
            "General Inpatient days were justified, with recoupment and "
            "extrapolation on the line. The Special Focus Program (2025) and "
            "state moratoria raise the stakes further."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("Medicare Hospice Conditions of Participation (42 CFR 418)",
                 "Certification, plan-of-care, and level-of-care rules that "
                 "gate participation and drive survey/audit exposure.",
                 "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-418"),
            Rule("Hospice aggregate cap (SSA §1814(i))",
                 "The per-beneficiary annual cap — the governing economic "
                 "constraint; over-cap payment is repaid.",
                 "https://www.cms.gov/medicare/payment/fee-for-service-providers/hospice"),
            Rule("Hospice Special Focus Program (2025)",
                 "Targets poor-performing providers for enhanced oversight — a "
                 "new, portfolio-relevant enforcement lever.",
                 "https://www.cms.gov/medicare/health-safety-standards/quality-safety-oversight-general-information/hospice-special-focus-program"),
            Rule("Program-integrity moratoria (new-provider enrollment)",
                 "CMS paused new hospice enrollments in glut markets (e.g. "
                 "California) — a direct check on the license-flip model.",
                 None),
            Rule("Hospice Quality Reporting Program (HQRP) + HOPE tool",
                 "The HOPE assessment replaces HIS in 2025; quality reporting "
                 "gates the full annual payment update.",
                 "https://www.cms.gov/medicare/quality/hospice"),
        ],
        policy_watch=[
            "Special Focus Program rollout and methodology challenges",
            "Continued OIG hospice vulnerability / deficiency reports",
            "Sun Belt license-glut crackdown (CA/AZ/NV/TX)",
            "Potential aggregate-cap or per-diem structural changes",
            "Any revival of an MA hospice carve-in after the VBID demo",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Several thousand providers with a for-profit majority that keeps "
            "rising, and an extreme independent long tail. The California "
            "new-license glut spawned a class of shell/flip agencies — the "
            "for-profit share our provider file measures below is both the M&A "
            "pool and the integrity-risk pool."),
        hhi_or_share=(
            "No dominant chain — extreme fragmentation. The for-profit share "
            "(the most PE-penetrated post-acute vertical) is measured directly "
            "from our provider file below."),
        consolidation=(
            "Heavily rolled up by PE and strategics: Chemed/VITAS, Gentiva "
            "under Clayton, Dubilier & Rice, Optum/Enclara, Addus, and "
            "Amedisys/Contessa. Multiples peaked in 2021 at double-digit "
            "EBITDA and then cooled as rate pressure and program-integrity "
            "risk repriced the sector."),
        pe_activity=(
            "One of the most PE-active post-acute verticals of the last "
            "decade. The 2021 peak has cooled: quality-of-earnings now centers "
            "on cap exposure and eligibility durability rather than pure census "
            "growth, and the CA glut plus the Special Focus Program made "
            "geography and license vintage first-order diligence items."),
        notable_players=[
            "VITAS Healthcare (Chemed)", "Gentiva (Clayton, Dubilier & Rice)",
            "Optum / Enclara", "AccentCare", "Amedisys (Contessa)",
            "Addus HomeCare", "Agape Care Group", "St. Croix Hospice",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Revenue / patient-day (blended)", "$180-220",
                "Weighted across levels of care; RHC two-tier structure drives "
                "the blend."),
            Kpi("Average length of stay (ALOS)", "70-95 days",
                "A long right tail (dementia) pulls the mean well above the "
                "~18-day median — the core margin and cap variable."),
            Kpi("Cap cushion (% headroom to aggregate cap)", "varies by CBSA",
                "How close the agency runs to cap liability — the number that "
                "can erase profit on repayment."),
            Kpi("Live-discharge rate", "10-20%",
                "High live-discharge signals eligibility/quality concerns and "
                "draws audit attention."),
            Kpi("RHC vs GIP mix", "GIP ~1-2% of days",
                "GIP is the highest rate and the heaviest audit target — mix "
                "matters for both margin and risk."),
            Kpi("Hospice EBITDA margin", "15-25%",
                "High in the quiet middle of stays; scale spreads the "
                "interdisciplinary team and on-call cost."),
        ],
        margin_profile=(
            "Hospice margin is a function of census × length of stay × cap "
            "headroom. Because payment is per enrolled day and cost "
            "concentrates at admission and death, a managed length-of-stay "
            "distribution — long enough to earn the high-margin middle, not so "
            "long that cap liability and audit risk bite — is the whole game. "
            "Scale spreads the interdisciplinary group, medical direction, and "
            "24/7 on-call across more census, but does not change the "
            "underlying cap arithmetic."),
    ),
    risks=[
        Risk("Aggregate-cap repayment", "High",
             "Long-stay, high-margin census pushes the agency over the "
             "per-beneficiary cap; repayment can erase a year's profit."),
        Risk("Eligibility / long-stay audit and recoupment", "High",
             "UPIC/TPE reviews test terminal-prognosis and GIP justification, "
             "with extrapolated recoupment on the line."),
        Risk("Special Focus Program + integrity crackdown", "High",
             "New oversight lever plus OIG scrutiny concentrated on for-profit "
             "long-stay and Sun Belt providers."),
        Risk("Sun Belt license-glut oversupply", "Medium",
             "The CA/AZ/NV/TX new-license flood created flip agencies and "
             "referral saturation in specific markets."),
        Risk("Labor (RN / aide) supply and wage inflation", "Medium",
             "Caps census growth and pressures the per-diem margin as rate "
             "updates lag wages."),
        Risk("Short-stay / late-referral admissions", "Medium",
             "Cancer and late referrals are visit-heavy and unprofitable — "
             "admission + death cost with little high-margin middle."),
    ],
    diligence_questions=[
        "What is the cap cushion by CBSA, and what is the trend — is any "
        "market approaching or over cap?",
        "What is the length-of-stay distribution, and how concentrated is the "
        "long-stay (dementia/non-cancer) tail?",
        "What is the diagnosis mix, and how has the non-cancer share moved?",
        "What is GIP utilization, and what is the audit/denial history on GIP "
        "days?",
        "What is the live-discharge rate, and how does it compare to peers?",
        "What share of census sits in nursing facilities (room-and-board plus "
        "referral/AKS scrutiny)?",
        "What is the Special Focus Program risk profile and the survey "
        "deficiency history?",
        "What is the UPIC/TPE/ADR history, and what reserves are held against "
        "potential recoupment?",
    ],
    insider_lens=[
        "The economics are the cap. A hospice with great margins may be "
        "sitting on a cap-repayment time bomb — long-stay dementia patients "
        "are high-margin until aggregate-cap liability claws it back. "
        "Reconcile revenue to the cap, CBSA by CBSA, before believing the P&L.",
        "Length of stay cuts both ways. Too short (late cancer referral) is "
        "unprofitable — admission and death cost with no middle. Too long "
        "(dementia) is high-margin but cap and audit risk. The asset is a "
        "managed LOS distribution, not a number.",
        "GIP is the rate you least want on audit: highest per-diem, heaviest "
        "documentation, favorite UPIC target. A GIP-rich mix flatters margin "
        "and raises risk simultaneously.",
        "The California license glut manufactured agencies that exist to bill "
        "and flip. The Special Focus Program and moratoria are the government "
        "catching up — target geography and license vintage are underwriting "
        "inputs, not footnotes.",
        "MedPAC keeps flagging hospice margins as high and floating cap and "
        "aggregate changes. The political economy points to tighter, not "
        "looser, across a typical hold — underwrite the regulatory drift.",
    ],
    connections=default_connections(
        "hospice",
        deals_sector="hospice",
        extra_pages=[
            ("/hospice", "Hospice vertical — CMS Care Compare + care index"),
        ],
        connectors=[
            ("provider_data_catalog",
             "CMS Provider Data Catalog — Hospice General Information"),
            ("cms_open_data_catalog",
             "CMS Open Data — hospice utilization & spending"),
            ("oig_leie",
             "OIG LEIE — excluded individuals/entities (integrity screen)"),
            ("census_acs_cbsa_profile",
             "Census ACS — senior (65+) density for demand mapping"),
        ],
    ),
    sources=[
        Source("MedPAC — Report to Congress, hospice services chapter", "GOV",
               "https://www.medpac.gov/"),
        Source("CMS Hospice Wage Index and Payment Rate Update — annual Final "
               "Rule (per-diems + aggregate cap)", "GOV",
               "https://www.cms.gov/medicare/payment/fee-for-service-providers/hospice"),
        Source("Medicare Hospice Conditions of Participation (42 CFR 418)",
               "GOV",
               "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-418"),
        Source("HHS Office of Inspector General — hospice program-integrity "
               "and vulnerability reports", "GOV",
               "https://oig.hhs.gov/reports-and-publications/all-reports-and-publications/"),
        Source("JAMA / Health Affairs — research on for-profit hospice "
               "ownership and length of stay", "ACADEMIC",
               "https://jamanetwork.com/"),
        Source("PE Desk industry deep-dive (CMS Hospice General Information) + "
               "realized-deal corpus", "INTERNAL",
               "/diligence/tam-sam?template=hospice"),
    ],
    live_figures=live_figures_from_dive("hospice"),
)

register(REPORT)
