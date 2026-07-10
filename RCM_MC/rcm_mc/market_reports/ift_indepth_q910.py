"""In-Depth content — Questions 9 & 10: the dedicated partnership model vs
its alternatives, and transportation as a strategic health-system capability.

Authored 2026-07-10 from the suite's cited corpus (ift_company,
ift_competitive, ift_npi_landscape, ift_unit_economics, ift_insourcing,
ift_moat, ift_study, ift_health_systems, ift_growth_evidence, ift_mmt, plus
the failure-quantification and NEMT/contracting dossiers). Every evidence
line carries its basis + source; claims about what MMT's CONTRACTS actually
guarantee are diligence requests — the public record contains no MMT
contract terms, and this module does not invent any. Claimed-value and
flywheel relationships are graded honestly: directly proven vs inferred vs
unvalidated, with the mechanism each read rests on named.
"""
from __future__ import annotations

from .ift_indepth import Block, Evidence, QuestionDef, SubQ

_E = Evidence
_S = SubQ


# ═════════════════════════════════════════════════════════════════════════════
# Question 9 — the dedicated partnership model vs alternatives
# ═════════════════════════════════════════════════════════════════════════════

_DEFINITION = Block(
    "q9-definition", "Definition of the partnership",
    conclusion=(
        "The public record defines the model's DESIGN — units reserved for "
        "IFT with no 911 obligation, transfer-center integration, an "
        "availability-retainer contract form — but not MMT's actual terms: "
        "what is guaranteed versus best-efforts, who bears which risk, and "
        "what reporting and governance ride along are all readable only in "
        "the agreements themselves, which are not public."),
    why_true=(
        "The design intent is publicly stated and consistent: MMT presents "
        "itself as 'not a 911 service' — inter-facility transport, hospital "
        "to hospital and nursing home to hospital — and the 2022 sponsor "
        "release describes ALS/BLS interfacility and specialty transport "
        "sold to health systems, critical-access hospitals, and long-term "
        "care facilities.",
        "The contract form that makes a dedicated model rational is known "
        "from the wider market: per-transport rates plus an availability "
        "retainer, first-call or exclusivity at the transfer center, "
        "defined service levels, and term length — which of these elements "
        "MMT's contracts actually carry is not in the public record.",
        "Risk allocation follows the fee structure, not the marketing: a "
        "dedicated-unit or retainer fee shifts underutilization risk to "
        "the hospital; absent surge commitments with remedies, "
        "excess-demand risk stays with the hospital, where it shows up as "
        "boarding and blocked beds.",
        "What separates a dedicated partnership from a preferred-provider "
        "letter is enforceability — committed capacity, defined ETAs, "
        "reporting, remedies. Most hospital IFT purchasing has none of "
        "these (Question 1's purchasing finding), which is precisely why "
        "the distinction cannot be assumed and must be read."),
    why_matters=(
        "The difference between a partnership and a letter is exactly the "
        "part that is not publicly observable. Diligence must read the "
        "actual contracts — term, minimums, retainer, SLA, remedies, "
        "termination — before crediting the model with any guarantee; "
        "until then the model is a stated design, not a proven contract "
        "form."),
    evidence=(
        _E("MMT company positioning: 'Midwest Medical Transport is not a "
           "911 service—it provides inter-facility medical transportation, "
           "taking patients from hospital to hospital, nursing home to "
           "hospital, and vice versa' — the stated design, not a contract "
           "term",
           "SOURCED", "MMT / Siouxland Chamber directory (company "
           "positioning)",
           "https://directory.siouxlandchamber.com/list/member/midwest-medical-transport-company-6143"),
        _E("2022 deal framing: 'advanced life support and basic life "
           "support inter-facility transports (IFT) and specialty "
           "transports to large and mid-sized health systems, critical "
           "access hospitals and long-term care facilities'",
           "SOURCED", "Businesswire / Harbour Point Capital, Jan 2022",
           "https://www.businesswire.com/news/home/20220125006174/en/"),
        _E("SLA-grade contract forms exist next door: urban 911 contracts "
           "run response-time fractiles (8:59 at 90%) with penalties "
           "(e.g. $5,000 per response beyond 24 minutes in San Diego's "
           "Falck contract) — the enforceability template IFT deals must "
           "import",
           "SOURCED", "911 contracting dossier — municipal contract "
           "examples (re-verify)", ""),
        _E("No MMT hospital contract, SLA, or capacity commitment is in "
           "the public record — an honest not-found after a full sweep, "
           "and the reason every guarantee question below is a diligence "
           "request",
           "FRAMEWORK", "2026-07-10 research sweep (dead-end log)", ""),
    ),
    subqs=(
        _S("What exactly is dedicated under the contract?",
           skip="MMT contract terms are not public — a diligence request; "
                "the company states the design (units reserved for IFT, no "
                "911 obligation), but what the agreements actually "
                "dedicate — units, crews, posts, hours — must be read from "
                "them."),
        _S("What is contractually guaranteed?",
           skip="Not public: no MMT SLA, capacity commitment, or remedy "
                "schedule is in the record; request live term sheets in "
                "diligence."),
        _S("What remains best-efforts?",
           skip="The guarantee/best-efforts line is exactly what the "
                "unpublished contract language draws — unanswerable from "
                "desk research."),
        _S("Who determines capacity?",
           "At the model level, the provider staffs to the system's "
           "demand curve with the hospital's forecast input; whether the "
           "hospital holds a contractual capacity-setting right is a term "
           "to read in diligence."),
        _S("Who controls priorities?",
           "Design intent: the transfer center's queue — dedicated units "
           "answer to hospital demand, not a PSAP; how the contract "
           "arbitrates between competing facilities is unpublished."),
        _S("Who bears underutilization risk?",
           "Whoever funds availability: pure per-trip pricing leaves idle "
           "units on the provider; a dedicated-unit/retainer fee shifts "
           "that risk to the hospital — which form MMT uses is a "
           "diligence request."),
        _S("Who bears excess-demand risk?",
           "The hospital by default — unmet demand becomes boarding and "
           "blocked beds inside its own walls — unless the contract "
           "carries surge commitments with remedies."),
        _S("What operational resources are assigned to the customer?",
           "The model's package is reserved units, co-located posts, and "
           "named/embedded coordinators (the Superior–Mount Carmel "
           "pattern); MMT's per-account assignments are not public."),
        _S("What reporting is included?",
           skip="No MMT reporting package is public; positioning claims "
                "ETA/status visibility and shared quality data — ask for "
                "an actual monthly account packet."),
        _S("What governance is included?",
           skip="Not public — joint operating committees, review cadence, "
                "and escalation paths are contract exhibits; a diligence "
                "request."),
        _S("What distinguishes the arrangement from an ordinary "
           "preferred-provider contract?",
           "Enforceability: committed capacity, defined response/ETA "
           "standards, reporting, and remedies — a preferred letter names "
           "a first call but commits nothing; the dedicated form prices "
           "the commitment."),
    ),
)


