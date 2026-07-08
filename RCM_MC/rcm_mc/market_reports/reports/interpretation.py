"""Interpretation — medical language-access / interpretation services.

Deals-only pattern (copied from hospice.py): no vendored national facility
file, so geography is honestly omitted and the report leans on the qualitative
deep sections + ``live_figures_from_dive("interpretation")`` for any SOURCED
corpus figures. The defining fact of the vertical is that interpretation is a
CIVIL-RIGHTS-MANDATED, largely NON-REIMBURSED compliance opex line the provider
bears — not a payer-billed service — so the qualitative sections are authored
around Title VI / ACA Section 1557 / ADA, the OPI/VRI/on-site modality mix, and
the language-of-lesser-diffusion margin dynamic.
"""
from __future__ import annotations

from .. import (
    Competition, CostDriver, GrowthLever, HowItWorks, Kpi, MarketReport,
    MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment, Source,
    TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="interpretation",
    name="Interpretation",
    care_setting="Other services",
    naics="541930",
    one_line_def=(
        "Spoken-language interpretation (and often written translation) that "
        "gives limited-English-proficient and Deaf/Hard-of-Hearing patients "
        "meaningful access to care — delivered over-the-phone (OPI), by video "
        "remote interpreting (VRI), and on-site, and sold to hospitals and "
        "health systems as a civil-rights-mandated, largely non-reimbursed "
        "compliance service."),
    tam_headline=TamHeadline(
        value=2.6, unit="$B", growth_pct=8.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "Modeled US healthcare-interpretation spend (~$2.5-3.0B, a subset "
            "of the ~$7-8B US language-services market); no single published "
            "government total exists for the healthcare slice. Growth is the "
            "modeled composite of LEP-population growth, Section 1557 "
            "enforcement, and telehealth-driven VRI adoption."),
    ),
    executive_summary=[
        "This is a compliance cost, not a reimbursed service. Interpretation is "
        "mandated by Title VI, ACA Section 1557, and the ADA, but Medicare and "
        "most commercial payers do NOT pay for it — the hospital funds it as "
        "opex. That makes demand non-discretionary and recession-resistant, but "
        "the customer is actively trying to minimize the line item.",
        "The modality mix IS the margin story. Over-the-phone (OPI) and video "
        "(VRI) are scalable, technology-and-contractor businesses at 35-55% "
        "gross margin; on-site is a local, scheduling, fill-rate business with "
        "2-hour minimums and travel that is far harder to scale but stickier "
        "with the health system.",
        "Spanish is a commodity; the money is in the rare languages. Spanish is "
        "the majority of volume with deep, cheap interpreter supply — the "
        "premium and the scarcity sit in languages of lesser diffusion and in "
        "ASL/VRI, which is structurally supply-constrained and high-rate.",
        "AI compresses the low end and lifts the high end. Machine translation "
        "is eating routine OPI, but Section 1557 explicitly limits reliance on "
        "machine translation and unqualified staff/family for consequential "
        "encounters (consent, diagnosis, behavioral health) — protecting the "
        "qualified-human-interpreter premium.",
        "One of the most PE-active B2B healthcare-services rolls: recurring, "
        "mandated, uncapped per-minute spend, tech-enabled routing, and a long "
        "tail of local on-site agencies to consolidate under a scaled remote "
        "platform — but constant RFP re-bid and rate pressure cap the upside.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Patient encounter with an LEP or Deaf/HoH patient triggers a "
            "language-access obligation (Title VI / 1557 / ADA)",
            "Clinician requests an interpreter through the platform (app, "
            "tablet, phone, or scheduled on-site booking)",
            "Routing/dispatch matches language + modality + qualification "
            "(medical-interpreter certification for consequential encounters)",
            "Interpreter renders the encounter — OPI (per-minute), VRI "
            "(per-minute), or on-site (per-hour, with minimums)",
            "Usage is metered and billed to the health system under an "
            "enterprise MSA; document translation billed per word",
            "Quality/QA — call recording, certification checks, and "
            "language-access reporting the hospital needs for compliance",
        ],
        sites_of_care=[
            "Hospital inpatient + emergency department (highest-acuity demand)",
            "Ambulatory clinics and physician offices",
            "Telehealth / virtual visits (native VRI/OPI demand)",
            "Labor & delivery, oncology, behavioral health (on-site, sensitive)",
            "Payer/health-plan member services and public-health programs",
        ],
        money_flow=(
            "Interpretation is overwhelmingly a business-to-business sale to "
            "the provider, not a payer-billed service. Language service "
            "companies bill hospitals and health systems per-minute for OPI and "
            "VRI (roughly sub-$1 to ~$1.50/minute for common languages, more "
            "for rare languages and ASL) and per-hour for on-site work "
            "(commonly ~$45-90/hour with two-hour minimums plus travel). A "
            "minority thread is reimbursed: roughly a dozen-plus state Medicaid "
            "programs and CHIP cover interpretation as an optional/administrative "
            "benefit with federal match, but the dominant funding source is the "
            "hospital's own compliance budget. Because per-minute usage is "
            "uncapped, revenue scales directly with the client's LEP census — "
            "which is why enterprise health-system contracts are the prize."),
        key_players=(
            "A consolidated top with a long local tail. LanguageLine Solutions "
            "(owned by Teleperformance) is the dominant OPI platform; other "
            "scaled players include Cyracom, Propio Language Services, AMN "
            "Healthcare Language Services (which acquired Stratus Video), "
            "Certified Languages International, GLOBO, Voyce, Martti, and "
            "platform/marketplace layers such as Boostlingo and Jeenie. Beneath "
            "them sit hundreds of regional on-site interpreter agencies — the "
            "acquirable roll-up pool — and the hospital's own staff "
            "interpreters."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Over-the-phone interpreting (OPI)",
                    "largest by minutes — the commodity core",
                    "ILLUSTRATIVE · modeled modality mix; no published split"),
            Segment("Video remote interpreting (VRI)",
                    "fastest-growing — telehealth + ASL",
                    "ILLUSTRATIVE · modeled modality mix"),
            Segment("On-site / in-person interpreting",
                    "highest cost/hour — the local, sticky layer",
                    "ILLUSTRATIVE · modeled modality mix"),
            Segment("Document translation", "per-word adjacency",
                    "ILLUSTRATIVE · modeled adjacency"),
            Segment("US limited-English-proficient population", "~26M (~8% of "
                    "population), the demand base",
                    "GOV · US Census / ACS language-spoken-at-home"),
        ],
        growth_drivers=[
            "LEP population growth ~2-3%/yr — Census/ACS language trend",
            "ACA Section 1557 enforcement (2024 final rule) — qualified-"
            "interpreter + video-quality standards raise the compliance floor",
            "Telehealth normalization ~+2%/yr — native VRI/OPI demand",
            "Provider consolidation → enterprise MSAs concentrating spend",
            "AI/machine-translation substitution at the routine low end (drag "
            "on commodity OPI rate)",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Provider self-funded (Title VI / 1557 compliance opex)": 0.82,
            "Medicaid / CHIP administrative match (select states)": 0.13,
            "Grants / public health / other": 0.05,
        },
        rate_mechanics=[
            "OPI / VRI — metered per-minute pricing under an enterprise MSA; "
            "rate varies by language (common vs language-of-lesser-diffusion) "
            "and modality (VRI and ASL price above audio-only OPI).",
            "On-site — per-hour billing with a two-hour minimum plus travel/"
            "mileage; the scheduling fill-rate drives realized margin.",
            "Document translation — per-word, with rush and certification "
            "premiums.",
            "Medicaid/CHIP reimbursement — an optional benefit only a subset of "
            "states elect, drawn at the administrative federal match; NOT a "
            "national fee schedule.",
            "No Medicare or standard commercial fee schedule — the service is a "
            "provider compliance cost, so pricing is set by the B2B contract, "
            "not a payer rate sheet.",
        ],
        reimbursement_risk=(
            "The core risk is not a payer rate cut — it is that the customer "
            "funds this out of its own opex and is structurally motivated to "
            "minimize it. That drives constant RFP re-bidding, per-minute rate "
            "compression on commodity Spanish OPI, and vendor churn. The "
            "second-order risk is technology substitution: machine translation "
            "and AI voice are viable for routine, low-stakes exchanges, which "
            "erodes commodity OPI volume and price. The offsetting protection is "
            "regulatory — ACA Section 1557 limits reliance on machine "
            "translation and on unqualified staff or family members for "
            "consequential encounters, preserving demand for qualified human "
            "interpreters where the clinical and legal stakes are highest."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("Title VI of the Civil Rights Act (1964) + Executive Order "
                 "13166",
                 "Recipients of federal financial assistance (any provider "
                 "taking Medicare/Medicaid) must ensure meaningful access for "
                 "limited-English-proficient persons — the foundational "
                 "language-access mandate.",
                 "https://www.hhs.gov/civil-rights/for-individuals/special-topics/limited-english-proficiency/index.html"),
            Rule("ACA Section 1557 nondiscrimination rule (2024 final rule)",
                 "Requires qualified interpreters and translators, sets video "
                 "interpreting quality standards, and limits reliance on "
                 "machine translation and unqualified staff/family for "
                 "consequential communications — the single most important "
                 "demand-and-standard driver.",
                 "https://www.hhs.gov/civil-rights/for-individuals/section-1557/index.html"),
            Rule("Americans with Disabilities Act (Title III)",
                 "Requires effective communication for Deaf/Hard-of-Hearing "
                 "patients, including qualified ASL interpreters and VRI that "
                 "meets performance standards — the structurally scarce, "
                 "high-rate niche.",
                 "https://www.ada.gov/"),
            Rule("The Joint Commission + HHS CLAS standards",
                 "Accreditation and National CLAS (Culturally and "
                 "Linguistically Appropriate Services) standards operationalize "
                 "language access into survey-able hospital requirements.",
                 "https://thinkculturalhealth.hhs.gov/clas"),
            Rule("Medicaid/CHIP language-services federal match",
                 "States may elect to draw federal match for interpretation as "
                 "an administrative/optional benefit — the only meaningful "
                 "reimbursed thread, and it is state-by-state.",
                 None),
        ],
        policy_watch=[
            "Section 1557 (2024) implementation and litigation — the "
            "qualified-interpreter and video-quality standards",
            "State-level medical-interpreter certification / registry mandates",
            "Any expansion of Medicaid interpretation coverage to more states",
            "OCR enforcement posture on language-access complaints",
            "AI/machine-translation guidance — where regulators draw the "
            "human-required line",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "A barbell: a consolidated set of scaled national OPI/VRI platforms "
            "at the top, and hundreds of small, local on-site interpreter "
            "agencies in the tail. The remote-platform layer is concentrating "
            "fast around a handful of names; the on-site layer is the classic "
            "fragmented roll-up pool, tied to local interpreter rosters and "
            "health-system relationships."),
        hhi_or_share=(
            "No vendored facility file exists for this services vertical, so a "
            "computed HHI is honestly omitted. Qualitatively, OPI is the most "
            "concentrated modality (LanguageLine is the clear leader) while "
            "on-site remains highly fragmented and local."),
        consolidation=(
            "Active. Teleperformance's acquisition of LanguageLine and AMN's "
            "acquisition of Stratus Video signaled strategic and platform "
            "consolidation of the remote layer, while sponsors have "
            "recapitalized players such as Propio to fund tuck-in acquisitions "
            "of regional on-site agencies. The thesis is a scaled remote "
            "platform absorbing local on-site books and layering routing "
            "technology."),
        pe_activity=(
            "High and durable. The attributes PE likes are all here: mandated "
            "and recurring spend, uncapped per-minute usage that grows with the "
            "client, a fragmented on-site tail to consolidate, and technology "
            "(routing, VRI apps, AI-assisted QA) to expand margin. Quality-of-"
            "earnings centers on client concentration, contract renewal terms, "
            "the commodity-Spanish rate trajectory, and the durability of the "
            "on-site vs remote mix."),
        notable_players=[
            "LanguageLine Solutions (Teleperformance)", "Cyracom",
            "Propio Language Services", "AMN Language Services (Stratus Video)",
            "Certified Languages International", "GLOBO", "Voyce",
            "Martti", "Boostlingo (platform)", "Jeenie",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Interpreter utilization", "55-75%",
                "Paid contractor minutes as a share of available minutes — the "
                "core efficiency lever for OPI/VRI margin."),
            Kpi("Average speed of answer (ASA)", "<30 sec (OPI)",
                "Seconds to connect a live interpreter — the primary service-"
                "level term in enterprise contracts."),
            Kpi("Cost per minute (OPI/VRI)", "commodity vs LLD spread",
                "Common languages price near cost; languages of lesser "
                "diffusion and ASL carry the premium."),
            Kpi("On-site fill rate", "85-95%",
                "Filled vs requested on-site appointments — misses forfeit the "
                "minimum and damage the health-system relationship."),
            Kpi("Language mix (Spanish share)", "~60-70% of minutes",
                "Spanish is the commodity majority; margin concentrates in the "
                "long tail of rare languages."),
            Kpi("Net revenue retention / client concentration", "varies",
                "Enterprise MSAs are sticky but uncapped and re-bid; a top-"
                "client-heavy book is a concentration risk."),
            Kpi("EBITDA margin", "15-30%",
                "Higher for tech-enabled remote at scale; lower for on-site-"
                "heavy and Spanish-commodity-heavy books."),
        ],
        margin_profile=(
            "Interpretation margin is a labor-arbitrage-plus-technology story. "
            "OPI and VRI run largely on 1099 contractor interpreters paid "
            "per-minute, so gross margin turns on interpreter utilization, "
            "routing efficiency, and the language mix — a book weighted to rare "
            "languages and ASL out-earns a Spanish-commodity book. On-site is "
            "structurally lower-margin (scheduling gaps, travel, two-hour "
            "minimums) but stickier and harder to displace. Scale spreads the "
            "platform, dispatch, and QA cost across more minutes; the swing "
            "variables are the commodity-Spanish rate trend and how much of the "
            "routine low end AI eventually absorbs."),
    ),
    risks=[
        Risk("Non-reimbursed cost-center pricing pressure", "High",
             "The customer funds this from opex and minimizes it — perpetual "
             "RFP re-bids and per-minute rate compression on commodity volume."),
        Risk("AI / machine-translation substitution", "High",
             "Viable for routine low-stakes OPI; erodes commodity volume and "
             "price, though regulation protects the qualified-human high end."),
        Risk("Client concentration / contract churn", "Medium",
             "Enterprise MSAs are large but re-bid; loss of an anchor health "
             "system is a step-change to revenue."),
        Risk("Interpreter supply in rare languages / ASL", "Medium",
             "The margin languages are supply-constrained; scarcity is both the "
             "premium and the fulfillment risk."),
        Risk("Regulatory rollback / interpretation-standard change", "Low",
             "A future weakening of Section 1557 standards would soften the "
             "compliance floor that underpins demand."),
        Risk("Wage inflation for certified medical interpreters", "Medium",
             "Certification mandates raise interpreter pay and compress the "
             "arbitrage on which OPI/VRI margin depends."),
    ],
    diligence_questions=[
        "What is the revenue split across OPI, VRI, on-site, and translation, "
        "and how is each trending?",
        "What is the language mix, and how much revenue and margin sits in "
        "commodity Spanish vs languages of lesser diffusion and ASL?",
        "What is client concentration — top-5 and top-10 share — and what are "
        "the renewal terms and historical re-bid outcomes?",
        "What is the interpreter workforce model (1099 vs employee, onshore vs "
        "offshore) and its exposure to certification-mandate wage inflation?",
        "What is the realized commodity-OPI rate trend, and what is the AI/"
        "machine-translation exposure of the volume base?",
        "What are the contractual service levels (ASA, fill rate) and the "
        "penalty exposure for missing them?",
        "How much revenue is reimbursed (Medicaid/CHIP states) vs provider-"
        "funded, and how durable is each?",
        "What is the technology moat — routing, VRI app footprint, EHR "
        "integration — and how defensible is it against platform entrants?",
    ],
    insider_lens=[
        "It is a mandated cost the customer wants to shrink. That paradox is "
        "the whole business: demand is non-discretionary and grows with the LEP "
        "census, but the buyer's incentive is to cut the line item — so pricing "
        "power is weak on commodity volume and the RFP cycle never stops.",
        "Spanish is a loss-leader; the tail is the profit. Deep, cheap "
        "interpreter supply commoditizes Spanish, while rare languages and ASL "
        "carry scarce supply and premium rates. A book's language mix, not its "
        "total minutes, predicts its margin.",
        "AI is a scalpel, not a wrecking ball. It compresses routine OPI but "
        "Section 1557 requires qualified humans for consequential encounters — "
        "so AI hollows out the middle and pushes value toward the certified, "
        "high-stakes work. Underwrite the mix that survives automation.",
        "On-site is the moat, remote is the margin. The scalable dollars are in "
        "OPI/VRI, but the on-site relationship — local rosters, scheduled L&D "
        "and oncology encounters — is what makes a health system reluctant to "
        "switch. The best assets pair a scaled remote platform with a defensible "
        "on-site book.",
        "Usage is uncapped, so a single enterprise health-system win compounds "
        "as that system's LEP volume grows — but the same structure means a "
        "single loss is a cliff. Revenue durability is a contract-renewal "
        "question first and a demand question second.",
    ],
    connections=default_connections(
        "interpretation",
        deals_sector="interpretation",
        connectors=[
            ("census_acs_cbsa_profile",
             "Census ACS — language-spoken-at-home / LEP density by metro (the "
             "demand base)"),
            ("census_acs_county_profile",
             "Census ACS — county LEP and foreign-born share for market "
             "mapping"),
            ("bls_qcew_industry_area",
             "BLS QCEW — NAICS 541930 interpretation/translation employment & "
             "wages (labor cost + supply)"),
            ("oig_leie_exclusions",
             "OIG LEIE — excluded individuals/entities (integrity screen)"),
        ],
    ),
    sources=[
        Source("HHS Office for Civil Rights — Limited English Proficiency and "
               "Title VI guidance", "GOV",
               "https://www.hhs.gov/civil-rights/for-individuals/special-topics/limited-english-proficiency/index.html"),
        Source("HHS — ACA Section 1557 nondiscrimination final rule (2024)",
               "GOV",
               "https://www.hhs.gov/civil-rights/for-individuals/section-1557/index.html"),
        Source("US Census Bureau / American Community Survey — language spoken "
               "at home and English-speaking ability", "GOV",
               "https://www.census.gov/topics/population/language-use.html"),
        Source("National Council on Interpreting in Health Care (NCIHC) — "
               "standards of practice and workforce", "INDUSTRY",
               "https://www.ncihc.org/"),
        Source("Certification Commission for Healthcare Interpreters (CCHI) / "
               "National Board of Certification for Medical Interpreters",
               "INDUSTRY", "https://cchicertification.org/"),
        Source("PE Desk industry deep-dive + realized-deal corpus "
               "(interpretation / language services)", "INTERNAL",
               "/diligence/tam-sam?template=interpretation"),
    ],
    live_figures=live_figures_from_dive("interpretation"),
    trends=(
        "Language access moved from a back-office courtesy to a board-level "
        "compliance function over the last decade, and the market restructured "
        "around it. Over-the-phone interpreting scaled first and commoditized "
        "fastest; video remote interpreting then surged with telehealth and "
        "with ADA-driven ASL demand, becoming the growth modality. Consolidation "
        "followed the money: Teleperformance bought LanguageLine and AMN bought "
        "Stratus Video, while sponsors recapitalized platforms such as Propio to "
        "fund tuck-ins of the fragmented local on-site agencies. The 2024 ACA "
        "Section 1557 final rule reset the standard floor — qualified "
        "interpreters, video-quality requirements, and explicit limits on "
        "machine translation and family/staff interpreters for consequential "
        "encounters — which simultaneously raises demand for certified human "
        "interpreters and draws the line AI cannot cross. The trajectory from "
        "here: AI compresses commodity Spanish OPI on price and volume, while "
        "the premium migrates to rare languages, ASL/VRI, and the certified, "
        "high-stakes encounters the rule protects."),
    growth_levers=[
        GrowthLever(
            "LEP population growth",
            "The demand base — roughly 26M limited-English-proficient people, "
            "growing with immigration and demographic change — expands "
            "interpreted encounters across every care setting.",
            "+2-3%/yr", "GOV"),
        GrowthLever(
            "Section 1557 enforcement (2024 rule)",
            "Qualified-interpreter, video-quality, and machine-translation-"
            "limit standards raise the compliance floor and shift volume from "
            "unqualified staff/family to paid qualified interpreters.",
            "step-up in qualified demand", "GOV"),
        GrowthLever(
            "Telehealth-driven VRI adoption",
            "Virtual visits are natively remote-interpreted, pulling volume "
            "into the higher-rate VRI modality and normalizing on-screen "
            "interpreting.",
            "+2%/yr modality shift", "ILLUSTRATIVE"),
        GrowthLever(
            "Enterprise MSA consolidation",
            "As providers consolidate, language spend concentrates into scaled "
            "enterprise contracts, favoring platforms that can serve a whole "
            "system across modalities.",
            "share shift to scale", "ILLUSTRATIVE"),
        GrowthLever(
            "AI / machine-translation substitution",
            "Automation absorbs routine low-stakes OPI, compressing commodity "
            "volume and price even as it lifts value toward the certified "
            "high end.",
            "−rate on commodity OPI", "ILLUSTRATIVE"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Limited-English-proficient encounter volume × the 1557 "
               "qualified-interpreter mandate",
        analysis=(
            "The dominant demand driver is the number of clinical encounters "
            "involving a limited-English-proficient or Deaf/Hard-of-Hearing "
            "patient, multiplied by the share of those encounters that must now "
            "be served by a qualified interpreter rather than ad-hoc staff or "
            "family. The first term grows with the LEP population (~26M and "
            "rising per the Census/ACS) and with total healthcare utilization; "
            "the second term is a regulatory step-function — ACA Section 1557's "
            "2024 rule, ADA effective-communication requirements, and CLAS "
            "standards convert previously-informal interpreting into billable, "
            "qualified-interpreter demand. Telehealth amplifies both by routing "
            "encounters into VRI/OPI natively. The offsetting drag is AI "
            "substitution at the routine low end, which trims commodity minutes "
            "without touching the regulated, high-stakes core."),
        basis="GOV"),
    cost_drivers=[
        CostDriver(
            "Interpreter labor (per-minute contractors + on-site staff)",
            "~50-65% of cost",
            "The core cost — contractor minute-pay for OPI/VRI plus employed "
            "on-site interpreters. Utilization and language mix determine how "
            "much of it converts to margin.", "ILLUSTRATIVE"),
        CostDriver(
            "Technology & platform (routing, VRI apps, EHR integration)",
            "~10-20% of cost",
            "Dispatch/routing engines, the VRI application footprint, and "
            "integration into the health system's workflow — the scalable moat "
            "that spreads across minutes.", "ILLUSTRATIVE"),
        CostDriver(
            "On-site scheduling & travel inefficiency",
            "concentrated in on-site",
            "Two-hour minimums, fill-rate gaps, and mileage make the on-site "
            "modality structurally lower-margin than remote.", "ILLUSTRATIVE"),
        CostDriver(
            "Quality, certification & compliance",
            "~5-10% of cost",
            "Interpreter certification, QA/call monitoring, and the language-"
            "access reporting clients need for Title VI/1557 defense.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Sales, MSA management & implementation",
            "~10% of cost",
            "Enterprise sales cycles and health-system implementation are long "
            "and relationship-driven — a real cost of winning uncapped, sticky "
            "contracts.", "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "Interpretation is delivered remotely for OPI/VRI, so geography is not "
        "the structure read — demand tracks limited-English-proficient density "
        "rather than facility location. The meaningful geographic layer is LEP "
        "concentration (high-immigration metros in CA, TX, NY, FL, and the "
        "Southwest, plus specific refugee-resettlement corridors for languages "
        "of lesser diffusion), which the Census/ACS connectors below map "
        "directly. No national interpreter-agency roster is vendored, so a "
        "computed facility breakdown is honestly omitted."),
)

register(REPORT)
