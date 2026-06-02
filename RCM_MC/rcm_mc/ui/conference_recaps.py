"""Curated healthcare-conference recaps — the research layer behind the
Conference page.

A forward calendar tells a diligence team *where to be*; it doesn't tell them
*what happened* or *what it means*. This module is the "what happened" layer:
structured, sourced recaps of the big healthcare events (JPM, HLTH, HIMSS,
HFMA, Becker's, McGuireWoods HCPE, AHA, ViVE) — themes, notable announcements,
market impact, and the diligence read — plus the macro threads running across
them.

Architecture (per the product owner's call): this is **curated data, not
runtime scraping**. The PE Desk runtime is offline (no external network), so
recaps live here as a committed, reviewable data structure and the page reads
them directly. "Live-updatable" = edit/commit this file (optionally via an
offline refresh script that writes the same schema). Every recap carries real
source URLs; figures flagged as press-reported in research are labelled.

Each recap dict:
    id, name, edition, held, sentiment ∈ {bullish, optimistic, mixed,
    cautious, bearish}, sentiment_note, one_line, themes [(title, desc)],
    announcements [str], market_impact [str], diligence (str),
    sources [(title, url)].
"""
from __future__ import annotations

from typing import Dict, List

# Overall mood → editorial severity tone (drives the sentiment badge color).
SENTIMENT_TONE = {
    "bullish": "positive",
    "optimistic": "positive",   # "cautiously optimistic"
    "mixed": "warning",
    "cautious": "warning",
    "bearish": "negative",
}

# Macro threads running across the 2025→2026 events — the synthesis a partner
# should carry into underwriting. (title, body)
MACRO_THREADS: List[Dict[str, str]] = [
    {
        "title": "Policy overhang is the dominant downside risk",
        "body": (
            "Medicaid cuts, the end-2025 expiration of ACA enhanced premium "
            "tax credits, 340B uncertainty, and Medicare site-neutral threats "
            "recur from AHA 2025 through HLTH 2025 into JPM 2026 — all pressure "
            "provider payer mix, volumes, and bad debt. Model them as explicit "
            "downside scenarios in any provider underwriting."
        ),
    },
    {
        "title": "AI / RCM efficiency has crossed from hype to underwritable ROI",
        "body": (
            "Every event (JPM26, ViVE, HIMSS26, HLTH, HFMA) converged on AI as "
            "deployed infrastructure with measurable savings — especially in "
            "revenue cycle (Optum Real, Suki, R1, Epic's Penny / Agent Factory, "
            "the UC San Diego clean-claim case). Documented automation is now a "
            "legitimate value-creation lever — and EHR-native agents are a real "
            "threat to standalone healthtech."
        ),
    },
    {
        "title": "Deal pace is recovering but disciplined and rate-dependent",
        "body": (
            "McGuireWoods HCPE 2025 and JPM 2026 both describe abundant dry "
            "powder, a slow H1 2025, and expected acceleration as rates ease — "
            "channeled into smaller, targeted add-on / licensing deals and a "
            "flight to quality (with terms loosening down-market). Expect "
            "competitive auctions; hold entry-multiple discipline."
        ),
    },
    {
        "title": "Labor costs and care-site migration are reshaping provider economics",
        "body": (
            "Becker's 2025 and JPM 2026 flag easing-but-material labor pressure "
            "and a persistent nursing shortage alongside accelerating migration "
            "of volume to ambulatory / ASC / home / virtual settings — favoring "
            "behavioral health, home health, and ASC theses while pressuring "
            "inpatient-heavy and HOPD-dependent operators."
        ),
    },
]

