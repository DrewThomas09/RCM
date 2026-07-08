"""ENT & Allergy — the otolaryngology + allergy/immunology ancillary roll-up.

Deals-only deep-dive (no national physician-practice facility file; ENT/allergy
workforce data is aggregate-only, so geography is omitted rather than
fabricated). ENT & Allergy is a combined specialty platform whose economics live
far more in the owned ancillary stack than in the professional fee: allergy
immunotherapy antigen preparation, audiology and hearing-aid dispensing, in-
office sinus CT, balloon sinuplasty migrated to the office, and severe-disease
biologics. The qualitative sections are authored around that ancillary stack,
the 2022 FDA over-the-counter hearing-aid rule that repriced the audiology
margin, and the site-of-service migration of sinus procedures. Consumes
``ent_allergy_deep_dive()`` for SOURCED corpus deal figures.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="ent_allergy",
    name="ENT & Allergy",
    care_setting="Physician services",
    naics="621111",
    one_line_def=(
        "Combined otolaryngology (ear, nose & throat) and allergy/immunology "
        "physician practices — sinus, otology, head & neck, laryngology, sleep, "
        "and allergic disease — where the platform economics live in the owned "
        "ancillaries (allergy immunotherapy antigen prep, audiology and "
        "hearing-aid dispensing, in-office sinus CT, office-based sinus "
        "procedures, and biologics) more than in the surgeon's professional fee."),
    tam_headline=TamHeadline(
        value=24.0, unit="$B", growth_pct=5.5, basis_label="ILLUSTRATIVE",
        basis_note=(
            "Modeled from the ~9,000-9,500 practicing US otolaryngologists and "
            "~4,500 allergist/immunologists (AAO-HNS / AAAAI workforce, "
            "directional) times the professional fee plus the ancillary stack "
            "(allergy immunotherapy, audiology/hearing aids, in-office CT, "
            "office-based sinus surgery, sleep, and severe-disease biologics) — "
            "not a single published figure. Growth is the modeled composite of "
            "aging/chronic-sinusitis demand, in-office site-of-service "
            "migration, and biologic adoption, net of MPFS rate drag and the "
            "OTC hearing-aid margin hit."),
    ),
    executive_summary=[
        "ENT & Allergy is an ancillary business wearing a surgical coat. The "
        "professional fee for the sinus scope or the tube placement is the "
        "smallest piece; the money is allergy immunotherapy antigen prep, "
        "audiology and hearing-aid dispensing, in-office sinus CT, office-based "
        "balloon sinuplasty, and severe-disease biologics.",
        "Allergy immunotherapy is the quiet annuity. The antigen-preparation "
        "code (CPT 95165, billed per dose) is a recurring, high-margin ancillary "
        "that turns an allergic-rhinitis patient into a multi-year revenue "
        "stream — and it is the reason allergy sits inside the ENT platform.",
        "The 2022 FDA over-the-counter hearing-aid rule is a structural repricing "
        "of the audiology ancillary. Retail cash-pay hearing-aid dispensing was a "
        "high-margin pillar; OTC devices and payer/retail channels compress it — "
        "underwrite audiology margin durability, not the historical run-rate.",
        "Sinus procedures are migrating to the office. Balloon sinuplasty and "
        "in-office CT let ENTs capture a facility-style economic that used to "
        "live in the hospital or ASC — a genuine growth lever, but exposed to "
        "site-of-service and medical-necessity repricing.",
        "Consolidation is real but younger than dermatology or GI. Platforms "
        "like ENT & Allergy Associates, SENTA Partners, and Allergy Partners "
        "built regional density; the acquirable pool is the independent single- "
        "or combined-specialty group with a capturable ancillary stack.",
        "Demand is chronic and demographic: allergic rhinitis and chronic "
        "rhinosinusitis in ~1 in 8 adults, pediatric otitis media (tympanostomy "
        "tubes are among the most common child surgeries), and age-related "
        "hearing loss — non-discretionary, recurring, and aging-weighted.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Referral / self-referral (PCP, allergist, or direct) for sinus, "
            "ear, throat, sleep, or allergic complaints",
            "Office E&M visit + diagnostics (nasal endoscopy, audiometry, "
            "allergy skin/serum testing, in-office sinus CT)",
            "Allergy pathway — immunotherapy antigen prep (95165) + injection "
            "administration, or biologic referral for severe disease",
            "Procedural pathway — office-based balloon sinuplasty / tubes, or "
            "ASC/hospital functional endoscopic sinus surgery (FESS)",
            "Audiology — hearing evaluation and hearing-aid dispensing (largely "
            "cash-pay retail)",
            "Sleep pathway — home sleep testing and hypoglossal-nerve-stimulator "
            "(Inspire) implant for obstructive sleep apnea",
            "Charge capture, coding, and collections across the professional fee "
            "and the ancillary stack",
        ],
        sites_of_care=[
            "Physician office / clinic (E&M, endoscopy, allergy testing, "
            "in-office procedures)",
            "In-office allergy immunotherapy suite (antigen prep + shots)",
            "In-office audiology booth + hearing-aid dispensing",
            "In-office / point-of-care sinus CT (cone-beam)",
            "Owned or JV ambulatory surgery center (FESS, tonsillectomy, ear "
            "surgery)",
            "Hospital outpatient department (higher-acuity head & neck, oncology)",
        ],
        money_flow=(
            "An otolaryngologist or allergist earns a professional fee off the "
            "Medicare Physician Fee Schedule for the office visit, the nasal "
            "endoscopy, the allergy test, or the procedure — or a commercial "
            "multiple of it. But the durable economics are the ancillaries "
            "layered on the same patient. Allergy immunotherapy bills the "
            "antigen-preparation code (95165) per dose plus an injection "
            "administration fee, generating recurring revenue across a multi-year "
            "desensitization course. Audiology dispenses hearing aids largely "
            "cash-pay at retail margin. In-office sinus CT captures an imaging "
            "technical component. Balloon sinuplasty performed in the office "
            "captures a facility-style differential. Severe chronic-rhinosinusitis "
            "and asthma biologics (dupilumab, omalizumab, mepolizumab) run mostly "
            "through the pharmacy benefit, with a smaller in-office buy-and-bill "
            "slice. In the PE structure the payer pays the physician-owned "
            "professional corporation, which pays the MSO a management fee for the "
            "immunotherapy lab, audiology, imaging, billing, and shared services — "
            "so platform value is a function of how much of that stack it owns."),
        key_players=(
            "PE-backed platforms lead a still-consolidating market: ENT & Allergy "
            "Associates (the large New York/New Jersey combined-specialty group), "
            "SENTA Partners, Allied ENT Partners, Spire ENT, and US ENT Partners "
            "on the otolaryngology side, with Allergy Partners the marquee "
            "allergy-only platform. Device and pharma players shape the "
            "ancillaries — Inspire Medical Systems (hypoglossal-nerve stimulation "
            "for sleep apnea), the balloon-sinuplasty device makers, and the "
            "biologic manufacturers (Sanofi/Regeneron's dupilumab, Genentech's "
            "omalizumab). Large independent single-specialty ENT and allergy "
            "groups anchor most metros and are the acquirable pool."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Practicing US otolaryngologists", "~9,000-9,500",
                    "INDUSTRY · AAO-HNS workforce (directional)"),
            Segment("Practicing US allergist/immunologists", "~4,500",
                    "INDUSTRY · AAAAI workforce (directional)"),
            Segment("Adults with allergic rhinitis", "~19-30% of adults",
                    "GOV · CDC / NHANES allergic-rhinitis prevalence"),
            Segment("Adults with chronic rhinosinusitis", "~11-12% of adults",
                    "GOV · CDC chronic-sinusitis prevalence"),
            Segment("Pediatric tympanostomy-tube procedures / yr",
                    "~500,000-700,000",
                    "ACADEMIC · AAO-HNS clinical guideline (directional)"),
            Segment("Ancillary share of a mature ENT/allergy platform's revenue",
                    "~35-55% (immunotherapy + audiology + imaging + procedures)",
                    "ILLUSTRATIVE · platform economics, directional"),
        ],
        growth_drivers=[
            "Aging + chronic allergic/sinus disease prevalence ~2-3%/yr",
            "Allergy immunotherapy penetration + recurring antigen-prep annuity",
            "In-office site-of-service migration (balloon sinuplasty, CT, tubes)",
            "Severe-disease biologics (CRSwNP, asthma) expanding the drug line",
            "Sleep apnea device adoption (Inspire hypoglossal-nerve stimulation)",
            "OTC hearing-aid disruption + MPFS rate drag — the offsetting headwinds",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Commercial": 0.50,
            "Medicare / MA": 0.34,
            "Medicaid": 0.10,
            "Self-pay / cash (audiology, cosmetic)": 0.06,
        },
        rate_mechanics=[
            "MPFS professional fee for E&M and ENT procedures (nasal endoscopy "
            "31231, FESS 31255+, tympanostomy 69436, tonsillectomy 42820+) — "
            "RVUs × GPCI × the annual conversion factor, or a commercial multiple.",
            "Allergy immunotherapy — antigen preparation billed per dose (CPT "
            "95165, capped by Medicare at 10 doses per multi-dose vial) plus "
            "injection administration (95115 single / 95117 multiple); the "
            "antigen-prep code is the recurring high-margin engine.",
            "Allergy testing — percutaneous/intradermal skin tests (95004, "
            "95024) and specific-IgE serum panels, billed per test/antigen.",
            "In-office imaging — sinus CT technical + professional components, "
            "governed by the Stark in-office ancillary-services exception and the "
            "imaging appropriate-use / accreditation requirements.",
            "Audiology — diagnostic audiometry on the MPFS, but hearing-aid "
            "dispensing is largely cash-pay retail (Medicare does not cover "
            "hearing aids), so audiology margin is a retail, not a reimbursed, "
            "economic.",
            "Severe-disease biologics (dupilumab, omalizumab, mepolizumab) — "
            "predominantly pharmacy-benefit / specialty-pharmacy, with a smaller "
            "Part B in-office buy-and-bill slice at ASP-plus.",
        ],
        reimbursement_risk=(
            "The professional fee for the visit and the scope is under the same "
            "MPFS conversion-factor drift that squeezes every specialty, but the "
            "ENT/allergy exposures are in the ancillary stack. The 2022 FDA "
            "over-the-counter hearing-aid rule structurally reprices the "
            "audiology dispensing margin as OTC devices and payer/retail channels "
            "erode the cash-pay premium. Office-based balloon sinuplasty faces "
            "site-of-service and medical-necessity scrutiny (payers periodically "
            "challenge coverage of in-office sinus procedures). The allergy "
            "immunotherapy antigen-prep code has an audit history around the "
            "definition of a billable dose and the vial cap. And biologics are "
            "migrating spend to the pharmacy benefit, thinning the in-office drug "
            "ancillary. The healthiest platforms diversify the ancillary base so "
            "no single change is existential."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("FDA Over-the-Counter Hearing Aid rule (2022)",
                 "Created an OTC category for mild-to-moderate hearing loss, "
                 "effective October 2022 — a structural repricing of the "
                 "prescription/audiology hearing-aid dispensing margin that has "
                 "been an ENT platform pillar.",
                 "https://www.fda.gov/medical-devices/hearing-aids/otc-hearing-aids-what-you-should-know"),
            Rule("Medicare Physician Fee Schedule (annual Final Rule)",
                 "Sets the RVUs and conversion factor for the E&M visit, allergy "
                 "testing, immunotherapy administration, and ENT procedures.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
            Rule("Physician self-referral law (Stark, 42 CFR 411.350+)",
                 "The in-office ancillary-services exception is what makes the "
                 "owned allergy immunotherapy lab, in-office sinus CT, and "
                 "audiology captures legal.",
                 "https://www.cms.gov/medicare/regulations-guidance/physician-self-referral"),
            Rule("Allergen immunotherapy billing (CPT 95165 dose definition)",
                 "Medicare caps antigen-prep billing at 10 doses per multi-dose "
                 "vial and defines a billable dose; the code has a documented "
                 "audit and overpayment history.",
                 "https://www.cms.gov/medicare-coverage-database/"),
            Rule("Medicare ASC / OPPS Payment System (annual Final Rule)",
                 "Sets the facility fee for FESS, tonsillectomy, and ear surgery "
                 "performed in an owned or JV ambulatory surgery center, and the "
                 "in-office-vs-facility differential for sinus procedures.",
                 "https://www.cms.gov/medicare/payment/prospective-payment-systems/ambulatory-surgical-center-asc"),
            Rule("Anti-Kickback Statute + corporate practice of medicine",
                 "Governs MSO / friendly-PC structures, device-company and "
                 "biologic relationships, and referral arrangements in the "
                 "combined ENT/allergy platform.",
                 "https://oig.hhs.gov/compliance/advisory-opinions/"),
        ],
        policy_watch=[
            "OTC hearing-aid adoption curve and payer/retail channel encroachment "
            "on audiology dispensing margin",
            "Payer coverage / medical-necessity policies for office-based balloon "
            "sinuplasty and in-office CT",
            "Biologic (CRSwNP / asthma) coverage, prior-auth, and pharmacy-vs- "
            "Part B channel mix",
            "Annual MPFS conversion-factor cuts and the perennial 'doc fix'",
            "State PE-in-healthcare transaction-review and CPOM enforcement",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "US ENT and allergy remain highly fragmented across independent "
            "single- and combined-specialty groups. Consolidation is real but "
            "younger and less complete than dermatology or gastroenterology — a "
            "set of regional PE platforms has built density in specific metros "
            "rather than a national chain. The acquirable pool is the independent "
            "ENT or allergy group with a capturable ancillary stack "
            "(immunotherapy, audiology, imaging, and an ASC relationship)."),
        hhi_or_share=(
            "No single owner is dominant nationally; concentration is regional "
            "and platform-specific. No vendored physician-practice roll captures "
            "operator concentration, so a national chain HHI is honestly omitted "
            "— the corpus deal history below is the real read."),
        consolidation=(
            "The model is specialty buy-and-build: acquire an anchor combined "
            "ENT/allergy group, tuck in independents, centralize the MSO back "
            "office, and deepen the ancillary stack (immunotherapy lab, "
            "audiology, in-office CT, ASC). The combined ENT + allergy structure "
            "is deliberate — allergy supplies the recurring immunotherapy annuity "
            "that smooths the surgical revenue. Platforms are on their first or "
            "second sponsor; the sector is earlier in the roll-up cycle than the "
            "first-wave specialties."),
        pe_activity=(
            "An active but less-saturated specialty roll-up: ENT & Allergy "
            "Associates, SENTA Partners, Allied ENT Partners, Spire ENT, US ENT "
            "Partners, and the allergy-focused Allergy Partners built regional "
            "platforms. Diligence centers on ancillary durability (the OTC "
            "hearing-aid hit to audiology, biologic channel shift, and "
            "site-of-service risk on office sinus procedures) and physician "
            "retention rather than pure visit growth."),
        notable_players=[
            "ENT & Allergy Associates", "SENTA Partners", "Allergy Partners",
            "Allied ENT Partners", "Spire ENT", "US ENT Partners",
            "Inspire Medical Systems (sleep-apnea device — adjacent)",
            "Sanofi / Regeneron (dupilumab — biologic driver)",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Ancillary revenue (% of total)", "35-55%",
                "Allergy immunotherapy + audiology + in-office CT + office "
                "procedures — the higher the capture, the more platform value "
                "beyond the professional fee."),
            Kpi("Allergy immunotherapy patients on maintenance",
                "practice-dependent",
                "The recurring antigen-prep annuity; a large, stable "
                "immunotherapy census is the smoothest revenue in the platform."),
            Kpi("Hearing aids dispensed / audiologist / yr", "cash-pay retail",
                "The audiology margin engine — now pressured by the OTC hearing- "
                "aid rule, so the trend matters more than the level."),
            Kpi("Office vs facility procedure mix",
                "balloon sinuplasty / tubes in-office",
                "In-office sinus procedures capture a facility-style differential "
                "but carry site-of-service and medical-necessity exposure."),
            Kpi("Visits / provider (with APP leverage)", "physician + APP",
                "Advanced-practice-provider leverage extends physician capacity "
                "across the E&M and allergy-injection base."),
            Kpi("Platform EBITDA margin (post-MSO)", "15-22% (illustrative)",
                "Ancillary-rich ENT/allergy runs in the mid-teens-to-low-20s of "
                "physician-services margins."),
        ],
        margin_profile=(
            "ENT/allergy economics are dominated by physician and clinical-staff "
            "compensation like any specialty, but the differentiator is the "
            "recurring, capturable ancillary base. Allergy immunotherapy is the "
            "steadiest: an antigen-prep annuity that runs for years per patient "
            "on a largely fixed lab cost. Audiology has been a high-margin cash "
            "retail line, now repriced by OTC devices. In-office CT and "
            "office-based sinus procedures capture facility-style economics on a "
            "fixed equipment chassis, so margin steps up with utilization. "
            "Biologics are large gross revenue but thin real margin and are "
            "migrating to the pharmacy benefit. Scale spreads the MSO back office "
            "and strengthens payer leverage, but the underlying quality of an "
            "ENT/allergy platform is the durability and diversity of its "
            "ancillary stack."),
    ),
    risks=[
        Risk("OTC hearing-aid repricing of the audiology ancillary", "High",
             "The 2022 FDA rule and payer/retail channels erode the cash-pay "
             "hearing-aid dispensing margin that has been a platform pillar."),
        Risk("Physician retention / comp-haircut backlash", "High",
             "Selling otolaryngologists and allergists are the EBITDA; a botched "
             "post-close compensation redesign drives defection and volume loss."),
        Risk("Site-of-service / medical-necessity on office sinus procedures",
             "Medium",
             "Payer challenges to office-based balloon sinuplasty and in-office "
             "CT coverage can compress the facility-style ancillary."),
        Risk("Allergy immunotherapy billing audit (95165 dose/vial cap)",
             "Medium",
             "The per-dose antigen-prep code has a documented overpayment and "
             "audit history around dose definition and the 10-dose vial cap."),
        Risk("Biologic channel shift to the pharmacy benefit", "Medium",
             "CRSwNP/asthma biologics moving to specialty pharmacy thin the "
             "in-office buy-and-bill drug ancillary."),
        Risk("MPFS conversion-factor erosion", "Medium",
             "A structural, no-inflation-update squeeze on the professional fee "
             "for the visit, testing, and procedures."),
        Risk("Multiple compression on exit", "Medium",
             "As ENT/allergy roll-ups mature toward derm/GI, the entry-multiple "
             "arbitrage the thesis is priced on can compress."),
    ],
    diligence_questions=[
        "What share of EBITDA is ancillary (allergy immunotherapy, audiology, "
        "in-office CT, office procedures, biologics) versus the professional fee, "
        "and how is each captured?",
        "How exposed is the audiology line to OTC hearing aids, and what is the "
        "dispensing-volume and margin trend since 2022?",
        "How large and stable is the allergy immunotherapy maintenance census, "
        "and what is the 95165 billing/audit posture (dose definition, vial cap)?",
        "What is the office-vs-facility procedure mix, and how durable is payer "
        "coverage of office-based balloon sinuplasty and in-office CT?",
        "Are the immunotherapy lab, in-office imaging, and audiology captures "
        "clean under Stark and the Anti-Kickback Statute?",
        "What is the post-close physician compensation model, and how much "
        "projected EBITDA depends on the comp haircut versus organic growth?",
        "What is the payer mix and commercial-rate position, and how durable are "
        "the top commercial contracts?",
        "What is the biologic exposure and channel mix (pharmacy vs Part B "
        "buy-and-bill), and how does biosimilar/formulary change affect it?",
    ],
    insider_lens=[
        "The scope is the least of it. An ENT's professional fee for the sinus "
        "procedure or the tube placement is small; the allergy immunotherapy "
        "lab, the audiology booth, the in-office CT, and the office procedure "
        "suite are the business. ENT/allergy value is how much of that ancillary "
        "stack the platform legally owns.",
        "Allergy is in the platform for the annuity. The antigen-prep code "
        "(95165) turns an allergic-rhinitis patient into a multi-year, recurring, "
        "high-margin revenue stream on a fixed lab cost — the steadiest cash flow "
        "in an otherwise procedure-lumpy business, which is exactly why combined "
        "ENT + allergy platforms exist.",
        "The OTC hearing-aid rule changed the audiology math. Cash-pay "
        "hearing-aid dispensing was a quiet high-margin pillar; the 2022 FDA rule "
        "and retail/payer channels are eroding the premium — underwrite the "
        "audiology trend, not the historical run-rate.",
        "Office-based sinus surgery is a facility fee in disguise. Moving balloon "
        "sinuplasty and CT into the office captures a facility-style economic — "
        "great while it lasts, but it is exactly the kind of site-of-service and "
        "medical-necessity capture payers periodically reprice.",
        "The whole ancillary stack lives on the Stark in-office ancillary "
        "exception. The immunotherapy lab, the in-office CT, and the audiology "
        "capture are legal because of one carve-out; a change to it reprices the "
        "model at once.",
        "ENT/allergy is earlier in the roll-up cycle than derm or GI. That means "
        "more independent whitespace and less picked-over multiples — but also a "
        "less-proven playbook and thinner comparable exit data to underwrite.",
    ],
    connections=default_connections(
        "ent_allergy",
        deals_sector="ent",
        extra_pages=[
            ("/industry/ent_allergy",
             "Industry deep-dive — ENT/allergy deal history + ancillary read"),
        ],
        connectors=[
            ("npi_provider_taxonomy",
             "NPI taxonomy — otolaryngology & allergy/immunology specialty mix "
             "and practice enrollment"),
            ("cms_open_data_mup_physician_by_provider_service",
             "Medicare physician utilization — ENT/allergy procedure volume, "
             "immunotherapy admin & allowed charges"),
            ("provider_data_asc_quality_facility",
             "CMS ASC quality file — sinus/ENT surgery-center footprint"),
            ("cms_open_data_part_b_spending_by_drug",
             "Medicare Part B drug spending — CRSwNP/asthma biologic read"),
            ("open_payments_general_payments_2024",
             "Open Payments — device/biologic industry payments to ENT & allergy "
             "physicians (relationship screen)"),
            ("census_acs_cbsa_profile",
             "Census ACS — CBSA age and pediatric density for allergy, tube, and "
             "hearing-loss demand"),
        ],
    ),
    sources=[
        Source("American Academy of Otolaryngology–Head and Neck Surgery "
               "(AAO-HNS) — workforce and clinical practice guidelines", "INDUSTRY",
               "https://www.entnet.org/"),
        Source("American Academy of Allergy, Asthma & Immunology (AAAAI) — "
               "workforce and immunotherapy practice parameters", "INDUSTRY",
               "https://www.aaaai.org/"),
        Source("FDA — Over-the-Counter Hearing Aids final rule (2022)", "GOV",
               "https://www.fda.gov/medical-devices/hearing-aids/otc-hearing-aids-what-you-should-know"),
        Source("CMS — Medicare Physician Fee Schedule annual Final Rule (RVUs, "
               "conversion factor, immunotherapy/allergy codes)", "GOV",
               "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
        Source("CDC / NHANES — allergic rhinitis and chronic sinusitis "
               "prevalence", "GOV",
               "https://www.cdc.gov/nchs/"),
        Source("Physician self-referral law (Stark, 42 CFR 411.350+) — in-office "
               "ancillary-services exception", "GOV",
               "https://www.cms.gov/medicare/regulations-guidance/physician-self-referral"),
        Source("PE Desk industry deep-dive (ENT & allergy) + realized-deal "
               "corpus", "INTERNAL",
               "/diligence/tam-sam?template=ent_allergy"),
    ],
    live_figures=live_figures_from_dive("ent_allergy"),
    trends=(
        "ENT & Allergy is consolidating on the same logic that rolled up "
        "dermatology and gastroenterology — the professional fee is a fraction of "
        "the economic footprint the physician generates — but it is a cycle or "
        "two behind, with more independent whitespace remaining. The combined "
        "ENT + allergy structure is deliberate: allergy supplies a recurring "
        "immunotherapy antigen-prep annuity that smooths the lumpier surgical "
        "revenue, and the platform layers audiology, in-office CT, office-based "
        "sinus procedures, and severe-disease biologics on top. Three forces "
        "frame the forward trajectory. First, the 2022 FDA over-the-counter "
        "hearing-aid rule structurally reprices the audiology dispensing margin "
        "that has been a platform pillar. Second, site-of-service migration is "
        "pulling balloon sinuplasty and CT into the office, capturing "
        "facility-style economics but exposing them to coverage and "
        "medical-necessity repricing. Third, biologics for chronic "
        "rhinosinusitis with nasal polyps and severe asthma are expanding demand "
        "while migrating spend toward the pharmacy benefit. Quality-of-earnings "
        "work centers on ancillary durability and physician retention rather than "
        "raw visit counts."),
    growth_levers=[
        GrowthLever(
            "Allergy immunotherapy annuity",
            "The antigen-prep code (95165) generates recurring, multi-year, "
            "high-margin revenue per allergic patient on a fixed lab cost — the "
            "steadiest cash flow in the platform.",
            "+ recurring ancillary", "ILLUSTRATIVE"),
        GrowthLever(
            "In-office site-of-service migration",
            "Move balloon sinuplasty, tubes, and CT into the office to capture "
            "facility-style economics that used to live in the hospital or ASC.",
            "+ facility-style capture", "ILLUSTRATIVE"),
        GrowthLever(
            "Severe-disease biologics (CRSwNP / asthma)",
            "Dupilumab and other biologics expand the treatable population and "
            "the drug line, mostly through the pharmacy benefit with a Part B "
            "slice.",
            "+ biologic demand", "ILLUSTRATIVE"),
        GrowthLever(
            "Sleep-apnea device adoption (Inspire)",
            "Hypoglossal-nerve-stimulation implants for obstructive sleep apnea "
            "add a high-value surgical and follow-up line.",
            "+ procedure line", "ILLUSTRATIVE"),
        GrowthLever(
            "Consolidation multiple arbitrage + comp haircut",
            "Acquire independent ENT/allergy groups at lower multiples, "
            "centralize the MSO, and re-rate on scale and ancillaries.",
            "primary / retention-gated", "ILLUSTRATIVE"),
        GrowthLever(
            "OTC hearing-aid + MPFS rate drag",
            "The OTC audiology repricing and a flat-to-declining professional fee "
            "are the structural headwinds.",
            "rate / margin headwind", "GOV"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Chronic allergic/sinus disease + pediatric otitis + aging hearing "
               "loss",
        analysis=(
            "The demand base is broad, chronic, and demographic rather than a "
            "single discrete driver. Allergic rhinitis affects roughly 19-30% of "
            "US adults and chronic rhinosinusitis about 11-12%, giving a large, "
            "recurring pool that feeds allergy testing, immunotherapy, and sinus "
            "procedures. Pediatric otitis media makes tympanostomy-tube placement "
            "one of the most common childhood surgeries requiring anesthesia "
            "(roughly 500,000-700,000 procedures a year), a steady pediatric "
            "volume source. And age-related hearing loss expands the audiology "
            "and hearing-aid pool as the population ages. Layered on top, "
            "biologics enlarge the treatable severe-disease population, and sleep "
            "apnea adds a growing device-and-procedure line. The offsets are "
            "policy, not demand: OTC hearing aids reprice the audiology capture "
            "and MPFS drift squeezes the professional fee — the patients keep "
            "coming, but the per-encounter economics face repricing."),
        basis="GOV"),
    cost_drivers=[
        CostDriver(
            "Physician & advanced-practice compensation", "~40-50% of cost",
            "The dominant cost; the post-close comp model is both the biggest "
            "margin lever and the biggest retention risk.", "ILLUSTRATIVE"),
        CostDriver(
            "Clinical + audiology staff", "~15-20% of cost",
            "Nurses, medical assistants, allergy-injection staff, and "
            "audiologists — the labor running the office and the ancillaries.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Antigen / serum + hearing-aid COGS", "variable / retail",
            "Immunotherapy antigen and serum acquisition plus hearing-aid device "
            "cost — the cost side of the two signature ancillaries.",
            "ILLUSTRATIVE"),
        CostDriver(
            "In-office CT + procedure equipment / occupancy", "~10-15% of cost",
            "The imaging and office-procedure chassis (cone-beam CT, balloon "
            "sinuplasty capital) plus clinic real estate.", "ILLUSTRATIVE"),
        CostDriver(
            "MSO back office (billing/RCM, IT, compliance)", "~10-15% of cost",
            "The shared-services and compliance apparatus the ancillary-heavy "
            "structure requires.", "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "No national physician-practice facility file is vendored — an ENT or "
        "allergy group is a business, not a Medicare-certified facility — and "
        "AAO-HNS/AAAAI workforce data is aggregate-only, so state geography is "
        "omitted rather than fabricated. The most consequential geographic "
        "variables are the corporate-practice-of-medicine doctrine (strong-CPOM "
        "states force the friendly-PC/MSO structure), state ASC licensure and "
        "certificate-of-need regimes that gate where an owned surgery center can "
        "open, and the growing list of states enacting PE-in-healthcare "
        "transaction-review laws. The NPI-taxonomy, Medicare physician-utilization, "
        "ASC-quality, and demographic connectors linked below map ENT/allergy "
        "supply and procedure volume against the population that drives allergy, "
        "tube, and hearing-loss demand — the honest footprint read."),
)

register(REPORT)
