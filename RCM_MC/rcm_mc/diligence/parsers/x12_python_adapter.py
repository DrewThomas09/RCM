"""X12PythonAdapter — primary parser, backed by the ``x12-python`` lib.

Imported only when ``x12`` is installed (see ``parsers/__init__`` guard),
so core ``rcm_mc`` keeps zero new *hard* dependencies; ``x12-python`` is
an optional ``[edi]`` extra. This adapter is richer than the fallback:
it recovers ISA delimiters + envelope metadata, the subscriber member
id (NM1*IL), CAS adjustment group/reason/amount triples, and the BPR
payment total — fields the hand-rolled fallback drops.

Output is the same library-independent ``ParsedTransactionSet`` the
fallback emits, so downstream (CCD builder, matching) is parser-blind.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import x12  # optional dep; import-guarded by parsers/__init__.available_adapters

from .base import (
    Delimiters,
    FileDetectionResult,
    ParsedFileMetadata,
    ParsedTransactionSet,
    ValidationReport,
)
from .detection import detect_file
from .fallback_adapter import _envelope_issues


def _flatten(loop) -> List[Any]:
    segs: List[Any] = list(getattr(loop, "segments", None) or [])
    for sub in (getattr(loop, "loops", None) or []):
        segs.extend(_flatten(sub))
    return segs


def _els(seg) -> List[str]:
    return [e.value if hasattr(e, "value") else str(e) for e in seg.elements]


def _f(v: Optional[str]) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except ValueError:
        return None


# NM1 ID-qualifier codes that introduce a patient/member identifier.
_MEMBER_ID_QUALIFIERS = {"MI", "MR", "II", "34", "HN", "MB"}


def _npi(els: List[str]) -> Optional[str]:
    """Pull an NPI from an NM1 element list — qualifier ``XX`` at NM108
    introduces the NPI at NM109."""
    for i, val in enumerate(els):
        if val == "XX" and i + 1 < len(els) and els[i + 1]:
            return els[i + 1]
    return None


def _member_id(els: List[str]) -> Optional[str]:
    """Pull the member/patient id from an NM1 element list (segment tag
    already stripped). NM108 is the ID qualifier and NM109 the ID; we
    scan for a known qualifier rather than hard-coding an index, since
    NM1 layouts vary across 835/837 and trailing empties differ by
    parser."""
    for i, val in enumerate(els):
        if val in _MEMBER_ID_QUALIFIERS and i + 1 < len(els) and els[i + 1]:
            return els[i + 1]
    return None


def _claims_from_837(segs: List[Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    cur: Optional[Dict[str, Any]] = None
    pending_payer: Optional[str] = None
    pending_patient: Optional[str] = None

    def _flush():
        nonlocal cur
        if cur and cur.get("claim_id"):
            rows.append(cur)
        cur = None

    pending_npi: Optional[str] = None
    for seg in segs:
        tag = seg.segment_id
        e = _els(seg)
        if tag == "NM1" and len(e) > 1:
            qual = e[0]
            if qual == "PR" and len(e) > 2:
                pending_payer = e[2]
            elif qual == "85":  # billing provider
                npi = _npi(e)
                if npi:
                    pending_npi = npi
            elif qual in ("IL", "QC"):
                mid = _member_id(e)
                if mid:
                    pending_patient = mid
        elif tag == "CLM":
            _flush()
            cur = {
                "claim_id": e[0] if e else None,
                "charge_amount": _f(e[1]) if len(e) > 1 else None,
                "payer": pending_payer,
                "patient_id": pending_patient,
                "billing_npi": pending_npi,
            }
            pending_payer = pending_patient = pending_npi = None
        elif cur is not None:
            if tag == "SV1" and e:
                parts = e[0].split(":")
                cur["cpt_code"] = parts[1] if len(parts) > 1 else parts[0]
            elif tag == "DTP" and len(e) > 2 and e[0] == "472":
                raw = e[2]
                if "-" in raw and len(raw) >= 17:
                    cur["service_date_from"] = raw[:8]
                    cur["service_date_to"] = raw[9:17]
                else:
                    cur["service_date_from"] = raw
            elif tag == "HI" and e and not cur.get("icd10_primary"):
                parts = e[0].split(":")
                if len(parts) > 1:
                    cur["icd10_primary"] = parts[1]
    _flush()
    return rows


def _claims_from_835(segs: List[Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    cur: Optional[Dict[str, Any]] = None
    cur_payer: Optional[str] = None
    cur_npi: Optional[str] = None

    def _flush():
        nonlocal cur
        if cur and cur.get("claim_id"):
            rows.append(cur)
        cur = None

    for seg in segs:
        tag = seg.segment_id
        e = _els(seg)
        if tag == "N1" and len(e) > 1 and e[0] == "PR":
            cur_payer = e[1]
        elif tag == "N1" and len(e) > 1 and e[0] == "PE":
            cur_npi = _npi(e)
        elif tag == "CLP":
            _flush()
            cur = {
                "claim_id": e[0] if e else None,
                "status_code": e[1] if len(e) > 1 else None,
                "charge_amount": _f(e[2]) if len(e) > 2 else None,
                "paid_amount": _f(e[3]) if len(e) > 3 else None,
                "patient_responsibility": _f(e[4]) if len(e) > 4 else None,
                "payer": cur_payer,
                "billing_npi": cur_npi,
                "adjustment_reason_codes": [],
                "adjustment_amount": 0.0,
            }
        elif cur is not None:
            if tag == "CAS":
                # CAS*<group>*<reason1>*<amt1>*<qty1>*<reason2>*<amt2>...
                # group at e[0]; (reason, amount, quantity) triples from e[1].
                i = 1
                while i < len(e):
                    reason = e[i]
                    amt = _f(e[i + 1]) if i + 1 < len(e) else None
                    if reason:
                        cur["adjustment_reason_codes"].append(reason)
                    if amt:
                        cur["adjustment_amount"] = (cur.get("adjustment_amount") or 0.0) + amt
                    i += 3
            elif tag == "NM1" and e and e[0] == "QC":
                mid = _member_id(e)
                if mid:
                    cur["patient_id"] = mid
            elif tag == "SVC" and e:
                parts = e[0].split(":")
                cur["cpt_code"] = parts[1] if len(parts) > 1 else parts[0]
            elif tag == "DTM" and len(e) > 1 and e[0] in ("232", "472", "050"):
                cur.setdefault("service_date_from", e[1])
    _flush()
    # Normalize adjustment codes to tuples for CCD compatibility.
    for r in rows:
        r["adjustment_reason_codes"] = tuple(r.get("adjustment_reason_codes") or ())
    return rows


class X12PythonAdapter:
    name = "x12_python"

    def detect(self, path: Path | str) -> FileDetectionResult:
        return detect_file(path)

    def parse(self, path: Path | str) -> List[ParsedTransactionSet]:
        content = Path(path).read_text(encoding="latin-1")
        inter = x12.Parser().parse(content)
        out: List[ParsedTransactionSet] = []
        for fg in inter.functional_groups:
            for ts in fg.transactions:
                segs = _flatten(ts.root_loop)
                code = str(ts.transaction_set_id)
                if code == "835":
                    payload = _claims_from_835(segs)
                    txn_type = "835"
                elif code == "837":
                    payload = _claims_from_837(segs)
                    txn_type = "837P"
                else:
                    payload, txn_type = [], "unknown"
                out.append(ParsedTransactionSet(
                    transaction_type=txn_type,
                    transaction_control_number=str(ts.control_number),
                    implementation_version=str(getattr(ts, "version", "") or ""),
                    interchange_metadata={
                        "sender_id": inter.sender_id,
                        "receiver_id": inter.receiver_id,
                        "interchange_control_number": inter.control_number,
                    },
                    functional_group_metadata={
                        "control_number": fg.control_number,
                    },
                    raw_segments_reference=str(path),
                    parsed_payload=payload,
                ))
        return out

    def validate(self, path: Path | str) -> ValidationReport:
        p = Path(path)
        errors: List[str] = []
        try:
            sets = self.parse(p)
        except Exception as exc:  # noqa: BLE001
            return ValidationReport(
                is_valid=False, parser_name=self.name,
                errors=[f"{type(exc).__name__}: {exc}"],
                envelope_issues=["x12-python could not parse the interchange"],
            )
        envelope_issues = _envelope_issues(p)
        n_claims = sum(len(s.parsed_payload) for s in sets)
        if n_claims == 0:
            errors.append("no claims extracted")
        return ValidationReport(
            is_valid=(not envelope_issues and n_claims > 0),
            parser_name=self.name,
            errors=errors,
            envelope_issues=envelope_issues,
        )

    def extract_metadata(self, path: Path | str) -> ParsedFileMetadata:
        p = Path(path)
        content = p.read_text(encoding="latin-1")
        inter = x12.Parser().parse(content)
        d = inter.delimiters
        txn_count = sum(len(fg.transactions) for fg in inter.functional_groups)
        seg_count = sum(
            len(_flatten(ts.root_loop))
            for fg in inter.functional_groups for ts in fg.transactions
        )
        return ParsedFileMetadata(
            parser_name=self.name,
            sender_id=inter.sender_id,
            receiver_id=inter.receiver_id,
            interchange_control_number=str(inter.control_number),
            transaction_count=txn_count,
            segment_count=seg_count,
            delimiters=Delimiters(
                element=getattr(d, "element", "*"),
                component=getattr(d, "component", ":"),
                segment=getattr(d, "segment", "~"),
                repetition=getattr(d, "repetition", None),
            ),
            parse_timestamp=datetime.now(timezone.utc).isoformat(),
        )
