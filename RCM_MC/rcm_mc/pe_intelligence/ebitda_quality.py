"""EBITDA quality — assess add-backs against reported EBITDA.

Sellers always pro-forma EBITDA with add-backs: "normalize for one-
time costs, stranded overhead, synergies achievable on day 1."
Some are legitimate, many are not. Partners scrutinize add-backs
more than headline EBITDA.

This module classifies each add-back as:

- **Defensible** — truly one-time, cash-backed, easily documented.
- **Aggressive** — plausible but aggressive (e.g., ongoing CEO
  compensation normalized, rent-for-owned-real-estate).
- **Phantom** — synergy adjustments, run-rate "projected" items,
  non-cash adjustments with no hard evidence.

Output: normalized EBITDA + partner-voice verdict.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class EBITDAAddback:
    name: str
    amount: float                         # $ — positive adds back
    category: str = "other"               # "one_time" | "normalization" | "synergy" | "run_rate" | "other"
    evidence: Optional[str] = None        # "documented" | "estimated" | "projected"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "amount": self.amount,
            "category": self.category,
            "evidence": self.evidence,
        }


@dataclass
class AddbackFinding:
    addback: EBITDAAddback
    classification: str                   # "defensible" | "aggressive" | "phantom"
    haircut_pct: float                    # fraction to discount
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "addback": self.addback.to_dict(),
            "classification": self.classification,
            "haircut_pct": self.haircut_pct,
            "partner_note": self.partner_note,
        }


@dataclass
class EBITDAQualityReport:
    reported_ebitda: float
    gross_addbacks: float
    haircut_addbacks: float
    partner_ebitda: float                 # reported + (addbacks × (1 - haircut))
    findings: List[AddbackFinding] = field(default_factory=list)
    addback_ratio: float = 0.0            # addbacks / reported_ebitda
    quality_verdict: str = ""             # high / moderate / low / implausible
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reported_ebitda": self.reported_ebitda,
            "gross_addbacks": self.gross_addbacks,
            "haircut_addbacks": self.haircut_addbacks,
            "partner_ebitda": self.partner_ebitda,
            "findings": [f.to_dict() for f in self.findings],
            "addback_ratio": self.addback_ratio,
            "quality_verdict": self.quality_verdict,
            "partner_note": self.partner_note,
        }


# ── Classifier ─────────────────────────────────────────────────────

_CATEGORY_DEFAULTS = {
    "one_time": ("defensible", 0.10),      # 10% haircut even when documented
    "normalization": ("aggressive", 0.35),
    "synergy": ("phantom", 0.75),
    "run_rate": ("phantom", 0.60),
    "other": ("aggressive", 0.30),
}


def _classify_addback(addback: EBITDAAddback) -> AddbackFinding:
    base_class, base_haircut = _CATEGORY_DEFAULTS.get(
        addback.category, ("aggressive", 0.30),
    )
    # Evidence modifier.
    if addback.evidence == "documented":
        if base_class == "phantom":
            # Documented synergy is rare; soften.
            cls, hc = "aggressive", 0.50
        elif base_class == "aggressive":
            cls, hc = "aggressive", base_haircut - 0.15
        else:
            cls, hc = "defensible", max(0.05, base_haircut - 0.05)
    elif addback.evidence == "estimated":
        cls, hc = base_class, base_haircut
    elif addback.evidence == "projected":
        if base_class != "phantom":
            cls, hc = "aggressive", min(0.70, base_haircut + 0.20)
        else:
            cls, hc = base_class, base_haircut
    else:
        cls, hc = base_class, base_haircut

    note_map = {
        "defensible": f"Take at {(1 - hc)*100:.0f}% of stated.",
        "aggressive": f"Defensible with evidence; haircut to {(1 - hc)*100:.0f}%.",
        "phantom": f"Do not credit beyond {(1 - hc)*100:.0f}% without hard evidence.",
    }
    return AddbackFinding(
        addback=addback,
        classification=cls,
        haircut_pct=round(hc, 4),
        partner_note=note_map.get(cls, ""),
    )


# ── Orchestrator ────────────────────────────────────────────────────

def assess_ebitda_quality(
    reported_ebitda: float,
    addbacks: List[EBITDAAddback],
) -> EBITDAQualityReport:
    """Classify add-backs, compute partner-EBITDA after haircuts."""
    findings = [_classify_addback(a) for a in addbacks]
    gross = sum(a.amount for a in addbacks)
    after_haircut = sum(f.addback.amount * (1 - f.haircut_pct)
                        for f in findings)
    partner_ebitda = reported_ebitda + after_haircut
    ratio = gross / max(abs(reported_ebitda), 1e-9)

    # Verdict
    phantom_dollars = sum(f.addback.amount for f in findings
                          if f.classification == "phantom")
    phantom_share = (phantom_dollars / gross) if gross > 0 else 0.0
    if ratio < 0.05 and phantom_share < 0.10:
        verdict = "high"
        note = ("EBITDA quality is high — add-backs are minor and well "
                "categorized.")
    elif ratio < 0.15 and phantom_share < 0.25:
        verdict = "moderate"
        note = ("EBITDA quality is moderate — some add-backs but within "
                "reason.")
    elif ratio < 0.30 and phantom_share < 0.50:
        verdict = "low"
        note = (f"Low EBITDA quality — add-backs are {ratio*100:.0f}% of "
                "reported; haircut before pricing.")
    else:
        verdict = "implausible"
        note = (f"Reported EBITDA is materially inflated — {ratio*100:.0f}% "
                "add-backs, a large share of which are phantom. Use "
                "partner-EBITDA for pricing.")

    return EBITDAQualityReport(
        reported_ebitda=reported_ebitda,
        gross_addbacks=round(gross, 2),
        haircut_addbacks=round(after_haircut, 2),
        partner_ebitda=round(partner_ebitda, 2),
        findings=findings,
        addback_ratio=round(ratio, 4),
        quality_verdict=verdict,
        partner_note=note,
    )


def render_ebitda_quality_markdown(report: EBITDAQualityReport) -> str:
    lines = [
        "# EBITDA quality report",
        "",
        f"**Verdict:** {report.quality_verdict}  ",
        f"**Reported EBITDA:** ${report.reported_ebitda:,.0f}  ",
        f"**Gross add-backs:** ${report.gross_addbacks:,.0f}  ",
        f"**Partner EBITDA (post-haircut):** ${report.partner_ebitda:,.0f}  ",
        f"**Add-back ratio:** {report.addback_ratio*100:.1f}% of reported",
        "",
        f"_{report.partner_note}_",
        "",
        "| Add-back | Amount | Category | Evidence | Class | Haircut | Note |",
        "|---|---:|---|---|---|---:|---|",
    ]
    for f in report.findings:
        a = f.addback
        lines.append(
            f"| {a.name} | ${a.amount:,.0f} | {a.category} | "
            f"{a.evidence or 'n/a'} | {f.classification} | "
            f"{f.haircut_pct*100:.0f}% | {f.partner_note} |"
        )
    return "\n".join(lines)
