"""Urgent Care — walk-in, extended-hours episodic acute care.

Deals-only deep-dive (no CMS urgent-care provider type or file; the Urgent Care
Association census is proprietary). Urgent care bills like a physician office —
there is no facility fee — so the qualitative sections are authored around
throughput economics, the commercial/self-pay payer mix, the COVID testing
windfall and its reversal, and the Corporate-Practice-of-Medicine ownership
structure. Consumes ``urgent_care_deep_dive()`` for SOURCED corpus deal figures.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="urgent_care",
    name="Urgent Care",
    care_setting="Ambulatory",
    naics="621498",
    one_line_def=(
        "Walk-in, extended-hours clinics that treat episodic, non-life-"
        "threatening acute illness and minor injury — the middle tier between "
        "primary care and the emergency department — staffed by physicians, "
        "NPs, and PAs, paid like a physician office on E/M office-visit codes "
        "with no separate facility fee, and heavily commercial/self-pay."),
    tam_headline=TamHeadline(
        value=35.0, unit="$B", growth_pct=5.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "US urgent-care industry revenue is not a single published figure "
            "(the Urgent Care Association center census is proprietary); ~$35B "
            "is the modeled composite of ~11,000+ centers × visits/clinic × "
            "net revenue/visit. Growth is the modeled composite of demand, de "
            "novo build, and the post-COVID testing-revenue reversal."),
    ),
    executive_summary=[
        "Urgent care is a retail throughput business, not a facility business. "
        "There is no facility fee — the clinic is paid like a physician office "
        "— so value is visits/clinic/day × net revenue/visit × labor "
        "productivity. The model loses money below a volume threshold and "
        "scales fast above it.",
        "Payer mix is commercial- and self-pay-heavy, and that IS the point: "
        "commercial and cash pay far more than Medicaid for the same low-"
        "acuity E/M visit, and Medicare is a small share. De novo site "
        "selection is a payer-mix bet as much as a demography bet.",
        "The census exploded then saturated. COVID testing and vaccination "
        "turned 2020-2022 into a windfall and pulled a wave of new clinics "
        "into the market; that revenue has fully evaporated, so trailing "
        "financials on the 2020-2022 vintage overstate the normalized run-"
        "rate. Underwrite the post-2022 base.",
        "Consolidation is a barbell — national/regional platforms (many now "
        "payer- or system-owned: Optum's MedExpress, HCA's CareNow, GoHealth "
        "system JVs) plus a very long independent and franchise tail (American "
        "Family Care). The strategic buyer increasingly wants the low-acuity "
        "front door, not just the clinic EBITDA.",
        "Reimbursement risk is rate and code: urgent care is paid on E/M "
        "office codes (99202-99215) plus separately-billed point-of-care "
        "tests, X-ray, and procedures — but some payers cap it with a flat "
        "S9083 per-visit rate, and payer downcoding, telehealth, and retail "
        "clinics all press on the modest per-visit economics.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Walk-in or online check-in → registration + eligibility",
            "Triage (acuity screen; ED transfer if needed)",
            "Provider visit (NP / PA / physician)",
            "Point-of-care testing (rapid strep/flu/COVID, urinalysis, X-ray)",
            "Treatment / procedure (laceration repair, splinting, injections)",
            "Discharge + prescription / PCP follow-up referral",
            "E/M + ancillary coding → claim or cash collection",
        ],
        sites_of_care=[
            "Freestanding urgent care (retail strip / standalone box)",
            "Hospital- or health-system-affiliated urgent care",
            "Hybrid urgent care + occupational health",
            "Virtual / telehealth triage front-end",
            "Freestanding ED — a distinct, higher-acuity competing site",
        ],
        money_flow=(
            "Urgent care bills the professional E/M office-visit codes "
            "(99202-99215, new vs established) on the Medicare Physician Fee "
            "Schedule or its commercial equivalent, plus separate codes for "
            "point-of-care tests, X-rays, injections, and procedures. There is "
            "generally NO separate facility fee (unlike a hospital outpatient "
            "department), so the clinic is paid like a physician office and the "
            "economics are pure throughput: net revenue per visit is modest "
            "(~$150-250 commercial, far less for Medicaid), and profit comes "
            "from volume against a fixed rent-and-staff base. Some commercial "
            "payers reimburse a flat per-visit 'global' urgent-care rate "
            "(S9083) or an after-hours add-on (S9088) instead of itemized E/M. "
            "Self-pay/cash is a meaningful, high-margin slice."),
        key_players=(
            "A fragmented field. Larger platforms and franchises include "
            "American Family Care (AFC), MedExpress (Optum/UnitedHealth), "
            "CityMD (Summit Health/VillageMD), GoHealth Urgent Care (health-"
            "system JVs), NextCare, FastMed, CareNow (HCA), and the occ-health-"
            "heavy Concentra. Payers and health systems increasingly own the "
            "front door to steer downstream referrals; the rest is regional "
            "chains and independents."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("US urgent care centers", "~11,000-14,000",
                    "INDUSTRY · Urgent Care Association center census"),
            Segment("Net revenue / visit (commercial)", "~$150-250",
                    "ILLUSTRATIVE · modeled per-visit economics"),
            Segment("Commercial + self-pay share of revenue",
                    "the majority — clears the fixed base",
                    "ILLUSTRATIVE · modeled payer mix"),
            Segment("COVID testing / vaccination windfall (2020-2022)",
                    "a revenue spike, since fully normalized",
                    "ILLUSTRATIVE · directional (post-COVID reversal)"),
            Segment("Visits / mature clinic / day", "~35-50",
                    "ILLUSTRATIVE · modeled throughput at maturity"),
        ],
        growth_drivers=[
            "ED-diversion + convenience demand for low-acuity acute care",
            "Primary-care access gaps push episodic care to walk-in sites",
            "Retailization + consumer expectation of on-demand care",
            "Formulaic de novo real-estate roll-out",
            "Offsets: post-COVID testing cliff, telehealth, and saturation",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Commercial": 0.58,
            "Medicaid": 0.16,
            "Medicare / MA": 0.13,
            "Self-pay / other": 0.13,
        },
        rate_mechanics=[
            "Paid like a physician office on E/M codes (99202-99215) on the "
            "MPFS or commercial equivalent — there is no separate facility fee "
            "to cushion the model.",
            "Point-of-care ancillaries billed separately — rapid strep/flu/"
            "COVID, urinalysis, X-ray, injections, laceration repair, splinting "
            "— a meaningful revenue and margin layer.",
            "Urgent-care 'global' / per-visit codes — some commercial payers "
            "pay a flat S9083 per-visit rate (or an S9088 after-hours add-on) "
            "instead of itemized E/M, capping revenue per visit.",
            "Cash / self-pay pricing — transparent flat visit prices; high-"
            "margin and a real share of volume.",
            "Payer contracting & steerage — in-network status and 'urgent care "
            "vs ED' cost-share differentials drive volume; E/M downcoding "
            "audits (99204/99214) are a live risk.",
            "Occupational-health / employer + workers'-comp direct contracts — "
            "pay well and smooth seasonal volume.",
        ],
        reimbursement_risk=(
            "With no facility fee and a modest per-visit rate, margin is "
            "entirely throughput and coding integrity. Three threats press on "
            "it: payer downcoding and E/M audit (urgent care skews to the "
            "higher-level 99204/99214 codes payers scrutinize); the flat S9083 "
            "per-visit rate caps revenue regardless of visit intensity, so "
            "coding-up does not help where it applies; and telehealth plus "
            "retail/pharmacy clinics substitute for the lowest-acuity visits. "
            "The 2020-2022 COVID testing/vaccination windfall inflated a cohort "
            "of clinics and has since evaporated, so trailing financials can "
            "badly overstate the normalized run-rate. Medicaid-heavy or under-"
            "trafficked locations struggle to clear the fixed rent-and-staff "
            "base at all."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("State clinic licensure + Corporate Practice of Medicine "
                 "(CPOM)",
                 "Many states bar non-physician (PE) ownership of the clinical "
                 "entity, forcing MSO / friendly-PC structures — the ownership "
                 "backbone of every platform.",
                 None),
            Rule("E/M documentation & coding rules (2021 office-visit "
                 "revision)",
                 "Visit-level selection (99213 vs 99214) drives revenue and is "
                 "the primary payer-audit and downcoding exposure.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/physician/evaluation-management-visits"),
            Rule("CLIA certification for point-of-care testing",
                 "A Clinical Laboratory Improvement Amendments certificate is "
                 "required to run the rapid strep/flu/COVID and other waived "
                 "tests that anchor urgent-care ancillary revenue.",
                 "https://www.cms.gov/medicare/quality/clinical-laboratory-improvement-amendments"),
            Rule("Scope-of-practice / NP-PA supervision laws (state)",
                 "Independent-NP-practice states are materially cheaper to "
                 "staff and set the whole labor model and cost structure.",
                 None),
            Rule("Urgent-care vs freestanding-ED disclosure rules (state)",
                 "Signage and billing-transparency laws tightening around what "
                 "may call itself 'emergency' — a consumer-protection and "
                 "billing-integrity exposure.",
                 None),
        ],
        policy_watch=[
            "Telehealth parity and its substitution for low-acuity visits",
            "Payer 'urgent care vs ED' site-of-service cost-share steerage",
            "E/M downcoding audit intensity",
            "CPOM enforcement / MSO-structure scrutiny in key states",
            "Scope-of-practice expansion (independent NP practice) lowering "
            "labor cost",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Thousands of centers (the Urgent Care Association counts "
            "~11,000+), heavily fragmented across national franchises, "
            "regional chains, health-system-affiliated clinics, payer-owned "
            "platforms, and independents. No single owner dominates and the "
            "long independent/franchise tail is the acquirable pool."),
        hhi_or_share=(
            "No dominant national owner — the largest platforms (AFC, "
            "MedExpress/Optum, CityMD, GoHealth, Concentra) each hold low-"
            "single-digit share. No public facility file carries an operator "
            "field, so a chain HHI is honestly omitted."),
        consolidation=(
            "A consolidation wave led increasingly by payers and health "
            "systems that want to own the low-acuity front door and feed "
            "downstream referrals — Optum (MedExpress), HCA (CareNow), the "
            "Walgreens/VillageMD-CityMD adjacency, and system JVs (GoHealth). "
            "Franchise models (AFC) scale the independent tail. The COVID "
            "cohort's normalization triggered distress, closures, and tuck-in "
            "opportunities."),
        pe_activity=(
            "PE built and flipped several regional platforms in the 2010s, "
            "many exiting to strategics and payers. Current PE interest is more "
            "selective — occupational-health-anchored platforms (Concentra "
            "spun from Select Medical), multi-site regional roll-ups with real "
            "commercial mix, and hybrid urgent-care/primary-care/occ-health "
            "models. The COVID windfall and its reversal made normalized-EBITDA "
            "quality-of-earnings the central diligence question."),
        notable_players=[
            "American Family Care (AFC)", "MedExpress (Optum)",
            "CityMD (Summit / VillageMD)", "GoHealth Urgent Care",
            "Concentra", "NextCare", "CareNow (HCA)", "FastMed",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Visits / clinic / day (mature)", "35-50",
                "The core throughput metric; break-even sits around ~25-30 "
                "visits/day against the fixed base."),
            Kpi("Net revenue / visit (blended)", "$110-170",
                "Modest — commercial ~$150-250, Medicaid far lower; the blend "
                "follows payer mix."),
            Kpi("Provider productivity (visits / provider / hour)", "3-5",
                "Labor is the swing cost; NP/PA staffing leverage lowers cost "
                "per visit."),
            Kpi("Commercial + self-pay mix", "55-70% of visits",
                "Determines whether a clinic clears its fixed rent-and-staff "
                "base."),
            Kpi("Ramp to maturity", "18-36 months",
                "De novo clinics burn cash until they cross the volume "
                "threshold — the maturity curve drives portfolio value."),
            Kpi("Clinic EBITDA margin (mature)", "12-20%",
                "Thinner than facility-fee models; throughput and labor "
                "productivity are everything."),
        ],
        margin_profile=(
            "Urgent care is a fixed-cost box: rent in a visible retail "
            "location, a provider (increasingly NP/PA), a couple of "
            "techs/MAs, and point-of-care lab/X-ray. Below a volume threshold "
            "(~25-30 visits/day) the clinic loses money; above it, incremental "
            "visits drop to strong contribution margin because staff and rent "
            "are fixed. Mature, well-located, commercially-mixed clinics run "
            "mid-teens EBITDA margin, but a de novo burns cash for 18-36 months "
            "and a Medicaid-heavy or under-trafficked site can stay underwater. "
            "There is no facility fee to cushion the model — margin is "
            "throughput × payer mix × labor productivity."),
    ),
    risks=[
        Risk("COVID-windfall normalization / stale trailing financials",
             "High",
             "2020-2022 testing and vaccination revenue inflated a cohort of "
             "clinics; the normalized run-rate can be far below trailing."),
        Risk("Payer downcoding + E/M audit + flat per-visit (S9083) rates",
             "High",
             "Directly caps the modest per-visit revenue that is the whole "
             "margin."),
        Risk("Telehealth / retail-pharmacy clinic substitution", "Medium",
             "Pulls the lowest-acuity visits away from the clinic."),
        Risk("Saturation / cannibalization in dense metros", "Medium",
             "Over-built markets split the same episodic-visit pool."),
        Risk("Provider labor cost & availability", "Medium",
             "NP/PA/physician wages and staffing gate throughput and de novo "
             "expansion."),
        Risk("CPOM / MSO structure + de novo ramp risk", "Medium",
             "Friendly-PC compliance plus the long, cash-burning ramp to "
             "breakeven on new sites."),
    ],
    diligence_questions=[
        "What is the COVID-normalized visit and revenue run-rate by clinic, "
        "stripping out testing/vaccination — how do 2019 and post-2022 comps "
        "look?",
        "What is the payer mix and net revenue per visit by clinic, and how "
        "many sites clear the fixed-cost breakeven?",
        "What is the E/M coding distribution (99204/99214 share), and what is "
        "the payer downcoding and audit history?",
        "How many clinics are still ramping (<24 months), and what is the "
        "maturity curve to steady-state volume?",
        "Which payers reimburse itemized E/M versus a flat S9083 per-visit "
        "rate, and what is the mix?",
        "How is the entity structured for Corporate Practice of Medicine "
        "(MSO / friendly-PC), and is it compliant in each state of operation?",
        "What is the local competitive density (other urgent cares, "
        "freestanding EDs, retail clinics, telehealth) per site?",
        "What is the occupational-health / employer-contract contribution and "
        "how durable is it?",
    ],
    insider_lens=[
        "The COVID cohort is a trap. Clinics opened or juiced in 2020-2022 "
        "rode a testing/vaccination windfall that has fully reversed — "
        "trailing EBITDA on that vintage overstates the normalized business. "
        "Always underwrite the post-2022 run-rate.",
        "There is no facility fee, so this is a retail-throughput business, "
        "not a healthcare-facility business. The model is visits/day × net "
        "revenue/visit × labor productivity — it behaves more like fast-casual "
        "than an ASC.",
        "Site selection is a payer-mix bet. Two clinics a mile apart can have "
        "wildly different economics because one draws commercial and self-pay "
        "while the other draws Medicaid — the demographics of the strip "
        "determine the margin.",
        "The strategic buyer is now the payer or the system. They want the "
        "low-acuity front door to steer downstream referrals and manage total "
        "cost — which prices independents on referral value, not just clinic "
        "EBITDA.",
        "The S9083 flat per-visit rate is a silent margin cap. Where a big "
        "commercial payer pays one flat rate per visit regardless of "
        "intensity, coding-up does nothing — volume and cost control are the "
        "only levers, and that reshapes the whole thesis.",
    ],
    connections=default_connections(
        "urgent_care",
        deals_sector="urgent_care",
        extra_pages=[
            ("/industry/urgent_care",
             "Industry deep-dive — urgent care deal history + structure"),
        ],
        connectors=[
            ("npi_provider_taxonomy",
             "NPI taxonomy — urgent-care clinic + NP/PA census & staffing"),
            ("census_acs_cbsa_profile",
             "Census ACS — catchment demographics & commercial-payer density "
             "for site selection"),
            ("hrsa_data_hpsa_primary_care",
             "HRSA HPSA — primary-care shortage areas (the access gap urgent "
             "care fills)"),
            ("cms_open_data_medicare_telehealth_trends",
             "CMS Medicare Telehealth Trends — low-acuity substitution signal"),
            ("cms_open_data_mup_physician_by_geo_service",
             "Medicare physician utilization by geography — E/M office-visit "
             "pattern"),
        ],
    ),
    sources=[
        Source("Urgent Care Association (UCA) — Benchmarking Report + center "
               "census", "INDUSTRY", "https://www.ucaoa.org/"),
        Source("CMS — Medicare Physician Fee Schedule + E/M office-visit "
               "documentation (2021 revision)", "GOV",
               "https://www.cms.gov/medicare/payment/fee-schedules/physician/evaluation-management-visits"),
        Source("Health Affairs — urgent care centers and emergency-department "
               "diversion / non-emergent visit demand", "ACADEMIC",
               "https://www.healthaffairs.org/"),
        Source("CMS — Clinical Laboratory Improvement Amendments (CLIA), "
               "waived point-of-care testing", "GOV",
               "https://www.cms.gov/medicare/quality/clinical-laboratory-improvement-amendments"),
        Source("CMS — Medicare Telehealth Trends (utilization substitution)",
               "GOV",
               "https://www.cms.gov/data-research/statistics-trends-reports/medicare-telehealth-trends"),
        Source("PE Desk industry deep-dive (urgent care) + realized-deal "
               "corpus", "INTERNAL",
               "/diligence/tam-sam?template=urgent_care"),
    ],
    live_figures=live_figures_from_dive("urgent_care"),
    trends=(
        "The urgent-care census roughly doubled over the 2010s as consumers "
        "embraced on-demand, extended-hours care and payers embraced ED "
        "diversion — then COVID super-charged it: rapid testing and "
        "vaccination turned 2020-2022 into a revenue windfall and pulled a "
        "wave of new clinics into the market. That windfall has fully "
        "reversed — testing revenue evaporated in 2023-2024 and the 2020-2022 "
        "vintage is now lapping brutal comps, triggering distress, closures, "
        "and tuck-in consolidation. The durable trends underneath are "
        "structural: primary-care access gaps and consumer convenience keep "
        "episodic demand flowing to walk-in sites, and ownership is shifting "
        "toward payers and health systems (Optum, HCA, system JVs) that want "
        "the low-acuity front door as a referral and total-cost-of-care "
        "control point. The headwinds are telehealth and retail/pharmacy "
        "clinics competing for the lowest-acuity visits, and payer downcoding "
        "and flat per-visit rates capping the modest per-visit economics. The "
        "center of gravity for value is a normalized, commercially-mixed, "
        "well-located clinic base — not the COVID-peak run-rate."),
    growth_levers=[
        GrowthLever(
            "Convenience / ED-diversion demand",
            "Consumers and payers route low-acuity acute care away from the "
            "far-costlier ED and long PCP wait-lists — the primary demand "
            "engine.",
            "primary", "ILLUSTRATIVE"),
        GrowthLever(
            "De novo real-estate roll-out",
            "A formulaic site model (visible retail, extended hours) expands "
            "the clinic base where payer mix supports it.",
            "+ sites", "ILLUSTRATIVE"),
        GrowthLever(
            "Primary-care access gap",
            "Constrained PCP capacity and shortage areas push episodic acute "
            "visits to walk-in urgent care.",
            "+ episodic volume", "ILLUSTRATIVE"),
        GrowthLever(
            "Occupational-health / employer contracts",
            "Workers'-comp and employer direct contracts add payer-rich, "
            "schedulable volume that smooths seasonality.",
            "+ payer-rich volume", "ILLUSTRATIVE"),
        GrowthLever(
            "COVID-normalization + telehealth substitution drag",
            "The testing-revenue cliff plus virtual-visit and retail-clinic "
            "substitution remove volume and revenue per visit.",
            "− normalization drag", "ILLUSTRATIVE"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Episodic low-acuity acute visits × where consumers choose "
               "to have them",
        analysis=(
            "The dominant demand driver is the pool of episodic, low-acuity "
            "acute-care visits and the site a consumer chooses. Structural "
            "forces route a rising share to urgent care: primary-care access "
            "is constrained (long PCP waits, shortage areas), consumers expect "
            "on-demand extended-hours care, and payers actively steer low-"
            "acuity visits out of the far-costlier emergency department. The "
            "demand is season- and weather-sensitive — flu and respiratory "
            "season drive a sharp winter peak. COVID distorted the trend "
            "(testing and vaccination spiked then collapsed), so the honest "
            "underlying driver is the non-COVID acute-visit base, which grows "
            "with population, insurance coverage, and the persistence of the "
            "primary-care access gap. The offsets are telehealth and "
            "retail/pharmacy clinics competing for the very lowest-acuity "
            "visits, and saturation cannibalizing volume where clinics are "
            "over-built."),
        basis="ILLUSTRATIVE"),
    cost_drivers=[
        CostDriver(
            "Provider & clinical labor (physician / NP / PA + MA/techs)",
            "~40-50% of cost",
            "The dominant cost; NP/PA staffing leverage and provider "
            "productivity set the whole model.", "ILLUSTRATIVE"),
        CostDriver(
            "Occupancy / rent (visible retail real estate)",
            "~12-18% of cost",
            "Fixed — the location that drives volume is also the biggest fixed "
            "cost.", "ILLUSTRATIVE"),
        CostDriver(
            "Point-of-care lab, imaging & medical supplies",
            "~10-15% of cost",
            "Rapid tests, X-ray, injectables, and procedure supplies — the "
            "ancillary layer that also carries margin.", "ILLUSTRATIVE"),
        CostDriver(
            "Billing, RCM & payer-contract management",
            "~5-8% of cost",
            "E/M coding integrity and denials management directly protect the "
            "modest per-visit revenue.", "ILLUSTRATIVE"),
        CostDriver(
            "Marketing & G&A (brand, local demand-gen)",
            "~5-10% of cost",
            "Consumer acquisition matters in a retail model — a real, ongoing "
            "cost, not overhead to strip.", "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "No national all-payer urgent-care facility file is vendored (the "
        "Urgent Care Association census is proprietary), so state geography is "
        "omitted rather than fabricated. Qualitatively, density is highest in "
        "fast-growing Sun Belt and suburban metros (Texas, Florida, the "
        "Carolinas, Arizona) where retail expansion, commercial-payer density, "
        "and primary-care access gaps align; scope-of-practice laws "
        "(independent-NP-practice states are cheaper to staff) and Corporate-"
        "Practice-of-Medicine rules shape how ownership is structured state by "
        "state. The NPI taxonomy and Census ACS connectors below support a "
        "real site-and-catchment read."),
)

register(REPORT)
