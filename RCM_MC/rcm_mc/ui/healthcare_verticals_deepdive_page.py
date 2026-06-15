"""Healthcare Verticals & Life-Sciences deep-dive page.

Surfaces the 15-vertical sector-intelligence brief
(docs/PEDESK_HEALTHCARE_VERTICALS_LIFE_SCIENCES.md) as an editorial
research page: ten provider/therapy/ancillary verticals plus the
five-segment life-sciences "drug-dollar" layer. Each card carries
chart-ready billing codes, the headline epidemiology/scale figure,
the 2025/2026 reimbursement hook, and the named primary datasets so
a partner can trace every number back to its source.

Static reference content (no DB, no network) — it is the planning
surface that sits under PEDESK_SECTOR_INTELLIGENCE_ROADMAP.md for the
next round of vertical expansion.
"""
from __future__ import annotations

import html
from typing import Dict, List

from ._chartis_kit import (
    chartis_shell, ck_editorial_head, ck_fmt_num, ck_kpi_block,
    ck_next_section, ck_page_actions,
)
from .brand import PALETTE


# Cross-cutting 2025/2026 reimbursement anchors — the levers that reshape
# every PFS-driven provider vertical. Sourced from CMS CY2026 final rules.
_ANCHORS: List[Dict[str, str]] = [
    {
        "name": "2026 PFS conversion factors",
        "detail": (
            "$33.5675 (qualifying-APM) and $33.4009 (non-qualifying), up from "
            "the single 2025 CF of $32.3465 (+3.77% / +3.26%). Includes a 2.5% "
            "one-year OBBBA increase plus a -2.5% efficiency adjustment applied "
            "to non-time-based codes."
        ),
        "source": "CMS-1832-F, Oct 31 2025",
    },
    {
        "name": "Skin substitutes / CTPs reclassified",
        "detail": (
            "Non-BLA skin substitutes move from ASP+6% biologicals to "
            "incident-to supplies effective Jan 1 2026 at a single national "
            "rate: $127.28/cm² under PFS, $127.14/cm² under OPPS. Discarded "
            "product not payable; CMS projects ~$19B PFS savings in 2026. Three "
            "FDA-based APCs created (6000 PMA, 6001 510(k), 6002 361 HCT/P)."
        ),
        "source": "CMS CY2026 final rule (National Law Review, Nov 5 2025)",
    },
    {
        "name": "CLFS / PAMA cuts delayed",
        "detail": (
            "No lab fee-schedule cuts in 2026; up-to-15%/yr cuts delayed to "
            "2027-2029. New data collection Jan 1 - Jun 30 2025, reporting "
            "May 1 - Jul 31 2026."
        ),
        "source": "CAA 2026 §6226",
    },
    {
        "name": "2026 OPPS / ASC update",
        "detail": (
            "Payment rates up 2.6%; rules affect ~4,000 hospitals and ~6,000 "
            "ASCs."
        ),
        "source": "CMS-1834-FC, Nov 21 2025",
    },
    {
        "name": "Drug-spend context",
        "detail": (
            "US market at net prices grew 11.4% in 2024 to $487 billion, with "
            "specialty medications accounting for $262 billion (53% of net "
            "sales)."
        ),
        "source": "IQVIA Institute, Use of Medicines in the U.S. 2025 (Apr 2025)",
    },
]


