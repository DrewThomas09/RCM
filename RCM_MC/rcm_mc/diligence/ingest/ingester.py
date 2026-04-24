"""Phase 1 ingester — driver.

``ingest_dataset(path)`` walks a dataset directory (or a single file),
dispatches to the right reader for each file, feeds each :class:`RawRow`
through the normalisers, and emits a :class:`CanonicalClaimsDataset`
with a row-logged :class:`TransformationLog`.

Invariants (enforced by tests against ``tests/fixtures/messy/``):

- **Same logical claim across clinics collapses to one canonical
  ``claim_id``**. The multi-EHR rollup fixture puts three clinics'
  copies of the same 500 claims into one dataset — we emit 500
  canonical rows (not 1500), with a ``source_system`` distinct per
  row so Phase 2 can still stratify by clinic.
- **Duplicate claims are preserved but marked**. A claim resubmitted
  under three different IDs produces three rows in the CCD with a
  transformation entry linking them (rule ``duplicate_resubmit``).
  Phase 3 decides how to dedupe; Phase 1 doesn't drop information.
- **ZBA write-offs preserve the original balance**. Adjustment codes
  that force the paid amount to zero don't clobber ``charge_amount``
  or ``allowed_amount``; the adjustment is written to
  ``adjustment_amount`` + ``adjustment_reason_codes`` so the full
  trail survives.

Everything else is the reader / normaliser layer's responsibility.
"""
from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .ccd import (
    CCD_SCHEMA_VERSION,
    CanonicalClaim,
    CanonicalClaimsDataset,
    ClaimStatus,
    PayerClass,
    TransformationLog,
)
from .normalize import (
    parse_date,
    resolve_payer,
    validate_cpt,
    validate_icd,
)
from .readers import RawRow, ReaderResult, read_file


# ── Column synonyms ─────────────────────────────────────────────────
#
# Each canonical field maps to the list of source-column names it can
# come from. Ordering is preference — the first present name wins.
# Ordering also ensures deterministic behaviour under the multi-EHR
# merge.
_SYNONYMS: Dict[str, Sequence[str]] = {
    "claim_id": ("claim_id", "claim_number", "control_id",
                 "claim_control_number", "claim_ref", "reference"),
    "line_number": ("line_number", "claim_line_number", "line_num",
                    "service_line", "sequence"),
    "patient_id": ("patient_id", "mrn", "member_number", "member_id",
                   "patient_mrn", "chart_number"),
    "patient_dob": ("patient_dob", "dob", "date_of_birth", "birth_date",
                    "birthday"),
    "patient_sex": ("patient_sex", "sex", "gender"),
    "service_date_from": ("service_date_from", "service_start_date",
                          "claim_start_date", "date_of_service", "dos",
                          "from_date"),
    "service_date_to": ("service_date_to", "service_end_date",
                        "claim_end_date", "thru_date"),
    "place_of_service": ("place_of_service", "pos", "pos_code",
                         "place_of_service_code"),
    "bill_type": ("bill_type", "bill_type_code"),
    "cpt_code": ("cpt_code", "hcpcs_code", "procedure_code",
                 "primary_procedure"),
    "cpt_modifier_1": ("cpt_modifier_1", "hcpcs_modifier_1", "modifier_1",
                       "mod_1", "modifier"),
    "cpt_modifier_2": ("cpt_modifier_2", "hcpcs_modifier_2", "modifier_2", "mod_2"),
    "icd10_primary": ("icd10_primary", "diagnosis_code_1", "primary_dx",
                      "primary_diagnosis", "diagnosis"),
    "icd10_secondary_1": ("diagnosis_code_2", "secondary_dx_1"),
    "icd10_secondary_2": ("diagnosis_code_3", "secondary_dx_2"),
    "drg": ("drg", "drg_code"),
    "billing_npi": ("billing_npi", "provider_npi", "billing_provider_npi"),
    "rendering_npi": ("rendering_npi", "rendering_provider_npi",
                      "attending_npi"),
    "facility": ("facility", "facility_name", "service_location"),
    "physician": ("physician", "rendering_provider", "provider_name",
                  "physician_name"),
    "payer": ("payer", "payer_name", "insurance_name", "payer_id",
              "insurance_company"),
    "charge_amount": ("charge_amount", "billed_amount", "total_charge",
                      "total_billed", "gross_charges"),
    "allowed_amount": ("allowed_amount", "contract_allowed",
                       "allowable_amount"),
    "paid_amount": ("paid_amount", "insurance_paid", "payment_amount"),
    "patient_responsibility": ("patient_responsibility", "patient_paid",
                               "patient_share", "deductible_plus_coinsurance"),
    "adjustment_amount": ("adjustment_amount", "adjustment_total",
                          "contractual_adjustment", "write_off_amount"),
    "adjustment_reason_codes": ("adjustment_reason_codes",
                                "adjustment_code", "carc",
                                "adjustment_reason"),
    "submit_date": ("submit_date", "claim_submit_date", "date_submitted"),
    "paid_date": ("paid_date", "payment_date", "check_date", "remit_date"),
    "denial_date": ("denial_date", "denied_date"),
    "denial_reason": ("denial_reason", "denial_code", "rejection_reason"),
    "status": ("status", "claim_status"),
    "source_system": ("source_system", "data_source", "ehr", "clinic"),
}