_VS_TRADITIONAL = Block(
    "q9-traditional-ems", "Versus traditional EMS",
    conclusion=(
        "Traditional EMS shares its fleet with 911 and rationally "
        "displaces scheduled IFT when emergencies spike — readiness "
        "economics (posted units, 0.30-0.50 unit-hour utilization, "
        "dispatch priority to life-threats) make the displacement "
        "structural, not a service failure; EMS keeps real advantages in "
        "emergency depth, subsidy, and rural ubiquity, and remains the "
        "better choice where volume cannot carry a dedicated unit."),
    why_true=(
        "911 economics are readiness economics: units are posted against "
        "unknown emergencies, utilization is deliberately held in the "
        "0.30-0.50 band, and dispatch protocol ranks life-threats first — "
        "a scheduled discharge competes against the jurisdiction's "
        "emergency queue and loses by design, because the operator's "
        "contract runs to the municipality, not the hospital.",
        "ETAs from a shared fleet are therefore structurally unreliable "
        "for IFT: the truck promised to a discharge can be pulled to a "
        "911 call at any moment, so no shared-fleet operator can promise "
        "a window it does not control — the mechanism behind the "
        "hospitals' #1 complaint about mixed operators.",
        "Integration and data point the wrong way: municipal CAD and "
        "response-time reporting are built for the PSAP and the city "
        "contract; transfer-center workflow integration and per-facility "
        "reporting are not what the system is designed — or paid — to "
        "offer.",
        "The retained advantages are real: full emergency response depth "
        "and surge scale, municipal subsidy, licensure everywhere, and "
        "in thin rural markets 911-anchored capacity may be the only "
        "transporter that exists — the fire-based metro monopolies "
        "(Omaha FD's 18 ALS ambulances, Lincoln Fire & Rescue) also show "
        "the flip side: they leave the scheduled-IFT lane to privates."),
    why_matters=(
        "The comparison is fit, not better/worse: shared-fleet EMS is "
        "optimized for a different buyer (the municipality). A hospital "
        "purchasing ETA reliability is buying the one thing a 911-first "
        "fleet is structurally unable to sell — and clinical stakes ride "
        "on that reliability, because transfer delay is measured in "
        "mortality, not just minutes."),
    evidence=(
        _E("911 systems target ~0.30-0.50 unit-hour utilization (AIMHI "
           "survey mean 0.508) — idle readiness is the design, and it is "
           "what scheduled IFT competes against on a shared fleet",
           "SOURCED", "AIMHI benchmarking / EMS1",
           "https://aimhi.mobi/benchmarking-resources/"),
        _E("Mean cost per transport $3,127 for governmental agencies vs "
           "$1,778 private for-profit — readiness coverage rides on every "
           "shared-fleet trip",
           "SOURCED", "CMS/RAND GADCS Year 1-2 report, via trade coverage "
           "(re-verify)",
           "https://ambulance.org/2025/12/09/cms-releases-new-gadcs-report/"),
        _E("Fire-based 911 monopolies (Omaha FD runs 18 ALS ambulances as "
           "the city's primary transport; Lincoln Fire & Rescue runs city "
           "EMS) leave the scheduled-IFT lane to private operators — the "
           "structural opening the dedicated model occupies",
           "SOURCED", "City EMS pages via NPPES landscape sweep, "
           "2026-07-10 (re-verify)",
           "https://www.omaha-fire.org/our-services/emergency-medical-services"),
        _E("What unreliable transfer timing costs: STEMI transfer median "
           "door-in-door-out 68 minutes, only 11% within the 30-minute "
           "standard; DIDO >30 min carried in-hospital mortality 5.9% vs "
           "2.7% (adjusted OR 1.56)",
           "ACADEMIC", "Wang et al., JAMA 2011",
           "https://doi.org/10.1001/jama.2011.862"),
    ),
    subqs=(
        _S("Is traditional EMS capacity shared with 911?",
           "Yes — that is its defining economics: units are posted "
           "against unknown emergencies, and IFT runs on whatever "
           "readiness is left over."),
        _S("Can IFT trips be displaced?",
           "Yes, by design — dispatch priority ranks life-threats first, "
           "so a scheduled discharge is bumped when the 911 queue spikes; "
           "the operator's obligation runs to the municipality, not the "
           "hospital."),
        _S("How predictable are ETAs?",
           "Structurally unpredictable for IFT: the promised truck can be "
           "pulled to an emergency at any time — a shared fleet cannot "
           "promise a window it does not control."),
        _S("How much integration is available?",
           "Thin — municipal CAD and reporting serve the PSAP and the "
           "city contract; transfer-center workflow integration is "
           "neither the design nor the incentive."),
        _S("How broad are clinical capabilities?",
           "Broad at the emergency end (full ALS response depth); "
           "scheduled CCT/SCT interfacility capability varies and is "
           "often the gap — 911 systems staff for scene response, not "
           "critical-care legs."),
        _S("How much performance data are shared?",
           "With the municipality, extensively (response-time fractiles, "
           "penalties); with hospitals, typically nothing — the "
           "accountability instrument points at the city."),
        _S("How does fleet density compare?",
           "Denser in absolute units, but positioned for response-time "
           "geometry rather than for chaining facility-to-facility legs — "
           "density of the wrong shape for IFT economics."),
        _S("How do costs compare?",
           "Readiness is expensive: GADCS mean cost per transport is "
           "$3,127 governmental vs $1,778 private for-profit — idle "
           "coverage rides on every trip a shared fleet runs."),
        _S("What advantages does traditional EMS retain?",
           "Emergency depth and surge scale, municipal subsidy, "
           "licensure everywhere, and in thin rural markets it may be "
           "the only transporter available at all."),
        _S("Under what circumstances would traditional EMS be the better "
           "choice?",
           "Where volume cannot support a dedicated unit (thin rural "
           "books), where the trip mix is emergency-adjacent, or where a "
           "public-utility contract explicitly protects IFT capacity — "
           "otherwise the hospital is buying leftover readiness."),
    ),
)


_VS_REGIONAL = Block(
    "q9-regional", "Versus regional transportation vendors",
    conclusion=(
        "Scaled regional privates are the closest comparables — Superior "
        "and Ryan Brothers run the same embedded, dedicated playbook and "
        "can beat any entrant inside their tenured home relationships — "
        "but the archetype is geographically boxed, capital-constrained, "
        "and often 911-mixed, and it cannot follow a multi-hospital "
        "system across markets; below it, the mom-and-pop tail cannot "
        "serve system contracts at all."),
    why_true=(
        "The supply base is a long tail: ~10,600 ground ambulance "
        "organizations bill Medicare nationally, and the vendored NE+IA "
        "registry shows 751 org NPIs with only 58 private organizations "
        "in all of Nebraska — genuine regional scale is rare, and most of "
        "what hospitals can call is subscale.",
        "Regional strength is real where it exists: Superior's embedded "
        "scheduling coordinators at Mount Carmel and Ryan Brothers' "
        "60-year Madison first-call are working proof that a regional "
        "can hold dedication and integration as well as any platform — "
        "inside its region.",
        "The boxed-geography constraint binds harder every year: 70% of "
        "community hospitals are now system-affiliated (3,567 of 5,121, "
        "FY2024), and systems increasingly buy transport at the system "
        "level — a single-region vendor cannot extend dedicated capacity "
        "to the out-of-region half of the account.",
        "Consolidation is the market's own answer: AmeriPro (Whistler "
        "Capital) bought North Platte's Priority Medical Transport in "
        "Feb 2025 to acquire incumbency rather than build it — the "
        "regional archetype is simultaneously the competitive bar and "
        "the roll-up pipeline."),
    why_matters=(
        "Against a regional the contest is symmetric — same offer, "
        "decided by tenure, density, and first-call per metro — so entry "
        "strategy must be buy-or-avoid where tenure is deep, and "
        "build-and-win where the pool is fragmented; pretending the "
        "dedicated offer itself is proprietary would misread the field."),
    evidence=(
        _E("~10,600 ground ambulance organizations bill Medicare — an "
           "extremely long tail below regional scale",
           "GOV", "MedPAC Ambulance Payment Basics, Oct 2024",
           "https://www.medpac.gov/wp-content/uploads/2024/10/MedPAC_Payment_Basics_24_ambulance_FINAL_SEC.pdf"),
        _E("751 unique ambulance org NPIs across NE+IA; Nebraska's "
           "private layer is 58 organizations — the fragmented base "
           "beneath the few scaled regionals",
           "SOURCED", "CMS NPPES registry sweep, vendored 2026-07-10", ""),
        _E("AmeriPro Health (Whistler Capital) acquired Priority Medical "
           "Transport (North Platte) in Feb 2025 — 'expands its suite of "
           "patient-centric 911, interfacility medical transportation, "
           "and critical care transport services across Nebraska'",
           "SOURCED", "PRNewswire deal release, Feb 2025",
           "https://www.prnewswire.com/news-releases/ameripro-health-acquires-priority-medical-transport-and-expands-midwest-presence-302372373.html"),
        _E("70% of US community hospitals are system-affiliated (3,567 "
           "of 5,121, FY2024) — the buyer is consolidating past "
           "single-region vendors",
           "SOURCED", "AHA Fast Facts 2026 (2024 Annual Survey) "
           "(re-verify)",
           "https://www.aha.org/system/files/media/file/2026/02/Fast-Facts-on-US-Hospitals-2026.pdf"),
        _E("Superior's embedded coordinators per Mount Carmel campus and "
           "Ryan Brothers' 60-year Madison first-call — the regional "
           "playbook at its strongest",
           "SOURCED", "ift_geo registry, public/company web (re-verify)",
           ""),
    ),
    subqs=(
        _S("How does geographic coverage compare?",
           "Regionals are boxed to a home region by licensure, posts, "
           "and density; a platform can follow the buyer — MMT claims 13 "
           "states, with 23 active org NPIs across 11 states in NPPES "
           "(one VA record unconfirmed)."),
        _S("How does service breadth compare?",
           "The strong regionals match the full BLS-through-CCT ladder "
           "(Superior and Ryan Brothers run genuine critical-care "
           "transport); the mom-and-pop tail below them thins to BLS "
           "discharge work."),
        _S("How does technology compare?",
           "Dispatch/ETA stacks scale with capital: subscale locals lack "
           "them, strong regionals have credible ones — whose stack "
           "actually performs is an account-level demonstration, not a "
           "brochure comparison."),
        _S("How does standardization compare?",
           "A platform standardizes protocols, revenue cycle, and "
           "reporting across markets; a single-region vendor carries one "
           "market's habits — cross-market consistency is where the "
           "archetype structurally cannot compete."),
        _S("How does local responsiveness compare?",
           "Often the regional's best card: owner-operator proximity and "
           "decades of first-call tenure (Ryan Brothers' 60 years in "
           "Madison) can beat any platform's account management locally."),
        _S("How does pricing compare?",
           "No public IFT rate cards exist to compare — flagged; "
           "subscale locals undercut on simple BLS legs, while "
           "committed-capacity pricing is a different product than a "
           "per-trip rate."),
        _S("How does workforce depth compare?",
           "Scale wins recruiting pipelines and float pools, but labor "
           "is local (~70.7% of ambulance cost): a tenured regional with "
           "local loyalty can out-staff a platform's new-market entry."),
        _S("Can the vendor support a multi-hospital system?",
           "Within one region, the strong ones demonstrably do (Superior "
           "across Mount Carmel's campuses); across a system's "
           "multi-state footprint, no — the archetype's binding "
           "constraint."),
        _S("Can it enter adjacent markets?",
           "Slowly and at capital cost — licensure, density, and "
           "relationships take years per market; the faster path is "
           "being acquired (the AmeriPro-Priority pattern)."),
        _S("Are regional vendors capable of offering similarly dedicated "
           "capacity?",
           "Yes in kind — dedication is a contract-and-operations "
           "choice, not proprietary technology; Superior's embedded "
           "model is functionally the same offer inside its region."),
        _S("Where might a regional vendor outperform MMT?",
           "Inside its tenured home relationships (Madison, Mount "
           "Carmel), on local responsiveness, and anywhere MMT is the "
           "new entrant facing an embedded incumbent's switching costs."),
    ),
)


