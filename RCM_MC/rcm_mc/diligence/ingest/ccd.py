"""Canonical Claims Dataset (CCD) — the data contract.

The CCD is the single artefact every downstream diligence phase reads
from. Partners and CFOs can defend a number to a skeptical auditor by
walking:

    KPI  →  CCD rows that feed it  →  TransformationLog entries  →
    source file + source row + rule

Everything in this module is *schema*, not logic. The ingester (and
Phase 2/3/4) live alongside.

Why a dataclass rather than a SQLAlchemy model: the CCD has to be
cheap to produce in a test harness and cheap to hash for dedup in the
packet's observed-metrics cache. A dict-shaped dataclass round-trips
to JSON cleanly and a blob of bytes to SHA-256 cleanly — no ORM
coupling, no per-deal table proliferation.

Storage is an additive SQLite table per the CLAUDE.md "SQLite via
sqlite3 stdlib — 17 tables, idempotent CREATE TABLE IF NOT EXISTS
migrations" convention. See :func:`ccd_store.save_ccd` for the write
path.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple


# ── Schema version ──────────────────────────────────────────────────
#
# Bump this when the CCD contract changes in a way that would
# invalidate a previously-stored dataset (e.g., renaming a field,
# changing a type, tightening a constraint). Readers check this
# before trusting a stored CCD's KPI-derivation.
CCD_SCHEMA_VERSION = "1.0.0"


# ── Enums ──────────────────────────────────────────────────────────

class ClaimStatus(str, Enum):
    """Lifecycle state for a canonical claim row.

    We preserve submit + each adjudication separately (rather than
    collapsing to a final state up-front) because Phase 3's ZBA
    autopsy needs the full trail to identify recoverable write-offs.
    """
    SUBMITTED = "SUBMITTED"
    ACCEPTED = "ACCEPTED"
    DENIED = "DENIED"
    PAID = "PAID"
    REWORK = "REWORK"      # appeal / correction in flight
    WRITTEN_OFF = "WRITTEN_OFF"
    UNKNOWN = "UNKNOWN"


class PayerClass(str, Enum):
    """Coarse payer classification — the resolution target for
    fixture_04 (payer typos). Phase 2 uses this for base-rate
    stratification; downstream analyses require a non-``UNKNOWN``
    value for the vast majority of rows."""
    MEDICARE = "MEDICARE"
    MEDICAID = "MEDICAID"
    COMMERCIAL = "COMMERCIAL"
    MEDICARE_ADVANTAGE = "MEDICARE_ADVANTAGE"
    TRICARE = "TRICARE"
    SELF_PAY = "SELF_PAY"
    WORKERS_COMP = "WORKERS_COMP"
    UNKNOWN = "UNKNOWN"


class SourceFormat(str, Enum):
    EDI_837 = "EDI_837"
    EDI_835 = "EDI_835"
    CSV = "CSV"
    TSV = "TSV"
    PARQUET = "PARQUET"
    EXCEL = "EXCEL"
    UNKNOWN = "UNKNOWN"


# ── The canonical row ───────────────────────────────────────────────

@dataclass
class CanonicalClaim:
    """One canonical claim-line. The grain is (claim_id, line_number,
    source_system) — same as Tuva's medical_claim, intentionally, so
    Phase 2 KPI math that follows Tuva's conventions ports cleanly.

    Every monetary field is a ``float`` in dollars (2dp at render).
    Nulls remain ``None`` rather than being zeroed — Phase 2 needs to
    distinguish "zero paid" from "paid amount unknown" to avoid
    silently deflating recovery estimates.
    """
    # Identity
    claim_id: str
    line_number: int
    source_system: str          # "epic_clinic_a" | "edi_837_primary" | etc.
    source_file: str            # relative path inside the ingest dir
    source_row: int             # 1-indexed row within source file
    ccd_row_id: str             # stable synthetic key — hashable

    # Patient
    patient_id: str             # resolved MRN-equivalent (post-normalisation)
    patient_dob: Optional[date] = None
    patient_sex: Optional[str] = None

    # Service
    service_date_from: Optional[date] = None
    service_date_to: Optional[date] = None
    place_of_service: Optional[str] = None
    bill_type: Optional[str] = None

    # Clinical
    cpt_code: Optional[str] = None
    cpt_modifiers: Tuple[str, ...] = ()
    icd10_primary: Optional[str] = None
    icd10_secondary: Tuple[str, ...] = ()
    drg: Optional[str] = None

    # Provider
    billing_npi: Optional[str] = None
    rendering_npi: Optional[str] = None
    facility: Optional[str] = None
    physician: Optional[str] = None

    # Payer
    payer_raw: Optional[str] = None                 # verbatim from source
    payer_canonical: Optional[str] = None            # resolved payer name
    payer_class: PayerClass = PayerClass.UNKNOWN

    # Amounts
    charge_amount: Optional[float] = None
    allowed_amount: Optional[float] = None
    paid_amount: Optional[float] = None
    patient_responsibility: Optional[float] = None
    adjustment_amount: Optional[float] = None
    adjustment_reason_codes: Tuple[str, ...] = ()

    # Lifecycle
    status: ClaimStatus = ClaimStatus.UNKNOWN
    submit_date: Optional[date] = None
    paid_date: Optional[date] = None
    denial_date: Optional[date] = None
    denial_reason: Optional[str] = None

    # Provenance on the row itself — Phase 3 joins on this to surface
    # "which source file fed this KPI" without a second scan.
    ingest_datetime: Optional[str] = None           # UTC ISO string
    ccd_schema_version: str = CCD_SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return _json_safe(asdict(self))


# ── The transformation log ──────────────────────────────────────────

@dataclass
class Transformation:
    """One row-logged transformation. The analyst can answer the
    question "why does ccd_row X claim a payer_class of MEDICARE?" by
    filtering TransformationLog rows where ``ccd_row_id = X`` and
    ``target_field = payer_class``, then reading the chain.
    """
    ccd_row_id: str
    source_file: str
    source_row: int
    target_field: str
    source_value: Optional[str]
    coerced_value: Optional[str]
    rule: str                   # "synonym_map:payer" | "date_parse:mdy" | …
    severity: str = "INFO"      # "INFO" | "WARN" | "ERROR"
    note: str = ""
    at_utc: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return _json_safe(asdict(self))


@dataclass
class TransformationLog:
    """Append-only log of row-level transformations. Queryable by
    Phase 2+ to defend a KPI to a skeptical reader."""
    entries: List[Transformation] = field(default_factory=list)

    def log(
        self,
        *,
        ccd_row_id: str,
        source_file: str,
        source_row: int,
        target_field: str,
        source_value: Any,
        coerced_value: Any,
        rule: str,
        severity: str = "INFO",
        note: str = "",
    ) -> None:
        self.entries.append(Transformation(
            ccd_row_id=ccd_row_id,
            source_file=source_file,
            source_row=source_row,
            target_field=target_field,
            source_value=_stringify(source_value),
            coerced_value=_stringify(coerced_value),
            rule=rule,
            severity=severity,
            note=note,
            at_utc=datetime.now(timezone.utc).isoformat(),
        ))

    def by_row(self, ccd_row_id: str) -> List[Transformation]:
        return [t for t in self.entries if t.ccd_row_id == ccd_row_id]

    def by_rule(self, rule: str) -> List[Transformation]:
        return [t for t in self.entries if t.rule == rule]

    def summary(self) -> Dict[str, int]:
        """Count entries per rule. Cheap dashboard for the analyst."""
        counts: Dict[str, int] = {}
        for t in self.entries:
            counts[t.rule] = counts.get(t.rule, 0) + 1
        return counts

    def to_dict(self) -> Dict[str, Any]:
        return {"entries": [e.to_dict() for e in self.entries]}

    def to_json(self, *, indent: int = 2, sort_keys: bool = True) -> str:
        return json.dumps(
            self.to_dict(), indent=indent, sort_keys=sort_keys,
            default=_json_default,
        )


# ── The dataset wrapper ─────────────────────────────────────────────

@dataclass
class CanonicalClaimsDataset:
    """A whole CCD — claims + transformation log + provenance.

    ``content_hash`` is a deterministic sha256 over claims + log with
    wall-clock fields excluded. Running the same ingest twice on the
    same inputs produces the same hash — this is the dedup key in the
    packet's observed_metrics cache.
    """
    claims: List[CanonicalClaim] = field(default_factory=list)
    log: TransformationLog = field(default_factory=TransformationLog)
    source_files: List[str] = field(default_factory=list)
    ccd_schema_version: str = CCD_SCHEMA_VERSION
    generator: str = "rcm_mc.diligence.ingest"
    ingest_id: str = ""

    # ------- serialisation -----------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claims": [c.to_dict() for c in self.claims],
            "log": self.log.to_dict(),
            "source_files": list(self.source_files),
            "ccd_schema_version": self.ccd_schema_version,
            "generator": self.generator,
            "ingest_id": self.ingest_id,
        }

    def to_json(self, *, indent: int = 2, sort_keys: bool = True) -> str:
        return json.dumps(
            self.to_dict(), indent=indent, sort_keys=sort_keys,
            default=_json_default,
        )

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "CanonicalClaimsDataset":
        claims = [_claim_from_dict(c) for c in (d.get("claims") or [])]
        log_entries = [
            Transformation(**{
                **t,
                "source_value": t.get("source_value"),
                "coerced_value": t.get("coerced_value"),
            })
            for t in ((d.get("log") or {}).get("entries") or [])
        ]
        return cls(
            claims=claims,
            log=TransformationLog(entries=log_entries),
            source_files=list(d.get("source_files") or []),
            ccd_schema_version=d.get("ccd_schema_version", CCD_SCHEMA_VERSION),
            generator=d.get("generator", "rcm_mc.diligence.ingest"),
            ingest_id=d.get("ingest_id", ""),
        )

    @classmethod
    def from_json(cls, s: str) -> "CanonicalClaimsDataset":
        return cls.from_dict(json.loads(s))

    # ------- hashing ------------------------------------------------

    def content_hash(self) -> str:
        """Deterministic sha256 over claims + summary of the log.

        Excludes: ingest_datetime on rows, at_utc on log entries, and
        ingest_id on the dataset (all wall-time-ish). Same invariant
        as ``rcm_mc.analysis.packet.hash_inputs``.
        """
        d = self.to_dict()
        for c in d["claims"]:
            c.pop("ingest_datetime", None)
        for e in d["log"]["entries"]:
            e.pop("at_utc", None)
        d.pop("ingest_id", None)
        payload = json.dumps(d, sort_keys=True, default=_json_default)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    # ------- Phase-2-facing helpers --------------------------------

    def rows_by_claim_id(self, claim_id: str) -> List[CanonicalClaim]:
        return [c for c in self.claims if c.claim_id == claim_id]

    def distinct_payer_classes(self) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for c in self.claims:
            out[c.payer_class.value] = out.get(c.payer_class.value, 0) + 1
        return out

    # ------- IO -----------------------------------------------------

    def write(self, output_dir: Path | str) -> Tuple[Path, Path]:
        """Write ``ccd.json`` + ``transformation_log.json`` into
        ``output_dir``. Returns the two paths."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        ccd_p = out / "ccd.json"
        log_p = out / "transformation_log.json"
        ccd_p.write_text(self.to_json(), encoding="utf-8")
        log_p.write_text(self.log.to_json(), encoding="utf-8")
        return ccd_p, log_p


