"""Layered 837↔835 claim matching.

Links submitted claims (837) to remittance claims (835) so leakage
analytics can compare what was billed against what was paid. Matching
is **layered** and every match carries a confidence band, a reason, and
a 0..1 score (plan §"835/837 MATCHING ENGINE"):

  high     — exact claim-control-number, or a full composite agreement
  medium   — strong composite (most discriminating fields agree)
  low      — weak/fuzzy composite; flagged for review
  unmatched — no acceptable candidate

Low-confidence matches are marked ``needs_review`` and must be excluded
from high-confidence financial conclusions unless explicitly caveated.

Inputs are claim-shaped dicts (the parser adapters' ``parsed_payload``
shape, also producible from CCD rows), keeping this engine decoupled
from any one parser or the CCD's auto-reconcile behaviour.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

Confidence = str  # "high" | "medium" | "low" | "unmatched"


@dataclass
class ClaimMatch:
    submitted_key: Optional[str]
    remittance_key: Optional[str]
    match_confidence: Confidence
    match_reason: str
    match_score: float           # 0..1
    review_status: str           # "auto" | "needs_review"

    def to_dict(self) -> Dict[str, Any]:
        return vars(self)


@dataclass
class MatchResult:
    matches: List[ClaimMatch] = field(default_factory=list)
    unmatched_submitted: List[str] = field(default_factory=list)
    unmatched_remittance: List[str] = field(default_factory=list)

    def counts(self) -> Dict[str, int]:
        out = {"high": 0, "medium": 0, "low": 0}
        for m in self.matches:
            out[m.match_confidence] = out.get(m.match_confidence, 0) + 1
        out["unmatched_submitted"] = len(self.unmatched_submitted)
        out["unmatched_remittance"] = len(self.unmatched_remittance)
        return out

    def to_dict(self) -> Dict[str, Any]:
        return {
            "matches": [m.to_dict() for m in self.matches],
            "unmatched_submitted": list(self.unmatched_submitted),
            "unmatched_remittance": list(self.unmatched_remittance),
            "counts": self.counts(),
        }


def _key(claim: Dict[str, Any], idx: int) -> str:
    cid = (claim.get("claim_id") or "").strip()
    return cid if cid else f"_row{idx}"


def _norm(v: Any) -> str:
    return str(v).strip().upper() if v not in (None, "") else ""


def _money_close(a: Any, b: Any, *, tol: float = 0.01) -> bool:
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return False


# Composite scoring: each agreeing field contributes weight. The most
# discriminating fields (patient token, service date, charge) weigh most.
_FIELD_WEIGHTS: Tuple[Tuple[str, float], ...] = (
    ("patient_id", 0.30),
    ("service_date_from", 0.20),
    ("charge_amount", 0.20),
    ("cpt_code", 0.15),
    ("billing_npi", 0.10),
    ("payer", 0.05),
)


def _composite_score(s: Dict[str, Any], r: Dict[str, Any]) -> Tuple[float, List[str]]:
    score = 0.0
    agreed: List[str] = []
    for field_name, weight in _FIELD_WEIGHTS:
        sv, rv = s.get(field_name), r.get(field_name)
        if field_name == "charge_amount":
            ok = sv is not None and rv is not None and _money_close(sv, rv)
        else:
            ok = bool(_norm(sv)) and _norm(sv) == _norm(rv)
        if ok:
            score += weight
            agreed.append(field_name)
    return score, agreed


def match_claims(
    submitted: Sequence[Dict[str, Any]],
    remittance: Sequence[Dict[str, Any]],
    *,
    medium_threshold: float = 0.55,
    low_threshold: float = 0.30,
) -> MatchResult:
    """Match submitted→remittance claims with layered confidence.

    Pass 1: exact claim_id (high). Pass 2: best composite among the
    remaining remittance rows (medium/low by score). Each remittance row
    matches at most one submitted row.
    """
    result = MatchResult()
    sub_keys = [_key(c, i) for i, c in enumerate(submitted)]
    rem_keys = [_key(c, i) for i, c in enumerate(remittance)]
    rem_used = [False] * len(remittance)

    # Index remittance by exact claim_id for pass 1.
    rem_by_id: Dict[str, List[int]] = {}
    for i, c in enumerate(remittance):
        cid = (c.get("claim_id") or "").strip()
        if cid:
            rem_by_id.setdefault(cid, []).append(i)

    matched_sub = [False] * len(submitted)

    # Pass 1 — exact claim-control-number.
    for si, s in enumerate(submitted):
        cid = (s.get("claim_id") or "").strip()
        if not cid:
            continue
        cand = [i for i in rem_by_id.get(cid, []) if not rem_used[i]]
        if cand:
            ri = cand[0]
            rem_used[ri] = True
            matched_sub[si] = True
            result.matches.append(ClaimMatch(
                submitted_key=sub_keys[si], remittance_key=rem_keys[ri],
                match_confidence="high",
                match_reason="exact claim_control_number",
                match_score=1.0, review_status="auto",
            ))

    # Pass 2 — composite for remaining submitted rows.
    for si, s in enumerate(submitted):
        if matched_sub[si]:
            continue
        best_ri, best_score, best_fields = -1, 0.0, []
        for ri, r in enumerate(remittance):
            if rem_used[ri]:
                continue
            score, fields = _composite_score(s, r)
            if score > best_score:
                best_ri, best_score, best_fields = ri, score, fields
        if best_ri >= 0 and best_score >= low_threshold:
            rem_used[best_ri] = True
            matched_sub[si] = True
            if best_score >= medium_threshold:
                conf, review = "medium", "auto"
            else:
                conf, review = "low", "needs_review"
            result.matches.append(ClaimMatch(
                submitted_key=sub_keys[si], remittance_key=rem_keys[best_ri],
                match_confidence=conf,
                match_reason="composite: " + "+".join(best_fields),
                match_score=round(best_score, 3), review_status=review,
            ))

    result.unmatched_submitted = [
        sub_keys[i] for i in range(len(submitted)) if not matched_sub[i]
    ]
    result.unmatched_remittance = [
        rem_keys[i] for i in range(len(remittance)) if not rem_used[i]
    ]
    return result