# The fifteen verticals. group A = provider/therapy/ancillary (PFS-driven);
# group B = specialty-pharmacy / life-sciences drug-dollar layer.
_VERTICALS: List[Dict[str, str]] = [
    # ---- Group A ---------------------------------------------------------
    {
        "group": "A",
        "name": "Physical, Occupational & Speech Therapy",
        "tag": "Outpatient rehab",
        "codes": (
            "Timed CPT 97110/97112/97116/97140/97530; evals 97161-97168; "
            "SLP 92507/92610/92526. Taxonomy 225100000X / 225X00000X / "
            "235Z00000X."
        ),
        "scale": (
            "PTs ~253,300 jobs (median $101,020); OTs ~162,000; SLPs median "
            "$95,410 (BLS OOH 2024)."
        ),
        "reimb": (
            "PFS. 2026 CF $33.4009. The -2.5% efficiency adjustment exempts "
            "time-based codes, so therapy is relatively insulated. 2025 "
            "KX-modifier threshold $2,330 (PT+SLP) / $2,330 (OT)."
        ),
        "sources": "CMS PFS; Benefit Policy Manual Ch. 15; APTA; BLS OES.",
        "charts": "Bar (visit economics by CPT); 100% stacked (timed vs untimed); line (cap threshold).",
    },
    {
        "group": "A",
        "name": "Chiropractic Care",
        "tag": "Covered vs cash-pay",
        "codes": (
            "Medicare covers only 98940/98941/98942 (CMT, AT modifier "
            "required); 98943 not covered. Primary ICD-10 must be M99.0x."
        ),
        "scale": (
            "~50,000 chiropractors (median ~$78,410; headcount needs BLS "
            "verification). Large cash-pay/wellness market outside Medicare."
        ),
        "reimb": (
            "Covered/non-covered split is the defining feature: Medicare pays "
            "only spinal manipulation for an active subluxation; maintenance, "
            "X-rays, E/M and therapies are cash-pay. One CMT code per day."
        ),
        "sources": "CMS LCD/Article A56273; MLN SE1601; ACA.",
        "charts": "Stacked bar (covered vs cash-pay); bar (CMT code distribution).",
    },
    {
        "group": "A",
        "name": "Podiatry",
        "tag": "Routine vs medically-necessary",
        "codes": (
            "Routine foot care 11055-11057 / 11719-11721 / G0127 / G0247. Q7/Q8/Q9 "
            "modifiers mandatory; ICD-10 E11.621, B35.1, G60.x. Surgical 20610, "
            "28810/28820."
        ),
        "scale": (
            "~37M Americans have diabetes; ~1.6M diabetic foot ulcers/yr; "
            "lifetime DFU risk 19-34%. ~9,700 DPMs (median $152,800)."
        ),
        "reimb": (
            "PFS. Routine foot care excluded unless a qualifying systemic "
            "condition (diabetes w/ neuropathy/PVD) is documented with class "
            "findings; capped ~once/60 days."
        ),
        "sources": "CMS LCD A57759/A56232; CDC; APMA; ADA Diabetes Care; JAMA (PMID 37395769).",
        "charts": "Funnel (diabetes -> neuropathy -> DFU -> amputation); bar (RVU by code).",
    },
    {
        "group": "A",
        "name": "Plastic Surgery & Medical Aesthetics",
        "tag": "Reconstructive vs cosmetic",
        "codes": (
            "Cosmetic (cash): J0585 botulinum toxin, fillers, 15780s, 15834+, "
            "17106-17108. Reconstructive (insured): 19357, 15734, 14000-series."
        ),
        "scale": (
            "US aesthetic injectable market ~$4.1B (2024); ~4.7M botox "
            "procedures (2023); med spas ~47.3% of injectable delivery; avg med "
            "spa >$1.9M/yr."
        ),
        "reimb": (
            "Reconstructive procedures insured under PFS/OPPS; cosmetic is "
            "fully cash-pay with no third-party reimbursement - the defining "
            "payer split."
        ),
        "sources": "ASPS; ISAPS; AmSpa; Grand View Research (market sizes approximate).",
        "charts": "Stacked bar (procedure mix); line (injectable growth); bar (cash-pay economics).",
    },
    {
        "group": "A",
        "name": "Sleep Medicine",
        "tag": "In-lab PSG vs home HSAT",
        "codes": (
            "In-lab PSG 95810/95811/95808; HSAT 95800/95801/95806 + "
            "G0398-G0400; CPAP/DME E0601, E0470/E0471, A7030. ICD-10 G47.33."
        ),
        "scale": (
            "OSA prevalence: 54M+ US adults 30-69 (33.2%) previously estimated; "
            "a 2024 estimate puts adult OSA at 83.7M (32.4%). Historically "
            "underdiagnosed."
        ),
        "reimb": (
            "PSG/HSAT professional + technical paid under PFS; CPAP DME under "
            "DMEPOS with adherence documented in the first 90 days. Strong payer "
            "push toward lower-cost HSAT."
        ),
        "sources": "AASM; USPSTF (NBK588761); CMS NCD CAG-00405N; CDC.",
        "charts": "100% stacked (PSG vs HSAT); funnel (dx -> tx -> adherence); bar (OSA severity).",
    },
    {
        "group": "A",
        "name": "Wound Care",
        "tag": "CTP flat-rate overhaul",
        "codes": (
            "Debridement 11042-11047, 97597/97598; skin-substitute application "
            "15271-15278 (C5271-C5278 deleted for 2026); HBOT 99183/G0277. "
            "ICD-10 E11.621, L97.x, L89.x."
        ),
        "scale": (
            "~15% of Medicare beneficiaries (8.2M) had a wound/infection; "
            "conservative cost $28.1-$31.7B/yr. >50% of DFUs infect, ~20% lead "
            "to amputation."
        ),
        "reimb": (
            "The headline 2026 disruption: non-BLA skin substitutes flat-rated "
            "at $127.28/cm² (PFS) / $127.14/cm² (OPPS); wastage not payable; "
            "~$19B projected savings. BLA (§351) products stay on ASP+6%. Spurred "
            "by the DOJ 2025 $1.1B amniotic-allograft fraud takedown."
        ),
        "sources": "CMS PFS/OPPS final rules; Alliance of Wound Care Stakeholders; MedPAC; Nussbaum et al. (PMID 29304937).",
        "charts": "Waterfall (CTP before/after 2026); funnel (wound -> infection -> amputation); line (CTP spend).",
    },
    {
        "group": "A",
        "name": "Allergy & Immunology",
        "tag": "Antigen prep + biologics",
        "codes": (
            "Testing 95004/95017/95024/86003; immunotherapy 95165 (antigen "
            "prep), 95115/95117; biologics J2357, J2182, J0517, J2786, "
            "dupilumab. ICD-10 J30.x, J45.x, L20.x."
        ),
        "scale": (
            "Allergic rhinitis affects ~400M worldwide and is highly prevalent "
            "in the US; AIT is the only disease-modifying therapy for allergic "
            "respiratory disease."
        ),
        "reimb": (
            "PFS for testing and immunotherapy; biologics under Part B ASP+6% "
            "(buy-and-bill) or pharmacy benefit. 95165 antigen prep is a "
            "recurring revenue stream."
        ),
        "sources": "CMS PFS; AAAAI; ACAAI; JACI/JCAAI.",
        "charts": "Bar (testing vs IT vs biologics); funnel (testing -> IT -> maintenance).",
    },
    {
        "group": "A",
        "name": "Clinical Laboratories & Pathology",
        "tag": "PAMA / CLFS exposure",
        "codes": (
            "Chemistry 80053/80048/85025/80061/83036; molecular 81479, PLA "
            "0xxxU, 81455; pathology 88305/88307/88309, 88341/88342. Pathology "
            "splits -26 (professional) / -TC (technical)."
        ),
        "scale": (
            "~13.3-14B clinical lab tests/yr; ~70% of medical decisions rely on "
            "labs. ~320,000 CLIA entities; ~351,200 lab tech jobs (median "
            "$61,890)."
        ),
        "reimb": (
            "CDLTs paid on CLFS at the weighted-median of private-payor rates. "
            "No 2026 cuts; up-to-15%/yr cuts delayed to 2027-2029. ~820 tests "
            "face cuts absent reform (RESULTS Act)."
        ),
        "sources": "CMS CLFS; ACLA; NILA; CDC CLIA.",
        "charts": "Bar (test volume by category); line (CLFS cuts timeline); stacked (prof vs tech).",
    },
    {
        "group": "A",
        "name": "Emergency Medical Services / Ambulance",
        "tag": "Surprise-billing carve-out",
        "codes": (
            "Ground A0425-A0434; air A0430/A0431, A0435/A0436. "
            "Origin/destination modifiers (R, H, S)."
        ),
        "scale": (
            "~3M privately-insured emergency ground transports/yr; ~13,000 "
            "providers (4 in 5 carry <1,000 Medicare trips/yr) - highly "
            "fragmented."
        ),
        "reimb": (
            "Uniquely exposed: ground ambulances were EXCLUDED from the No "
            "Surprises Act. 28-50% of rides produce OON/surprise bills (median "
            "~$450); 22 states now have some protection; ERISA plans remain "
            "outside state authority. Paid under the Medicare Ambulance Fee "
            "Schedule."
        ),
        "sources": "CMS Ambulance Fee Schedule; GAPB report; Commonwealth Fund; American Ambulance Association.",
        "charts": "Bar (reimbursement by level); map (state protections); bar (OON rate by state).",
    },
    {
        "group": "A",
        "name": "IRF, LTACH & PACE",
        "tag": "Post-acute capitation",
        "codes": (
            "IRF-PPS (CMGs from IRF-PAI, 60% Rule); LTCH-PPS (MS-LTC-DRGs, "
            "site-neutral); PACE fully-capitated PMPM (Parts A/B/D + Medicaid)."
        ),
        "scale": (
            "IRFs ~1,180 (stroke ~21.8% of cases); PACE 178 programs by Dec "
            "2024, 80,815 enrolled Jan 1 2025 (~90% dual-eligible)."
        ),
        "reimb": (
            "IRF FFS Medicare ~$11.0B, margin ~13.7%. FY2026 LTACH PPS +2.7%. "
            "PACE Medicare capitation averages ~20% more per beneficiary than "
            "comparable MA plans."
        ),
        "sources": "CMS IRF-PPS/LTCH-PPS final rules; MedPAC Ch. 8/9; National PACE Association; NORC; MACPAC.",
        "charts": "Line (PACE enrollment); bar (IRF case-mix); bar (post-acute margins).",
    },
    # ---- Group B ---------------------------------------------------------
    {
        "group": "B",
        "name": "Specialty Pharmacy",
        "tag": "53% of net drug sales",
        "codes": (
            "NDC-driven dispensing; J-codes for provider-administered "
            "specialty; NCPDP claims standards. Accreditation URAC / ACHC."
        ),
        "scale": (
            "Specialty = $262B, 53% of US net drug sales (2024). US dispensing "
            "revenue ~$265B (2024, DCI). ~1,749-1,900 accredited locations (~3% "
            "of pharmacies)."
        ),
        "reimb": (
            "Mix of pharmacy benefit (PBM-adjudicated) and medical benefit "
            "(ASP+6% buy-and-bill). Big-three PBM-affiliated specialty "
            "pharmacies (Accredo, CVS Specialty, Optum Specialty) hold ~2/3 of "
            "specialty Rx revenue. Gross-to-net erosion dominant."
        ),
        "sources": "Drug Channels Institute; IQVIA Use of Medicines; CMS.",
        "charts": "Line (specialty spend); treemap (market share); waterfall (gross-to-net).",
    },
    {
        "group": "B",
        "name": "Pharmacy Benefit Managers (PBMs)",
        "tag": "80% claim concentration",
        "codes": (
            "Formulary management, rebate negotiation, spread pricing, network "
            "contracting, claims adjudication, mail/specialty dispensing."
        ),
        "scale": (
            "Big-three (CVS Caremark, Express Scripts, Optum Rx) processed 80% "
            "of equivalent claims in 2025. 2025 shares: Express Scripts 31%, "
            "CVS Caremark 26%, Optum Rx 23%. Five of six largest are "
            "insurer-owned."
        ),
        "reimb": (
            "Economics: rebate retention, spread pricing, DIR fees. Optum Rx "
            "managed $188B in 2025 drug spend (46% specialty). Under FTC "
            "antitrust and transparency pressure."
        ),
        "sources": "Drug Channels Institute 2026 Economic Report; AMA Policy Research Perspectives; FTC; JAMA.",
        "charts": "Stacked bar / treemap (PBM share); line (share shift 2023 -> 2025).",
    },
    {
        "group": "B",
        "name": "CROs & CDMOs",
        "tag": "Outsourced R&D + manufacturing",
        "codes": (
            "CROs: Phase I-IV trial services, biostatistics, pharmacovigilance, "
            "regulatory. CDMOs: contract development + manufacturing (API, drug "
            "product, biologics)."
        ),
        "scale": (
            "Global CRO market ~$80-86B (2024); 5,318 trials started in 2024 "
            "(oncology/immunology/neuro/CV = 71%); R&D funding hit $102B "
            "(2024); >50% of sponsor budgets outsourced."
        ),
        "reimb": (
            "Not government-reimbursed: fee-for-service / FSP / milestone "
            "pricing. Book-to-bill ~1.2-1.3x. Phase costs ~$4M (I), $13M (II), "
            "$20M (III); only ~12% of trialed drugs gain FDA approval."
        ),
        "sources": "IQVIA Global Trends in R&D; Contract Pharma; SEC filings; ClinicalTrials.gov (sizes approximate).",
        "charts": "Line (CRO market growth); bar (trial starts by area); bar (phase costs).",
    },
    {
        "group": "B",
        "name": "GPOs & the 340B Program",
        "tag": "$81.4B, +22.8%",
        "codes": (
            "GPOs funded by vendor admin fees (≤3% safe harbor; actual ~1.22-"
            "2.25%). 340B: statutory manufacturer discount on outpatient drugs "
            "to covered entities."
        ),
        "scale": (
            "340B purchases hit $81.4B in 2024 (+22.8% over $66.3B); CAGR 23.5% "
            "(2015-2024). Hospitals = 87% of purchases. Vizient/Premier/"
            "HealthTrust control ~75% of GPO spend."
        ),
        "reimb": (
            "List-to-340B gap (entity benefit) ~$66.4B (2024). IRA pressure "
            "expected to slow growth from 2026. CMS will survey hospital "
            "acquisition costs, likely lowering future 340B reimbursement."
        ),
        "sources": "HRSA OPA; Drug Channels Institute; GAO; Minnesota DOH; MedPAC; CBO; NPC.",
        "charts": "Line (340B growth); bar (purchases by entity); waterfall (list-to-340B gap).",
    },
    {
        "group": "B",
        "name": "Infusion Pharmacy / Home Infusion",
        "tag": "Site-of-care shift",
        "codes": (
            "Per-diem S-codes S9325-S9379 (S9494 antibiotics, S9347 TPN); "
            "Medicare G0068-G0070, J-codes, B4xxx parenteral nutrition."
        ),
        "scale": (
            "~3.2M patients/yr (up from 829,000 in 2010); 74.3% age 50+. US "
            "infusion market ~$39.9B (2025), ~11% CAGR. Option Care Health "
            "largest (~$5.65B FY2025)."
        ),
        "reimb": (
            "Commercial plans treat home infusion as a MEDICAL benefit "
            "(per-diem + drug + nursing). Medicare benefit narrow/fragmented "
            "(G0068-G0070, infusion days only). Home ~$122-225/day vs inpatient "
            "$586-798/day. H.R. 4993 would expand coverage."
        ),
        "sources": "NHIA Infusion Industry Trends (2026); IQVIA; Mordor Intelligence; CMS home-infusion benefit (sizes approximate).",
        "charts": "Bar (home vs inpatient cost); line (market growth); 100% stacked (site-of-care shift).",
    },
]