# ── Helpers ────────────────────────────────────────────────────────

def _json_safe(v: Any) -> Any:
    if v is None or isinstance(v, (bool, int, str)):
        return v
    if isinstance(v, float):
        if v != v or v in (float("inf"), float("-inf")):
            return None
        return v
    if isinstance(v, Enum):
        return v.value
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, (list, tuple, set)):
        return [_json_safe(x) for x in v]
    if isinstance(v, dict):
        return {str(k): _json_safe(val) for k, val in v.items()}
    if is_dataclass(v):
        return _json_safe(asdict(v))
    return str(v)


def _json_default(o: Any) -> Any:
    if isinstance(o, Enum):
        return o.value
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    if is_dataclass(o):
        return asdict(o)
    raise TypeError(f"not JSON-serialisable: {type(o).__name__}")


def _stringify(v: Any) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    return str(v)


def _claim_from_dict(d: Mapping[str, Any]) -> CanonicalClaim:
    def _d(key: str) -> Optional[date]:
        v = d.get(key)
        if not v:
            return None
        try:
            return date.fromisoformat(str(v)[:10])
        except Exception:
            return None
    return CanonicalClaim(
        claim_id=str(d.get("claim_id", "")),
        line_number=int(d.get("line_number", 1)),
        source_system=str(d.get("source_system", "")),
        source_file=str(d.get("source_file", "")),
        source_row=int(d.get("source_row", 0)),
        ccd_row_id=str(d.get("ccd_row_id", "")),
        patient_id=str(d.get("patient_id", "")),
        patient_dob=_d("patient_dob"),
        patient_sex=d.get("patient_sex"),
        service_date_from=_d("service_date_from"),
        service_date_to=_d("service_date_to"),
        place_of_service=d.get("place_of_service"),
        bill_type=d.get("bill_type"),
        cpt_code=d.get("cpt_code"),
        cpt_modifiers=tuple(d.get("cpt_modifiers") or ()),
        icd10_primary=d.get("icd10_primary"),
        icd10_secondary=tuple(d.get("icd10_secondary") or ()),
        drg=d.get("drg"),
        billing_npi=d.get("billing_npi"),
        rendering_npi=d.get("rendering_npi"),
        facility=d.get("facility"),
        physician=d.get("physician"),
        payer_raw=d.get("payer_raw"),
        payer_canonical=d.get("payer_canonical"),
        payer_class=PayerClass(d.get("payer_class", "UNKNOWN")),
        charge_amount=_as_float(d.get("charge_amount")),
        allowed_amount=_as_float(d.get("allowed_amount")),
        paid_amount=_as_float(d.get("paid_amount")),
        patient_responsibility=_as_float(d.get("patient_responsibility")),
        adjustment_amount=_as_float(d.get("adjustment_amount")),
        adjustment_reason_codes=tuple(d.get("adjustment_reason_codes") or ()),
        status=ClaimStatus(d.get("status", "UNKNOWN")),
        submit_date=_d("submit_date"),
        paid_date=_d("paid_date"),
        denial_date=_d("denial_date"),
        denial_reason=d.get("denial_reason"),
        ingest_datetime=d.get("ingest_datetime"),
        ccd_schema_version=d.get("ccd_schema_version", CCD_SCHEMA_VERSION),
    )


def _as_float(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