_VS_INSOURCING = Block(
    "q9-insourcing", "Versus insourcing",
    conclusion=(
        "Insourcing buys maximum control at the price of capital, an EMS "
        "management burden, and unhedged utilization risk — economics "
        "that clear only at very high captive volume (Mayo, Allina) or "
        "where acuity mandates control (Children's Nebraska's owned "
        "peds/neonatal fleet); most systems therefore insource only the "
        "top tier and outsource the routine book, which is exactly the "
        "opening the dedicated model's 'system-like control without "
        "ownership' pitch addresses."),
    why_true=(
        "The control is real and sometimes decisive: an owned fleet "
        "means absolute dispatch priority, direct clinical governance, "
        "and full data — Children's Nebraska runs a CAMTS-accredited "
        "neonatal/pediatric fleet (ground ambulances, an EC145 "
        "helicopter, a PC-12 fixed-wing) precisely because peds/NICU "
        "acuity is worth owning at any cost.",
        "The costs are equally real: 24/7 credentialed crews (labor is "
        "~70.7% of ambulance cost), medical direction, fleet capital, "
        "dispatch, and an ambulance revenue cycle — and the GADCS gap "
        "between governmental ($3,127) and private for-profit ($1,778) "
        "mean cost per transport shows what sub-scale readiness costs, "
        "while the MedPAC volume-cost curve says only high, stable "
        "volume amortizes it.",
        "The classification trap cuts against overstating insourcing: "
        "owning a few trucks is not insourcing — measured by transport "
        "VOLUME, most multi-hospital systems sit in hybrid bands, "
        "self-running the high-acuity slice and outsourcing the routine "
        "book; even in MMT's footprint, Bryan Health outsources its air "
        "program (StarCare is operated by Air Methods) and no Bryan-"
        "owned ground fleet was found.",
        "System finances currently push toward asset-light: CommonSpirit "
        "posted a -$225M FY2025 operating loss (improved from -$875M "
        "FY2024) — the environment in which a fixed-cost fleet competes "
        "against clinical uses of the same capital, and the backdrop for "
        "strategic reviews that flip captive fleets to outsource."),
    why_matters=(
        "The insourcing comparison sets both the ceiling and the "
        "conversion moment: above the volume bar the door is closed "
        "(size the addressable market net of captive fleets); below it "
        "the dedicated model is structurally advantaged — and margin "
        "pressure plus M&A are when owned fleets come into play."),
    evidence=(
        _E("Children's Nebraska OWNS its transport: a CAMTS-accredited "
           "neonatal/pediatric critical-care team with 'a fleet of "
           "ground ambulances, a EC 145-C2 helicopter and a PC 12 "
           "fixed-wing aircraft' — the acuity-mandated insource "
           "archetype",
           "SOURCED", "Children's Nebraska provider pages, 2026",
           "https://www.childrensnebraska.org/providers/specialties/transport-critical-care"),
        _E("Mean cost per transport $3,127 governmental vs $1,778 "
           "private for-profit; labor 70.7% of total cost — the "
           "sub-scale readiness penalty an owned fleet must beat",
           "SOURCED", "CMS/RAND GADCS Year 1-2 + Year 1-4 reports, via "
           "trade coverage (re-verify)",
           "https://ambulance.org/2025/12/09/cms-releases-new-gadcs-report/"),
        _E("Strong inverse relationship between response volume and cost "
           "per response — only high captive volume amortizes a fleet",
           "SOURCED", "MedPAC assessment of GADCS data, Dec 2025",
           "https://www.medpac.gov/wp-content/uploads/2025/12/Tab-M-Ambulance-Dec-2025.pdf"),
        _E("CommonSpirit FY2025 operating loss $225M (improved from "
           "$875M FY2024) — system-level margin pressure favors "
           "asset-light outsourcing over fleet ownership",
           "SOURCED", "CommonSpirit FY2025 year-end results (re-verify)",
           "https://www.commonspirit.org/news-articles/commonspirit-health-releases-fy2025-year-end-results"),
        _E("Bryan Health outsources even its branded air program — "
           "StarCare has long been operated by Air Methods (equipment, "
           "pilots, medical staffing); no Bryan-owned ground ambulance "
           "found",
           "SOURCED", "Bryan Health system pages + air-program coverage "
           "(re-verify)",
           "https://www.bryanhealth.com/locations/hospitals/bryan-medical-center/"),
    ),
    subqs=(
        _S("How much control does insourcing provide?",
           "Maximum — the fleet is a department: absolute dispatch "
           "priority, direct clinical governance, full data; Mayo runs "
           "fleet, transfer center, and the 911 designation as one "
           "enterprise."),
        _S("How much capital does it require?",
           "Vehicles, posts, and CAD are the visible part; the larger "
           "commitment is a permanent 24/7 credentialed workforce (labor "
           "~70.7% of ambulance cost) competing against clinical uses of "
           "the same capital."),
        _S("What management capabilities are required?",
           "A genuine EMS operating company inside the hospital: medical "
           "direction, crew scheduling, fleet maintenance, dispatch, and "
           "a specialized ambulance revenue cycle — none of it core to "
           "running hospitals."),
        _S("How difficult is staffing?",
           "The binding constraint: credentialed EMS labor is scarce "
           "(80%+ of Nebraska agencies are volunteer-dependent and the "
           "base is contracting), and a hospital fleet competes for the "
           "same paramedics as every operator."),
        _S("How difficult is scaling capacity?",
           "Lumpy and slow — each added unit is a fixed 24/7 crew "
           "commitment; covering surge means carrying idle cost the rest "
           "of the year, exactly the utilization risk outsourcing "
           "shifts away."),
        _S("How does technology investment compare?",
           "A captive fleet amortizes CAD/ePCR over one system's volume; "
           "a multi-account operator amortizes it over many — the "
           "platform's per-trip technology cost is structurally lower."),
        _S("How does clinical oversight compare?",
           "Insourcing puts crews under the system's own medical "
           "direction — the strongest argument for it, and why the "
           "acuity-mandated slices (Children's peds/NICU fleet) stay "
           "owned."),
        _S("How does utilization compare?",
           "An insourced fleet serves one system's demand curve, peaks "
           "and troughs unhedged; an outsourced operator pools accounts "
           "and chains legs — the MedPAC volume-cost curve working in "
           "its favor."),
        _S("Can MMT provide health-system-like control without "
           "ownership?",
           "Partially, and only contractually: dedicated units + "
           "embedded coordinators + shared data replicate operational "
           "control — design-consistent, but not publicly demonstrated; "
           "the contract terms are the proof that matters."),
        _S("Which control does the health system give up?",
           "Direct employment and medical direction of crews, unilateral "
           "re-tasking of units, and vertical data ownership — plus "
           "counterparty risk on the partner's staffing and solvency."),
        _S("Under what conditions is insourcing economically superior?",
           "Very large, stable captive volume that keeps owned units at "
           "high utilization (Mayo; Allina at ~34,000 interfacility "
           "requests/yr), or acuity niches where control outweighs any "
           "cost (peds/neonatal CCT)."),
        _S("Under what conditions is MMT structurally advantaged?",
           "Everywhere below that volume bar: mid-density systems with "
           "peaked discharge curves, capital-constrained systems "
           "(CommonSpirit's -$225M FY2025 operating loss is the "
           "environment), and multi-site books where pooling lifts "
           "utilization."),
    ),
)


