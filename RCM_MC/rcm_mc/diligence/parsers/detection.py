"""File + X12 transaction detection.

This is the "File Detection Layer" from the plan. It is parser-agnostic:
it reads just enough of a file to classify it (type, X12-or-not,
transaction types, ISA delimiters, multi-transaction) so the upload
flow can route to the right adapter and surface warnings early.

ISA delimiter detection is the piece the legacy ``read_edi`` assumed
away (it hard-coded ``~ * :``). Real VDR exports vary, so we read the
fixed-width ISA segment to recover the actual delimiters.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from .base import Delimiters, FileDetectionResult

_X12_SUFFIXES = {".edi", ".txt", ".835", ".837"}
_TABULAR_SUFFIXES = {".csv": "csv", ".tsv": "tsv", ".xlsx": "xlsx",
                     ".xlsm": "xlsx", ".parquet": "parquet"}


def _read_head_bytes(path: Path, n: int = 4096) -> bytes:
    with open(path, "rb") as fh:
        return fh.read(n)


def detect_delimiters(head: str) -> Optional[Delimiters]:
    """Recover delimiters from a leading ISA segment.

    ISA is exactly 106 chars in canonical form: the element separator
    is the 4th char (index 3); element 16 (the component separator) is
    the 105th char (index 104); the segment terminator is the char
    right after it (index 105). We do not assume the canonical length —
    we locate ISA, take its element separator, split on it, and read the
    last element's first char as the component separator and the
    following char as the segment terminator.
    """
    idx = head.find("ISA")
    if idx == -1 or len(head) < idx + 4:
        return None
    element = head[idx + 3]
    rest = head[idx:]
    # The segment terminator is the char after the 16th element value.
    # Walk 16 element separators from ISA.
    parts = rest.split(element)
    if len(parts) < 17:
        return None
    component = parts[16][:1] or ":"
    # The terminator follows the component separator in the raw stream.
    after = rest.find(element.join(parts[:16]))
    seg_term = "~"
    # Find the component char then the next char is the terminator.
    comp_pos = rest.find(component, len(element.join(parts[:16])))
    if comp_pos != -1 and comp_pos + 1 < len(rest):
        candidate = rest[comp_pos + 1]
        if candidate not in (element, component) and not candidate.isalnum():
            seg_term = candidate
    return Delimiters(element=element, component=component, segment=seg_term)


def _transaction_types(head: str, delim: Delimiters) -> List[str]:
    """Find ST*<code> transaction types, refining 837 by the BHT/GS
    implementation hints when present (837P professional vs 837I
    institutional)."""
    types: List[str] = []
    segs = head.split(delim.segment)
    is_institutional = "X223" in head or "*11:" in head  # crude 837I hints
    is_professional = "X222" in head
    for seg in segs:
        elems = seg.split(delim.element)
        if elems and elems[0].strip() == "ST" and len(elems) > 1:
            code = elems[1].strip()
            if code == "837":
                if is_institutional and not is_professional:
                    types.append("837I")
                else:
                    types.append("837P")
            else:
                types.append(code)
    return types


def detect_file(path: Path | str) -> FileDetectionResult:
    p = Path(path)
    suffix = p.suffix.lower()

    if suffix == ".zip":
        return FileDetectionResult(file_type="zip", confidence=1.0)

    if suffix in _TABULAR_SUFFIXES:
        return FileDetectionResult(
            file_type=_TABULAR_SUFFIXES[suffix], confidence=0.9,
        )

    # Sniff content for X12 regardless of extension (.txt/.edi/.835/…).
    try:
        head = _read_head_bytes(p).decode("latin-1", errors="replace")
    except OSError as exc:
        return FileDetectionResult(
            file_type="unknown", confidence=0.0,
            warnings=[f"could not read file: {exc}"],
        )

    if "ISA" in head[:512] or head.lstrip().startswith("ISA"):
        delim = detect_delimiters(head) or Delimiters()
        txn = _transaction_types(head, delim)
        warnings: List[str] = []
        if not txn:
            warnings.append("X12 envelope detected but no ST transaction set found")
        return FileDetectionResult(
            file_type="edi",
            is_x12=True,
            detected_transaction_types=txn,
            detected_delimiters=delim,
            is_multi_transaction=len(txn) > 1,
            confidence=0.95 if txn else 0.6,
            warnings=warnings,
        )

    # No ISA but an X12-ish suffix: low-confidence, let a parser try.
    if suffix in _X12_SUFFIXES:
        return FileDetectionResult(
            file_type="edi", is_x12=False, confidence=0.3,
            warnings=["X12-like extension but no ISA envelope found"],
        )

    return FileDetectionResult(file_type="unknown", confidence=0.0,
                               warnings=[f"unrecognized file type: {suffix}"])
