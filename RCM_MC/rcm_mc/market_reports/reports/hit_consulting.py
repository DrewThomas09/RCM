"""HIT Consulting — health-IT advisory, implementation & managed services.

Deals-only market-report module (a professional-services vertical with no CMS
facility file, so no computed state_breakdown or supply trend). Live SOURCED
figures wire from ``hit_consulting_deep_dive()`` — the sector's own realized-
deal corpus (health-IT / consulting trade history). The qualitative sections
are authored around the two facts that define the economics: it is a classic
consulting business (utilization × bill rate × realization × leverage), and the
scarce, moat-defining resource is EHR-certified talent — Epic controls
certification, so a firm's certified-consultant roster is both its asset and its
throughput ceiling. The durable annuity is application managed services (AMS),
not the lumpy, finite go-live project.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver, default_connections,
    live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="hit_consulting",
    name="HIT Consulting",
    care_setting="Other services",
    naics="541512",
    one_line_def=(
        "Health-IT consulting and services — advisory, EHR/ERP implementation "
        "and activation, optimization, application managed services (AMS), "
        "interoperability, cybersecurity, analytics, and staff augmentation "
        "for health systems, payers, and life-sciences clients. A "
        "professional-services business priced on time-and-materials, "
        "fixed-fee, or recurring managed-services fees, whose economics are "
        "utilization × bill rate × realization × leverage."),
    tam_headline=TamHeadline(
        value=40.0, unit="$B", growth_pct=9.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "Modeled US health-IT consulting, implementation, and managed-"
            "services spend. There is no clean government figure for a services "
            "market; analysts (e.g. Everest/KLAS/Definitive) size the US "
            "advisory + implementation + AMS spend in the ~$30-50B range "
            "growing high-single to low-double digits. Growth is the modeled "
            "composite of EHR cycles + regulatory (interoperability, prior-auth, "
            "cyber) + the managed-services outsourcing shift."),
    ),
    executive_summary=[
        "It is a consulting business, so the P&L is utilization × bill rate × "
        "realization × leverage. A bench of idle consultants kills margin; the "
        "asset is billable people at a spread, and the multiple compresses if "
        "it is just bodies and phones rather than IP, AMS, and offshore "
        "leverage.",
        "EHR certification is the moat and the bottleneck. Epic controls who "
        "gets certified, and certified consultants are scarce — a firm's "
        "certified-badge roster is a real, hard-to-replicate asset and its "
        "throughput ceiling at once.",
        "The durable value is the annuity, not the project. EHR go-lives are "
        "lumpy and finite; the recurring prize is application managed services "
        "(AMS) — offshore/nearshore support of the EHR/ERP after go-live. "
        "Diligence the recurring-vs-project mix and the AMS attach rate.",
        "Demand is regulation- and cycle-driven: EHR replacement/consolidation "
        "(Cerner→Epic migrations, Oracle Health uncertainty), the CMS "
        "interoperability & prior-authorization rule, TEFCA, and — since the "
        "Change Healthcare attack — a board-level cybersecurity tailwind.",
        "PE has rolled the sector up (Guidehouse under Bain then Veritas, "
        "Tegria, Nordic, CereCore) around a fragmented pool of EHR-implementation "
        "and AMS boutiques — but the returns depend on converting project "
        "revenue to recurring AMS and industrializing offshore delivery.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Advisory & strategy — IT roadmap, EHR selection, M&A integration, "
            "digital and analytics strategy",
            "Implementation & activation — EHR/ERP build, configuration, "
            "testing, training, command-center go-live support",
            "Optimization — post-live workflow, revenue-cycle and clinical "
            "content tuning, upgrade and enhancement work",
            "Application managed services (AMS) — ongoing offshore/nearshore "
            "support, ticketing, and enhancement — the recurring annuity",
            "Specialty services — interoperability/FHIR, cybersecurity, data & "
            "analytics, AI enablement, ERP (Workday/Oracle)",
            "Staff augmentation & talent — placing certified consultants and "
            "backfill (analysts, PMs) on client teams",
        ],
        sites_of_care=[
            "Health-system IT & informatics (the core buyer)",
            "Payer / health-plan technology & operations",
            "Life sciences & digital-health platforms",
            "Government & public-health agencies (VA, state Medicaid, CDC)",
            "Remote / offshore delivery centers (AMS + build factories)",
        ],
        money_flow=(
            "The firm is paid by the client on one of a few structures. "
            "Time-and-materials bills a consultant day-rate (blended bill rates "
            "commonly run ~$150-350/hr by seniority and skill), with margin "
            "made on the bill-rate-to-cost spread and on utilization. Fixed-fee "
            "or milestone project pricing shifts delivery risk to the firm and "
            "rewards efficient, certified teams. Application managed services "
            "are priced recurring — monthly retainer, per-application, or PEPM — "
            "and are the sticky annuity that smooths the lumpiness of project "
            "work. Staff augmentation is a bill-rate/pay-rate spread like "
            "clinical staffing. Underneath every model the economics are the "
            "consulting pyramid: utilization (billable %), realization (rate "
            "actually collected vs. standard), and leverage (junior-to-senior "
            "mix) determine gross margin."),
        key_players=(
            "EHR implementation & AMS specialists: Nordic Global, Tegria "
            "(Providence-founded), CereCore (HCA), Impact Advisors, Pivot Point "
            "Consulting, Divurgent, Galen, HCTec. Advisory/strategy: Chartis, "
            "Huron Healthcare, Guidehouse (Veritas), plus the big-consulting and "
            "payer-services arms of Deloitte, Accenture, and Optum Advisory. "
            "Talent/staff-aug: Medasource (Health Carousel), HCTec. The "
            "acquirable pool is the fragmented long tail of Epic/Oracle-Health "
            "implementation boutiques and regional AMS shops."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("US health-IT consulting + implementation + AMS spend",
                    "~$30-50B (modeled)",
                    "ILLUSTRATIVE · services-market analyst sizing"),
            Segment("EHR implementation & activation (project, lumpy)",
                    "cycle-driven; peaks on migrations",
                    "INDUSTRY · KLAS/analyst implementation-market reads"),
            Segment("Application managed services (AMS, recurring)",
                    "the growing annuity slice",
                    "INDUSTRY · managed-services outsourcing sizing"),
            Segment("Cybersecurity & interoperability advisory",
                    "board-level demand post-Change Healthcare",
                    "INDUSTRY · health-IT security spend estimates"),
        ],
        growth_drivers=[
            "EHR replacement/consolidation cycles (Cerner→Epic, Oracle Health "
            "migration uncertainty, M&A integration)",
            "Regulatory compliance — CMS interoperability & prior-auth rule, "
            "TEFCA, ONC info-blocking, USCDI/FHIR",
            "Managed-services shift — systems outsourcing EHR support (AMS) to "
            "cut cost, a recurring-revenue tailwind",
            "Cybersecurity & resilience — a board-level line item after the "
            "Change Healthcare attack",
            "AI/analytics enablement — governance, data platforms, and "
            "ambient/clinical AI deployment",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Hospitals & health systems": 0.55,
            "Payers / health plans": 0.20,
            "Life sciences & digital health": 0.15,
            "Government & public health": 0.10,
        },
        rate_mechanics=[
            "Time-and-materials — a consultant day/hour bill rate (blended "
            "~$150-350/hr); margin is the bill-rate-to-cost spread × "
            "utilization. (Shares above are ILLUSTRATIVE revenue-by-client-"
            "segment — who funds the firm — not an insurance payer mix; the "
            "firm bills no payer.)",
            "Fixed-fee / milestone — the firm carries delivery risk; efficient, "
            "certified teams earn the upside.",
            "Managed services — recurring monthly retainer, per-application, or "
            "PEPM; the sticky annuity that smooths project lumpiness.",
            "Staff augmentation — bill-rate/pay-rate spread on placed certified "
            "consultants and backfill.",
            "The consulting pyramid governs it all: utilization (billable %), "
            "realization (collected vs. standard rate), and leverage "
            "(junior:senior mix) set gross margin.",
            "Epic/Oracle-Health certification gates who can bill on a build — "
            "certified scarcity supports rate and is the throughput constraint.",
        ],
        reimbursement_risk=(
            "The revenue risk is a consulting-cycle risk, not a payer-rate risk. "
            "First, project lumpiness and bench: EHR go-lives are finite events, "
            "so a firm heavy in project work faces feast-or-famine utilization "
            "and a costly bench between cycles — the AMS attach rate is the "
            "hedge. Second, certification scarcity cuts both ways: Epic controls "
            "certification, so a firm cannot instantly scale a hot skill, and "
            "attrition of certified consultants is a direct revenue loss. Third, "
            "platform-cycle risk: the Oracle-Cerner migration path could either "
            "unlock a migration super-cycle (to Epic or Oracle Health) or freeze "
            "client spend, and a demand pause hits utilization immediately. "
            "Cybersecurity demand is a tailwind but a crowded, commoditizing one."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("ONC/ASTP Cures Act — info blocking, CEHRT, USCDI/FHIR",
                 "The interoperability and certified-EHR regime is the primary "
                 "demand engine for interoperability and data consulting; "
                 "info-blocking carries OIG penalties.",
                 "https://www.healthit.gov/topic/information-blocking"),
            Rule("CMS Interoperability & Prior Authorization Final Rule "
                 "(CMS-0057-F)",
                 "FHIR API and prior-auth automation mandates on payers "
                 "(2026-27 compliance) — a large, dated wave of implementation "
                 "consulting demand.",
                 "https://www.cms.gov/newsroom/fact-sheets/cms-interoperability-and-prior-authorization-final-rule-cms-0057-f"),
            Rule("TEFCA — Trusted Exchange Framework & Common Agreement",
                 "QHIN participation and nationwide exchange onboarding create "
                 "interoperability advisory and integration work.",
                 "https://www.healthit.gov/topic/interoperability/policy/trusted-exchange-framework-and-common-agreement-tefca"),
            Rule("HIPAA Security Rule (proposed 2025 strengthening)",
                 "A tighter security-rule update — accelerated after the Change "
                 "Healthcare attack — drives cybersecurity and resilience "
                 "engagements.",
                 "https://www.hhs.gov/hipaa/for-professionals/security/index.html"),
            Rule("ONC HTI-1 / HTI-2 — decision-support & algorithm transparency",
                 "Rules on certified decision-support and predictive/AI "
                 "transparency create AI-governance and enablement demand.",
                 "https://www.healthit.gov/topic/laws-regulation-and-policy/health-data-technology-and-interoperability-hti-1-final-rule"),
        ],
        policy_watch=[
            "CMS interoperability & prior-auth rule implementation timelines",
            "Oracle Health (Cerner) platform roadmap and migration decisions",
            "HIPAA Security Rule finalization and cybersecurity mandates",
            "TEFCA/QHIN expansion and info-blocking enforcement",
            "AI governance / decision-support transparency (HTI rules)",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Barbell: a few scaled advisory and big-consulting firms plus a "
            "handful of large EHR-implementation platforms at the top, and a "
            "long tail of Epic/Oracle-Health implementation boutiques, AMS "
            "shops, and specialty (analytics, cyber, interoperability) firms "
            "below. No facility file exists for a services vertical, so "
            "geography is honestly omitted; the corpus deal history stands in "
            "its place below."),
        hhi_or_share=(
            "Fragmented and skill-defined — 'share' is really a share of "
            "certified consultants and installed AMS relationships, not a "
            "market count. The big-four and Optum sit above; the specialist "
            "boutique tail is the roll-up pool."),
        consolidation=(
            "Active PE roll-up. Guidehouse (Bain Capital, then Veritas) built a "
            "scaled health/public-sector advisory platform; Tegria assembled "
            "implementation and AMS assets; Nordic, CereCore (HCA), Impact "
            "Advisors, and Pivot Point anchor the implementation tier. The "
            "thesis is buying certified-talent capacity and converting project "
            "revenue to recurring AMS, with the Oracle-Cerner migration "
            "uncertainty and the post-Change-Healthcare cyber wave as demand "
            "catalysts."),
        pe_activity=(
            "Sponsors like the asset-light, high-return-on-capital consulting "
            "model plus a recurring-AMS annuity and a fragmented roll-up "
            "runway. The value-creation levers are: raise utilization and "
            "realization, shift mix from project to recurring AMS, industrialize "
            "offshore/nearshore delivery, and cross-sell cyber/interoperability/"
            "AI. The risk is a demand pause (an EHR-spend freeze or a bench "
            "between go-live cycles) hitting utilization fast."),
        notable_players=[
            "Nordic Global", "Tegria", "CereCore (HCA)", "Impact Advisors",
            "Pivot Point Consulting", "Chartis", "Huron Healthcare",
            "Guidehouse (Veritas)", "Optum Advisory", "Deloitte / Accenture",
            "Medasource / HCTec (talent)",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Consultant utilization (billable %)", "~70-85%",
                "The core efficiency lever — idle bench between go-lives is the "
                "margin killer."),
            Kpi("Bill rate / realization", "$150-350/hr; ~85-95% realized",
                "Rate by seniority/skill and the share actually collected versus "
                "standard — certification scarcity supports both."),
            Kpi("Leverage ratio (junior:senior)", "engagement-dependent",
                "The pyramid — more leverage lifts margin but requires "
                "certified junior capacity to deliver."),
            Kpi("Recurring (AMS) vs. project mix", "the durability metric",
                "Recurring AMS smooths the lumpy project book and lifts the "
                "multiple — the number sponsors underwrite."),
            Kpi("Book-to-bill / backlog", ">1.0x healthy",
                "Leading indicator of pipeline versus burn — a stalling "
                "book-to-bill signals a demand pause."),
            Kpi("Firm EBITDA margin", "~15-30%",
                "Advisory and offshore-leveraged AMS sit higher; on-shore "
                "project-heavy mixes lower (ILLUSTRATIVE ranges)."),
        ],
        margin_profile=(
            "Health-IT consulting margin is the classic consulting equation: "
            "utilization × realization × leverage, over a cost base that is "
            "mostly people. A firm that keeps certified consultants billable at "
            "a healthy spread, runs sensible pyramid leverage, and delivers "
            "efficiently earns 15-30% EBITDA; a firm carrying a bench between "
            "go-live cycles bleeds. The structural margin upgrade is mix: "
            "shifting from finite, lumpy implementation projects to recurring "
            "AMS delivered offshore/nearshore raises both durability and "
            "margin, which is why sponsors prize the AMS attach rate over raw "
            "project revenue (ILLUSTRATIVE ranges)."),
    ),
    risks=[
        Risk("Project lumpiness / bench utilization", "High",
             "Finite EHR go-lives create feast-or-famine utilization; a bench "
             "between cycles directly erodes margin — AMS is the hedge."),
        Risk("Certified-talent scarcity & attrition", "High",
             "Epic controls certification, so capacity cannot scale on demand "
             "and losing certified consultants is a direct revenue loss."),
        Risk("Platform-cycle risk (Oracle Health / EHR-spend pause)", "Medium",
             "The Cerner→Oracle Health migration could unlock a super-cycle or "
             "freeze client spend; a demand pause hits utilization immediately."),
        Risk("Commoditization of cyber/interoperability advisory", "Medium",
             "The post-Change-Healthcare demand wave is crowded and "
             "price-competitive — differentiation and IP matter."),
        Risk("Client concentration & big-consulting encroachment", "Medium",
             "Reliance on a few health-system logos, with Deloitte/Accenture/"
             "Optum competing down-market for the same work."),
        Risk("Offshore delivery execution", "Medium",
             "The AMS margin upgrade depends on building reliable offshore/"
             "nearshore delivery without quality or security slippage."),
    ],
    diligence_questions=[
        "What is the recurring (AMS) versus project revenue mix, and what is "
        "the AMS attach rate and net retention?",
        "How many certified consultants (Epic/Oracle Health) by application, "
        "and what is the certified-staff attrition rate?",
        "What is utilization, realization, and the leverage ratio — and how do "
        "they move between go-live cycles?",
        "What is the client concentration, and how much revenue sits in the top "
        "handful of health-system logos?",
        "What is the offshore/nearshore delivery footprint and its share of AMS "
        "delivery cost?",
        "What is the exposure to the Oracle-Cerner migration path — upside "
        "super-cycle or downside spend freeze?",
        "What is book-to-bill/backlog and the pipeline coverage against burn?",
        "What IP, accelerators, or productized offerings differentiate the firm "
        "from staff-augmentation commoditization?",
    ],
    insider_lens=[
        "Epic certification is the moat and the ceiling. You cannot conjure "
        "certified consultants on demand — Epic controls the badge — so a "
        "firm's certified roster is a genuine asset and simultaneously the cap "
        "on how much work it can staff. Read the certified-headcount and "
        "attrition before the pipeline.",
        "The project is the sizzle; the annuity is the AMS. Go-lives are "
        "lumpy and finite, and a firm that lives on implementation revenue is "
        "one migration cycle from a bench. The durable, multiple-expanding "
        "asset is recurring managed services — underwrite the recurring mix, "
        "not the marquee go-live.",
        "It is utilization × bill rate × realization × leverage — the same math "
        "as any consulting firm. A stalling book-to-bill or a growing bench "
        "shows up in margin a quarter before it shows up in the narrative.",
        "The Oracle-Cerner overhang is the sector's wildcard. It can unlock a "
        "migration super-cycle (clients moving to Epic or committing to Oracle "
        "Health) or freeze EHR spend while executives wait — and utilization is "
        "exposed to whichever way it breaks.",
        "Cybersecurity became board-level the day Change Healthcare went down — "
        "real, durable demand — but it is also where every firm now claims to "
        "play. Differentiation is IP and delivery, not another slide that says "
        "'zero trust'.",
    ],
    connections=default_connections(
        "hit_consulting",
        deals_sector="hit_consulting",
        extra_pages=[
            ("/diligence/tam-sam?template=hit_consulting",
             "HIT Consulting deep-dive — sizing build + realized-deal history"),
        ],
        connectors=[
            ("bls_qcew_industry_area",
             "BLS QCEW — computer systems design (NAICS 541512) employment & "
             "wages (the consulting labor-cost base)"),
            ("cms_open_data_catalog",
             "CMS Open Data — interoperability, QPP, and program surfaces that "
             "drive compliance demand"),
            ("npi_provider",
             "NPI Registry — the health-system & provider client universe"),
            ("oig_leie_exclusions",
             "OIG LEIE — excluded entities (compliance/integrity screen)"),
        ],
    ),
    sources=[
        Source("ONC/ASTP HealthIT.gov — Cures Act, info blocking, USCDI/FHIR, "
               "TEFCA, HTI rules", "GOV", "https://www.healthit.gov/"),
        Source("CMS — Interoperability & Prior Authorization Final Rule "
               "(CMS-0057-F)", "GOV",
               "https://www.cms.gov/newsroom/fact-sheets/cms-interoperability-and-prior-authorization-final-rule-cms-0057-f"),
        Source("KLAS Research / industry analysts — EHR implementation and "
               "managed-services market reads", "INDUSTRY",
               "https://klasresearch.com/"),
        Source("HHS Office for Civil Rights — HIPAA Security Rule (proposed "
               "2025 strengthening)", "GOV",
               "https://www.hhs.gov/hipaa/for-professionals/security/index.html"),
        Source("PE Desk industry deep-dive (health-IT / consulting) + realized-"
               "deal corpus", "INTERNAL",
               "/diligence/tam-sam?template=hit_consulting"),
    ],
    live_figures=live_figures_from_dive("hit_consulting"),
    trends=(
        "Health-IT consulting demand rides three overlapping waves. The first "
        "is the EHR cycle: after a decade of Epic and Cerner installs, the work "
        "shifted from net-new implementation to optimization, consolidation "
        "(M&A integration onto a single instance), and — the current wildcard — "
        "the Oracle-Cerner migration path, which could unlock a super-cycle to "
        "Epic or Oracle Health or freeze spend. The second is regulation: the "
        "CMS interoperability and prior-authorization rule (FHIR APIs, dated "
        "2026-27 compliance), TEFCA, ONC info-blocking, and the HTI AI-"
        "transparency rules each manufacture implementation demand. The third, "
        "and newest, is cybersecurity and resilience, which became board-level "
        "after the Change Healthcare attack. Under all three, the structural "
        "business shift is from lumpy, finite project revenue toward recurring "
        "application managed services delivered offshore/nearshore — the "
        "durable annuity that PE roll-ups (Guidehouse, Tegria, Nordic, "
        "CereCore) are built to capture. The binding constraint throughout is "
        "certified talent: Epic controls certification, so capacity, not "
        "demand, is what most often caps a firm's growth."),
    growth_levers=[
        GrowthLever(
            "EHR cycles (migration / consolidation / optimization)",
            "Cerner→Epic migrations, Oracle Health decisions, and M&A "
            "integration onto single instances drive waves of implementation "
            "and optimization work.",
            "cycle-driven", "ILLUSTRATIVE"),
        GrowthLever(
            "Regulatory compliance (interoperability / prior-auth / TEFCA)",
            "CMS-0057-F FHIR and prior-auth mandates, TEFCA onboarding, and "
            "info-blocking create dated, non-discretionary demand.",
            "+ regulatory", "GOV"),
        GrowthLever(
            "Managed-services (AMS) outsourcing shift",
            "Health systems outsource EHR/ERP support to cut cost — converting "
            "project clients into recurring, offshore-delivered AMS annuities.",
            "recurring shift", "ILLUSTRATIVE"),
        GrowthLever(
            "Cybersecurity & resilience",
            "The Change Healthcare attack made security a board-level spend — "
            "durable demand, though a crowded field.",
            "+ cyber demand", "ILLUSTRATIVE"),
        GrowthLever(
            "AI / analytics enablement",
            "Data platforms, AI governance, and ambient/clinical AI deployment "
            "open a new advisory and integration category.",
            "emerging", "ILLUSTRATIVE"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Regulatory & EHR-cycle events × certified-talent capacity",
        analysis=(
            "Demand is event- and regulation-driven rather than a smooth "
            "utilization curve. The engine is a stack of catalysts — EHR "
            "migrations and consolidations, the CMS interoperability and "
            "prior-auth mandates (with hard 2026-27 dates), TEFCA onboarding, "
            "and post-breach cybersecurity — each of which manufactures a burst "
            "of implementation work. The managed-services shift then converts a "
            "share of that burst into recurring AMS, smoothing the lumpiness. "
            "But the binding real-world constraint is supply, not demand: "
            "because Epic controls certification, a firm cannot instantly scale "
            "the certified consultants a hot skill requires, so growth is "
            "gated by certified-talent capacity and by how efficiently the firm "
            "leverages junior staff under certified leads. The winners "
            "industrialize offshore delivery and build IP/accelerators to lift "
            "throughput per certified head."),
        basis="ILLUSTRATIVE"),
    cost_drivers=[
        CostDriver(
            "Consultant labor (billable delivery staff)",
            "~55-70% of cost",
            "The dominant cost — certified implementation consultants, PMs, and "
            "AMS analysts. Utilization and the onshore/offshore mix set gross "
            "margin.", "ILLUSTRATIVE"),
        CostDriver(
            "Recruiting, bench & certification/training",
            "~10-15% of cost",
            "Sourcing scarce certified talent, carrying a bench between cycles, "
            "and funding Epic/Oracle-Health certification and upskilling.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Delivery, PMO & travel",
            "~8-12% of cost",
            "Project management, delivery tooling, and (reduced but real) "
            "on-site travel for go-lives and command centers.", "ILLUSTRATIVE"),
        CostDriver(
            "Sales, BD & partner/alliance management",
            "~8-12% of cost",
            "Long consultative sales cycles plus EHR-vendor alliance and "
            "certification relationships that gate access to work.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Technology, security & G&A",
            "~5-10% of cost",
            "Delivery platforms, IP/accelerators, and the security posture "
            "(SOC 2/HITRUST) clients now require of their consultants.",
            "ILLUSTRATIVE"),
    ],
    state_breakdown=None,
    cms_trend=None,
)

register(REPORT)
