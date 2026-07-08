"""Perfusion — cardiovascular perfusion & extracorporeal circulation services.

Deals-only pattern (copied from hospice.py): no vendored national facility
file, so geography is honestly omitted and the report leans on the qualitative
deep sections + ``live_figures_from_dive("perfusion")`` for any SOURCED corpus
figures. The defining reimbursement fact is that there is NO CMS fee schedule
for perfusion — it is a hospital-contract (Part A / facility) business paid by
the hospital, and the scarce asset is the certified clinical perfusionist, so
the sections are authored around hospital coverage economics, the CABG-decline /
ECMO-growth case-mix, and the surgical-support-services platform thesis.
"""
from __future__ import annotations

from .. import (
    Competition, CostDriver, GrowthLever, HowItWorks, Kpi, MarketReport,
    MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment, Source,
    TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="perfusion",
    name="Perfusion",
    care_setting="Other services",
    naics="621399",
    one_line_def=(
        "The clinical service of operating the heart-lung machine "
        "(cardiopulmonary bypass) and related extracorporeal circulation — "
        "ECMO, cell salvage/autotransfusion, ventricular assist, balloon pump — "
        "during cardiac and major surgery, provided by certified clinical "
        "perfusionists who are either hospital-employed or contracted through "
        "perfusion staffing/management groups."),
    tam_headline=TamHeadline(
        value=0.8, unit="$B", growth_pct=3.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "Modeled US perfusion-services market (~$0.5-1.0B; a small, "
            "clinician-labor-defined vertical sitting inside the larger "
            "surgical-support / intraoperative-services market). No published "
            "government total exists. Growth is the modeled composite of "
            "flat-to-declining core cardiac-surgery volume offset by ECMO/ECLS "
            "expansion and autotransfusion adjacencies."),
    ),
    executive_summary=[
        "There is no CMS fee schedule for perfusion. Perfusionists are not "
        "independently Medicare-billing providers, so this is a hospital-"
        "contract (Part A / facility) business — the group is paid by the "
        "hospital via per-case rates and 24/7 coverage stipends, and revenue "
        "quality is a contract question, not a payer-mix one.",
        "The scarce asset is the perfusionist, not the machine. Only ~4,000-"
        "5,000 certified clinical perfusionists practice in the US, from a "
        "supply bottleneck of roughly two dozen accredited training programs — "
        "so the roll-up thesis is aggregating and retaining scarce clinicians "
        "and selling coverage hospitals cannot staff themselves.",
        "The core market is flat-to-shrinking, and the growth is in the "
        "adjacencies. CABG volume has declined for two decades as PCI/stents, "
        "TAVR, and medical therapy substitute for open-heart surgery; the "
        "offsets are exploding ECMO/ECLS use, structural-heart/valve cases, and "
        "autotransfusion spreading into ortho/spine/trauma/OB.",
        "Coverage economics punish subscale programs. A cardiac program needs "
        "24/7/365 perfusion availability even at low volume, so the per-case "
        "cost of self-staffing is prohibitive — the structural reason hospitals "
        "outsource and the moat for the contract groups.",
        "The real platform is surgical support, not pure perfusion. The value "
        "compounds when perfusion is cross-sold with intraoperative "
        "neuromonitoring, autotransfusion, surgical assist, and sterile "
        "processing into the same OR relationship — the SpecialtyCare template.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Cardiac / major surgical case scheduled requiring extracorporeal "
            "circulation",
            "Perfusionist coverage assured (employed or contracted; 24/7 call "
            "for emergencies and ECMO)",
            "Pre-bypass setup — heart-lung machine, oxygenator, cannulae, "
            "circuit prime, blood management plan",
            "Intraoperative management of cardiopulmonary bypass (flow, "
            "anticoagulation, temperature, gases)",
            "Adjacent services as needed — cell salvage/autotransfusion, "
            "ECMO/ECLS, ventricular assist, balloon pump",
            "Post-case documentation, quality/QA, and device/disposables "
            "resupply",
            "Hospital billed per-case / per-coverage under the service "
            "contract",
        ],
        sites_of_care=[
            "Hospital cardiac operating rooms (open-heart / CABG / valve)",
            "Structural-heart / hybrid cath-OR suites (TAVR-era procedures)",
            "ICU / ECMO & extracorporeal life-support (rapidly growing)",
            "Orthopedic, spine, trauma, and OB ORs (autotransfusion / cell "
            "salvage)",
        ],
        money_flow=(
            "Perfusion is paid by the hospital, not by a payer fee schedule. "
            "Perfusionists are generally not recognized as independent Medicare "
            "Part B billing providers, so the core cardiac service is captured "
            "in the hospital's facility economics (Part A / DRG) rather than "
            "billed professionally. A contracted perfusion group therefore "
            "earns revenue through a service contract with the hospital — "
            "typically a per-case rate plus a 24/7 coverage/availability stipend "
            "that pays for call readiness even when the OR is idle, or a full-"
            "service management fee. ECMO is billed by the hospital under high-"
            "cost DRGs with the perfusionist's time as a hospital cost. Cell "
            "salvage/autotransfusion is sometimes billed as an ancillary in "
            "specific settings. The group's economics are thus clinician labor "
            "arbitrage plus a coverage premium plus case volume — not a payer-"
            "mix story."),
        key_players=(
            "Fragmented, with a scaled leader. Most perfusionists are hospital-"
            "employed or work for regional contract groups; the largest "
            "national player is SpecialtyCare, which pairs perfusion with "
            "intraoperative neuromonitoring, surgical assist, and sterile "
            "processing as a surgical-support platform. Regional perfusion "
            "groups (e.g. Keystone/Epic-style operators) hold local hospital "
            "contracts. Upstream sits a device oligopoly — LivaNova (Sorin), "
            "Terumo Cardiovascular, Getinge/Maquet, and Medtronic supply the "
            "heart-lung machines, oxygenators, and cannulae."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Cardiac cardiopulmonary bypass (CABG + valve)",
                    "the core — flat-to-declining volume",
                    "ILLUSTRATIVE · modeled case-mix; CABG in secular decline"),
            Segment("ECMO / extracorporeal life support",
                    "fastest-growing utilization",
                    "ILLUSTRATIVE · modeled case-mix"),
            Segment("Autotransfusion / cell salvage",
                    "adjacency into ortho/spine/trauma/OB",
                    "ILLUSTRATIVE · modeled adjacency"),
            Segment("Certified clinical perfusionists (US)",
                    "~4,000-5,000 practitioners — the supply constraint",
                    "INDUSTRY · ABCP / AmSECT workforce estimates"),
            Segment("Ventricular assist / balloon pump support",
                    "specialized, lower-volume",
                    "ILLUSTRATIVE · modeled adjacency"),
        ],
        growth_drivers=[
            "CABG volume secular decline −2-3%/yr — PCI/TAVR/medical-therapy "
            "substitution (a HEADWIND)",
            "ECMO/ECLS utilization growth — the primary volume offset",
            "Structural-heart / valve case growth",
            "Autotransfusion spread into ortho/spine/trauma/OB",
            "Perfusionist labor scarcity — supports coverage pricing and the "
            "outsourcing thesis",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Hospital service contract (per-case + coverage stipend)": 0.90,
            "Ancillary / professional billing (cell salvage, select)": 0.06,
            "ECMO transport / adjacencies / other": 0.04,
        },
        rate_mechanics=[
            "No Medicare fee schedule for perfusion — the defining "
            "reimbursement fact; the profession has no independent Part B "
            "billing pathway, so payment runs through the hospital.",
            "Per-case rate — the hospital pays the contract group per bypass / "
            "ECMO / autotransfusion case performed.",
            "Coverage / availability stipend — a premium paid for guaranteed "
            "24/7/365 call readiness regardless of case volume; the economics "
            "that make subscale programs outsource.",
            "Full-service management fee — a fixed fee for the group to run the "
            "hospital's entire perfusion function including staffing and "
            "equipment coordination.",
            "ECMO — billed by the hospital under high-cost DRGs; the "
            "perfusionist's time is a hospital cost embedded in that facility "
            "payment.",
        ],
        reimbursement_risk=(
            "The revenue risk is contractual, not payer-driven. Because there "
            "is no fee schedule, the group's economics depend on the pricing "
            "and durability of hospital service contracts and on case volume at "
            "the covered programs — a hospital that closes or consolidates a "
            "low-volume cardiac program, or in-sources perfusion, is a direct "
            "revenue hit. The demand backdrop is mixed: the core cardiac-bypass "
            "market is in secular decline as PCI, TAVR, and medical therapy "
            "substitute for open-heart surgery, which the group must offset with "
            "ECMO, structural-heart, and autotransfusion growth. The protective "
            "factor is the coverage economics — 24/7 availability is prohibitively "
            "expensive to self-staff at low volume — and the scarcity of "
            "perfusionists, which supports coverage pricing and contract "
            "renewals."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("ABCP certification (Certified Clinical Perfusionist, CCP)",
                 "The board certification that defines a qualified "
                 "perfusionist; hospital credentialing and contracts require "
                 "it, and it gates the labor supply.",
                 "https://www.abcp.org/"),
            Rule("CAAHEP-accredited perfusion education programs",
                 "Only ~two dozen accredited programs train perfusionists — the "
                 "structural supply bottleneck behind the workforce scarcity and "
                 "the roll-up thesis.",
                 "https://www.caahep.org/"),
            Rule("State perfusionist licensure (a partial patchwork)",
                 "A growing but incomplete set of states license perfusionists; "
                 "licensure raises the credential barrier and affects staffing "
                 "and mobility across markets.",
                 None),
            Rule("AmSECT standards & clinical guidelines",
                 "The professional society's standards of practice for "
                 "cardiopulmonary bypass and ECMO define the quality baseline "
                 "hospitals contract against.",
                 "https://www.amsect.org/"),
            Rule("Hospital credentialing / privileging + Joint Commission",
                 "Perfusionists are credentialed and privileged like other "
                 "clinicians; the hospital's accreditation obligations flow "
                 "into the service contract.",
                 "https://www.jointcommission.org/"),
        ],
        policy_watch=[
            "Spread of state perfusionist licensure and any scope-of-practice "
            "changes",
            "ECMO/ECLS coverage and DRG treatment as utilization scales",
            "Cardiac-surgery-volume trajectory as TAVR/structural-heart "
            "indications expand",
            "Any move toward recognizing perfusionists as billing providers "
            "(unlikely, but a structural swing factor)",
            "Accredited-program capacity — the workforce-supply bottleneck",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Highly fragmented. Most perfusionists are hospital-employed or "
            "with small regional contract groups; a single scaled national "
            "surgical-support platform (SpecialtyCare) sits above a long tail "
            "of local operators. No vendored facility file exists for this "
            "clinician-services vertical, so a computed HHI is honestly "
            "omitted."),
        hhi_or_share=(
            "Qualitatively, SpecialtyCare is the clear national leader across "
            "perfusion and adjacent intraoperative services, but the majority "
            "of perfusion is still delivered by hospital-employed staff and "
            "regional groups — the market is defined by hospital-vs-outsource, "
            "not vendor-vs-vendor concentration."),
        consolidation=(
            "The consolidation logic is clinician aggregation. Because the "
            "binding constraint is the scarce perfusionist and the ability to "
            "guarantee 24/7 coverage, roll-ups assemble clinicians and hospital "
            "contracts and cross-sell adjacent surgical services. SpecialtyCare "
            "is the archetype, built across multiple PE ownerships into a multi-"
            "service intraoperative platform."),
        pe_activity=(
            "Active within the broader surgical-support-services thesis rather "
            "than pure perfusion. The attractive attributes are the scarce, "
            "hard-to-replicate clinician workforce, the coverage-economics moat, "
            "and the cross-sell into neuromonitoring, autotransfusion, and "
            "surgical assist. Quality-of-earnings centers on hospital-contract "
            "durability and pricing, the case-mix trajectory (CABG decline vs "
            "ECMO/adjacency growth), and clinician retention in a scarce labor "
            "market."),
        notable_players=[
            "SpecialtyCare", "Keystone Perfusion Services",
            "Epic Cardiovascular Services", "Comprehensive Care Services",
            "regional hospital-contract perfusion groups",
            "LivaNova (device)", "Terumo Cardiovascular (device)",
            "Getinge / Maquet (device)",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Cases per perfusionist FTE", "volume/coverage-driven",
                "The productivity metric; low-volume programs carry idle "
                "coverage cost that crushes per-case economics."),
            Kpi("Coverage / call cost", "high fixed burden",
                "24/7/365 availability must be staffed regardless of volume — "
                "the structural reason subscale programs outsource."),
            Kpi("Revenue per case", "contract-set",
                "Per-case rate under the hospital service contract, plus the "
                "coverage stipend spread across cases."),
            Kpi("Clinician utilization & retention", "scarcity-constrained",
                "With only ~4-5K CCPs nationally, retention is the binding "
                "operational constraint."),
            Kpi("Case mix (CABG vs ECMO vs adjacency)", "shifting",
                "Core bypass is declining; ECMO and autotransfusion are the "
                "growth — the mix predicts the trajectory."),
            Kpi("Contract retention", "high when coverage holds",
                "Sticky while the group reliably staffs 24/7 coverage; a missed "
                "case is a program-risk event."),
            Kpi("EBITDA margin", "low-to-mid teens (pure); higher on platform",
                "Labor-dominated for pure perfusion; a diversified surgical-"
                "support platform earns more."),
        ],
        margin_profile=(
            "Perfusion margin is a clinician-labor-and-coverage story. Certified "
            "perfusionists are highly paid and scarce, so labor is the dominant "
            "cost and clinician utilization against a fixed 24/7 coverage "
            "obligation is the whole game — a busy program spreads coverage cost "
            "across many cases, a subscale program bleeds on idle availability. "
            "Pure-perfusion staffing therefore runs at low-to-mid-teens EBITDA, "
            "labor-constrained. The margin expands materially when perfusion is "
            "delivered inside a surgical-support platform that cross-sells "
            "neuromonitoring, autotransfusion, and surgical assist into the same "
            "OR relationship, spreading management and coverage overhead across "
            "more service lines and raising the switching cost for the hospital."),
    ),
    risks=[
        Risk("Cardiac-surgery (CABG) secular decline", "High",
             "PCI, TAVR, and medical therapy substitute for open-heart surgery, "
             "shrinking the core bypass-case base over the hold."),
        Risk("Perfusionist workforce scarcity & wage inflation", "High",
             "Only ~4-5K CCPs and a tiny training pipeline; retention and wage "
             "pressure are the binding operational constraint."),
        Risk("Hospital-contract concentration & in-sourcing", "High",
             "Revenue is a book of hospital service contracts; loss, re-bid, or "
             "in-sourcing of an anchor program is a step-change."),
        Risk("Subscale coverage economics", "Medium",
             "Low-volume programs carry idle 24/7 coverage cost; a mix skewed "
             "to small programs is structurally low-margin."),
        Risk("Clinical adverse event / liability", "Medium",
             "Cardiopulmonary bypass and ECMO are high-acuity; an adverse event "
             "carries clinical, reputational, and contract risk."),
        Risk("Reliance on adjacency growth to offset core decline", "Medium",
             "The thesis depends on ECMO and autotransfusion growth actually "
             "offsetting bypass decline — an execution and case-mix risk."),
    ],
    diligence_questions=[
        "What is the hospital-contract book — number, size, pricing "
        "(per-case vs stipend vs management fee), terms, and renewal history?",
        "What is the case mix and its trajectory — CABG vs valve/structural "
        "heart vs ECMO vs autotransfusion?",
        "What is the perfusionist headcount, tenure, retention, and wage "
        "trend, and how exposed is the book to a few key clinicians?",
        "What is the coverage-economics profile — how many covered programs are "
        "subscale and carry idle 24/7 cost?",
        "How much revenue comes from surgical-support adjacencies (IONM, "
        "autotransfusion, surgical assist) vs pure perfusion?",
        "What is the ECMO/ECLS growth in the book, and does it offset the "
        "core-bypass decline?",
        "What is the clinical-quality and adverse-event history across covered "
        "programs?",
        "What is the state-licensure exposure and its effect on clinician "
        "mobility and cost?",
    ],
    insider_lens=[
        "There is no fee schedule — the hospital is the payer. Perfusion "
        "revenue is a book of hospital service contracts, so revenue quality is "
        "a contract-durability and pricing question, not a payer-mix analysis. "
        "Read the contracts, the coverage stipends, and the re-bid history "
        "before the P&L.",
        "The asset is the clinician, and there aren't many. Roughly 4-5K "
        "certified perfusionists nationally, an aging workforce, and only about "
        "two dozen accredited training programs — the entire roll-up thesis is "
        "aggregating and retaining scarce clinicians and selling 24/7 coverage "
        "hospitals cannot staff. Retention risk is the equity risk.",
        "The core market is quietly shrinking. CABG volume has fallen for two "
        "decades as stents, TAVR, and medical therapy displace open-heart "
        "surgery — so a flat headcount can mask a declining case base. The "
        "growth is ECMO/ECLS, structural heart, and autotransfusion; underwrite "
        "the case-mix trajectory, not the clinician count.",
        "Coverage economics are the moat and the trap. A cardiac program needs "
        "24/7/365 availability even at low volume, which is prohibitively "
        "expensive to self-staff — that is why hospitals outsource. But a book "
        "loaded with subscale programs carries idle coverage cost that crushes "
        "margin; the quality of the coverage book matters more than the case "
        "total.",
        "Pure perfusion is worth less than the same clinicians in a platform. "
        "The value compounds when perfusion is bundled with neuromonitoring, "
        "autotransfusion, surgical assist, and sterile processing into one OR "
        "relationship — SpecialtyCare is the template. A standalone perfusion "
        "group is a component, not the platform.",
    ],
    connections=default_connections(
        "perfusion",
        deals_sector="perfusion",
        connectors=[
            ("provider_data_hospital_general",
             "CMS Provider Data — Hospital General Information (cardiac-program "
             "customer base)"),
            ("cms_open_data_mup_inpatient_by_provider",
             "CMS Medicare inpatient by provider — cardiac-surgery & ECMO DRG "
             "volume (the demand signal)"),
            ("npi_provider_taxonomy",
             "NPI taxonomy — perfusionist / cardiac-surgery clinician supply "
             "mapping"),
            ("oig_leie_exclusions",
             "OIG LEIE — excluded individuals/entities (integrity screen)"),
        ],
    ),
    sources=[
        Source("American Board of Cardiovascular Perfusion (ABCP) — CCP "
               "certification and workforce", "INDUSTRY",
               "https://www.abcp.org/"),
        Source("American Society of ExtraCorporeal Technology (AmSECT) — "
               "standards and clinical guidelines", "INDUSTRY",
               "https://www.amsect.org/"),
        Source("Extracorporeal Life Support Organization (ELSO) — ECMO registry "
               "and utilization trends", "ACADEMIC",
               "https://www.elso.org/"),
        Source("CAAHEP — accredited cardiovascular-perfusion education programs "
               "(the supply bottleneck)", "INDUSTRY",
               "https://www.caahep.org/"),
        Source("Society of Thoracic Surgeons (STS) — cardiac-surgery volume and "
               "outcomes database", "ACADEMIC",
               "https://www.sts.org/"),
        Source("PE Desk industry deep-dive + realized-deal corpus (perfusion / "
               "surgical-support services)", "INTERNAL",
               "/diligence/tam-sam?template=perfusion"),
    ],
    live_figures=live_figures_from_dive("perfusion"),
    trends=(
        "Perfusion is a small, scarce-labor clinical vertical caught between a "
        "declining core and growing adjacencies. For two decades the "
        "foundational market — cardiopulmonary bypass for CABG — has shrunk as "
        "percutaneous coronary intervention, transcatheter aortic valve "
        "replacement, and better medical therapy substituted for open-heart "
        "surgery. Over the same period two things bent the other way: ECMO and "
        "extracorporeal life support went from rare to routine (accelerated "
        "sharply during COVID and in cardiogenic-shock care), and "
        "autotransfusion/cell salvage spread from cardiac ORs into orthopedics, "
        "spine, trauma, and obstetrics. Because perfusionists are scarce — only "
        "a few thousand nationally, trained by a handful of accredited programs "
        "— and because every cardiac program needs 24/7 coverage it cannot "
        "economically self-staff at low volume, the consolidation logic is "
        "clinician aggregation: assemble the scarce clinicians, guarantee "
        "coverage, and cross-sell adjacent intraoperative services. "
        "SpecialtyCare built the archetype surgical-support platform on exactly "
        "that logic. The trajectory rewards diversified case-mix and platform "
        "breadth over pure cardiac-bypass exposure."),
    growth_levers=[
        GrowthLever(
            "ECMO / extracorporeal life support growth",
            "ECMO utilization has expanded rapidly in cardiogenic shock, "
            "respiratory failure, and ECLS programs — the primary offset to "
            "declining bypass volume.",
            "primary growth offset", "ILLUSTRATIVE"),
        GrowthLever(
            "Autotransfusion / cell salvage spread",
            "Cell-salvage adoption in ortho, spine, trauma, and OB extends "
            "perfusion-adjacent volume beyond the cardiac OR.",
            "+ adjacency volume", "ILLUSTRATIVE"),
        GrowthLever(
            "Surgical-support platform cross-sell",
            "Bundling perfusion with neuromonitoring, surgical assist, and "
            "sterile processing raises revenue per OR relationship and switching "
            "cost.",
            "revenue/relationship uplift", "ILLUSTRATIVE"),
        GrowthLever(
            "Coverage pricing on clinician scarcity",
            "With perfusionists scarce, contract groups hold pricing on the "
            "24/7 coverage hospitals cannot self-staff.",
            "supports contract pricing", "ILLUSTRATIVE"),
        GrowthLever(
            "CABG / open-heart secular decline",
            "PCI, TAVR, and medical-therapy substitution shrink the core "
            "cardiopulmonary-bypass case base — the structural headwind on the "
            "growth algorithm.",
            "−2-3%/yr core volume", "ILLUSTRATIVE"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Cardiac-surgery + ECMO/ECLS case volume against a fixed "
               "coverage obligation",
        analysis=(
            "Demand is the count of cases requiring extracorporeal circulation "
            "at covered programs — but the economics are dominated by the fact "
            "that coverage is a fixed 24/7/365 obligation regardless of that "
            "count. The core driver, cardiopulmonary bypass for CABG and valve "
            "surgery, is in secular decline as PCI, TAVR, and medical therapy "
            "substitute for open-heart procedures, so raw cardiac volume is a "
            "headwind. The offsetting drivers are ECMO/ECLS — whose utilization "
            "has grown rapidly and now anchors the growth case — and "
            "autotransfusion/cell salvage spreading into non-cardiac ORs. "
            "Because a low-volume cardiac program still requires full coverage, "
            "the vendor economics hinge less on total national case volume than "
            "on the concentration and case-mix of the specific programs under "
            "contract: a book of busy, ECMO-active, multi-service programs "
            "compounds, while a book of subscale bypass-only programs erodes."),
        basis="ILLUSTRATIVE"),
    cost_drivers=[
        CostDriver(
            "Perfusionist clinical labor",
            "~55-70% of cost",
            "Scarce, highly-paid certified perfusionists plus call pay — the "
            "dominant cost and the binding constraint on the whole model.",
            "ILLUSTRATIVE"),
        CostDriver(
            "24/7 coverage / call burden",
            "high fixed",
            "Guaranteed availability for emergent and ECMO cases must be staffed "
            "regardless of volume — the cost that makes subscale programs "
            "uneconomic to self-staff.", "ILLUSTRATIVE"),
        CostDriver(
            "Disposables & device circuits",
            "~10-15% of cost",
            "Oxygenators, cannulae, tubing packs, and circuit primes — largely "
            "pass-through but working-capital-intensive.", "ILLUSTRATIVE"),
        CostDriver(
            "Management, scheduling & QA overhead",
            "~10% of cost",
            "Coordinating clinician schedules across programs, credentialing, "
            "and clinical quality — the overhead a platform spreads across "
            "service lines.", "ILLUSTRATIVE"),
        CostDriver(
            "Training & recruiting (workforce scarcity)",
            "elevated, structural",
            "Recruiting from a tiny accredited-program pipeline and retaining "
            "scarce clinicians is a persistent, structural cost.",
            "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "Perfusion follows cardiac surgical programs, not a national vendor "
        "roster, so geography concentrates where open-heart and ECMO programs "
        "are — larger metros and academic/tertiary centers — mappable via the "
        "hospital and inpatient-DRG connectors below. The state perfusionist-"
        "licensure patchwork also shapes clinician mobility and cost by market. "
        "No national perfusion-group facility file is vendored, so a computed "
        "facility breakdown is honestly omitted."),
)

register(REPORT)
