"""Transplant Services — the organ-transplant ecosystem, where the organ is the
scarce asset and the investable money lives around the centers.

Deals-only deep-dive (UNOS/OPTN center lists are public but not vendored, so
geography is omitted rather than fabricated; consumes ``transplant_services_
deep_dive()`` for SOURCED corpus figures — empty offline, so the authored,
basis-labeled OPTN/SRTR segments carry the sizing). Solid-organ transplantation
is hospital- and academic-medical-center dominated and outcome-regulated, so the
centers themselves are NOT a fragmented PE roll-up. The qualitative sections are
authored around the unique organ-acquisition-cost pass-through reimbursement
mechanic, the outcome-based Conditions of Participation that can de-certify a
program, the 2023 OPTN break-up (Securing the U.S. OPTN Act), the organ-supply
ceiling as the binding demand constraint, and the real investable surface — the
ecosystem of organ-preservation/perfusion technology, immunosuppressant specialty
pharmacy, and transplant centers-of-excellence network services.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="transplant_services",
    name="Transplant Services",
    care_setting="Physician services",
    naics="622110",
    one_line_def=(
        "Solid-organ transplantation (kidney, liver, heart, lung, pancreas) and "
        "its ecosystem — the ~250 OPTN-credentialed transplant centers, the "
        "federally-designated organ procurement organizations that recover "
        "organs, and the for-profit layer around them (organ-preservation/"
        "perfusion technology, immunosuppressant specialty pharmacy, and "
        "centers-of-excellence network services)."),
    tam_headline=TamHeadline(
        value=40.0, unit="$B", growth_pct=5.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "Modeled from OPTN transplant volumes (~46,000 transplants/yr) times "
            "per-transplant episode cost (Milliman U.S. organ/tissue transplant "
            "cost estimates — e.g. ~$400K kidney to ~$1.7M heart, billed "
            "charges), not a single published market figure. Growth reflects "
            "record transplant volumes plus machine-perfusion/DCD expansion of "
            "the usable organ pool; the investable services layer is a fraction "
            "of the gross episode figure."),
    ),
    executive_summary=[
        "The organ — not the patient — is the scarce asset. Demand is "
        "structurally supply-constrained: roughly 100,000+ people sit on the "
        "national waiting list while ~46,000 transplants are performed a year, so "
        "the binding variable is donor-organ availability, not patient demand.",
        "The centers are not a PE roll-up. Transplantation is concentrated in "
        "~250 OPTN-credentialed hospitals, dominated by academic medical centers "
        "and large systems, and gated by outcome-based Conditions of "
        "Participation — so the investable surface is the ecosystem AROUND the "
        "centers, not the centers themselves.",
        "Reimbursement has a mechanic found almost nowhere else: organ "
        "acquisition cost. The cost of procuring the organ (OPO fees, donor "
        "workup, recovery, tissue typing, transport) is accumulated in a separate "
        "acquisition cost center and reimbursed by Medicare on a reasonable-cost "
        "pass-through basis, distinct from the transplant DRG.",
        "The real money is downstream and adjacent. Lifelong immunosuppressant "
        "specialty pharmacy (recurring, high-dollar anti-rejection therapy), "
        "organ-preservation/perfusion technology (normothermic machine "
        "perfusion — TransMedics-style 'organ-in-a-box'), and commercial "
        "centers-of-excellence networks are where for-profit returns concentrate.",
        "Governance is being rebuilt in real time. The 2023 Securing the U.S. "
        "OPTN Act broke up the decades-long UNOS monopoly and had HRSA re-compete "
        "and modernize the national transplant network — a live structural reset "
        "of the system's plumbing.",
        "Machine perfusion and DCD are expanding the pie. Normothermic and "
        "hypothermic machine perfusion and donation-after-circulatory-death "
        "recovery are increasing the number of usable organs — the one lever that "
        "actually loosens the supply ceiling, and the center of current "
        "investment and innovation.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Referral + transplant evaluation — candidacy workup and listing on "
            "the OPTN waiting list at a credentialed center",
            "Waitlist management — the candidate accrues time/priority under the "
            "OPTN allocation policy for the organ",
            "Donor identification + OPO recovery — an organ procurement "
            "organization recovers the deceased-donor organ (or a living donor "
            "is worked up)",
            "Organ allocation + acceptance — the OPTN match run offers the organ; "
            "the center accepts and mobilizes",
            "Preservation + transport — cold storage or machine perfusion "
            "(normothermic/hypothermic) keeps the organ viable in transit",
            "Transplant surgery + peri-operative care — the high-cost inpatient "
            "episode (transplant MS-DRG plus acquisition cost)",
            "Lifelong post-transplant care + immunosuppression — anti-rejection "
            "specialty pharmacy, monitoring, and rejection management",
        ],
        sites_of_care=[
            "OPTN-credentialed transplant center (hospital / academic medical "
            "center — the surgical and listing core)",
            "Organ procurement organization (federally-designated regional "
            "nonprofit that recovers deceased-donor organs)",
            "Histocompatibility / tissue-typing laboratory (crossmatch and HLA)",
            "Living-donor evaluation and surgery program",
            "Transplant / specialty pharmacy (lifelong immunosuppressant therapy)",
            "Post-transplant ambulatory clinic + referring nephrology/hepatology",
        ],
        money_flow=(
            "Transplant is paid unlike almost any other service line. The "
            "transplant admission itself bills a Medicare MS-DRG (or a commercial "
            "case rate), but the cost of obtaining the organ is handled "
            "separately: the center accumulates OPO acquisition fees, donor "
            "evaluation, surgical recovery, tissue typing, and transport in a "
            "dedicated organ-acquisition cost center that Medicare reimburses on "
            "a reasonable-cost pass-through basis, and bills payers a Standard "
            "Acquisition Charge for it. Commercial payers contract very high "
            "per-case rates through centers-of-excellence networks (a solid-organ "
            "case can run from several hundred thousand to well over a million "
            "dollars all-in) and steer members to designated centers with travel "
            "benefits. Because the National Organ Transplant Act bars buying or "
            "selling organs, the donor organ has no purchase price — only the "
            "regulated cost of recovering it. The lucrative, recurring economics "
            "sit downstream in lifelong immunosuppressant specialty pharmacy and "
            "in the technology (machine perfusion) that expands the usable organ "
            "pool — which is why for-profit capital concentrates around the "
            "centers rather than in them."),
        key_players=(
            "The system runs through the OPTN (the federal Organ Procurement and "
            "Transplantation Network, historically operated by UNOS and being "
            "re-competed after the 2023 OPTN Act) and ~55 federally-designated "
            "organ procurement organizations that recover organs regionally. The "
            "centers are academic and large-system hospitals. The for-profit "
            "ecosystem is where investment lives: organ-preservation/perfusion "
            "technology (TransMedics' Organ Care System, Paragonix, XVIVO and "
            "normothermic-regional-perfusion providers), immunosuppressant and "
            "transplant specialty pharmacies, commercial centers-of-excellence "
            "network managers (Optum/Interlink-style transplant networks), and "
            "histocompatibility labs. SRTR (the Scientific Registry of Transplant "
            "Recipients) publishes the outcome data that regulates the centers."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Transplants performed per year (all organs)", "~46,000",
                    "GOV · OPTN/UNOS national data (record year)"),
            Segment("National transplant waiting list", "~100,000+ candidates",
                    "GOV · OPTN/UNOS waiting-list data"),
            Segment("Kidney transplants (largest organ segment)", "~27,000/yr",
                    "GOV · OPTN/UNOS by-organ volumes"),
            Segment("OPTN-credentialed transplant centers", "~250 centers",
                    "GOV · OPTN member transplant hospitals"),
            Segment("Federally-designated OPOs", "~55 organizations",
                    "GOV · HRSA/CMS OPO designations"),
        ],
        growth_drivers=[
            "Record transplant volumes — supply-side gains, not demand shortage",
            "Machine perfusion + DCD expanding the usable organ pool",
            "Rising need — ESRD, NASH/MASH cirrhosis, and heart-failure "
            "prevalence",
            "Immunosuppressant specialty-pharmacy recurring revenue growth",
            "OPO performance reform lifting deceased-donor recovery",
            "Long-run: xenotransplantation as a potential supply unlock "
            "(early-stage)",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Medicare / MA": 0.55,
            "Commercial (COE case rates)": 0.30,
            "Medicaid": 0.12,
            "Other / self-pay": 0.03,
        },
        rate_mechanics=[
            "Organ acquisition cost pass-through — OPO fees, donor evaluation, "
            "recovery, tissue typing, and transport accumulate in a dedicated "
            "acquisition cost center reimbursed by Medicare on a reasonable-cost "
            "basis, separate from the transplant DRG (the sector's signature "
            "mechanic).",
            "Transplant MS-DRG / inpatient PPS — the transplant admission bills "
            "an inpatient DRG; kidney transplant is a distinct Medicare benefit "
            "(ESRD patients qualify for Medicare).",
            "Standard Acquisition Charge (SAC) — the center's billed charge to "
            "payers for the accumulated organ-acquisition cost.",
            "Commercial centers-of-excellence case rates — very high per-case "
            "rates negotiated through COE networks that steer members to "
            "designated centers, often with travel/lodging benefits.",
            "Immunosuppressant drug coverage — lifelong anti-rejection therapy "
            "billed through pharmacy benefit / specialty pharmacy (Medicare Part "
            "B/D coverage of transplant immunosuppressants was made lifelong "
            "under recent law).",
            "National Organ Transplant Act (NOTA) constraint — organs cannot be "
            "bought or sold, so only the regulated cost of recovery is "
            "reimbursed; there is no organ 'price'.",
        ],
        reimbursement_risk=(
            "Transplant reimbursement risk is regulatory and structural rather "
            "than rate-cyclical. The organ-acquisition cost pass-through is "
            "audit-intensive: CMS scrutinizes how acquisition cost centers are "
            "populated, and the 2021 CMS clarification of acquisition-cost "
            "accounting reset how centers must document it, so mis-costed "
            "acquisition is a real recoupment exposure. On the commercial side, "
            "centers-of-excellence case rates concentrate high-dollar episodes "
            "with a handful of payers whose network and travel-steerage decisions "
            "can move a program's volume. The outcome-based Conditions of "
            "Participation add a payment-gating risk found almost nowhere else — "
            "a program with poor risk-adjusted graft/patient survival can lose "
            "Medicare approval outright. And the whole system's plumbing is being "
            "rebuilt under the 2023 OPTN Act, so allocation policy and OPO "
            "performance rules are in active flux."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("National Organ Transplant Act (NOTA, 1984)",
                 "The foundational law: bars buying/selling organs and "
                 "established the OPTN — the reason there is no organ price, only "
                 "regulated recovery cost.",
                 "https://www.congress.gov/bill/98th-congress/senate-bill/2048"),
            Rule("Securing the U.S. OPTN Act (2023) + OPTN modernization",
                 "Broke up the decades-long single-contractor (UNOS) model and "
                 "had HRSA re-compete and modernize the national transplant "
                 "network — a live structural reset of allocation governance.",
                 "https://www.congress.gov/bill/118th-congress/house-bill/2544"),
            Rule("CMS transplant-program Conditions of Participation (42 CFR 482 "
                 "Subpart E)",
                 "Outcome-based: a program with poor risk-adjusted graft/patient "
                 "survival can lose Medicare approval — a payment-gating quality "
                 "regime with existential stakes.",
                 "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-G/part-482"),
            Rule("CMS OPO Conditions for Coverage + 2020 outcome-metric final "
                 "rule",
                 "Re-based OPO performance on objective donation/transplantation "
                 "rate metrics with de-certification risk — reshaping the organ-"
                 "recovery layer that feeds the centers.",
                 "https://www.cms.gov/medicare/health-safety-standards/quality-safety-oversight-general-information/organ-procurement-organizations"),
            Rule("Organ-acquisition cost reporting (CMS 2021 final rule)",
                 "Clarified how transplant centers accumulate and report organ-"
                 "acquisition costs in the cost report — the basis of the "
                 "pass-through and an audit focus.",
                 "https://www.cms.gov/medicare/payment/prospective-payment-systems/acute-inpatient-pps"),
            Rule("OPTN allocation policy (organ-specific)",
                 "The continuous-distribution and organ-specific allocation "
                 "policies determine which candidate gets an available organ — "
                 "the rulebook that governs waitlist priority and center volume.",
                 "https://optn.transplant.hrsa.gov/policies-bylaws/policies/"),
        ],
        policy_watch=[
            "OPTN re-competition and modernization rollout after the 2023 Act",
            "Continuous-distribution allocation policy changes by organ",
            "OPO performance-metric enforcement and de-certification actions",
            "Machine-perfusion / DCD coverage and coding evolution",
            "Xenotransplantation clinical-trial and regulatory pathway (FDA)",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "This is the opposite of a fragmented roll-up: transplantation is "
            "concentrated in roughly 250 OPTN-credentialed hospitals, dominated "
            "by academic medical centers and large health systems, and gated by "
            "outcome-based Conditions of Participation that make a new program "
            "expensive and slow to stand up. The 'acquirable' market is therefore "
            "not the centers but the surrounding ecosystem — perfusion technology, "
            "immunosuppressant specialty pharmacy, histocompatibility labs, and "
            "centers-of-excellence network services."),
        hhi_or_share=(
            "Center concentration is high and academic — a handful of large "
            "programs perform a disproportionate share of volume by organ — but "
            "this is a regulated hospital service line, not a chain market, so a "
            "PE chain HHI does not apply. UNOS/OPTN center lists are public but "
            "not vendored, so a computed geography/HHI is honestly omitted; the "
            "OPTN/SRTR figures and the corpus deal history are the read."),
        consolidation=(
            "Consolidation happens at the ecosystem layer, not the centers. "
            "Organ-preservation/perfusion technology has scaled (TransMedics went "
            "public and built a national organ-logistics network; Paragonix and "
            "XVIVO compete), transplant/immunosuppressant specialty pharmacy has "
            "been rolled into the large specialty-pharmacy platforms, and "
            "commercial centers-of-excellence transplant networks are managed by "
            "a few payers/network firms. The centers themselves consolidate only "
            "as their parent health systems merge."),
        pe_activity=(
            "Direct PE ownership of transplant centers is rare — they are "
            "hospital/academic assets under outcome-based CoP. Sponsor and "
            "growth capital concentrates in the adjacencies: perfusion/organ-"
            "preservation technology and organ logistics, transplant specialty "
            "pharmacy (durable, recurring immunosuppressant revenue), "
            "histocompatibility labs, living-donor and transplant management "
            "services, and centers-of-excellence network administration. "
            "Diligence turns on regulatory posture (OPTN/CoP/OPO reform), the "
            "durability of the organ-supply tailwind, and reimbursement "
            "complexity rather than practice-count roll-up math."),
        notable_players=[
            "OPTN (federal network; UNOS historically operated it)",
            "SRTR (Scientific Registry of Transplant Recipients — outcome data)",
            "TransMedics (Organ Care System / organ logistics)", "Paragonix",
            "XVIVO Perfusion", "Academic medical-center transplant programs",
            "Organ procurement organizations (~55, federally designated)",
            "Transplant / immunosuppressant specialty pharmacies",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Transplant volume by organ (center)", "program-dependent",
                "Volume is capped by organ availability and center capacity — "
                "the scarce input is the organ, not the patient demand."),
            Kpi("Risk-adjusted 1-yr graft / patient survival", "SRTR-benchmarked",
                "The outcome metric that gates Medicare approval under the CoP — "
                "a quality number with existential regulatory stakes."),
            Kpi("Organ-acquisition cost per transplant", "cost-report-driven",
                "Accumulated in the acquisition cost center and pass-through "
                "reimbursed; mis-costing is an audit/recoupment exposure."),
            Kpi("Commercial COE case rate", "high six / seven figures",
                "Very high per-case commercial rates negotiated through centers-"
                "of-excellence networks — the high-dollar episode economics."),
            Kpi("Immunosuppressant specialty-pharmacy revenue / patient-yr",
                "recurring, durable",
                "Lifelong anti-rejection therapy — the recurring, high-margin "
                "downstream annuity that outlasts the surgical episode."),
            Kpi("Organ discard / non-use rate", "the supply-loss metric",
                "Recovered organs that go untransplanted; machine perfusion and "
                "logistics aim to cut discards and expand usable supply."),
        ],
        margin_profile=(
            "Economics split sharply by layer. For a hospital, transplant is a "
            "high-cost, high-reimbursement, low-volume, outcome-regulated "
            "prestige service line: the surgical episode is expensive, the organ-"
            "acquisition cost is pass-through rather than margin, and the program "
            "is often run for its halo, referral pull, and downstream care rather "
            "than a fat operating margin — with commercial COE case rates "
            "carrying the profitable episodes. The recurring, higher-margin money "
            "is downstream and adjacent: lifelong immunosuppressant specialty "
            "pharmacy is a durable annuity per surviving recipient, and organ-"
            "preservation/perfusion technology and logistics earn strong, "
            "scalable margins as they expand the usable organ pool. So a "
            "'transplant services' investment thesis is really an ecosystem "
            "thesis — the center is the regulated hub; the returns sit in the "
            "recurring and technology-enabled layers around it."),
    ),
    risks=[
        Risk("Organ-supply ceiling (structural demand > supply)", "High",
             "Volume is capped by donor-organ availability, not patient demand — "
             "growth depends on expanding usable supply (perfusion/DCD), a "
             "supply-side, not demand-side, story."),
        Risk("Outcome-based CoP de-approval risk", "High",
             "A program with poor risk-adjusted survival can lose Medicare "
             "approval outright — a payment-gating quality regime with "
             "existential stakes for a center."),
        Risk("OPTN / regulatory upheaval (2023 OPTN Act)", "Medium",
             "The break-up of the UNOS monopoly and OPTN modernization put "
             "allocation governance and system plumbing in active flux."),
        Risk("Reimbursement complexity + acquisition-cost audit", "Medium",
             "The organ-acquisition cost pass-through is audit-intensive; "
             "mis-costing is a recoupment exposure unique to this sector."),
        Risk("Center concentration / academic dominance", "Medium",
             "Transplantation is concentrated in academic hospitals under CoP — "
             "the centers are hard to acquire, so the investable surface is the "
             "ecosystem, not the programs."),
        Risk("Long-run technology disruption uncertainty", "Low",
             "Xenotransplantation and bioengineered organs could reshape supply, "
             "but the clinical/regulatory timeline is long and uncertain."),
    ],
    diligence_questions=[
        "For an ecosystem target, what is the exposure to OPTN/OPO reform and "
        "allocation-policy change — how does the 2023 OPTN Act reshape the "
        "customer base or the recovery layer?",
        "How durable is the organ-supply tailwind for this asset — is it levered "
        "to machine perfusion / DCD expansion or to raw center volume?",
        "For a transplant specialty pharmacy, what is the recurring "
        "immunosuppressant revenue per surviving recipient, churn/mortality, and "
        "payer-mix durability?",
        "For a perfusion/preservation technology, what is the clinical evidence, "
        "coding/coverage status, and the discard-rate reduction it delivers?",
        "For any center-linked service, what is the risk-adjusted graft/patient "
        "survival (SRTR) posture and the Conditions-of-Participation standing of "
        "the partner programs?",
        "How is organ-acquisition cost documented, and what is the audit/"
        "recoupment history on the acquisition cost center and Standard "
        "Acquisition Charge?",
        "What is the commercial centers-of-excellence contracting exposure, and "
        "how concentrated is high-dollar case volume with a few payers/networks?",
        "How exposed is the thesis to NOTA constraints and to the long-run "
        "xenotransplantation / bioengineering pathway?",
    ],
    insider_lens=[
        "The organ is the scarce asset, not the patient. Every other healthcare "
        "vertical grows by winning more demand; transplant is capped by donor-"
        "organ supply. So the only durable growth lever is expanding usable "
        "organs — machine perfusion, DCD recovery, OPO performance — which is "
        "exactly where the innovation and the investment are.",
        "Acquisition cost is the mechanic outsiders miss. The organ's recovery "
        "cost is not in the DRG — it accumulates in a separate acquisition cost "
        "center reimbursed on a cost pass-through, billed as a Standard "
        "Acquisition Charge. Model transplant economics without understanding "
        "acquisition cost and you will misread the entire P&L.",
        "Don't try to buy the center — buy what the center depends on. Programs "
        "are academic hospital assets under outcome-based CoP and are effectively "
        "un-rollable. The returns live in the ecosystem: immunosuppressant "
        "specialty pharmacy (a lifelong annuity), perfusion/logistics technology, "
        "and centers-of-excellence networks.",
        "Outcomes are a payment gate with a death penalty. A program with poor "
        "risk-adjusted survival can lose Medicare approval under the Conditions "
        "of Participation — SRTR outcome data is not a quality nicety, it is the "
        "license to operate, so any center-linked thesis lives or dies on it.",
        "The system's plumbing is being rebuilt. The 2023 OPTN Act ended the UNOS "
        "monopoly and set HRSA to re-compete and modernize the network — "
        "allocation policy, technology vendors, and OPO performance rules are all "
        "in motion, which is risk and opportunity for ecosystem vendors.",
        "Immunosuppression is the annuity. A transplanted patient needs anti-"
        "rejection therapy for the life of the graft, and coverage of transplant "
        "immunosuppressants is now lifelong — so the recurring specialty-pharmacy "
        "revenue per surviving recipient often outweighs the one-time surgical "
        "episode in investable value.",
    ],
    connections=default_connections(
        "transplant_services",
        deals_sector="transplant_services",
        extra_pages=[
            ("/industry/transplant_services",
             "Industry deep-dive — transplant-ecosystem deal history + supply "
             "read"),
        ],
        connectors=[
            ("provider_data_hospital_general",
             "CMS Hospital General Information — the transplant-center host "
             "hospitals (academic/large-system footprint)"),
            ("cms_open_data_mup_inpatient_by_provider",
             "Medicare inpatient utilization — transplant MS-DRG volumes & "
             "payments by hospital"),
            ("npi_provider_taxonomy",
             "NPI taxonomy — transplant surgery, nephrology, hepatology & "
             "histocompatibility provider supply"),
            ("cms_open_data_part_b_spending_by_drug",
             "Medicare Part B drug spending — immunosuppressant / anti-rejection "
             "therapy utilization & cost"),
            ("open_payments_general_payments_2024",
             "Open Payments — device/perfusion and pharma payments to transplant "
             "physicians (relationship screen)"),
            ("cdc_data_diabetes_state_burden",
             "CDC diabetes/CKD burden — ESRD demand geography feeding kidney-"
             "transplant need"),
        ],
    ),
    sources=[
        Source("OPTN / UNOS — national transplant data (volumes, waiting list, "
               "centers, allocation policy)", "GOV",
               "https://optn.transplant.hrsa.gov/data/"),
        Source("SRTR — Scientific Registry of Transplant Recipients (program "
               "outcome reports)", "GOV", "https://www.srtr.org/"),
        Source("National Organ Transplant Act (NOTA), Pub. L. 98-507 (1984)",
               "GOV",
               "https://www.congress.gov/bill/98th-congress/senate-bill/2048"),
        Source("Securing the U.S. OPTN Act (2023) — OPTN modernization", "GOV",
               "https://www.congress.gov/bill/118th-congress/house-bill/2544"),
        Source("CMS transplant-program Conditions of Participation (42 CFR 482 "
               "Subpart E)", "GOV",
               "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-G/part-482"),
        Source("Milliman Research Report — U.S. organ and tissue transplant cost "
               "estimates (per-transplant billed charges)", "INDUSTRY",
               "https://www.milliman.com/en/insight/2020-us-organ-tissue-transplant-cost-estimates"),
        Source("PE Desk industry deep-dive (transplant services) + realized-deal "
               "corpus", "INTERNAL",
               "/diligence/tam-sam?template=transplant_services"),
    ],
    live_figures=live_figures_from_dive("transplant_services"),
    trends=(
        "Transplantation has spent the last several years hitting record annual "
        "volumes even as the waiting list stays far larger than the organ supply "
        "— the defining tension of the sector, where demand is structurally "
        "capped by donor availability rather than patient need. Three forces are "
        "reshaping it. First, supply-side technology: normothermic and hypothermic "
        "machine perfusion and donation-after-circulatory-death recovery are "
        "expanding the pool of usable organs and cutting discards, and TransMedics "
        "and peers built the organ-logistics layer around it — the one lever that "
        "actually loosens the supply ceiling. Second, governance: the 2023 "
        "Securing the U.S. OPTN Act broke up the long-standing UNOS single-"
        "contractor model and set HRSA to re-compete and modernize the national "
        "network, while continuous-distribution allocation policy and re-based OPO "
        "performance metrics (with de-certification teeth) are in active flux. "
        "Third, capital: because the centers are academic hospital assets under "
        "outcome-based Conditions of Participation and effectively un-rollable, "
        "for-profit investment has flowed to the ecosystem — perfusion technology, "
        "transplant/immunosuppressant specialty pharmacy (a recurring per-"
        "recipient annuity, now that immunosuppressant coverage is lifelong), "
        "histocompatibility labs, and centers-of-excellence networks. Underneath, "
        "rising ESRD, MASH/NASH cirrhosis, and heart-failure prevalence keep the "
        "need growing, and xenotransplantation sits as a long-run, uncertain "
        "supply unlock."),
    growth_levers=[
        GrowthLever(
            "Machine perfusion + DCD (usable-organ expansion)",
            "Normothermic/hypothermic perfusion and donation-after-circulatory-"
            "death recovery increase the number of transplantable organs and cut "
            "discards — the primary supply-side growth engine.",
            "primary supply lever", "ILLUSTRATIVE"),
        GrowthLever(
            "Immunosuppressant specialty-pharmacy annuity",
            "Every surviving recipient needs lifelong anti-rejection therapy; "
            "lifelong coverage plus a growing recipient base compounds recurring "
            "specialty-pharmacy revenue.",
            "recurring", "GOV"),
        GrowthLever(
            "Rising need (ESRD, MASH/NASH, heart failure)",
            "Diabetes-driven ESRD, MASH/NASH cirrhosis, and heart-failure "
            "prevalence expand the candidate pool — demand that supply must catch "
            "up to.",
            "+ demand base", "GOV"),
        GrowthLever(
            "OPO performance reform (recovery gains)",
            "Re-based OPO outcome metrics with de-certification risk push higher "
            "deceased-donor recovery — more organs into the system.",
            "+ supply", "GOV"),
        GrowthLever(
            "Centers-of-excellence network services",
            "Commercial COE contracting and network administration monetize the "
            "steerage of very-high-dollar transplant episodes.",
            "+ services layer", "ILLUSTRATIVE"),
        GrowthLever(
            "Xenotransplantation (long-run)",
            "Gene-edited animal organs could eventually break the supply ceiling, "
            "but the clinical and regulatory timeline is long and uncertain.",
            "optionality", "ILLUSTRATIVE"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Usable donor-organ supply (perfusion / DCD / OPO recovery), not "
               "patient demand",
        analysis=(
            "Transplant is the rare healthcare vertical whose growth driver is "
            "supply, not demand. Patient need vastly exceeds availability — the "
            "national waiting list runs above 100,000 while roughly 46,000 "
            "transplants are performed a year — so the binding constraint is the "
            "number of usable donor organs, and volume grows only when supply "
            "grows. The levers that expand supply are concrete and current: "
            "machine perfusion (normothermic and hypothermic) keeps marginal "
            "organs viable and cuts discards; donation-after-circulatory-death "
            "recovery adds donors beyond brain-death cases; organ logistics "
            "networks move organs farther with less loss; and re-based OPO "
            "performance metrics (with de-certification risk) push higher "
            "deceased-donor recovery. Underlying need keeps rising with diabetes-"
            "driven ESRD, MASH/NASH cirrhosis, and heart-failure prevalence, but "
            "that need is already latent on the list — so an investment thesis "
            "should be underwritten to the supply curve (perfusion, DCD, OPO "
            "reform, and eventually xenotransplantation), because that is what "
            "actually moves transplant volume."),
        basis="GOV"),
    cost_drivers=[
        CostDriver(
            "Surgical + peri-operative clinical labor", "largest episode cost",
            "Transplant surgeons, anesthesia, ICU, and the multidisciplinary team "
            "for a high-acuity inpatient episode — the dominant cost of the "
            "surgical event.", "ILLUSTRATIVE"),
        CostDriver(
            "Organ acquisition cost (OPO fees, recovery, typing, transport)",
            "pass-through, not margin",
            "Accumulated in the acquisition cost center and reimbursed on a "
            "reasonable-cost basis — a large cost that flows through rather than "
            "contributing margin to the center.", "ILLUSTRATIVE"),
        CostDriver(
            "Immunosuppressant + post-transplant drugs", "recurring lifetime cost",
            "Lifelong anti-rejection therapy per recipient — a cost to the payer "
            "and the recurring revenue base for transplant specialty pharmacy.",
            "GOV"),
        CostDriver(
            "Preservation / perfusion technology + logistics", "growing per case",
            "Machine-perfusion consumables, devices, and organ transport — a "
            "rising per-case cost that buys expanded usable supply and lower "
            "discards.", "ILLUSTRATIVE"),
        CostDriver(
            "Histocompatibility labs, evaluation + regulatory/quality overhead",
            "program fixed cost",
            "Tissue typing/crossmatch, candidate evaluation, SRTR outcome "
            "reporting, and CoP compliance — the fixed cost of running a "
            "credentialed program.", "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "UNOS/OPTN transplant-center lists are public but not vendored offline, "
        "and transplantation is a concentrated, academic hospital service line "
        "rather than a chain market, so a fabricated state map is omitted. The "
        "most consequential geography is not fragmentation but concentration: a "
        "relatively small number of high-volume academic centers dominate each "
        "organ, ~55 federally-designated OPOs recover organs on regional "
        "service areas whose performance now carries de-certification risk, and "
        "OPTN allocation policy (moving to continuous distribution) increasingly "
        "decouples organ offers from strict geographic boundaries. The hospital-"
        "general, Medicare-inpatient-transplant-DRG, NPI-taxonomy, Part-B "
        "immunosuppressant-drug, and CKD/ESRD-burden connectors linked below map "
        "the center footprint, transplant volumes, provider supply, downstream "
        "drug economics, and the demand geography feeding the waiting list — the "
        "honest read in the absence of a vendored center roll."),
)

register(REPORT)
