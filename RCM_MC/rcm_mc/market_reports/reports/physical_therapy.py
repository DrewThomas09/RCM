"""Physical Therapy — outpatient musculoskeletal & neuromuscular rehab.

Deals-only deep-dive (no vendored national PT-clinic facility file). PT is the
archetypal fragmented healthcare roll-up: tens of thousands of clinics, no
dominant owner, and economics that turn entirely on therapist labor
productivity against a fee-schedule rate that only ratchets down. The
qualitative sections are authored around the MPFS per-timed-unit mechanics (the
8-minute rule, MPPR, the PTA differential), the therapist-retention constraint
that sank ATI, and the same-clinic-volume/payer-mix diligence frame. Consumes
``physical_therapy_deep_dive()`` for SOURCED corpus deal figures.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="physical_therapy",
    name="Physical Therapy",
    care_setting="Ambulatory",
    naics="621340",
    one_line_def=(
        "Outpatient rehabilitation clinics delivering therapist-led "
        "musculoskeletal and neuromuscular rehab — post-surgical, post-injury, "
        "chronic pain, and sports — paid on the Medicare Physician Fee "
        "Schedule per timed 15-minute unit of CPT therapy codes, labor-"
        "intensive, and deeply fragmented."),
    tam_headline=TamHeadline(
        value=34.0, unit="$B", growth_pct=4.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "US outpatient physical-therapy market is ~$30-35B all-payer "
            "(modeled composite; no single published figure). Medicare Part B "
            "outpatient therapy alone runs ~$8-9B (MedPAC) — see segments. "
            "Growth is the modeled composite of aging/surgical demand and "
            "direct access, net of the MPFS rate headwind."),
    ),
    executive_summary=[
        "PT is the archetypal fragmented healthcare roll-up: tens of thousands "
        "of clinics, mostly independent or small groups, no dominant owner — "
        "the classic buy-and-build, with synergy in payer contracting, "
        "billing, and back-office scale rather than in the core labor ratio.",
        "The whole economics are labor productivity: revenue is therapist-time "
        "converted into billable units, and the single most important metric "
        "is visits (or units) per therapist per day against a fixed clinic. "
        "Therapist recruiting, retention, and productivity ARE the business.",
        "Reimbursement is a structural headwind. PT is paid on the MPFS per "
        "timed 15-minute unit (the '8-minute rule'), and the conversion factor "
        "plus PT-specific cuts — the MPPR multiple-procedure reduction, the "
        "15% PTA assistant differential, sequestration — have ratcheted rates "
        "down for years, straight to margin because there is no facility fee.",
        "Payer mix spans commercial, Medicare, workers' comp (high-paying), "
        "Medicaid (below cost), and cash-pay (growing). Workers' comp and "
        "cash/wellness are the margin bright spots; Medicaid and heavily-"
        "managed commercial are the squeeze.",
        "Consolidation is intense and multiples compressed. The ATI Physical "
        "Therapy SPAC blow-up — over-levered and hollowed by therapist "
        "attrition — repriced the sector, so quality-of-earnings now centers "
        "on same-clinic visit growth and therapist retention, not tuck-in "
        "arithmetic.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Injury / surgery / diagnosis → physician referral or direct access",
            "PT evaluation + plan of care (eval code by complexity)",
            "Course of visits — timed therapeutic exercise, manual therapy, "
            "neuromuscular re-ed, modalities",
            "Re-evaluation / progress against functional goals",
            "Discharge to a home exercise program",
            "Claim per timed CPT unit (8-minute rule) + eval codes",
            "Outcomes / functional reporting; KX attestation above the "
            "threshold",
        ],
        sites_of_care=[
            "Freestanding outpatient PT clinic (the core asset)",
            "Hospital outpatient rehab department (HOPD — higher-paid)",
            "Physician-owned in-office therapy (POPTS — Stark-sensitive)",
            "Home-based / mobile PT",
            "Industrial / on-site occupational PT",
            "Cash-pay performance / wellness studio",
            "Telehealth / digital-MSK virtual PT (Hinge, Sword — adjacent)",
        ],
        money_flow=(
            "Outpatient PT bills the Medicare Physician Fee Schedule (or "
            "commercial equivalent) per procedure: an evaluation code "
            "(97161-97163 by complexity) at the start, then timed treatment "
            "codes billed in 15-minute units under the '8-minute rule' — "
            "therapeutic exercise (97110), manual therapy (97140), "
            "neuromuscular re-education (97112), therapeutic activities "
            "(97530) — plus untimed modalities. Revenue per visit is units "
            "billed × the per-unit rate, so the clinic's income is therapist "
            "time turned into billable units. Workers' comp and some commercial "
            "contracts pay materially above Medicare; Medicaid and tightly-"
            "managed plans pay below. There is no facility fee in the "
            "freestanding setting, and the HOPD setting pays more for the same "
            "service (a site-of-service differential). Cash-pay wellness sits "
            "outside insurance entirely."),
        key_players=(
            "A consolidating but still-fragmented field. Larger platforms "
            "include US Physical Therapy (USPh, publicly traded), Upstream "
            "Rehabilitation (Revelstoke), Confluent Health, Athletico, Select "
            "Medical's outpatient division (Physio/NovaCare/Select Physical "
            "Therapy), ATI Physical Therapy (public, post-SPAC distress), Ivy "
            "Rehab, and Professional PT. Below them, thousands of independent "
            "single- and multi-clinic practices — the acquisition pool. "
            "Digital-MSK entrants (Hinge Health, Sword Health) compete for the "
            "same patients virtually."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("US outpatient PT market (all-payer)", "~$30-35B",
                    "ILLUSTRATIVE · modeled all-payer market"),
            Segment("Medicare Part B outpatient therapy (PT/OT/SLP)",
                    "~$8-9B",
                    "GOV · MedPAC / CMS Part B therapy spending"),
            Segment("Workers' comp + cash-pay",
                    "the high-rate slices — the margin bright spot",
                    "ILLUSTRATIVE · modeled payer mix"),
            Segment("US PT clinics", "tens of thousands, mostly independent",
                    "INDUSTRY · APTA / market estimates"),
            Segment("Visits per episode of care", "~10-12",
                    "ILLUSTRATIVE · modeled utilization per plan of care"),
        ],
        growth_drivers=[
            "Aging + rising MSK/orthopedic surgical volume (post-op rehab)",
            "Direct access — patients can start PT without a referral in most "
            "states",
            "PT-first, non-opioid conservative MSK management",
            "Sports/activity + cash-pay wellness expansion",
            "Offsets: MPFS rate cuts (CF, MPPR, PTA differential) + therapist "
            "shortage",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Commercial": 0.45,
            "Medicare / MA": 0.30,
            "Workers' comp": 0.10,
            "Medicaid": 0.08,
            "Cash / self-pay": 0.07,
        },
        rate_mechanics=[
            "Medicare Physician Fee Schedule per timed unit — evaluation codes "
            "(97161-97163) plus timed treatment codes (97110/97112/97140/97530) "
            "billed in 15-minute units under the '8-minute rule'; revenue = "
            "units × per-unit rate.",
            "Annual conversion-factor cuts — the MPFS CF has declined in most "
            "recent years and each cut hits PT directly, since there is no "
            "offsetting facility fee.",
            "Multiple Procedure Payment Reduction (MPPR) — the practice-expense "
            "component of the second-and-later timed code on the same day is "
            "reduced ~50%, structurally lowering multi-unit visit revenue.",
            "PTA/OTA differential (CQ/CO modifier) — services delivered by a "
            "therapist assistant are paid at 85% (a 15% cut), reshaping the "
            "assistant-leverage staffing model.",
            "KX-modifier threshold + targeted medical review — replaced the old "
            "hard therapy cap; above an annual dollar threshold the clinic "
            "attests medical necessity and faces targeted review higher up.",
            "Site-of-service + payer differential — HOPD pays more than the "
            "freestanding clinic for the same codes; workers' comp and some "
            "commercial contracts pay well above Medicare, Medicaid below.",
            "Cash-pay / direct-pay — wellness, performance, and out-of-network "
            "cash services outside insurance entirely.",
        ],
        reimbursement_risk=(
            "PT is a fee-schedule business squarely in CMS's cost-cutting path. "
            "The MPFS conversion factor has been cut in most recent years, and "
            "PT-specific reductions stack on top — the MPPR haircut on multi-"
            "unit visits, the 15% PTA differential that penalizes the "
            "assistant-leverage staffing model, and sequestration. Because "
            "there is no facility fee and revenue is therapist time × rate, "
            "every cut flows straight to margin. Commercial payers increasingly "
            "impose visit caps, prior authorization, and utilization "
            "management, while Medicaid pays below cost. The bright spots — "
            "workers' comp and cash-pay — are a minority of most clinics' "
            "volume, and the KX-threshold/targeted-review regime adds "
            "documentation and audit burden. Only same-clinic volume growth, "
            "payer-mix improvement, and productivity offset the persistent rate "
            "headwind."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("Medicare Physician Fee Schedule + therapy provisions "
                 "(annual Final Rule)",
                 "Sets the conversion factor, timed-code values, MPPR, and the "
                 "PTA differential — the sector's core price mechanism.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
            Rule("KX-modifier threshold + targeted medical review",
                 "Replaced the hard therapy cap; above an annual dollar "
                 "threshold the clinic attests medical necessity (KX) and "
                 "faces targeted review above a higher amount.",
                 "https://www.cms.gov/medicare/billing/therapyservices"),
            Rule("Therapist-assistant payment differential (CQ/CO modifiers)",
                 "PTA/OTA-delivered services are paid at 85% — the rule that "
                 "reshapes staffing leverage and clinic economics.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
            Rule("Stark law / physician-owned PT services (POPTS)",
                 "Physician referral to owned therapy is Stark-sensitive under "
                 "the in-office ancillary exception — the referral-source "
                 "dynamics matter to a PT platform.",
                 "https://www.cms.gov/medicare/regulations-guidance/physician-self-referral"),
            Rule("State direct-access + licensure/scope laws",
                 "Whether patients can self-refer to PT without a physician "
                 "order (now most states, with varying limits) widens the top "
                 "of the demand funnel.",
                 None),
        ],
        policy_watch=[
            "Annual MPFS conversion-factor cuts and any Congressional patch",
            "PTA/OTA differential and its effect on the assistant-leverage "
            "model",
            "Commercial utilization-management / prior-auth / visit-cap "
            "expansion",
            "Digital-MSK (Hinge, Sword) reimbursement and substitution",
            "Direct-access expansion and scope-of-practice changes",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Tens of thousands of outpatient PT clinics, overwhelmingly "
            "independent or small groups; even the largest platform holds low-"
            "single-digit national share. This is one of the most fragmented "
            "healthcare verticals — the textbook buy-and-build, and a deep "
            "acquirable long tail."),
        hhi_or_share=(
            "No dominant owner — US Physical Therapy, Upstream, Confluent, "
            "Athletico, Select/Physio, and ATI each hold low-single-digit "
            "share. No public clinic file carries an operator field, so a chain "
            "HHI is honestly omitted; fragmentation is the structure."),
        consolidation=(
            "A decade of intense PE-backed roll-up built the current platforms "
            "(Upstream/Revelstoke, Confluent, Ivy, Athletico, Professional PT), "
            "while US Physical Therapy consolidates via partnership/JV as a "
            "public serial acquirer. The ATI Physical Therapy SPAC (2021) and "
            "its subsequent distress became the cautionary tale — over-levered, "
            "therapist-attrition-hit, repriced — which cooled multiples and "
            "refocused diligence on same-clinic growth and retention."),
        pe_activity=(
            "Highly PE-active — one of the most-rolled-up outpatient "
            "verticals. But the thesis matured: after the ATI blow-up and "
            "years of MPFS cuts, sponsors underwrite therapist retention, same-"
            "clinic volume, and payer mix rather than pure tuck-in multiple "
            "arbitrage. Add-on multiples compressed from the 2021 peak."),
        notable_players=[
            "US Physical Therapy (USPh)", "Upstream Rehabilitation",
            "Confluent Health", "Athletico",
            "Select Physical Therapy (Physio/NovaCare)",
            "ATI Physical Therapy", "Ivy Rehab", "Professional PT",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Visits / therapist / day", "10-16",
                "The core productivity metric — too low kills margin, too high "
                "risks quality and audit exposure."),
            Kpi("Units billed / visit (timed)", "~3-4",
                "Revenue is units × rate; the 8-minute rule governs how time "
                "converts to billable units."),
            Kpi("Net revenue / visit (blended)", "$80-120",
                "Modest and rate-pressured; workers' comp and cash-pay lift the "
                "blend, Medicaid drags it."),
            Kpi("Therapist labor cost (% of revenue)", "45-55%",
                "The dominant cost; comp inflation and turnover are the swing "
                "that makes or breaks the clinic."),
            Kpi("Therapist turnover", "15-25%+",
                "The sector's chronic wound — recruiting cost and lost "
                "productivity; attrition is what sank ATI."),
            Kpi("Same-clinic visit growth", "the value metric",
                "Organic volume, not tuck-ins, is what survived the diligence "
                "repricing."),
            Kpi("Clinic EBITDA margin (mature)", "12-20%",
                "Labor-heavy and rate-pressured; scale helps contracting and "
                "back-office, not the core labor ratio."),
        ],
        margin_profile=(
            "An outpatient PT clinic is a therapist-labor business: revenue is "
            "therapist time converted into billable timed units, and therapist "
            "compensation is 45-55% of revenue, so margin lives and dies on "
            "visits-per-therapist-per-day and payer mix. There is no facility "
            "fee; a rate cut flows straight to the bottom line. Mature, well-"
            "utilized clinics with a favorable commercial/workers'-comp/cash "
            "mix run mid-teens EBITDA margin; Medicaid-heavy or under-scheduled "
            "clinics are far thinner. Scale delivers real but bounded synergy — "
            "better payer contracts, centralized billing, PTA-leverage "
            "staffing, and back-office spread — but cannot change the "
            "fundamental labor ratio or the fee-schedule headwind. Therapist "
            "recruiting and retention are the binding constraint on growth."),
    ),
    risks=[
        Risk("MPFS rate cuts (CF, MPPR, PTA differential)", "High",
             "A persistent, stacking fee-schedule headwind that flows straight "
             "to margin in a business with no facility fee."),
        Risk("Therapist recruiting, retention & wage inflation", "High",
             "The binding growth constraint; turnover crippled ATI and gates "
             "how much volume a clinic can serve."),
        Risk("Commercial UM / prior-auth / visit caps", "Medium",
             "Payers limiting authorized visits per episode compress volume "
             "and revenue per plan of care."),
        Risk("Digital-MSK substitution (Hinge, Sword)", "Medium",
             "Virtual MSK competing for the same patients and payer dollars, "
             "especially the lower-acuity ones."),
        Risk("Over-leverage + tuck-in integration risk", "Medium",
             "The ATI lesson: debt plus attrition plus rate cuts is a fatal "
             "combination."),
        Risk("Medicaid / low-payer exposure", "Medium",
             "Below-cost reimbursement in a labor-heavy model erodes margin "
             "where the mix skews public."),
    ],
    diligence_questions=[
        "What is same-clinic (organic) visit growth, and how does it separate "
        "from acquired growth?",
        "What is visits/therapist/day and the productivity trend, and how does "
        "it compare to benchmark?",
        "What is therapist turnover, time-to-fill, and comp inflation — and "
        "how exposed is volume to a few key therapists?",
        "What is the payer mix and net revenue per visit by payer, and what is "
        "the workers'-comp and cash-pay share?",
        "How exposed is the P&L to the next MPFS conversion-factor cut and the "
        "PTA differential given the staffing model?",
        "What share of visits are delivered by PTAs (85% payment), and how is "
        "that modeled forward?",
        "What is the commercial prior-auth / visit-cap exposure and the "
        "denial/appeal history?",
        "How is any physician-referral relationship (POPTS / JV) structured "
        "against Stark?",
    ],
    insider_lens=[
        "The whole business is visits per therapist per day. Everything else — "
        "real estate, brand, tuck-ins — is secondary to converting therapist "
        "time into billable units at a healthy payer rate. A clinic that "
        "cannot staff and schedule is worthless regardless of the market.",
        "Therapist retention is the ATI lesson written in blood. ATI's SPAC "
        "blow-up was fundamentally a labor story — attrition gutted "
        "productivity while the debt stayed. Underwrite turnover, comp "
        "trajectory, and clinician satisfaction before the roll-up math.",
        "The fee schedule only goes one way. Years of CF cuts, MPPR, and the "
        "15% PTA differential mean the base rate erodes; the only offsets are "
        "same-clinic volume, payer-mix upgrade (workers' comp, cash), and "
        "productivity. A thesis that assumes flat rates is already wrong.",
        "Cash-pay and workers' comp are the quiet margin. The clinics that "
        "outperform lean into out-of-network cash wellness/performance and "
        "workers'-comp contracts that pay well above Medicare — payer mix, not "
        "visit count, often separates a great clinic from an average one.",
        "Direct access widened the funnel but referral relationships still "
        "rule. Even where patients can self-refer, orthopedic and PCP referral "
        "streams drive most volume — losing a key referring surgeon can hollow "
        "a clinic, which is why physician alignment (and its Stark limits) "
        "matters.",
    ],
    connections=default_connections(
        "physical_therapy",
        deals_sector="physical_therapy",
        extra_pages=[
            ("/industry/physical_therapy",
             "Industry deep-dive — PT deal history + structure"),
        ],
        connectors=[
            ("cms_open_data_mup_physician_by_provider_service",
             "Medicare utilization by provider & service — therapy CPT (97xxx) "
             "volume and payment"),
            ("npi_provider_taxonomy",
             "NPI taxonomy — PT / PTA provider census & clinic footprint"),
            ("census_acs_cbsa_profile",
             "Census ACS — catchment demographics for site & roll-up mapping"),
            ("cms_open_data_mup_physician_by_geo_service",
             "Medicare physician utilization by geography — therapy pattern"),
            ("bls_qcew_area_industry",
             "BLS QCEW — PT-office employment & the therapist labor market"),
        ],
    ),
    sources=[
        Source("MedPAC — Report to Congress, outpatient therapy services "
               "(Part B) context", "GOV", "https://www.medpac.gov/"),
        Source("CMS — Medicare Physician Fee Schedule Final Rule (therapy "
               "provisions: CF, MPPR, PTA differential, KX threshold)", "GOV",
               "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
        Source("American Physical Therapy Association (APTA) — payment and "
               "workforce data", "INDUSTRY", "https://www.apta.org/"),
        Source("US Physical Therapy, Inc. — public filings (10-K) as a sector "
               "read", "INDUSTRY", "https://www.sec.gov/"),
        Source("Health Affairs / JAMA — research on PT-first, non-opioid "
               "conservative MSK management vs surgery", "ACADEMIC",
               "https://www.healthaffairs.org/"),
        Source("PE Desk industry deep-dive (physical therapy) + realized-deal "
               "corpus", "INTERNAL",
               "/diligence/tam-sam?template=physical_therapy"),
    ],
    live_figures=live_figures_from_dive("physical_therapy"),
    trends=(
        "Outpatient PT spent the last decade as one of healthcare's busiest "
        "roll-ups: PE-backed platforms — Upstream, Confluent, Athletico, Ivy, "
        "Professional PT — consolidated a deeply fragmented base while US "
        "Physical Therapy compounded as a public serial acquirer. Two forces "
        "then reset the trajectory. First, reimbursement: the Medicare "
        "Physician Fee Schedule conversion factor was cut in most recent years "
        "and PT-specific reductions stacked on top — the MPPR haircut, the 15% "
        "PTA differential, sequestration — steadily eroding the per-unit rate "
        "in a business with no facility fee. Second, labor: a chronic "
        "physical-therapist shortage and high turnover made staffing the "
        "binding constraint, and the ATI Physical Therapy SPAC (2021) became "
        "the cautionary tale — over-levered and hollowed by attrition, it "
        "repriced the whole sector. The durable demand tailwinds remain real — "
        "an aging population, rising orthopedic surgical volume, direct access, "
        "and a PT-first shift away from opioids and surgery — but multiples "
        "compressed and diligence moved to same-clinic visit growth, therapist "
        "retention, and payer mix rather than tuck-in arithmetic. Digital-MSK "
        "entrants (Hinge, Sword) add a new competitive and substitution vector "
        "for the lower-acuity patient."),
    growth_levers=[
        GrowthLever(
            "Aging + orthopedic surgical volume (post-op rehab)",
            "More joint-replacement, spine, and sports surgery drives a defined "
            "post-op course of PT visits per case.",
            "primary", "ILLUSTRATIVE"),
        GrowthLever(
            "Direct access + PT-first conservative care",
            "Self-referral laws in most states and a non-opioid MSK-management "
            "shift widen the top of the demand funnel.",
            "+ funnel", "ILLUSTRATIVE"),
        GrowthLever(
            "Roll-up + same-clinic volume & payer-mix upgrade",
            "Contracting scale plus a richer workers'-comp/cash mix lift "
            "revenue per visit above the fee-schedule base.",
            "+ organic", "ILLUSTRATIVE"),
        GrowthLever(
            "Cash-pay / wellness / industrial on-site",
            "Out-of-network performance, wellness, and employer on-site "
            "programs add high-rate volume outside insurance.",
            "+ high-rate volume", "ILLUSTRATIVE"),
        GrowthLever(
            "MPFS rate cuts + PTA differential drag",
            "The declining conversion factor, MPPR, and the 15% PTA cut erode "
            "the per-unit rate every year.",
            "− structural", "GOV"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="MSK & post-surgical rehab episodes × visits per episode",
        analysis=(
            "The dominant demand driver is the volume of musculoskeletal and "
            "post-surgical rehabilitation episodes and the number of visits per "
            "episode. Two structural forces lift it: an aging, active "
            "population drives rising orthopedic surgical volume (joint "
            "replacement, spine, sports injuries), each generating a defined "
            "post-op course of PT visits; and a system-wide shift toward "
            "conservative, non-opioid, PT-first management of back and joint "
            "pain — reinforced by direct-access laws that let patients start PT "
            "without a physician referral in most states — expands the "
            "addressable population beyond the post-surgical base. Demand is "
            "fairly non-discretionary once a plan of care is prescribed, and "
            "episodes run ~10-12 visits. The offsets sit on the supply and "
            "payer side rather than demand: a therapist labor shortage caps how "
            "much volume a clinic can serve, commercial visit caps and prior "
            "authorization limit authorized visits per episode, and digital-MSK "
            "substitution peels off the lowest-acuity patients."),
        basis="GOV"),
    cost_drivers=[
        CostDriver(
            "Therapist & clinical labor (PT, PTA, aides)",
            "~45-55% of cost",
            "The dominant cost; comp inflation and turnover are the swing that "
            "makes or breaks the clinic.", "ILLUSTRATIVE"),
        CostDriver(
            "Occupancy / clinic rent & rehab equipment",
            "~10-15% of cost",
            "The fixed clinic footprint plus rehab equipment — the chassis the "
            "labor works against.", "ILLUSTRATIVE"),
        CostDriver(
            "Front-office, scheduling & billing/RCM",
            "~10-15% of cost",
            "Scheduling drives utilization and denials management protects the "
            "rate-pressured revenue.", "ILLUSTRATIVE"),
        CostDriver(
            "Corporate G&A / management (platform overhead)",
            "~8-12% of cost",
            "The roll-up's central cost, spread across the clinic base — the "
            "main scale synergy lever.", "ILLUSTRATIVE"),
        CostDriver(
            "Marketing & referral development",
            "~3-6% of cost",
            "Physician-referral cultivation and, for cash-pay, consumer demand "
            "generation.", "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "No national outpatient-PT clinic file is vendored, so state geography "
        "is omitted rather than fabricated. Qualitatively, clinic density "
        "tracks population and orthopedic/surgical volume, and the operating "
        "model varies with two state variables: direct-access scope (states "
        "allowing full self-referral to PT widen the funnel) and workers'-comp "
        "fee schedules (states with rich comp rates lift the payer mix). Roll-"
        "up platforms concentrate where they can cluster clinics for "
        "contracting and staffing scale — Texas, the Southeast, the Mid-"
        "Atlantic, and the Midwest are heavily consolidated. The Medicare "
        "therapy-utilization and NPI connectors below support a real provider-"
        "and-billing footprint read."),
)

register(REPORT)
