"""Normalisation primitives used by the ingester.

Each function takes a raw value + a TransformationLog + the row context
needed to log its decision, and returns the coerced value. All log
entries are row-scoped so "why is this field what it is?" is one
filter away.

These live here, separate from ccd.py, so that schema changes don't
ripple through the normalisation code and vice versa.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, timedelta
from typing import Any, Iterable, Mapping, Optional, Sequence, Tuple

from .ccd import PayerClass, TransformationLog


# ── Date parsing ────────────────────────────────────────────────────

_ISO_RE = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$")
_COMPACT_YYYYMMDD_RE = re.compile(r"^(\d{4})(\d{2})(\d{2})$")    # X12/EDI format
_US_RE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{2,4})$")
_US_DASH_RE = re.compile(r"^(\d{1,2})-(\d{1,2})-(\d{2,4})$")
_EU_RE = re.compile(r"^(\d{1,2})\.(\d{1,2})\.(\d{2,4})$")
# Excel serial date — days since 1899-12-30 (the "Lotus 1-2-3 leap bug")
_EXCEL_EPOCH = date(1899, 12, 30)


def parse_date(
    raw: Any,
    log: TransformationLog,
    *,
    ccd_row_id: str,
    source_file: str,
    source_row: int,
    target_field: str,
) -> Optional[date]:
    """Parse a heterogeneous date representation into a ``date``.

    Accepts: ISO ``YYYY-MM-DD``, US ``MM/DD/YYYY`` (or 2-digit year),
    US dashed ``MM-DD-YYYY``, European ``DD.MM.YYYY``, Unix epoch
    integer (treated as UTC), Excel serial date (days since
    1899-12-30), and actual ``date``/``datetime`` objects.

    Logs a transformation entry either way — INFO on success, WARN on
    fallback, ERROR on unparseable.
    """
    if raw is None or raw == "" or str(raw).strip().lower() in ("null", "none", "n/a", "na"):
        return None
    if isinstance(raw, datetime):
        log.log(ccd_row_id=ccd_row_id, source_file=source_file,
                source_row=source_row, target_field=target_field,
                source_value=raw, coerced_value=raw.date().isoformat(),
                rule="date_parse:datetime_native")
        return raw.date()
    if isinstance(raw, date):
        log.log(ccd_row_id=ccd_row_id, source_file=source_file,
                source_row=source_row, target_field=target_field,
                source_value=raw, coerced_value=raw.isoformat(),
                rule="date_parse:date_native")
        return raw

    s = str(raw).strip()
    # ISO
    m = _ISO_RE.match(s)
    if m:
        try:
            y, mm, dd = int(m[1]), int(m[2]), int(m[3])
            d = date(y, mm, dd)
            log.log(ccd_row_id=ccd_row_id, source_file=source_file,
                    source_row=source_row, target_field=target_field,
                    source_value=s, coerced_value=d.isoformat(),
                    rule="date_parse:iso")
            return d
        except ValueError:
            pass
    # Compact YYYYMMDD (X12/EDI)
    m = _COMPACT_YYYYMMDD_RE.match(s)
    if m:
        try:
            y, mm, dd = int(m[1]), int(m[2]), int(m[3])
            d = date(y, mm, dd)
            log.log(ccd_row_id=ccd_row_id, source_file=source_file,
                    source_row=source_row, target_field=target_field,
                    source_value=s, coerced_value=d.isoformat(),
                    rule="date_parse:iso")
            return d
        except ValueError:
            pass
    # US / US-dashed
    for rgx, rule in ((_US_RE, "date_parse:us_slash"),
                      (_US_DASH_RE, "date_parse:us_dash")):
        m = rgx.match(s)
        if m:
            try:
                mm, dd, y = int(m[1]), int(m[2]), int(m[3])
                if y < 100:
                    # 2-digit year — assume 2000s for 00-69, 1900s for 70-99.
                    y = 2000 + y if y < 70 else 1900 + y
                d = date(y, mm, dd)
                log.log(ccd_row_id=ccd_row_id, source_file=source_file,
                        source_row=source_row, target_field=target_field,
                        source_value=s, coerced_value=d.isoformat(),
                        rule=rule)
                return d
            except ValueError:
                pass
    # European
    m = _EU_RE.match(s)
    if m:
        try:
            dd, mm, y = int(m[1]), int(m[2]), int(m[3])
            if y < 100:
                y = 2000 + y if y < 70 else 1900 + y
            d = date(y, mm, dd)
            log.log(ccd_row_id=ccd_row_id, source_file=source_file,
                    source_row=source_row, target_field=target_field,
                    source_value=s, coerced_value=d.isoformat(),
                    rule="date_parse:eu_dot")
            return d
        except ValueError:
            pass
    # Excel serial — plausible if integer-like and in a reasonable range.
    if s.isdigit() or (s.startswith("-") and s[1:].isdigit()):
        try:
            serial = int(s)
            if 10_000 < serial < 60_000:
                d = _EXCEL_EPOCH + timedelta(days=serial)
                log.log(ccd_row_id=ccd_row_id, source_file=source_file,
                        source_row=source_row, target_field=target_field,
                        source_value=s, coerced_value=d.isoformat(),
                        rule="date_parse:excel_serial",
                        severity="WARN",
                        note="interpreted Excel serial date — confirm timezone handling")
                return d
            if 1_000_000_000 < serial < 9_999_999_999:
                # 10-digit Unix epoch seconds (2001-09-09 .. 2286)
                d = datetime.fromtimestamp(serial).date()
                log.log(ccd_row_id=ccd_row_id, source_file=source_file,
                        source_row=source_row, target_field=target_field,
                        source_value=s, coerced_value=d.isoformat(),
                        rule="date_parse:unix_epoch")
                return d
        except (ValueError, OSError):
            pass

    log.log(ccd_row_id=ccd_row_id, source_file=source_file,
            source_row=source_row, target_field=target_field,
            source_value=s, coerced_value=None,
            rule="date_parse:unparseable",
            severity="ERROR", note=f"could not parse {s!r} as a date")
    return None


# ── Payer resolution ────────────────────────────────────────────────

# Canonical payer → PayerClass map. Extend when partners surface a new
# payer; the dictionary is intentionally small + auditable so partners
# can scrutinise which "Blue Cross" variant resolves to what.
_PAYER_CANONICAL_MAP = {
    # Medicare family
    "medicare": ("Medicare", PayerClass.MEDICARE),
    "mcare": ("Medicare", PayerClass.MEDICARE),
    "medicare part a": ("Medicare", PayerClass.MEDICARE),
    "medicare part b": ("Medicare", PayerClass.MEDICARE),
    "cms": ("Medicare", PayerClass.MEDICARE),
    # Medicare Advantage
    "humana medicare": ("Humana Medicare Advantage", PayerClass.MEDICARE_ADVANTAGE),
    "humana": ("Humana", PayerClass.COMMERCIAL),
    "humana gold plus": ("Humana Medicare Advantage", PayerClass.MEDICARE_ADVANTAGE),
    "aetna medicare": ("Aetna Medicare Advantage", PayerClass.MEDICARE_ADVANTAGE),
    "united medicare": ("UHC Medicare Advantage", PayerClass.MEDICARE_ADVANTAGE),
    "uhc medicare advantage": ("UHC Medicare Advantage", PayerClass.MEDICARE_ADVANTAGE),
    # Medicaid
    "medicaid": ("Medicaid", PayerClass.MEDICAID),
    "mcaid": ("Medicaid", PayerClass.MEDICAID),
    "state medicaid": ("Medicaid", PayerClass.MEDICAID),
    # Blue Cross family — heavy synonymy
    "blue cross": ("Blue Cross Blue Shield", PayerClass.COMMERCIAL),
    "blue cross blue shield": ("Blue Cross Blue Shield", PayerClass.COMMERCIAL),
    "bcbs": ("Blue Cross Blue Shield", PayerClass.COMMERCIAL),
    "bcbs of il": ("Blue Cross Blue Shield", PayerClass.COMMERCIAL),
    "bcbs of illinois": ("Blue Cross Blue Shield", PayerClass.COMMERCIAL),
    "bcbs of tx": ("Blue Cross Blue Shield", PayerClass.COMMERCIAL),
    "bc bs": ("Blue Cross Blue Shield", PayerClass.COMMERCIAL),
    "blue x bs": ("Blue Cross Blue Shield", PayerClass.COMMERCIAL),
    "bluecross": ("Blue Cross Blue Shield", PayerClass.COMMERCIAL),
    "blue cross ppo": ("Blue Cross Blue Shield", PayerClass.COMMERCIAL),
    "anthem bcbs": ("Anthem Blue Cross Blue Shield", PayerClass.COMMERCIAL),
    "anthem": ("Anthem", PayerClass.COMMERCIAL),
    # Commercials
    "aetna": ("Aetna", PayerClass.COMMERCIAL),
    "aetna ppo": ("Aetna", PayerClass.COMMERCIAL),
    "aetna hmo": ("Aetna", PayerClass.COMMERCIAL),
    "united": ("UnitedHealthcare", PayerClass.COMMERCIAL),
    "unitedhealthcare": ("UnitedHealthcare", PayerClass.COMMERCIAL),
    "uhc": ("UnitedHealthcare", PayerClass.COMMERCIAL),
    "cigna": ("Cigna", PayerClass.COMMERCIAL),
    "cigna healthspring": ("Cigna", PayerClass.COMMERCIAL),
    # Self-pay / WC / TRICARE
    "self pay": ("Self-Pay", PayerClass.SELF_PAY),
    "self-pay": ("Self-Pay", PayerClass.SELF_PAY),
    "patient pay": ("Self-Pay", PayerClass.SELF_PAY),
    "workers comp": ("Workers Compensation", PayerClass.WORKERS_COMP),
    "workers compensation": ("Workers Compensation", PayerClass.WORKERS_COMP),
    "wc": ("Workers Compensation", PayerClass.WORKERS_COMP),
    "tricare": ("TRICARE", PayerClass.TRICARE),
}


def resolve_payer(
    raw: Any,
    log: TransformationLog,
    *,
    ccd_row_id: str,
    source_file: str,
    source_row: int,
) -> Tuple[Optional[str], Optional[str], PayerClass]:
    """Return (payer_raw, payer_canonical, payer_class).

    Resolution strategy:
    1. Strip, lowercase, remove punctuation, collapse whitespace.
    2. Exact match in the canonical map.
    3. Substring match against every map key, picking the longest
       matching key (so "humana medicare" beats "humana").
    4. Fall back to UNKNOWN + log a WARN so the partner can see the
       unresolved rate in Phase 2.
    """
    if raw is None or str(raw).strip() == "":
        return None, None, PayerClass.UNKNOWN
    raw_s = str(raw)
    key = _normalise_payer_key(raw_s)
    if key in _PAYER_CANONICAL_MAP:
        canon, cls = _PAYER_CANONICAL_MAP[key]
        log.log(ccd_row_id=ccd_row_id, source_file=source_file,
                source_row=source_row, target_field="payer_class",
                source_value=raw_s, coerced_value=cls.value,
                rule="payer_resolve:exact",
                note=f"canonical: {canon}")
        return raw_s, canon, cls
    # Longest-prefix substring match.
    match_key: Optional[str] = None
    for k in _PAYER_CANONICAL_MAP:
        if k in key and (match_key is None or len(k) > len(match_key)):
            match_key = k
    if match_key:
        canon, cls = _PAYER_CANONICAL_MAP[match_key]
        log.log(ccd_row_id=ccd_row_id, source_file=source_file,
                source_row=source_row, target_field="payer_class",
                source_value=raw_s, coerced_value=cls.value,
                rule="payer_resolve:substring",
                note=f"matched '{match_key}' → {canon}")
        return raw_s, canon, cls
    log.log(ccd_row_id=ccd_row_id, source_file=source_file,
            source_row=source_row, target_field="payer_class",
            source_value=raw_s, coerced_value=PayerClass.UNKNOWN.value,
            rule="payer_resolve:unresolved",
            severity="WARN",
            note="no canonical match — left as UNKNOWN")
    return raw_s, None, PayerClass.UNKNOWN


def _normalise_payer_key(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


# ── CPT / ICD validation ────────────────────────────────────────────

# HCPCS-compatible CPT: 5-char alphanumeric, starting with digit for
# standard CPT, letter for HCPCS Level II.
_CPT_RE = re.compile(r"^[A-Z0-9]{5}$")
_ICD10_RE = re.compile(r"^[A-TV-Z][0-9][0-9A-Z](\.[0-9A-Z]{1,4})?$")
_ICD9_RE = re.compile(r"^(E\d{3}(\.\d{1,2})?|V\d{2}(\.\d{1,2})?|\d{3}(\.\d{1,2})?)$")


def validate_cpt(
    raw: Any,
    log: TransformationLog,
    *,
    ccd_row_id: str,
    source_file: str,
    source_row: int,
) -> Optional[str]:
    """Validate + normalise a CPT/HCPCS code. Returns the uppercased
    value if it matches the HCPCS shape, else logs WARN and returns
    the raw string (we preserve unknown codes rather than dropping —
    Phase 3 wants to see them)."""
    if raw is None or str(raw).strip() == "":
        return None
    s = str(raw).strip().upper()
    if _CPT_RE.match(s):
        log.log(ccd_row_id=ccd_row_id, source_file=source_file,
                source_row=source_row, target_field="cpt_code",
                source_value=raw, coerced_value=s,
                rule="cpt_validate:ok")
        return s
    log.log(ccd_row_id=ccd_row_id, source_file=source_file,
            source_row=source_row, target_field="cpt_code",
            source_value=raw, coerced_value=s,
            rule="cpt_validate:non_standard",
            severity="WARN",
            note="preserved for Phase 3 review; does not match HCPCS shape")
    return s


def validate_icd(
    raw: Any,
    log: TransformationLog,
    *,
    ccd_row_id: str,
    source_file: str,
    source_row: int,
    is_primary: bool = True,
) -> Optional[str]:
    """Validate + normalise an ICD-10 code. Accepts ICD-9 with a WARN
    log entry (drifted legacy data). Returns uppercased value."""
    if raw is None or str(raw).strip() == "":
        return None
    s = str(raw).strip().upper()
    field = "icd10_primary" if is_primary else "icd10_secondary"
    if _ICD10_RE.match(s):
        log.log(ccd_row_id=ccd_row_id, source_file=source_file,
                source_row=source_row, target_field=field,
                source_value=raw, coerced_value=s,
                rule="icd_validate:icd10_ok")
        return s
    if _ICD9_RE.match(s):
        log.log(ccd_row_id=ccd_row_id, source_file=source_file,
                source_row=source_row, target_field=field,
                source_value=raw, coerced_value=s,
                rule="icd_validate:icd9_legacy",
                severity="WARN",
                note="ICD-9 coding retained; Phase 2 should stratify")
        return s
    log.log(ccd_row_id=ccd_row_id, source_file=source_file,
            source_row=source_row, target_field=field,
            source_value=raw, coerced_value=s,
            rule="icd_validate:malformed",
            severity="WARN",
            note="preserved as-is for Phase 3 review")
    return s


# ── Duplicate detection ─────────────────────────────────────────────

def detect_duplicates(
    rows: Sequence[Mapping[str, Any]],
) -> Iterable[Tuple[str, int, int]]:
    """Yield (claim_id, first_index, duplicate_index) for rows that
    share a claim_id. Callers log a transformation per duplicate."""
    seen: dict[str, int] = {}
    for i, row in enumerate(rows):
        cid = str(row.get("claim_id") or "")
        if not cid:
            continue
        if cid in seen:
            yield cid, seen[cid], i
        else:
            seen[cid] = i


def detect_near_duplicates(
    rows: Sequence[Mapping[str, Any]],
) -> Iterable[Tuple[int, int, str]]:
    """Yield (first_index, duplicate_index, reason) for rows that
    share the (patient_id, service_date_from, cpt_code) tuple but
    have different claim_ids — the "same claim resubmitted under a
    different ID" pattern (fixture_09)."""
    seen: dict[tuple, int] = {}
    for i, row in enumerate(rows):
        key = (
            str(row.get("patient_id") or ""),
            str(row.get("service_date_from") or ""),
            str(row.get("cpt_code") or "").upper(),
        )
        if not all(key):
            continue
        if key in seen:
            yield seen[key], i, "same patient+service_date+cpt, different claim_id"
        else:
            seen[key] = i
