"""Home Care — non-medical personal care / private-duty home care.

Deals-only deep-dive (no vendored national personal-care agency file; state
registries are fragmented). Authored around the two-payer split that defines the
sector: private-pay consumer home care versus Medicaid personal-care services,
the caregiver-supply constraint that actually governs revenue, and the two
margin-resetting rules of the decade — the FLSA Home Care Rule and the 2024
Medicaid Access "80/20" mandate. NOT the Medicare home health benefit (that is
its own report, ``home_health``).
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks,
    Kpi, MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule,
    Segment, Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="home_care",
    name="Home Care",
    care_setting="Post-acute",
    naics="624120",
    one_line_def=(
        "Non-medical personal care and companionship in the home — help with "
        "activities of daily living (bathing, dressing, transfers, toileting, "
        "meal prep) delivered by aides and billed by the hour — paid mostly by "
        "Medicaid HCBS, private funds, the VA, and long-term-care insurance, "
        "NOT the Medicare home health benefit."),
    tam_headline=TamHeadline(
        value=45.0, unit="$B", growth_pct=7.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "Modeled US non-medical/personal-care home-care spend — the "
            "composite of Medicaid personal-care services (the largest slice "
            "of the ~$125B national HCBS spend), private-pay, and VA/LTC-"
            "insurance. Growth is the modeled composite of demographic demand "
            "(+3%), HCBS rebalancing (+2%), and wage-driven rate updates "
            "(+2-3%). Anchored to KFF HCBS spending and BLS employment, not a "
            "single filed figure."),
    ),
    executive_summary=[
        "There are two different businesses under one label. Private-pay home "
        "care is a consumer, referral-and-marketing business at 30-40% gross "
        "margin; Medicaid personal care is a high-volume, state-rate-taker "
        "business at 20-25%. Diligence must never blend them — they have "
        "different payers, margins, growth, and regulatory exposure.",
        "The binding constraint is caregiver SUPPLY, not demand. Demand is "
        "effectively unlimited; the whole operational game is recruiting and "
        "retaining aides against 60-80%+ annual turnover. Authorized hours you "
        "cannot staff are lost revenue.",
        "Two rules reset the economics. The FLSA Home Care Rule (2015) ended "
        "the companionship overtime exemption for agency employees; the 2024 "
        "Medicaid Access Rule '80/20' provision requires 80% of HCBS personal-"
        "care payments to reach the direct-care worker — an existential margin "
        "reset for Medicaid-heavy agencies as it phases in.",
        "On the Medicaid side you are a price-taker: the state (or its MLTSS "
        "plan) sets the hourly rate and authorizes the hours per client. Your "
        "only levers are caregiver cost and back-office overhead.",
        "Extreme fragmentation. Private pay is a franchise landscape (Home "
        "Instead/Honor, Comfort Keepers, Right at Home, Visiting Angels); "
        "Medicaid is a PE roll-up landscape (Help at Home, Addus, All Ways "
        "Caring). Electronic Visit Verification (EVV) is now table stakes.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Referral or inquiry (discharge planner, family, aging network, "
            "Medicaid case manager)",
            "Assessment + plan of care (ADL needs, hours, private-pay vs "
            "Medicaid authorization)",
            "Caregiver recruiting, screening, and background check",
            "Scheduling / matching a caregiver to the client's authorized hours",
            "Shift delivery in the home + Electronic Visit Verification (EVV) "
            "clock-in/out",
            "Billing — private-pay invoice, or Medicaid/MLTSS hourly claim",
            "Supervision, reassessment, and reauthorization of hours",
        ],
        sites_of_care=[
            "Private residence / apartment (the overwhelming majority)",
            "Assisted-living or senior-housing unit (care brought to the "
            "resident)",
            "Family/kinship home (paid family caregiver where the state "
            "allows it)",
        ],
        money_flow=(
            "Revenue is hours × an hourly bill rate. On the private-pay side a "
            "family pays out of pocket — a bill rate of roughly $30-40/hour "
            "against a caregiver wage of ~$15-18/hour, with the spread covering "
            "recruiting, scheduling, supervision, workers' comp, and margin. On "
            "the Medicaid side the state (directly, or through an MLTSS managed-"
            "care plan) sets the hourly rate and authorizes a weekly hour "
            "budget per client; the agency bills that rate and captures the "
            "spread over caregiver wages. Because the model is a labor arbitrage "
            "on a fixed hourly rate, margin is decided almost entirely by "
            "caregiver wage, utilization, and turnover — and, on Medicaid, by "
            "the state rate, which the agency does not control."),
        key_players=(
            "Two distinct competitive sets. Private-pay is dominated by "
            "franchised brands: Home Instead (now owned by Honor Technology), "
            "Comfort Keepers (Sodexo), Right at Home, Visiting Angels, "
            "BrightStar Care, Griswold, and Senior Helpers. The Medicaid "
            "personal-care side is where the scaled PE-backed platforms live: "
            "Help at Home, Addus HomeCare, All Ways Caring (BrightSpring), Care "
            "Advantage, and a long tail of regional agencies. Honor Technology "
            "is the notable tech-enabled disruptor after absorbing Home "
            "Instead's franchise network."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Medicaid personal-care services (HCBS)",
                    "largest payer slice",
                    "GOV · KFF/CMS Medicaid HCBS spending (~$125B all HCBS)"),
            Segment("Private-pay / out-of-pocket home care",
                    "the high-margin consumer segment",
                    "ILLUSTRATIVE · modeled private-pay share of home-care "
                    "spend"),
            Segment("VA (Homemaker/Home Health Aide, Veteran-Directed Care)",
                    "a stable, higher-rate niche",
                    "GOV · VA community-care programs"),
            Segment("Long-term-care insurance + MA supplemental (SSBCI)",
                    "small but growing new payer channels",
                    "ILLUSTRATIVE · modeled emerging-payer share"),
        ],
        growth_drivers=[
            "85+ population growth ~3%/yr — the highest-need, highest-hours "
            "cohort",
            "Medicaid HCBS rebalancing +2%/yr — states shifting spend from "
            "institutions to home",
            "Wage-driven rate updates +2-3%/yr — states raising rates to fund "
            "caregiver pay",
            "Medicare Advantage in-home supplemental benefits — a genuinely new "
            "payer channel",
            "Aging-in-place preference — durable consumer demand for private "
            "pay",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Medicaid (state plan + HCBS waivers + MLTSS)": 0.55,
            "Private pay / out-of-pocket": 0.30,
            "VA / long-term-care insurance / other": 0.15,
        },
        rate_mechanics=[
            "Medicaid personal care — state-plan benefit plus 1915(c) HCBS "
            "waivers, 1915(i)/(j)/(k) and Community First Choice; each state "
            "sets its own hourly rate, so economics are state-by-state.",
            "MLTSS (managed long-term services and supports) — many states now "
            "route personal care through Medicaid managed-care plans, adding a "
            "payer layer that sets rates and authorizes hours.",
            "Private pay — an hourly bill rate set by the agency (~$30-40/hr); "
            "the only truly market-priced segment, and the margin engine.",
            "VA — Homemaker/Home Health Aide, Veteran-Directed Care, and "
            "Aid & Attendance; typically higher, more stable rates than "
            "Medicaid.",
            "Electronic Visit Verification (EVV) — the 21st Century Cures Act "
            "mandate; GPS/telephony visit capture is now a condition of "
            "Medicaid payment.",
            "The 2024 Medicaid Access Rule '80/20' — as it phases in, 80% of "
            "HCBS personal-care payment must go to direct-care worker "
            "compensation, capping agency overhead + margin on Medicaid hours.",
        ],
        reimbursement_risk=(
            "The dominant reimbursement risk is Medicaid rate adequacy versus "
            "caregiver wages. When a state's hourly rate lags the local wage "
            "for an aide, the agency cannot recruit and authorized hours go "
            "unstaffed — revenue you are entitled to but cannot bill. The 2024 "
            "'80/20' Access Rule compounds this by mandating that 80% of "
            "personal-care payment reach the worker, structurally capping the "
            "overhead-plus-margin share on Medicaid volume and pressuring "
            "sub-scale agencies. EVV adds compliance cost and denies claims for "
            "unverified visits. Private-pay carries a different risk: it is "
            "discretionary and rate-sensitive, tied to the family's ability to "
            "pay (often from a home sale or savings), so it softens in a "
            "downturn even as Medicaid demand holds."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("FLSA Home Care Final Rule (2013, effective 2015)",
                 "Ended the companionship-services minimum-wage/overtime "
                 "exemption for aides employed by third-party agencies — a "
                 "direct, permanent cost and scheduling constraint.",
                 "https://www.dol.gov/agencies/whd/direct-care"),
            Rule("Medicaid Access Rule — HCBS '80/20' payment provision (2024)",
                 "Requires 80% of Medicaid personal-care payments to reach the "
                 "direct-care worker; the single biggest margin variable for "
                 "Medicaid-heavy agencies as it phases in over six years.",
                 "https://www.cms.gov/newsroom/fact-sheets/ensuring-access-medicaid-services-final-rule-cms-2442-f"),
            Rule("Electronic Visit Verification (21st Century Cures Act §12006)",
                 "Mandates GPS/telephony verification of Medicaid personal-care "
                 "and home-health visits; non-compliant claims are denied.",
                 "https://www.medicaid.gov/medicaid/home-community-based-services/guidance/electronic-visit-verification-evv/index.html"),
            Rule("HCBS Settings Rule (42 CFR 441)",
                 "Defines what qualifies as a community-based (vs "
                 "institutional) setting for HCBS payment — shapes where and "
                 "how personal care can be delivered.",
                 "https://www.medicaid.gov/medicaid/home-community-based-services/guidance/home-community-based-services-final-regulation/index.html"),
            Rule("State home-care agency licensure + caregiver registries",
                 "Licensure, background-check, and training rules vary widely "
                 "by state (some do not license non-medical home care at all) — "
                 "a patchwork that shapes entry and M&A.",
                 None),
        ],
        policy_watch=[
            "80/20 rule phase-in timeline, litigation, and state "
            "implementation variance",
            "State Medicaid personal-care rate actions (the core revenue "
            "variable)",
            "Paid-family-caregiver policies (many expanded during COVID; "
            "permanence varies)",
            "Medicare Advantage supplemental in-home benefits (SSBCI) scope and "
            "uptake",
            "Direct-care workforce initiatives, minimum-wage moves, and "
            "immigration policy (the labor pool)",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Among the most fragmented healthcare services verticals — tens of "
            "thousands of agencies, most small and local. The fragmentation is "
            "structural: low capital intensity, local caregiver labor pools, "
            "and (in many states) light licensure make entry easy, so the "
            "acquirable long tail is enormous but each unit is caregiver-supply-"
            "constrained."),
        hhi_or_share=(
            "No national operator holds a meaningful share; even the largest "
            "Medicaid platforms are low-single-digit percentages of a highly "
            "atomized base. There is no vendored national personal-care agency "
            "file, so a computed geographic HHI is honestly omitted — "
            "fragmentation is the structure."),
        consolidation=(
            "Two separate roll-up games. On private pay, franchising did the "
            "consolidating (Home Instead, Comfort Keepers, Right at Home) and "
            "Honor's acquisition of Home Instead put a tech layer over the "
            "franchise network. On Medicaid personal care, PE has been building "
            "scaled platforms — Help at Home (Centerbridge/Vistria), Addus "
            "HomeCare, All Ways Caring (BrightSpring) — betting on density, "
            "back-office leverage, and rate advocacy."),
        pe_activity=(
            "Highly active, but the thesis has matured. Early roll-ups priced "
            "pure census growth; today's diligence centers on caregiver "
            "recruiting/retention, state rate trajectories, the 80/20 exposure "
            "on Medicaid books, and the private-pay/Medicaid mix. Quality of "
            "earnings hinges on staffed-hours durability, not authorized-hours "
            "backlog."),
        notable_players=[
            "Help at Home", "Addus HomeCare", "All Ways Caring (BrightSpring)",
            "Home Instead (Honor)", "Comfort Keepers (Sodexo)",
            "Right at Home", "Visiting Angels", "BrightStar Care",
            "Care Advantage",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Bill-rate / pay-rate spread", "private pay $30-40 vs "
                "$15-18/hr",
                "The core arbitrage; Medicaid spreads are thinner and set by "
                "the state rate."),
            Kpi("Caregiver turnover (annual)", "60-80%+",
                "The number-one operational cost and the ceiling on how many "
                "authorized hours can actually be staffed."),
            Kpi("Staffed vs authorized hours (fill rate)", "the real revenue "
                "governor",
                "Authorized hours you cannot staff are lost, non-recoverable "
                "revenue — the KPI that separates operators."),
            Kpi("Gross margin", "private pay 30-40% · Medicaid 20-25%",
                "Mix of private-pay vs Medicaid is the biggest driver of "
                "blended gross margin."),
            Kpi("Agency EBITDA margin", "8-15%",
                "Back-office and supervision leverage over the caregiver base; "
                "sub-scale agencies run thin."),
            Kpi("Revenue / client / week (hours authorized)", "varies widely",
                "Higher-acuity Medicaid and private clients with more "
                "authorized hours are more efficient to staff and supervise."),
        ],
        margin_profile=(
            "Home-care margin is a labor arbitrage on a per-hour rate, so it is "
            "decided by three variables: the bill-rate/pay-rate spread, "
            "caregiver utilization (staffed vs authorized hours), and "
            "turnover-driven recruiting cost. Private pay carries the richer "
            "spread and the pricing power; Medicaid carries the volume and the "
            "rate-taker constraint, now tightened by the 80/20 mandate. Scale "
            "helps by spreading scheduling, supervision, recruiting, and "
            "compliance (EVV) across more hours — but it does not change the "
            "state rate or conjure caregivers, which is why density in a market "
            "matters more than national size."),
    ),
    risks=[
        Risk("Caregiver supply / turnover", "High",
             "60-80%+ turnover and local labor shortages cap staffable hours; "
             "unstaffed authorized hours are lost revenue and the sector's "
             "defining constraint."),
        Risk("Medicaid 80/20 Access Rule margin cap", "High",
             "Capping agency overhead+margin at 20% of personal-care payment "
             "structurally pressures Medicaid-heavy books as it phases in."),
        Risk("State Medicaid rate adequacy", "High",
             "Rates that lag local wages make recruiting impossible in a "
             "market; the agency is a price-taker with no offsetting lever."),
        Risk("Wage inflation / minimum-wage moves", "Medium",
             "Direct-care wages set the cost floor; increases that outrun rate "
             "updates compress the spread."),
        Risk("Private-pay discretionary softness", "Medium",
             "Out-of-pocket demand is rate-sensitive and tied to the family's "
             "ability to pay, so it softens in a downturn."),
        Risk("EVV / compliance and integrity exposure", "Medium",
             "Unverified visits are denied, and personal-care billing has drawn "
             "program-integrity scrutiny — documentation discipline is "
             "underwriting."),
    ],
    diligence_questions=[
        "What is the private-pay vs Medicaid revenue mix, and how does gross "
        "margin differ between them?",
        "What is caregiver turnover, and what is the trend in staffed vs "
        "authorized hours (the fill rate)?",
        "What is the 80/20 exposure on the Medicaid book — how much of current "
        "overhead+margin sits above the 20% ceiling as it phases in?",
        "What are the state rates in each market served, and what is the "
        "recent rate-action history and outlook?",
        "How concentrated is revenue by state / MLTSS plan, and what is "
        "renewal / re-procurement risk?",
        "What is the recruiting funnel — cost per hire, time-to-fill, and "
        "caregiver source mix?",
        "What is the EVV/compliance posture and the program-integrity / audit "
        "history?",
        "How much revenue is franchise-royalty vs owned-operations (for "
        "branded private-pay), and how portable are referral sources?",
    ],
    insider_lens=[
        "Private pay and Medicaid are two businesses wearing one uniform. "
        "Private pay is a marketing/consumer business with pricing power and "
        "30-40% gross margin; Medicaid is a rate-taker volume business now "
        "capped by 80/20. A blended P&L hides which one you are actually "
        "buying.",
        "Demand is not the question — supply is. You can sell more hours than "
        "you can ever staff. The asset is a recruiting-and-retention machine "
        "in a local labor market, not a book of authorized hours.",
        "On Medicaid you do not price your product; the state does. The only "
        "growth lever you control is caregiver cost and overhead — plus rate "
        "advocacy, which the best operators treat as a core competency.",
        "The 80/20 rule quietly redraws the Medicaid margin map: it rewards "
        "low-overhead, dense operators and punishes the sub-scale long tail — "
        "the phase-in is a multi-year re-rating of the acquirable universe.",
        "'Unstaffed hours' is the number nobody volunteers. Two agencies with "
        "identical authorized-hour books can have very different revenue "
        "because one can staff 92% and the other 70% — always diligence the "
        "fill rate, not the authorization backlog.",
    ],
    connections=default_connections(
        "home_care",
        deals_sector="home_care",
        extra_pages=[
            ("/diligence/tam-sam?template=home_care",
             "Size it — home-care TAM/SAM build (HCBS + private-pay chain)"),
        ],
        connectors=[
            ("medicaid_data_managed_care_by_state_2024",
             "Medicaid managed care by state — MLTSS penetration (the payer "
             "layer)"),
            ("medicaid_data_enrollment_monthly",
             "Medicaid enrollment (monthly) — the HCBS-eligible base"),
            ("census_acs_cbsa_profile",
             "Census ACS — 65+/85+ density for demand mapping"),
            ("bls_qcew_industry_area",
             "BLS QCEW — home-care employment & wages (the caregiver labor "
             "pool)"),
            ("oig_leie_exclusions",
             "OIG LEIE — excluded individuals/entities (integrity screen)"),
        ],
    ),
    sources=[
        Source("KFF — Medicaid Home & Community-Based Services (HCBS) "
               "spending and enrollment", "GOV",
               "https://www.kff.org/medicaid/issue-brief/medicaid-home-community-based-services/"),
        Source("CMS — Ensuring Access to Medicaid Services Final Rule "
               "(CMS-2442-F), HCBS 80/20 provision", "GOV",
               "https://www.cms.gov/newsroom/fact-sheets/ensuring-access-medicaid-services-final-rule-cms-2442-f"),
        Source("US DOL Wage & Hour Division — Home Care / companionship "
               "services FLSA rule", "GOV",
               "https://www.dol.gov/agencies/whd/direct-care"),
        Source("PHI — Direct Care Workforce (turnover, wages, supply) "
               "research", "INDUSTRY", "https://www.phinational.org/"),
        Source("Home Care Association of America (HCAOA) — industry "
               "benchmarking", "INDUSTRY", "https://www.hcaoa.org/"),
        Source("PE Desk industry deep-dive (deals-only) + realized-deal "
               "corpus for home care", "INTERNAL",
               "/diligence/tam-sam?template=home_care"),
    ],
    live_figures=live_figures_from_dive("home_care"),
    trends=(
        "Home care spent the last decade absorbing two structural cost shocks "
        "and one demographic tailwind. The FLSA Home Care Rule (2015) "
        "permanently added overtime to the agency cost base, and the 2024 "
        "Medicaid Access Rule's 80/20 provision is now redrawing the Medicaid "
        "margin map by mandating that 80% of personal-care payment reach the "
        "worker. Against that, the 85+ population is compounding ~3%/yr and "
        "states continue rebalancing Medicaid spend out of institutions and "
        "into HCBS — durable, non-discretionary demand. The consolidation story "
        "split in two: franchising rolled up private pay (capped by Honor's "
        "acquisition of Home Instead) while PE built scaled Medicaid platforms "
        "(Help at Home, Addus, All Ways Caring). Throughout, the sector's real "
        "governor has stayed constant — caregiver supply. Rates, rules, and "
        "demographics all matter, but the operators who win are the ones who "
        "can recruit and keep aides in a tight local labor market and turn "
        "authorized hours into staffed, billable ones."),
    growth_levers=[
        GrowthLever(
            "85+ demographic wave",
            "The highest-need, highest-hours cohort expands structurally, "
            "lifting both Medicaid and private-pay demand.",
            "+3%/yr (85+)", "GOV"),
        GrowthLever(
            "Medicaid HCBS rebalancing",
            "States keep shifting long-term-care spend from institutions to "
            "home and community settings, growing the personal-care pool.",
            "+2%/yr HCBS shift", "GOV"),
        GrowthLever(
            "Wage-driven Medicaid rate updates",
            "States raise personal-care rates to fund caregiver wages; the "
            "revenue side moves with the cost side, though often with a lag.",
            "+2-3%/yr rate", "ILLUSTRATIVE"),
        GrowthLever(
            "Medicare Advantage in-home supplemental benefits",
            "SSBCI / expanded primarily-health-related benefits let MA plans "
            "buy non-medical in-home support — a genuinely new payer channel.",
            "new channel", "ILLUSTRATIVE"),
        GrowthLever(
            "Caregiver-supply and 80/20 drag",
            "Turnover, wage inflation, and the 80/20 overhead cap remove "
            "effective capacity and margin — the offsetting headwind.",
            "−margin / −capacity", "ILLUSTRATIVE"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="85+ population × aging-in-place preference — gated by caregiver "
               "supply",
        analysis=(
            "The demand driver is demographic and non-discretionary: the 85+ "
            "population — the cohort with the highest rate of ADL dependency — "
            "is compounding around 3%/yr, and both public policy (HCBS "
            "rebalancing) and consumer preference push that need toward the "
            "home rather than the nursing facility. That makes the addressable "
            "hour-pool grow faster than the overall senior population. But the "
            "effective, realizable volume is gated by caregiver supply: an "
            "agency can only bill the hours it can staff. So the honest read is "
            "that demand growth sets the ceiling while caregiver recruiting and "
            "retention set the floor — and in most markets the floor, not the "
            "ceiling, is binding."),
        basis="GOV"),
    cost_drivers=[
        CostDriver(
            "Caregiver wages",
            "~65-75% of revenue",
            "The dominant cost — and, on Medicaid, now floored by the 80/20 "
            "rule. The entire model is the spread between the bill rate and "
            "this wage.", "ILLUSTRATIVE"),
        CostDriver(
            "Recruiting & turnover",
            "#2 cost driver",
            "At 60-80%+ turnover, the cost of continuously sourcing, "
            "screening, and onboarding aides is a large, recurring line — and "
            "the constraint on staffable hours.", "ILLUSTRATIVE"),
        CostDriver(
            "Workers' compensation & benefits",
            "~5-10% of revenue",
            "Home-care work carries real injury exposure; comp rates and any "
            "benefits load sit directly on the wage base.", "ILLUSTRATIVE"),
        CostDriver(
            "Scheduling, supervision & back office",
            "~8-12% of revenue",
            "Matching caregivers to authorized hours, RN/supervisor oversight, "
            "and billing — the leverage scale is supposed to deliver.",
            "ILLUSTRATIVE"),
        CostDriver(
            "EVV & compliance technology",
            "smaller but mandatory",
            "Electronic Visit Verification, background-check, and training "
            "compliance — table stakes for Medicaid payment.",
            "ILLUSTRATIVE"),
    ],
    # Deals-only vertical: no provider_backed CMS roll, so cms_trend and a
    # computed state_breakdown are intentionally omitted — the renderer shows an
    # honest "unavailable offline" note and the qualitative sections carry the
    # weight.
)

register(REPORT)
