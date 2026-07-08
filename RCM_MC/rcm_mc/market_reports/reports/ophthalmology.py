"""Ophthalmology — cataract surgery, retina drug buy-and-bill, and the ASC.

Deals-only deep-dive (no national physician-practice census; AAO workforce data
is aggregate-only, so geography is omitted rather than fabricated). Ophthalmology
is two very different businesses under one specialty: high-volume cataract surgery
(the ASC facility fee plus cash-pay premium-IOL upgrades) and retina, where
anti-VEGF intravitreal injections are among the single largest lines of Medicare
Part B drug spend, billed buy-and-bill at ASP-plus. The qualitative sections are
authored around that split, the biosimilar and longer-acting-agent pressure on the
retina drug spread, the optometry co-management model, and the cataract ASC.
Consumes ``ophthalmology_deep_dive()`` for SOURCED corpus deal figures.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="ophthalmology",
    name="Ophthalmology",
    care_setting="Physician services",
    naics="621111",
    one_line_def=(
        "Physician eye-care practices spanning comprehensive ophthalmology and "
        "high-volume cataract surgery, retina (age-related macular degeneration "
        "and diabetic eye disease), glaucoma, cornea, and oculoplastics — where "
        "the economics split between the cataract ASC facility fee plus cash-pay "
        "premium-lens upgrades and the retina anti-VEGF drug buy-and-bill that is "
        "one of the largest single lines of Medicare Part B spend."),
    tam_headline=TamHeadline(
        value=35.0, unit="$B", growth_pct=5.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "Modeled from the ~18,000-19,000 practicing US ophthalmologists (AAO "
            "workforce, directional) times the professional fee plus the "
            "cataract-ASC facility, cash-pay premium-IOL, retina drug "
            "buy-and-bill, and optical ancillary stack — not a single published "
            "figure. Growth is the modeled composite of aging cataract and "
            "retina demand and premium-IOL cash growth, net of anti-VEGF "
            "biosimilar/longer-acting-agent drug-margin erosion and MPFS/ASC "
            "rate drag."),
    ),
    executive_summary=[
        "Ophthalmology is two businesses in one specialty. Cataract surgery is a "
        "high-volume ASC facility-fee business with a cash-pay premium-lens "
        "upgrade; retina is a drug business, where anti-VEGF intravitreal "
        "injections are among the largest single lines of Medicare Part B spend. "
        "They are diligenced very differently.",
        "Cataract is the volume engine. It is the most common surgery in Medicare, "
        "performed overwhelmingly in ambulatory surgery centers — so the value is "
        "the owned or JV cataract ASC facility fee, not just the surgeon's "
        "professional fee, plus the cash-pay premium (presbyopia/astigmatism) "
        "intraocular-lens upgrade patients pay out of pocket.",
        "Retina runs on the drug spread. Anti-VEGF agents (aflibercept, "
        "ranibizumab, faricimab, and off-label bevacizumab) are bought and billed "
        "at ASP-plus; the gross line is enormous but the real margin is the "
        "spread — which biosimilars and longer-acting agents are now compressing.",
        "Optometry co-management is the referral and structural core. "
        "Optometrists feed cataract and disease referrals and share post-op care "
        "(the surgical/post-op modifier split) — a growth engine and an "
        "Anti-Kickback-sensitive arrangement diligence must test.",
        "PE consolidation is well advanced and often retina-led precisely because "
        "of the drug economics — EyeCare Partners, Retina Consultants of America, "
        "EyeSouth, US Eye, and AEG Vision built multi-state platforms; the "
        "acquirable pool is the independent integrated or single-subspecialty "
        "group.",
        "Demand is demographic and non-discretionary: aging drives cataract, "
        "age-related macular degeneration, and diabetic retinopathy — a rising, "
        "recurring, procedure- and injection-heavy pipeline that underwrites the "
        "sector across a hold.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Referral / optometry co-management / self-referral for vision or eye "
            "disease",
            "Comprehensive exam + diagnostics (OCT imaging, visual fields, "
            "biometry)",
            "Cataract pathway — surgery in the owned/JV ASC + IOL selection "
            "(standard vs cash-pay premium lens)",
            "Retina pathway — anti-VEGF intravitreal injections (buy-and-bill), "
            "often monthly-to-quarterly",
            "Glaucoma / cornea / oculoplastics procedures as indicated (MIGS, "
            "transplants, lids)",
            "Optical dispensing (eyewear/contacts — retail cash-pay) where the "
            "practice runs it",
            "Charge capture, coding (surgery, injections, drug J-codes), and "
            "collections",
        ],
        sites_of_care=[
            "Physician clinic (exams, diagnostics, in-office injections)",
            "Owned or JV ambulatory surgery center (cataract — the facility-fee "
            "base)",
            "In-office retina injection suite (anti-VEGF buy-and-bill)",
            "Hospital outpatient department (complex or hospital-based surgery)",
            "Optical / optometry co-management network (referral + retail)",
        ],
        money_flow=(
            "An ophthalmologist earns a professional fee off the Medicare "
            "Physician Fee Schedule for the exam, the cataract operation (66984 / "
            "66982), and the intravitreal injection (67028) — or a commercial "
            "multiple of it. But the two subspecialty engines run on different "
            "ancillaries. Cataract is performed almost entirely in an ambulatory "
            "surgery center that bills a facility fee (Medicare ASC Payment "
            "System) — high-volume, and pure capture when the practice owns or "
            "co-owns the center — and the patient may pay cash out of pocket for a "
            "premium presbyopia- or astigmatism-correcting intraocular lens above "
            "what Medicare covers for the standard lens. Retina is a drug "
            "business: anti-VEGF agents are purchased by the practice and billed "
            "to Part B at ASP plus a percentage, so the practice earns the "
            "acquisition spread on an enormous gross drug line. Optical dispensing "
            "adds retail cash-pay. In the PE structure the payer (and patient) pay "
            "the physician-owned professional corporation, which pays the MSO a "
            "management fee for the ASC, the injection/drug operation, the "
            "optical, billing, and shared services — so platform value turns on "
            "the ASC facility capture, the durability of the retina drug spread, "
            "and the premium-IOL and optical cash lines."),
        key_players=(
            "PE-backed platforms lead the consolidation: EyeCare Partners "
            "(Partners Group), Retina Consultants of America (Webster Equity), "
            "EyeSouth Partners (Olympus/Shore), US Eye, AEG Vision, Prism Vision "
            "Group, and Unifeye Vision Partners built multi-state footprints. "
            "Retina drug manufacturers shape the largest ancillary — Regeneron "
            "(aflibercept / Eylea), Genentech/Roche (ranibizumab / Lucentis and "
            "faricimab / Vabysmo), and the aflibercept and ranibizumab biosimilar "
            "makers — while off-label repackaged bevacizumab (Avastin) is the "
            "cheap alternative. Optometrists are the referral and co-management "
            "network. Large independent integrated and single-subspecialty groups "
            "anchor most metros and are the acquirable pool."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Practicing US ophthalmologists", "~18,000-19,000",
                    "INDUSTRY · AAO workforce (directional)"),
            Segment("Cataract surgeries / yr (US)", "~3.5-4M procedures",
                    "INDUSTRY · AAO / ophthalmology-utilization estimates "
                    "(directional)"),
            Segment("Anti-VEGF intravitreal agents",
                    "among the largest Part B drug lines",
                    "GOV · CMS Medicare Part B drug spending dashboard"),
            Segment("Adults with age-related macular degeneration",
                    "~20M early / ~1.5-2M advanced",
                    "GOV · NEI / CDC AMD prevalence estimates"),
            Segment("Ancillary + cash share (ASC + drug spread + premium IOL + "
                    "optical)", "~40-60% of a mature platform's revenue",
                    "ILLUSTRATIVE · platform economics, directional"),
        ],
        growth_drivers=[
            "Aging → cataract, AMD, and diabetic-retinopathy prevalence ~3%/yr",
            "Cataract ASC migration + de novo surgery centers (facility-fee "
            "capture)",
            "Cash-pay premium-IOL (presbyopia/astigmatism) upgrade attach growth",
            "Retina anti-VEGF injection volume (offset by biosimilar/longer- "
            "acting-agent margin erosion)",
            "Optometry co-management extending surgical referral funnels",
            "MPFS / ASC facility-fee updates + drug-margin drag — the offsets",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Medicare / MA": 0.58,
            "Commercial": 0.28,
            "Self-pay / cash (premium IOL, optical)": 0.09,
            "Medicaid": 0.05,
        },
        rate_mechanics=[
            "MPFS professional fee for exams, cataract surgery (66984/66982), and "
            "intravitreal injection administration (67028) — RVUs × GPCI × the "
            "annual conversion factor, or a commercial multiple; ophthalmology is "
            "a heavily Medicare-weighted specialty.",
            "Medicare ASC Payment System facility fee — cataract is one of the "
            "highest-volume ASC procedures; the owned/JV ASC facility fee is the "
            "anchor cataract ancillary.",
            "Cash-pay premium intraocular lenses — CMS permits the patient to pay "
            "out of pocket for the presbyopia-/astigmatism-correcting portion "
            "above the covered standard lens (the 2005/2007 rulings) — a cash "
            "upgrade line.",
            "Retina drug buy-and-bill — anti-VEGF agents billed to Part B at ASP "
            "plus a percentage (subject to the sequester); the practice earns the "
            "acquisition spread on a very large gross drug line.",
            "Biosimilar substitution + longer-acting agents — aflibercept and "
            "ranibizumab biosimilars and longer-interval agents (faricimab, "
            "high-dose aflibercept) compress the injection count and the "
            "per-dose spread.",
            "Optometry co-management — the surgical global period split (modifiers "
            "54/55) shares post-op payment between surgeon and optometrist — a "
            "referral-sensitive, Anti-Kickback-scrutinized arrangement.",
        ],
        reimbursement_risk=(
            "The two engines carry different reimbursement risks. Cataract rides "
            "MPFS conversion-factor drift and periodic revaluation of the "
            "cataract codes, plus site-neutral pressure on the ASC facility fee "
            "(though the ASC has historically been favored over the "
            "hospital-outpatient site). Retina is a drug-margin story: anti-VEGF "
            "buy-and-bill economics decay as aflibercept and ranibizumab "
            "biosimilars erode the ASP spread and as longer-acting agents "
            "(faricimab, high-dose aflibercept) reduce injection frequency — "
            "shrinking both the per-dose spread and the number of billable "
            "injections. The premium-IOL and optical lines are cash-pay and "
            "cyclical. And optometry co-management is Anti-Kickback-sensitive: an "
            "improperly structured referral or global-period split is a "
            "compliance exposure. A durable platform balances the cataract "
            "facility economics against the retina drug economics so neither "
            "repricing is existential."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("Medicare Physician Fee Schedule (annual Final Rule)",
                 "Sets the RVUs and conversion factor for the eye exam, cataract "
                 "surgery, and intravitreal-injection codes and periodically "
                 "revalues high-volume ophthalmology services.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
            Rule("Medicare ASC Payment System (annual OPPS/ASC Final Rule)",
                 "Sets the cataract facility fee — the anchor ancillary — and the "
                 "ASC-vs-HOPD site differential the owned-center thesis rides.",
                 "https://www.cms.gov/medicare/payment/prospective-payment-systems/ambulatory-surgical-center-asc"),
            Rule("Medicare Part B drug payment (ASP+6% + sequester)",
                 "Governs anti-VEGF buy-and-bill — the retina drug spread that is "
                 "one of the largest Part B drug lines and the core retina "
                 "economic.",
                 "https://www.cms.gov/medicare/payment/part-b-drugs"),
            Rule("Premium-IOL patient-payment rulings (2005/2007)",
                 "Permit patients to pay out of pocket for presbyopia-/"
                 "astigmatism-correcting lenses above the covered standard lens — "
                 "the legal basis of the cash-pay upgrade line.",
                 "https://www.cms.gov/medicare/coverage"),
            Rule("Anti-Kickback Statute — optometry co-management",
                 "OIG has scrutinized optometrist co-management fee-splitting and "
                 "referral arrangements (the surgical global-period 54/55 split).",
                 "https://oig.hhs.gov/compliance/advisory-opinions/"),
            Rule("Physician self-referral law (Stark, 42 CFR 411.350+)",
                 "The in-office ancillary-services exception underpins the owned "
                 "ASC, in-office imaging, and drug-administration captures.",
                 "https://www.cms.gov/medicare/regulations-guidance/physician-self-referral"),
        ],
        policy_watch=[
            "Anti-VEGF biosimilar uptake and longer-acting-agent adoption eroding "
            "the retina drug spread and injection count",
            "Medicare Part B drug-payment reform (ASP+ methodology, add-on "
            "changes) affecting buy-and-bill",
            "MPFS revaluation of cataract and injection codes + conversion-factor "
            "cuts",
            "Site-neutral / ASC-vs-HOPD facility-fee convergence",
            "OIG scrutiny of optometry co-management and referral structures; "
            "state PE-transaction-review laws",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "US ophthalmology remains fragmented across independent integrated "
            "and single-subspecialty (retina, cataract, glaucoma) groups, but it "
            "is now among the more consolidated specialties — a set of PE-backed "
            "multi-state platforms, several of them retina-led, has built "
            "meaningful density. The acquirable pool is the independent integrated "
            "group or single-subspecialty (especially retina) practice with a "
            "capturable ASC, drug, and optical stack."),
        hhi_or_share=(
            "No single owner is dominant nationally; concentration is regional and "
            "platform-specific. No vendored physician-practice roll captures "
            "operator concentration, so a national chain HHI is honestly omitted — "
            "the corpus deal history below is the real read."),
        consolidation=(
            "The model is specialty buy-and-build with two flavors. Comprehensive/"
            "cataract platforms (EyeCare Partners, EyeSouth, US Eye, AEG Vision) "
            "acquire integrated groups, centralize the MSO, and capture the "
            "cataract ASC and optical. Retina platforms (Retina Consultants of "
            "America, Prism Vision) consolidate specifically for the anti-VEGF "
            "drug economics and payer scale. Optometry integration feeds the "
            "surgical funnel. The sector is a cycle behind dermatology in maturity "
            "but well past the early innings."),
        pe_activity=(
            "One of the most PE-active specialties of the last decade, with "
            "distinct comprehensive and retina roll-up strategies. Diligence "
            "centers on the durability of the retina drug spread (biosimilars and "
            "longer-acting agents), cataract ASC facility capture and site-neutral "
            "risk, optometry co-management compliance, and physician retention "
            "rather than raw visit growth."),
        notable_players=[
            "EyeCare Partners", "Retina Consultants of America",
            "EyeSouth Partners", "US Eye", "AEG Vision", "Prism Vision Group",
            "Regeneron (aflibercept / Eylea — retina drug driver)",
            "Genentech / Roche (ranibizumab, faricimab — retina drug driver)",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Cataract cases / surgeon / yr", "high-volume",
                "The cataract engine; volume drives both the professional fee and "
                "the ASC facility fee."),
            Kpi("Premium-IOL attach rate", "cash-pay upgrade %",
                "The cash upside on cataract — the share of patients paying out of "
                "pocket for a presbyopia/astigmatism lens."),
            Kpi("Anti-VEGF injections / retina physician / yr",
                "high-volume, drug-heavy",
                "The retina engine; injection count times the drug spread is the "
                "retina economic — both are under biosimilar/longer-acting "
                "pressure."),
            Kpi("Retina drug-spread margin (ASP-plus)", "biosimilar-sensitive",
                "Large gross drug revenue; the real margin is the acquisition "
                "spread, which biosimilars and interval extension compress."),
            Kpi("ASC facility capture / utilization", "owned or JV %",
                "Cataract facility-fee economics on a fixed-cost surgical "
                "chassis; empty block time kills the ASC margin."),
            Kpi("Platform EBITDA margin (post-MSO)", "18-25% (illustrative)",
                "Ancillary- and drug-rich ophthalmology runs at the higher end of "
                "physician-services margins."),
        ],
        margin_profile=(
            "Ophthalmology margin is a blend of two very different structures. On "
            "the cataract side it is a facility business: a high-fixed-cost ASC "
            "chassis where facility-fee margin steps up sharply with surgical "
            "volume, plus a cash-pay premium-IOL upgrade that carries retail "
            "margin. On the retina side it is a drug business: enormous gross "
            "buy-and-bill revenue on anti-VEGF agents, with the real margin sitting "
            "in the acquisition spread (ASP-plus) — thin relative to the gross "
            "line and actively eroding as biosimilars enter and longer-acting "
            "agents reduce injection frequency. Optical dispensing adds retail cash "
            "margin. Scale spreads the MSO, ASC, and injection operation and "
            "strengthens both payer and drug-purchasing leverage, but the quality "
            "of an ophthalmology platform is the balance between durable cataract "
            "facility economics and a retina drug spread that is structurally under "
            "pressure."),
    ),
    risks=[
        Risk("Retina anti-VEGF drug-spread erosion (biosimilars + longer-acting "
             "agents)", "High",
             "Aflibercept/ranibizumab biosimilars compress the ASP spread and "
             "longer-acting agents cut injection frequency — squeezing both the "
             "per-dose margin and the billable volume of the retina engine."),
        Risk("Physician retention / comp-haircut backlash", "High",
             "Selling cataract and retina surgeons are the EBITDA; a botched "
             "post-close compensation redesign drives defection and volume loss."),
        Risk("Cataract ASC facility-fee + site-neutral repricing", "Medium",
             "The cataract facility fee is the anchor ancillary; site-neutral "
             "convergence compresses the owned-center thesis."),
        Risk("Optometry co-management Anti-Kickback exposure", "Medium",
             "Improperly structured co-management fee-splits and referral "
             "arrangements carry AKS risk."),
        Risk("Medicare Part B drug-payment reform", "Medium",
             "Changes to ASP+ methodology or add-on payment directly reprice the "
             "retina buy-and-bill economics."),
        Risk("MPFS revaluation + conversion-factor erosion", "Medium",
             "A structural squeeze on the professional fee for exams, cataract "
             "surgery, and injection administration."),
        Risk("Cash-pay premium-IOL / optical cyclicality", "Low",
             "The discretionary cash lines soften in a downturn, though the "
             "medical core is non-discretionary."),
    ],
    diligence_questions=[
        "What is the revenue split between cataract (professional + ASC facility "
        "+ premium IOL) and retina (professional + drug spread), and how is each "
        "captured?",
        "How durable is the retina drug spread — what is the biosimilar-uptake "
        "and longer-acting-agent exposure, and how does it hit injection count and "
        "per-dose margin?",
        "What is the cataract ASC ownership/JV structure and utilization, and how "
        "exposed is the facility fee to site-neutral repricing?",
        "What is the premium-IOL attach rate and the optical cash-pay line, and "
        "how cyclical are they?",
        "How is optometry co-management structured (referral, 54/55 split), and "
        "is it clean under the Anti-Kickback Statute?",
        "What is the post-close physician (cataract and retina) compensation "
        "model, and how much projected EBITDA rests on the comp haircut?",
        "What is the payer mix (heavily Medicare) and commercial-rate position, "
        "and how durable are the top contracts?",
        "Where is the platform in its ownership cycle, and what does the entry-vs- "
        "exit multiple picture imply for the arbitrage?",
    ],
    insider_lens=[
        "Ophthalmology is two businesses. Cataract is a facility-fee-and-ASC "
        "business with a cash-pay lens upgrade; retina is a drug-spread business. "
        "They have different growth curves, different risks, and different "
        "diligence — never underwrite an 'ophthalmology' platform as one thing.",
        "Retina is a pharmacy with a physician attached. Anti-VEGF injections are "
        "one of the biggest lines of Medicare Part B drug spend, and the practice "
        "earns the acquisition spread — so the value is the drug margin, and the "
        "drug margin is exactly what biosimilars and longer-acting agents are "
        "eroding on both price and frequency.",
        "The premium lens is the quiet cash line. Medicare covers the standard "
        "cataract lens; the patient pays out of pocket for the "
        "presbyopia/astigmatism upgrade — a legal cash-pay attach on top of the "
        "covered surgery, and a real, growing, cyclical margin stream.",
        "Cataract value is the ASC, not the surgeon's fee. It is the most common "
        "Medicare surgery and it moved almost entirely into ambulatory surgery "
        "centers — so owning or co-owning the cataract ASC is where the money is, "
        "and site-neutral pressure is the thing that reprices it.",
        "Optometrists are the funnel. The co-management model feeds surgical "
        "referrals and shares post-op care through the global-period split — a "
        "growth engine that is also one of OIG's named Anti-Kickback concerns, so "
        "the arrangement is a diligence item, not a footnote.",
        "The specialty is Medicare-heavy by nature. An aging patient base means "
        "government payers dominate the mix, so MPFS drift, ASC-rate policy, and "
        "Part B drug reform hit ophthalmology harder and more directly than a "
        "commercially-weighted specialty.",
    ],
    connections=default_connections(
        "ophthalmology",
        deals_sector="ophthalmology",
        extra_pages=[
            ("/industry/ophthalmology",
             "Industry deep-dive — ophthalmology deal history + cataract/retina "
             "read"),
        ],
        connectors=[
            ("npi_provider_taxonomy",
             "NPI taxonomy — ophthalmology, retina & optometry specialty mix and "
             "enrollment"),
            ("cms_open_data_mup_physician_by_provider_service",
             "Medicare physician utilization — cataract, injection & exam volume "
             "and allowed charges"),
            ("cms_open_data_part_b_spending_by_drug",
             "Medicare Part B drug spending — anti-VEGF (aflibercept / "
             "ranibizumab / faricimab) buy-and-bill read"),
            ("provider_data_asc_quality_facility",
             "CMS ASC quality file — cataract surgery-center footprint"),
            ("open_payments_general_payments_2024",
             "Open Payments — retina-drug/device industry payments to "
             "ophthalmologists (relationship screen)"),
            ("census_acs_cbsa_profile",
             "Census ACS — CBSA age (65+) density for cataract and AMD demand "
             "mapping"),
        ],
    ),
    sources=[
        Source("American Academy of Ophthalmology (AAO) — workforce and clinical "
               "practice data", "INDUSTRY",
               "https://www.aao.org/"),
        Source("CMS — Medicare Part B drug spending dashboard (anti-VEGF ASP and "
               "utilization)", "GOV",
               "https://www.cms.gov/medicare/payment/part-b-drugs"),
        Source("CMS — Ambulatory Surgical Center Payment System annual Final Rule "
               "(cataract facility fee)", "GOV",
               "https://www.cms.gov/medicare/payment/prospective-payment-systems/ambulatory-surgical-center-asc"),
        Source("CMS — Medicare Physician Fee Schedule annual Final Rule (RVUs, "
               "conversion factor, cataract/injection codes)", "GOV",
               "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
        Source("National Eye Institute / CDC — age-related macular degeneration, "
               "cataract, and diabetic-retinopathy prevalence", "GOV",
               "https://www.nei.nih.gov/"),
        Source("NEJM / Ophthalmology — anti-VEGF comparative trials (CATT) and "
               "biosimilar/longer-acting-agent evidence", "ACADEMIC",
               "https://www.nejm.org/"),
        Source("PE Desk industry deep-dive (ophthalmology) + realized-deal "
               "corpus", "INTERNAL",
               "/diligence/tam-sam?template=ophthalmology"),
    ],
    live_figures=live_figures_from_dive("ophthalmology"),
    trends=(
        "Ophthalmology consolidated hard over the last decade, but it is really "
        "two roll-ups under one specialty. The comprehensive/cataract platforms "
        "(EyeCare Partners, EyeSouth, US Eye, AEG Vision) are built on the "
        "cataract ASC facility fee, the cash-pay premium-lens upgrade, and the "
        "optical line, riding an aging population into the most common surgery in "
        "Medicare. The retina platforms (Retina Consultants of America, Prism "
        "Vision) are built specifically on the anti-VEGF drug economics — buying "
        "and billing aflibercept, ranibizumab, and faricimab at ASP-plus on one "
        "of the largest single lines of Medicare Part B spend. The central forward "
        "tension is on that retina drug spread: aflibercept and ranibizumab "
        "biosimilars are entering and longer-acting agents (faricimab, high-dose "
        "aflibercept) are extending dosing intervals, so both the per-dose margin "
        "and the number of billable injections face erosion. On the cataract side "
        "the pressures are MPFS revaluation, ASC facility-fee and site-neutral "
        "policy, and the cyclicality of the premium-IOL cash line, while optometry "
        "co-management (a referral funnel and an Anti-Kickback-sensitive "
        "structure) underpins surgical volume. Demand is durable and demographic "
        "— cataract, AMD, and diabetic retinopathy all rise with aging — so "
        "quality-of-earnings work centers on drug-spread durability, ASC capture, "
        "and physician retention rather than raw case counts."),
    growth_levers=[
        GrowthLever(
            "Aging → cataract, AMD & diabetic-retinopathy demand",
            "An aging population drives rising cataract surgery, macular "
            "degeneration, and diabetic eye disease — the durable, non-"
            "discretionary demand base.",
            "+~3%/yr prevalence", "GOV"),
        GrowthLever(
            "Cataract ASC migration + de novo centers",
            "Own the facility fee for the most common Medicare surgery by "
            "performing cataracts in an owned or JV ambulatory surgery center.",
            "+ facility-fee capture", "ILLUSTRATIVE"),
        GrowthLever(
            "Cash-pay premium-IOL attach",
            "Patients pay out of pocket for presbyopia-/astigmatism-correcting "
            "lenses above the covered standard lens — a growing cash upgrade line.",
            "+ cash-pay revenue", "ILLUSTRATIVE"),
        GrowthLever(
            "Retina anti-VEGF injection volume",
            "Growing AMD/DR prevalence drives injection volume and the drug "
            "spread — the retina engine, offset by biosimilar and interval "
            "erosion.",
            "+ drug economics", "ILLUSTRATIVE"),
        GrowthLever(
            "Consolidation multiple arbitrage + comp haircut",
            "Acquire independent eye groups at lower multiples, centralize the MSO "
            "and ASC, and re-rate on scale, drug purchasing, and payer leverage.",
            "primary / retention-gated", "ILLUSTRATIVE"),
        GrowthLever(
            "Biosimilar / longer-acting drug erosion + MPFS/ASC drag",
            "Anti-VEGF biosimilars and longer-interval agents compress the retina "
            "spread and injection count, while MPFS/ASC rate drift squeezes the "
            "cataract side.",
            "primary headwind", "GOV"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Aging-driven eye disease (cataract + AMD + diabetic retinopathy)",
        analysis=(
            "Ophthalmology demand is demographic and non-discretionary, and it "
            "compounds three aging-linked conditions. Cataract is nearly universal "
            "with age, and cataract surgery is already the most common surgical "
            "procedure in Medicare (on the order of 3.5-4 million procedures a "
            "year in the US); the eligible pool grows structurally as the "
            "population ages. Age-related macular degeneration affects roughly 20 "
            "million Americans in early stages and 1.5-2 million in advanced "
            "stages, and diabetic retinopathy rises with the diabetes epidemic — "
            "together they drive the anti-VEGF injection pipeline that is the "
            "retina engine. Because these are aging-driven and progressive, the "
            "demand curve is highly predictable and recurring (retina injections "
            "are repeated for years per patient). The genuine offset is not "
            "demand but drug economics: longer-acting anti-VEGF agents reduce the "
            "number of injections per patient even as the treated population grows, "
            "so retina volume in billable-injection terms can grow more slowly "
            "than prevalence. The patients keep coming; the retina economics turn "
            "on dosing interval and drug spread, and the cataract economics on ASC "
            "capture."),
        basis="GOV"),
    cost_drivers=[
        CostDriver(
            "Physician + clinical-staff compensation", "~35-45% of cost",
            "The dominant cost; cataract- and retina-surgeon comp is the biggest "
            "margin lever and the biggest retention risk.", "ILLUSTRATIVE"),
        CostDriver(
            "Anti-VEGF drug acquisition (retina buy-and-bill COGS)",
            "large gross / thin spread",
            "The cost side of the retina engine — purchasing anti-VEGF agents to "
            "bill at ASP-plus; biosimilars change the acquisition math.",
            "ILLUSTRATIVE"),
        CostDriver(
            "ASC clinical staff + surgical supplies + IOLs", "~15-20% of cost",
            "The cataract surgical chassis — OR staff, phaco supplies, and "
            "intraocular lenses — the fixed cost facility fees cover.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Imaging / diagnostic equipment + occupancy", "~10-15% of cost",
            "OCT, biometry, and visual-field capital plus clinic and ASC real "
            "estate.", "ILLUSTRATIVE"),
        CostDriver(
            "MSO back office (billing/RCM, drug purchasing, compliance)",
            "~10-15% of cost",
            "The shared-services, drug-procurement, and compliance apparatus the "
            "drug- and facility-heavy structure requires.", "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "No national physician-practice census is vendored — an ophthalmology "
        "group is a business, not a Medicare-certified facility — and AAO "
        "workforce data is aggregate-only, so state geography is omitted rather "
        "than fabricated. The most consequential geographic variables are state "
        "ASC licensure and certificate-of-need regimes (which gate where an owned "
        "cataract center can open), the corporate-practice-of-medicine doctrine "
        "and optometry-scope-of-practice rules (which shape the integrated MD-OD "
        "co-management structure), and the growing list of states enacting "
        "PE-in-healthcare transaction-review laws. The NPI-taxonomy, Medicare "
        "physician-utilization, Part B drug-spending, ASC-quality, and demographic "
        "connectors linked below map ophthalmology and retina supply, cataract and "
        "injection volume, and anti-VEGF drug spend against the aging population "
        "that drives demand — the honest footprint read."),
)

register(REPORT)
