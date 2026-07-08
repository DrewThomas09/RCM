"""Cardiology — cardiovascular physician practices (the OBL roll-up thesis).

Deals-only deep-dive (no vendored cardiology facility file; ACC workforce data
is aggregate-only). The current PE thesis is site-of-service migration of cath,
peripheral-vascular, and EP procedures into physician-owned office-based labs
(OBLs) and ASCs, so the qualitative sections are authored around the technical/
facility-fee capture, the non-facility practice-expense differential, in-office
imaging ancillaries, Stark/site-neutral exposure, and value-based cardiac care.
Consumes ``cardiology_deep_dive()`` for SOURCED corpus deal figures.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="cardiology",
    name="Cardiology",
    care_setting="Physician services",
    naics="621111",
    one_line_def=(
        "Cardiovascular physician practices — general and interventional "
        "cardiology, electrophysiology, and vascular — increasingly performing "
        "catheterization, peripheral-vascular, and rhythm procedures in "
        "physician-owned office-based labs (OBLs) and ASCs; reimbursed under the "
        "Medicare Physician Fee Schedule (professional plus in-office technical/"
        "facility fees) with commercial multiples."),
    tam_headline=TamHeadline(
        value=250.0, unit="$B", growth_pct=6.0, basis_label="GOV",
        basis_note=(
            "AHA/CDC estimate US cardiovascular-disease direct medical costs "
            "above ~$250B (and far higher including lost productivity); the "
            "cardiology physician-services and OBL-addressable slice is a "
            "fraction of that total. Growth is the modeled composite of "
            "aging-driven volume, site-of-service migration to OBLs, and rate "
            "updates."),
    ),
    executive_summary=[
        "Cardiology is the newest big physician roll-up, and the thesis is site "
        "of service. Moving diagnostic cath, peripheral-vascular (PAD), and "
        "increasingly electrophysiology procedures out of the hospital into "
        "physician-owned office-based labs (OBLs) and ASCs captures the "
        "facility/technical fee the hospital used to earn — the same procedure "
        "at a fraction of the cost and a multiple of the professional-fee "
        "margin.",
        "In-office ancillaries are unusually rich. Cardiology owns high-value "
        "technical services — echocardiography, nuclear cardiology, vascular "
        "ultrasound, stress testing, and the cath/EP lab itself — so a "
        "cardiology platform captures far more than the E&M visit; higher "
        "non-facility practice-expense RVUs make office-based procedures "
        "lucrative.",
        "The buyers arrived late and fast. After derm, GI, and ortho, PE built "
        "cardiology platforms in a rush (Cardiovascular Associates of America, "
        "US Heart & Vascular, US Cardiology Partners, Novocardia) — often in "
        "partnership with health systems and payers chasing value-based cardiac "
        "care.",
        "Value-based cardiology is a real second thesis. Cardiometabolic "
        "disease is enormous and expensive; models that take risk on CHF/CAD "
        "populations (and CMS episode and ACO frameworks) reward keeping cardiac "
        "patients out of the hospital — an aligned but operationally hard bet "
        "layered on fee-for-service.",
        "The risks are payment-structure specific: MPFS conversion-factor "
        "erosion on the professional fee, OBL/site-of-service reimbursement and "
        "Stark exposure on physician-owned labs, appropriate-use/medical-"
        "necessity scrutiny of imaging and stenting, and device cost on fixed "
        "procedure rates.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Referral (PCP/ED) or self-presentation → cardiology consult",
            "Non-invasive diagnostics (ECG, echo, stress, nuclear, vascular "
            "ultrasound, CT/CTA)",
            "Risk stratification → decision for intervention or medical "
            "management",
            "Invasive/interventional procedure — diagnostic cath, PCI/stent, PAD "
            "intervention, EP study/ablation, device (pacemaker/ICD) implant",
            "Site selection — OBL / ASC / HOPD (the economic fork)",
            "Post-procedure follow-up + remote device/rhythm monitoring "
            "(CIED, RPM)",
            "Billing — professional (MPFS) + technical/facility (in-office or "
            "facility) + device",
        ],
        sites_of_care=[
            "Cardiology office / clinic (E&M + non-invasive imaging)",
            "Office-based lab (OBL) — physician-owned cath/PAD/EP suite (the "
            "thesis)",
            "Ambulatory surgery center (ASC) — cardiac codes now on the ASC-CPL",
            "Hospital cath / EP lab (HOPD) — the site procedures migrate FROM",
            "Remote monitoring (implantable-device and rhythm telemetry) — "
            "recurring",
        ],
        money_flow=(
            "A cardiology practice stacks professional fees, technical/ancillary "
            "fees, and (increasingly) facility fees. The physician bills E&M and "
            "procedure codes off the Medicare Physician Fee Schedule; the "
            "practice separately bills the technical component of its in-office "
            "diagnostics — echocardiography, nuclear cardiology, vascular "
            "ultrasound, stress testing — which are high-value ancillaries. The "
            "strategic shift is procedural: performing diagnostic catheterization, "
            "peripheral-vascular interventions, and select electrophysiology "
            "cases in a physician-owned office-based lab (OBL) or ASC lets the "
            "practice capture the technical/facility payment the hospital "
            "outpatient department used to earn. Because non-facility practice-"
            "expense RVUs are higher (the practice, not a hospital, bears the "
            "overhead), office-based procedures pay the practice more than the "
            "professional fee alone. Commercial payers pay multiples of "
            "Medicare. Devices (stents, ICDs, pacemakers) carry separate device "
            "payment. On top of fee-for-service, value-based cardiac contracts "
            "pay care-management fees and share savings for managing high-cost "
            "CHF/CAD populations."),
        key_players=(
            "The PE-backed cardiovascular platforms now define the independent "
            "segment — Cardiovascular Associates of America (Webster Equity), US "
            "Heart & Vascular (Ares), US Cardiology Partners, Novocardia "
            "(Deerfield), and CardioOne (enablement). Large independent groups "
            "(Cardiovascular Institute of the South and other regional anchors) "
            "hold entire markets. On the other side, hospital systems employ the "
            "majority of cardiologists — cardiology was one of the first "
            "specialties hospitals acquired for the downstream procedural "
            "revenue. Adjacent: device makers (Medtronic, Abbott, Boston "
            "Scientific, Edwards), remote-monitoring vendors, and payers building "
            "cardiometabolic risk programs."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("US cardiovascular-disease direct medical cost",
                    "~$250.00B+",
                    "GOV · AHA/CDC cost-of-CVD estimates"),
            Segment("Cardiologists in the US", "~33,000",
                    "INDUSTRY · ACC/AAMC workforce (directional)"),
            Segment("Office-based labs (OBLs) doing cardiac/vascular work",
                    "growing rapidly",
                    "ILLUSTRATIVE · industry OBL trend, directional"),
            Segment("Cardiac codes on the ASC Covered Procedures List",
                    "expanding each year",
                    "GOV · CMS ASC-CPL additions"),
            Segment("Implantable cardiac device + remote-monitoring base",
                    "large recurring",
                    "ILLUSTRATIVE · CIED install base, directional"),
        ],
        growth_drivers=[
            "Aging + cardiometabolic-disease prevalence — the demographic base",
            "Site-of-service migration to OBLs/ASCs — capturing the facility fee",
            "Cardiac-code additions to the ASC-CPL — widening the ambulatory set",
            "In-office imaging/diagnostics ancillary expansion",
            "Value-based cardiac care — risk contracts on CHF/CAD populations",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Medicare / MA": 0.55,
            "Commercial": 0.35,
            "Medicaid / other": 0.10,
        },
        rate_mechanics=[
            "Medicare Physician Fee Schedule — professional fees plus the "
            "technical component of in-office diagnostics; higher non-facility "
            "practice-expense RVUs make office procedures pay the practice more.",
            "Office-based-lab (OBL) reimbursement — the practice bills the "
            "technical/facility portion for cath/PAD/EP done in a physician-"
            "owned lab, capturing what the HOPD used to earn.",
            "ASC payment system — cardiac codes added to the ASC Covered "
            "Procedures List paid a packaged facility fee (a discount to HOPD).",
            "Device / pass-through payment — stents, ICDs, and pacemakers carry "
            "separate device payment so device-heavy cases are not underwater.",
            "Remote monitoring & CCM codes — implantable-device and rhythm "
            "monitoring plus chronic-care-management codes — recurring "
            "technical/management revenue.",
            "Commercial multiples + prior authorization — payers pay MPFS-plus "
            "multiples but manage imaging and elective PCI via prior auth and "
            "appropriate-use criteria.",
            "Value-based cardiac contracts — episode/ACO and payer "
            "cardiometabolic programs paying management fees and shared savings.",
        ],
        reimbursement_risk=(
            "Two structures dominate the risk. First, the Medicare Physician Fee "
            "Schedule conversion factor — flat-to-declining in nominal terms "
            "while costs rise — squeezes the professional fee with no inflation "
            "update, and budget neutrality reshuffles RVUs among cardiology's "
            "codes (imaging and procedures have been repeatedly revalued). "
            "Second, site of service and Stark: the OBL thesis depends on "
            "physician-owned labs continuing to bill favorable technical/"
            "facility rates, and any move toward site-neutral payment — or "
            "tighter enforcement of self-referral to owned imaging and labs — "
            "would compress the exact margin the roll-up is priced on. Layer on "
            "appropriate-use and medical-necessity scrutiny of high-volume "
            "imaging (nuclear/echo) and elective stenting (the legacy of "
            "overutilization enforcement), prior-authorization friction, and "
            "device-cost inflation on fixed procedure rates, and the cardiology "
            "margin has multiple policy-sensitive pressure points — offset by a "
            "genuine aging-driven volume tailwind and the still-open HOPD-to-OBL "
            "arbitrage."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("Medicare Physician Fee Schedule (annual Final Rule)",
                 "Sets the professional and in-office technical RVUs and the "
                 "conversion factor — the core price of cardiology revenue.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
            Rule("Physician self-referral law (Stark) + in-office ancillary "
                 "exception",
                 "Governs self-referral to physician-owned imaging, labs, and "
                 "OBLs — what makes ancillary and OBL capture legal.",
                 "https://www.cms.gov/medicare/regulations-guidance/physician-self-referral"),
            Rule("Hospital OPPS / ASC Payment System + ASC Covered Procedures "
                 "List",
                 "Sets OBL/ASC facility payment and which cardiac codes are "
                 "ambulatory-payable — the site-of-service arbitrage rules.",
                 "https://www.cms.gov/medicare/payment/prospective-payment-systems/ambulatory-surgical-center-asc"),
            Rule("Anti-Kickback Statute + physician-ownership safe harbors",
                 "Governs OBL/ASC investment and device/referral relationships; "
                 "fair-market-value and safe-harbor compliance are diligence "
                 "gates.",
                 "https://oig.hhs.gov/compliance/safe-harbor-regulations/"),
            Rule("Appropriate Use Criteria / medical-necessity (imaging & PCI)",
                 "Coverage conditions and utilization scrutiny on nuclear/echo "
                 "imaging and elective stenting — a quality-of-revenue check.",
                 "https://www.cms.gov/medicare/quality/appropriate-use-criteria-program"),
            Rule("No Surprises Act (out-of-network protections)",
                 "Limits balance billing at facilities/OBLs and hospital-based "
                 "cardiology arrangements.",
                 "https://www.cms.gov/nosurprises"),
        ],
        policy_watch=[
            "MPFS conversion-factor cuts and cardiology-specific RVU "
            "revaluations",
            "Site-neutral payment (HOPD vs OBL vs ASC vs office) — the central "
            "swing for the OBL thesis",
            "Cardiac-code additions to the ASC-CPL (more EP/structural cases "
            "ambulatory)",
            "Stark/self-referral enforcement on physician-owned labs and "
            "imaging",
            "FTC/state scrutiny of cardiology roll-ups and physician-market "
            "concentration",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Cardiology is still fragmented among independent single- and "
            "multi-specialty cardiovascular groups and hospital-employed "
            "cardiologists — but PE consolidation arrived recently and moved "
            "fast, and hospitals already employ the majority (cardiology was an "
            "early hospital-employment target for its downstream procedural "
            "revenue). The acquirable pool is the remaining large independent "
            "cardiovascular groups."),
        hhi_or_share=(
            "No dominant national owner; hospital systems employ most "
            "cardiologists, and PE platforms (CVAUSA, US Heart & Vascular, US "
            "Cardiology Partners, Novocardia) are assembling the independent "
            "segment quickly. No vendored cardiology facility file exists, so "
            "operator concentration is honestly not measured here."),
        consolidation=(
            "A late but rapid roll-up — Webster's Cardiovascular Associates of "
            "America, Ares' US Heart & Vascular, US Cardiology Partners, and "
            "Deerfield's Novocardia formed within a few years, frequently "
            "partnering with health systems and payers rather than purely "
            "competing with them. The model centralizes the MSO back office, "
            "expands OBL/ASC capacity, builds imaging ancillaries, and adds "
            "value-based cardiac contracts. Premium multiples reflected the "
            "scarcity of scaled independent platforms."),
        pe_activity=(
            "One of the most active recent physician-platform theses — the "
            "combination of a large aging patient base, rich in-office "
            "ancillaries, and the open HOPD-to-OBL arbitrage made cardiology the "
            "'next GI/ortho.' Diligence centers on OBL economics and Stark "
            "structure, imaging appropriate-use exposure, payer-contract "
            "durability, and value-based readiness."),
        notable_players=[
            "Cardiovascular Associates of America (Webster)",
            "US Heart & Vascular (Ares)", "US Cardiology Partners",
            "Novocardia (Deerfield)", "CardioOne",
            "Cardiovascular Institute of the South",
            "Hospital-employed cardiology groups",
            "Payer cardiometabolic programs",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Ancillary / technical revenue (% of total)", "30-50%",
                "Imaging (echo/nuclear/vascular) plus OBL procedures — the "
                "platform value beyond the E&M visit."),
            Kpi("OBL/ASC procedure volume & utilization", "cases per lab",
                "The fixed-cost procedural chassis; empty lab time is lost, "
                "non-recoverable margin."),
            Kpi("Imaging volume (echo/nuclear/vascular)", "studies / day",
                "High-value technical fees — rich, but appropriate-use-"
                "sensitive."),
            Kpi("Provider productivity (wRVUs / cardiologist)",
                "vs MGMA benchmark",
                "The throughput driver behind the professional fee."),
            Kpi("Payer mix (commercial vs Medicare)",
                "commercial lifts the blend",
                "Commercial pays a multiple of Medicare, so mix drives realized "
                "yield per RVU."),
            Kpi("Device cost (% of procedure net revenue)", "15-30%",
                "Stents/ICDs on fixed procedure rates — the implant squeeze in "
                "interventional and EP cases."),
            Kpi("Platform EBITDA margin", "high-teens to 20s (illustrative)",
                "Richer where OBL and imaging ancillaries are built out; thinner "
                "on a pure office-consult book."),
        ],
        margin_profile=(
            "Cardiology's margin story is ancillary capture. The professional "
            "fee — squeezed by a flat MPFS conversion factor — is the thin part; "
            "the value is in high-technical-fee diagnostics (echocardiography, "
            "nuclear cardiology, vascular ultrasound, stress testing) and, "
            "increasingly, in owning the site where procedures happen. Moving "
            "diagnostic cath, peripheral-vascular, and select EP cases into a "
            "physician-owned OBL or ASC lets the practice earn the technical/"
            "facility payment the hospital used to keep, and because non-facility "
            "practice-expense RVUs are higher, office-based procedures are "
            "materially more profitable to the practice. The offsets are device "
            "cost on fixed procedure rates (stents/ICDs can be a large share of "
            "a case) and the policy risk that site-neutral payment or Stark "
            "enforcement compresses exactly the OBL/ancillary premium the "
            "platform is built on."),
    ),
    risks=[
        Risk("Site-neutral / OBL reimbursement compression", "High",
             "The OBL-migration thesis depends on favorable technical/facility "
             "payment; rate equalization reprices it."),
        Risk("MPFS conversion-factor erosion + RVU revaluation", "High",
             "A structural squeeze on the professional fee, with cardiology-"
             "specific imaging and procedure cuts under budget neutrality."),
        Risk("Stark / self-referral & OBL-ownership exposure", "High",
             "Physician-owned labs and imaging depend on the in-office ancillary "
             "exception and safe-harbor compliance; a misstructured lab is an "
             "existential risk."),
        Risk("Appropriate-use / medical-necessity scrutiny (imaging, PCI)",
             "Medium",
             "Utilization enforcement can cut high-margin nuclear/echo imaging "
             "and elective stenting volume."),
        Risk("Device-cost inflation on fixed procedure rates", "Medium",
             "Implant-heavy cath/EP cases are squeezed when case rates do not "
             "cover stent/ICD cost."),
        Risk("Physician retention / comp-haircut + key-man concentration",
             "Medium",
             "Proceduralists are the EBITDA; post-close comp and retention are "
             "decisive to volume."),
        Risk("Multiple compression on a late, heavily-bid thesis", "Medium",
             "Premium entry multiples in a compressed window are exposed to a "
             "cooling market and higher rates."),
    ],
    diligence_questions=[
        "What share of EBITDA is OBL/ASC procedural and imaging ancillary, and "
        "how exposed is it to site-neutral and Stark repricing?",
        "How is OBL/ASC ownership structured against Stark and the AKS safe "
        "harbors, and is every physician-owner compliant?",
        "What is the imaging mix and appropriate-use posture (nuclear/echo/"
        "vascular), and what is the audit/medical-necessity history?",
        "What is the payer mix and commercial-rate position, and how durable "
        "are the top contracts?",
        "How concentrated is procedural volume in the top interventionalists and "
        "electrophysiologists, and what are their retention terms?",
        "What is the post-close physician compensation model, and how much "
        "projected EBITDA depends on the comp haircut?",
        "What is device cost as a % of procedure net revenue, and how are case "
        "rates structured to cover implants?",
        "What value-based cardiac contracts exist, and what is the risk profile "
        "and track record?",
    ],
    insider_lens=[
        "The deal is the OBL, not the office visit. Cardiology's PE thesis is "
        "capturing the technical/facility fee by moving cath, peripheral-"
        "vascular, and EP cases into physician-owned labs — the professional fee "
        "is the small part; the site-of-service margin is the prize.",
        "Imaging is a second, quieter ancillary engine. Echo, nuclear, and "
        "vascular studies are high-technical-fee services cardiologists order "
        "constantly — rich margin, but also the historical target of "
        "appropriate-use and overutilization enforcement, so the quality of that "
        "revenue matters.",
        "Cardiology was late because hospitals got there first. Hospitals "
        "employed cardiologists early for the downstream cath and surgery "
        "revenue, so the independent pool PE is buying is what is left — scarcer "
        "scaled platforms, which is why multiples ran high fast.",
        "Non-facility RVUs are the hidden subsidy. Medicare pays more when a "
        "procedure is done in the office (the practice bears the overhead) than "
        "in a facility — the entire OBL economic case rests on that practice-"
        "expense differential, which is exactly what site-neutral policy would "
        "erase.",
        "The device can eat the case. In implant-heavy interventional and EP "
        "work, the stent or ICD is a large share of net revenue on a fixed "
        "rate — a lucrative-looking OBL procedure can be thin if case rates and "
        "device pricing are not managed.",
    ],
    connections=default_connections(
        "cardiology",
        deals_sector="cardiology",
        extra_pages=[
            ("/industry/cardiology",
             "Industry deep-dive — cardiology deal history + structure"),
        ],
        connectors=[
            ("cms_open_data_mup_physician_by_provider_service",
             "Medicare physician utilization — cath/EP/imaging service volume"),
            ("cms_open_data_mup_outpatient_by_provider_service",
             "Medicare outpatient utilization — HOPD/OBL site-of-service read"),
            ("open_payments_general_payments_2024",
             "Open Payments — device-maker payments to cardiologists "
             "(relationship screen)"),
            ("open_payments_ownership_payments_2024",
             "Open Payments — physician ownership & investment (OBL/ASC "
             "safe-harbor screen)"),
            ("npi_provider_taxonomy",
             "NPI taxonomy — cardiology subspecialty supply & enrollment"),
        ],
    ),
    sources=[
        Source("American Heart Association — Heart Disease and Stroke "
               "Statistics Update (cost of CVD), Circulation", "ACADEMIC",
               "https://www.heart.org/en/about-us/heart-and-stroke-association-statistics"),
        Source("CMS — Medicare Physician Fee Schedule annual Final Rule (RVUs, "
               "conversion factor)", "GOV",
               "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
        Source("CMS — Hospital OPPS / ASC Payment System + ASC Covered "
               "Procedures List", "GOV",
               "https://www.cms.gov/medicare/payment/prospective-payment-systems/ambulatory-surgical-center-asc"),
        Source("Physician self-referral law (Stark, 42 CFR 411.350+)", "GOV",
               "https://www.cms.gov/medicare/regulations-guidance/physician-self-referral"),
        Source("MedPAC — Report to Congress, physician services and ambulatory "
               "payment chapters", "GOV", "https://www.medpac.gov/"),
        Source("American College of Cardiology — workforce and health-policy "
               "data", "INDUSTRY", "https://www.acc.org/"),
        Source("PE Desk industry deep-dive (cardiology) + realized-deal corpus",
               "INTERNAL", "/diligence/tam-sam?template=cardiology"),
    ],
    live_figures=live_figures_from_dive("cardiology"),
    trends=(
        "Cardiology followed dermatology, GI, and orthopedics into PE "
        "consolidation, but late and fast — Cardiovascular Associates of "
        "America, US Heart & Vascular, US Cardiology Partners, and Novocardia "
        "all formed within a few years around 2020-2022. Three shifts drove it. "
        "First, site of service: diagnostic catheterization, peripheral-vascular "
        "intervention, and increasingly electrophysiology moved out of the "
        "hospital into physician-owned office-based labs and ASCs, capturing the "
        "technical/facility fee the HOPD used to earn — aided by CMS adding "
        "cardiac codes to the ASC Covered Procedures List. Second, ancillary "
        "richness: cardiology's in-office imaging (echo, nuclear, vascular) "
        "throws off high-technical-fee revenue that scales with a platform. "
        "Third, value-based care: the sheer cost of cardiometabolic disease drew "
        "payers and CMS toward risk models that reward keeping cardiac patients "
        "out of the hospital, and several platforms formed explicitly to take "
        "that risk in partnership with systems and payers. The forward tension "
        "is policy — MPFS conversion-factor erosion on the professional fee, and "
        "the site-neutral/Stark debate on the OBL economics — against a durable "
        "aging-driven volume tailwind."),
    growth_levers=[
        GrowthLever(
            "Site-of-service migration (HOPD → OBL/ASC)",
            "Moving cath, PAD, and EP cases into physician-owned labs captures "
            "the technical/facility fee the hospital used to earn.",
            "primary", "ILLUSTRATIVE"),
        GrowthLever(
            "Aging / cardiometabolic prevalence",
            "An aging, increasingly diabetic/obese population expands the CVD "
            "patient base and its procedural volume.",
            "+ mid-single %/yr volume", "GOV"),
        GrowthLever(
            "ASC-CPL cardiac-code expansion",
            "CMS keeps adding cardiac codes Medicare will pay in an ASC, "
            "widening the ambulatory-payable case set.",
            "+ case set", "GOV"),
        GrowthLever(
            "In-office imaging & diagnostics ancillary",
            "Echo, nuclear, and vascular technical fees — rich, scalable "
            "ancillary margin beyond the professional fee.",
            "+ ancillary", "ILLUSTRATIVE"),
        GrowthLever(
            "Value-based cardiac contracts",
            "Risk and management fees on high-cost CHF/CAD populations — a "
            "second revenue engine layered on fee-for-service.",
            "+ VBC", "ILLUSTRATIVE"),
        GrowthLever(
            "MPFS conversion-factor / site-neutral drag",
            "A flat professional fee and any site-neutral repricing of the OBL "
            "premium are the structural headwinds.",
            "policy risk", "GOV"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Aging × cardiometabolic prevalence × site-of-service migration",
        analysis=(
            "The demand base is cardiovascular disease — the leading cause of US "
            "death and, with an aging and increasingly cardiometabolic "
            "(diabetes/obesity/hypertension) population, a structurally growing "
            "patient pool that generates diagnostic imaging, catheterization, "
            "rhythm, and vascular procedures. On top of the demographic base, "
            "the migration of those procedures from the hospital outpatient "
            "department into physician-owned OBLs and ASCs shifts where the "
            "volume — and the technical/facility margin — is captured, which is "
            "the actual PE value lever. CMS's ongoing additions of cardiac codes "
            "to the ASC Covered Procedures List keep widening the ambulatory-"
            "payable case set. The offsets are appropriate-use scrutiny (which "
            "can trim imaging and elective-PCI volume) and the competing pull of "
            "hospital employment."),
        basis="GOV"),
    cost_drivers=[
        CostDriver(
            "Physician & clinical labor (cardiologists, techs, imaging staff)",
            "~35-45% of cost",
            "Proceduralists and imaging technologists — the scarce, expensive "
            "core and the key-man concentration.", "ILLUSTRATIVE"),
        CostDriver(
            "Devices & procedural supplies (stents, ICDs, catheters)",
            "~15-30% of cost",
            "Implant-heavy interventional/EP cases; the device can approach a "
            "large share of case net revenue on a fixed rate.", "ILLUSTRATIVE"),
        CostDriver(
            "Imaging & lab equipment (cath lab, nuclear, echo capital)",
            "~10-15% of cost",
            "The capital-intensive OBL/imaging chassis plus maintenance and "
            "radiopharmaceuticals.", "ILLUSTRATIVE"),
        CostDriver(
            "Facility & OBL build-out / real estate", "~8-12% of cost",
            "The fixed lab chassis and de novo OBL capex that gate procedural "
            "capacity.", "ILLUSTRATIVE"),
        CostDriver(
            "G&A, billing, prior-auth & compliance (Stark/AUC)",
            "~8-12% of cost",
            "A heavy prior-authorization and appropriate-use/compliance "
            "overhead on imaging and elective procedures.", "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "No vendored cardiology facility file exists — a cardiology group is a "
        "practice, not a Medicare-certified facility — so state geography is "
        "omitted rather than fabricated. Qualitatively, the OBL opportunity "
        "varies with two policy variables: state Certificate-of-Need regimes "
        "(which gate new labs and ASCs and protect incumbents) and state "
        "licensure/OBL rules, plus the local balance of hospital-employed versus "
        "independent cardiologists. Regional independent anchors (for example "
        "Cardiovascular Institute of the South in Louisiana) and the platforms' "
        "build-outs concentrate in favorable states. The Medicare physician- and "
        "outpatient-utilization connectors linked below map cath, imaging, and "
        "vascular volume by geography — the honest footprint read for where the "
        "site-of-service migration has the most room to run."),
)

register(REPORT)
