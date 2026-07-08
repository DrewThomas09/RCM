"""Eating Disorders — the residential/PHP/IOP treatment continuum for EDs.

Deals-only deep-dive (no public eating-disorder-treatment census, so geography
is omitted rather than fabricated). Consumes ``eating_disorders_deep_dive()``
for SOURCED corpus figures where the corpus tags them. This is a
commercial-pay, medical-necessity-fought vertical unlike the Medicaid-heavy rest
of behavioral health — so the sections are authored around the level-of-care
continuum, per-diem residential economics, and the parity/utilization-review war
that the Wit v. UBH litigation made the governing dynamic.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="eating_disorders",
    name="Eating Disorders",
    care_setting="Behavioral",
    naics="622210",
    one_line_def=(
        "Specialty treatment of anorexia, bulimia, binge-eating disorder, and "
        "ARFID across a level-of-care continuum — inpatient medical "
        "stabilization, residential, partial hospitalization (PHP), intensive "
        "outpatient (IOP), and outpatient — delivered by multidisciplinary "
        "teams (therapy, psychiatry, medical, and dietetics) and paid "
        "overwhelmingly by commercial insurance under contested medical-"
        "necessity review."),
    tam_headline=TamHeadline(
        value=64.7, unit="$B", growth_pct=7.0, basis_label="ACADEMIC",
        basis_note=(
            "The Deloitte Access Economics / STRIPED 'Social and Economic Cost "
            "of Eating Disorders in the US' put the total economic cost near "
            "$64.7B/yr (2018-19); the treatment-services market itself is a far "
            "smaller modeled ~$4-6B. Growth here is the modeled composite of "
            "prevalence/adolescent surge (+4.0%), diagnosis breadth "
            "(ARFID/BED/male, +2.0%), and virtual-care access (+1.0%)."),
    ),
    executive_summary=[
        "The asset is a licensed bed continuum, and the economics are a "
        "commercial per-diem times occupancy times length of stay. Unlike the "
        "Medicaid-heavy rest of behavioral health, ED treatment is a "
        "commercial-pay vertical — residential per-diems run into four figures "
        "a day — which makes it attractive and makes the payer the adversary.",
        "Utilization review is the business. Payers challenge the level of care "
        "and the length of stay continuously; the gap between clinically "
        "indicated days and authorized/paid days is the single largest revenue "
        "leak, and appeals/single-case-agreement capability is a core "
        "competency, not back office.",
        "Wit v. UBH reset the parity landscape. The landmark ruling against "
        "United Behavioral Health's internal level-of-care guidelines — for "
        "being stricter than generally-accepted standards — is the reference "
        "point for every medical-necessity fight in this sector and a tailwind "
        "for days-paid, even after appellate complications.",
        "Demand stepped up and got younger. Adolescent eating-disorder "
        "presentations surged during and after COVID, and broadening diagnosis "
        "(ARFID, binge-eating disorder, males, older and more diverse patients) "
        "keeps expanding the treated population beyond the classic profile.",
        "Two models are converging: PE-backed residential platforms (Monte "
        "Nido, Eating Recovery Center, Discovery, Alsana, Veritas/Walden) that "
        "own the high-acuity beds, and venture-backed virtual programs (Equip, "
        "Within) delivering evidence-based family-based and higher-level "
        "outpatient care at home — reshaping where the continuum's volume sits.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Screening / referral (PCP, therapist, ED, school, self) + medical "
            "and psychiatric assessment",
            "Level-of-care determination against APA/AED criteria (medical "
            "acuity, weight, comorbidity, function)",
            "Benefit verification + prior authorization / single-case "
            "agreement for the level of care",
            "Admission to the indicated level — inpatient medical stabilization, "
            "residential, PHP, or IOP",
            "Multidisciplinary treatment (therapy, psychiatry, medical "
            "monitoring, dietetics, milieu, meal support)",
            "Concurrent utilization review — the payer re-authorizes (or "
            "denies) continued days; step-down decisions",
            "Step-down through the continuum to outpatient + relapse "
            "prevention; billing, denials, and appeals",
        ],
        sites_of_care=[
            "Inpatient medical stabilization (hospital-based; acute medical "
            "risk — bradycardia, electrolytes, refeeding)",
            "Residential treatment (24/7 non-hospital; the commercial per-diem "
            "core of the sector)",
            "Partial hospitalization (PHP — day treatment with meals)",
            "Intensive outpatient (IOP — several sessions/week)",
            "Outpatient (therapy + dietetics + psychiatry; maintenance)",
            "Virtual PHP/IOP + family-based treatment (the fast-growing "
            "home-delivered layer)",
        ],
        money_flow=(
            "Higher levels of care bill a commercial per-diem — residential and "
            "PHP at rates that can reach four figures a day — while IOP and "
            "outpatient bill per-session or per-day bundles and clinician time. "
            "Almost all of it is commercial insurance (this is not a Medicaid "
            "vertical), often out-of-network at admission with single-case "
            "agreements negotiated per patient. The defining feature of the cash "
            "flow is concurrent utilization review: the payer authorizes a short "
            "block of days, a utilization-review clinician reassesses, and "
            "continued stay must be re-justified against the payer's medical-"
            "necessity criteria — so revenue is a function not of clinically-"
            "indicated length of stay but of authorized-and-paid length of stay, "
            "with the difference recovered (or not) through appeals. Because the "
            "per-diem is high and the cost base (24/7 milieu, medical, "
            "psychiatry, dietetics) is largely fixed to the bed, occupancy and "
            "the days-paid-to-days-delivered ratio drive the entire P&L."),
        key_players=(
            "PE- and sponsor-backed residential platforms dominate the "
            "high-acuity segment: Monte Nido & Affiliates, Eating Recovery "
            "Center (which absorbed The Emily Program), Center for Discovery "
            "(Discovery Behavioral Health), Alsana, and Veritas Collaborative / "
            "Walden Behavioral Care. Venture-backed virtual programs — Equip "
            "Health (family-based treatment at home) and Within Health — are "
            "reshaping the outpatient and PHP/IOP layers. Academic and "
            "hospital-based programs anchor the medical-stabilization end. The "
            "acquirable pool is regional residential and PHP/IOP operators plus "
            "the virtual entrants."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Total US economic cost of eating disorders",
                    "~$64.70B/yr", "ACADEMIC · Deloitte/STRIPED cost study"),
            Segment("ED treatment-services market (modeled)", "~$4-6B",
                    "ILLUSTRATIVE · services revenue model, directional"),
            Segment("US lifetime ED prevalence", "~9% of the population",
                    "ACADEMIC · STRIPED / epidemiological estimates"),
            Segment("Residential / PHP per-diem tier", "the revenue core",
                    "ILLUSTRATIVE · level-of-care revenue structure"),
            Segment("Virtual PHP/IOP + FBT", "the fastest-growing layer",
                    "ILLUSTRATIVE · care-model shift, directional"),
        ],
        growth_drivers=[
            "Prevalence + the post-COVID adolescent surge ~4.0%/yr",
            "Diagnosis breadth — ARFID, binge-eating disorder, male/older ~2.0%",
            "Virtual FBT/PHP expanding access to non-metro patients ~1.0%/yr",
            "Parity enforcement (Wit legacy) lifting authorized days",
            "Payer utilization review — a length-of-stay, not a volume, drag",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Commercial (in- and out-of-network)": 0.82,
            "Self-pay / single-case": 0.10,
            "Medicaid / Medicare / other": 0.08,
        },
        rate_mechanics=[
            "Residential and PHP per-diem — a single daily rate covering the "
            "24/7 milieu, therapy, psychiatry, medical monitoring, and meal "
            "support; the high-acuity revenue core.",
            "IOP / outpatient per-session or per-day bundles plus clinician "
            "time (therapy, psychiatry E&M, medical-nutrition therapy for "
            "dietetics).",
            "Out-of-network billing + single-case agreements — many admissions "
            "start OON with a per-patient negotiated rate, since specialty ED "
            "programs are thinly in-network.",
            "Concurrent utilization review + medical-necessity criteria — the "
            "payer authorizes days in blocks and re-reviews; the criteria and "
            "the appeal process determine paid length of stay.",
            "MHPAEA parity — behavioral levels of care must be no more "
            "restricted than comparable medical/surgical care; the lever "
            "programs use to fight denials.",
            "No Surprises Act / balance-billing rules — constrain the OON "
            "economics that residential ED has historically relied on.",
        ],
        reimbursement_risk=(
            "The dominant risk is not price but authorized length of stay. "
            "Eating disorders require long, stepped courses of care, but payers "
            "apply utilization review to compress days and push patients down "
            "the continuum sooner than clinicians recommend — so the revenue a "
            "program earns is the payer's authorized-and-paid days, which can "
            "sit well below the clinically-indicated (and staffed-for) days. The "
            "Wit v. UBH litigation established that a large payer's internal "
            "level-of-care guidelines were more restrictive than generally-"
            "accepted standards, a landmark for the sector's appeals posture, "
            "though subsequent appellate history tempered the remedy. Layered on "
            "top: much specialty ED care is out-of-network, so the No Surprises "
            "Act and balance-billing rules pressure a historically important "
            "margin source, and single-case-agreement negotiation is a "
            "per-admission revenue variable. Net, a program's financial quality "
            "is a function of its denial rate, appeal win rate, and days-paid-"
            "to-days-delivered ratio far more than its headline per-diem."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("Wit v. United Behavioral Health (N.D. Cal.)",
                 "Landmark ruling that UBH's internal level-of-care/medical-"
                 "necessity guidelines were stricter than generally-accepted "
                 "standards — the reference case for ED (and behavioral) "
                 "medical-necessity and parity disputes.",
                 "https://www.csearight.com/"),
            Rule("Mental Health Parity and Addiction Equity Act (MHPAEA)",
                 "Requires behavioral levels of care to be covered no more "
                 "restrictively than medical/surgical — the statutory basis for "
                 "challenging length-of-stay and level-of-care denials.",
                 "https://www.cms.gov/marketplace/private-health-insurance/mental-health-parity-addiction-equity"),
            Rule("No Surprises Act (balance-billing protections)",
                 "Constrains out-of-network balance billing and sets IDR for OON "
                 "disputes — directly relevant to the OON residential ED model.",
                 "https://www.cms.gov/nosurprises"),
            Rule("State residential-treatment-facility licensure + accreditation "
                 "(Joint Commission / CARF)",
                 "Governs licensure of residential and PHP programs and the "
                 "accreditation payers require to contract.",
                 None),
            Rule("APA / AED level-of-care and treatment guidelines",
                 "The generally-accepted clinical standards for level-of-care "
                 "placement that anchor medical-necessity arguments against "
                 "payer criteria.",
                 "https://www.aedweb.org/"),
        ],
        policy_watch=[
            "Post-Wit medical-necessity-criteria litigation and payer guideline "
            "revisions",
            "MHPAEA 2024 final-rule enforcement on level-of-care NQTLs",
            "No Surprises Act IDR outcomes and OON-economics pressure",
            "State parity enforcement and external-review expansion",
            "Coverage and coding for virtual PHP/IOP and family-based treatment",
            "ARFID recognition and coverage broadening the diagnosed pool",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Moderately consolidated at the high-acuity end and fragmented "
            "below it. A handful of PE-backed national residential platforms "
            "own much of the branded residential capacity, while PHP/IOP and "
            "outpatient are a long tail of regional programs and independent "
            "clinicians, and virtual entrants are building a parallel national "
            "footprint. Specialty ED beds are scarce and referral-driven, so "
            "reputation, clinical outcomes, and payer-contract breadth matter "
            "more than local density."),
        hhi_or_share=(
            "The residential segment is meaningfully concentrated in a few "
            "national platforms, but no single owner dominates the full "
            "continuum. There is no public ED-treatment census, so operator "
            "concentration is honestly not measured here — the deal corpus "
            "below is the real trading history."),
        consolidation=(
            "PE has assembled the national residential platforms — Monte Nido "
            "(Levine Leichtman, then Revelstoke), Eating Recovery Center (CCMP, "
            "Oak HC/FT), and Discovery Behavioral Health among them — through "
            "roll-up of regional programs, with Eating Recovery Center's "
            "absorption of The Emily Program a marquee tuck-in. In parallel, "
            "venture capital funded virtual disruptors (Equip, Within) rather "
            "than beds, betting the continuum's growth shifts toward home-"
            "delivered higher-level outpatient care."),
        pe_activity=(
            "Active on both sides: buyout capital in the high-per-diem "
            "residential platforms and venture capital in virtual family-based "
            "treatment. The residential thesis rests on scarce specialty beds "
            "and commercial per-diems; the diligence has moved from occupancy "
            "growth to denial/appeal performance, days-paid durability, "
            "out-of-network exposure under the No Surprises Act, and outcomes "
            "evidence that defends length of stay against utilization review."),
        notable_players=[
            "Monte Nido & Affiliates", "Eating Recovery Center (+ The Emily "
            "Program)", "Center for Discovery (Discovery Behavioral Health)",
            "Alsana", "Veritas Collaborative / Walden Behavioral Care",
            "Equip Health", "Within Health", "The Renfrew Center",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Residential per-diem (commercial)", "~$1,000-1,500+/day",
                "The high-acuity revenue unit; the rate is attractive but the "
                "paid days are contested."),
            Kpi("Bed occupancy", "75-90% (target)",
                "The core utilization driver on a fixed 24/7 cost base; empty "
                "beds are non-recoverable margin."),
            Kpi("Authorized ÷ clinically-indicated length of stay", "the gap",
                "Utilization review compresses paid days below indicated days — "
                "the single biggest revenue leak."),
            Kpi("Denial rate + appeal win rate", "program-specific",
                "Appeals capability converts denied days into paid days; a core "
                "competency, not back office."),
            Kpi("Out-of-network / single-case share", "material",
                "OON admissions carry higher rates but rising No-Surprises and "
                "balance-billing risk."),
            Kpi("Program EBITDA margin (residential, full)",
                "15-25% (illustrative)",
                "High operating leverage — strong when full and paid, sharply "
                "lower on soft census or heavy denials."),
        ],
        margin_profile=(
            "An ED residential program is a fixed-cost bed operation: the 24/7 "
            "milieu staff, medical and psychiatric coverage, dietetics, and meal "
            "support are largely fixed to the licensed bed, so contribution "
            "steps up with each occupied, authorized, and paid bed-day and "
            "collapses on soft census or denied days. Because the commercial "
            "per-diem is high, a full and well-collected program earns "
            "attractive mid-to-high-teens (and up) EBITDA margins; the same "
            "cost base half-full, or delivering days the payer will not "
            "authorize, runs near breakeven. The defensible operator is the one "
            "whose clinical outcomes, accreditation, and appeals machine let it "
            "hold length of stay against utilization review — the margin lives "
            "in days-paid, not in the headline rate. Virtual PHP/IOP inverts the "
            "cost structure toward variable clinician time and can scale margin "
            "without beds, at lower per-episode revenue."),
    ),
    risks=[
        Risk("Utilization-review length-of-stay compression", "High",
             "Payers authorize fewer days than clinically indicated; days-paid "
             "vs days-delivered is the dominant revenue leak."),
        Risk("Out-of-network economics under the No Surprises Act", "High",
             "The OON/single-case model that lifts rates is pressured by "
             "balance-billing rules and IDR outcomes."),
        Risk("Census volatility + occupancy", "Medium",
             "Referral-driven, seasonal admissions on a fixed bed-cost base "
             "make occupancy swings expensive."),
        Risk("Parity-litigation and medical-necessity-criteria shifts",
             "Medium",
             "Post-Wit appellate developments and payer guideline revisions can "
             "move the authorized-days baseline either way."),
        Risk("Clinical labor (therapists, dietitians, psychiatry, milieu)",
             "Medium",
             "Multidisciplinary specialty staffing is scarce and expensive; "
             "vacancies cap admissions and quality."),
        Risk("Patient-safety / medical-acuity events", "Medium",
             "High medical acuity (refeeding, cardiac) carries clinical, "
             "licensure, and reputational tail risk."),
    ],
    diligence_questions=[
        "What is the denial rate and appeal win rate by payer, and what is the "
        "days-paid-to-days-delivered ratio?",
        "What is the payer mix and the in-network vs out-of-network split, and "
        "how exposed is revenue to No-Surprises/IDR outcomes?",
        "What is bed occupancy by program and its seasonality, and what is the "
        "referral-source concentration?",
        "What is the average length of stay by level of care versus the "
        "clinically-indicated benchmark and payer authorization patterns?",
        "What is the accreditation and licensure status, and any patient-safety "
        "or survey history?",
        "What is the multidisciplinary staffing model, vacancy rate, and cost "
        "per bed-day?",
        "How is the continuum integrated (residential → PHP → IOP → outpatient), "
        "and does step-down retain patients in-network?",
        "What is the virtual-program strategy and its unit economics versus the "
        "bed base?",
    ],
    insider_lens=[
        "The per-diem is not the revenue — the authorized day is. A residential "
        "program can quote a rich daily rate and still lose money if the payer "
        "only authorizes half the clinically-indicated stay. The whole business "
        "is a fight over length of stay, and the appeals department is a profit "
        "center, not overhead.",
        "This is the one behavioral vertical where commercial pays the freight. "
        "Unlike Medicaid-dominated mental health and SUD, eating-disorder "
        "residential is a commercial-per-diem business — which is why margins "
        "can be attractive and why the payer's utilization-review function is "
        "the adversary in every case.",
        "Wit is the sector's touchstone. The finding that a major payer's "
        "internal criteria were stricter than accepted clinical standards armed "
        "every program's appeals posture; underwriting has to read where the "
        "post-Wit case law and payer guidelines actually sit now, because that "
        "line sets the days-paid baseline.",
        "Out-of-network was the margin and is now the risk. Specialty ED "
        "programs are thinly in-network and historically leaned on OON rates and "
        "single-case agreements — exactly the economics the No Surprises Act and "
        "balance-billing rules are squeezing.",
        "The demand curve got younger and broader. The post-COVID adolescent "
        "surge and the recognition of ARFID, binge-eating disorder, and male/"
        "older/diverse presentations expanded the treated population well beyond "
        "the classic young-female-anorexia profile — a real, durable volume "
        "tailwind, not a blip.",
        "Virtual is eating the outpatient layer. Family-based treatment and "
        "virtual PHP/IOP (Equip, Within) deliver evidence-based higher-level "
        "care at home, extending reach into non-metro markets and shifting where "
        "the continuum's growth — and some of its margin — will sit.",
    ],
    connections=default_connections(
        "eating_disorders",
        deals_sector="behavioral_health",
        extra_pages=[
            ("/industry/eating_disorders",
             "Industry deep-dive — eating-disorder deal history + structure"),
        ],
        connectors=[
            ("census_acs_county_profile",
             "Census ACS — adolescent/young-adult population, the ED demand "
             "denominator"),
            ("npi_provider_taxonomy",
             "NPI taxonomy — psychiatry, psychology, dietetics, and "
             "ED-specialty providers"),
            ("hrsa_data_hpsa_mental_health",
             "HRSA Mental-Health HPSAs — access geography for specialty ED "
             "care"),
            ("cms_open_data_medicare_telehealth_trends",
             "Medicare telehealth trends — the virtual-PHP/IOP shift context"),
            ("cdc_data_places_county",
             "CDC PLACES — county mental-distress prevalence as a demand "
             "proxy"),
            ("oig_leie_exclusions",
             "OIG LEIE — excluded providers (integrity screen)"),
        ],
    ),
    sources=[
        Source("Deloitte Access Economics / STRIPED (Harvard) — Social and "
               "Economic Cost of Eating Disorders in the US", "ACADEMIC",
               "https://www.hsph.harvard.edu/striped/report-economic-costs-of-eating-disorders/"),
        Source("Wit v. United Behavioral Health — level-of-care / medical-"
               "necessity litigation (N.D. Cal.)", "ACADEMIC",
               "https://www.cearight.com/"),
        Source("Mental Health Parity and Addiction Equity Act (MHPAEA) — CMS "
               "parity resources", "GOV",
               "https://www.cms.gov/marketplace/private-health-insurance/mental-health-parity-addiction-equity"),
        Source("CMS — No Surprises Act (balance-billing protections + IDR)",
               "GOV", "https://www.cms.gov/nosurprises"),
        Source("Academy for Eating Disorders (AED) — medical care and "
               "level-of-care standards", "INDUSTRY",
               "https://www.aedweb.org/"),
        Source("American Psychiatric Association — Practice Guideline for the "
               "Treatment of Patients with Eating Disorders", "ACADEMIC",
               "https://www.psychiatry.org/psychiatrists/practice/clinical-practice-guidelines"),
        Source("PE Desk industry deep-dive (eating disorders) + realized-deal "
               "corpus", "INTERNAL",
               "/diligence/tam-sam?template=eating_disorders"),
    ],
    live_figures=live_figures_from_dive("eating_disorders"),
    trends=(
        "Eating-disorder treatment matured from a scattering of academic and "
        "founder-led residential programs into a PE-consolidated, commercial-"
        "pay specialty over the past fifteen years, and two forces now define "
        "its trajectory. The first is the parity-and-utilization-review war. "
        "Because ED care requires long, expensive, stepped courses at high "
        "commercial per-diems, payers manage cost through aggressive level-of-"
        "care and length-of-stay review — and the Wit v. UBH litigation, which "
        "found a major payer's internal criteria stricter than accepted "
        "standards, became the reference point that shifted the appeals posture "
        "in providers' favor, even as appellate rulings complicated the remedy. "
        "The second is a genuine step-up in demand: adolescent presentations "
        "surged during and after COVID, and the diagnostic frame broadened to "
        "ARFID, binge-eating disorder, and male, older, and more diverse "
        "patients, expanding the treated population beyond the classic profile. "
        "Against that backdrop, capital split — buyout sponsors consolidated the "
        "high-acuity residential platforms (Monte Nido, Eating Recovery Center, "
        "Discovery) while venture investors funded virtual family-based "
        "treatment (Equip, Within) that delivers higher-level outpatient care at "
        "home. The forward inflection is the No Surprises Act pressuring the "
        "out-of-network economics residential has leaned on, and a continuing "
        "migration of the continuum's growth toward virtual and lower-acuity "
        "settings that scale without beds."),
    growth_levers=[
        GrowthLever(
            "Prevalence + the adolescent surge",
            "Post-COVID adolescent presentations stepped up and remain "
            "elevated; lifetime ED prevalence is estimated near 9% of the "
            "population — a large, under-treated base.",
            "+4.0%/yr demand", "ACADEMIC"),
        GrowthLever(
            "Diagnosis breadth (ARFID, BED, male/older/diverse)",
            "Formal recognition of ARFID and binge-eating disorder and better "
            "detection beyond young women expand the diagnosed, treatable pool.",
            "+2.0%/yr diagnosed", "ILLUSTRATIVE"),
        GrowthLever(
            "Virtual FBT / PHP-IOP access",
            "Family-based treatment and virtual higher-level outpatient care "
            "reach non-metro patients the bed network never did.",
            "+1.0%/yr access", "ILLUSTRATIVE"),
        GrowthLever(
            "Parity enforcement (Wit legacy)",
            "A strengthened medical-necessity/appeals posture lifts authorized "
            "days per admission — a revenue-per-episode lever, not a volume one.",
            "+ days-paid", "ACADEMIC"),
        GrowthLever(
            "Utilization-review / No-Surprises drag",
            "Length-of-stay compression and pressure on OON economics offset "
            "part of the demand tailwind.",
            "−margin", "ILLUSTRATIVE"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="ED prevalence × the post-COVID adolescent step-up × broadening "
               "diagnosis",
        analysis=(
            "Eating disorders are common and under-treated — lifetime "
            "prevalence is estimated near 9% of the US population in the "
            "STRIPED/epidemiological literature, and the Deloitte/STRIPED cost "
            "study put the total annual economic burden around $64.7B, of which "
            "direct treatment is a small fraction, signaling a large unmet-"
            "treatment gap. Three forces drive treated volume above the "
            "demographic baseline. First, the post-COVID adolescent surge: "
            "hospitals and programs reported a marked, sustained rise in "
            "adolescent (especially young-female) presentations that has not "
            "fully reverted. Second, diagnostic breadth: the formal recognition "
            "of ARFID and binge-eating disorder and improved detection in males, "
            "older adults, and more diverse populations expand the identified, "
            "treatable pool beyond the classic anorexia profile. Third, access: "
            "virtual family-based treatment and virtual PHP/IOP convert "
            "previously-unreachable non-metro demand into treated episodes. The "
            "practical nuance is that realized volume is gated less by demand "
            "than by scarce specialty beds and multidisciplinary staffing at the "
            "high-acuity end — which is exactly why the virtual, staff-light "
            "layer is where incremental volume is easiest to add."),
        basis="ACADEMIC"),
    cost_drivers=[
        CostDriver(
            "Clinical + milieu labor (therapy, psychiatry, medical, dietetics, "
            "24/7 staff)",
            "~55-65% of cost",
            "The dominant, largely fixed-to-the-bed cost — multidisciplinary "
            "specialty staffing plus round-the-clock milieu and meal support.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Facility / bed occupancy cost",
            "~12-18% of cost",
            "The licensed residential real estate and program space that "
            "occupancy must cover; empty beds are non-recoverable.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Dietary / meal program & medical supplies",
            "~6-10% of cost",
            "Supervised meals and nutritional rehabilitation are central to ED "
            "treatment and a real per-patient-day cost.", "ILLUSTRATIVE"),
        CostDriver(
            "Utilization review, billing, appeals & compliance",
            "~7-12% of cost",
            "A denial-heavy RCM function — concurrent review, appeals, and "
            "single-case-agreement negotiation are core, not back office.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Technology / virtual-program platform",
            "~4-8% of cost",
            "EHR plus the tele-infrastructure for the growing virtual PHP/IOP "
            "and FBT layer.", "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "There is no public eating-disorder-treatment census — residential and "
        "PHP/IOP programs are licensed under varied state behavioral/residential "
        "regimes and are not enumerated in a national CMS file — so state "
        "geography is omitted rather than fabricated. Because this is a "
        "commercial-pay, referral-driven, and increasingly virtual sector, "
        "physical geography matters less than payer-network breadth and the "
        "medical-necessity/appeals environment; specialty beds cluster around "
        "the national platforms' hub markets while virtual programs serve "
        "nationally. The Census demographic, NPI-taxonomy, HRSA-shortage, and "
        "telehealth connectors linked below are the honest way to map demand "
        "denominators and access by geography."),
)

register(REPORT)
