"""Neurology — the cognitive-plus-procedural specialty riding the anti-amyloid wave.

Deals-only deep-dive (no national physician-practice facility file; geography is
omitted rather than fabricated). Neurology straddles two economies: a cognitive
base (complex diagnosis, long visits) that the RVU system underpays, and a
diversified ancillary/procedural stack that subsidizes it — EMG/nerve-conduction
and EEG diagnostics, buy-and-bill infusion (MS disease-modifying therapies,
IVIG, and now the Alzheimer's anti-amyloid antibodies), and Botox for chronic
migraine, dystonia, and spasticity. Two structural forces frame the sector: a
severe, worsening workforce shortage ("neurology deserts") that teleneurology
extends, and a genuine step-change in demand as FDA-approved anti-amyloid drugs
(lecanemab, donanemab) open a large new infusion-plus-imaging-plus-monitoring
market. The qualitative sections are authored around that ancillary stack, the
anti-amyloid logistics, MS buy-and-bill, and scarce-clinician access. Consumes
``neurology_deep_dive()`` for SOURCED corpus deal figures where present.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="neurology",
    name="Neurology",
    care_setting="Physician services",
    naics="621111",
    one_line_def=(
        "Physician practices diagnosing and managing disorders of the brain, "
        "spinal cord, nerves, and muscles — stroke, epilepsy, multiple "
        "sclerosis, Parkinson's, dementia, migraine, and neuromuscular disease "
        "— where an underpaid cognitive base is subsidized by a diversified "
        "ancillary stack: EMG/EEG diagnostics, buy-and-bill infusion (MS "
        "therapies, IVIG, and the new Alzheimer's anti-amyloid antibodies), and "
        "Botox for chronic migraine and movement disorders."),
    tam_headline=TamHeadline(
        value=28.0, unit="$B", growth_pct=6.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "Modeled from the ~15,000-16,000 practicing US neurologists (AAN "
            "workforce) times the cognitive professional fee plus the ancillary "
            "stack — EMG/nerve-conduction and EEG diagnostics, buy-and-bill "
            "infusion (MS DMTs, IVIG, anti-amyloid), and Botox — not a single "
            "published figure. Growth is the modeled composite of the "
            "Alzheimer's anti-amyloid demand step-change, migraine-injectable "
            "and MS-infusion volume, and aging-neurologic demand, net of "
            "MPFS/E&M drag and white-bagging spread loss."),
    ),
    executive_summary=[
        "Neurology lives on two economies. The cognitive base — the diagnostic "
        "reasoning that is the specialty's real value — is underpaid on E&M "
        "RVUs, so the practice is subsidized by a diversified ancillary stack: "
        "EMG/nerve-conduction and EEG diagnostics, buy-and-bill infusion, and "
        "Botox injections. That diversification is healthier than a "
        "single-drug specialty.",
        "The Alzheimer's anti-amyloid wave is a real step-change. FDA-approved "
        "lecanemab (Leqembi) and donanemab (Kisunla), now covered by Medicare "
        "through a registry, open a large new market — but the binding "
        "constraint is infrastructure: amyloid PET/CSF diagnosis, IV infusion "
        "capacity, and serial MRI to monitor for ARIA (amyloid-related imaging "
        "abnormalities). The demand is genuine; the logistics and safety burden "
        "are the gate.",
        "MS infusion is the profitable core. Buy-and-bill disease-modifying "
        "therapies (ocrelizumab/Ocrevus, natalizumab/Tysabri) plus IVIG are "
        "high-value in-office infusion; oral DMTs and self-injectables leak to "
        "specialty pharmacy, and white bagging threatens the buy-and-bill "
        "spread just as it does in rheumatology.",
        "Botox is a recurring injectable annuity. OnabotulinumtoxinA for chronic "
        "migraine (the PREEMPT protocol), cervical dystonia, and spasticity is "
        "buy-and-bill, repeats roughly quarterly, and stacks with the CGRP "
        "migraine agents — a reliable, diversified ancillary line.",
        "Workforce scarcity is the defining constraint. The AAN documents a "
        "large, worsening neurologist shortfall and severe rural 'neurology "
        "deserts'; access is the bottleneck, which is why teleneurology and "
        "telestroke — extending a scarce clinician across hospitals and regions "
        "— are a structural part of the model.",
        "PE consolidation is earlier here than in GI/derm/ophthalmology. The "
        "acquirable pool is the independent neurology group with EMG/EEG "
        "ancillaries and an owned infusion suite; the aggregation logic mixes "
        "classic buy-and-build with buy-and-bill drug economics and "
        "teleneurology reach.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Referral for headache, weakness/numbness, seizures, tremor, memory "
            "loss, or acute stroke",
            "Cognitive E&M visit + neurologic exam and diagnostic workup",
            "Diagnostic ancillaries — EMG/nerve-conduction, EEG (routine or "
            "long-term monitoring), evoked potentials, imaging",
            "Diagnosis-specific pathway (MS, epilepsy, migraine, Parkinson's, "
            "dementia, neuromuscular)",
            "Benefits investigation + payer authorization / step therapy / "
            "site-of-care determination",
            "Treatment — in-office buy-and-bill infusion (MS DMT, IVIG, "
            "anti-amyloid), Botox injection, or specialty-pharmacy oral/injectable",
            "Ongoing monitoring (e.g. serial MRI for MS and for anti-amyloid "
            "ARIA) + charge capture across all lines",
        ],
        sites_of_care=[
            "Physician office / clinic (cognitive visit, EMG/EEG, Botox and "
            "injections)",
            "Owned in-office infusion suite (MS DMTs, IVIG, anti-amyloid "
            "antibodies)",
            "Epilepsy monitoring unit / long-term EEG (hospital or specialized "
            "center)",
            "Teleneurology / telestroke (acute hospital coverage and outpatient "
            "reach for scarce clinicians)",
            "Imaging (amyloid PET, MRI for MS and ARIA monitoring) — owned or "
            "referred",
        ],
        money_flow=(
            "A neurologist earns a professional fee off the Medicare Physician "
            "Fee Schedule for the cognitive E&M visit — but neurology, like "
            "rheumatology, is a specialty E&M valuation underpays relative to "
            "the diagnostic complexity, so the practice leans on ancillaries. "
            "EMG/nerve-conduction studies and EEG (routine and long-term "
            "monitoring) carry technical and professional components. The "
            "infusion suite buys and bills Part B drugs — MS disease-modifying "
            "therapies, IVIG, and now the Alzheimer's anti-amyloid antibodies — "
            "at Average Sales Price plus a margin, with separate "
            "infusion-administration codes, while Botox (onabotulinumtoxinA) is "
            "a buy-and-bill injectable for chronic migraine and movement "
            "disorders. Oral and self-injectable therapies instead run through "
            "the patient's Part D / specialty-pharmacy benefit at no drug margin "
            "to the practice. Teleneurology and telestroke are contracted "
            "services to hospitals. In an aggregated model the MSO runs "
            "contracting, benefit investigation, and drug purchasing. The "
            "question that sets a neurology platform's value is the mix and "
            "durability of those ancillary lines — infusion spread, diagnostic "
            "volume, and Botox — against a cognitive base that will not carry "
            "the enterprise alone."),
        key_players=(
            "Neurology is less consolidated than the ancillary-ASC specialties, "
            "and the landscape is a mix: emerging PE-backed and multi-specialty "
            "groups building regional neurology platforms and infusion centers; "
            "teleneurology/telestroke firms (Access TeleCare, formerly SOC "
            "Telemed; TeleSpecialists) that monetize scarce clinicians across "
            "hospitals; and the upstream drug and device makers that drive the "
            "buy-and-bill and injectable economics — Biogen/Eisai (lecanemab), "
            "Eli Lilly (donanemab), Roche/Genentech (ocrelizumab), and AbbVie "
            "(Botox). The acquirable pool is the independent neurology group "
            "with EMG/EEG ancillaries and an owned infusion suite."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Practicing US neurologists", "~15,000-16,000",
                    "INDUSTRY · AAN workforce estimates (directional)"),
            Segment("US adults living with Alzheimer's dementia", "~7M",
                    "ACADEMIC · Alzheimer's Association Facts & Figures "
                    "(directional)"),
            Segment("US people living with multiple sclerosis", "~1M",
                    "ACADEMIC · US MS prevalence study (directional)"),
            Segment("US adults with migraine (chronic-migraine subset "
                    "Botox-eligible)", "~39M with migraine",
                    "GOV · migraine-prevalence estimates (directional)"),
            Segment("Ancillary + infusion share of a neurology practice's "
                    "revenue", "significant (illustrative)",
                    "ILLUSTRATIVE · practice economics, directional"),
        ],
        growth_drivers=[
            "Alzheimer's anti-amyloid therapy adoption — a new "
            "infusion+imaging+monitoring demand step-change",
            "Aging population — stroke, Parkinson's, dementia, and neuropathy "
            "all rise steeply with age",
            "Migraine injectables (Botox + CGRP agents) expanding a large "
            "treatable base",
            "MS disease-modifying-therapy infusion volume and diagnostic "
            "(EMG/EEG) ancillary capture",
            "MPFS/E&M under-valuation, white-bagging spread loss, and drug "
            "logistics — the structural offsets",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Medicare / MA": 0.48,
            "Commercial": 0.40,
            "Medicaid": 0.08,
            "Self-pay / other": 0.04,
        },
        rate_mechanics=[
            "MPFS cognitive professional fee for the E&M visit — RVUs × GPCI × "
            "the conversion factor; the base that neurologic complexity "
            "outstrips, subsidized by ancillaries.",
            "Diagnostic ancillaries — EMG/nerve-conduction studies "
            "(95907-95913, 95885-95887) and EEG (routine 95812-95822; "
            "long-term monitoring 95700-series) with technical + professional "
            "components.",
            "Buy-and-bill Part B infusion — MS DMTs (ocrelizumab/Ocrevus, "
            "natalizumab/Tysabri), IVIG, and anti-amyloid antibodies "
            "(lecanemab, donanemab) at ASP+6% plus infusion-administration "
            "codes.",
            "Botox (onabotulinumtoxinA, J0585) buy-and-bill for chronic migraine "
            "(PREEMPT protocol), cervical dystonia, and spasticity — a recurring "
            "~quarterly injectable line.",
            "CMS anti-amyloid coverage via a required registry (the successor to "
            "coverage-with-evidence-development) plus the amyloid-PET and serial "
            "MRI (ARIA monitoring) that the therapy demands.",
            "Teleneurology / telestroke coverage and codes for acute hospital "
            "and outpatient services; white bagging / brown bagging threatens "
            "the infusion buy-and-bill spread as in rheumatology.",
        ],
        reimbursement_risk=(
            "Neurology's risk is more diversified than a single-drug specialty "
            "but real on several fronts. The cognitive E&M base rides the same "
            "MPFS conversion-factor drift as everyone while being structurally "
            "undervalued. The infusion buy-and-bill spread — MS DMTs, IVIG, "
            "anti-amyloid — is exposed to white bagging, ASP resets, and (for "
            "MS) oral/self-injectable substitution to pharmacy. The new "
            "anti-amyloid line carries genuine demand but thin drug margin "
            "against heavy infrastructure and safety-monitoring cost, plus "
            "registry and appropriate-use requirements that gate uptake. EMG/EEG "
            "diagnostic ancillaries have been repeatedly repriced and face "
            "utilization scrutiny. The healthiest neurology platforms spread "
            "revenue across diagnostics, multiple infusible drugs, Botox, and "
            "teleneurology so that no single reimbursement change is "
            "existential."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("CMS anti-amyloid coverage (National Coverage Determination + "
                 "registry)",
                 "Medicare covers FDA-fully-approved anti-amyloid antibodies "
                 "(lecanemab, donanemab) with a registry requirement — the rule "
                 "that unlocked the Alzheimer's demand wave and defines its "
                 "documentation burden.",
                 "https://www.cms.gov/medicare-coverage-database/"),
            Rule("Average Sales Price (ASP+6%) buy-and-bill methodology",
                 "Sets Part B reimbursement for in-office infusible drugs (MS "
                 "DMTs, IVIG, anti-amyloid) and Botox — the ancillary margin "
                 "engine; ASP resets and the sequester move the spread.",
                 "https://www.cms.gov/medicare/payment/part-b-drugs"),
            Rule("Medicare Physician Fee Schedule (annual Final Rule) — E&M + "
                 "EMG/EEG",
                 "Sets the underpaid cognitive-visit fee and the technical/"
                 "professional fees for EMG/nerve-conduction and EEG "
                 "diagnostics.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
            Rule("Payer white-bagging / brown-bagging + step-therapy policies",
                 "Payer specialty-pharmacy mandates strip the infusion "
                 "buy-and-bill spread, and step therapy/prior auth gate MS and "
                 "migraine drug access and the practice's drug mix.",
                 None),
            Rule("FDA appropriate-use + REMS/monitoring for anti-amyloid and MS "
                 "therapies",
                 "Amyloid-PET/CSF confirmation and serial MRI for ARIA (and MS "
                 "PML monitoring for natalizumab) are safety requirements that "
                 "gate throughput and add cost.",
                 "https://www.fda.gov/"),
            Rule("Anti-Kickback / Stark (in-office diagnostics + infusion)",
                 "In-office EMG/EEG and infusion sit inside the Stark in-office "
                 "ancillary exception and AKS — arrangements must be "
                 "fair-market-value and compliant.",
                 "https://www.cms.gov/medicare/regulations-guidance/physician-self-referral"),
        ],
        policy_watch=[
            "Anti-amyloid coverage evolution — registry burden, "
            "appropriate-use, blood-based diagnostics, and capacity build-out",
            "White-bagging mandates vs state bans on the infusion buy-and-bill "
            "spread",
            "ASP resets / Medicare sequester on infusible-drug and Botox add-on",
            "EMG/EEG diagnostic repricing and utilization review",
            "Annual MPFS conversion-factor cuts + E&M/cognitive-care valuation; "
            "teleneurology payment permanence",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "US neurology is highly fragmented across small independent "
            "practices, hospital-employed neurologists, and academic centers, "
            "and PE consolidation is earlier and thinner than in GI, "
            "dermatology, or ophthalmology. The acquirable pool is the "
            "independent neurology group with EMG/EEG diagnostics and an owned "
            "infusion suite; teleneurology adds a distinct, scalable "
            "consolidation vector."),
        hhi_or_share=(
            "No single owner is dominant nationally; concentration is low and "
            "the sector is early in its roll-up. No vendored physician-practice "
            "roll captures operator concentration, so a national chain HHI is "
            "honestly omitted — the corpus deal history below is the real read."),
        consolidation=(
            "Neurology's consolidation logic blends three models: classic "
            "buy-and-build of independent groups with EMG/EEG and infusion "
            "ancillaries; buy-and-bill drug-economics aggregation akin to "
            "rheumatology (MS DMTs, IVIG, anti-amyloid); and teleneurology/"
            "telestroke networks that monetize scarce clinicians across many "
            "hospitals. The anti-amyloid infrastructure build-out (infusion + "
            "PET/MRI + monitoring) is a fresh scale rationale."),
        pe_activity=(
            "A younger PE story, gated by workforce scarcity and by the "
            "cognitive base's weak standalone economics. Diligence centers on "
            "ancillary mix and durability (infusion spread, EMG/EEG volume, "
            "Botox), the ability to build and staff anti-amyloid capacity, "
            "white-bagging exposure, and — above all — recruiting and retaining "
            "a scarce neurologist."),
        notable_players=[
            "Emerging regional neurology / infusion-center platforms",
            "Access TeleCare (formerly SOC Telemed — teleneurology/telestroke)",
            "TeleSpecialists (teleneurology/telestroke)",
            "Biogen / Eisai (lecanemab — upstream)",
            "Eli Lilly (donanemab — upstream)",
            "Roche / Genentech (ocrelizumab — upstream)",
            "AbbVie (Botox — upstream)",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Ancillary + infusion revenue (% of total)",
                "significant (illustrative)",
                "EMG/EEG diagnostics + buy-and-bill infusion + Botox — the "
                "diversified stack that carries a specialty the cognitive fee "
                "cannot."),
            Kpi("Infusion chair utilization", "chairs × turns per day",
                "MS, IVIG, and anti-amyloid infusion is a fixed-cost chassis; "
                "utilization and authorization cycle time drive the drug "
                "margin."),
            Kpi("Anti-amyloid capacity (PET / infusion / MRI throughput)",
                "infrastructure-gated",
                "The Alzheimer's opportunity is capacity-limited — amyloid "
                "diagnosis, infusion slots, and ARIA-monitoring MRI are the "
                "bottlenecks, not demand."),
            Kpi("EMG/EEG diagnostic volume", "studies per neurologist",
                "Technical + professional diagnostic ancillary; repriced over "
                "time and utilization-reviewed."),
            Kpi("Botox / injectable recurrence", "~quarterly per patient",
                "Chronic-migraine and dystonia injections repeat on a "
                "predictable cadence — a recurring buy-and-bill annuity."),
            Kpi("Platform EBITDA margin (post-MSO)", "12-20% (illustrative)",
                "Ancillary-diversified but infusion-spread-sensitive; scarcer "
                "labor caps volume."),
        ],
        margin_profile=(
            "Neurology's economics resemble rheumatology's inversion — the "
            "cognitive diagnostic work is underpaid — but with a more "
            "diversified subsidy. Profit is spread across EMG/nerve-conduction "
            "and EEG diagnostics, buy-and-bill infusion (MS DMTs, IVIG, and the "
            "new anti-amyloid antibodies), and Botox injections, which makes the "
            "practice less hostage to any single line than an infusion-only "
            "specialty. The infusion suite and the diagnostic equipment are "
            "fixed-cost chasses whose margin rises with utilization; the "
            "anti-amyloid opportunity is uniquely infrastructure-gated (PET/CSF "
            "diagnosis, infusion capacity, and serial ARIA-monitoring MRI) and "
            "carries thin drug margin against a heavy logistics and safety "
            "burden. Scarcity of the neurologist both protects pricing and caps "
            "organic volume, so teleneurology leverage matters. Scale spreads "
            "the MSO, concentrates drug-purchasing and payer leverage, and funds "
            "the anti-amyloid build-out; the underlying quality of a neurology "
            "platform is the breadth and durability of its ancillary stack "
            "against a cognitive base that cannot stand alone."),
    ),
    risks=[
        Risk("Neurologist recruitment / retention in a structural shortage",
             "High",
             "A worsening AAN-documented shortfall and rural 'neurology "
             "deserts' make scarce-clinician access the core capacity "
             "constraint and integration risk."),
        Risk("Anti-amyloid execution risk (capacity, ARIA safety, thin margin)",
             "High",
             "The Alzheimer's opportunity is real but infrastructure- and "
             "safety-gated; PET/MRI capacity, ARIA monitoring, and thin drug "
             "margin can turn demand into a logistics and liability burden."),
        Risk("White bagging / ASP erosion of infusion buy-and-bill spread",
             "Medium",
             "Payer specialty-pharmacy mandates and ASP resets compress the MS/"
             "IVIG/anti-amyloid infusion margin, as in rheumatology."),
        Risk("MS oral/self-injectable substitution to pharmacy", "Medium",
             "Oral DMTs and self-injectables move MS revenue out of the "
             "in-office infusion suite to specialty pharmacy."),
        Risk("EMG/EEG diagnostic repricing + utilization review", "Medium",
             "The diagnostic ancillary lines have been cut repeatedly and face "
             "utilization scrutiny."),
        Risk("MPFS / cognitive-E&M under-valuation", "Medium",
             "A structurally-underpaid cognitive base leaves the practice "
             "dependent on ancillary margin."),
        Risk("PE model immaturity / integration", "Medium",
             "An earlier roll-up with fewer proven platforms and integration "
             "playbooks than adjacent specialties."),
    ],
    diligence_questions=[
        "What is the revenue mix across cognitive E&M, EMG/EEG diagnostics, "
        "buy-and-bill infusion, and Botox — and how diversified is profit?",
        "What is the infusion drug mix (MS DMTs, IVIG, anti-amyloid), the "
        "buy-and-bill spread, and the white-bagging exposure by payer?",
        "What anti-amyloid capacity exists (amyloid PET/CSF, infusion chairs, "
        "ARIA-monitoring MRI), and is the demand converting to throughput?",
        "What is the neurologist and APP staffing, age profile, and recruitment "
        "pipeline against a structural shortage?",
        "How large and durable is the teleneurology/telestroke contract book, "
        "and what are its economics and payment-permanence risks?",
        "What is EMG/EEG diagnostic utilization, and how exposed is it to "
        "repricing and utilization review?",
        "What is the Botox/injectable panel size and recurrence cadence, and "
        "the migraine (CGRP + Botox) treatment mix?",
        "What is the payer mix and commercial-rate position, and the "
        "prior-authorization burden gating drug and diagnostic starts?",
    ],
    insider_lens=[
        "Neurology is a cognitive specialty that pays its bills with "
        "procedures. The diagnostic reasoning is the real value and the "
        "worst-paid line; EMG/EEG diagnostics, buy-and-bill infusion, and Botox "
        "are what actually fund the practice. The upside versus rheumatology is "
        "that the subsidy is diversified across several ancillaries, not one "
        "drug.",
        "The anti-amyloid wave is demand you can't fully serve yet. Leqembi and "
        "Kisunla are covered and the eligible dementia population is huge, but "
        "the binding constraints are amyloid-PET/CSF diagnosis, infusion-chair "
        "capacity, and serial MRI to catch ARIA brain swelling/bleeding — the "
        "opportunity is an infrastructure build, and the drug margin is thin "
        "against the safety and logistics burden.",
        "MS infusion is the reliable core, and it's leaking. Ocrevus and "
        "Tysabri buy-and-bill are high-value in-office revenue, but oral DMTs "
        "and self-injectables keep shifting MS to specialty pharmacy, and white "
        "bagging threatens what stays — the same buy-and-bill fragility "
        "rheumatology faces.",
        "Botox is an underrated annuity. Chronic-migraine and movement-disorder "
        "injections repeat roughly every quarter under a defined protocol — a "
        "recurring, buy-and-bill injectable line that stacks with the CGRP "
        "migraine agents and diversifies the ancillary base.",
        "Scarcity runs the whole specialty. The AAN documents a deepening "
        "neurologist shortage and real rural deserts, so access is the "
        "bottleneck — which is why teleneurology and telestroke exist and why "
        "retaining and leveraging every clinician (with APPs) is the operating "
        "game, not volume marketing.",
        "This is an early roll-up, so underwrite the model, not a comp. "
        "Neurology hasn't produced the proven national platforms GI or derm "
        "have; the thesis blends buy-and-build, buy-and-bill drug economics, "
        "and teleneurology reach — make sure the plan names which engine is "
        "actually driving the return.",
    ],
    connections=default_connections(
        "neurology",
        deals_sector="neurology",
        extra_pages=[
            ("/industry/neurology",
             "Industry deep-dive — neurology deal history + ancillary-stack "
             "read"),
        ],
        connectors=[
            ("npi_provider_taxonomy",
             "NPI taxonomy — neurology specialty mix & practice enrollment"),
            ("cms_open_data_part_b_spending_by_drug",
             "Medicare Part B drug spending — buy-and-bill infusion (MS DMT, "
             "IVIG, anti-amyloid, Botox) read"),
            ("cms_open_data_mup_physician_by_provider_service",
             "Medicare physician utilization — EMG/EEG, infusion & E&M volume"),
            ("cms_open_data_part_d_spending_by_drug",
             "Medicare Part D drug spending — oral MS DMT & CGRP migraine "
             "read"),
            ("open_payments_general_payments_2024",
             "Open Payments — drug/device-maker payments to neurologists "
             "(relationship screen)"),
            ("census_acs_cbsa_profile",
             "Census ACS — CBSA age demographics for aging-neurologic demand "
             "mapping"),
        ],
    ),
    sources=[
        Source("American Academy of Neurology — neurology workforce and "
               "supply/demand analyses", "INDUSTRY",
               "https://www.aan.com/"),
        Source("CMS — anti-amyloid National Coverage Determination and coverage "
               "database (registry requirement)", "GOV",
               "https://www.cms.gov/medicare-coverage-database/"),
        Source("CMS — Medicare Physician Fee Schedule and Average Sales Price "
               "files (E&M, EMG/EEG, buy-and-bill drugs)", "GOV",
               "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
        Source("Alzheimer's Association — 2024 Alzheimer's Disease Facts & "
               "Figures (prevalence)", "ACADEMIC",
               "https://www.alz.org/alzheimers-dementia/facts-figures"),
        Source("US MS prevalence study (Wallin et al., Neurology) — ~1M US "
               "adults with MS", "ACADEMIC",
               "https://www.neurology.org/"),
        Source("PE Desk industry deep-dive (neurology) + realized-deal corpus",
               "INTERNAL",
               "/diligence/tam-sam?template=neurology"),
    ],
    live_figures=live_figures_from_dive("neurology"),
    trends=(
        "Neurology has always been a cognitive specialty the RVU system "
        "underpays for its actual work, so it built a diversified ancillary "
        "subsidy — EMG/nerve-conduction and EEG diagnostics, buy-and-bill "
        "infusion (MS disease-modifying therapies and IVIG), and Botox for "
        "chronic migraine and movement disorders. Two developments now reshape "
        "the trajectory. First, and genuinely new, the FDA-approved "
        "anti-amyloid antibodies for early Alzheimer's (lecanemab, donanemab), "
        "now covered by Medicare through a registry, open a large new market — "
        "but one gated by infrastructure: amyloid PET/CSF diagnosis, infusion "
        "capacity, and serial MRI to monitor for ARIA. Second, the workforce "
        "shortage keeps deepening — the AAN documents a widening shortfall and "
        "rural deserts — pushing teleneurology and telestroke from novelty to "
        "structure. Against these, the infusion buy-and-bill spread faces the "
        "same white-bagging and biosimilar/ASP pressures as rheumatology, MS "
        "keeps leaking to oral/pharmacy therapy, and the cognitive base rides "
        "MPFS erosion. PE consolidation is earlier than in adjacent "
        "specialties; quality-of-earnings work centers on ancillary breadth and "
        "durability, anti-amyloid execution, and scarce-clinician retention."),
    growth_levers=[
        GrowthLever(
            "Alzheimer's anti-amyloid adoption",
            "Build amyloid diagnosis, infusion, and ARIA-monitoring capacity to "
            "serve a large, newly-covered early-Alzheimer's population.",
            "step-change / infrastructure-gated", "GOV"),
        GrowthLever(
            "Migraine injectables (Botox + CGRP)",
            "Recurring chronic-migraine Botox plus CGRP agents expand a large "
            "treatable base into a predictable injectable line.",
            "+ recurring injectable revenue", "ILLUSTRATIVE"),
        GrowthLever(
            "MS + IVIG buy-and-bill infusion",
            "High-value in-office infusion of MS DMTs and IVIG — the profitable "
            "ancillary core (leaking partly to pharmacy).",
            "+ infusion margin", "ILLUSTRATIVE"),
        GrowthLever(
            "Aging-neurologic demand + EMG/EEG diagnostics",
            "Stroke, Parkinson's, dementia, and neuropathy rise with age and "
            "drive diagnostic ancillary volume.",
            "+ steady volume", "GOV"),
        GrowthLever(
            "Teleneurology / telestroke leverage",
            "Extend a scarce clinician across hospitals and regions — a "
            "scalable consolidation and access vector.",
            "+ access / capacity", "ILLUSTRATIVE"),
        GrowthLever(
            "White bagging + ASP erosion + MPFS/E&M drag",
            "Payer specialty-pharmacy mandates, infusible ASP resets, and "
            "cognitive-fee under-valuation are the structural headwind.",
            "rate + policy headwind", "ILLUSTRATIVE"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Aging-neurologic demand + the anti-amyloid Alzheimer's wave",
        analysis=(
            "The demand base is broad and aging-linked: stroke, Parkinson's, "
            "epilepsy, dementia, and peripheral neuropathy all climb steeply "
            "with age, and migraine (~39M US adults) and MS (~1M) add large, "
            "partly-younger cohorts. The discrete new driver is Alzheimer's: "
            "with ~7M US adults living with the disease and FDA-approved "
            "anti-amyloid antibodies now covered by Medicare through a registry, "
            "a large early-stage population becomes treatable for the first "
            "time — a genuine step-change in infusion, imaging, and monitoring "
            "demand. The critical nuance is that this demand is "
            "supply-constrained twice over: by a documented neurologist "
            "shortage that gates access to any neurologic care, and by the "
            "specific infrastructure the anti-amyloid pathway requires (amyloid "
            "PET/CSF, infusion chairs, and serial ARIA-monitoring MRI). Realized "
            "volume is therefore paced by capacity and clinician access, and the "
            "economic offsets are reimbursement (white bagging, thin drug "
            "margin, MPFS erosion), not the size of the patient pool."),
        basis="GOV"),
    cost_drivers=[
        CostDriver(
            "Physician & advanced-practice compensation", "~35-45% of cost",
            "The scarce neurologist is the biggest cost and the capacity "
            "constraint; retention and APP leverage are the core operating "
            "levers.", "ILLUSTRATIVE"),
        CostDriver(
            "Buy-and-bill drug COGS (MS DMT, IVIG, anti-amyloid, Botox)",
            "large gross / thin net",
            "Infusible and injectable drug acquisition dominates gross cost; "
            "the practice earns the thin ASP-plus spread, squeezed by white "
            "bagging.", "ILLUSTRATIVE"),
        CostDriver(
            "Infusion + diagnostics staff and equipment", "~12-18% of cost",
            "Infusion nursing, EMG/EEG technologists and equipment, and — for "
            "anti-amyloid — the PET/MRI and ARIA-monitoring infrastructure.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Benefit investigation + MSO back office (billing/RCM)",
            "~10-15% of cost",
            "Prior-authorization/benefit-investigation staff and the "
            "shared-services apparatus the drug- and diagnostic-heavy model "
            "requires.", "ILLUSTRATIVE"),
        CostDriver(
            "Facility/occupancy + telehealth platform", "~6-10% of cost",
            "Clinic and infusion-suite real estate plus the teleneurology "
            "technology and coverage overhead.", "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "No national physician-practice facility file is vendored — a neurology "
        "group is a business, not a Medicare-certified facility — so state "
        "geography is omitted rather than fabricated. The most consequential "
        "geographic variables are the acute maldistribution of the scarce "
        "neurology workforce (rural 'neurology deserts' where teleneurology "
        "substitutes for on-site coverage), state telehealth/telestroke "
        "licensure and payment rules, state white-bagging laws that protect the "
        "infusion buy-and-bill spread, the corporate-practice-of-medicine "
        "doctrine, and the growing set of states enacting PE-in-healthcare "
        "transaction-review laws. The NPI-taxonomy, Part B/Part D drug-spending, "
        "physician-utilization, and demographic connectors linked below map "
        "neurology supply and infusion/diagnostic volume against the aging "
        "population — the honest footprint read."),
)

register(REPORT)