_VS_MULTIVENDOR = Block(
    "q9-multivendor", "Versus multi-vendor outsourcing",
    conclusion=(
        "A multi-vendor call list buys nominal capacity and the comfort "
        "of no single dependence, but at the cost of accountability, "
        "diluted volume that prevents any vendor from investing in "
        "dedicated capacity, inconsistent standards, and coordination "
        "work pushed back onto nursing — while genuine resilience still "
        "requires a backstopped primary, because a dedicated partner "
        "that fails recreates the boarding queue with fewer alternatives "
        "kept warm."),
    why_true=(
        "Multi-vendor is how the market got here: call lists mean no "
        "committed volume, and without committed volume no operator "
        "rationally adds dedicated units — the purchasing structure "
        "itself creates the capacity problem (Question 1's finding), "
        "and the fragmentation is measurable: 751 ambulance org NPIs in "
        "just two states, with Nebraska's own assessment warning of a "
        "possible excess of licensed agencies.",
        "Accountability diffuses with share: below a dominant "
        "share-of-wallet no vendor owns the outcome, every failure is "
        "attributable to someone else's trip, and no minority-share "
        "vendor will accept SLA exposure — the operator thesis pegs the "
        "accountability threshold at 85%+ of a system's outsourced "
        "book.",
        "Coordination is a hospital-paid tax: staff work the list trip "
        "by trip, re-explaining requirements per vendor; the burden is "
        "real but unquantified — no peer-reviewed time-motion study of "
        "transport coordination exists (flagged as a measurement gap, "
        "not a number).",
        "Concentration risk is the honest counterweight: a dedicated "
        "primary at high share must be backstopped by contracted surge "
        "and backup arrangements — primary-plus-backup, not "
        "many-equal-vendors, is the resilient structure, and the "
        "backup terms belong in the primary's own contract."),
    why_matters=(
        "The real choice is committed versus uncommitted volume: "
        "dilution buys redundancy in name and forfeits the density "
        "economics (the volume-cost curve) that make reliable dedicated "
        "capacity affordable at all — but sole-sourcing without "
        "contracted failure remedies swaps one risk for another."),
    evidence=(
        _E("751 unique ambulance org NPIs across NE+IA — the fragmented "
           "pool a multi-vendor call list draws from, individually "
           "unable to serve system-wide contracts",
           "SOURCED", "CMS NPPES registry sweep, vendored 2026-07-10",
           ""),
        _E("Nebraska's state assessment: 'Nebraska may have an excess of "
           "licensed EMS transporting agencies, which may be "
           "exacerbating shortages and creating inefficiencies' — more "
           "vendors has not meant more capacity",
           "GOV", "NE DHHS Statewide EMS Assessment 2023-24 (re-verify)",
           "https://dhhs.ne.gov/OEHS%20Program%20Documents/NE%20Statewide%20EMS%20Assessment%20v2024.pdf"),
        _E("Strong inverse relationship between response volume and cost "
           "per response — splitting a book across vendors forfeits the "
           "density that funds dedicated capacity",
           "SOURCED", "MedPAC assessment of GADCS data, Dec 2025",
           "https://www.medpac.gov/wp-content/uploads/2025/12/Tab-M-Ambulance-Dec-2025.pdf"),
        _E("The 85%+ share-of-wallet threshold — below it the system "
           "keeps a second vendor warm and accountability stays "
           "contestable — is the operator thesis target, not a measured "
           "market statistic",
           "FRAMEWORK", "MMT operator stickiness thesis (ift_moat "
           "factors)", ""),
    ),
    subqs=(
        _S("Does a multi-vendor model provide more aggregate capacity?",
           "Nominally yes — more logos on the call list; effectively no: "
           "none of the vendors reserves anything, so peak-hour capacity "
           "is whatever each vendor's other customers left over."),
        _S("Does it reduce dependence on one provider?",
           "Yes — its genuine benefit, and the reason even a "
           "dedicated-primary structure should keep contracted backup "
           "rather than literal sole-sourcing."),
        _S("Does it create lower accountability?",
           "Yes — with volume split, no vendor owns the outcome; every "
           "failure is someone else's trip, and no minority-share vendor "
           "will accept SLA exposure."),
        _S("Does it dilute volume and prevent dedicated investment?",
           "Yes — the central mechanism: without committed volume no "
           "operator rationally adds dedicated units, so the model "
           "reproduces the capacity shortage it hedges against."),
        _S("Does it require greater hospital coordination?",
           "Yes — staff work the list trip by trip across vendors; the "
           "burden is real but unmeasured (no published time-motion "
           "study — flagged)."),
        _S("Are service standards consistent?",
           "No — each vendor brings its own crews, protocols, and "
           "habits; consistency requires either one accountable operator "
           "or a hospital-run vendor-management function most systems do "
           "not staff."),
        _S("Is performance measurable across providers?",
           "Rarely — trip-priced vendors report nothing, and willing "
           "ones report incomparably; measurement requires the hospital "
           "to impose one definition set across all of them."),
        _S("Can MMT offer enough redundancy to replace multiple vendors?",
           "Within a dense footprint, pooled units plus surge posts can "
           "functionally replace a call list — but the claim is "
           "capacity-plan-specific: ask for the unit-hour math per "
           "account rather than accepting it in general."),
        _S("Should MMT still operate with backup providers?",
           "Yes — an honest dedicated model names its backup "
           "arrangements for surge and downtime; primary-plus-contracted-"
           "backup is the resilient structure."),
        _S("What happens if MMT fails to meet demand?",
           "The queue re-forms inside the hospital (boarding, blocked "
           "beds) with fewer alternatives kept warm — which is why "
           "remedies, backup obligations, and exit/transition terms are "
           "the contract's most important pages."),
    ),
)


_VALUE_PROP = Block(
    "q9-value", "Claimed value proposition",
    conclusion=(
        "Every claimed benefit is design-consistent and none is publicly "
        "proven: the mechanisms (reserved units → acceptance and ETA; "
        "integration → fewer calls; whole-book visibility → modality "
        "match) follow from the model's structure, and the outcome "
        "literature proves the problems are large — but no account-level "
        "before/after data for MMT is public, so proof of each claim is "
        "a diligence request against CAD and EHR timestamps that "
        "already exist."),
    why_true=(
        "What is directly proven publicly is only the problem size and "
        "the stated design: STEMI transfer DIDO median 68 minutes with "
        "mortality aOR 1.56 beyond 30; ED boarding means rising from "
        "138 to 343 minutes (2018→2022); delayed discharges at a 22.8% "
        "weighted mean — plus MMT's stated reserved-unit, no-911 "
        "design.",
        "What is inferred, not shown: trip acceptance, ETA accuracy, "
        "cancellations, and coordination relief follow mechanically IF "
        "capacity is truly reserved and integrated — a logic chain from "
        "readiness economics and dispatch priority, not measured MMT "
        "performance.",
        "What is unvalidated: discharge timing, bed availability, total "
        "cost, patient experience, and cross-facility consistency — all "
        "require account-level before/after measurement, and no MMT "
        "customer case study with a controlled baseline is public "
        "(recorded as not-found).",
        "The total-cost claim is the most contested because the "
        "accounting is asymmetric: a dedicated deal converts hidden "
        "failure costs (bed-days at roughly $3,132 adjusted expense per "
        "inpatient day, boarding hours, staff time) into visible "
        "contract fees — the bed-day arithmetic can justify it, but "
        "only per-account netting decides."),
    why_matters=(
        "For underwriting, price the claims as testable hypotheses with "
        "named metrics — acceptance rate, ETA variance, cancellation "
        "rate, DIDO transport interval, discharge-order-to-depart — the "
        "data sits in MMT's CAD and the hospitals' EHRs, so diligence "
        "can convert every claim into evidence quickly, and a seller "
        "unwilling to share it is itself a finding."),
    evidence=(
        _E("STEMI transfers: median DIDO 68 minutes, only 11% within 30; "
           "DIDO >30 min carried mortality 5.9% vs 2.7% (aOR 1.56) — "
           "the clinical stake behind ETA reliability claims",
           "ACADEMIC", "Wang et al., JAMA 2011",
           "https://doi.org/10.1001/jama.2011.862"),
        _E("ED boarding among admitted patients 65+: mean 138 minutes "
           "(2018) → 343 minutes (2022); 85.2% boarded 2+ hours — the "
           "flow problem the model claims to relieve is measured and "
           "worsening",
           "ACADEMIC", "Lee et al., Ann Emerg Med 2026 (NHAMCS "
           "2015-2022)",
           "https://doi.org/10.1016/j.annemergmed.2026.03.011"),
        _E("Delayed discharges: weighted mean 22.8% of admissions across "
           "64 studies (range 1.6-91.3%) — large, real, and only partly "
           "transport-attributable",
           "ACADEMIC", "Landeiro et al., The Gerontologist 2019",
           "https://doi.org/10.1093/geront/gnx028"),
        _E("Adjusted expense per inpatient day ~$3,132 (2023) — the "
           "bed-day value that total-cost claims net against, an expense "
           "proxy rather than marginal cost",
           "SOURCED", "KFF state indicators / AHA data (re-verify)", ""),
        _E("No MMT account-level before/after performance data, case "
           "study with baseline, or customer-reported outcome is public "
           "— every value claim is a diligence request, not a fact",
           "FRAMEWORK", "2026-07-10 research sweep (dead-end log)", ""),
    ),
    subqs=(
        _S("Does MMT improve trip acceptance?",
           "Design-consistent (reserved units have no 911 queue to lose "
           "to) but unvalidated publicly — proof requires account-level "
           "acceptance rates before/after conversion."),
        _S("Does it improve ETA accuracy?",
           "Mechanically plausible for the same reason, and "
           "technology-dependent; no ETA-variance data is published — a "
           "CAD export request in diligence."),
        _S("Does it reduce cancellations?",
           "Inferred, not shown: cancellations track capacity shortfalls "
           "and double-booking, both of which dedication addresses; "
           "account data required."),
        _S("Does it reduce health-system coordination work?",
           "Inferred from the embedded-coordinator design; the baseline "
           "burden itself is unmeasured in the literature (no "
           "peer-reviewed time-motion study — flagged), so measure "
           "calls-per-trip in a live account."),
        _S("Does it improve discharge timing?",
           "Unvalidated — transport is one named cause of delayed "
           "discharge among larger ones (placement, beds); attribution "
           "requires timestamped before/after data."),
        _S("Does it improve bed availability?",
           "Unvalidated and indirect — bed release follows discharge "
           "timing; the stake is real (22.8% weighted-mean delayed "
           "discharges) but the transport-attributable share is "
           "account-specific."),
        _S("Does it improve modality matching?",
           "Testable rather than proven: a provider seeing the whole "
           "book can right-size BLS/ALS/CCT against 42 CFR 410.40 "
           "rules, and claims data can audit the mix — the CERT error "
           "taxonomy is the external benchmark."),
        _S("Does it reduce total transportation cost?",
           "Unvalidated and definitionally contested: the deal converts "
           "hidden failure costs (bed-days, boarding) into visible "
           "fees — netting can favor it at ~$3,132 expense per "
           "inpatient day, but only account arithmetic decides."),
        _S("Does it improve patient experience?",
           "Plausible (fewer waits and cancellations) and unmeasured "
           "publicly — no MMT patient-experience data is in the "
           "record."),
        _S("Does it produce more consistent performance across "
           "facilities?",
           "Design-consistent (one operator, one protocol set) and "
           "unvalidated; per-facility variance is exactly what a monthly "
           "reporting packet would show."),
        _S("Which outcomes are directly proven?",
           "None at the MMT account level in public; what is proven is "
           "the problem magnitude (DIDO, boarding, delayed-discharge "
           "literature) and the model's stated design."),
        _S("Which are inferred?",
           "Acceptance, ETA reliability, cancellations, coordination "
           "relief, cross-facility consistency — mechanical consequences "
           "IF capacity is truly reserved and integrated."),
        _S("Which remain unvalidated?",
           "All hospital-outcome claims — discharge timing, bed "
           "availability, total cost, patient experience — pending "
           "account-level before/after measurement, which diligence can "
           "obtain."),
    ),
)


