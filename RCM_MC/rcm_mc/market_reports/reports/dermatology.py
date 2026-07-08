"""Dermatology — the archetypal first-wave PE specialty roll-up.

Deals-only deep-dive (no national physician-practice census; geography is omitted
rather than fabricated). Dermatology was the first specialty PE rolled up, and it
set the template: a professional fee augmented by in-house dermatopathology, high-
value Mohs micrographic surgery, advanced-practice-provider (NP/PA) leverage, and
a cash-pay cosmetic line. The qualitative sections are authored around that stack,
the mid-level-utilization and Mohs-outlier scrutiny that the roll-up drew, and the
cash-pay cosmetic cyclicality. Consumes ``dermatology_deep_dive()`` for SOURCED
corpus deal figures.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="dermatology",
    name="Dermatology",
    care_setting="Physician services",
    naics="621111",
    one_line_def=(
        "Physician practices treating skin disease — medical dermatology (skin "
        "cancer, acne, psoriasis, eczema), surgical dermatology (Mohs "
        "micrographic surgery, excisions), dermatopathology (the in-house biopsy "
        "read), and cash-pay cosmetic/aesthetic services — where platform value "
        "is built on advanced-practice-provider leverage plus the pathology and "
        "Mohs ancillaries far more than the office-visit professional fee."),
    tam_headline=TamHeadline(
        value=38.0, unit="$B", growth_pct=5.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "Modeled from the ~12,000-13,000 practicing US dermatologists (plus "
            "the large NP/PA-extended visit base) times the professional fee plus "
            "the ancillary and cash-pay stack — dermatopathology, Mohs surgery, "
            "and cosmetic/aesthetic revenue — not a single published figure. "
            "Growth is the modeled composite of skin-cancer/aging demand, "
            "APP-leverage capacity expansion, and cosmetic cash-pay growth, net of "
            "MPFS revaluation drag on derm codes."),
    ),
    executive_summary=[
        "Dermatology wrote the specialty-roll-up playbook. It was the first "
        "vertical PE consolidated (Advanced Dermatology, Forefront, US "
        "Dermatology Partners, Schweiger), and its template — APP leverage plus "
        "in-house pathology, Mohs, and cosmetic cash-pay — became the model every "
        "later specialty copied.",
        "Advanced-practice-provider leverage is the margin engine and the "
        "flashpoint. NPs and PAs extend a dermatologist's capacity across "
        "high-volume medical-derm visits and biopsies; that leverage drives "
        "platform economics and is exactly what draws the 'derm mill' and "
        "overbilling scrutiny.",
        "Two ancillaries carry the value: dermatopathology (the in-house biopsy "
        "read — the classic self-referral-sensitive capture) and Mohs "
        "micrographic surgery (high-value, stage-based, and flagged for outlier "
        "utilization). How cleanly each is owned sets platform quality.",
        "Cosmetic is the cash-pay upside and the cyclical risk. Botox, fillers, "
        "lasers, and body contouring are non-reimbursed retail revenue at high "
        "margin — real growth, but recession-sensitive and overlapping the medspa "
        "adjacency.",
        "Demand is demographic and non-discretionary on the medical side: "
        "non-melanoma skin cancer is the most common cancer in the US (millions "
        "of cases a year), and an aging, sun-exposed population keeps the biopsy "
        "and Mohs pipeline full.",
        "The sector is mature — first- and second-generation platforms have "
        "turned sponsors, some have struggled, and diligence has shifted from "
        "buy-and-build growth to mid-level-compliance posture, ancillary "
        "durability, and physician retention.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Referral / self-referral / screening for a skin complaint or lesion",
            "Office E&M visit + full-skin exam — often APP-extended (NP/PA)",
            "Biopsy of suspicious lesions (shave / punch / excision)",
            "Dermatopathology — the biopsy read by the in-house derm-path lab",
            "Treatment — destruction/excision, Mohs surgery for skin cancer, or "
            "medical therapy (topicals, biologics)",
            "Cosmetic pathway — cash-pay Botox, fillers, laser, body contouring",
            "Charge capture, coding (E&M, path 88305, Mohs stages), and "
            "collections",
        ],
        sites_of_care=[
            "Physician / APP clinic (the E&M and biopsy volume base)",
            "In-house dermatopathology lab (biopsy reads)",
            "In-office Mohs surgical suite (skin-cancer excision + repair)",
            "Cosmetic / aesthetic suite (cash-pay injectables, laser, devices)",
            "Medspa adjacency (aesthetic services under medical direction)",
        ],
        money_flow=(
            "A dermatologist earns a professional fee off the Medicare Physician "
            "Fee Schedule for the office visit, the biopsy, and the destruction "
            "or excision — or a commercial multiple of it. The higher-value "
            "economics are the ancillaries and the leverage on the same patient. "
            "Advanced-practice providers (NPs and PAs) extend visit capacity, so a "
            "single dermatologist's clinical footprint — and billable volume — "
            "scales well beyond one pair of hands. Every suspicious lesion "
            "biopsied is read by the in-house dermatopathology lab, which bills "
            "the technical and professional components of the pathology code "
            "(88305 is the workhorse). Skin cancers flow to Mohs micrographic "
            "surgery, billed by stage/block — high-value, repetitive, in-office "
            "work. And the cosmetic line runs entirely cash-pay at retail margin. "
            "In the PE structure the payer (or the patient, for cosmetic) pays the "
            "physician-owned professional corporation, which pays the MSO a "
            "management fee for the pathology lab, the cosmetic operation, "
            "billing, and shared services — so platform value turns on how much of "
            "the pathology, Mohs, and cosmetic stack it legally owns and how "
            "productively APP leverage is deployed."),
        key_players=(
            "PE-backed platforms lead the consolidation and largely defined it: "
            "Advanced Dermatology & Cosmetic Surgery (ADCS), Forefront "
            "Dermatology, US Dermatology Partners, Schweiger Dermatology Group, "
            "QualDerm Partners, West Dermatology, and Epiphany Dermatology built "
            "regional and multi-state footprints. Biologic manufacturers "
            "(Sanofi/Regeneron's dupilumab, the psoriasis-biologic makers) sit "
            "upstream on the medical side, though most derm biologics run through "
            "the pharmacy benefit. Aesthetic manufacturers (AbbVie/Allergan's "
            "Botox and Juvederm, laser-device makers) supply the cosmetic line. "
            "Large independent single- and multi-provider derm groups anchor most "
            "metros and are the acquirable pool."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Practicing US dermatologists", "~12,000-13,000",
                    "INDUSTRY · AAD workforce (directional)"),
            Segment("Non-melanoma skin cancer cases treated / yr",
                    "~5.4M (most common US cancer)",
                    "GOV · CDC / peer-reviewed skin-cancer burden estimates"),
            Segment("New invasive melanoma cases / yr", "~100,000",
                    "GOV · NCI / CDC cancer statistics"),
            Segment("Cosmetic / cash-pay share of a mature platform's revenue",
                    "~15-30% (practice-dependent)",
                    "ILLUSTRATIVE · platform economics, directional"),
            Segment("Ancillary + cash share (path + Mohs + cosmetic)",
                    "~35-55% of a mature platform's revenue",
                    "ILLUSTRATIVE · platform economics, directional"),
        ],
        growth_drivers=[
            "Aging + cumulative UV exposure → rising skin-cancer incidence ~2-3%/yr",
            "APP leverage expanding visit and biopsy capacity per dermatologist",
            "Mohs volume growth with skin-cancer prevalence and older patients",
            "Cosmetic cash-pay growth (injectables, laser, body contouring)",
            "Biologic-treated inflammatory disease (atopic dermatitis, psoriasis)",
            "MPFS derm-code revaluation + mid-level scrutiny — the offsetting drag",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Commercial": 0.44,
            "Medicare / MA": 0.40,
            "Self-pay / cash (cosmetic)": 0.11,
            "Medicaid": 0.05,
        },
        rate_mechanics=[
            "MPFS professional fee for E&M and derm procedures (biopsies "
            "11102-11107, destruction 17000+, excisions, Mohs 17311-17315) — "
            "RVUs × GPCI × the annual conversion factor, or a commercial multiple.",
            "Dermatopathology — the technical and professional components of the "
            "biopsy read (88305 the workhorse), constrained by the anti-markup "
            "rule and Stark self-referral limits on in-house labs.",
            "Mohs micrographic surgery — billed per stage/block (17311 first "
            "stage, 17312 additional), with appropriate-use criteria and outlier- "
            "utilization scrutiny on high-stage billers.",
            "Advanced-practice-provider billing — NP/PA services billed "
            "incident-to or under the APP's own NPI; the leverage model's rules "
            "(supervision, incident-to conditions) gate the economics.",
            "Cosmetic / aesthetic — entirely cash-pay retail (Botox, fillers, "
            "laser, body contouring); no reimbursement, priced to the local "
            "market.",
            "Derm biologics (dupilumab, psoriasis agents) — predominantly "
            "pharmacy-benefit / specialty-pharmacy rather than in-office "
            "buy-and-bill, so the drug ancillary is thinner than in GI or "
            "rheumatology.",
        ],
        reimbursement_risk=(
            "Dermatology's professional fee rides the same MPFS conversion-factor "
            "drift as every specialty, and periodic revaluation of high-volume "
            "derm codes (E&M, biopsy, destruction, pathology) is a recurring "
            "specific risk. The ancillary exposures are structural: "
            "dermatopathology self-referral is constrained by the anti-markup rule "
            "and Stark, and aggressive in-house-lab or 'pod-lab' arrangements draw "
            "OIG scrutiny; Mohs micrographic surgery faces appropriate-use "
            "criteria and outlier-utilization audits on high-stage billers; and "
            "advanced-practice-provider leverage — the margin engine — is the "
            "focus of 'derm mill', incident-to, and medical-necessity scrutiny "
            "around biopsy and skin-exam volume. The cosmetic line is cash-pay and "
            "unregulated on price but recession-sensitive. A durable platform "
            "keeps its pathology, Mohs, and APP practices clean and its revenue "
            "diversified across medical, surgical, and cosmetic so no single "
            "repricing is existential."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("Medicare Physician Fee Schedule (annual Final Rule)",
                 "Sets the RVUs and conversion factor for the derm E&M visit, "
                 "biopsy, destruction, excision, and Mohs codes, and periodically "
                 "revalues high-volume dermatology services.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
            Rule("Physician self-referral law (Stark, 42 CFR 411.350+) + "
                 "anti-markup rule",
                 "Governs the in-house dermatopathology lab — the classic derm "
                 "ancillary — and the anti-markup limits on marking up purchased "
                 "diagnostic tests.",
                 "https://www.cms.gov/medicare/regulations-guidance/physician-self-referral"),
            Rule("Mohs appropriate-use criteria + outlier-utilization review",
                 "AUC and CMS/OIG scrutiny of high-stage Mohs billers constrain "
                 "the surgical-ancillary economics.",
                 "https://oig.hhs.gov/reports-and-publications/all-reports-and-publications/"),
            Rule("Incident-to + APP supervision rules",
                 "Govern how NP/PA services are billed (incident-to vs own NPI) "
                 "and supervised — the rules that gate the advanced-practice "
                 "leverage model.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
            Rule("Anti-Kickback Statute + corporate practice of medicine",
                 "Governs the MSO / friendly-PC structure, pathology and cosmetic "
                 "arrangements, and referral relationships in the platform.",
                 "https://oig.hhs.gov/compliance/advisory-opinions/"),
            Rule("FDA regulation of injectables, lasers & aesthetic devices",
                 "The cosmetic line's products (neuromodulators, fillers, energy "
                 "devices) are FDA-regulated; off-label and device-safety issues "
                 "carry liability.",
                 "https://www.fda.gov/medical-devices"),
        ],
        policy_watch=[
            "MPFS revaluation of high-volume dermatology and pathology codes",
            "OIG / payer scrutiny of advanced-practice-provider utilization and "
            "incident-to billing ('derm mill' concern)",
            "Mohs appropriate-use enforcement and high-stage outlier audits",
            "Dermatopathology self-referral / anti-markup and pod-lab scrutiny",
            "State PE-in-healthcare transaction-review and CPOM enforcement",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "US dermatology remains fragmented across independent single- and "
            "multi-provider groups, but it is the most PE-consolidated physician "
            "specialty — the first vertical rolled up, with several national and "
            "multi-state platforms now employing a meaningful share of "
            "dermatologists in their lead markets. The acquirable pool is the "
            "independent derm group with capturable pathology, Mohs, and cosmetic "
            "ancillaries and room for APP leverage."),
        hhi_or_share=(
            "No single owner is dominant nationally; concentration is regional and "
            "platform-specific. No vendored physician-practice roll captures "
            "operator concentration, so a national chain HHI is honestly omitted — "
            "the corpus deal history below is the real read."),
        consolidation=(
            "Dermatology is the original specialty roll-up and its playbook "
            "defined the category: acquire an anchor group, tuck in independents, "
            "centralize the MSO back office, capture the dermatopathology lab and "
            "cosmetic operation, and leverage advanced-practice providers to scale "
            "visit volume per dermatologist. As the first mover it is also the "
            "most mature — first-generation platforms (Advanced Dermatology, "
            "Forefront, US Dermatology Partners) have turned sponsors, some have "
            "struggled, and the category has absorbed the reputational scrutiny "
            "that its scale invited."),
        pe_activity=(
            "The most PE-active physician specialty of the last decade and the "
            "template for the rest. Diligence has matured from buy-and-build "
            "growth toward mid-level-compliance posture (incident-to and "
            "medical-necessity), pathology and Mohs ancillary durability, cosmetic "
            "cyclicality, and physician retention — and toward the multiple "
            "compression that a maturing, picked-over market brings."),
        notable_players=[
            "Advanced Dermatology & Cosmetic Surgery (ADCS)",
            "Forefront Dermatology", "US Dermatology Partners",
            "Schweiger Dermatology Group", "QualDerm Partners",
            "West Dermatology", "Epiphany Dermatology",
            "AbbVie / Allergan Aesthetics (Botox / Juvederm — cosmetic driver)",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Visits / provider (with APP leverage)", "physician + NP/PA",
                "The volume engine; advanced-practice leverage multiplies the "
                "billable clinical footprint per dermatologist."),
            Kpi("Dermatopathology pull-through", "biopsies read in-house",
                "The path ancillary — the higher the in-house read rate, the more "
                "margin captured, subject to anti-markup and Stark limits."),
            Kpi("Mohs cases / surgeon / yr", "high-value, stage-based",
                "The surgical ancillary; volume and stage mix drive yield, but "
                "high-stage outliers draw audit attention."),
            Kpi("Cosmetic / cash-pay revenue (% of total)", "15-30%",
                "The retail upside — high margin, no reimbursement, and "
                "recession-sensitive."),
            Kpi("Biopsy-to-visit ratio", "compliance-sensitive",
                "A watched utilization metric; unusually high ratios (often "
                "APP-driven) invite medical-necessity scrutiny."),
            Kpi("Platform EBITDA margin (post-MSO)", "18-25% (illustrative)",
                "Ancillary- and cash-rich dermatology runs at the higher end of "
                "physician-services margins."),
        ],
        margin_profile=(
            "Dermatology economics combine a high-volume, APP-leveraged visit base "
            "with three margin layers the office fee alone does not capture. "
            "Advanced-practice providers extend a dermatologist's billable "
            "capacity, so revenue per physician scales beyond one clinician's "
            "hands. In-house dermatopathology captures the biopsy-read margin on "
            "the same lesions the clinic samples (within anti-markup and Stark "
            "limits). Mohs micrographic surgery is high-value, repetitive, "
            "in-office work. And the cosmetic line adds cash-pay retail margin "
            "with no payer. The result is one of the richer physician-services "
            "margin profiles — but it is also the one that invited the most "
            "scrutiny, because the same levers that drive margin (APP leverage, "
            "path capture, Mohs volume) are the ones regulators and payers watch. "
            "Scale spreads the MSO and pathology lab; the durable quality is a "
            "clean, diversified stack rather than any single aggressive lever."),
    ),
    risks=[
        Risk("Advanced-practice-provider / incident-to compliance scrutiny",
             "High",
             "APP leverage is the margin engine and the flashpoint — 'derm mill', "
             "incident-to, and biopsy medical-necessity scrutiny can force volume "
             "and billing changes."),
        Risk("Physician retention / comp-haircut backlash", "High",
             "Selling dermatologists (and Mohs surgeons and dermatopathologists) "
             "are the EBITDA; a botched post-close comp redesign drives defection."),
        Risk("Dermatopathology self-referral / anti-markup repricing", "Medium",
             "The in-house path ancillary is constrained by Stark and anti-markup "
             "rules; aggressive pod-lab structures draw OIG scrutiny."),
        Risk("Mohs appropriate-use / outlier-utilization audit", "Medium",
             "High-stage Mohs billing is a known audit target; AUC enforcement "
             "compresses the surgical ancillary."),
        Risk("Cosmetic cash-pay cyclicality", "Medium",
             "Non-reimbursed aesthetic revenue is recession-sensitive and "
             "competitive with medspas — a discretionary-spend exposure."),
        Risk("MPFS derm-code revaluation + conversion-factor erosion", "Medium",
             "A structural squeeze on the professional fee plus periodic "
             "revaluation of high-volume derm and pathology codes."),
        Risk("Multiple compression on exit", "Medium",
             "As the most mature specialty roll-up, dermatology faces the "
             "clearest entry/exit multiple-compression pressure."),
    ],
    diligence_questions=[
        "What is the advanced-practice-provider mix and the incident-to billing "
        "posture, and what is the biopsy-to-visit and medical-necessity audit "
        "history?",
        "What share of EBITDA is dermatopathology, Mohs, and cosmetic versus the "
        "professional fee, and how cleanly is each captured under Stark / "
        "anti-markup?",
        "What is the Mohs stage-mix and outlier posture relative to peers, and "
        "the audit/appropriate-use history?",
        "How large and durable is the cosmetic cash-pay line, and how exposed is "
        "it to recession and medspa competition?",
        "What is the post-close physician (and Mohs-surgeon / dermatopathologist) "
        "compensation model, and how much projected EBITDA rests on the comp "
        "haircut?",
        "What is the payer mix and commercial-rate position, and how durable are "
        "the top commercial contracts?",
        "What is the reputational and media exposure around mid-level utilization "
        "given the sector's scrutiny history?",
        "Where is the platform in its ownership cycle, and what does the entry-vs- "
        "exit multiple picture imply for the arbitrage?",
    ],
    insider_lens=[
        "Dermatology wrote the playbook everyone copied. It was the first "
        "specialty PE rolled up, and its template — APP leverage plus in-house "
        "pathology, Mohs, and cash-pay cosmetic — is the model GI, ophthalmology, "
        "and the rest followed. That also makes it the most mature and the most "
        "scrutinized.",
        "Mid-level leverage is the whole margin story and the whole risk story. "
        "NPs and PAs let one dermatologist bill like several — which is the "
        "economics and, simultaneously, the 'derm mill', incident-to, and "
        "unnecessary-biopsy scrutiny. You cannot underwrite the margin without "
        "underwriting the compliance posture.",
        "The pathology lab is the quiet ancillary. Reading your own biopsies "
        "captures margin on the same lesions you sample — legal within Stark and "
        "the anti-markup rule, lucrative, and exactly the kind of self-referral "
        "structure OIG revisits.",
        "Mohs is high-value and high-visibility. The stage-based billing is "
        "genuine surgical revenue, but high-stage outliers are a named audit "
        "target — a Mohs-heavy platform flatters margin and raises audit risk at "
        "the same time.",
        "Cosmetic is the cash cushion and the cyclical tell. Botox and fillers "
        "carry retail margin with no payer, but the line breathes with the "
        "economy and competes with every medspa on the block — great in an "
        "expansion, first to soften in a downturn.",
        "Derm biologics mostly left the office. Unlike GI or rheumatology, most "
        "dermatology biologics run through the pharmacy benefit, so there is far "
        "less in-office buy-and-bill infusion margin to underwrite — the drug "
        "story is prescribing, not infusing.",
    ],
    connections=default_connections(
        "dermatology",
        deals_sector="dermatology",
        extra_pages=[
            ("/industry/dermatology",
             "Industry deep-dive — dermatology deal history + ancillary read"),
        ],
        connectors=[
            ("npi_provider_taxonomy",
             "NPI taxonomy — dermatology, dermatopathology, Mohs & NP/PA "
             "specialty mix and enrollment"),
            ("cms_open_data_mup_physician_by_provider_service",
             "Medicare physician utilization — E&M, biopsy, Mohs & pathology "
             "volume and allowed charges (outlier read)"),
            ("open_payments_general_payments_2024",
             "Open Payments — biologic/aesthetic industry payments to "
             "dermatologists (relationship screen)"),
            ("cms_open_data_mup_partd_prescriber_by_geo_drug",
             "Medicare Part D prescriber — dermatology biologic/topical "
             "prescribing footprint"),
            ("census_acs_cbsa_profile",
             "Census ACS — CBSA age (65+) and affluence for skin-cancer and "
             "cosmetic-demand mapping"),
            ("oig_leie_exclusions",
             "OIG LEIE — excluded individuals/entities (compliance screen)"),
        ],
    ),
    sources=[
        Source("American Academy of Dermatology (AAD) — workforce, skin-cancer "
               "burden, and practice data", "INDUSTRY",
               "https://www.aad.org/"),
        Source("CMS — Medicare Physician Fee Schedule annual Final Rule (RVUs, "
               "conversion factor, derm/pathology/Mohs codes)", "GOV",
               "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
        Source("Physician self-referral law (Stark, 42 CFR 411.350+) + "
               "anti-markup rule — in-house pathology", "GOV",
               "https://www.cms.gov/medicare/regulations-guidance/physician-self-referral"),
        Source("CDC / NCI — skin-cancer incidence (non-melanoma and melanoma "
               "burden)", "GOV",
               "https://www.cdc.gov/cancer/skin/"),
        Source("JAMA Dermatology / Health Affairs — research on private-equity "
               "ownership, mid-level utilization, and biopsy patterns", "ACADEMIC",
               "https://jamanetwork.com/journals/jamadermatology"),
        Source("HHS Office of Inspector General — Mohs and pathology utilization "
               "and self-referral reports", "GOV",
               "https://oig.hhs.gov/reports-and-publications/all-reports-and-publications/"),
        Source("PE Desk industry deep-dive (dermatology) + realized-deal corpus",
               "INTERNAL",
               "/diligence/tam-sam?template=dermatology"),
    ],
    live_figures=live_figures_from_dive("dermatology"),
    trends=(
        "Dermatology was the first specialty private equity rolled up, and it "
        "defined the category. The template — extend a dermatologist's capacity "
        "with advanced-practice providers, capture the in-house dermatopathology "
        "lab, add high-value Mohs micrographic surgery, and layer on a cash-pay "
        "cosmetic line — became the model GI, ophthalmology, and the rest "
        "followed. As the first mover, dermatology is also the most mature: "
        "first-generation platforms like Advanced Dermatology, Forefront, and US "
        "Dermatology Partners have turned sponsors, some have struggled, and the "
        "sector absorbed the reputational scrutiny its scale invited — JAMA "
        "Dermatology and mainstream-press critiques of 'derm mills', mid-level "
        "utilization, and unnecessary biopsies. The forward tensions are on the "
        "same levers that built the margin: advanced-practice-provider "
        "compliance and incident-to billing, dermatopathology self-referral under "
        "Stark and the anti-markup rule, Mohs appropriate-use and outlier "
        "auditing, and the cyclicality of the cosmetic cash-pay line. Underlying "
        "demand is durable and demographic — skin cancer is the most common "
        "cancer in the US and the aging, sun-exposed population keeps the biopsy "
        "and Mohs pipeline full — but quality-of-earnings work now centers on "
        "compliance posture, ancillary durability, and physician retention rather "
        "than buy-and-build growth."),
    growth_levers=[
        GrowthLever(
            "Skin-cancer / aging demand",
            "An aging, sun-exposed population drives rising non-melanoma and "
            "melanoma incidence — the durable, non-discretionary medical-derm "
            "base.",
            "+2-3%/yr incidence", "GOV"),
        GrowthLever(
            "Advanced-practice-provider leverage",
            "NP/PA extension multiplies billable visit and biopsy capacity per "
            "dermatologist — the platform's primary margin lever.",
            "primary / capacity", "ILLUSTRATIVE"),
        GrowthLever(
            "Dermatopathology + Mohs ancillary capture",
            "Reading biopsies in-house and performing Mohs surgery add margin "
            "streams off the same patients the clinic sees.",
            "+ ancillary margin", "ILLUSTRATIVE"),
        GrowthLever(
            "Cosmetic cash-pay growth",
            "Injectables, laser, and body contouring add high-margin retail "
            "revenue with no payer, overlapping the medspa adjacency.",
            "+ cash-pay revenue", "ILLUSTRATIVE"),
        GrowthLever(
            "Consolidation multiple arbitrage + comp haircut",
            "Acquire independent derm groups at lower multiples, centralize the "
            "MSO and pathology lab, and re-rate on scale and ancillaries.",
            "primary / retention-gated", "ILLUSTRATIVE"),
        GrowthLever(
            "MPFS revaluation + mid-level scrutiny",
            "Periodic derm-code revaluation, conversion-factor drift, and "
            "incident-to/utilization scrutiny are the structural headwinds.",
            "rate / compliance headwind", "GOV"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Skin-cancer incidence (aging × cumulative UV exposure)",
        analysis=(
            "The dominant medical-side demand driver is skin cancer, which is the "
            "most common cancer in the United States by a wide margin — roughly "
            "5.4 million non-melanoma cases treated a year, plus about 100,000 new "
            "invasive melanomas — driven by an aging population and cumulative "
            "lifetime ultraviolet exposure. That produces a large, recurring, and "
            "non-discretionary pipeline of skin exams, biopsies, dermatopathology "
            "reads, and Mohs surgeries that grows structurally with demographics. "
            "Inflammatory disease (atopic dermatitis, psoriasis) adds a growing, "
            "biologic-treated medical base, though most of that drug spend runs "
            "through the pharmacy benefit rather than the office. The discretionary "
            "layer is cosmetic — Botox, fillers, laser, and body contouring — which "
            "grows with disposable income and beauty-market trends but softens in a "
            "downturn. The net demand curve is a durable, aging-weighted medical "
            "core with a cyclical cash-pay overlay: the biopsy and Mohs pipeline is "
            "predictable; the cosmetic upside breathes with the economy."),
        basis="GOV"),
    cost_drivers=[
        CostDriver(
            "Physician + advanced-practice-provider compensation",
            "~40-50% of cost",
            "The dominant cost; dermatologist, Mohs-surgeon, and NP/PA comp — the "
            "biggest margin lever and the biggest retention risk.", "ILLUSTRATIVE"),
        CostDriver(
            "Clinical + front-office staff", "~15-20% of cost",
            "Medical assistants, nurses, and clinic staff running a high-volume "
            "visit and procedure operation.", "ILLUSTRATIVE"),
        CostDriver(
            "Dermatopathology lab (techs, reagents, equipment)", "~8-12% of cost",
            "The cost side of the in-house path ancillary — histology staff, "
            "reagents, and lab capital.", "ILLUSTRATIVE"),
        CostDriver(
            "Cosmetic product + device COGS", "variable / retail",
            "Neuromodulator and filler acquisition plus laser/energy-device "
            "capital — the cost side of the cash-pay line.", "ILLUSTRATIVE"),
        CostDriver(
            "MSO back office + occupancy", "~10-15% of cost",
            "Billing/RCM, IT, compliance, and clinic real estate across the "
            "platform.", "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "No national physician-practice census is vendored — a dermatology group "
        "is a business, not a Medicare-certified facility — so state geography is "
        "omitted rather than fabricated. The most consequential geographic "
        "variables are the corporate-practice-of-medicine doctrine (strong-CPOM "
        "states force the friendly-PC/MSO structure and shape how "
        "advanced-practice providers and dermatopathology can be organized), "
        "state APP scope-of-practice and supervision rules (which set how far the "
        "mid-level leverage model can run), and the growing list of states "
        "enacting PE-in-healthcare transaction-review laws. The NPI-taxonomy, "
        "Medicare physician-utilization, Part D prescriber, and demographic "
        "connectors linked below map dermatology supply and biopsy/Mohs volume "
        "against the aging, sun-exposed population that drives skin-cancer demand "
        "— the honest footprint read."),
)

register(REPORT)
