"""Urology — the ancillary-dense, aging-workforce specialty roll-up.

Deals-only deep-dive (no national physician-practice facility file; geography is
omitted rather than fabricated). Urology is, with GI and dermatology, an
archetypal ancillary-rich PE specialty: the professional fee for the office
visit or the scope is a fraction of the economic footprint a urologist
generates. The real engine is the owned ancillary stack — image-guided
radiation therapy for prostate cancer (the "urorad" in-office arrangement),
in-house anatomic pathology reading the prostate biopsies, buy-and-bill
androgen-deprivation hormones, lithotripsy, and the ambulatory surgery center
for BPH and stone procedures. Layered on top is a genuine supply story: the
urology workforce is one of the oldest and scarcest in medicine against an
aging-male demand curve. The qualitative sections are authored around that
ancillary stack, the Stark in-office-ancillary-services exception that makes it
legal, and the self-referral scrutiny that follows it. Consumes
``urology_deep_dive()`` for SOURCED corpus deal figures where present.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="urology",
    name="Urology",
    care_setting="Physician services",
    naics="621111",
    one_line_def=(
        "Physician practices treating the male and female urinary tract and the "
        "male reproductive system — prostate cancer, benign prostatic "
        "hyperplasia (BPH), kidney stones, incontinence, and bladder/kidney "
        "cancer — where the economics live in the owned ancillaries (in-office "
        "radiation therapy for prostate cancer, anatomic pathology on the "
        "biopsies, buy-and-bill hormone therapy, lithotripsy, and an ASC) far "
        "more than in the professional fee for the visit or the scope."),
    tam_headline=TamHeadline(
        value=28.0, unit="$B", growth_pct=5.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "Modeled from the ~13,500 practicing US urologists (AUA workforce "
            "census) times the professional fee plus the ancillary stack — "
            "in-office radiation therapy, anatomic pathology, buy-and-bill "
            "androgen-deprivation drugs, lithotripsy, urodynamics, and ASC "
            "facility fees — not a single published figure. Growth is the "
            "modeled composite of aging-male demand (prostate cancer, BPH, "
            "stones), device/ASC migration, and drug mix, net of MPFS/site- "
            "neutral rate drag and self-referral scrutiny."),
    ),
    executive_summary=[
        "The visit is the least of it — urology is an ancillary machine. The "
        "professional fee for a cystoscopy or an office visit is small; the "
        "money is the owned stack around a prostate-cancer or BPH patient: "
        "image-guided radiation therapy, in-house pathology on the biopsy "
        "cores, buy-and-bill hormone therapy, lithotripsy, and the ASC.",
        "The 'urorad' in-office radiation arrangement is the signature — and "
        "the flashpoint. A urology group that owns an IMRT/IGRT vault for "
        "prostate cancer captures the largest ancillary in medicine, and the "
        "GAO documented that self-referring urologists order materially more "
        "radiation — making it the poster child of Stark in-office-ancillary "
        "scrutiny.",
        "Prostate biopsy pathology is a self-referral volume story too. A "
        "standard biopsy yields 12+ separately-billable specimen cores read "
        "in-house; the anti-markup rule and self-referral research bound how "
        "much of that anatomic-pathology margin the practice can keep.",
        "Workforce scarcity is a real, structural moat. Urology has one of the "
        "oldest physician age profiles and among the fewest residency slots per "
        "capita, so a large share of urologists is near retirement against a "
        "rising aging-male demand curve — access itself is the asset, and "
        "recruitment/retention is the whole integration risk.",
        "BPH is migrating to the office and ASC. Minimally-invasive devices "
        "(UroLift, Rezum, Aquablation, GreenLight) move prostate procedures out "
        "of the hospital OR into owned ambulatory settings — a facility-fee and "
        "device-capture growth lever distinct from the cancer economics.",
        "It is a maturing ancillary-driven roll-up (Solaris Health, US Urology "
        "Partners, United Urology, and the LUGPA large independent groups); the "
        "acquirable pool is the independent single-specialty group with an "
        "owned radiation vault, pathology lab, ASC, and drug-dispensing "
        "infrastructure that can be legally captured.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Referral for an elevated PSA, BPH/LUTS symptoms, stones, "
            "hematuria, or incontinence",
            "Office E&M visit + in-office diagnostics (uroflow, urodynamics, "
            "ultrasound, cystoscopy)",
            "Prostate biopsy — 12+ cores read by the in-house anatomic "
            "pathology lab",
            "Prostate-cancer treatment path — active surveillance, surgery, or "
            "owned in-office radiation therapy (IMRT/IGRT)",
            "Androgen-deprivation therapy — buy-and-bill hormone injections "
            "administered in-office",
            "BPH / stone procedures — UroLift/Rezum/Aquablation/lithotripsy in "
            "the office or owned ASC",
            "Charge capture, coding, and collections across professional + "
            "facility + drug + technical lines",
        ],
        sites_of_care=[
            "Physician office / clinic (E&M, cystoscopy, urodynamics, "
            "injections, in-office BPH devices)",
            "Owned ambulatory surgery center (stones, cystoscopic and prostate "
            "procedures) — facility-fee capture",
            "Owned/JV radiation-therapy vault (prostate IMRT/IGRT — the "
            "'urorad' arrangement)",
            "In-house anatomic pathology lab (prostate-biopsy reads)",
            "Mobile / partnership lithotripsy (ESWL for kidney stones)",
        ],
        money_flow=(
            "A urologist earns a professional fee off the Medicare Physician Fee "
            "Schedule for the office visit, cystoscopy, biopsy, and surgery — or "
            "a commercial multiple of it — but that professional fee is the "
            "smallest piece. A prostate-cancer patient can generate, inside a "
            "single group, the pathology technical/professional fees on 12+ "
            "biopsy cores, weeks of in-office image-guided radiation therapy at "
            "the freestanding radiation fee, and quarterly buy-and-bill "
            "androgen-deprivation injections at ASP-plus; a BPH or stone patient "
            "generates ASC facility fees and device capture. The Stark in-office "
            "ancillary-services exception is what makes the owned radiation "
            "vault, pathology lab, and drug dispensing legal within the group. "
            "In the PE structure the payer pays the physician-owned professional "
            "corporation, which pays the MSO a management fee for the ASC, "
            "radiation, lab, billing, and shared services. The single question "
            "that sets a urology platform's value is how much of that ancillary "
            "stack it legally owns — because the scope and the visit are the "
            "least of it."),
        key_players=(
            "PE-backed platforms lead the consolidation: Solaris Health (Lee "
            "Equity, the largest national platform), US Urology Partners (NMS "
            "Capital), United Urology Group / Chesapeake Urology, Genesis "
            "Healthcare Partners, Comprehensive Urologic Care, and Integrated "
            "Medical Professionals. LUGPA (the Large Urology Group Practice "
            "Association) is the trade home of the big independent single- "
            "specialty groups that pioneered the ancillary model and predate the "
            "PE wave. Device and pharma players — Teleflex (UroLift), Boston "
            "Scientific (Rezum/lithotripsy), Procept (Aquablation), and the "
            "prostate-cancer drug makers — sit upstream. The acquirable pool is "
            "the independent large urology group with a capturable ancillary "
            "stack."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Practicing US urologists", "~13,500",
                    "INDUSTRY · AUA annual workforce census (directional)"),
            Segment("New US prostate-cancer diagnoses / yr", "~300,000",
                    "GOV · NCI SEER / American Cancer Society (directional)"),
            Segment("US men age 50+ with BPH / lower-urinary-tract symptoms",
                    "~50%+ of men over 50",
                    "ACADEMIC · BPH epidemiology (directional)"),
            Segment("Ancillary share of a mature urology platform's revenue",
                    "~40-55% (radiation + pathology + drugs + ASC)",
                    "ILLUSTRATIVE · platform economics, directional"),
            Segment("US adults with a history of kidney stones",
                    "~11% of adults",
                    "GOV · NHANES stone-prevalence estimate (directional)"),
        ],
        growth_drivers=[
            "Aging-male demography — prostate cancer, BPH, and incontinence all "
            "rise steeply with age ~2-3%/yr",
            "BPH device migration to office/ASC (UroLift, Rezum, Aquablation) — "
            "facility-fee + device capture",
            "In-office radiation and drug ancillary capture (urorad + "
            "buy-and-bill ADT)",
            "Kidney-stone prevalence rising with obesity/diet — lithotripsy and "
            "stone-surgery volume",
            "MPFS / radiation / site-neutral rate drag + self-referral scrutiny "
            "— the structural offsets",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Medicare / MA": 0.50,
            "Commercial": 0.37,
            "Medicaid": 0.08,
            "Self-pay / other": 0.05,
        },
        rate_mechanics=[
            "MPFS professional fee for the E&M visit, cystoscopy (52000-series), "
            "prostate biopsy (55700), urodynamics, and surgery — RVUs × GPCI × "
            "the annual conversion factor, or a commercial multiple.",
            "In-office radiation therapy (IMRT/IGRT for prostate cancer) — the "
            "freestanding radiation-therapy technical + professional fees; the "
            "single largest ancillary and the 'urorad' self-referral flashpoint.",
            "Anatomic pathology on the prostate-biopsy cores — technical and "
            "professional components read in-house, constrained by the "
            "anti-markup rule and Stark self-referral limits (12+ billable "
            "specimens per biopsy).",
            "Buy-and-bill androgen-deprivation therapy (leuprolide/Lupron, "
            "Eligard, degarelix/Firmagon, triptorelin) — Part B ASP+6% injected "
            "in-office; generics/biosimilar leuprolide compress the spread.",
            "ASC facility fee (Medicare ASC Payment System) for stone and "
            "cystoscopic procedures, and device capture for in-office BPH "
            "therapies (UroLift, Rezum, Aquablation, GreenLight).",
            "Oral advanced-prostate-cancer drugs (enzalutamide/Xtandi, "
            "abiraterone, darolutamide/Nubeqa) run largely through Part D "
            "pharmacy — the practice captures coordination/dispensing, not "
            "buy-and-bill margin.",
        ],
        reimbursement_risk=(
            "The professional fee rides the same MPFS conversion-factor drift as "
            "every specialty, but urology's specific exposures are in the "
            "ancillary stack. In-office radiation therapy is the largest and "
            "most scrutinized: the GAO and MedPAC have documented self-referral "
            "overuse, and any narrowing of the Stark in-office-ancillary "
            "exception for radiation would reprice the model. Prostate-biopsy "
            "pathology faces the anti-markup rule and self-referral research. "
            "Buy-and-bill hormone economics decay as generic leuprolide erodes "
            "the ASP+6 spread. And site-neutral pressure narrows the "
            "hospital-outpatient-vs-ASC/office differential that makes owned "
            "facilities attractive. The healthiest urology platforms diversify "
            "the ancillary base — cancer radiation, pathology, drugs, ASC, and "
            "stones — so no single reimbursement change is existential."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("Physician self-referral law (Stark, 42 CFR 411.350+) — "
                 "in-office ancillary-services exception",
                 "The exception is what makes the owned radiation vault, "
                 "pathology lab, and in-office drug dispensing legal within a "
                 "group — the load-bearing legal structure of the whole "
                 "ancillary model.",
                 "https://www.cms.gov/medicare/regulations-guidance/physician-self-referral"),
            Rule("GAO / MedPAC 'urorad' self-referral findings",
                 "Documented that self-referring urology groups order "
                 "substantially more IMRT for prostate cancer — the evidentiary "
                 "basis for recurring proposals to curb in-office radiation "
                 "self-referral.",
                 "https://www.gao.gov/products/gao-13-525"),
            Rule("Medicare anti-markup rule (in-house pathology)",
                 "Limits what a group may bill Medicare for the technical/"
                 "professional components of diagnostic tests (e.g. "
                 "prostate-biopsy pathology) performed by an outside supplier — "
                 "bounds the pathology-ancillary margin.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
            Rule("Medicare Physician Fee Schedule + ASC Payment System "
                 "(annual Final Rules)",
                 "Set the professional fee, the radiation-therapy technical "
                 "fees, and the ASC facility fee — the rate base for every "
                 "urology revenue line.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
            Rule("Average Sales Price (ASP+6%) buy-and-bill methodology",
                 "Sets Part B reimbursement for in-office androgen-deprivation "
                 "injections; generic leuprolide competition compresses the "
                 "spread.",
                 "https://www.cms.gov/medicare/payment/part-b-drugs"),
            Rule("Anti-Kickback Statute (lithotripsy / radiation JVs)",
                 "Physician-owned lithotripsy and radiation joint ventures must "
                 "sit inside AKS safe harbors and be fair-market-value.",
                 "https://oig.hhs.gov/compliance/advisory-opinions/"),
        ],
        policy_watch=[
            "Recurring proposals to remove radiation therapy (and advanced "
            "imaging) from the Stark in-office-ancillary exception",
            "Generic/biosimilar leuprolide erosion of buy-and-bill ADT "
            "economics",
            "Site-neutral / HOPD-vs-ASC-vs-office facility-fee convergence",
            "Coverage and coding of new in-office BPH devices and prostate "
            "radioligand/focal therapies",
            "State PE-in-healthcare transaction-review laws + annual MPFS "
            "conversion-factor cuts",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "US urology remains fragmented across independent single-specialty "
            "groups, but it consolidated early into large regional 'mega-groups' "
            "under LUGPA precisely to build and share the ancillary stack, and a "
            "handful of PE platforms have since rolled those up nationally. The "
            "acquirable pool is the independent large urology group with an owned "
            "radiation, pathology, ASC, and drug-dispensing footprint."),
        hhi_or_share=(
            "No single owner is dominant nationally; concentration is regional "
            "and platform-specific. No vendored physician-practice roll captures "
            "operator concentration, so a national chain HHI is honestly omitted "
            "— the corpus deal history below is the real read."),
        consolidation=(
            "Urology followed GI and dermatology into PE roll-up, but on a "
            "foundation the specialty had already built: the LUGPA large-group "
            "movement had consolidated independents into ancillary-rich "
            "mega-groups years earlier. The PE model is specialty-specific "
            "buy-and-build — acquire an anchor group with a radiation vault, "
            "pathology lab, and ASC, tuck in independents, centralize the MSO, "
            "and re-rate on scale and ancillary capture."),
        pe_activity=(
            "An increasingly PE-active specialty — Solaris Health, US Urology "
            "Partners, United Urology, and others built multi-state footprints. "
            "Diligence centers on ancillary durability (radiation self-referral "
            "and ADT-spread risk), the scarcity and age of the urologist "
            "workforce, and recruitment/retention rather than pure visit-volume "
            "growth."),
        notable_players=[
            "Solaris Health (Lee Equity)", "US Urology Partners (NMS Capital)",
            "United Urology Group / Chesapeake Urology",
            "Genesis Healthcare Partners", "Comprehensive Urologic Care",
            "Integrated Medical Professionals",
            "LUGPA large independent groups (The Urology Group, MIU, etc.)",
            "Teleflex / Boston Scientific / Procept (upstream devices)",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Ancillary revenue (% of total)", "40-55%",
                "Radiation + pathology + buy-and-bill drugs + ASC + "
                "lithotripsy — the higher the capture, the more platform value "
                "beyond the visit."),
            Kpi("Radiation vault utilization", "fractions per day / on-treatment "
                "census",
                "The IMRT/IGRT vault is a high-fixed-cost asset; the prostate "
                "on-treatment census drives the largest ancillary's margin."),
            Kpi("Prostate-biopsy pathology volume", "12+ specimens / biopsy",
                "Each biopsy generates multiple billable anatomic-pathology "
                "specimens; the anti-markup rule caps the keepable margin."),
            Kpi("Buy-and-bill ADT revenue / patient", "generic-sensitive",
                "Quarterly hormone injections; the real margin is the ASP+6 "
                "spread, eroded by generic leuprolide."),
            Kpi("ASC / in-office BPH procedure mix", "device-dependent",
                "UroLift/Rezum/Aquablation and stone cases move volume into "
                "owned facilities at facility-fee capture."),
            Kpi("Platform EBITDA margin (post-MSO)", "18-25% (illustrative)",
                "Ancillary-rich urology runs at the higher end of "
                "physician-services margins when the stack is fully captured."),
        ],
        margin_profile=(
            "Urology economics are dominated by physician compensation like any "
            "specialty, but the differentiator is the breadth of the ancillary "
            "stack, and its concentration in oncology care: a group that owns "
            "its radiation vault, reads its own biopsies, buys-and-bills its "
            "hormone therapy, runs an ASC, and does lithotripsy earns multiple "
            "margin streams off the same prostate-cancer, BPH, or stone patient "
            "the professional fee barely covers. The radiation vault is a "
            "high-fixed-cost chassis, so its margin steps up sharply with the "
            "on-treatment census; pathology and ADT add capture bounded by the "
            "anti-markup rule and generic erosion; and the ASC and in-office BPH "
            "devices add facility-fee and device capture. All of it lives on the "
            "Stark in-office ancillary exception, and workforce scarcity both "
            "protects pricing and constrains growth. Scale spreads the MSO and "
            "strengthens payer leverage, but the underlying quality of a urology "
            "platform is how much of the ancillary stack it legally owns and how "
            "durably it can staff it."),
    ),
    risks=[
        Risk("Radiation self-referral (Stark in-office-ancillary) reform",
             "High",
             "In-office IMRT/IGRT is the largest ancillary and the most "
             "scrutinized; removing radiation from the Stark exception would "
             "reprice the model."),
        Risk("Urologist recruitment / retention in a scarce, aging workforce",
             "High",
             "The selling urologists are the EBITDA and the access moat; an "
             "aging workforce and few trainees make retention the core "
             "integration risk."),
        Risk("Generic leuprolide erosion of buy-and-bill ADT", "Medium",
             "Generic and biosimilar competition thins the ASP+6 spread on "
             "in-office hormone therapy."),
        Risk("Pathology self-referral / anti-markup exposure", "Medium",
             "In-house prostate-biopsy pathology volume draws anti-markup and "
             "self-referral scrutiny that bounds the keepable margin."),
        Risk("Site-neutral / facility-fee convergence", "Medium",
             "Narrowing the HOPD-vs-ASC/office differential compresses the "
             "owned-facility and radiation-vault thesis."),
        Risk("MPFS conversion-factor erosion", "Medium",
             "A structural, no-inflation-update squeeze on the professional fee "
             "for visits, cystoscopy, biopsy, and surgery."),
        Risk("Multiple compression on exit", "Medium",
             "Entry multiples rose across the cycle in a maturing, "
             "ancillary-heavy roll-up."),
    ],
    diligence_questions=[
        "What share of EBITDA is ancillary (radiation, pathology, buy-and-bill "
        "drugs, ASC, lithotripsy), and how is each captured and structured?",
        "Is the in-office radiation ('urorad') arrangement clean under Stark, "
        "and how exposed is it to a change in the in-office-ancillary exception?",
        "What is the prostate-biopsy pathology model, and is it compliant with "
        "the anti-markup rule and self-referral limits?",
        "What is the buy-and-bill ADT revenue, and what is the generic-leuprolide "
        "exposure to the ASP+6 spread over the hold?",
        "What is the age distribution of the urologist roster, and what is the "
        "recruitment pipeline and retention track record?",
        "What is the ASC and in-office BPH-device utilization, and how much "
        "de novo or migration capacity remains?",
        "What is the payer mix and commercial-rate position, and how durable "
        "are the top commercial and radiation contracts?",
        "What is the post-close physician compensation model, and how much "
        "projected EBITDA depends on the comp haircut versus organic growth?",
    ],
    insider_lens=[
        "The visit is the least of it. A urologist's professional fee for a "
        "cystoscopy or an office visit is small; the radiation vault, the "
        "in-house pathology, the buy-and-bill hormones, the lithotripsy, and "
        "the ASC are the business. Urology value is a question of how much of "
        "that ancillary stack the platform legally owns.",
        "'Urorad' is the crown jewel and the liability at once. Owning the "
        "prostate-cancer radiation vault captures the single largest ancillary "
        "in medicine — and the GAO showed self-referring urologists order more "
        "of it, which is exactly why removing radiation from the Stark "
        "in-office exception is a recurring policy threat. Diligence the "
        "arrangement, not just the margin.",
        "A prostate biopsy is a dozen pathology bills. The standard 12-core "
        "biopsy generates 12+ separately-billable anatomic-pathology specimens "
        "read in-house; it is a real volume stream, but the anti-markup rule "
        "and self-referral research bound how much of it the group can keep.",
        "The workforce scarcity is the moat and the trap. Urology has one of "
        "the oldest age profiles and fewest trainees in medicine — so access is "
        "the asset (a supply-constrained specialty against aging-male demand), "
        "but a retiring roster and a thin pipeline make recruitment and "
        "retention the entire integration risk.",
        "Lupron isn't what it was. Buy-and-bill androgen-deprivation therapy "
        "was a legacy profit center; generic leuprolide has thinned the ASP+6 "
        "spread — underwrite the spread durability, not the gross injection "
        "line, and note the new oral prostate-cancer drugs mostly run through "
        "Part D pharmacy, not buy-and-bill.",
        "BPH is quietly leaving the OR. UroLift, Rezum, Aquablation, and "
        "GreenLight move prostate procedures into the office and owned ASC — a "
        "facility-fee and device-capture growth lever separate from the cancer "
        "economics, and a hedge if radiation self-referral is curbed.",
    ],
    connections=default_connections(
        "urology",
        deals_sector="urology",
        extra_pages=[
            ("/industry/urology",
             "Industry deep-dive — urology deal history + ancillary-stack read"),
        ],
        connectors=[
            ("npi_provider_taxonomy",
             "NPI taxonomy — urology specialty mix & practice enrollment"),
            ("cms_open_data_mup_physician_by_provider_service",
             "Medicare physician utilization — cystoscopy/biopsy/radiation "
             "volume & allowed charges"),
            ("cms_open_data_part_b_spending_by_drug",
             "Medicare Part B drug spending — buy-and-bill ADT (leuprolide) "
             "read"),
            ("provider_data_asc_quality_facility",
             "CMS ASC quality file — urology surgery-center footprint & "
             "quality"),
            ("open_payments_general_payments_2024",
             "Open Payments — device/pharma payments to urologists (relationship "
             "screen)"),
            ("census_acs_cbsa_profile",
             "Census ACS — CBSA age (men 50+) demographics for demand mapping"),
        ],
    ),
    sources=[
        Source("American Urological Association — annual Urology Workforce & "
               "Practice Characteristics Census", "INDUSTRY",
               "https://www.auanet.org/research/aua-census"),
        Source("US GAO — Higher Use of Advanced Imaging Services / IMRT by "
               "self-referring providers (GAO-13-525 and related)", "GOV",
               "https://www.gao.gov/products/gao-13-525"),
        Source("CMS — Medicare Physician Fee Schedule and ASC Payment System "
               "annual Final Rules (RVUs, radiation, ASC facility fee)", "GOV",
               "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
        Source("Physician self-referral law (Stark, 42 CFR 411.350+) — "
               "in-office ancillary-services exception", "GOV",
               "https://www.cms.gov/medicare/regulations-guidance/physician-self-referral"),
        Source("NCI SEER / American Cancer Society — prostate-cancer incidence; "
               "NHANES — kidney-stone prevalence", "GOV",
               "https://seer.cancer.gov/statfacts/html/prost.html"),
        Source("PE Desk industry deep-dive (urology) + realized-deal corpus",
               "INTERNAL",
               "/diligence/tam-sam?template=urology"),
    ],
    live_figures=live_figures_from_dive("urology"),
    trends=(
        "Urology consolidated in two waves. First, the LUGPA large-group "
        "movement pulled independents into ancillary-rich regional mega-groups "
        "built around owned radiation, pathology, ASCs, and drug dispensing. "
        "Then PE rolled those mega-groups up nationally — Solaris Health, US "
        "Urology Partners, United Urology — for the same reason as GI and "
        "dermatology: the professional fee is a fraction of the economic "
        "footprint a urologist generates. Two structural facts frame the "
        "trajectory. First, demand is a demographic near-certainty: prostate "
        "cancer, BPH, incontinence, and stones all climb with an aging male "
        "population, and the urology workforce is one of the oldest and "
        "scarcest in medicine — access is itself an asset. Second, the ancillary "
        "engine is under a slow policy squeeze: the GAO documented "
        "radiation-self-referral overuse and there are recurring proposals to "
        "pull radiation (and imaging) out of the Stark in-office exception, "
        "generic leuprolide has thinned the buy-and-bill hormone spread, and "
        "site-neutral pressure narrows the facility-fee differentials. The "
        "offsetting growth is BPH's migration to office/ASC devices and new "
        "prostate-cancer therapeutics. Quality-of-earnings work now centers on "
        "ancillary durability, self-referral exposure, and urologist retention, "
        "not visit count."),
    growth_levers=[
        GrowthLever(
            "In-office radiation ('urorad') capture",
            "Own the prostate-cancer IMRT/IGRT vault — the single largest "
            "ancillary — inside the Stark in-office exception.",
            "primary / self-referral-gated", "ILLUSTRATIVE"),
        GrowthLever(
            "BPH device migration to office/ASC",
            "Move UroLift/Rezum/Aquablation/GreenLight procedures into owned "
            "ambulatory settings for facility-fee and device capture.",
            "+ facility-fee capture", "ILLUSTRATIVE"),
        GrowthLever(
            "Aging-male demand",
            "Prostate cancer, BPH, incontinence, and stones all rise steeply "
            "with age against a scarce workforce.",
            "+ steady volume", "GOV"),
        GrowthLever(
            "Pathology + buy-and-bill drug capture",
            "In-house prostate-biopsy pathology and in-office ADT injections "
            "add margin streams off the same patient.",
            "+ ancillary margin", "ILLUSTRATIVE"),
        GrowthLever(
            "Consolidation multiple arbitrage + comp haircut",
            "Acquire independent groups at lower multiples, centralize the MSO, "
            "and re-rate on scale and ancillary capture.",
            "primary / retention-gated", "ILLUSTRATIVE"),
        GrowthLever(
            "MPFS / radiation / site-neutral rate drag + self-referral "
            "scrutiny",
            "A flat-to-declining professional fee, radiation self-referral "
            "reform risk, and generic ADT erosion are the structural headwind.",
            "rate + policy headwind", "GOV"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Aging-male urologic burden (prostate cancer + BPH + stones)",
        analysis=(
            "The dominant demand driver is the aging of the male population into "
            "the urologic-disease window. Prostate cancer — roughly 300,000 new "
            "US diagnoses a year — is overwhelmingly a disease of older men and "
            "drives the biopsy, pathology, radiation, and hormone-therapy "
            "ancillaries; benign prostatic hyperplasia affects a majority of men "
            "over 50 and drives the office, device, and ASC volume; kidney "
            "stones (a history in ~11% of adults, rising with obesity and diet) "
            "drive lithotripsy and stone surgery; and incontinence and bladder "
            "cancer add further age-linked demand. Uniquely, this demand meets a "
            "supply constraint: urology has among the oldest physician age "
            "profiles and fewest trainees per capita, so access itself is scarce "
            "— a demographic tailwind against a shrinking-supply backdrop. The "
            "genuine offsets are policy (radiation self-referral reform, generic "
            "ADT erosion, site-neutral pressure), not demand."),
        basis="GOV"),
    cost_drivers=[
        CostDriver(
            "Physician & advanced-practice compensation", "~40-50% of cost",
            "The dominant cost; the post-close comp model is the biggest margin "
            "lever and the biggest retention risk in a scarce workforce.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Buy-and-bill drug COGS (androgen-deprivation therapy)",
            "variable / large gross",
            "The cost side of the ADT ancillary — hormone acquisition where "
            "generic leuprolide compresses the ASP+6 spread.", "ILLUSTRATIVE"),
        CostDriver(
            "Radiation-vault + ASC operations", "~12-18% of cost",
            "Radiation therapists, physicists, and the capital/service cost of "
            "the IMRT/IGRT vault plus the ASC clinical staff — the fixed "
            "chassis the facility fees cover.", "ILLUSTRATIVE"),
        CostDriver(
            "MSO back office (billing/RCM, compliance)", "~10-15% of cost",
            "The shared-services and compliance apparatus the ancillary-heavy, "
            "self-referral-sensitive structure requires.", "ILLUSTRATIVE"),
        CostDriver(
            "Pathology + facility/occupancy + devices", "~8-12% of cost",
            "In-house lab reagents, the clinic/ASC real estate and equipment, "
            "and in-office BPH device supply.", "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "No national physician-practice facility file is vendored — a urology "
        "group is a business, not a Medicare-certified facility — so state "
        "geography is omitted rather than fabricated. The most consequential "
        "geographic variables are the corporate-practice-of-medicine doctrine "
        "(strong-CPOM states force the friendly-PC/MSO structure), state "
        "radiation-therapy and ASC licensure/certificate-of-need regimes that "
        "gate where an owned vault or surgery center can open, and the growing "
        "list of states enacting PE-in-healthcare transaction-review laws. The "
        "NPI-taxonomy, Medicare physician-utilization, Part B drug-spending, and "
        "demographic connectors linked below map urology supply and "
        "ancillary/drug volume against the aging-male population — the honest "
        "footprint read."),
)

register(REPORT)