Q9 = QuestionDef(
    num=9,
    slug="alternatives",
    title="How does MMT's dedicated partnership model compare with "
          "alternatives?",
    storyline=(
        "Each alternative fails on a different axis — shared 911 fleets "
        "on dispatch priority, regionals on geographic reach, insourcing "
        "on capital and utilization, multi-vendor lists on accountability "
        "and diluted volume — the dedicated model is engineered against "
        "all four, but its contract terms and claimed outcomes are "
        "diligence items, not public facts."),
    visual_key="tradeoff",
    blocks=(_DEFINITION, _VS_TRADITIONAL, _VS_REGIONAL, _VS_INSOURCING,
            _VS_MULTIVENDOR, _VALUE_PROP),
)


# ═════════════════════════════════════════════════════════════════════════════
# Question 10 — transportation as a strategic health-system capability
# ═════════════════════════════════════════════════════════════════════════════

_TRANSACTIONAL = Block(
    "q10-transactional", "Transactional versus strategic transportation",
    conclusion=(
        "The line between a transactional vendor and a strategic partner "
        "is drawn by five behaviors — shaping demand rather than only "
        "fulfilling requests, participating in planning, delivering "
        "decision-grade data, taking contractual accountability, and "
        "tying transport metrics to hospital throughput rather than "
        "transport-internal statistics — and the dedicated model is "
        "built to sit on the strategic side, though whether MMT operates "
        "there is observable only inside accounts."),
    why_true=(
        "The transactional baseline is the documented market default: "
        "trip-by-trip call lists, no committed capacity, no real-time "
        "status or ETA, no reporting, and accountability with no one — "
        "the purchasing and pain-point findings this study keeps "
        "returning to.",
        "Demand-shaping is possible because IFT demand is forecastable "
        "at the facility × hour × modality grain (discharge curves, "
        "procedure schedules, recurring dialysis): a provider that sees "
        "the whole book can re-time bookings and flag avoidable urgent "
        "requests; a vendor that sees one trip cannot.",
        "The accountability marker is contractual, not rhetorical: SLAs "
        "with remedies and shared throughput KPIs — the contract form is "
        "standard in 911 (response-time fractiles with penalties) and "
        "NEMT (on-time-pickup benchmarks with fines) and must be "
        "imported into IFT deals to mean anything.",
        "Connecting transport to hospital priorities has a measured "
        "basis: transport intervals sit inside metrics hospitals already "
        "track — stroke transfer door-in-door-out (median 174 minutes, "
        "only 27.3% within the 120-minute target) and boarding — so a "
        "partner reporting into those metrics speaks the hospital's "
        "own language."),
    why_matters=(
        "The distinction determines what the hospital is actually "
        "buying — rides, or a managed capability. Contract form and "
        "data sharing, not marketing language, reveal which one is on "
        "offer; diligence should grade any operator against the five "
        "behaviors with account evidence."),
    evidence=(
        _E("Stroke transfers: median door-in-door-out 174 minutes (IQR "
           "116-276), only 27.3% within 120 minutes — the hospital-owned "
           "flow metric a strategic transport partner reports into",
           "ACADEMIC", "GWTG-Stroke analysis, JAMA 2023 (n=108,913)",
           "https://doi.org/10.1001/jama.2023.12739"),
        _E("Adjacent markets contractualize service: Texas Medicaid NEMT "
           "carries an 85% on-time-pickup benchmark with penalties; NJ "
           "fined its broker ~$1.7M over 2017-22 — measurable, "
           "remedy-bearing service levels exist next door to IFT",
           "SOURCED", "NEMT contracting dossier — state contract terms "
           "and enforcement coverage (re-verify)", ""),
        _E("The IFT baseline is trip-by-trip and reporting-free: no "
           "public system-wide IFT contract, SLA, or vendor report "
           "surfaced for the footprint systems — the transactional "
           "default recorded as not-found",
           "FRAMEWORK", "2026-07-10 research sweep (dead-end log)", ""),
        _E("ED visits arriving via interfacility EMS transfer rose 15% "
           "(2017-19) and 35% (2020-22) vs the 2014-16 baseline — the "
           "demand a strategic partner would be planning against is "
           "measured and growing",
           "ACADEMIC", "Peters et al., Am J Emerg Med 2026",
           "https://doi.org/10.1016/j.ajem.2026.04.025"),
    ),
    subqs=(
        _S("What defines a transactional transportation vendor?",
           "Fulfills trips off a call list at per-trip rates: no "
           "committed capacity, no reporting, no planning role, "
           "accountability limited to the trip it accepted — the "
           "documented market default in hospital IFT."),
        _S("What defines a strategic operating partner?",
           "Shapes demand and capacity with the system, contracts "
           "committed capacity against SLAs, reports at the facility "
           "grain, and ties its metrics to hospital throughput rather "
           "than transport-internal statistics."),
        _S("Does the provider only fulfill requests, or does it help "
           "shape demand and capacity?",
           "The test question: shaping requires seeing the whole book "
           "(re-time bookings, flag avoidable urgencies, pre-position "
           "for discharge peaks); whether MMT does this in practice is "
           "observable inside accounts, not in the public record."),
        _S("Does the provider participate in planning?",
           "A strategic partner sits in capacity and discharge-planning "
           "forums; MMT's actual planning participation per account is a "
           "diligence observation — no public evidence either way."),
        _S("Does it provide actionable data?",
           "The model generates it by construction (CAD timestamps per "
           "trip); whether it is delivered as decision-grade reporting "
           "is unverified — request a live monthly packet."),
        _S("Does it help redesign workflows?",
           "The embedded-coordinator pattern is itself a workflow "
           "redesign (proven as a moat at Mount Carmel and UofL); depth "
           "beyond scheduling — booking steps, readiness protocols — "
           "must be seen on site."),
        _S("Does it take accountability for outcomes?",
           "Only a contract can say: accountability means SLAs with "
           "remedies and shared throughput KPIs, and the public record "
           "contains no MMT SLA — a diligence request."),
        _S("Does it connect transportation performance to hospital "
           "priorities?",
           "The connection is objectively available — transport "
           "intervals sit inside DIDO, boarding, and discharge metrics "
           "hospitals already track — so reporting into those metrics is "
           "the observable test of a strategic posture."),
    ),
)


