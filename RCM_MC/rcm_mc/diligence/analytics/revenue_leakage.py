"""PE revenue-leakage analytics over the CCD.

Converts canonical claims into the marts a deal team reads: overall
leakage totals, denial dollars by preventability category, payer
variance + concentration, CPT/procedure variance, and provider
outliers (plan §"ANALYTICS REQUIREMENTS").

Conservative by construction (plan §"DENIAL AND ADJUSTMENT
CATEGORIZATION"):
- Contractual adjustments are NOT counted as leakage.
- Patient responsibility is NOT counted as recoverable upside.
- "Potentially preventable leakage" sums only likely/possibly-
  preventable categories, and is labelled an estimate — never
  guaranteed EBITDA.

Per-code adjustment dollars are not present on the CCD (the parser sums
CAS amounts into one ``adjustment_amount`` + a code set), so a claim is
attributed to a single category via ``classify_carc_set`` precedence
and its adjustment dollars assigned there. This approximation is
documented and conservative.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from ..benchmarks._ansi_codes import DenialCategory, classify_carc_set
from ..ingest.ccd import CanonicalClaim, CanonicalClaimsDataset, ClaimStatus

# Preventability / recoverability / EBITDA-relevance per category.
# Conservative: contractual is not preventable and not recoverable.
_CATEGORY_META: Dict[DenialCategory, Dict[str, str]] = {
    DenialCategory.CLINICAL: {
        "preventability": "likely_preventable",      # prior-auth, med-necessity
        "recoverability": "medium",
        "ebitda_relevance": "high",
    },
    DenialCategory.CODING: {
        "preventability": "likely_preventable",
        "recoverability": "high",
        "ebitda_relevance": "high",
    },
    DenialCategory.FRONT_END: {
        "preventability": "possibly_preventable",     # eligibility/registration
        "recoverability": "medium",
        "ebitda_relevance": "medium",
    },
    DenialCategory.PAYER_BEHAVIOR: {
        "preventability": "possibly_preventable",      # timely filing/duplicate/policy
        "recoverability": "low",
        "ebitda_relevance": "medium",
    },
    DenialCategory.CONTRACTUAL: {
        "preventability": "likely_not_preventable",
        "recoverability": "low",
        "ebitda_relevance": "not_applicable",
    },
    DenialCategory.UNCLASSIFIED: {
        "preventability": "unknown",
        "recoverability": "unknown",
        "ebitda_relevance": "unknown",
    },
}

_PREVENTABLE = {"likely_preventable", "possibly_preventable"}


def category_meta(cat: DenialCategory) -> Dict[str, str]:
    return _CATEGORY_META.get(cat, _CATEGORY_META[DenialCategory.UNCLASSIFIED])


def _f(v: Any) -> float:
    try:
        return float(v) if v is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def _is_denied(c: CanonicalClaim, cat: DenialCategory) -> bool:
    return c.status == ClaimStatus.DENIED or cat in (
        DenialCategory.CLINICAL, DenialCategory.CODING,
        DenialCategory.FRONT_END, DenialCategory.PAYER_BEHAVIOR,
    )


@dataclass
class LeakageTotals:
    claim_count: int = 0
    gross_charges: float = 0.0
    allowed_amount: float = 0.0
    paid_amount: float = 0.0
    adjustment_amount: float = 0.0
    patient_responsibility: float = 0.0
    contractual_adjustments: float = 0.0
    denial_dollars: float = 0.0
    denied_claim_count: int = 0
    potentially_preventable_leakage: float = 0.0
    gross_collection_rate: Optional[float] = None
    paid_to_charge: Optional[float] = None
    allowed_to_charge: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return vars(self)


@dataclass
class CategoryLeakage:
    category: str
    preventability: str
    recoverability: str
    ebitda_relevance: str
    dollars: float
    claim_count: int
    pct_of_denial_dollars: float

    def to_dict(self) -> Dict[str, Any]:
        return vars(self)


@dataclass
class GroupLeakage:
    """Payer / CPT / provider roll-up row."""
    key: str
    claim_count: int
    charges: float
    paid: float
    denial_dollars: float
    paid_to_charge: Optional[float]
    denial_rate_dollars: Optional[float]
    pct_of_paid: float

    def to_dict(self) -> Dict[str, Any]:
        return vars(self)


@dataclass
class AnalyticsResult:
    totals: LeakageTotals
    by_category: List[CategoryLeakage] = field(default_factory=list)
    by_payer: List[GroupLeakage] = field(default_factory=list)
    by_cpt: List[GroupLeakage] = field(default_factory=list)
    by_provider: List[GroupLeakage] = field(default_factory=list)
    payer_concentration_top1_pct: float = 0.0
    cpt_concentration_top1_pct: float = 0.0
    provider_concentration_top1_pct: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "totals": self.totals.to_dict(),
            "by_category": [c.to_dict() for c in self.by_category],
            "by_payer": [g.to_dict() for g in self.by_payer],
            "by_cpt": [g.to_dict() for g in self.by_cpt],
            "by_provider": [g.to_dict() for g in self.by_provider],
            "payer_concentration_top1_pct": self.payer_concentration_top1_pct,
            "cpt_concentration_top1_pct": self.cpt_concentration_top1_pct,
            "provider_concentration_top1_pct": self.provider_concentration_top1_pct,
        }


def _ratio(num: float, den: float) -> Optional[float]:
    return round(num / den, 4) if den else None


def _group(
    claims: Sequence[CanonicalClaim], key_fn, total_paid: float
) -> List[GroupLeakage]:
    acc: Dict[str, Dict[str, float]] = {}
    for c in claims:
        k = key_fn(c)
        if not k:
            continue
        cat = classify_carc_set(c.adjustment_reason_codes or ())
        a = acc.setdefault(k, {"n": 0, "charges": 0.0, "paid": 0.0, "denial": 0.0})
        a["n"] += 1
        a["charges"] += _f(c.charge_amount)
        a["paid"] += _f(c.paid_amount)
        if _is_denied(c, cat) and cat != DenialCategory.CONTRACTUAL:
            a["denial"] += _f(c.adjustment_amount)
    rows = [
        GroupLeakage(
            key=k, claim_count=int(a["n"]), charges=round(a["charges"], 2),
            paid=round(a["paid"], 2), denial_dollars=round(a["denial"], 2),
            paid_to_charge=_ratio(a["paid"], a["charges"]),
            denial_rate_dollars=_ratio(a["denial"], a["charges"]),
            pct_of_paid=round(a["paid"] / total_paid, 4) if total_paid else 0.0,
        )
        for k, a in acc.items()
    ]
    rows.sort(key=lambda r: r.denial_dollars, reverse=True)
    return rows


def compute_analytics(ccd: CanonicalClaimsDataset) -> AnalyticsResult:
    claims = ccd.claims
    totals = LeakageTotals(claim_count=len(claims))
    cat_acc: Dict[DenialCategory, Dict[str, float]] = {}

    for c in claims:
        totals.gross_charges += _f(c.charge_amount)
        totals.allowed_amount += _f(c.allowed_amount)
        totals.paid_amount += _f(c.paid_amount)
        totals.adjustment_amount += _f(c.adjustment_amount)
        totals.patient_responsibility += _f(c.patient_responsibility)
        cat = classify_carc_set(c.adjustment_reason_codes or ())
        meta = category_meta(cat)
        adj = _f(c.adjustment_amount)
        ca = cat_acc.setdefault(cat, {"dollars": 0.0, "n": 0})
        ca["dollars"] += adj
        ca["n"] += 1
        if cat == DenialCategory.CONTRACTUAL:
            totals.contractual_adjustments += adj
        if _is_denied(c, cat) and cat != DenialCategory.CONTRACTUAL:
            totals.denial_dollars += adj
            totals.denied_claim_count += 1
        if meta["preventability"] in _PREVENTABLE:
            totals.potentially_preventable_leakage += adj

    totals.gross_collection_rate = _ratio(totals.paid_amount, totals.gross_charges)
    totals.paid_to_charge = _ratio(totals.paid_amount, totals.gross_charges)
    totals.allowed_to_charge = _ratio(totals.allowed_amount, totals.gross_charges)
    for k in ("gross_charges", "allowed_amount", "paid_amount",
              "adjustment_amount", "patient_responsibility",
              "contractual_adjustments", "denial_dollars",
              "potentially_preventable_leakage"):
        setattr(totals, k, round(getattr(totals, k), 2))

    by_category = []
    for cat, a in cat_acc.items():
        meta = category_meta(cat)
        by_category.append(CategoryLeakage(
            category=cat.value, preventability=meta["preventability"],
            recoverability=meta["recoverability"],
            ebitda_relevance=meta["ebitda_relevance"],
            dollars=round(a["dollars"], 2), claim_count=int(a["n"]),
            pct_of_denial_dollars=(
                round(a["dollars"] / totals.denial_dollars, 4)
                if totals.denial_dollars and cat != DenialCategory.CONTRACTUAL else 0.0),
        ))
    by_category.sort(key=lambda c: c.dollars, reverse=True)

    by_payer = _group(claims, lambda c: c.payer_canonical or c.payer_raw, totals.paid_amount)
    by_cpt = _group(claims, lambda c: c.cpt_code, totals.paid_amount)
    by_provider = _group(claims, lambda c: c.billing_npi or c.rendering_npi, totals.paid_amount)

    def _top1(rows: List[GroupLeakage]) -> float:
        return round(max((r.pct_of_paid for r in rows), default=0.0), 4)

    return AnalyticsResult(
        totals=totals, by_category=by_category, by_payer=by_payer,
        by_cpt=by_cpt, by_provider=by_provider,
        payer_concentration_top1_pct=_top1(by_payer),
        cpt_concentration_top1_pct=_top1(by_cpt),
        provider_concentration_top1_pct=_top1(by_provider),
    )