CONFERENCE_RECAPS: List[Dict] = [
    {
        "id": "jpm-2026",
        "name": "J.P. Morgan Healthcare Conference",
        "edition": "2026 · 44th Annual",
        "held": "Jan 12–15, 2026 · San Francisco",
        "sentiment": "optimistic",
        "sentiment_note": (
            "Dealmaking is clearly on the upswing and capital-markets access "
            "improved, but the optimism is materializing through smaller, "
            "targeted, licensing-style deals — and Medicaid / ACA policy "
            "signals remain a visible overhang."
        ),
        "one_line": (
            "The industry's flagship investor gathering — the single best "
            "leading indicator of healthcare risk appetite, financing "
            "conditions, and sector rotation for the year."
        ),
        "themes": [
            ("AI from hype to ROI", "The conversation shifted from AI's potential to measurable impact — drug discovery, diagnostics, operational efficiency, and revenue cycle. AI is now table-stakes infrastructure, not a differentiator."),
            ("M&A momentum in smaller, targeted deals", "Renewed dealmaking via tuck-ins, licensing, and portfolio-shaping rather than megamergers — roughly $8.3B announced around the event."),
            ("GLP-1 / cardiometabolic broadening", "Obesity stayed front-and-center, moving beyond injectable GLP-1s to oral agents (e.g. Lilly's orforglipron), combinations, and long-term access."),
            ("Outpatient migration & AI in care", "Systems emphasized shifting care to ambulatory/ASC settings and using AI to enhance care, not just clerical tasks; labor-cost moderation helped margins."),
            ("Improved but stratified capital markets", "Funding reopened, skewed to later-stage names with validated data; the IPO window is reopening."),
        ],
        "announcements": [
            "AbbVie–RemeGen: ~$5.6B licensing for ex-China rights to RC148 (PD-1/VEGF bispecific) — kicked off the week.",
            "GSK–IDRx: acquisition of the oncology developer for up to $1.15B.",
            "Eli Lilly–Nvidia: ~$1B, five-year AI drug-discovery partnership / co-innovation lab.",
            "Lilly–Scorpion Therapeutics: ~$2.5B reported around JPM26 (press-reported, not company-confirmed).",
        ],
        "market_impact": [
            "Reopening (but stratified) capital markets + expected rate relief support higher deal volume into 2026 — favorable for sponsors holding aging portfolios seeking exits/refis.",
            "The 'smaller targeted deals' pattern makes platform-plus-add-on and licensing/carve-out theses more financeable than transformational LBOs right now.",
            "AI ROI focus raises the bar: buyers will underwrite documented efficiency (RCM automation, ambient documentation) over AI optionality.",
        ],
        "diligence": (
            "Calibrate the LBO's financing assumptions (rate path, debt "
            "availability, exit-multiple recovery) to JPM26, and weight "
            "AI-driven cost-out as provable bridge upside — not speculative "
            "optionality. Stress cardiometabolic-exposed assets for GLP-1 "
            "substitution on volumes."
        ),
        "sources": [
            ("Ballard Spahr — JPM 2026 Recap and What to Watch", "https://www.ballardspahr.com/insights/alerts-and-articles/2026/02/jp-morgan-healthcare-conference-2026-recap-and-what-to-watch"),
            ("J.P. Morgan — Five trends shaping healthcare in 2026", "https://www.jpmorgan.com/insights/banking/investment-banking/health-care-conference-2026-trends"),
            ("Morgan Lewis — Key Takeaways from the 2026 JPM Conference", "https://www.morganlewis.com/blogs/asprescribed/2026/01/key-takeaways-from-the-2026-jp-morgan-healthcare-conference"),
            ("BioSpace — Deals Roll at JPM26, Policy Front and Center, IPOs Are Back", "https://www.biospace.com/business/deals-roll-at-jpm26-policy-front-and-center-ipos-are-back-fda-stays-busy"),
        ],
    },
    {
        "id": "hlth-2025",
        "name": "HLTH USA",
        "edition": "2025",
        "held": "Oct 19–22, 2025 · Las Vegas",
        "sentiment": "mixed",
        "sentiment_note": (
            "Genuine momentum on AI moving 'from potential to practical' and a "
            "wave of partnerships, set against heavy macro anxiety: rising "
            "costs, Medicaid coverage losses, and the looming end-2025 ACA "
            "enhanced-subsidy expiration."
        ),
        "one_line": (
            "The marquee health-innovation event — where venture and strategic "
            "capital signal which consumer/payer-facing categories are heating "
            "up."
        ),
        "themes": [
            ("AI from potential to practical", "60+ announcements and 40+ partnerships, with clear movement toward deployed, workflow-embedded use — especially RCM and claims."),
            ("RCM / claims automation & payer-provider plumbing", "Major focus on automating prior auth, denials, and adjudication by connecting payer cores to provider EHRs."),
            ("Women's health as an investable category", "Significant main-stage attention and capital, especially menopause/perimenopause and family-building."),
            ("ACA-subsidy & Medicaid overhang", "Explicit alarm that expiring ACA credits and Medicaid losses could strip coverage from millions — a direct demand/volume risk."),
        ],
        "announcements": [
            "Optum Real: AI real-time claims platform connecting payer cores + provider EHRs; UnitedHealthcare & Allina piloting (5,000+ visits processed).",
            "Suki: ambient AI extended to auto-generate billing codes, collaborating with Optum Real on documentation↔RCM.",
            "R1 + Heidi: RCM teamed with the AI scribe (per Fierce Healthcare).",
            "Oscar Health + Elektra Health 'HelloMeno': first menopause-focused ACA individual-market plan.",
        ],
        "market_impact": [
            "RCM-automation announcements validate a large, near-term cost-out opportunity in provider operations — directly relevant to provider-services and RCM-vendor theses.",
            "The ACA-subsidy / Medicaid overhang is a concrete downside to self-pay/exchange-exposed volumes and bad-debt assumptions into 2026.",
            "Payer-led AI (UnitedHealth/Optum) concentrating RCM infrastructure pressures independent RCM vendors' competitive position.",
        ],
        "diligence": (
            "Stress any provider or exchange-exposed target for ACA-subsidy "
            "expiration and Medicaid-disenrollment volume/bad-debt risk, and "
            "benchmark its RCM performance against the automation results "
            "(Optum Real, Suki, R1) now setting the efficiency bar."
        ),
        "sources": [
            ("Fierce Healthcare — Optum Real & Suki, R1 + Heidi", "https://www.fiercehealthcare.com/ai-and-machine-learning/optum-real-and-suki-build-out-collaboration-r1-teams-heidi-link-ai-scribe"),
            ("MedCity News — 7 HLTH Announcements You Don't Want to Miss", "https://medcitynews.com/2025/10/hlth-conference/"),
            ("Digital Health Wire — HLTH 2025 Recap and Major Announcements", "https://digitalhealthwire.com/hlth-2025-recap-and-major-announcements/"),
        ],
    },
    {
        "id": "hcpe-2025",
        "name": "McGuireWoods Healthcare PE & Finance (HCPE)",
        "edition": "2025 · 21st Annual",
        "held": "May 13–15, 2025 · Chicago",
        "sentiment": "optimistic",
        "sentiment_note": (
            "'Cautious optimism': a slower-than-expected H1 2025 on macro/"
            "political uncertainty and middle-market liquidity constraints, but "
            "ample dry powder and expectations for a stronger H2 as rates ease."
        ),
        "one_line": (
            "The most directly relevant event on the calendar — a healthcare-PE-"
            "and-lender-specific summit that sets the deal-flow, leverage, and "
            "valuation tone for healthcare services."
        ),
        "themes": [
            ("Slow start, expected H2 acceleration", "H1 2025 ran below expectations (mostly refis + add-ons); anticipated rate cuts seen as the catalyst to unlock sponsor-backed M&A."),
            ("Abundant capital, competitive terms", "Plenty of capital ready to deploy is driving competition for quality deals; more aggressive terms creeping down-market."),
            ("Hot vs. cold subsectors", "Capital rotating away from operationally-complex, real-estate-heavy, regulated sectors toward behavioral health and home health."),
            ("Patient engagement / eHealth most active", "22 patient-engagement transactions in the first four months of 2025 — the most active eHealth subsector."),
            ("Regulatory & reimbursement headwinds", "State transaction-notice / PE-disclosure laws and reimbursement pressure cited as concrete drags on deal velocity."),
        ],
        "announcements": [
            "Trend data point: 22 patient-engagement deals in the first 4 months of 2025 (most active eHealth subsector).",
            "Valuation context from coverage: home-health ~4–8x EBITDA; behavioral-health platforms ~9–15x (general market ranges, not podium figures).",
        ],
        "market_impact": [
            "The hot/cold rotation is a direct steer: behavioral health & home health carry tailwinds; real-estate/regulatory-heavy sectors face capital flight and likely multiple compression.",
            "Aggressive terms + dry powder imply competitive auctions and full pricing for quality assets — discipline on entry multiples matters.",
            "State PE-transaction-notice and reimbursement regimes are now a material gating/timeline risk to build into deal calendars.",
        ],
        "diligence": (
            "Map each target to the hot/cold subsector rotation, diligence "
            "state PE-transaction-notice / reimbursement exposure, and "
            "benchmark entry multiples against the behavioral-health (~9–15x) "
            "and home-health (~4–8x) ranges — avoid overpaying into loosening "
            "auctions."
        ),
        "sources": [
            ("McGuireWoods — Insights from the 21st HCPE Conference, Part 2: State of the Market", "https://www.mcguirewoods.com/client-resources/alerts/2025/6/insights-from-mcguirewoods-hcpe-conference-part-2-state-of-the-market/"),
            ("Levin Associates — Key Trends at the McGuireWoods 21st HCPE Conference", "https://www.levinassociates.com/key-trends-at-the-mcguirewoods-21st-annual-healthcare-private-equity-and-finance-conference/"),
        ],
    },
    {
        "id": "himss-2026",
        "name": "HIMSS Global Health Conference",
        "edition": "2026",
        "held": "Mar 9–12, 2026 · Las Vegas",
        "sentiment": "optimistic",
        "sentiment_note": (
            "Strong consensus that healthcare is 'moving beyond the AI hype "
            "cycle' toward scaled, accountable deployment — tempered by candid "
            "concern that clinicians lack benchmarks to judge AI safety and "
            "effectiveness."
        ),
        "one_line": (
            "The largest health-IT conference — it dictates the infrastructure, "
            "interoperability, and AI-governance environment portfolio "
            "healthtech and providers must operate in."
        ),
        "themes": [
            ("Agentic AI from demo to deployment", "The dominant theme — AI agents that reason and act across workflows, with vendors shipping orchestration platforms, not single models."),
            ("From pilot purgatory to production scale", "Organizations interrogating tangible, measurable value beyond chatbots — moving from experiments to accountable production use."),
            ("AI governance, benchmarks & safety gap", "Repeated acknowledgment that clinicians lack standardized benchmarks to assess AI performance."),
            ("Evolving FDA posture", "Regulators signaled lighter pre-market review with heavier post-market, real-world monitoring of AI tools."),
        ],
        "announcements": [
            "Epic 'Agent Factory': no-code platform to build/customize/monitor AI agents, with personas for clinical documentation, RCM, and patient engagement.",
            "Epic 'Curiosity': medical foundation models trained on de-identified records to predict patient journeys.",
            "Epic stated 85%+ of its customer base is now actively using its AI tools.",
            "Summit Health cited a 42% cut in prior-authorization submission time using Epic's revenue-cycle AI (Penny).",
        ],
        "market_impact": [
            "Epic's Agent Factory / Curiosity push concentrates AI capability inside the dominant EHR — a competitive headwind for standalone healthtech (especially RCM/documentation).",
            "Documented RCM gains (e.g. 42% faster prior auth) make RCM-automation upside more underwritable in provider value-creation bridges.",
            "Post-market FDA oversight lowers time-to-market for AI tools but raises ongoing compliance/monitoring cost.",
        ],
        "diligence": (
            "For any healthtech / RCM target, explicitly test 'Epic risk' — "
            "whether the EHR's native agents could absorb the target's function "
            "— and weight RCM-automation savings using production results, not "
            "vendor demos."
        ),
        "sources": [
            ("Healthcare Dive — 5 takeaways from HIMSS26", "https://www.healthcaredive.com/news/himss-2026-takeaways-ai-innovation-agents-cybersecurity-governance-interoperability/814812/"),
            ("Fierce Healthcare — Epic previews Agent Factory at HIMSS26", "https://www.fiercehealthcare.com/ai-and-machine-learning/himss26-epic-expands-ai-roadmap-previews-factory-build-and-orchestrate-ai"),
            ("HIT Consultant — Epic 'Agent Factory' and Custom Models", "https://hitconsultant.net/2026/03/10/epic-ai-himss-2026-agent-factory-curiosity-foundation-models/"),
        ],
    },
    {
        "id": "hfma-2025",
        "name": "HFMA Annual / Revenue Cycle Conference",
        "edition": "2025",
        "held": "Mid-2025",
        "sentiment": "optimistic",
        "sentiment_note": (
            "Practitioners energized by AI/automation delivering tangible RCM "
            "value, but operating under sustained financial pressure, a denials "
            "burden, and a demand for proven ROI before buying."
        ),
        "one_line": (
            "The premier gathering of hospital CFOs and revenue-cycle leaders — "
            "the clearest read on provider financial operations and the realism "
            "of margin-improvement plans."
        ),
        "themes": [
            ("RCM automation: AI from theory to tangible value", "AI moving to measurable results — payment posting, intelligent categorization; ambient-listening and agentic-AI sessions were standing-room-only."),
            ("Holistic financial/operational transformation", "Tactical fixes no longer enough; sustainable performance requires redesigning how finance and operations work together."),
            ("Denials management", "Denials top-of-mind; heavy demand for automation to cut manual rework and improve outcomes."),
            ("Vendor consolidation / proven ROI", "Buyers want demonstrated ROI and prefer extending existing vendor relationships over adding point solutions."),
        ],
        "announcements": [
            "UC San Diego Health case study: clean-claim rate 93% → 97.6% and point-of-service collections up $2M+ in one year via structured technology adoption — a citable RCM-automation ROI proof point.",
        ],
        "market_impact": [
            "Validates RCM automation as a real, quantifiable margin lever — strengthens RCM-driven value-creation bridges in provider deals.",
            "The 'proven ROI / vendor consolidation' posture means longer sales cycles + consolidation pressure for RCM-vendor targets — underwrite slower new-logo growth.",
            "Persistent denials + transparency pressure raise both operating cost and compliance considerations for operators.",
        ],
        "diligence": (
            "For provider or RCM-vendor targets, benchmark KPIs (clean-claim %, "
            "denial rate, POS collections, cost-to-collect) against UC San "
            "Diego-type results, and validate that modeled RCM savings are "
            "backed by reference-customer ROI, not vendor marketing."
        ),
        "sources": [
            ("HealthLeaders — Top 3 Themes at the 2025 HFMA Revenue Cycle Conference", "https://www.healthleadersmedia.com/revenue-cycle/infographic-top-3-themes-we-followed-2025-hfma-revenue-cycle-conference"),
            ("AAPC — HFMA 2025: Three Critical Takeaways for Revenue Cycle", "https://www.aapc.com/resources/hfma-2025-three-critical-takeaways-and-the-path-forward-for-revenue-cycle"),
        ],
    },
    {
        "id": "beckers-2025",
        "name": "Becker's Hospital Review Annual Meeting",
        "edition": "2025 · 15th Annual",
        "held": "Apr 28–May 1, 2025 · Chicago",
        "sentiment": "optimistic",
        "sentiment_note": (
            "A theme of 'momentum' and bold transformation, but framed around "
            "doing more under sustained financial pressure and acute workforce "
            "strain; leaders are narrowing priorities and demanding disciplined "
            "execution."
        ),
        "one_line": (
            "The largest convening of hospital and health-system operators "
            "(C-suite) — how operators are actually managing margins, labor, "
            "AI, and M&A appetite."
        ),
        "themes": [
            ("Strategic focus & disciplined execution", "CEOs narrowing to fewer priorities, aligning strategy, operations, and culture; several building '2030' plans."),
            ("AI: hype to operational use + partnerships", "Systems increasingly buy/partner rather than build for AI, virtual care, and RCM."),
            ("Workforce sustainability & burnout", "Persistent nursing shortage and burnout; travel-nurse contracts straining budgets (a projection of ~1.6M nurses intending to leave by 2029 was cited)."),
            ("Care-delivery beyond the hospital", "Shift of care to ambulatory, home, and virtual settings."),
        ],
        "announcements": [
            "Operator-strategy / education event — themes over named transactions; the signal is operators' embrace of 'buy/partner, don't build.'",
        ],
        "market_impact": [
            "Operators' 'partner, don't build' posture for AI/virtual care/RCM expands the addressable market for healthtech and services-enablement vendors.",
            "Workforce shortage + travel-nurse cost is a structural operating-cost risk for hospital and staffing targets (and a tailwind for workforce-tech).",
            "Care migration supports ASC, home-health, and virtual-care theses while pressuring inpatient-heavy operators.",
        ],
        "diligence": (
            "Pressure-test labor-cost assumptions (travel-nurse exposure, "
            "nursing attrition) and confirm whether a target is a beneficiary "
            "or victim of care migration; for healthtech, expect disciplined, "
            "ROI-gated procurement."
        ),
        "sources": [
            ("Healthmonix — A narrative from Becker's 2025 annual meeting", "https://blog.healthmonix.com/becker-2025-healthcare-transformation-highlights"),
            ("Becker's — Reimagining the hospital workforce", "https://www.beckershospitalreview.com/strategy/reimagining-the-hospital-workforce-the-next-era-of-care-delivery/"),
        ],
    },
    {
        "id": "vive-2026",
        "name": "ViVE",
        "edition": "2026",
        "held": "Feb 2026 · Los Angeles",
        "sentiment": "mixed",
        "sentiment_note": (
            "Real enthusiasm that AI is moving from experimentation into "
            "execution, tempered by 'anxiety' over change management, data "
            "quality, and ROI proof."
        ),
        "one_line": (
            "The digital-health buyer-meets-startup event — it reveals which "
            "healthtech categories have real provider/payer demand vs. fading "
            "hype."
        ),
        "themes": [
            ("AI from experimentation to implementation", "Ambient scribe tools are now everywhere; focus shifted to solutions that work inside real clinical/operational workflows."),
            ("Data infrastructure as the foundation", "Underneath the AI talk, the recurring requirement was scalable platforms integrating EHR, claims, and third-party data."),
            ("Change management is the real bottleneck", "The hardest part of transformation is adoption, not technology — 'build with clinicians, not for them.'"),
            ("Security as executive-level strategy", "Cybersecurity reframed as company-wide risk, not just an IT line item."),
        ],
        "announcements": [
            "A thematic/partnership event — no specific named blockbuster deals were verifiable as uniquely attributable to ViVE 2026 (themes above are well-sourced).",
        ],
        "market_impact": [
            "Confirms durable demand for ambient documentation and RCM-adjacent automation — supports revenue-quality theses for those categories.",
            "'Change management as the bottleneck' implies healthtech revenue ramps may be slower than ARR projections — underwrite adoption risk.",
            "Data-infrastructure centrality favors platform/integration ('picks-and-shovels') assets over single-point AI apps.",
        ],
        "diligence": (
            "For healthtech / services-enablement targets, validate net revenue "
            "retention and time-to-value against the 'change-management is the "
            "hard part' reality, and discount AI feature claims lacking "
            "documented workflow adoption and reference-customer ROI."
        ),
        "sources": [
            ("Chief Healthcare Executive — ViVE 2026 Takeaways", "https://www.chiefhealthcareexecutive.com/view/vive-2026-takeaways-ai-hope-anxiety-and-tackling-real-problems"),
            ("Healthcare IT Today — ViVE 2026: The Conversations That Mattered", "https://www.healthcareittoday.com/2026/02/26/vive-2026-part-1-the-conversations-that-mattered/"),
        ],
    },
    {
        "id": "aha-2025",
        "name": "AHA Annual Membership Meeting",
        "edition": "2025",
        "held": "May 4–6, 2025 · Washington, D.C.",
        "sentiment": "cautious",
        "sentiment_note": (
            "Dominated by defensive advocacy against potentially 'devastating' "
            "Medicaid cuts and other reimbursement threats — the framing was "
            "protecting access and preventing destabilization, not growth."
        ),
        "one_line": (
            "The hospital field's flagship policy gathering in D.C. — the "
            "clearest signal of the reimbursement and policy overhang that will "
            "move hospital/provider valuations."
        ),
        "themes": [
            ("Medicaid-cut overhang (top priority)", "AHA urged Congress to reject billions in Medicaid reductions, warning of service terminations/closures, especially at safety-net providers."),
            ("ACA enhanced premium tax credits expiring", "Push to extend the enhanced subsidies set to lapse at end of 2025 — a direct coverage/volume issue."),
            ("340B Drug Pricing Program defense", "Preserving 340B savings (critical to many hospitals' economics) was a core priority."),
            ("Opposing Medicare site-neutral payments", "Resisting policies that would cut hospital outpatient reimbursement."),
        ],
        "announcements": [
            "A policy/advocacy meeting — the substantive items are the AHA's positions: reject Medicaid cuts, extend ACA credits, protect 340B, oppose site-neutral payments.",
        ],
        "market_impact": [
            "Medicaid cuts + ACA-subsidy expiration are the single biggest downside macro risks to hospital volumes, payer mix, and bad debt into 2026.",
            "Site-neutral threats specifically compress hospital outpatient-department economics (a relative tailwind for independent ASCs).",
            "340B uncertainty is a real earnings-quality risk for hospitals relying on 340B margins.",
        ],
        "diligence": (
            "Treat AHA's 2025 priority list as a downside-scenario checklist: "
            "stress provider targets for Medicaid-cut and ACA-subsidy-expiration "
            "exposure (payer mix, self-pay/bad-debt), HOPD site-neutral risk, "
            "and 340B dependence in the EBITDA-bridge sensitivities."
        ),
        "sources": [
            ("AHA — Uniting to Protect Access to Care", "https://www.aha.org/news/perspective/2025-05-09-uniting-protect-access-care-patients-and-communities"),
            ("AHA — 2025 Annual Meeting Advocacy Messages", "https://www.aha.org/advocacy/aha-annual-membership-meeting-2025-advocacy-messages-card"),
        ],
    },
]


def recap_by_id() -> Dict[str, Dict]:
    return {r["id"]: r for r in CONFERENCE_RECAPS}