def _vertical_card(v: Dict[str, str]) -> str:
    """One editorial card per vertical."""
    accent = PALETTE["brand_accent"] if v["group"] == "A" else PALETTE.get(
        "warning", "#b8732a")
    return (
        f'<div class="cad-card" style="border-left:3px solid {accent};">'
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:start;gap:8px;margin-bottom:6px;">'
        f'<h3 style="margin:0;font-size:15px;">{html.escape(v["name"])}</h3>'
        f'<span class="cad-badge cad-badge-muted" style="font-size:10px;">'
        f'{html.escape(v["tag"])}</span>'
        f'</div>'
        f'<table class="cad-table" style="font-size:11.5px;">'
        f'<tbody>'
        f'<tr><td style="width:22%;font-weight:600;vertical-align:top;">Codes</td>'
        f'<td>{html.escape(v["codes"])}</td></tr>'
        f'<tr><td style="font-weight:600;vertical-align:top;">Scale</td>'
        f'<td>{html.escape(v["scale"])}</td></tr>'
        f'<tr><td style="font-weight:600;vertical-align:top;">Reimbursement</td>'
        f'<td>{html.escape(v["reimb"])}</td></tr>'
        f'<tr><td style="font-weight:600;vertical-align:top;">Sources</td>'
        f'<td style="color:{PALETTE["text_muted"]};">{html.escape(v["sources"])}</td></tr>'
        f'<tr><td style="font-weight:600;vertical-align:top;">Charts</td>'
        f'<td style="color:{PALETTE["text_secondary"]};font-style:italic;">'
        f'{html.escape(v["charts"])}</td></tr>'
        f'</tbody></table>'
        f'</div>'
    )


