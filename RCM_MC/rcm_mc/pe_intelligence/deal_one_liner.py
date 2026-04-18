"""Deal one-liner — partner's margin-of-the-deck verdict.

Partner statement: "If I can't write the verdict in one
sentence, I don't understand the deal yet."

IC decks run 60 pages. Partners write a single sentence in
the margin when they pick up the deck. That one sentence is
the synthesis: recommendation + the one reason that matters.

This module glues three of the brain's judgment layers
together:

- **Face implausibility** (``unrealistic_on_its_face``):
  are there pass-before-modeling findings?
- **Pattern stack** (``cross_pattern_digest``): do multiple
  libraries fire on the same theme?
- **Thesis chain** (``thesis_implications_chain``): is the
  chain tight, broken, or dangling?

And returns a single-sentence verdict plus a 3-word label
(``invest`` / ``pass`` / ``diligence_more`` / ``reprice``).

The partner voice is direct and numbers-first. If the deal
has ``face`` implausibilities, the one-liner *leads* with
them — the math-level gate dominates all other signal. If
the thesis chain is broken, the one-liner names the specific
link. If the pattern stack compounds, the one-liner names
the theme.

This is intentionally opinionated. It's not a summary of
findings; it's the partner's read.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .unrealistic_on_its_face import (
    FaceInputs,
    ImplausibilityReport,
    scan_unrealistic,
)
from .cross_pattern_digest import (
    CrossPatternDigest,
    PatternContext,
    cross_pattern_scan,
)
from .thesis_implications_chain import (
    ThesisChainReport,
    walk_thesis_chain,
)


RECOMMENDATIONS = ("invest", "pass", "diligence_more",
                    "reprice", "proceed_with_mitigants")


@dataclass
class OneLinerInputs:
    face: Optional[FaceInputs] = None
    pattern_ctx: Optional[PatternContext] = None
    thesis: Optional[str] = None
    thesis_packet: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OneLinerVerdict:
    recommendation: str
    one_liner: str
    reason_source: str   # "face"/"pattern"/"chain"/"none"
    supporting_evidence: List[str] = field(default_factory=list)

    # Keep references for downstream renderers.
    face_report: Optional[ImplausibilityReport] = None
    pattern_digest: Optional[CrossPatternDigest] = None
    thesis_chain: Optional[ThesisChainReport] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recommendation": self.recommendation,
            "one_liner": self.one_liner,
            "reason_source": self.reason_source,
            "supporting_evidence": list(self.supporting_evidence),
            "face_report": (self.face_report.to_dict()
                             if self.face_report else None),
            "pattern_digest": (self.pattern_digest.to_dict()
                                if self.pattern_digest else None),
            "thesis_chain": (self.thesis_chain.to_dict()
                              if self.thesis_chain else None),
        }


def _face_one_liner(r: ImplausibilityReport) -> str:
    high = [f for f in r.findings if f.severity == "high"]
    if high:
        head = high[0]
        return (f"Pass — {head.name.replace('_', ' ')}: "
                f"{head.claim}")
    if r.findings:
        return (f"Reprice — {len(r.findings)} implausibility "
                "finding(s) on face of packet; diligence specifics "
                "or walk.")
    return ""


def _pattern_one_liner(d: CrossPatternDigest) -> str:
    # Compound all-three on one theme.
    all_three = [c for c in d.compound_risks
                 if len(c.libraries_hit) >= 3]
    if all_three:
        c = all_three[0]
        return (f"Pass — {c.theme.replace('_', ' ')} fires across "
                f"all three pattern libraries; rebuild or walk.")
    if d.compound_risks:
        c = d.compound_risks[0]
        return (f"Reprice — {c.theme.replace('_', ' ')} compound "
                f"risk across {len(c.libraries_hit)} libraries "
                f"(severity {c.severity:.2f}).")
    if d.matches:
        m = d.matches[0]
        return (f"Diligence_more — {m.library} library flagged "
                f"{m.name}; single-library hit, explicit mitigant "
                "required.")
    return ""


def _chain_one_liner(r: ThesisChainReport) -> str:
    if r.contradicted_count >= 1:
        broken = next(e for e in r.entries
                       if e.status == "contradicted")
        return (f"Pass — thesis '{r.thesis}' chain breaks at: "
                f"{broken.claim}")
    if r.high_risk_unresolved >= 2:
        return (f"Diligence_more — thesis '{r.thesis}' has "
                f"{r.high_risk_unresolved} high-risk links "
                "unresolved.")
    if r.not_addressed_count >= 1:
        return (f"Proceed_with_mitigants — thesis '{r.thesis}' "
                f"has {r.not_addressed_count} open downstream "
                "implication(s); document before IC.")
    if r.confirmed_count >= 1:
        return (f"Invest — thesis '{r.thesis}' chain is tight; "
                "seller has closed each downstream loop.")
    return ""


def _classify_rec_from_one_liner(line: str) -> str:
    head = line.split(" ", 1)[0].lower().rstrip(".,:-—")
    if head in ("pass",):
        return "pass"
    if head in ("reprice",):
        return "reprice"
    if head in ("diligence_more",):
        return "diligence_more"
    if head in ("proceed_with_mitigants",):
        return "proceed_with_mitigants"
    if head in ("invest",):
        return "invest"
    return "proceed_with_mitigants"


def synthesize_one_liner(inputs: OneLinerInputs) -> OneLinerVerdict:
    face_r = (scan_unrealistic(inputs.face)
              if inputs.face is not None else None)
    patt_d = (cross_pattern_scan(inputs.pattern_ctx)
              if inputs.pattern_ctx is not None else None)
    chain_r = None
    if inputs.thesis:
        chain_r = walk_thesis_chain(inputs.thesis,
                                     inputs.thesis_packet)

    # Precedence: face > chain-broken > pattern-compound-3 >
    # chain-unresolved > pattern-compound >= 2 > single-lib.
    line = ""
    source = "none"
    evidence: List[str] = []

    if face_r and any(f.severity == "high" for f in face_r.findings):
        line = _face_one_liner(face_r)
        source = "face"
        evidence = [f.name for f in face_r.findings
                    if f.severity == "high"]
    elif chain_r and chain_r.contradicted_count >= 1:
        line = _chain_one_liner(chain_r)
        source = "chain"
        evidence = [e.claim for e in chain_r.entries
                    if e.status == "contradicted"]
    elif patt_d and any(len(c.libraries_hit) >= 3
                         for c in patt_d.compound_risks):
        line = _pattern_one_liner(patt_d)
        source = "pattern"
        evidence = [c.theme for c in patt_d.compound_risks
                    if len(c.libraries_hit) >= 3]
    elif chain_r and chain_r.high_risk_unresolved >= 2:
        line = _chain_one_liner(chain_r)
        source = "chain"
        evidence = [e.claim for e in chain_r.entries
                    if e.risk == "high" and e.status != "confirmed"]
    elif patt_d and patt_d.compound_risks:
        line = _pattern_one_liner(patt_d)
        source = "pattern"
        evidence = [c.theme for c in patt_d.compound_risks]
    elif face_r and face_r.findings:
        line = _face_one_liner(face_r)
        source = "face"
        evidence = [f.name for f in face_r.findings]
    elif chain_r and (chain_r.not_addressed_count >= 1
                       or chain_r.confirmed_count >= 1):
        line = _chain_one_liner(chain_r)
        source = "chain"
        evidence = [e.claim for e in chain_r.entries
                    if e.status != "confirmed"]
    elif patt_d and patt_d.matches:
        line = _pattern_one_liner(patt_d)
        source = "pattern"
        evidence = [m.name for m in patt_d.matches[:2]]
    else:
        line = ("Proceed — no face implausibility, no pattern "
                "stack, no broken thesis chain.")
        source = "none"
        evidence = []

    rec = _classify_rec_from_one_liner(line)

    # If we picked "proceed" from the fall-through but no thesis
    # or pattern data was given, downgrade to
    # proceed_with_mitigants to avoid false confidence.
    if rec == "proceed_with_mitigants" and not line.startswith(
        "Proceed_with_mitigants"
    ) and not (face_r or patt_d or chain_r):
        rec = "proceed_with_mitigants"

    return OneLinerVerdict(
        recommendation=rec,
        one_liner=line,
        reason_source=source,
        supporting_evidence=evidence,
        face_report=face_r,
        pattern_digest=patt_d,
        thesis_chain=chain_r,
    )


def render_one_liner_markdown(v: OneLinerVerdict) -> str:
    lines = [
        "# Deal one-liner",
        "",
        f"**Recommendation:** `{v.recommendation}`",
        "",
        f"> {v.one_liner}",
        "",
        f"_Source: {v.reason_source}_",
        "",
    ]
    if v.supporting_evidence:
        lines.append("**Supporting evidence:**")
        lines.append("")
        for e in v.supporting_evidence[:5]:
            lines.append(f"- {e}")
    return "\n".join(lines)
