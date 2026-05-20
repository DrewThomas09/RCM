"""Parser adapter boundary for healthcare EDI snapshots.

The V2 module must not be locked to one X12 library. Every parser
candidate (the existing hand-rolled subset, ``x12-python``, ``pyx12``,
…) is wrapped behind :class:`ParserAdapter` and emits the same
library-independent internal types defined here.

Downstream code (normalization, the CCD builder, matching, analytics)
depends only on these types — never on a parser's own object model.
That is the swap-ability guarantee the plan calls for
(``docs/healthcare-revenue-leakage-v2-plan.md`` §4).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


# ── Internal, library-independent result types ──────────────────────


@dataclass
class Delimiters:
    """X12 delimiters, normally read from the ISA segment.

    ISA is fixed-width: the element separator is ISA[3] (the 4th byte),
    the component (sub-element) separator is ISA element 16, and the
    segment terminator is the byte immediately after that element.
    """
    element: str = "*"
    component: str = ":"
    segment: str = "~"
    repetition: Optional[str] = None


@dataclass
class FileDetectionResult:
    file_type: str                       # "edi" | "csv" | "tsv" | "xlsx" | "parquet" | "zip" | "unknown"
    is_x12: bool = False
    detected_transaction_types: List[str] = field(default_factory=list)  # ["835"], ["837P"], …
    detected_delimiters: Optional[Delimiters] = None
    is_multi_transaction: bool = False
    confidence: float = 0.0              # 0..1
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_type": self.file_type,
            "is_x12": self.is_x12,
            "detected_transaction_types": list(self.detected_transaction_types),
            "detected_delimiters": (
                vars(self.detected_delimiters) if self.detected_delimiters else None
            ),
            "is_multi_transaction": self.is_multi_transaction,
            "confidence": round(self.confidence, 3),
            "warnings": list(self.warnings),
        }


@dataclass
class ValidationReport:
    is_valid: bool
    parser_name: str
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    unsupported_segments: List[str] = field(default_factory=list)
    envelope_issues: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "parser_name": self.parser_name,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "unsupported_segments": list(self.unsupported_segments),
            "envelope_issues": list(self.envelope_issues),
        }


@dataclass
class ParsedFileMetadata:
    parser_name: str
    sender_id: Optional[str] = None
    receiver_id: Optional[str] = None
    interchange_control_number: Optional[str] = None
    functional_group_control_number: Optional[str] = None
    transaction_count: int = 0
    segment_count: int = 0
    delimiters: Optional[Delimiters] = None
    parse_timestamp: Optional[str] = None


@dataclass
class ParsedTransactionSet:
    """One ST…SE transaction, parser-independent.

    ``parsed_payload`` carries a list of normalized claim-shaped dicts
    (one per claim or claim-line) using the same key vocabulary the
    ingester's column-synonym map already understands, so the adapter
    output flows into the existing CCD builder without a second mapping
    layer. ``raw_segments_reference`` keeps a pointer back to source for
    traceability.
    """
    transaction_type: str                # "835" | "837P" | "837I" | "unknown"
    transaction_control_number: Optional[str] = None
    implementation_version: Optional[str] = None
    interchange_metadata: Dict[str, Any] = field(default_factory=dict)
    functional_group_metadata: Dict[str, Any] = field(default_factory=dict)
    raw_segments_reference: Optional[str] = None
    parsed_payload: List[Dict[str, Any]] = field(default_factory=list)


# ── The adapter contract ────────────────────────────────────────────


@runtime_checkable
class ParserAdapter(Protocol):
    """Every parser candidate implements this. Keep it minimal so a
    thin library wrapper can satisfy it."""

    name: str

    def detect(self, path: Path | str) -> FileDetectionResult: ...

    def parse(self, path: Path | str) -> List[ParsedTransactionSet]: ...

    def validate(self, path: Path | str) -> ValidationReport: ...

    def extract_metadata(self, path: Path | str) -> ParsedFileMetadata: ...


@dataclass
class AdapterAvailability:
    """Whether an adapter's backing library is importable. The harness
    and the ingester use this to skip unavailable adapters gracefully
    rather than hard-failing on a missing optional dependency."""
    name: str
    available: bool
    reason: str = ""