def render_healthcare_verticals_deepdive() -> str:
    """Render the 15-vertical healthcare + life-sciences deep-dive."""

    head = ck_editorial_head(
        eyebrow="RESEARCH · SECTOR INTELLIGENCE",
        title="Healthcare Verticals & Life-Sciences Deep Dive",
        meta="15 VERTICALS · 10 PROVIDER · 5 LIFE-SCIENCES · CMS CY2026",
        lede_italic_phrase=(
            "Fifteen diligence verticals beyond acute care, each with "
            "chart-ready billing codes, headline epidemiology, and the "
            "2025/2026 reimbursement lever that reshapes it."
        ),
        lede_body=(
            "Provider verticals are PFS-driven; the life-sciences drug-dollar "
            "layer is large, concentrated, and growing double-digit. Every "
            "figure traces to a named primary dataset."
        ),
    )

    group_a = [v for v in _VERTICALS if v["group"] == "A"]
    group_b = [v for v in _VERTICALS if v["group"] == "B"]

    kpi_strip = (
        '<div class="ck-kpi-grid" '
        'style="grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:14px;">'
        + ck_kpi_block("Verticals profiled", ck_fmt_num(len(_VERTICALS)), "10 provider + 5 life-sciences")
        + ck_kpi_block("CTP flat rate", "$127.28/cm²", "skin substitutes, Jan 1 2026")
        + ck_kpi_block("PBM concentration", "80%", "claims via big-three (2025)")
        + ck_kpi_block("340B purchases", "$81.4B", "+22.8% in 2024")
        + '</div>'
    )

    anchor_rows = ""
    for a in _ANCHORS:
        anchor_rows += (
            f'<tr>'
            f'<td style="font-weight:600;width:24%;vertical-align:top;">'
            f'{html.escape(a["name"])}</td>'
            f'<td>{html.escape(a["detail"])}</td>'
            f'<td style="color:{PALETTE["text_muted"]};width:22%;vertical-align:top;">'
            f'{html.escape(a["source"])}</td>'
            f'</tr>'
        )
    anchors_card = (
        f'<div class="cad-card">'
        f'<h2>Cross-cutting 2025/2026 reimbursement anchors</h2>'
        f'<p style="font-size:12px;color:{PALETTE["text_secondary"]};">'
        f'The levers that reshape every PFS-driven provider vertical at once. '
        f'Model wound-care and podiatry revenue under the flat CTP rate before '
        f'any other refresh.</p>'
        f'<table class="cad-table" style="font-size:11.5px;"><thead><tr>'
        f'<th>Lever</th><th>What changes</th><th>Source</th>'
        f'</tr></thead><tbody>{anchor_rows}</tbody></table>'
        f'</div>'
    )

    cards_a = "".join(_vertical_card(v) for v in group_a)
    cards_b = "".join(_vertical_card(v) for v in group_b)

    group_a_header = (
        f'<div class="cad-card" style="background:transparent;border:none;'
        f'box-shadow:none;padding-bottom:0;">'
        f'<h2 style="margin-bottom:2px;">Group A &mdash; provider / therapy / ancillary</h2>'
        f'<p style="font-size:12px;color:{PALETTE["text_secondary"]};margin:0;">'
        f'Ten PFS-driven verticals. Wound care, podiatry, and clinical labs face '
        f'the largest 2026 reimbursement disruptions; ground ambulance is the lone '
        f'surprise-billing carve-out.</p></div>'
    )
    group_b_header = (
        f'<div class="cad-card" style="background:transparent;border:none;'
        f'box-shadow:none;padding-bottom:0;">'
        f'<h2 style="margin-bottom:2px;">Group B &mdash; specialty pharmacy &amp; life-sciences</h2>'
        f'<p style="font-size:12px;color:{PALETTE["text_secondary"]};margin:0;">'
        f'The drug-dollar layer: large, concentrated, double-digit growth. These '
        f'five share the gross-to-net / rebate datasets (DCI, IQVIA, HRSA).</p></div>'
    )

    caveat = (
        f'<div class="cad-card" style="border-left:3px solid {PALETTE["text_muted"]};">'
        f'<h2>Caveats</h2>'
        f'<p style="font-size:12px;color:{PALETTE["text_secondary"]};">'
        f'Market-size figures from commercial research firms (Grand View, Mordor, '
        f'Fortune, MarketsandMarkets) are approximate ranges, not precise points. '
        f'The chiropractor headcount needs direct BLS verification; GPO/PBM shares '
        f'differ by metric (beds vs purchase volume vs claims vs lives); 340B '
        f'net-revenue figures beyond Minnesota are modeled. Full sourcing in '
        f'<code>docs/PEDESK_HEALTHCARE_VERTICALS_LIFE_SCIENCES.md</code>.</p>'
        f'</div>'
    )

    next_up = ck_next_section(
        "Open the sector verticals overview",
        "/verticals",
        eyebrow="Up next",
        italic_word="verticals",
    )

    body = (
        head
        + kpi_strip
        + anchors_card
        + group_a_header
        + cards_a
        + group_b_header
        + cards_b
        + caveat
        + next_up
        + ck_page_actions()
    )
    return chartis_shell(
        body, "Healthcare Verticals & Life-Sciences Deep Dive",
        subtitle="15 diligence verticals · chart-ready codes · CMS CY2026 reimbursement",
        active_nav="research",
    )