_CAPACITY = Block(
    "q10-capacity", "Capacity planning",
    conclusion=(
        "Capacity planning is the strongest analytically supported link "
        "in the strategic case: IFT demand is forecastable at the "
        "facility × hour × modality grain, and the volume-cost curve "
        "says planned, dense capacity is cheaper per trip — so a "
        "provider holding the whole book can size dedicated capacity and "
        "price the capacity-versus-service tradeoff explicitly; whether "
        "MMT's tooling actually does this is a demonstration to request, "
        "not assume."),
    why_true=(
        "Forecastability is evidenced, not asserted: demand is generated "
        "by institutional rhythms — discharge curves, procedure "
        "schedules, recurring dialysis round-trips — with a "
        "scheduled-majority / urgent-minority split measurable per "
        "facility, and a thin critical slice (6.6% of adult ED "
        "transfers, rising) that sets the immediate-readiness floor.",
        "Even outside data brackets the book: allocating the 3.47M "
        "measured national acute legs by the footprint's population "
        "share versus its 65+ share yields a demand band from published "
        "inputs alone — an operator holding actual trip history can do "
        "far better, by facility, modality, and hour.",
        "Staffing a known curve is the whole economic difference "
        "between logistics and readiness: unit-hour utilization above "
        "the 0.30-0.50 911 band is achievable only when peaks are "
        "planned, and the volume-cost curve converts that planning into "
        "unit cost.",
        "The capacity-versus-service tradeoff is a solvable problem, "
        "not a slogan: each added unit-hour buys a measurable "
        "improvement in ETA bands and acceptance — a provider that can "
        "show the hospital this curve is doing capacity planning; one "
        "that cannot is quoting rates."),
    why_matters=(
        "Capacity planning converts the forecastability advantage into "
        "money for both sides — the hospital buys fewer boarding hours, "
        "the provider earns utilization — but only if demand data is "
        "pooled at the system level rather than fragmented across a "
        "call list; asking MMT to produce the unit-hour math for a live "
        "account is the cheapest possible test of the whole strategic "
        "claim."),
    evidence=(
        _E("Strong inverse relationship between response volume and cost "
           "per response — planned density is the cost lever that makes "
           "dedicated capacity affordable",
           "SOURCED", "MedPAC assessment of GADCS data, Dec 2025",
           "https://www.medpac.gov/wp-content/uploads/2025/12/Tab-M-Ambulance-Dec-2025.pdf"),
        _E("911 systems target ~0.30-0.50 unit-hour utilization; "
           "non-emergency providers target higher — the utilization "
           "headroom a planned scheduled book captures",
           "SOURCED", "AIMHI benchmarking / EMS1",
           "https://aimhi.mobi/benchmarking-resources/"),
        _E("Footprint demand is bracketable from published inputs alone: "
           "3.47M measured national legs/yr (1.97M NEDS ED-to-ED + 1.5M "
           "NIS interhospital) allocated by footprint population share "
           "vs 65+ share — an outside-in floor the operator's own trip "
           "data should beat at the facility×modality grain",
           "DERIVED", "ift_mmt footprint demand band (ACADEMIC "
           "inputs ÷ GOV Census, equations stated)", ""),
        _E("6.6% of adult ED transfers involved a critical procedure, "
           "rising at OR 1.09/yr — the slice that must be staffed for "
           "immediate readiness inside an otherwise schedulable book",
           "ACADEMIC", "Nikolla et al., J Emerg Med 2025",
           "https://doi.org/10.1016/j.jemermed.2025.12.020"),
    ),
    subqs=(
        _S("Can MMT forecast demand by facility and modality?",
           "The demand is forecastable at that grain (discharge curves, "
           "procedure schedules, recurring dialysis) and the trip "
           "history accrues to the operator by construction; MMT's "
           "actual forecasting practice is a capabilities demo to "
           "request."),
        _S("Can it identify recurring peaks?",
           "Yes at the method level — weekday/daylight discharge peaks "
           "and procedure-day patterns are visible in any complete trip "
           "log; the open question is whether the analysis is run and "
           "shared."),
        _S("Can it plan staffing around discharge patterns?",
           "That is the core economic move of the dedicated model: "
           "staffing a known curve is what lifts unit-hour utilization "
           "above the 911 readiness band."),
        _S("Can it recommend booking-time changes?",
           "A provider seeing every facility's curve can propose "
           "re-timing (book earlier, spread peaks); the recommendation "
           "costs nothing to make — evidence of hospitals adopting it is "
           "account-level."),
        _S("Can it identify unnecessary urgent requests?",
           "The method exists (compare requested urgency against "
           "pickup-to-depart slack patterns); no published IFT "
           "over-triage rate exists to benchmark against — flagged as a "
           "measurement to build, not cite."),
        _S("Can it adjust fleet placement?",
           "Yes — posting against forecast demand is standard dispatch "
           "practice, and co-located posts at anchor campuses are the "
           "model's stated design."),
        _S("Can it help the health system determine required dedicated "
           "capacity?",
           "Yes in principle — unit-hour math against the facility "
           "demand curve yields required units per promised ETA band; "
           "even outsiders can bracket the demand from published inputs, "
           "and the operator's data does far better."),
        _S("Can it quantify the trade-off between capacity cost and "
           "service performance?",
           "Yes — a solvable queueing/pricing problem: each added "
           "unit-hour buys a measurable ETA/acceptance improvement; "
           "demanding this curve from the provider is a strong test of "
           "its analytical maturity."),
    ),
)


_WORKFLOW = Block(
    "q10-workflow", "Workflow improvement",
    conclusion=(
        "The workflow offer — fewer booking steps, fewer chase calls, "
        "readiness coordination, receiving-facility confirmation, one "
        "standard across hospitals — is the embedded-coordinator "
        "playbook already proven as a competitive moat at Mount Carmel "
        "and UofL; and the same integration that removes hospital work "
        "generates the timestamps that separate provider delays from "
        "hospital-created delays, the analytically decisive attribution "
        "step."),
    why_true=(
        "The embedded model exists in the wild and wins accounts: "
        "Superior's scheduling coordinators per Mount Carmel campus and "
        "AMR's embedded coordinators across nine UofL facilities are "
        "public proof the workflow offer holds books — as incumbency "
        "evidence, whoever runs it.",
        "Delay attribution is measurable and it matters: in stroke "
        "transfers the disposition/transport interval dominates "
        "(imaging-to-door 153.1 of a 171.4-minute mean DIDO), and "
        "within that dwell hospital-side and transport-side time must "
        "be split by timestamps — the offload literature shows "
        "hospital-created delay is real and large (three-fourths of "
        "California hospitals detained EMS crews over an hour).",
        "Patient-not-ready waits are where incentives align exactly: "
        "they are the operator's largest controllable loss and the "
        "hospital's own delay — readiness coordination is the rare "
        "improvement both sides are paid to want.",
        "Standardization is a platform capability with a compliance "
        "floor: one booking workflow, one modality-selection rule set "
        "applied against 42 CFR 410.40's necessity rules, variation "
        "surfaced per facility — a single-market vendor cannot compare "
        "facilities; a cross-facility operator holds the comparison "
        "set by construction."),
    why_matters=(
        "Workflow integration is double-edged and should be "
        "underwritten as such: it is simultaneously the service "
        "(removed coordination burden) and the moat (switching costs) — "
        "and its data exhaust is the raw material for the performance "
        "management the next block grades."),
    evidence=(
        _E("Stroke transfer DIDO decomposition: mean 171.4 minutes, of "
           "which door-to-imaging 18.3 and imaging-to-door 153.1 — the "
           "disposition/transport interval dominates, and attribution "
           "within it is a timestamp problem",
           "ACADEMIC", "JAMA Network Open 2024 (n=28,887)",
           "https://doi.org/10.1001/jamanetworkopen.2024.31183"),
        _E("'Three-fourths of hospitals detained EMS crews more than one "
           "hour, 40% more than two hours' — hospital-created delay is "
           "large, measurable, and must be split from provider delay",
           "ACADEMIC", "Backer et al., Prehosp Emerg Care 2018 (CA 2017, "
           "830,637 transports)",
           "https://doi.org/10.1080/10903127.2018.1525456"),
        _E("Median ambulance patient offload time 10.9 minutes (IQR "
           "6.6-17.5) across 7.24M records, but 3.3% of agencies had "
           ">=25% of transports offloading beyond 30 minutes — the tail, "
           "not the median, is where flow breaks",
           "ACADEMIC", "Shaw et al., Prehosp Emerg Care 2025",
           "https://doi.org/10.1080/10903127.2025.2535576"),
        _E("Superior's embedded scheduling coordinators per Mount Carmel "
           "campus; AMR embedded across 9 UofL facilities with "
           "co-branded units — the workflow playbook proven as an "
           "account-holding moat",
           "SOURCED", "ift_geo registry, public/company web (re-verify)",
           ""),
    ),
    subqs=(
        _S("Can MMT reduce the number of steps required to book a trip?",
           "Integration determines it: a booking channel wired into the "
           "transfer-center workflow removes call-and-wait loops; "
           "demonstrable in a site visit, not from the public record."),
        _S("Can it reduce repeated calls?",
           "Live ETA/status visibility is the mechanism that removes "
           "chase calls; unmeasured publicly — count calls-per-trip "
           "before/after in a pilot."),
        _S("Can it improve patient-readiness coordination?",
           "The highest-alignment target: patient-not-ready waits are "
           "the operator's largest controllable loss and the hospital's "
           "own delay — coordinators exist precisely to fix this seam."),
        _S("Can it improve modality selection?",
           "Yes as decision support at booking — level-of-service rules "
           "applied consistently against 42 CFR 410.40 — with the CERT "
           "error taxonomy as the external benchmark that makes "
           "improvement auditable."),
        _S("Can it integrate receiving-facility confirmation?",
           "Design-supported (transfer-center workflow includes "
           "destination bed confirmation); whether MMT's booking flow "
           "closes that loop is an implementation detail to observe."),
        _S("Can it standardize workflows across hospitals?",
           "A single operator across a system can impose one "
           "booking/handoff standard — something a fragmented vendor "
           "pool structurally cannot; the multi-hospital argument for "
           "the model."),
        _S("Can it identify facility-level process variation?",
           "Yes by construction — identical trips timestamped across "
           "facilities expose which campuses run slow; only a "
           "cross-facility operator holds this comparison set."),
        _S("Can it separate provider delays from hospital-created "
           "delays?",
           "Yes, and it is the decisive capability: interval timestamps "
           "split crew-side from hospital-side time — the same "
           "decomposition the DIDO literature runs and the offload "
           "studies quantify."),
        _S("Can it support continuous process improvement?",
           "The loop (measure → attribute → correct → re-measure) is "
           "standard once data flows; sustaining it requires a "
           "governance cadence that lives in contract exhibits — verify "
           "it exists."),
    ),
)


