"""Data Confidence Score + plain-English data-quality summary.

PE users must be able to trust (or distrust) the snapshot. This module
turns the CCD — plus optional match results — into a single 0..100
score AND, more importantly, a detailed issue list and plain-English
summaries (plan §"DATA QUALITY AND RECONCILIATION").

The score is deliberately conservative: deficiencies deduct from 100.
The *issue list* is the load-bearing output; the scalar is a glanceable
roll-up, never a substitute for the detail.

Pure function over already-built artifacts — no IO, no parser coupling.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from ..benchmarks._ansi_codes import DenialCategory, classify_carc
from ..ingest.ccd import CanonicalClaimsDataset, PayerClass


@dataclass
class DataQualityIssue:
    severity: str        # "INFO" | "WARN" | "ERROR"
    issue_type: str
    entity_type: str     # "claim" | "payer" | "provider" | "match" | "file"
    message: str
    count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return vars(self)


@dataclass
class DataConfidenceReport:
    score: int                              # 0..100
    issues: List[DataQualityIssue] = field(default_factory=list)
    summaries: List[str] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "issues": [i.to_dict() for i in self.issues],
            "summaries": list(self.summaries),
            "metrics": self.metrics,
        }


def _pct(num: int, den: int) -> float:
    return (num / den) if den else 0.0


def _sum_charges(rows: Sequence[Dict[str, Any]]) -> float:
    total = 0.0
    for r in rows:
        v = r.get("charge_amount")
        try:
            if v is not None:
                total += float(v)
        except (TypeError, ValueError):
            pass
    return total


def compute_data_confidence(
    ccd: CanonicalClaimsDataset,
    *,
    match_result: Optional[Any] = None,        # matching.MatchResult
    submitted: Optional[Sequence[Dict[str, Any]]] = None,
    remittance: Optional[Sequence[Dict[str, Any]]] = None,
) -> DataConfidenceReport:
    claims = ccd.claims
    n = len(claims)
    issues: List[DataQualityIssue] = []
    summaries: List[str] = []
    metrics: Dict[str, float] = {}

    if n == 0:
        return DataConfidenceReport(
            score=0,
            issues=[DataQualityIssue("ERROR", "no_claims", "file",
                                     "no claims were extracted from the snapshot")],
            summaries=["No claims were extracted — the snapshot could not be parsed."],
            metrics={"claims": 0},
        )

    score = 100.0

    # ── Field-completeness metrics ─────────────────────────────────
    payer_ok = sum(1 for c in claims if c.payer_class != PayerClass.UNKNOWN)
    npi_ok = sum(1 for c in claims if (c.billing_npi or c.rendering_npi))
    date_ok = sum(1 for c in claims if c.service_date_from)
    charge_ok = sum(1 for c in claims if c.charge_amount is not None)

    payer_pct = _pct(payer_ok, n)
    npi_pct = _pct(npi_ok, n)
    date_pct = _pct(date_ok, n)
    charge_pct = _pct(charge_ok, n)
    metrics.update(
        claims=n, payer_resolved_pct=round(payer_pct, 4),
        npi_present_pct=round(npi_pct, 4),
        service_date_present_pct=round(date_pct, 4),
        charge_present_pct=round(charge_pct, 4),
    )
    summaries.append(f"Captured a charge amount on {charge_pct * 100:.1f}% of claims.")
    summaries.append(f"Resolved a payer class on {payer_pct * 100:.1f}% of claims.")

    def _deduct(pct: float, floor: float, weight: float, *,
                issue_type: str, entity: str, label: str) -> None:
        nonlocal score
        if pct < floor:
            shortfall = (floor - pct) / floor
            score -= weight * shortfall
            issues.append(DataQualityIssue(
                "WARN", issue_type, entity,
                f"{label}: {pct * 100:.1f}% (below {floor * 100:.0f}% threshold)",
                count=n - int(round(pct * n)),
            ))

    _deduct(charge_pct, 0.95, 15.0, issue_type="missing_charge",
            entity="claim", label="charge amount present")
    _deduct(payer_pct, 0.95, 15.0, issue_type="unresolved_payer",
            entity="payer", label="payer class resolved")
    _deduct(npi_pct, 0.90, 10.0, issue_type="missing_npi",
            entity="provider", label="provider NPI present")
    _deduct(date_pct, 0.95, 10.0, issue_type="missing_service_date",
            entity="claim", label="service date present")

    # ── Adjustment-code mapping ────────────────────────────────────
    adj_total = adj_mapped = 0
    for c in claims:
        for code in (c.adjustment_reason_codes or ()):
            adj_total += 1
            if classify_carc(code) != DenialCategory.UNCLASSIFIED:
                adj_mapped += 1
    if adj_total:
        mapped_pct = _pct(adj_mapped, adj_total)
        metrics["adjustment_codes_mapped_pct"] = round(mapped_pct, 4)
        summaries.append(
            f"Mapped {mapped_pct * 100:.1f}% of adjustment reason codes to a "
            f"diligence category.")
        if mapped_pct < 0.90:
            score -= 10.0 * ((0.90 - mapped_pct) / 0.90)
            issues.append(DataQualityIssue(
                "WARN", "unmapped_adjustment_codes", "claim",
                f"{adj_total - adj_mapped} of {adj_total} adjustment codes are "
                f"unmapped (manual review)", count=adj_total - adj_mapped))

    # ── Duplicate claim ids ────────────────────────────────────────
    distinct = len({c.claim_id for c in claims if c.claim_id})
    dup = n - distinct
    metrics["duplicate_claim_rows"] = dup
    if dup > 0:
        score -= min(10.0, 10.0 * _pct(dup, n))
        issues.append(DataQualityIssue(
            "WARN", "duplicate_claims", "claim",
            f"{dup} claim rows share a claim id with another row "
            f"(possible resubmits/lines)", count=dup))

    # ── Matching coverage ──────────────────────────────────────────
    if match_result is not None:
        counts = match_result.counts()
        matched = counts.get("high", 0) + counts.get("medium", 0) + counts.get("low", 0)
        n_sub = matched + counts.get("unmatched_submitted", 0)
        low = counts.get("low", 0)
        if n_sub:
            match_pct = _pct(matched, n_sub)
            high_pct = _pct(counts.get("high", 0), n_sub)
            metrics["submitted_matched_pct"] = round(match_pct, 4)
            summaries.append(
                f"Matched {match_pct * 100:.1f}% of submitted claims to remittance "
                f"records ({high_pct * 100:.1f}% high-confidence).")
            score -= 20.0 * (1.0 - match_pct)
            if low:
                score -= min(10.0, 10.0 * _pct(low, n_sub))
                issues.append(DataQualityIssue(
                    "WARN", "low_confidence_matches", "match",
                    f"{low} matches are low-confidence and need analyst review",
                    count=low))
            if counts.get("unmatched_submitted", 0):
                issues.append(DataQualityIssue(
                    "WARN", "unmatched_submitted", "match",
                    f"{counts['unmatched_submitted']} submitted claims have no "
                    f"remittance match", count=counts["unmatched_submitted"]))

    # ── Dollar reconciliation (optional, when both sides supplied) ──
    if submitted is not None and remittance is not None and match_result is not None:
        sub_total = _sum_charges(submitted)
        matched_sub_keys = {m.submitted_key for m in match_result.matches}
        sub_by_key = {
            (c.get("claim_id") or f"_row{i}"): c for i, c in enumerate(submitted)
        }
        matched_dollars = _sum_charges(
            [sub_by_key[k] for k in matched_sub_keys if k in sub_by_key])
        unreconciled = max(0.0, sub_total - matched_dollars)
        if sub_total > 0:
            metrics["submitted_dollars_matched_pct"] = round(matched_dollars / sub_total, 4)
            summaries.append(
                f"Matched {matched_dollars / sub_total * 100:.1f}% of submitted "
                f"claim dollars to remittance records.")
            if unreconciled > 0:
                summaries.append(
                    f"${unreconciled:,.0f} in submitted charges could not be "
                    f"reconciled to remittance and is excluded from "
                    f"high-confidence conclusions.")

    final = int(max(0.0, min(100.0, round(score))))
    return DataConfidenceReport(
        score=final, issues=issues, summaries=summaries, metrics=metrics)
