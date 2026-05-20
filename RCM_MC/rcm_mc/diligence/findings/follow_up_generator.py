"""Follow-up diligence questions + document requests, tailored to findings.

Aggregates and de-duplicates the per-finding follow-ups and document
requests, then adds a conservative baseline request list every
revenue-cycle diligence should include (plan §"FOLLOW-UP REQUEST
GENERATION"). Order is preserved (findings first, then baseline) and
duplicates are dropped.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence

from .finding_generator import Finding

# Baseline asks that apply to virtually any RCM diligence snapshot.
_BASELINE_QUESTIONS: List[str] = [
    "What is the net collection rate by month for the last 24 months?",
    "What is the appeal success rate by denial category?",
    "What is the prior-authorization capture rate and workflow?",
]
_BASELINE_DOCUMENTS: List[str] = [
    "Denial summary by payer and reason code (24 months).",
    "AR aging by payer.",
    "Payer contracts and fee schedules.",
    "Write-off and bad-debt policy.",
]


@dataclass
class FollowUpPackage:
    questions: List[str] = field(default_factory=list)
    document_requests: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"questions": self.questions,
                "document_requests": self.document_requests}


def _dedupe(items: Sequence[str]) -> List[str]:
    seen: set = set()
    out: List[str] = []
    for it in items:
        key = it.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(it.strip())
    return out


def generate_follow_ups(findings: Sequence[Finding]) -> FollowUpPackage:
    questions: List[str] = []
    documents: List[str] = []
    for f in findings:
        questions.extend(f.recommended_follow_up)
        documents.extend(f.document_requests)
    questions.extend(_BASELINE_QUESTIONS)
    documents.extend(_BASELINE_DOCUMENTS)
    return FollowUpPackage(
        questions=_dedupe(questions),
        document_requests=_dedupe(documents),
    )