_PERFORMANCE = Block(
    "q10-performance", "Performance management",
    conclusion=(
        "Performance management is where the public record is thinnest: "
        "what data MMT actually delivers, at what grain, with what "
        "root-cause discipline and SLA comparability, is entirely a "
        "diligence request — what is defensible is that the model "
        "generates the required data by construction (CAD timestamps by "
        "facility, modality, hour) and that the market default it "
        "replaces reports nothing at all."),
    why_true=(
        "The baseline is zero: trip-priced IFT purchasing carries no "
        "reporting, no SLAs, and no penalties (Question 1's contracting "
        "finding), so any structured reporting is an upgrade — which is "
        "precisely why reporting claims need verification rather than "
        "mere contrast against nothing.",
        "The data exists by construction: dispatch systems timestamp "
        "request → assign → enroute → arrive → depart on every trip, so "
        "facility, modality, hour, and weekday grain is a query, not an "
        "invention — the open questions are whether it is shared, "
        "contractualized, and acted on.",
        "Root-cause and corrective-action discipline separates a "
        "dashboard from management: recorded delay reasons (crew, "
        "patient-not-ready, receiving refusal) are what enable "
        "provider-versus-hospital attribution and a closable "
        "improvement loop — coding discipline is unobservable from "
        "outside.",
        "Accountability has a contract test, and external precedent: "
        "comparability to contracted service levels requires such "
        "levels to exist — billing-side accountability is already "
        "external and measured (CERT ambulance improper-payment rate "
        "13.2%, $595.1M projected), while service-level accountability "
        "in IFT exists only where a dedicated contract writes it."),
    why_matters=(
        "A partner's willingness to expose per-facility performance "
        "against SLAs — with credits at risk — is the cleanest "
        "observable signal separating strategic partnership from "
        "marketing; diligence should ask for the actual monthly packet "
        "from a live account, and treat its absence as the answer."),
    evidence=(
        _E("Ambulance improper-payment rate 13.2% (projected $595.1M; "
           "insufficient documentation 63.5%, medical necessity 27.5%) — "
           "external, measured accountability already exists on the "
           "billing side; the service side has no equivalent unless a "
           "contract creates it",
           "GOV", "CMS CERT 2024 supplemental improper payment data "
           "(re-verify)", ""),
        _E("Adjacent-market service accountability is real and enforced: "
           "state NEMT programs run on-time-pickup benchmarks with "
           "fines (Mississippi's broker ran ~5.8% late/missed against a "
           "contractual limit; NJ fined ~$1.7M over 2017-22)",
           "SOURCED", "NEMT contracting dossier — state enforcement "
           "coverage (re-verify)", ""),
        _E("Urban 911 contracts define response-time fractiles with "
           "penalties (8:59 at 90%; per-response fines) — the "
           "measurable-SLA template a dedicated IFT contract can adopt",
           "SOURCED", "911 contracting dossier — municipal contract "
           "examples (re-verify)", ""),
        _E("No MMT reporting sample, dashboard, data dictionary, or SLA "
           "is public — the performance-management offer is asserted, "
           "not observable, from outside",
           "FRAMEWORK", "2026-07-10 research sweep (dead-end log)", ""),
    ),
    subqs=(
        _S("What performance data does MMT provide?",
           skip="Not public — no sample reporting packet, dashboard, or "
                "data dictionary is in the record; request live account "
                "reporting in diligence."),
        _S("Are metrics available by facility?",
           "The underlying CAD data carries facility on every trip, so "
           "the grain exists by construction; whether reports expose it "
           "is unverified."),
        _S("Are they available by modality?",
           "Same answer — modality is a field on every trip record; "
           "exposure in delivered reporting is the open question."),
        _S("Are they available by hour and weekday?",
           "Timestamps make hour/weekday grain trivial to compute; "
           "unverified as a delivered report."),
        _S("Are root causes recorded?",
           skip="Unknowable from outside — delay-reason coding is an "
                "operations discipline, not a public fact; audit the "
                "delay-reason field fill rates in a live account."),
        _S("Can performance be compared with contracted service levels?",
           "Only where contracted service levels exist — the decisive "
           "structural question: trip-priced IFT has none, and whether "
           "MMT's contracts define them is unpublished."),
        _S("Can recurring problems be identified?",
           "Yes given the data — the same lane, hour, and failure "
           "repeating is a query; the discipline to run and act on it is "
           "what diligence should observe."),
        _S("Are corrective actions tracked?",
           skip="Not observable publicly; ask for the issue log and "
                "closure rates from a live account."),
        _S("Can the health system quantify improvement over time?",
           "Only if a baseline was captured at conversion — the "
           "strongest argument for writing measurement into the contract "
           "from day one."),
        _S("Does MMT accept accountability for performance?",
           skip="Accountability is a contract fact (SLAs, credits, "
                "termination triggers) and no MMT contract is public — "
                "the single most load-bearing diligence request in this "
                "question."),
    ),
)


_OUTCOMES = Block(
    "q10-outcomes", "Health-system outcomes",
    conclusion=(
        "Transportation is causally close to some outcomes (discharge "
        "timing, transfer intervals, bed release) and only contributory "
        "to others (length of stay, total cost, placement success, "
        "patient experience) — the literature proves the stakes are "
        "large and partly transport-sensitive, but demonstrating MMT's "
        "effect requires account-level before/after measurement that is "
        "not public; the honest offer distinguishes 'directly affected' "
        "from 'influenced, not controlled', and never says "
        "'guaranteed'."),
    why_true=(
        "The direct channel is proven directionally: transport is a "
        "named non-clinical discharge-delay cause (second-most-common "
        "at 11.1% in the one quantified PACU cohort — a non-US series, "
        "magnitude only), transport-related reasons appear in US "
        "delayed-discharge series, and in stroke transfers the "
        "disposition/transport interval dominates the door-in-door-out "
        "clock (153.1 of 171.4 minutes).",
        "The magnitude at stake is large: delayed discharges average "
        "22.8% of admissions (weighted mean across 64 studies), and in "
        "one US academic hospital 3.5% of hospitalizations consumed "
        "27.2% of all inpatient days — small timing gains are worth "
        "real bed capacity.",
        "The confounded channel must be named to stay honest: facility "
        "placement availability was the dominant non-medical discharge "
        "barrier at every timepoint in the US series, and staffing and "
        "payer authorization move the same metrics — transport cannot "
        "claim them.",
        "One outcome is genuinely auditable today: high-acuity overuse "
        "and modality mismatch have external benchmarks (the CERT error "
        "taxonomy), and the RSNAT experience shows repetitive ambulance "
        "use falls hard when rules tighten — a 61% reduction in the "
        "probability of use — so right-sizing claims can be tested "
        "against claims data rather than taken on faith."),
    why_matters=(
        "The outcome case should be bought and sold as shared "
        "measurement: hold the vendor to transport-attributable metrics "
        "(pickup-window adherence, transport legs of DIDO, "
        "discharge-order-to-depart) and treat hospital-owned outcomes "
        "(LOS, experience, total cost) as jointly influenced — inflated "
        "attribution is a renewal-time liability, not a sales asset."),
    evidence=(
        _E("Transport shortage as a named discharge-delay cause: 'lack "
           "of available hospital patient transport (n = 34, 11.1%)' — "
           "second-most-common non-clinical cause in the quantified "
           "PACU cohort (non-US; magnitude signal only)",
           "ACADEMIC", "Ego et al., Ann Med Surg 2022",
           "https://doi.org/10.1016/j.amsu.2022.104680"),
        _E("Delay concentration: 101 hospitalizations (3.5%) accounted "
           "for 27.2% of 23,934 inpatient days; the most common "
           "non-medical barrier was facility placement — transport is "
           "in the causal mix, not at its head",
           "ACADEMIC", "Gao & Berland, Brown J Hosp Med 2022",
           "https://doi.org/10.56305/001c.36593"),
        _E("Stroke DIDO decomposition: the disposition/transport "
           "interval dominates (imaging-to-door 153.1 of 171.4 mean "
           "minutes) — the transfer-interval slice transport can "
           "actually own",
           "ACADEMIC", "JAMA Network Open 2024 (n=28,887)",
           "https://doi.org/10.1001/jamanetworkopen.2024.31183"),
        _E("Demand-side rules move ambulance overuse: RSNAT prior "
           "authorization produced 'a 61% reduction in the probability "
           "of RSNAT use' — modality/overuse claims are testable in "
           "claims data",
           "ACADEMIC", "Contreary et al., JAMA Health Forum 2022",
           "https://doi.org/10.1001/jamahealthforum.2022.2093"),
        _E("Delayed discharges: weighted mean 22.8% of admissions "
           "(range 1.6-91.3% across 64 studies) — the size of the pool "
           "any timing improvement draws from",
           "ACADEMIC", "Landeiro et al., The Gerontologist 2019",
           "https://doi.org/10.1093/geront/gnx028"),
    ),
    subqs=(
        _S("Can MMT demonstrate faster discharge?",
           "Not publicly — no before/after account data exists in the "
           "record; the literature proves the stake (22.8% weighted-mean "
           "delayed discharges), not the vendor effect."),
        _S("Can it demonstrate reduced bed blockage?",
           "Not publicly; bed release is downstream of discharge timing "
           "and confounded by placement availability — the dominant "
           "non-medical barrier in the US series."),
        _S("Can it demonstrate less staff coordination time?",
           "No — the baseline itself is unmeasured (no peer-reviewed "
           "time-motion study of transport coordination); a pilot with "
           "call-counting would be the first real measurement."),
        _S("Can it demonstrate fewer lost post-acute placements?",
           "Not publicly; the mechanism (hitting placement windows) is "
           "plausible, but placement loss is driven mostly by SNF "
           "selectivity and authorization, not transport alone."),
        _S("Can it demonstrate better patient experience?",
           "No public data; the mechanism (fewer waits and "
           "cancellations) is plausible and cheap to measure with "
           "existing survey tooling."),
        _S("Can it demonstrate reduced high-acuity overuse?",
           "Closest to demonstrable: modality mix is visible in claims, "
           "external benchmarks exist (CERT error taxonomy; RSNAT cut "
           "repetitive-use probability 61% when rules tightened) — an "
           "auditable claim."),
        _S("Can it demonstrate lower total cost?",
           "Not publicly, and only account arithmetic can: contract "
           "fees are visible while avoided failure costs (bed-days, "
           "boarding hours, staff time) must be counted honestly "
           "against them."),
        _S("Can it demonstrate more predictable care transitions?",
           "Variance metrics (pickup-window hit rate, ETA error "
           "distribution) would show it directly; none are published — "
           "a reporting request."),
        _S("Which outcomes are affected directly?",
           "The transport-owned intervals: request-to-pickup, "
           "pickup-window adherence, the transport legs of DIDO, "
           "discharge-order-to-depart — timestamped, attributable, and "
           "fair to hold a vendor to."),
        _S("Which outcomes are influenced but not controlled by "
           "transportation?",
           "Length of stay, bed availability, placement success, ED "
           "boarding, patient experience, total cost of care — "
           "transport moves them at the margin while placement, "
           "staffing, and payer behavior move them more."),
    ),
)


