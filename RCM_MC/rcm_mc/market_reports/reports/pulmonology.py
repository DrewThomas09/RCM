"""Pulmonology — pulmonary / critical-care / sleep physician practices.

Deals-only deep-dive (no vendored pulmonology facility file; CHEST workforce
data is aggregate-only). Pulmonology is a hybrid specialty: an ambulatory
chronic-disease book (COPD, asthma, ILD, pulmonary hypertension, sleep) plus a
hospital-based critical-care/ICU footprint that ties it to physician-staffing
economics and the No Surprises Act. The investment story is the ambulatory
side — interventional pulmonology and lung-nodule/robotic-bronchoscopy programs,
in-office pulmonary-function and sleep testing, and the deep respiratory-DME
adjacency (home oxygen, CPAP/BiPAP, home ventilators). Consumes
``pulmonology_deep_dive()`` for SOURCED corpus figures.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="pulmonology",
    name="Pulmonology",
    care_setting="Physician services",
    naics="621111",
    one_line_def=(
        "Physician practices treating lung and respiratory disease — COPD, "
        "asthma, interstitial lung disease, pulmonary hypertension, lung-cancer "
        "screening/nodules, and sleep apnea — often combined with critical-care "
        "(ICU/intensivist) work; reimbursed under the Medicare Physician Fee "
        "Schedule (professional plus in-office technical fees) with a large "
        "respiratory-DME and sleep-testing adjacency."),
    tam_headline=TamHeadline(
        value=50.0, unit="$B", growth_pct=5.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "Modeled addressable pool for US pulmonary/respiratory physician "
            "services plus the closely-tied respiratory-DME and sleep-testing "
            "adjacencies — a directional composite, not a filed figure. The "
            "underlying disease burden is far larger: COPD direct medical costs "
            "run ~$24B (see market-size segments, GOV/ACADEMIC) and asthma's "
            "total economic burden is higher still; growth is the modeled "
            "composite of aging, lung-cancer-screening expansion, and rate "
            "updates."),
    ),
    executive_summary=[
        "Pulmonology is a hybrid specialty, and the investable half is the "
        "ambulatory one. A pulmonologist's week splits between an office "
        "chronic-disease book (COPD, asthma, ILD, pulmonary hypertension, "
        "sleep) and hospital critical-care/ICU coverage. The ICU side is "
        "hospital-based physician-staffing economics (and No Surprises Act "
        "exposure); the roll-up thesis lives in the ambulatory clinic and its "
        "ancillaries.",
        "The ancillary set is real: pulmonary-function testing (spirometry/"
        "PFTs), sleep testing (home sleep apnea tests and in-lab "
        "polysomnography), CT lung-cancer screening, and — increasingly — "
        "interventional pulmonology (navigational/robotic bronchoscopy and "
        "pleural procedures) migrating to the office/ASC. These technical fees "
        "are the margin beyond the E&M visit.",
        "Respiratory DME is the sleeper adjacency. COPD and sleep patients need "
        "home oxygen, CPAP/BiPAP, nebulizers, and increasingly home "
        "ventilators — a recurring, resupply-driven DME stream. A pulmonology "
        "platform that captures the DME and sleep testing around its own "
        "patients internalizes a large, sticky revenue pool the specialty "
        "usually leaks to third parties.",
        "Lung-cancer screening and robotic bronchoscopy are the growth edge. "
        "The USPSTF's 2021 expansion of low-dose-CT screening eligibility "
        "widened the funnel, and robotic/navigational bronch (Ion, Monarch) "
        "made peripheral-nodule biopsy an ambulatory, technology-differentiated "
        "procedure — a genuine volume and margin engine for organized programs.",
        "The risks are payment-structure and mix specific: MPFS conversion-"
        "factor erosion on the professional fee, DMEPOS competitive bidding and "
        "oxygen/CPAP coverage rules, sleep-testing site-of-service pressure "
        "(home vs lab), and the hospital-based/critical-care exposure to No "
        "Surprises Act rate-setting and staffing economics.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Referral (PCP/ED/hospital) or lung-screening finding → pulmonary "
            "consult",
            "Diagnostics — spirometry/PFTs, imaging (CXR/CT, low-dose-CT "
            "screening), sleep testing (HSAT/PSG), labs",
            "Diagnosis + plan (inhaler/biologic therapy for COPD/asthma, "
            "antifibrotics for ILD, PAP for sleep apnea, oxygen)",
            "Procedures where indicated — bronchoscopy (incl. navigational/"
            "robotic), EBUS, pleural procedures, nodule biopsy",
            "Durable medical equipment — home oxygen, CPAP/BiPAP, nebulizer, "
            "home ventilator (with resupply)",
            "Longitudinal management + remote monitoring (PAP adherence data, "
            "RPM) and critical-care/ICU episodes when acute",
            "Billing — professional (MPFS) + technical (PFT/sleep/imaging) + DME "
            "(DMEPOS) + inpatient critical-care time codes",
        ],
        sites_of_care=[
            "Pulmonology office / clinic (E&M + PFTs + PAP management)",
            "Accredited sleep lab + home-sleep-test program",
            "Bronchoscopy suite / ASC (interventional pulmonology, robotic "
            "bronch)",
            "Hospital ICU / inpatient consult (critical care — the hospital-"
            "based half)",
            "Respiratory-DME operation (home oxygen, CPAP/BiPAP, ventilators, "
            "resupply)",
        ],
        money_flow=(
            "A pulmonology practice stacks professional fees, in-office "
            "technical fees, and, where it is organized to capture them, DME "
            "and facility fees. The physician bills E&M and procedure codes off "
            "the Medicare Physician Fee Schedule; the practice separately bills "
            "the technical component of its in-office diagnostics — pulmonary-"
            "function testing, sleep studies, and (in a screening program) "
            "low-dose CT. Interventional procedures (navigational/robotic "
            "bronchoscopy, EBUS, pleural work) done in an office suite or ASC "
            "add technical/facility payment. The distinctive adjacency is "
            "durable medical equipment: COPD and sleep-apnea patients need home "
            "oxygen, CPAP/BiPAP, nebulizers, and home ventilators billed under "
            "the DMEPOS fee schedule with recurring resupply — a large stream "
            "most practices leak to third-party suppliers. On the hospital side, "
            "critical-care/ICU work is billed as time-based critical-care and "
            "inpatient codes, and often sits inside a hospital-based staffing "
            "arrangement. Commercial payers pay a multiple of Medicare."),
        key_players=(
            "The independent segment is fragmented among pulmonary/critical-care "
            "(and pulmonary/sleep) groups and hospital-employed pulmonologists, "
            "with critical-care coverage frequently delivered through hospital-"
            "based physician-staffing organizations. There is no dominant "
            "national pulmonology PPM at the scale of GI or ortho; the organized "
            "capital tends to sit in interventional-pulmonology / lung-nodule "
            "programs, respiratory-DME platforms, and sleep networks. Adjacent: "
            "robotic-bronch and device makers (Intuitive/Ion, J&J/Monarch, "
            "Olympus, Medtronic), respiratory-DME suppliers, PAP/ventilator "
            "makers (ResMed, Philips Respironics, React Health), and the "
            "biologic/antifibrotic drugmakers whose therapies pull specialist "
            "volume."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("US COPD direct medical cost", "~$24.00B",
                    "GOV · CDC / NHLBI COPD cost estimates (directional)"),
            Segment("US asthma total economic burden", "high tens of $B",
                    "ACADEMIC · Nurmagambetov et al., peer-reviewed burden "
                    "studies"),
            Segment("Adults with COPD (US)", "~15M+ diagnosed",
                    "GOV · CDC BRFSS / NHIS"),
            Segment("Adults with obstructive sleep apnea (US)",
                    "tens of millions (largely undiagnosed)",
                    "ACADEMIC · AASM / peer-reviewed prevalence estimates"),
            Segment("Low-dose-CT lung-screening-eligible population",
                    "expanded under 2021 USPSTF criteria",
                    "GOV · USPSTF lung-cancer-screening recommendation"),
        ],
        growth_drivers=[
            "Aging + smoking-legacy COPD/lung-disease prevalence — the base",
            "Lung-cancer-screening expansion (2021 USPSTF criteria) — new funnel",
            "Robotic/navigational bronchoscopy — ambulatory nodule-biopsy volume",
            "Sleep-apnea diagnosis + home-sleep-test shift — testing volume",
            "Respiratory-DME resupply + home-ventilation growth — recurring "
            "stream",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Medicare / MA": 0.55,
            "Commercial": 0.33,
            "Medicaid / other": 0.12,
        },
        rate_mechanics=[
            "Medicare Physician Fee Schedule — professional E&M and procedure "
            "fees plus the technical component of in-office pulmonary-function "
            "and sleep testing.",
            "Sleep testing — home sleep apnea tests (HSAT) and in-lab "
            "polysomnography; payers push toward the lower-cost home test, "
            "compressing lab volume.",
            "DMEPOS fee schedule + competitive bidding — home oxygen, CPAP/BiPAP, "
            "nebulizers, and ventilators, with recurring resupply and "
            "adherence/coverage conditions (e.g. PAP compliance rules).",
            "Interventional-pulmonology / ASC facility payment — navigational/"
            "robotic bronchoscopy, EBUS, and pleural procedures paid a "
            "technical/facility fee when done in an office suite or ASC.",
            "Critical-care time-based codes (99291/99292) + inpatient E&M — the "
            "hospital-based half, often inside a staffing arrangement.",
            "Lung-cancer-screening (low-dose CT) coverage — a covered preventive "
            "benefit with shared-decision-making and eligibility conditions.",
            "Commercial multiples + prior authorization — commercial pays "
            "MPFS-plus, but biologics, advanced imaging, and DME are prior-auth "
            "gated.",
        ],
        reimbursement_risk=(
            "Pulmonology's risk is spread across an unusually wide payment "
            "surface. The professional fee is squeezed by a flat-to-declining "
            "MPFS conversion factor with no inflation update. The DME adjacency "
            "— attractive because it is recurring — is exposed to DMEPOS "
            "competitive bidding, oxygen and PAP coverage/compliance rules, and "
            "audit risk on resupply, so its economics can move with a bidding "
            "round or a coverage revision. Sleep testing faces a durable site-"
            "of-service push from the in-lab study toward the cheaper home test, "
            "compressing lab revenue. Interventional-pulmonology margin depends "
            "on favorable ASC/office facility payment and on device cost "
            "(robotic-bronch capital and disposables) against fixed procedure "
            "rates. And the hospital-based/critical-care half carries No "
            "Surprises Act rate-setting and the broader repricing of physician-"
            "staffing economics that reset valuations across hospital-based "
            "specialties. The offset is a genuine aging-driven volume tailwind "
            "and the still-widening lung-screening funnel."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("Medicare Physician Fee Schedule (annual Final Rule)",
                 "Sets the professional and in-office technical RVUs and the "
                 "conversion factor — the core price of pulmonology revenue.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
            Rule("DMEPOS fee schedule + competitive bidding + oxygen/PAP "
                 "coverage rules",
                 "Governs the respiratory-DME adjacency (home oxygen, CPAP/"
                 "BiPAP, ventilators) and its recurring resupply economics.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/dmepos"),
            Rule("USPSTF low-dose-CT lung-cancer-screening recommendation "
                 "(2021 expansion)",
                 "Widened screening eligibility (age/pack-year) — the funnel "
                 "for nodule work-up and interventional-pulmonology volume.",
                 "https://www.uspreventiveservicestaskforce.org/"),
            Rule("Hospital OPPS / ASC Payment System + ASC Covered Procedures "
                 "List",
                 "Sets facility payment for bronchoscopy and pleural procedures "
                 "moving to the office/ASC — the site-of-service economics.",
                 "https://www.cms.gov/medicare/payment/prospective-payment-systems/ambulatory-surgical-center-asc"),
            Rule("No Surprises Act (out-of-network / IDR)",
                 "Governs the hospital-based critical-care half's out-of-network "
                 "billing and the arbitration that reset staffing economics.",
                 "https://www.cms.gov/nosurprises"),
            Rule("Stark / Anti-Kickback (in-office ancillary exception)",
                 "Governs self-referral to owned PFT/sleep/imaging/DME and any "
                 "DME/device referral relationships.",
                 "https://www.cms.gov/medicare/regulations-guidance/physician-self-referral"),
        ],
        policy_watch=[
            "MPFS conversion-factor cuts and pulmonary/sleep RVU revaluation",
            "DMEPOS competitive-bidding rounds and oxygen/PAP coverage-rule "
            "changes",
            "Sleep testing site-of-service (home vs lab) and PAP-compliance "
            "policy",
            "ASC-CPL additions for bronchoscopy/pleural procedures (more "
            "ambulatory work)",
            "No Surprises Act IDR outcomes and hospital-based/critical-care "
            "staffing economics",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Pulmonology is fragmented among pulmonary/critical-care and "
            "pulmonary/sleep groups, hospital-employed pulmonologists, and — for "
            "the ICU coverage — hospital-based physician-staffing organizations. "
            "No dominant national platform exists. The acquirable pool for an "
            "ambulatory thesis is the independent group with organized ancillary "
            "capacity (sleep, PFT, screening, DME) or an interventional-"
            "pulmonology program."),
        hhi_or_share=(
            "No dominant national owner and no vendored pulmonology facility "
            "file, so operator concentration is honestly not measured here. The "
            "relevant concentration sits in the respiratory-DME and PAP/"
            "ventilator device markets and in hospital-based critical-care "
            "staffing, not in office-based practice ownership."),
        consolidation=(
            "Consolidation has been selective rather than a broad PPM roll-up: "
            "interventional-pulmonology / lung-nodule programs, sleep networks, "
            "and respiratory-DME platforms attract organized capital because "
            "they carry technical, facility, or recurring-DME margin, while the "
            "pure office chronic-disease book and the hospital-based critical-"
            "care work are harder to underwrite as standalone platforms. Where "
            "practices combine, it is often into multispecialty groups or health "
            "systems, or under staffing organizations for the ICU coverage."),
        pe_activity=(
            "PE interest concentrates on the ancillary-rich edges — "
            "interventional pulmonology and robotic bronch, sleep testing, and "
            "respiratory DME — rather than on rolling up general pulmonology. "
            "Diligence centers on the DME adjacency's exposure to competitive "
            "bidding and coverage rules, sleep's home-vs-lab site-of-service "
            "shift, device cost in interventional programs, and the separation "
            "of the investable ambulatory book from the No-Surprises-exposed "
            "hospital-based critical-care work."),
        notable_players=[
            "Interventional-pulmonology / lung-nodule programs",
            "Regional pulmonary/critical-care & pulmonary/sleep groups",
            "Respiratory-DME platforms", "Sleep-testing networks",
            "Hospital-based critical-care staffing groups",
            "Robotic-bronch makers (Intuitive/Ion, J&J/Monarch)",
            "PAP/ventilator makers (ResMed, Philips Respironics)",
            "Hospital-employed pulmonology groups",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Ancillary / technical revenue (% of total)", "25-45%",
                "PFT, sleep testing, screening CT, and DME — the platform value "
                "beyond the E&M visit."),
            Kpi("Sleep-test mix (home vs in-lab)", "shifting to home",
                "Home tests are lower-cost and payer-preferred; lab volume and "
                "revenue per study are under pressure."),
            Kpi("Respiratory-DME resupply revenue", "recurring per-patient",
                "Oxygen/CPAP/ventilator resupply is sticky, recurring revenue — "
                "but exposed to competitive bidding and audits."),
            Kpi("Interventional-bronch case volume & utilization", "cases / lab",
                "The fixed-cost procedural/robotic chassis; idle capacity is "
                "lost margin."),
            Kpi("Provider productivity (wRVUs / physician)",
                "vs MGMA benchmark",
                "Split across clinic and ICU coverage — the professional-fee "
                "engine and a scheduling constraint."),
            Kpi("Payer mix (commercial vs Medicare)", "commercial lifts blend",
                "Commercial pays a multiple of Medicare, so mix drives realized "
                "yield."),
            Kpi("Platform EBITDA margin", "mid-teens to 20s (illustrative)",
                "Richer where sleep, screening, and DME ancillaries are built "
                "out; thinner on a pure office/ICU book."),
        ],
        margin_profile=(
            "Pulmonology's margin story is ancillary and DME capture around a "
            "modest professional fee. The office E&M and inpatient critical-care "
            "work are the throughput base, squeezed by a flat MPFS conversion "
            "factor; the margin lives in the technical services (pulmonary-"
            "function and sleep testing, screening CT), in interventional "
            "bronchoscopy where a program has the volume to cover the robotic "
            "chassis, and above all in the respiratory-DME resupply stream that "
            "most practices leak to outside suppliers. The offsets are the DME "
            "adjacency's exposure to competitive bidding and coverage rules, the "
            "steady erosion of in-lab sleep revenue toward home testing, device "
            "cost in interventional programs, and the No-Surprises repricing of "
            "the hospital-based critical-care half — so the durable margin comes "
            "from an organized ambulatory ancillary book, not the ICU."),
    ),
    risks=[
        Risk("MPFS conversion-factor erosion", "High",
             "A structural squeeze on the professional fee with limited offset "
             "on the pure office/ICU book."),
        Risk("Respiratory-DME competitive bidding & coverage/audit risk",
             "High",
             "The recurring DME adjacency is exposed to bidding rounds, oxygen/"
             "PAP coverage rules, and resupply audits that can reset its "
             "economics."),
        Risk("Sleep-testing site-of-service shift (home vs lab)", "Medium",
             "Payer preference for home tests compresses in-lab polysomnography "
             "volume and revenue per study."),
        Risk("Device cost & utilization in interventional bronchoscopy",
             "Medium",
             "Robotic-bronch capital and disposables against fixed procedure "
             "rates require volume to be accretive."),
        Risk("No Surprises Act / critical-care staffing economics", "Medium",
             "The hospital-based half is exposed to IDR rate-setting and the "
             "repricing that hit hospital-based specialties."),
        Risk("Physician retention / workforce", "Medium",
             "Pulmonary/critical-care physicians are scarce and split across "
             "sites; retention and call coverage are decisive."),
        Risk("Prior authorization on biologics & advanced imaging", "Low",
             "Administrative friction on asthma/ILD biologics and CT that slows "
             "throughput and cash collection."),
    ],
    diligence_questions=[
        "What share of EBITDA is ambulatory ancillary (PFT/sleep/screening/DME) "
        "versus hospital-based critical-care, and how is each exposed to "
        "payment policy?",
        "How large and durable is the respiratory-DME stream, and what is its "
        "exposure to competitive bidding, coverage rules, and resupply audits?",
        "What is the sleep-testing mix (home vs in-lab), and how is lab volume "
        "trending under the home-test shift?",
        "For any interventional-pulmonology program, what are case volumes, "
        "device/robotic costs, and site-of-service (office/ASC/HOPD)?",
        "How much revenue is hospital-based/critical-care, and what is the No "
        "Surprises Act and staffing-contract exposure?",
        "What is the lung-cancer-screening program's volume and nodule-work-up "
        "funnel, and how is it reimbursed?",
        "What is the payer mix and commercial-rate position, and how durable "
        "are the top contracts?",
        "How concentrated is revenue in a few physicians across clinic and ICU, "
        "and what are their retention and call-coverage terms?",
    ],
    insider_lens=[
        "Underwrite the ambulatory book, not the ICU. Pulmonology's investable "
        "value is the clinic and its ancillaries (sleep, PFT, screening, "
        "interventional bronch, DME); the hospital critical-care half is "
        "staffing economics with No-Surprises exposure — a different, lower-"
        "multiple business hiding inside the same physician.",
        "The DME is the quiet prize. COPD and sleep patients need recurring "
        "oxygen, CPAP, and ventilator resupply, and most practices hand that "
        "revenue to a third-party supplier — a pulmonology platform that "
        "internalizes its own DME captures a large, sticky stream, at the cost "
        "of taking on competitive-bidding and audit exposure.",
        "Robotic bronch is a volume-or-nothing bet. Navigational/robotic "
        "bronchoscopy makes peripheral-nodule biopsy an ambulatory, "
        "differentiated procedure — but the capital and disposables only pencil "
        "with a real lung-nodule program feeding it, so the screening funnel "
        "and referral base matter more than the machine.",
        "Sleep is migrating out from under you. The in-lab polysomnography that "
        "made sleep labs valuable is being replaced by cheaper home tests; the "
        "durable sleep economics are in diagnosis-to-PAP-to-resupply "
        "management, not in owning lab beds.",
        "Screening changed the funnel. The 2021 USPSTF expansion of low-dose-CT "
        "eligibility enlarged the population feeding nodule work-up and "
        "interventional pulmonology — the practices organized to run screening "
        "and close the loop to biopsy capture disproportionate downstream "
        "volume.",
    ],
    connections=default_connections(
        "pulmonology",
        deals_sector="pulmonology",
        extra_pages=[
            ("/industry/pulmonology",
             "Industry deep-dive — pulmonology deal history + structure"),
        ],
        connectors=[
            ("cms_open_data_mup_physician_by_provider_service",
             "Medicare physician utilization — PFT/bronchoscopy/critical-care "
             "service volume"),
            ("cms_open_data_mup_dme_by_supplier_service",
             "Medicare DME by supplier — home oxygen/CPAP/ventilator resupply "
             "read"),
            ("cms_open_data_mup_outpatient_by_provider_service",
             "Medicare outpatient utilization — sleep/bronch HOPD vs ambulatory "
             "site read"),
            ("cdc_data_places_county",
             "CDC PLACES — county COPD/asthma prevalence for demand mapping"),
            ("npi_provider_taxonomy",
             "NPI taxonomy — pulmonary/critical-care/sleep workforce supply"),
            ("open_payments_general_payments_2024",
             "Open Payments — device/biologic-maker payments to pulmonologists"),
        ],
    ),
    sources=[
        Source("CDC / NHLBI — COPD surveillance and cost estimates", "GOV",
               "https://www.cdc.gov/copd/"),
        Source("Nurmagambetov, Kuwahara & Garbe — The economic burden of "
               "asthma in the US (Ann Am Thorac Soc)", "ACADEMIC",
               "https://www.atsjournals.org/"),
        Source("USPSTF — Lung Cancer: Screening (low-dose CT) recommendation, "
               "2021", "GOV",
               "https://www.uspreventiveservicestaskforce.org/"),
        Source("CMS — Medicare Physician Fee Schedule annual Final Rule (RVUs, "
               "conversion factor)", "GOV",
               "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
        Source("CMS — DMEPOS fee schedule, competitive bidding, and oxygen/PAP "
               "coverage rules", "GOV",
               "https://www.cms.gov/medicare/payment/fee-schedules/dmepos"),
        Source("American College of Chest Physicians (CHEST) / American Academy "
               "of Sleep Medicine — workforce and practice data", "INDUSTRY",
               "https://www.chestnet.org/"),
        Source("PE Desk industry deep-dive (pulmonology) + realized-deal "
               "corpus", "INTERNAL",
               "/diligence/tam-sam?template=pulmonology"),
    ],
    live_figures=live_figures_from_dive("pulmonology"),
    trends=(
        "Pulmonology has not followed the classic physician-PPM path, because "
        "it is really two businesses stapled together: an ambulatory chronic-"
        "respiratory clinic and a hospital-based critical-care/ICU practice. "
        "The ICU half moved with the rest of hospital-based medicine — into "
        "physician-staffing organizations and, after the No Surprises Act, "
        "through a hard repricing of out-of-network and contract economics. The "
        "ambulatory half is where the investment story developed, along three "
        "lines. First, interventional pulmonology matured: navigational and "
        "robotic bronchoscopy (Ion, Monarch) turned peripheral-nodule biopsy "
        "into an ambulatory, technology-differentiated procedure, and the 2021 "
        "USPSTF expansion of low-dose-CT lung-cancer screening widened the "
        "funnel feeding it. Second, the respiratory-DME and sleep adjacencies "
        "drew attention as recurring, resupply-driven revenue — even as sleep "
        "testing itself migrated from the in-lab study to the cheaper home "
        "test. Third, biologics for severe asthma and antifibrotics for ILD "
        "pulled complex management back to the specialist. The forward tensions "
        "are payment-policy — MPFS erosion on the professional fee, DMEPOS "
        "competitive bidding and coverage rules on the DME stream, and the sleep "
        "site-of-service shift — against a durable aging and lung-disease "
        "prevalence tailwind."),
    growth_levers=[
        GrowthLever(
            "Lung-cancer screening + nodule / interventional-bronch program",
            "The 2021 USPSTF screening expansion enlarges the nodule funnel; "
            "robotic/navigational bronch converts it to ambulatory procedure "
            "volume.",
            "primary ambulatory engine", "GOV"),
        GrowthLever(
            "Aging + smoking-legacy respiratory prevalence",
            "COPD, ILD, and pulmonary-hypertension burden grows with an aging "
            "population — the durable E&M and management base.",
            "+ mid-single %/yr", "GOV"),
        GrowthLever(
            "Respiratory-DME resupply capture",
            "Internalizing home oxygen, CPAP/BiPAP, and ventilator resupply "
            "around the practice's own patients adds a recurring stream.",
            "+ recurring DME", "ILLUSTRATIVE"),
        GrowthLever(
            "Sleep diagnosis-to-therapy management",
            "Rising OSA diagnosis (home-test-enabled) plus PAP setup, "
            "adherence, and resupply management — a longitudinal revenue loop.",
            "+ sleep management", "ILLUSTRATIVE"),
        GrowthLever(
            "Biologics / antifibrotics pulling specialist volume",
            "Severe-asthma biologics and ILD antifibrotics require specialist "
            "management and monitoring, concentrating complex patients.",
            "+ complex mgmt", "ILLUSTRATIVE"),
        GrowthLever(
            "MPFS / DMEPOS-bidding / sleep-shift drag",
            "A flat professional fee, DME competitive bidding, and the in-lab-"
            "to-home sleep shift are the structural headwinds.",
            "policy risk", "GOV"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Aging + smoking-legacy lung disease × the screening funnel",
        analysis=(
            "The demand base is chronic respiratory disease in an aging "
            "population — COPD (more than 15 million diagnosed US adults), "
            "asthma, interstitial lung disease, pulmonary hypertension, and a "
            "large, still-largely-undiagnosed obstructive-sleep-apnea "
            "population — which generates a steady flow of office visits, "
            "pulmonary-function and sleep testing, and durable-medical-equipment "
            "need. Layered on that base, the 2021 USPSTF expansion of low-dose-"
            "CT lung-cancer screening enlarged the population entering nodule "
            "work-up, and robotic/navigational bronchoscopy turned the resulting "
            "biopsies into ambulatory procedural volume — the actual growth "
            "edge. The offsets are the migration of sleep testing from lab to "
            "home (which lowers revenue per study) and the split of physician "
            "time between clinic and ICU coverage, which caps how much ambulatory "
            "volume a given group can convert."),
        basis="GOV"),
    cost_drivers=[
        CostDriver(
            "Physician & advanced-practice clinical labor",
            "~40-50% of cost",
            "Pulmonary/critical-care physicians and APPs split across clinic and "
            "ICU — the scarce, expensive core and a scheduling constraint.",
            "ILLUSTRATIVE"),
        CostDriver(
            "DME acquisition & resupply logistics",
            "large where DME is internalized",
            "Home oxygen, CPAP/BiPAP, and ventilator equipment plus resupply "
            "fulfillment — a channel cost that comes with the recurring "
            "revenue.", "ILLUSTRATIVE"),
        CostDriver(
            "Devices, disposables & imaging capital (robotic bronch, CT, sleep)",
            "~10-18% of cost",
            "The interventional and diagnostic chassis — robotic-bronch capital "
            "and disposables, CT, and sleep-testing equipment.", "ILLUSTRATIVE"),
        CostDriver(
            "Support staff, respiratory therapists & sleep techs",
            "~12-18% of cost",
            "The care-team overhead behind PFTs, sleep studies, PAP setup, and "
            "DME/adherence management.", "ILLUSTRATIVE"),
        CostDriver(
            "G&A, billing, prior-auth & compliance (DME audits)",
            "~10-15% of cost",
            "Heavy prior-authorization on biologics/imaging and a real DME "
            "audit/compliance overhead.", "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "No vendored pulmonology facility file exists — a pulmonology group is a "
        "physician practice, not a Medicare-certified facility — so state "
        "geography is omitted rather than fabricated. Qualitatively, the "
        "footprint tracks respiratory-disease burden (COPD and smoking-legacy "
        "prevalence concentrated in Appalachian, Southern, and Rust-Belt "
        "states), the local balance of hospital-employed versus independent "
        "pulmonologists, and — for the DME adjacency — DMEPOS competitive-"
        "bidding areas and state DME licensure. Interventional-pulmonology and "
        "lung-screening programs cluster where referral bases and CT/robotic "
        "capacity exist. The CDC PLACES county prevalence connector and the "
        "Medicare physician-, outpatient-, and DME-utilization connectors linked "
        "below map COPD/asthma burden and pulmonary/DME service volume by "
        "geography — the honest footprint read for where demand and the "
        "screening funnel are largest."),
)

register(REPORT)
