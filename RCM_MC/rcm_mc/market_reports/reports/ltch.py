"""Long-Term Acute Care (LTCH) — extended-stay hospitals for the sickest patients.

Rich-data flagship: consumes ``ltch_deep_dive()`` (CMS Long-Term Care Hospital
Compare, ~320 facilities) for SOURCED live figures. The qualitative sections are
authored around the policy that redefined the sector — the FY2016 site-neutral
dual-payment system — plus the moratorium that caps supply and the ventilator-
weaning case mix that is the clinical and economic core.
"""
from __future__ import annotations

from .. import (
    CmsTrend, Competition, Connection, CostDriver, GrowthLever, HowItWorks,
    Kpi, MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule,
    Segment, Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="ltch",
    name="Long-Term Acute Care (LTCH)",
    care_setting="Post-acute",
    naics="622310",
    one_line_def=(
        "Hospitals that treat the sickest post-ICU patients — prolonged "
        "ventilator weaning, respiratory failure, complex wounds, multi-organ "
        "recovery — over extended stays (a >25-day average Medicare length of "
        "stay is the defining criterion), paid a Medicare per-discharge rate "
        "that since FY2016 splits into a full LTCH rate and a much lower site-"
        "neutral rate."),
    tam_headline=TamHeadline(
        value=4.2, unit="$B", growth_pct=0.5, basis_label="GOV",
        basis_note=(
            "Medicare FFS LTCH spending ~$4.2B across ~90-100K cases at ~340 "
            "LTCHs (MedPAC). The modeled composite is roughly flat: high-acuity "
            "demand +2.0% and rate +2.5% are largely offset by site-neutral "
            "repricing and moratorium-driven closures −4.0%."),
    ),
    executive_summary=[
        "One policy defines the economics: the FY2016 site-neutral dual-payment "
        "system. An LTCH earns the full, premium LTCH rate only on cases that "
        "qualify — an immediately preceding acute stay with ≥3 ICU/CCU days, or "
        "≥96 hours of mechanical ventilation. Everything else is paid a much "
        "lower site-neutral (acute-comparable) rate that is near breakeven or a "
        "loss, so the P&L is the qualifying-case mix.",
        "Supply is capped and shrinking by design. A long-standing moratorium "
        "bars new LTCHs and bed expansions, and site-neutral plus closures have "
        "cut the count from well over 400 to roughly 320 — this is a "
        "consolidation / last-operator-standing sector, not a growth one.",
        "Ventilator weaning and respiratory failure are the clinical and "
        "economic core — the highest-acuity, best-qualifying, longest-stay "
        "cases. A facility's value is its vent program and its referral pipeline "
        "of ICU step-downs, not bed count.",
        "It is the most concentrated post-acute vertical: two national operators "
        "— Select Medical (Select Specialty) and ScionHealth (the former "
        "Kindred Hospitals) — dominate, with a handful of regional players. The "
        "acquirable independent pool is very thin.",
        "The referral base is narrowing structurally: acute hospitals keep more "
        "complex patients, MA plans steer to cheaper vent units and SNFs, and "
        "the >25-day-ALOS certification plus the 25% Rule constrain how the "
        "business can be run — the diligence is durability, not expansion.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Prolonged ICU stay (respiratory failure, sepsis, multi-organ)",
            "Acute hospital reaches the limit of DRG-efficient care",
            "Referral to LTCH for extended, hospital-level recovery",
            "Admission screen — does the case qualify for the full LTCH rate?",
            "Extended treatment: vent weaning, complex wounds, rehab-to-tolerate",
            "Discharge to home, SNF, or IRF (discharge-to-community measure)",
            "Billing — LTCH PPS full rate (qualifying) or site-neutral rate",
            "Compliance — >25-day ALOS certification + the 25% Rule",
        ],
        sites_of_care=[
            "Free-standing long-term care hospital",
            "Hospital-within-a-hospital (co-located, distinct-provider LTCH)",
            "Satellite LTCH bed complement",
            "Specialty vent-weaning / pulmonary program within an LTCH",
        ],
        money_flow=(
            "Medicare pays per discharge under the LTCH PPS using MS-LTC-DRGs, "
            "but since FY2016 the rate a case receives depends on whether it "
            "qualifies. A case qualifies for the full standard federal LTCH rate "
            "only if the immediately preceding stay was an acute hospitalization "
            "with at least 3 days in an ICU/CCU, or the case involves at least "
            "96 hours of mechanical ventilation. Non-qualifying cases are paid a "
            "site-neutral rate benchmarked to what an acute hospital (IPPS) "
            "would receive — a fraction of the LTCH premium, typically at or "
            "below cost. Because the cost base is ICU-grade (respiratory "
            "therapists, intensivist-level physicians, high nurse ratios) and "
            "stays are very long, the entire margin lives in the qualifying-case "
            "mix; the facility must also maintain a >25-day average Medicare LOS "
            "to keep its LTCH certification."),
        key_players=(
            "The most concentrated post-acute setting. Select Medical operates "
            "the Select Specialty Hospitals network and ScionHealth carries the "
            "former Kindred Hospitals footprint — together the two national "
            "leaders — with regional operators such as PAM Health and Ernest "
            "Health and a shrinking tail of independents. The moratorium means "
            "no new entrants; growth is share and survival, so the strategic "
            "question is which operators consolidate the closing capacity, not "
            "who builds."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Medicare FFS LTCH program spend",
                    "~$4.2B",
                    "GOV · MedPAC (Medicare FFS LTCH)"),
            Segment("Annual Medicare LTCH cases",
                    "~90,000-100,000 cases",
                    "GOV · MedPAC LTCH chapter"),
            Segment("Qualifying (full-rate) vs site-neutral mix",
                    "margin lives in the qualifying share",
                    "GOV · CMS LTCH PPS dual-rate framework"),
            Segment("Certified LTCHs (US)",
                    "~320 facilities and declining",
                    "SOURCED · CMS LTCH Compare (our file)"),
            Segment("Medicare share of payer mix",
                    "~60%+ (FFS + MA)",
                    "GOV · MedPAC / CMS LTCH utilization"),
        ],
        growth_drivers=[
            "High-acuity/vent demand ~2.0%/yr — aging + ICU survivorship",
            "LTCH PPS annual rate updates ~2.5%/yr on qualifying cases",
            "Site-neutral repricing −(large) — strips the premium off non-"
            "qualifying cases",
            "Moratorium + closures −(large) — supply capped and shrinking",
            "MA / vent-unit / SNF substitution — narrows the referral base",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Medicare FFS": 0.62,
            "Medicare Advantage": 0.13,
            "Commercial": 0.15,
            "Medicaid / other": 0.10,
        },
        rate_mechanics=[
            "LTCH PPS — a per-discharge payment by MS-LTC-DRG for cases that "
            "qualify for the standard federal LTCH rate.",
            "The site-neutral (dual) payment rate — non-qualifying cases are "
            "paid an IPPS-comparable amount (the lower of a cost-based or "
            "acute-equivalent rate); this FY2016 change (Pathway for SGR Reform "
            "Act, 2013) is the defining economic fact of the sector.",
            "Qualifying criteria — the immediately preceding acute stay had ≥3 "
            "ICU/CCU days, OR the case involves ≥96 hours of mechanical "
            "ventilation; these gate the full LTCH rate.",
            ">25-day average length-of-stay certification (42 CFR 412.23(e)) — "
            "the facility must maintain a >25-day average Medicare inpatient LOS "
            "to remain classified as an LTCH.",
            "The 25% Rule (discharge-payment-percentage threshold) — a payment "
            "adjustment when too high a share of admissions comes from a single "
            "referring acute hospital, targeting hospital-within-hospital "
            "self-referral.",
            "LTCH PPS annual update + LTCH QRP quality reporting (2% penalty "
            "for non-compliance).",
        ],
        reimbursement_risk=(
            "The realized risk is already embedded and still moving: site-"
            "neutral payment stripped the premium off every non-qualifying case, "
            "so the whole business is now a bet on maintaining a high qualifying "
            "(vent/post-ICU) mix — and any tightening of the qualifying criteria "
            "or the site-neutral rate compresses it further. On top of that, the "
            "moratorium caps supply while the referral base narrows: acute "
            "hospitals increasingly manage complex patients in place or route "
            "them to cheaper vent units and SNFs, and MA plans authorize the "
            "lower-cost setting. The result is a sector where the rate premium "
            "survives only for the sickest, best-documented cases, and volume is "
            "structurally under pressure."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("LTCH Prospective Payment System (SSA §1886(m))",
                 "Sets the per-discharge MS-LTC-DRG rate for qualifying cases — "
                 "the price of the sector's economic core.",
                 "https://www.cms.gov/medicare/payment/prospective-payment-systems/long-term-care-hospital-ltch-pps"),
            Rule("Site-neutral dual-payment (Pathway for SGR Reform Act, 2013; "
                 "FY2016)",
                 "Pays non-qualifying cases an acute-comparable (site-neutral) "
                 "rate — the single policy that redefined LTCH economics and "
                 "forced the sector's consolidation.",
                 "https://www.cms.gov/medicare/payment/prospective-payment-systems/long-term-care-hospital-ltch-pps"),
            Rule(">25-day average length-of-stay certification (42 CFR "
                 "412.23(e))",
                 "The defining classification criterion — a facility must "
                 "maintain a >25-day average Medicare LOS to be an LTCH.",
                 "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-412"),
            Rule("LTCH moratorium on new facilities / beds",
                 "Bars new LTCHs and bed expansions — supply is capped, so the "
                 "sector can only shrink or consolidate, never add greenfield "
                 "capacity.",
                 "https://www.medpac.gov/"),
            Rule("The 25% Rule (discharge-payment-percentage threshold)",
                 "Adjusts payment when a single acute hospital sends too large a "
                 "share of admissions — a check on hospital-within-hospital "
                 "self-referral.",
                 "https://www.cms.gov/medicare/payment/prospective-payment-systems/long-term-care-hospital-ltch-pps"),
        ],
        policy_watch=[
            "Any tightening of the qualifying criteria or the site-neutral rate",
            "Moratorium extensions / any (unlikely) relaxation",
            "25% Rule enforcement and transition-policy changes",
            "MA authorization behavior toward LTCH versus vent units / SNFs",
            "MedPAC LTCH payment-adequacy recommendations",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "The least fragmented post-acute vertical: only ~320 LTCHs, "
            "dominated by two national operators (Select Medical and "
            "ScionHealth) plus a few regionals. For-profit ownership runs high "
            "(measured directly from our facility file below), and the "
            "moratorium means no new entrants can dilute the incumbents."),
        hhi_or_share=(
            "Two operators lead a small national field; the CMS file carries "
            "ownership TYPE but no operator name, so operator HHI is honestly "
            "omitted — but LTCH is materially more concentrated than SNF, IRF, "
            "home health, or hospice."),
        consolidation=(
            "A decade of managed decline: site-neutral payment and the "
            "moratorium drove closures, and the surviving capacity concentrated "
            "into Select and ScionHealth with regional operators (PAM Health, "
            "Ernest Health) picking up assets. The strategic logic is last-"
            "operator-standing — absorbing closing or distressed facilities and "
            "running the qualifying-case mix efficiently — not greenfield "
            "growth, which the moratorium forbids."),
        pe_activity=(
            "Sponsor activity is limited and structural: the dominant platforms "
            "are Select Medical (public) and ScionHealth (the TPG/Welsh "
            "Carson-era Kindred lineage), with regional operators carrying "
            "sponsor backing. There is little independent whitespace, and the "
            "site-neutral/moratorium overhang makes LTCH a defensive, cash-"
            "generative, consolidation play rather than a classic buy-and-build."),
        notable_players=[
            "Select Specialty Hospitals (Select Medical)",
            "ScionHealth (Kindred Hospitals)", "PAM Health",
            "Ernest Health", "Regional / independent LTCHs",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Qualifying (full-rate) case share", "the whole margin",
                "The percent of cases meeting the ≥3-ICU-day or ≥96-hour-vent "
                "criteria — site-neutral cases are near-breakeven or a loss."),
            Kpi("Average length of stay (ALOS)", ">25 days (required)",
                "Both a certification requirement and a cost driver — very long "
                "stays on an ICU-grade cost base."),
            Kpi("Ventilator / vent-weaning case mix", "core program",
                "The highest-acuity, best-qualifying, most-referred cases — the "
                "clinical and economic anchor of a strong LTCH."),
            Kpi("Occupancy", "~65-75%",
                "Fixed-cost leverage on a small bed base; a shrinking referral "
                "pool pressures fill."),
            Kpi("Discharge-to-community rate", "risk-standardized",
                "The LTCH QRP quality measure — referrer and payer confidence "
                "and public reporting."),
            Kpi("Cost per patient day", "ICU-grade",
                "Respiratory therapists, high nurse ratios, and intensivist "
                "coverage make LTCH among the costliest post-acute days."),
        ],
        margin_profile=(
            "An LTCH is an ICU-grade fixed-cost hospital running very long "
            "stays, so the margin math is unusually binary: full-rate "
            "qualifying cases (vent ≥96 hours, or post-ICU ≥3 days) carry the "
            "economics, while site-neutral cases are paid near or below cost. "
            "The result is that a facility's operating margin tracks its "
            "qualifying-case mix and its vent program almost directly — a strong "
            "LTCH with a deep vent-weaning pipeline and disciplined admission "
            "screening earns a solid margin, while one drifting into site-"
            "neutral volume bleeds. Because supply is capped and the referral "
            "base is narrowing, the durable operators are those that lock in the "
            "high-acuity referral relationships and run the qualifying mix "
            "tightly."),
    ),
    risks=[
        Risk("Site-neutral rate / qualifying-criteria tightening", "High",
             "The premium already survives only on qualifying cases; any "
             "further tightening compresses the entire margin base."),
        Risk("Shrinking referral base (acute-in-place, vent units, SNFs)",
             "High",
             "Acute hospitals keep complex patients longer and MA steers to "
             "cheaper settings, narrowing the pipeline the sector depends on."),
        Risk("Moratorium-capped, structurally declining sector", "Medium",
             "No greenfield growth is permitted; the sector can only consolidate "
             "or shrink, so the thesis is defensive."),
        Risk("Respiratory-therapist & ICU-nurse labor supply", "Medium",
             "The ICU-grade staffing model is scarce and expensive; shortages "
             "cap the vent census that drives the margin."),
        Risk("25% Rule / hospital-within-hospital scrutiny", "Medium",
             "Referral-concentration and co-location rules constrain the "
             "classic HwH operating model and its payment."),
        Risk("Concentration limits target availability", "Low",
             "Select/ScionHealth dominance and moratorium-capped supply leave "
             "few independent assets to acquire."),
    ],
    diligence_questions=[
        "What is the qualifying-case mix (≥3-ICU-day and ≥96-hour-vent) and its "
        "trend — how much of the book is full-rate versus site-neutral?",
        "How strong and defensible is the ventilator-weaning program, and how "
        "concentrated is the referral pipeline?",
        "What is the average LOS and the certification headroom above 25 days?",
        "What is the exposure to the 25% Rule and any hospital-within-hospital "
        "co-location arrangements?",
        "How is respiratory-therapist and ICU-nurse staffing sourced and "
        "priced, and what is agency reliance?",
        "What is the discharge-to-community rate and QRP standing versus peers?",
        "How exposed is the referral base to acute-hospital in-place management "
        "and MA site-of-care steering?",
        "For any distressed or closing-facility acquisitions, what are the "
        "ramp, licensure-transfer, and certification-continuity risks?",
    ],
    insider_lens=[
        "The site-neutral rule is the whole business. An LTCH only makes money "
        "on cases that qualify for the full rate — post-ICU ≥3 days or ≥96 "
        "hours on a vent — and loses money on the rest. Admissions are a "
        "qualification-screening exercise, and the qualifying mix is the single "
        "number that predicts the margin.",
        "The sector is winding down on purpose. The moratorium bars new "
        "facilities and site-neutral repriced the marginal case, so the count "
        "keeps falling. This is a last-operator-standing consolidation, not a "
        "growth market — underwrite share capture and cash generation, not "
        "expansion.",
        "Vents are the franchise. Ventilator weaning is the highest-acuity, "
        "best-qualifying, longest-stay case and the reason acute ICUs refer at "
        "all — a deep vent program and its referral relationships are the "
        "durable asset; bed count without it is a liability.",
        "The referral pipe is narrowing. Acute hospitals increasingly keep "
        "complex patients, and MA routes them to cheaper vent units or SNFs — "
        "so the LTCH's volume depends on being the indispensable step-down for "
        "the very sickest, which is a smaller pool every year.",
        "Concentration cuts both ways. Two operators dominate, so there is "
        "pricing and referral discipline but almost no independent supply to "
        "buy — the deals are distressed-asset absorption and regional "
        "consolidation, not a fragmented roll-up.",
    ],
    connections=default_connections(
        "ltch",
        deals_sector="post_acute",
        extra_pages=[
            ("/diligence/tam-sam?template=ltch",
             "LTCH deep-dive — state footprint, ownership, discharge-to-community"),
        ],
        connectors=[
            ("provider_data_ltch_general",
             "CMS LTCH Compare — facility list & quality measures"),
            ("cms_open_data_hospital_cost_report",
             "CMS Hospital Cost Report — LTCH facility cost & margin"),
            ("cms_open_data_mup_inpatient_by_provider",
             "CMS Medicare inpatient utilization by provider"),
            ("provider_data_hospital_general",
             "CMS Hospital General Info — acute referral-source mapping"),
            ("census_acs_cbsa_profile",
             "Census ACS — senior density for demand mapping"),
        ],
    ),
    sources=[
        Source("MedPAC — Report to Congress, long-term care hospital services "
               "chapter (site-neutral impact, margins, payment adequacy)",
               "GOV", "https://www.medpac.gov/"),
        Source("CMS LTCH Prospective Payment System — annual Final Rule "
               "(dual-rate, MS-LTC-DRG, market basket)", "GOV",
               "https://www.cms.gov/medicare/payment/prospective-payment-systems/long-term-care-hospital-ltch-pps"),
        Source("Pathway for SGR Reform Act of 2013 — LTCH site-neutral payment "
               "provisions (implemented FY2016)", "GOV",
               "https://www.congress.gov/bill/113th-congress/house-bill/2810"),
        Source("LTCH classification & >25-day ALOS (42 CFR 412.23(e))", "GOV",
               "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-412"),
        Source("Select Medical / ScionHealth public disclosures — the LTCH "
               "operating and vent-weaning model", "INDUSTRY",
               "https://www.selectmedical.com/"),
        Source("PE Desk industry deep-dive (CMS LTCH Compare) + realized-deal "
               "corpus", "INTERNAL", "/diligence/tam-sam?template=ltch"),
    ],
    live_figures=live_figures_from_dive("ltch"),
    trends=(
        "LTCH is a sector in managed decline. It proliferated in the early "
        "2000s — a build boom that crested before the 2007 moratorium — and then "
        "the FY2016 site-neutral dual-payment system stripped the LTCH premium "
        "off every case that did not meet the qualifying criteria, forcing a "
        "decade of closures and consolidation that cut the facility count from "
        "well over 400 to roughly 320. The demand for the highest-acuity cases "
        "— prolonged ventilator weaning, respiratory failure, complex ICU step-"
        "downs — persists and even grows with aging and ICU survivorship, but "
        "the moratorium caps supply, the referral base narrows as acute "
        "hospitals manage complex patients in place, and MA steers to cheaper "
        "settings. The net trajectory is roughly flat dollars on a shrinking "
        "footprint: the survivors are concentrated, cash-generative operators "
        "who run a tight qualifying-case mix and own the vent-weaning niche. The "
        "thesis is defensive consolidation, not growth."),
    growth_levers=[
        GrowthLever(
            "High-acuity / ventilator demand",
            "Aging and improved ICU survivorship keep producing complex, vent-"
            "dependent post-ICU patients — the LTCH's core, non-discretionary "
            "demand.",
            "+2.0%/yr demand", "GOV"),
        GrowthLever(
            "LTCH PPS annual rate updates",
            "The per-discharge rate on qualifying cases steps up with the annual "
            "market basket and wage index.",
            "+2.5%/yr rate", "ILLUSTRATIVE"),
        GrowthLever(
            "Consolidation of closing / distressed capacity",
            "With the moratorium barring greenfield, the growth lever is "
            "absorbing closing facilities and referral share — the last-"
            "operator-standing dynamic.",
            "share capture", "ILLUSTRATIVE"),
        GrowthLever(
            "Site-neutral repricing",
            "The FY2016 dual-rate strips the premium off non-qualifying cases — "
            "the dominant negative that reset the sector's economics.",
            "−(large) margin", "GOV"),
        GrowthLever(
            "Moratorium + referral-base erosion",
            "No new supply is permitted while acute-in-place management and MA "
            "steering narrow the referral pool — a structural volume drag.",
            "−(large) volume", "GOV"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Qualifying high-acuity ICU step-downs (esp. ventilator weaning), "
               "net of referral-base erosion",
        analysis=(
            "LTCH demand is the narrowest and most acute in post-acute: it is "
            "the flow of patients who survive an ICU stay but cannot yet be "
            "managed in a lower setting — prolonged ventilator weaning, "
            "respiratory failure, complex wounds, multi-organ recovery. That "
            "clinical need grows with the aging population and with ICU "
            "survivorship (more patients live through critical illness into a "
            "prolonged-recovery phase). But unlike other post-acute settings, "
            "the realized LTCH volume is capped and squeezed from three sides: "
            "the moratorium forbids adding beds, acute hospitals increasingly "
            "keep these patients in place or in their own vent units, and MA "
            "plans authorize cheaper alternatives. So the dominant driver is "
            "qualifying high-acuity incidence — above all ventilator cases — but "
            "the sector captures a shrinking share of it, which is why volume is "
            "structurally flat-to-down even as the underlying clinical need rises."),
        basis="GOV"),
    cost_drivers=[
        CostDriver(
            "ICU-grade nursing & respiratory therapy",
            "~45-55% of cost",
            "High nurse ratios plus respiratory therapists for the vent census — "
            "the dominant, scarce, expensive labor line that runs the whole "
            "care model.", "ILLUSTRATIVE"),
        CostDriver(
            "Physician / intensivist coverage",
            "~10-15% of cost",
            "Hospital-level and intensivist medical direction for a medically "
            "complex census — a required, fixed professional cost.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Facility / occupancy (owned or co-located)",
            "~10-15% of cost",
            "Hospital-grade real estate; for hospital-within-hospital models the "
            "co-location and lease economics with the host acute hospital.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Pharmacy, supplies & ancillary services",
            "~12-18% of cost",
            "Intensive drug regimens, wound and vent supplies, dialysis and "
            "diagnostics on a very long stay.", "ILLUSTRATIVE"),
        CostDriver(
            "G&A, compliance & professional liability",
            "~8-12% of cost",
            "Corporate overhead plus the QRP, certification, and 25%-Rule "
            "compliance apparatus and liability coverage.", "ILLUSTRATIVE"),
    ],
    cms_trend=CmsTrend(
        takeaway=(
            "The LTCH certification vintage captures the sector's arc in one "
            "curve: the heaviest build cohort is the early-2000s boom, and there "
            "is essentially nothing recent — the fingerprint of a moratorium "
            "that barred new facilities and a site-neutral policy that forced "
            "closures. Read the absence of new cohorts as the structural signal: "
            "supply is capped and declining, so the investable action is "
            "consolidating the surviving, qualifying-mix-rich operators, not "
            "adding capacity."),
        chart_kind="bars"),
    state_breakdown=(
        "LTCHs concentrate in the large Sun Belt and industrial states (Texas "
        "and Florida lead the count), reflecting where the early-2000s build "
        "boom landed before the moratorium froze supply. For-profit ownership "
        "runs high nationally, consistent with the two big for-profit operators. "
        "The CMS file carries ownership TYPE but no operator name, so the "
        "Select/ScionHealth concentration is described qualitatively rather than "
        "computed as an HHI — but LTCH is the most operator-concentrated post-"
        "acute vertical in our files.")
)

register(REPORT)