_DURABILITY = Block(
    "q10-durability", "Strategic durability",
    conclusion=(
        "The flywheel has links of different strength and must be "
        "underwritten link by link: density → economics → performance "
        "is analytically solid (the volume-cost curve plus utilization "
        "math), operating-data accumulation → better planning is solid "
        "by construction, but performance → deeper adoption → expansion "
        "is the partnership HYPOTHESIS — supported by switching-cost "
        "logic and embedded-incumbency proof points, contradicted by "
        "nothing, and proven nowhere publicly."),
    why_true=(
        "Density compounds by measurement, not metaphor: MedPAC finds a "
        "strong inverse volume-to-cost-per-response relationship, so "
        "each added facility in a metro raises utilization, cuts "
        "deadhead, and lowers unit cost — added facilities genuinely "
        "make the partnership cheaper to run, and the gain is "
        "shareable.",
        "Data compounds by construction: every trip extends the demand "
        "history that forecasting runs on, and multi-facility data "
        "enables cross-campus comparisons no single hospital can make — "
        "this link requires no leap of faith.",
        "Retention-through-integration has proof points, but as "
        "INCUMBENCY evidence rather than outcome evidence: Ryan "
        "Brothers' 60-year tenure, Superior's embedded coordinators, "
        "AMR's UofL co-branding show workflow embedding holds "
        "accounts — whether it holds because of measured performance or "
        "mere switching cost is not distinguishable from public data.",
        "The failure modes are concrete and observed: a strategic flip "
        "at an anchor (Wichita's Wesley/HCA moved ~77% of county IFT — "
        "~4,873 transports on the 2020 base — to AMR in 2022), crew "
        "supply breaks (MMT's three FLSA wage-and-hour suits across "
        "three districts mark the labor seam of a multi-state rollup), "
        "a leveraged national buying share (GMR's KKR-owned platform "
        "cut its IPO target to $3.3B after a $5.4B refinancing), and "
        "payment-policy shocks to the commercial/OON spread (the GAPB "
        "committee's balance-billing recommendations).",
        "What must be executed to hold position is the moat "
        "combination, not any single factor: reliability at the "
        "promised ETA band, crew pipeline, data delivery with honest "
        "attribution, and 85%+ share-of-wallet at the anchors — the "
        "operator thesis is explicit that digital connection alone "
        "holds nothing without co-located assets and share."),
    why_matters=(
        "For an investor or a hospital buyer the flywheel is "
        "underwritable link by link: pay for the proven links (density "
        "economics, data accumulation), test the hypothesized one "
        "(performance → expansion) against MMT's actual account "
        "retention and expansion history — a decisive fact that exists "
        "only inside the company."),
    evidence=(
        _E("Strong inverse relationship between response volume and cost "
           "per response — the measured basis for 'the partnership gets "
           "cheaper as facilities are added'",
           "SOURCED", "MedPAC assessment of GADCS data, Dec 2025",
           "https://www.medpac.gov/wp-content/uploads/2025/12/Tab-M-Ambulance-Dec-2025.pdf"),
        _E("The flip risk is observed, not theoretical: Wesley/HCA moved "
           "~77% of county IFT (~4,873 transports/2020 base) to AMR in "
           "2022 — share-of-wallet durability tracks ownership intent, "
           "not tenure",
           "SOURCED", "County EMS data via ift_geo public/analyst read "
           "(re-verify)", ""),
        _E("Three FLSA wage-and-hour suits against MMT across three "
           "districts (OH 2020, WI 2023, NE 2024) — the classic "
           "multi-state EMS-rollup labor seam; outcomes sealed without "
           "PACER",
           "SOURCED", "Federal dockets via Justia / CourtListener",
           "https://www.courtlistener.com/docket/67552669/wroblewski-v-midwest-medical-transport-company-llc/"),
        _E("GMR (KKR) cut its IPO valuation target to $3.3B in May 2026 "
           "after a $5.4B 2025 refinancing — the leveraged national "
           "competitor is constrained, not absent",
           "SOURCED", "Deal/IPO coverage via NPPES landscape sweep "
           "(re-verify)", ""),
        _E("GAPB advisory committee recommends banning ground-ambulance "
           "OON balance billing with cost-sharing capped at the lesser "
           "of $100 or 10% — the policy watch item over the "
           "commercial/OON spread",
           "GOV", "CMS GAPB Advisory Committee report, 2024",
           "https://www.cms.gov/files/document/report-advisory-committee-ground-ambulance-and-patient-billing.pdf"),
    ),
    subqs=(
        _S("Does the partnership become more valuable as more facilities "
           "are added?",
           "Yes on the cost side, by measurement — the volume-cost curve "
           "means added facilities raise density, utilization, and "
           "chainable legs; how the gain is split between parties is a "
           "negotiation, not a law."),
        _S("Does network density improve performance?",
           "Yes — density shortens response legs, cuts deadhead, and "
           "deepens surge cover; it is the one moat factor scored from "
           "sourced node counts rather than qualitative reads."),
        _S("Does operating data improve future planning?",
           "Yes by construction — forecast accuracy grows with trip "
           "history, and multi-facility data enables comparisons no "
           "single hospital can make; this link needs no leap of "
           "faith."),
        _S("Does workflow integration increase retention?",
           "The incumbency evidence says integration holds accounts "
           "(60-year tenure, embedded coordinators, co-branding); "
           "whether retention follows measured performance or mere "
           "switching cost is not distinguishable from public data."),
        _S("Does customer expansion improve economics for both parties?",
           "It can — density gains are real and shareable — but the "
           "split depends on contract mechanics (rate resets, volume "
           "tiers); assume alignment only where the contract creates "
           "it."),
        _S("Does the model create a repeatable health-system playbook?",
           "A hypothesis with a supporting pattern: the embedded-partner "
           "playbook has been run by more than one operator (Superior, "
           "AMR), suggesting repeatability; MMT's own multi-state "
           "expansion is the live test, unproven publicly."),
        _S("Can the same model work across different geographies?",
           "Conditionally — the economics require density and labor "
           "supply, so the model transfers to metros with clustered "
           "nodes and inverts in thin rural corridors, where the "
           "exclusive contract, not density, is the moat."),
        _S("What could cause the strategic partnership to fail?",
           "Losing first-call at an anchor, a system insourcing or M&A "
           "flip (the Wichita Wesley→AMR move proves it happens), crew "
           "supply breaks (three FLSA suits mark the labor seam), a "
           "leveraged competitor buying share, or payment-policy shocks "
           "to the OON/commercial spread."),
        _S("What must MMT consistently execute to preserve its "
           "position?",
           "Reliability at the promised ETA band, the crew pipeline, "
           "data delivery with honest attribution, and 85%+ "
           "share-of-wallet at anchors — the moat is a combination of "
           "factors and decays wherever any one is dropped."),
    ),
)


Q10 = QuestionDef(
    num=10,
    slug="strategic",
    title="How does MMT help make transportation a strategic "
          "health-system capability?",
    storyline=(
        "The strategic case is a flywheel whose links carry different "
        "proof: demand data → forecasting → capacity → reliability is "
        "analytically solid; reliability → hospital flow is "
        "directionally supported by the DIDO/boarding/discharge "
        "literature; flow → deeper adoption is the partnership "
        "hypothesis — backed by incumbency evidence, proven nowhere "
        "publicly."),
    visual_key="flywheel",
    blocks=(_TRANSACTIONAL, _CAPACITY, _WORKFLOW, _PERFORMANCE, _OUTCOMES,
            _DURABILITY),
)


QUESTIONS = (Q9, Q10)
