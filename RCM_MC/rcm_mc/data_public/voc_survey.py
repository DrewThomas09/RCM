"""Voice-of-Customer survey evidence — the missing CDD primary-research read.

Every commercial-diligence readout leans on three customer-evidence
exhibits: NPS by segment, a key-purchase-criteria (KPC) gap matrix
(importance × target-vs-best-competitor performance), and a
willingness-to-pay read. The desk had none of them — TAM/SAM and
demand forecasting cover the market top-down, but nothing represented
what customers actually say. This module computes those three exhibits
from a structured survey panel so the CDD hub can show the demand side
of the thesis, and so a real survey vendor file can later replace the
illustrative panel without touching the math.

The classification thresholds follow standard CDD practice:
- a KPC is a **differentiator** when the target outscores the best
  competitor by ≥ 0.3 (on a 10-pt scale) on a criterion with
  importance ≥ 3.5/5;
- a **vulnerability** when it trails by ≥ 0.3 on the same importance
  bar;
- **table stakes** otherwise (parity, or low-importance criteria
  where a gap doesn't move purchase decisions).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

# 10-pt performance scale, 5-pt importance scale — the convention most
# survey vendors (and therefore most CDD readouts) use.
_DIFF_GAP = 0.3
_IMPORTANCE_BAR = 3.5


@dataclass
class KpcRow:
    criterion: str
    importance: float           # 1-5 stated importance
    target_score: float         # 0-10 performance
    best_competitor_score: float
    gap: float                  # target - best competitor
    classification: str         # DIFFERENTIATOR | VULNERABILITY | TABLE_STAKES


@dataclass
class SegmentRead:
    segment: str
    n_respondents: int
    nps: int                    # -100..100
    repurchase_intent_pct: float   # would choose target again
    churn_intent_pct: float        # actively considering a switch
    verbatim_theme: str            # dominant open-text theme


@dataclass
class WtpBand:
    label: str                  # e.g. "Accept +5% price increase"
    share_pct: float            # share of respondents in band


@dataclass
class VocResult:
    sector: str
    n_total: int
    blended_nps: int
    segments: List[SegmentRead]
    kpc_rows: List[KpcRow]
    wtp_bands: List[WtpBand]
    differentiators: List[str]
    vulnerabilities: List[str]
    headline: str


# Survey panels by sector. Curated, deterministic, clearly illustrative
# — the page renders ck_illustrative_note. Shapes mirror what a survey
# vendor (e.g. a 150-200 N B2B panel) delivers, so swapping in a real
# panel is a data change, not a code change.
_PANELS: Dict[str, Dict] = {
    "Physician Services": {
        "segments": [
            ("Referring physicians", 64, 38, 81.0, 9.0,
             "Access and scheduling speed beat the local health system"),
            ("Patients", 88, 52, 86.0, 6.0,
             "Front-desk experience strong; billing clarity is the gripe"),
            ("Payer network managers", 22, 12, 68.0, 14.0,
             "Rates seen as rich vs market; quality data underwhelming"),
            ("Employer benefit buyers", 18, 21, 72.0, 11.0,
             "Want bundled pricing and faster reporting"),
        ],
        "kpc": [
            ("Appointment access / wait time", 4.6, 8.4, 7.1),
            ("Clinical quality reputation", 4.8, 8.1, 8.0),
            ("Referral communication loop", 4.2, 7.8, 6.9),
            ("Price / negotiated rates", 3.9, 6.2, 7.4),
            ("Geographic coverage", 3.6, 7.0, 8.1),
            ("Digital experience (portal, telehealth)", 3.2, 6.8, 6.5),
            ("Billing accuracy & transparency", 4.0, 6.1, 6.6),
        ],
        "wtp": [
            ("Accept +5% price increase", 46.0),
            ("Accept +3% only", 27.0),
            ("Flat — no increase tolerated", 19.0),
            ("Would demand concession", 8.0),
        ],
    },
    "HCIT / SaaS": {
        "segments": [
            ("Health-system CIOs", 31, 41, 84.0, 8.0,
             "Integration depth is the moat; support tickets aging"),
            ("Department end-users", 96, 33, 79.0, 12.0,
             "Workflow fit praised; UI dated vs newer entrants"),
            ("Revenue-cycle directors", 28, 47, 88.0, 5.0,
             "Denial-prevention ROI is provable and renewed on it"),
        ],
        "kpc": [
            ("EHR integration depth", 4.9, 8.8, 7.6),
            ("Measurable ROI / denial reduction", 4.7, 8.5, 7.7),
            ("Implementation time", 4.1, 6.4, 7.2),
            ("Customer support responsiveness", 4.3, 6.9, 7.4),
            ("Product roadmap / AI features", 3.8, 7.2, 7.9),
            ("Total cost of ownership", 4.0, 7.1, 7.0),
        ],
        "wtp": [
            ("Accept +8% at renewal", 38.0),
            ("Accept +5% at renewal", 33.0),
            ("Flat renewal only", 21.0),
            ("Would demand concession", 8.0),
        ],
    },
    "Home Health": {
        "segments": [
            ("Discharge planners", 42, 44, 85.0, 7.0,
             "Response time on referrals is the differentiator"),
            ("Patients & families", 74, 49, 87.0, 5.0,
             "Caregiver consistency drives satisfaction"),
            ("MA plan network managers", 19, 8, 64.0, 16.0,
             "Pushing rate cuts; want documented outcomes"),
        ],
        "kpc": [
            ("Referral response time", 4.7, 8.6, 7.2),
            ("Caregiver consistency / retention", 4.5, 7.9, 6.8),
            ("Clinical outcomes documentation", 4.3, 6.5, 7.0),
            ("Coverage area", 3.7, 7.4, 7.8),
            ("Rate competitiveness vs MA plans", 4.0, 6.0, 6.7),
        ],
        "wtp": [
            ("Accept +4% episodic rate", 35.0),
            ("Accept +2%", 30.0),
            ("Flat", 24.0),
            ("Would demand concession", 11.0),
        ],
    },
}

SECTORS = list(_PANELS)


def _classify(importance: float, gap: float) -> str:
    if importance >= _IMPORTANCE_BAR and gap >= _DIFF_GAP:
        return "DIFFERENTIATOR"
    if importance >= _IMPORTANCE_BAR and gap <= -_DIFF_GAP:
        return "VULNERABILITY"
    return "TABLE_STAKES"


def compute_voc(sector: str = "Physician Services") -> VocResult:
    panel = _PANELS.get(sector) or _PANELS[SECTORS[0]]
    if sector not in _PANELS:
        sector = SECTORS[0]

    segments = [
        SegmentRead(segment=s, n_respondents=n, nps=nps,
                    repurchase_intent_pct=rep, churn_intent_pct=churn,
                    verbatim_theme=theme)
        for s, n, nps, rep, churn, theme in panel["segments"]
    ]
    n_total = sum(s.n_respondents for s in segments)
    # NPS blends respondent-weighted, not segment-weighted — a 96-user
    # segment should move the blend more than a 19-buyer one.
    blended = round(
        sum(s.nps * s.n_respondents for s in segments) / max(n_total, 1))

    kpc_rows: List[KpcRow] = []
    for crit, imp, tgt, comp in panel["kpc"]:
        gap = round(tgt - comp, 2)
        kpc_rows.append(KpcRow(
            criterion=crit, importance=imp, target_score=tgt,
            best_competitor_score=comp, gap=gap,
            classification=_classify(imp, gap),
        ))
    # Importance-descending: the readout leads with what customers
    # weight most, not with the target's best scores.
    kpc_rows.sort(key=lambda r: r.importance, reverse=True)

    wtp = [WtpBand(label=lbl, share_pct=p) for lbl, p in panel["wtp"]]
    diffs = [r.criterion for r in kpc_rows
             if r.classification == "DIFFERENTIATOR"]
    vulns = [r.criterion for r in kpc_rows
             if r.classification == "VULNERABILITY"]

    if diffs and not vulns:
        headline = (f"Customers confirm the thesis: {len(diffs)} "
                    f"differentiator(s), no high-importance vulnerability.")
    elif diffs and vulns:
        headline = (f"Mixed evidence: wins on {diffs[0].lower()}, "
                    f"but {vulns[0].lower()} is a high-importance gap.")
    elif vulns:
        headline = (f"Caution: customers rank the target behind the best "
                    f"competitor on {len(vulns)} high-importance criteria.")
    else:
        headline = "Parity positioning — no differentiator, no vulnerability."

    return VocResult(
        sector=sector, n_total=n_total, blended_nps=blended,
        segments=segments, kpc_rows=kpc_rows, wtp_bands=wtp,
        differentiators=diffs, vulnerabilities=vulns, headline=headline,
    )