# ── Entry point ─────────────────────────────────────────────────────

def ingest_dataset(
    path: Path | str,
    *,
    source_system_hint: Optional[str] = None,
    ingest_id: Optional[str] = None,
) -> CanonicalClaimsDataset:
    """Ingest a file or a directory into a :class:`CanonicalClaimsDataset`.

    When ``path`` is a directory, every supported file is ingested in
    filesystem-sorted order. When it's a file, a single file is read.
    Sub-directories are walked so a "three EHRs under three folders"
    layout works (fixture_02).
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"dataset not found: {p}")

    files = _collect_files(p)
    dataset = CanonicalClaimsDataset(
        source_files=[str(f.relative_to(p) if p.is_dir() else f.name) for f in files],
        ingest_id=ingest_id or _default_ingest_id(files),
    )
    log = dataset.log

    # Per-file ingest. We emit canonical rows per file and handle
    # cross-file reconciliation in _reconcile after.
    raw_results: List[Tuple[Path, ReaderResult, str]] = []
    for f in files:
        result = read_file(f)
        system = source_system_hint or _infer_source_system(f, p)
        raw_results.append((f, result, system))

    # Build canonical rows.
    for f, result, system in raw_results:
        if not result.rows:
            log.log(ccd_row_id="", source_file=str(f.name), source_row=0,
                    target_field="", source_value=None, coerced_value=None,
                    rule="reader:empty",
                    severity="WARN" if result.malformed else "INFO",
                    note=result.note or "no rows extracted")
            continue
        for raw in result.rows:
            claim = _row_to_canonical(raw, log, source_system=system)
            dataset.claims.append(claim)

    # 835 remittance reconciliation: if an 835 row for a claim_id
    # matches an 837 row, enrich the 837 row with paid_amount /
    # paid_date / status. 835-only rows (orphans) remain as-is.
    _reconcile_remittance(dataset, log)

    # Multi-EHR rollup: if the same (patient_id, service_date_from,
    # cpt_code) appears from multiple source_systems with different
    # claim_ids, collapse to the earliest observed claim_id — but keep
    # all rows in the CCD so Phase 2 can stratify by source_system.
    _roll_up_multi_ehr(dataset, log)

    # Duplicate-resubmit detection: same (patient, dos, cpt) with
    # different claim_ids in the SAME source_system — Phase 3 may
    # dedup; we mark rather than drop.
    _mark_duplicate_resubmits(dataset, log)

    # Stamp wall-time.
    now_iso = datetime.now(timezone.utc).isoformat()
    for c in dataset.claims:
        c.ingest_datetime = now_iso

    return dataset


# ── Internals ───────────────────────────────────────────────────────

_SUPPORTED_SUFFIXES = {".csv", ".tsv", ".parquet", ".xlsx", ".xlsm", ".edi"}


def _collect_files(p: Path) -> List[Path]:
    if p.is_file():
        return [p]
    files: List[Path] = []
    for child in sorted(p.rglob("*")):
        if child.is_file() and child.suffix.lower() in _SUPPORTED_SUFFIXES:
            # Skip expected.json and README.md — fixture metadata.
            if child.name in ("expected.json", "README.md"):
                continue
            files.append(child)
    return files


def _default_ingest_id(files: Sequence[Path]) -> str:
    """Deterministic ID from the file contents — same files → same id."""
    h = hashlib.sha256()
    for f in files:
        try:
            h.update(str(f).encode("utf-8"))
            with f.open("rb") as fh:
                while True:
                    b = fh.read(1 << 20)
                    if not b:
                        break
                    h.update(b)
        except OSError:
            h.update(b"<unreadable>")
    return f"ccd-{h.hexdigest()[:12]}"


def _infer_source_system(f: Path, root: Path) -> str:
    """A source_system label from the filename / directory.

    Prefer the enclosing directory name when the file is under a
    subdirectory (``fixture_02/epic/claims.csv`` → ``epic``). Otherwise
    derive from the filename stem. EDI files get a type-qualified
    label (``edi_837`` / ``edi_835``).
    """
    if f.suffix.lower() == ".edi":
        text = f.read_text(encoding="latin-1", errors="replace")[:200]
        if "ST*835" in text:
            return "edi_835"
        return "edi_837"
    if root.is_dir() and f.parent != root:
        return f.parent.name.lower()
    return f.stem.lower()


def _row_to_canonical(
    raw: RawRow, log: TransformationLog, *, source_system: str,
) -> CanonicalClaim:
    """Convert one raw source row into a canonical claim."""
    values = raw.values
    claim_id = _first_present(values, _SYNONYMS["claim_id"]) or ""
    claim_id_str = str(claim_id).strip()
    ccd_row_id = _derive_row_id(source_system, raw.source_file, raw.row_number,
                                claim_id_str)

    def _dt(field: str) -> Optional[date]:
        raw_val = _first_present(values, _SYNONYMS[field])
        return parse_date(raw_val, log,
                          ccd_row_id=ccd_row_id, source_file=raw.source_file,
                          source_row=raw.row_number, target_field=field)

    def _str(field: str) -> Optional[str]:
        v = _first_present(values, _SYNONYMS[field])
        if v is None or str(v).strip() == "":
            return None
        return str(v).strip()

    def _amt(field: str) -> Optional[float]:
        v = _first_present(values, _SYNONYMS[field])
        coerced = _to_float(v)
        if v is not None and coerced is None:
            log.log(ccd_row_id=ccd_row_id, source_file=raw.source_file,
                    source_row=raw.row_number, target_field=field,
                    source_value=v, coerced_value=None,
                    rule="amount_parse:unparseable",
                    severity="WARN", note=f"could not parse {v!r} as amount")
        return coerced

    payer_raw_val = _first_present(values, _SYNONYMS["payer"])
    payer_raw, payer_canonical, payer_class = resolve_payer(
        payer_raw_val, log, ccd_row_id=ccd_row_id,
        source_file=raw.source_file, source_row=raw.row_number,
    )

    cpt = validate_cpt(
        _first_present(values, _SYNONYMS["cpt_code"]), log,
        ccd_row_id=ccd_row_id, source_file=raw.source_file,
        source_row=raw.row_number,
    )
    icd_primary = validate_icd(
        _first_present(values, _SYNONYMS["icd10_primary"]), log,
        ccd_row_id=ccd_row_id, source_file=raw.source_file,
        source_row=raw.row_number, is_primary=True,
    )
    icd_secondary = tuple(
        validated for validated in (
            validate_icd(
                _first_present(values, _SYNONYMS[k]), log,
                ccd_row_id=ccd_row_id, source_file=raw.source_file,
                source_row=raw.row_number, is_primary=False,
            )
            for k in ("icd10_secondary_1", "icd10_secondary_2")
        ) if validated
    )

    cpt_mods = tuple(
        m for m in (_str("cpt_modifier_1"), _str("cpt_modifier_2")) if m
    )

    status_raw = _str("status")
    status = _coerce_status(status_raw, raw.source_format.value, values, log,
                            ccd_row_id=ccd_row_id,
                            source_file=raw.source_file,
                            source_row=raw.row_number)

    # ZBA write-off preservation: if paid_amount is 0 and an adjustment
    # amount is present, retain both — do NOT propagate the zero into
    # allowed_amount or charge_amount. This is the fixture_10 invariant.
    charge = _amt("charge_amount")
    allowed = _amt("allowed_amount")
    paid = _amt("paid_amount")
    adj_amt = _amt("adjustment_amount")
    adj_codes = _parse_reason_codes(_first_present(values, _SYNONYMS["adjustment_reason_codes"]))

    if (paid == 0.0 or paid is None) and (adj_amt and adj_amt > 0):
        log.log(ccd_row_id=ccd_row_id, source_file=raw.source_file,
                source_row=raw.row_number, target_field="adjustment_amount",
                source_value=adj_amt, coerced_value=adj_amt,
                rule="zba_writeoff:preserve",
                severity="INFO",
                note="zero paid + nonzero adjustment — original balance preserved")

    # line_number default is 1 if absent.
    line_num_raw = _first_present(values, _SYNONYMS["line_number"])
    try:
        line_num = int(line_num_raw) if line_num_raw not in (None, "") else 1
    except (TypeError, ValueError):
        line_num = 1

    return CanonicalClaim(
        claim_id=claim_id_str,
        line_number=line_num,
        source_system=source_system,
        source_file=raw.source_file,
        source_row=raw.row_number,
        ccd_row_id=ccd_row_id,
        patient_id=str(_first_present(values, _SYNONYMS["patient_id"]) or ""),
        patient_dob=_dt("patient_dob"),
        patient_sex=_str("patient_sex"),
        service_date_from=_dt("service_date_from"),
        service_date_to=_dt("service_date_to"),
        place_of_service=_str("place_of_service"),
        bill_type=_str("bill_type"),
        cpt_code=cpt,
        cpt_modifiers=cpt_mods,
        icd10_primary=icd_primary,
        icd10_secondary=icd_secondary,
        drg=_str("drg"),
        billing_npi=_str("billing_npi"),
        rendering_npi=_str("rendering_npi"),
        facility=_str("facility"),
        physician=_str("physician"),
        payer_raw=payer_raw,
        payer_canonical=payer_canonical,
        payer_class=payer_class,
        charge_amount=charge,
        allowed_amount=allowed,
        paid_amount=paid,
        patient_responsibility=_amt("patient_responsibility"),
        adjustment_amount=adj_amt,
        adjustment_reason_codes=adj_codes,
        status=status,
        submit_date=_dt("submit_date"),
        paid_date=_dt("paid_date"),
        denial_date=_dt("denial_date"),
        denial_reason=_str("denial_reason"),
        ccd_schema_version=CCD_SCHEMA_VERSION,
    )


def _first_present(values: Mapping[str, Any], keys: Sequence[str]) -> Any:
    """Return the first non-empty value from ``values`` matching any
    key in ``keys`` (case-insensitive, whitespace-insensitive)."""
    lower = {str(k).strip().lower(): v for k, v in values.items()
             if k is not None}
    for k in keys:
        v = lower.get(k.lower())
        if v is not None and str(v).strip() != "":
            return v
    return None


def _derive_row_id(system: str, source_file: str, row_num: int, claim_id: str) -> str:
    """Stable synthetic row id. Used by TransformationLog + dedup."""
    h = hashlib.sha1(f"{system}|{source_file}|{row_num}|{claim_id}".encode("utf-8"))
    return f"r-{h.hexdigest()[:12]}"


def _to_float(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    s = str(v).strip()
    # Strip common currency formatting.
    s = s.replace("$", "").replace(",", "").replace(" ", "")
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1]   # accounting-style negatives
    try:
        return float(s)
    except ValueError:
        return None


def _parse_reason_codes(v: Any) -> Tuple[str, ...]:
    if v is None or str(v).strip() == "":
        return ()
    s = str(v).strip()
    # Accept comma / pipe / semicolon delimiters.
    parts = re.split(r"[,;|]", s)
    return tuple(p.strip().upper() for p in parts if p.strip())


def _coerce_status(
    raw_value: Optional[str],
    source_format: str,
    values: Mapping[str, Any],
    log: TransformationLog,
    *,
    ccd_row_id: str,
    source_file: str,
    source_row: int,
) -> ClaimStatus:
    """Derive a canonical ClaimStatus.

    If the source has an explicit status column, prefer that. For
    EDI 835 rows without an explicit field, use the CLP02 status_code
    (1=paid primary, 2=paid secondary, 3=paid tertiary, 4=denied,
    …).
    """
    if raw_value:
        key = raw_value.strip().lower()
        mapping = {
            "submitted": ClaimStatus.SUBMITTED,
            "accepted": ClaimStatus.ACCEPTED,
            "denied": ClaimStatus.DENIED,
            "paid": ClaimStatus.PAID,
            "rework": ClaimStatus.REWORK,
            "appeal": ClaimStatus.REWORK,
            "written_off": ClaimStatus.WRITTEN_OFF,
            "writeoff": ClaimStatus.WRITTEN_OFF,
            "write-off": ClaimStatus.WRITTEN_OFF,
        }
        if key in mapping:
            return mapping[key]
    # 835 CLP02 codes
    status_code = _first_present(values, ("status_code",))
    if status_code is not None:
        sc = str(status_code).strip()
        if sc in ("1", "2", "3"):
            return ClaimStatus.PAID
        if sc == "4":
            return ClaimStatus.DENIED
        if sc == "22":  # reversal
            return ClaimStatus.REWORK
    # Fall back based on presence of paid_amount.
    paid = _to_float(_first_present(values, _SYNONYMS["paid_amount"]))
    if paid is None:
        return ClaimStatus.SUBMITTED
    if paid > 0:
        return ClaimStatus.PAID
    return ClaimStatus.SUBMITTED


# ── Cross-file reconciliation ───────────────────────────────────────

def _reconcile_remittance(
    dataset: CanonicalClaimsDataset, log: TransformationLog,
) -> None:
    """When an 835 row shares a claim_id with an 837 row, enrich the
    837 with paid_amount + paid_date + status. Log the reconciliation
    on both rows. Orphaned 835s remain unchanged."""
    by_id_837: Dict[str, CanonicalClaim] = {}
    for c in dataset.claims:
        if c.source_system == "edi_837":
            by_id_837.setdefault(c.claim_id, c)

    for c in dataset.claims:
        if c.source_system != "edi_835":
            continue
        parent = by_id_837.get(c.claim_id)
        if parent is None:
            log.log(ccd_row_id=c.ccd_row_id, source_file=c.source_file,
                    source_row=c.source_row, target_field="paid_amount",
                    source_value=c.paid_amount, coerced_value=c.paid_amount,
                    rule="remittance:orphan",
                    severity="WARN",
                    note="835 row has no matching 837 — retained as standalone")
            continue
        if c.paid_amount is not None and parent.paid_amount is None:
            parent.paid_amount = c.paid_amount
            log.log(ccd_row_id=parent.ccd_row_id, source_file=parent.source_file,
                    source_row=parent.source_row, target_field="paid_amount",
                    source_value=None, coerced_value=parent.paid_amount,
                    rule="remittance:enriched",
                    note=f"paid_amount joined from 835 row {c.ccd_row_id}")
        if parent.status == ClaimStatus.SUBMITTED and c.status in (
            ClaimStatus.PAID, ClaimStatus.DENIED, ClaimStatus.REWORK,
        ):
            parent.status = c.status
            log.log(ccd_row_id=parent.ccd_row_id, source_file=parent.source_file,
                    source_row=parent.source_row, target_field="status",
                    source_value="SUBMITTED", coerced_value=parent.status.value,
                    rule="remittance:status_advance",
                    note=f"status advanced from 835 row {c.ccd_row_id}")


def _roll_up_multi_ehr(
    dataset: CanonicalClaimsDataset, log: TransformationLog,
) -> None:
    """When three EHRs each export the same 500 claims under different
    claim_ids (fixture_02), we want one canonical ``claim_id`` per
    logical claim while keeping each source_system's row visible.

    Heuristic: group by (patient_id, service_date_from, cpt_code). If
    a group has >1 distinct claim_id across source systems, rename all
    rows in the group to the lexicographically smallest claim_id,
    logging the rewrite per row.
    """
    groups: Dict[Tuple[str, str, str], List[CanonicalClaim]] = {}
    for c in dataset.claims:
        if not c.patient_id or not c.service_date_from or not c.cpt_code:
            continue
        key = (c.patient_id, c.service_date_from.isoformat(), c.cpt_code)
        groups.setdefault(key, []).append(c)

    for key, rows in groups.items():
        distinct_ids = {r.claim_id for r in rows if r.claim_id}
        distinct_systems = {r.source_system for r in rows}
        if len(distinct_ids) <= 1 or len(distinct_systems) <= 1:
            continue
        canonical = sorted(distinct_ids)[0]
        for r in rows:
            if r.claim_id == canonical:
                continue
            log.log(ccd_row_id=r.ccd_row_id, source_file=r.source_file,
                    source_row=r.source_row, target_field="claim_id",
                    source_value=r.claim_id, coerced_value=canonical,
                    rule="multi_ehr_rollup",
                    note=f"three-EHR collapse: {r.source_system} "
                         f"{r.claim_id} → {canonical}")
            r.claim_id = canonical


def _mark_duplicate_resubmits(
    dataset: CanonicalClaimsDataset, log: TransformationLog,
) -> None:
    """Same (patient, service_date, cpt) with different claim_ids in
    the SAME source_system → resubmit pattern. Rows retained; marked
    via transformation entry."""
    groups: Dict[Tuple[str, str, str, str], List[CanonicalClaim]] = {}
    for c in dataset.claims:
        if not c.patient_id or not c.service_date_from or not c.cpt_code:
            continue
        key = (c.source_system, c.patient_id,
               c.service_date_from.isoformat(), c.cpt_code)
        groups.setdefault(key, []).append(c)

    for rows in groups.values():
        ids = {r.claim_id for r in rows}
        if len(ids) <= 1:
            continue
        for r in rows:
            log.log(ccd_row_id=r.ccd_row_id, source_file=r.source_file,
                    source_row=r.source_row, target_field="claim_id",
                    source_value=r.claim_id, coerced_value=r.claim_id,
                    rule="duplicate_resubmit",
                    severity="WARN",
                    note=f"duplicate resubmit cohort of {len(rows)} rows "
                         f"sharing (patient, service_date, cpt)")
