"""Snapshot pipeline orchestrator.

Chains the V2 module end-to-end for a set of uploaded EDI files:

    files -> detect/parse (adapters) -> CCD (837+835 merged by claim)
    -> PHI tokenize -> 837<->835 match -> data confidence -> analytics
    -> findings + follow-ups -> Markdown memo

Snapshot-only: no live integrations. This is the single call the upload
flow (and tests) use to turn a VDR drop into investor-grade output.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .analytics import AnalyticsResult, compute_analytics
from .findings import (
    Finding,
    FollowUpPackage,
    generate_findings,
    generate_follow_ups,
)
from .ingest.ccd import (
    CanonicalClaim,
    CanonicalClaimsDataset,
    ClaimStatus,
    TransformationLog,
)
from .ingest.normalize import parse_date, resolve_payer
from .matching import MatchResult, match_claims
from .parsers import available_adapters
from .reconciliation import DataConfidenceReport, compute_data_confidence
from .reporting import MemoContext, render_markdown_memo
from .security import PhiTokenizer, new_salt, tokenize_ccd

# 835 CLP02 claim-status → CCD ClaimStatus.
_CLP_STATUS = {
    "1": ClaimStatus.PAID, "2": ClaimStatus.PAID, "3": ClaimStatus.PAID,
    "4": ClaimStatus.DENIED, "19": ClaimStatus.PAID, "22": ClaimStatus.REWORK,
    "23": ClaimStatus.REWORK,
}


@dataclass
class BuildResult:
    ccd: CanonicalClaimsDataset
    submitted: List[Dict[str, Any]] = field(default_factory=list)
    remittance: List[Dict[str, Any]] = field(default_factory=list)
    transaction_types: List[str] = field(default_factory=list)
    parser_used: str = ""


@dataclass
class SnapshotResult:
    ccd: CanonicalClaimsDataset
    match: MatchResult
    confidence: DataConfidenceReport
    analytics: AnalyticsResult
    findings: List[Finding]
    follow_ups: FollowUpPackage
    memo_markdown: str
    transaction_types: List[str] = field(default_factory=list)
    parser_used: str = ""
    salt: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ingest_id": self.ccd.ingest_id,
            "content_hash": self.ccd.content_hash(),
            "match": self.match.to_dict(),
            "confidence": self.confidence.to_dict(),
            "analytics": self.analytics.to_dict(),
            "findings": [f.to_dict() for f in self.findings],
            "follow_ups": self.follow_ups.to_dict(),
            "transaction_types": self.transaction_types,
            "parser_used": self.parser_used,
        }


def _row_id(*parts: Any) -> str:
    return hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()[:12]


def _status_for(payload: Dict[str, Any], is_remittance: bool) -> ClaimStatus:
    if not is_remittance:
        return ClaimStatus.SUBMITTED
    code = (payload.get("status_code") or "").strip()
    return _CLP_STATUS.get(code, ClaimStatus.UNKNOWN)


def _build_claim(
    payload: Dict[str, Any], *, source_file: str, source_system: str,
    idx: int, log: TransformationLog, is_remittance: bool,
    enrich: Optional[Dict[str, Any]] = None,
) -> CanonicalClaim:
    enrich = enrich or {}
    claim_id = str(payload.get("claim_id") or f"_row{idx}")
    rid = _row_id(claim_id, source_system, idx)
    payer_raw, payer_canon, payer_class = resolve_payer(
        payload.get("payer") or enrich.get("payer"), log,
        ccd_row_id=rid, source_file=source_file, source_row=idx)

    def _date(key: str) -> Any:
        raw = payload.get(key) or enrich.get(key)
        if not raw:
            return None
        return parse_date(raw, log, ccd_row_id=rid, source_file=source_file,
                          source_row=idx, target_field=key)

    codes = tuple(payload.get("adjustment_reason_codes") or ())
    return CanonicalClaim(
        claim_id=claim_id, line_number=1, source_system=source_system,
        source_file=source_file, source_row=idx, ccd_row_id=rid,
        patient_id=str(payload.get("patient_id") or enrich.get("patient_id") or ""),
        service_date_from=_date("service_date_from"),
        service_date_to=_date("service_date_to"),
        cpt_code=payload.get("cpt_code") or enrich.get("cpt_code"),
        icd10_primary=payload.get("icd10_primary") or enrich.get("icd10_primary"),
        billing_npi=payload.get("billing_npi") or enrich.get("billing_npi"),
        payer_raw=payer_raw, payer_canonical=payer_canon, payer_class=payer_class,
        charge_amount=payload.get("charge_amount") if payload.get("charge_amount") is not None
            else enrich.get("charge_amount"),
        paid_amount=payload.get("paid_amount"),
        patient_responsibility=payload.get("patient_responsibility"),
        adjustment_amount=payload.get("adjustment_amount"),
        adjustment_reason_codes=codes,
        status=_status_for(payload, is_remittance),
    )


def build_ccd_from_files(paths: Sequence[Path | str]) -> BuildResult:
    """Parse EDI files with the best available adapter and build a CCD.

    Remittance (835) rows are the financial source of truth and are
    enriched by their submitted (837) counterpart (CPT/NPI/ICD/charge)
    via claim_id. Submitted claims with no remittance become
    SUBMITTED-status rows so unmatched billings still appear.
    """
    adapters = available_adapters()
    primary = adapters[0]
    submitted: List[Dict[str, Any]] = []
    remittance: List[Dict[str, Any]] = []
    txn_types: List[str] = []

    for p in paths:
        path = Path(p)
        adapter = primary
        # Per-file: prefer the primary, but any adapter that validates wins.
        for cand in adapters:
            try:
                if cand.validate(path).is_valid:
                    adapter = cand
                    break
            except Exception:  # noqa: BLE001
                continue
        for ts in adapter.parse(path):
            txn_types.append(ts.transaction_type)
            tagged = [dict(row, _source_file=path.name) for row in ts.parsed_payload]
            if ts.transaction_type == "835":
                remittance.extend(tagged)
            else:
                submitted.extend(tagged)

    sub_by_id = {r["claim_id"]: r for r in submitted if r.get("claim_id")}
    rem_ids = {r["claim_id"] for r in remittance if r.get("claim_id")}

    log = TransformationLog()
    claims: List[CanonicalClaim] = []
    for i, r in enumerate(remittance):
        claims.append(_build_claim(
            r, source_file=r.get("_source_file", "835.edi"),
            source_system="edi_835", idx=i, log=log, is_remittance=True,
            enrich=sub_by_id.get(r.get("claim_id"))))
    for i, s in enumerate(submitted):
        if s.get("claim_id") in rem_ids:
            continue  # already represented by its remittance row
        claims.append(_build_claim(
            s, source_file=s.get("_source_file", "837.edi"),
            source_system="edi_837", idx=i, log=log, is_remittance=False))

    src_files = sorted({c.source_file for c in claims})
    ingest_id = hashlib.sha256("|".join(src_files).encode()).hexdigest()[:16]
    ccd = CanonicalClaimsDataset(
        claims=claims, log=log, source_files=src_files, ingest_id=ingest_id)
    return BuildResult(
        ccd=ccd, submitted=submitted, remittance=remittance,
        transaction_types=sorted(set(txn_types)), parser_used=primary.name)


def run_snapshot_from_zip(
    zip_path: Path | str, *,
    deal_name: str = "Target", salt: Optional[str] = None,
) -> SnapshotResult:
    """Extract a VDR ZIP to a temp dir and run the snapshot over its
    supported files. The temp dir is cleaned up afterwards."""
    import tempfile

    from .ingestion import extract_zip

    with tempfile.TemporaryDirectory(prefix="hcrl_zip_") as tmp:
        res = extract_zip(zip_path, tmp)
        if not res.extracted_files:
            raise ValueError(
                "no supported EDI files in archive: "
                + ("; ".join(res.warnings) or "empty"))
        return run_snapshot(res.extracted_files, deal_name=deal_name, salt=salt)


def run_snapshot(
    paths: Sequence[Path | str], *,
    deal_name: str = "Target", salt: Optional[str] = None,
) -> SnapshotResult:
    """End-to-end: files → CCD → tokenize → match → confidence →
    analytics → findings → memo."""
    build = build_ccd_from_files(paths)
    salt = salt or new_salt()
    tokenize_ccd(build.ccd, PhiTokenizer(salt=salt))
    match = match_claims(build.submitted, build.remittance)
    confidence = compute_data_confidence(
        build.ccd, match_result=match,
        submitted=build.submitted, remittance=build.remittance)
    analytics = compute_analytics(build.ccd)
    findings = generate_findings(analytics, confidence, match_result=match)
    follow_ups = generate_follow_ups(findings)
    memo = render_markdown_memo(
        analytics=analytics, confidence=confidence, findings=findings,
        follow_ups=follow_ups,
        context=MemoContext(
            deal_name=deal_name, source_file_count=len(paths),
            transaction_types=build.transaction_types))
    return SnapshotResult(
        ccd=build.ccd, match=match, confidence=confidence, analytics=analytics,
        findings=findings, follow_ups=follow_ups, memo_markdown=memo,
        transaction_types=build.transaction_types,
        parser_used=build.parser_used, salt=salt)
