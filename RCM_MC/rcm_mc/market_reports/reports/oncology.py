"""Oncology — community (non-hospital) medical & radiation oncology practices.

Deals-only deep-dive (no vendored community-oncology facility file; oncology
practices are outside the CMS post-acute provider rolls). The whole model is a
thin spread on a huge buy-and-bill drug base, reshaped by 340B and site-of-
service, so the qualitative sections are authored around Part B drug payment
(ASP+6%), the 340B arbitrage, the distributor-backed network model, and the
Enhancing Oncology Model. Consumes ``oncology_deep_dive()`` for SOURCED corpus
deal figures.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="oncology",
    name="Oncology",
    care_setting="Physician services",
    naics="621111",
    one_line_def=(
        "Community (non-hospital) medical, radiation, and surgical oncology "
        "practices that diagnose and treat cancer largely through physician-"
        "administered 'buy-and-bill' drugs — reimbursed under the Medicare "
        "Physician Fee Schedule plus Part B drug payment (ASP+6%), with 340B and "
        "site-of-service economics dominating the model."),
    tam_headline=TamHeadline(
        value=208.0, unit="$B", growth_pct=8.0, basis_label="GOV",
        basis_note=(
            "NCI estimates US national cancer-care spending at ~$208B (2020), "
            "projected to exceed $245B by 2030. Community (non-hospital) "
            "oncology is a large but shrinking share as care shifts to hospital/"
            "340B systems; growth is the modeled composite of incidence, "
            "novel-drug launches, and site shift."),
    ),
    executive_summary=[
        "Oncology's economics are the drug, not the visit. Most medical-"
        "oncology revenue flows through physician-administered ('buy-and-bill') "
        "Part B drugs paid at Average Sales Price + 6% — the practice buys "
        "expensive infusibles and earns a spread, so drug margin and purchasing "
        "scale, not E&M coding, drive the P&L.",
        "The battleground is site of service and 340B. The same chemotherapy "
        "costs Medicare far more in a hospital outpatient department than in a "
        "physician office, and 340B lets qualifying hospitals buy drugs at deep "
        "discounts and bill full price — a subsidy that has pulled oncologists "
        "into hospital employment and steadily shrunk the independent community "
        "base. Where a patient is treated is worth more than what they are "
        "treated for.",
        "The independent survivor is the network. The US Oncology Network "
        "(McKesson), OneOncology (Cencora, with General Atlantic/TPG), and "
        "American Oncology Network aggregate independent practices to defend "
        "drug-purchasing scale, negotiate payer and value-based contracts, and "
        "build ancillaries (in-office pharmacy, pathology, imaging, radiation).",
        "Value-based oncology is arriving. CMS's Oncology Care Model and its "
        "successor, the Enhancing Oncology Model, push practices toward "
        "episode-based accountability, and payers demand pathway adherence — "
        "layering care-management and shared-savings economics onto buy-and-"
        "bill.",
        "The tail risks all bear on the drug margin: IRA Medicare drug-price "
        "negotiation, ASP+6% sequestration, biosimilar substitution, and the "
        "relentless 340B/site-of-service pressure that keeps eroding the "
        "independent model.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Diagnosis / referral (screening, biopsy, pathology, staging)",
            "Oncologist consult + molecular/genomic testing → pathway plan",
            "Benefit verification, prior authorization, financial counseling",
            "Drug procurement (GPO/wholesaler, buy-and-bill inventory)",
            "Treatment delivery — infusion suite, oral oncolytics, or radiation",
            "Supportive care + monitoring (labs, imaging, toxicity management)",
            "Billing — professional fee (MPFS) + Part B drug (ASP+6%) + "
            "technical/ancillary; value-based episode reconciliation",
        ],
        sites_of_care=[
            "Community oncology clinic + infusion suite (the independent model)",
            "Hospital outpatient department (HOPD) — often 340B, the site care "
            "shifts TO",
            "Radiation-oncology center (linear accelerators — capital-intensive)",
            "In-office dispensing pharmacy (oral oncolytics — a growing "
            "ancillary)",
            "Pathology / molecular lab (in-house or reference)",
        ],
        money_flow=(
            "A community oncology practice earns three stacked revenue streams. "
            "First, the professional fee — E&M and procedure codes paid off the "
            "Medicare Physician Fee Schedule. Second, and far larger, physician-"
            "administered drug revenue: the practice buys infused chemotherapy "
            "and immunotherapy through a GPO/wholesaler and bills Medicare Part "
            "B at Average Sales Price plus 6% (reduced by sequestration to "
            "roughly ASP+4.3%), earning a spread plus vendor rebates — this "
            "'buy-and-bill' margin is the economic core. Third, ancillaries — "
            "in-office oral-oncolytic dispensing, pathology, imaging, and "
            "radiation-therapy technical fees. Commercial payers pay multiples "
            "of Medicare while enforcing clinical pathways and prior "
            "authorization. Overlaid on all of it is value-based episode payment "
            "(OCM/EOM) that pays management fees and shares savings against a "
            "benchmark. The critical distortion is 340B: qualifying hospitals "
            "buy the same drugs at steep discounts while billing full price, an "
            "arbitrage that has drawn oncologists into hospital employment and "
            "pressured the independent economics."),
        key_players=(
            "The independent networks provide drug-purchasing and administrative "
            "scale — The US Oncology Network (McKesson-backed), OneOncology "
            "(Cencora/AmerisourceBergen, with GA/TPG), American Oncology "
            "Network, and large independents like Florida Cancer Specialists, "
            "Texas Oncology, Tennessee Oncology, and Minnesota Oncology. On the "
            "other side, hospital systems and 340B-eligible academic centers "
            "employ a rising share of oncologists. Adjacent: GPOs and specialty "
            "distributors (McKesson, Cencora, Cardinal), molecular diagnostics "
            "(Foundation Medicine, Guardant, Tempus, Natera), and radiation-"
            "oncology equipment and roll-ups."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("US national cancer-care spending (2020)", "~$208.00B",
                    "GOV · NCI cancer-expenditure estimates"),
            Segment("Medicare Part B oncology drug spending",
                    "tens of $B / yr",
                    "GOV · MedPAC Part B drug spending (directional)"),
            Segment("New US cancer cases per year", "~2.0M / yr",
                    "GOV · NCI / ACS incidence estimates"),
            Segment("Community vs hospital share of infusions",
                    "shifting toward HOPD/340B",
                    "ILLUSTRATIVE · site-of-service trend, directional"),
            Segment("Oral-oncolytic / precision-therapy spend",
                    "the fastest-growing line",
                    "ILLUSTRATIVE · industry pipeline, directional"),
        ],
        growth_drivers=[
            "Cancer incidence + aging — ~2.0M new US cases/yr and rising",
            "Novel high-cost therapies (immuno-oncology, targeted, cell)",
            "Site-of-service shift to HOPD/340B — reshuffles WHERE margin sits",
            "Value-based episode models (OCM → EOM) — new management-fee revenue",
            "Precision diagnostics driving targeted-therapy volume",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Medicare / MA": 0.50,
            "Commercial": 0.40,
            "Medicaid / other": 0.10,
        },
        rate_mechanics=[
            "Medicare Part B 'buy-and-bill' — physician-administered drugs paid "
            "Average Sales Price + 6% (net ~ASP+4.3% after sequestration); the "
            "practice buys, bills, and earns the spread plus rebates — the "
            "economic core.",
            "Medicare Physician Fee Schedule — E&M and procedure professional "
            "fees (RVU × conversion factor × GPCI) — the smaller stream.",
            "340B Drug Pricing Program — qualifying (mostly hospital) providers "
            "buy at ~25-50% discounts and bill full price; the arbitrage that "
            "pulls oncologists into hospital employment.",
            "Radiation-oncology technical fees — freestanding vs HOPD payment "
            "(and the on-again/off-again Radiation Oncology Model bundle "
            "proposal).",
            "Oral oncolytics — Part D or the medical benefit, with in-office "
            "dispensing as an ancillary margin capture.",
            "Value-based episodes — the Oncology Care Model (2016-2022) and "
            "Enhancing Oncology Model (2023+): management fees plus shared "
            "savings/risk against episode benchmarks.",
            "Commercial pathways & prior authorization — payers pay ASP-plus "
            "multiples but enforce regimen pathways and step therapy.",
            "IRA drug-price effects — Medicare-negotiated 'maximum fair prices' "
            "and inflation rebates reshape ASP and the buy-and-bill spread over "
            "time.",
        ],
        reimbursement_risk=(
            "The whole model rests on the drug margin, so drug-payment reform is "
            "the dominant risk. Sequestration already cut ASP+6% to roughly "
            "ASP+4.3%, biosimilar substitution compresses the per-unit spread on "
            "legacy blockbusters, and the Inflation Reduction Act's Medicare "
            "drug-price negotiation and inflation rebates will reshape the very "
            "ASPs the spread is calculated on over the next several years. "
            "Structurally, 340B and site-of-service policy is a continuous "
            "headwind: because hospitals capture the 340B discount and higher "
            "HOPD rates, independent community practices face both a competitive "
            "disadvantage and a steady pull of physicians into employment. Payer "
            "utilization management (pathways, prior authorization, step "
            "therapy) and the shift toward episode-based accountability (EOM) "
            "add margin and administrative pressure. The offset is that novel "
            "high-cost therapies keep expanding the drug-revenue base — but on a "
            "spread that policy is actively trying to compress."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("Medicare Part B drug payment (ASP+6%, Section 1847A)",
                 "Sets buy-and-bill reimbursement; sequestration and reform "
                 "proposals move the spread that is the model's core margin.",
                 "https://www.cms.gov/medicare/payment/part-b-drugs"),
            Rule("340B Drug Pricing Program (Section 340B, PHS Act)",
                 "The discount-vs-full-price arbitrage that drives site shift "
                 "and pulls oncologists into hospital employment.",
                 "https://www.hrsa.gov/opa"),
            Rule("Inflation Reduction Act — Medicare drug-price negotiation",
                 "Negotiated 'maximum fair prices' plus inflation rebates "
                 "reshape ASP on major oncology drugs — and the buy-and-bill "
                 "spread.",
                 "https://www.cms.gov/inflation-reduction-act-and-medicare"),
            Rule("Enhancing Oncology Model (EOM)",
                 "CMS Innovation Center episode model (successor to OCM) — the "
                 "value-based-oncology payment framework.",
                 "https://www.cms.gov/priorities/innovation/innovation-models/enhancing-oncology-model"),
            Rule("Stark Law / in-office ancillary services exception",
                 "Governs in-office drug administration, dispensing, pathology, "
                 "and imaging — what makes ancillary capture legal.",
                 "https://www.cms.gov/medicare/regulations-guidance/physician-self-referral"),
            Rule("Oral-chemotherapy parity + USP <800> hazardous-drug handling",
                 "Coverage-parity mandates for oral oncolytics plus compounding "
                 "and safety standards for hazardous drug handling.",
                 None),
        ],
        policy_watch=[
            "IRA negotiated-price rollout and its effect on ASP and the "
            "buy-and-bill spread",
            "340B program reform, contract-pharmacy litigation, and eligibility "
            "fights",
            "Site-neutral payment equalizing HOPD and physician-office drug "
            "administration",
            "EOM participation economics and mandatory-model risk",
            "Biosimilar adoption pace and interchangeability driving spread "
            "compression",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Community oncology has consolidated defensively — independent "
            "practices banded into large networks (US Oncology, OneOncology, "
            "AON) to preserve drug-purchasing scale — while hospital systems and "
            "340B centers employ a rising share of oncologists. The result is a "
            "barbell: a shrinking but still-substantial independent long tail "
            "organized under a few networks, against growing hospital "
            "ownership."),
        hhi_or_share=(
            "No single owner dominates nationally, but a handful of networks "
            "(US Oncology/McKesson, OneOncology/Cencora, AON) aggregate much of "
            "the independent segment's purchasing, while 340B hospitals capture "
            "an increasing share of infusion volume. No vendored community-"
            "oncology facility file exists, so operator concentration is "
            "honestly not measured here."),
        consolidation=(
            "Two forces run in parallel: hospital/340B employment on one side "
            "and network aggregation on the other. The networks provide GPO "
            "scale, payer contracting, OCM/EOM infrastructure, and ancillary "
            "build-out (in-office pharmacy, pathology, radiation) that let "
            "independents survive. Distributors and sponsors (McKesson, Cencora, "
            "General Atlantic, TPG) back the networks — Cencora took a majority "
            "of OneOncology in 2023."),
        pe_activity=(
            "Active but structurally constrained — the buy-and-bill drug margin "
            "and 340B dynamics make oncology a scale-and-purchasing game, so the "
            "winning model is the distributor-/network-backed platform rather "
            "than a classic small-practice roll-up. Diligence centers on drug-"
            "margin durability, 340B exposure, payer pathway contracts, and "
            "value-based readiness."),
        notable_players=[
            "The US Oncology Network (McKesson)", "OneOncology (Cencora)",
            "American Oncology Network", "Florida Cancer Specialists",
            "Texas Oncology", "Tennessee Oncology",
            "New York Cancer & Blood Specialists", "Minnesota Oncology",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Drug revenue (% of total)", "60-80%",
                "Buy-and-bill dominates the top line; margin is the spread, not "
                "the gross — the number that makes oncology a purchasing "
                "business."),
            Kpi("Drug gross margin (spread + rebates)",
                "low-to-mid single digits of drug revenue",
                "A thin percentage on a huge base, so purchasing terms and "
                "biosimilar selection are everything."),
            Kpi("Infusion-chair utilization", "chair-hours booked",
                "The fixed-cost infusion suite; empty chairs are lost, "
                "non-recoverable margin."),
            Kpi("Provider productivity (visits + infusions)",
                "oncologist throughput",
                "The professional-fee driver in a shortage specialty."),
            Kpi("340B exposure of the local market",
                "share of infusion in 340B hospitals",
                "The site-shift threat — how much of the addressable volume can "
                "be out-economics'd by a hospital's 340B discount."),
            Kpi("Value-based performance (OCM/EOM)",
                "shared savings vs benchmark",
                "The new margin layer — management fees plus (two-sided) "
                "episode risk."),
            Kpi("Practice EBITDA margin",
                "mid-teens to low-20s (illustrative)",
                "Sensitive to the drug-margin spread and the site/payer mix."),
        ],
        margin_profile=(
            "Community oncology is a paradox — an enormous top line dominated by "
            "pass-through drug cost, on which the practice earns a thin "
            "percentage spread. Because the ASP+6% (post-sequester ~4.3%) margin "
            "is small relative to acquisition cost, purchasing scale (GPO terms, "
            "rebates, biosimilar selection, inventory management) is decisive, "
            "and small changes in the spread or in payer mix swing profitability "
            "hard. Ancillaries — in-office oral-drug dispensing, pathology, "
            "imaging, and radiation technical fees — carry richer margins and "
            "are where independents differentiate. The overhang is that the "
            "highest-margin capture (340B) belongs to hospitals, and drug-"
            "payment reform is actively compressing the spread the independent "
            "model depends on."),
    ),
    risks=[
        Risk("Drug-payment reform (IRA negotiation, ASP+6% cuts, biosimilars)",
             "High",
             "Directly compresses the buy-and-bill spread that is the model's "
             "core margin."),
        Risk("340B / site-of-service shift to hospitals", "High",
             "The hospital discount plus higher HOPD rates pull volume and "
             "physicians out of the independent community base."),
        Risk("Payer utilization management + pathway/prior-auth pressure",
             "Medium",
             "Restricts regimen choice and adds administrative cost and denials "
             "on high-dollar claims."),
        Risk("Value-based-model (EOM) downside risk", "Medium",
             "Episode benchmarks and two-sided risk can turn a management-fee "
             "upside into a loss on catastrophic drug spend."),
        Risk("Drug-inventory + reimbursement-timing (working capital)",
             "Medium",
             "The practice fronts cash for expensive inventory; ASP lag and "
             "denials create working-capital and margin exposure."),
        Risk("Oncologist recruitment / retention (shortage specialty)",
             "Medium",
             "Oncologist supply is tight; key-man concentration risk is acute."),
    ],
    diligence_questions=[
        "What is the drug-margin bridge — GPO terms, rebates, biosimilar mix, "
        "and sequestration — and how durable is the spread under the IRA?",
        "What is the practice's 340B exposure and the local competitive share "
        "of 340B hospitals?",
        "What is the payer mix, and how do commercial contracts pay drugs "
        "(ASP-plus level) and enforce pathways/prior auth?",
        "What is the ancillary build-out (in-office pharmacy, pathology, "
        "imaging, radiation), and what is each contributing to EBITDA?",
        "What is the OCM/EOM participation history and shared-savings/risk track "
        "record?",
        "How concentrated is volume in the top oncologists, and what are "
        "recruitment, tenure, and retention terms?",
        "What is infusion-chair utilization, and how much capacity and working "
        "capital does the drug book consume?",
        "How exposed is the top line to a handful of blockbuster drugs facing "
        "negotiation or biosimilar entry?",
    ],
    insider_lens=[
        "The practice is a pharmacy with exam rooms attached. Sixty-plus percent "
        "of the top line is drug pass-through, and the business is really a thin "
        "spread on a huge purchasing volume — which is why GPO terms, rebates, "
        "and biosimilar selection matter more than E&M coding, and why scale (a "
        "network) is close to existential.",
        "340B is the invisible hand reshaping the sector. Because hospitals buy "
        "the same drugs at deep 340B discounts and bill full price, they can "
        "out-economics any independent and afford to employ the oncologist — the "
        "steady erosion of community oncology is a policy artifact, not a "
        "management failure.",
        "The margin is small and policy is aiming at it. ASP+6% is already "
        "ASP+4.3% after sequester, and the IRA's negotiated prices and inflation "
        "rebates will move the very ASPs the spread is calculated on — a "
        "business whose core margin is being actively legislated.",
        "Ancillaries are the differentiator, not the drug. Independents defend "
        "margin by adding in-office dispensing, pathology, imaging, and "
        "radiation — the technical and dispensing fees are where real, "
        "non-pass-through margin lives.",
        "Value-based oncology is a management-fee business bolted onto buy-and-"
        "bill. OCM/EOM pays practices to manage total episode cost; done well it "
        "is incremental margin and defensible payer relationships, done badly "
        "(two-sided risk on catastrophic drug spend) it is a loss center.",
    ],
    connections=default_connections(
        "oncology",
        deals_sector="oncology",
        extra_pages=[
            ("/industry/oncology",
             "Industry deep-dive — oncology deal history + structure"),
        ],
        connectors=[
            ("cms_open_data_part_b_spending_by_drug",
             "Medicare Part B drug spending — the buy-and-bill drug base"),
            ("cms_open_data_mup_physician_by_provider_service",
             "Medicare physician utilization — drug-administration & service "
             "volume"),
            ("cms_open_data_mup_partd_prescriber_by_geo_drug",
             "Medicare Part D prescribing by geography — oral-oncolytic read"),
            ("open_payments_general_payments_2024",
             "Open Payments — pharma payments to oncologists (relationship "
             "screen)"),
            ("npi_provider_taxonomy",
             "NPI taxonomy — hematology/oncology supply & enrollment"),
        ],
    ),
    sources=[
        Source("NCI — Cancer Prevalence and Cost of Care Projections", "GOV",
               "https://costprojections.cancer.gov/"),
        Source("CMS — Medicare Part B drug Average Sales Price (ASP) payment "
               "(Section 1847A)", "GOV",
               "https://www.cms.gov/medicare/payment/part-b-drugs"),
        Source("HRSA — 340B Drug Pricing Program", "GOV",
               "https://www.hrsa.gov/opa"),
        Source("CMS Innovation Center — Enhancing Oncology Model (EOM)", "GOV",
               "https://www.cms.gov/priorities/innovation/innovation-models/enhancing-oncology-model"),
        Source("MedPAC — Report to Congress, Part B drug payment chapter",
               "GOV", "https://www.medpac.gov/"),
        Source("Community Oncology Alliance — Practice Impact Report "
               "(site-of-service / consolidation trends)", "INDUSTRY",
               "https://communityoncology.org/"),
        Source("PE Desk industry deep-dive (oncology) + realized-deal corpus",
               "INTERNAL", "/diligence/tam-sam?template=oncology"),
    ],
    live_figures=live_figures_from_dive("oncology"),
    trends=(
        "Community oncology's trajectory is a story of margin under siege and "
        "defensive consolidation. The 2005 shift to Average-Sales-Price drug "
        "payment reset buy-and-bill economics to a thin, transparent spread; "
        "sequestration then trimmed ASP+6% to roughly ASP+4.3%. Meanwhile the "
        "340B program — hospitals buying drugs at deep discounts and billing "
        "full price — gave hospital systems an economics advantage that pulled "
        "oncologists into employment and steadily shrank the independent base. "
        "Independents responded by banding into distributor-backed networks (US "
        "Oncology under McKesson, OneOncology, American Oncology Network) to "
        "preserve purchasing scale and build ancillaries. CMS layered on "
        "value-based episodes (the Oncology Care Model, then the Enhancing "
        "Oncology Model), and a wave of novel high-cost therapies (immuno-"
        "oncology, targeted agents, cell therapy) expanded the drug-revenue base "
        "even as the spread on it compressed. The forward inflection is the "
        "Inflation Reduction Act: Medicare drug-price negotiation and inflation "
        "rebates will reshape the ASPs the entire model is priced on, while "
        "340B reform and site-neutral proposals keep the structural pressure on "
        "the independent community setting."),
    growth_levers=[
        GrowthLever(
            "Cancer incidence + aging",
            "~2.0M new US cases a year and rising with the 65+ population — the "
            "non-discretionary demand base.",
            "+ mid-single %/yr volume", "GOV"),
        GrowthLever(
            "Novel high-cost therapies",
            "Immuno-oncology, targeted agents, and cell/gene therapy raise spend "
            "per patient and expand the drug-revenue base.",
            "+ drug spend", "ILLUSTRATIVE"),
        GrowthLever(
            "Ancillary build-out (pharmacy, pathology, imaging, radiation)",
            "The non-pass-through margin lever independents use to defend "
            "economics against 340B hospitals.",
            "+ ancillary margin", "ILLUSTRATIVE"),
        GrowthLever(
            "Value-based episodes (OCM → EOM)",
            "Management fees plus shared savings for managing total episode "
            "cost — a new revenue layer bolted onto buy-and-bill.",
            "+ management fees", "GOV"),
        GrowthLever(
            "Drug-payment reform drag (IRA, sequester, biosimilars)",
            "Negotiation, inflation rebates, and biosimilar substitution "
            "compress the very spread the model runs on.",
            "spread headwind", "GOV"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Cancer incidence × aging × novel-therapy expansion",
        analysis=(
            "The demand base is cancer incidence — roughly 2.0M new US cases a "
            "year (NCI/ACS) and rising with the aging population, since most "
            "cancers are diseases of older age. On top of the demographic base, "
            "two forces expand revenue faster than case counts: a wave of novel "
            "high-cost therapies (immuno-oncology, targeted agents, and cell/"
            "gene therapy) that raises spend per patient, and precision "
            "diagnostics that convert more patients onto targeted regimens. "
            "Survivorship gains also lengthen treatment duration. The critical "
            "nuance for an independent practice is that volume growth does not "
            "automatically accrue to the community setting — site-of-service and "
            "340B dynamics determine whether the incremental patient is treated "
            "in a physician office or a hospital outpatient department."),
        basis="GOV"),
    cost_drivers=[
        CostDriver(
            "Physician-administered drugs (buy-and-bill inventory)",
            "~60-75% of cost",
            "The dominant, largely pass-through cost; purchasing terms, "
            "rebates, and biosimilar selection decide the thin spread.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Clinical labor (oncologists, infusion nurses, pharmacists)",
            "~12-18% of cost",
            "Specialized, scarce, and expensive — a shortage-specialty labor "
            "line.", "ILLUSTRATIVE"),
        CostDriver(
            "Infusion suite, pharmacy & facility", "~6-10% of cost",
            "The fixed chair/pharmacy chassis plus USP <800> hazardous-drug "
            "handling.", "ILLUSTRATIVE"),
        CostDriver(
            "Diagnostics & ancillary cost of goods (pathology, imaging, "
            "radiation)", "variable",
            "The cost side of the margin-differentiating ancillaries — each "
            "carries its own capital and consumables.", "ILLUSTRATIVE"),
        CostDriver(
            "Billing, prior-authorization & compliance", "~5-8% of cost",
            "A heavy prior-authorization and denials workload on high-cost drug "
            "claims.", "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "No vendored community-oncology facility file exists — oncology "
        "practices are outside the CMS post-acute provider rolls — so state "
        "geography is omitted rather than fabricated. Qualitatively, the "
        "independent-versus-hospital balance is what varies by geography: states "
        "and metros with heavy 340B hospital penetration have seen faster "
        "erosion of community oncology, while large independent networks anchor "
        "specific states (Texas Oncology, Florida Cancer Specialists, Tennessee "
        "Oncology). The Medicare Part B drug-spending and physician-utilization "
        "connectors linked below map infusion and drug volume by geography — the "
        "honest footprint read for where community-oncology economics are "
        "strongest."),
)

register(REPORT)
