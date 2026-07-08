"""Gastroenterology (GI) — the ancillary-rich endoscopy roll-up.

Deals-only deep-dive (no national physician-practice facility file; geography is
omitted rather than fabricated). GI is, with dermatology, the archetypal PE
specialty roll-up because the professional fee is a fraction of the economic
footprint a gastroenterologist generates: the endoscopy ASC facility fee,
anesthesia, in-house pathology, and IBD biologic infusion are the real engine.
The qualitative sections are authored around that ancillary stack, the 2021
screening-age drop to 45, and the non-invasive-screening / biosimilar tensions.
Consumes ``gastroenterology_deep_dive()`` for SOURCED corpus deal figures.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="gastroenterology",
    name="Gastroenterology (GI)",
    care_setting="Physician services",
    naics="621111",
    one_line_def=(
        "Physician practices treating digestive disease — screening and "
        "diagnostic endoscopy (colonoscopy, EGD), inflammatory bowel disease, "
        "GERD, and hepatology — where the economics live in the owned "
        "ancillaries (an endoscopy ASC, anesthesia, in-house pathology, and IBD "
        "biologic infusion) far more than in the professional fee for the scope."),
    tam_headline=TamHeadline(
        value=30.0, unit="$B", growth_pct=6.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "Modeled from the ~15,000-16,000 practicing US gastroenterologists "
            "(AGA/ACG workforce) times the endoscopy professional fee plus the "
            "ASC facility, anesthesia, pathology, and IBD-infusion ancillary "
            "stack — not a single published figure. Growth is the modeled "
            "composite of the screening-age-45 volume expansion, aging demand, "
            "ancillary capture, and biologic mix, net of MPFS/ASC rate drag."),
    ),
    executive_summary=[
        "The colonoscopy is almost a loss-leader for the professional fee — the "
        "money is the stack around it: the endoscopy ASC facility fee, the "
        "separately-billed anesthesia, the in-house pathology reading the "
        "biopsies, and IBD biologic infusion. GI value is ancillary capture, "
        "not the scope.",
        "The 2021 USPSTF drop in the colorectal-cancer screening age from 50 to "
        "45 added roughly 19 million newly-eligible Americans overnight — a "
        "demographic step-change in the screening pool that is nearly unique to "
        "GI and underwrites a decade of volume.",
        "Anesthesia is the quiet ancillary. Propofol / monitored anesthesia care "
        "turned routine sedation into a separately-billed revenue stream; the "
        "anesthesia 'company model' JV is lucrative and Anti-Kickback-fraught, "
        "and its medical necessity for average-risk cases draws payer scrutiny.",
        "IBD biologic infusion (infliximab, vedolizumab, ustekinumab) is large "
        "buy-and-bill revenue at ASP-plus, but biosimilar erosion is thinning "
        "the real spread — underwrite the ASP+6 margin durability, not the gross "
        "infusion line.",
        "Non-invasive screening (Cologuard stool-DNA, blood-based tests) is a "
        "double-edged sword: it diverts some average-risk scopes but funnels "
        "every positive result to a diagnostic colonoscopy, so the net volume "
        "effect is ambiguous while the case mix shifts toward higher-acuity work.",
        "GI is a maturing, ancillary-driven specialty roll-up (GI Alliance, "
        "Gastro Health, One GI, United Digestive); the acquirable pool is the "
        "independent single-specialty group, richest where the ASC, anesthesia, "
        "pathology, and infusion ancillaries can be legally captured.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Referral / self-referral for screening or symptoms (PCP or direct)",
            "Office E&M visit + risk stratification (average vs high risk)",
            "Scheduled endoscopy — colonoscopy / EGD in the owned ASC",
            "Anesthesia (propofol MAC) billed separately by the CRNA/MD",
            "Pathology — biopsies read by the in-house GI pathology lab",
            "IBD / chronic disease management — biologic infusion buy-and-bill",
            "Charge capture, coding (screening vs diagnostic), and collections",
        ],
        sites_of_care=[
            "Physician office / clinic (the E&M encounter, in-office procedures)",
            "Owned ambulatory endoscopy center (ASC) — the volume + margin base",
            "In-office infusion suite (IBD biologics)",
            "Hospital outpatient department (higher-acuity or hospital-based scopes)",
            "In-house anatomic pathology lab (biopsy reads)",
        ],
        money_flow=(
            "A gastroenterologist earns a professional fee off the Medicare "
            "Physician Fee Schedule for each scope (e.g. diagnostic colonoscopy "
            "45378, screening G0121/G0105) or a commercial multiple of it — but "
            "that professional fee is the smallest piece. The endoscopy is "
            "performed in an owned ambulatory surgery center that bills a "
            "facility fee (Medicare ASC Payment System, a fraction of the "
            "hospital-outpatient rate but pure capture for the practice); "
            "anesthesia is billed separately as monitored anesthesia care; the "
            "biopsies are read by an in-house pathology lab; and IBD patients "
            "receive biologic infusions billed buy-and-bill at ASP-plus. In the "
            "PE structure the payer pays the physician-owned professional "
            "corporation, which pays the MSO a management fee for the ASC, "
            "billing, and shared services. The single question that sets a GI "
            "platform's value is how much of that ancillary stack it legally "
            "owns — because the scope itself is the least of it."),
        key_players=(
            "PE-backed platforms lead the consolidation: GI Alliance (the "
            "largest, physician-led with Apollo/Waud capital), Gastro Health, "
            "One GI, United Digestive (Frazier), Allied Digestive Health, and "
            "Capital Digestive Care; Physicians Endoscopy / PE GI Solutions "
            "operates endoscopy ASCs (now within Optum). Large independent "
            "single-specialty groups anchor most metros. Exact Sciences "
            "(Cologuard) and blood-based screeners (e.g. Guardant Shield) sit "
            "upstream as substitute-and-feeder screening technologies. The "
            "acquirable pool is the independent GI group long tail with an "
            "owned or JV endoscopy center."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("US screening colonoscopy volume", "~15M+ procedures / yr",
                    "INDUSTRY · GI society / endoscopy-utilization estimates "
                    "(directional)"),
            Segment("Newly-eligible screening population (age 45-49)",
                    "~19M added by the 2021 age drop",
                    "GOV · USPSTF 2021 CRC screening recommendation"),
            Segment("Practicing US gastroenterologists",
                    "~15,000-16,000",
                    "INDUSTRY · AGA/ACG workforce (directional)"),
            Segment("Ancillary share of a mature GI platform's revenue",
                    "~40-60% (ASC + anesthesia + path + infusion)",
                    "ILLUSTRATIVE · platform economics, directional"),
            Segment("IBD (Crohn's + ulcerative colitis) prevalence",
                    "~3M+ US adults",
                    "GOV · CDC IBD prevalence estimates"),
        ],
        growth_drivers=[
            "Screening-age drop to 45 (2021) — a step-change in the eligible pool",
            "Aging + rising colorectal-cancer and GERD/IBD prevalence ~2-3%/yr",
            "ASC migration + de novo endoscopy centers — facility-fee capture",
            "IBD biologic infusion volume (offset by biosimilar price erosion)",
            "MPFS / ASC facility-fee updates — a flat-to-declining rate drag",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Commercial": 0.48,
            "Medicare / MA": 0.38,
            "Medicaid": 0.09,
            "Self-pay / other": 0.05,
        },
        rate_mechanics=[
            "MPFS professional fee for endoscopy CPTs (colonoscopy 45378-45385, "
            "EGD 43235+, screening G0105/G0121) — RVUs × GPCI × the annual "
            "conversion factor, or a commercial multiple of it.",
            "Medicare ASC Payment System facility fee — the anchor ancillary; "
            "GI endoscopy is among the highest-volume ASC procedures, and the "
            "ASC rate is a fraction of the hospital-outpatient (HOPD) rate for "
            "the same scope (the site-of-service differential).",
            "Anesthesia (monitored anesthesia care / propofol) billed separately "
            "by the CRNA or anesthesiologist — the 'company model' JV is the "
            "revenue mechanism and the Anti-Kickback exposure.",
            "ACA preventive-services coverage — average-risk screening "
            "colonoscopy is a USPSTF grade-A/B service with no cost-sharing; the "
            "CAA-2021 phase-out is removing beneficiary coinsurance when a "
            "screening colonoscopy becomes diagnostic (ramping to zero by 2030).",
            "IBD biologics (infliximab, vedolizumab, ustekinumab) — Part B "
            "buy-and-bill at ASP+6% in the in-office infusion suite; biosimilars "
            "compress the spread.",
            "Anatomic pathology technical/professional components read in-house — "
            "constrained by the anti-markup rule and Stark self-referral limits.",
        ],
        reimbursement_risk=(
            "The professional fee for the scope is under the same MPFS "
            "conversion-factor drift that squeezes every specialty, but GI's "
            "specific exposures are in the ancillary stack. The ASC facility fee "
            "and the site-of-service differential can be repriced (site-neutral "
            "pressure narrows the HOPD/ASC gap that makes the owned center "
            "attractive). Anesthesia for average-risk endoscopy faces "
            "medical-necessity scrutiny and 'company model' Anti-Kickback risk. "
            "IBD infusion economics decay as biosimilars erode the ASP+6 spread. "
            "And non-invasive screening substitution reshapes volume and mix. "
            "The healthiest GI platforms diversify the ancillary base so no "
            "single reimbursement change is existential."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("USPSTF colorectal-cancer screening recommendation (2021)",
                 "Lowered the average-risk screening start age from 50 to 45, "
                 "expanding the eligible pool by ~19M and triggering ACA "
                 "no-cost-share coverage — the sector's demand tailwind.",
                 "https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/colorectal-cancer-screening"),
            Rule("Medicare ASC Payment System (annual OPPS/ASC Final Rule)",
                 "Sets the endoscopy facility fee — the anchor ancillary — and "
                 "the ASC-vs-HOPD site differential the owned-center thesis rides.",
                 "https://www.cms.gov/medicare/payment/prospective-payment-systems/ambulatory-surgical-center-asc"),
            Rule("Medicare Physician Fee Schedule (annual Final Rule)",
                 "Sets the RVUs and conversion factor for the endoscopy "
                 "professional fee and the E&M visit.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
            Rule("Physician self-referral law (Stark, 42 CFR 411.350+)",
                 "The in-office ancillary-services exception is what makes the "
                 "owned ASC, in-house pathology lab, and infusion suite legal.",
                 "https://www.cms.gov/medicare/regulations-guidance/physician-self-referral"),
            Rule("Anti-Kickback Statute + anesthesia 'company model' scrutiny",
                 "OIG has warned on anesthesia arrangements in GI/endoscopy where "
                 "the referring practice shares in the anesthesia revenue.",
                 "https://oig.hhs.gov/compliance/advisory-opinions/"),
            Rule("CAA-2021 screening-colonoscopy cost-sharing phase-out",
                 "Removes beneficiary coinsurance when a screening colonoscopy "
                 "becomes diagnostic (polyp removed) — a demand-side coverage fix.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
        ],
        policy_watch=[
            "Non-invasive screening (Cologuard, blood-based tests) coverage and "
            "guideline placement — substitution vs colonoscopy-feeder dynamics",
            "Biosimilar erosion of infliximab/biologic buy-and-bill economics",
            "Anesthesia medical-necessity + company-model Anti-Kickback "
            "enforcement in average-risk endoscopy",
            "Site-neutral / ASC-vs-HOPD facility-fee convergence",
            "Annual MPFS conversion-factor cuts and the perennial 'doc fix'",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "US gastroenterology is still fragmented across independent "
            "single-specialty groups, but it is one of the most consolidated "
            "specialties after dermatology — a handful of national PE platforms "
            "now employ a meaningful share of gastroenterologists in their lead "
            "markets. The acquirable pool is the independent group with an owned "
            "or JV endoscopy center and a capturable ancillary stack."),
        hhi_or_share=(
            "No single owner is dominant nationally; concentration is regional "
            "and platform-specific. No vendored physician-practice roll captures "
            "operator concentration, so a national chain HHI is honestly omitted "
            "— the corpus deal history below is the real read."),
        consolidation=(
            "GI followed dermatology as an early, aggressive specialty roll-up "
            "precisely because of its ancillary richness. The model is "
            "specialty-specific buy-and-build: acquire an anchor group with an "
            "endoscopy ASC, tuck in independents, centralize the MSO back office, "
            "add anesthesia/pathology/infusion, and re-rate the platform. Several "
            "first-generation platforms are now on their second sponsor."),
        pe_activity=(
            "One of the most PE-active specialties of the last decade — GI "
            "Alliance, Gastro Health, One GI, United Digestive, Allied Digestive, "
            "and Capital Digestive Care built national footprints, and Physicians "
            "Endoscopy (now Optum) scaled endoscopy-center operation. Diligence "
            "now centers on ancillary durability (biosimilar and non-invasive "
            "screening headwinds) and physician retention rather than pure scope "
            "volume growth."),
        notable_players=[
            "GI Alliance", "Gastro Health", "One GI", "United Digestive",
            "Allied Digestive Health", "Capital Digestive Care",
            "Physicians Endoscopy / PE GI Solutions (Optum)",
            "Exact Sciences (Cologuard — upstream substitute)",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Procedures / gastroenterologist / yr", "~1,000-1,500 scopes",
                "The volume engine; colonoscopy + EGD throughput drives both the "
                "professional fee and the ASC facility fee."),
            Kpi("Ancillary revenue (% of total)", "40-60%",
                "ASC facility + anesthesia + pathology + infusion — the higher "
                "the capture, the more platform value beyond the scope."),
            Kpi("ASC room throughput / utilization",
                "cases per room per day",
                "The endoscopy suite is a fixed-cost chassis; empty rooms and "
                "block-time gaps kill facility-fee economics."),
            Kpi("Screening vs diagnostic mix", "practice-dependent",
                "Screening drives volume and no-cost-share access; diagnostic and "
                "therapeutic cases carry higher acuity and yield."),
            Kpi("IBD infusion revenue / patient", "biosimilar-sensitive",
                "Large gross buy-and-bill revenue; the real margin is the ASP+6 "
                "spread, which biosimilars erode."),
            Kpi("Platform EBITDA margin (post-MSO)", "15-22% (illustrative)",
                "Ancillary-rich GI runs at the higher end of physician-services "
                "margins."),
        ],
        margin_profile=(
            "GI economics are dominated by physician compensation like any "
            "specialty, but the differentiator is the ancillary contribution: a "
            "practice that owns its endoscopy ASC, captures the anesthesia, reads "
            "its own pathology, and runs an infusion suite earns several margin "
            "streams off the same patient the professional fee barely covers. "
            "The ASC is a high-fixed-cost chassis, so facility-fee margin steps "
            "up sharply with throughput; the infusion suite carries thin real "
            "margin (ASP+6, biosimilar-pressured) on large gross revenue; and "
            "pathology and anesthesia add capture that is entirely dependent on "
            "the Stark in-office ancillary exception. Scale spreads the MSO back "
            "office and strengthens payer leverage, but the underlying quality of "
            "a GI platform is how much of the ancillary stack it legally owns."),
    ),
    risks=[
        Risk("Endoscopy / ASC facility-fee and site-neutral repricing", "High",
             "The ASC facility fee is the anchor ancillary; site-neutral "
             "convergence of HOPD and ASC rates directly compresses the "
             "owned-center thesis."),
        Risk("Physician retention / comp-haircut backlash", "High",
             "Selling gastroenterologists are the EBITDA; a botched post-close "
             "compensation redesign drives defection and volume loss."),
        Risk("Anesthesia medical-necessity + company-model Anti-Kickback",
             "Medium",
             "MAC/propofol for average-risk endoscopy faces payer scrutiny, and "
             "revenue-sharing anesthesia JVs carry AKS exposure."),
        Risk("Non-invasive screening substitution (Cologuard, blood tests)",
             "Medium",
             "Diverts some average-risk scopes even as it feeds diagnostic "
             "colonoscopies — an ambiguous net-volume and mix risk."),
        Risk("Biosimilar erosion of IBD infusion economics", "Medium",
             "Biosimilar competition thins the ASP+6 spread that makes the "
             "infusion suite lucrative."),
        Risk("MPFS conversion-factor erosion", "Medium",
             "A structural, no-inflation-update squeeze on the professional fee "
             "for the scope and the E&M visit."),
        Risk("Multiple compression on exit", "Medium",
             "Entry multiples rose across the cycle; a maturing GI market "
             "pressures the arbitrage the thesis is priced on."),
    ],
    diligence_questions=[
        "What share of EBITDA is ancillary (ASC facility, anesthesia, pathology, "
        "infusion) versus the professional fee, and how is each captured?",
        "Is the endoscopy-center ownership and the anesthesia arrangement clean "
        "under Stark and the Anti-Kickback Statute (FMV, no improper "
        "revenue-share)?",
        "What is the screening-vs-diagnostic and average-vs-high-risk case mix, "
        "and how exposed is volume to non-invasive screening substitution?",
        "How large is IBD infusion revenue, and what is the biosimilar exposure "
        "to the ASP+6 spread over the hold?",
        "What is the ASC utilization / room throughput, and how much de novo or "
        "block-time capacity remains?",
        "What is the post-close physician compensation model, and how much "
        "projected EBITDA depends on the comp haircut versus organic growth?",
        "What is the payer mix and commercial-rate position, and how durable "
        "are the top commercial contracts?",
        "What is the coding / documentation posture on screening-vs-diagnostic "
        "billing and modifier use, and the audit history?",
    ],
    insider_lens=[
        "The scope is the least of it. A gastroenterologist's professional fee "
        "for a colonoscopy is small; the ASC facility fee, the anesthesia, the "
        "pathology read, and the infusion suite are the business. GI value is a "
        "question of how much of that ancillary stack the platform legally owns.",
        "The screening age drop to 45 was a one-time step-change. Overnight in "
        "2021 the eligible average-risk screening population grew by roughly 19 "
        "million people — a demographic gift almost unique to GI that underwrites "
        "a decade of colonoscopy volume.",
        "Anesthesia is the quiet money. Propofol sedation turned routine "
        "endoscopy anesthesia into a separately-billed revenue stream, and the "
        "'company model' JV that captures it is both lucrative and one of OIG's "
        "favorite Anti-Kickback targets — diligence the arrangement, not just "
        "the P&L line.",
        "Non-invasive screening cuts both ways. Cologuard and blood-based tests "
        "divert some average-risk scopes, but every positive result becomes a "
        "diagnostic colonoscopy — so the net volume effect is ambiguous while the "
        "mix shifts toward higher-acuity, higher-yield cases.",
        "Infusion is big revenue and thin real margin. IBD biologics billed "
        "buy-and-bill look like a large line, but biosimilars are eroding the "
        "ASP+6 spread — underwrite the spread durability, not the gross infusion "
        "revenue.",
        "The whole ancillary stack lives on the Stark in-office ancillary "
        "exception. The ASC, the pathology lab, and the infusion suite are legal "
        "because of one carve-out; a change to it, or a site-neutral facility-fee "
        "move, reprices the entire model at once.",
    ],
    connections=default_connections(
        "gastroenterology",
        deals_sector="gastroenterology",
        extra_pages=[
            ("/industry/gastroenterology",
             "Industry deep-dive — GI deal history + endoscopy ancillary read"),
        ],
        connectors=[
            ("npi_provider_taxonomy",
             "NPI taxonomy — gastroenterology specialty mix & practice enrollment"),
            ("cms_open_data_mup_physician_by_provider_service",
             "Medicare physician utilization — endoscopy volume & allowed charges"),
            ("provider_data_asc_quality_facility",
             "CMS ASC quality file — endoscopy-center footprint & quality"),
            ("cms_open_data_part_b_spending_by_drug",
             "Medicare Part B drug spending — IBD biologic infusion read"),
            ("open_payments_general_payments_2024",
             "Open Payments — industry payments to GI physicians (relationship "
             "screen)"),
            ("census_acs_cbsa_profile",
             "Census ACS — CBSA age (45+) demographics for screening demand"),
        ],
    ),
    sources=[
        Source("US Preventive Services Task Force — Colorectal Cancer Screening "
               "(2021, age 45+)", "GOV",
               "https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/colorectal-cancer-screening"),
        Source("CMS — Ambulatory Surgical Center Payment System annual Final "
               "Rule (endoscopy facility fee)", "GOV",
               "https://www.cms.gov/medicare/payment/prospective-payment-systems/ambulatory-surgical-center-asc"),
        Source("CMS — Medicare Physician Fee Schedule annual Final Rule (RVUs, "
               "conversion factor)", "GOV",
               "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
        Source("Physician self-referral law (Stark, 42 CFR 411.350+) — "
               "in-office ancillary-services exception", "GOV",
               "https://www.cms.gov/medicare/regulations-guidance/physician-self-referral"),
        Source("American College of Gastroenterology / AGA — workforce and "
               "endoscopy practice data", "INDUSTRY",
               "https://gi.org/"),
        Source("NEJM / peer-reviewed literature — Cologuard (DeeP-C) and "
               "blood-based CRC screening performance", "ACADEMIC",
               "https://www.nejm.org/"),
        Source("PE Desk industry deep-dive (gastroenterology) + realized-deal "
               "corpus", "INTERNAL",
               "/diligence/tam-sam?template=gastroenterology"),
    ],
    live_figures=live_figures_from_dive("gastroenterology"),
    trends=(
        "Gastroenterology was, with dermatology, one of the first specialties PE "
        "rolled up, and for the same reason: the professional fee is a fraction "
        "of the economic footprint a gastroenterologist generates. The endoscopy "
        "ASC facility fee, the separately-billed anesthesia, the in-house "
        "pathology lab, and the IBD biologic infusion suite are the real engine, "
        "and platforms like GI Alliance, Gastro Health, and United Digestive were "
        "built to capture them. Two demand facts frame the trajectory. First, the "
        "2021 USPSTF drop in the screening age to 45 added roughly 19 million "
        "newly-eligible Americans — a step-change in the colonoscopy pool. "
        "Second, non-invasive screening (Cologuard, blood-based tests) is "
        "simultaneously a substitute for and a feeder into diagnostic "
        "colonoscopy, muddying the volume outlook. The forward tension is on the "
        "ancillary base the whole thesis rests on: biosimilars are eroding "
        "infusion economics, anesthesia medical-necessity and company-model "
        "arrangements draw scrutiny, and site-neutral pressure threatens the "
        "ASC-vs-HOPD facility-fee gap. Quality-of-earnings work now centers on "
        "ancillary durability and physician retention, not scope count."),
    growth_levers=[
        GrowthLever(
            "Screening-age expansion (USPSTF 45+, 2021)",
            "A one-time step-change adding ~19M newly-eligible average-risk "
            "adults to the colonoscopy screening pool.",
            "step-change / +eligible pop", "GOV"),
        GrowthLever(
            "Endoscopy ASC migration + de novo centers",
            "Own the facility fee for the scope by moving cases into an owned or "
            "JV ambulatory endoscopy center — the anchor ancillary.",
            "+ facility-fee capture", "ILLUSTRATIVE"),
        GrowthLever(
            "Anesthesia + pathology capture",
            "Separately-billed MAC anesthesia and in-house biopsy reads add "
            "margin streams off the same procedure.",
            "+ ancillary margin", "ILLUSTRATIVE"),
        GrowthLever(
            "IBD biologic infusion",
            "In-office buy-and-bill infusion for Crohn's/UC — large gross "
            "revenue, biosimilar-pressured real margin.",
            "+ infusion revenue", "ILLUSTRATIVE"),
        GrowthLever(
            "Consolidation multiple arbitrage + comp haircut",
            "Acquire independent GI groups at lower multiples, centralize the "
            "MSO, and re-rate the platform on scale and ancillaries.",
            "primary / retention-gated", "ILLUSTRATIVE"),
        GrowthLever(
            "MPFS / ASC rate drag",
            "A flat-to-declining professional fee and site-neutral pressure on "
            "the ASC facility fee are the structural headwind.",
            "rate headwind", "GOV"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Colorectal-cancer screening demand (age-45 expansion × aging)",
        analysis=(
            "The dominant demand driver is colorectal-cancer screening, and it "
            "took a discrete jump in 2021 when the USPSTF lowered the average-risk "
            "start age from 50 to 45 — adding roughly 19 million newly-eligible "
            "Americans to the screening pool at once, on top of the steady aging "
            "of the population into and through the 45-75 screening window. Under "
            "the ACA that screening carries no beneficiary cost-share, which "
            "sustains access. Layered on top are diagnostic and therapeutic "
            "demand from rising GERD, IBD (~3M+ US adults), and hepatology "
            "burden. The genuine offset is non-invasive screening (stool-DNA and "
            "blood-based tests): it substitutes for some average-risk "
            "colonoscopies but feeds every positive result into a diagnostic "
            "colonoscopy, so the net effect on scope volume is directionally "
            "positive-to-ambiguous with a shift toward higher-acuity cases."),
        basis="GOV"),
    cost_drivers=[
        CostDriver(
            "Physician & advanced-practice compensation", "~40-50% of cost",
            "The dominant cost; the post-close comp model is both the biggest "
            "margin lever and the biggest retention risk.", "ILLUSTRATIVE"),
        CostDriver(
            "IBD infusion drug COGS (buy-and-bill biologics)",
            "variable / large gross",
            "The cost side of the infusion ancillary — buy-and-bill drug "
            "acquisition, where biosimilars compress the ASP+6 spread.",
            "ILLUSTRATIVE"),
        CostDriver(
            "ASC clinical staff + scope reprocessing", "~15-20% of cost",
            "Endoscopy nurses/techs and the reprocessing, capital, and supply "
            "cost of running the suite — the fixed chassis facility fees cover.",
            "ILLUSTRATIVE"),
        CostDriver(
            "MSO back office (billing/RCM, IT, compliance)", "~10-15% of cost",
            "The shared-services and compliance apparatus the ancillary-heavy "
            "structure requires.", "ILLUSTRATIVE"),
        CostDriver(
            "Pathology + facility/occupancy", "~8-12% of cost",
            "In-house lab reagents and the clinic/ASC real estate and equipment.",
            "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "No national physician-practice facility file is vendored — a GI group "
        "is a business, not a Medicare-certified facility — so state geography "
        "is omitted rather than fabricated. The most consequential geographic "
        "variables are the corporate-practice-of-medicine doctrine (strong-CPOM "
        "states force the friendly-PA/MSO structure), state ASC "
        "licensure/certificate-of-need regimes that gate where an owned "
        "endoscopy center can open, and the growing list of states enacting "
        "PE-in-healthcare transaction-review laws. The NPI-taxonomy, Medicare "
        "physician-utilization, ASC-quality, and demographic connectors linked "
        "below map gastroenterology supply and endoscopy volume against the "
        "age-45+ screening population — the honest footprint read."),
)

register(REPORT)
