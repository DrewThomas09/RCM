"""FallbackSegmentAdapter — wraps the existing hand-rolled X12 subset.

This adapter is always available (zero new dependencies) and is the
documented *fallback*, never the primary, per acceptance criterion #19.
It satisfies :class:`ParserAdapter` by delegating segment extraction to
``rcm_mc.diligence.ingest.readers.read_edi`` and re-shaping the result
into the library-independent internal types.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import List

from ..ingest.ccd import SourceFormat
from ..ingest.readers import read_edi
from .base import (
    FileDetectionResult,
    ParsedFileMetadata,
    ParsedTransactionSet,
    ValidationReport,
)
from .detection import detect_file

def _envelope_issues(path: Path) -> List[str]:
    """Lightweight X12 envelope consistency check (ISA/IEA, GS/GE,
    ST/SE pairing). Independent of the segment parser's weak truncation
    heuristic so a file that ends mid-transaction without an SE/IEA
    trailer is flagged."""
    issues: List[str] = []
    try:
        text = path.read_text(encoding="latin-1")
    except OSError as exc:
        return [f"could not read file: {exc}"]
    # Tolerate either ~ or any single non-alnum segment terminator; we
    # only need to count envelope tags, so split on common terminators.
    tags = [seg.strip().split("*")[0].split(":")[0]
            for seg in text.replace("\r", "").replace("\n", "").split("~")
            if seg.strip()]
    if not tags:
        return ["empty file"]

    def _bal(open_tag: str, close_tag: str, label: str) -> None:
        o, c = tags.count(open_tag), tags.count(close_tag)
        if o != c:
            issues.append(
                f"{label} envelope unbalanced: {o}× {open_tag} vs {c}× {close_tag}")

    if "ISA" in tags:
        _bal("ISA", "IEA", "interchange")
        _bal("GS", "GE", "functional-group")
        _bal("ST", "SE", "transaction")
    return issues


_PAYLOAD_KEYS = (
    "claim_id", "patient_id", "cpt_code", "icd10_primary", "payer",
    "service_date_from", "service_date_to", "charge_amount",
    "paid_amount", "status_code",
)


class FallbackSegmentAdapter:
    name = "fallback_segment"

    def detect(self, path: Path | str) -> FileDetectionResult:
        return detect_file(path)

    def parse(self, path: Path | str) -> List[ParsedTransactionSet]:
        p = Path(path)
        result = read_edi(p)
        if not result.rows:
            return []
        fmt = result.rows[0].source_format
        if fmt == SourceFormat.EDI_835:
            txn_type = "835"
        elif fmt == SourceFormat.EDI_837:
            # The fallback parser does not distinguish P vs I; detection
            # refines that. Default to 837P (the common professional case).
            det = detect_file(p)
            txn_type = next(
                (t for t in det.detected_transaction_types if t.startswith("837")),
                "837P",
            )
        else:
            txn_type = "unknown"
        payload = [
            {k: row.values.get(k) for k in _PAYLOAD_KEYS}
            for row in result.rows
        ]
        return [ParsedTransactionSet(
            transaction_type=txn_type,
            raw_segments_reference=str(p),
            parsed_payload=payload,
        )]

    def validate(self, path: Path | str) -> ValidationReport:
        p = Path(path)
        result = read_edi(p)
        errors: List[str] = []
        envelope_issues = _envelope_issues(p)
        if result.malformed and not envelope_issues:
            envelope_issues.append(
                result.note or "file appears truncated or malformed")
        if not result.rows:
            errors.append("no claim/remittance segments extracted")
        is_valid = (
            not result.malformed
            and not envelope_issues
            and bool(result.rows)
        )
        return ValidationReport(
            is_valid=is_valid,
            parser_name=self.name,
            errors=errors,
            warnings=([result.note] if result.note and not result.malformed else []),
            envelope_issues=envelope_issues,
        )

    def extract_metadata(self, path: Path | str) -> ParsedFileMetadata:
        p = Path(path)
        det = detect_file(p)
        result = read_edi(p)
        return ParsedFileMetadata(
            parser_name=self.name,
            transaction_count=len(det.detected_transaction_types) or (1 if result.rows else 0),
            segment_count=len(result.rows),
            delimiters=det.detected_delimiters,
            parse_timestamp=datetime.now(timezone.utc).isoformat(),
        )
